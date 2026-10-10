"""The structured risk signal: the central output of the NLP Risk Engine."""

from pydantic import BaseModel, Field

from app.models.base import UtcDatetime, utc_now
from app.models.enums import EventType, RiskLevel, SentimentLabel, SourceType
from app.schemas.common import CleanText, CompanyName, OptionalTicker


class SignalProvenance(BaseModel):
    """Records which parts of a signal are pretrained-ML output and which are rules."""

    sentiment_source: str = Field(default="finbert", description="e.g. 'finbert'")
    event_source: str = Field(
        default="zero_shot", description="'zero_shot' | 'keyword_override' | 'fallback'"
    )
    impact_method: str = Field(default="rule_based_v1", description="Deterministic formula id")
    sentiment_model: str | None = None
    event_model: str | None = None


class RiskSignal(BaseModel):
    signal_id: str = Field(min_length=1, max_length=120)
    document_id: str = Field(min_length=1, max_length=100)
    company: CompanyName | None = None
    ticker: OptionalTicker = None
    source: SourceType
    text: CleanText
    timestamp: UtcDatetime

    sentiment_score: float = Field(ge=-1.0, le=1.0, description="P(positive) - P(negative)")
    sentiment_label: SentimentLabel
    event_type: EventType
    event_confidence: float = Field(ge=0.0, le=1.0)
    impact_score: int = Field(ge=1, le=10, description="Prototype Market Impact Score")
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0, description="Overall signal confidence")

    matched_keywords: list[str] = Field(default_factory=list)
    impact_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Contribution of each factor to the impact score"
    )
    provenance: SignalProvenance = Field(default_factory=SignalProvenance)
    created_at: UtcDatetime = Field(default_factory=utc_now)