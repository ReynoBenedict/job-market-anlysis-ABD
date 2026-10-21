"""Find candidate job pages for one crawl in Common Crawl's columnar index.

The index is ~300 Parquet files per crawl, each sorted by SURT key ("id,co,acme)/karir").
All pages under the .id top-level domain therefore share the key prefix "id," and sit in
two or three files. We read every file's footer statistics once to find them, then scan
only those files, letting DuckDB skip row groups outside the key range.
"""

from __future__ import annotations

import gzip
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.request import urlopen

import duckdb

from talentscope.lake.commoncrawl import ARCHIVE_ROOT, INDEX_SERVER
from talentscope.lake.domains import EXCLUDED_DOMAINS

logger = logging.getLogger(__name__)

TLD_KEY_START = "id,"
TLD_KEY_END = "id-"  # the next possible key after every "id,..." key
# Words in Indonesian and English job URLs. Broad on purpose: pages without JobPosting
# markup are discarded after download, and per-domain yield tracking stops wasted fetches.
JOB_URL_PATTERN = r"(lowongan|loker|karir|career|/jobs?/|/job-|vacanc|rekrutmen|recruit|hiring)"
HTTP_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class DiscoveryStats:
    crawl: str
    index_files_scanned: int
    tld_pages: int
    job_like_pages: int
    excluded_by_domain_policy: int
    candidates: int
    seconds: float


def list_crawls() -> list[str]:
    """Crawl IDs, newest first, from Common Crawl's index server."""
    with urlopen(f"{INDEX_SERVER}/collinfo.json", timeout=HTTP_TIMEOUT_SECONDS) as response:
        return [entry["id"] for entry in json.load(response)]


def _index_files(crawl: str) -> list[str]:
    url = f"{ARCHIVE_ROOT}/crawl-data/{crawl}/cc-index-table.paths.gz"
    with urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as response:
        paths = gzip.decompress(response.read()).decode().split()
    return [f"{ARCHIVE_ROOT}/{path}" for path in paths if "/subset=warc/" in path]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET http_retries = 5; SET http_retry_wait_ms = 2000")
    return con


def files_covering_tld(con: duckdb.DuckDBPyConnection, files: list[str]) -> list[str]:
    """Index files whose url_surtkey range overlaps the .id key range (footers only)."""
    file_list = ", ".join(f"'{f}'" for f in files)
    rows = con.execute(
        f"""
        select file_name
        from parquet_metadata([{file_list}])
        where path_in_schema = 'url_surtkey'
        group by file_name
        having max(stats_max_value) >= ? and min(stats_min_value) < ?
        """,
        [TLD_KEY_START, TLD_KEY_END],
    ).fetchall()
    return [row[0] for row in rows]


def discover(con: duckdb.DuckDBPyConnection, crawl: str, output: Path) -> DiscoveryStats:
    """Write the crawl's candidate job pages to ``output`` (Parquet) and return counts."""
    started = time.monotonic()
    files = files_covering_tld(con, _index_files(crawl))
    if not files:
        raise RuntimeError(
            f"no index file covers the .id key range in {crawl}; index layout changed?"
        )
    file_list = ", ".join(f"'{f}'" for f in files)
    excluded = ", ".join(f"'{d}'" for d in sorted(EXCLUDED_DOMAINS))

    con.execute(
        f"""
        create or replace temp table tld_pages as
        select url, url_host_registered_domain as domain, fetch_time, fetch_status,
               content_mime_detected as mime, content_digest, warc_filename,
               warc_record_offset, warc_record_length
        from read_parquet([{file_list}])
        where url_surtkey >= '{TLD_KEY_START}' and url_surtkey < '{TLD_KEY_END}'
        """
    )
    con.execute(
        f"""
        create or replace temp table job_like as
        select * from tld_pages
        where fetch_status = 200 and mime = 'text/html'
          and regexp_matches(lower(url), '{JOB_URL_PATTERN}')
        """
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"""
        copy (
            select '{crawl}' as crawl, url, domain, fetch_time, content_digest,
                   warc_filename, warc_record_offset, warc_record_length
            from job_like
            where domain is not null and lower(domain) not in ({excluded})
            order by domain, url
        ) to '{output.as_posix()}' (format parquet, compression zstd)
        """
    )
    tld_pages = con.execute("select count(*) from tld_pages").fetchone()[0]  # type: ignore[index]
    job_like = con.execute("select count(*) from job_like").fetchone()[0]  # type: ignore[index]
    candidates = con.execute(f"select count(*) from '{output.as_posix()}'").fetchone()[0]  # type: ignore[index]
    stats = DiscoveryStats(
        crawl=crawl,
        index_files_scanned=len(files),
        tld_pages=tld_pages,
        job_like_pages=job_like,
        excluded_by_domain_policy=job_like - candidates,
        candidates=candidates,
        seconds=round(time.monotonic() - started, 1),
    )
    output.with_name("discovery.json").write_text(
        json.dumps(asdict(stats), indent=2), encoding="utf-8"
    )
    logger.info("discovery finished", extra=asdict(stats))
    return stats
