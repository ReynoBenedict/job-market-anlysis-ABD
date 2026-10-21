"""Silver → gold: analytics tables (Parquet) and the inventory / data-quality report (JSON).

Every table counts canonical vacancies unless its name says otherwise. Salary tables use
only `salary_reliable` monthly IDR values (midpoint per vacancy); groups below
MIN_SALARY_SAMPLE get no statistics. Skill shares use vacancies that have a description
of at least MIN_DESCRIPTION_CHARS as the denominator.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from talentscope.lake.domain_reviews import REVIEWED_AT, USABLE, review_of
from talentscope.lake.domains import EXCLUDED_DOMAINS
from talentscope.lake.layout import Lake
from talentscope.lake.postings import PARSER_VERSION
from talentscope.lake.skills import SKILL_DICTIONARY_VERSION
from talentscope.normalization.salary import IDR_MONTHLY_LOW_OUTLIER
from talentscope.sources import COMMON_CRAWL_SOURCE_ID

logger = logging.getLogger(__name__)

MIN_SALARY_SAMPLE = 5
SMALL_SALARY_SAMPLE = 20
MIN_DESCRIPTION_CHARS = 100

# Salary midpoints count only when reliable and not below the plausibility floor.
_SALARY_OK = f"salary_reliable and (salary_monthly_min + salary_monthly_max) / 2 >= {IDR_MONTHLY_LOW_OUTLIER}"
_MIDPOINT = "(salary_monthly_min + salary_monthly_max) / 2.0"


def _salary_by(dimension: str) -> str:
    return f"""
        select {dimension} as key,
               count(*) as vacancies,
               count(*) filter (where {_SALARY_OK}) as n,
               case when count(*) filter (where {_SALARY_OK}) >= {MIN_SALARY_SAMPLE}
                    then quantile_cont({_MIDPOINT}, 0.25) filter (where {_SALARY_OK}) end as p25,
               case when count(*) filter (where {_SALARY_OK}) >= {MIN_SALARY_SAMPLE}
                    then quantile_cont({_MIDPOINT}, 0.5) filter (where {_SALARY_OK}) end as median,
               case when count(*) filter (where {_SALARY_OK}) >= {MIN_SALARY_SAMPLE}
                    then quantile_cont({_MIDPOINT}, 0.75) filter (where {_SALARY_OK}) end as p75,
               count(*) filter (where {_SALARY_OK}) < {SMALL_SALARY_SAMPLE} as small_sample
        from vacancies group by 1 order by n desc, vacancies desc
    """


TABLES: dict[str, str] = {
    "vacancies_by_province": """
        select province, count(distinct vacancy_id) as vacancies
        from (select vacancy_id, unnest(case when city_templated or len(provinces) = 0
                                             then ['(tidak diketahui / banyak lokasi)'] else provinces end) as province
              from vacancies)
        group by 1 order by 2 desc
    """,
    "vacancies_by_city": """
        select province, city, count(*) as vacancies from vacancies
        where city is not null and not city_templated group by all order by 3 desc
    """,
    "vacancies_by_role_family": "select role_family, count(*) as vacancies from vacancies group by 1 order by 2 desc",
    "vacancies_by_employment_type": "select employment_type, count(*) as vacancies from vacancies group by 1 order by 2 desc",
    "vacancies_by_education": "select education_level, count(*) as vacancies from vacancies group by 1 order by 2 desc",
    "vacancies_by_experience": """
        select case when experience_min_years is null then 'UNKNOWN'
                    when experience_min_years < 1 then '<1' when experience_min_years < 3 then '1-2'
                    when experience_min_years < 5 then '3-4' when experience_min_years < 10 then '5-9'
                    else '10+' end as min_years,
               count(*) as vacancies
        from vacancies group by 1 order by 2 desc
    """,
    "vacancies_by_work_arrangement": "select work_arrangement, count(*) as vacancies from vacancies group by 1 order by 2 desc",
    "employers": """
        -- min(): spellings of one employer key differ ("PT Maju" / "PT. Maju"); any_value
        -- picked a different one on each rebuild.
        select organization_key, min(organization) as organization, count(*) as vacancies,
               count(distinct source_domain) as sites
        from vacancies group by 1 order by 3 desc
    """,
    "salary_overall": f"""
        select count(*) as vacancies,
               count(*) filter (where salary_status = 'DISCLOSED') as disclosed,
               count(*) filter (where salary_monthly_min is not null) as disclosed_monthly_idr,
               count(*) filter (where salary_template_site) as on_salary_template_sites,
               count(*) filter (where {_SALARY_OK}) as n,
               quantile_cont({_MIDPOINT}, [0.1, 0.25, 0.5, 0.75, 0.9]) filter (where {_SALARY_OK}) as percentiles
        from vacancies
    """,
    "salary_by_role_family": _salary_by("role_family"),
    "salary_by_province": _salary_by("province"),
    "salary_histogram": f"""
        select least(floor({_MIDPOINT} / 1000000), 30) * 1000000 as lower_bound, count(*) as vacancies
        from vacancies where {_SALARY_OK} group by 1 order by 1
    """,
    "skills_overall": f"""
        with described as (select * from vacancies where description_length >= {MIN_DESCRIPTION_CHARS})
        select skill, count(*) as vacancies, count(*) / (select count(*) from described) as share,
               (select count(*) from described) as denominator
        from (select unnest(skills) as skill from described) group by 1 order by 2 desc
    """,
    "skills_by_role_family": f"""
        with described as (select * from vacancies where description_length >= {MIN_DESCRIPTION_CHARS}),
             totals as (select role_family, count(*) as denominator from described group by 1)
        select role_family, skill, count(*) as vacancies, count(*) / any_value(denominator) as share,
               any_value(denominator) as denominator
        from (select role_family, unnest(skills) as skill from described) join totals using (role_family)
        group by all having count(*) >= 3 order by role_family, vacancies desc
    """,
    "postings_by_month": """
        select date_trunc('month', date_posted) as month, count(*) as vacancies
        from vacancies where date_posted is not null group by 1 order by 1
    """,
    "observation_lag": """
        select case when date_posted is null then 'unknown'
                    when lag_days <= 7 then '0-7 days' when lag_days <= 30 then '8-30 days'
                    when lag_days <= 90 then '31-90 days' when lag_days <= 365 then '91-365 days'
                    else '>1 year' end as posted_before_first_capture,
               count(*) as vacancies
        from (select date_posted, cast(first_seen_at as date) - date_posted as lag_days from vacancies)
        group by 1 order by 2 desc
    """,
    "sites": """
        select source_domain, site_type, count(*) as vacancies,
               count(*) filter (where salary_template_site) > 0 as salary_template_site
        from vacancies group by all order by 3 desc
    """,
}


def _scalar(con: duckdb.DuckDBPyConnection, sql: str) -> Any:
    return con.execute(sql).fetchone()[0]  # type: ignore[index]


def _coverage_by_crawl(lake: Lake) -> list[dict[str, Any]]:
    rows = []
    for discovery_file in sorted(
        (lake.bronze / "commoncrawl" / "candidates").glob("crawl=*/discovery.json")
    ):
        rows.append(json.loads(discovery_file.read_text("utf-8")))
    return rows


def _crawl_yield(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Per crawl, newest first (the collection order): how many canonical vacancies it
    contains, and how many of those no newer crawl had. The second column is the
    marginal value of collecting one more, older crawl."""
    rows = con.execute(
        """
        with membership as (
            select vacancy_id, unnest(crawls) as crawl from vacancies
        ), newest as (
            select vacancy_id, max(crawl) as newest_crawl from membership group by 1
        )
        select m.crawl,
               count(*) as vacancies,
               count(*) filter (where n.newest_crawl = m.crawl) as not_in_newer_crawls
        from membership m join newest n using (vacancy_id)
        group by 1 order by 1 desc
        """
    ).fetchall()
    return [
        {"crawl": crawl, "vacancies": total, "not_in_newer_crawls": new}
        for crawl, total, new in rows
    ]


