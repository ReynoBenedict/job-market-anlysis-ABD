"""Fetch single archived pages from Common Crawl WARC files with HTTP range requests."""

from __future__ import annotations

import gzip
import threading
import time
from collections.abc import Callable, Generator, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

import httpx

from talentscope import __version__
from talentscope.lake.commoncrawl import ARCHIVE_ROOT

# Common Crawl asks clients to back off on 503 ("Slow Down"): wait at least a second,
# growing to 10 s or more for small requests such as single captures. 403 from CloudFront
# is their explicit rate-limit rule: never retried, it stops the run (see AccessBlocked).
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
DEFAULT_WORKERS = 2
DEFAULT_REQUESTS_PER_SECOND = 2.0
MAX_ATTEMPTS = 6
FIRST_BACKOFF_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 60.0


@dataclass(frozen=True)
class RecordPointer:
    warc_filename: str
    offset: int
    length: int


@dataclass(frozen=True)
class Capture:
    target_uri: str
    captured_at: datetime
    http_status: int | None
    body: bytes


class AccessBlocked(Exception):
    """Common Crawl refused access (403, or 429 after retries). The whole run must stop:
    continuing would ignore an explicit rate-limit block (SRS FR-ING-009)."""


class FetchFailed(Exception):
    """The record could not be retrieved; ``reason`` is a short category for reporting."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def parse_warc_record(record: bytes) -> Capture:
    """Split an uncompressed WARC 'response' record into its capture metadata and body."""
    warc_head, _, rest = record.partition(b"\r\n\r\n")
    headers: dict[str, str] = {}
    for line in warc_head.decode("utf-8", "replace").split("\r\n")[1:]:
        name, _, value = line.partition(":")
        headers[name.strip().lower()] = value.strip()
    if headers.get("warc-type") != "response":
        raise FetchFailed("not_a_response_record", headers.get("warc-type", "missing"))

    http_head, _, body = rest.partition(b"\r\n\r\n")
    status_line = http_head.split(b"\r\n", 1)[0].decode("latin-1")
    parts = status_line.split(" ")
    http_status = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    return Capture(
        target_uri=headers.get("warc-target-uri", ""),
        captured_at=datetime.fromisoformat(headers["warc-date"].replace("Z", "+00:00")),
        http_status=http_status,
        body=body,
    )


class _RateLimiter:
    """Spaces request starts at least 1/rate seconds apart across all threads."""

    def __init__(
        self, per_second: float, clock: Callable[[], float], sleep: Callable[[float], None]
    ) -> None:
        self._interval = 1.0 / per_second
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            start = max(now, self._next)
            self._next = start + self._interval
        if start > now:
            self._sleep(start - now)


class ArchiveFetcher:
    def __init__(
        self,
        *,
        contact_url: str,
        workers: int = DEFAULT_WORKERS,
        requests_per_second: float = DEFAULT_REQUESTS_PER_SECOND,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": f"TalentScopeResearch/{__version__} (+{contact_url})"},
            timeout=60.0,
            transport=transport,
            limits=httpx.Limits(max_connections=workers),
        )
        self._workers = workers
        self._limiter = _RateLimiter(requests_per_second, clock, sleep)
        self._sleep = sleep

    def close(self) -> None:
        self._client.close()

    def fetch(self, pointer: RecordPointer) -> Capture:
        url = f"{ARCHIVE_ROOT}/{pointer.warc_filename}"
        headers = {"Range": f"bytes={pointer.offset}-{pointer.offset + pointer.length - 1}"}
        backoff = FIRST_BACKOFF_SECONDS
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._limiter.wait()
            try:
                response = self._client.get(url, headers=headers)
            except httpx.TransportError as exc:
                if attempt == MAX_ATTEMPTS:
                    raise FetchFailed("network", type(exc).__name__) from exc
            else:
                if response.status_code == 206:
                    try:
                        return parse_warc_record(gzip.decompress(response.content))
                    except (OSError, EOFError, ValueError, KeyError) as exc:
                        raise FetchFailed("corrupt_record", type(exc).__name__) from exc
                if response.status_code == 403:
                    raise AccessBlocked("Common Crawl answered HTTP 403 (rate-limit block)")
                if response.status_code not in RETRYABLE_STATUS:
                    raise FetchFailed(f"http_{response.status_code}")
                if attempt == MAX_ATTEMPTS:
                    if response.status_code == 429:
                        raise AccessBlocked("Common Crawl kept answering HTTP 429")
                    raise FetchFailed(f"http_{response.status_code}", "retries exhausted")
            self._sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
        raise AssertionError("unreachable")

    def fetch_many(
        self, pointers: Iterable[RecordPointer]
    ) -> Generator[tuple[RecordPointer, Capture | FetchFailed], None, None]:
        """Fetch concurrently; yields each pointer with its capture or failure.

        AccessBlocked propagates to the caller (remaining results are abandoned)."""

        blocked = threading.Event()

        def attempt(
            pointer: RecordPointer,
        ) -> tuple[RecordPointer, Capture | FetchFailed | AccessBlocked]:
            # Once blocked, queued work returns without sending further requests.
            if blocked.is_set():
                return pointer, FetchFailed("not_attempted")
            try:
                return pointer, self.fetch(pointer)
            except FetchFailed as failure:
                return pointer, failure
            except AccessBlocked as denial:
                blocked.set()
                return pointer, denial

        with ThreadPoolExecutor(self._workers) as pool:
            for pointer, result in pool.map(attempt, pointers):
                if isinstance(result, AccessBlocked):
                    raise result
                yield pointer, result
