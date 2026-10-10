"""Evaluate whether a risk signal triggers a configured scenario."""

from app.schemas.risk_signal import RiskSignal
from app.schemas.stress import ScenarioDefinition, StressTrigger


def evaluate_trigger(
    signal: RiskSignal,
    scenarios: dict[str, ScenarioDefinition],
) -> StressTrigger:
    """Select the first matching scenario by configured impact threshold."""
    eligible = [
        scenario
        for scenario in scenarios.values()
        if signal.event_type in scenario.trigger_event_types
        and signal.impact_score >= scenario.impact_threshold
    ]

    if not eligible:
        return StressTrigger(
            triggered=False,
            event_type=signal.event_type,
            impact_score=signal.impact_score,
            threshold=min(
                (
                    scenario.impact_threshold
                    for scenario in scenarios.values()
                    if signal.event_type in scenario.trigger_event_types
                ),
                default=1,
            ),
            reason=(
                "No configured scenario matched both the event type "
                "and impact threshold."
            ),
        )

    # Lower priority values win; scenario key breaks ties deterministically.
    scenario = min(
        eligible,
        key=lambda candidate: (candidate.priority, candidate.key),
    )

    return StressTrigger(
        triggered=True,
        scenario_key=scenario.key,
        event_type=signal.event_type,
        impact_score=signal.impact_score,
        threshold=scenario.impact_threshold,
        reason=(
            f"Event type '{signal.event_type.value}' matches scenario "
            f"'{scenario.key}' and impact score {signal.impact_score} "
            f"meets threshold {scenario.impact_threshold}."
        ),
    )
