from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    GEMINI_API_KEY: str
    BILLING_SERVICE_URL: str  # e.g., http://billing-service:8004
    SECRET_KEY: str
    ALGORITHM: str = "HS256"


settings = Settings()
