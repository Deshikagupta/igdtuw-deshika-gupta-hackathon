
import json

import pytest

from app.services.loaders import LoaderError, load_records


def test_load_csv_records(tmp_path):
    path = tmp_path / "documents.csv"
    path.write_text(
        "document_id,ticker,text\n"
        "doc-1,NVDA,Revenue increased\n"
        "doc-2,AAPL,Sales declined\n",
        encoding="utf-8",
    )

    records = load_records(path)

    assert len(records) == 2
    assert records[0]["ticker"] == "NVDA"
    assert records[1]["text"] == "Sales declined"


def test_load_csv_skips_blank_rows(tmp_path):
    path = tmp_path / "documents.csv"
    path.write_text(
        "document_id,ticker\n"
        "doc-1,NVDA\n"
        "\n"
        "doc-2,AAPL\n",
        encoding="utf-8",
    )

    assert len(load_records(path)) == 2


def test_load_json_list(tmp_path):
    path = tmp_path / "documents.json"
    path.write_text(
        json.dumps([
            {"document_id": "doc-1", "ticker": "NVDA"},
            {"document_id": "doc-2", "ticker": "AAPL"},
        ]),
        encoding="utf-8",
    )

    assert len(load_records(path)) == 2


def test_load_json_single_object(tmp_path):
    path = tmp_path / "document.json"
    path.write_text(
        json.dumps({"document_id": "doc-1", "ticker": "NVDA"}),
        encoding="utf-8",
    )

    records = load_records(path)

    assert len(records) == 1
    assert records[0]["document_id"] == "doc-1"


def test_missing_file_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_records(tmp_path / "missing.csv")


def test_unsupported_extension_raises_error(tmp_path):
    path = tmp_path / "documents.txt"
    path.write_text("some data", encoding="utf-8")

    with pytest.raises(LoaderError, match="Unsupported file type"):
        load_records(path)


def test_json_scalar_is_rejected(tmp_path):
    path = tmp_path / "documents.json"
    path.write_text(json.dumps("not a record"), encoding="utf-8")

    with pytest.raises(LoaderError, match="object or a list"):
        load_records(path)


def test_json_list_with_non_object_is_rejected(tmp_path):
    path = tmp_path / "documents.json"
    path.write_text(json.dumps([{"document_id": "doc-1"}, 42]), encoding="utf-8")

    with pytest.raises(LoaderError, match="must be an object"):
        load_records(path)


def test_malformed_json_is_rejected(tmp_path):
    path = tmp_path / "documents.json"
    path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(LoaderError, match="Could not parse"):
        load_records(path)


def test_csv_duplicate_headers_are_rejected(tmp_path):
    path = tmp_path / "documents.csv"
    path.write_text("ticker,ticker\nNVDA,AAPL\n", encoding="utf-8")

    with pytest.raises(LoaderError, match="unique"):
        load_records(path)