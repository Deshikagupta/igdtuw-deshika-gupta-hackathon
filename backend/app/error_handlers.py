"""Exception handlers: every error becomes a clean JSON body, never a raw stack trace."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pymongo.errors import ConnectionFailure, PyMongoError

from app.exceptions import AppError
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def _json(status_code: int, detail: str, error_code: str) -> JSONResponse:
    body = ErrorResponse(detail=detail, error_code=error_code)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.warning("%s %s -> %s: %s", request.method, request.url.path, exc.error_code, exc.detail)
        return _json(exc.status_code, exc.detail, exc.error_code)

    @app.exception_handler(ConnectionFailure)
    async def handle_db_connection(request: Request, exc: ConnectionFailure) -> JSONResponse:
        logger.warning("Database connection failure on %s: %s", request.url.path, exc)
        return _json(
            503,
            "The database is unavailable or the connection was lost. "
            "Check that MongoDB is running and try again.",
            "database_unavailable",
        )

    @app.exception_handler(PyMongoError)
    async def handle_db_error(request: Request, exc: PyMongoError) -> JSONResponse:
        logger.error("Database error on %s: %s", request.url.path, exc, exc_info=True)
        return _json(500, "A database operation failed.", "database_error")

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=True)
        return _json(500, "Internal server error.", "internal_error")