from typing import Annotated
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


class DatabaseSettings(BaseSettings):
    database_urls: Annotated[list[str], NoDecode]
    database_replica_urls: Annotated[list[str], NoDecode] = []

    @field_validator("database_urls", mode="before")
    @classmethod
    def split_urls(cls, value: str | list[str]) -> list[str]:
        urls = split(value)
        if not urls:
            raise ValueError("DATABASE_URLS must contain at least one URL")
        return urls

    @field_validator("database_replica_urls", mode="before")
    @classmethod
    def split_replica_urls(cls, value: str | list[str]) -> list[str]:
        return split(value)

    @property
    def shard_count(self) -> int:
        return len(self.database_urls)


def split(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        value = value.split(",")
    return [url.strip() for url in value if url.strip()]


class RedisSettings(BaseSettings):
    redis_url: str
    redis_timeout_seconds: float = 0.5

    @field_validator("redis_url")
    @classmethod
    def check_sentinel_url(cls, value: str) -> str:
        url = urlsplit(value)
        if url.scheme != "redis+sentinel" or not url.netloc or not url.path.strip("/"):
            raise ValueError("REDIS_URL must look like redis+sentinel://host:port,host:port/master")
        return value


class KafkaSettings(BaseSettings):
    kafka_bootstrap_servers: str
    kafka_topic: str = "counter-events"


class AuthSettings(BaseSettings):
    jwt_secret: str
