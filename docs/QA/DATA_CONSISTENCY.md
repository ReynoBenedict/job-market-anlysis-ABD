# Data consistency: reconciliation of counts

**Measured 2026-10-18 between 08:50 and 09:10 WIB** on the real lake (`./lake`) and the app
database (Docker PostgreSQL, `localhost:5433/talentscope`, read-only queries). Nothing
synthetic is counted (`lake/synthetic/` is never read). Every metric names its
denominator. Status counts depend on the time of the query (a deadline passes, a
30-day window moves), so they are given with the query time.

Two states are reported:

- **App now**: the database as last published (before the 2026-10-18 data-layer fixes).
- **Lake now / after republish**: the rebuilt silver/gold with the fixes. These are the
  values the app will show once the tech lead republishes (steps in §6). Rows marked
  **changes after republish** are expected to move.

> **Republish done and verified (2026-10-18 09:40–09:55 WIB).** `lake run --publish`
> (6,174 seen, 12 retired, 48 s), then `ingest glints-snapshot-2026-06`; a second run
> created 0, updated 0, retired 0. SQL at 09:54 WIB confirms every "after republish"
> value below: jobs 7,307 (6,174 + 1,133), expired 5,227, Riwayat lowongan 2,080
> (947 + 1,133), recent 0, published deadlines 5,347, comparable salaries 1,683
> (825 + 858; `/salaries/overview` eligible 1,683, excluded_implausible 0), city values
> 524, cross-source matches 0, bisakerja.id 55 → 43. The "App now" column is therefore
> the pre-fix state and kept for the audit trail.

## 1. How the levels fit together

```
archived pages fetched 12,418 (failed 882)  → pages with JobPosting 11,943
  → observations 9,929 (after per-site review; 0 from unchanged re-captures)
  → source records 9,919 (one per page posting)  = valid 9,349 + rejected 570
  → canonical vacancies 6,174 (lake now; app now 6,186)
app jobs = archive vacancies + Glints snapshot listings 1,133 − cross-source matches 0
         = 7,319 now → 7,307 after republish
```

Checks that must hold (all hold on 2026-10-18):

| Check | Expected | Now |
|---|---|---|
| app archive jobs = lake canonical vacancies of the last published build | equal | 6,186 = 6,186 (published build); lake now 6,174 |
| app source records per source = app jobs per source (no cross-source matches) | equal | 6,186 / 6,186 and 1,133 / 1,133 |
| observations ≥ source records ≥ valid source records ≥ vacancies | ordered | 9,929 ≥ 9,919 ≥ 9,349 ≥ 6,174 |
| valid + rejected source records = source records | equal | 9,349 + 570 = 9,919 |
| Σ vacancies per publisher domain = vacancies | equal | 6,174 (§3.4) |
| silver/gold rebuilt twice from the same bronze | identical | identical (§5) |

## 2. Commands

Lake (from the repository root):

```sh
export DATABASE_URL=postgresql+psycopg://talentscope:talentscope@localhost:5433/talentscope
export PYTHONIOENCODING=utf-8
talentscope lake silver --full     # 9,929 observations (9,359 valid), 9,919 source records, 6,174 vacancies
talentscope lake gold              # 6,174 vacancies from 22 sites, 3,674 employers
talentscope lake report            # inventory, completeness, time coverage (gold/report.json)
```

Lake SQL (DuckDB; `v` = `lake/silver/vacancies.parquet`, `r` = `source_records.parquet`,
`o` = `observations_all.parquet`):

