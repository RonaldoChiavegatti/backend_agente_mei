from sqlalchemy import create_engine, Column, String, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

from ..application.domain.document_job import DocumentType, ProcessingStatus
from .config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLAlchemy DocumentJob Table Model
class DocumentJobModel(Base):
    __tablename__ = "document_processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    status = Column(
        Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.PROCESSING
    )
    extracted_data = Column(JSONB)
    error_message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
