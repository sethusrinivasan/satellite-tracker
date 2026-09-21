"""
Datastore configuration — SQLite and PostgreSQL, stored outside the database
so first-launch setup and later admin switches do not depend on a live engine.
"""

from __future__ import annotations

import logging
import os
from copy import deepcopy
from typing import Any
from urllib.parse import quote_plus, unquote, urlparse

from sqlalchemy import create_engine, inspect, text

log = logging.getLogger(__name__)

SUPPORTED_ENGINES = ("sqlite", "postgresql")
PLACEHOLDER_URI = "sqlite:///:memory:"
_UNREADABLE_LOGGED: set[str] = set()


def _running_as_root() -> bool:
    geteuid = getattr(os, "geteuid", None)
    return callable(geteuid) and geteuid() == 0


def permission_denied_hint(path: str) -> str:
    directory = os.path.dirname(os.path.abspath(path)) or "."
    return (
        f"Cannot read {path}: permission denied. "
        "Docker likely created instance/ files as root with mode 600. "
        f'Fix: sudo chown -R "$(id -u):$(id -g)" "{directory}"'
    )


def align_path_owner_with_parent(path: str) -> None:
    """When running as root, match a host-mounted parent directory's owner."""
    if not path or not os.path.exists(path) or not _running_as_root():
        return
    chown = getattr(os, "chown", None)
    if not callable(chown):
        return
    parent = os.path.dirname(os.path.abspath(path)) or "."
    try:
        parent_stat = os.stat(parent)
        file_stat = os.stat(path)
        if (file_stat.st_uid, file_stat.st_gid) == (parent_stat.st_uid, parent_stat.st_gid):
            return
        chown(path, parent_stat.st_uid, parent_stat.st_gid)
        log.info(
            "[datastore] Adjusted owner of %s to %s:%s",
            path,
            parent_stat.st_uid,
            parent_stat.st_gid,
        )
    except OSError as exc:
        log.warning("[datastore] Could not adjust owner of %s: %s", path, exc)


def repair_host_volume_ownership(root: str) -> None:
    """Chown files under a bind-mounted instance/ dir to that directory's owner."""
    if not root or not os.path.isdir(root) or not _running_as_root():
        return
    try:
        os.stat(root)
    except OSError:
        return
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            align_path_owner_with_parent(os.path.join(dirpath, name))


def default_sqlite_path() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "instance", "satellites.db")


def resolve_sqlite_path(path: str | None) -> str:
    """Return a writable SQLite file path, remapping host paths that do not exist here."""
    default = default_sqlite_path()
    instance_dir = os.path.dirname(default)
    os.makedirs(instance_dir, exist_ok=True)
    if not path or path == ":memory:":
        return path or default
    if not os.path.isabs(path):
        return os.path.join(instance_dir, os.path.basename(path) or "satellites.db")
    path_abs = os.path.abspath(path)
    parent = os.path.dirname(path_abs)
    if parent == os.path.abspath(instance_dir) or os.path.isdir(parent):
        return path_abs
    remapped = os.path.join(instance_dir, os.path.basename(path_abs) or "satellites.db")
    log.info("[datastore] SQLite path %s is not available; using %s", path, remapped)
    return remapped


def default_postgres_settings() -> dict[str, Any]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432") or 5432),
        "user": os.environ.get("POSTGRES_USER", "sattrack"),
        "password": os.environ.get("POSTGRES_PASSWORD", "sattrack"),
        "database": os.environ.get("POSTGRES_DB", "sattrack"),
    }


def empty_config() -> dict[str, Any]:
    return {
        "engine": "sqlite",
        "configured": False,
        "sqlite": {"path": default_sqlite_path()},
        "postgresql": default_postgres_settings(),
    }


def config_path_for_app(app) -> str:
    return app.config.get(
        "DATASTORE_CONFIG_PATH",
        os.path.join(os.path.dirname(app.root_path), "instance", "datastore.json"),
    )


def load_datastore_config(path: str) -> dict[str, Any] | None:
    if not path or not os.path.exists(path):
        return None
    try:
        import json

        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None
        cfg = empty_config()
        cfg.update({k: v for k, v in data.items() if k in cfg or k == "configured"})
        if isinstance(data.get("sqlite"), dict):
            cfg["sqlite"].update(data["sqlite"])
        if isinstance(data.get("postgresql"), dict):
            cfg["postgresql"].update(data["postgresql"])
        engine = str(cfg.get("engine", "sqlite")).lower()
        if engine in ("postgres", "pgsql"):
            engine = "postgresql"
        cfg["engine"] = engine if engine in SUPPORTED_ENGINES else "sqlite"
        cfg["configured"] = bool(data.get("configured", True))
        return cfg
    except PermissionError:
        if path not in _UNREADABLE_LOGGED:
            _UNREADABLE_LOGGED.add(path)
            log.error("[datastore] %s", permission_denied_hint(path))
        return None
    except Exception as exc:
        log.error("[datastore] Failed to read %s: %s", path, exc)
        return None


