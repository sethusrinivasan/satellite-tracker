from io import BytesIO
import os

from sqlalchemy import inspect

from app import db, _seed_kaggle_data_if_needed
from app.models import Satellite, Upload
from app.services.demo_tle import demo_tle_text
from app.services.tle_parser import parse_tle_file

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
