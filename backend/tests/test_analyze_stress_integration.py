
"""Integration tests for automatic stress testing through /api/analyze."""

from app.models.collections import Collections
from app.models.enums import AssetType


def insert_test_portfolio(db):
    """Insert a small synthetic portfolio into the test database."""
    db[Collections.PORTFOLIO_ASSETS].insert_many(
        [
            {
                "asset_id": "test-equity",
                "asset_name": "Synthetic Equity",
                "asset_type": AssetType.EQUITY.value,
                "ticker": "TEST",
                "quantity": 10,
                "current_price": 100,
                "market_value": 1000,
            },
            {
                "asset_id": "test-bond",
                "asset_name": "Synthetic Corporate Bond",
                "asset_type": AssetType.CORPORATE_BOND.value,
                "quantity": 20,
                "current_price": 50,
                "market_value": 1000,
            },
        ]
    )


def test_analyze_skips_stress_test_when_disabled(client):
    response = client.post(
        "/api/analyze",
        json={
            "text": "The company reported routine quarterly results.",
            "company": "Example Corp",
            "ticker": "EXM",
            "persist": False,
            "run_stress_test": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["trigger"] is None
    assert body["stress_test"] is None


def test_analyze_skips_stress_test_when_persistence_is_disabled(client):
    response = client.post(
        "/api/analyze",
        json={
            "text": (
                "Geopolitical tensions escalated after new sanctions "
                "and export restrictions threatened global markets."
            ),
            "company": "Example Corp",
            "ticker": "EXM",
            "persist": False,
            "run_stress_test": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stress_test"] is None
    assert body["trigger"] is None


def test_analyze_runs_stress_test_for_triggering_signal(client, app):
    db = app.state.mongo.db
    insert_test_portfolio(db)

    response = client.post(
        "/api/analyze",
        json={
            "text": (
                "Geopolitical conflict escalated as new sanctions "
                "and export restrictions threatened global markets."
            ),
            "company": "Example Corp",
            "ticker": "EXM",
            "source": "financial_news",
            "persist": True,
            "run_stress_test": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["signal"] is not None
    assert body["trigger"] is not None
    assert body["trigger"]["triggered"] is True
    assert body["stress_test"] is not None
    assert body["stress_test"]["mode"] == "automatic"
    assert body["stress_test"]["trigger_signal_id"] == (
        body["signal"]["signal_id"]
    )

    saved = db[Collections.STRESS_TESTS].find_one(
        {"stress_test_id": body["stress_test"]["stress_test_id"]}
    )
    assert saved is not None


def test_analyze_returns_trigger_without_stress_test_for_nontriggering_signal(
    client, app
):
    response = client.post(
        "/api/analyze",
        json={
            "text": "The company announced its routine quarterly meeting.",
            "company": "Example Corp",
            "ticker": "EXM",
            "persist": True,
            "run_stress_test": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["trigger"] is not None
    assert body["trigger"]["triggered"] is False
    assert body["stress_test"] is None


def test_analyze_rejects_triggered_stress_test_with_empty_portfolio(
    client, app
):
    response = client.post(
        "/api/analyze",
        json={
            "text": (
                "Geopolitical conflict escalated as new sanctions "
                "and export restrictions threatened global markets."
            ),
            "company": "Example Corp",
            "ticker": "EXM",
            "persist": True,
            "run_stress_test": True,
        },
    )

    assert response.status_code == 422
    assert "portfolio contains no assets" in response.json()["detail"]

