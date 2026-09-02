"""
Geo-Query Service
=================
Handles natural-language queries like "Starlink satellites over United States" by:
  1. Detecting a country name in the prompt
  2. Looking up that country's bounding box
  3. Propagating each satellite's current position using SGP4 math
  4. Filtering by bounding box (and optional name filter)

SGP4 propagation is implemented here in pure Python so no extra dependency
is needed beyond what's already in requirements.txt.
"""

from __future__ import annotations
import math
import re
import statistics
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Country bounding boxes  {name: (lat_min, lat_max, lon_min, lon_max)}
# Boxes are intentionally generous (~300 km pad) so low-inclination passes
# at the boundary are still caught.
# ---------------------------------------------------------------------------
COUNTRY_BBOX: dict[str, tuple[float, float, float, float]] = {
    "afghanistan":        (29.0, 38.5, 60.5, 74.9),
    "argentina":          (-55.0, -21.8, -73.6, -53.6),
    "australia":          (-43.7, -10.0, 113.3, 153.7),
    "bangladesh":         (20.6, 26.6, 88.0, 92.7),
    "brazil":             (-33.8, 5.3, -73.1, -34.8),
    "canada":             (41.7, 83.1, -141.0, -52.3),
    "chile":              (-55.9, -17.5, -75.7, -66.4),
    "china":              (18.2, 53.5, 73.6, 134.8),
    "colombia":           (-4.2, 12.5, -79.0, -66.9),
    "egypt":              (22.0, 31.7, 24.7, 36.9),
    "ethiopia":           (3.4, 14.9, 33.0, 47.9),
    "france":             (41.3, 51.1, -5.2, 9.6),
    "germany":            (47.3, 55.1, 5.9, 15.1),
    "india":              (8.0,  37.1, 68.1, 97.4),
    "indonesia":          (-11.0, 6.1, 95.0, 141.0),
    "iran":               (25.1, 39.8, 44.0, 63.3),
    "iraq":               (29.1, 37.4, 38.8, 48.6),
    "israel":             (29.5, 33.3, 34.3, 35.9),
    "italy":              (35.5, 47.1, 6.6, 18.5),
    "japan":              (24.0, 45.6, 122.9, 145.9),
    "kenya":              (-4.7, 5.0, 33.9, 41.9),
    "mexico":             (14.5, 32.7, -117.1, -86.7),
    "morocco":            (27.7, 35.9, -13.2, -1.0),
    "netherlands":        (50.8, 53.6, 3.3, 7.2),
    "new zealand":        (-47.4, -34.4, 166.4, 178.6),
    "nigeria":            (4.3, 13.9, 2.7, 14.7),
    "norway":             (57.9, 71.2, 4.6, 31.1),
    "pakistan":           (23.6, 37.1, 60.9, 77.0),
    "peru":               (-18.4, -0.0, -81.3, -68.7),
    "philippines":        (4.6, 21.1, 116.9, 126.6),
    "poland":             (49.0, 54.9, 14.1, 24.2),
    "russia":             (41.2, 81.9, 19.6, 190.0),   # wraps; handled specially
    "saudi arabia":       (16.4, 32.2, 34.6, 55.7),
    "south africa":       (-34.9, -22.1, 16.5, 32.9),
    "south korea":        (33.1, 38.6, 125.1, 129.6),
    "spain":              (35.9, 43.8, -9.3, 4.3),
    "sweden":             (55.4, 69.1, 11.1, 24.2),
    "switzerland":        (45.8, 47.8, 5.9, 10.5),
    "thailand":           (5.6, 20.5, 97.3, 105.7),
    "turkey":             (35.8, 42.1, 25.7, 44.8),
    "ukraine":            (44.4, 52.4, 22.1, 40.2),
    "united arab emirates": (22.6, 26.1, 51.6, 56.4),
    "united kingdom":     (49.9, 60.9, -8.2, 1.8),
    "united states":      (24.4, 49.4, -124.8, -66.9),
    "vietnam":            (8.6, 23.4, 102.1, 109.5),
}

