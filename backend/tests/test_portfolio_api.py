"""Tests for portfolio CRUD and summary endpoints."""

from app.models.collections import Collections


def asset_payload(asset_id="asset-1", **overrides):
    payload = {
        "asset_id": asset_id,
        "asset_name": "Example Equity",
        "asset_type": "Equity",
        "ticker": "EXM",
        "quantity": 10,
        "current_price": 100,
    }
    payload.update(overrides)
    return payload


def test_add_and_get_portfolio(client):
    response = client.post("/api/portfolio", json=asset_payload())
    assert response.status_code == 201
    assert response.json()["market_value"] == 1000

    response = client.get("/api/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_value"] == 1000
    assert data["summary"]["asset_count"] == 1
    assert data["assets"][0]["weight"] == 1.0
    assert data["summary"]["allocation"][0]["asset_count"] == 1


def test_duplicate_asset_returns_409(client):
    client.post("/api/portfolio", json=asset_payload())
    response = client.post("/api/portfolio", json=asset_payload())
    assert response.status_code == 409


def test_update_asset(client):
    client.post("/api/portfolio", json=asset_payload())
    response = client.put(
        "/api/portfolio/asset-1",
        json=asset_payload(quantity=5, current_price=200),
    )
    assert response.status_code == 200
    assert response.json()["market_value"] == 1000

    portfolio = client.get("/api/portfolio").json()
    assert portfolio["summary"]["asset_count"] == 1
    assert portfolio["summary"]["total_value"] == 1000


def test_update_requires_matching_id(client):
    response = client.put(
        "/api/portfolio/asset-1",
        json=asset_payload(asset_id="asset-2"),
    )
    assert response.status_code == 422


def test_update_missing_asset_returns_404(client):
    response = client.put(
        "/api/portfolio/missing",
        json=asset_payload(asset_id="missing"),
    )
    assert response.status_code == 404


def test_delete_asset(client):
    client.post("/api/portfolio", json=asset_payload())
    response = client.delete("/api/portfolio/asset-1")
    assert response.status_code == 204
    assert client.get("/api/portfolio").json()["summary"]["asset_count"] == 0


def test_delete_missing_asset_returns_404(client):
    assert client.delete("/api/portfolio/missing").status_code == 404


def test_portfolio_weights_across_asset_types(client):
    client.post("/api/portfolio", json=asset_payload())
    client.post(
        "/api/portfolio",
        json=asset_payload(
            asset_id="bond-1",
            asset_name="Example Bond",
            asset_type="Corporate Bond",
            ticker=None,
            quantity=5,
            current_price=200,
        ),
    )

    data = client.get("/api/portfolio").json()
    assert data["summary"]["total_value"] == 2000
    assert data["summary"]["asset_count"] == 2
    assert sum(item["weight"] for item in data["assets"]) == 1
    assert len(data["summary"]["allocation"]) == 2
