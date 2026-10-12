from functools import lru_cache
from typing import Literal

from pydantic import HttpUrl, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False

    auth_service_url: HttpUrl = HttpUrl("http://localhost:8000")

    redis_dsn: RedisDsn

    pg_dsn: PostgresDsn
    pg_pool_min_size: int = 4
    pg_pool_max_size: int = 20
    pg_pool_timeout: float = 30.0
    pg_pool_max_idle: float = 300.0

    jwt_secret_key: str = "fineshare-super-secret-jwt-key-change-in-production-123456"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    service_name: str = "auth-service"
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
    return Settings()  # type: ignore


settings = get_settings()