```sql
-- L1 levels
select (select count(*) from o) observations,
       (select count(*) from o where observation_type = 'reobservation') reobservations,
       (select count(*) from o where is_valid) valid_observations,
       (select count(*) from r) source_records,
       (select count(*) from r where is_valid) valid_source_records,
       (select count(*) from r where not is_valid) rejected_source_records,
       (select count(*) from v) canonical_vacancies,
       round(1 - (select count(*) from v) / (select count(*) from r where is_valid), 4) duplicate_rate;
-- L2 rejections
select reason, count(*) from (select unnest(invalid_reasons) reason from r) group by 1 order by 2 desc;
-- L3 dedup and coverage
select count(*) filter (where source_sites > 1) multi_site, count(*) filter (where merged_fuzzy) fuzzy,
       count(*) filter (where city_templated) campaigns, count(*) filter (where len(crawls) > 1) multi_crawl,
       count(distinct organization_key) employers, count(distinct source_domain) sites,
       count(distinct city) cities, count(distinct province) provinces from v;
-- L4 salary and deadline reliability
select count(*) filter (where salary_status = 'DISCLOSED') disclosed, count(salary_monthly_min) monthly_idr,
       count(*) filter (where salary_reliable) reliable,
       count(*) filter (where salary_unreliable_reason = 'SITE_TEMPLATE') site_template,
       count(*) filter (where salary_unreliable_reason = 'BELOW_MONTHLY_FLOOR') below_floor,
       count(valid_through) with_deadline, count(*) filter (where valid_through_reliable) reliable_deadline,
       count(*) filter (where valid_through is not null and not valid_through_reliable) template_deadline
from v;
-- L5 per publisher domain
select source_domain, count(*) vacancies, sum(source_records) member_records, sum(observations) observations
from v group by 1 order by 2 desc, 1;
-- L6 status the app will show after republish (query time 2026-10-18 09:05 WIB)
select case when valid_through_reliable and valid_through < current_date then 'EXPIRED_BY_SOURCE'
            when last_seen_at >= now() - interval 30 day then 'POTENTIALLY_ACTIVE'
            else 'NOT_SEEN_RECENTLY' end status, count(*)
from v group by 1;
```

App SQL (PostgreSQL, run with `set default_transaction_read_only = on`):

```sql
-- D1 jobs and source records per source
select s.id source,
       (select count(*) from jobs j where j.primary_source_id = s.id) jobs_primary,
       (select count(*) from source_records r where r.source_id = s.id) source_records,
       (select count(*) from source_records r where r.source_id = s.id and r.match_rule <> 'new_job') cross_source_matches
from sources s where exists (select 1 from source_records r where r.source_id = s.id);
-- D2 jobs backed by several records / several sources
select count(*) filter (where n > 1), count(*) filter (where sources > 1)
from (select job_id, count(*) n, count(distinct source_id) sources from source_records group by 1) x;
-- D3 status (the rule of analytics/filters.py freshness_of, 30-day window)
select primary_source_id,
       count(*) filter (where expires_at < now()) expired_by_source,
       count(*) filter (where (expires_at is null or expires_at >= now()) and last_seen_at <  now() - interval '30 days') history,
       count(*) filter (where (expires_at is null or expires_at >= now()) and last_seen_at >= now() - interval '30 days') seen_recently_unverified,
       count(*) total
from jobs group by 1;
-- D4 archive jobs per publisher domain
select regexp_replace(substring(source_url from '^https?://([^/]+)'), '^www\.', '') publisher_domain,
       count(*) jobs, count(*) filter (where expires_at < now()) expired
from jobs where primary_source_id = 'commoncrawl-jobposting' group by 1 order by 2 desc;
-- D5 latest run per source
select distinct on (source_id) source_id, status, records_seen, records_created, records_updated,
       records_unchanged, records_rejected, cross_source_matches
from ingestion_runs order by source_id, started_at desc;
-- D6 companies, cities, provinces
select coalesce(primary_source_id, 'ALL'), count(distinct lower(company_name)), count(distinct city),
       count(distinct province), round(100.0 * count(city) / count(*), 1), round(100.0 * count(province) / count(*), 1)
from jobs group by rollup (primary_source_id);
-- D7 salary coverage and validity (validity = the API statistics rule)
select coalesce(primary_source_id, 'ALL'), count(*),
       count(*) filter (where salary_status = 'DISCLOSED') disclosed,
       count(*) filter (where salary_monthly_min is not null) monthly_idr,
       count(*) filter (where salary_monthly_min <= salary_monthly_max
                        and (salary_monthly_min + salary_monthly_max) / 2.0 >= 500000) valid_for_statistics,
       count(*) filter (where (salary_monthly_min + salary_monthly_max) / 2.0 < 500000) below_floor,
       count(*) filter (where salary_monthly_min > salary_monthly_max) min_gt_max,
       count(*) filter (where salary_monthly_max > 100000000) above_100m_flagged,
       count(*) filter (where salary_text like 'Nilai gaji%') explained_unreliable
from jobs group by rollup (primary_source_id);
-- D8 attribute coverage
select coalesce(primary_source_id, 'ALL'), count(*),
       round(100.0 * count(*) filter (where education_level <> 'UNKNOWN') / count(*), 1) education,
       round(100.0 * count(*) filter (where experience_band <> 'UNKNOWN') / count(*), 1) experience,
       round(100.0 * count(*) filter (where cardinality(source_tags) > 0) / count(*), 1) skill_tags,
       round(100.0 * count(*) filter (where role_family <> 'OTHER') / count(*), 1) role_named,
       round(100.0 * count(*) filter (where expires_at is not null) / count(*), 1) deadline
from jobs group by rollup (primary_source_id);
```

