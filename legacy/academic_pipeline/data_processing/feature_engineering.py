# feature_engineering.py
# Skrip untuk menambahkan fitur baru (Feature Engineering) pada dataset

import os
import re
import pandas as pd

def extract_city(location_str):
    if pd.isna(location_str) or location_str == "Not Specified":
        return "Not Specified"
    if "," in location_str:
        parts = location_str.split(",")
        return parts[0].strip()
    return location_str

def extract_province(location_str):
    if pd.isna(location_str) or location_str == "Not Specified":
        return "Not Specified"
    if "," in location_str:
        parts = location_str.split(",")
        prov = parts[-1].strip()
        if "dki" in prov.lower() or "jakarta" in prov.lower():
            return "DKI Jakarta"
        return prov
    
    # Fallback keyword matching
    loc_lower = location_str.lower()
    if "jakarta" in loc_lower or "dki" in loc_lower:
        return "DKI Jakarta"
    elif "jawa barat" in loc_lower or any(x in loc_lower for x in ["bandung", "bekasi", "depok", "bogor", "karawang", "purwakarta"]):
        return "Jawa Barat"
    elif "jawa tengah" in loc_lower or any(x in loc_lower for x in ["semarang", "surakarta", "solo", "cilacap", "sukoharjo"]):
        return "Jawa Tengah"
    elif "jawa timur" in loc_lower or any(x in loc_lower for x in ["surabaya", "malang", "sidoarjo", "mojokerto"]):
        return "Jawa Timur"
    elif "banten" in loc_lower or "tangerang" in loc_lower:
        return "Banten"
    elif "sumatera utara" in loc_lower or "medan" in loc_lower:
        return "Sumatera Utara"
    return "Luar Daerah / Lainnya"

def parse_salary(salary_text, get_max=False):
    if pd.isna(salary_text) or "tidak ditampilkan" in str(salary_text).lower():
        return 0
        
    text = str(salary_text).replace(".", "").replace(",", ".").replace("\xa0", " ")
    
    # Parsing format jt atau juta
    if "jt" in text.lower() or "juta" in text.lower():
        numbers = re.findall(r"\d+\.?\d*", text)
        if len(numbers) >= 2:
            val = float(numbers[1]) if get_max else float(numbers[0])
            return int(val * 1000000)
        elif len(numbers) == 1:
            return int(float(numbers[0]) * 1000000)
            
    # Parsing format IDR/angka standar (contoh: IDR 5000000 - 7000000)
    numbers = re.findall(r"\d+", text)
    if len(numbers) >= 2:
        val = int(numbers[1]) if get_max else int(numbers[0])
        return val
    elif len(numbers) == 1:
        return int(numbers[0])
        
    return 0

def main():
    input_path = os.path.join("data", "processed", "processed_jobs.csv")
    output_path = os.path.join("data", "processed", "jobs_featured.csv")
    
    if not os.path.exists(input_path):
        print(f"Error: File {input_path} tidak ditemukan!")
        return
        
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} baris data untuk feature engineering.")
    
    # 1. Fitur City dan Province
    df["city"] = df["location"].apply(extract_city)
    df["province"] = df["location"].apply(extract_province)
    
    # 2. Fitur Kejelasan Gaji (salary_visible)
    df["salary_visible"] = df["salary_range"].apply(
        lambda x: 0 if "tidak ditampilkan" in str(x).lower() else 1
    )
    
    # 3. Fitur Gaji Minimum dan Maksimum (salary_min, salary_max)
    df["salary_min"] = df["salary_range"].apply(lambda x: parse_salary(x, get_max=False))
    df["salary_max"] = df["salary_range"].apply(lambda x: parse_salary(x, get_max=True))
    
    # 4. Fitur Panjang Karakter Judul & Persyaratan (title_length, requirements_length)
    df["title_length"] = df["job_title"].apply(lambda x: len(str(x)))
    df["requirements_length"] = df["job_requirements"].apply(
        lambda x: 0 if str(x).lower() == "not specified" else len(str(x))
    )
    
    # Simpan dataset hasil feature engineering
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Feature engineering selesai. Dataset disimpan ke {output_path}")

if __name__ == "__main__":
    main()
