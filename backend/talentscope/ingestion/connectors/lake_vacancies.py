"""Publish canonical vacancies from the lake's silver layer into the application database.

One app job per canonical vacancy (not per archived page), so app counts match the
lake's deduplicated counts. Descriptions are not published (retention policy); the job
links to the original page instead.

Values the lake marks unreliable are not published as facts:
- a salary from a site's theme default, or below the monthly floor, becomes an
  explanatory ``salary_text`` (no amount, so it is never parsed back into a number);
- a validThrough from a site whose deadlines are a theme default is not published as
  ``expires_at`` (so it cannot mark the job expired); the source's value is kept in
  ``raw_fields["source_valid_through"]`` with ``raw_fields["valid_through_unreliable"]``.

The publish is a complete snapshot of the source (``replaces_snapshot``): the pipeline
applies it in one transaction and retires vacancies the snapshot no longer contains.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from talentscope.ingestion.connectors.base import Connector
from talentscope.ingestion.records import SchemaChanged, SourceJob, StructuredSalary
from talentscope.lake.domain_reviews import review_of
from talentscope.lake.silver import SALARY_BELOW_MONTHLY_FLOOR, SALARY_SITE_TEMPLATE
from talentscope.vocab import SalaryPeriod

# The app normalizes education from text; these are the phrases its normalizer maps
# back to the same codes the lake already assigned.
_EDUCATION_TEXT = {
    "SD": "SD",
    "SMP": "SMP",
    "SMA_SMK": "SMA/SMK",
    "DIPLOMA": "Diploma",
    "BACHELOR": "Sarjana (S1)",
    "PROFESSIONAL": "Pendidikan Profesi",
    "MASTER": "Magister (S2)",
    "DOCTORATE": "Doktor (S3)",
}
# No digits in these texts: the app parses salary_text, and must find no amount in them.
TEMPLATE_SALARY_TEXT = "Nilai gaji berasal dari templat situs dan tidak dipakai"
IMPLAUSIBLE_SALARY_TEXT = (
    "Nilai gaji di situs asal tidak wajar (di bawah batas minimum gaji bulanan) dan tidak dipakai"
)
_UNRELIABLE_SALARY_TEXT = {
    SALARY_SITE_TEMPLATE: TEMPLATE_SALARY_TEXT,
    SALARY_BELOW_MONTHLY_FLOOR: IMPLAUSIBLE_SALARY_TEXT,
}
REQUIRED_COLUMNS = {
    "vacancy_id",
    "registry_source_id",
    "title",
    "organization",
    "canonical_url",
    "first_seen_at",
    "last_seen_at",
    "salary_reliable",
    "salary_unreliable_reason",
    "valid_through_reliable",
}


def _day(value: object) -> datetime | None:
    return datetime.combine(value, time(), tzinfo=timezone.utc) if value else None  # type: ignore[arg-type]


# Indonesian sites mean "open through this day" (local time). Midnight UTC would mark the
# job expired from 07:00 WIB on the deadline day itself.
_WIB = timezone(timedelta(hours=7))


def _end_of_day(value: object) -> datetime | None:
    return datetime.combine(value, time(23, 59, 59), tzinfo=_WIB) if value else None  # type: ignore[arg-type]


class LakeVacancies(Connector):
    name = "lake_vacancies"
    parser_version = "lake-vacancies/2"
    mode = "import"
    replaces_snapshot = True

    def __init__(self, vacancies_path: Path, registry_source_id: str) -> None:
        self.path = vacancies_path
        self.registry_source_id = registry_source_id

    def describe_input(self) -> str:
        rows = pq.ParquetFile(self.path).metadata.num_rows
        return f"lake silver {self.path.name} ({rows} vacancies)"

    def observed_at(self) -> datetime:
        return datetime.now(timezone.utc)

    def current_keys(self) -> set[str]:
        """Vacancy ids this source publishes from the current silver build."""
        table = pq.read_table(self.path, columns=["vacancy_id", "registry_source_id"])
        return {
            row["vacancy_id"]
            for row in table.to_pylist()
            if row["registry_source_id"] == self.registry_source_id
        }

    def fetch(self) -> Iterator[SourceJob]:
        table = pq.read_table(self.path)
        missing = REQUIRED_COLUMNS - set(table.column_names)
        if missing:
            raise SchemaChanged(f"{self.path.name} lacks columns {sorted(missing)}; rebuild silver")
        for row in table.to_pylist():
            # Each source publishes the vacancies whose representative record it supplied.
            if row["registry_source_id"] != self.registry_source_id:
                continue
            salary, salary_text = _salary(row)
            deadline_unreliable = (
                row["valid_through"] is not None and not row["valid_through_reliable"]
            )
            review = review_of(row["source_domain"])
            years = row["experience_min_years"]
            yield SourceJob(
                source_key=row["vacancy_id"],
                source_key_kind="content_fingerprint",
                title=row["title"],
                company_name=row["organization"],
                location_text=", ".join(part for part in (row["city"], row["province"]) if part)
                or None,
                structured_salary=salary,
                salary_text=salary_text,
                employment_type_text=row["employment_type_raw"],
                work_arrangement_text="remote" if row["work_arrangement"] == "REMOTE" else None,
                experience_text=f"minimal {years} tahun" if years is not None else None,
                education_text=_EDUCATION_TEXT.get(row["education_level"]),
                published_at=_day(row["date_posted"]),
                expires_at=None if deadline_unreliable else _end_of_day(row["valid_through"]),
                source_url=row["canonical_url"],
                first_observed_at=row["first_seen_at"],
                last_observed_at=row["last_seen_at"],
                raw_fields={
                    "vacancy_id": row["vacancy_id"],
                    "sites": sorted(row["sites"]),
                    "source_records": row["source_records"],
                    # Several near-identical pages for different places (an SEO campaign);
                    # the vacancy has no single location.
                    "city_templated": bool(row["city_templated"]),
                    # The title as the site wrote it; `title` has blog boilerplate removed.
                    "source_title": row["source_title"],
                    # The site says it gathers vacancies from elsewhere (second-hand record).
                    "aggregator_site": bool(review and review.aggregator),
                    "parser_version": row["parser_version"],
                    # The source's validThrough, kept even when it is not used as a deadline.
                    "source_valid_through": (
                        row["valid_through"].isoformat() if row["valid_through"] else None
                    ),
                    # True when the site's validThrough values are a theme default, so the
                    # date is not the employer's application deadline.
                    "valid_through_unreliable": deadline_unreliable,
                },
            )


def _salary(row: dict[str, Any]) -> tuple[StructuredSalary | None, str | None]:
    """The structured monthly salary when the lake trusts it, else an explanation (or
    nothing when no salary was disclosed). Never a zero or an implausible amount."""
    if row["salary_reliable"]:
        minimum, maximum = row["salary_monthly_min"], row["salary_monthly_max"]
        if minimum is not None and maximum is not None and minimum <= maximum:
            return StructuredSalary(minimum, maximum, "IDR", SalaryPeriod.MONTH), None
    return None, _UNRELIABLE_SALARY_TEXT.get(row["salary_unreliable_reason"])
