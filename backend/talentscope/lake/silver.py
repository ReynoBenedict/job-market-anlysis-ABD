"""Bronze → silver: parsed observations, source records, and canonical vacancies.

Levels of counting (each is a separate table, so reports never mix them up):

observations     every JobPosting object in every capture, including unchanged
                 re-captures recorded from the index (same URL and content digest)
source_records   one per (site, posting identity): the site's identifier when it gives
                 one, otherwise page URL + position. Repeated captures collapse here.
vacancies        canonical openings after deduplicating reposts, syndication across sites,
                 and near-identical titles (see `deduplicate`).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from talentscope.lake.domain_reviews import usable_domains
from talentscope.lake.domains import EXCLUDED_DOMAINS, site_type
from talentscope.lake.layout import Lake
from talentscope.lake.postings import PARSER_VERSION, normalize_posting
from talentscope.lake.skills import SKILL_DICTIONARY_VERSION
from talentscope.normalization.salary import IDR_MONTHLY_LOW_OUTLIER
from talentscope.sources import COMMON_CRAWL_SOURCE_ID

logger = logging.getLogger(__name__)

OBSERVATION_SCHEMA = pa.schema(
    [
        ("observation_type", pa.string()),
        ("registry_source_id", pa.string()),
        ("crawl", pa.string()),
        ("captured_at", pa.timestamp("us", tz="UTC")),
        ("bronze_file", pa.string()),
        ("warc_filename", pa.string()),
        ("warc_record_offset", pa.int64()),
        ("content_digest", pa.string()),
        ("source_record_key", pa.string()),
        ("record_key_kind", pa.string()),
        ("source_domain", pa.string()),
        ("site_type", pa.string()),
        ("canonical_url", pa.string()),
        ("page_url", pa.string()),
        ("posting_position", pa.int32()),
        ("source_identifier", pa.string()),
        ("title", pa.string()),
        ("source_title", pa.string()),
        ("title_key", pa.string()),
        ("organization", pa.string()),
        ("organization_key", pa.string()),
        ("role_family", pa.string()),
        ("city", pa.string()),
        ("province", pa.string()),
        ("locality_raw", pa.string()),
        ("region_raw", pa.string()),
        ("country_raw", pa.string()),
        ("location_count", pa.int32()),
        ("provinces", pa.list_(pa.string())),
        ("employment_type_raw", pa.string()),
        ("employment_type", pa.string()),
        ("work_arrangement", pa.string()),
        ("experience_min_years", pa.int32()),
        ("education_level", pa.string()),
        ("date_posted", pa.date32()),
        ("valid_through", pa.date32()),
        ("salary_status", pa.string()),
        ("salary_currency", pa.string()),
        ("salary_unit_raw", pa.string()),
        ("salary_period", pa.string()),
        ("salary_min", pa.int64()),
        ("salary_max", pa.int64()),
        ("salary_monthly_min", pa.int64()),
        ("salary_monthly_max", pa.int64()),
        ("description_length", pa.int32()),
        ("description_sha1", pa.string()),
        ("skills", pa.list_(pa.string())),
        ("is_valid", pa.bool_()),
        ("invalid_reasons", pa.list_(pa.string())),
        ("quality_flags", pa.list_(pa.string())),
        ("parser_version", pa.string()),
    ]
)

# Bump when the observation file naming or manifest keys change (forces a reparse).
MANIFEST_LAYOUT = 2

# A repost or syndicated copy is merged with an earlier record of the same opening only
# if both were posted (or, without a posting date, first seen) within this many days.
# City-templated campaigns are not split by this window (see `deduplicate`).
SAME_OPENING_WINDOW_DAYS = 45
# Near-duplicate titles inside one employer + place block (Jaro-Winkler similarity).
FUZZY_TITLE_THRESHOLD = 0.93
# One site posting the same employer + role for this many places is treated as one
# city-templated campaign (SEO pages per city), counted once with no single place.
TEMPLATED_PLACES_THRESHOLD = 5
# ... and at least this share of its pages show one identical salary (or all show none).
CAMPAIGN_SAME_SALARY_SHARE = 0.8
# A site whose disclosed salaries are mostly one identical range is using a theme default,
# so none of its salaries are used in statistics.
SALARY_TEMPLATE_MIN_RECORDS = 10
SALARY_TEMPLATE_SHARE = 0.5
# Why a disclosed monthly IDR salary is not used (`salary_unreliable_reason`). The floor
# is the same one the API's salary statistics apply (monthly midpoint below Rp500,000).
SALARY_SITE_TEMPLATE = "SITE_TEMPLATE"
SALARY_BELOW_MONTHLY_FLOOR = "BELOW_MONTHLY_FLOOR"
# A site whose validThrough values are mostly one theme default is not stating real
# application deadlines: either one identical date on at least this share of its pages,
# or one identical number of days after datePosted on at least this share. Measured
# 2026-10-18 on usable sites: defaults at 100% (bisakerja.id, mediaanalisindonesia.co.id:
# one fixed date) and 29% (lokerbekasi.my.id: +60 days); every other site with >= 20
# deadlines peaks at <= 20% for a date and <= 17% for an offset.
DEADLINE_TEMPLATE_MIN_RECORDS = 20
DEADLINE_TEMPLATE_SHARE = 0.25


@dataclass
class SilverStats:
    bronze_files_parsed: int
    observations: int
    valid_observations: int
    source_records: int
    vacancies: int
    seconds: float


def _parse_bronze_file(path: Path, registry_source: str) -> pa.Table:
    rows = []
    table = pq.read_table(
        path,
        columns=[
            "crawl",
            "url",
            "domain",
            "captured_at",
            "warc_filename",
            "warc_record_offset",
            "content_digest",
            "fetch_result",
            "postings_json",
        ],
    )
    for capture in table.to_pylist():
        if capture["fetch_result"] != "ok" or not capture["postings_json"]:
            continue
        for position, posting in enumerate(json.loads(capture["postings_json"])):
            parsed = normalize_posting(
                posting,
                page_url=capture["url"],
                domain=capture["domain"],
                captured_at=capture["captured_at"],
                position=position,
            )
            rows.append(
                {
                    **parsed.values,
                    "observation_type": "capture",
                    "crawl": capture["crawl"],
                    "captured_at": capture["captured_at"],
                    "bronze_file": path.name,
                    "warc_filename": capture["warc_filename"],
                    "warc_record_offset": capture["warc_record_offset"],
                    "content_digest": capture["content_digest"],
                    "site_type": site_type(capture["domain"]),
                    "registry_source_id": registry_source,
                    "is_valid": not parsed.invalid_reasons,
                    "invalid_reasons": parsed.invalid_reasons,
                    "quality_flags": parsed.quality_flags,
                }
            )
    return pa.Table.from_pylist(rows, schema=OBSERVATION_SCHEMA)


def bronze_files(lake: Lake) -> list[tuple[Path, str]]:
    """Every bronze capture file with the registry source it belongs to."""
    files = [
        (path, COMMON_CRAWL_SOURCE_ID)
        for path in sorted((lake.bronze / "commoncrawl" / "captures").glob("crawl=*/*.parquet"))
    ]
    imports_root = lake.bronze / "imports"
    if imports_root.exists():
        for source_dir in sorted(p for p in imports_root.iterdir() if p.is_dir()):
            files += [(path, source_dir.name) for path in sorted(source_dir.glob("*.parquet"))]
    return files


def parse_bronze(lake: Lake, *, full: bool = False) -> int:
    """Parse new bronze capture files into silver/observations; returns files parsed."""
    out_dir = lake.silver / "observations"
    manifest_path = lake.state / "silver_manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8")) if manifest_path.exists() else {}
    versions_changed = (
        manifest.get("parser_version") != PARSER_VERSION
        or manifest.get("skills_version") != SKILL_DICTIONARY_VERSION
        or manifest.get("layout") != MANIFEST_LAYOUT
    )
    if full or versions_changed:
        for old in out_dir.glob("*.parquet"):
            old.unlink()
        manifest = {
            "parser_version": PARSER_VERSION,
            "skills_version": SKILL_DICTIONARY_VERSION,
            "layout": MANIFEST_LAYOUT,
            "files": [],
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    done = set(manifest["files"])
    parsed = 0
    for path, registry_source in bronze_files(lake):
        key = f"{registry_source}/{path.parent.name}/{path.name}"
        if key in done:
            continue
        pq.write_table(
            _parse_bronze_file(path, registry_source),
            out_dir / f"{registry_source}__{path.parent.name}__{path.stem}.parquet",
            compression="zstd",
        )
        manifest["files"].append(key)
        parsed += 1
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return parsed


def build_silver(lake: Lake, *, full: bool = False) -> SilverStats:
    started = time.monotonic()
    parsed_files = parse_bronze(lake, full=full)
    con = duckdb.connect()
    observations = (lake.silver / "observations" / "*.parquet").as_posix()
    reobservations = lake.bronze / "commoncrawl" / "reobservations"

    # The site policy applies here too, so a site added to EXCLUDED_DOMAINS later (e.g. an
    # owner opt-out) disappears from silver and gold on the next build. Archived pages
    # additionally need a per-site review with a usable status (default deny); licensed
    # imports carry their own registry decision instead.
    excluded = ", ".join(f"'{domain}'" for domain in sorted(EXCLUDED_DOMAINS))
    usable = ", ".join(f"'{domain}'" for domain in usable_domains()) or "''"
    con.execute(
        f"create view captures as select * from read_parquet('{observations}') "
        f"where lower(source_domain) not in ({excluded}) "
        f"and (registry_source_id <> '{COMMON_CRAWL_SOURCE_ID}' or lower(source_domain) in ({usable}))"
    )
    if any(reobservations.glob("**/*.parquet")):
        # An unchanged re-capture repeats the postings of the earliest capture with the
        # same URL and digest, observed at the re-capture's time.
        con.execute(
            f"""
            create view all_observations as
            select * from captures
            union all
            select c.* replace ('reobservation' as observation_type, r.crawl as crawl,
                              r.index_fetch_time as captured_at, null as bronze_file)
            from (select distinct crawl, url, content_digest, index_fetch_time
                  from read_parquet('{(reobservations / "**" / "*.parquet").as_posix()}', hive_partitioning=false)) r
            join (select * from captures
                  qualify row_number() over (partition by page_url, content_digest, posting_position
                                             order by captured_at) = 1) c
              on c.content_digest = r.content_digest
             and c.page_url = r.url
            """
        )
    else:
        con.execute("create view all_observations as select * from captures")

    con.execute(
        """
        create or replace table source_records as
        select source_record_key,
               arg_max(columns(* exclude (source_record_key, observation_type, crawl, captured_at,
                                          bronze_file, warc_filename, warc_record_offset,
                                          content_digest)), (captured_at, content_digest, bronze_file)),
               min(captured_at) as first_seen_at,
               max(captured_at) as last_seen_at,
               count(*) as observations,
               count(distinct crawl) as crawls_observed,
               list(distinct crawl order by crawl) as crawls
        from all_observations
        group by source_record_key
        """
    )
    mark_salary_templates(con)
    mark_deadline_templates(con)
    vacancies = deduplicate(con)
    silver = lake.silver
    con.execute(
        f"copy all_observations to '{(silver / 'observations_all.parquet').as_posix()}' (format parquet, compression zstd)"
    )
    con.execute(
        f"copy source_records to '{(silver / 'source_records.parquet').as_posix()}' (format parquet, compression zstd)"
    )
    con.execute(
        f"copy vacancies to '{(silver / 'vacancies.parquet').as_posix()}' (format parquet, compression zstd)"
    )
    counts = con.execute(
        "select (select count(*) from all_observations), (select count(*) from all_observations where is_valid),"
        " (select count(*) from source_records)"
    ).fetchone()
    assert counts is not None
    stats = SilverStats(
        parsed_files,
        counts[0],
        counts[1],
        counts[2],
        vacancies,
        round(time.monotonic() - started, 1),
    )
    logger.info("silver built", extra=vars(stats))
    return stats


def mark_salary_templates(con: duckdb.DuckDBPyConnection) -> None:
    """Add `salary_reliable`, `salary_unreliable_reason` and `salary_template_site` to
    source_records. A disclosed monthly IDR salary is unreliable when its site uses a theme
    default (SALARY_TEMPLATE_SHARE) or its midpoint is below the monthly floor. Ranges with
    minimum > maximum never reach this point: the parser marks them INVALID."""
    con.execute(
        f"""
        create or replace temp table salary_templates as
        with pairs as (
            select source_domain, salary_monthly_min, salary_monthly_max, count(*) as n
            from source_records
            where is_valid and salary_monthly_min is not null
            group by all
        )
        select source_domain, sum(n) as disclosed, max(n) / sum(n) as top_share
        from pairs group by source_domain
        having sum(n) >= {SALARY_TEMPLATE_MIN_RECORDS} and max(n) / sum(n) >= {SALARY_TEMPLATE_SHARE}
        """
    )
    con.execute(
        f"""
        create or replace table source_records as
        select r.*,
               r.salary_monthly_min is not null and r.salary_unreliable_reason is null
                   as salary_reliable
        from (
            select r.*,
                   t.source_domain is not null as salary_template_site,
                   case when r.salary_monthly_min is null then null
                        when t.source_domain is not null then '{SALARY_SITE_TEMPLATE}'
                        when (r.salary_monthly_min + r.salary_monthly_max) / 2
                             < {IDR_MONTHLY_LOW_OUTLIER} then '{SALARY_BELOW_MONTHLY_FLOOR}'
                   end as salary_unreliable_reason
            from source_records r left join salary_templates t using (source_domain)
        ) r
        """
    )


def mark_deadline_templates(con: duckdb.DuckDBPyConnection) -> None:
    """Add `valid_through_reliable` and `deadline_template_site` to source_records.

    On a site whose validThrough is mostly a theme default (DEADLINE_TEMPLATE_SHARE), no
    deadline is treated as the employer's: they are kept as source values but must not be
    shown as application deadlines or mark a vacancy as expired.
    """
    con.execute(
        f"""
        create or replace temp table deadline_templates as
        with dated as (
            select source_domain, valid_through, valid_through - date_posted as days_after_posted
            from source_records
            where is_valid and valid_through is not null
        ),
        sites as (
            select source_domain, count(*) as deadlines from dated group by 1
        ),
        top_date as (
            select source_domain, max(n) as n
            from (select source_domain, valid_through, count(*) as n from dated group by all)
            group by 1
        ),
        top_offset as (
            select source_domain, max(n) as n
            from (select source_domain, days_after_posted, count(*) as n from dated
                  where days_after_posted is not null group by all)
            group by 1
        )
        select source_domain
        from sites
        left join top_date d using (source_domain)
        left join top_offset o using (source_domain)
        where deadlines >= {DEADLINE_TEMPLATE_MIN_RECORDS}
          and greatest(coalesce(d.n, 0), coalesce(o.n, 0)) / deadlines >= {DEADLINE_TEMPLATE_SHARE}
        """
    )
    con.execute(
        """
        create or replace table source_records as
        select r.*,
               r.valid_through is not null and t.source_domain is null as valid_through_reliable,
               t.source_domain is not null as deadline_template_site
        from source_records r left join deadline_templates t using (source_domain)
        """
    )


def deduplicate(con: duckdb.DuckDBPyConnection) -> int:
    """Group valid source records into canonical vacancies; returns the vacancy count.

    1. Exact: same employer key, normalized title key, and place (city, else province),
       posted within SAME_OPENING_WINDOW_DAYS of the group's previous record. Catches
       reposts on one site and the same vacancy syndicated to other sites.
    2. Fuzzy: inside an employer + place block, titles with Jaro-Winkler similarity
       >= FUZZY_TITLE_THRESHOLD and anchor dates within the window are merged too.
    3. Campaigns: city-templated copies (one site, one employer + role, many places, see
       TEMPLATED_PLACES_THRESHOLD) share the place key '*' and form one vacancy for their
       whole observed life. The window does not split them: their page dates record when
       the site generated pages, not separate hiring rounds.
    Records without an employer were already excluded as invalid. Different places stay
    different vacancies, so a genuinely multi-site hiring drive counts once per place.
    """
    con.execute(
        f"""
        create or replace temp table candidates as
        with base as (
            select source_record_key, source_domain, organization_key, title_key,
                   coalesce(lower(city), lower(province), '?') as place_key,
                   coalesce(date_posted, cast(first_seen_at as date)) as anchor_date,
                   coalesce(salary_min::varchar, '-') || '/' || coalesce(salary_max::varchar, '-') as salary_key
            from source_records
            where is_valid and title_key <> '' and organization_key <> ''
        ),
        -- A site repeating one employer + role across many places is an SEO campaign only
        -- when the pages are copies: nearly all show the same salary (or none). Different
        -- salaries per place mean genuine local openings (regional pay); they stay separate.
        salary_counts as (
            select source_domain, organization_key, title_key, salary_key, count(*) as n
            from base group by all
        ),
        groups as (
            select source_domain, organization_key, title_key,
                   max(n) / sum(n) as top_salary_share,
                   any_value(places) as places
            from salary_counts
            join (select source_domain, organization_key, title_key, count(distinct place_key) as places
                  from base group by all) using (source_domain, organization_key, title_key)
            group by all
        )
        select * replace (case when templated then '*' else place_key end as place_key), templated
        from (
            select b.*,
                   coalesce(g.places >= {TEMPLATED_PLACES_THRESHOLD}
                            and g.top_salary_share >= {CAMPAIGN_SAME_SALARY_SHARE}, false) as templated
            from base b left join groups g using (source_domain, organization_key, title_key)
        )
        """
    )
    # Exact groups, split into openings where consecutive anchor dates are too far apart
    # (except campaigns, which stay one group).
    con.execute(
        f"""
        create or replace temp table exact_groups as
        with ordered as (
            select *, anchor_date - lag(anchor_date) over w as gap
            from candidates
            window w as (partition by organization_key, title_key, place_key order by anchor_date, source_record_key)
        )
        select *, organization_key || '|' || title_key || '|' || place_key || '|' ||
               sum(case when gap is null or (gap > {SAME_OPENING_WINDOW_DAYS} and not templated)
                        then 1 else 0 end)
                   over (partition by organization_key, title_key, place_key order by anchor_date, source_record_key)
               as exact_group
        from ordered
        """
    )
    group_rows = con.execute(
        "select exact_group, organization_key, place_key, title_key, min(anchor_date) "
        "from exact_groups group by all"
    ).fetchall()
    parent = {row[0]: row[0] for row in group_rows}

    def find(group: str) -> str:
        while parent[group] != group:
            parent[group] = parent[parent[group]]
            group = parent[group]
        return group

    pairs = con.execute(
        f"""
        with groups as (
            select exact_group, organization_key, place_key, title_key, min(anchor_date) as anchor
            from exact_groups group by all
        )
        select a.exact_group, b.exact_group
        from groups a join groups b
          on a.organization_key = b.organization_key and a.place_key = b.place_key
         and a.exact_group < b.exact_group and a.title_key <> b.title_key
        where jaro_winkler_similarity(a.title_key, b.title_key) >= {FUZZY_TITLE_THRESHOLD}
          and (a.place_key = '*' or abs(a.anchor - b.anchor) <= {SAME_OPENING_WINDOW_DAYS})
        """
    ).fetchall()
    for left, right in pairs:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[max(root_left, root_right)] = min(root_left, root_right)

    mapping = pa.table({"exact_group": list(parent), "vacancy_group": [find(g) for g in parent]})
    con.register("group_mapping", mapping)
    con.execute(
        """
        create or replace table vacancies as
        with members as (
            select r.*, m.vacancy_group, g.templated
            from source_records r
            join exact_groups g using (source_record_key)
            join group_mapping m using (exact_group)
        )
        select md5(min(source_record_key)) as vacancy_id,
               arg_min(columns(* exclude (vacancy_group, source_record_key, first_seen_at, last_seen_at,
                                          observations, crawls_observed, crawls, templated)),
                       -- full tiebreak so a rebuild always picks the same representative
                       (coalesce(date_posted, cast(first_seen_at as date)), first_seen_at, source_record_key)),
               min(first_seen_at) as first_seen_at,
               max(last_seen_at) as last_seen_at,
               count(*) as source_records,
               count(distinct source_domain) as source_sites,
               sum(observations) as observations,
               list(distinct source_domain order by source_domain) as sites,
               list(source_record_key order by source_record_key) as member_keys,
               list_sort(list_distinct(flatten(list(crawls)))) as crawls,
               count(distinct title_key) > 1 as merged_fuzzy,
               bool_or(templated) as city_templated
        from members
        group by vacancy_group
        """
    )
    count = con.execute("select count(*) from vacancies").fetchone()
    assert count is not None
    return int(count[0])
