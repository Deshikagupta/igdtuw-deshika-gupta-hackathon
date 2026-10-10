"""Shared enumerations. Values are the exact strings stored in MongoDB and sent over the API."""

from enum import StrEnum


class SourceType(StrEnum):
    FINANCIAL_NEWS = "financial_news"
    SOCIAL_MEDIA = "social_media"


class EventType(StrEnum):
    GEOPOLITICAL = "Geopolitical"
    MACROECONOMIC = "Macroeconomic"
    CREDIT_EVENT = "Credit Event"
    MERGER_ACQUISITION = "Merger & Acquisition"
    PRODUCT_LAUNCH = "Product Launch"
    REGULATORY = "Regulatory"
    EARNINGS = "Earnings"
    LEGAL = "Legal"
    OPERATIONAL = "Operational"
    OTHER = "Other"


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AssetType(StrEnum):
    EQUITY = "Equity"
    CORPORATE_BOND = "Corporate Bond"
    GOVERNMENT_BOND = "Government Bond"
    CORPORATE_LOAN = "Corporate Loan"
    DERIVATIVE = "Derivative"


class StressMode(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"