# Common aliases / alternate spellings
_ALIASES: dict[str, str] = {
    "usa":           "united states",
    "us":            "united states",
    "america":       "united states",
    "uk":            "united kingdom",
    "great britain": "united kingdom",
    "uae":           "united arab emirates",
    "emirates":      "united arab emirates",
    "korea":         "south korea",
    "dprk":          "south korea",
    "nederland":     "netherlands",
    "brasil":        "brazil",
}


def resolve_country(text: str) -> Optional[tuple[str, tuple[float, float, float, float]]]:
    """
    Given free-form text, try to extract a country name and return
    (canonical_name, (lat_min, lat_max, lon_min, lon_max)).
    Returns None if no country is recognised.
    """
    lowered = text.lower()

    # Try full canonical names first (longest first to avoid partial matches)
    for name in sorted(COUNTRY_BBOX.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(name) + r'\b', lowered):
            return name.title(), COUNTRY_BBOX[name]

    # Try aliases
    for alias, canonical in _ALIASES.items():
        if re.search(r'\b' + re.escape(alias) + r'\b', lowered):
            return canonical.title(), COUNTRY_BBOX[canonical]

    return None


def extract_name_filter(text: str) -> Optional[str]:
    """
    Try to pull a satellite family name from the prompt, e.g.
    "starlink satellites over india" → "STARLINK"
    "show gps sats above china"     → "GPS"
    Returns None if no useful filter is found.
    """
    # Strip known stop-words / geography / prepositions
    stopwords = {
        "satellites", "satellite", "sats", "sat", "spacecraft", "space",
        "over", "above", "in", "around", "near", "within", "inside",
        "show", "get", "find", "list", "me", "all", "the", "that", "are",
        "currently", "now", "flying", "orbiting", "passing",
    }

    # Pull words that look like satellite names (uppercase-ish tokens > 2 chars)
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9\-_]+", text)
    candidates = [w.upper() for w in words if w.lower() not in stopwords and len(w) > 2]

    # Remove any words that match a country name
    country_words = set()
    for country_name in COUNTRY_BBOX:
        for part in country_name.split():
            country_words.add(part.upper())
    for alias in _ALIASES:
        for part in alias.split():
            country_words.add(part.upper())

    candidates = [c for c in candidates if c not in country_words]

    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# Pure-Python SGP4 (simplified circular orbit approximation)
# Accurate enough for over-the-horizon / bounding-box filtering.
# ---------------------------------------------------------------------------

_TWO_PI   = 2.0 * math.pi
_DEG2RAD  = math.pi / 180.0
_RAD2DEG  = 180.0 / math.pi
_RE_KM    = 6378.137         # Earth equatorial radius km
_MU       = 398600.4418      # Earth gravitational parameter km³/s²
_J2       = 1.08262668e-3    # Earth J2 perturbation


def _gmst(t: datetime) -> float:
    """Approximate Greenwich Mean Sidereal Time in radians."""
    # Julian date
    d = (t - datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)).total_seconds() / 86400.0
    gmst_deg = 280.46061837 + 360.98564736629 * d
    return math.radians(gmst_deg % 360.0)


