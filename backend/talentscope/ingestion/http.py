"""HTTP access for network connectors, enforcing the SRS crawling rules (§8.4).

* Identifies TalentScope in the User-Agent, with a contact URL.
* Checks robots.txt before the first request to a host. robots.txt is a crawler rule,
  not permission; eligibility is decided separately by the source registry.
* One request at a time per host, at least ``min_interval`` seconds apart.
* Retries only transient failures (network errors, 5xx), with exponential backoff and
  jitter, and honours Retry-After on 429 up to a ceiling.
* 401/403 and robots disallow raise ``AccessDenied``: the run stops, nothing is retried.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from talentscope import __version__
from talentscope.ingestion.records import (
    AccessDenied,
    RateLimited,
    SchemaChanged,
    SourceUnavailable,
)

logger = logging.getLogger(__name__)

DEFAULT_MIN_INTERVAL_SECONDS = 5.0
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3
MAX_RETRY_AFTER_SECONDS = 120.0
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class PoliteClient:
    def __init__(
        self,
        *,
        contact_url: str,
        min_interval: float = DEFAULT_MIN_INTERVAL_SECONDS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.user_agent = f"TalentScopeBot/{__version__} (+{contact_url})"
        self._client = httpx.Client(
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PoliteClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        response = self._get(url, params)
        if "json" not in response.headers.get("content-type", ""):
            raise SchemaChanged(
                f"expected JSON from {_host(url)}, got {response.headers.get('content-type')!r}"
            )
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise SchemaChanged(f"response from {_host(url)} exceeds {MAX_RESPONSE_BYTES} bytes")
        try:
            return response.json()
        except ValueError as exc:
            raise SchemaChanged(f"invalid JSON from {_host(url)}") from exc

    def _get(self, url: str, params: dict[str, Any] | None) -> httpx.Response:
        self._ensure_allowed_by_robots(url)
        for attempt in range(self._max_retries + 1):
            self._wait_for_turn(url)
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError as exc:
                if attempt == self._max_retries:
                    raise SourceUnavailable(
                        f"network error contacting {_host(url)}: {type(exc).__name__}"
                    ) from exc
                self._backoff(attempt)
                continue

            if response.status_code in (401, 403):
                raise AccessDenied(f"{_host(url)} answered HTTP {response.status_code}; stopping")
            if response.status_code == 429:
                if attempt == self._max_retries:
                    raise RateLimited(f"{_host(url)} kept answering HTTP 429")
                self._sleep(_retry_after_seconds(response) or self._backoff_delay(attempt))
                continue
            if response.status_code >= 500:
                if attempt == self._max_retries:
                    raise SourceUnavailable(f"{_host(url)} answered HTTP {response.status_code}")
                self._backoff(attempt)
                continue
            if response.status_code >= 400:
                raise SourceUnavailable(
                    f"{_host(url)} answered HTTP {response.status_code} for {urlsplit(url).path}"
                )
            return response
        raise AssertionError("unreachable: the retry loop always returns or raises")

    def _ensure_allowed_by_robots(self, url: str) -> None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        parser = self._robots.get(origin)
        if parser is None:
            parser = self._load_robots(origin)
            self._robots[origin] = parser
        if not parser.can_fetch(self.user_agent, url):
            raise AccessDenied(f"robots.txt at {parts.netloc} disallows {parts.path}")

    def _load_robots(self, origin: str) -> RobotFileParser:
        parser = RobotFileParser()
        self._wait_for_turn(origin)
        try:
            response = self._client.get(f"{origin}/robots.txt")
        except httpx.TransportError as exc:
            raise SourceUnavailable(
                f"could not fetch robots.txt from {urlsplit(origin).netloc}"
            ) from exc
        # RFC 9309: an unavailable robots.txt (4xx) means no restrictions; an unreachable
        # one (5xx) means assume complete disallow.
        if response.status_code >= 500:
            parser.parse(["User-agent: *", "Disallow: /"])
        elif response.status_code >= 400:
            parser.parse([])
        else:
            parser.parse(response.text.splitlines())
        return parser

    def _wait_for_turn(self, url: str) -> None:
        host = _host(url)
        last = self._last_request_at.get(host)
        if last is not None:
            remaining = self._min_interval - (self._clock() - last)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_at[host] = self._clock()

    def _backoff_delay(self, attempt: int) -> float:
        delay: float = min(MAX_RETRY_AFTER_SECONDS, (2**attempt) * self._min_interval)
        return delay + random.uniform(0, 1)

    def _backoff(self, attempt: int) -> None:
        delay = self._backoff_delay(attempt)
        logger.info("retrying after transient failure", extra={"delay_seconds": round(delay, 1)})
        self._sleep(delay)


def _host(url: str) -> str:
    return urlsplit(url).netloc


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError):
            return None
    if seconds > MAX_RETRY_AFTER_SECONDS:
        raise RateLimited(f"source asked to wait {int(seconds)}s, longer than this run allows")
    return max(seconds, 0.0)
