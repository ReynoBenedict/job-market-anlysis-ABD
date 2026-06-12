# Analisis Lowongan Kerja Big Data (Tugas Akhir)

Proyek ini adalah tugas akhir mata kuliah Analitik Big Data yang berfokus pada pengumpulan, pembersihan, dan analisis data lowongan kerja di Indonesia menggunakan teknologi web scraping dan Apache Spark.

---

## 1. Project Overview
Proyek ini mengintegrasikan data lowongan kerja dari dua portal karir terkemuka di Indonesia untuk dianalisis polanya (seperti sebaran lokasi penempatan, rata-rata gaji minimum/maksimum, dan pengelompokan jenis pekerjaan menggunakan Machine Learning KMeans).

---

## 2. Data Sources
*   **Karir.com**: Diambil menggunakan Selenium (master-detail split-pane).
*   **Glints.com/id**: Diambil menggunakan Selenium dengan mengekstrak data JSON-LD / NextJS `__NEXT_DATA__` untuk kestabilan tinggi.

---

## 3. Folder Structure
```text
ABD/
├── main.py                          # Legacy scraper Karir.com (referensi)
├── scraper.py                       # Scraper produksi Karir.com
├── requirements.txt                 # Dependensi Python proyek
├── README.md                        # Dokumentasi tunggal proyek
├── scrapers/
│   └── glints_scraper.py            # Scraper produksi Glints.com
├── data/
│   ├── raw/
│   │   ├── raw_job_data_karir.csv   # Data mentah Karir.com
│   │   ├── glints_jobs.csv          # Data mentah Glints.com
│   │   └── combined_jobs.csv        # Hasil gabungan data mentah
│   └── processed/
│       ├── processed_jobs.csv       # Hasil pembersihan data
│       └── jobs_featured.csv        # Hasil feature engineering
├── data_processing/
│   ├── clean_dataset.py             # Kode pembersihan dataset
│   └── feature_engineering.py       # Kode rekayasa fitur baru
├── spark_jobs/
│   ├── spark_sql_analysis.py        # Analisis data dengan Spark SQL
│   └── mllib_demo.py                # Pemodelan KMeans menggunakan Spark MLlib
└── experiments/
    └── glints_debug/                # File sementara riset Glints
```

---

## 4. How to Run Scraper
Sebelum menjalankan, pastikan Google Chrome dan WebDriver sudah terpasang.

1.  **Menjalankan Scraper Karir.com**:
    ```bash
    python scraper.py
    ```
2.  **Menjalankan Scraper Glints**:
    ```bash
    python scrapers/glints_scraper.py
    ```
3.  **Menggabungkan Dataset Mentah**:
    ```bash
    python experiments/glints_debug/merge_datasets.py
    ```

---

## 5. How to Run Cleaning
Skrip ini akan membuang duplikat data, merapikan spasi (trim), serta melakukan standardisasi lokasi dan format gaji.

1.  **Pembersihan Data**:
    ```bash
    python data_processing/clean_dataset.py
    ```
2.  **Feature Engineering** (menambahkan kolom kota, provinsi, gaji min/max, dan panjang karakter teks):
    ```bash
    python data_processing/feature_engineering.py
    ```

---

## 6. How to Run Spark Analysis
Analisis ini memerlukan Java JDK dan Apache Spark terpasang di sistem lokal Anda.

1.  **Analisis SQL (Kueri Top 10 Perusahaan, Gaji, dll.)**:
    ```bash
    python spark_jobs/spark_sql_analysis.py
    ```
2.  **Machine Learning KMeans Clustering**:
    ```bash
    python spark_jobs/mllib_demo.py
    ```

---

## 7. Expected Outputs
*   `data/raw/combined_jobs.csv`: Data gabungan mentah berskala ~300-500 baris setelah proses scraping skala penuh.
*   `data/processed/jobs_featured.csv`: Dataset bersih yang siap diolah oleh engine Spark.
*   **Terminal Output Spark SQL**: Tabel frekuensi top lokasi, perusahaan teraktif, statistik rata-rata gaji, dan platform asal data.
*   **Terminal Output MLlib**: Hasil pembagian cluster lowongan kerja berdasarkan kata kunci kualifikasi pekerjaan.
