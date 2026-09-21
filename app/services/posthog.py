"""Server-side PostHog capture for events that happen on redirects."""

from __future__ import annotations

import logging
from typing import Any

import requests
from flask import current_app, has_request_context, request

log = logging.getLogger(__name__)


def capture_event(event: str, properties: dict[str, Any] | None = None, distinct_id: str = "anonymous") -> None:
    """Fire-and-forget capture. No-op in tests or when no project key is set."""
    try:
        app = current_app
    except RuntimeError:
        return
    if app.config.get("TESTING"):
        return
    key = (app.config.get("POSTHOG_PROJECT_API_KEY") or "").strip()
    if not key:
        return
    host = (app.config.get("POSTHOG_HOST") or "https://us.i.posthog.com").rstrip("/")
    payload_props: dict[str, Any] = {
        "distinct_id": distinct_id,
        "$lib": "sattrack-flask",
        "app": "sattrack",
        "intended_for_production": False,
    }
    if has_request_context():
        payload_props["$current_url"] = request.url
        payload_props["path"] = request.path
        payload_props["host"] = request.host
    if properties:
        payload_props.update(properties)
    try:
        requests.post(
            f"{host}/capture/",
            json={"api_key": key, "event": event, "properties": payload_props},
            timeout=2,
        )
    except Exception as exc:
        log.warning("[posthog] capture failed for %s: %s", event, exc)
