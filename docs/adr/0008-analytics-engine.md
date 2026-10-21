# ADR-0008: Analytics engine and the role of Spark

**Status:** accepted (2026-10-17)

## Context
The academic project used PySpark for five SQL aggregates and MLlib K-Means. The data is
1,133 rows. Spark local mode needs a JVM and ~9 s to start.

## Decision
- Online analytics (breakdowns, percentiles, histograms) are PostgreSQL queries computed
  per request. Measured on 2026-10-17 against the Compose stack on a laptop (10 sequential
  requests per endpoint, localhost): medians 12–33 ms, maximum 87 ms. Precomputation and
  caching add nothing yet.
- Spark is kept as a **batch** tool: `analytics/evaluate_title_clustering.py` reproduces
  and re-evaluates the MLlib experiment (docs/ML_EVALUATION.md). It is never called from
  the API or web request path.
- The original scripts remain runnable under `legacy/academic_pipeline/`.

## Consequences
- The deployed stack needs no JVM. Revisit Spark (or DuckDB/Polars) for batch analytics
  when the dataset grows to millions of observations or multi-snapshot history.
