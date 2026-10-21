"""Engine benchmark: DuckDB vs. Spark (local mode) on the lake's two heavy workloads.

All data here is SYNTHETIC: generated rows shaped like silver source records, written
under lake/synthetic/, never read by silver/gold, and never counted as real vacancies.
Results are written to lake/synthetic/benchmark/results.json.

Workloads (the same SQL semantics on both engines):
  aggregate  counts by province and role family, exact salary quartiles per role family,
             and skill frequencies (unnest), i.e. the gold layer's shape
  dedupe     exact-key grouping with gap-based sessionization (window lag + running sum),
             i.e. the first step of silver deduplication
"""

from __future__ import annotations

import json
import platform
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import psutil

from talentscope.lake.layout import Lake

SEED = 0.42
DUPLICATE_SHARE = 0.2

AGGREGATE_SQL = [
    "select province, count(*) from {t} group by 1",
    "select role_family, count(*) from {t} group by 1",
    "select role_family, {q} from {t} where salary_reliable group by 1",
    "select skill, count(*) from (select explode_skills from {t}) group by 1",
]
DEDUPE_SQL = """
    select count(distinct grp) from (
        select organization_key, title_key, place_key,
               sum(case when gap is null or gap > 45 then 1 else 0 end)
                   over (partition by organization_key, title_key, place_key order by anchor_date, source_record_key) as grp
        from (
            select *, {datediff} as gap from {t}
        )
    )
"""


@dataclass
class Measurement:
    engine: str
    rows: int
    workload: str
    seconds: float
    peak_rss_mb: float


class _PeakMemory:
    """Samples resident memory of this process and its children (e.g. Spark's JVM)."""

    def __init__(self, interval: float = 0.05) -> None:
        self._interval = interval
        self._stop = threading.Event()
        self.peak = 0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        process = psutil.Process()
        while not self._stop.is_set():
            try:
                total = process.memory_info().rss + sum(
                    c.memory_info().rss for c in process.children(recursive=True)
                )
            except psutil.Error:
                total = 0
            self.peak = max(self.peak, total)
            time.sleep(self._interval)

    def __enter__(self) -> _PeakMemory:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join()


