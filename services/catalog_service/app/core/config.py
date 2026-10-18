from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    port: int = 8002
    host: str = "127.0.0.1"

    service_name: str = "catalog-service"

    # Databases
    pg_dsn: PostgresDsn = PostgresDsn(
        "postgresql://postgres:12345678@localhost:5432/fineshare"
    )
    pg_pool_min_size: int = 4
    pg_pool_max_size: int = 20
    pg_pool_timeout: float = 30.0
    pg_pool_max_idle: float = 300.0

    redis_dsn: RedisDsn = RedisDsn("redis://localhost:6379/0")

    # Security & Auth
    jwt_secret_key: str = "fineshare-super-secret-jwt-key-change-in-production-123456"
    jwt_algorithm: str = "HS256"

    # Caching
    catalog_cache_enabled: bool = True
    catalog_cache_ttl_seconds: int = 30

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
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
