from datetime import datetime, timedelta, timezone

from app.services import market_indices


def test_quote_computes_horizon_changes():
    now = datetime.now(timezone.utc)
    points = []
    for days, close in [(3650, 25), (365, 50), (91, 70), (30, 80), (7, 90), (1, 100), (0, 110)]:
        points.append(((now - timedelta(days=days)).timestamp(), close))
    quote = market_indices._quote_from_points(points)
    assert quote["value"] == 110
    assert quote["changes"]["1d"] == 10.0
    assert quote["changes"]["7d"] == round((110 - 90) / 90 * 100, 2)
    assert quote["changes"]["10y"] == 340.0


def test_parse_stooq_csv():
    csv_text = "Date,Open,High,Low,Close,Volume\n2026-09-18,10,11,9,10.5,0\n2026-09-19,10.5,12,10,11,0\n"
    points = market_indices.parse_stooq_csv(csv_text)
    assert len(points) == 2
    assert points[-1][1] == 11


def test_market_indices_api_returns_top_ten(client, monkeypatch):
    sample = [{
        "rank": 1,
        "exchange": "NYSE",
        "city": "New York",
        "lat": 40.7,
        "lng": -74.0,
        "index": "S&P 500",
        "value": 5800.1,
        "changes": {"1d": 0.4, "7d": 1.1, "30d": 2.0, "1q": 4.0, "1y": 12.0, "10y": 180.0},
        "color": "#22c55e",
        "market_cap_tn": 28.0,
    }]
    monkeypatch.setattr(market_indices, "list_market_indices", lambda: sample)
    response = client.get("/api/market-indices")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["source"]["name"] == "CNBC"
    assert payload["markets"][0]["index"] == "S&P 500"
    assert set(payload["markets"][0]["changes"]) >= {"1d", "7d", "30d", "1q", "1y", "10y"}


def test_tracker_has_markets_checkbox(client):
    from io import BytesIO

    from app.services.demo_tle import demo_tle_text

    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?ids=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="markets-overlay"' in html
    assert "toggleMarketsOverlay" in js
    assert "10 years" in js
    assert "CNBC" in js


def test_parse_cnbc_quotes_and_nasdaq_history():
    quotes = market_indices.parse_cnbc_quotes({
        "FormattedQuoteResult": {"FormattedQuote": [
            {"symbol": ".SPX", "last": "7,650.50", "change_pct": "+0.17%"},
            {"symbol": ".HSI", "last": "24,750.78", "change_pct": "UNCH"},
        ]}
    })
    assert quotes[".SPX"]["last"] == 7650.5
    assert quotes[".SPX"]["change_pct"] == 0.17
    assert quotes[".HSI"]["change_pct"] == 0.0
    points = market_indices.parse_nasdaq_history({
        "data": {"tradesTable": {"rows": [
            {"date": "09/18/2026", "close": "761.69"},
            {"date": "09/11/2026", "close": "750.00"},
        ]}}
    })
    assert len(points) == 2
    assert points[-1][1] == 761.69


def test_load_market_indices_uses_cnbc_1d(monkeypatch):
    monkeypatch.setattr(market_indices, "fetch_cnbc_quotes", lambda _symbols: {
        ".SPX": {"last": 5800.1, "change_pct": 0.4},
    })
    monkeypatch.setattr(market_indices, "TOP_MARKETS", [market_indices.TOP_MARKETS[0]])
    rows = market_indices._load_market_indices()
    assert rows[0]["value"] == 5800.1
    assert rows[0]["changes"]["1d"] == 0.4
    assert rows[0]["changes"]["1y"] is None
    assert rows[0]["source"] == "CNBC"
