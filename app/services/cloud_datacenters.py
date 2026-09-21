"""AWS, Azure, and GCP region pins with HTTPS ping percentiles (no API key)."""

from __future__ import annotations

import logging
import math
import socket
import time
import copy
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

import requests

from app.services import overlay_http
from app.services.overlay_cache import get_fresh, get_stale, store

log = logging.getLogger(__name__)

SAMPLE_COUNT = 3
PING_TIMEOUT = 4.0
PING_CONNECT_TIMEOUT = 2.5
PING_WORKERS = 10
CACHE_NS = "cloud-datacenters"
HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
    "Accept": "*/*",
    "Connection": "close",
}
GCPING_ENDPOINTS = "https://global.gcping.com/api/endpoints"
GCPING_HOME = "https://www.gcping.com/"
AZURE_SPEED_HOME = "https://www.azurespeed.com/"
AWS_INFRA_HOME = "https://aws.amazon.com/about-aws/global-infrastructure/regions_az/"
AZURE_GEO_HOME = "https://azure.microsoft.com/explore/global-infrastructure/geographies/"
GCP_LOCATIONS_HOME = "https://cloud.google.com/about/locations"

PROVIDERS = {
    "aws": {
        "label": "AWS",
        "color": "#FF9900",
        "letter": "A",
        "lat_off": 0.0,
        "lng_off": 0.0,
        "docs": AWS_INFRA_HOME,
    },
    "azure": {
        "label": "Azure",
        "color": "#0078D4",
        "letter": "Az",
        "lat_off": 0.32,
        "lng_off": 0.42,
        "docs": AZURE_GEO_HOME,
    },
    "gcp": {
        "label": "GCP",
        "color": "#34A853",
        "letter": "G",
        "lat_off": -0.32,
        "lng_off": -0.42,
        "docs": GCP_LOCATIONS_HOME,
    },
}

SOURCES = [
    {
        "name": "Amazon Web Services",
        "url": AWS_INFRA_HOME,
        "license": "Public region geography; DynamoDB /ping is unauthenticated",
        "attribution": (
            "Region pins use AWS public geography. Latency is HTTPS round-trip to "
            "https://dynamodb.{region}.amazonaws.com/ping from this SatTrack server."
        ),
    },
    {
        "name": "Microsoft Azure",
        "url": AZURE_GEO_HOME,
        "license": "Public region geography; AzureSpeed public blobs",
        "attribution": (
            "Region pins use Azure public geographies. Latency is HTTPS round-trip to "
            "public Azure Speed Test blobs (azurespeed.com), not ICMP."
        ),
    },
    {
        "name": "Google Cloud",
        "url": GCP_LOCATIONS_HOME,
        "license": "Public region geography; GCPing Cloud Run /api/ping",
        "attribution": (
            "Region pins use Google Cloud public locations. Latency is HTTPS round-trip to "
            "GCPing Cloud Run /api/ping (gcping.com)."
        ),
    },
]

