from datetime import date, timedelta
from io import BytesIO

import pytest

from app.services import currency_overlay
from app.services.demo_tle import demo_tle_text


def test_local_costs_are_units_needed_to_buy_baskets():
    usd_to = {"EUR": 0.80, "JPY": 150.0, "XAU": 0.0005, "INR": 80.0}
    costs = currency_overlay.local_costs(usd_to, "INR", oil_usd=100.0, bigmac_local=190.0)
    assert costs["USD"] == 80.0
    assert costs["EUR"] == 100.0
    assert costs["JPY"] == pytest.approx(80.0 / 150.0)
    assert costs["XAU"] == 160_000.0
    assert costs["OIL"] == 8_000.0
    assert costs["BIGMAC"] == 190.0


def test_local_costs_usd_pin():
    usd_to = {"EUR": 0.80, "JPY": 150.0, "XAU": 0.0005}
    costs = currency_overlay.local_costs(usd_to, "USD", oil_usd=100.0, bigmac_local=6.22)
    assert costs["USD"] == 1.0
    assert costs["EUR"] == 1.25
    assert costs["JPY"] == pytest.approx(1 / 150.0)
    assert costs["OIL"] == 100.0
    assert costs["BIGMAC"] == 6.22


def test_quote_from_series_includes_extended_horizons():
    latest = date(2026, 9, 20)
    series = {}
    samples = {
        0: 80.0,
        1: 79.0,
        7: 78.0,
        30: 77.0,
        90: 76.0,
        182: 75.0,
        365: 70.0,
        1826: 50.0,
    }
    for offset, inr in samples.items():
        day = (latest - timedelta(days=offset)).isoformat()
        series[day] = {"EUR": 0.80, "JPY": 150.0, "XAU": 0.0005, "INR": inr}
    series = dict(sorted(series.items()))
    quote = currency_overlay.quote_from_series(series, "INR", oil_usd=100.0, bigmac_local=190.0)
    assert quote["as_of"] == latest.isoformat()
    assert quote["rates"]["USD"] == 80.0
    assert quote["rates"]["OIL"] == 8_000.0
    assert quote["rates"]["BIGMAC"] == 190.0
    assert set(quote["changes"]["USD"]) == {"1d", "7d", "30d", "90d", "6m", "1y", "5y"}
    assert quote["changes"]["USD"]["1d"] == round((80 - 79) / 79 * 100, 2)
    assert quote["changes"]["USD"]["90d"] == round((80 - 76) / 76 * 100, 2)
    assert quote["changes"]["USD"]["6m"] == round((80 - 75) / 75 * 100, 2)
    assert quote["changes"]["USD"]["5y"] == round((80 - 50) / 50 * 100, 2)
    assert all(value is None for value in quote["changes"]["OIL"].values())
    assert all(value is None for value in quote["changes"]["BIGMAC"].values())


def test_parse_cnbc_last():
    payload = {"FormattedQuoteResult": {"FormattedQuote": [{"last": "100.64"}]}}
    assert currency_overlay.parse_cnbc_last(payload) == 100.64
    assert currency_overlay.parse_cnbc_last({"FormattedQuoteResult": {"FormattedQuote": [{"last": "1,234.50"}]}}) == 1234.5
    assert currency_overlay.parse_cnbc_last({}) is None


def test_local_costs_missing_fx_keeps_big_mac():
    costs = currency_overlay.local_costs({}, "XYZ", oil_usd=100.0, bigmac_local=12.0)
    assert costs["USD"] is None
    assert costs["OIL"] is None
    assert costs["BIGMAC"] == 12.0


def test_parse_big_mac_prices_prefers_euro_area():
    csv_text = (
        "date,iso_a3,currency_code,local_price\n"
        "2026-01-01,FRA,EUR,5.50\n"
        "2026-07-01,EUZ,EUR,6.19\n"
        "2026-07-01,USA,USD,6.22\n"
        "2026-07-01,IND,INR,190\n"
    )
    prices = currency_overlay.parse_big_mac_prices(csv_text)
    assert prices["EUR"] == 6.19
    assert prices["USD"] == 6.22
    assert prices["INR"] == 190.0


def test_weaker_local_currency_is_red():
    assert currency_overlay._pin_color(0.4) == "#ef4444"
    assert currency_overlay._pin_color(-0.4) == "#22c55e"


def test_currencies_api(client, monkeypatch):
    sample = {
        "count": 1,
        "as_of": "2026-09-18",
        "oil_usd": 100.64,
        "currencies": [{
            "code": "INR",
            "name": "Indian Rupee",
            "city": "Mumbai",
            "lat": 19.07,
            "lng": 72.87,
            "rates": {"USD": 80.0, "EUR": 100.0, "JPY": 0.53, "XAU": 160000, "OIL": 8000, "BIGMAC": 190},
            "changes": {
                "USD": {"1d": 0.1, "7d": 0.2, "30d": 0.3, "90d": 0.4, "6m": 0.5, "1y": 1.0, "5y": 5.0},
            },
            "color": "#ef4444",
        }],
        "source": currency_overlay.SOURCE,
        "sources": currency_overlay.SOURCES,
    }
    monkeypatch.setattr(currency_overlay, "list_currencies", lambda force_refresh=False: sample)
    response = client.get("/api/currencies")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["currencies"][0]["rates"]["BIGMAC"] == 190
    assert set(payload["currencies"][0]["changes"]["USD"]) >= {"1d", "90d", "6m", "5y"}


def test_tracker_has_currencies_checkbox(client):
    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?ids=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="currencies-overlay"' in html
    assert "toggleCurrenciesOverlay" in js
    assert "how many" in js
    assert "1 Big Mac" in js
    assert "1 barrel oil" in js
    assert "['90d', '90d']" in js or "90d" in js
    assert "['6m', '6m']" in js or "6m" in js
    assert "['5y', '5y']" in js or "5y" in js
    assert "currency-popup__pct" in js
    assert "currencyChangeCells" in js
