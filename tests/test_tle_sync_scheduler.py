"""Tests for background CelesTrak TLE sync scheduler and freshness service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app import db
from app.models import Satellite, TLEElement, Upload
from app.services.tle_sync_scheduler import (
    get_tle_freshness,
    sync_celestrak_active_satellites,
    start_tle_sync_scheduler,
    stop_tle_sync_scheduler,
)


def test_get_tle_freshness_empty(app):
    """When no uploads or TLEs exist, freshness reports no data."""
    with app.app_context():
        freshness = get_tle_freshness()
        assert freshness["has_data"] is False
        assert freshness["is_stale"] is True
        assert freshness["freshness_label"] == "No TLEs loaded"


def test_get_tle_freshness_with_data(app):
    """Freshness returns correct hours and freshness label when uploads exist."""
    with app.app_context():
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upload = Upload(
            filename="test_sync.tle",
            upload_time=now - timedelta(hours=3),
            total_records_in_file=10,
            source="celestrak_auto_sync",
        )
        db.session.add(upload)
        db.session.commit()

        freshness = get_tle_freshness()
        assert freshness["has_data"] is True
        assert freshness["is_stale"] is False
        assert "3h ago" in freshness["freshness_label"]


def test_api_tle_freshness_endpoint(client):
    """The /api/tle/freshness endpoint returns JSON with valid schema."""
    resp = client.get("/api/tle/freshness")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "has_data" in data
    assert "freshness_label" in data
    assert "is_stale" in data


@patch("app.routes.upload.fetch_tle_from_url")
def test_sync_celestrak_active_satellites(mock_fetch, app):
    """Sync fetches active TLEs, persists them, and updates timestamps."""
    sample_tle = (
        "ISS (ZARYA)\n"
        "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9001\n"
        "2 25544  51.6400 208.5000 0004500  70.0000 290.0000 15.49500000400001\n"
    )
    mock_fetch.return_value = (sample_tle, None, None)

    with app.app_context():
        res = sync_celestrak_active_satellites(force=True)
        assert res["success"] is True
        assert res["records_count"] == 1
        assert "ISS (ZARYA)" in res["message"] or res["summary"]["new_satellites"] == 1


def test_scheduler_lifecycle():
    """Verify start and stop scheduler do not crash or leak threads."""
    mock_app = MagicMock()
    mock_app.config = {"TESTING": True}
    start_tle_sync_scheduler(mock_app)
    stop_tle_sync_scheduler()