# City-level public region geography (not a building address).
# (provider, region_id, display_name, city, lat, lng)
REGIONS: list[tuple[str, str, str, str, float, float]] = [
    ("aws", "us-east-1", "US East (N. Virginia)", "Ashburn", 39.0438, -77.4874),
    ("aws", "us-east-2", "US East (Ohio)", "Columbus", 39.9612, -82.9988),
    ("aws", "us-west-1", "US West (N. California)", "San Jose", 37.3382, -121.8863),
    ("aws", "us-west-2", "US West (Oregon)", "Boardman", 45.8399, -119.7006),
    ("aws", "ca-central-1", "Canada (Central)", "Montreal", 45.5019, -73.5674),
    ("aws", "ca-west-1", "Canada West (Calgary)", "Calgary", 51.0447, -114.0719),
    ("aws", "sa-east-1", "South America (São Paulo)", "São Paulo", -23.5505, -46.6333),
    ("aws", "mx-central-1", "Mexico (Central)", "Querétaro", 20.5888, -100.3899),
    ("aws", "eu-west-1", "Europe (Ireland)", "Dublin", 53.3498, -6.2603),
    ("aws", "eu-west-2", "Europe (London)", "London", 51.5074, -0.1278),
    ("aws", "eu-west-3", "Europe (Paris)", "Paris", 48.8566, 2.3522),
    ("aws", "eu-central-1", "Europe (Frankfurt)", "Frankfurt", 50.1109, 8.6821),
    ("aws", "eu-central-2", "Europe (Zurich)", "Zurich", 47.3769, 8.5417),
    ("aws", "eu-north-1", "Europe (Stockholm)", "Stockholm", 59.3293, 18.0686),
    ("aws", "eu-south-1", "Europe (Milan)", "Milan", 45.4642, 9.1900),
    ("aws", "eu-south-2", "Europe (Spain)", "Aragón", 41.6488, -0.8891),
    ("aws", "af-south-1", "Africa (Cape Town)", "Cape Town", -33.9249, 18.4241),
    ("aws", "me-south-1", "Middle East (Bahrain)", "Manama", 26.2235, 50.5876),
    ("aws", "me-central-1", "Middle East (UAE)", "Dubai", 25.2048, 55.2708),
    ("aws", "il-central-1", "Israel (Tel Aviv)", "Tel Aviv", 32.0853, 34.7818),
    ("aws", "ap-south-1", "Asia Pacific (Mumbai)", "Mumbai", 19.0760, 72.8777),
    ("aws", "ap-south-2", "Asia Pacific (Hyderabad)", "Hyderabad", 17.3850, 78.4867),
    ("aws", "ap-southeast-1", "Asia Pacific (Singapore)", "Singapore", 1.3521, 103.8198),
    ("aws", "ap-southeast-2", "Asia Pacific (Sydney)", "Sydney", -33.8688, 151.2093),
    ("aws", "ap-southeast-3", "Asia Pacific (Jakarta)", "Jakarta", -6.2088, 106.8456),
    ("aws", "ap-southeast-4", "Asia Pacific (Melbourne)", "Melbourne", -37.8136, 144.9631),
    ("aws", "ap-southeast-5", "Asia Pacific (Malaysia)", "Kuala Lumpur", 3.1390, 101.6869),
    ("aws", "ap-northeast-1", "Asia Pacific (Tokyo)", "Tokyo", 35.6762, 139.6503),
    ("aws", "ap-northeast-2", "Asia Pacific (Seoul)", "Seoul", 37.5665, 126.9780),
    ("aws", "ap-northeast-3", "Asia Pacific (Osaka)", "Osaka", 34.6937, 135.5023),
    ("aws", "ap-east-1", "Asia Pacific (Hong Kong)", "Hong Kong", 22.3193, 114.1694),
    ("aws", "ap-east-2", "Asia Pacific (Taipei)", "Taipei", 25.0330, 121.5654),
    ("azure", "eastus", "East US", "Virginia", 37.4316, -78.6569),
    ("azure", "eastus2", "East US 2", "Virginia", 37.2710, -79.9414),
    ("azure", "westus", "West US", "California", 37.3382, -121.8863),
    ("azure", "westus2", "West US 2", "Washington", 47.2529, -119.8520),
    ("azure", "westus3", "West US 3", "Arizona", 33.4484, -112.0740),
    ("azure", "centralus", "Central US", "Iowa", 41.5868, -93.6250),
    ("azure", "northcentralus", "North Central US", "Illinois", 41.8781, -87.6298),
    ("azure", "southcentralus", "South Central US", "Texas", 29.4241, -98.4936),
    ("azure", "westcentralus", "West Central US", "Wyoming", 41.1400, -104.8202),
    ("azure", "canadacentral", "Canada Central", "Toronto", 43.6532, -79.3832),
    ("azure", "canadaeast", "Canada East", "Quebec City", 46.8139, -71.2080),
    ("azure", "brazilsouth", "Brazil South", "São Paulo", -23.5505, -46.6333),
    ("azure", "mexicocentral", "Mexico Central", "Querétaro", 20.5888, -100.3899),
    ("azure", "chilecentral", "Chile Central", "Santiago", -33.4489, -70.6693),
    ("azure", "northeurope", "North Europe", "Dublin", 53.3498, -6.2603),
    ("azure", "westeurope", "West Europe", "Netherlands", 52.3676, 4.9041),
    ("azure", "uksouth", "UK South", "London", 51.5074, -0.1278),
    ("azure", "ukwest", "UK West", "Cardiff", 51.4816, -3.1791),
    ("azure", "francecentral", "France Central", "Paris", 48.8566, 2.3522),
    ("azure", "germanywestcentral", "Germany West Central", "Frankfurt", 50.1109, 8.6821),
    ("azure", "switzerlandnorth", "Switzerland North", "Zurich", 47.3769, 8.5417),
    ("azure", "norwayeast", "Norway East", "Oslo", 59.9139, 10.7522),
    ("azure", "swedencentral", "Sweden Central", "Gävle", 60.6749, 17.1413),
    ("azure", "polandcentral", "Poland Central", "Warsaw", 52.2297, 21.0122),
    ("azure", "italynorth", "Italy North", "Milan", 45.4642, 9.1900),
    ("azure", "spaincentral", "Spain Central", "Madrid", 40.4168, -3.7038),
    ("azure", "austriaeast", "Austria East", "Vienna", 48.2082, 16.3738),
    ("azure", "belgiumcentral", "Belgium Central", "Brussels", 50.8503, 4.3517),
    ("azure", "denmarkeast", "Denmark East", "Copenhagen", 55.6761, 12.5683),
    ("azure", "southafricanorth", "South Africa North", "Johannesburg", -26.2041, 28.0473),
    ("azure", "uaenorth", "UAE North", "Dubai", 25.2048, 55.2708),
    ("azure", "qatarcentral", "Qatar Central", "Doha", 25.2854, 51.5310),
    ("azure", "israelcentral", "Israel Central", "Tel Aviv", 32.0853, 34.7818),
    ("azure", "eastasia", "East Asia", "Hong Kong", 22.3193, 114.1694),
    ("azure", "southeastasia", "Southeast Asia", "Singapore", 1.3521, 103.8198),
    ("azure", "japaneast", "Japan East", "Tokyo", 35.6762, 139.6503),
    ("azure", "japanwest", "Japan West", "Osaka", 34.6937, 135.5023),
    ("azure", "koreacentral", "Korea Central", "Seoul", 37.5665, 126.9780),
    ("azure", "koreasouth", "Korea South", "Busan", 35.1796, 129.0756),
    ("azure", "centralindia", "Central India", "Pune", 18.5204, 73.8567),
    ("azure", "southindia", "South India", "Chennai", 13.0827, 80.2707),
    ("azure", "westindia", "West India", "Mumbai", 19.0760, 72.8777),
    ("azure", "australiaeast", "Australia East", "Sydney", -33.8688, 151.2093),
    ("azure", "australiasoutheast", "Australia Southeast", "Melbourne", -37.8136, 144.9631),
    ("azure", "australiacentral", "Australia Central", "Canberra", -35.2809, 149.1300),
    ("azure", "newzealandnorth", "New Zealand North", "Auckland", -36.8509, 174.7645),
    ("azure", "indonesiacentral", "Indonesia Central", "Jakarta", -6.2088, 106.8456),
    ("azure", "malaysiawest", "Malaysia West", "Kuala Lumpur", 3.1390, 101.6869),
    ("gcp", "us-central1", "Iowa", "Council Bluffs", 41.2619, -95.8608),
    ("gcp", "us-east1", "South Carolina", "Moncks Corner", 33.1960, -80.0131),
    ("gcp", "us-east4", "Northern Virginia", "Ashburn", 39.0438, -77.4874),
    ("gcp", "us-east5", "Columbus", "Columbus", 39.9612, -82.9988),
    ("gcp", "us-south1", "Dallas", "Dallas", 32.7767, -96.7970),
    ("gcp", "us-west1", "Oregon", "The Dalles", 45.5946, -121.1787),
    ("gcp", "us-west2", "Los Angeles", "Los Angeles", 34.0522, -118.2437),
    ("gcp", "us-west3", "Salt Lake City", "Salt Lake City", 40.7608, -111.8910),
    ("gcp", "us-west4", "Las Vegas", "Las Vegas", 36.1699, -115.1398),
    ("gcp", "northamerica-northeast1", "Montréal", "Montréal", 45.5019, -73.5674),
    ("gcp", "northamerica-northeast2", "Toronto", "Toronto", 43.6532, -79.3832),
    ("gcp", "northamerica-south1", "Mexico", "Querétaro", 20.5888, -100.3899),
    ("gcp", "southamerica-east1", "São Paulo", "Osasco", -23.5329, -46.7916),
    ("gcp", "southamerica-west1", "Santiago", "Santiago", -33.4489, -70.6693),
    ("gcp", "europe-west1", "Belgium", "St. Ghislain", 50.4490, 3.8186),
    ("gcp", "europe-west2", "London", "London", 51.5074, -0.1278),
    ("gcp", "europe-west3", "Frankfurt", "Frankfurt", 50.1109, 8.6821),
    ("gcp", "europe-west4", "Netherlands", "Eemshaven", 53.4386, 6.8311),
    ("gcp", "europe-west6", "Zurich", "Zurich", 47.3769, 8.5417),
    ("gcp", "europe-west8", "Milan", "Milan", 45.4642, 9.1900),
    ("gcp", "europe-west9", "Paris", "Paris", 48.8566, 2.3522),
    ("gcp", "europe-west10", "Berlin", "Berlin", 52.5200, 13.4050),
    ("gcp", "europe-west12", "Turin", "Turin", 45.0703, 7.6869),
    ("gcp", "europe-north1", "Finland", "Hamina", 60.5693, 27.1878),
    ("gcp", "europe-north2", "Stockholm", "Stockholm", 59.3293, 18.0686),
    ("gcp", "europe-central2", "Warsaw", "Warsaw", 52.2297, 21.0122),
    ("gcp", "europe-southwest1", "Madrid", "Madrid", 40.4168, -3.7038),
    ("gcp", "africa-south1", "Johannesburg", "Johannesburg", -26.2041, 28.0473),
    ("gcp", "me-west1", "Tel Aviv", "Tel Aviv", 32.0853, 34.7818),
    ("gcp", "me-central1", "Doha", "Doha", 25.2854, 51.5310),
    ("gcp", "me-central2", "Dammam", "Dammam", 26.4207, 50.0888),
    ("gcp", "asia-east1", "Taiwan", "Changhua County", 24.0518, 120.5161),
    ("gcp", "asia-east2", "Hong Kong", "Hong Kong", 22.3193, 114.1694),
    ("gcp", "asia-northeast1", "Tokyo", "Tokyo", 35.6762, 139.6503),
    ("gcp", "asia-northeast2", "Osaka", "Osaka", 34.6937, 135.5023),
    ("gcp", "asia-northeast3", "Seoul", "Seoul", 37.5665, 126.9780),
    ("gcp", "asia-south1", "Mumbai", "Mumbai", 19.0760, 72.8777),
    ("gcp", "asia-south2", "Delhi", "Delhi", 28.6139, 77.2090),
    ("gcp", "asia-southeast1", "Singapore", "Jurong West", 1.3404, 103.7090),
    ("gcp", "asia-southeast2", "Jakarta", "Jakarta", -6.2088, 106.8456),
    ("gcp", "australia-southeast1", "Sydney", "Sydney", -33.8688, 151.2093),
    ("gcp", "australia-southeast2", "Melbourne", "Melbourne", -37.8136, 144.9631),
]

