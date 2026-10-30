from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class DatabaseSettings(BaseSettings):
    database_urls: Annotated[list[str], NoDecode]

    @field_validator("database_urls", mode="before")
    @classmethod
    def split_urls(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            value = value.split(",")
        urls = [url.strip() for url in value if url.strip()]
        if not urls:
            raise ValueError("DATABASE_URLS must contain at least one URL")
        return urls

    @property
    def shard_count(self) -> int:
        return len(self.database_urls)


class RedisSettings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    redis_sentinels: str = ""
    redis_master_name: str = "counters"
    redis_timeout_seconds: float = 0.5


class KafkaSettings(BaseSettings):
    kafka_bootstrap_servers: str
    kafka_topic: str = "counter-events"


class AuthSettings(BaseSettings):
    jwt_secret: str
