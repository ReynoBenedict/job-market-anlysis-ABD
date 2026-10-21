"""Response models. Categorical values are returned as {code, label} so the web client
never re-implements the code-to-Indonesian-label mapping."""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from talentscope.analytics.filters import freshness_of
from talentscope.analytics.salary_rule import is_comparable
from talentscope.models import Job, Source, SourceRecord
from talentscope.vocab import (
    EducationLevel,
    EmploymentType,
    ExperienceBand,
    LabelledEnum,
    ObservationMethod,
    PermissionStatus,
    RoleFamily,
    SalaryPeriod,
    SalaryStatus,
    WorkArrangement,
)

T = TypeVar("T")

_LINK_SCHEMES = ("http://", "https://")


def safe_link(url: str | None) -> str | None:
    """Source URLs are rendered as links; only http(s) URLs are passed on, so a stored
    value such as "javascript:..." can never become a clickable link."""
    return url if url is not None and url.lower().startswith(_LINK_SCHEMES) else None


class Coded(BaseModel):
    code: str
    label: str

    @classmethod
    def of(cls, enum: type[LabelledEnum], code: str) -> Coded:
        return cls(code=code, label=enum(code).label)


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def build(cls, items: list[T], *, page: int, page_size: int, total: int) -> Page[T]:
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=math.ceil(total / page_size) if total else 0,
        )


class SourceRef(BaseModel):
    id: str
    name: str
    attribution: str | None
    method: Coded
    public_label: str | None = Field(description="Public reuse badge; null when unset.")
    public_condition: str | None = Field(
        description="One-sentence reuse condition; null when unset."
    )

    @classmethod
    def from_source(cls, source: Source) -> SourceRef:
        method = ObservationMethod.of_technical_method(source.technical_method)
        return cls(
            id=source.id,
            name=source.name,
            attribution=source.attribution_text,
            method=Coded(code=method.value, label=method.label),
            public_label=source.public_label,
            public_condition=source.public_condition,
        )


class ArchiveEvidence(BaseModel):
    """What the web archive saw for one canonical vacancy (lake publish only)."""

    pages: int
    sites: list[str]
    city_templated: bool
    source_title: str | None
    aggregator_site: bool
    # The site fills deadlines automatically (same date or offset on most listings), so
    # its deadline was not used; `expires_at` is null and the source value is shown as is.
    deadline_unreliable: bool
    source_valid_through: str | None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> ArchiveEvidence | None:
        if "source_records" not in raw or "sites" not in raw:
            return None
        return cls(
            pages=int(raw["source_records"]),
            sites=list(raw["sites"]),
            city_templated=bool(raw.get("city_templated", False)),
            source_title=raw.get("source_title"),
            aggregator_site=bool(raw.get("aggregator_site", False)),
            deadline_unreliable=bool(raw.get("valid_through_unreliable", False)),
            source_valid_through=raw.get("source_valid_through"),
        )


class Salary(BaseModel):
    status: Coded
    text: str | None
    min: int | None
    max: int | None
    currency: str | None
    period: Coded
    period_assumed: bool
    monthly_min: int | None
    monthly_max: int | None
    comparable: bool = Field(
        description="True when this salary meets the statistics eligibility rule "
        "(disclosed IDR, monthly equivalent, min <= max, monthly midpoint >= Rp500,000); "
        "only such salaries enter statistics, salary filters, and the salary sort."
    )


class Location(BaseModel):
    text: str | None
    city: str | None
    province: str | None
    confidence: str


class Experience(BaseModel):
    text: str | None
    min_years: int | None
    max_years: int | None
    band: Coded


