"""Live aircraft positions from the free OpenSky Network REST API."""

from __future__ import annotations

import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import requests

log = logging.getLogger(__name__)

OPENSKY_STATES = "https://opensky-network.org/api/states/all"
OPENSKY_FLIGHTS = "https://opensky-network.org/api/flights/all"
OPENSKY_HOME = "https://opensky-network.org"
ADSBdb_CALLSIGN = "https://api.adsbdb.com/v0/callsign/"
ADSBdb_HOME = "https://www.adsbdb.com"
RECENT_FLIGHT_CACHE_SECONDS = 90
ROUTE_CACHE_SECONDS = 6 * 3600
ROUTE_MISS_CACHE_SECONDS = 1800
MAX_FLIGHTS = 400
MAX_ROUTE_LOOKUPS = 24
REQUEST_TIMEOUT = 12
ROUTE_TIMEOUT = 6
EARTH_RADIUS_KM = 6371.0
CRUISE_KMH = 800.0
MIN_BLOCK_SECONDS = 45 * 60
DELAY_SLACK_SECONDS = 15 * 60
HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json",
}

SOURCE = {
    "name": "The OpenSky Network",
    "url": OPENSKY_HOME,
    "license": "Free anonymous REST access (rate-limited); cite OpenSky",
    "attribution": (
        "Aircraft positions from The OpenSky Network (https://opensky-network.org). "
        "See Schäfer et al., IPSN 2014, Bringing Up OpenSky. "
        "Likely origin/destination from adsbdb.com community callsign routes. "
        "On-time / delayed is estimated from OpenSky first-seen time versus typical "
        "great-circle duration, not an airline schedule."
    ),
}

ROUTE_SOURCE = {
    "name": "adsbdb",
    "url": ADSBdb_HOME,
    "license": "Free public JSON; no API key",
    "attribution": (
        "Callsign routes from adsbdb.com (community aircraft/route database). "
        "A route is the usual city pair for that callsign, not a guarantee for this flight."
    ),
}

_route_cache: dict[str, dict[str, Any]] = {}
_recent_flights_cache: dict[str, Any] = {"expires": 0.0, "data": {"icao": {}, "callsign": {}}}


def _as_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def parse_bbox(args: Any) -> tuple[float, float, float, float] | None:
    keys = ("lamin", "lomin", "lamax", "lomax")
    if not all(getattr(args, "get", lambda _k, _d=None: None)(key) not in (None, "") for key in keys):
        return None
    try:
        lamin = max(-90.0, min(90.0, float(args.get("lamin"))))
        lamax = max(-90.0, min(90.0, float(args.get("lamax"))))
        lomin = max(-180.0, min(180.0, float(args.get("lomin"))))
        lomax = max(-180.0, min(180.0, float(args.get("lomax"))))
    except (TypeError, ValueError):
        return None
    if lamin >= lamax or lomin >= lomax:
        return None
    return (lamin, lomin, lamax, lomax)


def _cache_key(bbox: tuple[float, float, float, float] | None) -> str:
    if not bbox:
        return "global"
    return ",".join(f"{value:.0f}" for value in bbox)


def _in_bbox(flight: dict[str, Any], bbox: tuple[float, float, float, float] | None) -> bool:
    if not bbox:
        return True
    lamin, lomin, lamax, lomax = bbox
    lat = flight.get("lat")
    lng = flight.get("lng")
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return False
    return lamin <= lat <= lamax and lomin <= lng <= lomax


def _normalize_state(state: list[Any]) -> dict[str, Any] | None:
    if not state or len(state) < 12:
        return None
    lat = _as_float(state[6])
    lng = _as_float(state[5])
    if lat is None or lng is None:
        return None
    on_ground = bool(state[8])
    if on_ground:
        return None
    return {
        "icao24": state[0] or "",
        "callsign": (state[1] or "").strip(),
        "origin_country": state[2] or "",
        "lng": lng,
        "lat": lat,
        "altitude_m": _as_float(state[13]) or _as_float(state[7]),
        "on_ground": on_ground,
        "velocity_ms": _as_float(state[9]),
        "heading": _as_float(state[10]),
        "vertical_rate_ms": _as_float(state[11]),
        "source": SOURCE["name"],
        "source_url": SOURCE["url"],
    }


