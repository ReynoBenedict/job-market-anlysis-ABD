import os
from pyspark.sql import SparkSession

def main():
    # 1. Inisialisasi Sesi Spark
    print("Membuat sesi Apache Spark...")
    spark = SparkSession.builder \
        .appName("JobMarketSparkSQLAnalysis") \
        .master("local[*]") \
        .getOrCreate()
        
    # Mematikan log INFO agar terminal tetap bersih
    spark.sparkContext.setLogLevel("WARN")
    
    # Path file input
    input_csv = os.path.join("data", "processed", "jobs_featured.csv")
    
    if not os.path.exists(input_csv):
        print(f"Error: Dataset {input_csv} belum dibuat. Jalankan skrip pembersihan terlebih dahulu!")
        spark.stop()
        return
        
    print(f"Membaca dataset dari {input_csv}...")
    df = spark.read.csv(input_csv, header=True, inferSchema=True)
    
    # 2. Buat Temporary SQL View dari DataFrame
    df.createOrReplaceTempView("jobs")
    print("Temporary SQL View 'jobs' berhasil dibuat.")
    
    # 3. Kueri 1: Top 10 Perusahaan dengan Lowongan Terbanyak
    print("\n--- 1. TOP 10 PERUSAHAAN TERAKTIF ---")
    q_companies = """
        SELECT company_name, COUNT(*) as jumlah_lowongan
        FROM jobs
        WHERE company_name IS NOT NULL AND company_name != 'Not Specified'
        GROUP BY company_name
        ORDER BY jumlah_lowongan DESC
        LIMIT 10
    """
    spark.sql(q_companies).show(10, truncate=False)
    
    # 4. Kueri 2: Top 10 Kota/Kabupaten Penempatan Terbanyak
    print("\n--- 2. TOP 10 KOTA PENEMPATAN TERBANYAK ---")
    q_cities = """
        SELECT city, COUNT(*) as jumlah_lowongan
        FROM jobs
        WHERE city IS NOT NULL AND city != 'Not Specified'
        GROUP BY city
        ORDER BY jumlah_lowongan DESC
        LIMIT 10
    """
    spark.sql(q_cities).show(10, truncate=False)
    
    # 5. Kueri 3: Jumlah Lowongan Berdasarkan Tipe Pekerjaan
    print("\n--- 3. JUMLAH PEKERJAAN BERDASARKAN TIPE PEKERJAAN ---")
    q_job_types = """
        SELECT job_type, COUNT(*) as jumlah_lowongan
        FROM jobs
        WHERE job_type IS NOT NULL AND job_type != 'Not Specified'
        GROUP BY job_type
        ORDER BY jumlah_lowongan DESC
    """
    spark.sql(q_job_types).show(truncate=False)
    
    # 6. Kueri 4: Rata-rata Gaji Minimum dan Maksimum (Bila Gaji Ditampilkan)
    print("\n--- 4. RATA-RATA GAJI MINIMUM DAN MAKSIMUM (RUPIAH) ---")
    q_salary = """
        SELECT 
            AVG(salary_min) as rata_rata_gaji_min, 
            AVG(salary_max) as rata_rata_gaji_max
        FROM jobs
        WHERE salary_visible = 1 AND salary_min > 0 AND salary_max > 0
    """
    spark.sql(q_salary).show()
    
    # 7. Kueri 5: 10 Posisi Pekerjaan Paling Umum
    print("\n--- 5. 10 POSISI PEKERJAAN PALING BANYAK DICARI ---")
    q_titles = """
        SELECT job_title, COUNT(*) as jumlah_posisi
        FROM jobs
        GROUP BY job_title
        ORDER BY jumlah_posisi DESC
        LIMIT 10
    """
    spark.sql(q_titles).show(10, truncate=False)
    
    # Menutup Sesi Spark
    print("Menutup sesi Spark...")
    spark.stop()

if __name__ == "__main__":
    main()
