"""Portfolio asset management and allocation summary endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.database import get_db
from app.models.collections import Collections
from app.models.documents import PortfolioAssetRecord
from app.schemas.portfolio import (
    AllocationItem,
    PortfolioAsset,
    PortfolioResponse,
    PortfolioSummary,
)

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


def _build_response(db: Database) -> PortfolioResponse:
    records = list(
        db[Collections.PORTFOLIO_ASSETS].find().sort("asset_id", 1)
    )
    assets = [
        PortfolioAsset.model_validate({k: v for k, v in row.items() if k != "_id"})
        for row in records
    ]

    total = round(sum(asset.market_value or 0 for asset in assets), 2)
    weighted_assets = [
        asset.model_copy(
            update={
                "weight": round((asset.market_value or 0) / total, 6)
                if total > 0
                else 0.0
            }
        )
        for asset in assets
    ]

    grouped: dict = {}
    for asset in weighted_assets:
        entry = grouped.setdefault(
            asset.asset_type,
            {"market_value": 0.0, "asset_count": 0},
        )
        entry["market_value"] += asset.market_value or 0
        entry["asset_count"] += 1

    allocation = [
        AllocationItem(
            asset_type=asset_type,
            market_value=round(values["market_value"], 2),
            weight=round(values["market_value"] / total, 6) if total > 0 else 0.0,
            asset_count=values["asset_count"],
        )
        for asset_type, values in sorted(grouped.items(), key=lambda item: item[0].value)
    ]

    return PortfolioResponse(
        summary=PortfolioSummary(
            total_value=total,
            asset_count=len(weighted_assets),
            allocation=allocation,
        ),
        assets=weighted_assets,
    )


@router.get("", response_model=PortfolioResponse, summary="Get portfolio and allocation")
def get_portfolio(db: Database = Depends(get_db)) -> PortfolioResponse:
    return _build_response(db)


@router.post(
    "",
    response_model=PortfolioAsset,
    status_code=status.HTTP_201_CREATED,
    summary="Add a portfolio asset",
)
def add_asset(
    asset: PortfolioAsset,
    db: Database = Depends(get_db),
) -> PortfolioAsset:
    record = PortfolioAssetRecord.model_validate(asset.model_dump())
    try:
        db[Collections.PORTFOLIO_ASSETS].insert_one(record.to_mongo())
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset '{asset.asset_id}' already exists.",
        ) from exc
    return asset


@router.put(
    "/{asset_id}",
    response_model=PortfolioAsset,
    summary="Replace an existing portfolio asset",
)
def update_asset(
    asset_id: str,
    asset: PortfolioAsset,
    db: Database = Depends(get_db),
) -> PortfolioAsset:
    if asset.asset_id != asset_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Path asset_id must match the asset_id in the request body.",
        )

    record = PortfolioAssetRecord.model_validate(asset.model_dump())
    result = db[Collections.PORTFOLIO_ASSETS].replace_one(
        {"asset_id": asset_id},
        record.to_mongo(),
        upsert=False,
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Portfolio asset not found.")
    return asset


@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a portfolio asset",
)
def delete_asset(asset_id: str, db: Database = Depends(get_db)) -> None:
    result = db[Collections.PORTFOLIO_ASSETS].delete_one({"asset_id": asset_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Portfolio asset not found.")
