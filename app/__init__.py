import sys
import os
import logging
from flask import Flask, jsonify, redirect, request, url_for
from flask_sqlalchemy import SQLAlchemy

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

log = logging.getLogger(__name__)
db = SQLAlchemy()

_SETUP_ENDPOINTS = {
    "setup.index",
    "setup.test",
    "static",
}


def _normalize_posthog_host(raw: str | None) -> str:
    host = (raw or "https://us.i.posthog.com").strip()
    if not host:
        host = "https://us.i.posthog.com"
    if not host.startswith("https://") and not host.startswith("http://"):
        host = "https://" + host.lstrip("/")
    return host.rstrip("/")


def create_app(config_object="config.Config"):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)

    os.makedirs(app.config.get("UPLOAD_FOLDER", "instance/uploads"), exist_ok=True)
    os.makedirs(os.path.dirname(app.config.get("DATASTORE_CONFIG_PATH") or "instance/datastore.json") or "instance", exist_ok=True)

    from app.services.datastore import repair_host_volume_ownership

    repair_host_volume_ownership(
        os.path.dirname(app.config.get("DATASTORE_CONFIG_PATH") or "instance/datastore.json") or "instance"
    )

    _resolve_datastore(app)

    db.init_app(app)

    from app.routes.auth import auth_bp, init_oauth
    init_oauth(app)

    with app.app_context():
        from app.routes.upload import upload_bp
        from app.routes.report import report_bp
        from app.routes.admin import admin_bp
        from app.routes.setup import setup_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(upload_bp)
        app.register_blueprint(report_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(setup_bp)

        if app.config.get("DATASTORE_CONFIGURED"):
            try:
                from app.services.datastore import ensure_database_schema

                ensure_database_schema(app)
                if not app.config.get("TESTING"):
                    _seed_kaggle_data_if_needed(app)
            except Exception as exc:
                log.error("[datastore] Database is configured but unreachable: %s", exc)
                app.config["DATASTORE_ERROR"] = str(exc)

    @app.before_request
    def _reload_or_require_datastore():
        if request.endpoint in _SETUP_ENDPOINTS or (request.path or "").startswith("/static"):
            return None
        if request.path in ("/health", "/favicon.ico"):
            return None
        if not app.config.get("TESTING"):
            _maybe_reload_datastore(app)
        if not app.config.get("DATASTORE_CONFIGURED"):
            return redirect(url_for("setup.index"))
        if not app.config.get("SCHEMA_READY"):
            try:
                from app.services.datastore import ensure_database_schema

                ensure_database_schema(app)
            except Exception as exc:
                log.error("[datastore] Failed to create schema: %s", exc)
                app.config["DATASTORE_ERROR"] = str(exc)
                return None
        if not app.config.get("TESTING") and not app.config.get("SEED_APPLIED"):
            _seed_kaggle_data_if_needed(app)
        return None

    @app.get("/health")
    def health():
        payload = {
            "status": "ok",
            "datastore_configured": bool(app.config.get("DATASTORE_CONFIGURED")),
            "engine": app.config.get("DATASTORE_ENGINE") or "unconfigured",
        }
        if app.config.get("DATASTORE_ERROR"):
            payload["status"] = "degraded"
            payload["error"] = app.config["DATASTORE_ERROR"]
        return jsonify(payload)

    @app.context_processor
    def inject_environment_info():
        is_docker = os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER") == "true" or os.getenv("CONTAINER_ENV") == "docker"
        is_dev = app.debug or os.getenv("FLASK_ENV") == "development" or os.getenv("DEBUG") == "true"
        return {
            "is_docker": is_docker,
            "is_dev": is_dev,
            "runtime_env_name": "Docker Container" if is_docker else ("Local Virtualenv" if is_dev else "Production Host"),
            "datastore_engine": app.config.get("DATASTORE_ENGINE") or "unconfigured",
            "datastore_configured": bool(app.config.get("DATASTORE_CONFIGURED")),
            "datastore_error": app.config.get("DATASTORE_ERROR"),
            "carto_api_key": app.config.get("CARTO_API_KEY") or "",
            "posthog_enabled": bool(app.config.get("POSTHOG_PROJECT_API_KEY")) and not app.config.get("TESTING"),
            "posthog_key": app.config.get("POSTHOG_PROJECT_API_KEY") or "",
            "posthog_host": _normalize_posthog_host(app.config.get("POSTHOG_HOST")),
            "posthog_session_replay": bool(app.config.get("POSTHOG_SESSION_REPLAY")),
        }

    return app


def _resolve_datastore(app):
    """Bind SQLALCHEMY_DATABASE_URI from file, env, or leave unconfigured."""
    from app.services.datastore import (
        PLACEHOLDER_URI,
        bootstrap_from_env,
        build_database_uri,
        config_path_for_app,
        load_datastore_config,
        permission_denied_hint,
        repair_host_volume_ownership,
        save_datastore_config,
    )

    if app.config.get("DATASTORE_CONFIGURED"):
        app.config.setdefault("DATASTORE_ENGINE", "sqlite")
        if app.config.get("SQLALCHEMY_DATABASE_URI") in (None, "", PLACEHOLDER_URI):
            app.config["SQLALCHEMY_DATABASE_URI"] = PLACEHOLDER_URI
        return

    path = config_path_for_app(app)
    app.config["DATASTORE_CONFIG_PATH"] = path
    repair_host_volume_ownership(os.path.dirname(path) or ".")
    cfg = load_datastore_config(path)
    if cfg is None and os.path.isfile(path) and not os.access(path, os.R_OK):
        app.config["DATASTORE_ERROR"] = permission_denied_hint(path)
        app.config["DATASTORE_UNREADABLE"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = PLACEHOLDER_URI
        app.config["DATASTORE_CONFIGURED"] = False
        app.config["DATASTORE_ENGINE"] = None
        return
    if cfg and cfg.get("configured"):
        app.config["SQLALCHEMY_DATABASE_URI"] = build_database_uri(cfg)
        app.config["DATASTORE_CONFIGURED"] = True
        app.config["DATASTORE_ENGINE"] = cfg.get("engine", "sqlite")
        if os.path.exists(path):
            app.config["DATASTORE_MTIME"] = os.path.getmtime(path)
        log.info("[datastore] Using %s from %s", app.config["DATASTORE_ENGINE"], path)
        return

    if not app.config.get("TESTING"):
        env_cfg = bootstrap_from_env()
        if env_cfg:
            save_datastore_config(path, env_cfg)
            app.config["SQLALCHEMY_DATABASE_URI"] = build_database_uri(env_cfg)
            app.config["DATASTORE_CONFIGURED"] = True
            app.config["DATASTORE_ENGINE"] = env_cfg.get("engine", "sqlite")
            if os.path.exists(path):
                app.config["DATASTORE_MTIME"] = os.path.getmtime(path)
            log.info("[datastore] Bootstrapped %s from environment", app.config["DATASTORE_ENGINE"])
            return

    app.config["SQLALCHEMY_DATABASE_URI"] = PLACEHOLDER_URI
    app.config["DATASTORE_CONFIGURED"] = False
    app.config["DATASTORE_ENGINE"] = None
    log.info("[datastore] Unconfigured — first-launch setup is required")


def _maybe_reload_datastore(app):
    """Pick up admin datastore.json changes in other gunicorn workers."""
    from app.services.datastore import build_database_uri, load_datastore_config, rebind_database

    path = app.config.get("DATASTORE_CONFIG_PATH")
    if not path or not os.path.exists(path):
        return
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return
    if app.config.get("DATASTORE_MTIME") == mtime:
        return
    cfg = load_datastore_config(path)
    if not cfg or not cfg.get("configured"):
        return
    uri = build_database_uri(cfg)
    if uri != app.config.get("SQLALCHEMY_DATABASE_URI"):
        rebind_database(app, uri, cfg.get("engine"))
        log.info("[datastore] Reloaded %s configuration from %s", cfg.get("engine"), path)
    app.config["DATASTORE_MTIME"] = mtime
    app.config["DATASTORE_CONFIGURED"] = True
    app.config["DATASTORE_ENGINE"] = cfg.get("engine")
    try:
        from app.services.datastore import ensure_database_schema

        ensure_database_schema(app)
    except Exception as exc:
        log.error("[datastore] Reloaded database has no usable schema: %s", exc)
        app.config["DATASTORE_ERROR"] = str(exc)


def _seed_kaggle_data_if_needed(app):
    """Ingest Kaggle TLE data, or bundled demo TLEs, exactly once on first startup."""
    from app.models import SystemSetting
    from app.services.tle_parser import parse_tle_file
    from app.services.db_service import upsert_tle_records
    from app.services.demo_tle import demo_tle_text

    if not app.config.get("DATASTORE_CONFIGURED"):
        return
    if app.config.get("SEED_APPLIED"):
        return

    SEED_KEY = "kaggle_seed_imported"
    try:
        already_seeded = SystemSetting.query.get(SEED_KEY)
    except Exception as exc:
        log.warning("[seed] Cannot read system_settings yet: %s", exc)
        return
    if already_seeded:
        app.config["SEED_APPLIED"] = True
        return

    seed_path_data = os.path.join(os.path.dirname(app.root_path), "data", "kaggle_tle_data.txt")
    seed_path_root = os.path.join(os.path.dirname(app.root_path), "kaggle_tle_data.txt")
    seed_path = seed_path_data if os.path.exists(seed_path_data) else seed_path_root

    if os.path.exists(seed_path):
        log.info("[seed] First-time startup: importing Kaggle TLE data from %s …", seed_path)
        with open(seed_path, "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        filename = "kaggle_tle_data.txt"
        source = "seed"
        label = "Kaggle Starlink TLE Dataset — April 2025"
    else:
        log.warning(
            "[seed] Seed data file not found at %s — loading bundled demo TLE sample.",
            seed_path_data,
        )
        content = demo_tle_text()
        filename = "demo_tle_sample.txt"
        source = "demo"
        label = "Demo sample TLE data (bundled)"

    parsed = parse_tle_file(content)
    if parsed:
        summary = upsert_tle_records(
            parsed,
            filename=filename,
            source=source,
            is_seed=True,
            label=label,
        )
        log.info(
            "[seed] Done (%s): %d new satellites, %d TLE elements, %d duplicates skipped.",
            source,
            summary["new_satellites"],
            summary["new_elements"],
            summary["duplicate_epochs"],
        )
    else:
        log.warning("[seed] No valid TLE records found in %s.", filename)

    db.session.add(SystemSetting(key=SEED_KEY, value=source))
    db.session.commit()
    app.config["SEED_APPLIED"] = True
