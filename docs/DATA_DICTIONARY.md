# Data dictionary

## Source file: `data/raw/glints_jobs.csv`

1,133 rows, UTF-8 with BOM, 205 KB, committed 2026-06-13 02:57 WIB. Produced by the
legacy Selenium scraper from Glints search-result **cards** (page 1 of 44 keyword
searches). `data/processed/*.csv` are derived by the legacy pandas scripts and are not
used by TalentScope (they replaced missing salaries with 0).

| Column | Content | Notes |
|---|---|---|
| job_title | Title as written | 577 distinct |
| company_name | Company as written | 917 distinct; includes staffing vendors and a Glints channel |
| location | `City,Province` | all rows structured; 76 cities, 16 provinces |
| salary_range | `Rp 7 jt-9 jt`, `Rp 2,5 jt`, or `Gaji Tidak Ditampilkan` | no currency code, **no period**, NBSP separators |
| job_type | Penuh Waktu, Kontrak, Magang, Freelance, Paruh Waktu | |
| experience_level | `1–3 tahun` … `Lebih dari 10 tahun`, `Not Specified` | en dash |
| education_req | `Minimal Sarjana (S1)` etc. | |
| job_requirements | card tags joined by ` \| ` | truncated with `+N`; includes Hybrid/Remote |
| posted_date | `3 hari yang lalu`, `Kemarin`, `UrgentKemarin` | relative to an unknown observation time |
| source_platform | always `glints` | |

## Database (`backend/talentscope/models.py`, migration `0001`)

### `jobs` (canonical vacancy)
| Column | Type | Meaning |
|---|---|---|
| id | uuid | stable internal ID |
| primary_source_id | text → sources | source that owns the canonical fields |
| fingerprint | text | SHA-256 of normalized title, company, city (dedupe candidate key) |
| title / company_name / location_text | text | as provided (cleaned whitespace) |
| role_family | code | `RoleFamily` (taxonomy 2026.10.1) |
| city / province / location_confidence | text | province from the 38-province list; `SOURCE_STRUCTURED`, `INFERRED`, `UNKNOWN` |
| employment_type_text / employment_type | text / code | original label + `EmploymentType` |
| work_arrangement / work_arrangement_evidence | code / text | `ONSITE/HYBRID/REMOTE/FIELD/UNKNOWN` + the text that justified it |
| experience_text / experience_min_years / experience_max_years / experience_band | | band from the lower bound |
| education_text / education_level | text / code | |
| salary_text | text | original |
| salary_status | code | `DISCLOSED, NOT_DISCLOSED, NEGOTIABLE, INVALID, UNPARSEABLE` |
| salary_min / salary_max / salary_currency / salary_period | | amounts only when DISCLOSED (check constraint) |
| salary_period_assumed | bool | period came from a documented source convention |
| salary_monthly_min / salary_monthly_max | bigint | only for MONTH or YEAR (÷12) periods |
| source_tags / hidden_tag_count | text[] / int | visible card tags (work-arrangement tags removed) and "+N" total |
| description | text | NULL unless a source provides and permits it |
| posted_text / posted_age_days / is_urgent | | relative age only; no invented dates |
| published_at / expires_at | timestamptz | NULL for the snapshot |
| first_seen_at / last_seen_at | timestamptz | observation times (snapshot: upper bound 2026-06-12T19:57:02Z) |
| source_url | text | validated http(s) only; NULL for the snapshot |
| quality_flags | text[] | see table below |
| normalization_version | text | `1.1+roles-2026.10.1`; bump to re-normalize on re-import |
| search_text | text | lower-cased title/company/location/tags, trigram-indexed |

**Quality flags:** `SALARY_PERIOD_ASSUMED`, `SALARY_CURRENCY_ASSUMED`,
`SALARY_SINGLE_VALUE`, `SALARY_WIDE_RANGE` (max > 4× min), `SALARY_HIGH_OUTLIER`
(> Rp100 jt/month), `SALARY_LOW_OUTLIER` (< Rp500 rb/month), `SALARY_MIN_GREATER_THAN_MAX`,
`TAGS_TRUNCATED`, `LOCATION_UNRESOLVED`, `ROLE_UNCLASSIFIED`, `POSTING_AGE_APPROXIMATE`,
`INVALID_SOURCE_URL`.

### `source_records`
`(source_id, source_key)` unique; `source_key_kind` (`source_id | url |
content_fingerprint`), `source_url`, `job_id`, `match_rule` (`new_job |
cross_source_fingerprint`), `content_hash`, `raw_fields` (JSONB), `parser_version`,
first/last seen and run IDs.

### `sources`
Registry entry: `permission_status` (SRS §3.4 states, check-constrained),
`technical_method`, `connector` + `connector_config`, `is_paused`, policy URLs,
`decision_reason`, `attribution_text`, `retention_constraints`, `coverage_note`,
`reviewed_at`.

### `ingestion_runs`
`status` (`RUNNING, SUCCEEDED, PARTIAL, FAILED, REFUSED`), `error_category`, sanitized
`message`, `parser_version`, `input_reference` (file + SHA-256 or endpoint),
`observed_at`, record counts (`seen, created, updated, unchanged, rejected,
cross_source_matches`), `details` (rejection samples, `empty_result`), timestamps.

### `audit_events`
Append-only: `actor, action, entity_type, entity_id, reason, details, created_at`.
