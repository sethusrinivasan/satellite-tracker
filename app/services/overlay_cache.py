"""Shared overlay cache: per-feed TTL, stale-while-revalidate, and pluggable backends."""

from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

from app.services.cache_backends import (
    CacheBackend,
    CacheBackendFactory,
    FallbackCacheBackend,
    FileCacheBackend,
    MemoryCacheBackend,
    TieredCacheBackend,
    ValkeyCacheBackend,
    format_cache_id,
    is_valkey_supported_platform,
    safe_part,
)

log = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60
PENDING_TTL_SECONDS = 12

# Slow-changing or expensive feeds keep longer than live positions.
NAMESPACE_TTL = {
    "city-temps": 3600,
    "webcams-osm": 900,
    "shipping-meta": 1800,
    "currencies": 300,
    "news": 180,
    "world-events": 120,
    "markets": 90,
    "markets-hist": 3600,
    "flights": 25,
    "shipping": 45,
    "cloud-datacenters": 90,
}

_memory: dict[str, dict[str, Any]] = {}
_thread_locks: dict[str, threading.Lock] = {}
_thread_locks_guard = threading.Lock()
_refresh_threads: dict[str, threading.Thread] = {}
_refresh_guard = threading.Lock()

_valkey_client: Any = None
_valkey_init_attempted: bool = False
_valkey_lock = threading.Lock()

_backend: CacheBackend | None = None
_backend_lock = threading.Lock()


def _safe_part(value: str) -> str:
    return safe_part(value)


def cache_id(namespace: str, key: str = "global") -> str:
    return format_cache_id(namespace, key)


def ttl_for(namespace: str, ttl: float | None = None) -> float:
    if ttl is not None:
        return float(ttl)
    return float(NAMESPACE_TTL.get(namespace, CACHE_TTL_SECONDS))


def cache_dir() -> Path:
    configured = os.environ.get("OVERLAY_CACHE_DIR")
    if configured:
        root = Path(configured)
    elif os.environ.get("SATELLITE_RUNTIME_DIR"):
        root = Path(os.environ["SATELLITE_RUNTIME_DIR"]) / "overlay_cache"
    elif os.environ.get("VERCEL"):
        root = Path("/tmp/satellite-tracker") / "overlay_cache"
    else:
        root = Path(__file__).resolve().parents[2] / "instance" / "overlay_cache"
    try:
        root.mkdir(parents=True, exist_ok=True)
        return root
    except OSError:
        fallback = Path(tempfile.gettempdir()) / "sattrack_overlay_cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


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
    except (OSError, ImportError):
        try:
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        except Exception:
            pass
    return handle


def _unlock(handle) -> None:
    try:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except (OSError, ImportError):
        try:
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
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


def _find_valkey_backend(backend: CacheBackend) -> ValkeyCacheBackend | None:
    if isinstance(backend, ValkeyCacheBackend):
        return backend
    if isinstance(backend, FallbackCacheBackend):
        return _find_valkey_backend(backend.primary) or _find_valkey_backend(backend.fallback)
    if isinstance(backend, TieredCacheBackend):
        for tier in backend.tiers:
            found = _find_valkey_backend(tier)
            if found is not None:
                return found
    return None


def get_active_backend() -> CacheBackend:
    """Return the active configured cache backend hierarchy."""
    global _backend
    with _backend_lock:
        vk_in_backend = _find_valkey_backend(_backend) if _backend is not None else None
        current_backend_client = vk_in_backend.get_client() if vk_in_backend else None

        if _backend is not None:
            if _valkey_client is not None and current_backend_client is not _valkey_client:
                _backend.close()
                _backend = None
            else:
                return _backend

        _backend = CacheBackendFactory.create_backend(
            prefer_valkey=True if _valkey_client is not None else None,
            valkey_client=_valkey_client,
            memory_store=_memory,
            cache_directory=cache_dir(),
        )
        return _backend


