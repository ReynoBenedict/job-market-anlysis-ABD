from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from environment variables (and `.env` if present).

    `DATABASE_URL` has no default on purpose: starting the API against an unintended
    database is worse than failing fast with a clear validation error.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    admin_api_token: SecretStr | None = None
    # Comma-separated in the environment, e.g. "http://localhost:3001,https://example.org".
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3001"]
    )
    log_level: str = "INFO"
    log_format: Literal["text", "json"] = "text"
    freshness_window_days: int = Field(default=30, ge=1, le=365)
    crawler_contact_url: str = "https://github.com/ReynoBenedict/job-market-anlysis-ABD"
    # Root of the Parquet data lake; relative paths resolve against the working directory.
    lake_dir: Path = Path("lake")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("admin_api_token", mode="before")
    @classmethod
    def _empty_token_means_disabled(cls, value: object) -> object:
        return None if value in ("", None) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # fields are read from the environment
