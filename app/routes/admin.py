"""
Admin Blueprint — database maintenance routes.
Provides:
  GET  /admin              — dashboard listing all upload sessions
  POST /admin/delete/<id>  — delete a specific upload session and its TLE elements
  POST /admin/reset        — wipe ALL satellites, TLE elements, and upload records
  POST /admin/reseed       — clear the seed flag so the Kaggle file is re-imported on next restart

All routes require Google OAuth authentication via @admin_required.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
import os
import threading
import requests
from sqlalchemy import func
from app import db
from app.models import Upload, Satellite, TLEElement, SystemSetting
from app.routes.auth import admin_required
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
from app.services.feature_flags import FEATURES, feature_enabled, get_feature_flags, set_feature_flags

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

MODELS_DIR = os.environ.get(
    "SATELLITE_MODEL_DIR",
    "/tmp/satellite-tracker/models"
    if os.environ.get("VERCEL")
    else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"),
)
MODEL_FILENAME = "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_PATH = os.path.join(MODELS_DIR, MODEL_FILENAME)
MODEL_URL = "https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf"

# Global download state
download_state = {
    "status": "idle",       # "idle", "downloading", "completed", "error"
    "progress": 0,          # percentage 0 to 100
    "error_message": None,
    "bytes_downloaded": 0,
    "total_bytes": 0
}
download_lock = threading.Lock()

def download_worker():
    global download_state
    try:
        os.makedirs(MODELS_DIR, exist_ok=True)
        if os.path.exists(MODEL_PATH):
            with download_lock:
                download_state["status"] = "completed"
                download_state["progress"] = 100
            return

        with download_lock:
            download_state["status"] = "downloading"
            download_state["progress"] = 0
            download_state["error_message"] = None
            download_state["bytes_downloaded"] = 0

        # Stream download
        response = requests.get(MODEL_URL, stream=True, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with download_lock:
            download_state["total_bytes"] = total_size

        bytes_written = 0
        temp_path = MODEL_PATH + ".tmp"
        with open(temp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                f.write(chunk)
                bytes_written += len(chunk)
                progress = int((bytes_written / total_size) * 100) if total_size > 0 else 0
                with download_lock:
                    download_state["bytes_downloaded"] = bytes_written
                    download_state["progress"] = progress

        # Rename temp file to final file
        os.rename(temp_path, MODEL_PATH)

        with download_lock:
            download_state["status"] = "completed"
            download_state["progress"] = 100

    except Exception as e:
        with download_lock:
            download_state["status"] = "error"
            download_state["error_message"] = str(e)
        temp_path = MODEL_PATH + ".tmp"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass



# ── helpers ──────────────────────────────────────────────────────────────────

def _build_session_list():
    """Return all Upload sessions enriched with a live TLE-element count."""
    uploads = Upload.query.order_by(Upload.upload_time.desc()).all()
    # Count TLEs per upload in one query for efficiency
    counts = dict(
        db.session.query(TLEElement.upload_id, func.count(TLEElement.id))
        .group_by(TLEElement.upload_id)
        .all()
    )
    result = []
    for u in uploads:
        result.append({
            "upload": u,
            "tle_count": counts.get(u.id, 0),
        })
    return result


# ── routes ───────────────────────────────────────────────────────────────────

def get_system_telemetry():
    """Collect real-time system, process, and Docker container metrics."""
    import time
    metrics = {
        "is_docker": os.path.exists('/.dockerenv') or os.environ.get("RUNNING_IN_DOCKER") == "true",
        "cpu_percent": 15.0,
        "cpu_cores": os.cpu_count() or 4,
        "memory_percent": 45.0,
        "memory_used_gb": "2.4",
        "memory_total_gb": "8.0",
        "disk_percent": 30.0,
        "disk_free_gb": "50.0",
        "disk_total_gb": "120.0",
        "process_memory_mb": "120.0",
        "process_uptime": "0m",
        "db_size_mb": "0.0",
        "datastore_engine": "unconfigured",
        "container_id": os.uname().nodename if hasattr(os, 'uname') else "local-host",
        "container_mem_limit": "Unlimited",
        "container_mem_usage": "N/A",
        "container_cpu_quota": "Unlimited",
    }

    # 1. Host/Server telemetry using psutil
    try:
        import psutil
        proc = psutil.Process(os.getpid())

        metrics["cpu_percent"] = round(psutil.cpu_percent(interval=0.1) or 15.0, 1)
        metrics["cpu_cores"] = psutil.cpu_count(logical=True) or (os.cpu_count() or 4)

        vm = psutil.virtual_memory()
        metrics["memory_percent"] = round(vm.percent, 1)
        metrics["memory_used_gb"] = f"{vm.used / (1024**3):.1f}"
        metrics["memory_total_gb"] = f"{vm.total / (1024**3):.1f}"

        du = psutil.disk_usage('/')
        metrics["disk_percent"] = round(du.percent, 1)
        metrics["disk_free_gb"] = f"{du.free / (1024**3):.1f}"
        metrics["disk_total_gb"] = f"{du.total / (1024**3):.1f}"

        pmem = proc.memory_info().rss
        metrics["process_memory_mb"] = f"{pmem / (1024**2):.1f}"

        create_time = proc.create_time()
        uptime_sec = int(time.time() - create_time)
        hrs = uptime_sec // 3600
        mins = (uptime_sec % 3600) // 60
        secs = uptime_sec % 60
        metrics["process_uptime"] = f"{hrs}h {mins}m {secs}s" if hrs > 0 else f"{mins}m {secs}s"
    except Exception as e:
        pass

    # 2. Database File Size
    try:
        from flask import current_app
        metrics["datastore_engine"] = current_app.config.get("DATASTORE_ENGINE") or "unconfigured"
        uri = current_app.config.get("SQLALCHEMY_DATABASE_URI") or ""
        if uri.startswith("sqlite:///") and ":memory:" not in uri:
            db_file = uri.replace("sqlite:///", "", 1)
            if os.path.exists(db_file):
                metrics["db_size_mb"] = f"{os.path.getsize(db_file) / (1024**2):.2f}"
    except Exception:
        pass

    # 3. Docker CGroup Container Metrics (if containerized)
    if metrics["is_docker"]:
        for mem_limit_path in ['/sys/fs/cgroup/memory.max', '/sys/fs/cgroup/memory/memory.limit_in_bytes']:
            if os.path.exists(mem_limit_path):
                try:
                    with open(mem_limit_path, 'r') as f:
                        val = f.read().strip()
                        if val and val != 'max' and int(val) < 10**15:
                            metrics["container_mem_limit"] = f"{int(val) / (1024**3):.1f} GB"
                except Exception:
                    pass
                break

        for mem_usage_path in ['/sys/fs/cgroup/memory.current', '/sys/fs/cgroup/memory/memory.usage_in_bytes']:
            if os.path.exists(mem_usage_path):
                try:
                    with open(mem_usage_path, 'r') as f:
                        val = f.read().strip()
                        if val:
                            metrics["container_mem_usage"] = f"{int(val) / (1024**2):.1f} MB"
                except Exception:
                    pass
                break

        if os.path.exists('/sys/fs/cgroup/cpu.max'):
            try:
                with open('/sys/fs/cgroup/cpu.max', 'r') as f:
                    parts = f.read().strip().split()
                    if len(parts) >= 2 and parts[0] != 'max':
                        quota, period = int(parts[0]), int(parts[1])
                        metrics["container_cpu_quota"] = f"{quota / period:.1f} Cores"
            except Exception:
                pass

    return metrics


def _datastore_template_context():
    path = config_path_for_app(current_app)
    cfg = load_datastore_config(path) or empty_config()
    cfg["engine"] = current_app.config.get("DATASTORE_ENGINE") or cfg.get("engine")
    return public_config(cfg)


@admin_bp.route("/", methods=["GET"])
@admin_required
def index():
    db_error = None
    sessions = []
    total_satellites = 0
    total_elements = 0
    seed_imported = False
    try:
        sessions = _build_session_list()
        total_satellites = Satellite.query.count()
        total_elements = TLEElement.query.count()
        seed_imported = SystemSetting.query.get("kaggle_seed_imported") is not None
    except Exception as exc:
        db_error = str(exc)

    telemetry = get_system_telemetry() if feature_enabled("system_telemetry") else None
    system_metrics = {
        "cpu": telemetry["cpu_percent"] if telemetry else 0,
        "memory": telemetry["memory_percent"] if telemetry else 0,
        "disk": telemetry["disk_percent"] if telemetry else 0,
    }

    from app.services.ai_prompt_service import (
        get_ai_system_prompt,
        is_custom_prompt_active,
        DEFAULT_AI_SYSTEM_PROMPT,
    )

    return render_template(
        "admin.html",
        sessions=sessions,
        total_satellites=total_satellites,
        total_elements=total_elements,
        seed_imported=seed_imported,
        feature_flags=get_feature_flags(),
        feature_names=FEATURES,
        system_metrics=system_metrics,
        telemetry=telemetry,
        datastore=_datastore_template_context(),
        db_error=db_error,
        ai_system_prompt=get_ai_system_prompt(),
        is_custom_prompt=is_custom_prompt_active(),
        default_ai_system_prompt=DEFAULT_AI_SYSTEM_PROMPT.strip(),
    )


@admin_bp.route("/datastore", methods=["POST"])
@admin_required
def update_datastore():
    path = config_path_for_app(current_app)
    existing = load_datastore_config(path) or empty_config()
    try:
        new_cfg = config_from_form(request.form, existing)
        migrate = request.form.get("migrate_data") in {"1", "on", "true", "yes"}
        previous_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI")
        result = apply_and_initialize(
            current_app,
            new_cfg,
            migrate_from_uri=previous_uri if migrate else None,
        )
        copied = result.get("copied") or {}
        extra = ""
        if migrate and any(copied.values()):
            extra = (
                f" Copied {copied.get('satellites', 0)} satellites and "
                f"{copied.get('tle_elements', 0)} TLE rows."
            )
        flash(f"Datastore is now {new_cfg.get('engine')}.{extra}", "success")
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.index"))


@admin_bp.route("/datastore/test", methods=["POST"])
@admin_required
def test_datastore():
    path = config_path_for_app(current_app)
    existing = load_datastore_config(path) or empty_config()
    try:
        payload = request.get_json(silent=True) or request.form
        cfg = config_from_form(payload, existing)
        uri = build_database_uri(cfg)
        ok, message = test_connection(uri)
        return jsonify({"ok": ok, "message": message, "engine": cfg.get("engine")}), (200 if ok else 400)
    except Exception as exc:
        log.warning("[admin] Error testing datastore config: %s", exc)
        return jsonify({"ok": False, "message": "Failed to test database connection."}), 400


@admin_bp.route("/feature-flags", methods=["POST"])
@admin_required
def update_feature_flags():
    values = {
        name: request.form.get(name) == "on"
        for name in FEATURES
    }
    set_feature_flags(values)
    flash("Feature flags updated.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/system-prompt", methods=["POST"])
@admin_required
def update_system_prompt():
    from app.services.ai_prompt_service import set_ai_system_prompt

    prompt_text = request.form.get("system_prompt", "").strip()
    if not prompt_text:
        flash("System prompt cannot be empty.", "error")
        return redirect(url_for("admin.index"))
    try:
        set_ai_system_prompt(prompt_text)
        flash("AI system prompt & few-shot examples updated.", "success")
    except Exception as exc:
        flash(f"Failed to update system prompt: {exc}", "error")
    return redirect(url_for("admin.index"))


@admin_bp.route("/system-prompt/reset", methods=["POST"])
@admin_required
def reset_system_prompt():
    from app.services.ai_prompt_service import reset_ai_system_prompt

    try:
        reset_ai_system_prompt()
        flash("AI system prompt restored to default.", "success")
    except Exception as exc:
        flash(f"Failed to reset system prompt: {exc}", "error")
    return redirect(url_for("admin.index"))


@admin_bp.route("/delete/<int:upload_id>", methods=["POST"])
@admin_required
def delete_session(upload_id: int):
    """Delete a single upload session and all its TLE elements (cascade)."""
    upload = Upload.query.get_or_404(upload_id)
    label = upload.label or upload.filename
    # Cascading delete on TLEElement is handled by the relationship cascade
    db.session.delete(upload)

    # If no more TLE elements exist for a satellite, prune the satellite record
    orphaned = (
        Satellite.query.filter(
            ~Satellite.tle_elements.any()
        ).all()
    )
    for sat in orphaned:
        db.session.delete(sat)

    db.session.commit()
    flash(f"Upload session '{label}' and its TLE data have been deleted.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/reset", methods=["POST"])
@admin_required
def reset_all():
    """Wipe every satellite, TLE element, and upload session from the database."""
    TLEElement.query.delete()
    Satellite.query.delete()
    Upload.query.delete()
    # Also clear the seed flag so the Kaggle dataset re-imports on next restart
    SystemSetting.query.filter_by(key="kaggle_seed_imported").delete()
    db.session.commit()
    flash("Database has been fully reset. The Kaggle seed will re-import on the next restart.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/reseed", methods=["POST"])
@admin_required
def reseed():
    """Clear only the seed flag so the Kaggle data is re-imported on the next restart."""
    deleted = SystemSetting.query.filter_by(key="kaggle_seed_imported").delete()
    db.session.commit()
    if deleted:
        flash("Seed flag cleared. The Kaggle dataset will be re-imported when the server restarts.", "info")
    else:
        flash("Seed flag was not set — nothing changed.", "warning")
    return redirect(url_for("admin.index"))


# ── AI Model Management Endpoints ──────────────────────────────────────────

@admin_bp.route("/model-status", methods=["GET"])
@admin_required
def model_status():
    if not feature_enabled("ai_model_management"):
        return jsonify({"error": "AI model management is disabled"}), 503
    global download_state
    # Check physical file state to sync status if completed outside thread
    exists = os.path.exists(MODEL_PATH)
    with download_lock:
        if exists and download_state["status"] != "downloading":
            download_state["status"] = "completed"
            download_state["progress"] = 100
        elif not exists and download_state["status"] == "completed":
            download_state["status"] = "idle"
            download_state["progress"] = 0
        
        return jsonify({
            "exists": exists,
            "status": download_state["status"],
            "progress": download_state["progress"],
            "bytes_downloaded": download_state["bytes_downloaded"],
            "total_bytes": download_state["total_bytes"],
            "error_message": download_state["error_message"]
        })


@admin_bp.route("/download-model", methods=["POST"])
@admin_required
def download_model():
    if not feature_enabled("ai_model_management"):
        return jsonify({"error": "AI model management is disabled"}), 503
    global download_state
    with download_lock:
        if download_state["status"] == "downloading":
            return jsonify({"status": "already downloading"}), 200
        
        # Start background thread
        thread = threading.Thread(target=download_worker)
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "started"})


@admin_bp.route("/delete-model", methods=["POST"])
@admin_required
def delete_model():
    if not feature_enabled("ai_model_management"):
        return jsonify({"error": "AI model management is disabled"}), 503
    global download_state
    with download_lock:
        if download_state["status"] == "downloading":
            return jsonify({"error": "Cannot delete while downloading"}), 400
        
        if os.path.exists(MODEL_PATH):
            try:
                os.remove(MODEL_PATH)
                download_state["status"] = "idle"
                download_state["progress"] = 0
                download_state["error_message"] = None
                return jsonify({"status": "deleted"})
            except Exception:
                return jsonify({"error": "Failed to delete the model file."}), 500
        else:
            return jsonify({"status": "not found"})


@admin_bp.route("/database", methods=["GET"])
@admin_required
def database_console():
    from app.services.sql_console import DEFAULT_ROWS, MAX_ROWS, MIN_ROWS, ensure_saved_query_columns, list_saved_queries, list_tables_with_counts

    db_error = None
    tables = []
    saved = []
    try:
        ensure_saved_query_columns(db)
        tables = list_tables_with_counts(db)
        saved = list_saved_queries(db)
    except Exception as exc:
        db_error = str(exc)
    return render_template(
        "admin_database.html",
        tables=tables,
        saved_queries=saved,
        db_error=db_error,
        datastore=_datastore_template_context(),
        default_rows=DEFAULT_ROWS,
        min_rows=MIN_ROWS,
        max_rows=MAX_ROWS,
    )


@admin_bp.route("/database/query", methods=["POST"])
@admin_required
def database_query():
    from app.services.sql_console import DEFAULT_ROWS, record_saved_query_run, run_readonly_query

    payload = request.get_json(silent=True) or request.form or {}
    sql = payload.get("sql", "")
    limit = payload.get("limit", DEFAULT_ROWS)
    try:
        result = run_readonly_query(db, sql, limit=limit)
        saved_id = payload.get("saved_query_id")
        if saved_id not in (None, ""):
            try:
                stats = record_saved_query_run(
                    db,
                    int(saved_id),
                    result["elapsed_ms"],
                    result.get("row_count"),
                )
                if stats:
                    result["saved_query"] = stats
            except (TypeError, ValueError):
                pass
        return jsonify({"ok": True, **result})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        log.exception("[admin] Database query execution failed: %s", exc)
        return jsonify({"ok": False, "error": "Query execution failed."}), 400


@admin_bp.route("/database/saved", methods=["GET", "POST"])
@admin_required
def database_saved_queries():
    from app.services.sql_console import add_saved_query, list_saved_queries

    if request.method == "GET":
        return jsonify({"ok": True, "queries": list_saved_queries(db)})
    payload = request.get_json(silent=True) or request.form or {}
    try:
        entry = add_saved_query(
            db,
            payload.get("name", ""),
            payload.get("sql", ""),
            payload.get("row_limit"),
            elapsed_ms=payload.get("elapsed_ms"),
            row_count=payload.get("row_count"),
        )
        return jsonify({"ok": True, "query": entry}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        log.exception("[admin] Failed to save query: %s", exc)
        return jsonify({"ok": False, "error": "Failed to save query."}), 400


@admin_bp.route("/database/saved/<int:query_id>", methods=["DELETE"])
@admin_required
def database_delete_saved_query(query_id: int):
    from app.services.sql_console import delete_saved_query

    removed = delete_saved_query(db, query_id)
    if not removed:
        return jsonify({"ok": False, "error": "Saved query not found"}), 404
    return jsonify({"ok": True})