def get_valkey_client() -> Any | None:
    """
    Return an active Valkey/Redis client if configured and enabled under feature flag.
    Returns None if unconfigured, disabled by feature flag, or unsupported.
    """
    global _valkey_client, _valkey_init_attempted
    if _valkey_client is not None:
        return _valkey_client

    with _valkey_lock:
        if _valkey_init_attempted:
            return _valkey_client
        _valkey_init_attempted = True

        backend = get_active_backend()
        vk = _find_valkey_backend(backend)
        if vk is not None:
            _valkey_client = vk.get_client()
            return _valkey_client
        return None


def _write_record(
    path: Path,
    payload: Any,
    now: float | None = None,
    ttl: float | None = None,
    namespace: str | None = None,
    key: str | None = None,
) -> None:
    now = time.time() if now is None else now
    lifetime = CACHE_TTL_SECONDS if ttl is None else float(ttl)
    record = {"expires": now + lifetime, "stored": now, "payload": payload}

    # Atomic file persistence
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    _memory[str(path)] = record

    if namespace:
        cid = cache_id(namespace, key or "global")
        _memory[cid] = record
        backend = get_active_backend()
        backend.set_record(namespace, key or "global", record, ttl=lifetime)

    # Ensure direct test mocks attached via _valkey_client receive write
    vk = get_valkey_client()
    if vk is not None and namespace:
        try:
            vk_key = f"sattrack:overlay:{cache_id(namespace, key or 'global')}"
            valkey_ttl = max(int(lifetime * 3), 3600)
            vk.set(vk_key, json.dumps(record, ensure_ascii=False), ex=valkey_ttl)
        except Exception as exc:
            log.debug("[valkey] Store failed for %s: %s", namespace, exc)


def get_fresh(namespace: str, key: str = "global") -> Any | None:
    path, _ = _paths(namespace, key)
    now = time.time()
    cid = cache_id(namespace, key)

    record = _memory.get(str(path)) or _memory.get(cid)
    if not record:
        backend = get_active_backend()
        record = backend.get_record(namespace, key)
    if not record:
        vk = get_valkey_client()
        if vk is not None:
            try:
                raw = vk.get(f"sattrack:overlay:{cid}")
                if raw:
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    loaded = json.loads(raw)
                    if isinstance(loaded, dict) and "payload" in loaded:
                        record = loaded
            except Exception as exc:
                log.debug("[valkey] Read failed for %s: %s", namespace, exc)
    if not record:
        record = _read_record(path)
    if not record:
        return None

    _memory[str(path)] = record
    _memory[cid] = record

    if float(record.get("expires") or 0) <= now:
        return None
    return copy.deepcopy(record.get("payload"))


def get_stale(namespace: str, key: str = "global") -> Any | None:
    path, _ = _paths(namespace, key)
    cid = cache_id(namespace, key)

    record = _memory.get(str(path)) or _memory.get(cid)
    if not record:
        backend = get_active_backend()
        record = backend.get_record(namespace, key)
    if not record:
        vk = get_valkey_client()
        if vk is not None:
            try:
                raw = vk.get(f"sattrack:overlay:{cid}")
                if raw:
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")
                    loaded = json.loads(raw)
                    if isinstance(loaded, dict) and "payload" in loaded:
                        record = loaded
            except Exception as exc:
                log.debug("[valkey] Stale read failed for %s: %s", namespace, exc)
    if not record:
        record = _read_record(path)
    if not record:
        return None

    _memory[str(path)] = record
    _memory[cid] = record
    return copy.deepcopy(record.get("payload"))


def cache_age_seconds(namespace: str, key: str = "global") -> float | None:
    path, _ = _paths(namespace, key)
    cid = cache_id(namespace, key)
    record = _memory.get(str(path)) or _memory.get(cid) or _read_record(path)
    if not record:
        return None
    stored = record.get("stored")
    try:
        return max(0.0, time.time() - float(stored))
    except (TypeError, ValueError):
        return None


