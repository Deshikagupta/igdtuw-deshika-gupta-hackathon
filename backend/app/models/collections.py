"""MongoDB collection names (single source of truth)."""


class Collections:
    DOCUMENTS = "documents"
    RISK_SIGNALS = "risk_signals"
    COMPANIES = "companies"
    PORTFOLIO_ASSETS = "portfolio_assets"
    STRESS_TESTS = "stress_tests"

    ALL = (DOCUMENTS, RISK_SIGNALS, COMPANIES, PORTFOLIO_ASSETS, STRESS_TESTS)