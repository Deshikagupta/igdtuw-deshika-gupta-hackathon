"""Shared fixtures. Tests use mongomock, so no MongoDB server is required."""

from types import SimpleNamespace

import mongomock
import pytest
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from app.config import Settings
from app.database import MongoManager
from app.main import create_app

SECRET_URI = "mongodb://user:secret@localhost:27017"


class DownClient:
    """Stand-in for a MongoClient whose server is unreachable."""

    def __init__(self) -> None:
        self.admin = SimpleNamespace(command=self._fail)

    @staticmethod
    def _fail(*args, **kwargs):
        raise ServerSelectionTimeoutError("localhost:27017: connection refused")

    def __getitem__(self, name):
        raise ServerSelectionTimeoutError("localhost:27017: connection refused")

    def close(self) -> None:
        pass


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        mongodb_uri="mongodb://localhost:27017",
        database_name="risk_intelligence_test",
        frontend_url="http://localhost:5173",
    )


@pytest.fixture
def mongo(settings) -> MongoManager:
    return MongoManager(settings, client_factory=lambda: mongomock.MongoClient(tz_aware=True))


@pytest.fixture
def down_mongo(settings) -> MongoManager:
    down_settings = settings.model_copy(update={"mongodb_uri": SECRET_URI})
    return MongoManager(down_settings, client_factory=DownClient)


@pytest.fixture
def app(settings, mongo):
    return create_app(settings=settings, mongo=mongo)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def down_app(settings, down_mongo):
    return create_app(settings=settings, mongo=down_mongo)


@pytest.fixture
def signal_payload() -> dict:
    return {
        "signal_id": "sig-001",
        "document_id": "doc-001",
        "company": "NVIDIA",
        "ticker": "nvda",
        "source": "financial_news",
        "text": "Synthetic headline: new export restrictions threaten chip shipments.",
        "timestamp": "2026-01-15T09:30:00Z",
        "sentiment_score": -0.74,
        "sentiment_label": "negative",
        "event_type": "Geopolitical",
        "event_confidence": 0.81,
        "impact_score": 8,
        "risk_level": "HIGH",
        "confidence": 0.87,
    }