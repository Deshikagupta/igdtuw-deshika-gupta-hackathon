"""Application-level exceptions.

`AppError` subclasses carry an HTTP status code and a stable machine-readable
`error_code`; `error_handlers.py` turns them into clean JSON responses.
"""


class ConfigurationError(RuntimeError):
    """Raised at startup when environment configuration is invalid."""


class AppError(Exception):
    """Base class for errors that map to an HTTP response."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BadRequestError(AppError):
    status_code = 400
    error_code = "bad_request"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class DatabaseUnavailableError(AppError):
    status_code = 503
    error_code = "database_unavailable"


class NlpUnavailableError(AppError):
    status_code = 503
    error_code = "nlp_unavailable"