GCP_FALLBACK_URLS = {
    "africa-south1": "https://africa-south1-5tkroniexa-bq.a.run.app",
    "asia-east1": "https://asia-east1-5tkroniexa-de.a.run.app",
    "asia-east2": "https://asia-east2-5tkroniexa-df.a.run.app",
    "asia-northeast1": "https://asia-northeast1-5tkroniexa-an.a.run.app",
    "asia-northeast2": "https://asia-northeast2-5tkroniexa-dt.a.run.app",
    "asia-northeast3": "https://asia-northeast3-5tkroniexa-du.a.run.app",
    "asia-south1": "https://asia-south1-5tkroniexa-el.a.run.app",
    "asia-south2": "https://asia-south2-5tkroniexa-em.a.run.app",
    "asia-southeast1": "https://asia-southeast1-5tkroniexa-as.a.run.app",
    "asia-southeast2": "https://asia-southeast2-5tkroniexa-et.a.run.app",
    "asia-southeast3": "https://asia-southeast3-5tkroniexa-eu.a.run.app",
    "australia-southeast1": "https://australia-southeast1-5tkroniexa-ts.a.run.app",
    "australia-southeast2": "https://australia-southeast2-5tkroniexa-km.a.run.app",
    "europe-central2": "https://europe-central2-5tkroniexa-lm.a.run.app",
    "europe-north1": "https://europe-north1-5tkroniexa-lz.a.run.app",
    "europe-north2": "https://europe-north2-5tkroniexa-ma.a.run.app",
    "europe-southwest1": "https://europe-southwest1-5tkroniexa-no.a.run.app",
    "europe-west1": "https://europe-west1-5tkroniexa-ew.a.run.app",
    "europe-west10": "https://europe-west10-5tkroniexa-oe.a.run.app",
    "europe-west12": "https://europe-west12-5tkroniexa-og.a.run.app",
    "europe-west2": "https://europe-west2-5tkroniexa-nw.a.run.app",
    "europe-west3": "https://europe-west3-5tkroniexa-ey.a.run.app",
    "europe-west4": "https://europe-west4-5tkroniexa-ez.a.run.app",
    "europe-west6": "https://europe-west6-5tkroniexa-oa.a.run.app",
    "europe-west8": "https://europe-west8-5tkroniexa-oc.a.run.app",
    "europe-west9": "https://europe-west9-5tkroniexa-od.a.run.app",
    "me-central1": "https://me-central1-5tkroniexa-ww.a.run.app",
    "me-central2": "https://me-central2-5tkroniexa-wx.a.run.app",
    "me-west1": "https://me-west1-5tkroniexa-zf.a.run.app",
    "northamerica-northeast1": "https://northamerica-northeast1-5tkroniexa-nn.a.run.app",
    "northamerica-northeast2": "https://northamerica-northeast2-5tkroniexa-pd.a.run.app",
    "northamerica-south1": "https://northamerica-south1-5tkroniexa-pv.a.run.app",
    "southamerica-east1": "https://southamerica-east1-5tkroniexa-rj.a.run.app",
    "southamerica-west1": "https://southamerica-west1-5tkroniexa-tl.a.run.app",
    "us-central1": "https://us-central1-5tkroniexa-uc.a.run.app",
    "us-east1": "https://us-east1-5tkroniexa-ue.a.run.app",
    "us-east4": "https://us-east4-5tkroniexa-uk.a.run.app",
    "us-east5": "https://us-east5-5tkroniexa-ul.a.run.app",
    "us-south1": "https://us-south1-5tkroniexa-vp.a.run.app",
    "us-west1": "https://us-west1-5tkroniexa-uw.a.run.app",
    "us-west2": "https://us-west2-5tkroniexa-wl.a.run.app",
    "us-west3": "https://us-west3-5tkroniexa-wm.a.run.app",
    "us-west4": "https://us-west4-5tkroniexa-wn.a.run.app",
}


