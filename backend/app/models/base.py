"""Shared model helpers: UTC datetimes and the base class for persisted records."""

from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, ClassVar, Self

from pydantic import AfterValidator, BaseModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_utc(value: datetime) -> datetime:
    """Naive datetimes are assumed to be UTC; aware ones are converted to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(to_utc)]


def _to_plain(value: Any) -> Any:
    """Recursively convert Enums (including dict keys) to plain values for BSON."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {_to_plain(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value


class MongoRecord(BaseModel):
    """Mixin for classes persisted in MongoDB.

    Subclasses declare `collection_name` and `id_field` (the business key,
    e.g. 'signal_id'). MongoDB's own `_id` is never exposed to the application.
    """

    collection_name: ClassVar[str]
    id_field: ClassVar[str]

    def to_mongo(self) -> dict[str, Any]:
        return _to_plain(self.model_dump(mode="python"))

    @classmethod
    def from_mongo(cls, document: Mapping[str, Any]) -> Self:
        data = {k: v for k, v in document.items() if k != "_id"}
        return cls.model_validate(data)

    def key_filter(self) -> dict[str, Any]:
        """Filter matching this record by business key (use with upsert)."""
        return {self.id_field: getattr(self, self.id_field)}