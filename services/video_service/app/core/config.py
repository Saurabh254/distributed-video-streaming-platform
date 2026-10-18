from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    port: int = 8001
    host: str = "127.0.0.1"

    service_name: str = "video-service"

    # Databases
    pg_dsn: PostgresDsn = PostgresDsn(
        "postgresql://postgres:12345678@localhost:5432/fineshare"
    )
    pg_pool_min_size: int = 4
    pg_pool_max_size: int = 20
    pg_pool_timeout: float = 30.0
    pg_pool_max_idle: float = 300.0

    redis_dsn: RedisDsn = RedisDsn("redis://localhost:6379/0")

    # Security & Auth (Shared with auth_service)
    jwt_secret_key: str = "fineshare-super-secret-jwt-key-change-in-production-123456"
    jwt_algorithm: str = "HS256"

    # Object Storage (MinIO / S3)
    s3_endpoint_url: str = "http://127.0.0.1:9000"
    s3_public_endpoint_url: str = "http://127.0.0.1:9000"
    s3_access_key: str = "localminio"
    s3_secret_key: str = "12345678"
    s3_bucket: str = "videos"
    s3_region: str = "us-east-1"
    s3_presigned_expiry_seconds: int = 900  # 15 minutes

    # Upload restrictions (Default: 5GB)
    max_upload_size_bytes: int = 5 * 1024 * 1024 * 1024
    allowed_content_types: list[str] = [
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "video/x-matroska",
    ]

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:4000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4000",
    ]

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "console"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
