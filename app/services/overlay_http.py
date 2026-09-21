"""HTTP helper for overlay providers: skip hosts in cooldown, honor 429 / Retry-After."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

THROTTLE_STATUSES = {429, 502, 503, 504}
MIN_BACKOFF_SECONDS = 15.0
MAX_BACKOFF_SECONDS = 300.0
DEFAULT_HEADERS = {
    "User-Agent": "SatTrack/1.0 (educational; +https://github.com/sethusrinivasan/satellite-tracker)",
}

_throttle: dict[str, dict[str, Any]] = {}
_throttle_guard = threading.Lock()


def host_from_url(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def remaining_backoff(host_or_url: str) -> float:
    host = host_or_url if "://" not in host_or_url else host_from_url(host_or_url)
    if not host:
        return 0.0
    with _throttle_guard:
        record = _throttle.get(host) or {}
        until = float(record.get("until") or 0)
    return max(0.0, until - time.time())


def parse_retry_after(response: requests.Response) -> float | None:
    raw = (response.headers or {}).get("Retry-After")
    if not raw:
        return None
    text = str(raw).strip()
    try:
        return max(1.0, min(MAX_BACKOFF_SECONDS, float(text)))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(text)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(1.0, min(MAX_BACKOFF_SECONDS, (when - datetime.now(timezone.utc)).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return None


def note_success(host_or_url: str) -> None:
    host = host_or_url if "://" not in host_or_url else host_from_url(host_or_url)
    if not host:
        return
    with _throttle_guard:
        record = _throttle.get(host)
        if record:
            record["failures"] = 0
            record["until"] = 0


def note_throttle(host_or_url: str, retry_after: float | None = None, status: Any = None) -> float:
    host = host_or_url if "://" not in host_or_url else host_from_url(host_or_url)
    if not host:
        return 0.0
    with _throttle_guard:
        record = _throttle.setdefault(host, {"failures": 0, "until": 0.0})
        record["failures"] = int(record.get("failures") or 0) + 1
        failures = record["failures"]
        if retry_after is not None and retry_after > 0:
            delay = min(MAX_BACKOFF_SECONDS, float(retry_after))
        else:
            delay = min(MAX_BACKOFF_SECONDS, MIN_BACKOFF_SECONDS * (2 ** max(0, failures - 1)))
        record["until"] = time.time() + delay
    log.warning(
        "[overlay-http] %s cooling down %.0fs (status=%s failures=%s)",
        host,
        delay,
        status,
        failures,
    )
    return delay


def reset_runtime_state() -> None:
    with _throttle_guard:
        _throttle.clear()


def request(
    method: str,
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: Any = None,
    source: str = "overlay",
    throttle_timeouts: bool = True,
    allow_statuses: set[int] | None = None,
) -> requests.Response | None:
    host = host_from_url(url)
    wait = remaining_backoff(host)
    if wait > 0:
        log.info("[%s] Skip %s — backoff %.0fs remaining", source, host, wait)
        return None
    merged = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        response = requests.request(
            method,
            url,
            timeout=timeout,
            headers=merged,
            params=params,
            data=data,
        )
    except requests.Timeout:
        if throttle_timeouts:
            note_throttle(host, retry_after=MIN_BACKOFF_SECONDS, status="timeout")
        log.warning("[%s] Timeout %s", source, url)
        return None
    except Exception as exc:
        log.warning("[%s] %s failed: %s", source, url, exc)
        return None
    if response.status_code in THROTTLE_STATUSES:
        note_throttle(host, retry_after=parse_retry_after(response), status=response.status_code)
        return None
    if allow_statuses and response.status_code in allow_statuses:
        note_success(host)
        return response
    if not response.ok:
        log.warning("[%s] %s HTTP %s", source, url, response.status_code)
        return None
    note_success(host)
    return response


def get_json(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    source: str = "overlay",
    throttle_timeouts: bool = True,
) -> Any | None:
    response = request(
        "GET",
        url,
        timeout=timeout,
        headers=headers,
        params=params,
        source=source,
        throttle_timeouts=throttle_timeouts,
    )
    if response is None:
        return None
    try:
        return response.json()
    except ValueError as exc:
        log.warning("[%s] Invalid JSON from %s: %s", source, url, exc)
        return None


def get_text(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    source: str = "overlay",
) -> str | None:
    response = request(
        "GET",
        url,
        timeout=timeout,
        headers=headers,
        params=params,
        source=source,
    )
    if response is None:
        return None
    return response.text


def post_json(
    url: str,
    *,
    timeout: float,
    headers: dict[str, str] | None = None,
    data: Any = None,
    source: str = "overlay",
) -> Any | None:
    response = request(
        "POST",
        url,
        timeout=timeout,
        headers=headers,
        data=data,
        source=source,
    )
    if response is None:
        return None
    try:
        return response.json()
    except ValueError as exc:
        log.warning("[%s] Invalid JSON from %s: %s", source, url, exc)
        return None
