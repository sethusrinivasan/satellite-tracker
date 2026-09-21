"""
First-launch datastore setup. Shown until instance/datastore.json (or DATABASE_URL)
has been configured. Later changes go through the Admin panel.
"""

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for

from app.services.datastore import (
    apply_and_initialize,
    build_database_uri,
    config_from_form,
    config_path_for_app,
    empty_config,
    load_datastore_config,
    public_config,
    test_connection,
)

setup_bp = Blueprint("setup", __name__)


def _current_config():
    path = config_path_for_app(current_app)
    return load_datastore_config(path) or empty_config()


@setup_bp.route("/setup", methods=["GET", "POST"])
def index():
    if current_app.config.get("DATASTORE_CONFIGURED") and request.method == "GET":
        flash("Datastore is already configured. Change it from Admin → Database.", "info")
        return redirect(url_for("report.report"))

    cfg = _current_config()
    if request.method == "POST":
        if current_app.config.get("DATASTORE_CONFIGURED"):
            flash("Datastore is already configured. Change it from Admin → Database.", "info")
            return redirect(url_for("report.report"))
        try:
            new_cfg = config_from_form(request.form, cfg)
            apply_and_initialize(current_app, new_cfg, migrate_from_uri=None)
            from app import _seed_kaggle_data_if_needed

            _seed_kaggle_data_if_needed(current_app)
            engine = new_cfg.get("engine")
            flash(f"Datastore initialized ({engine}). You can change this later in Admin settings.", "success")
            return redirect(url_for("report.report"))
        except Exception as exc:
            flash(str(exc), "error")
            try:
                cfg = config_from_form(request.form, cfg)
            except Exception:
                pass

    return render_template(
        "setup.html",
        datastore=public_config(cfg),
        mode="setup",
    )


@setup_bp.route("/setup/test", methods=["POST"])
def test():
    if current_app.config.get("DATASTORE_CONFIGURED"):
        return jsonify({"ok": False, "message": "Datastore is already configured."}), 400
    try:
        cfg = config_from_form(request.get_json(silent=True) or request.form, _current_config())
        uri = build_database_uri(cfg)
        ok, message = test_connection(uri)
        return jsonify({"ok": ok, "message": message, "engine": cfg.get("engine")}), (200 if ok else 400)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400
