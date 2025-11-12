from abc import ABC, abstractmethod
from typing import IO, Dict, Any, List, Optional
import uuid

from shared.models.base_models import DocumentJob as DocumentJobResponse
from services.document_service.application.domain.document_job import DocumentType
from services.document_service.application.dto.document_details import (
    DocumentDetailsResponse,
)


class DocumentService(ABC):
    """Input port defining the document service use cases."""

    @abstractmethod
    def start_document_processing(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file_content: IO[bytes],
        document_type: DocumentType,
    ) -> DocumentJobResponse:
        """
        Use case for uploading a document and starting the processing workflow.
        """
        pass

    @abstractmethod
    def get_job_status(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> DocumentJobResponse:
        """
        Use case for checking the status of a specific processing job.
        """
        pass

    @abstractmethod
    def get_user_jobs(
        self, user_id: uuid.UUID, document_type: Optional[DocumentType] = None
    ) -> List[DocumentJobResponse]:
        """
        Use case for retrieving all jobs for a specific user.
        """
        pass

    @abstractmethod
    def get_job_details(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> DocumentDetailsResponse:
        """Return a normalized view of the extracted data for a job."""
        pass

    @abstractmethod
    def update_extracted_data(
        self, job_id: uuid.UUID, user_id: uuid.UUID, payload: Dict[str, Any]
    ) -> DocumentDetailsResponse:
        """Apply manual corrections to the extracted payload and version them."""
        pass
