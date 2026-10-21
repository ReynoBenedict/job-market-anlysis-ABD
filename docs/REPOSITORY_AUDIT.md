# Repository audit (baseline before TalentScope)

Read-only audit performed 2026-10-17 on commit `733008e`, before any change. Summary of
verified findings; full narrative was delivered in the engineering conversation.

## What existed
- `scrapers/glints_scraper.py`: Selenium + BeautifulSoup, Glints search page 1 for 44
  keywords; disguised automation; overwrote the raw CSV; swallowed errors.
- `data_processing/clean_dataset.py`, `feature_engineering.py` (pandas); salary
  parsed to integers with **0 for missing**.
- `spark_jobs/spark_sql_analysis.py`: five Spark SQL aggregates printed to stdout.
- `spark_jobs/mllib_demo.py` and a duplicate in `visualization/generate_plots.py`:
  TF-IDF + K-Means on job titles.
- 1,133-row raw CSV, two derived CSVs, 11 PNG charts, the academic report PDF.
- No API, database, frontend, tests, CI, Docker, or configuration layer.
- Now under `legacy/academic_pipeline/` (moved with `git mv`) and `docs/academic/`.

## Verified (executed)
- Cleaning and feature engineering reproduce the committed processed CSVs byte-for-byte.
- `spark_sql_analysis.py` output matches the report (average salary Rp5,193,473 /
  Rp7,327,622; Jakarta Selatan 221; Penuh Waktu 835).
- K-Means k=3, seed 42 reproduces silhouette 0.0351 and sizes 947/123/63, and the
  committed cluster labels exactly (see docs/ML_EVALUATION.md for the defects).

## Report vs. code/data discrepancies
1. The report says job descriptions were collected; only card tags were.
2. The report calls cluster 2 "finance/administration"; it is defined by a punctuation
   artifact (123/123 members) and contains software roles.
3. The report says k=3 shows high cohesion and clear separation; silhouette 0.035 means
   heavily overlapping clusters.
4. Education/experience analysis was pandas-only, not Spark SQL as the report states.
5. Spark SQL chart PNGs promised by the README were never committed.

## Data limitations carried into TalentScope
No job IDs, URLs, collection timestamps, descriptions, or salary periods; 1,127/1,133
rows with truncated tags; Hybrid/Remote mixed into tags; relative posting dates; a
keyword-biased, Java-concentrated sample from a single source whose terms prohibit
further automated collection.
