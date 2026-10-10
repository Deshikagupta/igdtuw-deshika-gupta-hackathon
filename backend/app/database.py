"""MongoDB connection management, index definitions and the FastAPI DB dependency.

PyMongo connects lazily, so creating the client never fails just because MongoDB is
down. Connectivity problems are detected via `ping()` / `ensure_ready()` and surface
as clear errors (HTTP 503) instead of stack traces.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any, NamedTuple

from fastapi import Request
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database
from pymongo.errors import ConfigurationError as PyMongoConfigurationError
from pymongo.errors import OperationFailure, PyMongoError

from app.config import Settings
from app.exceptions import DatabaseUnavailableError
from app.models.collections import Collections

logger = logging.getLogger(__name__)


class IndexSpec(NamedTuple):
    name: str
    keys: list[tuple[str, int]]
    unique: bool = False


INDEX_SPECS: dict[str, list[IndexSpec]] = {
    Collections.DOCUMENTS: [
        IndexSpec("ux_document_id", [("document_id", ASCENDING)], unique=True),
        IndexSpec("ix_doc_source_ts", [("source", ASCENDING), ("timestamp", DESCENDING)]),
        IndexSpec("ix_doc_ticker_ts", [("ticker", ASCENDING), ("timestamp", DESCENDING)]),
    ],
    Collections.RISK_SIGNALS: [
        IndexSpec("ux_signal_id", [("signal_id", ASCENDING)], unique=True),
        # one signal per document -> re-analysis is an upsert, never a duplicate
        IndexSpec("ux_signal_document_id", [("document_id", ASCENDING)], unique=True),
        IndexSpec("ix_signal_ticker_ts", [("ticker", ASCENDING), ("timestamp", DESCENDING)]),
        IndexSpec("ix_signal_event_impact", [("event_type", ASCENDING), ("impact_score", DESCENDING)]),
        IndexSpec("ix_signal_risk_ts", [("risk_level", ASCENDING), ("timestamp", DESCENDING)]),
        IndexSpec("ix_signal_ts", [("timestamp", DESCENDING)]),
    ],
    Collections.COMPANIES: [
        IndexSpec("ux_company_ticker", [("ticker", ASCENDING)], unique=True),
    ],
    Collections.PORTFOLIO_ASSETS: [
        IndexSpec("ux_asset_id", [("asset_id", ASCENDING)], unique=True),
        IndexSpec("ix_asset_type", [("asset_type", ASCENDING)]),
    ],
    Collections.STRESS_TESTS: [
        # automatic tests use a deterministic id derived from the signal -> idempotent triggering
        IndexSpec("ux_stress_test_id", [("stress_test_id", ASCENDING)], unique=True),
        IndexSpec("ix_stress_signal", [("trigger_signal_id", ASCENDING)]),
        IndexSpec("ix_stress_created", [("created_at", DESCENDING)]),
    ],
}


class MongoManager:
    """Owns the MongoClient, index creation and connectivity checks."""

    def __init__(
        self,
        settings: Settings,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._client_factory = client_factory or self._default_client_factory
        self._client: Any = None
        self._indexes_ready = False
        self._lock = threading.RLock()

    # ---- client / database ------------------------------------------------
    def _default_client_factory(self) -> MongoClient:
        timeout = self._settings.mongodb_timeout_ms
        return MongoClient(
            self._settings.mongodb_uri,
            serverSelectionTimeoutMS=timeout,
            connectTimeoutMS=timeout,
            socketTimeoutMS=max(timeout * 5, 10_000),
            tz_aware=True,
            appname="risk-intelligence-platform",
        )

    @property
    def client(self) -> Any:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = self._client_factory()
        return self._client

    @property
    def db(self) -> Database:
        return self.client[self._settings.database_name]

    @property
    def indexes_ready(self) -> bool:
        return self._indexes_ready

    # ---- connectivity -----------------------------------------------------
    def _describe_failure(self, exc: Exception) -> str:
        if isinstance(exc, PyMongoConfigurationError):
            return "MONGODB_URI is not a valid MongoDB connection string. Check your .env file."
        if isinstance(exc, OperationFailure):
            return (
                "MongoDB rejected the connection (authentication or permission problem). "
                "Check the credentials in MONGODB_URI."
            )
        return (
            f"Cannot reach MongoDB at {self._settings.masked_mongodb_uri} "
            f"(waited {self._settings.mongodb_timeout_ms} ms). "
            "Make sure MongoDB is running, e.g. `docker compose up -d` from the project root."
        )

    def ping(self) -> tuple[bool, str | None]:
        """Return (True, None) if MongoDB answers, else (False, human-readable message)."""
        try:
            self.client.admin.command("ping")
            return True, None
        except PyMongoError as exc:
            logger.warning("MongoDB ping failed: %s: %s", type(exc).__name__, exc)
            return False, self._describe_failure(exc)

    def ensure_ready(self) -> None:
        """Verify connectivity and create indexes once. Raises DatabaseUnavailableError.

        Safe to call repeatedly; retries automatically if MongoDB was down earlier.
        """
        if self._indexes_ready:
            return
        with self._lock:
            if self._indexes_ready:
                return
            try:
                self.client.admin.command("ping")
            except PyMongoError as exc:
                logger.warning("MongoDB unavailable: %s: %s", type(exc).__name__, exc)
                raise DatabaseUnavailableError(self._describe_failure(exc)) from exc
            try:
                self._create_indexes()
            except PyMongoError as exc:
                logger.error("Index creation failed: %s", exc)
                raise DatabaseUnavailableError(f"Could not create MongoDB indexes: {exc}") from exc
            self._indexes_ready = True
            logger.info(
                "MongoDB ready: database '%s' at %s",
                self._settings.database_name,
                self._settings.masked_mongodb_uri,
            )

    def _create_indexes(self) -> None:
        db = self.db
        for collection, specs in INDEX_SPECS.items():
            for spec in specs:
                db[collection].create_index(spec.keys, name=spec.name, unique=spec.unique)

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:  # noqa: BLE001 - closing must never raise
                    logger.debug("Ignoring error while closing MongoDB client", exc_info=True)
            self._client = None
            self._indexes_ready = False


# ---- FastAPI dependencies --------------------------------------------------
def get_mongo(request: Request) -> MongoManager:
    return request.app.state.mongo


def get_db(request: Request) -> Database:
    """Dependency returning the database. Raises 503 (clean JSON) if MongoDB is down."""
    mongo = get_mongo(request)
    mongo.ensure_ready()
    return mongo.db