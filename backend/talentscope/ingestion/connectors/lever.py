"""Lever Postings API adapter (https://github.com/lever/postings-api).

The API is public and documented, but intended for an employer's own job site. Per
docs/RESEARCH_SOURCES.md each employer board needs written consent before it may be
collected, so sources using this connector stay disabled until that is recorded.

Descriptions are not retained by default (SRS FR-ING-016); enable ``store_description``
only when the employer's permission covers it.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from talentscope.ingestion.connectors.base import Connector
from talentscope.ingestion.http import PoliteClient
from talentscope.ingestion.records import SchemaChanged, SourceJob, StructuredSalary
from talentscope.vocab import SalaryPeriod

API_ROOT = "https://api.lever.co/v0/postings"
PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 20

_INTERVALS = {
    "per-hour-wage": SalaryPeriod.HOUR,
    "per-day-wage": SalaryPeriod.DAY,
    "per-week-salary": SalaryPeriod.WEEK,
    "per-month-salary": SalaryPeriod.MONTH,
    "per-year-salary": SalaryPeriod.YEAR,
}


class LeverPostings(Connector):
    name = "lever"
    parser_version = "lever-postings/1"
    mode = "collect"

    def __init__(
        self,
        client: PoliteClient,
        *,
        site: str,
        company_name: str,
        max_pages: int = DEFAULT_MAX_PAGES,
        store_description: bool = False,
    ) -> None:
        self.client = client
        self.site = site
        self.company_name = company_name
        self.max_pages = max_pages
        self.store_description = store_description
        self._observed_at = datetime.now(timezone.utc)

    def describe_input(self) -> str:
        return f"{API_ROOT}/{self.site}"

    def observed_at(self) -> datetime:
        return self._observed_at

    def fetch(self) -> Iterator[SourceJob]:
        for page in range(self.max_pages):
            payload = self.client.get_json(
                f"{API_ROOT}/{self.site}",
                params={"mode": "json", "skip": page * PAGE_SIZE, "limit": PAGE_SIZE},
            )
            if not isinstance(payload, list):
                raise SchemaChanged("Lever response is not a list of postings")
            for posting in payload:
                yield self._parse(posting)
            if len(payload) < PAGE_SIZE:
                return

    def _parse(self, posting: Any) -> SourceJob:
        if not isinstance(posting, dict) or "id" not in posting or "text" not in posting:
            raise SchemaChanged("Lever posting lacks 'id' or 'text'")
        categories = posting.get("categories") or {}
        created_ms = posting.get("createdAt")
        return SourceJob(
            source_key=str(posting["id"]),
            source_key_kind="source_id",
            title=posting["text"],
            company_name=self.company_name,
            location_text=categories.get("location"),
            employment_type_text=categories.get("commitment"),
            work_arrangement_text=posting.get("workplaceType"),
            structured_salary=_salary(posting.get("salaryRange")),
            description=posting.get("descriptionPlain") if self.store_description else None,
            published_at=(
                datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc)
                if isinstance(created_ms, (int, float))
                else None
            ),
            source_url=posting.get("hostedUrl"),
            raw_fields={
                "id": posting["id"],
                "text": posting["text"],
                "categories": categories,
                "workplaceType": posting.get("workplaceType"),
                "salaryRange": posting.get("salaryRange"),
                "hostedUrl": posting.get("hostedUrl"),
                "createdAt": created_ms,
            },
        )


def _salary(value: Any) -> StructuredSalary | None:
    if not isinstance(value, dict):
        return None
    period = _INTERVALS.get(str(value.get("interval")), SalaryPeriod.UNKNOWN)
    minimum, maximum = value.get("min"), value.get("max")
    return StructuredSalary(
        minimum=int(minimum) if isinstance(minimum, (int, float)) else None,
        maximum=int(maximum) if isinstance(maximum, (int, float)) else None,
        currency=value.get("currency"),
        period=period,
    )