class JobSummary(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str | None
    role_family: Coded
    location: Location
    employment_type: Coded
    work_arrangement: Coded
    experience: Experience
    education: Coded
    salary: Salary
    source_tags: list[str]
    hidden_tag_count: int
    is_urgent: bool
    posted_text: str | None
    posted_age_days: int | None
    published_at: datetime | None
    expires_at: datetime | None
    last_seen_at: datetime
    freshness: Coded
    source: SourceRef
    source_url: str | None

    @classmethod
    def from_job(cls, job: Job, *, freshness_window_days: int) -> JobSummary:
        return cls(**_summary_fields(job, freshness_window_days))


class SourceRecordOut(BaseModel):
    source: SourceRef
    source_key_kind: str
    source_url: str | None
    match_rule: str
    first_seen_at: datetime
    last_seen_at: datetime

    @classmethod
    def from_record(cls, record: SourceRecord, source: Source) -> SourceRecordOut:
        return cls(
            source=SourceRef.from_source(source),
            source_key_kind=record.source_key_kind,
            source_url=safe_link(record.source_url),
            match_rule=record.match_rule,
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
        )


class JobDetail(JobSummary):
    description: str | None
    employment_type_text: str | None
    work_arrangement_evidence: str | None
    education_text: str | None
    first_seen_at: datetime
    quality_flags: list[str]
    normalization_version: str
    source_records: list[SourceRecordOut]
    archive: ArchiveEvidence | None

    @classmethod
    def build(
        cls, job: Job, *, freshness_window_days: int, sources: dict[str, Source]
    ) -> JobDetail:
        return cls(
            **_summary_fields(job, freshness_window_days),
            description=job.description,
            employment_type_text=job.employment_type_text,
            work_arrangement_evidence=job.work_arrangement_evidence,
            education_text=job.education_text,
            first_seen_at=job.first_seen_at,
            quality_flags=job.quality_flags,
            normalization_version=job.normalization_version,
            source_records=[
                SourceRecordOut.from_record(r, sources[r.source_id]) for r in job.source_records
            ],
            archive=next(
                (
                    evidence
                    for record in job.source_records
                    if (evidence := ArchiveEvidence.from_raw(record.raw_fields)) is not None
                ),
                None,
            ),
        )


def _summary_fields(job: Job, freshness_window_days: int) -> dict[str, object]:
    freshness = freshness_of(job.last_seen_at, job.expires_at, window_days=freshness_window_days)
    return {
        "id": job.id,
        "title": job.title,
        "company_name": job.company_name,
        "role_family": Coded.of(RoleFamily, job.role_family),
        "location": Location(
            text=job.location_text,
            city=job.city,
            province=job.province,
            confidence=job.location_confidence,
        ),
        "employment_type": Coded.of(EmploymentType, job.employment_type),
        "work_arrangement": Coded.of(WorkArrangement, job.work_arrangement),
        "experience": Experience(
            text=job.experience_text,
            min_years=job.experience_min_years,
            max_years=job.experience_max_years,
            band=Coded.of(ExperienceBand, job.experience_band),
        ),
        "education": Coded.of(EducationLevel, job.education_level),
        "salary": Salary(
            status=Coded.of(SalaryStatus, job.salary_status),
            text=job.salary_text,
            min=job.salary_min,
            max=job.salary_max,
            currency=job.salary_currency,
            period=Coded.of(SalaryPeriod, job.salary_period),
            period_assumed=job.salary_period_assumed,
            monthly_min=job.salary_monthly_min,
            monthly_max=job.salary_monthly_max,
            comparable=is_comparable(
                job.salary_status,
                job.salary_currency,
                job.salary_monthly_min,
                job.salary_monthly_max,
            ),
        ),
        "source_tags": job.source_tags,
        "hidden_tag_count": job.hidden_tag_count,
        "is_urgent": job.is_urgent,
        "posted_text": job.posted_text,
        "posted_age_days": job.posted_age_days,
        "published_at": job.published_at,
        "expires_at": job.expires_at,
        "last_seen_at": job.last_seen_at,
        "freshness": Coded(code=freshness.value, label=freshness.label),
        "source": SourceRef.from_source(job.primary_source),
        "source_url": safe_link(job.source_url),
    }


class FilterOption(BaseModel):
    value: str
    label: str
    count: int


class FilterOptions(BaseModel):
    total: int
    province: list[FilterOption]
    city: list[FilterOption]
    role_family: list[FilterOption]
    employment_type: list[FilterOption]
    work_arrangement: list[FilterOption]
    education: list[FilterOption]
    experience: list[FilterOption]
    source: list[FilterOption]
    freshness: list[FilterOption]
    salary_monthly_range: tuple[int, int] | None


class DatasetScope(BaseModel):
    """What the numbers describe. Shown next to every analytical view (SRS FR-MKT-005)."""

    observed_from: datetime | None = Field(
        description="Earliest last_seen_at (observation/archive-capture time), not a "
        "publication or collection date."
    )
    observed_to: datetime | None = Field(description="Latest last_seen_at.")
    published_from: datetime | None = Field(
        description="Earliest published_at stated by the listings; null if none states one."
    )
    published_to: datetime | None = Field(description="Latest published_at; null if none.")
    is_historical: bool
    freshness_window_days: int
    sources: list[SourceRef]
    publisher_sites: int = Field(
        description="Distinct publisher websites (host of source_url, without 'www.') among "
        "the described jobs. `sources` are ingestion datasets; one archive source spans many "
        "sites. Jobs without a source URL (e.g. the historical snapshot) add no site."
    )
    coverage_notes: list[str]


class MarketOverview(BaseModel):
    total_jobs: int
    total_source_records: int
    companies: int
    cities: int
    provinces: int
    publisher_sites: int = Field(description="Same as scope.publisher_sites.")
    salary_disclosed: int
    salary_disclosed_share: float
    remote_or_hybrid: int
    scope: DatasetScope


class BreakdownRowOut(BaseModel):
    key: str | None
    label: str
    count: int
    share: float


class BreakdownOut(BaseModel):
    dimension: str
    total: int
    distinct_values: int
    other_count: int
    rows: list[BreakdownRowOut]


class HistogramBin(BaseModel):
    lower: int
    upper: int | None
    count: int


class SalaryOverviewOut(BaseModel):
    total_jobs: int
    status_counts: list[FilterOption]
    eligible: int = Field(description="Jobs with a comparable salary (see Salary.comparable).")
    eligible_share: float = Field(description="eligible / total_jobs")
    excluded_implausible: int = Field(
        description="Disclosed monthly IDR salaries left out of statistics because the range "
        "is reversed or its midpoint is below min_monthly_midpoint. Stored data is unchanged."
    )
    min_monthly_midpoint: int
    period_assumed: int
    min_records_for_statistics: int
    percentiles: dict[str, float] | None = Field(
        description="Percentiles of monthly range midpoints of eligible jobs."
    )
    median_min: float | None = Field(
        description="Median of the range lower bounds (monthly minimum) of eligible jobs."
    )
    median_max: float | None = Field(
        description="Median of the range upper bounds (monthly maximum) of eligible jobs."
    )
    histogram: list[HistogramBin]
    flag_counts: dict[str, int]
    currency: str
    scope: DatasetScope


class SalaryGroupOut(BaseModel):
    key: str | None
    label: str
    n: int
    jobs_in_group: int
    p25: float | None
    median: float | None
    p75: float | None
    small_sample: bool


class SalaryComparisonOut(BaseModel):
    by: str
    min_records_for_statistics: int
    small_sample_threshold: int
    groups: list[SalaryGroupOut]
    scope: DatasetScope


class TagStatsOut(BaseModel):
    total_jobs: int
    jobs_with_visible_tags: int
    jobs_with_hidden_tags: int
    visible_tags: int
    hidden_tags: int
    top_tags: list[FilterOption]
    role_families: list[FilterOption]
    scope: DatasetScope


class SourceCoverage(BaseModel):
    id: str
    name: str
    canonical_domain: str | None
    category: str
    permission_status: Coded
    method: Coded
    decision_reason: str | None
    job_count: int
    last_successful_run_at: datetime | None
    attribution: str | None
    coverage_note: str | None
    public_label: str | None
    public_condition: str | None
    reviewed_at: datetime | None

    @classmethod
    def build(
        cls, source: Source, *, job_count: int, last_success: datetime | None
    ) -> SourceCoverage:
        return cls(
            id=source.id,
            name=source.name,
            canonical_domain=source.canonical_domain,
            category=source.category,
            permission_status=Coded.of(PermissionStatus, source.permission_status),
            method=Coded.of(
                ObservationMethod, ObservationMethod.of_technical_method(source.technical_method)
            ),
            decision_reason=source.decision_reason,
            job_count=job_count,
            last_successful_run_at=last_success,
            attribution=source.attribution_text,
            coverage_note=source.coverage_note,
            public_label=source.public_label,
            public_condition=source.public_condition,
            reviewed_at=source.reviewed_at,
        )
