# Scraper Glints
# Jalankan file ini untuk mengambil data lowongan dari Glints
# Output: data/raw/glints_jobs.csv

import os
import re
import time
import logging
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
CSV_FILE_PATH = os.path.join("data", "raw", "glints_jobs.csv")
SOURCE_PLATFORM = "glints"

COLUMN_SCHEMA = [
    "job_title", "company_name", "location", "salary_range", "job_type",
    "experience_level", "education_req", "job_requirements",
    "posted_date", "source_platform"
]

def setup_driver():
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    driver.set_page_load_timeout(30)
    return driver

def parse_job_card_directly(card, keyword=None):
    # 1. Job Title
    title_el = card.find('h2', class_=lambda c: c and 'JobTitle' in c)
    if not title_el:
        title_el = card.find('a', href=lambda h: h and '/opportunities/jobs/' in h)
    title = title_el.get_text(strip=True) if title_el else "Not Specified"
    
    # 2. Company Name
    company_el = card.find('a', class_=lambda c: c and 'CompanyLinkResolver' in c)
    if not company_el:
        company_el = card.find(class_=lambda c: c and 'CompanyInformation' in c)
    company = company_el.get_text(strip=True) if company_el else "Not Specified"
    
    # 3. Location
    location_el = card.find(class_=lambda c: c and 'LocationWrapper' in c)
    if not location_el:
        location_el = card.find('div', class_=lambda c: c and 'OpportunityInfo' in c)
    location = location_el.get_text(strip=True) if location_el else "Not Specified"
    
    # 4. Salary Range (Regex search on card text)
    salary = "Gaji Tidak Ditampilkan"
    card_text = " ".join(card.stripped_strings)
    patterns = [
        r"Rp\s*[\d.,]+\s*jt\s*-\s*[\d.,]+\s*jt",
        r"Rp\s*[\d.,]+\s*-\s*[\d.,]+\s*jt",
        r"Rp\s*[\d.,]+\s*jt",
        r"Rp\s*[\d.,]+\s*-\s*[\d.,]+"
    ]
    for pattern in patterns:
        match = re.search(pattern, card_text, re.IGNORECASE)
        if match:
            salary = match.group(0).strip()
            break
            
    # Temporary debugging log to verify salary extraction
    logger.info(f"Salary detected: {salary}")
    
    # 5. Posted Date
    posted_el = card.find(class_=lambda c: c and any(x in c for x in ['UpdatedAtMessage', 'UpdatedTimeContainer', 'OpportunityMeta']))
    posted = posted_el.get_text(strip=True) if posted_el else "Not Specified"
    
    # 6. Parse Tags (job_type, experience_level, education_req, skills)
    job_type = "Not Specified"
    experience = "Not Specified"
    education = "Not Specified"
    skills = []
    
    tag_elements = card.find_all(class_=lambda c: c and ('Tag-sc' in c or 'TagStyle' in c or 'aries-tag' in c))
    tag_texts = list(set([t.get_text(strip=True) for t in tag_elements if t.get_text(strip=True)]))
    
    for t_text in tag_texts:
        t_low = t_text.lower()
        if any(x in t_low for x in ['kontrak', 'magang', 'full-time', 'part-time', 'freelance', 'internship', 'penuh waktu', 'paruh waktu']):
            job_type = t_text
        elif 'tahun' in t_low or 'year' in t_low or re.search(r'\d+\s*-\s*\d+', t_low):
            experience = t_text
        elif any(x in t_low for x in ['minimal', 'pendidikan', 'sma', 'smk', 'diploma', 'sarjana', 's1', 's2', 'd3']):
            education = t_text
        elif t_low not in ['perusahaan premium']:
            skills.append(t_text)
            
    record = {
        "job_title": title,
        "company_name": company,
        "location": location,
        "salary_range": salary,
        "job_type": job_type,
        "experience_level": experience,
        "education_req": education,
        "job_requirements": " | ".join(skills) if skills else "Not Specified",
        "posted_date": posted,
        "source_platform": SOURCE_PLATFORM
    }
    
    return record

