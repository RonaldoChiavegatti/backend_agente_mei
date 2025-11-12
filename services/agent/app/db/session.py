"""Database session and base utilities for the Agent service."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, future=True
)
Base = declarative_base()


def get_session():
    """Provide a SQLAlchemy session for dependency injection."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
