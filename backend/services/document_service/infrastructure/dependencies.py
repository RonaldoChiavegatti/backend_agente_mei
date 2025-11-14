from fastapi import Depends
from sqlalchemy.orm import Session

from services.document_service.infrastructure.database import get_db
from services.document_service.application.ports.input.document_service import (
    DocumentService,
)
from services.document_service.application.services.document_service_impl import (
    DocumentServiceImpl,
)
from services.document_service.infrastructure.adapters.persistence.postgres_document_job_repository import (
    PostgresDocumentJobRepository,
)
from services.document_service.infrastructure.adapters.storage.minio_file_storage import (
    MinioFileStorage,
)
from services.document_service.infrastructure.adapters.queue.redis_message_queue import (
    RedisMessageQueue,
)
from services.document_service.infrastructure.config import settings
from services.billing_service.infrastructure.adapters.persistence.postgres_billing_repository import (
    PostgresBillingRepository,
)


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """
    Composition Root for the DocumentService.
    """
    job_repo = PostgresDocumentJobRepository(db)

    file_storage = MinioFileStorage(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        bucket_name=settings.MINIO_BUCKET_NAME,
    )

    message_queue = RedisMessageQueue(redis_url=settings.REDIS_URL)

    billing_repo = PostgresBillingRepository(db)

    return DocumentServiceImpl(
        job_repository=job_repo,
        file_storage=file_storage,
        message_queue=message_queue,
        ocr_queue_name=settings.OCR_QUEUE_NAME,
        billing_repository=billing_repo,
    )
