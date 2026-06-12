# visualization/generate_plots.py
# Skrip untuk menghasilkan semua visualisasi EDA, Spark SQL, dan Spark MLlib

import os
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, trim
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF
from pyspark.ml.clustering import KMeans
from pyspark.ml import Pipeline

def set_style():
    """Mengatur gaya visualisasi agar terlihat modern dan premium."""
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 11,
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.titlesize': 16,
        'figure.dpi': 150
    })

def generate_eda_plots(df, output_dir):
    """Menghasilkan 10 visualisasi EDA yang diminta."""
    print("Menghasilkan visualisasi EDA...")
    
    # Palette warna kustom yang harmonis (Clean & Professional)
    colors_single = '#2b5c8f'  # Deep Ocean Blue
    palette_multi = sns.color_palette("Blues_r", 10)
    palette_categorical = sns.color_palette("Set2", 10)
    
    # 1. Jumlah Lowongan Berdasarkan Tipe Pekerjaan
    plt.figure(figsize=(10, 6))
    job_type_counts = df['job_type'].value_counts()
    sns.barplot(x=job_type_counts.index, y=job_type_counts.values, hue=job_type_counts.index, legend=False, palette="viridis")
    plt.title("Jumlah Lowongan Berdasarkan Tipe Pekerjaan", pad=15)
    plt.xlabel("Tipe Pekerjaan")
    plt.ylabel("Jumlah Lowongan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_tipe_pekerjaan.png"), dpi=200)
    plt.close()

    # 2. Top 10 Kota dengan Lowongan Terbanyak
    plt.figure(figsize=(12, 6))
    city_counts = df[df['city'] != 'Not Specified']['city'].value_counts().head(10)
    sns.barplot(y=city_counts.index, x=city_counts.values, hue=city_counts.index, legend=False, palette=palette_multi)
    plt.title("Top 10 Kota dengan Lowongan Kerja Terbanyak", pad=15)
    plt.xlabel("Jumlah Lowongan")
    plt.ylabel("Kota / Kabupaten")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_top_kota.png"), dpi=200)
    plt.close()

    # 3. Top 10 Perusahaan Paling Aktif
    plt.figure(figsize=(12, 6))
    comp_counts = df[df['company_name'] != 'Not Specified']['company_name'].value_counts().head(10)
    sns.barplot(y=comp_counts.index, x=comp_counts.values, hue=comp_counts.index, legend=False, palette="flare_r")
    plt.title("Top 10 Perusahaan Paling Aktif Melakukan Rekrutmen", pad=15)
    plt.xlabel("Jumlah Lowongan")
    plt.ylabel("Nama Perusahaan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_top_perusahaan.png"), dpi=200)
    plt.close()

    # 4. Top 10 Posisi Pekerjaan Terbanyak
    plt.figure(figsize=(12, 6))
    title_counts = df['job_title'].value_counts().head(10)
    sns.barplot(y=title_counts.index, x=title_counts.values, hue=title_counts.index, legend=False, palette="crest")
    plt.title("Top 10 Posisi Pekerjaan Paling Banyak Dicari", pad=15)
    plt.xlabel("Jumlah Lowongan")
    plt.ylabel("Judul Posisi Pekerjaan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_top_posisi.png"), dpi=200)
    plt.close()

    # Data filter untuk analisis gaji
    df_sal = df[(df['salary_visible'] == 1) & (df['salary_min'] > 0) & (df['salary_max'] > 0)]

    # 5. Distribusi Gaji Minimum
    plt.figure(figsize=(10, 6))
    sns.histplot(df_sal['salary_min'] / 1_000_000, kde=True, color='#2b5c8f', bins=20)
    plt.title("Distribusi Gaji Minimum Terbuka (Juta Rupiah)", pad=15)
    plt.xlabel("Gaji Minimum (Juta Rp)")
    plt.ylabel("Frekuensi Lowongan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_distribusi_gaji_min.png"), dpi=200)
    plt.close()

    # 6. Distribusi Gaji Maksimum
    plt.figure(figsize=(10, 6))
    sns.histplot(df_sal['salary_max'] / 1_000_000, kde=True, color='#d95f02', bins=20)
    plt.title("Distribusi Gaji Maksimum Terbuka (Juta Rupiah)", pad=15)
    plt.xlabel("Gaji Maksimum (Juta Rp)")
    plt.ylabel("Frekuensi Lowongan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_distribusi_gaji_max.png"), dpi=200)
    plt.close()

    # 7. Perbandingan Rata-rata Gaji Minimum dan Maksimum
    plt.figure(figsize=(8, 6))
    avg_sal_min = df_sal['salary_min'].mean() / 1_000_000
    avg_sal_max = df_sal['salary_max'].mean() / 1_000_000
    categories = ['Rata-rata Gaji Min', 'Rata-rata Gaji Max']
    values = [avg_sal_min, avg_sal_max]
    sns.barplot(x=categories, y=values, hue=categories, legend=False, palette=["#2b5c8f", "#d95f02"])
    for i, val in enumerate(values):
        plt.text(i, val + 0.1, f"Rp {val:.2f} Juta", ha='center', fontweight='bold')
    plt.title("Perbandingan Rata-rata Gaji Minimum & Maksimum Lowongan Kerja", pad=15)
    plt.ylabel("Gaji (Juta Rupiah)")
    plt.ylim(0, max(values) + 1.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_perbandingan_gaji.png"), dpi=200)
    plt.close()

    # 8. Jumlah Lowongan Berdasarkan Provinsi
    plt.figure(figsize=(12, 6))
    prov_counts = df[df['province'] != 'Not Specified']['province'].value_counts()
    sns.barplot(y=prov_counts.index, x=prov_counts.values, hue=prov_counts.index, legend=False, palette="magma")
    plt.title("Jumlah Lowongan Berdasarkan Provinsi Penempatan", pad=15)
    plt.xlabel("Jumlah Lowongan")
    plt.ylabel("Provinsi")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_provinsi.png"), dpi=200)
    plt.close()

    # 9. Distribusi Tingkat Pendidikan
    plt.figure(figsize=(10, 6))
    edu_counts = df[df['education_req'] != 'Not Specified']['education_req'].value_counts()
    sns.barplot(x=edu_counts.index, y=edu_counts.values, hue=edu_counts.index, legend=False, palette="Set2")
    plt.xticks(rotation=15)
    plt.title("Distribusi Tingkat Pendidikan yang Dipersyaratkan", pad=15)
    plt.xlabel("Persyaratan Pendidikan")
    plt.ylabel("Jumlah Lowongan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_pendidikan.png"), dpi=200)
    plt.close()

    # 10. Distribusi Pengalaman Kerja
    plt.figure(figsize=(10, 6))
    exp_counts = df[df['experience_level'] != 'Not Specified']['experience_level'].value_counts().head(10)
    sns.barplot(x=exp_counts.index, y=exp_counts.values, hue=exp_counts.index, legend=False, palette="cubehelix")
    plt.xticks(rotation=15)
    plt.title("Distribusi Kategori Pengalaman Kerja yang Dibutuhkan", pad=15)
    plt.xlabel("Pengalaman Kerja")
    plt.ylabel("Jumlah Lowongan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "eda_pengalaman.png"), dpi=200)
    plt.close()

def generate_spark_sql_plots(spark, csv_path, output_dir):
    """Menjalankan kueri Spark SQL dan menyimpan hasilnya sebagai grafik."""
    print("Menjalankan analisis Spark SQL untuk visualisasi...")
    
    # 1. Baca dataset dengan Spark
    df = spark.read.csv(csv_path, header=True, inferSchema=True)
    df.createOrReplaceTempView("jobs")
    
    # Kueri 1: Top 10 Perusahaan Paling Aktif
    q_companies = """
        SELECT company_name, COUNT(*) as jumlah_lowongan
        FROM jobs
        WHERE company_name IS NOT NULL AND company_name != 'Not Specified'
        GROUP BY company_name
        ORDER BY jumlah_lowongan DESC
        LIMIT 10
    """
    df_companies = spark.sql(q_companies).toPandas()
    plt.figure(figsize=(12, 6))
    sns.barplot(y="company_name", x="jumlah_lowongan", data=df_companies, hue="company_name", legend=False, palette="flare_r")
    plt.title("Top 10 Perusahaan Paling Aktif (Spark SQL)", pad=15)
    plt.xlabel("Jumlah Lowongan")
    plt.ylabel("Perusahaan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "top_companies.png"), dpi=200)
    plt.close()

    # Kueri 2: Top 10 Kota dengan Lowongan Terbanyak
    q_cities = """
        SELECT city, COUNT(*) as jumlah_lowongan
        FROM jobs
        WHERE city IS NOT NULL AND city != 'Not Specified'
        GROUP BY city
        ORDER BY jumlah_lowongan DESC
        LIMIT 10
    """
    df_cities = spark.sql(q_cities).toPandas()
    plt.figure(figsize=(12, 6))
    sns.barplot(y="city", x="jumlah_lowongan", data=df_cities, hue="city", legend=False, palette="Blues_r")
    plt.title("Top 10 Kota Penempatan Terbanyak (Spark SQL)", pad=15)
    plt.xlabel("Jumlah Lowongan")
    plt.ylabel("Kota / Kabupaten")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "top_cities.png"), dpi=200)
    plt.close()

    # Kueri 3: Jumlah Pekerjaan Berdasarkan Tipe Pekerjaan
    q_job_types = """
        SELECT job_type, COUNT(*) as jumlah_lowongan
        FROM jobs
        WHERE job_type IS NOT NULL AND job_type != 'Not Specified'
        GROUP BY job_type
        ORDER BY jumlah_lowongan DESC
    """
    df_job_types = spark.sql(q_job_types).toPandas()
    plt.figure(figsize=(10, 6))
    sns.barplot(x="job_type", y="jumlah_lowongan", data=df_job_types, hue="job_type", legend=False, palette="viridis")
    plt.title("Jumlah Lowongan Berdasarkan Tipe Pekerjaan (Spark SQL)", pad=15)
    plt.xlabel("Tipe Pekerjaan")
    plt.ylabel("Jumlah Lowongan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "job_type_distribution.png"), dpi=200)
    plt.close()

    # Kueri 4: Rata-rata Gaji Minimum dan Maksimum
    q_salary = """
        SELECT 
            AVG(salary_min) as rata_rata_gaji_min, 
            AVG(salary_max) as rata_rata_gaji_max
        FROM jobs
        WHERE salary_visible = 1 AND salary_min > 0 AND salary_max > 0
    """
    df_salary = spark.sql(q_salary).toPandas()
    val_min = df_salary['rata_rata_gaji_min'].iloc[0] / 1_000_000
    val_max = df_salary['rata_rata_gaji_max'].iloc[0] / 1_000_000
    
    plt.figure(figsize=(8, 6))
    categories = ['Rata-rata Gaji Min', 'Rata-rata Gaji Max']
    values = [val_min, val_max]
    sns.barplot(x=categories, y=values, hue=categories, legend=False, palette=["#2b5c8f", "#d95f02"])
    for i, val in enumerate(values):
        plt.text(i, val + 0.1, f"Rp {val:.2f} Juta", ha='center', fontweight='bold')
    plt.title("Rata-rata Rentang Gaji Lowongan Kerja (Spark SQL)", pad=15)
    plt.ylabel("Gaji (Juta Rupiah)")
    plt.ylim(0, max(values) + 1.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "average_salary.png"), dpi=200)
    plt.close()

    # Kueri 5: 10 Posisi Pekerjaan Paling Umum
    q_titles = """
        SELECT job_title, COUNT(*) as jumlah_posisi
        FROM jobs
        GROUP BY job_title
        ORDER BY jumlah_posisi DESC
        LIMIT 10
    """
    df_titles = spark.sql(q_titles).toPandas()
    plt.figure(figsize=(12, 6))
    sns.barplot(y="job_title", x="jumlah_posisi", data=df_titles, hue="job_title", legend=False, palette="crest")
    plt.title("Top 10 Posisi Pekerjaan Paling Banyak Dicari (Spark SQL)", pad=15)
    plt.xlabel("Jumlah Lowongan")
    plt.ylabel("Posisi Pekerjaan")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "top_job_titles.png"), dpi=200)
    plt.close()

