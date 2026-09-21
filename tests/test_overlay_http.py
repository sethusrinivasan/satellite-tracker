from app.services import overlay_http


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"ok": True}
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def test_429_sets_backoff_and_skips_next_call(monkeypatch):
    calls = {"n": 0}

    def fake_request(*_args, **_kwargs):
        calls["n"] += 1
        return FakeResponse(status_code=429, headers={"Retry-After": "30"})

    monkeypatch.setattr(overlay_http.requests, "request", fake_request)
    assert overlay_http.get_json("https://example.test/feed", timeout=1, source="test") is None
    wait = overlay_http.remaining_backoff("example.test")
    assert 1 < wait <= 30
    assert overlay_http.get_json("https://example.test/other", timeout=1, source="test") is None
    assert calls["n"] == 1


def test_success_clears_failures(monkeypatch):
    overlay_http.note_throttle("ok.test", retry_after=1, status=429)
    monkeypatch.setattr(
        overlay_http.requests,
        "request",
        lambda *_args, **_kwargs: FakeResponse(),
    )
    overlay_http.note_success("ok.test")
    assert overlay_http.remaining_backoff("ok.test") == 0
    assert overlay_http.get_json("https://ok.test/v1", timeout=1, source="test") == {"ok": True}
