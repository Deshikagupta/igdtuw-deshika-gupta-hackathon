"""Schemas for reporting document-ingestion results."""

from pydantic import BaseModel, Field

class RejectedRecord(BaseModel):    
    record_index: int = Field(ge=0)
    document_id: str | None = None
    reason: str = Field(min_length=1)


class IngestionReport(BaseModel):
    total_records: int = Field(ge=0)
    accepted_records: int = Field(default=0, ge=0)
    rejected_records: int = Field(default=0, ge=0)
    duplicate_records: int = Field(default=0, ge=0)
    already_present_records: int = Field(default=0, ge=0)
    quality_rejected_records: int = Field(default=0, ge=0)
    quality_warnings: int = Field(default=0, ge=0)
    dry_run: bool = False
    errors: list[RejectedRecord] = Field(default_factory=list)

