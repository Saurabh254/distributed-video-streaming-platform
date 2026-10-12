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
