"""Tests for the document ingestion service."""

from datetime import datetime, timezone

import mongomock
import pytest

from app.nlp.entities import EntityResolver
from app.services.ingestion import ingest_records


@pytest.fixture
def collection():
    client = mongomock.MongoClient()
    return client["test_db"]["documents"]


@pytest.fixture
def resolver():
    return EntityResolver()


def valid_record(**overrides):
    record = {
        "document_id": "doc-001",
        "timestamp": "2026-10-09T10:30:00Z",
        "source": "financial_news",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "text": "Apple announced quarterly revenue growth.",
    }
    record.update(overrides)
    return record


def test_valid_record_is_accepted_without_database(collection, resolver):
    report = ingest_records(
        [valid_record()],
        dry_run=True,
        resolver=resolver,
    )

    assert report.total_records == 1
    assert report.accepted_records == 1
    assert report.rejected_records == 0
    assert report.dry_run is True
    assert collection.count_documents({}) == 0


def test_invalid_timestamp_is_rejected(resolver):
    report = ingest_records(
        [valid_record(timestamp="09/10/2026")],
        dry_run=True,
        resolver=resolver,
    )

    assert report.accepted_records == 0
    assert report.rejected_records == 1
    assert "ISO-8601" in report.errors[0].reason


def test_missing_document_id_is_rejected(resolver):
    report = ingest_records(
        [valid_record(document_id="")],
        dry_run=True,
        resolver=resolver,
    )

    assert report.rejected_records == 1
    assert report.errors[0].reason == "document_id is required"


def test_company_ticker_conflict_is_rejected(resolver):
    report = ingest_records(
        [valid_record(company="Apple Inc.", ticker="MSFT")],
        dry_run=True,
        resolver=resolver,
    )

    assert report.rejected_records == 1
    assert "different companies" in report.errors[0].reason


def test_identical_repeated_id_is_duplicate(resolver):
    record = valid_record()
    report = ingest_records(
        [record, record.copy()],
        dry_run=True,
        resolver=resolver,
    )

    assert report.accepted_records == 1
    assert report.duplicate_records == 1
    assert report.rejected_records == 0


def test_repeated_id_with_different_content_is_rejected(resolver):
    report = ingest_records(
        [
            valid_record(),
            valid_record(text="Apple announced a different result."),
        ],
        dry_run=True,
        resolver=resolver,
    )

    assert report.accepted_records == 1
    assert report.rejected_records == 1
    assert "different content" in report.errors[0].reason


def test_same_content_with_different_ids_is_duplicate(resolver):
    report = ingest_records(
        [
            valid_record(document_id="doc-001"),
            valid_record(document_id="doc-002"),
        ],
        dry_run=True,
        resolver=resolver,
    )

    assert report.accepted_records == 1
    assert report.duplicate_records == 1


def test_valid_record_is_persisted(collection, resolver):
    report = ingest_records(
        [valid_record()],
        collection=collection,
        resolver=resolver,
    )

    assert report.accepted_records == 1
    assert collection.count_documents({}) == 1

    stored = collection.find_one({"document_id": "doc-001"})
    assert stored["ticker"] == "AAPL"
    assert stored["company"] == "Apple Inc."


def test_reingesting_existing_record_is_already_present(collection, resolver):
    record = valid_record()
    first = ingest_records([record], collection=collection, resolver=resolver)
    second = ingest_records([record], collection=collection, resolver=resolver)

    assert first.accepted_records == 1
    assert second.already_present_records == 1
    assert second.accepted_records == 0
    assert collection.count_documents({}) == 1


def test_existing_id_with_changed_content_is_rejected(collection, resolver):
    ingest_records(
        [valid_record()],
        collection=collection,
        resolver=resolver,
    )

    report = ingest_records(
        [valid_record(text="Different content for the same ID.")],
        collection=collection,
        resolver=resolver,
    )

    assert report.rejected_records == 1
    assert report.accepted_records == 0
    assert collection.count_documents({}) == 1


def test_dry_run_does_not_write_to_database(collection, resolver):
    report = ingest_records(
        [valid_record()],
        collection=collection,
        dry_run=True,
        resolver=resolver,
    )

    assert report.accepted_records == 1
    assert report.dry_run is True
    assert collection.count_documents({}) == 0


def test_quality_error_increments_quality_rejection_count(resolver):
    report = ingest_records(
        [valid_record(timestamp="not-a-date")],
        dry_run=True,
        resolver=resolver,
    )

    assert report.rejected_records == 1
    assert report.quality_rejected_records == 1
    assert report.accepted_records == 0
    assert "ISO-8601" in report.errors[0].reason


def test_unresolved_company_is_warning_not_rejection(resolver):
    report = ingest_records(
        [
            valid_record(
            company="Unknown Example Corporation",
            ticker=None,
            text="A company announced a new business update.",
            )
        ],
        dry_run=True,
        resolver=resolver,
    )

    assert report.accepted_records == 1
    assert report.rejected_records == 0
    assert report.quality_rejected_records == 0
    assert report.quality_warnings >= 1


def test_quality_rejection_does_not_persist_record(collection, resolver):
    report = ingest_records(
        [valid_record(source="unknown_source")],
        collection=collection,
        resolver=resolver,
    )

    assert report.rejected_records == 1
    assert report.quality_rejected_records == 1
    assert collection.count_documents({}) == 0