def generate(path: Path, rows: int) -> None:
    """Write `rows` synthetic source records (about DUPLICATE_SHARE of them near-copies)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"select setseed({SEED})")
    base = int(rows * (1 - DUPLICATE_SHARE))
    con.execute(
        f"""
        copy (
            with base as (
                select i,
                       'synthetic-' || i as source_record_key,
                       'site' || (i % 2000) || '.id' as source_domain,
                       'org' || (hash(i) % greatest({base} // 8, 1)) as organization_key,
                       'title' || (hash(i * 7) % 400) as title_key,
                       'city' || (hash(i * 13) % 500) as place_key,
                       'province' || (hash(i * 17) % 38) as province,
                       'family' || (hash(i * 19) % 20) as role_family,
                       date '2023-01-01' + cast(random() * 1000 as integer) as anchor_date,
                       2000000 + cast(random() * 15000000 as bigint) as salary_monthly_min,
                       random() < 0.3 as salary_reliable,
                       [('skill' || cast(random() * 80 as integer)) for x in range(cast(random() * 5 as integer))] as skills
                from range({base}) t(i)
            ),
            copies as (
                select * replace ('synthetic-copy-' || i as source_record_key,
                                  anchor_date + cast(random() * 10 as integer) as anchor_date)
                from base using sample {rows - base} rows (reservoir, 7)
            )
            select * exclude (i) from base union all select * exclude (i) from copies
        ) to '{path.as_posix()}' (format parquet, compression zstd)
        """
    )


def _timed(engine: str, rows: int, workload: str, action: Callable[[], None]) -> Measurement:
    with _PeakMemory() as memory:
        started = time.perf_counter()
        action()
        seconds = time.perf_counter() - started
    return Measurement(engine, rows, workload, round(seconds, 3), round(memory.peak / 2**20, 1))


def run_duckdb(path: Path, rows: int) -> list[Measurement]:
    def aggregate() -> None:
        con = duckdb.connect()
        table = f"read_parquet('{path.as_posix()}')"
        for sql in AGGREGATE_SQL:
            con.execute(
                sql.format(
                    t=table,
                    q="quantile_cont(salary_monthly_min, [0.25, 0.5, 0.75])",
                ).replace("explode_skills", "unnest(skills) as skill")
            ).fetchall()

    def dedupe() -> None:
        table = (
            f"(select *, anchor_date - lag(anchor_date) over (partition by organization_key, title_key, place_key "
            f"order by anchor_date, source_record_key) as lagdiff from read_parquet('{path.as_posix()}'))"
        )
        duckdb.connect().execute(DEDUPE_SQL.format(t=table, datediff="lagdiff")).fetchall()

    return [
        _timed("duckdb", rows, "aggregate", aggregate),
        _timed("duckdb", rows, "dedupe", dedupe),
    ]


def run_spark(path: Path, rows: int, spark: object) -> list[Measurement]:
    from pyspark.sql import SparkSession

    assert isinstance(spark, SparkSession)

    def aggregate() -> None:
        spark.read.parquet(path.as_posix()).createOrReplaceTempView("records")
        for sql in AGGREGATE_SQL:
            spark.sql(
                sql.format(
                    t="records",
                    q="percentile(salary_monthly_min, array(0.25, 0.5, 0.75))",
                ).replace("explode_skills", "explode(skills) as skill")
            ).collect()

    def dedupe() -> None:
        spark.read.parquet(path.as_posix()).createOrReplaceTempView("records")
        table = (
            "(select *, datediff(anchor_date, lag(anchor_date) over (partition by organization_key, title_key, "
            "place_key order by anchor_date, source_record_key)) as lagdiff from records)"
        )
        spark.sql(DEDUPE_SQL.format(t=table, datediff="lagdiff")).collect()

    return [
        _timed("spark-local", rows, "aggregate", aggregate),
        _timed("spark-local", rows, "dedupe", dedupe),
    ]


def _start_spark() -> object:
    import os
    import sys

    from pyspark.sql import SparkSession

    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    spark = (
        SparkSession.builder.master("local[*]")
        .appName("talentscope-benchmark")
        .config("spark.driver.memory", "8g")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "64")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def run_benchmark(lake: Lake, sizes: list[int], *, with_spark: bool) -> dict[str, object]:
    """DuckDB runs first, before any JVM exists, so its memory figures are not inflated
    by Spark. Spark then gets one unrecorded warm-up run (JIT, class loading)."""
    out_dir = lake.synthetic / "benchmark"
    paths = {}
    for rows in sizes:
        paths[rows] = out_dir / f"synthetic_records_{rows}.parquet"
        if not paths[rows].exists():
            generate(paths[rows], rows)

    measurements: list[Measurement] = []
    for rows in sizes:
        measurements += run_duckdb(paths[rows], rows)

    spark_startup = None
    if with_spark:
        started = time.perf_counter()
        spark = _start_spark()
        spark_startup = round(time.perf_counter() - started, 1)
        try:
            run_spark(paths[min(sizes)], min(sizes), spark)  # warm-up, not recorded
            for rows in sizes:
                measurements += run_spark(paths[rows], rows, spark)
        finally:
            spark.stop()  # type: ignore[attr-defined]

    result: dict[str, object] = {
        "data": "SYNTHETIC — generated for performance measurement only; not real vacancies",
        "machine": {
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / 2**30, 1),
            "platform": platform.platform(),
            "duckdb": duckdb.__version__,
        },
        "spark_session_startup_seconds": spark_startup,
        "parquet_size_mb": {
            rows: round(path.stat().st_size / 2**20, 1) for rows, path in paths.items()
        },
        "measurements": [asdict(m) for m in measurements],
    }
    (out_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
