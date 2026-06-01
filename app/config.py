from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://emne:emne@localhost:5432/emne"
    secret_key: str = "change-me-in-production"
    auth_password_hash: str = ""  # bcrypt hash, set via environment

    # Tigris / S3-compatible storage
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "emne-photos"
    s3_region: str = "auto"

    model_config = {"env_prefix": "EMNE_"}


settings = Settings()
