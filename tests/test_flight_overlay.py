from app.services import flight_overlay


def test_normalize_states_keeps_airborne_only():
    payload = {
        "time": 1720000000,
        "states": [
            ["abc123", "UAL1  ", "United States", None, None, -74.0, 40.7, 10000, False, 250, 90, 0, None, 10000, None, False, 0],
            ["gnd1", "N123", "United States", None, None, -74.1, 40.6, 0, True, 0, 0, 0, None, 0, None, False, 0],
            ["bad", "XX", "Nowhere", None, None, None, None, None, False, None, None, None, None, None, None, False, 0],
        ],
    }
    flights, observed = flight_overlay.normalize_states(payload)
    assert observed is not None
    assert len(flights) == 1
    assert flights[0]["callsign"] == "UAL1"
    assert flights[0]["source"] == "The OpenSky Network"


def test_flights_api_uses_service(client, monkeypatch):
    monkeypatch.setattr(flight_overlay, "list_flights", lambda bbox=None: {
        "count": 1,
        "time": "2026-09-20T00:00:00+00:00",
        "flights": [{"icao24": "abc", "callsign": "TEST1", "lat": 1.0, "lng": 2.0}],
        "source": flight_overlay.SOURCE,
    })
    response = client.get("/api/flights")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["source"]["name"] == "The OpenSky Network"


def test_tracker_has_flights_checkbox(client):
    from io import BytesIO

    from app.services.demo_tle import demo_tle_text

    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?ids=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="flights-overlay"' in html
    assert "toggleFlightsOverlay" in js
    assert "OpenSky Network" in js
    assert "origin_label" in js
    assert "destination_label" in js
    assert "status_label" in js


def test_enrich_flight_adds_route_and_status():
    flight = {
        "callsign": "UAL1",
        "icao24": "abc123",
        "lat": 40.7,
        "lng": -74.0,
        "velocity_ms": 220,
        "origin_country": "United States",
    }
    routes = {
        "UAL1": {
            "origin": {"iata": "JFK", "city": "New York", "lat": 40.64, "lng": -73.78},
            "destination": {"iata": "LHR", "city": "London", "lat": 51.47, "lng": -0.45},
        }
    }
    recent = {"icao": {}, "callsign": {"UAL1": {"first_seen": 1_720_000_000.0}}}
    enriched = flight_overlay.enrich_flight(flight, routes, recent, now=1_720_000_000.0 + 3600)
    assert enriched["origin_label"] == "JFK · New York"
    assert enriched["destination_label"] == "LHR · London"
    assert enriched["status_label"] in {"On time", "Status unknown"} or "Delayed" in (enriched["status_label"] or "")
