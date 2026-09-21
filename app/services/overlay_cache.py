"""Shared 60s cache for overlay feeds so every user reuses the same fetch."""

from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

CACHE_TTL_SECONDS = 60

_memory: dict[str, dict[str, Any]] = {}
_thread_locks: dict[str, threading.Lock] = {}
_thread_locks_guard = threading.Lock()


def cache_dir() -> Path:
    configured = os.environ.get("OVERLAY_CACHE_DIR")
    if configured:
        root = Path(configured)
    else:
        root = Path(__file__).resolve().parents[2] / "instance" / "overlay_cache"
    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "sattrack_overlay_cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _safe_part(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in (value or "global"))
    return cleaned[:120] or "global"


def cache_id(namespace: str, key: str = "global") -> str:
    return f"{_safe_part(namespace)}::{_safe_part(key)}"


def _paths(namespace: str, key: str) -> tuple[Path, Path]:
    stem = f"{_safe_part(namespace)}__{_safe_part(key)}"
    root = cache_dir()
    return root / f"{stem}.json", root / f"{stem}.lock"


def _thread_lock(cache_key: str) -> threading.Lock:
    with _thread_locks_guard:
        lock = _thread_locks.get(cache_key)
        if lock is None:
            lock = threading.Lock()
            _thread_locks[cache_key] = lock
        return lock


def _file_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+", encoding="utf-8")
    try:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    except OSError:
        pass
    return handle


def _unlock(handle) -> None:
    try:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    handle.close()


def _read_record(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
        record = json.loads(raw)
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(record, dict) or "payload" not in record:
        return None
    return record


def _write_record(path: Path, payload: Any, now: float | None = None) -> None:
    now = time.time() if now is None else now
    record = {"expires": now + CACHE_TTL_SECONDS, "payload": payload}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    _memory[str(path)] = record


def get_fresh(namespace: str, key: str = "global") -> Any | None:
    path, _ = _paths(namespace, key)
    now = time.time()
    record = _memory.get(str(path)) or _read_record(path)
    if not record:
        return None
    _memory[str(path)] = record
    if float(record.get("expires") or 0) <= now:
        return None
    return copy.deepcopy(record.get("payload"))


def get_stale(namespace: str, key: str = "global") -> Any | None:
    path, _ = _paths(namespace, key)
    record = _memory.get(str(path)) or _read_record(path)
    if not record:
        return None
    return copy.deepcopy(record.get("payload"))


def store(namespace: str, payload: Any, key: str = "global") -> Any:
    path, _ = _paths(namespace, key)
    _write_record(path, payload)
    return copy.deepcopy(payload)


def get_or_set(
    namespace: str,
    loader: Callable[[], Any],
    key: str = "global",
    force_refresh: bool = False,
) -> Any:
    """Return shared overlay data, fetching at most once per TTL for all users."""
    cache_key = cache_id(namespace, key)
    path, lock_path = _paths(namespace, key)
    with _thread_lock(cache_key):
        handle = _file_lock(lock_path)
        try:
            if not force_refresh:
                fresh = get_fresh(namespace, key)
                if fresh is not None:
                    return fresh
            payload = loader()
            _write_record(path, payload)
            return copy.deepcopy(payload)
        finally:
            _unlock(handle)
