import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Callable, Dict, Mapping, Tuple
from urllib import error as urllib_error, parse as urllib_parse, request as urllib_request

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
COMPOSE_FILE = BACKEND_DIR / "docker" / "docker-compose.yml"
DEFAULT_ENV: Dict[str, str] = {
    "POSTGRES_USER": "appuser",
    "POSTGRES_PASSWORD": "apppass",
    "POSTGRES_DB": "postgres",
    "POSTGRES_DB_AUTH": "auth_service",
    "POSTGRES_DB_DOCUMENTS": "document_service",
    "POSTGRES_DB_ORCHESTRATOR": "agent_orchestrator",
    "POSTGRES_DB_BILLING": "billing_service",
    "MINIO_ROOT_USER": "minioadmin",
    "MINIO_ROOT_PASSWORD": "minioadmin",
    "MINIO_ENDPOINT": "minio:9000",
    "MINIO_ACCESS_KEY": "minioadmin",
    "MINIO_SECRET_KEY": "minioadmin",
    "REDIS_URL": "redis://redis:6379/0",
    "SECRET_KEY": "super-secret-key",
    "GEMINI_API_KEY": "dummy-gemini-key",
    "BILLING_SERVICE_URL": "http://billing-service:8004",
}
STARTUP_TIMEOUT = int(os.environ.get("E2E_STARTUP_TIMEOUT", "240"))


def _run_compose(args: list[str], env: Dict[str, str], check: bool = True) -> None:
    command = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    subprocess.run(command, cwd=BACKEND_DIR, env=env, check=check)


def _wait_for_gateway(base_url: str) -> None:
    health_url = f"{base_url.rstrip('/')}/auth/health"
    deadline = time.time() + STARTUP_TIMEOUT
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with urllib_request.urlopen(health_url, timeout=5) as response:
                if response.status == 200:
                    return
                last_error = RuntimeError(
                    f"Unexpected status {response.status}: {response.read().decode()}"
                )
        except urllib_error.URLError as exc:  # pragma: no cover - network errors
            last_error = exc
        time.sleep(2)

    raise RuntimeError(
        f"Gateway at {health_url} did not become healthy: {last_error}"
    )


@dataclass
class SimpleResponse:
    status_code: int
    content: bytes
    headers: Mapping[str, str]

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.text)


def _encode_multipart(
    fields: Mapping[str, str],
    files: Mapping[str, Tuple[str, BytesIO | bytes, str]],
) -> Tuple[bytes, str]:
    boundary = f"----E2E{uuid.uuid4().hex}"
    buffer = BytesIO()
    boundary_bytes = boundary.encode()

    for name, value in fields.items():
        buffer.write(b"--" + boundary_bytes + b"\r\n")
        buffer.write(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        )
        buffer.write(str(value).encode())
        buffer.write(b"\r\n")

    for name, (filename, file_content, content_type) in files.items():
        if hasattr(file_content, "read"):
            data = file_content.read()
            if hasattr(file_content, "seek"):
                file_content.seek(0)
        else:
            data = file_content
        if isinstance(data, str):
            data = data.encode()

        buffer.write(b"--" + boundary_bytes + b"\r\n")
        buffer.write(
            (
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"\r\n'
            ).encode()
        )
        buffer.write(f"Content-Type: {content_type}\r\n\r\n".encode())
        buffer.write(data)
        buffer.write(b"\r\n")

    buffer.write(b"--" + boundary_bytes + b"--\r\n")
    content_type = f"multipart/form-data; boundary={boundary}"
    return buffer.getvalue(), content_type


class APIGatewayClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def close(self) -> None:  # pragma: no cover - stateless client
        return None

    def _prepare_body(
        self,
        *,
        json_payload=None,
        data=None,
        files: Mapping[str, Tuple[str, BytesIO | bytes, str]] | None = None,
    ) -> Tuple[bytes | None, Dict[str, str]]:
        headers: Dict[str, str] = {"Accept": "application/json"}
        if files:
            form_fields = data or {}
            body, content_type = _encode_multipart(form_fields, files)
            headers["Content-Type"] = content_type
            return body, headers
        if json_payload is not None:
            body = json.dumps(json_payload).encode()
            headers.setdefault("Content-Type", "application/json")
            return body, headers
        if isinstance(data, dict):
            body = urllib_parse.urlencode(data).encode()
            headers.setdefault(
                "Content-Type", "application/x-www-form-urlencoded"
            )
            return body, headers
        return None, headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload=None,
        data=None,
        files=None,
        headers: Mapping[str, str] | None = None,
        timeout: int = 30,
    ) -> SimpleResponse:
        url = f"{self.base_url}{path}"
        body, default_headers = self._prepare_body(
            json_payload=json_payload, data=data, files=files
        )
        request_headers = dict(default_headers)
        if headers:
            request_headers.update(headers)
        req = urllib_request.Request(url, data=body, headers=request_headers, method=method)
        try:
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                return SimpleResponse(resp.status, resp.read(), dict(resp.headers))
        except urllib_error.HTTPError as exc:
            return SimpleResponse(exc.code, exc.read(), dict(exc.headers or {}))

    def post(self, path: str, json=None, **kwargs) -> SimpleResponse:
        if json is not None:
            kwargs["json_payload"] = json
        return self._request("POST", path, **kwargs)

    def get(self, path: str, **kwargs) -> SimpleResponse:
        return self._request("GET", path, **kwargs)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.environ.get("E2E_GATEWAY_BASE_URL", "http://localhost")


@pytest.fixture(scope="session")
def compose_env() -> Dict[str, str]:
    env = os.environ.copy()
    for key, value in DEFAULT_ENV.items():
        env.setdefault(key, value)
    return env


@pytest.fixture(scope="session", autouse=True)
def docker_stack(compose_env: Dict[str, str], api_base_url: str):
    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is required for backend E2E tests.", allow_module_level=True)
    _run_compose(["down", "-v"], env=compose_env, check=False)
    _run_compose(["up", "-d", "--build"], env=compose_env)
    _wait_for_gateway(api_base_url)
    yield
    _run_compose(["down", "-v"], env=compose_env, check=False)


@pytest.fixture()
def api_client(api_base_url: str) -> APIGatewayClient:
    client = APIGatewayClient(api_base_url)
    yield client
    client.close()


@pytest.fixture()
def ensure_user_balance(compose_env: Dict[str, str]) -> Callable[[str, int], None]:
    def _ensure(user_id: str, amount: int) -> None:
        sql = (
            "INSERT INTO user_balances (user_id, balance) VALUES "
            f"('{user_id}', {amount}) "
            "ON CONFLICT (user_id) DO UPDATE SET balance = EXCLUDED.balance;"
        )
        args = [
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            compose_env["POSTGRES_USER"],
            "-d",
            compose_env["POSTGRES_DB_BILLING"],
            "-c",
            sql,
        ]
        _run_compose(args, env=compose_env)

    return _ensure