def _downsample(flights: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if len(flights) <= limit:
        return flights
    step = len(flights) / limit
    return [flights[int(index * step)] for index in range(limit)]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def airport_from_adsb(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    iata = (payload.get("iata_code") or "").strip() or None
    icao = (payload.get("icao_code") or "").strip() or None
    if not iata and not icao:
        return None
    lat = _as_float(payload.get("latitude"))
    lng = _as_float(payload.get("longitude"))
    return {
        "code": iata or icao,
        "iata": iata,
        "icao": icao,
        "name": payload.get("name") or None,
        "city": payload.get("municipality") or None,
        "country": payload.get("country_name") or None,
        "lat": lat,
        "lng": lng,
    }


def airport_from_icao(code: str | None) -> dict[str, Any] | None:
    icao = (code or "").strip().upper()
    if not icao:
        return None
    return {
        "code": icao,
        "iata": None,
        "icao": icao,
        "name": None,
        "city": None,
        "country": None,
        "lat": None,
        "lng": None,
    }


def airport_label(airport: dict[str, Any] | None) -> str | None:
    if not airport:
        return None
    code = airport.get("iata") or airport.get("icao") or airport.get("code")
    city = airport.get("city")
    if code and city:
        return f"{code} · {city}"
    return code or city or airport.get("name") or None


def parse_adsbdb_route(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    route = (payload or {}).get("response", {}).get("flightroute") if payload else None
    if not isinstance(route, dict):
        return None
    origin = airport_from_adsb(route.get("origin"))
    destination = airport_from_adsb(route.get("destination"))
    if not origin and not destination:
        return None
    airline = (route.get("airline") or {}).get("name") if isinstance(route.get("airline"), dict) else None
    return {
        "airline": airline,
        "origin": origin,
        "destination": destination,
    }


def estimate_timeliness(
    *,
    now: float,
    first_seen: float | None,
    origin: dict[str, Any] | None,
    destination: dict[str, Any] | None,
    lat: float | None,
    lng: float | None,
    velocity_ms: float | None,
) -> dict[str, Any]:
    unknown = {"status": "unknown", "status_label": "Status unknown", "delay_minutes": None}
    dest_lat = (destination or {}).get("lat")
    dest_lng = (destination or {}).get("lng")
    origin_lat = (origin or {}).get("lat")
    origin_lng = (origin or {}).get("lng")
    if (
        first_seen is None
        or dest_lat is None
        or dest_lng is None
        or origin_lat is None
        or origin_lng is None
        or lat is None
        or lng is None
    ):
        return unknown
    try:
        first_seen_ts = float(first_seen)
    except (TypeError, ValueError):
        return unknown
    if first_seen_ts <= 0 or now - first_seen_ts > 36 * 3600:
        return unknown

    route_km = haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
    typical_sec = max(MIN_BLOCK_SECONDS, route_km / CRUISE_KMH * 3600.0)
    remaining_km = haversine_km(lat, lng, dest_lat, dest_lng)
    if remaining_km < 40:
        eta = now
    else:
        speed_kmh = (velocity_ms or 0) * 3.6
        if speed_kmh < 150:
            speed_kmh = CRUISE_KMH
        eta = now + remaining_km / speed_kmh * 3600.0
    late_sec = eta - (first_seen_ts + typical_sec)
    if late_sec > DELAY_SLACK_SECONDS:
        minutes = max(1, int(round(late_sec / 60.0)))
        return {
            "status": "delayed",
            "status_label": f"Delayed · ~{minutes} min",
            "delay_minutes": minutes,
        }
    return {"status": "on_time", "status_label": "On time", "delay_minutes": 0}


def fetch_adsbdb_route(callsign: str) -> dict[str, Any] | None:
    ident = (callsign or "").strip().upper()
    if len(ident) < 3:
        return None
    try:
        response = requests.get(
            f"{ADSBdb_CALLSIGN}{ident}",
            headers=HEADERS,
            timeout=ROUTE_TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return parse_adsbdb_route(response.json())
    except Exception as exc:
        log.warning("[flights] adsbdb route failed for %s: %s", ident, exc)
        return None


def lookup_routes(callsigns: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    now = time.time()
    seen: set[str] = set()
    for raw in callsigns:
        key = (raw or "").strip().upper()
        if not key or key in seen:
            continue
        seen.add(key)
        cached = _route_cache.get(key)
        if cached and now < cached["expires"]:
            if cached["route"]:
                found[key] = cached["route"]
        else:
            missing.append(key)
    if not missing:
        return found

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(fetch_adsbdb_route, callsign): callsign
            for callsign in missing[:MAX_ROUTE_LOOKUPS]
        }
        for future in as_completed(futures):
            callsign = futures[future]
            try:
                route = future.result()
            except Exception as exc:
                log.warning("[flights] adsbdb worker failed for %s: %s", callsign, exc)
                route = None
            _route_cache[callsign] = {
                "expires": now + (ROUTE_CACHE_SECONDS if route else ROUTE_MISS_CACHE_SECONDS),
                "route": route,
            }
            if route:
                found[callsign] = route
    return found


def fetch_opensky_recent_flights() -> dict[str, dict[str, Any]]:
    now = time.time()
    if now < float(_recent_flights_cache.get("expires") or 0) and _recent_flights_cache.get("data"):
        return _recent_flights_cache["data"]
    end = int(now)
    begin = end - 7200
    try:
        response = requests.get(
            OPENSKY_FLIGHTS,
            params={"begin": begin, "end": end},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json()
    except Exception as exc:
        log.warning("[flights] OpenSky recent flights failed: %s", exc)
        cached = _recent_flights_cache.get("data")
        return cached if cached else {"icao": {}, "callsign": {}}

    by_icao: dict[str, dict[str, Any]] = {}
    by_callsign: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = {
            "first_seen": row.get("firstSeen"),
            "est_origin": (row.get("estDepartureAirport") or "").strip() or None,
            "est_dest": (row.get("estArrivalAirport") or "").strip() or None,
        }
        icao = (row.get("icao24") or "").strip().lower()
        callsign = (row.get("callsign") or "").strip().upper()
        if icao:
            by_icao[icao] = item
        if callsign:
            by_callsign[callsign] = item
    data = {"icao": by_icao, "callsign": by_callsign}
    _recent_flights_cache["data"] = data
    _recent_flights_cache["expires"] = now + RECENT_FLIGHT_CACHE_SECONDS
    return data


def enrich_flight(
    flight: dict[str, Any],
    routes: dict[str, dict[str, Any]],
    recent: dict[str, dict[str, Any]],
    now: float,
) -> dict[str, Any]:
    callsign = (flight.get("callsign") or "").strip().upper()
    icao = (flight.get("icao24") or "").strip().lower()
    route = routes.get(callsign) or {}
    seen = (recent.get("icao") or {}).get(icao) or (recent.get("callsign") or {}).get(callsign) or {}
    origin = route.get("origin") or airport_from_icao(seen.get("est_origin"))
    destination = route.get("destination") or airport_from_icao(seen.get("est_dest"))
    timing = estimate_timeliness(
        now=now,
        first_seen=seen.get("first_seen"),
        origin=origin,
        destination=destination,
        lat=flight.get("lat"),
        lng=flight.get("lng"),
        velocity_ms=flight.get("velocity_ms"),
    )
    flight.update({
        "airline": route.get("airline"),
        "origin": origin,
        "destination": destination,
        "origin_label": airport_label(origin),
        "destination_label": airport_label(destination),
        "first_seen": seen.get("first_seen"),
        **timing,
        "route_source": ROUTE_SOURCE["name"] if route else (SOURCE["name"] if origin or destination else None),
    })
    return flight


def fetch_opensky_states(bbox: tuple[float, float, float, float] | None = None) -> dict[str, Any] | None:
    params = {}
    if bbox:
        params = {"lamin": bbox[0], "lomin": bbox[1], "lamax": bbox[2], "lomax": bbox[3]}
    try:
        response = requests.get(
            OPENSKY_STATES,
            params=params or None,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        log.warning("[flights] OpenSky request failed: %s", exc)
        return None


def normalize_states(payload: dict[str, Any] | None) -> tuple[list[dict[str, Any]], str | None]:
    if not payload:
        return [], None
    rows = []
    for state in payload.get("states") or []:
        item = _normalize_state(state)
        if item:
            rows.append(item)
    observed = payload.get("time")
    iso = None
    if isinstance(observed, (int, float)):
        iso = datetime.fromtimestamp(observed, tz=timezone.utc).isoformat()
    return _downsample(rows, MAX_FLIGHTS), iso


def _load_flights() -> dict[str, Any]:
    flights, observed = normalize_states(fetch_opensky_states(None))
    return {
        "count": len(flights),
        "time": observed,
        "flights": flights,
        "source": SOURCE,
    }


def list_flights(bbox: tuple[float, float, float, float] | None = None, force_refresh: bool = False) -> dict[str, Any]:
    from app.services.overlay_cache import get_or_set

    payload = get_or_set("flights", _load_flights, force_refresh=force_refresh)
    flights = [dict(row) for row in payload.get("flights") or [] if _in_bbox(row, bbox)]
    routes = lookup_routes([row.get("callsign") or "" for row in flights])
    recent = fetch_opensky_recent_flights()
    now = time.time()
    flights = [enrich_flight(row, routes, recent, now) for row in flights]
    return {
        "count": len(flights),
        "time": payload.get("time"),
        "flights": flights,
        "source": payload.get("source") or SOURCE,
        "sources": [SOURCE, ROUTE_SOURCE],
    }
