"""Geo-tagged news pins from free GDACS alerts and Wikipedia featured stories."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any

import requests

from app.services.overlay_cache import get_or_set

log = logging.getLogger(__name__)

GDACS_EVENTS = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
GDACS_HOME = "https://www.gdacs.org"
WIKI_FEATURED = "https://en.wikipedia.org/api/rest_v1/feed/featured"
WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_HOME = "https://en.wikipedia.org"
REQUEST_TIMEOUT = 18
MAX_PINS = 80
MAX_LINKS = 2
TITLE_LIMIT = 80
HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json,application/geo+json,*/*",
}

GDACS_SOURCE = {
    "name": "GDACS",
    "url": GDACS_HOME,
    "license": "Public disaster alerts; no API key",
    "attribution": (
        "Disaster and humanitarian alerts from the Global Disaster Alert and "
        "Coordination System (GDACS). Title links open the GDACS report."
    ),
}
WIKI_SOURCE = {
    "name": "Wikipedia",
    "url": WIKI_HOME,
    "license": "CC BY-SA; no API key",
    "attribution": (
        "Highlighted stories from the Wikipedia featured-feed news section, "
        "pinned at article coordinates when Wikipedia publishes them."
    ),
}
SOURCES = [GDACS_SOURCE, WIKI_SOURCE]
SOURCE = GDACS_SOURCE

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


def _point(feature: dict[str, Any]) -> tuple[float, float] | None:
    coords = (feature.get("geometry") or {}).get("coordinates") or []
    if len(coords) < 2:
        return None
    try:
        return float(coords[1]), float(coords[0])
    except (TypeError, ValueError):
        return None


def normalize_gdacs(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, feature in enumerate((payload or {}).get("features") or []):
        point = _point(feature)
        if not point:
            continue
        props = feature.get("properties") or {}
        urls = props.get("url") or {}
        url = _http_url((urls or {}).get("report") or (urls or {}).get("details"))
        if not url:
            continue
        kind = GDACS_LABELS.get(str(props.get("eventtype") or "").upper(), "Alert")
        title = short_title(str(props.get("name") or props.get("eventname") or kind))
        country = short_title(str(props.get("country") or props.get("iso3") or ""), 48)
        rows.append({
            "id": f"gdacs-{props.get('eventtype')}-{props.get('eventid') or index}",
            "lat": point[0],
            "lng": point[1],
            "region": country or kind,
            "title": title,
            "url": url,
            "articles": [{"title": title, "url": url}],
            "source": GDACS_SOURCE["name"],
            "source_url": GDACS_SOURCE["url"],
        })
        if len(rows) >= MAX_PINS:
            break
    return rows


def normalize_geojson(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Accept GDACS GeoJSON or a GDELT-style html/url feature list."""
    rows = normalize_gdacs(payload)
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
        })
        if len(out) >= MAX_PINS:
            break
    return out


def fetch_gdacs() -> dict[str, Any] | None:
    try:
        response = requests.get(
            GDACS_EVENTS,
            params={"eventlist": "EQ;TC;FL;VO;DR;WF"},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        log.warning("[news] GDACS failed: %s", exc)
        return None


def fetch_wikipedia_featured(when: datetime | None = None) -> dict[str, Any] | None:
    day = (when or datetime.now(timezone.utc)).date()
    try:
        response = requests.get(
            f"{WIKI_FEATURED}/{day:%Y}/{day:%m}/{day:%d}",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        log.warning("[news] Wikipedia featured failed: %s", exc)
        return None


def wikipedia_coordinates(titles: list[str]) -> dict[str, tuple[float, float]]:
    wanted = [title for title in titles if title]
    if not wanted:
        return {}
    try:
        response = requests.get(
            WIKI_API,
            params={
                "action": "query",
                "prop": "coordinates",
                "titles": "|".join(wanted[:20]),
                "format": "json",
            },
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        pages = ((response.json() or {}).get("query") or {}).get("pages") or {}
    except Exception as exc:
        log.warning("[news] Wikipedia coordinates failed: %s", exc)
        return {}
    found: dict[str, tuple[float, float]] = {}
    for page in pages.values():
        title = str(page.get("title") or "")
        coords = page.get("coordinates") or []
        if not title or not coords:
            continue
        try:
            found[title] = (float(coords[0]["lat"]), float(coords[0]["lon"]))
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return found


def normalize_wikipedia_featured(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    stories = []
    titles: list[str] = []
    for index, item in enumerate((payload or {}).get("news") or []):
        links = item.get("links") or []
        link = links[0] if links else {}
        title = short_title(str(link.get("title") or link.get("normalizedtitle") or item.get("story") or "Wikipedia news"))
        url = _http_url(((link.get("content_urls") or {}).get("desktop") or {}).get("page"))
        if not url:
            continue
        wiki_title = str(link.get("title") or link.get("normalizedtitle") or "")
        stories.append({
            "index": index,
            "title": title,
            "url": url,
            "wiki_title": wiki_title,
            "region": short_title(wiki_title or "Wikipedia", 48),
        })
        if wiki_title:
            titles.append(wiki_title)
    coords = wikipedia_coordinates(titles)
    rows: list[dict[str, Any]] = []
    for story in stories:
        point = coords.get(story["wiki_title"])
        if not point:
            continue
        rows.append({
            "id": f"wiki-{story['index']}",
            "lat": point[0],
            "lng": point[1],
            "region": story["region"],
            "title": story["title"],
            "url": story["url"],
            "articles": [{"title": story["title"], "url": story["url"]}],
            "source": WIKI_SOURCE["name"],
            "source_url": WIKI_SOURCE["url"],
        })
    return rows


def _load_geo_news() -> dict[str, Any]:
    items = normalize_gdacs(fetch_gdacs())
    wiki = normalize_wikipedia_featured(fetch_wikipedia_featured())
    seen = {(row["lat"], row["lng"], row["url"]) for row in items}
    for row in wiki:
        key = (row["lat"], row["lng"], row["url"])
        if key in seen:
            continue
        seen.add(key)
        items.append(row)
        if len(items) >= MAX_PINS:
            break
    return {
        "count": len(items),
        "hours": 24,
        "news": items,
        "source": SOURCE,
        "sources": SOURCES,
    }


def list_geo_news(force_refresh: bool = False) -> dict[str, Any]:
    return get_or_set("news", _load_geo_news, force_refresh=force_refresh)
