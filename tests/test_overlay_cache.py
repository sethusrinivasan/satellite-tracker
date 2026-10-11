from app.services.overlay_cache import CACHE_TTL_SECONDS, NAMESPACE_TTL, get_or_set, wait_refresh


def test_overlay_cache_ttl_is_one_minute_by_default():
    assert CACHE_TTL_SECONDS == 60
    assert NAMESPACE_TTL["city-temps"] >= 3600
    assert NAMESPACE_TTL["flights"] <= 60


def test_shared_cache_fetches_once_for_later_users():
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return {"count": 2, "items": ["a", "b"]}

    first = get_or_set("news", loader)
    second = get_or_set("news", loader)
    assert first == second
    assert calls["n"] == 1


def test_expired_overlay_cache_serves_stale_then_refreshes():
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return {"n": calls["n"]}

    import app.services.overlay_cache as overlay_cache

    get_or_set("flights", loader)
    path, _ = overlay_cache._paths("flights", "global")
    overlay_cache._write_record(path, {"n": 1}, now=0, ttl=60)
    second = get_or_set("flights", loader)
    assert second == {"n": 1}
    assert wait_refresh("flights", timeout=2)
    third = get_or_set("flights", loader)
    assert third == {"n": 2}
    assert calls["n"] == 2


def test_skeleton_returns_immediately_without_waiting_for_loader():
    import threading

    ready = threading.Event()

    def loader():
        ready.wait(2)
        return {"ready": True}

    first = get_or_set("markets", loader, skeleton={"ready": False})
    assert first == {"ready": False}
    ready.set()
    assert wait_refresh("markets", timeout=2)
    second = get_or_set("markets", loader)
    assert second == {"ready": True}


def test_world_events_uses_shared_cache(monkeypatch):
    from app.services import world_events

    hits = {"n": 0}

    def fake_load():
        hits["n"] += 1
        return [{"title": "Storm", "kind": "weather"}]

    monkeypatch.setattr(world_events, "_load_world_events", fake_load)
    first = world_events.list_world_events(force_refresh=True)
    second = world_events.list_world_events()
    assert first == second
    assert hits["n"] == 1


def test_valkey_enabled_by_default_on_supported_platform(monkeypatch):
    import sys
    import app.services.overlay_cache as overlay_cache
    from app.services.cache_backends import is_valkey_supported_platform, CacheBackendFactory

    if sys.platform == "win32":
        return

    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("ENABLE_VALKEY_CACHE", raising=False)
    overlay_cache.reset_runtime_state()

    assert is_valkey_supported_platform() is True
    assert CacheBackendFactory.should_enable_valkey() is True


def test_valkey_disabled_when_flag_off_falls_back_to_local_cache(monkeypatch):
    import app.services.overlay_cache as overlay_cache

    monkeypatch.setenv("ENABLE_VALKEY_CACHE", "0")
    overlay_cache.reset_runtime_state()

    client = overlay_cache.get_valkey_client()
    assert client is None

    # Verify fallback to local file + memory cache functions flawlessly
    overlay_cache.store("fallback_test", {"status": "ok"}, key="item1", ttl=60)
    fetched = overlay_cache.get_fresh("fallback_test", key="item1")
    assert fetched == {"status": "ok"}


