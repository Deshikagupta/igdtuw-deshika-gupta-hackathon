"""Application settings loaded from environment variables / .env files.

Lookup order (later wins): <repo>/.env, <repo>/backend/.env, real environment
variables. Real environment variables always take priority.
"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import __version__
from app.exceptions import ConfigurationError

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILES = (PROJECT_ROOT / ".env", BACKEND_DIR / ".env")

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_DB_NAME_FORBIDDEN = re.compile(r'[/\\. "$*<>:|?]')
_CREDENTIALS = re.compile(r"(?<=//)[^/]*@")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Risk Intelligence Platform API"
    app_version: str = __version__
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    mongodb_uri: str = "mongodb://localhost:27017"
    database_name: str = "risk_intelligence"
    mongodb_timeout_ms: int = Field(default=2000, ge=100, le=60000)

    backend_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1, le=65535)

    frontend_url: str = "http://localhost:5173"
    cors_extra_origins: str = "http://127.0.0.1:5173"

    # ---- validators -------------------------------------------------------
    @field_validator("mongodb_uri")
    @classmethod
    def _validate_mongodb_uri(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty (example: mongodb://localhost:27017)")
        if not value.startswith(("mongodb://", "mongodb+srv://")):
            raise ValueError("must start with 'mongodb://' or 'mongodb+srv://'")
        return value

    @field_validator("database_name")
    @classmethod
    def _validate_database_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        if len(value) > 63:
            raise ValueError("must be at most 63 characters")
        if _DB_NAME_FORBIDDEN.search(value):
            raise ValueError("must not contain spaces or any of / \\ . \" $ * < > : | ?")
        return value

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in _VALID_LOG_LEVELS:
            raise ValueError(f"must be one of {sorted(_VALID_LOG_LEVELS)}")
        return value

    @field_validator("frontend_url")
    @classmethod
    def _validate_frontend_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("must start with 'http://' or 'https://'")
        return value

    # ---- derived values ---------------------------------------------------
    @property
    def cors_origins(self) -> list[str]:
        """Allowed CORS origins: FRONTEND_URL plus CORS_EXTRA_ORIGINS, de-duplicated."""
        extras = [o.strip().rstrip("/") for o in self.cors_extra_origins.split(",") if o.strip()]
        return list(dict.fromkeys([self.frontend_url, *extras]))

    @property
    def masked_mongodb_uri(self) -> str:
        """MongoDB URI with credentials removed; the only form that may be logged."""
        return _CREDENTIALS.sub("***:***@", self.mongodb_uri)


def _format_validation_error(exc: ValidationError) -> str:
    lines = ["Invalid configuration. Fix these environment variables (see .env.example):"]
    for err in exc.errors():
        name = ".".join(str(part) for part in err["loc"]).upper()
        message = str(err["msg"]).removeprefix("Value error, ")
        lines.append(f"  - {name}: {message}")
    return "\n".join(lines)


@lru_cache
def get_settings() -> Settings:
    """Load settings once. Raises ConfigurationError with a readable message."""
    try:
        return Settings()
    except ValidationError as exc:
        raise ConfigurationError(_format_validation_error(exc)) from exc