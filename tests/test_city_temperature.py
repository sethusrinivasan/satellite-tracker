from datetime import date, timedelta

from app.services import city_temperature


def test_million_cities_are_unique_and_over_one_million():
    cities = city_temperature._unique_cities()
    assert len(cities) >= 80
    assert all(city["pop_m"] >= 1 for city in cities)
    keys = {(city["name"], city["country"]) for city in cities}
    assert len(keys) == len(cities)
    assert all("lat" in city and "lng" in city for city in cities)


def test_parse_daily_points_skips_nulls():
    points = city_temperature.parse_daily_points({
        "time": ["2026-09-01", "2026-09-02", "2026-09-03"],
        "temperature_2m_mean": [10.0, None, 12.5],
    })
    assert points == [("2026-09-01", 10.0), ("2026-09-03", 12.5)]


def test_trends_from_points_include_requested_horizons():
    latest = date(2026, 9, 20)
    points = []
    samples = {0: 20.0, 7: 18.0, 30: 16.0, 90: 12.0, 365: 19.0}
    for offset, temp in samples.items():
        points.append(((latest - timedelta(days=offset)).isoformat(), temp))
    points.sort()
    quote = city_temperature.trends_from_points(points)
    assert quote["as_of"] == latest.isoformat()
    assert quote["temp_c"] == 20.0
    assert set(quote["changes"]) == {"7d", "30d", "90d", "1y"}
    assert quote["changes"]["7d"] == 2.0
    assert quote["changes"]["30d"] == 4.0
    assert quote["changes"]["90d"] == 8.0
    assert quote["changes"]["1y"] == 1.0


def test_trends_from_empty_points():
    quote = city_temperature.trends_from_points([])
    assert quote["temp_c"] is None
    assert all(value is None for value in quote["changes"].values())


def test_warmer_seven_day_change_is_red():
    assert city_temperature._pin_color(2.4) == "#ef4444"
    assert city_temperature._pin_color(-2.4) == "#1d4ed8"
    assert city_temperature._pin_color(0.1) == "#94a3b8"


def test_list_city_temperatures_uses_shared_cache(monkeypatch):
    calls = {"n": 0}

    def fake_fetch(cities):
        calls["n"] += 1
        return [{
            "daily": {
                "time": ["2026-09-11", "2026-09-18"],
                "temperature_2m_mean": [18.0, 20.0],
            }
        } for _ in cities]

    monkeypatch.setattr(city_temperature, "MILLION_CITIES", [
        {"name": "Testville", "country": "Nowhere", "lat": 1.0, "lng": 2.0, "pop_m": 1.2},
    ])
    monkeypatch.setattr(city_temperature, "fetch_city_archive", fake_fetch)
    first = city_temperature.list_city_temperatures(force_refresh=True)
    second = city_temperature.list_city_temperatures()
    assert first["cities"][0]["name"] == "Testville"
    assert first["cities"][0]["temp_c"] == 20.0
    assert first["cities"][0]["changes"]["7d"] == 2.0
    assert second["cities"][0]["temp_c"] == 20.0
    assert calls["n"] == 1


def test_world_events_api_includes_city_temperatures(client, monkeypatch):
    from app.services import world_events

    monkeypatch.setattr(world_events, "list_world_events", lambda force_refresh=False: [{
        "id": "eonet-storm",
        "title": "Severe Storm - Sample",
        "category": "Severe Storms",
        "lat": -20.1,
        "lng": 168.2,
        "source": "NASA EONET",
    }])
    monkeypatch.setattr(city_temperature, "list_city_temperatures", lambda force_refresh=False: {
        "count": 1,
        "as_of": "2026-09-18",
        "cities": [{
            "name": "Tokyo",
            "country": "Japan",
            "lat": 35.67,
            "lng": 139.65,
            "pop_m": 37.4,
            "temp_c": 21.6,
            "changes": {"7d": 1.2, "30d": -0.4, "90d": 4.1, "1y": -0.8},
            "color": "#fb923c",
        }],
        "source": city_temperature.SOURCE,
    })
    response = client.get("/api/world-events")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["temperature_as_of"] == "2026-09-18"
    assert payload["temperatures"][0]["name"] == "Tokyo"
    assert set(payload["temperatures"][0]["changes"]) >= {"7d", "30d", "90d", "1y"}
    assert any(src["name"] == "Open-Meteo" for src in payload["sources"])
    assert any(src["name"] == "NASA EONET" for src in payload["sources"])
