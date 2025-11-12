from abc import ABC, abstractmethod
from typing import Optional, List
import uuid

from services.document_service.application.domain.document_job import (
    DocumentJob,
    DocumentType,
)


class DocumentJobRepository(ABC):
    """Output port for document job persistence."""

    @abstractmethod
    def save(self, job: DocumentJob) -> DocumentJob:
        """Saves a new or updated job to the persistence layer."""
        pass

    @abstractmethod
    def get_by_id(self, job_id: uuid.UUID) -> Optional[DocumentJob]:
        """Fetches a job by its ID."""
        pass

    @abstractmethod
    def get_by_user_id(
        self, user_id: uuid.UUID, document_type: Optional[DocumentType] = None
    ) -> List[DocumentJob]:
        """Fetches all jobs for a given user."""
        pass