def percentile(samples: list[float], p: float) -> float | None:
    """Linear-interpolated percentile; p in 0..100."""
    if not samples:
        return None
    ordered = sorted(float(v) for v in samples)
    if len(ordered) == 1:
        return round(ordered[0], 1)
    rank = (max(0.0, min(100.0, p)) / 100.0) * (len(ordered) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return round(ordered[lo], 1)
    frac = rank - lo
    return round(ordered[lo] * (1.0 - frac) + ordered[hi] * frac, 1)


def ping_url_for(provider: str, region_id: str, gcp_urls: dict[str, str] | None = None) -> str:
    if provider == "aws":
        return f"https://dynamodb.{region_id}.amazonaws.com/ping"
    if provider == "azure":
        return f"https://s8{region_id}.blob.core.windows.net/public/latency-test.json"
    base = (gcp_urls or {}).get(region_id) or GCP_FALLBACK_URLS.get(region_id) or ""
    return f"{base.rstrip('/')}/api/ping" if base else ""


def http_rtt_ms(url: str, timeout: float = PING_TIMEOUT) -> float | None:
    """HTTPS round-trip in ms. Any HTTP completion counts, including 4xx/5xx."""
    if not url or not url.startswith("https://"):
        return None
    started = time.perf_counter()
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(PING_CONNECT_TIMEOUT, timeout),
            allow_redirects=False,
        )
        try:
            response.close()
        except Exception:
            pass
    except Exception:
        return None
    return round((time.perf_counter() - started) * 1000.0, 1)


