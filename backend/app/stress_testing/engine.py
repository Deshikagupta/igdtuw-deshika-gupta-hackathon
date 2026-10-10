"""Deterministic portfolio stress-testing calculations."""

from collections import defaultdict
from typing import Mapping

from app.models.enums import AssetType
from app.schemas.portfolio import PortfolioAsset
from app.schemas.stress import (
    AssetStressResult,
    AssetTypeStressResult,
    ScenarioDefinition,
)


class StressTestingEngine:
    """Apply percentage shocks to portfolio assets."""

    @staticmethod
    def calculate_asset_impact(
        asset: PortfolioAsset,
        shock_pct: float,
    ) -> AssetStressResult:
        """Calculate the before/after value for one asset."""
        if not -100.0 <= shock_pct <= 100.0:
            raise ValueError("shock_pct must be between -100 and 100.")

        value_before = asset.market_value
        value_after = round(
            value_before * (1 + shock_pct / 100.0),
            2,
        )
        absolute_loss = round(value_before - value_after, 2)

        return AssetStressResult(
            asset_id=asset.asset_id,
            asset_name=asset.asset_name,
            asset_type=asset.asset_type,
            ticker=asset.ticker,
            value_before=value_before,
            shock_pct=shock_pct,
            value_after=value_after,
            absolute_loss=absolute_loss,
        )

    def calculate_portfolio_impact(
        self,
        assets: list[PortfolioAsset],
        scenario: ScenarioDefinition,
    ) -> tuple[list[AssetStressResult], list[AssetTypeStressResult]]:
        """Calculate asset-level and asset-type-level impact."""
        asset_results: list[AssetStressResult] = []
        totals: dict[AssetType, dict[str, float]] = defaultdict(
            lambda: {
                "before": 0.0,
                "after": 0.0,
                "loss": 0.0,
            }
        )

        for asset in assets:
            shock_pct = scenario.shocks_pct.get(asset.asset_type, 0.0)
            result = self.calculate_asset_impact(asset, shock_pct)
            asset_results.append(result)

            totals[asset.asset_type]["before"] += result.value_before
            totals[asset.asset_type]["after"] += result.value_after
            totals[asset.asset_type]["loss"] += result.absolute_loss

        type_results: list[AssetTypeStressResult] = []

        for asset_type, values in totals.items():
            before = round(values["before"], 2)
            after = round(values["after"], 2)
            loss = round(before - after, 2)

            # The weighted effective shock reflects the actual impact
            # when assets of the same type have different values.
            effective_shock = (
                (after / before - 1) * 100.0 if before > 0 else 0.0
            )

            type_results.append(
                AssetTypeStressResult(
                    asset_type=asset_type,
                    value_before=before,
                    value_after=after,
                    absolute_loss=loss,
                    shock_pct=round(effective_shock, 4),
                )
            )

        return asset_results, type_results
