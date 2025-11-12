import logging
from datetime import datetime
from io import BytesIO

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.celery_app import celery_app
from app.core.config import settings
from app.storage.oracle_s3 import get_s3_client
from app.processing import build_structured_data, extract_text_from_bytes


logger = logging.getLogger(__name__)


@celery_app.task(name="documents.process_document", bind=True, max_retries=3)
def process_document(self, document_id: str):
    """Process documents asynchronously, extracting OCR data and metadata."""

    logger.info("Iniciando processamento OCR para documento %s", document_id)

    try:
        object_id = ObjectId(document_id)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Identificador de documento inválido: %s", document_id)
        raise exc

    mongo_client = MongoClient(settings.mongo_url)
    documents = mongo_client[settings.mongo_db]["documents"]

    now = datetime.utcnow()
    documents.update_one(
        {"_id": object_id},
        {"$set": {"status": "processing", "updated_at": now}},
    )

    try:
        document = documents.find_one({"_id": object_id})
        if not document:
            logger.warning("Documento %s não encontrado no MongoDB", document_id)
            documents.update_one(
                {"_id": object_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": "Documento não encontrado",
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            return

        s3 = get_s3_client()
        buffer = BytesIO()
        s3.download_fileobj(settings.oracle_bucket, document["key"], buffer)
        file_bytes = buffer.getvalue()
        buffer.close()

        filename = document.get("filename") or document.get("key")
        extracted_text = extract_text_from_bytes(file_bytes, filename)
        structured_data = build_structured_data(
            extracted_text, document.get("document_type")
        )

        documents.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": "completed",
                    "extracted_text": extracted_text,
                    "extracted_data": structured_data,
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        logger.info(
            "Documento %s processado com sucesso e marcado como concluído",
            document_id,
        )
    except (PyMongoError, OSError) as exc:  # pragma: no cover - infra errors
        logger.exception("Erro de infraestrutura ao processar documento %s", document_id)
        documents.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise self.retry(exc=exc, countdown=30)
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.exception("Falha inesperada no processamento do documento %s", document_id)
        documents.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise
    finally:
        mongo_client.close()
