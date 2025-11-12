import pathlib
import uuid
from typing import IO, List, Optional

from services.document_service.application.domain.document_job import (
    DocumentJob,
    DocumentType,
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


class DocumentServiceImpl(DocumentService):
    """
    Concrete implementation of the DocumentService input port.
    """

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
