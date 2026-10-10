
from app.nlp.entities import EntityResolver


def test_resolves_ticker():
    resolver = EntityResolver()
    result = resolver.resolve(ticker="nvda")

    assert result["status"] == "resolved"
    assert result["ticker"] == "NVDA"
    assert result["company"] == "NVIDIA Corporation"
    assert result["matched_by"] == "ticker"


def test_resolves_company_alias():
    resolver = EntityResolver()
    result = resolver.resolve(company="Google")

    assert result["status"] == "resolved"
    assert result["ticker"] == "GOOGL"
    assert result["matched_by"] == "company"


def test_resolves_company_from_text_when_only_one_matches():
    resolver = EntityResolver()
    result = resolver.resolve(
        text="NVIDIA announced a new product this morning."
    )

    assert result["status"] == "resolved"
    assert result["ticker"] == "NVDA"
    assert result["matched_by"] == "text"


def test_does_not_match_partial_words():
    resolver = EntityResolver()
    result = resolver.resolve(text="The word apples appeared in a sentence.")

    assert result["status"] == "unresolved"


def test_conflicting_company_and_ticker_are_rejected():
    resolver = EntityResolver()
    result = resolver.resolve(company="NVIDIA", ticker="AAPL")

    assert result["status"] == "conflict"
    assert result["ticker"] is None


def test_unknown_ticker_is_unresolved():
    resolver = EntityResolver()
    result = resolver.resolve(ticker="UNKNOWN")

    assert result["status"] == "unresolved"


def test_multiple_companies_in_text_are_not_guessed():
    resolver = EntityResolver()
    result = resolver.resolve(
        text="NVIDIA and Microsoft discussed a partnership."
    )

    assert result["status"] == "unresolved"
    assert "multiple" in result["reason"].lower()


def test_unknown_company_without_text_is_unresolved():
    resolver = EntityResolver()
    result = resolver.resolve(company="A company not in our registry")

    assert result["status"] == "unresolved"