"""
Smoke script to quickly validate the public API flow:
register -> login -> profile -> billing -> upload (with polling) -> chat.

Configure with environment variables or CLI flags:
- SMOKE_BASE_URL / --base-url: API gateway base URL (default: http://localhost:8080/api)
- SMOKE_AGENT_ID / --agent-id: UUID of an existing agent for the chat step.
- SMOKE_DOCUMENT_TYPE / --document-type: Optional document type for upload.
"""
from __future__ import annotations

import argparse
import os
import time
import uuid
from io import BytesIO
from typing import Any, Dict

import requests


DEFAULT_BASE_URL = "http://localhost:8080/api"
DEFAULT_DOCUMENT_TYPE = "NOTA_FISCAL_EMITIDA"


class SmokeFailure(RuntimeError):
    """Raised when a smoke step fails."""


class SmokeClient:
    def __init__(self, base_url: str, agent_id: uuid.UUID, document_type: str):
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.document_type = document_type
        self.session = requests.Session()

    def _expect_status(self, response: requests.Response, expected: int, step: str) -> None:
        if response.status_code != expected:
            raise SmokeFailure(
                f"Step '{step}' failed: expected HTTP {expected}, got {response.status_code}. "
                f"Response: {response.text}"
            )

    def register(self, email: str, password: str) -> uuid.UUID:
        payload = {"full_name": "Smoke Tester", "email": email, "password": password}
        response = self.session.post(f"{self.base_url}/auth/register", json=payload, timeout=15)
        self._expect_status(response, 201, "register")
        body: Dict[str, Any] = response.json()
        return uuid.UUID(body["id"])

    def login(self, email: str, password: str) -> str:
        data = {"username": email, "password": password}
        response = self.session.post(f"{self.base_url}/auth/login", data=data, timeout=15)
        self._expect_status(response, 200, "login")
        body: Dict[str, Any] = response.json()
        token = body["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        return token

    def profile(self) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/auth/profile", timeout=10)
        self._expect_status(response, 200, "profile")
        return response.json()

    def billing_balance(self, user_id: uuid.UUID) -> Dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/billing/balance/{user_id}", timeout=10
        )
        self._expect_status(response, 200, "billing balance")
        return response.json()

    def upload_document(self) -> Dict[str, Any]:
        files = {
            "file": (
                "smoke.txt",
                BytesIO(b"Smoke test document"),
                "text/plain",
            )
        }
        data = {"document_type": self.document_type}
        response = self.session.post(
            f"{self.base_url}/documents/upload",
            files=files,
            data=data,
            timeout=30,
        )
        self._expect_status(response, 202, "upload")
        return response.json()

    def poll_job(self, job_id: uuid.UUID, attempts: int = 10, pause_seconds: float = 1.0) -> Dict[str, Any]:
        for attempt in range(1, attempts + 1):
            response = self.session.get(
                f"{self.base_url}/documents/jobs/{job_id}", timeout=10
            )
            self._expect_status(response, 200, "job status")
            body = response.json()
            status = body.get("status")
            if status in {"concluido", "falhou"}:
                return body
            time.sleep(pause_seconds)

        raise SmokeFailure(
            f"Job {job_id} did not finish after {attempts} attempts; last status: {body.get('status')}"
        )

    def chat(self, user_message: str) -> Dict[str, Any]:
        payload = {
            "agent_id": str(self.agent_id),
            "user_message": user_message,
            "conversation_history": [],
        }
        response = self.session.post(
            f"{self.base_url}/agent/chat", json=payload, timeout=30
        )
        self._expect_status(response, 200, "chat")
        return response.json()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test across core services.")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SMOKE_BASE_URL", DEFAULT_BASE_URL),
        help="API Gateway base URL (default: http://localhost:8080/api)",
    )
    parser.add_argument(
        "--agent-id",
        default=os.environ.get("SMOKE_AGENT_ID"),
        required=False,
        help="UUID of the agent to use for chat (required)",
    )
    parser.add_argument(
        "--document-type",
        default=os.environ.get("SMOKE_DOCUMENT_TYPE", DEFAULT_DOCUMENT_TYPE),
        help="Document type to use during upload.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.agent_id:
        raise SystemExit("--agent-id (or SMOKE_AGENT_ID) is required for the chat step.")

    client = SmokeClient(
        base_url=args.base_url,
        agent_id=uuid.UUID(args.agent_id),
        document_type=args.document_type,
    )

    unique_suffix = uuid.uuid4().hex[:8]
    email = f"smoke_{unique_suffix}@example.com"
    password = "SmokeTest!123"

    print(f"[register] Creating user {email}...")
    user_id = client.register(email, password)
    print(f"[register] ok -> user_id={user_id}")

    print("[login] Requesting token...")
    client.login(email, password)
    print("[login] ok")

    print("[profile] Fetching profile...")
    profile = client.profile()
    print(f"[profile] ok -> created_at={profile.get('created_at')}")

    print("[billing] Checking balance...")
    balance = client.billing_balance(user_id)
    print(f"[billing] ok -> balance={balance.get('balance')}")

    print("[upload] Sending document...")
    job = client.upload_document()
    job_id = uuid.UUID(job["id"])
    print(f"[upload] ok -> job_id={job_id}, status={job.get('status')}")

    print("[upload] Polling job status...")
    final_job = client.poll_job(job_id)
    print(
        f"[upload] completed -> status={final_job.get('status')}, "
        f"updated_at={final_job.get('updated_at')}"
    )

    print("[chat] Sending message to agent...")
    chat_response = client.chat("Teste rápido de fumo")
    print(f"[chat] ok -> assistant_message={chat_response.get('assistant_message')!r}")

    print("All smoke steps completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
