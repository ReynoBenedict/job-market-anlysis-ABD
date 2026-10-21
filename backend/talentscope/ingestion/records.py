"""The contract between source connectors and the shared pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from talentscope.vocab import RunErrorCategory, SalaryPeriod

SourceKeyKind = Literal["source_id", "url", "content_fingerprint"]


@dataclass(frozen=True)
class StructuredSalary:
    """Salary given as structured fields by an API, rather than as display text."""

    minimum: int | None
    maximum: int | None
    currency: str | None
    period: SalaryPeriod


@dataclass(frozen=True)
class SalaryConvention:
    """How a source writes salaries when the text omits currency or period.

    Only set this when the convention is documented (see docs/DATA_POLICY.md); records
    parsed with it are flagged as relying on an assumption.
    """

    currency: str | None = None
    period: SalaryPeriod | None = None


@dataclass(frozen=True)
class SourceJob:
    """One job as a connector found it, before normalization.

    Connectors fill only the fields their source provides and leave the rest empty;
    they never invent values. ``raw_fields`` keeps the original values that the source
    permits us to retain, for provenance and re-normalization.
    """

    source_key: str
    source_key_kind: SourceKeyKind
    title: str | None
    company_name: str | None = None
    location_text: str | None = None
    salary_text: str | None = None
    structured_salary: StructuredSalary | None = None
    employment_type_text: str | None = None
    work_arrangement_text: str | None = None
    experience_text: str | None = None
    education_text: str | None = None
    tags: tuple[str, ...] = ()
    description: str | None = None
    posted_text: str | None = None
    published_at: datetime | None = None
    expires_at: datetime | None = None
    source_url: str | None = None
    raw_fields: Mapping[str, Any] = field(default_factory=dict)
    # When a record carries its own observation history (e.g. archive captures), these
    # override the run's observation time for first/last seen.
    first_observed_at: datetime | None = None
    last_observed_at: datetime | None = None


class ConnectorError(Exception):
    """A failure that stops a connector run. ``category`` drives the run status."""

    category: RunErrorCategory = RunErrorCategory.INTERNAL

    def __init__(self, message: str, *, category: RunErrorCategory | None = None) -> None:
        super().__init__(message)
        if category is not None:
            self.category = category


class AccessDenied(ConnectorError):
    """401/403, CAPTCHA or challenge pages, robots.txt disallow: stop and do not retry."""

    category = RunErrorCategory.ACCESS_DENIED


class RateLimited(ConnectorError):
    category = RunErrorCategory.RATE_LIMITED


class SourceUnavailable(ConnectorError):
    """Network errors and 5xx responses that persisted after bounded retries."""

    category = RunErrorCategory.NETWORK


class SchemaChanged(ConnectorError):
    """The payload no longer has the shape the parser was written for."""

    category = RunErrorCategory.SCHEMA_CHANGED
