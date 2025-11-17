import importlib.metadata
import io
import os
import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient


# Reuse the dependency stubs from the existing document endpoint tests to avoid
# optional third-party dependencies during import time.
if "email_validator" not in sys.modules:
    email_module = types.ModuleType("email_validator")

    class EmailNotValidError(ValueError):
        pass

    def validate_email(address: str, *args, **kwargs):
        if "@" not in address:
            raise EmailNotValidError("Invalid email address")
        local, _, domain = address.partition("@")
        if not local or not domain:
            raise EmailNotValidError("Invalid email address")
        return types.SimpleNamespace(email=address, local_part=local, domain=domain)

    email_module.EmailNotValidError = EmailNotValidError
    email_module.validate_email = validate_email
    email_module.__all__ = ["validate_email", "EmailNotValidError"]
    sys.modules["email_validator"] = email_module

    original_distribution = importlib.metadata.distribution

    def distribution_stub(name: str):
        if name == "email-validator":
            class _Distribution:
                def __init__(self):
                    self.version = "2.0.0"
                    self._metadata = {"Name": "email-validator", "Version": self.version}

                @property
                def metadata(self):
                    return self._metadata

                def read_text(self, filename: str):
                    if filename == "METADATA":
                        return "Name: email-validator\nVersion: 2.0.0"
                    raise FileNotFoundError(filename)

            return _Distribution()
        return original_distribution(name)

    importlib.metadata.distribution = distribution_stub

if "minio" not in sys.modules:
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

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("MINIO_ENDPOINT", "localhost")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret")

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from services.document_service.application.domain.document_job import (  # noqa: E402
    DocumentType,
    ProcessingStatus,
)
from services.document_service.application.dto.dashboard_basic_metrics import (  # noqa: E402
    DashboardBasicMetricsResponse,
    DashboardCounter,
)
from services.document_service.application.dto.document_details import (  # noqa: E402
    DocumentDetailsResponse,
)
from services.document_service.application.exceptions import (  # noqa: E402
    JobAccessForbiddenError,
    JobNotFoundError,
)
from services.document_service.infrastructure.dependencies import (  # noqa: E402
    get_document_service,
)
from services.document_service.infrastructure.security import (  # noqa: E402
    get_current_user_id,
)
from services.document_service.infrastructure.web import api  # noqa: E402
from shared.models.base_models import DocumentJob as DocumentJobResponse  # noqa: E402


class FakeDocumentService:
    def __init__(
        self,
        *,
        job: DocumentJobResponse | None = None,
        jobs: list[DocumentJobResponse] | None = None,
        details: DocumentDetailsResponse | None = None,
        basic_metrics: DashboardBasicMetricsResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.job = job
        self.jobs = jobs or []
        self.details = details
        self.basic_metrics = basic_metrics
        self.error = error
        self.last_document_type: DocumentType | None = None
        self.received_payload: dict | None = None

    def start_document_processing(
        self, user_id: uuid.UUID, file_name: str, file_content, document_type: DocumentType
    ) -> DocumentJobResponse:
        if self.error:
            raise self.error
        self.last_document_type = document_type
        assert self.job is not None
        return self.job

    def get_job_status(self, job_id: uuid.UUID, user_id: uuid.UUID) -> DocumentJobResponse:
        if self.error:
            raise self.error
        assert self.job is not None
        return self.job

    def get_user_jobs(
        self, user_id: uuid.UUID, document_type: DocumentType | None = None
    ) -> list[DocumentJobResponse]:
        if self.error:
            raise self.error
        self.last_document_type = document_type
        return self.jobs

    def get_job_details(self, job_id: uuid.UUID, user_id: uuid.UUID) -> DocumentDetailsResponse:
        if self.error:
            raise self.error
        assert self.details is not None
        return self.details

    def update_extracted_data(
        self, job_id: uuid.UUID, user_id: uuid.UUID, payload: dict
    ) -> DocumentDetailsResponse:
        if self.error:
            raise self.error
        self.received_payload = payload
        assert self.details is not None
        return self.details

    def get_annual_revenue_summary(self, *args, **kwargs):  # pragma: no cover - unused stub
        raise NotImplementedError()

    def get_monthly_revenue_summary(self, *args, **kwargs):  # pragma: no cover - unused stub
        raise NotImplementedError()

    def get_basic_dashboard_metrics(self, *args, **kwargs):
        if self.error:
            raise self.error
        assert self.basic_metrics is not None
        return self.basic_metrics


def build_app(service: FakeDocumentService) -> TestClient:
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_document_service] = lambda: service
    app.dependency_overrides[get_current_user_id] = lambda: uuid.uuid4()
    return TestClient(app)


