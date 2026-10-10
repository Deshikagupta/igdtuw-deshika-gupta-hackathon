import pytest
from pydantic import ValidationError

from app.models.enums import AssetType, EventType, RiskLevel
from app.schemas import (
    AnalyzeRequest,
    PortfolioAsset,
    RiskSignal,
    SourceDocument,
    StressTestRequest,
)


def test_source_document_normalises_ticker_and_text():
    doc = SourceDocument(
        document_id="d1", timestamp="2026-01-15T09:30:00", source="social_media",
        company="  Tesla ", ticker=" tsla ", text="  Deliveries look weak.  ",
    )
    assert doc.ticker == "TSLA"
    assert doc.company == "Tesla"
    assert doc.text == "Deliveries look weak."
    assert doc.timestamp.tzinfo is not None  # naive input is treated as UTC


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_empty_text_is_rejected(text):
    with pytest.raises(ValidationError):
        SourceDocument(document_id="d1", timestamp="2026-01-15T09:30:00Z", source="financial_news", text=text)


def test_invalid_ticker_is_rejected():
    with pytest.raises(ValidationError):
        SourceDocument(document_id="d1", timestamp="2026-01-15T09:30:00Z",
                       source="financial_news", ticker="not a ticker!", text="x")


def test_risk_signal_accepts_valid_payload(signal_payload):
    signal = RiskSignal(**signal_payload)
    assert signal.ticker == "NVDA"
    assert signal.event_type is EventType.GEOPOLITICAL
    assert signal.risk_level is RiskLevel.HIGH
    assert signal.provenance.impact_method == "rule_based_v1"


@pytest.mark.parametrize(
    "field,value",
    [
        ("sentiment_score", 1.5),
        ("sentiment_score", -1.01),
        ("impact_score", 0),
        ("impact_score", 11),
        ("event_confidence", 1.2),
        ("event_type", "Not A Category"),
    ],
)
def test_risk_signal_rejects_out_of_range_values(signal_payload, field, value):
    signal_payload[field] = value
    with pytest.raises(ValidationError):
        RiskSignal(**signal_payload)


def test_portfolio_asset_derives_market_value():
    asset = PortfolioAsset(asset_id="A1", asset_name="Test Equity", asset_type="Equity",
                           ticker="aapl", quantity=100, current_price=190.5)
    assert asset.market_value == 19050.0
    assert asset.asset_type is AssetType.EQUITY
    assert asset.ticker == "AAPL"


def test_portfolio_asset_rejects_inconsistent_market_value():
    with pytest.raises(ValidationError):
        PortfolioAsset(asset_id="A1", asset_name="Bad", asset_type="Equity",
                       quantity=10, current_price=10.0, market_value=500.0)


@pytest.mark.parametrize("kwargs", [
    {"quantity": 0, "current_price": 10.0},
    {"quantity": -5, "current_price": 10.0},
    {"quantity": 5, "current_price": -1.0},
    {"quantity": 5, "current_price": 10.0, "credit_rating": "XYZ"},
])
def test_portfolio_asset_rejects_invalid_values(kwargs):
    with pytest.raises(ValidationError):
        PortfolioAsset(asset_id="A1", asset_name="Bad", asset_type="Corporate Bond", **kwargs)


def test_portfolio_asset_accepts_valid_credit_rating():
    asset = PortfolioAsset(asset_id="B1", asset_name="Bond", asset_type="Corporate Bond",
                           quantity=1000, current_price=98.5, credit_rating="BBB+", duration=4.2)
    assert asset.credit_rating == "BBB+"


@pytest.mark.parametrize("text", ["", "   "])
def test_analyze_request_rejects_empty_text(text):
    with pytest.raises(ValidationError):
        AnalyzeRequest(text=text)


def test_analyze_request_defaults():
    req = AnalyzeRequest(text="Company X announces merger", ticker="x")
    assert req.source.value == "financial_news"
    assert req.persist is True
    assert req.run_stress_test is True


def test_stress_request_requires_a_selector():
    with pytest.raises(ValidationError):
        StressTestRequest()
    assert StressTestRequest(scenario_key="geopolitical").scenario_key == "geopolitical"
    assert StressTestRequest(custom_shocks_pct={"Equity": -12.5}).custom_shocks_pct


def test_stress_request_rejects_impossible_shock():
    with pytest.raises(ValidationError):
        StressTestRequest(custom_shocks_pct={"Equity": -150})