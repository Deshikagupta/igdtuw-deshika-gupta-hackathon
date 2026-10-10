"""Load and validate stress scenarios from YAML."""

from pathlib import Path
from typing import Any

import yaml

from app.models.enums import AssetType
from app.schemas.stress import ScenarioDefinition


DEFAULT_SCENARIO_PATH = (
    Path(__file__).resolve().parents[2]
    / "config"
    / "scenarios.yaml"
)


class ScenarioLoader:
    """Load validated scenario definitions from a YAML file."""

    def __init__(self, path: Path | str = DEFAULT_SCENARIO_PATH) -> None:
        self.path = Path(path)

    def load_all(self) -> dict[str, ScenarioDefinition]:
        """Return scenarios indexed by their unique keys."""
        if not self.path.is_file():
            raise FileNotFoundError(
                f"Scenario configuration not found: {self.path}"
            )

        with self.path.open("r", encoding="utf-8") as file:
            data: Any = yaml.safe_load(file)

        if not isinstance(data, dict) or not isinstance(
            data.get("scenarios"), list
        ):
            raise ValueError(
                "Scenario configuration must contain a 'scenarios' list."
            )

        scenarios: dict[str, ScenarioDefinition] = {}

        for item in data["scenarios"]:
            if not isinstance(item, dict):
                raise ValueError("Each scenario must be a YAML mapping.")

            raw = dict(item)
            raw_shocks = raw.get("shocks_pct")

            if not isinstance(raw_shocks, dict):
                raise ValueError(
                    f"Scenario {raw.get('key', '<unknown>')} "
                    "must define shocks_pct as a mapping."
                )

            try:
                raw["shocks_pct"] = {
                    AssetType(asset_type): shock
                    for asset_type, shock in raw_shocks.items()
                }
                scenario = ScenarioDefinition.model_validate(raw)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Invalid scenario configuration: {exc}"
                ) from exc

            if scenario.key in scenarios:
                raise ValueError(
                    f"Duplicate scenario key: {scenario.key}"
                )

            scenarios[scenario.key] = scenario

        return scenarios

    def get(self, key: str) -> ScenarioDefinition:
        """Load a scenario by key."""
        scenarios = self.load_all()

        if key not in scenarios:
            available = ", ".join(sorted(scenarios))
            raise KeyError(
                f"Unknown scenario '{key}'. Available scenarios: {available}"
            )

        return scenarios[key]
