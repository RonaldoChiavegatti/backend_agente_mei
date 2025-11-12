import uuid
from typing import List, Optional

from services.document_service.application.domain.document_job import DocumentJob
from services.document_service.application.ports.output.document_job_repository import (
    DocumentJobRepository,
)
from services.document_service.infrastructure.database import DocumentJobModel
from sqlalchemy.orm import Session


class PostgresDocumentJobRepository(DocumentJobRepository):
    def __init__(self, db_session: Session):
        self.db = db_session

    def save(self, job: DocumentJob) -> DocumentJob:
        job_model = (
            self.db.query(DocumentJobModel)
            .filter(DocumentJobModel.id == job.id)
            .first()
        )
        if not job_model:
            job_model = DocumentJobModel(**job.model_dump())
            self.db.add(job_model)
        else:
            job_model.status = job.status
            job_model.document_type = job.document_type
            job_model.extracted_data = job.extracted_data
            job_model.error_message = job.error_message

        self.db.commit()
        self.db.refresh(job_model)
        return DocumentJob.model_validate(job_model, from_attributes=True)

    def get_by_id(self, job_id: uuid.UUID) -> Optional[DocumentJob]:
        job_model = (
            self.db.query(DocumentJobModel)
            .filter(DocumentJobModel.id == job_id)
            .first()
        )
        if job_model:
            return DocumentJob.model_validate(job_model, from_attributes=True)
        return None

    def get_by_user_id(self, user_id: uuid.UUID) -> List[DocumentJob]:
        job_models = (
            self.db.query(DocumentJobModel)
            .filter(DocumentJobModel.user_id == user_id)
            .all()
        )
        return [
            DocumentJob.model_validate(job, from_attributes=True) for job in job_models
        ]
