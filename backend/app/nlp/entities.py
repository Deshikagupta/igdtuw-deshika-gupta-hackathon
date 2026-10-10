
"""Deterministic company entity resolution using a local reference registry."""

import json
import re
from pathlib import Path
from typing import Any

from app.nlp.preprocessing import normalize_company, normalize_ticker


DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "companies.json"
)


class EntityResolver:
    """Resolve company names and tickers against a JSON company registry."""

    def __init__(self, registry_path: str | Path | None = None) -> None:
        path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH

        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"Company registry not found: {path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid company registry JSON: {path}") from exc

        if not isinstance(records, list):
            raise ValueError("Company registry must be a JSON list")

        self.by_ticker: dict[str, dict[str, Any]] = {}
        self.name_to_ticker: dict[str, str] = {}

        for record in records:
            ticker = normalize_ticker(record.get("ticker"))
            name = record.get("name")

            if not ticker or not isinstance(name, str) or not name.strip():
                raise ValueError("Each company needs a valid ticker and name")

            if ticker in self.by_ticker:
                raise ValueError(f"Duplicate ticker in registry: {ticker}")

            aliases = record.get("aliases", [])
            if not isinstance(aliases, list):
                raise ValueError(f"Aliases for {ticker} must be a list")

            company = {
                "ticker": ticker,
                "name": name.strip(),
                "sector": record.get("sector"),
                "aliases": aliases,
            }
            self.by_ticker[ticker] = company

            for alias in [company["name"], *aliases]:
                if not isinstance(alias, str):
                    raise ValueError(f"Invalid alias for {ticker}")

                normalized = normalize_company(alias)
                if not normalized:
                    continue

                previous = self.name_to_ticker.get(normalized)
                if previous and previous != ticker:
                    raise ValueError(
                        f"Alias '{alias}' maps to multiple companies"
                    )

                self.name_to_ticker[normalized] = ticker

        self._aliases = sorted(self.name_to_ticker, key=len, reverse=True)

    def _find_names_in_text(self, text: str | None) -> set[str]:
        """Find registry aliases as whole phrases, case-insensitively."""
        if not text:
            return set()

        found: set[str] = set()

        for alias in self._aliases:
            words = alias.split()
            pattern = r"(?<!\w)" + r"[\W_]+".join(
                re.escape(word) for word in words
            ) + r"(?!\w)"

            if re.search(pattern, text, flags=re.IGNORECASE):
                found.add(self.name_to_ticker[alias])

        return found

    def resolve(
        self,
        company: str | None = None,
        ticker: str | None = None,
        text: str | None = None,
    ) -> dict[str, Any]:
        """Resolve a company without guessing when evidence conflicts."""
        normalized_ticker = normalize_ticker(ticker)
        normalized_company = normalize_company(company)

        if normalized_ticker and normalized_ticker not in self.by_ticker:
            return {
                "status": "unresolved",
                "ticker": None,
                "company": None,
                "matched_by": None,
                "reason": f"Ticker {normalized_ticker} is not in the registry",
            }

        explicit_company_ticker = (
            self.name_to_ticker.get(normalized_company)
            if normalized_company
            else None
        )

        if (
            normalized_ticker
            and explicit_company_ticker
            and normalized_ticker != explicit_company_ticker
        ):
            return {
                "status": "conflict",
                "ticker": None,
                "company": None,
                "matched_by": None,
                "reason": (
                    "Provided company and ticker refer to different companies"
                ),
            }

        if normalized_ticker:
            record = self.by_ticker[normalized_ticker]
            return {
                "status": "resolved",
                "ticker": record["ticker"],
                "company": record["name"],
                "matched_by": "ticker",
                "reason": None,
            }

        if explicit_company_ticker:
            record = self.by_ticker[explicit_company_ticker]
            return {
                "status": "resolved",
                "ticker": record["ticker"],
                "company": record["name"],
                "matched_by": "company",
                "reason": None,
            }

        text_matches = self._find_names_in_text(text)

        if len(text_matches) == 1:
            matched_ticker = next(iter(text_matches))
            record = self.by_ticker[matched_ticker]
            return {
                "status": "resolved",
                "ticker": record["ticker"],
                "company": record["name"],
                "matched_by": "text",
                "reason": None,
            }

        reason = (
            "Text mentions multiple registered companies"
            if len(text_matches) > 1
            else "No registered company could be identified"
        )

        return {
            "status": "unresolved",
            "ticker": None,
            "company": None,
            "matched_by": None,
            "reason": reason,
        }