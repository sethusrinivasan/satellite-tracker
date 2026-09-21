"""Public webcam pins from free OSM Overpass data plus official government pages."""

from __future__ import annotations

import logging
from typing import Any

import requests

log = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_COPYRIGHT = "https://www.openstreetmap.org/copyright"
REQUEST_TIMEOUT = 20
MAX_CAMS = 120
MAX_BBOX_SPAN = 40.0
HUB_SPAN = 0.7
HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "application/json",
}

SOURCES = [
    {
        "name": "OpenStreetMap",
        "url": OSM_COPYRIGHT,
        "license": "ODbL; via Overpass API",
        "attribution": (
            "Webcam locations and outbound links from OpenStreetMap "
            "(© OpenStreetMap contributors, ODbL). Queried via overpass-api.de."
        ),
    },
    {
        "name": "USGS",
        "url": "https://www.usgs.gov/",
        "license": "U.S. Government work; public domain",
        "attribution": "Selected volcano webcams from the U.S. Geological Survey.",
    },
    {
        "name": "National Park Service",
        "url": "https://www.nps.gov/",
        "license": "U.S. Government work; public domain",
        "attribution": "Selected park webcam index pages from the U.S. National Park Service.",
    },
    {
        "name": "NOAA",
        "url": "https://www.noaa.gov/",
        "license": "U.S. Government work; public domain",
        "attribution": "Selected marine / weather webcam pages from NOAA.",
    },
    {
        "name": "INGV",
        "url": "https://www.ingv.it/",
        "license": "Public scientific monitoring pages",
        "attribution": "Italian volcano webcams from INGV.",
    },
    {
        "name": "GeoNet",
        "url": "https://www.geonet.org.nz/",
        "license": "CC BY 3.0 NZ",
        "attribution": "New Zealand volcano cameras from GeoNet / GNS Science.",
    },
]

