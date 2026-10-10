from fastapi import Depends
from fastapi.testclient import TestClient
from pymongo.errors import AutoReconnect, OperationFailure

from app.database import get_db
from app.exceptions import NotFoundError


def test_app_error_becomes_clean_json(app):
    def missing():
        raise NotFoundError("Ticker XYZ not found")

    app.add_api_route("/_missing", missing)
    with TestClient(app) as client:
        response = client.get("/_missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Ticker XYZ not found", "error_code": "not_found"}


def test_db_dependency_returns_503_when_database_is_down(down_app):
    def probe(db=Depends(get_db)):
        return {"ok": True}

    down_app.add_api_route("/_probe", probe)
    with TestClient(down_app) as client:
        response = client.get("/_probe")
    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "database_unavailable"
    assert "Cannot reach MongoDB" in body["detail"]
    assert "Traceback" not in response.text


def test_lost_connection_during_request_returns_503(app):
    def boom():
        raise AutoReconnect("connection lost")

    app.add_api_route("/_lost", boom)
    with TestClient(app) as client:
        response = client.get("/_lost")
    assert response.status_code == 503
    assert response.json()["error_code"] == "database_unavailable"


def test_other_database_errors_return_500_without_internal_details(app):
    def boom():
        raise OperationFailure("internal mongo detail")

    app.add_api_route("/_dberr", boom)
    with TestClient(app) as client:
        response = client.get("/_dberr")
    assert response.status_code == 500
    assert response.json()["error_code"] == "database_error"
    assert "internal mongo detail" not in response.text


def test_unexpected_errors_are_hidden_from_clients(app):
    def boom():
        raise RuntimeError("secret internal detail")

    app.add_api_route("/_boom", boom)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_boom")
    assert response.status_code == 500
    assert response.json()["error_code"] == "internal_error"
    assert "secret internal detail" not in response.text


def test_unknown_route_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert "detail" in response.json()