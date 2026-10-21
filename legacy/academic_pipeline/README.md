# Legacy academic pipeline

The original Big Data course project (Spark SQL + MLlib on Glints listings), kept for
history and reproducibility. TalentScope does not run it. See `docs/REPOSITORY_AUDIT.md`
and `docs/ML_EVALUATION.md` for what was verified and what was found to be wrong.

Run from the **repository root** with the dependencies in `requirements.txt` (Java 8/11/17
for PySpark):

```bash
python legacy/academic_pipeline/data_processing/clean_dataset.py        # writes data/processed/processed_jobs.csv
python legacy/academic_pipeline/data_processing/feature_engineering.py  # writes data/processed/jobs_featured.csv
python legacy/academic_pipeline/spark_jobs/spark_sql_analysis.py        # prints 5 aggregates
python legacy/academic_pipeline/spark_jobs/mllib_demo.py                # prints the K-Means sweep
python legacy/academic_pipeline/visualization/generate_plots.py         # writes PNG/CSV into this folder
```

The cleaning scripts overwrite the files in `data/processed/` (with identical content for
the committed raw file). `scrapers/glints_scraper.py` is **disabled**: Glints' terms
prohibit automated collection without written consent, and the script disguised its
automation (see docs/adr/0006-browser-automation-policy.md).
