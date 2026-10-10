import pytest
from pymongo.errors import DuplicateKeyError

from app.database import INDEX_SPECS
from app.exceptions import DatabaseUnavailableError
from app.models.collections import Collections


def test_ensure_ready_creates_every_declared_index(mongo):
    mongo.ensure_ready()
    assert mongo.indexes_ready
    assert set(INDEX_SPECS) == set(Collections.ALL)
    for collection, specs in INDEX_SPECS.items():
        existing = mongo.db[collection].index_information()
        for spec in specs:
            assert spec.name in existing, f"{collection}.{spec.name} missing"


def test_ensure_ready_is_idempotent(mongo):
    mongo.ensure_ready()
    mongo.ensure_ready()
    assert mongo.indexes_ready


def test_unique_index_allows_only_one_signal_per_document(mongo):
    mongo.ensure_ready()
    signals = mongo.db[Collections.RISK_SIGNALS]
    signals.insert_one({"signal_id": "s1", "document_id": "d1"})
    with pytest.raises(DuplicateKeyError):
        signals.insert_one({"signal_id": "s2", "document_id": "d1"})


def test_ping_succeeds_when_database_is_up(mongo):
    assert mongo.ping() == (True, None)


def test_ping_reports_clear_message_when_database_is_down(down_mongo):
    ok, message = down_mongo.ping()
    assert ok is False
    assert "Cannot reach MongoDB" in message
    assert "docker compose up -d" in message


def test_error_message_never_leaks_credentials(down_mongo):
    _, message = down_mongo.ping()
    assert "secret" not in message
    assert "user:" not in message


def test_ensure_ready_raises_503_error_when_database_is_down(down_mongo):
    with pytest.raises(DatabaseUnavailableError) as excinfo:
        down_mongo.ensure_ready()
    assert excinfo.value.status_code == 503
    assert not down_mongo.indexes_ready


def test_close_resets_state(mongo):
    mongo.ensure_ready()
    mongo.close()
    assert not mongo.indexes_ready