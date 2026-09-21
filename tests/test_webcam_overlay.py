from app.services import webcam_overlay


def test_normalize_overpass_keeps_http_webcam_urls():
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": 47.0,
                "lon": 8.0,
                "tags": {"name": "Alpine cam", "webcam:url": "https://example.com/cam"},
            },
            {
                "type": "node",
                "id": 2,
                "lat": 46.0,
                "lon": 7.0,
                "tags": {"name": "Bad", "webcam:url": "javascript:alert(1)"},
            },
        ]
    }
    rows = webcam_overlay.normalize_overpass(payload)
    assert len(rows) == 1
    assert rows[0]["url"] == "https://example.com/cam"
    assert rows[0]["source"] == "OpenStreetMap"


def test_webcams_api_uses_service(client, monkeypatch):
    monkeypatch.setattr(webcam_overlay, "list_webcams", lambda bbox=None: {
        "count": 1,
        "webcams": [{
            "name": "Kīlauea summit webcams",
            "url": "https://www.usgs.gov/volcanoes/kilauea/webcams",
            "lat": 19.4,
            "lng": -155.2,
            "source": "USGS",
        }],
        "sources": webcam_overlay.SOURCES,
    })
    response = client.get("/api/webcams")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["webcams"][0]["url"].startswith("https://")
    assert any(src["name"] == "OpenStreetMap" for src in payload["sources"])


def test_tracker_has_webcams_checkbox(client):
    from io import BytesIO

    from app.services.demo_tle import demo_tle_text

    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?ids=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="webcams-overlay"' in html
    assert "toggleWebcamsOverlay" in js
    assert 'target="_blank"' in js
    assert "OpenStreetMap" in js
    assert any(cam["id"] == "ingv-etna" for cam in webcam_overlay.PUBLIC_CAMS)
    assert any(cam["id"] == "geonet-nz" for cam in webcam_overlay.PUBLIC_CAMS)
    assert webcam_overlay.WORLD_HUBS
