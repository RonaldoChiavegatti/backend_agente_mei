import pathlib
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import IO, Dict, Any, List, Optional

from services.document_service.application.domain.document_job import (
    DocumentJob,
    DocumentType,
    ExtractedDataAuthor,
    ProcessingStatus,
)
from services.document_service.application.exceptions import (
    JobAccessForbiddenError,
    JobNotFoundError,
)
from services.document_service.application.ports.input.document_service import (
    DocumentService,
)
from services.document_service.application.ports.output.document_job_repository import (
    DocumentJobRepository,
)
from services.document_service.application.ports.output.file_storage import FileStorage
from services.document_service.application.ports.output.message_queue import (
    MessageQueue,
)
from services.document_service.application.services.document_details_formatter import (
    build_document_details,
)
from shared.models.base_models import DocumentJob as DocumentJobResponse
from services.document_service.application.dto.document_details import (
    DocumentDetailsResponse,
)
from services.document_service.application.dto.annual_revenue_summary import (
    AnnualRevenueSummaryResponse,
    AnnualRevenueSourceBreakdown,
)


class DocumentServiceImpl(DocumentService):
    """
    Concrete implementation of the DocumentService input port.
    """

    _ANNUAL_LIMIT = 81000.0
    _BREAKDOWN_LABELS: Dict[str, str] = {
        DocumentType.NOTA_FISCAL_EMITIDA.value: "Notas fiscais emitidas",
        DocumentType.INFORME_RENDIMENTOS.value: "Informes de rendimentos (receita operacional MEI)",
        "LUCRO_TRIBUTAVEL_DASN": "Lucro tributável informado na DASN-SIMEI",
    }
    _OPERATIONAL_FLAG_FRAGMENTS = (
        "receita_operacional",
        "operacional_mei",
        "mei_operacional",
    )

    def __init__(
        self,
        job_repository: DocumentJobRepository,
        file_storage: FileStorage,
        message_queue: MessageQueue,
        ocr_queue_name: str = "ocr_jobs",
    ):
        self.job_repository = job_repository
        self.file_storage = file_storage
        self.message_queue = message_queue
        self.ocr_queue_name = ocr_queue_name

    def start_document_processing(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file_content: IO[bytes],
        document_type: DocumentType,
    ) -> DocumentJobResponse:
        """
        Handles the business logic for starting a document processing job.
        1. Validates the file metadata (name and extension).
        2. Creates a unique path for the file.
        3. Uploads the file to storage.
        4. Creates a new DocumentJob domain entity with the provided document type.
        5. Saves the job to the repository.
        6. Publishes a message to the OCR queue.
        7. Returns the created job as a response DTO.
        """
        if not file_name:
            raise ValueError("Arquivo sem nome não pode ser processado.")

        file_extension = pathlib.Path(file_name).suffix.lower()
        allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg"}
        if file_extension not in allowed_extensions:
            raise ValueError("Formato de arquivo não suportado. Use PDF, JPG ou PNG.")

        unique_file_name = f"{uuid.uuid4()}{file_extension}"
        storage_path = f"documents/{user_id}/{unique_file_name}"

        # 1. Upload file
        self.file_storage.upload(file_obj=file_content, destination_path=storage_path)

        # 2. Create and save job
        job = DocumentJob(
            user_id=user_id,
            file_path=storage_path,
            document_type=document_type,
            status=ProcessingStatus.PROCESSING,
        )
        saved_job = self.job_repository.save(job)

        # 3. Publish message
        self.message_queue.publish_message(
            queue_name=self.ocr_queue_name,
            message={
                "job_id": str(saved_job.id),
                "file_path": saved_job.file_path,
                "document_type": saved_job.document_type.value,
            },
        )

        return DocumentJobResponse.model_validate(saved_job, from_attributes=True)

    def get_job_status(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> DocumentJobResponse:
        job = self.job_repository.get_by_id(job_id)
        if not job:
            raise JobNotFoundError(f"Job with ID {job_id} not found.")

        if job.user_id != user_id:
            raise JobAccessForbiddenError("User does not have access to this job.")

        return DocumentJobResponse.model_validate(job, from_attributes=True)

    def get_user_jobs(
        self, user_id: uuid.UUID, document_type: Optional[DocumentType] = None
    ) -> List[DocumentJobResponse]:
        jobs = self.job_repository.get_by_user_id(
            user_id=user_id, document_type=document_type
        )
        return [
            DocumentJobResponse.model_validate(job, from_attributes=True)
            for job in jobs
        ]

    def get_job_details(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> DocumentDetailsResponse:
        job = self.job_repository.get_by_id(job_id)
        if not job:
            raise JobNotFoundError(f"Job with ID {job_id} not found.")

        if job.user_id != user_id:
            raise JobAccessForbiddenError("User does not have access to this job.")

        return build_document_details(job)

    def update_extracted_data(
        self, job_id: uuid.UUID, user_id: uuid.UUID, payload: Dict[str, Any]
    ) -> DocumentDetailsResponse:
        job = self.job_repository.get_by_id(job_id)
        if not job:
            raise JobNotFoundError(f"Job with ID {job_id} not found.")

        if job.user_id != user_id:
            raise JobAccessForbiddenError("User does not have access to this job.")

        job.record_version(payload, author_type=ExtractedDataAuthor.USER, author_id=user_id)
        saved_job = self.job_repository.save(job)
        return build_document_details(saved_job)

    def get_annual_revenue_summary(
        self, user_id: uuid.UUID, year: Optional[int] = None
    ) -> AnnualRevenueSummaryResponse:
        target_year = year or datetime.utcnow().year
        jobs = self.job_repository.get_by_user_id(user_id=user_id)

        breakdown_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"label": "", "total": 0.0, "documents": []}
        )
        total_revenue = 0.0
        considered_labels: set[str] = set()

        for job in jobs:
            if job.status != ProcessingStatus.COMPLETED:
                continue

            details = build_document_details(job)
            document_year = self._resolve_year(details, job)
            if document_year is not None and document_year != target_year:
                continue

            if job.document_type == DocumentType.NOTA_FISCAL_EMITIDA:
                amount = details.valor
                if amount is None:
                    continue
                total_revenue += amount
                self._register_breakdown(
                    breakdown_data,
                    DocumentType.NOTA_FISCAL_EMITIDA.value,
                    amount,
                    job.id,
                )
                considered_labels.add(
                    self._BREAKDOWN_LABELS[DocumentType.NOTA_FISCAL_EMITIDA.value]
                )
                continue

            if job.document_type == DocumentType.INFORME_RENDIMENTOS:
                if not self._is_operational_revenue(job, details):
                    continue
                amount = details.valor
                if amount is None:
                    continue
                total_revenue += amount
                self._register_breakdown(
                    breakdown_data,
                    DocumentType.INFORME_RENDIMENTOS.value,
                    amount,
                    job.id,
                )
                considered_labels.add(
                    self._BREAKDOWN_LABELS[DocumentType.INFORME_RENDIMENTOS.value]
                )
                continue

            if job.document_type == DocumentType.DASN_SIMEI:
                amount = self._extract_lucro_tributavel(details, job)
                if amount is None:
                    continue
                total_revenue += amount
                self._register_breakdown(
                    breakdown_data,
                    "LUCRO_TRIBUTAVEL_DASN",
                    amount,
                    job.id,
                )
                considered_labels.add(self._BREAKDOWN_LABELS["LUCRO_TRIBUTAVEL_DASN"])

        breakdown_models: Dict[str, AnnualRevenueSourceBreakdown] = {}
        for key, payload in breakdown_data.items():
            if payload["total"] <= 0:
                continue
            label = payload["label"] or self._BREAKDOWN_LABELS.get(key, key)
            documents = payload["documents"]
            breakdown_models[key] = AnnualRevenueSourceBreakdown(
                document_type=key,
                label=label,
                total=round(payload["total"], 2),
                total_formatado=self._format_currency(payload["total"]),
                documentos=documents,
                quantidade_documentos=len(documents),
            )

        total_revenue = round(total_revenue, 2)
        total_formatted = self._format_currency(total_revenue)
        limit_formatted = self._format_currency(self._ANNUAL_LIMIT)
        highlight = f"Faturamento Anual: {total_formatted} / {limit_formatted}"

        notes = [
            (
                "Documentos de despesas, documentos de identificação, comprovantes de "
                "endereço e recibos de IR anteriores não entram no cálculo de faturamento, "
                "mas podem ser usados para outras análises."
            )
        ]

        return AnnualRevenueSummaryResponse(
            ano=target_year,
            faturamento_total=total_revenue,
            faturamento_total_formatado=total_formatted,
            limite_anual=self._ANNUAL_LIMIT,
            limite_anual_formatado=limit_formatted,
            destaque=highlight,
            detalhamento=breakdown_models,
            observacoes=notes,
            documentos_considerados=sorted(considered_labels),
        )

    def _register_breakdown(
        self,
        registry: Dict[str, Dict[str, Any]],
        key: str,
        amount: float,
        document_id: uuid.UUID,
    ) -> None:
        bucket = registry[key]
        if not bucket["label"]:
            bucket["label"] = self._BREAKDOWN_LABELS.get(key, key)
        bucket["total"] += amount
        bucket.setdefault("documents", []).append(document_id)

    def _resolve_year(
        self, details: DocumentDetailsResponse, job: DocumentJob
    ) -> Optional[int]:
        if details.data:
            try:
                return datetime.fromisoformat(details.data).year
            except ValueError:
                pass

        extras = details.extras or {}
        for key in ("ano_calendario", "ano-calendario", "ano_calendario_mei"):
            entry = extras.get(key)
            if isinstance(entry, dict):
                for field in ("valor", "valor_formatado"):
                    year = self._extract_year_from_text(entry.get(field))
                    if year is not None:
                        return year

        if details.raw_extracted_data:
            year = self._extract_year_from_text(details.raw_extracted_data)
            if year is not None:
                return year

        if job.created_at:
            return job.created_at.year

        return None

    def _extract_lucro_tributavel(
        self, details: DocumentDetailsResponse, job: DocumentJob
    ) -> Optional[float]:
        extras = details.extras or {}
        for key in ("lucro_tributavel", "lucro_tributavel_mei"):
            entry = extras.get(key)
            if isinstance(entry, dict):
                for field in ("valor", "valor_formatado"):
                    amount = self._parse_float(entry.get(field))
                    if amount is not None:
                        return amount

        payload = details.raw_extracted_data or job.extracted_data
        if payload:
            amount = self._extract_nested_amount(payload, ("lucro_tributavel", "lucro"))
            if amount is not None:
                return amount
        return None

    def _extract_nested_amount(
        self, payload: Any, keywords: tuple[str, ...]
    ) -> Optional[float]:
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = str(key).lower().replace(" ", "_")
                if any(fragment in normalized_key for fragment in keywords):
                    amount = self._parse_float(value)
                    if amount is not None:
                        return amount
                amount = self._extract_nested_amount(value, keywords)
                if amount is not None:
                    return amount
        elif isinstance(payload, (list, tuple, set)):
            for item in payload:
                amount = self._extract_nested_amount(item, keywords)
                if amount is not None:
                    return amount
        return None

    def _is_operational_revenue(
        self, job: DocumentJob, details: DocumentDetailsResponse
    ) -> bool:
        categoria = details.categoria or ""
        if "operacional" in categoria.lower():
            return True

        payload = job.extracted_data
        if not payload:
            return False

        return self._payload_has_operational_flag(payload)

    def _payload_has_operational_flag(self, payload: Any) -> bool:
        if isinstance(payload, dict):
            for key, value in payload.items():
                normalized_key = str(key).lower().replace(" ", "_")
                if any(fragment in normalized_key for fragment in self._OPERATIONAL_FLAG_FRAGMENTS):
                    if self._is_truthy(value) or (
                        isinstance(value, str)
                        and "operacional" in value.lower()
                        and "receita" in value.lower()
                    ):
                        return True
                if self._payload_has_operational_flag(value):
                    return True
            return False

        if isinstance(payload, (list, tuple, set)):
            for item in payload:
                if self._payload_has_operational_flag(item):
                    return True
        return False

    @staticmethod
    def _is_truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"true", "1", "sim", "yes", "y", "s"}
        return False

    def _extract_year_from_text(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, (float,)):
            return int(value)
        if isinstance(value, str):
            match = re.search(r"(19|20)\d{2}", value)
            if match:
                try:
                    return int(match.group(0))
                except ValueError:
                    return None
        if isinstance(value, dict):
            for nested in value.values():
                year = self._extract_year_from_text(nested)
                if year is not None:
                    return year
        if isinstance(value, (list, tuple, set)):
            for item in value:
                year = self._extract_year_from_text(item)
                if year is not None:
                    return year
        return None

    @staticmethod
    def _parse_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            cleaned = cleaned.replace("R$", "").replace(" ", "")
            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif cleaned.count(",") == 1 and cleaned.count(".") == 0:
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif cleaned.count(".") > 1 and "," not in cleaned:
                parts = cleaned.split(".")
                cleaned = "".join(parts[:-1]) + "." + parts[-1]
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    @staticmethod
    def _format_currency(value: float) -> str:
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
