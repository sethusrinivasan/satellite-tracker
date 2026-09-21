from io import BytesIO

from app.models import Satellite
from app.services.demo_tle import demo_tle_text


def _results_html(html: str) -> str:
    start = html.find('id="results-area"')
    assert start != -1
    return html[start:]


def _upload_sample(client):
    return client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )


def test_search_nav_defaults_to_keyword_tab(client):
    response = client.get("/report")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'id="tab-keyword-btn"' in html
    assert 'id="keyword-search-container"' in html
    assert 'id="keyword-search-container" style="display: none' not in html
    assert 'id="country-search-container" style="display: none' in html
    assert "Keyword Search" in html
    assert "Demo / hobby project" in html
    assert "for learning only" in html
    assert "Do not use SatTrack for real operational work" in html
    assert "loadProximityOptions" in html
    assert "/api/proximity/options" in html or "proximity_options" in html


def test_empty_keyword_search_lists_all_records(client, app):
    _upload_sample(client)
    response = client.get("/report")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ISS (ZARYA)" in html
    assert "STARLINK-1007" in html
    with app.app_context():
        assert Satellite.query.count() >= 6
    assert "Showing" in html
    assert "Enter a search term above" not in html


def test_empty_q_param_is_wildcard_list(client):
    _upload_sample(client)
    response = client.get("/report?q=")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ISS (ZARYA)" in html
    assert "STARLINK-1007" in html


def test_keyword_like_matches_name(client):
    _upload_sample(client)
    response = client.get("/report?q=starlink")
    html = response.get_data(as_text=True)
    assert "STARLINK-1007" in html
    assert "ISS (ZARYA)" not in html
    assert "matching" in html


def test_keyword_like_matches_norad_and_designator(client):
    _upload_sample(client)
    by_norad = _results_html(client.get("/report?q=25544").get_data(as_text=True))
    assert "ISS (ZARYA)" in by_norad
    assert 'data-norad="44713"' not in by_norad

    by_designator = _results_html(client.get("/report?q=98067A").get_data(as_text=True))
    assert "ISS (ZARYA)" in by_designator
    assert 'data-norad="44713"' not in by_designator


def test_keyword_like_matches_raw_tle_text(client):
    _upload_sample(client)
    html = _results_html(client.get("/report?q=51.6416").get_data(as_text=True))
    assert "ISS (ZARYA)" in html
    assert 'data-norad="44713"' not in html


def test_satellite_detail_map_uses_keyless_basemap(client):
    _upload_sample(client)
    response = client.get("/report/satellite/48274")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "basemap.js" in html
    assert "SatTrackBasemap.addDefaultBasemap" in html
    assert "basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'" not in html
    assert "map-fullscreen-btn" in html
    assert "toggleOrbitMapFullscreen" in html
    assert "Exit full screen" in html


def test_tracker_js_fits_view_to_satellites_with_1000km_radius(client):
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert "SAT_VIEW_RADIUS_KM = 1000" in js
    assert "fitMapToTrackedSats" in js
    assert "boundsForSatelliteCoverage" in js
    assert "fitBounds" in js
    _upload_sample(client)
    html = client.get("/tracker?ids=25544,44713").get_data(as_text=True)
    assert "1000 km radius" in html
    assert "tracker.js" in html


def test_proximity_options_lists_geo_countries_and_name_prefixes(client):
    _upload_sample(client)
    response = client.get("/api/proximity/options")
    assert response.status_code == 200
    payload = response.get_json()
    countries = {row["name"] for row in payload["countries"]}
    assert "United States" in countries
    assert "India" in countries
    prefixes = {row["prefix"]: row["count"] for row in payload["prefixes"]}
    assert prefixes.get("ISS")
    assert prefixes.get("STARLINK")
    assert prefixes.get("CSS")
