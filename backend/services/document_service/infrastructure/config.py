from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "documents"
    REDIS_URL: str
    OCR_QUEUE_NAME: str = "ocr_jobs"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"


settings = Settings()