def generate_mllib_plots(spark, csv_path, output_dir):
    """
    Menjalankan pipeline KMeans clustering (k=3, model terbaik)
    dan menyimpan hasil distribusi cluster sebagai PNG dan CSV.

    Pipeline: job_title → lower/regexp_replace → Tokenizer
              → StopWordsRemover → HashingTF → IDF → KMeans(k=3)
    """
    print("Menjalankan pipeline MLlib KMeans clustering...")

    df = spark.read.csv(csv_path, header=True, inferSchema=True)

    # --- Preprocessing (native Spark SQL — tanpa Python UDF) ---
    DOMAIN_STOPWORDS = [
        "+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8",
        "+9", "+10", "+11", "+12", "+13", "+14", "+15", "+16",
        "staff", "staf", "officer", "specialist",
        "pt", "cv", "tbk", "indonesia",
        "dan", "yang", "untuk", "dari", "dengan", "di",
    ]

    df_clean = (
        df
        .filter(col("job_title").isNotNull())
        .filter(col("job_title") != "Not Specified")
        .withColumn(
            "job_title_clean",
            trim(regexp_replace(lower(col("job_title")), r"[^a-z\s]", " "))
        )
        .filter(col("job_title_clean") != "")
    )

    # --- Pipeline ---
    tokenizer = Tokenizer(inputCol="job_title_clean", outputCol="words_raw")
    remover = StopWordsRemover(
        inputCol="words_raw",
        outputCol="words_filtered",
        stopWords=StopWordsRemover.loadDefaultStopWords("english") + DOMAIN_STOPWORDS,
    )
    hashingTF = HashingTF(inputCol="words_filtered", outputCol="rawFeatures", numFeatures=1024)
    idf = IDF(inputCol="rawFeatures", outputCol="features", minDocFreq=3)
    kmeans = KMeans(
        featuresCol="features", predictionCol="cluster_prediction",
        k=3, seed=42, maxIter=50, initMode="k-means||",
    )

    pipeline = Pipeline(stages=[tokenizer, remover, hashingTF, idf, kmeans])
    model = pipeline.fit(df_clean)
    predictions = model.transform(df_clean)

    # --- Simpan distribusi cluster sebagai PNG ---
    df_pd = predictions.toPandas()
    cluster_counts = df_pd["cluster_prediction"].value_counts().sort_index()

    cluster_labels = [f"Cluster {i}" for i in cluster_counts.index]

    plt.figure(figsize=(8, 6))
    bars = sns.barplot(x=cluster_labels, y=cluster_counts.values,
                       hue=cluster_labels, legend=False, palette="Set1")
    for i, val in enumerate(cluster_counts.values):
        plt.text(i, val + 8, str(val), ha="center", fontweight="bold", fontsize=12)
    plt.title("Distribusi Prediksi Cluster K-Means (k=3, Spark MLlib)", pad=15)
    plt.xlabel("Cluster ID")
    plt.ylabel("Jumlah Lowongan Kerja")
    plt.ylim(0, cluster_counts.max() + 80)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "cluster_distribution.png"), dpi=200)
    plt.close()

    # --- Simpan CSV hasil cluster ---
    cols_to_save = [
        "job_title", "company_name", "location", "salary_range",
        "job_type", "experience_level", "education_req",
        "job_requirements", "cluster_prediction",
    ]
    df_out = df_pd[[c for c in cols_to_save if c in df_pd.columns]]

    clustered_jobs_path  = os.path.join(output_dir, "clustered_jobs.csv")
    cluster_preview_path = os.path.join(output_dir, "cluster_preview.csv")

    df_out.to_csv(clustered_jobs_path, index=False, encoding="utf-8-sig")
    df_out.head(15).to_csv(cluster_preview_path, index=False, encoding="utf-8-sig")

    print(f"File KMeans berhasil disimpan:")
    print(f" - {clustered_jobs_path}")
    print(f" - {cluster_preview_path}")
    print(f" - {os.path.join(output_dir, 'cluster_distribution.png')}")



def main():
    output_dir = "visualization"
    os.makedirs(output_dir, exist_ok=True)
    
    csv_path = os.path.join("data", "processed", "jobs_featured.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Dataset {csv_path} tidak ditemukan. Silakan jalankan feature engineering dahulu.")
        return
        
    set_style()
    
    # A. Generate EDA Plots (Menggunakan Pandas untuk plotting cepat)
    df_pandas = pd.read_csv(csv_path)
    generate_eda_plots(df_pandas, output_dir)
    
    # Inisiasi Sesi Spark untuk analisis Spark SQL dan MLlib
    print("Membuat sesi Apache Spark...")
    spark = SparkSession.builder \
        .appName("JobMarketVisualization") \
        .master("local[*]") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        # B. Generate Spark SQL Plots
        generate_spark_sql_plots(spark, csv_path, output_dir)
        
        # C. Generate MLlib KMeans Plots & CSVs
        generate_mllib_plots(spark, csv_path, output_dir)
        
    finally:
        print("Menutup sesi Spark...")
        spark.stop()

if __name__ == "__main__":
    main()
