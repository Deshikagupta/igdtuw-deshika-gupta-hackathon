
"""Tests for the stress-testing orchestration service."""

from datetime import datetime, timezone

import mongomock
import pytest

from app.models.collections import Collections
from app.models.enums import AssetType, EventType, SourceType
from app.schemas.portfolio import PortfolioAsset
from app.schemas.risk_signal import RiskSignal
from app.schemas.stress import StressTestRequest
from app.stress_testing.service import StressTestingService


@pytest.fixture
def db():
    return mongomock.MongoClient().risk_platform


@pytest.fixture
def service():
    return StressTestingService()


@pytest.fixture
def portfolio(db):
    assets = [
        PortfolioAsset(
            asset_id="asset-aapl",
            asset_name="Apple Inc.",
            asset_type=AssetType.EQUITY,
            ticker="AAPL",
            quantity=10,
            current_price=100,
        ),
        PortfolioAsset(
            asset_id="asset-bond",
            asset_name="Illustrative Corporate Bond",
            asset_type=AssetType.CORPORATE_BOND,
            quantity=20,
            current_price=50,
        ),
    ]
    db[Collections.PORTFOLIO_ASSETS].insert_many(
        [asset.model_dump(mode="json") for asset in assets]
    )
    return assets


def insert_signal(db, event_type, impact_score):
    signal = RiskSignal(
        signal_id="sig-test-geopolitical",
        document_id="doc-test-geopolitical",
        company="Example Corp",
        ticker="AAPL",
        source=SourceType.FINANCIAL_NEWS,
        text="Illustrative market event.",
        timestamp=datetime.now(timezone.utc),
        sentiment_score=-0.8,
        sentiment_label="negative",
        event_type=event_type,
        event_confidence=0.95,
        impact_score=impact_score,
        risk_level="HIGH",
        confidence=0.9,
        matched_keywords=["geopolitical"],
    )
    db[Collections.RISK_SIGNALS].insert_one(signal.model_dump(mode="json"))
    return signal


def test_manual_stress_test_calculates_portfolio_impact(
    db, service, portfolio
):
    result = service.run(
        StressTestRequest(scenario_key="equity_downturn"),
        db,
        persist=False,
    )

    assert result.mode.value == "manual"
    assert result.scenario_key == "equity_downturn"
    assert result.portfolio_before == 2000.0
    assert result.portfolio_after != result.portfolio_before
    assert len(result.asset_level_results) == 2
    assert result.absolute_loss == pytest.approx(
        result.portfolio_before - result.portfolio_after
    )


def test_automatic_stress_test_uses_triggered_scenario(
    db, service, portfolio
):
    insert_signal(db, EventType.GEOPOLITICAL, 9)

    result = service.run(
        StressTestRequest(signal_id="sig-test-geopolitical"),
        db,
        persist=False,
    )

    assert result.mode.value == "automatic"
    assert result.scenario_key == "geopolitical_disruption"
    assert result.trigger_signal_id == "sig-test-geopolitical"
    assert result.trigger_impact_score == 9


def test_custom_shock_overrides_configured_shock(
    db, service, portfolio
):
    result = service.run(
        StressTestRequest(
            scenario_key="equity_downturn",
            custom_shocks_pct={AssetType.EQUITY: -30.0},
        ),
        db,
        persist=False,
    )

    equity_result = next(
        item
        for item in result.asset_level_results
        if item.asset_type == AssetType.EQUITY
    )
    assert equity_result.shock_pct == -30.0
    assert equity_result.value_after == 700.0


def test_persisted_manual_test_is_saved(db, service, portfolio):
    result = service.run(
        StressTestRequest(scenario_key="equity_downturn"),
        db,
        persist=True,
    )

    saved = db[Collections.STRESS_TESTS].find_one(
        {"stress_test_id": result.stress_test_id}
    )
    assert saved is not None
    assert saved["scenario_key"] == "equity_downturn"


def test_empty_portfolio_is_rejected(db, service):
    with pytest.raises(ValueError, match="portfolio contains no assets"):
        service.run(
            StressTestRequest(scenario_key="equity_downturn"),
            db,
            persist=False,
        )


def test_unknown_scenario_is_rejected(db, service, portfolio):
    with pytest.raises(ValueError, match="Unknown scenario_key"):
        service.run(
            StressTestRequest(scenario_key="unknown_scenario"),
            db,
            persist=False,
        )


def test_non_triggering_signal_is_rejected(db, service, portfolio):
    insert_signal(db, EventType.GEOPOLITICAL, 5)

    with pytest.raises(ValueError, match="did not trigger"):
        service.run(
            StressTestRequest(signal_id="sig-test-geopolitical"),
            db,
            persist=False,
        )
