
"""Deterministic quality checks for incoming financial source records."""

from collections.abc import Mapping
from typing import Any

from app.nlp.entities import EntityResolver
from app.nlp.preprocessing import normalize_ticker, parse_timestamp
from app.schemas.data_quality import DataQualityReport, QualityIssue


REQUIRED_FIELDS = ("document_id", "timestamp", "source", "text")
SUPPORTED_SOURCES = {"financial_news", "social_media"}


class DataQualityEngine:
    """Assess completeness, validity, and entity consistency."""

    def __init__(self, resolver: EntityResolver | None = None) -> None:
        self.resolver = resolver or EntityResolver()

    def assess(self, record: Mapping[str, Any]) -> DataQualityReport:
        """Return an explainable quality report for one source record."""
        issues: list[QualityIssue] = []
        checks_passed = 0
        checks_failed = 0

        def check(
            passed: bool,
            field: str,
            code: str,
            message: str,
            severity: str = "error",
        ) -> None:
            nonlocal checks_passed, checks_failed

            if passed:
                checks_passed += 1
            else:
                checks_failed += 1
                issues.append(
                    QualityIssue(
                        field=field,
                        code=code,
                        message=message,
                        severity=severity,
                    )
                )

        # Completeness: all four core fields must be present and nonblank.
        for field in REQUIRED_FIELDS:
            value = record.get(field)
            present = value is not None and (
                not isinstance(value, str) or bool(value.strip())
            )
            check(
                present,
                field,
                "MISSING_REQUIRED_FIELD",
                f"Required field '{field}' is missing or blank.",
            )

        # Validity: check fields only when values are present.
        timestamp = record.get("timestamp")
        if timestamp is not None and timestamp != "":
            try:
                parse_timestamp(timestamp)
                check(True, "timestamp", "INVALID_TIMESTAMP", "")
            except (TypeError, ValueError):
                check(
                    False,
                    "timestamp",
                    "INVALID_TIMESTAMP",
                    "Timestamp must be a valid ISO-8601 value.",
                )

        source = record.get("source")
        if source is not None and source != "":
            check(
                isinstance(source, str)
                and source.strip().casefold() in SUPPORTED_SOURCES,
                "source",
                "INVALID_SOURCE",
                "Source must be financial_news or social_media.",
            )

        text = record.get("text")
        if text is not None and text != "":
            check(
                isinstance(text, str) and bool(text.strip()),
                "text",
                "INVALID_TEXT",
                "Text must be a nonblank string.",
            )

        ticker = record.get("ticker")
        normalized_ticker = None
        if ticker is not None and ticker != "":
            try:
                normalized_ticker = normalize_ticker(ticker)
                check(
                    normalized_ticker is not None,
                    "ticker",
                    "INVALID_TICKER",
                    "Ticker must not be blank.",
                )
            except (AttributeError, TypeError, ValueError):
                check(
                    False,
                    "ticker",
                    "INVALID_TICKER",
                    "Ticker must contain 1-10 letters, digits, dots, or hyphens.",
                )

        # Consistency: only assess identity when company or ticker is supplied.
        company = record.get("company")
        if company is not None and company != "":
            check(
                isinstance(company, str) and bool(company.strip()),
                "company",
                "INVALID_COMPANY",
                "Company must be a nonblank string when supplied.",
            )

        if company or normalized_ticker:
            try:
                resolution = self.resolver.resolve(
                    company=company if isinstance(company, str) else None,
                    ticker=normalized_ticker,
                    text=text if isinstance(text, str) else None,
                )
                status = resolution["status"]

                if status == "conflict":
                    check(
                        False,
                        "company/ticker",
                        "ENTITY_CONFLICT",
                        resolution["reason"] or "Company and ticker conflict.",
                    )
                elif status == "unresolved":
                    check(
                        False,
                        "company/ticker",
                        "ENTITY_UNRESOLVED",
                        resolution["reason"] or "Company could not be resolved.",
                        severity="warning",
                    )
                else:
                    check(
                        True,
                        "company/ticker",
                        "ENTITY_CONSISTENT",
                        "",
                    )
            except (TypeError, ValueError):
                check(
                    False,
                    "company/ticker",
                    "ENTITY_CHECK_FAILED",
                    "Company identity could not be validated.",
                )

        total_checks = checks_passed + checks_failed
        score = (
            round(100 * checks_passed / total_checks, 2)
            if total_checks
            else 0.0
        )

        has_errors = any(issue.severity == "error" for issue in issues)

        return DataQualityReport(
            is_acceptable=not has_errors,
            quality_score=score,
            issues=issues,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )