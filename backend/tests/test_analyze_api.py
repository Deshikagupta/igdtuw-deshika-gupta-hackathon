
"""API tests for POST /api/analyze."""

def test_analyze_returns_structured_risk_signal(client):
    response = client.post(
        "/api/analyze",
        json={
            "text": (
                "Apple reported declining revenue amid a fraud "
                "investigation and a regulatory fine."
            ),
            "company": "Apple Inc.",
            "ticker": "AAPL",
            "source": "financial_news",
            "persist": False,
            "run_stress_test": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    signal = body["signal"]

    assert signal["ticker"] == "AAPL"
    assert signal["sentiment_label"] == "negative"
    assert signal["risk_level"] == "HIGH"
    assert 1 <= signal["impact_score"] <= 10
    assert "fraud" in signal["matched_keywords"]
    assert body["trigger"] is None
    assert body["stress_test"] is None


def test_analyze_rejects_empty_text(client):
    response = client.post(
        "/api/analyze",
        json={
            "text": "   ",
            "persist": False,
        },
    )

    assert response.status_code == 422


def test_analyze_rejects_invalid_source(client):
    response = client.post(
        "/api/analyze",
        json={
            "text": "Company reported quarterly results.",
            "source": "unknown_source",
            "persist": False,
        },
    )

    assert response.status_code == 422