## 3. Results

### 3.1 Rows, records, observations, duplicates

| Metric | Denominator | App now | Lake now (= after republish) |
|---|---|---:|---:|
| App jobs | — | 7,319 | 7,307 |
| ↳ archive vacancies (commoncrawl-jobposting) | — | 6,186 | **6,174** (changes after republish) |
| ↳ Glints snapshot listings | — | 1,133 | 1,133 |
| App source records | — | 7,319 (6,186 + 1,133) | 7,307 |
| Jobs backed by > 1 record / > 1 source | app jobs | 0 / 0 | 0 / 0 |
| Cross-source matches | snapshot records | 0 | 0 (§4.1) |
| Observations (archive) | — | 9,929 | 9,929 |
| ↳ from unchanged re-captures | observations | 0 | 0 |
| Valid observations | observations | 9,359 | 9,359 |
| Source records (archive) | — | 9,919 | 9,919 |
| Rejected source records | source records | 570 (567 outside Indonesia, 3 no employer) | 570 |
| Duplicate rate, valid records → vacancies | valid source records 9,349 | 33.83% | **33.96%** |
| Vacancies on > 1 site / fuzzy-merged | vacancies | 534 / 22 | 534 / 22 |
| SEO campaigns (one vacancy each) | vacancies | 36 (from 26 campaigns, split by date) | **24** |
| Vacancies seen in > 1 crawl | vacancies | 353 | **349** |
| Last publish run (commoncrawl) | records seen | SUCCEEDED, 6,187 seen, 50 created, 6,137 updated, 0 rejected | — |
| Last import run (Glints) | records seen | SUCCEEDED, 1,133 seen, 1,133 updated, 0 rejected | — |

The archive's 6,186 → 6,174 change is entirely the campaign fix: 16 bisakerja.id campaign
vacancies ("ART (Pembantu Rumah Tangga)" in 3 rotating title variants and 4 date batches,
"Kurir Motor JNE" in 3 batches) become 4. No other vacancy changes membership
(compared by member record keys: 0 records dropped or added, 0 vacancies split).

### 3.2 Status

Rule: `expires_at` before now → "Kedaluwarsa menurut sumber"; otherwise last seen within
30 days → "Baru terlihat, belum diverifikasi"; otherwise "Riwayat lowongan". "Aktif
terverifikasi" needs a permitted live check, which no source has. Denominator: jobs.

| Status | App now (09:00 WIB) | After republish (computed on the lake at 09:05 WIB) |
|---|---:|---:|
| Kedaluwarsa menurut sumber (archive) | 5,783 | **5,227** |
| Riwayat lowongan (archive) | 403 | **947** |
| Baru terlihat, belum diverifikasi | 0 | 0 |
| Aktif terverifikasi | 0 | 0 |
| Glints snapshot (all Riwayat lowongan, no deadlines) | 1,133 | 1,133 |

