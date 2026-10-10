"""Reusable schema building blocks."""

import re
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

_TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,9}$")


def _normalize_ticker(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not value:
        return None
    if not _TICKER_PATTERN.match(value):
        raise ValueError(
            f"invalid ticker '{value}': use 1-10 characters from A-Z, 0-9, '.' or '-'"
        )
    return value


def _require_ticker(value: str) -> str:
    normalized = _normalize_ticker(value)
    if normalized is None:
        raise ValueError("ticker must not be empty")
    return normalized


Ticker = Annotated[str, AfterValidator(_require_ticker)]
OptionalTicker = Annotated[str | None, AfterValidator(_normalize_ticker)]
CleanText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]
CompanyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Uniform error body returned by the API."""

    detail: str
    error_code: str | None = None


class Page(BaseModel, Generic[T]):
    """Generic paginated list response."""

    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)