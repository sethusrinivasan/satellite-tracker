from app.services import cloud_datacenters


def test_percentile_interpolation():
    assert cloud_datacenters.percentile([], 50) is None
    assert cloud_datacenters.percentile([10], 99) == 10
    assert cloud_datacenters.percentile([10, 20, 30, 40, 50], 50) == 30
    assert cloud_datacenters.percentile([10, 20, 30, 40, 50], 100) == 50


def test_ping_urls_are_https_and_color_coded():
    aws = cloud_datacenters.ping_url_for("aws", "us-west-2")
    azure = cloud_datacenters.ping_url_for("azure", "westus")
    gcp = cloud_datacenters.ping_url_for("gcp", "us-west1")
    assert aws.startswith("https://dynamodb.us-west-2.amazonaws.com/")
    assert azure.startswith("https://s8westus.blob.core.windows.net/")
    assert gcp.startswith("https://") and gcp.endswith("/api/ping")
    assert cloud_datacenters.PROVIDERS["aws"]["color"] == "#FF9900"
    assert cloud_datacenters.PROVIDERS["azure"]["color"] == "#0078D4"
    assert cloud_datacenters.PROVIDERS["gcp"]["color"] == "#34A853"
    providers = {row[0] for row in cloud_datacenters.REGIONS}
    assert providers == {"aws", "azure", "gcp"}


def test_cloud_datacenters_api_uses_service(client, monkeypatch):
    monkeypatch.setattr(cloud_datacenters, "list_cloud_datacenters", lambda: {
        "count": 1,
        "pending": False,
        "pinged": 1,
        "total": 1,
        "from_host": "test",
        "method": "HTTPS GET round-trip (not ICMP)",
        "datacenters": [{
            "provider": "aws",
            "provider_label": "AWS",
            "region": "us-west-2",
            "name": "US West (Oregon)",
            "city": "Boardman",
            "lat": 45.8,
            "lng": -119.7,
            "color": "#FF9900",
            "p50": 12.0,
            "p95": 18.0,
            "p99": 21.0,
        }],
        "sources": cloud_datacenters.SOURCES,
    })
    response = client.get("/api/cloud-datacenters")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["datacenters"][0]["p50"] == 12.0
    assert payload["datacenters"][0]["p99"] == 21.0
    assert any(src["name"] == "Amazon Web Services" for src in payload["sources"])


def test_tracker_has_cloud_dc_checkbox(client):
    from io import BytesIO

    from app.services.demo_tle import demo_tle_text

    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?ids=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="cloud-dc-overlay"' in html
    assert "toggleCloudDatacentersOverlay" in js
    assert "p50" in js and "p95" in js and "p99" in js
    assert "/api/cloud-datacenters" in js
    assert "data.pending" in js
    assert "overlayDebug" in js
    assert "overlayFetch" in js
    assert "applyOverlayProgress" in js


def test_http_rtt_counts_http_errors(monkeypatch):
    class _Resp:
        def close(self):
            return None

    monkeypatch.setattr(cloud_datacenters.requests, "get", lambda *args, **kwargs: _Resp())
    ms = cloud_datacenters.http_rtt_ms("https://example.com/missing")
    assert ms is not None
    assert ms >= 0.0


def test_ping_samples_retries_once_then_stops(monkeypatch):
    calls = {"n": 0}

    def fake(_url, timeout=4.0):
        calls["n"] += 1
        return None

    monkeypatch.setattr(cloud_datacenters, "http_rtt_ms", fake)
    assert cloud_datacenters.ping_samples("https://example.com/ping") == []
    assert calls["n"] == 2


def test_list_returns_pins_before_pings_finish(monkeypatch):
    cloud_datacenters._worker = None
    monkeypatch.setattr(cloud_datacenters, "ping_samples", lambda _url: (__import__("time").sleep(30) or [1.0]))
    started = __import__("time").time()
    payload = cloud_datacenters.list_cloud_datacenters()
    assert __import__("time").time() - started < 2
    assert payload["pending"] is True
    assert payload["datacenters"]
    assert payload["datacenters"][0]["lat"]
    assert payload["datacenters"][0]["p50"] is None