The −556 expired: 547 jobs whose deadline is a site theme default (lokerbekasi.my.id 407,
mediaanalisindonesia.co.id 124, bisakerja.id 16; LAKE.md "Deadline reliability") and 9 jobs
whose deadline is today (2026-10-18): they were shown as expired from 07:00 WIB because
the deadline was published as 00:00 UTC; it is now 23:59:59 WIB of the deadline date
(12 jobs had today's deadline; 3 of them are on template sites). No status is set by hand.
The "expired" count keeps growing as deadlines pass.

### 3.3 Coverage and validity

Denominator: jobs of the source (app) or vacancies (lake).

| Metric | Archive, app now | Archive, after republish | Glints snapshot |
|---|---:|---:|---:|
| Salary disclosed (any form) | 828 published; 5,739 disclosed in the lake | same | 858 |
| Monthly IDR salary published | 828 | **825** | 858 |
| Valid for statistics (midpoint ≥ Rp500,000 and min ≤ max) | 825 | 825 | 858 |
| Below the Rp500,000 monthly floor (published as amounts) | **3** (Rp2–897, Rp5–938, Rp5–877) | **0** (sent as explanation text) | 0 |
| min > max | 0 | 0 | 0 |
| Monthly max > Rp100 million (flagged, kept) | 0 | 0 | 1 (Rp140,000,000) |
| Salary explained as unreliable (`salary_text` "Nilai gaji ...") | 4,401 (site template) | **4,404** (4,401 template + 3 implausible) | 0 |
| Deadline published (`expires_at`) | 5,905 (95.5%) | **5,347 (86.6%)** | 0 |
| Deadline kept only as source value (`raw_fields.valid_through_unreliable`) | — | 546 | — |
| Education known | 65.6% | ≈ same | 100.0% |
| Experience known | 0.4% (sites rarely give `experienceRequirements`) | ≈ same | 81.8% |
| Skill tags | 0.0% (descriptions are not published) | same | 90.0% |
| Role family named (not "Lainnya") | 82.2% | ≈ same | 97.2% |
| City known / province known | 98.0% / 94.9% | ≈ same | 100% / 100% |

All app jobs: education 71.0%, experience 13.0%, skill tags 13.9%, role named 84.5%,
deadline 80.7% (→ ≈ 73% after republish).

Salary validity thresholds (shared with the API statistics rule): monthly IDR midpoint
≥ Rp500,000 (`IDR_MONTHLY_LOW_OUTLIER`); a range with minimum > maximum is invalid;
template-site salaries are unreliable; maxima above Rp100 million are flagged only.

### 3.4 Per publisher domain (archive)

App now = jobs whose representative page is on the domain (D4). Lake = vacancies (L5);
"member records" counts every source record merged into those vacancies, including
copies from other sites.

| Domain | App jobs now | expired now | Lake vacancies | member records | expired after republish |
|---|---:|---:|---:|---:|---:|
| lokeraceh.id | 1,582 | 1,581 | 1,582 | 1,806 | 1,581 |
| lokerbekasi.id | 1,266 | 1,244 | 1,266 | 1,809 | 1,244 |
| lowongankerjacirebon.id | 1,254 | 1,254 | 1,254 | 1,384 | 1,254 |
| gaji.co.id | 739 | 484 | 739 | 739 | 477 |
| aksesinfo.my.id | 515 | 510 | 515 | 515 | 510 |
| lokerbekasi.my.id | 418 | 407 | 418 | 438 | **0** (deadline template) |
| lokerbogor.co.id | 132 | 132 | 132 | 144 | 132 |
| mediaanalisindonesia.co.id | 128 | 124 | 128 | 129 | **0** (deadline template) |
| sportsmatters.id | 57 | 20 | 57 | 57 | 18 |
| bisakerja.id | 55 | 16 | **43** | 2,257 | **0** (deadline template) |
| lokerbandung.or.id | 23 | 4 | 23 | 23 | 4 |
| inaba.ac.id (pusatkarir.inaba.ac.id) | 3 | 0 | 3 | 3 | 0 |
| bursaloker.id | 2 | 2 | 2 | 2 | 2 |
| jogjaterkini.id | 2 | 0 | 2 | 2 | 0 |
| kusnendar.web.id | 2 | 2 | 2 | 2 | 2 |
| lokersamarinda.biz.id | 2 | 0 | 2 | 2 | 0 |
| lokerjakarta.id, lokerjogja.id, pixelninja.id | 1 each | 1 each | 1 each | 1 each | 1 each |
| openkerja.id, promag.id, sokacoke.id | 1 each | 0 | 1 each | 1 each | 0 |
| **Total** | **6,186** | **5,783** | **6,174** | 9,349 | **5,227** |

### 3.5 Companies, places

| Metric | App now | After republish |
|---|---:|---:|
| Distinct companies (lower-cased name), all jobs | 4,683 (archive 3,785, Glints 917) | ≈ same |
| Distinct employer keys, archive (lake) | 3,674 | 3,674 |
| Distinct city values, all jobs | 573 (archive 521, Glints 76) | **524** |
| Distinct provinces | 34 (archive 34, Glints 16) | 34 |

The city change comes from writing one regency one way ("Kab. Bandung" in Glints and
"Kabupaten Bandung" on archive sites were two values; 243 Glints jobs are affected) and
from the 12 merged campaign vacancies. Cities named without "Kota"/"Kabupaten"
("Bogor") stay separate because they are ambiguous.

## 4. Findings behind the numbers

### 4.1 Cross-source matches = 0 is plausible, not a blind spot

Matching links a new record to another source's job when exactly one job has the same
fingerprint (normalized title + company + city, else province). Measured on the app:

- exact fingerprint pairs Glints × archive: 0; same normalized company and title: 0;
- Glints jobs whose employer (normalized, legal form removed) appears in the archive: 37
  (40 with the lake's employer key), 74 pairs; the most similar titles within the same
  employer reach a similarity ratio of only 0.68 ("Sales Taking Order", Tangerang
  Selatan, Glints 2026-06 vs "Sales Taking Order Artaboga Jakarta", Cengkareng, posted
  2022-10); 0 pairs ≥ 0.8;
- same title and place but any employer: 48 pairs, all different employers
  ("Sales Executive", Makassar: PT Bahagia Indo Persada vs DESNET, ...).

The two sources barely overlap: a one-day Glints search for 44 mostly technology
keywords versus regional job blogs dominated by retail, sales and logistics roles from
2022–2026. One real blind spot was found and fixed: Glints writes "Kab. X", archive sites
"Kabupaten X", so the same regency produced different fingerprints. After the fix the
measured matches are still 0 (recomputed with the new rules for all 1,133 × 6,174 pairs).

### 4.2 Aggregator sites do not put themselves in the employer field

For the 8 aggregator domains (domain_reviews.py `aggregator=True`) with vacancies, the
employers are the hiring companies (top: gaji.co.id → PT Adira Dinamika Multi Finance
(58), Amartha, SPX Express; lokerbekasi.my.id → PT Jeje Harapan Transindo, PT BFI Finance;
sportsmatters.id → PT Sumber Alfaria Trijaya, PT Indomarco Prismatama, PT KAI). No
vacancy's employer contains its site's name, and silver already rejects the site's own
name as a placeholder. Recruitment agencies (RecruitFirst, BSS Recruitment Consultant)
appear as employers when the page names them as the hiring party; that is the source's
statement. The displayed title is the source's title with blog boilerplate removed
(original in `raw_fields.source_title`), and the link is the aggregator page that was
archived, not the employer's page; `raw_fields.aggregator_site = true` marks these.
Employer parsing problems seen are on a non-aggregator site: bisakerja.id puts the role
into the employer field ("Kurir Motor JNE", "Kurir Motor JNE Express") and rotates
spellings of Indomaret (5 variants), which splits its campaigns (LAKE.md, known limitation).

### 4.3 The reported listing (Satpam PT Petrosea Tbk, Tangerang)

sportsmatters.id, datePosted 2026-09-11T03:24:16Z, validThrough 2026-11-10T09:07:06Z,
archived 2026-09-12 20:55 WIB (app job c1f5ce13-8f12-4600-9717-d37444331ac8; three other
sportsmatters.id pages have the same dates). The deadline is parsed correctly and is in
the page's own JobPosting markup. Status "Riwayat lowongan" is correct: the deadline has
not passed, and the page was last seen 36 days ago (> 30). Whether 10 Nov is the
employer's deadline cannot be confirmed: the description says only "sebelum batas waktu
yang ditentukan", none of the site's 78 pages states its deadline in the text, and all
78 deadlines fall 31–61 days after posting, spread evenly (no fixed default; most common
offset 7.7%). The deadline-template rule therefore does not apply to this site (LAKE.md
explains why a band rule was rejected); the date is shown as the source's.

## 5. Pipeline robustness evidence

- **Idempotent rebuild:** `lake silver --full` + `lake gold`, twice; all 3 silver and 17
  gold Parquet files compared row by row (`EXCEPT ALL` both ways): 0 differing rows;
  `report.json` identical apart from `generated_at`/`seconds`. One non-determinism was
  found and fixed first: `gold/employers.parquet` chose the employer's display spelling
  with `any_value`, so 25 of 3,674 rows changed between rebuilds.
- **Half-published data:** fixed. A failing publish used to keep every 250-record commit
  and skip retirement, mixing two builds; the publish is now one transaction including
  retirement, and failures roll back (LAKE.md "Publishing"; tests in
  `tests/integration/test_lake_publish.py`).
- **Raw inputs unchanged:** `data/raw/glints_jobs.csv` sha256
  `c29229793e7be34149bf1f1965a12143c1d09ba777361d003496adc867e58d95`;
  `data/processed/jobs_featured.csv` `fb453aeb…16fa74e2`, `processed_jobs.csv`
  `5effe7df…c69bd4`; the 35 bronze files hash to the same combined digest before and after
  this work (`20714062…6b159e`, sha256 of the sorted per-file sha256 list).

## 6. Values that change after the tech lead republishes

Run order: `talentscope sources sync` (after worker 4's `public_label`/`public_condition`
migration), then `talentscope lake run --publish` (rebuilds silver/gold, publishes the archive
in one transaction), then re-run the Glints import (`talentscope ingest
glints-snapshot-2026-06`) so its rows pick up normalization 1.3 (regency spelling).
Expected afterwards: archive jobs 6,174; app jobs 7,307; expired ≈ 5,227 and history
≈ 947 (time-dependent); published deadlines 5,347; monthly salaries 825, all valid;
distinct cities 524; cross-source matches 0. Re-run the D-queries above to confirm.
