"""Import of the June 2026 academic Glints snapshot (data/raw/glints_jobs.csv).

The file is opened read-only and never rewritten. It has no job IDs, URLs, or
collection timestamps, so:

* identity is a content fingerprint of (title, company, location), which the original
  scraper also used to deduplicate and which is unique within the file;
* the observation time is configured explicitly and is an upper bound: the raw file was
  committed on 2026-06-13 02:57 WIB (19:57 UTC the day before), so collection happened
  on or before that moment;
* salaries carry no period. Glints cards display monthly IDR ranges, so the period is
  recorded as an assumption, not a fact.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from talentscope.ingestion.connectors.base import Connector
from talentscope.ingestion.records import SalaryConvention, SchemaChanged, SourceJob
from talentscope.normalization.job import job_fingerprint
from talentscope.vocab import SalaryPeriod

EXPECTED_COLUMNS = (
    "job_title",
    "company_name",
    "location",
    "salary_range",
    "job_type",
    "experience_level",
    "education_req",
    "job_requirements",
    "posted_date",
    "source_platform",
)
TAG_SEPARATOR = " | "


class LegacyGlintsSnapshot(Connector):
    name = "legacy_glints_csv"
    parser_version = "legacy-glints-csv/1"
    mode = "import"
    salary_convention = SalaryConvention(currency="IDR", period=SalaryPeriod.MONTH)

    def __init__(self, path: Path, observed_at: datetime) -> None:
        if observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        self.path = path
        self._observed_at = observed_at

    def describe_input(self) -> str:
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        return f"{self.path.name} sha256={digest}"

    def observed_at(self) -> datetime:
        return self._observed_at

    def fetch(self) -> Iterator[SourceJob]:
        # utf-8-sig: the legacy pipeline wrote the file with a byte-order mark.
        with self.path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = set(EXPECTED_COLUMNS) - set(reader.fieldnames or ())
            if missing:
                raise SchemaChanged(f"{self.path.name} is missing columns: {sorted(missing)}")
            for row in reader:
                yield SourceJob(
                    source_key=job_fingerprint(
                        row["job_title"], row["company_name"], row["location"]
                    ),
                    source_key_kind="content_fingerprint",
                    title=row["job_title"],
                    company_name=row["company_name"],
                    location_text=row["location"],
                    salary_text=row["salary_range"],
                    employment_type_text=row["job_type"],
                    experience_text=row["experience_level"],
                    education_text=row["education_req"],
                    tags=tuple(row["job_requirements"].split(TAG_SEPARATOR)),
                    posted_text=row["posted_date"],
                    raw_fields={column: row[column] for column in EXPECTED_COLUMNS},
                )
