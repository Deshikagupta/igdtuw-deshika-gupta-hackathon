"""Tests for YAML scenario loading."""

import pytest

from app.models.enums import AssetType
from app.stress_testing.scenarios import ScenarioLoader


def test_loads_all_configured_scenarios():
    scenarios = ScenarioLoader().load_all()

    assert len(scenarios) == 4
    assert "equity_downturn" in scenarios
    assert "credit_deterioration" in scenarios
    assert "macroeconomic_shock" in scenarios
    assert "geopolitical_disruption" in scenarios


def test_converts_asset_types_and_shocks():
    scenario = ScenarioLoader().get("equity_downturn")

    assert scenario.shocks_pct[AssetType.EQUITY] == -15.0
    assert scenario.shocks_pct[AssetType.GOVERNMENT_BOND] == 2.0


def test_unknown_scenario_raises_key_error():
    with pytest.raises(KeyError, match="Unknown scenario"):
        ScenarioLoader().get("does_not_exist")


def test_missing_file_raises_error(tmp_path):
    loader = ScenarioLoader(tmp_path / "missing.yaml")

    with pytest.raises(FileNotFoundError):
        loader.load_all()
