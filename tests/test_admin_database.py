from app import db
from app.models import SavedQuery, Satellite
from app.services.sql_console import validate_readonly_sql


def _login_admin(client):
    with client.session_transaction() as sess:
        sess["admin_user"] = {
            "email": "dev-admin@localhost",
            "name": "Dev Admin",
            "is_dev_bypass": True,
        }


def test_database_console_requires_login(client):
    response = client.get("/admin/database", follow_redirects=False)
    assert response.status_code == 302
    assert "/auth/login" in response.headers.get("Location", "")


def test_database_console_lists_tables(client):
    _login_admin(client)
    response = client.get("/admin/database")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Database explorer" in html
    assert "satellites" in html
    assert "sql-editor" in html
    assert "sql-row-limit" in html
    assert "Saved queries" in html


def test_readonly_sql_rejects_mutations():
    assert validate_readonly_sql("SELECT 1").upper().startswith("SELECT")
    try:
        validate_readonly_sql("DELETE FROM satellites")
        assert False, "should reject DELETE"
    except ValueError:
        pass
    try:
        validate_readonly_sql("SELECT 1; DROP TABLE satellites")
        assert False, "should reject stacked statements"
    except ValueError:
        pass


def test_run_query_respects_row_limit(client):
    _login_admin(client)
    run = client.post(
        "/admin/database/query",
        json={"sql": "SELECT name FROM satellites", "limit": 1},
    )
    assert run.status_code == 200
    payload = run.get_json()
    assert payload["ok"] is True
    assert payload["limit"] == 1
    assert payload["row_count"] <= 1


def test_run_and_save_sql_query_in_database(client, app):
    _login_admin(client)
    with app.app_context():
        db_count = Satellite.query.count()

    run = client.post(
        "/admin/database/query",
        json={"sql": "SELECT COUNT(*) AS n FROM satellites", "limit": 50},
    )
    assert run.status_code == 200
    payload = run.get_json()
    assert payload["ok"] is True
    assert payload["columns"] == ["n"]
    assert payload["rows"][0][0] == db_count

    blocked = client.post(
        "/admin/database/query",
        json={"sql": "DROP TABLE satellites"},
    )
    assert blocked.status_code == 400
    assert blocked.get_json()["ok"] is False

    saved = client.post(
        "/admin/database/saved",
        json={"name": "Count satellites", "sql": "SELECT COUNT(*) AS n FROM satellites", "row_limit": 25},
    )
    assert saved.status_code == 201
    entry = saved.get_json()["query"]
    assert entry["name"] == "Count satellites"
    assert entry["row_limit"] == 25

    with app.app_context():
        row = SavedQuery.query.filter_by(name="Count satellites").one()
        assert "COUNT(*)" in row.sql
        assert row.row_limit == 25

    listed = client.get("/admin/database/saved").get_json()
    assert any(item["id"] == entry["id"] for item in listed["queries"])

    page = client.get("/admin/database").get_data(as_text=True)
    assert "Count satellites" in page
    assert "Load" in page

    deleted = client.delete(f"/admin/database/saved/{entry['id']}")
    assert deleted.status_code == 200
    assert deleted.get_json()["ok"] is True
    with app.app_context():
        assert SavedQuery.query.get(entry["id"]) is None
