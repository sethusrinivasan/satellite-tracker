"""
Unit and integration tests for Tauri standalone desktop application mode.
Verifies OS AppData path resolution, environment bootstrapping, SQLite datastore
initialization, local authentication bypass, and GitHub Actions release workflow syntax.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from app import create_app
from app.routes.auth import admin_required, is_admin_email_allowed, is_local_dev
from config import Config
from desktop_entry import (
    ensure_desktop_environment,
    find_free_port,
    get_default_desktop_data_dir,
    get_default_desktop_model_dir,
)


def test_find_free_port():
    """Verify that find_free_port returns a valid positive integer port."""
    port = find_free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535


def test_platform_data_dir_resolution():
    """Verify platform-specific AppData directory generation."""
    with patch("sys.platform", "linux"):
        data_dir = get_default_desktop_data_dir()
        assert "satellite-tracker" in data_dir

    with patch("sys.platform", "darwin"):
        data_dir = get_default_desktop_data_dir()
        assert "Library/Application Support/satellite-tracker" in data_dir

    with patch("sys.platform", "win32"):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
            data_dir = get_default_desktop_data_dir()
            assert "satellite-tracker" in data_dir


def test_platform_model_dir_resolution():
    """Verify platform-specific models/cache directory generation."""
    with patch("sys.platform", "linux"):
        model_dir = get_default_desktop_model_dir("/tmp/dummy")
        assert "satellite-tracker" in model_dir
        assert "models" in model_dir

    with patch("sys.platform", "darwin"):
        model_dir = get_default_desktop_model_dir("/tmp/dummy")
        assert "Library/Caches/satellite-tracker/models" in model_dir

    with patch("sys.platform", "win32"):
        with patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\Test\\AppData\\Local"}):
            model_dir = get_default_desktop_model_dir("/tmp/dummy")
            assert "satellite-tracker" in model_dir
            assert "models" in model_dir


def test_ensure_desktop_environment_initialization():
    """Verify desktop environment setup generates keys, directories, and SQLite datastore.json."""
    temp_dir = tempfile.mkdtemp(prefix="sattrack_desktop_test_")
    temp_model_dir = os.path.join(temp_dir, "models")

    with patch.dict(os.environ, {}, clear=False):
        try:
            ensure_desktop_environment(temp_dir, temp_model_dir)

            assert os.environ.get("SATELLITE_DESKTOP") == "1"
            assert os.environ.get("SATELLITE_RUNTIME_DIR") == temp_dir
            assert os.environ.get("SATELLITE_MODEL_DIR") == temp_model_dir

            secret_file = os.path.join(temp_dir, "secret.key")
            assert os.path.exists(secret_file)
            with open(secret_file, "r", encoding="utf-8") as f:
                secret = f.read().strip()
            assert len(secret) == 64

            datastore_file = os.path.join(temp_dir, "datastore.json")
            assert os.path.exists(datastore_file)
            with open(datastore_file, "r", encoding="utf-8") as f:
                datastore_cfg = json.load(f)
            assert datastore_cfg["engine"] == "sqlite"
            assert datastore_cfg["configured"] is True
            assert "satellites.db" in datastore_cfg["sqlite"]["path"]
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_desktop_auth_bypass(client):
    """Verify that SATELLITE_DESKTOP mode enables seamless local desktop admin access."""
    with patch.dict(os.environ, {"SATELLITE_DESKTOP": "1"}):
        assert is_local_dev() is True
        assert is_admin_email_allowed("desktop-user@localhost") is True

        response = client.get("/admin/")
        assert response.status_code in (200, 302)


def test_github_actions_workflow_syntax():
    """Verify that .github/workflows/desktop-release.yml exists and contains expected structure."""
    workflow_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        ".github",
        "workflows",
        "desktop-release.yml",
    )
    assert os.path.exists(workflow_path)

    with open(workflow_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "build-desktop:" in content
    assert "publish-release:" in content
    assert "linux-x86_64" in content
    assert "windows-x64" in content
    assert "macos-arm64" in content
    assert "macos-x64" in content
    assert "softprops/action-gh-release" in content
    assert "tauri build" in content


def test_desktop_app_descriptions():
    """Verify that tauri.conf.json and package.json have consistent, descriptive short text."""
    root_dir = os.path.dirname(os.path.dirname(__file__))

    tauri_conf_path = os.path.join(root_dir, "desktop", "src-tauri", "tauri.conf.json")
    if not os.path.exists(tauri_conf_path):
        tauri_conf_path = os.path.join(root_dir, "src-tauri", "tauri.conf.json")
    with open(tauri_conf_path, "r", encoding="utf-8") as f:
        tauri_conf = json.load(f)

    short_desc = tauri_conf.get("bundle", {}).get("shortDescription", "")
    assert short_desc
    assert "tracking" in short_desc.lower()
    assert "orbital" in short_desc.lower()

    package_json_path = os.path.join(root_dir, "package.json")
    with open(package_json_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    pkg_desc = pkg.get("description", "")
    assert pkg_desc == short_desc


def test_desktop_loading_splash_screen():
    """Verify that desktop loading splash screen contains progressive initialization and fallback messaging."""
    root_dir = os.path.dirname(os.path.dirname(__file__))
    splash_path = os.path.join(root_dir, "app", "static", "index.html")
    assert os.path.exists(splash_path)

    with open(splash_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Structure & Visual Elements
    assert "splash-container" in html
    assert "progress-bar" in html
    assert "fallback-card" in html

    # Progressive Initialization Stages
    assert "Bootstrapping isolated desktop environment" in html
    assert "Initializing local SQLite datastore" in html
    assert "orbital ephemeris cache" in html
    assert "embedded WSGI application service" in html

    # Subtle Fallback Messaging
    assert "Resilient Offline Fallback Active" in html
    assert "cached ephemeris" in html.lower()


def test_global_in_app_splash_modal():
    """Verify that base template and stylesheets contain global loading splash and fallback notice."""
    root_dir = os.path.dirname(os.path.dirname(__file__))

    # Template
    base_html_path = os.path.join(root_dir, "app", "templates", "base.html")
    with open(base_html_path, "r", encoding="utf-8") as f:
        base_html = f.read()

    assert 'id="sat-global-splash"' in base_html
    assert 'class="sat-splash-overlay"' in base_html
    assert 'id="sat-splash-fallback"' in base_html
    assert "Resilient Fallback Active" in base_html

    # Stylesheet
    css_path = os.path.join(root_dir, "app", "static", "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert ".sat-splash-overlay" in css
    assert ".sat-splash-card" in css
    assert ".sat-splash-fallback-box" in css

    # Script
    js_path = os.path.join(root_dir, "app", "static", "js", "app.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "SatProgress" in js
    assert "fallbackMessage" in js


def test_version_synchronization_and_bump(client):
    """Verify that version synchronization utility works and health endpoint exposes current version."""
    import sys

    root_dir = os.path.dirname(os.path.dirname(__file__))
    scripts_dir = os.path.join(root_dir, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    from bump_version import bump_semver, check_version_sync, get_current_version
    from app import get_app_version

    # Semver calculations
    assert bump_semver("0.1.0", "patch") == "0.1.1"
    assert bump_semver("0.1.0", "minor") == "0.2.0"
    assert bump_semver("0.1.0", "major") == "1.0.0"

    # Project-wide synchronization
    synced, versions = check_version_sync(root_dir)
    assert synced is True
    current_ver = get_current_version(root_dir)
    assert get_app_version() == current_ver

    # Health API endpoint
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["version"] == current_ver



