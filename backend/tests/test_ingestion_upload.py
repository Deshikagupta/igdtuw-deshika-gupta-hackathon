"""Tests for CSV and JSON file-upload ingestion."""

import io
import json

from app.models.collections import Collections


def csv_bytes():
    return (
        "document_id,timestamp,source,company,ticker,text\n"
        'csv-001,2026-10-09T10:30:00Z,financial_news,Apple Inc.,AAPL,'
        '"Apple announced quarterly revenue growth."\n'
    ).encode("utf-8")


def json_bytes():
    return json.dumps(
        [
            {
                "document_id": "json-001",
                "timestamp": "2026-10-09T10:30:00Z",
                "source": "financial_news",
                "company": "Microsoft",
                "ticker": "MSFT",
                "text": "Microsoft announced a product update.",
            }
        ]
    ).encode("utf-8")


def upload(client, filename, content, dry_run=True):
    return client.post(
        "/api/v1/ingestion/upload",
        params={"dry_run": str(dry_run).lower()},
        files={"file": (filename, io.BytesIO(content))},
    )


def test_csv_upload_preview_does_not_write(client, mongo):
    response = upload(client, "news.csv", csv_bytes())

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_records"] == 1
    assert body["dry_run"] is True
    assert mongo.db[Collections.DOCUMENTS].count_documents({}) == 0


def test_json_upload_persists_when_requested(client, mongo):
    response = upload(
        client,
        "news.json",
        json_bytes(),
        dry_run=False,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_records"] == 1
    assert body["dry_run"] is False

    stored = mongo.db[Collections.DOCUMENTS].find_one(
        {"document_id": "json-001"}
    )
    assert stored is not None
    assert stored["ticker"] == "MSFT"


def test_csv_upload_rejects_invalid_record(client, mongo):
    content = (
        "document_id,timestamp,source,company,ticker,text\n"
        'bad-001,not-a-date,financial_news,Apple Inc.,AAPL,"Some text"\n'
    ).encode("utf-8")

    response = upload(client, "bad.csv", content)

    assert response.status_code == 200
    body = response.json()
    assert body["accepted_records"] == 0
    assert body["rejected_records"] == 1
    assert mongo.db[Collections.DOCUMENTS].count_documents({}) == 0


def test_upload_rejects_unsupported_extension(client):
    response = upload(client, "news.txt", b"some text")

    assert response.status_code == 415


def test_upload_rejects_malformed_json(client):
    response = upload(client, "news.json", b'{"records": ')

    assert response.status_code == 400


def test_upload_rejects_empty_file(client):
    response = upload(client, "empty.csv", b"")

    assert response.status_code == 400


def test_upload_rejects_file_over_size_limit(client):
    from app.routers.ingestion import MAX_UPLOAD_BYTES

    response = upload(
        client,
        "large.json",
        b"x" * (MAX_UPLOAD_BYTES + 1),
    )

    assert response.status_code == 413


def test_upload_rejects_more_than_1000_records(client):
    records = [
        {
            "document_id": f"doc-{i}",
            "timestamp": "2026-10-09T10:30:00Z",
            "source": "financial_news",
            "company": "Apple Inc.",
            "ticker": "AAPL",
            "text": f"Unique synthetic news item number {i}.",
        }
        for i in range(1001)
    ]

    response = upload(
        client,
        "large.json",
        json.dumps(records).encode("utf-8"),
    )

    assert response.status_code == 413

