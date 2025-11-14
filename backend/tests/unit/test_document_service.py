import unittest
from unittest.mock import MagicMock
import uuid
from datetime import datetime
from io import BytesIO

import importlib.metadata
import sys
import types
from pathlib import Path


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

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.document_service.application.services.document_service_impl import (
    DocumentServiceImpl,
)
from services.document_service.application.domain.document_job import (
    DocumentJob,
    DocumentType,
    ExtractedDataAuthor,
    ProcessingStatus,
)
from services.document_service.application.exceptions import (
    JobNotFoundError,
    JobAccessForbiddenError,
)
from services.document_service.application.ports.output.document_job_repository import (
    DocumentJobRepository,
)
from services.document_service.application.ports.output.file_storage import FileStorage
from services.document_service.application.ports.output.message_queue import (
    MessageQueue,
)
from services.document_service.application.dto.document_details import (
    DocumentDetailsResponse,
)
from services.document_service.application.dto.annual_revenue_summary import (
    AnnualRevenueSummaryResponse,
)
from services.document_service.application.dto.monthly_revenue_summary import (
    MonthlyRevenueSummaryResponse,
)


class TestDocumentService(unittest.TestCase):
    def setUp(self):
        self.mock_job_repo = MagicMock(spec=DocumentJobRepository)
        self.mock_file_storage = MagicMock(spec=FileStorage)
        self.mock_message_queue = MagicMock(spec=MessageQueue)

        self.doc_service = DocumentServiceImpl(
            job_repository=self.mock_job_repo,
            file_storage=self.mock_file_storage,
            message_queue=self.mock_message_queue,
            ocr_queue_name="test_ocr_queue",
        )

        self.user_id = uuid.uuid4()
        self.job_id = uuid.uuid4()
        self.test_job = DocumentJob(
            id=self.job_id,
            user_id=self.user_id,
            file_path=f"documents/{self.user_id}/test.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        )

    def test_start_document_processing_success(self):
        # Arrange
        file_content = BytesIO(b"dummy file content")
        file_name = "test.pdf"

        self.mock_file_storage.upload.return_value = (
            f"documents/{self.user_id}/some-uuid.pdf"
        )
        self.mock_job_repo.save.return_value = self.test_job

        # Act
        result = self.doc_service.start_document_processing(
            user_id=self.user_id,
            file_name=file_name,
            file_content=file_content,
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        )

        # Assert
        self.mock_file_storage.upload.assert_called_once()
        self.mock_job_repo.save.assert_called_once()
        self.mock_message_queue.publish_message.assert_called_once_with(
            queue_name="test_ocr_queue",
            message={
                "job_id": str(self.job_id),
                "file_path": self.test_job.file_path,
                "document_type": self.test_job.document_type.value,
            },
        )
        self.assertEqual(result.id, self.job_id)

    def test_get_job_status_success(self):
        # Arrange
        self.mock_job_repo.get_by_id.return_value = self.test_job

        # Act
        result = self.doc_service.get_job_status(
            job_id=self.job_id, user_id=self.user_id
        )

        # Assert
        self.mock_job_repo.get_by_id.assert_called_once_with(self.job_id)
        self.assertEqual(result.id, self.job_id)

    def test_get_job_status_not_found(self):
        # Arrange
        self.mock_job_repo.get_by_id.return_value = None

        # Act & Assert
        with self.assertRaises(JobNotFoundError):
            self.doc_service.get_job_status(job_id=self.job_id, user_id=self.user_id)

    def test_get_job_status_forbidden(self):
        # Arrange
        other_user_id = uuid.uuid4()
        self.mock_job_repo.get_by_id.return_value = self.test_job

        # Act & Assert
        with self.assertRaises(JobAccessForbiddenError):
            self.doc_service.get_job_status(job_id=self.job_id, user_id=other_user_id)

    def test_update_extracted_data_success(self):
        job = DocumentJob(
            id=self.job_id,
            user_id=self.user_id,
            file_path=f"documents/{self.user_id}/test.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data={"valor": 100.0},
        )
        self.mock_job_repo.get_by_id.return_value = job
        self.mock_job_repo.save.return_value = job

        result = self.doc_service.update_extracted_data(
            job_id=self.job_id,
            user_id=self.user_id,
            payload={"valor": 150.0},
        )

        self.mock_job_repo.save.assert_called_once()
        self.assertEqual(len(job.extracted_data_history), 1)
        self.assertEqual(job.extracted_data_history[0].author_type, ExtractedDataAuthor.USER)
        self.assertEqual(result.history[0].changes[0].previous_value, 100.0)
        self.assertEqual(result.history[0].changes[0].current_value, 150.0)

    def test_update_extracted_data_not_found(self):
        self.mock_job_repo.get_by_id.return_value = None

        with self.assertRaises(JobNotFoundError):
            self.doc_service.update_extracted_data(
                job_id=self.job_id, user_id=self.user_id, payload={}
            )

    def test_update_extracted_data_forbidden(self):
        other_user_id = uuid.uuid4()
        self.mock_job_repo.get_by_id.return_value = self.test_job

        with self.assertRaises(JobAccessForbiddenError):
            self.doc_service.update_extracted_data(
                job_id=self.job_id, user_id=other_user_id, payload={}
            )

    def test_get_user_jobs(self):
        # Arrange
        self.mock_job_repo.get_by_user_id.return_value = [self.test_job, self.test_job]

        # Act
        result = self.doc_service.get_user_jobs(user_id=self.user_id)

        # Assert
        self.mock_job_repo.get_by_user_id.assert_called_once_with(
            user_id=self.user_id, document_type=None
        )
        self.assertEqual(len(result), 2)

    def test_get_user_jobs_with_filter(self):
        # Arrange
        self.mock_job_repo.get_by_user_id.return_value = [self.test_job]

        # Act
        result = self.doc_service.get_user_jobs(
            user_id=self.user_id,
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        )

        # Assert
        self.mock_job_repo.get_by_user_id.assert_called_once_with(
            user_id=self.user_id,
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
        )
        self.assertEqual(len(result), 1)

    def test_start_document_processing_invalid_extension(self):
        file_content = BytesIO(b"dummy file content")
        file_name = "test.txt"

        with self.assertRaises(ValueError):
            self.doc_service.start_document_processing(
                user_id=self.user_id,
                file_name=file_name,
                file_content=file_content,
                document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            )

    def test_get_job_details_success(self):
        extracted_data = {
            "valor": 1500.0,
            "data": "2025-03-10",
            "natureza": "receita",
            "categoria": "faturamento MEI",
        }
        job_with_data = DocumentJob(
            id=self.job_id,
            user_id=self.user_id,
            file_path=f"documents/{self.user_id}/nota.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data=extracted_data,
        )

        self.mock_job_repo.get_by_id.return_value = job_with_data

        details = self.doc_service.get_job_details(
            job_id=self.job_id, user_id=self.user_id
        )

        self.assertIsInstance(details, DocumentDetailsResponse)
        self.assertEqual(details.valor, 1500.0)
        self.assertEqual(details.valor_formatado, "R$ 1.500,00")
        self.assertEqual(details.data, "2025-03-10")
        self.assertEqual(details.data_formatada, "10/03/2025")
        self.assertEqual(details.natureza, "receita")
        self.assertEqual(details.categoria, "faturamento MEI")
        self.assertEqual(
            details.resumo,
            "Nota Fiscal emitida em 10/03/2025 – Receita: R$ 1.500,00",
        )
        self.assertEqual(details.source_group, "nota_fiscal")
        self.assertEqual(details.source_group_label, "Notas Fiscais")

    def test_get_job_details_not_found(self):
        self.mock_job_repo.get_by_id.return_value = None

        with self.assertRaises(JobNotFoundError):
            self.doc_service.get_job_details(
                job_id=self.job_id, user_id=self.user_id
            )

    def test_get_job_details_forbidden(self):
        other_user_id = uuid.uuid4()
        self.mock_job_repo.get_by_id.return_value = self.test_job

        with self.assertRaises(JobAccessForbiddenError):
            self.doc_service.get_job_details(
                job_id=self.job_id, user_id=other_user_id
            )

    def test_get_job_details_dasn_summary(self):
        extracted_data = {
            "lucro_isento": "12500,00",
            "lucro_tributavel": "3500.5",
            "data": "2024-02-15",
        }
        dasn_job = DocumentJob(
            id=self.job_id,
            user_id=self.user_id,
            file_path=f"documents/{self.user_id}/dasn.pdf",
            document_type=DocumentType.DASN_SIMEI,
            status=ProcessingStatus.COMPLETED,
            extracted_data=extracted_data,
        )
        self.mock_job_repo.get_by_id.return_value = dasn_job

        details = self.doc_service.get_job_details(
            job_id=self.job_id, user_id=self.user_id
        )

        self.assertEqual(details.document_label, "DASN-SIMEI")
        self.assertIn("Lucro isento", details.resumo)
        self.assertIn("Lucro tributável", details.resumo)
        self.assertIn("lucro_isento", details.extras)
        self.assertEqual(
            details.extras["lucro_isento"]["valor_formatado"], "R$ 12.500,00"
        )

    def test_get_annual_revenue_summary(self):
        nf_job = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/nf.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data={"valor": 10000.0, "data": "2024-01-05"},
            created_at=datetime(2024, 1, 6),
        )

        informe_operacional = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/informe.pdf",
            document_type=DocumentType.INFORME_RENDIMENTOS,
            status=ProcessingStatus.COMPLETED,
            extracted_data={
                "valor": "25.750,30",
                "receita_operacional_mei": True,
                "data": "2024-02-10",
            },
            created_at=datetime(2024, 2, 15),
        )

        informe_nao_operacional = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/informe2.pdf",
            document_type=DocumentType.INFORME_RENDIMENTOS,
            status=ProcessingStatus.COMPLETED,
            extracted_data={
                "valor": "9.999,99",
                "receita_operacional_mei": False,
                "data": "2024-03-10",
            },
            created_at=datetime(2024, 3, 11),
        )

        dasn_job = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/dasn.pdf",
            document_type=DocumentType.DASN_SIMEI,
            status=ProcessingStatus.COMPLETED,
            extracted_data={
                "lucro_tributavel": "3.500,50",
                "ano_calendario": "2024",
            },
            created_at=datetime(2024, 4, 5),
        )

        old_job = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/nf_old.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data={"valor": 8000.0, "data": "2023-12-30"},
            created_at=datetime(2023, 12, 31),
        )

        self.mock_job_repo.get_by_user_id.return_value = [
            nf_job,
            informe_operacional,
            informe_nao_operacional,
            dasn_job,
            old_job,
        ]

        summary = self.doc_service.get_annual_revenue_summary(
            user_id=self.user_id, year=2024
        )

        self.assertIsInstance(summary, AnnualRevenueSummaryResponse)
        expected_total = 10000.0 + 25750.3 + 3500.5
        self.assertAlmostEqual(summary.faturamento_total, round(expected_total, 2))
        self.assertIn("Faturamento Anual", summary.destaque)
        self.assertIn("NOTA_FISCAL_EMITIDA", summary.detalhamento)
        self.assertIn("INFORME_RENDIMENTOS", summary.detalhamento)
        self.assertIn("LUCRO_TRIBUTAVEL_DASN", summary.detalhamento)
        informe_breakdown = summary.detalhamento["INFORME_RENDIMENTOS"]
        self.assertEqual(informe_breakdown.quantidade_documentos, 1)
        self.assertIn(informe_operacional.id, informe_breakdown.documentos)
        self.assertIn(
            self.doc_service._BREAKDOWN_LABELS["LUCRO_TRIBUTAVEL_DASN"],
            summary.documentos_considerados,
        )
        self.assertTrue(summary.observacoes)
        self.assertIsNone(summary.alerta_limite)

    def test_get_annual_revenue_summary_with_warning_alert(self):
        near_limit_job = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/nf.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data={"valor": 75000.0, "data": "2024-05-01"},
            created_at=datetime(2024, 5, 2),
        )

        self.mock_job_repo.get_by_user_id.return_value = [near_limit_job]

        summary = self.doc_service.get_annual_revenue_summary(
            user_id=self.user_id, year=2024
        )

        self.assertIsNotNone(summary.alerta_limite)
        assert summary.alerta_limite is not None
        self.assertEqual(summary.alerta_limite.nivel, "atencao")
        self.assertIn("90%", summary.alerta_limite.mensagem)
        self.assertGreaterEqual(summary.alerta_limite.percentual_utilizado, 90.0)
        self.assertLess(summary.alerta_limite.percentual_utilizado, 100.0)

    def test_get_annual_revenue_summary_with_critical_alert(self):
        above_limit_job = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/nf.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data={"valor": 82000.0, "data": "2024-06-01"},
            created_at=datetime(2024, 6, 2),
        )

        self.mock_job_repo.get_by_user_id.return_value = [above_limit_job]

        summary = self.doc_service.get_annual_revenue_summary(
            user_id=self.user_id, year=2024
        )

        self.assertIsNotNone(summary.alerta_limite)
        assert summary.alerta_limite is not None
        self.assertEqual(summary.alerta_limite.nivel, "critico")
        self.assertIn("ultrapassado", summary.alerta_limite.mensagem)
        self.assertGreaterEqual(summary.alerta_limite.percentual_utilizado, 100.0)
        self.assertTrue(summary.observacoes)

    def test_get_monthly_revenue_summary(self):
        nf_january = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/nf_jan.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data={"valor": 2000.0, "data": "2024-01-10"},
            created_at=datetime(2024, 1, 15),
        )

        informe_january = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/informe_jan.pdf",
            document_type=DocumentType.INFORME_RENDIMENTOS,
            status=ProcessingStatus.COMPLETED,
            extracted_data={
                "valor": "3.500,00",
                "receita_operacional_mei": True,
                "data": "2024-01-20",
            },
            created_at=datetime(2024, 1, 25),
        )

        dasn_january = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/dasn_jan.pdf",
            document_type=DocumentType.DASN_SIMEI,
            status=ProcessingStatus.COMPLETED,
            extracted_data={
                "lucro_tributavel": "1.250,00",
                "competencia": "01/2024",
            },
            created_at=datetime(2024, 1, 30),
        )

        nf_february = DocumentJob(
            id=uuid.uuid4(),
            user_id=self.user_id,
            file_path="/tmp/nf_fev.pdf",
            document_type=DocumentType.NOTA_FISCAL_EMITIDA,
            status=ProcessingStatus.COMPLETED,
            extracted_data={"valor": 1000.0, "data": "2024-02-05"},
            created_at=datetime(2024, 2, 10),
        )

        self.mock_job_repo.get_by_user_id.return_value = [
            nf_january,
            informe_january,
            dasn_january,
            nf_february,
        ]

        summary = self.doc_service.get_monthly_revenue_summary(
            user_id=self.user_id, year=2024, month=1
        )

        self.assertIsInstance(summary, MonthlyRevenueSummaryResponse)
        expected_total = 2000.0 + 3500.0 + 1250.0
        self.assertAlmostEqual(summary.faturamento_total, round(expected_total, 2))
        self.assertEqual(summary.mes, 1)
        self.assertEqual(summary.ano, 2024)
        self.assertEqual(
            summary.destaque,
            "Faturamento Mensal (01/2024): R$ 6.750,00 / R$ 6.750,00",
        )
        self.assertIn("NOTA_FISCAL_EMITIDA", summary.detalhamento)
        self.assertIn("INFORME_RENDIMENTOS", summary.detalhamento)
        self.assertIn("LUCRO_TRIBUTAVEL_DASN", summary.detalhamento)
        self.assertTrue(summary.observacoes)
        self.assertIn(
            "Notas fiscais emitidas", summary.documentos_considerados
        )


if __name__ == "__main__":
    unittest.main()
