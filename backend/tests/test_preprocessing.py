
from datetime import datetime, timezone

import pytest

from app.nlp.preprocessing import (
    content_hash,
    normalize_company,
    normalize_text,
    normalize_ticker,
    parse_timestamp,
)


def test_normalize_text_collapses_whitespace():
    assert normalize_text("  Market \n\t risk   increased ") == (
        "Market risk increased"
    )


def test_normalize_company_ignores_case_and_punctuation():
    assert normalize_company("  NVIDIA, Corp. ") == "nvidia corp"


def test_normalize_company_handles_none_and_empty():
    assert normalize_company(None) is None
    assert normalize_company("   ") is None


def test_normalize_ticker_uppercases_value():
    assert normalize_ticker("  nvda ") == "NVDA"


def test_normalize_ticker_handles_empty_value():
    assert normalize_ticker(None) is None
    assert normalize_ticker("  ") is None


def test_normalize_ticker_rejects_invalid_value():
    with pytest.raises(ValueError):
        normalize_ticker("$NVDA")


def test_parse_timestamp_converts_to_utc():
    result = parse_timestamp("2026-10-09T12:00:00+05:30")
    assert result == datetime(2026, 10, 9, 6, 30, tzinfo=timezone.utc)


def test_parse_timestamp_treats_naive_datetime_as_utc():
    result = parse_timestamp("2026-10-09T12:00:00")
    assert result == datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def test_parse_timestamp_rejects_ambiguous_format():
    with pytest.raises(ValueError):
        parse_timestamp("03/04/2026")


def test_content_hash_is_deterministic_after_normalization():
    first = content_hash("financial_news", "Market   risk increased")
    second = content_hash("FINANCIAL_NEWS", "Market risk increased")
    assert first == second


def test_content_hash_changes_when_content_changes():
    first = content_hash("financial_news", "Revenue increased")
    second = content_hash("financial_news", "Revenue decreased")
    assert first != second