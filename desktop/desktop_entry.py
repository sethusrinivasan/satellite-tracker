#!/usr/bin/env python3
"""
Desktop entrypoint for Satellite TLE Tracker (Tauri / Standalone Desktop).
Bootstraps the Flask application with Waitress WSGI on a localhost port,
redirects storage/database/models to OS AppData directory,
and signals readiness to Tauri via stdout.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socket
import sys
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [DESKTOP] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("desktop_entry")


def get_default_desktop_data_dir() -> str:
    """Return standard platform-specific AppData directory for desktop installation."""
    app_name = "satellite-tracker"
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
        return os.path.join(base, app_name)
    elif sys.platform == "darwin":
        return os.path.expanduser(f"~/Library/Application Support/{app_name}")
    else:
        # Linux / Unix
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        return os.path.join(base, app_name)


def get_default_desktop_model_dir(data_dir: str) -> str:
    """Return standard platform-specific cache/models directory."""
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Caches/satellite-tracker/models")
    elif sys.platform.startswith("win"):
        local_app = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
        return os.path.join(local_app, "satellite-tracker", "models")
    else:
        cache_base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
        return os.path.join(cache_base, "satellite-tracker", "models")


def find_free_port() -> int:
    """Find a random available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return s.getsockname()[1]


def ensure_desktop_environment(data_dir: str, model_dir: str) -> None:
    """Set up desktop paths, secret key, and default SQLite datastore config."""
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(model_dir, exist_ok=True)
    uploads_dir = os.path.join(data_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    os.environ["SATELLITE_DESKTOP"] = "1"
    os.environ["SATELLITE_RUNTIME_DIR"] = data_dir
    os.environ["SATELLITE_MODEL_DIR"] = model_dir
    os.environ.setdefault("FLASK_ENV", "production")

    # Persistent desktop SECRET_KEY
    secret_path = os.path.join(data_dir, "secret.key")
    if not os.path.exists(secret_path):
        import secrets

        key = secrets.token_hex(32)
        try:
            with open(secret_path, "w", encoding="utf-8") as f:
                f.write(key)
        except OSError:
            pass
    else:
        try:
            with open(secret_path, "r", encoding="utf-8") as f:
                key = f.read().strip()
        except OSError:
            key = "desktop-local-secret-key"
    os.environ.setdefault("SECRET_KEY", key)

    # Initialize default SQLite datastore.json if not present
    datastore_path = os.path.join(data_dir, "datastore.json")
    if not os.path.exists(datastore_path):
        sqlite_db_path = os.path.join(data_dir, "satellites.db")
        config_data: dict[str, Any] = {
            "engine": "sqlite",
            "configured": True,
            "sqlite": {"path": sqlite_db_path},
            "postgresql": {
                "host": "localhost",
                "port": 5432,
                "user": "sattrack",
                "password": "",
                "database": "sattrack",
            },
        }
        try:
            with open(datastore_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
                f.write("\n")
            logger.info("Initialized default desktop SQLite datastore at %s", sqlite_db_path)
        except OSError as exc:
            logger.warning("Could not write initial datastore.json: %s", exc)


def handle_shutdown(signum, frame):
    logger.info("Received termination signal %s. Shutting down desktop backend cleanly.", signum)
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    parser = argparse.ArgumentParser(
        description="Satellite Tracker Desktop - Real-time 2D/3D satellite tracking, orbital propagation, and offline AI discovery"
    )
    parser.add_argument("--port", type=int, default=0, help="Port to bind (0 for automatic)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--data-dir", type=str, default="", help="Custom application data directory")
    parser.add_argument("--model-dir", type=str, default="", help="Custom models directory")
    parser.add_argument("--dev", action="store_true", help="Run with Flask development server")
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir or get_default_desktop_data_dir())
    model_dir = os.path.abspath(args.model_dir or get_default_desktop_model_dir(data_dir))

    ensure_desktop_environment(data_dir, model_dir)

    port = args.port

    # Import Flask app after desktop environment is fully configured
    from config import Config
    from app import create_app

    app = create_app(config_object=Config)

    if args.dev:
        if port == 0:
            port = find_free_port()
        sys.stdout.write(f"READY:{port}\n")
        sys.stdout.flush()
        logger.info(
            "Satellite Tracker desktop backend listening on http://%s:%d (data: %s)",
            args.host,
            port,
            data_dir,
        )
        debug_mode = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes", "on")
        app.run(host=args.host, port=port, debug=debug_mode, use_reloader=False)
    else:
        try:
            from waitress.server import create_server

            server = create_server(app, host=args.host, port=port, threads=6)
            effective_port = int(server.effective_port)

            sys.stdout.write(f"READY:{effective_port}\n")
            sys.stdout.flush()
            logger.info(
                "Satellite Tracker desktop backend listening on http://%s:%d (data: %s)",
                args.host,
                effective_port,
                data_dir,
            )
            server.run()

        except ImportError:
            if port == 0:
                port = find_free_port()
            sys.stdout.write(f"READY:{port}\n")
            sys.stdout.flush()
            logger.warning("Waitress not found, falling back to Flask development server")
            app.run(host=args.host, port=port, debug=False)


if __name__ == "__main__":
    main()