# Official public index pages (we link out; we do not host or scrape the video).
PUBLIC_CAMS: list[dict[str, Any]] = [
    {"id": "usgs-kilauea", "name": "Kīlauea summit webcams", "city": "Hawaiʻi",
     "lat": 19.4069, "lng": -155.2834,
     "url": "https://www.usgs.gov/volcanoes/kilauea/webcams",
     "source": "USGS", "source_url": "https://www.usgs.gov/volcanoes/kilauea/webcams"},
    {"id": "usgs-cascades", "name": "Cascades volcano webcams", "city": "Washington / Oregon",
     "lat": 46.1914, "lng": -122.1956,
     "url": "https://www.usgs.gov/observatories/cvo/webcams",
     "source": "USGS", "source_url": "https://www.usgs.gov/observatories/cvo/webcams"},
    {"id": "usgs-avo", "name": "Alaska volcano webcams", "city": "Alaska",
     "lat": 58.3783, "lng": -155.3971,
     "url": "https://www.usgs.gov/observatories/avo/webcams",
     "source": "USGS", "source_url": "https://www.usgs.gov/observatories/avo/webcams"},
    {"id": "nps-yellowstone", "name": "Yellowstone webcams", "city": "Wyoming",
     "lat": 44.4605, "lng": -110.8281,
     "url": "https://www.nps.gov/yell/learn/photosmultimedia/webcams.htm",
     "source": "National Park Service",
     "source_url": "https://www.nps.gov/yell/learn/photosmultimedia/webcams.htm"},
    {"id": "nps-denali", "name": "Denali webcams", "city": "Alaska",
     "lat": 63.0695, "lng": -151.0063,
     "url": "https://www.nps.gov/dena/learn/photosmultimedia/webcams.htm",
     "source": "National Park Service",
     "source_url": "https://www.nps.gov/dena/learn/photosmultimedia/webcams.htm"},
    {"id": "nps-glacier", "name": "Glacier National Park webcams", "city": "Montana",
     "lat": 48.6967, "lng": -113.7183,
     "url": "https://www.nps.gov/glac/learn/photosmultimedia/webcams.htm",
     "source": "National Park Service",
     "source_url": "https://www.nps.gov/glac/learn/photosmultimedia/webcams.htm"},
    {"id": "nps-acadia", "name": "Acadia webcams", "city": "Maine",
     "lat": 44.3386, "lng": -68.2733,
     "url": "https://www.nps.gov/acad/learn/photosmultimedia/webcams.htm",
     "source": "National Park Service",
     "source_url": "https://www.nps.gov/acad/learn/photosmultimedia/webcams.htm"},
    {"id": "nps-yosemite", "name": "Yosemite webcams", "city": "California",
     "lat": 37.8651, "lng": -119.5383,
     "url": "https://www.nps.gov/yose/learn/photosmultimedia/webcams.htm",
     "source": "National Park Service",
     "source_url": "https://www.nps.gov/yose/learn/photosmultimedia/webcams.htm"},
    {"id": "noaa-ndbc", "name": "NOAA marine observation portal", "city": "United States",
     "lat": 38.8951, "lng": -77.0364,
     "url": "https://www.ndbc.noaa.gov/",
     "source": "NOAA", "source_url": "https://www.ndbc.noaa.gov/"},
    {"id": "ingv-etna", "name": "Etna volcano webcams", "city": "Sicily",
     "lat": 37.7510, "lng": 14.9934,
     "url": "https://www.ct.ingv.it/sezioniesterne/webcam/WebcamEtna.php",
     "source": "INGV", "source_url": "https://www.ct.ingv.it/sezioniesterne/webcam/WebcamEtna.php"},
    {"id": "ingv-italy", "name": "INGV real-time volcano data", "city": "Italy",
     "lat": 41.9028, "lng": 12.4964,
     "url": "https://ingv.it/en/real-time-data-volcanoes-maps",
     "source": "INGV", "source_url": "https://ingv.it/en/real-time-data-volcanoes-maps"},
    {"id": "geonet-nz", "name": "GeoNet volcano cameras", "city": "New Zealand",
     "lat": -39.1568, "lng": 175.6325,
     "url": "https://www.geonet.org.nz/volcano/cameras",
     "source": "GeoNet", "source_url": "https://www.geonet.org.nz/volcano/cameras"},
    {"id": "iceland-roads", "name": "Iceland road webcams", "city": "Reykjavík",
     "lat": 64.1466, "lng": -21.9426,
     "url": "https://umferdin.is/en",
     "source": "Icelandic Road Administration", "source_url": "https://umferdin.is/en"},
    {"id": "vegvesen", "name": "Norwegian road webcams", "city": "Oslo",
     "lat": 59.9139, "lng": 10.7522,
     "url": "https://www.vegvesen.no/trafikk",
     "source": "Statens vegvesen", "source_url": "https://www.vegvesen.no/trafikk"},
    {"id": "foto-webcam-alps", "name": "Alpine public webcams", "city": "Alps",
     "lat": 47.4210, "lng": 10.9850,
     "url": "https://www.foto-webcam.eu/",
     "source": "foto-webcam.eu", "source_url": "https://www.foto-webcam.eu/"},
    {"id": "traffic-scotland", "name": "Traffic Scotland cameras", "city": "Edinburgh",
     "lat": 55.9533, "lng": -3.1883,
     "url": "https://www.traffic.gov.scot/",
     "source": "Traffic Scotland", "source_url": "https://www.traffic.gov.scot/"},
    {"id": "national-highways", "name": "National Highways traffic", "city": "London",
     "lat": 51.5074, "lng": -0.1278,
     "url": "https://nationalhighways.co.uk/",
     "source": "National Highways", "source_url": "https://nationalhighways.co.uk/"},
    {"id": "mss-singapore", "name": "Singapore weather cameras", "city": "Singapore",
     "lat": 1.3521, "lng": 103.8198,
     "url": "https://www.weather.gov.sg/",
     "source": "Meteorological Service Singapore", "source_url": "https://www.weather.gov.sg/"},
    {"id": "usap-mcmurdo", "name": "McMurdo Station webcams", "city": "Antarctica",
     "lat": -77.8419, "lng": 166.6863,
     "url": "https://www.usap.gov/videoclipsandmaps/mcmwebcam.cfm",
     "source": "USAP", "source_url": "https://www.usap.gov/videoclipsandmaps/mcmwebcam.cfm"},
    {"id": "banff-gondola", "name": "Banff Gondola summit webcam", "city": "Banff",
     "lat": 51.1784, "lng": -115.5708,
     "url": "https://www.banffjaspercollection.com/attractions/banff-gondola/webcam/",
     "source": "Banff Gondola", "source_url": "https://www.banffjaspercollection.com/attractions/banff-gondola/webcam/"},
]

# Small boxes around world cities so OSM cams appear at global zoom.
WORLD_HUBS: list[tuple[float, float]] = [
    (51.51, -0.13), (48.86, 2.35), (41.90, 12.50), (52.52, 13.40), (47.37, 8.54),
    (59.91, 10.75), (64.15, -21.94), (41.01, 28.98), (25.20, 55.27), (30.04, 31.24),
    (-33.92, 18.42), (-1.29, 36.82), (19.08, 72.88), (28.61, 77.21), (1.35, 103.82),
    (22.32, 114.17), (35.68, 139.65), (37.57, 126.98), (-33.87, 151.21), (-36.85, 174.76),
    (-22.91, -43.17), (-34.60, -58.38), (-33.45, -70.67), (19.43, -99.13), (49.28, -123.12),
]



