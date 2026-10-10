"""Stress-testing schemas.

Conventions (used everywhere, including YAML config in Phase 5):
  * Shocks are PERCENTAGES: -10.0 means -10 %, +2.0 means +2 %.
  * absolute_loss = value_before - value_after  (positive = loss, negative = gain).
  * percentage_loss = absolute_loss / value_before * 100.
"""

from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator

from app.models.base import UtcDatetime, utc_now
from app.models.enums import AssetType, EventType, StressMode
from app.schemas.common import OptionalTicker

ShockPct = Annotated[float, Field(ge=-100.0, le=100.0)]
ImpactScore = Annotated[int, Field(ge=1, le=10)]


class ScenarioDefinition(BaseModel):
    """A configured stress scenario (loaded from YAML in Phase 5)."""

    key: str = Field(pattern=r"^[a-z0-9_\-]+$")
    name: str
    description: str | None = None
    shocks_pct: dict[AssetType, ShockPct]
    trigger_event_types: list[EventType] = Field(default_factory=list)
    impact_threshold: int = Field(default=8, ge=1, le=10)
    priority: int = Field(default=100, ge=1)


class StressTrigger(BaseModel):
    """Result of evaluating whether a risk signal should trigger a stress test."""

    triggered: bool
    scenario_key: str | None = None
    event_type: EventType
    impact_score: ImpactScore
    threshold: int = Field(ge=1, le=10)
    reason: str


class AssetStressResult(BaseModel):
    asset_id: str
    asset_name: str
    asset_type: AssetType
    ticker: OptionalTicker = None
    value_before: float
    shock_pct: float
    value_after: float
    absolute_loss: float


class AssetTypeStressResult(BaseModel):
    asset_type: AssetType
    value_before: float
    value_after: float
    absolute_loss: float
    shock_pct: float


class StressTestRequest(BaseModel):
    """Manual or signal-driven stress test request. At least one selector is required."""

    scenario_key: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"^[a-z0-9_\-]+$")
    signal_id: str | None = Field(default=None, min_length=1, max_length=120)
    custom_shocks_pct: dict[AssetType, ShockPct] | None = None

    @model_validator(mode="after")
    def _require_a_selector(self) -> Self:
        if not (self.scenario_key or self.signal_id or self.custom_shocks_pct):
            raise ValueError("provide at least one of: scenario_key, signal_id, custom_shocks_pct")
        return self


class StressTestResult(BaseModel):
    stress_test_id: str = Field(min_length=1, max_length=150)
    mode: StressMode
    scenario_key: str
    scenario_name: str
    scenario_description: str | None = None

    trigger_event_type: EventType | None = None
    trigger_impact_score: ImpactScore | None = None
    trigger_signal_id: str | None = None
    trigger_company: str | None = None
    trigger_ticker: OptionalTicker = None
    trigger_reason: str

    shocks_pct: dict[AssetType, float]
    portfolio_before: float
    portfolio_after: float
    absolute_loss: float
    percentage_loss: float
    asset_level_results: list[AssetStressResult]
    asset_type_results: list[AssetTypeStressResult] = Field(default_factory=list)

    assumptions_note: str = (
        "Shocks are simplified, illustrative hackathon assumptions; "
        "results are not a market forecast."
    )
    created_at: UtcDatetime = Field(default_factory=utc_now)