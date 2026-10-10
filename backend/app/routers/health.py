"""GET /health: liveness plus dependency status.

Always returns HTTP 200 while the process is up. `status` is "degraded" when MongoDB
is unreachable. It never loads NLP models, so it works before any model is downloaded.
"""

from fastapi import APIRouter, Request

from app.schemas.health import ComponentStatus, HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health_check(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    mongo = request.app.state.mongo

    db_ok, db_error = mongo.ping()
    if db_ok:
        index_state = "ready" if mongo.indexes_ready else "pending (created on first database request)"
        database = ComponentStatus(
            status="ok",
            detail=f"Connected to database '{settings.database_name}'; indexes {index_state}.",
        )
    else:
        database = ComponentStatus(status="unavailable", detail=db_error)

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        database=database,
        nlp=request.app.state.nlp_status,
    )