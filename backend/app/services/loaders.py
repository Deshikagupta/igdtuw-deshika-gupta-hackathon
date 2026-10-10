
"""CSV and JSON loaders for incoming document records."""

import csv
import json
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {".csv", ".json"}


class LoaderError(ValueError):
    """Raised when an input file cannot be loaded safely."""


def load_records(file_path: str | Path) -> list[dict[str, Any]]:
    """Load records from a CSV or JSON file.

    JSON may contain either a list of objects or a single object.
    CSV files must have a header row. Empty files and non-object records
    are rejected with a clear error.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    if not path.is_file():
        raise LoaderError(f"Input path is not a file: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise LoaderError(
            f"Unsupported file type '{suffix}'. Use CSV or JSON."
        )

    try:
        if suffix == ".csv":
            return _load_csv(path)
        return _load_json(path)
    except (UnicodeDecodeError, csv.Error, json.JSONDecodeError) as exc:
        raise LoaderError(f"Could not parse input file '{path}': {exc}") from exc


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise LoaderError("CSV file must contain a header row.")

        headers = [header.strip() if header else "" for header in reader.fieldnames]
        if any(not header for header in headers):
            raise LoaderError("CSV column names must not be empty.")

        if len(headers) != len(set(headers)):
            raise LoaderError("CSV column names must be unique.")

        records = []
        for row_number, row in enumerate(reader, start=2):
            # DictReader uses a None key when a row has extra columns.
            if None in row:
                raise LoaderError(
                    f"CSV row {row_number} contains more values than headers."
                )

            # Ignore completely blank rows.
            if not any(value and value.strip() for value in row.values()):
                continue

            record = {
                headers[index]: value
                for index, value in enumerate(row.values())
            }
            records.append(record)

        return records


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)

    if isinstance(payload, dict):
        payload = [payload]

    if not isinstance(payload, list):
        raise LoaderError("JSON must contain an object or a list of objects.")

    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            raise LoaderError(
                f"JSON record at index {index} must be an object."
            )

    return payload