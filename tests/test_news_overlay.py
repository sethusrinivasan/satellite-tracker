from datetime import datetime, timezone

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
                "datemodified": "2026-09-20T20:20:15",
                "url": {"report": "https://www.gdacs.org/report.aspx?eventid=1"},
            },
        }]
    }
    now = datetime(2026, 9, 21, 4, 0, tzinfo=timezone.utc)
    rows = news_overlay.normalize_gdacs(payload, now=now)
    assert len(rows) == 1
    assert rows[0]["url"].startswith("https://www.gdacs.org/")
    assert rows[0]["source"] == "GDACS"
    assert rows[0]["license"] == "Public disaster alerts"
    assert rows[0]["geo_basis"] == "coordinates"


def test_normalize_gdacs_drops_stale_alerts():
    payload = {
        "features": [{
            "geometry": {"type": "Point", "coordinates": [10.8, 48.0]},
            "properties": {
                "eventtype": "DR",
                "eventid": 2,
                "name": "Old drought",
                "datemodified": "2026-09-01T00:00:00",
                "url": {"report": "https://www.gdacs.org/report.aspx?eventid=2"},
            },
        }]
    }
    now = datetime(2026, 9, 21, 4, 0, tzinfo=timezone.utc)
    assert news_overlay.normalize_gdacs(payload, now=now) == []


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


def test_locate_article_prefers_title_city_then_category_country():
    kyiv = news_overlay.locate_article("Aid flights reach Kyiv after overnight strikes")
    assert kyiv["label"] == "Kyiv"
    assert kyiv["kind"] == "city"
    assert kyiv["geo_basis"] == "title"

    bangladesh = news_overlay.locate_article(
        "How two elections reshaped the border",
        categories=["Citizen Media", "Bangladesh", "South Asia"],
    )
    assert bangladesh["label"] == "Bangladesh"
    assert bangladesh["geo_basis"] == "category"

    texas = news_overlay.locate_article("US: Man wounded in Texas after being shot by ICE agent")
    assert texas["label"] == "Texas"
    assert texas["geo_basis"] == "title"


def test_locate_article_uses_region_when_no_place_name():
    located = news_overlay.locate_article("Talks continue overnight", feed_region="Middle East")
    assert located["label"] == "Middle East"
    assert located["kind"] == "region"
    assert located["geo_basis"] == "region"


def test_pin_from_article_filters_24h_and_geocodes():
    now = datetime(2026, 9, 21, 4, 0, tzinfo=timezone.utc)
    source = news_overlay.UN_SOURCE
    fresh = news_overlay.pin_from_article(
        {
            "title": "Relief supplies arrive in Nepal after the quake",
            "url": "https://news.un.org/en/story/nepal",
            "summary": "UN teams in Kathmandu",
            "categories": [],
            "published": "Sun, 20 Sep 2026 12:00:00 +0000",
        },
        source,
        feed_id="un-news",
        now=now,
    )
    stale = news_overlay.pin_from_article(
        {
            "title": "Relief supplies arrive in Nepal after the quake",
            "url": "https://news.un.org/en/story/nepal-old",
            "published": "Sun, 01 Sep 2026 12:00:00 +0000",
        },
        source,
        feed_id="un-news",
        now=now,
    )
    assert fresh is not None
    assert fresh["region"] == "Nepal"
    assert fresh["source"] == "UN News"
    assert stale is None


def test_parse_feed_xml_reads_rss_and_atom():
    rss = """<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>Flooding in Kenya</title>
        <link>https://news.un.org/en/story/kenya</link>
        <pubDate>Sun, 20 Sep 2026 12:00:00 +0000</pubDate>
        <category>Kenya</category>
      </item>
    </channel></rss>
    """
    atom = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Nepal could recover sustainably</title>
        <link href="https://theconversation.com/nepal-291968"/>
        <published>2026-09-20T12:58:02Z</published>
        <summary>Hazard zones in Kathmandu</summary>
      </entry>
    </feed>
    """
    rss_rows = news_overlay.parse_feed_xml(rss)
    atom_rows = news_overlay.parse_feed_xml(atom)
    assert rss_rows[0]["url"] == "https://news.un.org/en/story/kenya"
    assert rss_rows[0]["categories"] == ["Kenya"]
    assert atom_rows[0]["url"] == "https://theconversation.com/nepal-291968"


def test_geo_news_api_uses_service(client, monkeypatch):
    monkeypatch.setattr(news_overlay, "list_geo_news", lambda: {
        "count": 1,
        "hours": 24,
        "news": [{"title": "Sample", "url": "https://example.com/a", "lat": 1.0, "lng": 2.0}],
        "source": news_overlay.SOURCE,
        "sources": news_overlay.SOURCES,
    })
    response = client.get("/api/geo-news")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["source"]["name"] == "GDACS"
    assert payload["news"][0]["url"].startswith("https://")
    assert {row["name"] for row in payload["sources"]} >= {
        "GDACS", "UN News", "Global Voices", "The Conversation", "Deutsche Welle",
    }


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
    assert "news.un.org" in js
    assert "globalvoices.org" in js
    assert "theconversation.com" in js
    assert "dw.com" in js
    assert "wikipedia.org" not in js
