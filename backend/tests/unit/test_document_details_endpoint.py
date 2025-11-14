import importlib.metadata
import os
import sys
import types
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException


def _install_dependency_stubs():
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
            return types.SimpleNamespace(
                email=address, local_part=local, domain=domain
            )

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
                        self._metadata = {
                            "Name": "email-validator",
                            "Version": self.version,
                        }

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


_install_dependency_stubs()

os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("MINIO_ENDPOINT", "localhost")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret")

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.document_service.application.dto.document_details import (  # noqa: E402
    DocumentDetailsResponse,
)
from services.document_service.application.dto.annual_revenue_summary import (  # noqa: E402
    AnnualRevenueSummaryResponse,
    AnnualRevenueSourceBreakdown,
)
from services.document_service.application.domain.document_job import (  # noqa: E402
    DocumentType,
    ProcessingStatus,
)
from services.document_service.application.exceptions import (  # noqa: E402
    JobAccessForbiddenError,
    JobNotFoundError,
)
from services.document_service.infrastructure.web import api  # noqa: E402


class FakeDocumentService:
    def __init__(
        self,
        details: DocumentDetailsResponse | None = None,
        annual_summary: AnnualRevenueSummaryResponse | None = None,
        error: Exception | None = None,
    ):
        self.details = details
        self.annual_summary = annual_summary
        self.error = error

    def start_document_processing(self, *args, **kwargs):  # pragma: no cover - helper stub
        raise NotImplementedError()

    def get_job_status(self, *args, **kwargs):  # pragma: no cover - helper stub
        raise NotImplementedError()

    def get_user_jobs(self, *args, **kwargs):  # pragma: no cover - helper stub
        raise NotImplementedError()

    def get_job_details(self, job_id: uuid.UUID, user_id: uuid.UUID) -> DocumentDetailsResponse:
        if self.error:
            raise self.error
        assert self.details is not None
        return self.details

    def get_annual_revenue_summary(
        self, user_id: uuid.UUID, year: int | None = None
    ) -> AnnualRevenueSummaryResponse:
        if self.error:
            raise self.error
        assert self.annual_summary is not None
        return self.annual_summary


class TestDocumentDetailsEndpoint(unittest.TestCase):
    def setUp(self):
        self.user_id = uuid.uuid4()
        self.job_id = uuid.uuid4()
        timestamp = datetime.now(timezone.utc)
        self.sample_details = DocumentDetailsResponse(
            id=self.job_id,
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            document_label="Nota Fiscal emitida",
            status=ProcessingStatus.COMPLETED,
            source_group="nota_fiscal",
            source_group_label="Notas Fiscais",
            origem_legivel="Informações extraídas de Notas Fiscais",
            valor=1500.0,
            valor_formatado="R$ 1.500,00",
            data="2025-03-10",
            data_formatada="10/03/2025",
            natureza="receita",
            categoria="faturamento MEI",
            resumo="Nota Fiscal emitida em 10/03/2025 – Receita: R$ 1.500,00",
            extras={},
            raw_extracted_data={"valor": 1500.0},
            created_at=timestamp,
            updated_at=timestamp,
        )

    def test_returns_document_details_payload(self):
        service = FakeDocumentService(details=self.sample_details)

        result = api.get_job_details_endpoint(
            job_id=self.job_id,
            user_id=self.user_id,
            doc_service=service,
        )

        self.assertEqual(result.document_type, DocumentType.NOTA_FISCAL_EMITIDA)
        self.assertEqual(result.valor_formatado, "R$ 1.500,00")
        self.assertEqual(result.origem_legivel, "Informações extraídas de Notas Fiscais")

    def test_raises_http_404_when_job_missing(self):
        service = FakeDocumentService(error=JobNotFoundError("missing"))

        with self.assertRaises(HTTPException) as ctx:
            api.get_job_details_endpoint(
                job_id=self.job_id,
                user_id=self.user_id,
                doc_service=service,
            )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "missing")

    def test_raises_http_403_when_forbidden(self):
        service = FakeDocumentService(error=JobAccessForbiddenError("nope"))

        with self.assertRaises(HTTPException) as ctx:
            api.get_job_details_endpoint(
                job_id=self.job_id,
                user_id=self.user_id,
                doc_service=service,
            )

        self.assertEqual(ctx.exception.status_code, 403)

    def test_get_annual_revenue_summary_endpoint(self):
        breakdown = AnnualRevenueSourceBreakdown(
            document_type="NOTA_FISCAL_EMITIDA",
            label="Notas fiscais emitidas",
            total=15000.0,
            total_formatado="R$ 15.000,00",
            documentos=[uuid.uuid4()],
            quantidade_documentos=1,
        )
        summary = AnnualRevenueSummaryResponse(
            ano=2024,
            faturamento_total=15000.0,
            faturamento_total_formatado="R$ 15.000,00",
            limite_anual=81000.0,
            limite_anual_formatado="R$ 81.000,00",
            destaque="Faturamento Anual: R$ 15.000,00 / R$ 81.000,00",
            detalhamento={"NOTA_FISCAL_EMITIDA": breakdown},
            observacoes=["note"],
            documentos_considerados=["Notas fiscais emitidas"],
        )

        service = FakeDocumentService(annual_summary=summary)

        result = api.get_annual_revenue_summary_endpoint(
            year=2024,
            user_id=self.user_id,
            doc_service=service,
        )

        self.assertEqual(result.ano, 2024)
        self.assertIn("Faturamento Anual", result.destaque)
        self.assertIn("NOTA_FISCAL_EMITIDA", result.detalhamento)

    def test_get_annual_revenue_summary_endpoint_handles_error(self):
        service = FakeDocumentService(error=RuntimeError("boom"))

        with self.assertRaises(HTTPException) as ctx:
            api.get_annual_revenue_summary_endpoint(
                year=None,
                user_id=self.user_id,
                doc_service=service,
            )

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(ctx.exception.detail, "boom")


if __name__ == "__main__":
    unittest.main()
