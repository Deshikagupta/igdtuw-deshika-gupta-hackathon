
"""Deterministic, explainable baseline for generating financial risk signals."""

import hashlib
import re
from typing import Any

from app.models.enums import (
    EventType,
    RiskLevel,
    SentimentLabel,
    SourceType,
)
from app.schemas.documents import SourceDocument
from app.schemas.risk_signal import RiskSignal, SignalProvenance


# Negative indicators are weighted more heavily than neutral wording.
NEGATIVE_TERMS = {
    "decline": 1,
    "declining": 1,
    "loss": 2,
    "miss": 1,
    "missed": 1,
    "lawsuit": 2,
    "investigation": 2,
    "fraud": 3,
    "fine": 2,
    "penalty": 2,
    "downgrade": 2,
    "default": 3,
    "bankruptcy": 3,
    "layoffs": 2,
    "recall": 2,
    "breach": 2,
    "outage": 2,
    "warning": 1,
    "crisis": 3,
    "sanctions": 2,
}

POSITIVE_TERMS = {
    "growth": 1,
    "grew": 1,
    "profit": 2,
    "profits": 2,
    "beat": 2,
    "surge": 2,
    "record": 1,
    "upgrade": 2,
    "approval": 1,
    "recovery": 1,
    "innovation": 1,
    "expansion": 1,
}

EVENT_KEYWORDS = {
    EventType.GEOPOLITICAL: {
        "war", "conflict", "sanctions", "geopolitical", "invasion",
    },
    EventType.MACROECONOMIC: {
        "inflation", "interest rates", "recession", "gdp",
        "unemployment", "central bank",
    },
    EventType.CREDIT_EVENT: {
        "default", "debt restructuring", "credit downgrade",
        "missed payment", "bankruptcy",
    },
    EventType.MERGER_ACQUISITION: {
        "merger", "acquisition", "acquires", "acquired",
        "takeover", "buyout",
    },
    EventType.PRODUCT_LAUNCH: {
        "product launch", "launches a product", "unveiled",
        "new product", "product release",
    },
    EventType.REGULATORY: {
        "regulator", "regulatory", "fine", "penalty",
        "compliance", "sanctions", "antitrust",
    },
    EventType.EARNINGS: {
        "earnings", "quarterly revenue", "profit", "loss",
        "revenue", "financial results", "outlook",
    },
    EventType.LEGAL: {
        "lawsuit", "litigation", "court", "fraud",
        "investigation", "settlement",
    },
    EventType.OPERATIONAL: {
        "outage", "data breach", "cyberattack", "recall",
        "supply disruption", "layoffs", "factory shutdown",
    },
}

SEVERE_TERMS = {
    "bankruptcy", "default", "fraud", "crisis", "war",
    "cyberattack", "data breach", "major outage",
}
MODERATE_TERMS = {
    "lawsuit", "investigation", "downgrade", "fine",
    "penalty", "layoffs", "recall", "sanctions",
}


def _contains_term(text: str, term: str) -> bool:
    """Match a phrase or term without matching inside unrelated words."""
    pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _matched_terms(text: str, terms: set[str]) -> list[str]:
    return sorted(term for term in terms if _contains_term(text, term))


class RiskSignalEngine:
    """Generate validated risk signals from normalized source documents."""

    def analyze(self, document: SourceDocument) -> RiskSignal:
        """Create one signal with rule-based sentiment, event, and impact."""
        text = document.text.strip()
        lowered = text.casefold()

        negative_matches = _matched_terms(lowered, set(NEGATIVE_TERMS))
        positive_matches = _matched_terms(lowered, set(POSITIVE_TERMS))

        negative_weight = sum(NEGATIVE_TERMS[t] for t in negative_matches)
        positive_weight = sum(POSITIVE_TERMS[t] for t in positive_matches)
        total_weight = negative_weight + positive_weight

        if total_weight == 0:
            sentiment_score = 0.0
            sentiment_label = SentimentLabel.NEUTRAL
        else:
            sentiment_score = round(
                (positive_weight - negative_weight) / total_weight, 4
            )
            if sentiment_score > 0.15:
                sentiment_label = SentimentLabel.POSITIVE
            elif sentiment_score < -0.15:
                sentiment_label = SentimentLabel.NEGATIVE
            else:
                sentiment_label = SentimentLabel.NEUTRAL

        event_matches: list[tuple[int, EventType, list[str]]] = []
        for event_type, keywords in EVENT_KEYWORDS.items():
            matches = _matched_terms(lowered, keywords)
            if matches:
                event_matches.append((len(matches), event_type, matches))

        if event_matches:
            # Stable tie-breaking follows the declared event dictionary order.
            _, event_type, matched_event_terms = max(
                event_matches, key=lambda item: item[0]
            )
            event_confidence = min(
                0.60 + 0.10 * len(matched_event_terms), 0.95
            )
        else:
            event_type = EventType.OTHER
            matched_event_terms = []
            event_confidence = 0.40

        severe_matches = _matched_terms(lowered, SEVERE_TERMS)
        moderate_matches = _matched_terms(lowered, MODERATE_TERMS)

        # Transparent heuristic: severity + negative tone + event evidence.
        severity_points = 6 if severe_matches else 3 if moderate_matches else 1
        sentiment_points = (
            2 if sentiment_label == SentimentLabel.NEGATIVE
            else 1 if sentiment_label == SentimentLabel.NEUTRAL
            else 0
        )
        event_points = 2 if event_type in {
            EventType.CREDIT_EVENT,
            EventType.REGULATORY,
            EventType.LEGAL,
            EventType.GEOPOLITICAL,
        } else 1 if event_type != EventType.OTHER else 0

        impact_score = max(
            1, min(10, severity_points + sentiment_points + event_points)
        )

        if impact_score >= 8:
            risk_level = RiskLevel.HIGH
        elif impact_score >= 5:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Deterministic ID allows safe retries for the same source document.
        digest = hashlib.sha256(document.document_id.encode()).hexdigest()[:16]
        signal_id = f"sig-{digest}"

        matched_keywords = sorted(
            set(negative_matches)
            | set(positive_matches)
            | set(matched_event_terms)
            | set(severe_matches)
            | set(moderate_matches)
        )

        confidence = round(
            min(0.95, 0.50 + 0.10 * len(matched_keywords)), 2
        )

        return RiskSignal(
            signal_id=signal_id,
            document_id=document.document_id,
            company=document.company,
            ticker=document.ticker,
            source=document.source,
            text=text,
            timestamp=document.timestamp,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            event_type=event_type,
            event_confidence=event_confidence,
            impact_score=impact_score,
            risk_level=risk_level,
            confidence=confidence,
            matched_keywords=matched_keywords,
            impact_breakdown={
                "severity_points": float(severity_points),
                "sentiment_points": float(sentiment_points),
                "event_points": float(event_points),
            },
            provenance=SignalProvenance(
                sentiment_source="keyword_rules",
                event_source="keyword_rules",
                impact_method="rule_based_v1",
            ),
        )