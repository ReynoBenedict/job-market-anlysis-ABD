# API

Interactive OpenAPI documentation: `http://localhost:8010/api/docs` (schema at
`/api/openapi.json`). All routes are under `/api/v1`.

## Conventions
- Categorical values are `{ "code": "FULL_TIME", "label": "Penuh waktu" }`.
- Pagination: `page` (≥1), `page_size` (1–50); responses carry `total` and `total_pages`.
  Sorting always ends with the job ID, so pages are stable.
- Errors: `{ "error": { "code", "message", "details": [{field, message}], "request_id" } }`.
  422 `invalid_request`, 404 `job_not_found`/`not_found`, 401/503 for admin, 500
  `internal_error` (details are logged with the request ID, never returned).
- Every response has an `X-Request-ID` header. A caller-supplied `X-Request-ID` is reused
  only if it matches `[A-Za-z0-9._-]{1,64}`; otherwise a new ID is generated.
- Unknown query parameters are ignored. `source_url` fields are returned only for
  `http(s)` URLs (otherwise `null`).

## Shared filters (search and analytics)
`q` (≤100 chars; every word must match title, company, location, or tags; LIKE wildcards
are literal; at most 8 words are used), repeated `province`, `city`, `role_family`,
`employment_type`, `work_arrangement`, `education`, `experience`, `source` (≤40 values,
each ≤200 chars; NUL characters are a 422); `salary_disclosed` (bool, by status only);
`salary_min`/`salary_max` (monthly IDR, range overlap, **comparable salaries only**, see
below); `freshness` (`POTENTIALLY_ACTIVE | NOT_SEEN_RECENTLY | EXPIRED_BY_SOURCE`).

## Salary eligibility (one rule everywhere)
A salary is *comparable* (`salary.comparable = true`) when it is DISCLOSED, in IDR, has
both monthly bounds (monthly or yearly/12; hourly/daily/weekly never converted),
`monthly_min <= monthly_max`, and a monthly midpoint ≥ Rp500,000. Only comparable salaries
enter `/salaries/overview` (percentiles, histogram, medians, flag counts),
`/salaries/compare`, the `salary_min`/`salary_max` filters, `sort=salary_desc` (others
sort with unknown salaries), and `/filters` `salary_monthly_range`. Stored data is not
changed. Values > Rp100 jt and wide ranges stay included but are counted in `flag_counts`.
Defined in `backend/talentscope/analytics/salary_rule.py`.

Lifecycle: `EXPIRED_BY_SOURCE` if `expires_at < now`; else `POTENTIALLY_ACTIVE` if
`last_seen_at >= now - FRESHNESS_WINDOW_DAYS`; else `NOT_SEEN_RECENTLY`. A future or missing
deadline never makes a listing active; there is no "verified active" state.

## Public endpoints
| Method & path | Returns |
|---|---|
| GET `/health` | `{status, version}`; 503 if the database is unreachable |
| GET `/jobs` | Page of `JobSummary`; `sort` = `newest` (default), `relevance` (needs `q`), `salary_desc`, `title`, `company` |
| GET `/jobs/{id}` | `JobDetail`: summary + provenance (`source_records`), quality flags, source texts |
| GET `/filters` | Values and counts for every filter (200 most common per filter; `city` has more); monthly range of comparable salaries |
| GET `/market/overview` | Totals (jobs, source records, companies, cities, provinces, `publisher_sites`, disclosed salaries, remote/hybrid) + `scope` |
| GET `/market/breakdown/{dimension}` | `rows[{key,label,count,share}]`, `total`, `other_count`, `distinct_values`; dimensions: province, city, role_family, employment_type, work_arrangement, education, experience, company, title, source |
| GET `/salaries/overview` | Status counts, `eligible` (comparable) n and `eligible_share` (of all filtered jobs), `excluded_implausible`, `min_monthly_midpoint`, period-assumed n, percentiles p10–p90 of midpoints (null if n < 5), `median_min`/`median_max` = medians of range lower/upper bounds, 2-jt histogram, flag counts, `scope` |
| GET `/salaries/compare?by=` | Per-group n, quartiles (null if n < 5), `small_sample` (n < 20); `by` excludes title/company |
| GET `/skills/source-tags` | Visible card-tag counts with truncation statistics |
| GET `/sources/coverage` | Every registered source with status, decision reason, job count, last successful run |

`scope` = `{observed_from, observed_to, published_from, published_to, is_historical,
freshness_window_days, sources, publisher_sites, coverage_notes}`. `observed_*` are
min/max `last_seen_at` (observation or archive-capture time); `published_*` are min/max
`published_at` stated by listings (null if none). `sources` are ingestion datasets;
`publisher_sites` counts distinct publisher hosts of `source_url` (lower-cased, without
`www.`); jobs without a URL add none. `SourceRef` and `/sources/coverage` items carry
`public_label` and `public_condition` (public reuse statement; null when unset).

## Admin endpoints (`Authorization: Bearer $ADMIN_API_TOKEN`)
| Method & path | Notes |
|---|---|
| GET `/admin/sources` | Registry with connector, pause state, last run/success |
| POST `/admin/sources/{id}/pause` | Body `{reason}`; audited |
| POST `/admin/sources/{id}/resume` | 409 unless the source is approved |
| GET `/admin/ingestion-runs[?source_id=]` | Paginated runs |
| GET `/admin/ingestion-runs/{id}` | One run |
| GET `/admin/data-quality` | Missing-field counts, flags, location confidence, same-source fingerprint groups, normalization versions |
| GET `/admin/audit-events` | Paginated audit log |

Ingestion is deliberately not triggerable over HTTP (ADR-0013).
