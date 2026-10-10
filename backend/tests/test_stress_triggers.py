"""Tests for risk-signal stress triggers."""

from datetime import datetime, timezone

from app.models.enums import (
    EventType,
    RiskLevel,
    SentimentLabel,
    SourceType,
)
from app.schemas.risk_signal import RiskSignal
from app.stress_testing.scenarios import ScenarioLoader
from app.stress_testing.triggers import evaluate_trigger


def make_signal(event_type, impact_score):
    return RiskSignal(
        signal_id="sig-test",
        document_id="doc-test",
        source=SourceType.FINANCIAL_NEWS,
        text="Illustrative financial market event.",
        timestamp=datetime.now(timezone.utc),
        sentiment_score=-0.5,
        sentiment_label=SentimentLabel.NEGATIVE,
        event_type=event_type,
        event_confidence=0.9,
        impact_score=impact_score,
        risk_level=RiskLevel.HIGH,
        confidence=0.9,
    )


def test_high_impact_geopolitical_signal_triggers():
    scenarios = ScenarioLoader().load_all()
    signal = make_signal(EventType.GEOPOLITICAL, 9)

    result = evaluate_trigger(signal, scenarios)

    assert result.triggered is True
    assert result.scenario_key == "geopolitical_disruption"
    assert result.threshold == 7


def test_low_impact_signal_does_not_trigger():
    scenarios = ScenarioLoader().load_all()
    signal = make_signal(EventType.GEOPOLITICAL, 5)

    result = evaluate_trigger(signal, scenarios)

    assert result.triggered is False
    assert result.scenario_key is None


def test_unconfigured_event_type_does_not_trigger():
    scenarios = ScenarioLoader().load_all()
    signal = make_signal(EventType.LEGAL, 10)

    result = evaluate_trigger(signal, scenarios)

    assert result.triggered is False
    assert result.scenario_key is None


def test_scenario_selection_uses_configured_priority():
    scenarios = ScenarioLoader().load_all()
    signal = make_signal(EventType.GEOPOLITICAL, 9)

    # Both scenarios match; the lower configured priority number wins.
    scenarios["geopolitical_disruption"] = (
        scenarios["geopolitical_disruption"].model_copy(
            update={"priority": 30}
        )
    )
    scenarios["macroeconomic_shock"] = (
        scenarios["macroeconomic_shock"].model_copy(
            update={"priority": 10}
        )
    )

    result = evaluate_trigger(signal, scenarios)

    assert result.triggered is True
    assert result.scenario_key == "macroeconomic_shock"
    assert result.threshold == 8


def test_equal_priorities_use_scenario_key_as_tiebreaker():
    scenarios = ScenarioLoader().load_all()
    signal = make_signal(EventType.GEOPOLITICAL, 9)

    scenarios["geopolitical_disruption"] = (
        scenarios["geopolitical_disruption"].model_copy(
            update={"priority": 10}
        )
    )
    scenarios["macroeconomic_shock"] = (
        scenarios["macroeconomic_shock"].model_copy(
            update={"priority": 10}
        )
    )

    result = evaluate_trigger(signal, scenarios)

    assert result.scenario_key == "geopolitical_disruption"
