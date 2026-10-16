from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Like and View counter"

    database_url: str = "postgresql+asyncpg://sis1:sis1@postgres:5432/sis1"
    redis_url: str = "redis://redis:6379/0"
    kafka_bootstrap_servers: str = "kafka-1:9092,kafka-2:9092,kafka-3:9092"
    kafka_topic: str = "engagements"
    kafka_dlq_topic: str = "engagements-dlq"
    kafka_group_id: str = "counter-workers-v1"
    kafka_auto_offset_reset: Literal["earliest", "latest"] = "earliest"
    publish_timeout_seconds: float = Field(default=0.15, gt=0, le=5)
    max_inflight_publishes: int = Field(default=2000, ge=1)
    worker_batch_size: int = Field(default=500, ge=1, le=2000)
    worker_poll_ms: int = Field(default=100, ge=1, le=500)
    counter_cache_ttl_ms: int = Field(default=300, ge=1, le=500)
    db_pool_size: int = Field(default=20, ge=1, le=100)
    worker_metrics_port: int = 8001

    @field_validator("database_url")
    @classmethod
    def require_async_postgres(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg://")
        return value


@lru_cache
def get_settings() -> AppConfig:
    return AppConfig()
