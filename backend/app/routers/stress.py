
"""API endpoints for portfolio stress testing."""

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database

from app.database import get_db
from app.schemas.stress import StressTestRequest, StressTestResult
from app.stress_testing.service import StressTestingService

router = APIRouter(prefix="/api", tags=["Stress Testing"])


@router.post(
    "/stress-test",
    response_model=StressTestResult,
    summary="Run a manual or signal-triggered portfolio stress test",
)
def run_stress_test(
    request: StressTestRequest,
    db: Database = Depends(get_db),
) -> StressTestResult:
    """Calculate portfolio impact for a configured stress scenario."""
    try:
        return StressTestingService().run(request, db=db, persist=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
