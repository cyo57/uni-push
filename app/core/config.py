from functools import lru_cache
from typing import Any

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "UniPush"
    api_prefix: str = "/api/v1"
    debug: bool = False
    database_url: str = "sqlite+aiosqlite:///./unipush.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-production-please-use-a-long-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    data_encryption_key: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    log_retention_days: int = 30
    http_timeout_seconds: float = 10.0
    login_rate_limit_per_minute: int = 10
    sensitive_log_max_bytes: int = 1024
    delivery_stale_after_seconds: int = 300
    worker_heartbeat_ttl_seconds: int = 180
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "admin123456"
    bootstrap_admin_display_name: str = "平台管理员"

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return bool(value)

    @computed_field
    @property
    def sync_database_url(self) -> str:
        url = make_url(self.database_url)
        drivername = url.drivername
        if drivername == "sqlite+aiosqlite":
            return str(url.set(drivername="sqlite"))
        if drivername == "postgresql+asyncpg":
            return str(url.set(drivername="postgresql+psycopg"))
        if drivername in {"mysql+asyncmy", "mysql+aiomysql"}:
            return str(url.set(drivername="mysql+pymysql"))
        return self.database_url

    @property
    def effective_data_encryption_key(self) -> str:
        return self.data_encryption_key or self.jwt_secret

    @property
    def masked_settings(self) -> dict[str, Any]:
        return {
            "database_url": self.database_url,
            "redis_url": self.redis_url,
            "debug": self.debug,
            "cors_origins": self.cors_origins,
            "login_rate_limit_per_minute": self.login_rate_limit_per_minute,
            "sensitive_log_max_bytes": self.sensitive_log_max_bytes,
            "delivery_stale_after_seconds": self.delivery_stale_after_seconds,
            "worker_heartbeat_ttl_seconds": self.worker_heartbeat_ttl_seconds,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
