from io import BytesIO
import os
from unittest.mock import MagicMock

from sqlalchemy import inspect

from app import db, _seed_kaggle_data_if_needed
from app.models import Satellite, Upload
from app.services.demo_tle import demo_tle_text
from app.services.tle_parser import _parse_decimal_packed, parse_tle_file

SAMPLE_TLE = (
    "ISS (ZARYA)\n"
    "1 25544U 98067A   08264.51782528 -.00002182  00000-0 -11606-4 0  2927\n"
    "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537\n"
)


def test_get_upload_page_renders_form(client):
    response = client.get("/upload")
    assert response.status_code == 200
    assert b"upload-form" in response.data
    assert b"Upload &amp; Parse TLE" in response.data or b"Upload" in response.data
    assert b"Demo / hobby project" in response.data
    assert b"for learning only" in response.data


def test_nav_upload_is_not_home_redirect(client):
    home = client.get("/", follow_redirects=False)
    assert home.status_code == 302
    assert "/report" in home.headers.get("Location", "")

    upload = client.get("/upload", follow_redirects=False)
    assert upload.status_code == 200


def test_upload_page_creates_missing_tables(app, client):
    with app.app_context():
        db.drop_all()
    app.config["SCHEMA_READY"] = False
    response = client.get("/upload")
    assert response.status_code == 200
    assert b"upload-form" in response.data
    with app.app_context():
        assert inspect(db.engine).has_table("uploads")


