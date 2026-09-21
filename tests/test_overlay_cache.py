from app.services.overlay_cache import CACHE_TTL_SECONDS, get_or_set


def test_overlay_cache_ttl_is_one_minute():
    assert CACHE_TTL_SECONDS == 60


def test_shared_cache_fetches_once_for_later_users():
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return {"count": 2, "items": ["a", "b"]}

    first = get_or_set("news", loader)
    second = get_or_set("news", loader)
    assert first == second
    assert calls["n"] == 1


def test_expired_overlay_cache_refetches():
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return {"n": calls["n"]}

    import app.services.overlay_cache as overlay_cache

    get_or_set("flights", loader)
    path, _ = overlay_cache._paths("flights", "global")
    overlay_cache._write_record(path, {"n": 1}, now=0)
    third = get_or_set("flights", loader)
    assert third == {"n": 2}
    assert calls["n"] == 2


def test_world_events_uses_shared_cache(monkeypatch):
    from app.services import world_events

    hits = {"n": 0}

    def fake_load():
        hits["n"] += 1
        return [{"title": "Storm", "kind": "weather"}]

    monkeypatch.setattr(world_events, "_load_world_events", fake_load)
    first = world_events.list_world_events()
    second = world_events.list_world_events()
    assert first == second
    assert hits["n"] == 1
