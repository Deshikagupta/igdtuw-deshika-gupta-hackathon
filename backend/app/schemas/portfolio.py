"""Portfolio assets and summaries."""

from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import AssetType
from app.schemas.common import OptionalTicker

_RATING_PATTERN = r"^(AAA|AA|A|BBB|BB|B|CCC|CC|C|D|NR)[+-]?$"


class PortfolioAsset(BaseModel):
    asset_id: str = Field(min_length=1, max_length=50)
    asset_name: str = Field(min_length=1, max_length=150)
    asset_type: AssetType
    ticker: OptionalTicker = None
    sector: str | None = None
    quantity: float = Field(gt=0, description="Units / contracts / notional units held")
    current_price: float = Field(ge=0, description="Price per unit (USD, synthetic)")
    market_value: float | None = Field(
        default=None,
        ge=0,
        description="quantity x current_price. Always set after validation.",
    )
    weight: float | None = Field(default=None, ge=0, le=1, description="Share of portfolio value")
    duration: float | None = Field(default=None, ge=0, description="Years; bonds/loans only")
    credit_rating: str | None = Field(default=None, pattern=_RATING_PATTERN)

    @model_validator(mode="after")
    def _derive_and_check_market_value(self) -> Self:
        expected = round(self.quantity * self.current_price, 2)
        if self.market_value is None:
            self.market_value = expected
        elif abs(self.market_value - expected) > max(0.01, 0.01 * expected):
            raise ValueError(
                f"market_value {self.market_value} is inconsistent with "
                f"quantity x current_price = {expected}"
            )
        return self


class AllocationItem(BaseModel):
    asset_type: AssetType
    market_value: float = Field(ge=0)
    weight: float = Field(ge=0, le=1)
    asset_count: int = Field(ge=0)


class PortfolioSummary(BaseModel):
    total_value: float = Field(ge=0)
    asset_count: int = Field(ge=0)
    allocation: list[AllocationItem] = Field(default_factory=list)


class PortfolioResponse(BaseModel):
    summary: PortfolioSummary
    assets: list[PortfolioAsset]