def test_upload_tle_file_creates_satellite(client, app):
    response = client.post(
        "/upload",
        data={"file": (BytesIO(SAMPLE_TLE.encode("utf-8")), "iss.tle")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Upload Complete" in response.data
    with app.app_context():
        sat = Satellite.query.filter_by(norad_cat_id=25544).first()
        assert sat is not None
        assert "ISS" in sat.name


def test_demo_tle_sample_parses():
    records = parse_tle_file(demo_tle_text())
    assert len(records) >= 6
    names = {row["name"] for row in records}
    assert "ISS (ZARYA)" in names
    assert "STARLINK-1007" in names


def test_parse_decimal_packed_variants():
    assert _parse_decimal_packed(" 00000-0") == 0.0
    assert _parse_decimal_packed(" 00000+0") == 0.0
    assert abs(_parse_decimal_packed("-11606-4") - (-1.1606e-5)) < 1e-12
    assert abs(_parse_decimal_packed(" 12345-3") - 1.2345e-4) < 1e-12
    assert abs(_parse_decimal_packed("+12345+2") - 12.345) < 1e-12
    assert _parse_decimal_packed("") == 0.0
    assert _parse_decimal_packed("0") == 0.0
    assert _parse_decimal_packed("invalid-str") == 0.0
    assert _parse_decimal_packed("123+xyz") == 0.0


def test_seed_loads_demo_when_kaggle_file_missing(app, monkeypatch):
    real_exists = os.path.exists

    def fake_exists(path):
        if "kaggle_tle_data.txt" in str(path):
            return False
        return real_exists(path)

    monkeypatch.setattr(os.path, "exists", fake_exists)
    with app.app_context():
        app.config["SEED_APPLIED"] = False
        _seed_kaggle_data_if_needed(app)
        demo_upload = Upload.query.filter_by(source="demo").first()
        assert demo_upload is not None
        assert demo_upload.is_seed is True
        assert "Demo" in (demo_upload.label or "")
        assert Satellite.query.count() >= 6


def test_is_safe_url_validation():
    from app.routes.upload import is_safe_url

    assert is_safe_url("https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle") is True
    assert is_safe_url("http://celestrak.org/elements.txt") is True
    assert is_safe_url("https://example.com/tle.txt") is True

    # Reject loopback & private networks (SSRF defense)
    assert is_safe_url("http://localhost:5000") is False
    assert is_safe_url("http://127.0.0.1/admin") is False
    assert is_safe_url("http://127.0.0.1:8080/data") is False
    assert is_safe_url("http://169.254.169.254/latest/meta-data/") is False
    assert is_safe_url("http://10.0.0.1/tle.txt") is False
    assert is_safe_url("http://192.168.1.1/tle.txt") is False
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("ftp://celestrak.org/tle.txt") is False
    assert is_safe_url("javascript:alert(1)") is False
    assert is_safe_url("") is False


def test_derive_filename_from_url():
    from app.routes.upload import derive_filename_from_url

    assert derive_filename_from_url("https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle") == "celestrak_active.tle"
    assert derive_filename_from_url("https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle") == "celestrak_stations.tle"
    assert derive_filename_from_url("https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle") == "celestrak_25544.tle"
    assert derive_filename_from_url("https://example.com/custom_satellites.tle") == "custom_satellites.tle"


def test_upload_page_contains_celestrak_elements_and_presets(client):
    from app.routes.upload import DEFAULT_CELESTRAK_URL

    response = client.get("/upload")
    assert response.status_code == 200
    assert b"CelesTrak URL Import" in response.data
    assert b"url-import-form" in response.data
    assert DEFAULT_CELESTRAK_URL.encode("utf-8") in response.data
    assert b"GROUP=stations" in response.data
    assert b"GROUP=visual" in response.data
    assert b"GROUP=starlink" in response.data
    assert b"GROUP=weather" in response.data


def test_import_from_url_success(client, app, monkeypatch):
    from unittest.mock import MagicMock
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_TLE
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    test_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
    response = client.post(
        "/import-url",
        data={"url": test_url},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Upload Complete" in response.data
    assert b"celestrak_stations.tle" in response.data

    with app.app_context():
        sat = Satellite.query.filter_by(norad_cat_id=25544).first()
        assert sat is not None
        assert "ISS" in sat.name

        upload_entry = Upload.query.filter_by(filename="celestrak_stations.tle").first()
        assert upload_entry is not None
        assert upload_entry.source == "celestrak_url"


def test_import_from_url_defaults_to_active_celestrak(client, app, monkeypatch):
    from unittest.mock import MagicMock
    import requests

    called_urls = []

    def mock_get(url, *args, **kwargs):
        called_urls.append(url)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_TLE
        return mock_resp

    monkeypatch.setattr(requests, "get", mock_get)

    response = client.post("/import-url", data={}, follow_redirects=False)
    assert response.status_code == 200
    assert b"Upload Complete" in response.data
    assert len(called_urls) == 1
    assert "GROUP=active" in called_urls[0]


def test_import_from_url_unsafe_rejected(client):
    response = client.post(
        "/import-url",
        data={"url": "http://127.0.0.1:8080/private"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid or prohibited URL" in response.data


def test_import_from_url_rate_limit_handled_with_fallback(client, app, monkeypatch):
    from unittest.mock import MagicMock
    import requests

    # Simulate CelesTrak 403 2-hour interval rate notice
    rate_msg = "GP data has not updated since your last successful download of GROUP=active at 2026-10-11 18:00:00 UTC. Data is updated once every 2 hours."
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = rate_msg
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    response = client.post(
        "/import-url",
        data={"url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Should either ingest from cache snapshot or notify cleanly
    assert (
        b"Upload Complete" in response.data
        or b"CelesTrak rate notice" in response.data
        or b"Data is updated once every 2 hours" in response.data
    )


def test_upload_route_supports_url_field(client, app, monkeypatch):
    from unittest.mock import MagicMock
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_TLE
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    response = client.post(
        "/upload",
        data={"url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Upload Complete" in response.data


def test_import_from_url_json_api_response(client, monkeypatch):
    """Verify that import_from_url responds with rich JSON payload when requested asynchronously."""
    import requests

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_TLE
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    response = client.post(
        "/import-url",
        data={"url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["parsed_count"] == 1
    assert data["created_count"] + data["updated_count"] == 1
    assert "redirect_url" in data


def test_celestrak_progress_card_markup(client):
    """Verify that upload template includes the real-time CelesTrak progress card and fallback details."""
    response = client.get("/upload")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'id="celestrak-progress-card"' in html
    assert 'id="cp-step-1"' in html
    assert 'id="cp-step-2"' in html
    assert 'id="cp-step-3"' in html
    assert 'id="cp-step-4"' in html
    assert 'id="cp-timer"' in html
    assert "Resilience &amp; Snapshot Fallback:" in html


