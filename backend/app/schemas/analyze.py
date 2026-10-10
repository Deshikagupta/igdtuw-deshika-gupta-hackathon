"""Request/response for POST /api/analyze (analyze a new piece of text)."""

from pydantic import BaseModel, Field

from app.models.base import UtcDatetime
from app.models.enums import SourceType
from app.schemas.common import CleanText, CompanyName, OptionalTicker
from app.schemas.risk_signal import RiskSignal
from app.schemas.stress import StressTestResult, StressTrigger


class AnalyzeRequest(BaseModel):
    text: CleanText
    company: CompanyName | None = None
    ticker: OptionalTicker = None
    source: SourceType = SourceType.FINANCIAL_NEWS
    timestamp: UtcDatetime | None = Field(default=None, description="Defaults to now (UTC)")
    persist: bool = Field(default=True, description="Store the document and signal in MongoDB")
    run_stress_test: bool = Field(
        default=True, description="Evaluate the stress-test trigger and run it if met"
    )


class AnalyzeResponse(BaseModel):
    signal: RiskSignal
    trigger: StressTrigger | None = None
    stress_test: StressTestResult | None = None