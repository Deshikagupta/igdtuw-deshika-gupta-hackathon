"""Raw source documents (news articles / social posts) before NLP analysis."""

from pydantic import BaseModel, Field

from app.models.base import UtcDatetime
from app.models.enums import SourceType
from app.schemas.common import CleanText, CompanyName, OptionalTicker


class SourceDocument(BaseModel):
    document_id: str = Field(min_length=1, max_length=100)
    timestamp: UtcDatetime
    source: SourceType
    company: CompanyName | None = None
    ticker: OptionalTicker = None
    text: CleanText