def ping_samples(url: str, count: int = SAMPLE_COUNT) -> list[float]:
    first = http_rtt_ms(url)
    if first is None:
        first = http_rtt_ms(url)
    if first is None:
        return []
    samples = [first]
    for _ in range(max(0, count - 1)):
        sample = http_rtt_ms(url)
        if sample is not None:
            samples.append(sample)
    return samples


def _gcp_endpoint_urls() -> dict[str, str]:
    data = overlay_http.get_json(GCPING_ENDPOINTS, headers=HEADERS, timeout=8, source="cloud-dc")
    if not isinstance(data, dict):
        log.warning("[cloud-dc] GCPing endpoints failed; using fallback URLs")
        return dict(GCP_FALLBACK_URLS)
    urls: dict[str, str] = {}
    for key, row in data.items():
        if key == "global" or not isinstance(row, dict):
            continue
        url = str(row.get("URL") or "").rstrip("/")
        if url.startswith("https://"):
            urls[key] = url
    return urls or dict(GCP_FALLBACK_URLS)


def _summarize(samples: list[float]) -> dict[str, Any]:
    return {
        "p50": percentile(samples, 50),
        "p95": percentile(samples, 95),
        "p99": percentile(samples, 99),
        "samples": len(samples),
    }


_worker_guard = threading.Lock()
_worker: threading.Thread | None = None


