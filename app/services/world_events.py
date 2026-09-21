"""Last-24h weather and climate events for the tracker overlay (no API key)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

log = logging.getLogger(__name__)

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
EONET_HOME = "https://eonet.gsfc.nasa.gov/"
USGS_HOME = "https://earthquake.usgs.gov/"
# NASA EONET category ids that are weather or climate (not volcanoes / quakes).
EONET_WEATHER_CLIMATE_IDS = (
    "severeStorms",
    "floods",
    "drought",
    "droughts",
    "dustHaze",
    "snow",
    "seaLakeIce",
    "tempExtremes",
    "wildfires",
)
WEATHER_CLIMATE_HINTS = (
    "storm", "cyclone", "hurricane", "typhoon", "flood", "drought",
    "dust", "haze", "snow", "ice", "temperature", "heat", "cold",
    "wildfire", "fire", "rain", "wind",
)
SOURCES = [
    {
        "name": "NASA EONET",
        "url": EONET_HOME,
        "license": "NASA public information; free, no API key",
        "attribution": (
            "Weather and climate events from NASA Earth Observatory Natural Event Tracker (EONET): "
            "storms, floods, droughts, dust/haze, snow, sea/lake ice, temperature extremes, and wildfires."
        ),
    },
    {
        "name": "USGS",
        "url": USGS_HOME,
        "license": "U.S. Government work; public domain",
        "attribution": (
            "Earthquakes from the USGS M4.5+ past-day GeoJSON feed. "
            "Map bubbles scale size and color by magnitude."
        ),
    },
]
MAX_EVENTS = 200
REQUEST_TIMEOUT = 8


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _within_last_day(when: datetime | None, cutoff: datetime) -> bool:
    return when is not None and when >= cutoff


def is_weather_climate_category(categories: list[Any]) -> bool:
    for item in categories or []:
        slug = str(item.get("id") or "").strip()
        if slug in EONET_WEATHER_CLIMATE_IDS:
            return True
        title = str(item.get("title") or "").lower()
        if any(hint in title for hint in WEATHER_CLIMATE_HINTS):
            return True
    return False


def _fetch_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        log.warning("[world-events] Failed %s: %s", url, exc)
        return None


def _eonet_weather_climate_events(cutoff: datetime) -> list[dict[str, Any]]:
    payload = _fetch_json(
        EONET_URL,
        {
            "status": "open",
            "days": 1,
            "category": ",".join(EONET_WEATHER_CLIMATE_IDS),
        },
    )
    rows: list[dict[str, Any]] = []
    for item in (payload or {}).get("events") or []:
        categories = item.get("categories") or []
        if not is_weather_climate_category(categories):
            continue
        geometries = item.get("geometry") or []
        point = None
        when = None
        for geom in reversed(geometries):
            coords = geom.get("coordinates") or []
            if geom.get("type") == "Point" and len(coords) >= 2:
                point = coords
                when = _parse_time(geom.get("date"))
                break
        if not point or not _within_last_day(when, cutoff):
            continue
        category = (categories[0].get("title") if categories else "Weather") or "Weather"
        rows.append({
            "id": item.get("id") or f"eonet-{item.get('title')}",
            "title": item.get("title") or category,
            "category": category,
            "lat": float(point[1]),
            "lng": float(point[0]),
            "time": when.isoformat() if when else None,
            "kind": "weather",
            "magnitude": None,
            "source": "NASA EONET",
            "url": item.get("link") or "",
        })
    return rows


def _usgs_earthquakes(cutoff: datetime) -> list[dict[str, Any]]:
    payload = _fetch_json(USGS_URL)
    rows: list[dict[str, Any]] = []
    for feature in (payload or {}).get("features") or []:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        when = None
        millis = props.get("time")
        if isinstance(millis, (int, float)):
            when = datetime.fromtimestamp(millis / 1000, tz=timezone.utc)
        if not _within_last_day(when, cutoff):
            continue
        mag = props.get("mag")
        try:
            magnitude = float(mag) if mag is not None else None
        except (TypeError, ValueError):
            magnitude = None
        title = props.get("title") or "Earthquake"
        rows.append({
            "id": feature.get("id") or title,
            "title": title,
            "category": f"Earthquake M{magnitude}" if magnitude is not None else "Earthquake",
            "kind": "earthquake",
            "magnitude": magnitude,
            "lat": float(coords[1]),
            "lng": float(coords[0]),
            "time": when.isoformat() if when else None,
            "source": "USGS",
            "url": props.get("url") or "",
        })
    return rows


def _load_world_events() -> list[dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    events = _eonet_weather_climate_events(cutoff) + _usgs_earthquakes(cutoff)
    events.sort(key=lambda row: row.get("time") or "", reverse=True)
    return events[:MAX_EVENTS]


def list_world_events(force_refresh: bool = False) -> list[dict[str, Any]]:
    from app.services.overlay_cache import get_or_set

    return list(get_or_set("world-events", _load_world_events, force_refresh=force_refresh))
