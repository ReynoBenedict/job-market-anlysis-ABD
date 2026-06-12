import os

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, trim

from pyspark.ml import Pipeline
from pyspark.ml.feature import (
    Tokenizer,
    StopWordsRemover,
    HashingTF,
    IDF,
)
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


# additional stopwords
DOMAIN_STOPWORDS = [
    # Kata umum jabatan yang muncul di semua cluster
    "staff", "staf", "officer", "specialist",
    # Kata umum lainnya
    "pt", "cv", "tbk", "indonesia",
    # Partikel Indonesia
    "dan", "yang", "untuk", "dari", "dengan", "di",
]

# Minimum anggota per cluster agar dianggap valid (bukan degenerate)
MIN_CLUSTER_SIZE = 10


def build_tfidf_pipeline(k: int) -> Pipeline:
    tokenizer = Tokenizer(
        inputCol="job_title_clean",
        outputCol="words_raw",
    )

    all_stopwords = (
        StopWordsRemover.loadDefaultStopWords("english")
        + DOMAIN_STOPWORDS
    )

    remover = StopWordsRemover(
        inputCol="words_raw",
        outputCol="words_filtered",
        stopWords=all_stopwords,
    )

    hashingTF = HashingTF(
        inputCol="words_filtered",
        outputCol="rawFeatures",
        numFeatures=1024,
    )

    idf = IDF(
        inputCol="rawFeatures",
        outputCol="features",
        minDocFreq=3,   # abaikan token yang sangat jarang
    )

    kmeans = KMeans(
        featuresCol="features",
        predictionCol="cluster_prediction",
        k=k,
        seed=42,
        maxIter=50,
        initMode="k-means||",
    )

    return Pipeline(stages=[tokenizer, remover, hashingTF, idf, kmeans])


def is_valid_result(dist_rows, min_size: int) -> bool:
    return all(row["count"] >= min_size for row in dist_rows)


