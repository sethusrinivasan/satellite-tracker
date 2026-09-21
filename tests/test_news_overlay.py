from app.services import news_overlay


def test_articles_from_html_keeps_http_links():
    html = (
        '<b>Kyiv</b><br>'
        '<a href="https://example.com/story-one">A very long highlighted headline that should be shortened for the tooltip display window</a>'
        '<a href="javascript:alert(1)">bad</a>'
        '<a href="https://example.com/story-two">Second title</a>'
    )
    articles = news_overlay.articles_from_html(html)
    assert len(articles) == 2
    assert articles[0]["url"] == "https://example.com/story-one"
    assert articles[0]["title"].endswith("…")
    assert "javascript" not in articles[0]["url"]


def test_normalize_gdacs_uses_report_url():
    payload = {
        "features": [{
            "geometry": {"type": "Point", "coordinates": [10.8, 48.0]},
            "properties": {
                "eventtype": "DR",
                "eventid": 1,
                "name": "Drought in Europe",
                "country": "Germany",
                "url": {"report": "https://www.gdacs.org/report.aspx?eventid=1"},
            },
        }]
    }
    rows = news_overlay.normalize_gdacs(payload)
    assert len(rows) == 1
    assert rows[0]["url"].startswith("https://www.gdacs.org/")
    assert rows[0]["source"] == "GDACS"


def test_normalize_geojson_requires_article_link():
    payload = {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [30.5, 50.4]},
                "properties": {
                    "name": "Kyiv",
                    "html": '<a href="https://news.example/kyiv">Strike reported near Kyiv</a>',
                },
            },
            {
                "geometry": {"type": "Point", "coordinates": [10.0, 20.0]},
                "properties": {"name": "Nowhere", "html": ""},
            },
        ]
    }
    rows = news_overlay.normalize_geojson(payload)
    assert len(rows) == 1
    assert rows[0]["title"] == "Strike reported near Kyiv"
    assert rows[0]["url"] == "https://news.example/kyiv"


def test_geo_news_api_uses_service(client, monkeypatch):
    monkeypatch.setattr(news_overlay, "list_geo_news", lambda: {
        "count": 1,
        "hours": 24,
        "news": [{"title": "Sample", "url": "https://example.com/a", "lat": 1.0, "lng": 2.0}],
        "source": news_overlay.SOURCE,
    })
    response = client.get("/api/geo-news")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["source"]["name"] == "GDACS"
    assert payload["news"][0]["url"].startswith("https://")


def test_tracker_has_news_checkbox(client):
    from io import BytesIO

    from app.services.demo_tle import demo_tle_text

    client.post(
        "/upload",
        data={"file": (BytesIO(demo_tle_text().encode("utf-8")), "sample.tle")},
        content_type="multipart/form-data",
    )
    html = client.get("/tracker?ids=25544").get_data(as_text=True)
    js = client.get("/static/js/tracker.js").get_data(as_text=True)
    assert 'id="news-overlay"' in html
    assert "toggleNewsOverlay" in js
    assert 'target="_blank"' in js
    assert "gdacs.org" in js
    assert "wikipedia.org" in js
