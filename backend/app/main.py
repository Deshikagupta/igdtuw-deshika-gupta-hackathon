"""FastAPI application factory.

Run with:  python -m app          (uses BACKEND_HOST / BACKEND_PORT)
      or:  uvicorn app.main:create_app --factory --reload
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import Settings, get_settings
from app.database import MongoManager
from app.error_handlers import register_exception_handlers
from app.exceptions import DatabaseUnavailableError
from app.logging_config import configure_logging
from app.routers import analyze, health, ingestion, portfolio, stress
from app.schemas.health import ComponentStatus

logger = logging.getLogger(__name__)

API_DESCRIPTION = (
    "AI/NLP risk engine that turns unstructured financial text into structured risk "
    "signals and drives portfolio stress tests. All data is synthetic; impact scores "
    "and stress shocks are illustrative prototypes, not market forecasts."
)


def create_app(settings: Settings | None = None, mongo: MongoManager | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    mongo_manager = mongo or MongoManager(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Starting %s v%s (%s)", settings.app_name, settings.app_version, settings.environment)
        try:
            await asyncio.to_thread(mongo_manager.ensure_ready)
        except DatabaseUnavailableError as exc:
            # The API still starts; /health reports "degraded" and DB endpoints return 503.
            logger.warning("Starting without a database connection: %s", exc.detail)
        yield
        mongo_manager.close()
        logger.info("Shutdown complete")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        lifespan=lifespan,
    )

    # Shared state used by routers/dependencies.
    app.state.settings = settings
    app.state.mongo = mongo_manager
    # Updated by the NLP layer once models are loaded (Phase 4); /health only reads it.
    app.state.nlp_status = ComponentStatus(
        status="not_initialized",
        detail="NLP models are loaded lazily on first use; none are required for this endpoint.",
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info("%s %s -> %d (%.1f ms)", request.method, request.url.path, response.status_code, elapsed_ms)
        return response

    # Added last so it is the outermost middleware (CORS headers also on error responses).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(ingestion.router)
    app.include_router(analyze.router)
    app.include_router(stress.router)
    app.include_router(portfolio.router)
    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app

app = create_app()
