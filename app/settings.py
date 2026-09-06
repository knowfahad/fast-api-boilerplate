from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["critical", "error", "warning", "info", "debug", "trace"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "fahad"
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = Field(default=1, ge=1)
    log_level: LogLevel = "info"


@lru_cache
def get_settings() -> Settings:
    return Settings()
