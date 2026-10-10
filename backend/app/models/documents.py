"""MongoDB record classes.

Each record is the API schema plus persistence metadata (collection + business key),
so the shape of every entity is defined exactly once, in `app/schemas`.
"""

from typing import ClassVar

from app.models.base import MongoRecord
from app.models.collections import Collections
from app.schemas.company import Company
from app.schemas.documents import SourceDocument
from app.schemas.portfolio import PortfolioAsset
from app.schemas.risk_signal import RiskSignal
from app.schemas.stress import StressTestResult


class SourceDocumentRecord(SourceDocument, MongoRecord):
    collection_name: ClassVar[str] = Collections.DOCUMENTS
    id_field: ClassVar[str] = "document_id"


class RiskSignalRecord(RiskSignal, MongoRecord):
    collection_name: ClassVar[str] = Collections.RISK_SIGNALS
    id_field: ClassVar[str] = "signal_id"


class CompanyRecord(Company, MongoRecord):
    collection_name: ClassVar[str] = Collections.COMPANIES
    id_field: ClassVar[str] = "ticker"


class PortfolioAssetRecord(PortfolioAsset, MongoRecord):
    collection_name: ClassVar[str] = Collections.PORTFOLIO_ASSETS
    id_field: ClassVar[str] = "asset_id"


class StressTestRecord(StressTestResult, MongoRecord):
    collection_name: ClassVar[str] = Collections.STRESS_TESTS
    id_field: ClassVar[str] = "stress_test_id"