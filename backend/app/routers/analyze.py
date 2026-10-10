
"""Endpoint for analyzing financial text."""

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.database import get_db
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.services.analysis import AnalysisService

router = APIRouter(prefix="/api", tags=["Risk Analysis"])


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyze financial text and generate a risk signal",
)
def analyze_text(
    request: AnalyzeRequest,
    db: Database = Depends(get_db),
) -> AnalyzeResponse:
    """Generate a risk signal and optionally save it to MongoDB."""
    try:
        return AnalysisService().analyze(
            request,
            db=db if request.persist else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc