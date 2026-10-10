
"""Tests for the deterministic risk signal engine."""

from datetime import datetime, timezone

from app.models.enums import EventType, RiskLevel, SentimentLabel, SourceType
from app.risk_engine.engine import RiskSignalEngine
from app.schemas.documents import SourceDocument


def make_document(text: str) -> SourceDocument:
    return SourceDocument(
        document_id="doc-risk-001",
        timestamp=datetime(2026, 10, 9, 10, 30, tzinfo=timezone.utc),
        source=SourceType.FINANCIAL_NEWS,
        company="Apple Inc.",
        ticker="AAPL",
        text=text,
    )


def test_negative_legal_event_produces_negative_risk_signal():
    signal = RiskSignalEngine().analyze(
        make_document("Apple faces a fraud investigation and a major lawsuit.")
    )

    assert signal.sentiment_label == SentimentLabel.NEGATIVE
    assert signal.event_type == EventType.LEGAL
    assert signal.impact_score >= 1
    assert signal.risk_level in {
        RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH
    }
    assert "fraud" in signal.matched_keywords
    assert signal.provenance.impact_method == "rule_based_v1"


def test_positive_earnings_text_produces_positive_sentiment():
    signal = RiskSignalEngine().analyze(
        make_document("Apple reported profit growth and record quarterly revenue.")
    )

    assert signal.sentiment_label == SentimentLabel.POSITIVE
    assert signal.event_type == EventType.EARNINGS
    assert signal.sentiment_score > 0


def test_neutral_text_has_neutral_sentiment():
    signal = RiskSignalEngine().analyze(
        make_document("Apple held its regularly scheduled business meeting.")
    )

    assert signal.sentiment_label == SentimentLabel.NEUTRAL
    assert signal.sentiment_score == 0.0
    assert signal.event_type == EventType.OTHER


def test_signal_id_is_deterministic_for_same_document_id():
    engine = RiskSignalEngine()
    document = make_document("Apple reported quarterly revenue growth.")

    first = engine.analyze(document)
    second = engine.analyze(document)

    assert first.signal_id == second.signal_id


def test_impact_score_and_confidence_are_bounded():
    signal = RiskSignalEngine().analyze(
        make_document("Company faces bankruptcy, fraud, default, and crisis.")
    )

    assert 1 <= signal.impact_score <= 10
    assert 0.0 <= signal.confidence <= 1.0
    assert 0.0 <= signal.event_confidence <= 1.0