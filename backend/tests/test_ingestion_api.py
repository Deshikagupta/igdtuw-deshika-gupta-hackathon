
"""API tests for source-document ingestion endpoints."""

from tests.conftest import SECRET_URI


def valid_payload(**overrides):
    record = {
        "document_id": "api-doc-001",
        "timestamp": "2026-10-09T10:30:00Z",
        "source": "financial_news",
        "company": "Apple Inc.",
        "ticker": "AAPL",
        "text": "Apple announced quarterly revenue growth.",
    }
    record.update(overrides)
    return {"records": [record]}


def test_preview_accepts_valid_record_without_writing(client, mongo):
    response = client.post(
        "/api/v1/ingestion/preview",
        json=valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_records"] == 1
    assert body["accepted_records"] == 1
    assert body["rejected_records"] == 0
    assert body["dry_run"] is True
    assert mongo.db["documents"].count_documents({}) == 0


def test_ingest_persists_valid_record(client, mongo):
    response = client.post(
        "/api/v1/ingestion/ingest",
        json=valid_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_records"] == 1
    assert body["rejected_records"] == 0
    assert body["dry_run"] is False

    stored = mongo.db["documents"].find_one(
        {"document_id": "api-doc-001"}
    )
    assert stored is not None
    assert stored["ticker"] == "AAPL"


def test_preview_reports_invalid_timestamp(client, mongo):
    response = client.post(
        "/api/v1/ingestion/preview",
        json=valid_payload(timestamp="09/10/2026"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_records"] == 0
    assert body["rejected_records"] == 1
    assert "ISO-8601" in body["errors"][0]["reason"]
    assert mongo.db["documents"].count_documents({}) == 0


def test_ingest_does_not_overwrite_existing_document(client, mongo):
    first = client.post(
        "/api/v1/ingestion/ingest",
        json=valid_payload(),
    )
    assert first.status_code == 200

    second = client.post(
        "/api/v1/ingestion/ingest",
        json=valid_payload(text="Changed text for the same ID."),
    )

    assert second.status_code == 200
    body = second.json()
    assert body["rejected_records"] == 1
    assert body["accepted_records"] == 0

    stored = mongo.db["documents"].find_one(
        {"document_id": "api-doc-001"}
    )
    assert stored["text"] == "Apple announced quarterly revenue growth."


def test_request_with_empty_records_is_rejected(client):
    response = client.post(
        "/api/v1/ingestion/preview",
        json={"records": []},
    )

    assert response.status_code == 422


def test_request_over_batch_limit_is_rejected(client):
    response = client.post(
        "/api/v1/ingestion/preview",
        json={"records": [{}] * 1001},
    )

    assert response.status_code == 422


def test_ingestion_returns_503_when_database_is_unavailable(down_app):
    from fastapi.testclient import TestClient

    with TestClient(down_app) as down_client:
        response = down_client.post(
            "/api/v1/ingestion/ingest",
            json=valid_payload(),
        )

    assert response.status_code == 503
    assert response.json()["error_code"] == "database_unavailable"
    assert "secret" not in response.text

