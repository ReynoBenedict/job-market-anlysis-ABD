"""Network behaviour is tested against httpx.MockTransport; no test touches a real site."""

import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from talentscope.ingestion.connectors.lever import LeverPostings
from talentscope.ingestion.http import PoliteClient
from talentscope.ingestion.records import (
    AccessDenied,
    RateLimited,
    SchemaChanged,
    SourceUnavailable,
)
from talentscope.vocab import SalaryPeriod

FIXTURES = Path(__file__).parents[1] / "fixtures"
ROBOTS_ALLOW = "User-agent: *\nAllow: /\n"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def _client(
    handler: Callable[[httpx.Request], httpx.Response], clock: FakeClock | None = None
) -> PoliteClient:
    clock = clock or FakeClock()
    return PoliteClient(
        contact_url="https://example.org/about",
        transport=httpx.MockTransport(handler),
        min_interval=5.0,
        max_retries=2,
        sleep=clock.sleep,
        clock=clock,
    )


def _router(
    responses: dict[str, list[httpx.Response]], robots: str = ROBOTS_ALLOW
) -> Callable[[httpx.Request], httpx.Response]:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        queue = responses[request.url.path]
        return queue.pop(0) if len(queue) > 1 else queue[0]

    return handle


def test_identifies_itself_and_spaces_requests() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_ALLOW)
        return httpx.Response(200, json={"ok": True})

    clock = FakeClock()
    client = _client(handle, clock)
    client.get_json("https://api.example.com/a")
    client.get_json("https://api.example.com/b")
    assert all("TalentScopeBot" in r.headers["user-agent"] for r in seen)
    assert [r.url.path for r in seen] == ["/robots.txt", "/a", "/b"]
    # robots.txt, then two requests: each later request waited the full interval.
    assert clock.sleeps == [5.0, 5.0]


def test_robots_disallow_stops_before_requesting() -> None:
    client = _client(
        _router(
            {"/private/jobs": [httpx.Response(200, json=[])]},
            robots="User-agent: *\nDisallow: /private\n",
        )
    )
    with pytest.raises(AccessDenied):
        client.get_json("https://api.example.com/private/jobs")


@pytest.mark.parametrize("status", [401, 403])
def test_access_denied_is_not_retried(status: int) -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls.append(request)
        return httpx.Response(status)

    with pytest.raises(AccessDenied):
        _client(handle).get_json("https://api.example.com/jobs")
    assert len(calls) == 1


def test_server_errors_are_retried_with_backoff_then_fail() -> None:
    clock = FakeClock()
    client = _client(_router({"/jobs": [httpx.Response(503)]}), clock)
    with pytest.raises(SourceUnavailable):
        client.get_json("https://api.example.com/jobs")
    assert len([s for s in clock.sleeps if s >= 5.0]) >= 2


def test_transient_error_then_success() -> None:
    client = _client(_router({"/jobs": [httpx.Response(502), httpx.Response(200, json=[1])]}))
    assert client.get_json("https://api.example.com/jobs") == [1]


def test_rate_limit_honours_retry_after_then_gives_up() -> None:
    clock = FakeClock()
    client = _client(_router({"/jobs": [httpx.Response(429, headers={"Retry-After": "7"})]}), clock)
    with pytest.raises(RateLimited):
        client.get_json("https://api.example.com/jobs")
    assert 7.0 in clock.sleeps


def test_excessive_retry_after_stops_the_run() -> None:
    client = _client(_router({"/jobs": [httpx.Response(429, headers={"Retry-After": "3600"})]}))
    with pytest.raises(RateLimited):
        client.get_json("https://api.example.com/jobs")


def test_unreachable_robots_means_disallow() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with pytest.raises(AccessDenied):
        _client(handle).get_json("https://api.example.com/jobs")


def test_non_json_response_is_a_schema_change() -> None:
    client = _client(_router({"/jobs": [httpx.Response(200, html="<html>challenge</html>")]}))
    with pytest.raises(SchemaChanged):
        client.get_json("https://api.example.com/jobs")


def _lever(payload: object) -> LeverPostings:
    client = _client(_router({"/v0/postings/example-company": [httpx.Response(200, json=payload)]}))
    return LeverPostings(client, site="example-company", company_name="Example Company")


def test_lever_connector_parses_postings() -> None:
    payload = json.loads((FIXTURES / "lever_postings.json").read_text("utf-8"))
    jobs = list(_lever(payload).fetch())
    assert [j.source_key for j in jobs] == ["synthetic-0001", "synthetic-0002", "synthetic-0003"]
    first, second, third = jobs
    assert first.source_key_kind == "source_id"
    assert (
        first.structured_salary is not None and first.structured_salary.period is SalaryPeriod.MONTH
    )
    assert (
        second.structured_salary is not None
        and second.structured_salary.period is SalaryPeriod.YEAR
    )
    assert first.work_arrangement_text == "hybrid"
    assert first.description is None  # descriptions are not retained unless permitted
    assert first.published_at is not None
    assert third.structured_salary is None


def test_lever_connector_detects_changed_payload() -> None:
    with pytest.raises(SchemaChanged):
        list(_lever({"postings": []}).fetch())
    with pytest.raises(SchemaChanged):
        list(_lever([{"title": "no id"}]).fetch())


def test_lever_connector_stops_after_last_short_page() -> None:
    assert list(_lever([]).fetch()) == []
