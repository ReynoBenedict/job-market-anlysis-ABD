# Benchmarks

Two kinds of measurements, never mixed:
1. **Engine benchmark on SYNTHETIC data:** DuckDB versus Spark (local mode) at sizes the
   real dataset has not reached. The generated rows are not vacancies and are not counted
   anywhere.
2. **Real pipeline timings:** the actual Common Crawl collection and the silver, gold,
   and publish runs on the real lake (section 2).

Machine: Windows 11, 20 logical CPUs, 31.6 GB RAM, local SSD. Python 3.10,
DuckDB 1.5.6, PySpark 3.5.1 (local[*], 8 GB driver, 64 shuffle partitions).

## 1. Engine benchmark (synthetic)

**Reproduce:** `pip install -e "backend[bench]"`, then
`talentscope lake benchmark --sizes 10000 100000 500000 1000000 5000000`.
Code: `backend/talentscope/lake/benchmark.py`. Output, labelled SYNTHETIC:
`lake/synthetic/benchmark/results.json`.

**Data:** rows shaped like silver source records (employer, title and place keys, anchor
date, province, role family, monthly salary, skills list). About 20% of rows are
near-copies of another row, so deduplication has real work. Written once per size as
zstd Parquet: 10k = 0.2 MB, 100k = 1.4 MB, 500k = 7.5 MB, 1M = 15 MB, 5M = 79.5 MB.

**Workloads** (the same SQL on both engines):
- *aggregate*: counts by province and by role family, exact salary quartiles per role
  family, skill frequencies via unnest/explode (the gold layer's shape);
- *dedupe*: exact-key grouping with gap-based sessionization (`lag` window plus running
  sum), the first and heaviest step of silver deduplication.

**Method:** each workload reads the Parquet file from disk and materializes its results.
Wall-clock time per workload. Peak resident memory of the process tree (Python plus
Spark's JVM) is sampled every 50 ms. DuckDB runs before Spark starts, so the JVM does
not inflate DuckDB's memory. Spark gets one unrecorded warm-up pass; its session startup
is reported separately (6.1 s). Single run per cell (run 2, 2026-10-17 16:05 WIB),
measured while the polite collector was running in the background (network-bound, about
1 request/s). An earlier run 1 without the 500k size gave figures within ±15%
(DuckDB 5M dedupe 3.17 s, Spark 5M dedupe 5.87 s).

| Rows | DuckDB aggregate | DuckDB dedupe | Spark aggregate | Spark dedupe |
|---:|---|---|---|---|
| 10,000 | 0.03 s / 89 MB | 0.05 s / 92 MB | 1.65 s / 969 MB | 1.00 s / 958 MB |
| 100,000 | 0.04 s / 96 MB | 0.09 s / 139 MB | 1.57 s / 1.0 GB | 1.32 s / 1.1 GB |
| 500,000 | 0.09 s / 110 MB | 0.38 s / 206 MB | 2.01 s / 1.2 GB | 1.46 s / 1.4 GB |
| 1,000,000 | 0.17 s / 132 MB | 0.70 s / 334 MB | 2.22 s / 1.8 GB | 2.11 s / 2.2 GB |
| 5,000,000 | 0.45 s / 183 MB | 2.97 s / 939 MB | 4.50 s / 2.4 GB | 5.81 s / 3.8 GB |

**Reading the results**
- DuckDB is faster and uses less memory at every size measured. At 5M rows it is
  10× faster on aggregation and 2× faster on deduplication.
- Spark's time is nearly flat up to 1M rows: it is dominated by fixed scheduling
  overhead, plus 6 s to start a session. The gap narrows as data grows; DuckDB's
  dedupe grows roughly linearly (0.70 s → 2.97 s for 5×).
- Extrapolating linearly (an estimate, not a measurement), DuckDB dedupe would take
  ≈30 s and a few GB at 50M rows. Spark becomes the better tool when data no longer fits
  one machine, or a cluster is already available.
- **Not measured:** the fuzzy-title merge (it runs per employer+place block and is small
  relative to the exact step), Spark on a cluster, and anything over 5M rows.

**Decision:** DuckDB for silver and gold (ADR-0015). The benchmark runs the same SQL
on both engines, so the move to Spark is a known path, not a rewrite.

## 2. Real pipeline timings

See [DATA_INVENTORY.md](DATA_INVENTORY.md) §"Run log" for the measured collection
throughput, the silver, gold, and publish durations on the real lake, and storage on disk.
