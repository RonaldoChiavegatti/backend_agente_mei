import redis
import json
import time
import logging
import uuid

from services.document_service.infrastructure.config import settings
from services.document_service.infrastructure.database import SessionLocal
from services.document_service.infrastructure.adapters.persistence.postgres_document_job_repository import (
    PostgresDocumentJobRepository,
)
from services.document_service.application.domain.document_job import (
    ExtractedDataAuthor,
    ProcessingStatus,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def get_db_session():
    return SessionLocal()


def process_job(job_data: dict):
    """
    The core logic for processing a single OCR job.
    """
    job_id_str = job_data.get("job_id")
    if not job_id_str:
        logging.error("Job message is missing a job_id.")
        return

    job_id = uuid.UUID(job_id_str)
    file_path = job_data.get("file_path")
    logging.info(f"Processing job {job_id} for file {file_path}")

    db_session = get_db_session()
    repo = PostgresDocumentJobRepository(db_session)
    job = None

    try:
        # 1. Get the job from the DB
        job = repo.get_by_id(job_id)
        if not job:
            logging.error(f"Job {job_id} not found in database. Skipping.")
            return

        # 2. Update status to PROCESSING
        job.status = ProcessingStatus.PROCESSING
        repo.save(job)
        logging.info(f"Job {job_id} status updated to PROCESSING.")

        # 3. Simulate OCR processing
        time.sleep(10)  # Simulate a 10-second OCR task
        extracted_text = f"This is the simulated OCR text for file {file_path}."

        # 4. Update status to COMPLETED
        job.status = ProcessingStatus.COMPLETED
        job.record_version(
            {"text": extracted_text}, author_type=ExtractedDataAuthor.SYSTEM
        )
        repo.save(job)
        logging.info(f"Job {job_id} successfully processed and marked as COMPLETED.")

    except Exception as e:
        logging.error(f"Failed to process job {job_id}. Error: {e}")
        if job:
            # 5. Update status to FAILED
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            repo.save(job)
    finally:
        db_session.close()


def main():
    """
    The main worker loop.
    """
    logging.info("OCR Worker started. Waiting for jobs...")
    redis_client = redis.from_url(settings.REDIS_URL)

    while True:
        try:
            item = redis_client.blpop(settings.OCR_QUEUE_NAME, timeout=10)

            if item:
                queue, message_str = item
                logging.info(f"Received job from queue '{queue.decode('utf-8')}'")
                job_data = json.loads(message_str)
                process_job(job_data)
            else:
                logging.debug("No job in queue. Waiting...")

        except redis.exceptions.ConnectionError as e:
            logging.error(f"Redis connection error: {e}. Retrying in 15 seconds...")
            time.sleep(15)
        except Exception as e:
            logging.error(f"An unexpected error occurred in the worker loop: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