def collect_listing_cards(driver, max_scroll_rounds=5, delay_between_pages=2.0, keyword=None):
    records = []
    logger.info(f"[Glints] Memulai pengumpulan kartu pekerjaan (Keyword: {keyword}, Page: 1)")
    
    url = "https://glints.com/id/opportunities/jobs/explore?country=ID&page=1&locationName=All%20Cities%2FProvinces"
    if keyword:
        kw_encoded = keyword.replace(" ", "%20")
        url += f"&keyword={kw_encoded}"
        
    logger.info(f"[Glints] Membuka listing -> {url}")
    
    try:
        driver.get(url)
        time.sleep(2)
        
        # Scroll to load elements dynamically
        for scroll_round in range(1, max_scroll_rounds + 1):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(delay_between_pages)
            
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all('div', class_=lambda c: c and 'CompactJobCard-sc' in c)
        logger.info(f"  [Glints] Menemukan {len(cards)} kartu pekerjaan di DOM.")
        
        page_records_count = 0
        for card in cards:
            rec = parse_job_card_directly(card, keyword)
            if rec:
                records.append(rec)
                page_records_count += 1
        logger.info(f"  [Glints] Sukses memproses {page_records_count} kartu.")
        
    except Exception as e:
        logger.error(f"[Glints Error] Gagal memproses: {e}")
        time.sleep(2)
        
    return records

def save_csv(records):
    df = pd.DataFrame(records, columns=COLUMN_SCHEMA)
    df.drop_duplicates(subset=["job_title", "location", "company_name"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    os.makedirs(os.path.dirname(CSV_FILE_PATH), exist_ok=True)
    if os.path.exists(CSV_FILE_PATH):
        try:
            os.remove(CSV_FILE_PATH)
        except Exception as e:
            logger.warning(f"Gagal menghapus file lama: {e}")
            
    df.to_csv(CSV_FILE_PATH, index=False, encoding="utf-8-sig")
    logger.info(f"Dataset berhasil disimpan ke -> {CSV_FILE_PATH}")
    return len(df)

def main():
    logger.info("Memulai Glints Page 1 Card-Only Job Vacancy Scraper...")
    driver = setup_driver()
    records = []
    seen_keys = set()
    
    KEYWORDS = [
        # Software Engineering
        "software engineer", "software developer", "backend developer", "frontend developer",
        "full stack developer", "web developer", "mobile developer", "android developer",
        "ios developer", "devops engineer", "site reliability engineer", "qa engineer",
        "automation tester",
        # Data & AI
        "data analyst", "data scientist", "data engineer", "machine learning engineer",
        "ai engineer", "business analyst", "business intelligence analyst", "bi analyst",
        # Product
        "product manager", "project manager", "scrum master", "product owner",
        # Design
        "ui ux designer", "product designer", "graphic designer",
        # Business
        "marketing", "digital marketing", "sales", "finance", "accounting", "hr", "recruitment",
        # Entry-Level
        "internship", "management trainee", "graduate program",
        # Operations
        "administrator", "customer service", "operations", "procurement", "supply chain"
    ]
    
    try:
        for kw in KEYWORDS:
            logger.info(f"\n--- Mengambil Lowongan untuk Keyword: '{kw}' ---")
            extracted_records = collect_listing_cards(driver, max_scroll_rounds=5, delay_between_pages=2.0, keyword=kw)
            
            # Add and deduplicate records globally
            new_added = 0
            for rec in extracted_records:
                key = (rec["job_title"].lower().strip(), rec["company_name"].lower().strip(), rec["location"].lower().strip())
                if key not in seen_keys:
                    seen_keys.add(key)
                    records.append(rec)
                    new_added += 1
                    
            logger.info(f"Summary: Berhasil menambahkan {new_added} record baru unik. Total unik global: {len(records)}.")
            time.sleep(2)
            
        # Simpan records ke CSV
        if records:
            saved_count = save_csv(records)
            logger.info(f"Scraping selesai. Total data unik tersimpan ke glints_jobs.csv: {saved_count}")
        else:
            logger.warning("Tidak ada data yang berhasil diekstrak.")
            
    except Exception as e:
        logger.error(f"Terjadi kesalahan utama: {e}")
    finally:
        logger.info("Menutup Chrome Driver...")
        driver.quit()

if __name__ == "__main__":
    main()