def test_valkey_client_windows_guard(monkeypatch):
    import sys
    import app.services.overlay_cache as overlay_cache
    from app.services.cache_backends import is_valkey_supported_platform

    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("ENABLE_VALKEY_CACHE", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    overlay_cache.reset_runtime_state()

    assert is_valkey_supported_platform() is False
    client = overlay_cache.get_valkey_client()
    assert client is None


def test_valkey_client_vercel_guard(monkeypatch):
    import app.services.overlay_cache as overlay_cache
    from app.services.cache_backends import is_valkey_supported_platform

    monkeypatch.delenv("VALKEY_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("ENABLE_VALKEY_CACHE", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    overlay_cache.reset_runtime_state()

    assert is_valkey_supported_platform() is False
    client = overlay_cache.get_valkey_client()
    assert client is None


def test_valkey_cache_store_and_get_integration(monkeypatch):
    import json
    import app.services.overlay_cache as overlay_cache

    fake_store = {}

    class MockValkey:
        def get(self, k):
            return fake_store.get(k)

        def set(self, k, v, ex=None):
            fake_store[k] = v.encode("utf-8") if isinstance(v, str) else v

        def delete(self, *keys):
            for k in keys:
                fake_store.pop(k, None)

        def ping(self):
            return True

        def close(self):
            pass

    mock_client = MockValkey()
    monkeypatch.setattr(overlay_cache, "_valkey_client", mock_client)
    monkeypatch.setattr(overlay_cache, "_valkey_init_attempted", True)
    overlay_cache._memory.clear()

    test_payload = {"source": "valkey_test", "count": 42}
    overlay_cache.store("news", test_payload, key="vk_item", ttl=120)

    # Check that Valkey received the entry
    vk_key = "sattrack:overlay:news::vk_item"
    assert vk_key in fake_store
    stored_rec = json.loads(fake_store[vk_key])
    assert stored_rec["payload"] == test_payload

    # Clear memory cache to ensure get_fresh fetches from Valkey
    overlay_cache._memory.clear()
    fetched = overlay_cache.get_fresh("news", key="vk_item")
    assert fetched == test_payload

    # Test get_stale fetches from Valkey
    overlay_cache._memory.clear()
    stale = overlay_cache.get_stale("news", key="vk_item")
    assert stale == test_payload


def test_valkey_fallback_on_runtime_error(monkeypatch):
    import app.services.overlay_cache as overlay_cache

    class BrokenValkey:
        def get(self, k):
            raise ConnectionError("Valkey network partition")

        def set(self, k, v, ex=None):
            raise ConnectionError("Valkey write timeout")

        def ping(self):
            return True

        def close(self):
            pass

    broken_client = BrokenValkey()
    monkeypatch.setattr(overlay_cache, "_valkey_client", broken_client)
    monkeypatch.setattr(overlay_cache, "_valkey_init_attempted", True)
    overlay_cache._memory.clear()

    # Store must not raise an exception; it must fall back to disk
    overlay_cache.store("health", {"healthy": True}, key="service_a", ttl=60)

    # Clear memory to test reading through the broken Valkey
    overlay_cache._memory.clear()
    # Reading must not raise; it falls back to FileCache
    fetched = overlay_cache.get_fresh("health", key="service_a")
    assert fetched == {"healthy": True}


def test_pluggable_cache_design_patterns(tmp_path):
    from app.services.cache_backends import (
        MemoryCacheBackend,
        FileCacheBackend,
        ValkeyCacheBackend,
        FallbackCacheBackend,
        TieredCacheBackend,
        CacheBackendFactory,
    )

    # 1. Strategy Pattern: MemoryCacheBackend
    mem = MemoryCacheBackend()
    assert mem.name == "MemoryCache"
    assert mem.is_available() is True
    rec = {"expires": 9999999999.0, "stored": 1.0, "payload": {"foo": "bar"}}
    assert mem.set_record("test_ns", "key1", rec, ttl=60) is True
    assert mem.get_record("test_ns", "key1")["payload"] == {"foo": "bar"}
    assert mem.delete("test_ns", "key1") is True
    assert mem.get_record("test_ns", "key1") is None

    # 2. Strategy Pattern: FileCacheBackend
    file_cache = FileCacheBackend(cache_dir=tmp_path / "custom_cache")
    assert file_cache.name == "FileCache"
    assert file_cache.is_available() is True
    assert file_cache.set_record("test_ns", "key2", rec, ttl=60) is True
    assert file_cache.get_record("test_ns", "key2")["payload"] == {"foo": "bar"}

    # 3. Composite / Tiered Pattern: TieredCacheBackend
    tiered = TieredCacheBackend([mem, file_cache])
    assert tiered.is_available() is True
    # Read from file_cache, backpopulates mem
    fetched_tiered = tiered.get_record("test_ns", "key2")
    assert fetched_tiered["payload"] == {"foo": "bar"}
    assert mem.get_record("test_ns", "key2")["payload"] == {"foo": "bar"}

    # 4. Fallback Pattern: FallbackCacheBackend
    class MockFailingBackend(MemoryCacheBackend):
        def get_record(self, ns, key="global"):
            raise RuntimeError("Primary crashed")

        def set_record(self, ns, key, record, ttl):
            raise RuntimeError("Primary write failed")

    failing = MockFailingBackend()
    fallback = FallbackCacheBackend(primary=failing, fallback=file_cache)
    assert fallback.is_available() is True
    # Should catch RuntimeError and get from fallback (file_cache)
    assert fallback.get_record("test_ns", "key2")["payload"] == {"foo": "bar"}

    # 5. Factory Pattern: CacheBackendFactory
    backend_valkey_off = CacheBackendFactory.create_backend(
        prefer_valkey=False,
        cache_directory=tmp_path / "factory_cache"
    )
    assert isinstance(backend_valkey_off, TieredCacheBackend)
    assert len(backend_valkey_off.tiers) == 2
    assert backend_valkey_off.tiers[0].name == "MemoryCache"
    assert backend_valkey_off.tiers[1].name == "FileCache"


def test_valkey_embedded_lifecycle_if_available(monkeypatch):
    import sys
    import app.services.overlay_cache as overlay_cache

    if sys.platform == "win32":
        return

    try:
        import valkeylite
    except ImportError:
        return

    monkeypatch.setenv("ENABLE_VALKEY_CACHE", "1")
    overlay_cache.reset_runtime_state()

    client = overlay_cache.get_valkey_client()
    if client is not None:
        try:
            assert client.ping() is True
            overlay_cache.store("markets", {"index": "SPX", "price": 5000}, key="live", ttl=60)
            overlay_cache._memory.clear()
            fetched = overlay_cache.get_fresh("markets", key="live")
            assert fetched == {"index": "SPX", "price": 5000}
        finally:
            overlay_cache.reset_runtime_state()


def test_use_embedded_valkey_alias(monkeypatch):
    import app.services.overlay_cache as overlay_cache
    from app.services.cache_backends import CacheBackendFactory
    from app.services.feature_flags import _defaults

    monkeypatch.delenv("ENABLE_VALKEY_CACHE", raising=False)
    monkeypatch.setenv("USE_EMBEDDED_VALKEY", "0")
    assert CacheBackendFactory.should_enable_valkey() is False
    assert _defaults()["valkey_cache"] is False

    monkeypatch.setenv("USE_EMBEDDED_VALKEY", "1")
    assert CacheBackendFactory.should_enable_valkey() is True
    assert _defaults()["valkey_cache"] is True


def test_file_lock_windows_fallback_without_fcntl(monkeypatch, tmp_path):
    import builtins
    import app.services.overlay_cache as overlay_cache

    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fcntl":
            raise ModuleNotFoundError("No module named 'fcntl' (simulated Windows environment)")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    lock_file = tmp_path / "test.lock"
    handle = overlay_cache._file_lock(lock_file)
    assert handle is not None
    assert not handle.closed
    overlay_cache._unlock(handle)
    assert handle.closed


