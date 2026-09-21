from datetime import datetime, timezone

from app.services import city_temperature, world_events


def test_world_events_api_uses_cached_normalized_rows(client, monkeypatch):
    sample = [{
        "id": "eonet-storm",
        "title": "Severe Storm - Sample",
        "category": "Severe Storms",
        "lat": -20.1,
        "lng": 168.2,
        "time": datetime.now(timezone.utc).isoformat(),
        "source": "NASA EONET",
        "url": "https://eonet.gsfc.nasa.gov/",
    }]
    monkeypatch.setattr(world_events, "list_world_events", lambda: sample)
    monkeypatch.setattr(city_temperature, "list_city_temperatures", lambda force_refresh=False: {
        "count": 0,
        "as_of": None,
        "cities": [],
        "source": city_temperature.SOURCE,
    })
    response = client.get("/api/world-events")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["hours"] == 24
    assert payload["count"] == 1
    assert payload["events"][0]["title"] == "Severe Storm - Sample"
    assert payload["sources"][0]["name"] == "NASA EONET"
    assert payload["temperatures"] == []


def test_list_world_events_keeps_weather_and_quakes(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(world_events, "_fetch_json", lambda url, params=None: {
        "eonet": {
            "events": [
                {
                    "id": "EONET_1",
                    "title": "Wildfire - Test",
                    "link": "https://eonet.gsfc.nasa.gov/",
                    "categories": [{"id": "wildfires", "title": "Wildfires"}],
                    "geometry": [{"type": "Point", "date": now, "coordinates": [10.0, 20.0]}],
                },
                {
                    "id": "EONET_2",
                    "title": "Volcano - Test",
                    "link": "https://eonet.gsfc.nasa.gov/",
                    "categories": [{"id": "volcanoes", "title": "Volcanoes"}],
                    "geometry": [{"type": "Point", "date": now, "coordinates": [11.0, 21.0]}],
                },
            ],
        },
        "usgs": {
            "features": [{
                "id": "us1000",
                "properties": {
                    "mag": 6.4,
                    "title": "M 6.4 - Test",
                    "time": datetime.now(timezone.utc).timestamp() * 1000,
                    "url": "https://earthquake.usgs.gov/",
                },
                "geometry": {"coordinates": [12.0, -5.0, 10]},
            }],
        },
    }["eonet" if "eonet" in url else "usgs"])
    events = world_events.list_world_events(force_refresh=True)
    titles = {row["title"] for row in events}
    assert "Wildfire - Test" in titles
    assert "Volcano - Test" not in titles
    quake = next(row for row in events if row["kind"] == "earthquake")
    assert quake["magnitude"] == 6.4
    assert quake["title"] == "M 6.4 - Test"


def test_tracker_page_has_weather_climate_checkbox(client):
    from io import BytesIO

    from app.services.demo_tle import demo_tle_text

    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?view=tracker&sats=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="world-events-overlay"' in html
    assert "Weather &amp; quakes" in html
    assert "toggleWorldEventsOverlay" in js
    assert "earthquakeMarkerRadius" in js
    assert "earthquakeMarkerColor" in js
    assert "temperaturePopupHtml" in js
    assert "data.pending" in js
    assert "applyOverlayProgress" in js
    assert "scheduleOverlayPoll" in js
    assert "Open-Meteo" in js
    assert "['7d', changes['7d']]" in js or "changes['7d']" in js
    assert "changes['90d']" in js
    assert "changes['1y']" in js
    assert 'id="overlay-loading-chip"' in html
    assert "setOverlayLoading" in js
    assert "overlay-loading-chip" in js
