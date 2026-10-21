"""Re-evaluate the academic K-Means experiment on job titles (Spark MLlib batch job).

Compares the original preprocessing with a corrected one, across several k values and
random seeds, and writes the measurements to docs/ml/clustering_results.json. The
narrative interpretation lives in docs/ML_EVALUATION.md.

Run from the repository root with an environment that has pyspark and scikit-learn
(the legacy pipeline's requirements plus scikit-learn):

    python analytics/evaluate_title_clustering.py

This reads data/raw/glints_jobs.csv only; it writes nothing else.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from itertools import combinations
from pathlib import Path

from pyspark.ml import Pipeline
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml.feature import HashingTF, IDF, Normalizer, RegexTokenizer, StopWordsRemover, Tokenizer
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, trim
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from talentscope.normalization.role_family import classify_role_family  # noqa: E402

# Configuration of the original experiment (legacy/academic_pipeline/spark_jobs/mllib_demo.py).
ORIGINAL_DOMAIN_STOPWORDS = [
    "staff", "staf", "officer", "specialist", "pt", "cv", "tbk", "indonesia",
    "dan", "yang", "untuk", "dari", "dengan", "di",
]
# Corrected list: keeps occupation words ("officer", "specialist") and adds Indonesian
# function words and seniority/intern noise that say little about the occupation.
CORRECTED_STOPWORDS = [
    "pt", "cv", "tbk", "indonesia", "dan", "yang", "untuk", "dari", "dengan", "di", "atau",
    "senior", "junior", "sr", "jr", "lead", "intern", "internship", "magang", "urgent",
    "jakarta", "bandung", "surabaya", "remote", "hybrid", "wfh", "wfo", "fulltime", "full", "time",
]
K_VALUES = [3, 4, 5, 6, 8, 10, 15]
SEEDS = [42, 1, 7, 123, 2024]
NUM_FEATURES = 1024


def load_titles(spark: SparkSession, path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        titles = [row["job_title"] for row in csv.DictReader(handle)]
    # One partition, like the original job (spark.read.csv of a small file). K-Means||
    # initialisation depends on partition layout, so the same seed gives different
    # clusters on a differently partitioned DataFrame.
    frame = spark.createDataFrame([(i, t) for i, t in enumerate(titles)], ["row_id", "job_title"]).coalesce(1)
    return frame, titles


def original_pipeline(k: int, seed: int) -> Pipeline:
    return Pipeline(stages=[
        Tokenizer(inputCol="clean", outputCol="words"),
        StopWordsRemover(inputCol="words", outputCol="filtered",
                         stopWords=StopWordsRemover.loadDefaultStopWords("english") + ORIGINAL_DOMAIN_STOPWORDS),
        HashingTF(inputCol="filtered", outputCol="tf", numFeatures=NUM_FEATURES),
        IDF(inputCol="tf", outputCol="features", minDocFreq=3),
        KMeans(featuresCol="features", predictionCol="cluster", k=k, seed=seed, maxIter=50),
    ])


def corrected_pipeline(k: int, seed: int) -> Pipeline:
    return Pipeline(stages=[
        # Split on runs of separators, so punctuation can never yield empty tokens;
        # "+" and "#" are word characters here, keeping "c++" and "c#".
        RegexTokenizer(inputCol="clean", outputCol="words", pattern="[^a-z0-9+#]+", minTokenLength=1),
        StopWordsRemover(inputCol="words", outputCol="filtered",
                         stopWords=StopWordsRemover.loadDefaultStopWords("english") + CORRECTED_STOPWORDS),
        HashingTF(inputCol="filtered", outputCol="tf", numFeatures=NUM_FEATURES),
        IDF(inputCol="tf", outputCol="tfidf", minDocFreq=2),
        # L2-normalised vectors make Euclidean K-Means equivalent to cosine geometry.
        Normalizer(inputCol="tfidf", outputCol="features", p=2.0),
        KMeans(featuresCol="features", predictionCol="cluster", k=k, seed=seed, maxIter=50),
    ])


def run(raw_csv: Path, output: Path) -> None:
    # Spark launches Python workers by name ("python3"), which on Windows may resolve to
    # the Microsoft Store stub; use the interpreter running this script instead.
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
    spark = (SparkSession.builder.master("local[*]").appName("title-clustering-evaluation")
             .config("spark.ui.enabled", "false").getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    started = time.time()
    df, titles = load_titles(spark, raw_csv)

    original_input = df.withColumn("clean", trim(regexp_replace(lower(col("job_title")), r"[^a-z\s]", " "))).cache()
    corrected_input = df.withColumn("clean", lower(col("job_title"))).cache()
    reference = [classify_role_family(t).value for t in titles]

    # Diagnose the empty-token artifact in the original preprocessing.
    words = original_pipeline(3, 42).getStages()[0].transform(original_input)
    empty_token_rows = words.filter("array_contains(words, '')").count()

    sqeuclid = ClusteringEvaluator(featuresCol="features", predictionCol="cluster", metricName="silhouette")
    cosine = ClusteringEvaluator(featuresCol="features", predictionCol="cluster", metricName="silhouette",
                                 distanceMeasure="cosine")
    results: dict[str, object] = {
        "dataset": {"file": str(raw_csv), "rows": len(titles)},
        "original_empty_token_rows": empty_token_rows,
        "configurations": {},
    }

    for name, builder, data in (("original", original_pipeline, original_input),
                                ("corrected", corrected_pipeline, corrected_input)):
        per_k = []
        for k in K_VALUES:
            runs = []
            for seed in SEEDS:
                predictions = builder(k, seed).fit(data).transform(data)
                labels_by_row = dict(predictions.select("row_id", "cluster").collect())
                labels = [labels_by_row[i] for i in range(len(titles))]
                sizes = sorted((labels.count(c) for c in set(labels)), reverse=True)
                runs.append({
                    "seed": seed,
                    "silhouette_sq_euclidean": sqeuclid.evaluate(predictions),
                    "silhouette_cosine": cosine.evaluate(predictions),
                    "largest_cluster_share": sizes[0] / len(labels),
                    "sizes": sizes,
                    "nmi_vs_role_families": normalized_mutual_info_score(reference, labels),
                    "labels": labels,
                })
            pairwise_ari = [adjusted_rand_score(a["labels"], b["labels"]) for a, b in combinations(runs, 2)]
            summary = {
                "k": k,
                "silhouette_cosine_mean": statistics.mean(r["silhouette_cosine"] for r in runs),
                "silhouette_cosine_sd": statistics.stdev(r["silhouette_cosine"] for r in runs),
                "silhouette_sq_euclidean_mean": statistics.mean(r["silhouette_sq_euclidean"] for r in runs),
                "seed_stability_ari_mean": statistics.mean(pairwise_ari),
                "seed_stability_ari_min": min(pairwise_ari),
                "largest_cluster_share_mean": statistics.mean(r["largest_cluster_share"] for r in runs),
                "nmi_vs_role_families_mean": statistics.mean(r["nmi_vs_role_families"] for r in runs),
                "runs": [{key: value for key, value in r.items() if key != "labels"} for r in runs],
            }
            per_k.append(summary)
            print(f"{name:9} k={k:2} cos={summary['silhouette_cosine_mean']:.3f}±{summary['silhouette_cosine_sd']:.3f} "
                  f"ARI={summary['seed_stability_ari_mean']:.2f} (min {summary['seed_stability_ari_min']:.2f}) "
                  f"largest={summary['largest_cluster_share_mean']:.0%} NMI={summary['nmi_vs_role_families_mean']:.2f}",
                  flush=True)
        results["configurations"][name] = per_k  # type: ignore[index]

    baseline = next(r for r in results["configurations"]["original"][0]["runs"] if r["seed"] == 42)  # type: ignore[index]
    results["baseline_k3_seed42"] = baseline
    results["runtime_seconds"] = round(time.time() - started, 1)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {output} in {results['runtime_seconds']}s")
    spark.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=Path("data/raw/glints_jobs.csv"))
    parser.add_argument("--output", type=Path, default=Path("docs/ml/clustering_results.json"))
    args = parser.parse_args()
    run(args.input, args.output)
