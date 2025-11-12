"""Utilities for enqueuing Celery tasks from the documents service."""

from celery import Celery

from app.core.config import settings


celery_client = Celery(
    "documents_producer",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


def enqueue_document_processing(document_id: str) -> None:
    """Send the OCR task to the worker queue."""
    celery_client.send_task("documents.process_document", args=[document_id])
