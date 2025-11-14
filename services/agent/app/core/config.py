from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "dev"
    database_url: str = "postgresql+psycopg2://appuser:apppass@postgres:5432/appdb"
    mongo_url: str = "mongodb://mongo:27017"
    mongo_db: str = "appdb"
    mongo_collection_documents: str = "documents"
    rag_top_k: int = 5
    embedding_dimensions: int = 384
    billing_service_url: str = "http://billing:8000"
    billing_timeout_seconds: float = 5.0

    class Config:
        env_file = ".env"


settings = Settings()