def _domain_governance(con: duckdb.DuckDBPyConnection, lake: Lake) -> dict[str, Any]:
    """Archive observations per site-review status, including the sites silver excludes,
    so exclusions are counted rather than silently disappearing."""
    observations = (lake.silver / "observations" / "*.parquet").as_posix()
    rows = con.execute(
        f"select lower(source_domain), count(*) from read_parquet('{observations}') "
        f"where registry_source_id = '{COMMON_CRAWL_SOURCE_ID}' group by 1"
    ).fetchall()
    by_status: dict[str, dict[str, Any]] = {}
    for domain, count in rows:
        review = review_of(domain)
        status = (
            "excluded_portal"
            if domain in EXCLUDED_DOMAINS
            else review.status.value
            if review
            else "unreviewed"
        )
        entry = by_status.setdefault(status, {"domains": [], "observations": 0})
        entry["domains"].append(domain)
        entry["observations"] += count
    for entry in by_status.values():
        entry["domains"].sort()
    return {
        "reviewed_at": REVIEWED_AT,
        "usable_statuses": sorted(status.value for status in USABLE),
        "by_status": dict(sorted(by_status.items())),
    }


def build_gold(lake: Lake) -> dict[str, Any]:
    started = time.monotonic()
    con = duckdb.connect()
    silver = lake.silver
    con.execute(
        f"create view observations as select * from '{(silver / 'observations_all.parquet').as_posix()}'"
    )
    con.execute(
        f"create view source_records as select * from '{(silver / 'source_records.parquet').as_posix()}'"
    )
    con.execute(
        f"create view vacancies as select * from '{(silver / 'vacancies.parquet').as_posix()}'"
    )
    captures = (lake.bronze / "commoncrawl" / "captures" / "**" / "*.parquet").as_posix()
    con.execute(
        f"create view captures as select * from read_parquet('{captures}', hive_partitioning=false)"
    )

    lake.gold.mkdir(parents=True, exist_ok=True)
    for name, sql in TABLES.items():
        con.execute(
            f"copy ({sql}) to '{(lake.gold / f'{name}.parquet').as_posix()}' (format parquet)"
        )

    vacancies = _scalar(con, "select count(*) from vacancies")
    source_records = _scalar(con, "select count(*) from source_records")
    valid_records = _scalar(con, "select count(*) from source_records where is_valid")
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "versions": {"parser": PARSER_VERSION, "skills": SKILL_DICTIONARY_VERSION},
        "inventory": {
            "archived_pages_fetched": _scalar(
                con, "select count(*) from captures where fetch_result = 'ok'"
            ),
            "archived_pages_failed": _scalar(
                con, "select count(*) from captures where fetch_result <> 'ok'"
            ),
            "pages_with_jobposting": _scalar(
                con, "select count(*) from captures where jobposting_count > 0"
            ),
            "observations": _scalar(con, "select count(*) from observations"),
            "observations_from_unchanged_recaptures": _scalar(
                con, "select count(*) from observations where observation_type = 'reobservation'"
            ),
            "valid_observations": _scalar(con, "select count(*) from observations where is_valid"),
            "source_records": source_records,
            "valid_source_records": valid_records,
            "canonical_vacancies": vacancies,
            "duplicate_rate_records_to_vacancies": round(1 - vacancies / valid_records, 4)
            if valid_records
            else None,
            "vacancies_on_multiple_sites": _scalar(
                con, "select count(*) from vacancies where source_sites > 1"
            ),
            "vacancies_with_fuzzy_merge": _scalar(
                con, "select count(*) from vacancies where merged_fuzzy"
            ),
            "city_templated_campaigns": _scalar(
                con, "select count(*) from vacancies where city_templated"
            ),
            "deadline_template_sites": [
                row[0]
                for row in con.execute(
                    "select distinct source_domain from source_records "
                    "where deadline_template_site order by 1"
                ).fetchall()
            ],
            "vacancies_with_template_deadline": _scalar(
                con,
                "select count(*) from vacancies where valid_through is not null "
                "and not valid_through_reliable",
            ),
            "vacancies_seen_in_multiple_crawls": _scalar(
                con, "select count(*) from vacancies where len(crawls) > 1"
            ),
            "distinct_employers": _scalar(
                con, "select count(distinct organization_key) from vacancies"
            ),
            "distinct_sites": _scalar(con, "select count(distinct source_domain) from vacancies"),
        },
        "completeness_of_vacancies": {
            field: _scalar(con, f"select round(avg(({expr})::int), 4) from vacancies")
            for field, expr in {
                "province": "province is not null",
                "city": "city is not null",
                "date_posted": "date_posted is not null",
                "valid_through": "valid_through is not null",
                "valid_through_reliable": "valid_through_reliable",
                "salary_disclosed": "salary_status = 'DISCLOSED'",
                "salary_reliable_monthly_idr": _SALARY_OK,
                "description_100_chars": f"description_length >= {MIN_DESCRIPTION_CHARS}",
                "canonical_url": "canonical_url is not null",
                "source_identifier": "source_identifier is not null",
                "employment_type": "employment_type <> 'UNKNOWN'",
                "education": "education_level <> 'UNKNOWN'",
            }.items()
        },
        "time_coverage": {
            "first_capture": _scalar(con, "select min(first_seen_at)::varchar from vacancies"),
            "last_capture": _scalar(con, "select max(last_seen_at)::varchar from vacancies"),
            "earliest_date_posted": _scalar(con, "select min(date_posted)::varchar from vacancies"),
            "latest_date_posted": _scalar(con, "select max(date_posted)::varchar from vacancies"),
            "crawls_with_data": _scalar(con, "select count(distinct crawl) from observations"),
            "expired_at_last_capture_share": _scalar(
                con,
                "select round(avg((valid_through < cast(last_seen_at as date))::int), 4) from vacancies "
                "where valid_through_reliable",
            ),
        },
        "invalid_reasons": dict(
            con.execute(
                "select r, count(*) from (select unnest(invalid_reasons) r from source_records) group by 1 order by 2 desc"
            ).fetchall()
        ),
        "quality_flags": dict(
            con.execute(
                "select f, count(*) from (select unnest(quality_flags) f from source_records) group by 1 order by 2 desc"
            ).fetchall()
        ),
        "source_mix": dict(
            con.execute("select site_type, count(*) from vacancies group by 1").fetchall()
        ),
        "top10_sites_share": _scalar(
            con,
            "select round(sum(n) / (select count(*) from vacancies), 4) from "
            "(select count(*) n from vacancies group by source_domain order by n desc limit 10)",
        )
        if vacancies
        else None,
        "discovery_by_crawl": _coverage_by_crawl(lake),
        "crawl_yield": _crawl_yield(con),
        "domain_governance": _domain_governance(con, lake),
        "geography": {
            "provinces_with_vacancies": _scalar(
                con, "select count(distinct province) from vacancies where province is not null"
            ),
            "cities_with_vacancies": _scalar(
                con, "select count(distinct city) from vacancies where city is not null"
            ),
            "top5_provinces_share": _scalar(
                con,
                "select round(sum(n) / (select count(*) from vacancies where province is not null), 4) "
                "from (select count(*) n from vacancies where province is not null "
                "group by province order by n desc limit 5)",
            )
            if vacancies
            else None,
        },
        "seconds": None,
    }
    report["seconds"] = round(time.monotonic() - started, 1)
    (lake.gold / "report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    logger.info("gold built", extra={"vacancies": vacancies, "seconds": report["seconds"]})
    return report


def read_table(lake: Lake, name: str) -> Path:
    return lake.gold / f"{name}.parquet"