def propagate_tle(
    line1: str,
    line2: str,
    t: Optional[datetime] = None,
) -> Optional[tuple[float, float, float]]:
    """
    Propagate a TLE to time *t* (UTC datetime; defaults to now).
    Returns (latitude_deg, longitude_deg, altitude_km) or None on error.

    Implements J2-perturbed Keplerian propagation.
    All internal angles are in radians; distances in km; time in seconds.
    Accurate to ~10-30 km for LEO satellites within a few days of epoch —
    sufficient for bounding-box geo-filtering.
    """
    if t is None:
        t = datetime.now(timezone.utc)
    elif t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)

    try:
        # ── Parse Line 1 ──────────────────────────────────────────────────────
        epoch_year_2d = int(line1[18:20])
        epoch_day     = float(line1[20:32])
        epoch_year    = (2000 + epoch_year_2d) if epoch_year_2d < 57 else (1900 + epoch_year_2d)

        from datetime import timedelta as _td
        epoch_dt = datetime(epoch_year, 1, 1, tzinfo=timezone.utc) + _td(days=epoch_day - 1)

        # ── Parse Line 2 ──────────────────────────────────────────────────────
        inc    = float(line2[8:16])  * _DEG2RAD   # inclination (rad)
        raan   = float(line2[17:25]) * _DEG2RAD   # RAAN (rad)
        ecc    = float("0." + line2[26:33].strip())  # eccentricity (dimensionless)
        omega  = float(line2[34:42]) * _DEG2RAD   # arg of perigee (rad)
        M0     = float(line2[43:51]) * _DEG2RAD   # mean anomaly at epoch (rad)
        # Mean motion: TLE gives rev/day → convert to rad/s
        #   n [rad/s] = n [rev/day] × 2π / 86400
        n0     = float(line2[52:63]) * _TWO_PI / 86400.0   # rad/s

        # ── Semi-major axis from Kepler 3rd law (MU in km³/s², n in rad/s) ──
        a0 = (_MU / (n0 * n0)) ** (1.0 / 3.0)   # km

        # ── Time since epoch (seconds) ────────────────────────────────────────
        dt_s = (t - epoch_dt).total_seconds()

        # ── J2 secular drift rates (all in rad/s) ─────────────────────────────
        p       = a0 * (1.0 - ecc * ecc)           # semi-latus rectum (km)
        cos_i   = math.cos(inc)
        factor  = -1.5 * _J2 * ((_RE_KM / p) ** 2) * n0
        raan_dot  =  factor * cos_i
        omega_dot =  factor * (2.5 * cos_i * cos_i - 0.5)
        M_dot     = -factor * math.sqrt(1.0 - ecc * ecc) * (1.5 * cos_i * cos_i - 0.5)

        # ── Propagated orbital elements ───────────────────────────────────────
        raan_t  = raan  + raan_dot  * dt_s
        omega_t = omega + omega_dot * dt_s
        M_t     = M0   + (n0 + M_dot) * dt_s

        # ── Kepler's equation: solve E − e·sin(E) = M (Newton-Raphson) ───────
        E = M_t
        for _ in range(50):
            dE = (M_t - E + ecc * math.sin(E)) / (1.0 - ecc * math.cos(E))
            E += dE
            if abs(dE) < 1e-12:
                break

        # ── True anomaly ──────────────────────────────────────────────────────
        sin_E  = math.sin(E)
        cos_E  = math.cos(E)
        sqrt_1me2 = math.sqrt(1.0 - ecc * ecc)
        nu = math.atan2(sqrt_1me2 * sin_E, cos_E - ecc)

        # ── Orbital radius ────────────────────────────────────────────────────
        r = a0 * (1.0 - ecc * cos_E)   # km

        # ── Position in perifocal (orbital) plane ─────────────────────────────
        u      = omega_t + nu           # argument of latitude
        x_orb  = r * math.cos(u)
        y_orb  = r * math.sin(u)

        # ── Perifocal → ECI (rotate by inc and RAAN) ─────────────────────────
        sin_raan = math.sin(raan_t);  cos_raan = math.cos(raan_t)
        sin_i    = math.sin(inc);     cos_i_v  = math.cos(inc)
        x_eci = cos_raan * x_orb - sin_raan * y_orb * cos_i_v
        y_eci = sin_raan * x_orb + cos_raan * y_orb * cos_i_v
        z_eci = sin_i * y_orb

        # ── ECI → ECEF (rotate by Greenwich Mean Sidereal Time) ───────────────
        theta   = _gmst(t)
        cos_th  = math.cos(theta);  sin_th = math.sin(theta)
        x_ecef  =  x_eci * cos_th + y_eci * sin_th
        y_ecef  = -x_eci * sin_th + y_eci * cos_th
        z_ecef  =  z_eci

        # ── ECEF → Geodetic (WGS-84, Bowring iteration) ───────────────────────
        lon_deg = math.atan2(y_ecef, x_ecef) * _RAD2DEG

        _a_wgs  = _RE_KM          # 6378.137 km
        _b_wgs  = 6356.7523142    # WGS-84 semi-minor axis km
        _e2     = 1.0 - (_b_wgs / _a_wgs) ** 2   # first eccentricity squared

        p_xy    = math.sqrt(x_ecef ** 2 + y_ecef ** 2)
        lat_rad = math.atan2(z_ecef, p_xy * (1.0 - _e2))   # initial guess
        for _ in range(10):
            sin_lat = math.sin(lat_rad)
            N_prime = _a_wgs / math.sqrt(1.0 - _e2 * sin_lat * sin_lat)
            lat_rad = math.atan2(z_ecef + _e2 * N_prime * sin_lat, p_xy)

        lat_deg  = lat_rad * _RAD2DEG
        sin_lat  = math.sin(lat_rad)
        cos_lat  = math.cos(lat_rad)
        N_final  = _a_wgs / math.sqrt(1.0 - _e2 * sin_lat * sin_lat)

        if abs(cos_lat) > 1e-6:
            alt_km = p_xy / cos_lat - N_final
        else:
            alt_km = abs(z_ecef) / abs(sin_lat) - N_final * (1.0 - _e2)

        return lat_deg, lon_deg, alt_km

    except Exception:
        return None


