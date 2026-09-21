from app.services import shipping_overlay


def test_digitraffic_requests_require_gzip():
    assert shipping_overlay.HEADERS.get("Accept-Encoding") == "gzip"


def test_ship_class_from_ais_type():
    assert shipping_overlay.ship_class(70) == "cargo"
    assert shipping_overlay.ship_class(80) == "tanker"
    assert shipping_overlay.ship_class(60) == "passenger"
    assert shipping_overlay.ship_class(33) == "fishing"


def test_normalize_locations_joins_vessel_meta():
    payload = {
        "features": [{
            "mmsi": 230001,
            "geometry": {"type": "Point", "coordinates": [24.96, 60.17]},
            "properties": {"mmsi": 230001, "sog": 12.5, "cog": 90, "heading": 88},
        }],
    }
    rows = shipping_overlay.normalize_locations(payload, {
        230001: {"name": "TEST SHIP", "callsign": "OJAA", "ship_type": 70},
    })
    assert len(rows) == 1
    assert rows[0]["name"] == "TEST SHIP"
    assert rows[0]["ship_class"] == "cargo"
    assert rows[0]["lat"] == 60.17
    assert rows[0]["lng"] == 24.96
    assert rows[0]["source"] == "Fintraffic Digitraffic"


def test_shipping_api_uses_service(client, monkeypatch):
    monkeypatch.setattr(shipping_overlay, "list_shipping", lambda: {
        "ship_count": 1,
        "ships": [{"mmsi": 1, "name": "A", "lat": 60.0, "lng": 25.0}],
        "sources": shipping_overlay.SOURCES,
    })
    response = client.get("/api/shipping")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ship_count"] == 1
    assert "routes" not in payload
    assert any(src["name"] == "Fintraffic Digitraffic" for src in payload["sources"])


def test_tracker_has_ships_checkbox(client):
    from io import BytesIO

    from app.services.demo_tle import demo_tle_text

    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?ids=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="ships-overlay"' in html
    assert "toggleShipsOverlay" in js
    assert "Digitraffic" in js
    assert "/api/shipping" in js
    assert "formatShipCoord" in js
    assert "trackShip" not in js
