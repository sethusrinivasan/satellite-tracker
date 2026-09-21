import os

import pytest

from app import create_app, db
from app.services.datastore import (
    build_database_uri,
    config_from_form,
    empty_config,
    parse_database_url,
    public_config,
    save_datastore_config,
    test_connection as probe_connection,
)
from tests.conftest import TestConfig


class UnconfiguredConfig(TestConfig):
    DATASTORE_CONFIGURED = False
    DATASTORE_ENGINE = None
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def unconfigured_app(tmp_path):
    class Cfg(UnconfiguredConfig):
        DATASTORE_CONFIG_PATH = str(tmp_path / "datastore.json")
        UPLOAD_FOLDER = str(tmp_path / "uploads")

    app = create_app(config_object=Cfg)
    yield app


@pytest.fixture
def unconfigured_client(unconfigured_app):
    with unconfigured_app.test_client() as client:
        yield client


def test_build_sqlite_and_postgres_uris(tmp_path):
    sqlite_cfg = empty_config()
    sqlite_cfg["engine"] = "sqlite"
    sqlite_cfg["sqlite"]["path"] = str(tmp_path / "sats.db")
    uri = build_database_uri(sqlite_cfg)
    assert uri.startswith("sqlite:///")
    assert uri.endswith("sats.db")

    pg_cfg = empty_config()
    pg_cfg["engine"] = "postgresql"
    pg_cfg["postgresql"] = {
        "host": "postgres",
        "port": 5432,
        "user": "sattrack",
        "password": "s@cret/word",
        "database": "sattrack",
    }
    pg_uri = build_database_uri(pg_cfg)
    assert pg_uri.startswith("postgresql+psycopg://")
    assert "sattrack:" in pg_uri
    assert "@postgres:5432/sattrack" in pg_uri


def test_parse_database_url_variants():
    sqlite = parse_database_url("sqlite:////app/instance/satellites.db")
    assert sqlite["engine"] == "sqlite"
    assert sqlite["sqlite"]["path"].endswith("satellites.db")

    postgres = parse_database_url("postgres://user:pass@db:5433/orbit")
    assert postgres["engine"] == "postgresql"
    assert postgres["postgresql"]["host"] == "db"
    assert postgres["postgresql"]["port"] == 5433
    assert postgres["postgresql"]["database"] == "orbit"
    assert postgres["postgresql"]["user"] == "user"
    assert postgres["postgresql"]["password"] == "pass"


def test_public_config_redacts_password():
    cfg = empty_config()
    cfg["postgresql"]["password"] = "super-secret"
    published = public_config(cfg)
    assert published["postgresql"]["password"] == ""
    assert published["postgresql"]["password_set"] is True


def test_unconfigured_app_redirects_to_setup(unconfigured_client):
    response = unconfigured_client.get("/report", follow_redirects=False)
    assert response.status_code == 302
    assert "/setup" in response.headers.get("Location", "")


def test_health_allows_unconfigured_app(unconfigured_client):
    response = unconfigured_client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["datastore_configured"] is False


def test_first_launch_sqlite_setup(unconfigured_app, tmp_path):
    db_path = tmp_path / "satellites.db"
    with unconfigured_app.test_client() as client:
        page = client.get("/setup")
        assert page.status_code == 200
        assert b"Choose a datastore" in page.data

        test_res = client.post(
            "/setup/test",
            json={"engine": "sqlite", "sqlite_path": str(db_path)},
        )
        assert test_res.status_code == 200
        assert test_res.get_json()["ok"] is True

        save_res = client.post(
            "/setup",
            data={"engine": "sqlite", "sqlite_path": str(db_path)},
            follow_redirects=False,
        )
        assert save_res.status_code == 302
        assert save_res.headers.get("Location", "").endswith("/report")

    assert unconfigured_app.config["DATASTORE_CONFIGURED"] is True
    assert unconfigured_app.config["DATASTORE_ENGINE"] == "sqlite"
    assert os.path.exists(db_path)
    assert os.path.exists(unconfigured_app.config["DATASTORE_CONFIG_PATH"])

    with unconfigured_app.test_client() as client:
        report = client.get("/report", follow_redirects=False)
        assert report.status_code == 200


def test_admin_datastore_requires_login():
    app = create_app(config_object=TestConfig)
    with app.test_client() as client:
        response = client.post("/admin/datastore", data={"engine": "sqlite"})
        assert response.status_code == 302
        assert "/auth/login" in response.headers.get("Location", "")


def test_form_keeps_existing_postgres_password():
    existing = empty_config()
    existing["engine"] = "postgresql"
    existing["postgresql"]["password"] = "keep-me"
    cfg = config_from_form(
        {"engine": "postgresql", "pg_host": "postgres", "pg_password": ""},
        existing,
    )
    assert cfg["postgresql"]["password"] == "keep-me"


def test_sqlite_test_connection_succeeds(tmp_path):
    cfg = empty_config()
    cfg["sqlite"]["path"] = str(tmp_path / "probe.db")
    ok, message = probe_connection(build_database_uri(cfg))
    assert ok, message


def test_save_datastore_config_roundtrip(tmp_path):
    path = tmp_path / "datastore.json"
    cfg = empty_config()
    cfg["engine"] = "sqlite"
    cfg["sqlite"]["path"] = str(tmp_path / "x.db")
    save_datastore_config(str(path), cfg)
    from app.services.datastore import load_datastore_config

    loaded = load_datastore_config(str(path))
    assert loaded["configured"] is True
    assert loaded["engine"] == "sqlite"


def test_unreadable_datastore_json_is_not_treated_as_missing(tmp_path):
    path = tmp_path / "datastore.json"
    path.write_text('{"engine":"sqlite","configured":true,"sqlite":{"path":":memory:"}}\n', encoding="utf-8")
    path.chmod(0o000)

    class Cfg(UnconfiguredConfig):
        DATASTORE_CONFIG_PATH = str(path)
        UPLOAD_FOLDER = str(tmp_path / "uploads")

    try:
        from app.services.datastore import _UNREADABLE_LOGGED, load_datastore_config

        _UNREADABLE_LOGGED.discard(str(path))
        loaded = load_datastore_config(str(path))
        assert loaded is None
        app = create_app(config_object=Cfg)
        assert app.config.get("DATASTORE_UNREADABLE") is True
        assert app.config.get("DATASTORE_CONFIGURED") is False
        assert "permission denied" in (app.config.get("DATASTORE_ERROR") or "").lower()
        with app.test_client() as client:
            setup = client.get("/setup")
            assert setup.status_code == 200
            assert b"permission denied" in setup.data.lower()
    finally:
        path.chmod(0o600)


def test_dev_bypass_disabled_in_production_docker(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
    app = create_app(config_object=TestConfig)
    with app.test_client() as client:
        response = client.get("/auth/dev-bypass", follow_redirects=False)
        assert response.status_code == 403