def _sample_job(user_id: uuid.UUID, job_id: uuid.UUID | None = None) -> DocumentJobResponse:
    job_id = job_id or uuid.uuid4()
    timestamp = datetime.now(timezone.utc)
    return DocumentJobResponse(
        id=job_id,
        user_id=user_id,
        file_path="/tmp/file.pdf",
        document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        status=ProcessingStatus.PROCESSING,
        extracted_data={},
        created_at=timestamp,
        updated_at=timestamp,
    )


def _sample_details(job_id: uuid.UUID) -> DocumentDetailsResponse:
    timestamp = datetime.now(timezone.utc)
    return DocumentDetailsResponse(
        id=job_id,
        document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        document_label="Nota Fiscal",
        status=ProcessingStatus.COMPLETED,
        source_group="nota_fiscal",
        source_group_label="Notas Fiscais",
        origem_legivel="Origem",
        valor=100.0,
        valor_formatado="R$ 100,00",
        data="2024-01-01",
        data_formatada="01/01/2024",
        natureza="receita",
        categoria="faturamento",
        resumo="Resumo",
        extras={},
        raw_extracted_data={"valor": 100.0},
        history=[],
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_upload_document_returns_job_metadata():
    user_id = uuid.uuid4()
    job = _sample_job(user_id=user_id)
    service = FakeDocumentService(job=job)
    upload = UploadFile(filename="report.pdf", file=io.BytesIO(b"hello"))

    result = api.upload_document(
        file=upload,
        document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        user_id=user_id,
        doc_service=service,
    )

    assert result.id == job.id
    assert service.last_document_type == DocumentType.NOTA_FISCAL_EMITIDA


def test_get_job_status_returns_latest_state():
    user_id = uuid.uuid4()
    job = _sample_job(user_id=user_id)
    client = build_app(FakeDocumentService(job=job))

    response = client.get(f"/documents/jobs/{job.id}")

    assert response.status_code == 200
    assert response.json()["status"] == ProcessingStatus.PROCESSING.value


def test_get_job_status_returns_403_when_forbidden():
    user_id = uuid.uuid4()
    job = _sample_job(user_id=user_id)
    client = build_app(
        FakeDocumentService(job=job, error=JobAccessForbiddenError("not allowed"))
    )

    response = client.get(f"/documents/jobs/{job.id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "not allowed"


def test_get_user_jobs_allows_filtering_by_document_type():
    user_id = uuid.uuid4()
    job = _sample_job(user_id=user_id)
    service = FakeDocumentService(job=job, jobs=[job])
    client = build_app(service)

    response = client.get(
        "/documents/jobs",
        params={"document_type": DocumentType.NOTA_FISCAL_EMITIDA.value},
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(job.id)
    assert service.last_document_type == DocumentType.NOTA_FISCAL_EMITIDA


def test_update_extracted_data_returns_details():
    user_id = uuid.uuid4()
    job = _sample_job(user_id=user_id)
    details = _sample_details(job.id)
    service = FakeDocumentService(job=job, details=details)
    client = build_app(service)

    response = client.patch(
        f"/documents/jobs/{job.id}/extracted-data",
        json={"data": {"valor": 123}},
    )

    assert response.status_code == 200
    assert response.json()["valor_formatado"] == "R$ 100,00"
    assert service.received_payload == {"valor": 123}


def test_update_extracted_data_returns_404_when_missing():
    user_id = uuid.uuid4()
    job = _sample_job(user_id=user_id)
    service = FakeDocumentService(job=job, error=JobNotFoundError("missing"))
    client = build_app(service)

    response = client.patch(
        f"/documents/jobs/{job.id}/extracted-data",
        json={"data": {}},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "missing"


def test_get_basic_dashboard_metrics_returns_counters():
    metrics = DashboardBasicMetricsResponse(
        reference_year=2024,
        reference_month=3,
        counters=[
            DashboardCounter(
                key="documents_total",
                title="Documentos",
                subtitle="Contagem de março/2024",
                value=12,
            ),
            DashboardCounter(
                key="processing_pending",
                title="Em processamento",
                subtitle="Ainda analisando",
                value=2,
            ),
        ],
    )
    client = build_app(FakeDocumentService(basic_metrics=metrics))

    response = client.get("/documents/dashboard/basic-metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["reference_year"] == 2024
    assert payload["reference_month"] == 3
    assert payload["counters"][0]["key"] == "documents_total"
    assert payload["counters"][0]["value"] == 12
