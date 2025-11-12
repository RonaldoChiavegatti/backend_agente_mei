from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "dev"
    mongo_url: str = "mongodb://mongo:27017"
    mongo_db: str = "mei_docs"
    redis_url: str = "redis://redis:6379/0"
    oracle_endpoint: str
    oracle_access_key_id: str
    oracle_secret_access_key: str
    oracle_bucket: str

    class Config:
        env_file = ".env"


settings = Settings()
