from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "dev"
    mongo_url: str = "mongodb://mongo:27017"
    mongo_db: str = "mei_docs"
    redis_url: str = "redis://redis:6379/0"
    oracle_endpoint: str
    oracle_access_key_id: str
    oracle_secret_access_key: str
    oracle_bucket: str


settings = Settings()
