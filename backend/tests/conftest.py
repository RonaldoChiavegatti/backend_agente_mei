import os
import sys
import types
import warnings
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1].parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Passlib still imports the deprecated stdlib ``crypt`` module when available.
# Filter the warning globally so it doesn't pollute the test output.
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"passlib\.utils.*",
)


def _install_minio_stub():
    if "minio" in sys.modules:
        return

    minio_module = types.ModuleType("minio")

    class Minio:
        def __init__(self, *args, **kwargs):
            self.bucket_objects = {}

        def bucket_exists(self, bucket_name: str) -> bool:
            return True

        def make_bucket(self, bucket_name: str) -> None:
            self.bucket_objects.setdefault(bucket_name, set())

        def put_object(self, bucket_name: str, object_name: str, data, length: int) -> None:
            bucket = self.bucket_objects.setdefault(bucket_name, set())
            bucket.add(object_name)

    error_module = types.ModuleType("minio.error")

    class S3Error(RuntimeError):
        pass

    error_module.S3Error = S3Error
    minio_module.Minio = Minio
    minio_module.error = error_module

    sys.modules["minio"] = minio_module
    sys.modules["minio.error"] = error_module


def _install_redis_stub():
    class _FakeRedis:
        def __init__(self, *args, **kwargs):
            self._queues: dict[str, list[str]] = {}

        def rpush(self, queue_name: str, message: str) -> None:
            self._queues.setdefault(queue_name, []).append(message)

        def blpop(self, queue_name: str, timeout: int | None = None):
            queue = self._queues.get(queue_name, [])
            if not queue:
                return None
            return queue_name, queue.pop(0)

    redis_module = types.ModuleType("redis")
    redis_module._fake_instance = _FakeRedis()
    redis_module.from_url = lambda *args, **kwargs: redis_module._fake_instance
    redis_module.exceptions = types.SimpleNamespace(ConnectionError=ConnectionError)

    sys.modules["redis"] = redis_module


def pytest_configure():
    os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
    os.environ.setdefault("MINIO_ACCESS_KEY", "test")
    os.environ.setdefault("MINIO_SECRET_KEY", "test")
    os.environ.setdefault("MINIO_BUCKET_NAME", "documents")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("USE_STUB_LLM", "true")

    _install_minio_stub()
    _install_redis_stub()

