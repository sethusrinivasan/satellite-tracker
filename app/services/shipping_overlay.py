"""Current AIS ship positions from Fintraffic Digitraffic."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.services import overlay_http

log = logging.getLogger(__name__)

DIGITRAFFIC_LOCATIONS = "https://meri.digitraffic.fi/api/ais/v1/locations"
DIGITRAFFIC_VESSELS = "https://meri.digitraffic.fi/api/ais/v1/vessels"
DIGITRAFFIC_HOME = "https://www.digitraffic.fi/en/marine-traffic/"
MAX_SHIPS = 300
REQUEST_TIMEOUT = 12
HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json,application/geo+json",
    "Accept-Encoding": "gzip",
}

SOURCES = [
    {
        "name": "Fintraffic Digitraffic",
        "url": DIGITRAFFIC_HOME,
        "license": "CC BY 4.0; free, no API key",
        "attribution": (
            "Current AIS positions in Finnish waters from Fintraffic Digitraffic "
            "(https://www.digitraffic.fi), CC BY 4.0. Each pin is the latest reported "
            "location only — no predicted track or route."
        ),
        "coverage": "Finland and nearby Baltic waters",
    },
]



def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_ais_time(value: Any) -> str | None:
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return None
    if raw > 1e12:
        raw /= 1000.0
    if raw < 1e9:
        return None
    return datetime.fromtimestamp(raw, tz=timezone.utc).isoformat()


def ship_class(ship_type: Any) -> str:
    try:
        code = int(ship_type)
    except (TypeError, ValueError):
        return "other"
    if 60 <= code <= 69:
        return "passenger"
    if 70 <= code <= 79:
        return "cargo"
    if 80 <= code <= 89:
        return "tanker"
    if 30 <= code <= 39:
        return "fishing"
    return "other"


def _downsample(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(rows) <= limit:
        return rows
    step = len(rows) / limit
    return [rows[int(index * step)] for index in range(limit)]


def fetch_json(url: str) -> Any:
    payload = overlay_http.get_json(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, source="shipping")
    if payload is None:
        raise RuntimeError(f"Digitraffic unavailable: {url}")
    return payload


def _parse_vessel_meta(payload: Any) -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for item in payload or []:
        mmsi = item.get("mmsi")
        try:
            key = str(int(mmsi))
        except (TypeError, ValueError):
            continue
        meta[key] = {
            "name": (item.get("name") or "").strip(),
            "callsign": (item.get("callSign") or "").strip(),
            "ship_type": item.get("shipType"),
        }
    return meta


def load_vessel_meta(force_refresh: bool = False) -> dict[int, dict[str, Any]]:
    from app.services.overlay_cache import get_or_set, get_stale

    def _load() -> dict[str, dict[str, Any]]:
        try:
            return _parse_vessel_meta(fetch_json(DIGITRAFFIC_VESSELS))
        except Exception as exc:
            log.warning("[shipping] Digitraffic vessels failed: %s", exc)
            stale = get_stale("shipping-meta")
            if stale:
                return stale
            raise

    try:
        raw = get_or_set("shipping-meta", _load, force_refresh=force_refresh)
    except Exception:
        raw = {}
    return {int(mmsi): extra for mmsi, extra in (raw or {}).items()}


def normalize_locations(payload: dict[str, Any] | None, meta: dict[int, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    meta = meta or {}
    for feature in (payload or {}).get("features") or []:
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        try:
            lng = float(coords[0])
            lat = float(coords[1])
        except (TypeError, ValueError):
            continue
        props = feature.get("properties") or {}
        try:
            mmsi = int(feature.get("mmsi") or props.get("mmsi"))
        except (TypeError, ValueError):
            continue
        extra = meta.get(mmsi) or {}
        rows.append({
            "mmsi": mmsi,
            "name": extra.get("name") or f"MMSI {mmsi}",
            "callsign": extra.get("callsign") or "",
            "ship_class": ship_class(extra.get("ship_type")),
            "lat": lat,
            "lng": lng,
            "time": parse_ais_time(props.get("timestampExternal") or props.get("timestamp")),
            "source": "Fintraffic Digitraffic",
            "source_url": DIGITRAFFIC_HOME,
        })
    return _downsample(rows, MAX_SHIPS)


def _empty_shipping(pending: bool = False, status: str | None = None) -> dict[str, Any]:
    return {
        "ship_count": 0,
        "ships": [],
        "sources": SOURCES,
        "coverage": (
            "Current AIS positions from Fintraffic Digitraffic (Finland/Baltic, CC BY 4.0). "
            "Each marker is the latest reported location at that report time."
        ),
        "pending": pending,
        "status": status or "No AIS positions",
    }


def _load_shipping() -> dict[str, Any]:
    from app.services.overlay_cache import get_stale

    meta = load_vessel_meta()
    try:
        ships = normalize_locations(fetch_json(DIGITRAFFIC_LOCATIONS), meta)
    except Exception as exc:
        log.warning("[shipping] Digitraffic locations failed: %s", exc)
        stale = get_stale("shipping")
        if stale:
            return stale
        raise
    payload = _empty_shipping(pending=False, status=f"{len(ships)} current AIS positions")
    payload["ship_count"] = len(ships)
    payload["ships"] = ships
    return payload


def list_shipping(force_refresh: bool = False) -> dict[str, Any]:
    from app.services.overlay_cache import get_or_set, get_stale, is_refreshing

    try:
        data = get_or_set(
            "shipping",
            _load_shipping,
            force_refresh=force_refresh,
            skeleton=_empty_shipping(True, "Loading AIS positions…"),
        )
    except Exception:
        data = get_stale("shipping") or _empty_shipping()
    if not data:
        return _empty_shipping()
    pending = bool(data.get("pending")) or is_refreshing("shipping")
    data = dict(data)
    data["pending"] = pending
    if pending and not data.get("status"):
        data["status"] = "Loading AIS positions…"
    return data
