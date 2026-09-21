"""World currency pins: local units needed to buy USD, EUR, yen, gold, oil, and a Big Mac."""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

from app.services.overlay_cache import get_or_set

log = logging.getLogger(__name__)

FRANKFURTER_RATES = "https://api.frankfurter.dev/v2/rates"
FRANKFURTER_HOME = "https://frankfurter.dev"
CNBC_QUOTE = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
CNBC_HOME = "https://www.cnbc.com"
BIGMAC_CSV = "https://raw.githubusercontent.com/TheEconomist/big-mac-data/master/output-data/big-mac-full-index.csv"
BIGMAC_HOME = "https://github.com/TheEconomist/big-mac-data"
REQUEST_TIMEOUT = 20
HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json,text/csv,text/plain,*/*",
}

SOURCE = {
    "name": "Frankfurter",
    "url": FRANKFURTER_HOME,
    "license": "Free public JSON; no API key",
    "attribution": (
        "Local-currency prices of 1 USD, 1 EUR, 1 yen, and 1 troy ounce of gold use daily "
        "Frankfurter rates (https://frankfurter.dev; official / central-bank sources). "
        "1 barrel of oil uses the CNBC public WTI crude quote. "
        "1 Big Mac uses The Economist Big Mac Index local prices."
    ),
}

SOURCES = [
    SOURCE,
    {
        "name": "CNBC",
        "url": CNBC_HOME,
        "license": "Public quote widget; no API key",
        "attribution": "WTI crude oil (USD/barrel) from CNBC public quotes (@CL.1).",
    },
    {
        "name": "The Economist Big Mac Index",
        "url": BIGMAC_HOME,
        "license": "Public dataset on GitHub",
        "attribution": "Big Mac local prices from The Economist Big Mac Index dataset.",
    },
]

BASKETS = ("USD", "EUR", "JPY", "XAU", "OIL", "BIGMAC")
PERIODS = (
    ("1d", 1),
    ("7d", 7),
    ("30d", 30),
    ("90d", 90),
    ("6m", 182),
    ("1y", 365),
    ("5y", 1826),
)
CHANGE_HORIZONS = ("USD", "EUR", "JPY", "XAU")

# Pins sit on the issuing city / market. Gold is the London fix (LBMA).
WORLD_CURRENCIES: list[dict[str, Any]] = [
    {"code": "USD", "name": "US Dollar", "city": "Washington", "lat": 38.9072, "lng": -77.0369},
    {"code": "EUR", "name": "Euro", "city": "Frankfurt", "lat": 50.1109, "lng": 8.6821},
    {"code": "JPY", "name": "Japanese Yen", "city": "Tokyo", "lat": 35.6762, "lng": 139.6503},
    {"code": "GBP", "name": "British Pound", "city": "London", "lat": 51.5074, "lng": -0.1278},
    {"code": "CHF", "name": "Swiss Franc", "city": "Zurich", "lat": 47.3769, "lng": 8.5417},
    {"code": "CNY", "name": "Chinese Yuan", "city": "Beijing", "lat": 39.9042, "lng": 116.4074},
    {"code": "INR", "name": "Indian Rupee", "city": "Mumbai", "lat": 19.0760, "lng": 72.8777},
    {"code": "CAD", "name": "Canadian Dollar", "city": "Ottawa", "lat": 45.4215, "lng": -75.6972},
    {"code": "AUD", "name": "Australian Dollar", "city": "Sydney", "lat": -33.8688, "lng": 151.2093},
    {"code": "BRL", "name": "Brazilian Real", "city": "Brasília", "lat": -15.7975, "lng": -47.8919},
    {"code": "MXN", "name": "Mexican Peso", "city": "Mexico City", "lat": 19.4326, "lng": -99.1332},
    {"code": "KRW", "name": "South Korean Won", "city": "Seoul", "lat": 37.5665, "lng": 126.9780},
    {"code": "ZAR", "name": "South African Rand", "city": "Johannesburg", "lat": -26.2041, "lng": 28.0473},
    {"code": "SGD", "name": "Singapore Dollar", "city": "Singapore", "lat": 1.3521, "lng": 103.8198},
    {"code": "HKD", "name": "Hong Kong Dollar", "city": "Hong Kong", "lat": 22.3193, "lng": 114.1694},
    {"code": "SEK", "name": "Swedish Krona", "city": "Stockholm", "lat": 59.3293, "lng": 18.0686},
    {"code": "TRY", "name": "Turkish Lira", "city": "Ankara", "lat": 39.9334, "lng": 32.8597},
    {"code": "PLN", "name": "Polish Zloty", "city": "Warsaw", "lat": 52.2297, "lng": 21.0122},
    {"code": "NZD", "name": "New Zealand Dollar", "city": "Wellington", "lat": -41.2865, "lng": 174.7762},
    {"code": "XAU", "name": "Gold (troy oz)", "city": "London", "lat": 51.5145, "lng": -0.0930},
]


def _pct_change(current: float | None, past: float | None) -> float | None:
    if current is None or past is None or past == 0:
        return None
    return round((current - past) / past * 100.0, 2)


def parse_frankfurter_rates(rows: list[Any] | None) -> dict[str, dict[str, float]]:
    """Map YYYY-MM-DD -> {quote: units of quote per 1 USD}."""
    by_day: dict[str, dict[str, float]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        day = str(row.get("date") or "")
        quote = str(row.get("quote") or "").upper()
        try:
            rate = float(row.get("rate"))
        except (TypeError, ValueError):
            continue
        if not day or not quote or rate == 0:
            continue
        by_day.setdefault(day, {})[quote] = rate
    return dict(sorted(by_day.items()))


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def local_per_usd(usd_to: dict[str, float], code: str) -> float | None:
    code = (code or "").upper()
    if code == "USD":
        return 1.0
    rate = usd_to.get(code)
    return None if not rate else float(rate)


def local_costs(
    usd_to: dict[str, float],
    code: str,
    *,
    oil_usd: float | None = None,
    bigmac_local: float | None = None,
) -> dict[str, float | None]:
    """How many units of `code` are needed to buy each basket item."""
    out: dict[str, float | None] = {key: None for key in BASKETS}
    per_usd = local_per_usd(usd_to, code)
    if per_usd is None:
        out["BIGMAC"] = bigmac_local
        return out
    out["USD"] = per_usd
    for base in ("EUR", "JPY", "XAU"):
        base_per_usd = usd_to.get(base)
        out[base] = None if not base_per_usd else per_usd / base_per_usd
    out["OIL"] = None if oil_usd is None else per_usd * oil_usd
    out["BIGMAC"] = bigmac_local
    return out


def _close_on_or_before(days: list[str], target: date) -> str | None:
    wanted = target.isoformat()
    chosen = None
    for day in days:
        if day <= wanted:
            chosen = day
        else:
            break
    return chosen


def quote_from_series(
    series: dict[str, dict[str, float]],
    code: str,
    *,
    oil_usd: float | None = None,
    bigmac_local: float | None = None,
) -> dict[str, Any]:
    days = list(series)
    empty_rates = {base: None for base in BASKETS}
    empty_changes = {base: {key: None for key, _ in PERIODS} for base in BASKETS}
    if not days:
        empty_rates["BIGMAC"] = bigmac_local
        return {"as_of": None, "rates": empty_rates, "changes": empty_changes}

    latest_day = None
    current = empty_rates
    for day in reversed(days):
        current = local_costs(series[day], code, oil_usd=oil_usd, bigmac_local=bigmac_local)
        if current.get("USD") is not None:
            latest_day = day
            break
    if latest_day is None:
        current["BIGMAC"] = bigmac_local
        return {"as_of": None, "rates": current, "changes": empty_changes}

    latest = date.fromisoformat(latest_day)
    changes = {base: {} for base in BASKETS}
    for key, offset in PERIODS:
        past_day = _close_on_or_before(days, latest - timedelta(days=offset))
        past = local_costs(series[past_day], code, oil_usd=oil_usd, bigmac_local=None) if past_day else empty_rates
        for base in BASKETS:
            if base not in CHANGE_HORIZONS:
                changes[base][key] = None
            else:
                changes[base][key] = _pct_change(current.get(base), past.get(base))
    return {"as_of": latest_day, "rates": current, "changes": changes}


def parse_cnbc_last(payload: dict[str, Any] | None) -> float | None:
    quotes = ((payload or {}).get("FormattedQuoteResult") or {}).get("FormattedQuote") or []
    if not quotes:
        return None
    return _as_float((quotes[0] or {}).get("last"))


def parse_big_mac_prices(text: str) -> dict[str, float]:
    rows = list(csv.DictReader(io.StringIO(text or "")))
    latest: dict[str, tuple[str, float]] = {}
    for row in rows:
        code = (row.get("currency_code") or "").strip().upper()
        price = _as_float(row.get("local_price"))
        day = row.get("date") or ""
        if not code or price is None:
            continue
        if code == "EUR" and (row.get("iso_a3") or "") not in ("EUZ", "EU", "EMU"):
            continue
        prev = latest.get(code)
        if prev is None or day >= prev[0]:
            latest[code] = (day, price)
    return {code: price for code, (_day, price) in latest.items()}


def fetch_oil_usd() -> float | None:
    try:
        response = requests.get(
            CNBC_QUOTE,
            params={
                "symbols": "@CL.1",
                "requestMethod": "itv",
                "noform": "1",
                "partnerId": "2",
                "output": "json",
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return parse_cnbc_last(response.json())
    except Exception as exc:
        log.warning("[currencies] CNBC oil quote failed: %s", exc)
        return None


def fetch_big_mac_prices() -> dict[str, float]:
    try:
        response = requests.get(BIGMAC_CSV, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return parse_big_mac_prices(response.text)
    except Exception as exc:
        log.warning("[currencies] Big Mac Index failed: %s", exc)
        return {}


def fetch_frankfurter_history(codes: list[str]) -> list[dict[str, Any]]:
    quotes = sorted({code.upper() for code in codes if code.upper() != "USD"} | {"EUR", "JPY", "XAU"})
    start = (datetime.now(timezone.utc).date() - timedelta(days=1900)).isoformat()
    response = requests.get(
        FRANKFURTER_RATES,
        params={"base": "USD", "quotes": ",".join(quotes), "from": start},
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Frankfurter rates response was not a list")
    return payload


def _pin_color(day_change: float | None) -> str:
    """More local units per 1 USD means a weaker currency → red."""
    if day_change is None:
        return "#94a3b8"
    if day_change > 0:
        return "#ef4444"
    if day_change < 0:
        return "#22c55e"
    return "#94a3b8"


def _load_currencies() -> dict[str, Any]:
    codes = [row["code"] for row in WORLD_CURRENCIES]
    try:
        series = parse_frankfurter_rates(fetch_frankfurter_history(codes))
    except Exception as exc:
        log.warning("[currencies] Frankfurter request failed: %s", exc)
        series = {}
    oil_usd = fetch_oil_usd()
    bigmac = fetch_big_mac_prices()

    rows = []
    as_of = None
    for entry in WORLD_CURRENCIES:
        quote = quote_from_series(
            series,
            entry["code"],
            oil_usd=oil_usd,
            bigmac_local=bigmac.get(entry["code"]),
        )
        as_of = as_of or quote["as_of"]
        day = (quote["changes"].get("USD") or {}).get("1d")
        rows.append({
            **entry,
            "rates": quote["rates"],
            "changes": quote["changes"],
            "as_of": quote["as_of"],
            "color": _pin_color(day),
            "source": SOURCE["name"],
            "source_url": SOURCE["url"],
        })
    return {
        "count": len(rows),
        "as_of": as_of,
        "oil_usd": oil_usd,
        "currencies": rows,
        "source": SOURCE,
        "sources": SOURCES,
    }


def list_currencies(force_refresh: bool = False) -> dict[str, Any]:
    return get_or_set("currencies", _load_currencies, force_refresh=force_refresh)
