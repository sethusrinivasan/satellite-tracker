"""Major stock-market index pins from CNBC quotes plus Yahoo daily history."""

from __future__ import annotations

import csv
import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

from app.services import overlay_http
from app.services.overlay_cache import get_fresh, get_or_set, get_stale, store

log = logging.getLogger(__name__)

CNBC_QUOTE = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
CNBC_HOME = "https://www.cnbc.com"
NASDAQ_HIST = "https://api.nasdaq.com/api/quote/{symbol}/historical"
NASDAQ_HOME = "https://www.nasdaq.com"
STOOQ_DAILY = "https://stooq.com/q/d/l/"
STOOQ_HOME = "https://stooq.com"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"
YAHOO_HOME = "https://finance.yahoo.com"
REQUEST_TIMEOUT = 12
HIST_TIMEOUT = 18
HIST_WORKERS = 8
HIST_NS = "markets-hist"
CACHE_NS = "markets"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SatTrack/1.0; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json,text/csv,text/plain,*/*",
}
NASDAQ_HEADERS = {
    **HEADERS,
    "Referer": "https://www.nasdaq.com/",
}

SOURCE = {
    "name": "CNBC",
    "url": CNBC_HOME,
    "license": "Public quote widget; no API key",
    "attribution": (
        "Index levels and 1-day % from CNBC public quotes. "
        "7d / 30d / 1q / 6m / 1y / 2y / 5y / 10y % are computed locally from Yahoo Finance daily closes."
    ),
}
YAHOO_SOURCE = {
    "name": "Yahoo Finance",
    "url": YAHOO_HOME,
    "license": "Public chart endpoint; no API key",
    "attribution": (
        "Daily historical closes from Yahoo Finance. Period changes are calculated "
        "on this server from those closes, not from a paid market-data feed."
    ),
}
SOURCES = [SOURCE, YAHOO_SOURCE]

# Confirmed CNBC public index symbols. nasdaq_* is optional history (index or ETF proxy).
TOP_MARKETS: list[dict[str, Any]] = [
    {"rank": 1, "exchange": "NYSE", "city": "New York", "lat": 40.7069, "lng": -74.0113,
     "cnbc": ".SPX", "index": "S&P 500", "market_cap_tn": 28.0, "nasdaq": "SPY", "nasdaq_class": "etf"},
    {"rank": 2, "exchange": "Nasdaq", "city": "New York", "lat": 40.7580, "lng": -73.9855,
     "cnbc": ".IXIC", "index": "Nasdaq Composite", "market_cap_tn": 26.0, "nasdaq": "COMP", "nasdaq_class": "index"},
    {"rank": 3, "exchange": "Shanghai Stock Exchange", "city": "Shanghai", "lat": 31.2397, "lng": 121.4998,
     "cnbc": ".SSEC", "index": "SSE Composite", "market_cap_tn": 7.2, "nasdaq": "ASHR", "nasdaq_class": "etf"},
    {"rank": 4, "exchange": "Euronext", "city": "Paris", "lat": 48.8698, "lng": 2.3078,
     "cnbc": ".FCHI", "index": "CAC 40", "market_cap_tn": 7.0, "nasdaq": "EWQ", "nasdaq_class": "etf"},
    {"rank": 5, "exchange": "Japan Exchange Group", "city": "Tokyo", "lat": 35.6828, "lng": 139.7590,
     "cnbc": ".N225", "index": "Nikkei 225", "market_cap_tn": 6.5, "nasdaq": "EWJ", "nasdaq_class": "etf"},
    {"rank": 6, "exchange": "Shenzhen Stock Exchange", "city": "Shenzhen", "lat": 22.5431, "lng": 114.0579,
     "cnbc": ".SZI", "index": "SZSE Component", "market_cap_tn": 6.0, "nasdaq": "CNXT", "nasdaq_class": "etf"},
    {"rank": 7, "exchange": "Hong Kong Exchanges", "city": "Hong Kong", "lat": 22.3193, "lng": 114.1694,
     "cnbc": ".HSI", "index": "Hang Seng", "market_cap_tn": 4.5, "nasdaq": "EWH", "nasdaq_class": "etf"},
    {"rank": 8, "exchange": "NSE India", "city": "Mumbai", "lat": 19.0760, "lng": 72.8777,
     "cnbc": ".NSEI", "index": "Nifty 50", "market_cap_tn": 4.4, "nasdaq": "INDA", "nasdaq_class": "etf"},
    {"rank": 9, "exchange": "London Stock Exchange", "city": "London", "lat": 51.5145, "lng": -0.0930,
     "cnbc": ".FTSE", "index": "FTSE 100", "market_cap_tn": 3.4, "nasdaq": "EWU", "nasdaq_class": "etf"},
    {"rank": 10, "exchange": "Deutsche Börse", "city": "Frankfurt", "lat": 50.1155, "lng": 8.6822,
     "cnbc": ".GDAXI", "index": "DAX", "market_cap_tn": 2.3, "nasdaq": "EWG", "nasdaq_class": "etf"},
    {"rank": 11, "exchange": "TMX Group", "city": "Toronto", "lat": 43.6487, "lng": -79.3803,
     "cnbc": ".GSPTSE", "index": "S&P/TSX Composite", "market_cap_tn": 3.2, "nasdaq": "EWC", "nasdaq_class": "etf"},
    {"rank": 12, "exchange": "Korea Exchange", "city": "Seoul", "lat": 37.5220, "lng": 126.9270,
     "cnbc": ".KS11", "index": "KOSPI", "market_cap_tn": 1.8, "nasdaq": "EWY", "nasdaq_class": "etf"},
    {"rank": 13, "exchange": "Taiwan Stock Exchange", "city": "Taipei", "lat": 25.0330, "lng": 121.5654,
     "cnbc": ".TWII", "index": "TAIEX", "market_cap_tn": 1.8, "nasdaq": "EWT", "nasdaq_class": "etf"},
    {"rank": 14, "exchange": "ASX", "city": "Sydney", "lat": -33.8688, "lng": 151.2093,
     "cnbc": ".AXJO", "index": "S&P/ASX 200", "market_cap_tn": 1.7, "nasdaq": "EWA", "nasdaq_class": "etf"},
    {"rank": 15, "exchange": "SIX Swiss Exchange", "city": "Zurich", "lat": 47.3769, "lng": 8.5417,
     "cnbc": ".SSMI", "index": "SMI", "market_cap_tn": 1.8, "nasdaq": "EWL", "nasdaq_class": "etf"},
    {"rank": 16, "exchange": "B3", "city": "São Paulo", "lat": -23.5505, "lng": -46.6333,
     "cnbc": ".BVSP", "index": "Bovespa", "market_cap_tn": 0.9, "nasdaq": "EWZ", "nasdaq_class": "etf"},
    {"rank": 17, "exchange": "BME", "city": "Madrid", "lat": 40.4168, "lng": -3.7038,
     "cnbc": ".IBEX", "index": "IBEX 35", "market_cap_tn": 0.9, "nasdaq": "EWP", "nasdaq_class": "etf"},
    {"rank": 18, "exchange": "Borsa Italiana", "city": "Milan", "lat": 45.4654, "lng": 9.1859,
     "cnbc": ".FTMIB", "index": "FTSE MIB", "market_cap_tn": 0.8, "nasdaq": "EWI", "nasdaq_class": "etf"},
    {"rank": 19, "exchange": "Euronext Amsterdam", "city": "Amsterdam", "lat": 52.3676, "lng": 4.9041,
     "cnbc": ".AEX", "index": "AEX", "market_cap_tn": 0.8, "nasdaq": "EWN", "nasdaq_class": "etf"},
    {"rank": 20, "exchange": "Nasdaq Stockholm", "city": "Stockholm", "lat": 59.3293, "lng": 18.0686,
     "cnbc": ".OMXS30", "index": "OMX Stockholm 30", "market_cap_tn": 0.8, "nasdaq": "EWD", "nasdaq_class": "etf"},
    {"rank": 21, "exchange": "Borsa Istanbul", "city": "Istanbul", "lat": 41.0082, "lng": 28.9784,
     "cnbc": ".XU100", "index": "BIST 100", "market_cap_tn": 0.3, "nasdaq": "TUR", "nasdaq_class": "etf"},
    {"rank": 22, "exchange": "Bolsa Mexicana", "city": "Mexico City", "lat": 19.4326, "lng": -99.1332,
     "cnbc": ".MXX", "index": "S&P/BMV IPC", "market_cap_tn": 0.4, "nasdaq": "EWW", "nasdaq_class": "etf"},
    {"rank": 23, "exchange": "SGX", "city": "Singapore", "lat": 1.3521, "lng": 103.8198,
     "cnbc": ".STI", "index": "Straits Times", "market_cap_tn": 0.6, "nasdaq": "EWS", "nasdaq_class": "etf"},
    {"rank": 24, "exchange": "SET", "city": "Bangkok", "lat": 13.7563, "lng": 100.5018,
     "cnbc": ".SETI", "index": "SET Composite", "market_cap_tn": 0.5, "nasdaq": "THD", "nasdaq_class": "etf"},
    {"rank": 25, "exchange": "Bursa Malaysia", "city": "Kuala Lumpur", "lat": 3.1390, "lng": 101.6869,
     "cnbc": ".KLSE", "index": "FTSE KLCI", "market_cap_tn": 0.4, "nasdaq": "EWM", "nasdaq_class": "etf"},
    {"rank": 26, "exchange": "PSE", "city": "Manila", "lat": 14.5995, "lng": 120.9842,
     "cnbc": ".PSI", "index": "PSEi", "market_cap_tn": 0.3},
    {"rank": 27, "exchange": "HOSE", "city": "Ho Chi Minh City", "lat": 10.8231, "lng": 106.6297,
     "cnbc": ".VNI", "index": "VN-Index", "market_cap_tn": 0.2},
    {"rank": 28, "exchange": "NZX", "city": "Auckland", "lat": -36.8485, "lng": 174.7633,
     "cnbc": ".NZ50", "index": "S&P/NZX 50", "market_cap_tn": 0.1, "nasdaq": "ENZL", "nasdaq_class": "etf"},
    {"rank": 29, "exchange": "TASE", "city": "Tel Aviv", "lat": 32.0853, "lng": 34.7818,
     "cnbc": ".TA35", "index": "TA-35", "market_cap_tn": 0.3, "nasdaq": "EIS", "nasdaq_class": "etf"},
    {"rank": 30, "exchange": "EGX", "city": "Cairo", "lat": 30.0444, "lng": 31.2357,
     "cnbc": ".EGX30", "index": "EGX 30", "market_cap_tn": 0.05},
    {"rank": 31, "exchange": "DFM", "city": "Dubai", "lat": 25.2048, "lng": 55.2708,
     "cnbc": ".DFMGI", "index": "DFM General", "market_cap_tn": 0.2},
    {"rank": 32, "exchange": "MSX", "city": "Muscat", "lat": 23.5880, "lng": 58.3829,
     "cnbc": ".MSM30", "index": "MSX 30", "market_cap_tn": 0.02},
    {"rank": 33, "exchange": "BYMA", "city": "Buenos Aires", "lat": -34.6037, "lng": -58.3816,
     "cnbc": ".MERV", "index": "S&P Merval", "market_cap_tn": 0.06, "nasdaq": "ARGT", "nasdaq_class": "etf"},
    {"rank": 34, "exchange": "bvc", "city": "Bogotá", "lat": 4.7110, "lng": -74.0721,
     "cnbc": ".COLCAP", "index": "MSCI COLCAP", "market_cap_tn": 0.08},
    {"rank": 35, "exchange": "Euronext Brussels", "city": "Brussels", "lat": 50.8503, "lng": 4.3517,
     "cnbc": ".BFX", "index": "BEL 20", "market_cap_tn": 0.4},
    {"rank": 36, "exchange": "Euronext Lisbon", "city": "Lisbon", "lat": 38.7223, "lng": -9.1393,
     "cnbc": ".PSI20", "index": "PSI 20", "market_cap_tn": 0.08},
    {"rank": 37, "exchange": "Euronext Dublin", "city": "Dublin", "lat": 53.3498, "lng": -6.2603,
     "cnbc": ".ISEQ", "index": "ISEQ Overall", "market_cap_tn": 0.15},
    {"rank": 38, "exchange": "Oslo Børs", "city": "Oslo", "lat": 59.9139, "lng": 10.7522,
     "cnbc": ".OSEBX", "index": "OSEBX", "market_cap_tn": 0.3, "nasdaq": "NORW", "nasdaq_class": "etf"},
    {"rank": 39, "exchange": "Nasdaq Helsinki", "city": "Helsinki", "lat": 60.1699, "lng": 24.9384,
     "cnbc": ".OMXH25", "index": "OMX Helsinki 25", "market_cap_tn": 0.3},
    {"rank": 40, "exchange": "PSE Prague", "city": "Prague", "lat": 50.0755, "lng": 14.4378,
     "cnbc": ".PX", "index": "PX", "market_cap_tn": 0.05},
    {"rank": 41, "exchange": "BSE Budapest", "city": "Budapest", "lat": 47.4979, "lng": 19.0402,
     "cnbc": ".BUX", "index": "BUX", "market_cap_tn": 0.03},
    {"rank": 42, "exchange": "STOXX", "city": "Zurich", "lat": 47.3667, "lng": 8.5500,
     "cnbc": ".STOXX50", "index": "STOXX 50", "market_cap_tn": 0.0, "nasdaq": "FEZ", "nasdaq_class": "etf"},
    {"rank": 43, "exchange": "NYSE", "city": "New York", "lat": 40.7128, "lng": -74.0060,
     "cnbc": ".DJI", "index": "Dow Jones Industrial", "market_cap_tn": 12.0, "nasdaq": "DIA", "nasdaq_class": "etf"},
    {"rank": 44, "exchange": "NYSE", "city": "New York", "lat": 40.7200, "lng": -74.0000,
     "cnbc": ".RUT", "index": "Russell 2000", "market_cap_tn": 2.5, "nasdaq": "IWM", "nasdaq_class": "etf"},
    {"rank": 45, "exchange": "NYSE", "city": "New York", "lat": 40.6900, "lng": -74.0200,
     "cnbc": ".NYA", "index": "NYSE Composite", "market_cap_tn": 25.0},
    {"rank": 46, "exchange": "Nasdaq", "city": "New York", "lat": 40.7500, "lng": -73.9700,
     "cnbc": ".NDX", "index": "Nasdaq-100", "market_cap_tn": 20.0, "nasdaq": "QQQ", "nasdaq_class": "etf"},
    {"rank": 47, "exchange": "NYSE", "city": "New York", "lat": 40.7300, "lng": -74.0300,
     "cnbc": ".MID", "index": "S&P MidCap 400", "market_cap_tn": 2.0, "nasdaq": "MDY", "nasdaq_class": "etf"},
    {"rank": 48, "exchange": "NYSE", "city": "New York", "lat": 40.7000, "lng": -73.9900,
     "cnbc": ".SML", "index": "S&P SmallCap 600", "market_cap_tn": 1.0, "nasdaq": "IJR", "nasdaq_class": "etf"},
    {"rank": 49, "exchange": "Nasdaq", "city": "Philadelphia", "lat": 39.9526, "lng": -75.1652,
     "cnbc": ".SOX", "index": "PHLX Semiconductor", "market_cap_tn": 0.0, "nasdaq": "SMH", "nasdaq_class": "etf"},
    {"rank": 50, "exchange": "LSE", "city": "London", "lat": 51.5074, "lng": -0.1400,
     "cnbc": ".FTMC", "index": "FTSE 250", "market_cap_tn": 0.5},
    {"rank": 51, "exchange": "JPX", "city": "Tokyo", "lat": 35.6895, "lng": 139.6917,
     "cnbc": ".TOPX", "index": "TOPIX", "market_cap_tn": 6.0},
    {"rank": 52, "exchange": "HKEX", "city": "Hong Kong", "lat": 22.2800, "lng": 114.1600,
     "cnbc": ".HSTECH", "index": "Hang Seng Tech", "market_cap_tn": 0.8},
    {"rank": 53, "exchange": "HKEX", "city": "Hong Kong", "lat": 22.3000, "lng": 114.1800,
     "cnbc": ".HSCE", "index": "HSCEI", "market_cap_tn": 1.0},
    {"rank": 54, "exchange": "SET", "city": "Bangkok", "lat": 13.7300, "lng": 100.5300,
     "cnbc": ".SET50", "index": "SET 50", "market_cap_tn": 0.3},
    {"rank": 55, "exchange": "TASE", "city": "Tel Aviv", "lat": 32.0700, "lng": 34.7900,
     "cnbc": ".TA125", "index": "TA-125", "market_cap_tn": 0.3},
    {"rank": 56, "exchange": "Borsa Istanbul", "city": "Istanbul", "lat": 41.0200, "lng": 28.9600,
     "cnbc": ".XU030", "index": "BIST 30", "market_cap_tn": 0.2},
    {"rank": 57, "exchange": "Oslo Børs", "city": "Oslo", "lat": 59.9100, "lng": 10.7400,
     "cnbc": ".OBX", "index": "OBX", "market_cap_tn": 0.2},
    {"rank": 58, "exchange": "Nasdaq Helsinki", "city": "Helsinki", "lat": 60.1800, "lng": 24.9500,
     "cnbc": ".HEX", "index": "OMX Helsinki All Share", "market_cap_tn": 0.3},
    {"rank": 59, "exchange": "JPX", "city": "Tokyo", "lat": 35.6700, "lng": 139.7700,
     "cnbc": ".N300", "index": "Nikkei 300", "market_cap_tn": 5.0},
    {"rank": 60, "exchange": "LSE AIM", "city": "London", "lat": 51.5200, "lng": -0.0900,
     "cnbc": ".FTAI", "index": "FTSE AIM All-Share", "market_cap_tn": 0.1},
    {"rank": 61, "exchange": "NYSE", "city": "New York", "lat": 40.7400, "lng": -73.9800,
     "cnbc": ".RUA", "index": "Russell 3000", "market_cap_tn": 45.0},
]

PERIODS = (
    ("1d", 1),
    ("7d", 7),
    ("30d", 30),
    ("1q", 91),
    ("6m", 182),
    ("1y", 365),
    ("2y", 730),
    ("5y", 1826),
    ("10y", 3650),
)

# Yahoo Finance chart symbols (or a close ETF proxy) keyed by CNBC index symbol.
YAHOO_HISTORY: dict[str, str] = {
    ".SPX": "^GSPC",
    ".IXIC": "^IXIC",
    ".SSEC": "000001.SS",
    ".FCHI": "^FCHI",
    ".N225": "^N225",
    ".SZI": "399001.SZ",
    ".HSI": "^HSI",
    ".NSEI": "^NSEI",
    ".FTSE": "^FTSE",
    ".GDAXI": "^GDAXI",
    ".GSPTSE": "^GSPTSE",
    ".KS11": "^KS11",
    ".TWII": "^TWII",
    ".AXJO": "^AXJO",
    ".SSMI": "^SSMI",
    ".BVSP": "^BVSP",
    ".IBEX": "^IBEX",
    ".FTMIB": "FTSEMIB.MI",
    ".AEX": "^AEX",
    ".OMXS30": "^OMX",
    ".XU100": "XU100.IS",
    ".MXX": "^MXX",
    ".STI": "^STI",
    ".SETI": "THD",
    ".KLSE": "^KLSE",
    ".PSI": "PSEI.PS",
    ".VNI": "VNM",
    ".NZ50": "^NZ50",
    ".TA35": "TA35.TA",
    ".EGX30": "^CASE30",
    ".DFMGI": "DFMGI.AE",
    ".MERV": "^MERV",
    ".BFX": "^BFX",
    ".PSI20": "PSI20.LS",
    ".ISEQ": "^ISEQ",
    ".OSEBX": "OSEBX.OL",
    ".OMXH25": "^OMXH25",
    ".STOXX50": "^STOXX50E",
    ".DJI": "^DJI",
    ".RUT": "^RUT",
    ".NYA": "^NYA",
    ".NDX": "^NDX",
    ".MID": "^MID",
    ".SML": "IJR",
    ".SOX": "^SOX",
    ".FTMC": "^FTMC",
    ".TOPX": "1306.T",
    ".HSTECH": "3067.HK",
    ".HSCE": "^HSCE",
    ".SET50": "THD",
    ".XU030": "XU030.IS",
    ".OBX": "OBX.OL",
    ".HEX": "^OMXHPI",
    ".N300": "^N300",
    ".FTAI": "^FTAI",
    ".RUA": "^RUA",
}
ETF_PROXIES = {"THD", "VNM", "IJR", "1306.T", "3067.HK"}


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("%", "").replace("+", "").strip()
    if not text or text.upper() in {"UNCH", "NA", "N/A", "--"}:
        return 0.0 if text.upper() == "UNCH" else None
    try:
        return float(text)
    except ValueError:
        return None


def _pct_change(current: float | None, past: float | None) -> float | None:
    if current is None or past is None or past == 0:
        return None
    return round((current - past) / past * 100.0, 2)


def _slop_days(horizon_days: int) -> int:
    return max(5, min(45, int(horizon_days) // 8 or 5))


def _close_on_or_before(
    points: list[tuple[float, float]],
    target: datetime,
    slop_days: int = 21,
) -> float | None:
    target_ts = target.timestamp()
    chosen: tuple[float, float] | None = None
    for ts, close in points:
        if ts <= target_ts:
            chosen = (ts, close)
        else:
            break
    if chosen is None:
        return None
    if target_ts - chosen[0] > slop_days * 86400:
        return None
    return chosen[1]


def parse_stooq_csv(text: str) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    if not text or "no data" in text.lower():
        return points
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if not row or str(row[0]).lower().startswith("date"):
            continue
        if len(row) < 5:
            continue
        try:
            day = datetime.strptime(row[0].strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            close = float(row[4])
        except (ValueError, TypeError):
            continue
        points.append((day.timestamp(), close))
    points.sort(key=lambda item: item[0])
    return points


def parse_cnbc_quotes(payload: dict[str, Any] | None) -> dict[str, dict[str, float | None]]:
    out: dict[str, dict[str, float | None]] = {}
    quotes = ((payload or {}).get("FormattedQuoteResult") or {}).get("FormattedQuote") or []
    for quote in quotes:
        symbol = str((quote or {}).get("symbol") or "").upper()
        last = _as_float((quote or {}).get("last"))
        if not symbol or last is None:
            continue
        change = (quote or {}).get("change_pct")
        day = 0.0 if str(change or "").upper() == "UNCH" else _as_float(change)
        out[symbol] = {"last": last, "change_pct": day}
    return out


def parse_nasdaq_history(payload: dict[str, Any] | None) -> list[tuple[float, float]]:
    rows = (((payload or {}).get("data") or {}).get("tradesTable") or {}).get("rows") or []
    points: list[tuple[float, float]] = []
    for row in rows:
        try:
            day = datetime.strptime(str(row.get("date") or ""), "%m/%d/%Y").replace(tzinfo=timezone.utc)
            close = _as_float(row.get("close"))
        except (ValueError, TypeError):
            continue
        if close is None:
            continue
        points.append((day.timestamp(), close))
    points.sort(key=lambda item: item[0])
    return points


def fetch_cnbc_quotes(symbols: list[str]) -> dict[str, dict[str, float | None]]:
    if not symbols:
        return {}
    payload = overlay_http.get_json(
        CNBC_QUOTE,
        params={
            "symbols": "|".join(symbols),
            "requestMethod": "itv",
            "noform": "1",
            "partnerId": "2",
            "output": "json",
        },
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        source="markets",
    )
    if payload is None:
        return {}
    try:
        return parse_cnbc_quotes(payload)
    except Exception as exc:
        log.warning("[markets] CNBC quotes failed: %s", exc)
        return {}


def parse_yahoo_chart(payload: dict[str, Any] | None) -> list[tuple[float, float]]:
    result = ((payload or {}).get("chart") or {}).get("result") or []
    if not result:
        return []
    row = result[0] or {}
    timestamps = row.get("timestamp") or []
    closes = ((row.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    points: list[tuple[float, float]] = []
    for ts, close in zip(timestamps, closes):
        if ts is None or close is None:
            continue
        try:
            points.append((float(ts), float(close)))
        except (TypeError, ValueError):
            continue
    points.sort(key=lambda item: item[0])
    return points


def _as_points(payload: Any) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for row in payload or []:
        try:
            points.append((float(row[0]), float(row[1])))
        except (TypeError, ValueError, IndexError):
            continue
    return points


def fetch_yahoo_history(symbol: str) -> list[tuple[float, float]]:
    if not symbol:
        return []
    if overlay_http.remaining_backoff(YAHOO_CHART) > 0:
        return _as_points(get_stale(HIST_NS, key=symbol))
    fresh = get_fresh(HIST_NS, key=symbol)
    if fresh:
        return _as_points(fresh)
    payload = overlay_http.get_json(
        f"{YAHOO_CHART}{quote(symbol, safe='')}",
        params={"range": "10y", "interval": "1d", "includeAdjustedClose": "true"},
        headers=HEADERS,
        timeout=HIST_TIMEOUT,
        source="markets",
    )
    points = parse_yahoo_chart(payload if isinstance(payload, dict) else None)
    if points:
        store(HIST_NS, [[ts, close] for ts, close in points], key=symbol)
        return points
    return _as_points(get_stale(HIST_NS, key=symbol))


def apply_history(row: dict[str, Any], points: list[tuple[float, float]]) -> dict[str, Any]:
    quote = _quote_from_points(points)
    changes = dict(row.get("changes") or {})
    for key, value in (quote.get("changes") or {}).items():
        if key == "1d" and changes.get("1d") is not None:
            continue
        changes[key] = value
    row["changes"] = changes
    if row.get("value") is None and quote.get("value") is not None:
        row["value"] = quote["value"]
    row["color"] = _pin_color(changes.get("1d"))
    yahoo = YAHOO_HISTORY.get(str(row.get("cnbc") or "").upper()) or ""
    row["history_source"] = YAHOO_SOURCE["name"]
    row["history_symbol"] = yahoo
    row["history_proxy"] = yahoo in ETF_PROXIES
    return row


def fetch_nasdaq_history(symbol: str, asset_class: str, days: int = 400) -> list[tuple[float, float]]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days + 20)
    try:
        payload = overlay_http.get_json(
            NASDAQ_HIST.format(symbol=symbol),
            params={
                "assetclass": asset_class,
                "fromdate": start.isoformat(),
                "todate": end.isoformat(),
                "limit": "3000" if days > 1000 else "500",
            },
            headers=NASDAQ_HEADERS,
            timeout=HIST_TIMEOUT,
            source="markets",
            throttle_timeouts=False,
        )
        if payload is None:
            return []
        return parse_nasdaq_history(payload)
    except Exception as exc:
        log.warning("[markets] Nasdaq history failed for %s: %s", symbol, exc)
        return []


def _quote_from_points(points: list[tuple[float, float]]) -> dict[str, Any]:
    empty = {"value": None, "currency": None, "changes": {key: None for key, _ in PERIODS}}
    if not points:
        return empty
    current = float(points[-1][1])
    now = datetime.now(timezone.utc)
    changes = {}
    for key, days in PERIODS:
        past = _close_on_or_before(
            points,
            now - timedelta(days=days),
            slop_days=_slop_days(days),
        )
        changes[key] = _pct_change(current, past)
    return {
        "value": round(current, 2),
        "currency": None,
        "changes": changes,
    }


def _pin_color(day: float | None) -> str:
    if day is None:
        return "#94a3b8"
    if day > 0:
        return "#22c55e"
    if day < 0:
        return "#ef4444"
    return "#94a3b8"


def _market_rows(quotes: dict[str, dict[str, float | None]]) -> list[dict[str, Any]]:
    rows = []
    for entry in TOP_MARKETS:
        cnbc = quotes.get(str(entry.get("cnbc") or "").upper()) or {}
        last = cnbc.get("last")
        changes = {key: None for key, _ in PERIODS}
        if cnbc.get("change_pct") is not None:
            changes["1d"] = round(float(cnbc["change_pct"]), 2)
        rows.append({
            **entry,
            "symbol": entry.get("cnbc"),
            "value": round(float(last), 2) if last is not None else None,
            "currency": None,
            "changes": changes,
            "color": _pin_color(changes.get("1d")),
            "source": SOURCE["name"],
            "source_url": SOURCE["url"],
            "history_source": None,
            "history_symbol": None,
            "history_proxy": False,
            "as_of": datetime.now(timezone.utc).isoformat(),
        })
    return rows


def _fill_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    jobs: dict[Any, int] = {}
    with ThreadPoolExecutor(max_workers=HIST_WORKERS) as pool:
        for index, row in enumerate(rows):
            symbol = YAHOO_HISTORY.get(str(row.get("cnbc") or "").upper())
            if not symbol:
                continue
            jobs[pool.submit(fetch_yahoo_history, symbol)] = index
        done = 0
        for future in as_completed(jobs):
            index = jobs[future]
            try:
                points = future.result() or []
            except Exception as exc:
                log.warning("[markets] History failed for %s: %s", rows[index].get("index"), exc)
                points = []
            if points:
                apply_history(rows[index], points)
            done += 1
            if done == 1 or done % 8 == 0 or done == len(jobs):
                store(CACHE_NS, rows)
                log.info("[markets] History %s/%s indexes", done, len(jobs))
    return rows


def _load_market_indices() -> list[dict[str, Any]] | None:
    quotes = fetch_cnbc_quotes([entry["cnbc"] for entry in TOP_MARKETS if entry.get("cnbc")])
    rows = _market_rows(quotes)
    store(CACHE_NS, rows)
    log.info("[markets] CNBC quotes for %s indexes; loading Yahoo daily history", sum(1 for row in rows if row.get("value") is not None))
    rows = _fill_history(rows)
    if not quotes and not any(row.get("value") is not None for row in rows):
        return None
    return rows


def list_market_indices(force_refresh: bool = False) -> list[dict[str, Any]]:
    data = get_or_set(
        CACHE_NS,
        _load_market_indices,
        force_refresh=force_refresh,
        skeleton=_market_rows({}),
    )
    return list(data or [])
