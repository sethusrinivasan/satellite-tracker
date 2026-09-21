"""Geo-tagged news pins from free, attributed feeds (last 24 hours)."""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from xml.etree import ElementTree as ET

from app.services import overlay_http
from app.services.geo_query_service import COUNTRY_CENTERS
from app.services.overlay_cache import (
    PENDING_TTL_SECONDS,
    get_fresh,
    get_stale,
    store,
)

log = logging.getLogger(__name__)

GDACS_EVENTS = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GDACS_HOME = "https://www.gdacs.org"
UN_NEWS_FEED = "https://news.un.org/feed/subscribe/en/news/all/rss.xml"
UN_NEWS_HOME = "https://news.un.org"
GLOBAL_VOICES_FEED = "https://globalvoices.org/feed/"
GLOBAL_VOICES_HOME = "https://globalvoices.org"
CONVERSATION_FEED = "https://theconversation.com/global/articles.atom"
CONVERSATION_HOME = "https://theconversation.com"
DW_FEED = "https://rss.dw.com/rdf/rss-en-all"
DW_HOME = "https://www.dw.com"
REQUEST_TIMEOUT = 18
MAX_PINS = 100
MAX_LINKS = 2
TITLE_LIMIT = 80
NEWS_HOURS = 24
CACHE_NS = "news"

