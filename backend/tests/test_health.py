def test_health_ok_with_database_up(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Risk Intelligence Platform API"
    assert body["environment"] == "test"
    assert body["database"]["status"] == "ok"
    assert "risk_intelligence_test" in body["database"]["detail"]


def test_health_does_not_require_nlp_models(client):
    body = client.get("/health").json()
    assert body["nlp"]["status"] == "not_initialized"


def test_health_is_degraded_but_still_200_when_database_is_down(down_app):
    from fastapi.testclient import TestClient

    with TestClient(down_app) as test_client:
        response = test_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"]["status"] == "unavailable"
    assert "Cannot reach MongoDB" in body["database"]["detail"]
    assert "secret" not in response.text


def test_cors_allows_configured_frontend_origin(client):
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_unknown_origin(client):
    response = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


def test_openapi_docs_are_served(client):
    assert client.get("/docs").status_code == 200
    assert "/health" in client.get("/openapi.json").json()["paths"]