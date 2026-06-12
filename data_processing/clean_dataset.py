# clean_dataset.py
# Skrip untuk membersihkan dataset Glints

import os
import pandas as pd

def clean_text(val):
    if pd.isna(val):
        return "Not Specified"
    return str(val).strip()

def standardize_location(loc):
    if pd.isna(loc):
        return "Not Specified"
    loc_str = str(loc).strip()
    loc_lower = loc_str.lower()
    if "not specified" in loc_lower or "lihat perusahaan" in loc_lower:
        return "Not Specified"
    return loc_str

def standardize_salary(sal):
    if pd.isna(sal):
        return "Tidak Ditampilkan"
    sal_lower = str(sal).lower().strip()
    if "tidak menampilkan gaji" in sal_lower or "gaji di atas ekspektasi" in sal_lower or "not specified" in sal_lower or "tidak ditampilkan" in sal_lower:
        return "Tidak Ditampilkan"
    return str(sal).strip()

def main():
    raw_path = os.path.join("data", "raw", "glints_jobs.csv")
    processed_dir = os.path.join("data", "processed")
    output_path = os.path.join(processed_dir, "processed_jobs.csv")
    
    if not os.path.exists(raw_path):
        print(f"Error: File {raw_path} tidak ditemukan!")
        return
        
    df = pd.read_csv(raw_path)
    print(f"Loaded {len(df)} baris data mentah.")
    
    # 1. Hapus baris duplikat berdasarkan judul, perusahaan, dan lokasi
    df.drop_duplicates(subset=["job_title", "company_name", "location"], inplace=True)
    
    # 2. Trim whitespace dan isi Not Specified untuk text
    for col in df.columns:
        df[col] = df[col].apply(clean_text)
        
    # 3. Standardisasi lokasi
    df["location"] = df["location"].apply(standardize_location)
    
    # 4. Standardisasi gaji
    df["salary_range"] = df["salary_range"].apply(standardize_salary)
    
    # Buat direktori output jika belum ada
    os.makedirs(processed_dir, exist_ok=True)
    
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Pembersihan selesai. Berhasil menyimpan {len(df)} baris ke {output_path}")

if __name__ == "__main__":
    main()
