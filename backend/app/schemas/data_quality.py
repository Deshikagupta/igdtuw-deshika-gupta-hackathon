
"""Schemas for explainable data-quality assessments."""

from typing import Literal

from pydantic import BaseModel, Field


class QualityIssue(BaseModel):
    """One detected data-quality issue."""

    field: str
    code: str
    message: str
    severity: Literal["error", "warning"]


class DataQualityReport(BaseModel):
    """Quality assessment for a single source record."""

    is_acceptable: bool
    quality_score: float = Field(ge=0.0, le=100.0)
    issues: list[QualityIssue] = Field(default_factory=list)
    checks_passed: int = Field(ge=0)
    checks_failed: int = Field(ge=0)