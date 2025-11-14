from abc import ABC, abstractmethod
from typing import IO, Dict, Any, List, Optional
import uuid

from shared.models.base_models import DocumentJob as DocumentJobResponse
from services.document_service.application.domain.document_job import DocumentType
from services.document_service.application.dto.annual_revenue_summary import (
    AnnualRevenueSummaryResponse,
)
from services.document_service.application.dto.monthly_revenue_summary import (
    MonthlyRevenueSummaryResponse,
)
from services.document_service.application.dto.document_details import (
    DocumentDetailsResponse,
)
from services.document_service.application.dto.dashboard_basic_metrics import (
    DashboardBasicMetricsResponse,
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

    @abstractmethod
    def get_annual_revenue_summary(
        self, user_id: uuid.UUID, year: Optional[int] = None
    ) -> AnnualRevenueSummaryResponse:
        """Aggregate the MEI annual revenue for dashboard consumption."""
        pass

    @abstractmethod
    def get_monthly_revenue_summary(
        self, user_id: uuid.UUID, year: Optional[int] = None, month: Optional[int] = None
    ) -> MonthlyRevenueSummaryResponse:
        """Aggregate the MEI monthly revenue for dashboard consumption."""
        pass

    @abstractmethod
    def get_basic_dashboard_metrics(
        self, user_id: uuid.UUID
    ) -> DashboardBasicMetricsResponse:
        """Return the basic counters displayed in the dashboard overview."""
        pass
