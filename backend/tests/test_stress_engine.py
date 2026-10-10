"""Tests for portfolio stress calculations."""

import pytest

from app.models.enums import AssetType, EventType
from app.schemas.portfolio import PortfolioAsset
from app.schemas.stress import ScenarioDefinition
from app.stress_testing.engine import StressTestingEngine


@pytest.fixture
def engine():
    return StressTestingEngine()


@pytest.fixture
def equity():
    return PortfolioAsset(
        asset_id="asset-1",
        asset_name="Apple shares",
        asset_type=AssetType.EQUITY,
        ticker="AAPL",
        quantity=10,
        current_price=100,
    )


def test_negative_shock_calculates_loss(engine, equity):
    result = engine.calculate_asset_impact(equity, -10.0)

    assert result.value_before == 1000.0
    assert result.value_after == 900.0
    assert result.absolute_loss == 100.0


def test_positive_shock_calculates_gain(engine, equity):
    result = engine.calculate_asset_impact(equity, 5.0)

    assert result.value_after == 1050.0
    assert result.absolute_loss == -50.0


def test_invalid_shock_is_rejected(engine, equity):
    with pytest.raises(ValueError):
        engine.calculate_asset_impact(equity, -101.0)


def test_portfolio_impact_aggregates_assets(engine, equity):
    second_asset = PortfolioAsset(
        asset_id="asset-2",
        asset_name="Microsoft shares",
        asset_type=AssetType.EQUITY,
        ticker="MSFT",
        quantity=5,
        current_price=200,
    )
    scenario = ScenarioDefinition(
        key="equity_downturn",
        name="Equity downturn",
        shocks_pct={AssetType.EQUITY: -10.0},
        trigger_event_types=[EventType.MACROECONOMIC],
        impact_threshold=8,
    )

    asset_results, type_results = engine.calculate_portfolio_impact(
        [equity, second_asset],
        scenario,
    )

    assert len(asset_results) == 2
    assert len(type_results) == 1
    assert type_results[0].value_before == 2000.0
    assert type_results[0].value_after == 1800.0
    assert type_results[0].absolute_loss == 200.0
    assert type_results[0].shock_pct == -10.0


def test_unconfigured_asset_type_receives_zero_shock(engine, equity):
    scenario = ScenarioDefinition(
        key="bond_shock",
        name="Bond-only shock",
        shocks_pct={AssetType.GOVERNMENT_BOND: -5.0},
    )

    asset_results, _ = engine.calculate_portfolio_impact([equity], scenario)

    assert asset_results[0].value_after == 1000.0
    assert asset_results[0].absolute_loss == 0.0