def save_datastore_config(path: str, cfg: dict[str, Any]) -> None:
    import json

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    payload = deepcopy(cfg)
    payload["configured"] = True
    engine = str(payload.get("engine", "sqlite")).lower()
    if engine in ("postgres", "pgsql"):
        engine = "postgresql"
    payload["engine"] = engine
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    align_path_owner_with_parent(path)
    log.info("[datastore] Saved %s configuration to %s", payload["engine"], path)


def public_config(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Return a copy safe to send to templates (password redacted)."""
    data = deepcopy(cfg or empty_config())
    password = (data.get("postgresql") or {}).get("password") or ""
    data["postgresql"] = dict(data.get("postgresql") or {})
    data["postgresql"]["password"] = ""
    data["postgresql"]["password_set"] = bool(password)
    return data


def normalize_database_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url.split("://", 1)[0]:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def parse_database_url(url: str) -> dict[str, Any]:
    cfg = empty_config()
    url = normalize_database_url(url)
    if url.startswith("sqlite:"):
        rest = url.split("sqlite:", 1)[1]
        path = rest[3:] if rest.startswith("///") else rest.lstrip("/")
        cfg["engine"] = "sqlite"
        cfg["configured"] = True
        cfg["sqlite"]["path"] = path or default_sqlite_path()
        return cfg

    parsed = urlparse(url)
    cfg["engine"] = "postgresql"
    cfg["configured"] = True
    cfg["postgresql"] = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username or "sattrack"),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "/sattrack").lstrip("/") or "sattrack",
    }
    return cfg


def build_database_uri(cfg: dict[str, Any]) -> str:
    engine = str(cfg.get("engine", "sqlite")).lower()
    if engine in ("postgres", "pgsql"):
        engine = "postgresql"
    if engine != "postgresql":
        path = resolve_sqlite_path((cfg.get("sqlite") or {}).get("path"))
        if path == ":memory:":
            return "sqlite:///:memory:"
        return "sqlite:///" + path

    pg = cfg.get("postgresql") or {}
    user = quote_plus(str(pg.get("user") or "sattrack"))
    password = quote_plus(str(pg.get("password") or ""))
    host = pg.get("host") or "localhost"
    port = int(pg.get("port") or 5432)
    database = pg.get("database") or "sattrack"
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def config_from_form(form, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = deepcopy(existing) if existing else empty_config()
    engine = (form.get("engine") or cfg.get("engine") or "sqlite").strip().lower()
    if engine in ("postgres", "pgsql"):
        engine = "postgresql"
    if engine not in SUPPORTED_ENGINES:
        raise ValueError("Unsupported database engine")
    cfg["engine"] = engine
    sqlite_path = (form.get("sqlite_path") or "").strip()
    if sqlite_path:
        cfg["sqlite"]["path"] = sqlite_path
    elif not cfg.get("sqlite", {}).get("path"):
        cfg["sqlite"]["path"] = default_sqlite_path()

    pg = cfg.setdefault("postgresql", default_postgres_settings())
    if form.get("pg_host"):
        pg["host"] = form.get("pg_host").strip()
    if form.get("pg_port"):
        pg["port"] = int(form.get("pg_port"))
    if form.get("pg_user"):
        pg["user"] = form.get("pg_user").strip()
    if form.get("pg_database"):
        pg["database"] = form.get("pg_database").strip()
    password = form.get("pg_password")
    if password not in (None, ""):
        pg["password"] = password
    cfg["configured"] = True
    return cfg


def test_connection(uri: str) -> tuple[bool, str]:
    if not uri:
        return False, "Database URI is empty"
    engine = None
    try:
        engine = create_engine(uri, pool_pre_ping=True, pool_size=1, max_overflow=0)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        dialect = engine.dialect.name
        return True, f"Connected successfully ({dialect})"
    except Exception as exc:
        return False, str(exc)
    finally:
        if engine is not None:
            engine.dispose()


def dispose_engines(app) -> None:
    from app import db

    db.session.remove()
    engines = getattr(db, "_app_engines", None)
    if isinstance(engines, dict):
        app_engines = engines.pop(app, {})
        for eng in list(app_engines.values()):
            try:
                eng.dispose()
            except Exception:
                pass
        return
    try:
        db.engine.dispose()
    except Exception:
        pass


def rebind_database(app, uri: str, engine_name: str | None = None) -> None:
    dispose_engines(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    if engine_name:
        app.config["DATASTORE_ENGINE"] = engine_name
    app.config["DATASTORE_CONFIGURED"] = True
    app.config["SCHEMA_READY"] = False


def ensure_database_schema(app) -> None:
    """Create ORM tables if this database file/server has none yet."""
    from app import db
    from app import models as _models  # noqa: F401 — register metadata

    if not app.config.get("DATASTORE_CONFIGURED"):
        return
    db.create_all()
    try:
        from app.services.sql_console import ensure_saved_query_columns

        ensure_saved_query_columns(db)
    except Exception:
        pass
    app.config["SCHEMA_READY"] = True
    app.config.pop("DATASTORE_ERROR", None)
    cfg_path = app.config.get("DATASTORE_CONFIG_PATH")
    if cfg_path:
        repair_host_volume_ownership(os.path.dirname(cfg_path) or ".")


def _model_to_dict(obj) -> dict[str, Any]:
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}


def snapshot_all_rows() -> dict[str, list[dict[str, Any]]]:
    from app.models import Satellite, SavedQuery, SystemSetting, TLEElement, Upload

    return {
        "uploads": [_model_to_dict(row) for row in Upload.query.order_by(Upload.id).all()],
        "satellites": [_model_to_dict(row) for row in Satellite.query.order_by(Satellite.id).all()],
        "tle_elements": [_model_to_dict(row) for row in TLEElement.query.order_by(TLEElement.id).all()],
        "system_settings": [_model_to_dict(row) for row in SystemSetting.query.all()],
        "saved_queries": [_model_to_dict(row) for row in SavedQuery.query.order_by(SavedQuery.id).all()],
    }


def restore_snapshot(snapshot: dict[str, list[dict[str, Any]]]) -> None:
    from app import db
    from app.models import Satellite, SavedQuery, SystemSetting, TLEElement, Upload

    mapping = (
        ("uploads", Upload),
        ("satellites", Satellite),
        ("tle_elements", TLEElement),
        ("system_settings", SystemSetting),
        ("saved_queries", SavedQuery),
    )
    for key, model in mapping:
        for row in snapshot.get(key, []):
            db.session.merge(model(**row))
    db.session.commit()
    _reset_integer_sequences()


def _reset_integer_sequences() -> None:
    from app import db

    bind = db.session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    inspector = inspect(bind)
    for table_name, column in (("uploads", "id"), ("satellites", "id"), ("tle_elements", "id"), ("saved_queries", "id")):
        if table_name not in inspector.get_table_names():
            continue
        db.session.execute(
            text(
                "SELECT setval(pg_get_serial_sequence(:table_name, :column_name), "
                "COALESCE((SELECT MAX(id) FROM " + table_name + "), 1), true)"
            ),
            {"table_name": table_name, "column_name": column},
        )
    db.session.commit()


def apply_and_initialize(app, cfg: dict[str, Any], migrate_from_uri: str | None = None) -> dict[str, Any]:
    """Write config, optionally copy data, create schema, and rebind the live app."""
    from app import db

    uri = build_database_uri(cfg)
    ok, message = test_connection(uri)
    if not ok:
        raise RuntimeError(f"Could not connect to the new database: {message}")

    snapshot = None
    if migrate_from_uri and migrate_from_uri != uri and app.config.get("DATASTORE_CONFIGURED"):
        try:
            snapshot = snapshot_all_rows()
            log.info(
                "[datastore] Captured %d satellites / %d TLE rows for migration",
                len(snapshot["satellites"]),
                len(snapshot["tle_elements"]),
            )
        except Exception as exc:
            log.warning("[datastore] Could not snapshot current database: %s", exc)
            snapshot = None

    path = config_path_for_app(app)
    save_datastore_config(path, cfg)
    rebind_database(app, uri, cfg.get("engine"))
    app.config["DATASTORE_MTIME"] = os.path.getmtime(path) if os.path.exists(path) else None

    db.create_all()
    copied = {"uploads": 0, "satellites": 0, "tle_elements": 0, "system_settings": 0}
    if snapshot:
        restore_snapshot(snapshot)
        copied = {key: len(value) for key, value in snapshot.items()}
    return {"uri_engine": cfg.get("engine"), "copied": copied}


def bootstrap_from_env() -> dict[str, Any] | None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return parse_database_url(url)
    engine = (os.environ.get("DB_ENGINE") or os.environ.get("DATASTORE_ENGINE") or "").strip().lower()
    if engine in ("postgres", "pgsql"):
        engine = "postgresql"
    if engine in SUPPORTED_ENGINES:
        cfg = empty_config()
        cfg["engine"] = engine
        cfg["configured"] = True
        return cfg
    return None
