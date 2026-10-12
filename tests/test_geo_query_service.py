"""Unit tests for geo_query_service and SGP4 orbit pre-filtering."""

from datetime import datetime, timezone
from app.services.geo_query_service import (
    resolve_country,
    extract_name_filter,
    propagate_tle,
    satellites_over_region,
    COUNTRY_BBOX,
)


def test_resolve_country():
    res = resolve_country("Find Starlink satellites over Germany")
    assert res is not None
    name, bbox = res
    assert name == "Germany"
    assert bbox == COUNTRY_BBOX["germany"]

    res_alias = resolve_country("Show ISS passing over USA")
    assert res_alias is not None
    assert res_alias[0] == "United States"


def test_extract_name_filter():
    assert extract_name_filter("Starlink satellites over France") == "STARLINK"
    assert extract_name_filter("Show GPS satellites over Japan") == "GPS"


def test_propagate_tle_iss():
    l1 = "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9001"
    l2 = "2 25544  51.6400 208.5000 0004500  70.0000 290.0000 15.49500000400001"
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    pos = propagate_tle(l1, l2, now)
    assert pos is not None
    lat, lon, alt = pos
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180
    assert 350 <= alt <= 460


def test_satellites_over_region_prefiltering():
    # Low inclination orbit (e.g. 5 degrees) can never reach high latitude country (e.g. Norway lat_min=57.9)
    low_inc_sat = {
        "norad_cat_id": 99991,
        "name": "EQUATORIAL-SAT",
        "l1": "1 99991U 20001A   24001.50000000  .00001000  00000-0  10000-4 0  9991",
        "l2": "2 99991   05.0000 100.0000 0001000  50.0000 300.0000 15.1000000010001",
    }
    norway_bbox = COUNTRY_BBOX["norway"]
    matched = satellites_over_region([low_inc_sat], norway_bbox)
    assert len(matched) == 0
