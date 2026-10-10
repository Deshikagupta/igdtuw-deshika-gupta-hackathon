"""Health-check response."""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.base import UtcDatetime, utc_now


class ComponentStatus(BaseModel):
    status: str = Field(description="e.g. 'ok', 'unavailable', 'not_initialized', 'ready'")
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    service: str
    version: str
    environment: str
    timestamp: UtcDatetime = Field(default_factory=utc_now)
    database: ComponentStatus
    nlp: ComponentStatus