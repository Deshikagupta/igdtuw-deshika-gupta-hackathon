from app.models.collections import Collections
from app.models.documents import (
    PortfolioAssetRecord,
    RiskSignalRecord,
    StressTestRecord,
)
from app.models.enums import AssetType, EventType


def test_to_mongo_uses_plain_values_and_no_object_id(signal_payload):
    doc = RiskSignalRecord(**signal_payload).to_mongo()
    assert "_id" not in doc
    assert doc["event_type"] == "Geopolitical"
    assert type(doc["event_type"]) is str
    assert doc["ticker"] == "NVDA"


def test_record_metadata(signal_payload):
    record = RiskSignalRecord(**signal_payload)
    assert RiskSignalRecord.collection_name == Collections.RISK_SIGNALS
    assert record.key_filter() == {"signal_id": "sig-001"}


def test_round_trip_through_mongodb(mongo, signal_payload):
    mongo.ensure_ready()
    record = RiskSignalRecord(**signal_payload)
    mongo.db[record.collection_name].insert_one(record.to_mongo())

    stored = mongo.db[record.collection_name].find_one(record.key_filter())
    assert "_id" in stored  # added by MongoDB...
    restored = RiskSignalRecord.from_mongo(stored)  # ...and dropped on the way back
    assert restored.signal_id == record.signal_id
    assert restored.event_type is EventType.GEOPOLITICAL
    assert restored.timestamp == record.timestamp
    assert restored.timestamp.tzinfo is not None


def test_stress_record_round_trip_with_enum_keys(mongo):
    mongo.ensure_ready()
    record = StressTestRecord(
        stress_test_id="st-auto-sig-001",
        mode="automatic",
        scenario_key="geopolitical",
        scenario_name="Geopolitical Shock",
        trigger_event_type="Geopolitical",
        trigger_impact_score=8,
        trigger_signal_id="sig-001",
        trigger_reason="Impact score 8 >= threshold 8",
        shocks_pct={"Equity": -10.0, "Government Bond": -2.0},
        portfolio_before=1000.0,
        portfolio_after=920.0,
        absolute_loss=80.0,
        percentage_loss=8.0,
        asset_level_results=[],
    )
    doc = record.to_mongo()
    assert doc["shocks_pct"] == {"Equity": -10.0, "Government Bond": -2.0}  # string keys for BSON

    mongo.db[record.collection_name].insert_one(doc)
    restored = StressTestRecord.from_mongo(
        mongo.db[record.collection_name].find_one(record.key_filter())
    )
    assert restored.shocks_pct[AssetType.EQUITY] == -10.0
    assert restored.percentage_loss == 8.0


def test_portfolio_record_keeps_derived_market_value():
    record = PortfolioAssetRecord(asset_id="E1", asset_name="Equity", asset_type="Equity",
                                  quantity=10, current_price=50.0)
    assert record.to_mongo()["market_value"] == 500.0
    assert PortfolioAssetRecord.id_field == "asset_id"