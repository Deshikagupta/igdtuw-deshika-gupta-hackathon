
"""Tests for the source-document data-quality engine."""

from app.data_quality.engine import DataQualityEngine


def valid_record():
    return {
        "document_id": "quality-001",
        "timestamp": "2026-10-09T10:30:00Z",
        "source": "financial_news",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "text": "Apple announced quarterly revenue growth.",
    }


def test_valid_record_gets_perfect_score():
    report = DataQualityEngine().assess(valid_record())

    assert report.is_acceptable is True
    assert report.quality_score == 100.0
    assert report.issues == []
    assert report.checks_failed == 0


def test_missing_required_field_is_an_error():
    record = valid_record()
    record["text"] = "   "

    report = DataQualityEngine().assess(record)

    assert report.is_acceptable is False
    assert any(
        issue.code == "MISSING_REQUIRED_FIELD"
        and issue.field == "text"
        for issue in report.issues
    )


def test_invalid_timestamp_is_rejected():
    record = valid_record()
    record["timestamp"] = "09/10/2026"

    report = DataQualityEngine().assess(record)

    assert report.is_acceptable is False
    assert any(issue.code == "INVALID_TIMESTAMP" for issue in report.issues)


def test_unsupported_source_is_rejected():
    record = valid_record()
    record["source"] = "unknown_source"

    report = DataQualityEngine().assess(record)

    assert report.is_acceptable is False
    assert any(issue.code == "INVALID_SOURCE" for issue in report.issues)


def test_malformed_ticker_is_rejected():
    record = valid_record()
    record["ticker"] = "AAPL!"

    report = DataQualityEngine().assess(record)

    assert report.is_acceptable is False
    assert any(issue.code == "INVALID_TICKER" for issue in report.issues)


def test_company_ticker_conflict_is_rejected():
    record = valid_record()
    record["company"] = "Apple Inc."
    record["ticker"] = "MSFT"

    report = DataQualityEngine().assess(record)

    assert report.is_acceptable is False
    assert any(issue.code == "ENTITY_CONFLICT" for issue in report.issues)


def test_unknown_company_is_warning_not_critical_error():
    record = valid_record()
    record["company"] = "Unknown Example Corporation"
    record["ticker"] = None
    record["text"] = "A company announced an update."

    report = DataQualityEngine().assess(record)

    assert report.is_acceptable is True
    assert any(
        issue.code == "ENTITY_UNRESOLVED"
        and issue.severity == "warning"
        for issue in report.issues
    )


def test_report_score_stays_within_bounds():
    record = valid_record()
    record["timestamp"] = "not-a-date"
    record["ticker"] = "AAPL!"

    report = DataQualityEngine().assess(record)

    assert 0.0 <= report.quality_score <= 100.0
    assert report.checks_failed >= 2