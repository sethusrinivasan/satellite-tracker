def test_posthog_snippet_absent_without_key(client):
    html = client.get("/report").get_data(as_text=True)
    assert "posthog.init" not in html
    assert "us.i.posthog.com" not in html


def test_posthog_snippet_renders_when_key_configured(app, client):
    app.config["TESTING"] = False
    app.config["POSTHOG_PROJECT_API_KEY"] = "phc_test_project_key"
    app.config["POSTHOG_HOST"] = "https://eu.i.posthog.com"
    app.config["POSTHOG_SESSION_REPLAY"] = False
    html = client.get("/report").get_data(as_text=True)
    assert "posthog.init" in html
    assert "phc_test_project_key" in html
    assert "https://eu.i.posthog.com" in html
    assert "disable_session_recording: true" in html
    assert "identified_only" in html


def test_posthog_snippet_stays_off_in_testing_even_with_key(app, client):
    app.config["TESTING"] = True
    app.config["POSTHOG_PROJECT_API_KEY"] = "phc_test_project_key"
    html = client.get("/report").get_data(as_text=True)
    assert "posthog.init" not in html
