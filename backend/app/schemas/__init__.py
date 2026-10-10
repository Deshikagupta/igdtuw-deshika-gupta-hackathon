"""Pydantic request/response schemas (also the canonical entity shapes)."""

from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.common import CleanText, ErrorResponse, OptionalTicker, Page, Ticker
from app.schemas.company import Company, CompanyRiskSummary, RiskCounts
from app.schemas.dashboard import DashboardSummary
from app.schemas.documents import SourceDocument
from app.schemas.health import ComponentStatus, HealthResponse
from app.schemas.portfolio import (
    AllocationItem,
    PortfolioAsset,
    PortfolioResponse,
    PortfolioSummary,
)
from app.schemas.risk_signal import RiskSignal, SignalProvenance
from app.schemas.stress import (
    AssetStressResult,
    AssetTypeStressResult,
    ScenarioDefinition,
    StressTestRequest,
    StressTestResult,
    StressTrigger,
)

__all__ = [
    "AllocationItem",
    "AnalyzeRequest",
    "AnalyzeResponse",
    "AssetStressResult",
    "AssetTypeStressResult",
    "CleanText",
    "Company",
    "CompanyRiskSummary",
    "ComponentStatus",
    "DashboardSummary",
    "ErrorResponse",
    "HealthResponse",
    "OptionalTicker",
    "Page",
    "PortfolioAsset",
    "PortfolioResponse",
    "PortfolioSummary",
    "RiskCounts",
    "RiskSignal",
    "ScenarioDefinition",
    "SignalProvenance",
    "SourceDocument",
    "StressTestRequest",
    "StressTestResult",
    "StressTrigger",
    "Ticker",
]