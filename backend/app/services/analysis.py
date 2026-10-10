
"""Orchestrate source-document analysis and optional persistence."""

from datetime import datetime, timezone
from hashlib import sha256

from pymongo.database import Database

from app.models.collections import Collections
from app.models.documents import RiskSignalRecord
from app.risk_engine.engine import RiskSignalEngine
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.documents import SourceDocument
from app.schemas.risk_signal import RiskSignal
from app.schemas.stress import StressTestRequest, StressTrigger
from app.services.ingestion import ingest_records
from app.stress_testing.scenarios import ScenarioLoader
from app.stress_testing.service import StressTestingService
from app.stress_testing.triggers import evaluate_trigger


class AnalysisService:
    """Generate risk signals and optionally persist their source and result."""

    def __init__(self, engine: RiskSignalEngine | None = None) -> None:
        self.engine = engine or RiskSignalEngine()
        self.scenario_loader = ScenarioLoader()
        self.stress_service = StressTestingService(
            scenario_loader=self.scenario_loader
        )

    def analyze(
        self,
        request: AnalyzeRequest,
        db: Database | None = None,
    ) -> AnalyzeResponse:
        timestamp = request.timestamp or datetime.now(timezone.utc)
        document_id = self._document_id(request, timestamp)

        document = SourceDocument(
            document_id=document_id,
            timestamp=timestamp,
            source=request.source,
            company=request.company,
            ticker=request.ticker,
            text=request.text,
        )

        signal = self.engine.analyze(document)

        if request.persist:
            if db is None:
                raise ValueError(
                    "A database is required when persist=true."
                )

            report = ingest_records(
                [document.model_dump(mode="json")],
                collection=db[Collections.DOCUMENTS],
                dry_run=False,
            )

            if report.rejected_records:
                reasons = "; ".join(
                    item.reason for item in report.errors
                )
                raise ValueError(
                    f"Source document was rejected: {reasons}"
                )

            signal_record = RiskSignalRecord.model_validate(
                signal.model_dump()
            )

            db[Collections.RISK_SIGNALS].update_one(
                {"document_id": document_id},
                {"$setOnInsert": signal_record.to_mongo()},
                upsert=True,
            )

        trigger: StressTrigger | None = None
        stress_test = None

        # Automatic stress testing requires persisted signal data and a portfolio.
        if request.run_stress_test and request.persist and db is not None:
            scenarios = self.scenario_loader.load_all()
            trigger = evaluate_trigger(signal, scenarios)

            if trigger.triggered and trigger.scenario_key:
                stress_test = self.stress_service.run(
                    StressTestRequest(signal_id=signal.signal_id),
                    db=db,
                    persist=True,
                )

        return AnalyzeResponse(
            signal=signal,
            trigger=trigger,
            stress_test=stress_test,
        )

    @staticmethod
    def _document_id(
        request: AnalyzeRequest,
        timestamp: datetime,
    ) -> str:
        """Build an ID for ad-hoc text when the caller provides no ID."""
        identity = "|".join(
            [
                request.source.value,
                request.ticker or "",
                request.company or "",
                timestamp.isoformat(),
                request.text,
            ]
        )
        digest = sha256(identity.encode("utf-8")).hexdigest()[:32]
        return f"analyze-{digest}"
