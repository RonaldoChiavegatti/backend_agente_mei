from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pymongo import MongoClient

from app.core.config import settings
from app.storage.oracle_s3 import upload_fileobj
from app.worker_client import enqueue_document_processing

router = APIRouter(prefix="/documents", tags=["documents"])


def get_mongo_collection():
    client = MongoClient(settings.mongo_url)
    db = client[settings.mongo_db]
    return db["documents"]


FISCAL_DOCUMENT_TYPES = {
    "NOTA_FISCAL_EMITIDA",
    "NOTA_FISCAL_RECEBIDA",
    "INFORME_BANCARIO",
    "DESPESA_DEDUTIVEL",
    "INFORME_RENDIMENTOS",
    "DASN_SIMEI",
}

ALLOWED_DOCUMENT_TYPES = FISCAL_DOCUMENT_TYPES.union(
    {"RECIBO_IR_ANTERIOR", "DOC_IDENTIFICACAO", "COMPROVANTE_ENDERECO"}
)


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "documents"}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    collection=Depends(get_mongo_collection),
):
    if file.content_type not in ["application/pdf", "image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Tipo de arquivo não suportado")

    normalized_document_type = document_type.strip().upper()
    if normalized_document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de documento inválido")

    doc_key = f"{datetime.utcnow().timestamp()}_{file.filename}"
    contents = await file.read()
    upload_fileobj(fileobj=BytesIO(contents), key=doc_key)

    doc = {
        "filename": file.filename,
        "key": doc_key,
        "status": "pending",
        "document_type": normalized_document_type,
        "extracted_text": None,
        "extracted_data": None,
        "error": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = collection.insert_one(doc)

    try:
        enqueue_document_processing(str(result.inserted_id))
    except Exception as exc:
        collection.update_one(
            {"_id": result.inserted_id},
            {
                "$set": {
                    "status": "failed",
                    "error": f"Falha ao enfileirar OCR: {exc}",
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise HTTPException(
            status_code=500, detail="Não foi possível iniciar o processamento do documento"
        ) from exc

    return {"id": str(result.inserted_id), "status": "pending"}
