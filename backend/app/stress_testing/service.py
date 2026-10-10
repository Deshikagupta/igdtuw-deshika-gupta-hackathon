"""Orchestrate portfolio stress tests and optional persistence."""

from hashlib import sha256
from uuid import uuid4

from pymongo.database import Database

from app.models.collections import Collections
from app.models.documents import (
    PortfolioAssetRecord,
    RiskSignalRecord,
    StressTestRecord,
)
from app.models.enums import StressMode
from app.schemas.risk_signal import RiskSignal
from app.schemas.stress import (
    ScenarioDefinition,
    StressTestRequest,
    StressTestResult,
)
from app.stress_testing.engine import StressTestingEngine
from app.stress_testing.scenarios import ScenarioLoader
from app.stress_testing.triggers import evaluate_trigger


class StressTestingService:
    """Load portfolio data, evaluate scenarios, and save stress-test results."""

    def __init__(
        self,
        scenario_loader: ScenarioLoader | None = None,
        engine: StressTestingEngine | None = None,
    ) -> None:
        self.scenario_loader = scenario_loader or ScenarioLoader()
        self.engine = engine or StressTestingEngine()

    def run(
        self,
        request: StressTestRequest,
        db: Database,
        persist: bool = True,
    ) -> StressTestResult:
        scenarios = self.scenario_loader.load_all()

        signal = self._get_signal(request.signal_id, db) if request.signal_id else None

        # Signal-driven requests must match a configured trigger.
        if signal is not None:
            trigger = evaluate_trigger(signal, scenarios)
            if not trigger.triggered or not trigger.scenario_key:
                raise ValueError(
                    f"Risk signal did not trigger a stress test: {trigger.reason}"
                )

            if request.scenario_key and request.scenario_key != trigger.scenario_key:
                raise ValueError(
                    "scenario_key conflicts with the scenario selected by the risk signal."
                )

            scenario = scenarios[trigger.scenario_key]
            mode = StressMode.AUTOMATIC
            trigger_reason = trigger.reason
        else:
            if not request.scenario_key:
                raise ValueError(
                    "Manual stress tests require scenario_key unless a triggering signal is provided."
                )

            try:
                scenario = scenarios[request.scenario_key]
            except KeyError as exc:
                raise ValueError(
                    f"Unknown scenario_key: {request.scenario_key}"
                ) from exc

            mode = StressMode.MANUAL
            trigger_reason = "Scenario selected manually."

        # Custom shocks override configured shocks for the specified asset types.
        if request.custom_shocks_pct:
            scenario = scenario.model_copy(
                update={
                    "shocks_pct": {
                        **scenario.shocks_pct,
                        **request.custom_shocks_pct,
                    }
                }
            )
            if mode == StressMode.MANUAL:
                trigger_reason += " Custom shocks were applied."

        assets = [
            PortfolioAssetRecord.from_mongo(record)
            for record in db[Collections.PORTFOLIO_ASSETS].find({})
        ]

        if not assets:
            raise ValueError(
                "Cannot run a stress test because the portfolio contains no assets."
            )

        asset_results, type_results = self.engine.calculate_portfolio_impact(
            assets,
            scenario,
        )

        portfolio_before = round(sum(item.value_before for item in asset_results), 2)
        portfolio_after = round(sum(item.value_after for item in asset_results), 2)
        absolute_loss = round(portfolio_before - portfolio_after, 2)
        percentage_loss = (
            round(absolute_loss / portfolio_before * 100.0, 4)
            if portfolio_before > 0
            else 0.0
        )

        # A signal-driven test gets a deterministic ID so retries are idempotent.
        if mode == StressMode.AUTOMATIC and signal is not None:
            digest = sha256(signal.signal_id.encode("utf-8")).hexdigest()[:24]
            stress_test_id = f"stress-auto-{digest}"
        else:
            stress_test_id = f"stress-manual-{uuid4().hex}"

        result = StressTestResult(
            stress_test_id=stress_test_id,
            mode=mode,
            scenario_key=scenario.key,
            scenario_name=scenario.name,
            scenario_description=scenario.description,
            trigger_event_type=signal.event_type if signal else None,
            trigger_impact_score=signal.impact_score if signal else None,
            trigger_signal_id=signal.signal_id if signal else None,
            trigger_company=signal.company if signal else None,
            trigger_ticker=signal.ticker if signal else None,
            trigger_reason=trigger_reason,
            shocks_pct=scenario.shocks_pct,
            portfolio_before=portfolio_before,
            portfolio_after=portfolio_after,
            absolute_loss=absolute_loss,
            percentage_loss=percentage_loss,
            asset_level_results=asset_results,
            asset_type_results=type_results,
        )

        if persist:
            record = StressTestRecord.model_validate(result.model_dump())
            db[Collections.STRESS_TESTS].update_one(
                {"stress_test_id": stress_test_id},
                {"$setOnInsert": record.to_mongo()},
                upsert=True,
            )

        return result

    @staticmethod
    def _get_signal(signal_id: str, db: Database) -> RiskSignal:
        record = db[Collections.RISK_SIGNALS].find_one(
            {"signal_id": signal_id}
        )
        if record is None:
            raise ValueError(f"Risk signal not found: {signal_id}")

        return RiskSignalRecord.from_mongo(record)

