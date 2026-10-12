"""
Automated Background CelesTrak TLE Synchronization Service and Scheduler.
Periodically refreshes orbital element sets while strictly adhering to
CelesTrak rate-limiting rules and tracking data freshness.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from app import db
from app.models import Satellite, TLEElement, Upload
from app.services.db_service import upsert_tle_records
from app.services.tle_parser import parse_tle_file

logger = logging.getLogger(__name__)

# CelesTrak active satellites URL
CELESTRAK_ACTIVE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"

# Rate-limiting: minimum seconds between automated CelesTrak syncs (2 hours)
MIN_SYNC_INTERVAL_SECONDS = 7200

# Default background check interval: 12 hours
DEFAULT_BACKGROUND_INTERVAL_SECONDS = 43200

_sync_lock = threading.Lock()
_last_sync_timestamp: float = 0.0
_scheduler_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_tle_freshness() -> dict[str, Any]:
    """
    Calculate orbital data freshness and age metrics.
    Safe to call within Flask application contexts.
    """
    try:
        latest_upload = Upload.query.order_by(Upload.upload_time.desc()).first()
        latest_tle = TLEElement.query.order_by(TLEElement.epoch_datetime.desc()).first()
        sat_count = Satellite.query.count()

        if not latest_upload and not latest_tle:
            return {
                "has_data": False,
                "freshness_label": "No TLEs loaded",
                "hours_ago": None,
                "is_stale": True,
                "last_sync_time": None,
                "satellite_count": 0,
            }

        ref_time = latest_upload.upload_time if latest_upload else latest_tle.epoch_datetime
        now = _utcnow()
        diff_seconds = max(0, (now - ref_time).total_seconds())
        hours_ago = round(diff_seconds / 3600.0, 1)

        if hours_ago < 1.0:
            minutes_ago = max(1, int(diff_seconds / 60.0))
            label = f"Updated {minutes_ago}m ago"
            is_stale = False
        elif hours_ago < 12.0:
            label = f"Updated {hours_ago:.0f}h ago"
            is_stale = False
        elif hours_ago < 48.0:
            label = f"Stale ({hours_ago:.0f}h ago)"
            is_stale = True
        else:
            days_ago = int(hours_ago / 24.0)
            label = f"Stale ({days_ago}d ago)"
            is_stale = True

        return {
            "has_data": True,
            "freshness_label": label,
            "hours_ago": hours_ago,
            "is_stale": is_stale,
            "last_sync_time": ref_time.isoformat(),
            "satellite_count": sat_count,
        }
    except Exception as exc:
        logger.debug("[tle_sync_scheduler] Error querying freshness: %s", exc)
        return {
            "has_data": False,
            "freshness_label": "Unknown",
            "hours_ago": None,
            "is_stale": True,
            "last_sync_time": None,
            "satellite_count": 0,
        }


def sync_celestrak_active_satellites(app=None, force: bool = False) -> dict[str, Any]:
    """
    Execute synchronization against CelesTrak active satellite elements.
    Adheres to CelesTrak rate-limiting unless force=True.
    """
    global _last_sync_timestamp

    if not _sync_lock.acquire(blocking=False):
        return {"success": False, "message": "Synchronization is already running in background."}

    try:
        now_ts = time.time()
        elapsed = now_ts - _last_sync_timestamp
        if not force and elapsed < MIN_SYNC_INTERVAL_SECONDS:
            remaining_mins = int((MIN_SYNC_INTERVAL_SECONDS - elapsed) / 60)
            return {
                "success": False,
                "rate_limited": True,
                "message": f"Rate-limit active. CelesTrak allows refreshes every 2 hours. Next allowed in {remaining_mins} min.",
            }

        # Import fetch helper from upload route
        from app.routes.upload import fetch_tle_from_url

        content, warn_msg, err_msg = fetch_tle_from_url(CELESTRAK_ACTIVE_URL, timeout=45)
        if err_msg or not content:
            return {
                "success": False,
                "message": err_msg or "Failed to fetch TLE content from CelesTrak.",
                "warning": warn_msg,
            }

        records = parse_tle_file(content)
        if not records:
            return {
                "success": False,
                "message": "No valid TLE records parsed from response.",
            }

        summary = upsert_tle_records(
            records,
            filename="celestrak_active_auto_sync.tle",
            source="celestrak_auto_sync",
            label="Automated Background CelesTrak Sync",
        )
        db.session.commit()

        _last_sync_timestamp = time.time()
        logger.info(
            "[tle_sync_scheduler] Auto-sync complete: %d parsed, %d new sats, %d updated.",
            len(records),
            summary.get("new_satellites", 0),
            summary.get("updated_satellites", 0),
        )
        return {
            "success": True,
            "summary": summary,
            "records_count": len(records),
            "message": f"Successfully synchronized {len(records)} active satellites from CelesTrak.",
        }
    except Exception as exc:
        logger.error("[tle_sync_scheduler] Synchronization error: %s", exc, exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"success": False, "message": f"Sync failed: {str(exc)}"}
    finally:
        _sync_lock.release()


def _run_scheduler_loop(app, check_interval_seconds: int):
    """Background worker daemon loop."""
    logger.info("[tle_sync_scheduler] Background scheduler worker started (interval=%ds).", check_interval_seconds)
    while not _stop_event.is_set():
        # Sleep in small slices to respond promptly to stop_event
        for _ in range(check_interval_seconds):
            if _stop_event.is_set():
                break
            time.sleep(1)

        if _stop_event.is_set():
            break

        try:
            with app.app_context():
                freshness = get_tle_freshness()
                # If stale (> 12 hours) or no data, initiate sync
                if freshness.get("is_stale", True):
                    logger.info("[tle_sync_scheduler] TLE data is stale (%s). Triggering auto-sync.", freshness.get("freshness_label"))
                    sync_celestrak_active_satellites(app=app, force=False)
        except Exception as exc:
            logger.warning("[tle_sync_scheduler] Error in background loop: %s", exc)


def start_tle_sync_scheduler(app, interval_seconds: int = DEFAULT_BACKGROUND_INTERVAL_SECONDS) -> None:
    """Start background scheduler thread if auto-sync is enabled."""
    global _scheduler_thread, _stop_event

    if app.config.get("TESTING"):
        return

    auto_enabled = app.config.get("AUTO_TLE_SYNC_ENABLED", True)
    if not auto_enabled:
        logger.info("[tle_sync_scheduler] Auto-sync disabled via config (AUTO_TLE_SYNC_ENABLED=False).")
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_run_scheduler_loop,
        args=(app, interval_seconds),
        name="tle-sync-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()


def stop_tle_sync_scheduler() -> None:
    """Signal background thread to gracefully stop."""
    global _scheduler_thread, _stop_event
    _stop_event.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=2.0)
