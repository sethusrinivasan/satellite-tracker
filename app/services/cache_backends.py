"""
Pluggable Cache Architecture with Strategy, Composite (Tiered), Fallback (Resilient),
and Factory Design Patterns.

Supports Memory, File/Disk, and Valkey/Redis cache backends with automatic platform fallback.
"""

from __future__ import annotations

import abc
import copy
import json
import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60
DEFAULT_VALKEY_PREFIX = "sattrack:overlay:"


def is_valkey_supported_platform() -> bool:
    """
    Check if the current runtime environment natively supports Valkey.
    Supported:
      - Linux and macOS (POSIX) environments for both Web and Desktop runtimes.
      - Any platform with an external VALKEY_URL or REDIS_URL configured.
    Unsupported by default:
      - Native Windows (win32) desktop / server (valkey server requires POSIX syscalls).
      - Vercel serverless environment (ephemeral execution, no persistent daemon).
    """
    if os.environ.get("VALKEY_URL") or os.environ.get("REDIS_URL"):
        return True
    if os.environ.get("VERCEL"):
        return False
    if sys.platform == "win32":
        return False
    return True


def safe_part(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in (value or "global"))
    return cleaned[:120] or "global"


def format_cache_id(namespace: str, key: str = "global") -> str:
    return f"{safe_part(namespace)}::{safe_part(key)}"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Strategy Pattern: Abstract Cache Strategy
# ─────────────────────────────────────────────────────────────────────────────

