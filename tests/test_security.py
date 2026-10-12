import pytest

from app.routes.auth import is_admin_email_allowed
from app.services.query_cache import (
    cache_user_verified_query,
    get_cached_query,
    validate_sql_for_cache,
)


def test_validate_sql_for_cache_rejects_mutation_sql():
    assert validate_sql_for_cache("SELECT norad_cat_id FROM satellites LIMIT 10")
    assert not validate_sql_for_cache("UPDATE satellites SET name = 'x'")
    assert not validate_sql_for_cache("SELECT 1; DROP TABLE satellites")
    assert not validate_sql_for_cache("DELETE FROM satellites")


def test_validate_sql_safety_blocks_stacked_and_mutation_queries():
    from app.routes.report import validate_sql_safety

    assert validate_sql_safety("SELECT norad_cat_id FROM satellites LIMIT 10")
    assert validate_sql_safety("SELECT s.norad_cat_id FROM satellites s JOIN tle_elements t ON s.id = t.satellite_id;")
    assert validate_sql_safety("WITH recent AS (SELECT id, norad_cat_id FROM satellites) SELECT norad_cat_id FROM recent")
    assert not validate_sql_safety("SELECT 1; DROP TABLE satellites;")
    assert not validate_sql_safety("SELECT norad_cat_id FROM satellites; SELECT 1")
    assert not validate_sql_safety("UPDATE satellites SET name = 'hacked'")
    assert not validate_sql_safety("DROP TABLE tle_elements")
    assert not validate_sql_safety("INSERT INTO satellites (name) VALUES ('bad')")
    assert not validate_sql_safety("ATTACH DATABASE 'x.db' AS x")


def test_cache_user_verified_query_allows_safe_sql(app):
    with app.app_context():
        entry = cache_user_verified_query(
            "Find Starlink satellites",
            "SELECT norad_cat_id FROM satellites WHERE name LIKE '%Starlink%' LIMIT 5",
            category="user_verified",
        )
        assert entry["verified"] is True
        cached = get_cached_query("Find Starlink satellites")
        assert cached is not None
        assert cached["sql"].startswith("SELECT")


def test_cache_user_verified_query_rejects_unsafe_sql(app):
    with app.app_context():
        with pytest.raises(ValueError, match="Only read-only SELECT SQL may be cached"):
            cache_user_verified_query("bad prompt", "DROP TABLE satellites")


def test_admin_allowlist_fails_closed(app):
    with app.test_request_context("/"):
        assert not is_admin_email_allowed("someone@example.com")


def test_cache_feedback_requires_admin_login(client):
    response = client.post(
        "/api/ai/cache-feedback",
        json={
            "prompt": "Find Starlink satellites",
            "sql": "SELECT norad_cat_id FROM satellites LIMIT 5",
            "feedback": "positive",
        },
    )
    assert response.status_code == 302
    assert "/auth/login" in response.headers.get("Location", "")


def test_public_routes_are_accessible(client):
    root = client.get("/", follow_redirects=False)
    assert root.status_code == 302
    assert root.headers.get("Location", "").endswith("/report")

    report = client.get("/report")
    assert report.status_code == 200
    assert "text/html" in report.headers.get("Content-Type", "")

    stats = client.get("/stats")
    assert stats.status_code == 200
    assert "text/html" in stats.headers.get("Content-Type", "")

    latest_tles = client.get("/api/satellites/latest-tles")
    assert latest_tles.status_code == 200
    assert latest_tles.is_json
    assert isinstance(latest_tles.get_json(), list)