JSON_HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json,application/geo+json,*/*",
}
FEED_HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}

GDACS_SOURCE = {
    "name": "GDACS",
    "url": GDACS_HOME,
    "license": "Public disaster alerts",
    "attribution": (
        "Disaster and humanitarian alerts from the Global Disaster Alert and "
        "Coordination System (GDACS). Title links open the GDACS report."
    ),
}
UN_SOURCE = {
    "name": "UN News",
    "url": UN_NEWS_HOME,
    "license": "UN copyright; attribution required",
    "attribution": (
        "Headlines from UN News. Pins use places named in the story; the title "
        "opens the UN article."
    ),
}
GV_SOURCE = {
    "name": "Global Voices",
    "url": GLOBAL_VOICES_HOME,
    "license": "CC BY 3.0",
    "attribution": (
        "Citizen media from Global Voices (CC BY 3.0). Pins use story categories "
        "and place names; the title opens the article."
    ),
}
CONVERSATION_SOURCE = {
    "name": "The Conversation",
    "url": CONVERSATION_HOME,
    "license": "CC BY-ND",
    "attribution": (
        "Analysis from The Conversation (CC BY-ND). Pins use places named in the "
        "headline or summary; the title opens the article."
    ),
}
DW_SOURCE = {
    "name": "Deutsche Welle",
    "url": DW_HOME,
    "license": "RSS headlines with attribution",
    "attribution": (
        "World headlines from Deutsche Welle RSS. Pins use places named in the "
        "story; the title opens the DW article."
    ),
}
SOURCES = [GDACS_SOURCE, UN_SOURCE, GV_SOURCE, CONVERSATION_SOURCE, DW_SOURCE]
SOURCE = GDACS_SOURCE

ARTICLE_FEEDS = [
    {"id": "un-news", "source": UN_SOURCE, "url": UN_NEWS_FEED, "region": ""},
    {"id": "global-voices", "source": GV_SOURCE, "url": GLOBAL_VOICES_FEED, "region": ""},
    {"id": "conversation", "source": CONVERSATION_SOURCE, "url": CONVERSATION_FEED, "region": ""},
    {"id": "dw", "source": DW_SOURCE, "url": DW_FEED, "region": ""},
]

GDACS_LABELS = {
    "EQ": "Earthquake",
    "TC": "Tropical cyclone",
    "FL": "Flood",
    "VO": "Volcano",
    "DR": "Drought",
    "WF": "Wildfire",
}

ARTICLE_RE = re.compile(
    r'<a[^>]+href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")
US_RE = re.compile(r"(?<![A-Za-z])U\.?S\.?A?\.?(?![A-Za-z])", re.IGNORECASE)
UK_RE = re.compile(r"(?<![A-Za-z])U\.?K\.?(?![A-Za-z])", re.IGNORECASE)
GEO_POINT_RE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)",
)

# Extra countries, territories, cities, and regions used to pin headlines.
# kind: city (most specific), country, region (fallback centroid).
_EXTRA_PLACES: dict[str, tuple[float, float, str]] = {
    "syria": (33.5138, 36.2765, "country"),
    "yemen": (15.3694, 44.1910, "country"),
    "sudan": (15.5007, 32.5599, "country"),
    "south sudan": (4.8594, 31.5719, "country"),
    "myanmar": (19.7633, 96.0785, "country"),
    "burma": (19.7633, 96.0785, "country"),
    "haiti": (18.5944, -72.3074, "country"),
    "venezuela": (10.4806, -66.9036, "country"),
    "lebanon": (33.8938, 35.5018, "country"),
    "libya": (32.8872, 13.1913, "country"),
    "somalia": (2.0469, 45.3182, "country"),
    "ghana": (5.6037, -0.1870, "country"),
    "tanzania": (-6.1630, 35.7516, "country"),
    "uganda": (0.3476, 32.5825, "country"),
    "rwanda": (-1.9441, 30.0619, "country"),
    "kazakhstan": (51.1694, 71.4491, "country"),
    "uzbekistan": (41.2995, 69.2401, "country"),
    "georgia": (41.7151, 44.8271, "country"),
    "armenia": (40.1792, 44.4991, "country"),
    "azerbaijan": (40.4093, 49.8671, "country"),
    "belarus": (53.9006, 27.5590, "country"),
    "moldova": (47.0105, 28.8638, "country"),
    "serbia": (44.7866, 20.4489, "country"),
    "greece": (37.9838, 23.7275, "country"),
    "portugal": (38.7223, -9.1393, "country"),
    "ireland": (53.3498, -6.2603, "country"),
    "belgium": (50.8503, 4.3517, "country"),
    "austria": (48.2082, 16.3738, "country"),
    "czech republic": (50.0755, 14.4378, "country"),
    "czechia": (50.0755, 14.4378, "country"),
    "hungary": (47.4979, 19.0402, "country"),
    "romania": (44.4268, 26.1025, "country"),
    "finland": (60.1699, 24.9384, "country"),
    "denmark": (55.6761, 12.5683, "country"),
    "iceland": (64.1466, -21.9426, "country"),
    "singapore": (1.3521, 103.8198, "country"),
    "malaysia": (3.1390, 101.6869, "country"),
    "cambodia": (11.5564, 104.9282, "country"),
    "laos": (17.9757, 102.6331, "country"),
    "nepal": (27.7172, 85.3240, "country"),
    "sri lanka": (6.9271, 79.8612, "country"),
    "qatar": (25.2854, 51.5310, "country"),
    "kuwait": (29.3759, 47.9774, "country"),
    "oman": (23.5880, 58.3829, "country"),
    "bahrain": (26.2235, 50.5876, "country"),
    "jordan": (31.9454, 35.9284, "country"),
    "palestine": (31.9073, 35.2044, "country"),
    "tunisia": (36.8065, 10.1815, "country"),
    "algeria": (36.7538, 3.0588, "country"),
    "mali": (12.6392, -8.0029, "country"),
    "senegal": (14.7167, -17.4677, "country"),
    "cameroon": (3.8480, 11.5021, "country"),
    "angola": (-8.8390, 13.2894, "country"),
    "mozambique": (-25.9692, 32.5732, "country"),
    "zimbabwe": (-17.8252, 31.0335, "country"),
    "madagascar": (-18.8792, 47.5079, "country"),
    "cuba": (23.1136, -82.3666, "country"),
    "ecuador": (-0.1807, -78.4678, "country"),
    "bolivia": (-16.4897, -68.1193, "country"),
    "uruguay": (-34.9011, -56.1645, "country"),
    "paraguay": (-25.2637, -57.5759, "country"),
    "panama": (8.9824, -79.5199, "country"),
    "costa rica": (9.9281, -84.0907, "country"),
    "guatemala": (14.6349, -90.5069, "country"),
    "honduras": (14.0723, -87.1921, "country"),
    "nicaragua": (12.1150, -86.2362, "country"),
    "dominican republic": (18.4861, -69.9312, "country"),
    "jamaica": (18.0179, -76.8099, "country"),
    "taiwan": (25.0330, 121.5654, "country"),
    "north korea": (39.0392, 125.7625, "country"),
    "dprk": (39.0392, 125.7625, "country"),
    "hong kong": (22.3193, 114.1694, "city"),
    "gaza": (31.5017, 34.4668, "city"),
    "west bank": (31.9522, 35.2332, "region"),
    "vatican": (41.9029, 12.4534, "city"),
    "crimea": (44.9521, 34.1024, "region"),
    "donbas": (48.0159, 37.8028, "region"),
    "darfur": (13.4500, 25.3500, "region"),
    "sahel": (15.0, 10.0, "region"),
    "south china sea": (12.0, 113.0, "region"),
    "taiwan strait": (24.5, 119.5, "region"),
    "ivory coast": (5.3600, -4.0083, "country"),
    "cote d'ivoire": (5.3600, -4.0083, "country"),
    "democratic republic of the congo": (-4.4419, 15.2663, "country"),
    "drc": (-4.4419, 15.2663, "country"),
    "congo": (-4.4419, 15.2663, "country"),
    "kyiv": (50.4501, 30.5234, "city"),
    "kiev": (50.4501, 30.5234, "city"),
    "kharkiv": (49.9935, 36.2304, "city"),
    "odesa": (46.4825, 30.7233, "city"),
    "lviv": (49.8397, 24.0297, "city"),
    "moscow": (55.7558, 37.6173, "city"),
    "tehran": (35.6892, 51.3890, "city"),
    "beijing": (39.9042, 116.4074, "city"),
    "shanghai": (31.2304, 121.4737, "city"),
    "taipei": (25.0330, 121.5654, "city"),
    "pyongyang": (39.0392, 125.7625, "city"),
    "kabul": (34.5553, 69.2075, "city"),
    "baghdad": (33.3152, 44.3661, "city"),
    "beirut": (33.8938, 35.5018, "city"),
    "sanaa": (15.3694, 44.1910, "city"),
    "mogadishu": (2.0469, 45.3182, "city"),
    "caracas": (10.4806, -66.9036, "city"),
    "seoul": (37.5665, 126.9780, "city"),
    "tokyo": (35.6895, 139.6917, "city"),
    "delhi": (28.6139, 77.2090, "city"),
    "new delhi": (28.6139, 77.2090, "city"),
    "mumbai": (19.0760, 72.8777, "city"),
    "lagos": (6.5244, 3.3792, "city"),
    "nairobi": (-1.2921, 36.8219, "city"),
    "cairo": (30.0444, 31.2357, "city"),
    "istanbul": (41.0082, 28.9784, "city"),
    "berlin": (52.5200, 13.4050, "city"),
    "rome": (41.9028, 12.4964, "city"),
    "madrid": (40.4168, -3.7038, "city"),
    "warsaw": (52.2297, 21.0122, "city"),
    "london": (51.5074, -0.1278, "city"),
    "paris": (48.8566, 2.3522, "city"),
    "jerusalem": (31.7683, 35.2137, "city"),
    "tel aviv": (32.0853, 34.7818, "city"),
    "washington": (38.9072, -77.0369, "city"),
    "new york": (40.7128, -74.0060, "city"),
    "los angeles": (34.0522, -118.2437, "city"),
    "chicago": (41.8781, -87.6298, "city"),
    "miami": (25.7617, -80.1918, "city"),
    "houston": (29.7604, -95.3698, "city"),
    "austin": (30.2672, -97.7431, "city"),
    "dallas": (32.7767, -96.7970, "city"),
    "san francisco": (37.7749, -122.4194, "city"),
    "seattle": (47.6062, -122.3321, "city"),
    "boston": (42.3601, -71.0589, "city"),
    "atlanta": (33.7490, -84.3880, "city"),
    "denver": (39.7392, -104.9903, "city"),
    "phoenix": (33.4484, -112.0740, "city"),
    "brussels": (50.8503, 4.3517, "city"),
    "geneva": (46.2044, 6.1432, "city"),
    "vienna": (48.2082, 16.3738, "city"),
    "amsterdam": (52.3676, 4.9041, "city"),
    "stockholm": (59.3293, 18.0686, "city"),
    "sydney": (-33.8688, 151.2093, "city"),
    "melbourne": (-37.8136, 144.9631, "city"),
    "toronto": (43.6532, -79.3832, "city"),
    "mexico city": (19.4326, -99.1332, "city"),
    "bogota": (4.7110, -74.0721, "city"),
    "lima": (-12.0464, -77.0428, "city"),
    "santiago": (-33.4489, -70.6693, "city"),
    "buenos aires": (-34.6037, -58.3816, "city"),
    "sao paulo": (-23.5505, -46.6333, "city"),
    "rio de janeiro": (-22.9068, -43.1729, "city"),
    "jakarta": (-6.2088, 106.8456, "city"),
    "manila": (14.5995, 120.9842, "city"),
    "bangkok": (13.7563, 100.5018, "city"),
    "hanoi": (21.0285, 105.8542, "city"),
    "islamabad": (33.6844, 73.0479, "city"),
    "karachi": (24.8607, 67.0011, "city"),
    "dhaka": (23.8103, 90.4125, "city"),
    "riyadh": (24.7136, 46.6753, "city"),
    "dubai": (25.2048, 55.2708, "city"),
    "doha": (25.2854, 51.5310, "city"),
    "port-au-prince": (18.5944, -72.3074, "city"),
    "khartoum": (15.5007, 32.5599, "city"),
    "addis ababa": (9.0320, 38.7469, "city"),
    "cape town": (-33.9249, 18.4241, "city"),
    "johannesburg": (-26.2041, 28.0473, "city"),
    "texas": (31.0, -100.0, "region"),
    "california": (36.7783, -119.4179, "region"),
    "florida": (27.6648, -81.5158, "region"),
    "alaska": (64.2008, -149.4937, "region"),
    "hawaii": (20.7967, -156.3319, "region"),
    "africa": (1.0, 17.0, "region"),
    "europe": (50.0, 10.0, "region"),
    "middle east": (29.0, 42.0, "region"),
    "east asia": (35.0, 115.0, "region"),
    "south asia": (23.0, 78.0, "region"),
    "central asia": (43.0, 68.0, "region"),
    "southeast asia": (4.0, 108.0, "region"),
    "asia": (30.0, 100.0, "region"),
    "americas": (10.0, -75.0, "region"),
    "latin america": (-15.0, -60.0, "region"),
    "north america": (40.0, -100.0, "region"),
    "south america": (-15.0, -60.0, "region"),
    "oceania": (-18.0, 150.0, "region"),
    "caribbean": (18.0, -72.0, "region"),
    "balkans": (43.5, 21.0, "region"),
    "sahel": (15.0, 10.0, "region"),
}

_KIND_BONUS = {"city": 8, "country": 4, "region": 0}
_FIELD_BASE = {"title": 30, "category": 20, "summary": 12, "region": 5}
_gazetteer_cache: list[dict[str, Any]] | None = None
_worker_guard = threading.Lock()
_worker: threading.Thread | None = None


def short_title(text: str, limit: int = TITLE_LIMIT) -> str:
    cleaned = TAG_RE.sub(" ", unescape(text or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > limit:
        return cleaned[: limit - 1].rstrip() + "…"
    return cleaned


def articles_from_html(html: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in ARTICLE_RE.finditer(html or ""):
        url = match.group(1).strip()
        title = short_title(match.group(2))
        if not title or url in seen:
            continue
        seen.add(url)
        rows.append({"title": title, "url": url})
        if len(rows) >= MAX_LINKS:
            break
    return rows


def _http_url(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return ""


def _local_tag(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _child_text(element: ET.Element, names: set[str]) -> str:
    wanted = {name.lower() for name in names}
    for child in element:
        if _local_tag(child.tag).lower() in wanted:
            text = (child.text or "").strip()
            if text:
                return text
    return ""


def _child_texts(element: ET.Element, names: set[str]) -> list[str]:
    wanted = {name.lower() for name in names}
    rows: list[str] = []
    for child in element:
        if _local_tag(child.tag).lower() not in wanted:
            continue
        text = (child.text or "").strip()
        if text:
            rows.append(text)
    return rows


def _item_link(element: ET.Element) -> str:
    for child in element:
        if _local_tag(child.tag).lower() != "link":
            continue
        href = (child.attrib.get("href") or child.text or "").strip()
        if href.startswith("http"):
            return href
    guid = _child_text(element, {"guid", "id"})
    return guid if guid.startswith("http") else ""


def parse_when(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        try:
            when = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc)


def within_hours(value: Any, hours: int = NEWS_HOURS, now: datetime | None = None) -> bool:
    when = parse_when(value)
    if when is None:
        return False
    current = now or datetime.now(timezone.utc)
    return when >= current - timedelta(hours=hours)


def _point(feature: dict[str, Any]) -> tuple[float, float] | None:
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    if len(coords) < 2:
        return None
    try:
        return float(coords[1]), float(coords[0])
    except (TypeError, ValueError):
        return None


def _geo_from_element(element: ET.Element) -> tuple[float, float] | None:
    lat_text = _child_text(element, {"lat"})
    lng_text = _child_text(element, {"long", "lon", "lng"})
    if lat_text and lng_text:
        try:
            return float(lat_text), float(lng_text)
        except ValueError:
            return None
    point = _child_text(element, {"point"})
    match = GEO_POINT_RE.search(point or "")
    if not match:
        return None
    try:
        return float(match.group(1)), float(match.group(2))
    except ValueError:
        return None


def _jitter(key: str, lat: float, lng: float) -> tuple[float, float]:
    digest = hashlib.md5(key.encode("utf-8")).digest()
    dlat = (digest[0] - 127) / 127.0 * 0.55
    dlng = (digest[1] - 127) / 127.0 * 0.55
    lat = max(-85.0, min(85.0, lat + dlat))
    lng = ((lng + dlng + 180) % 360) - 180
    return round(lat, 4), round(lng, 4)


def _place_pattern(name: str) -> re.Pattern[str]:
    return re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)


def gazetteer() -> list[dict[str, Any]]:
    global _gazetteer_cache
    if _gazetteer_cache is not None:
        return _gazetteer_cache
    rows: dict[str, dict[str, Any]] = {}
    for name, (lat, lng) in COUNTRY_CENTERS.items():
        rows[name] = {
            "name": name,
            "label": name.title(),
            "lat": lat,
            "lng": lng,
            "kind": "country",
            "pattern": _place_pattern(name),
        }
    for name, (lat, lng, kind) in _EXTRA_PLACES.items():
        rows[name] = {
            "name": name,
            "label": name.replace("dprk", "North Korea").title() if name != "dprk" else "North Korea",
            "lat": lat,
            "lng": lng,
            "kind": kind,
            "pattern": _place_pattern(name),
        }
    for key, label in {
        "united states": "United States",
        "united kingdom": "United Kingdom",
        "united arab emirates": "United Arab Emirates",
        "south africa": "South Africa",
        "south korea": "South Korea",
        "north korea": "North Korea",
        "new zealand": "New Zealand",
        "czech republic": "Czech Republic",
        "hong kong": "Hong Kong",
        "south china sea": "South China Sea",
        "ivory coast": "Ivory Coast",
        "dprk": "North Korea",
        "drc": "DRC",
        "gaza": "Gaza",
    }.items():
        if key in rows:
            rows[key]["label"] = label
    _gazetteer_cache = list(rows.values())
    return _gazetteer_cache


def _special_places(text: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    lookup = {row["name"]: row for row in gazetteer()}
    if US_RE.search(text or ""):
        found.append(lookup["united states"])
    if UK_RE.search(text or ""):
        found.append(lookup["united kingdom"])
    return found


def locate_article(
    title: str,
    summary: str = "",
    categories: list[str] | None = None,
    feed_region: str = "",
) -> dict[str, Any] | None:
    """Pick the closest mappable place from title, categories, body, or feed region."""
    fields = [
        ("title", title or ""),
        ("category", " , ".join(categories or [])),
        ("summary", summary or ""),
        ("region", feed_region or ""),
    ]
    best: tuple[int, int, dict[str, Any], str] | None = None
    for field, text in fields:
        if not text:
            continue
        candidates = list(gazetteer())
        if field in {"title", "summary"}:
            candidates = _special_places(text) + candidates
        for place in candidates:
            match = place["pattern"].search(text)
            if not match:
                continue
            score = (
                _FIELD_BASE[field]
                + _KIND_BONUS[place["kind"]]
                + min(len(place["name"]), 24)
            )
            rank = (score, -match.start(), place, field)
            if best is None or rank[0] > best[0] or (rank[0] == best[0] and rank[1] > best[1]):
                best = rank
    if best is None:
        return None
    _, _, place, field = best
    return {
        "label": place["label"],
        "lat": place["lat"],
        "lng": place["lng"],
        "kind": place["kind"],
        "geo_basis": field,
    }


def parse_feed_xml(xml_text: str) -> list[dict[str, Any]]:
    if not (xml_text or "").lstrip().startswith("<"):
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items = [
        element
        for element in root.iter()
        if _local_tag(element.tag).lower() in {"item", "entry"}
    ]
    rows: list[dict[str, Any]] = []
    for element in items:
        title = short_title(_child_text(element, {"title"}), 200)
        url = _http_url(_item_link(element))
        if not title or not url:
            continue
        summary = short_title(
            _child_text(element, {"description", "summary", "encoded", "content"}),
            400,
        )
        published = (
            _child_text(element, {"pubDate", "published", "updated", "date"})
            or None
        )
        rows.append({
            "title": short_title(title),
            "url": url,
            "summary": summary,
            "categories": _child_texts(element, {"category", "subject"}),
            "published": published,
            "point": _geo_from_element(element),
        })
    return rows


def pin_from_article(
    article: dict[str, Any],
    source: dict[str, str],
    *,
    feed_id: str,
    feed_region: str = "",
    hours: int = NEWS_HOURS,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    if not within_hours(article.get("published"), hours=hours, now=now):
        return None
    url = _http_url(article.get("url"))
    title = short_title(str(article.get("title") or ""))
    if not url or not title:
        return None
    located = locate_article(
        title,
        str(article.get("summary") or ""),
        list(article.get("categories") or []),
        feed_region,
    )
    point = article.get("point")
    geo_basis = "coordinates"
    region = short_title(str(article.get("region") or ""), 48)
    if point:
        if located:
            region = located["label"]
    elif located:
        point = (located["lat"], located["lng"])
        geo_basis = located["geo_basis"]
        region = located["label"]
    else:
        return None
    lat, lng = _jitter(url, float(point[0]), float(point[1]))
    return {
        "id": f"{feed_id}-{hashlib.md5(url.encode('utf-8')).hexdigest()[:12]}",
        "lat": lat,
        "lng": lng,
        "region": region or source["name"],
        "title": title,
        "url": url,
        "articles": [{"title": title, "url": url}],
        "source": source["name"],
        "source_url": source["url"],
        "license": source.get("license") or "",
        "geo_basis": geo_basis,
        "published": article.get("published") or "",
    }


def normalize_gdacs(
    payload: dict[str, Any] | None,
    *,
    hours: int = NEWS_HOURS,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, feature in enumerate((payload or {}).get("features") or []):
        props = feature.get("properties") or {}
        stamp = props.get("datemodified") or props.get("fromdate") or props.get("todate")
        if hours and not within_hours(stamp, hours=hours, now=now):
            continue
        point = _point(feature)
        country = short_title(str(props.get("country") or props.get("iso3") or ""), 48)
        geo_basis = "coordinates"
        if not point:
            located = locate_article(country or str(props.get("name") or ""), categories=[country])
            if not located:
                continue
            point = (located["lat"], located["lng"])
            geo_basis = located["geo_basis"]
            country = located["label"]
        urls = props.get("url") or {}
        url = _http_url((urls or {}).get("report") or (urls or {}).get("details"))
        if not url:
            continue
        kind = GDACS_LABELS.get(str(props.get("eventtype") or "").upper(), "Alert")
        title = short_title(str(props.get("name") or props.get("eventname") or kind))
        lat, lng = _jitter(url, point[0], point[1])
        rows.append({
            "id": f"gdacs-{props.get('eventtype')}-{props.get('eventid') or index}",
            "lat": lat,
            "lng": lng,
            "region": country or kind,
            "title": title,
            "url": url,
            "articles": [{"title": title, "url": url}],
            "source": GDACS_SOURCE["name"],
            "source_url": GDACS_SOURCE["url"],
            "license": GDACS_SOURCE["license"],
            "geo_basis": geo_basis,
            "published": str(stamp or ""),
        })
        if len(rows) >= MAX_PINS:
            break
    return rows


def normalize_geojson(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Accept GDACS GeoJSON or a GDELT-style html/url feature list."""
    rows = normalize_gdacs(payload, hours=0)
    if rows:
        return rows
    out: list[dict[str, Any]] = []
    for index, feature in enumerate((payload or {}).get("features") or []):
        point = _point(feature)
        if not point:
            continue
        props = feature.get("properties") or {}
        articles = articles_from_html(str(props.get("html") or ""))
        url = _http_url(props.get("url"))
        title = short_title(str(props.get("name") or ""))
        if not articles and url:
            articles = [{"title": title or "Open article", "url": url}]
        if not articles:
            continue
        out.append({
            "id": f"news-{index}",
            "lat": point[0],
            "lng": point[1],
            "region": short_title(str(props.get("name") or "Region"), 48),
            "title": articles[0]["title"],
            "url": articles[0]["url"],
            "articles": articles,
            "source": SOURCE["name"],
            "source_url": SOURCE["url"],
            "license": SOURCE.get("license") or "",
            "geo_basis": "coordinates",
        })
        if len(out) >= MAX_PINS:
            break
    return out


def fetch_gdacs() -> dict[str, Any] | None:
    payload = overlay_http.get_json(
        GDACS_EVENTS,
        params={"eventlist": "EQ;TC;FL;VO;DR;WF"},
        headers=JSON_HEADERS,
        timeout=REQUEST_TIMEOUT,
        source="news",
    )
    return payload if isinstance(payload, dict) else None


def fetch_feed(url: str) -> list[dict[str, Any]]:
    text = overlay_http.get_text(
        url,
        headers=FEED_HEADERS,
        timeout=REQUEST_TIMEOUT,
        source="news",
    )
    return parse_feed_xml(text or "")


def _merge_news(primary: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = list(primary)
    seen = {row["url"] for row in items}
    for row in extra:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        items.append(row)
        if len(items) >= MAX_PINS:
            break
    return items


def _news_payload(items: list[dict[str, Any]], pending: bool, status: str) -> dict[str, Any]:
    return {
        "count": len(items),
        "hours": NEWS_HOURS,
        "news": items,
        "source": SOURCE,
        "sources": SOURCES,
        "pending": pending,
        "status": status,
    }


def _pins_from_feed(spec: dict[str, Any], now: datetime | None = None) -> list[dict[str, Any]]:
    pins: list[dict[str, Any]] = []
    for article in fetch_feed(spec["url"]):
        pin = pin_from_article(
            article,
            spec["source"],
            feed_id=spec["id"],
            feed_region=spec.get("region") or "",
            now=now,
        )
        if pin:
            pins.append(pin)
    return pins


def _load_geo_news() -> dict[str, Any]:
    items = normalize_gdacs(fetch_gdacs())
    for spec in ARTICLE_FEEDS:
        items = _merge_news(items, _pins_from_feed(spec))
    return _news_payload(items, pending=False, status=f"{len(items)} news pins")


def _run_news() -> None:
    log.info("[news] Loading GDACS alerts from the last %sh", NEWS_HOURS)
    items = normalize_gdacs(fetch_gdacs())
    store(
        CACHE_NS,
        _news_payload(items, True, f"{len(items)} GDACS alerts; loading free news feeds"),
        ttl=PENDING_TTL_SECONDS,
    )
    log.info("[news] GDACS %s pins; fetching attributed article feeds", len(items))
    for spec in ARTICLE_FEEDS:
        added = _pins_from_feed(spec)
        items = _merge_news(items, added)
        status = f"{len(items)} pins after {spec['source']['name']} ({len(added)} new)"
        store(CACHE_NS, _news_payload(items, True, status), ttl=PENDING_TTL_SECONDS)
        log.info("[news] %s", status)
    final = _news_payload(items, False, f"{len(items)} news pins")
    store(CACHE_NS, final)
    log.info("[news] Finished %s", final["status"])


def _ensure_worker() -> None:
    global _worker
    with _worker_guard:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_run_news, name="geo-news", daemon=True)
        _worker.start()


def list_geo_news(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh:
        payload = _load_geo_news()
        store(CACHE_NS, payload)
        return payload
    current = get_stale(CACHE_NS)
    if current and current.get("pending"):
        _ensure_worker()
        return current
    fresh = get_fresh(CACHE_NS)
    if fresh is not None:
        return fresh
    stale = get_stale(CACHE_NS)
    if stale is not None:
        _ensure_worker()
        return stale
    skeleton = _news_payload([], True, "Loading GDACS alerts…")
    store(CACHE_NS, skeleton, ttl=PENDING_TTL_SECONDS)
    _ensure_worker()
    return skeleton