class CacheBackend(abc.ABC):
    """
    Abstract Strategy pattern interface for cache storage engines.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Identifying name of the cache backend."""
        pass

    @abc.abstractmethod
    def get_record(self, namespace: str, key: str = "global") -> dict[str, Any] | None:
        """
        Retrieve record dict: {'expires': float, 'stored': float, 'payload': Any}.
        Returns None if record does not exist or is invalid.
        """
        pass

    @abc.abstractmethod
    def set_record(
        self,
        namespace: str,
        key: str,
        record: dict[str, Any],
        ttl: float,
    ) -> bool:
        """
        Persist a cache record. Returns True on success, False on failure.
        """
        pass

    @abc.abstractmethod
    def delete(self, namespace: str, key: str = "global") -> bool:
        """Delete an entry from the cache."""
        pass

    @abc.abstractmethod
    def clear(self) -> None:
        """Clear cache entries or reset in-memory state."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if backend is available and operational."""
        pass

    def close(self) -> None:
        """Release underlying connections or handles."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 2. Concrete Strategy: MemoryCacheBackend
# ─────────────────────────────────────────────────────────────────────────────

class MemoryCacheBackend(CacheBackend):
    """
    Concrete Strategy: High-speed in-memory dictionary cache.
    Thread-safe and process-local.
    """

    def __init__(self, store: dict[str, dict[str, Any]] | None = None):
        self._store = store if store is not None else {}
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "MemoryCache"

    def is_available(self) -> bool:
        return True

    def get_record(self, namespace: str, key: str = "global") -> dict[str, Any] | None:
        cid = format_cache_id(namespace, key)
        with self._lock:
            rec = self._store.get(cid)
            if rec is None:
                # Also check file-path-like key for backward compatibility
                stem = f"{safe_part(namespace)}__{safe_part(key)}.json"
                for k, v in self._store.items():
                    if k.endswith(stem):
                        rec = v
                        break
            if rec is not None and isinstance(rec, dict) and "payload" in rec:
                return copy.deepcopy(rec)
            return None

    def set_record(
        self,
        namespace: str,
        key: str,
        record: dict[str, Any],
        ttl: float,
    ) -> bool:
        cid = format_cache_id(namespace, key)
        with self._lock:
            self._store[cid] = copy.deepcopy(record)
        return True

    def delete(self, namespace: str, key: str = "global") -> bool:
        cid = format_cache_id(namespace, key)
        with self._lock:
            return self._store.pop(cid, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def get_store(self) -> dict[str, dict[str, Any]]:
        return self._store


# ─────────────────────────────────────────────────────────────────────────────
# 3. Concrete Strategy: FileCacheBackend
# ─────────────────────────────────────────────────────────────────────────────

class FileCacheBackend(CacheBackend):
    """
    Concrete Strategy: File-based atomic JSON storage with OS file locking.
    Cross-process persistent and safe across web workers.
    """

    def __init__(self, cache_dir: Path | None = None):
        self._dir = cache_dir

    @property
    def name(self) -> str:
        return "FileCache"

    def get_dir(self) -> Path:
        if self._dir is not None:
            return self._dir
        from app.services.overlay_cache import cache_dir
        return cache_dir()

    def paths(self, namespace: str, key: str = "global") -> tuple[Path, Path]:
        stem = f"{safe_part(namespace)}__{safe_part(key)}"
        root = self.get_dir()
        return root / f"{stem}.json", root / f"{stem}.lock"

    def is_available(self) -> bool:
        try:
            d = self.get_dir()
            d.mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False

    def get_record(self, namespace: str, key: str = "global") -> dict[str, Any] | None:
        path, _ = self.paths(namespace, key)
        try:
            raw = path.read_text(encoding="utf-8")
            record = json.loads(raw)
        except (OSError, json.JSONDecodeError, TypeError):
            return None
        if not isinstance(record, dict) or "payload" not in record:
            return None
        return record

    def set_record(
        self,
        namespace: str,
        key: str,
        record: dict[str, Any],
        ttl: float,
    ) -> bool:
        path, _ = self.paths(namespace, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            tmp.replace(path)
            return True
        except OSError as exc:
            log.warning("[FileCache] Failed to write cache record to %s: %s", path, exc)
            return False

    def delete(self, namespace: str, key: str = "global") -> bool:
        path, _ = self.paths(namespace, key)
        try:
            if path.exists():
                path.unlink()
                return True
            return False
        except OSError:
            return False

    def clear(self) -> None:
        try:
            d = self.get_dir()
            for p in d.glob("*__*.json"):
                try:
                    p.unlink()
                except OSError:
                    pass
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# 4. Concrete Strategy: ValkeyCacheBackend
# ─────────────────────────────────────────────────────────────────────────────

class ValkeyCacheBackend(CacheBackend):
    """
    Concrete Strategy: Valkey / Redis high-performance in-memory cache.
    Connects to external Valkey/Redis via VALKEY_URL / REDIS_URL, or spawns
    an embedded Valkey daemon via valkeylite on supported POSIX systems.
    """

    def __init__(
        self,
        client: Any | None = None,
        url: str | None = None,
        key_prefix: str = DEFAULT_VALKEY_PREFIX,
    ):
        self.key_prefix = key_prefix
        self._client: Any = client
        self._url: str | None = url
        self._init_attempted: bool = client is not None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return "ValkeyCache"

    def _valkey_key(self, namespace: str, key: str) -> str:
        return f"{self.key_prefix}{format_cache_id(namespace, key)}"

    def get_client(self) -> Any | None:
        if self._init_attempted:
            return self._client

        with self._lock:
            if self._init_attempted:
                return self._client
            self._init_attempted = True

            # 1. External URL
            valkey_url = self._url or os.environ.get("VALKEY_URL") or os.environ.get("REDIS_URL")
            if valkey_url:
                try:
                    import valkey

                    client = valkey.Valkey.from_url(valkey_url, socket_timeout=2.0)
                    client.ping()
                    self._client = client
                    log.info("[valkey] Connected to Valkey at %s", valkey_url)
                    return self._client
                except Exception as exc:
                    log.warning("[valkey] External Valkey unavailable at %s: %s", valkey_url, exc)
                    self._client = None
                    return None

            # 2. Embedded Valkey via valkeylite on supported POSIX systems
            if is_valkey_supported_platform():
                try:
                    from valkeylite import Valkey

                    client = Valkey()
                    client.ping()
                    self._client = client
                    log.info("[valkey] Started embedded Valkey daemon via valkeylite")
                    return self._client
                except Exception as exc:
                    log.warning("[valkey] Embedded valkeylite startup failed: %s", exc)
                    self._client = None
                    return None
            else:
                log.info("[valkey] Embedded valkeylite unsupported on current platform; skipping.")
                self._client = None
                return None

    def is_available(self) -> bool:
        client = self.get_client()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except Exception as exc:
            log.warning("[valkey] Ping check failed: %s", exc)
            return False

    def get_record(self, namespace: str, key: str = "global") -> dict[str, Any] | None:
        client = self.get_client()
        if client is None:
            return None
        vk_key = self._valkey_key(namespace, key)
        try:
            raw = client.get(vk_key)
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            loaded = json.loads(raw)
            if isinstance(loaded, dict) and "payload" in loaded:
                return loaded
            return None
        except Exception as exc:
            log.debug("[valkey] Read failed for %s: %s", vk_key, exc)
            return None

    def set_record(
        self,
        namespace: str,
        key: str,
        record: dict[str, Any],
        ttl: float,
    ) -> bool:
        client = self.get_client()
        if client is None:
            return False
        vk_key = self._valkey_key(namespace, key)
        try:
            valkey_ttl = max(int(ttl * 3), 3600)
            payload_str = json.dumps(record, ensure_ascii=False)
            client.set(vk_key, payload_str, ex=valkey_ttl)
            return True
        except Exception as exc:
            log.debug("[valkey] Store failed for %s: %s", vk_key, exc)
            return False

    def delete(self, namespace: str, key: str = "global") -> bool:
        client = self.get_client()
        if client is None:
            return False
        vk_key = self._valkey_key(namespace, key)
        try:
            client.delete(vk_key)
            return True
        except Exception as exc:
            log.debug("[valkey] Delete failed for %s: %s", vk_key, exc)
            return False

    def clear(self) -> None:
        client = self.get_client()
        if client is None:
            return
        try:
            keys = client.keys(f"{self.key_prefix}*")
            if keys:
                client.delete(*keys)
        except Exception as exc:
            log.debug("[valkey] Clear failed: %s", exc)

    def close(self) -> None:
        with self._lock:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            self._init_attempted = False


# ─────────────────────────────────────────────────────────────────────────────
# 5. Resilience / Fallback Pattern: FallbackCacheBackend
# ─────────────────────────────────────────────────────────────────────────────

class FallbackCacheBackend(CacheBackend):
    """
    Fallback Decorator / Resilient Adapter Pattern:
    Delegates cache operations to a primary backend (e.g. Valkey).
    If the primary is unavailable or encounters a runtime error, gracefully
    and seamlessly falls back to a secondary backend (e.g. File).
    """

    def __init__(self, primary: CacheBackend, fallback: CacheBackend):
        self.primary = primary
        self.fallback = fallback

    @property
    def name(self) -> str:
        return f"{self.primary.name}+Fallback({self.fallback.name})"

    def is_available(self) -> bool:
        return self.primary.is_available() or self.fallback.is_available()

    def get_record(self, namespace: str, key: str = "global") -> dict[str, Any] | None:
        if self.primary.is_available():
            try:
                rec = self.primary.get_record(namespace, key)
                if rec is not None:
                    return rec
            except Exception as exc:
                log.warning("[%s] Primary backend read failed, falling back to %s: %s",
                            self.name, self.fallback.name, exc)
        return self.fallback.get_record(namespace, key)

    def set_record(
        self,
        namespace: str,
        key: str,
        record: dict[str, Any],
        ttl: float,
    ) -> bool:
        # Always persist to fallback for durable fail-safe storage
        fb_ok = self.fallback.set_record(namespace, key, record, ttl)
        if self.primary.is_available():
            try:
                self.primary.set_record(namespace, key, record, ttl)
            except Exception as exc:
                log.warning("[%s] Primary backend write failed; fallback succeeded: %s",
                            self.name, exc)
        return fb_ok

    def delete(self, namespace: str, key: str = "global") -> bool:
        if self.primary.is_available():
            try:
                self.primary.delete(namespace, key)
            except Exception:
                pass
        return self.fallback.delete(namespace, key)

    def clear(self) -> None:
        if self.primary.is_available():
            try:
                self.primary.clear()
            except Exception:
                pass
        self.fallback.clear()

    def close(self) -> None:
        try:
            self.primary.close()
        except Exception:
            pass
        self.fallback.close()


# ─────────────────────────────────────────────────────────────────────────────
# 6. Composite Pattern: TieredCacheBackend
# ─────────────────────────────────────────────────────────────────────────────

class TieredCacheBackend(CacheBackend):
    """
    Composite Pattern: Multi-level cache hierarchy (e.g. L1 Memory -> L2 Valkey / Disk).
    Reads through tiers in order, back-populating earlier tiers on cache hits.
    Writes through all active tiers.
    """

    def __init__(self, tiers: list[CacheBackend]):
        self.tiers = tiers

    @property
    def name(self) -> str:
        return " -> ".join(t.name for t in self.tiers)

    def is_available(self) -> bool:
        return any(t.is_available() for t in self.tiers)

    def get_record(self, namespace: str, key: str = "global") -> dict[str, Any] | None:
        for idx, tier in enumerate(self.tiers):
            if not tier.is_available():
                continue
            try:
                record = tier.get_record(namespace, key)
            except Exception as exc:
                log.debug("[%s] Error in tier %s: %s", self.name, tier.name, exc)
                continue
            if record is not None:
                # Back-populate earlier tiers
                for prev_tier in self.tiers[:idx]:
                    if prev_tier.is_available():
                        try:
                            prev_tier.set_record(namespace, key, record, ttl=CACHE_TTL_SECONDS)
                        except Exception:
                            pass
                return record
        return None

    def set_record(
        self,
        namespace: str,
        key: str,
        record: dict[str, Any],
        ttl: float,
    ) -> bool:
        ok = False
        for tier in self.tiers:
            if tier.is_available():
                try:
                    tier_ok = tier.set_record(namespace, key, record, ttl)
                    ok = ok or tier_ok
                except Exception as exc:
                    log.debug("[%s] Error setting in tier %s: %s", self.name, tier.name, exc)
        return ok

    def delete(self, namespace: str, key: str = "global") -> bool:
        ok = False
        for tier in self.tiers:
            if tier.is_available():
                try:
                    ok = tier.delete(namespace, key) or ok
                except Exception:
                    pass
        return ok

    def clear(self) -> None:
        for tier in self.tiers:
            try:
                tier.clear()
            except Exception:
                pass

    def close(self) -> None:
        for tier in self.tiers:
            try:
                tier.close()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# 7. Factory Pattern: CacheBackendFactory
# ─────────────────────────────────────────────────────────────────────────────

class CacheBackendFactory:
    """
    Factory Pattern: Configures and constructs the pluggable cache hierarchy
    based on feature flags, platform support, and environment variables.
    """

    @classmethod
    def should_enable_valkey(cls) -> bool:
        """
        Evaluate if Valkey caching should be enabled:
        - If ENABLE_VALKEY_CACHE or USE_EMBEDDED_VALKEY env var is explicitly configured, honor it.
        - Otherwise, consult feature flag 'valkey_cache'.
        - Falls back to is_valkey_supported_platform().
        """
        env_val = os.environ.get("ENABLE_VALKEY_CACHE") or os.environ.get("USE_EMBEDDED_VALKEY")
        if env_val is not None:
            return env_val.lower() in ("1", "true", "yes", "on")

        try:
            from app.services.feature_flags import feature_enabled
            return feature_enabled("valkey_cache")
        except Exception:
            return is_valkey_supported_platform()


    @classmethod
    def create_backend(
        cls,
        prefer_valkey: bool | None = None,
        valkey_client: Any | None = None,
        memory_store: dict[str, dict[str, Any]] | None = None,
        cache_directory: Path | None = None,
    ) -> CacheBackend:
        memory_tier = MemoryCacheBackend(store=memory_store)
        file_tier = FileCacheBackend(cache_dir=cache_directory)

        should_valkey = cls.should_enable_valkey() if prefer_valkey is None else prefer_valkey

        if should_valkey:
            valkey_tier = ValkeyCacheBackend(client=valkey_client)
            if valkey_tier.is_available():
                log.info("[cache-factory] Valkey cache initialized with file fallback")
                fallback_tier = FallbackCacheBackend(primary=valkey_tier, fallback=file_tier)
                return TieredCacheBackend([memory_tier, fallback_tier])
            else:
                log.info("[cache-factory] Valkey unavailable; using Memory + FileCache backend")

        return TieredCacheBackend([memory_tier, file_tier])
