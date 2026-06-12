# Analisis Lowongan Kerja Indonesia Menggunakan Apache Spark

> **Tugas Akhir — Mata Kuliah Analitik Big Data**

Proyek ini berfokus pada pengumpulan, pembersihan, analisis, dan pengelompokan data lowongan kerja di Indonesia menggunakan **Apache Spark**. Dataset diperoleh melalui web scraping dari platform **Glints** dan kemudian diproses menggunakan **Spark SQL** serta **Spark MLlib** untuk menghasilkan insight terkait pasar kerja Indonesia.

---

## Tech Stack

| Kategori | Teknologi |
|---|---|
| **Data Collection** | Python, Selenium, BeautifulSoup |
| **Data Processing** | Pandas, NumPy |
| **Big Data Processing** | Apache Spark, Spark SQL, Spark MLlib |
| **Visualization** | Matplotlib, Seaborn |

---

## Dataset

- **Sumber Data:** [Glints Indonesia](https://glints.com/id)
- **Jumlah Data:** 1.133 lowongan kerja
- **Kategori Pekerjaan:** IT, Business, Finance, Marketing, HR, dan lainnya
- **Informasi yang Tersedia:**
  - Lokasi & Perusahaan
  - Tipe Pekerjaan
  - Tingkat Pendidikan
  - Pengalaman Kerja
  - Rentang Gaji

---

## Struktur Repository

```text
ABD/
│
├── requirements.txt
├── README.md
│
├── scrapers/
│   └── glints_scraper.py
│
├── data/
│   ├── raw/
│   │   └── glints_jobs.csv
│   │
│   └── processed/
│       ├── processed_jobs.csv
│       └── jobs_featured.csv
│
├── data_processing/
│   ├── clean_dataset.py
│   └── feature_engineering.py
│
├── spark_jobs/
│   ├── spark_sql_analysis.py
│   └── mllib_demo.py
│
└── visualization/
    ├── *.png
    ├── clustered_jobs.csv
    └── cluster_preview.csv
```

---

## Alur Proses

```
Web Scraping
      ↓
Data Cleaning
      ↓
Feature Engineering
      ↓
Spark SQL Analysis
      ↓
MLlib K-Means Clustering
      ↓
Visualization
```

---

## Cara Menjalankan

### 1. Install Dependency
```bash
pip install -r requirements.txt
```

### 2. Scraping Dataset
```bash
python scrapers/glints_scraper.py
```

### 3. Data Cleaning
```bash
python data_processing/clean_dataset.py
```

### 4. Feature Engineering
```bash
python data_processing/feature_engineering.py
```

### 5. Spark SQL Analysis
```bash
python spark_jobs/spark_sql_analysis.py
```

### 6. MLlib Clustering
```bash
python spark_jobs/mllib_demo.py
```

### 7. Generate Visualization
```bash
python visualization/generate_plots.py
```

---

## Output

### Dataset
| File | Deskripsi |
|---|---|
| `data/raw/glints_jobs.csv` | Data mentah hasil scraping |
| `data/processed/processed_jobs.csv` | Data setelah pembersihan |
| `data/processed/jobs_featured.csv` | Data setelah feature engineering |

### Analisis Spark SQL
- Top Companies
- Top Cities
- Job Type Distribution
- Average Salary Analysis
- Most Demanded Job Titles

### Machine Learning (K-Means Clustering)
| File | Deskripsi |
|---|---|
| `clustered_jobs.csv` | Dataset hasil pengelompokan |
| `cluster_preview.csv` | Pratinjau hasil cluster |
| `cluster_distribution.png` | Visualisasi distribusi cluster |

### Visualisasi
- EDA Charts
- Spark SQL Charts
- K-Means Cluster Visualization