def store(namespace: str, payload: Any, key: str = "global", ttl: float | None = None) -> Any:
    path, _ = _paths(namespace, key)
    _write_record(path, payload, ttl=ttl_for(namespace, ttl), namespace=namespace, key=key)
    return copy.deepcopy(payload)


def is_refreshing(namespace: str, key: str = "global") -> bool:
    thread = _refresh_threads.get(cache_id(namespace, key))
    return thread is not None and thread.is_alive()


def wait_refresh(namespace: str, key: str = "global", timeout: float = 5.0) -> bool:
    thread = _refresh_threads.get(cache_id(namespace, key))
    if thread is None:
        return True
    thread.join(timeout)
    return not thread.is_alive()


def _run_refresh(namespace: str, key: str, loader: Callable[[], Any], ttl: float | None) -> None:
    log.info("[overlay-cache] Refreshing %s", cache_id(namespace, key))
    try:
        payload = loader()
    except Exception as exc:
        log.warning("[overlay-cache] Refresh %s failed: %s", cache_id(namespace, key), exc)
        return
    if payload is None:
        log.info("[overlay-cache] Refresh %s returned nothing; keeping stale", cache_id(namespace, key))
        return
    store(namespace, payload, key=key, ttl=ttl)
    log.info("[overlay-cache] Stored %s", cache_id(namespace, key))


def schedule_refresh(
    namespace: str,
    loader: Callable[[], Any],
    key: str = "global",
    ttl: float | None = None,
) -> None:
    cache_key = cache_id(namespace, key)
    with _refresh_guard:
        current = _refresh_threads.get(cache_key)
        if current is not None and current.is_alive():
            return
        thread = threading.Thread(
            target=_run_refresh,
            args=(namespace, key, loader, ttl),
            name=f"overlay-{namespace}",
            daemon=True,
        )
        _refresh_threads[cache_key] = thread
        thread.start()


def get_or_set(
    namespace: str,
    loader: Callable[[], Any],
    key: str = "global",
    force_refresh: bool = False,
    ttl: float | None = None,
    skeleton: Any = None,
) -> Any:
    """Return shared overlay data. Expired entries are served immediately while a refresh runs."""
    cache_key = cache_id(namespace, key)
    lifetime = ttl_for(namespace, ttl)
    if not force_refresh:
        fresh = get_fresh(namespace, key)
        if fresh is not None:
            return fresh
        stale = get_stale(namespace, key)
        if stale is not None:
            schedule_refresh(namespace, loader, key=key, ttl=lifetime)
            return stale
        if skeleton is not None:
            store(namespace, skeleton, key=key, ttl=PENDING_TTL_SECONDS)
            schedule_refresh(namespace, loader, key=key, ttl=lifetime)
            return copy.deepcopy(skeleton)
    path, lock_path = _paths(namespace, key)
    with _thread_lock(cache_key):
        handle = _file_lock(lock_path)
        try:
            if not force_refresh:
                fresh = get_fresh(namespace, key)
                if fresh is not None:
                    return fresh
            payload = loader()
            if payload is None:
                stale = get_stale(namespace, key)
                if stale is not None:
                    return stale
                return copy.deepcopy(skeleton) if skeleton is not None else None
            _write_record(path, payload, ttl=lifetime, namespace=namespace, key=key)
            return copy.deepcopy(payload)
        finally:
            _unlock(handle)


def reset_runtime_state() -> None:
    """Reset all in-memory runtime cache state, backend hierarchy, and Valkey connections."""
    global _valkey_client, _valkey_init_attempted, _backend
    _memory.clear()
    with _backend_lock:
        if _backend is not None:
            try:
                _backend.close()
            except Exception:
                pass
            _backend = None
        with _valkey_lock:
            if _valkey_client is not None:
                try:
                    _valkey_client.close()
                except Exception:
                    pass
                _valkey_client = None
            _valkey_init_attempted = False
