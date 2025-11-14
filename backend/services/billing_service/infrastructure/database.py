from sqlalchemy import create_engine, Column, String, DateTime, BigInteger, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

from ..application.domain.transaction import TransactionType
from .config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# SQLAlchemy UserBalance Table Model
class UserBalanceModel(Base):
    __tablename__ = "user_balances"
    user_id = Column(UUID(as_uuid=True), primary_key=True)
    balance = Column(BigInteger, nullable=False, default=0)
    last_updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# SQLAlchemy Transaction Table Model
class TransactionModel(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    amount = Column(BigInteger, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    description = Column(String)
    related_job_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
