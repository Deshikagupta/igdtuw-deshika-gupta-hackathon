"""Validate, normalize, deduplicate, and optionally persist source documents."""

from collections.abc import Mapping
from typing import Any
from app.data_quality.engine import DataQualityEngine

from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from app.models.documents import SourceDocumentRecord
from app.nlp.entities import EntityResolver
from app.nlp.preprocessing import (
    content_hash,
    normalize_text,
    normalize_ticker,
    parse_timestamp,
)
from app.schemas.documents import SourceDocument
from app.schemas.ingestion import IngestionReport, RejectedRecord


def _clean_optional(value: Any) -> str | None:
    """Convert blank optional CSV values to None."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = normalize_text(value)
    return cleaned or None


def _existing_document_hash(document: Mapping[str, Any]) -> str:
    """Hash a stored document using the fields available in the current schema."""
    source = document.get("source", "")
    if hasattr(source, "value"):
        source = source.value

    return content_hash(str(source), str(document.get("text", "")))


def ingest_records(
    records: list[dict[str, Any]],
    collection: Any | None = None,
    *,
    dry_run: bool = False,
    resolver: EntityResolver | None = None,
) -> IngestionReport:
    quality_engine = DataQualityEngine(resolver=resolver)
    """Ingest dictionaries matching the SourceDocument schema.

    If collection is None, records are validated but not persisted.
    Existing documents are never intentionally overwritten.
    """
    resolver = resolver or EntityResolver()

    report = IngestionReport(
        total_records=len(records),
        dry_run=dry_run,
    )

    # Index existing records for ID and content checks.
    existing_by_id: dict[str, dict[str, Any]] = {}
    existing_hashes: set[str] = set()

    if collection is not None:
        for stored in collection.find(
            {},
            {"_id": 0, "document_id": 1, "source": 1, "text": 1},
        ):
            document_id = stored.get("document_id")
            if document_id:
                existing_by_id[str(document_id)] = stored
            existing_hashes.add(_existing_document_hash(stored))

    batch_by_id: dict[str, str] = {}
    batch_hashes: set[str] = set()
    pending: list[SourceDocumentRecord] = []

    for index, raw in enumerate(records):
        document_id = None

        try:
            if not isinstance(raw, dict):
                raise ValueError("Record must be an object")

            quality_report = quality_engine.assess(raw)

            report.quality_warnings += sum(
                1 for issue in quality_report.issues
                if issue.severity == "warning"
            )

            if not quality_report.is_acceptable:
                report.quality_rejected_records += 1
                report.errors.append(
                    RejectedRecord(
                        record_index=index,
                        document_id=(
                            str(raw.get("document_id")).strip()
                            if raw.get("document_id") is not None
                            else None
                        ),
                        reason=(
                            "document_id is required"
                            if not _clean_optional(raw.get("document_id"))
                            else "; ".join(
                                f"{issue.field}: {issue.message}"
                                for issue in quality_report.issues
                                if issue.severity == "error"
                            )
                        ),
                    )
                )
                report.rejected_records += 1
                continue

            document_id = _clean_optional(raw.get("document_id"))
            if not document_id:
                raise ValueError("document_id is required")

            text = normalize_text(raw.get("text"))
            source = _clean_optional(raw.get("source"))
            if not source:
                raise ValueError("source is required")

            timestamp = parse_timestamp(raw.get("timestamp"))
            company_input = _clean_optional(raw.get("company"))
            ticker_input = normalize_ticker(
                _clean_optional(raw.get("ticker"))
            )

            # Resolve against the local registry. Conflicting explicit
            # company/ticker information is rejected rather than guessed.
            resolution = resolver.resolve(
                company=company_input,
                ticker=ticker_input,
                text=text,
            )
            if resolution["status"] == "conflict":
                raise ValueError(resolution["reason"])

            resolved_company = resolution["company"]
            resolved_ticker = resolution["ticker"]

            # Build the canonical schema before any duplicate checks.
            document = SourceDocument.model_validate(
                {
                    "document_id": document_id,
                    "timestamp": timestamp,
                    "source": source,
                    "company": resolved_company,
                    "ticker": resolved_ticker,
                    "text": text,
                }
            )
            record = SourceDocumentRecord.model_validate(
                document.model_dump()
            )

            doc_hash = content_hash(
                record.source.value,
                record.text,
            )

            # Repeated ID in this batch: identical content is a duplicate;
            # different content is a conflicting ID and is rejected.
            if document_id in batch_by_id:
                if batch_by_id[document_id] == doc_hash:
                    report.duplicate_records += 1
                else:
                    report.errors.append(
                        RejectedRecord(
                            record_index=index,
                            document_id=document_id,
                            reason="document_id repeated in this batch with different content",
                        )
                    )
                    report.rejected_records += 1
                continue

            batch_by_id[document_id] = doc_hash

            # Existing ID: do not overwrite it.
            if document_id in existing_by_id:
                stored_hash = _existing_document_hash(
                    existing_by_id[document_id]
                )
                if stored_hash == doc_hash:
                    report.already_present_records += 1
                else:
                    report.errors.append(
                        RejectedRecord(
                            record_index=index,
                            document_id=document_id,
                            reason="document_id already exists with different content",
                        )
                    )
                    report.rejected_records += 1
                continue

            # Same content under another ID is a duplicate.
            if doc_hash in batch_hashes or doc_hash in existing_hashes:
                report.duplicate_records += 1
                continue

            batch_hashes.add(doc_hash)
            report.accepted_records += 1

            if not dry_run and collection is not None:
                pending.append(record)

        except (ValidationError, ValueError, TypeError) as exc:
            report.errors.append(
                RejectedRecord(
                    record_index=index,
                    document_id=document_id,
                    reason=str(exc),
                )
            )
            report.rejected_records += 1

    # Insert individually so a concurrent duplicate ID does not replace data
    # or prevent unrelated valid records from being inserted.
    if not dry_run and collection is not None:
        for record in pending:
            try:
                collection.insert_one(record.to_mongo())
            except DuplicateKeyError:
                # A concurrent process may have inserted this ID after our
                # initial scan. Report it as rejected rather than overwriting.
                report.accepted_records -= 1
                report.rejected_records += 1
                report.errors.append(
                    RejectedRecord(
                        record_index=next(
                            (
                                i
                                for i, item in enumerate(records)
                                if str(item.get("document_id", "")).strip()
                                == record.document_id
                            ),
                            0,
                        ),
                        document_id=record.document_id,
                        reason="document_id was inserted concurrently by another process",
                    )
                )

    return report