def _site_row(
    provider: str,
    region_id: str,
    name: str,
    city: str,
    lat: float,
    lng: float,
    url: str,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = PROVIDERS[provider]
    stats = stats or _summarize([])
    return {
        "id": f"{provider}:{region_id}",
        "provider": provider,
        "provider_label": meta["label"],
        "region": region_id,
        "name": name,
        "city": city,
        "lat": round(lat + meta["lat_off"], 4),
        "lng": round(lng + meta["lng_off"], 4),
        "color": meta["color"],
        "letter": meta["letter"],
        "ping_url": url,
        "p50": stats["p50"],
        "p95": stats["p95"],
        "p99": stats["p99"],
        "samples": stats["samples"],
        "docs_url": meta["docs"],
    }


def _payload(
    latencies: dict[tuple[str, str], dict[str, Any]],
    gcp_urls: dict[str, str] | None = None,
    pending: bool = True,
) -> dict[str, Any]:
    sites = []
    pinged = 0
    for provider, region_id, name, city, lat, lng in REGIONS:
        stats = latencies.get((provider, region_id))
        if stats and stats.get("p50") is not None:
            pinged += 1
        sites.append(_site_row(
            provider,
            region_id,
            name,
            city,
            lat,
            lng,
            ping_url_for(provider, region_id, gcp_urls),
            stats,
        ))
    total = len(sites)
    return {
        "count": total,
        "pinged": pinged,
        "total": total,
        "pending": bool(pending and pinged < total),
        "status": (
            f"Pinged {pinged}/{total} regions"
            if pinged
            else "Region pins ready; HTTPS pings running"
        ),
        "from_host": socket.gethostname(),
        "method": "HTTPS GET round-trip (not ICMP)",
        "sample_count": SAMPLE_COUNT,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "datacenters": sites,
        "sources": SOURCES,
    }


def _run_pings() -> None:
    log.info("[cloud-dc] Starting HTTPS pings for %s regions (%s samples each)", len(REGIONS), SAMPLE_COUNT)
    gcp_urls = _gcp_endpoint_urls()
    latencies: dict[tuple[str, str], dict[str, Any]] = {}
    jobs = [
        (provider, region_id, ping_url_for(provider, region_id, gcp_urls))
        for provider, region_id, _name, _city, _lat, _lng in REGIONS
    ]
    last_store = 0.0
    with ThreadPoolExecutor(max_workers=PING_WORKERS) as pool:
        futures = {
            pool.submit(ping_samples, url): (provider, region_id)
            for provider, region_id, url in jobs
            if url
        }
        total = len(futures) or 1
        for future in as_completed(futures):
            key = futures[future]
            try:
                latencies[key] = _summarize(future.result())
            except Exception as exc:
                log.warning("[cloud-dc] Ping failed %s: %s", key, exc)
                latencies[key] = _summarize([])
            done = len(latencies)
            now = time.time()
            if done == total or done % 8 == 0 or now - last_store >= 0.6:
                payload = _payload(latencies, gcp_urls, pending=done < total)
                store(CACHE_NS, payload)
                last_store = now
                log.info("[cloud-dc] %s", payload["status"])
    final = _payload(latencies, gcp_urls, pending=False)
    final["status"] = f"Pinged {final['pinged']}/{final['total']} regions"
    store(CACHE_NS, final)
    log.info("[cloud-dc] Finished %s", final["status"])


def _ensure_worker() -> None:
    global _worker
    with _worker_guard:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_run_pings, name="cloud-dc-pings", daemon=True)
        _worker.start()


def list_cloud_datacenters() -> dict[str, Any]:
    current = get_stale(CACHE_NS)
    if current and current.get("pending"):
        _ensure_worker()
        return current
    fresh = get_fresh(CACHE_NS)
    if fresh is not None:
        return fresh
    payload = _payload({}, pending=True)
    store(CACHE_NS, payload)
    _ensure_worker()
    log.info("[cloud-dc] Serving %s region pins while pings run in the background", payload["count"])
    return copy.deepcopy(payload)
