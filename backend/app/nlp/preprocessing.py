"""Pure preprocessing utilities for incoming financial documents."""

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any


_TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,9}$")


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace without changing the wording."""
    if not isinstance(value, str):
        raise TypeError("text must be a string")

    value = unicodedata.normalize("NFKC", value)
    return " ".join(value.split())


def normalize_company(value: str | None) -> str | None:
    """Normalize a company name for matching, not for display."""
    if value is None:
        return None

    value = normalize_text(value).casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def normalize_ticker(value: str | None) -> str | None:
    """Normalize a ticker and reject values outside our accepted format."""
    if value is None:
        return None

    value = value.strip().upper()
    if not value:
        return None

    if not _TICKER_PATTERN.fullmatch(value):
        raise ValueError(
            "ticker must contain 1-10 characters: A-Z, 0-9, '.' or '-'"
        )

    return value


def parse_timestamp(value: Any) -> datetime:
    """Parse an ISO-8601 timestamp and return an aware UTC datetime.

    Naive ISO timestamps are interpreted as UTC. Ambiguous date formats
    such as 03/04/2026 are deliberately rejected.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise ValueError("timestamp must not be empty")

        if not re.match(r"^\d{4}-\d{2}-\d{2}(?:$|T| )", raw):
            raise ValueError(
                "timestamp must use ISO-8601 format, e.g. "
                "2026-10-09T12:30:00Z"
            )

        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid ISO-8601 timestamp: {raw}") from exc
    else:
        raise TypeError("timestamp must be an ISO-8601 string or datetime")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def content_hash(
    source: str,
    text: str,
    headline: str | None = None,
) -> str:
    """Return a deterministic SHA-256 hash for duplicate-content checks."""
    payload = {
        "source": normalize_text(source).casefold(),
        "headline": normalize_text(headline or "").casefold(),
        "text": normalize_text(text).casefold(),
    }
    serialized = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
