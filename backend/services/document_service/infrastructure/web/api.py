import uuid
from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    UploadFile,
    File,
    Form,
)

from shared.models.base_models import DocumentJob as DocumentJobResponse
from services.document_service.application.ports.input.document_service import (
    DocumentService,
)
from services.document_service.application.exceptions import (
    JobNotFoundError,
    JobAccessForbiddenError,
)
from services.document_service.application.domain.document_job import DocumentType
from services.document_service.application.dto.document_details import (
    DocumentDetailsResponse,
)
from services.document_service.application.dto.annual_revenue_summary import (
    AnnualRevenueSummaryResponse,
)
from services.document_service.application.dto.monthly_revenue_summary import (
    MonthlyRevenueSummaryResponse,
)
from services.document_service.application.dto.extracted_data_update import (
    ExtractedDataUpdateRequest,
)
from services.document_service.infrastructure.dependencies import get_document_service
from services.document_service.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/upload", response_model=DocumentJobResponse, status_code=status.HTTP_202_ACCEPTED
)
def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        job = doc_service.start_document_processing(
            user_id=user_id,
            file_name=file.filename,
            file_content=file.file,
            document_type=document_type,
        )
        return job
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start processing: {e}",
        )


@router.get("/jobs/{job_id}", response_model=DocumentJobResponse)
def get_job_status_endpoint(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        job = doc_service.get_job_status(job_id=job_id, user_id=user_id)
        return job
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except JobAccessForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/jobs/{job_id}/details", response_model=DocumentDetailsResponse)
def get_job_details_endpoint(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        details = doc_service.get_job_details(job_id=job_id, user_id=user_id)
        return details
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except JobAccessForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/jobs", response_model=List[DocumentJobResponse])
def get_user_jobs_endpoint(
    user_id: uuid.UUID = Depends(get_current_user_id),
    document_type: Optional[DocumentType] = Query(
        default=None,
        description="Filtra os documentos pelo tipo informado.",
    ),
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        jobs = doc_service.get_user_jobs(
            user_id=user_id, document_type=document_type
        )
        return jobs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/dashboard/annual-revenue",
    response_model=AnnualRevenueSummaryResponse,
)
def get_annual_revenue_summary_endpoint(
    year: Optional[int] = Query(
        default=None,
        ge=2000,
        le=2100,
        description="Ano-calendário considerado para o faturamento.",
    ),
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        return doc_service.get_annual_revenue_summary(user_id=user_id, year=year)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get(
    "/dashboard/monthly-revenue",
    response_model=MonthlyRevenueSummaryResponse,
)
def get_monthly_revenue_summary_endpoint(
    year: Optional[int] = Query(
        default=None,
        ge=2000,
        le=2100,
        description="Ano considerado para o faturamento mensal.",
    ),
    month: Optional[int] = Query(
        default=None,
        ge=1,
        le=12,
        description="Mês considerado para o faturamento mensal.",
    ),
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        return doc_service.get_monthly_revenue_summary(
            user_id=user_id, year=year, month=month
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.patch(
    "/jobs/{job_id}/extracted-data",
    response_model=DocumentDetailsResponse,
)
def update_extracted_data_endpoint(
    job_id: uuid.UUID,
    payload: ExtractedDataUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentService = Depends(get_document_service),
):
    try:
        return doc_service.update_extracted_data(
            job_id=job_id, user_id=user_id, payload=payload.data
        )
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except JobAccessForbiddenError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
