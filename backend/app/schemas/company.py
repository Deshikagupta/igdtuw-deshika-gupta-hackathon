"""Company reference data and per-company risk summaries."""

from pydantic import BaseModel, Field

from app.schemas.common import CompanyName, Ticker
from app.schemas.risk_signal import RiskSignal


class Company(BaseModel):
    ticker: Ticker
    name: CompanyName
    sector: str | None = None
    aliases: list[str] = Field(default_factory=list)


class RiskCounts(BaseModel):
    high: int = Field(default=0, ge=0)
    medium: int = Field(default=0, ge=0)
    low: int = Field(default=0, ge=0)


class CompanyRiskSummary(BaseModel):
    ticker: Ticker
    company: CompanyName
    sector: str | None = None
    document_count: int = Field(default=0, ge=0)
    average_sentiment: float | None = None
    average_impact_score: float | None = None
    sentiment_trend: float | None = Field(
        default=None, description="Mean sentiment of recent signals minus earlier signals"
    )
    risk_counts: RiskCounts = Field(default_factory=RiskCounts)
    event_distribution: dict[str, int] = Field(default_factory=dict)
    latest_signal: RiskSignal | None = None
    recent_high_risk_events: list[RiskSignal] = Field(default_factory=list)