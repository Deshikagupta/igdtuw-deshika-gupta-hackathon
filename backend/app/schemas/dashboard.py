"""Aggregated numbers for the dashboard header cards."""

from pydantic import BaseModel, Field

from app.models.base import UtcDatetime


class DashboardSummary(BaseModel):
    total_documents: int = Field(default=0, ge=0)
    total_signals: int = Field(default=0, ge=0)
    high_risk_events: int = Field(default=0, ge=0)
    average_sentiment: float | None = None
    average_impact_score: float | None = None
    stress_tests_triggered: int = Field(default=0, ge=0)
    latest_signal_at: UtcDatetime | None = None

    portfolio_value: float | None = None
    stressed_portfolio_value: float | None = None
    potential_loss: float | None = None
    potential_loss_pct: float | None = None