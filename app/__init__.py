import sys
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

log = logging.getLogger(__name__)
db = SQLAlchemy()


def create_app(config_object="config.Config"):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_object)

    # Ensure upload folder exists
    os.makedirs(app.config.get("UPLOAD_FOLDER", "instance/uploads"), exist_ok=True)

    db.init_app(app)

    # ── OAuth (must happen before blueprints that use it) ─────────────────────
    from app.routes.auth import auth_bp, init_oauth
    init_oauth(app)

    with app.app_context():
        from app.routes.upload import upload_bp
        from app.routes.report import report_bp
        from app.routes.admin import admin_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(upload_bp)
        app.register_blueprint(report_bp)
        app.register_blueprint(admin_bp)

        db.create_all()

        # ── Auto-seed from Kaggle TLE file on very first run ──────────────────
        _seed_kaggle_data_if_needed(app)

    @app.context_processor
    def inject_environment_info():
        is_docker = os.path.exists('/.dockerenv') or os.getenv('RUNNING_IN_DOCKER') == 'true' or os.getenv('CONTAINER_ENV') == 'docker'
        is_dev = app.debug or os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG') == 'true'
        return {
            'is_docker': is_docker,
            'is_dev': is_dev,
            'runtime_env_name': 'Docker Container' if is_docker else ('Local Virtualenv' if is_dev else 'Production Host')
        }

    return app


def _seed_kaggle_data_if_needed(app):
    """Ingest kaggle_tle_data.txt into the DB exactly once, on first startup."""
    from app.models import SystemSetting
    from app.services.tle_parser import parse_tle_file
    from app.services.db_service import upsert_tle_records

    SEED_KEY = "kaggle_seed_imported"
    already_seeded = SystemSetting.query.get(SEED_KEY)
    if already_seeded:
        return

    seed_path_data = os.path.join(os.path.dirname(app.root_path), "data", "kaggle_tle_data.txt")
    seed_path_root = os.path.join(os.path.dirname(app.root_path), "kaggle_tle_data.txt")
    seed_path = seed_path_data if os.path.exists(seed_path_data) else seed_path_root
    if not os.path.exists(seed_path):
        log.warning("[seed] Seed data file not found at %s — skipping auto-seed.", seed_path_data)
        return

    log.info("[seed] First-time startup: importing Kaggle TLE data from %s …", seed_path)
    with open(seed_path, "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()

    parsed = parse_tle_file(content)
    if parsed:
        summary = upsert_tle_records(
            parsed,
            filename="kaggle_tle_data.txt",
            source="seed",
            is_seed=True,
            label="Kaggle Starlink TLE Dataset — April 2025",
        )
        log.info(
            "[seed] Done: %d new satellites, %d TLE elements, %d duplicates skipped.",
            summary["new_satellites"],
            summary["new_elements"],
            summary["duplicate_epochs"],
        )
    else:
        log.warning("[seed] No valid TLE records found in kaggle_tle_data.txt.")

    # Mark as seeded regardless so we don't retry on every restart
    db.session.add(SystemSetting(key=SEED_KEY, value="1"))
    db.session.commit()
