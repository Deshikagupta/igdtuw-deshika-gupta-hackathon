"""API endpoints for previewing and ingesting source documents."""

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from pymongo.database import Database

from app.database import get_db
from app.models.collections import Collections
from app.schemas.ingestion import IngestionReport
from app.services.ingestion import ingest_records
from app.services.loaders import LoaderError, load_records

router = APIRouter(
    prefix="/api/v1/ingestion",
    tags=["Ingestion"],
)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MiB
MAX_RECORDS = 1000
CHUNK_SIZE = 64 * 1024
SUPPORTED_SUFFIXES = {".csv", ".json"}


class IngestionRequest(BaseModel):
    """A batch of source records submitted for ingestion."""

    records: list[dict[str, Any]] = Field(
        min_length=1,
        max_length=MAX_RECORDS,
    )


def _ingest_upload(
    upload: UploadFile,
    db: Database,
    dry_run: bool,
) -> IngestionReport:
    filename = upload.filename or ""
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload a .csv or .json file.",
        )

    total_bytes = 0

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            delete=False,
        ) as temporary_file:
            temp_path = temporary_file.name

            while True:
                chunk = upload.file.read(CHUNK_SIZE)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Upload exceeds the 5 MiB file-size limit.",
                    )

                temporary_file.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty.",
            )

        try:
            records = load_records(temp_path)
        except (LoaderError, FileNotFoundError) as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        if not records:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file contains no records.",
            )

        if len(records) > MAX_RECORDS:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds the {MAX_RECORDS}-record limit.",
            )

        return ingest_records(
            records,
            collection=db[Collections.DOCUMENTS],
            dry_run=dry_run,
        )
    finally:
        if "temp_path" in locals():
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass


@router.post(
    "/preview",
    response_model=IngestionReport,
    summary="Preview source-document ingestion",
)
def preview_ingestion(
    request: IngestionRequest,
    db: Database = Depends(get_db),
) -> IngestionReport:
    """Validate records and detect duplicates without writing."""
    return ingest_records(
        request.records,
        collection=db[Collections.DOCUMENTS],
        dry_run=True,
    )


@router.post(
    "/ingest",
    response_model=IngestionReport,
    summary="Ingest source documents",
)
def ingest_documents(
    request: IngestionRequest,
    db: Database = Depends(get_db),
) -> IngestionReport:
    """Validate, deduplicate, and persist accepted source documents."""
    return ingest_records(
        request.records,
        collection=db[Collections.DOCUMENTS],
        dry_run=False,
    )


@router.post(
    "/upload",
    response_model=IngestionReport,
    summary="Upload a CSV or JSON file for ingestion",
)
def upload_documents(
    file: UploadFile = File(...),
    dry_run: bool = Query(
        default=True,
        description="When true, validate without persisting records.",
    ),
    db: Database = Depends(get_db),
) -> IngestionReport:
    """Load a CSV or JSON file and preview or persist its records."""
    try:
        return _ingest_upload(file, db, dry_run)
    finally:
        file.file.close()