def main():

    # 1. Inisialisasi Spark 
    print("Membuat sesi Apache Spark...")

    spark = (
        SparkSession.builder
        .appName("JobClusteringMLlib_Improved")
        .master("local[*]")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    # 2. Read Dataset
    input_csv = os.path.join("data", "processed", "jobs_featured.csv")

    if not os.path.exists(input_csv):
        print(f"ERROR: Dataset tidak ditemukan -> {input_csv}")
        spark.stop()
        return

    print(f"Membaca dataset dari {input_csv}...")

    df = spark.read.csv(input_csv, header=True, inferSchema=True)

    # 3. Text Preprocessing
    df_clean = (
        df
        .filter(col("job_title").isNotNull())
        .filter(col("job_title") != "Not Specified")
        .withColumn(
            "job_title_clean",
            trim(
                regexp_replace(
                    lower(col("job_title")),
                    r"[^a-z\s]",   # hanya pertahankan huruf dan spasi
                    " "
                )
            )
        )
        .filter(col("job_title_clean") != "")
    )

    total_rows = df_clean.count()
    print(f"Data valid untuk diproses ML: {total_rows} baris.")
    print("Kolom fitur: job_title (setelah normalisasi teks)\n")

    # Cache agar tidak dihitung ulang untuk setiap nilai k
    df_clean.cache()

    # 4. K Means experimenting
    evaluator = ClusteringEvaluator(
        featuresCol="features",
        predictionCol="cluster_prediction",
        metricName="silhouette",
    )

    # Mulai dari k=3 karena k=2 cenderung menghasilkan 1 mega-cluster
    K_VALUES = [3, 4, 5, 6]
    results = []   # (k, silhouette_score, is_valid, model, predictions, dist)

    print("=" * 60)
    print("EKSPERIMEN NILAI K")
    print("=" * 60)

    for k in K_VALUES:
        print(f"\n[Melatih K-Means dengan k={k}]")

        pipeline = build_tfidf_pipeline(k)
        model    = pipeline.fit(df_clean)
        preds    = model.transform(df_clean)

        score = evaluator.evaluate(preds)

        dist = (
            preds
            .groupBy("cluster_prediction")
            .count()
            .orderBy("cluster_prediction")
            .collect()
        )

        valid = is_valid_result(dist, MIN_CLUSTER_SIZE)
        flag  = "[OK]" if valid else "[!!] ada cluster < 10 anggota"

        print(f"  Silhouette Score : {score:.4f}  {flag}")
        print("  Distribusi Cluster:")
        for row in dist:
            print(f"    Cluster {row['cluster_prediction']}: {row['count']} lowongan")

        results.append((k, score, valid, model, preds, dist))

    # 5. Summmary dan pemilihan model terbaik
    print("\n" + "=" * 60)
    print("RINGKASAN SEMUA NILAI K")
    print("=" * 60)
    print(f"{'k':>4}  {'Silhouette Score':>18}  {'Valid?':>8}")
    print("-" * 38)
    for k, score, valid, _, _, _ in results:
        status = "YA" if valid else "TIDAK"
        print(f"{k:>4}  {score:>18.4f}  {status:>8}")

    # Prioritaskan model valid (semua cluster >= MIN_CLUSTER_SIZE)
    # dengan Silhouette Score tertinggi
    valid_results = [(k, s, v, m, p, d) for k, s, v, m, p, d in results if v]

    if valid_results:
        best_k, best_score, _, best_model, best_preds, best_dist = max(
            valid_results, key=lambda x: x[1]
        )
        print(f"\n>>> MODEL TERBAIK (distribusi valid): k={best_k}  |  Silhouette Score = {best_score:.4f}")
    else:
        # Fallback: pilih berdasarkan skor tertinggi dari semua k
        best_k, best_score, _, best_model, best_preds, best_dist = max(
            results, key=lambda x: x[1]
        )
        print(f"\n>>> MODEL TERBAIK (skor tertinggi): k={best_k}  |  Silhouette Score = {best_score:.4f}")
        print("    (catatan: tidak ada distribusi valid dengan min 10 anggota per cluster)")

    # 6. Analisis detail model yang terbaik
    print("\n" + "=" * 60)
    print(f"ANALISIS DETAIL MODEL TERBAIK (k={best_k})")
    print("=" * 60)

    print("\n--- Distribusi Cluster ---")
    (
        best_preds
        .groupBy("cluster_prediction")
        .count()
        .orderBy("cluster_prediction")
        .show(truncate=False)
    )

    # ==========================================================
    # 7. INTERPRETASI PER CLUSTER (Top Judul & Contoh Data)
    # ==========================================================
    print("\n--- Interpretasi dan Contoh Data Per Cluster ---")

    for cluster_id in range(best_k):
        cluster_df = best_preds.filter(
            col("cluster_prediction") == cluster_id
        )
        count = cluster_df.count()

        top_titles = (
            cluster_df
            .groupBy("job_title")
            .count()
            .orderBy("count", ascending=False)
            .limit(5)
            .collect()
        )

        print(f"\n{'='*55}")
        print(f"CLUSTER {cluster_id}  ({count} lowongan)")
        print(f"{'='*55}")

        print("  Top 5 Judul Pekerjaan Dominan:")
        for row in top_titles:
            print(f"    - {row['job_title']} ({row['count']} lowongan)")

        print(f"\n  Contoh 10 Data dari Cluster {cluster_id}:")
        (
            cluster_df
            .select("job_title", "company_name", "location")
            .limit(10)
            .show(truncate=False)
        )

    # 8. Informasi akhir model 
    kmeans_model = best_model.stages[-1]

    print("\n=== INFORMASI MODEL TERBAIK ===")
    print(f"  Algoritma        : K-Means (Spark MLlib)")
    print(f"  Jumlah Cluster   : {kmeans_model.getK()}")
    print(f"  Silhouette Score : {best_score:.4f}")
    print(f"  Jumlah Data      : {total_rows} baris")
    print(f"  Kolom Fitur      : job_title")
    print(f"  Preprocessing    : lower + regexp_replace + StopWordsRemover + HashingTF(1024) + IDF(minDocFreq=3)")

    df_clean.unpersist()
    print("\nMenutup sesi Spark...")
    spark.stop()


if __name__ == "__main__":
    main()