def _http_url(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("http://") or text.startswith("https://"):
        return text.split()[0]
    return ""


def _in_bbox(lat: float, lng: float, bbox: tuple[float, float, float, float] | None) -> bool:
    if not bbox:
        return True
    lamin, lomin, lamax, lomax = bbox
    return lamin <= lat <= lamax and lomin <= lng <= lomax


def _bbox_span(bbox: tuple[float, float, float, float] | None) -> float:
    if not bbox:
        return 180.0
    return max(bbox[2] - bbox[0], bbox[3] - bbox[1])


def _cache_key(bbox: tuple[float, float, float, float] | None) -> str:
    if not bbox:
        return "global"
    return ",".join(f"{value:.0f}" for value in bbox)


def _overpass_query(bbox: tuple[float, float, float, float] | None = None, hubs: list[tuple[float, float]] | None = None) -> str:
    parts = ['[out:json][timeout:18];(']
    if bbox:
        lamin, lomin, lamax, lomax = bbox
        box = f"{lamin},{lomin},{lamax},{lomax}"
        parts.append(f'nwr["webcam:url"]({box});nwr["contact:webcam"]({box});node["amenity"="webcam"]({box});')
    for lat, lng in hubs or []:
        box = f"{lat - HUB_SPAN},{lng - HUB_SPAN},{lat + HUB_SPAN},{lng + HUB_SPAN}"
        parts.append(f'nwr["webcam:url"]({box});')
    parts.append(");out center;")
    return "".join(parts)


def _url_from_tags(tags: dict[str, Any]) -> str:
    for key in ("webcam:url", "contact:webcam", "webcam", "url", "website", "image"):
        url = _http_url(tags.get(key))
        if url:
            return url
    return ""


def normalize_overpass(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for element in (payload or {}).get("elements") or []:
        tags = element.get("tags") or {}
        url = _url_from_tags(tags)
        if not url or url in seen:
            continue
        lat = element.get("lat")
        lng = element.get("lon")
        center = element.get("center") or {}
        if lat is None:
            lat = center.get("lat")
        if lng is None:
            lng = center.get("lon")
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (TypeError, ValueError):
            continue
        name = (tags.get("name") or tags.get("description") or "Public webcam").strip()
        seen.add(url)
        rows.append({
            "id": f"osm-{element.get('type')}-{element.get('id')}",
            "name": name[:80],
            "city": (tags.get("addr:city") or tags.get("location") or "").strip(),
            "lat": lat_f,
            "lng": lng_f,
            "url": url,
            "source": "OpenStreetMap",
            "source_url": OSM_COPYRIGHT,
        })
        if len(rows) >= MAX_CAMS:
            break
    return rows


def fetch_overpass(
    bbox: tuple[float, float, float, float] | None = None,
    hubs: list[tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": _overpass_query(bbox, hubs)},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return normalize_overpass(response.json())
    except Exception as exc:
        log.warning("[webcams] Overpass failed: %s", exc)
        return []


def list_webcams(bbox: tuple[float, float, float, float] | None = None, force_refresh: bool = False) -> dict[str, Any]:
    from app.services.overlay_cache import get_or_set

    official = [dict(cam) for cam in PUBLIC_CAMS if _in_bbox(cam["lat"], cam["lng"], bbox)]
    osm: list[dict[str, Any]] = []
    if bbox and _bbox_span(bbox) <= MAX_BBOX_SPAN:
        osm = get_or_set(
            "webcams-osm",
            lambda: fetch_overpass(bbox),
            key=_cache_key(bbox),
            force_refresh=force_refresh,
        )
    else:
        osm = get_or_set(
            "webcams-osm",
            lambda: fetch_overpass(hubs=WORLD_HUBS),
            key="world-hubs",
            force_refresh=force_refresh,
        )

    seen = {row["url"] for row in official}
    merged = official[:]
    for row in osm or []:
        if row["url"] in seen:
            continue
        if bbox and not _in_bbox(row["lat"], row["lng"], bbox):
            continue
        seen.add(row["url"])
        merged.append(row)
        if len(merged) >= MAX_CAMS:
            break

    return {
        "count": len(merged),
        "webcams": merged,
        "sources": SOURCES,
        "note": (
            "Pins link out to the publisher page. Official public camera indexes "
            "show worldwide. Extra OpenStreetMap webcams load around world hubs "
            "and in the current view when you zoom in."
        ),
    }