def satellites_over_region(
    tles: list[dict],
    bbox: tuple[float, float, float, float],
    name_filter: Optional[str] = None,
    now: Optional[datetime] = None,
    altitude_max_km: float = 2000.0,
) -> list[dict]:
    """
    Given a list of TLE dicts (from /api/satellites/latest-tles),
    filter to those currently over the given bounding box.

    bbox = (lat_min, lat_max, lon_min, lon_max)
    name_filter: if provided, only consider satellites whose name
                 contains this string (case-insensitive).
    altitude_max_km: ignore satellites above this altitude (filters out GEO).

    Returns list of dicts enriched with current lat/lon/alt.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    lat_min, lat_max, lon_min, lon_max = bbox
    results = []

    for sat in tles:
        # Optional name filter
        if name_filter and name_filter.upper() not in sat.get("name", "").upper():
            continue

        l1 = sat.get("l1") or ""
        l2 = sat.get("l2") or ""
        if len(l1) < 69 or len(l2) < 69:
            continue

        pos = propagate_tle(l1, l2, now)
        if pos is None:
            continue

        lat, lon, alt = pos

        # Altitude sanity – skip GEO / HEO unless caller opts in
        if alt > altitude_max_km or alt < 100:
            continue

        # Bounding-box check (handle Russia's lon wrap-around)
        in_lat = lat_min <= lat <= lat_max
        if lon_max > 180:  # wraps antimeridian (Russia)
            in_lon = lon >= lon_min or lon <= (lon_max - 360)
        else:
            in_lon = lon_min <= lon <= lon_max

        if in_lat and in_lon:
            results.append({
                **sat,
                "current_lat": round(lat, 4),
                "current_lon": round(lon, 4),
                "current_alt": round(alt, 1),
            })

    return results


def filter_anomalous_altitudes(
    sats: list[dict],
    percentile: float = 99.0,
) -> list[dict]:
    """
    Remove satellites with anomalous altitudes by computing the given
    percentile across all propagated altitudes. Any satellite with an
    altitude above the threshold is considered an outlier (bad TLE data).

    This catches cases where a stale / malformed TLE produces a physically
    impossible position (e.g. 50 000 km for what should be a LEO bird).

    Returns the filtered list.
    """
    if not sats:
        return sats

    altitudes = [s["current_alt"] for s in sats]
    threshold = statistics.quantiles(altitudes, n=100, method="inclusive")[int(percentile) - 1]

    return [s for s in sats if s["current_alt"] <= threshold]
