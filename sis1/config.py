from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Like and View counter"

    database_url: str = "sqlite:///./database.db"


settings = AppConfig()


@lru_cache
def get_settings():
    return settings
