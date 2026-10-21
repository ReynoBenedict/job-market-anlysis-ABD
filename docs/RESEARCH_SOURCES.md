# TalentScope — Source Eligibility Research

Machine-readable companion: `docs/research/source_matrix.json`.

## 1. Method

- **Date:** all evidence was accessed on 2026-10-17 between about 04:30 and 05:05 UTC. Every `accessed_at` below means `2026-10-17T05:00Z ±30 min`.
- **What was checked:** for each source we read the current terms of service / user terms, robots.txt, API or developer documentation, and (where relevant) dataset licence pages. We used WebSearch only to find policy URLs. No job listing or search-result pages were collected. The only non-policy pages fetched were single homepages, fetched once to confirm that a source exists (Karir.com, Pintarnya, HiredToday, Kalibrr, Karirhub, Pasker ID, SSCASN, data.go.id).
- **Rules applied (SRS §0.3, §3.3–3.4, §13):**
  - Permission is never inferred from the absence of a prohibition.
  - robots.txt is treated as one input and never as a grant.
  - An explicit ban on scraping, automated collection or aggregation gives `BLOCKED` for automated collection. Written permission could change that.
  - Unclear terms give `NEEDS_REVIEW` or `REQUIRES_WRITTEN_PERMISSION`.
- **Limitations:**
  - The fetch tool converts pages to text and summarises them. Quotes are short exact phrases as returned. Indonesian clauses are quoted in the original with an English gloss.
  - Several pages could not be read: they returned HTTP 403, were client-rendered, refused the connection, or the domain was blocked for the tool. These are listed explicitly, and their contents were not guessed.
  - Long pages (Indeed legal, about 370k characters) were read only partly. Sections not read are noted.
  - Terms change. The JobStreet terms, for example, became effective 20 July 2026. Every decision must be re-reviewed before activation and periodically after it.
  - **This is not legal advice.** Indonesian law (including UU 27/2022 on personal data protection, copyright and database rights) and contract enforceability were not analysed. Counsel should review before any source is activated or any permission letter is relied on.

## 2. Summary table

| source_name | canonical_domain | category | permission_status | technical_method | decision | one-line reason |
|---|---|---|---|---|---|---|
| Glints | glints.com | general_board | BLOCKED | unknown | Exclude; ask for written consent | SRS-recorded clause bans scraping without prior written consent; terms returned HTTP 403 today, so the clause was not re-verified |
| JobStreet (SEEK) | id.jobstreet.com | general_board | BLOCKED | unknown | Exclude; written permission only | Terms (eff. 20 Jul 2026) ban robots, screen scraping and aggregation of content, including expired listings |
| LinkedIn Jobs | linkedin.com | general_board | BLOCKED | unknown | Exclude | User Agreement bans scraping/bots; robots `User-agent: * Disallow: /`; Job Posting API is inbound-only and closed |
| Indeed Indonesia | id.indeed.com | general_board | BLOCKED | unknown | Exclude; written permission only | Terms s.21 ban bots/scrapers/spiders without Indeed's written permission |
| Kalibrr | kalibrr.com | general_board | REQUIRES_WRITTEN_PERMISSION | unknown | Ask permission | Copying/distribution needs written permission; third-party syndication needs explicit permission |
| Dealls | dealls.com | general_board | NEEDS_REVIEW | unknown | Investigate / contact | Only HRIS-product terms found; they forbid sharing content without written consent; scope over job site unclear |
| KitaLulus | id.kitalulus.com | general_board | BLOCKED | unknown | Exclude | Terms ban scraping, combining/copying content, and reproducing content for public use |
| Karir.com | karir.com | general_board | BLOCKED | unknown | Exclude; written permission only | Terms ban automated data retrieval without permission and commercial use of content |
| Loker.id | loker.id | general_board | NEEDS_REVIEW | unknown | Investigate | Terms page returned HTTP 403; no decisive clause seen |
| Pintarnya | pintarnya.com | general_board | REQUIRES_WRITTEN_PERMISSION | unknown | Ask permission | Copying or commercial use of content requires written permission |
| TopKarir | topkarir.com | general_board | NEEDS_REVIEW | unknown | Check whether site is active | Connection refused; no terms retrievable |
| HiredToday | hiredtoday.com | general_board | NEEDS_REVIEW | unknown | Investigate / contact | Terms page client-rendered; text not readable |
| Tech in Asia Jobs | techinasia.com | niche_board | NEEDS_REVIEW | unknown | Investigate | Domain not fetchable by tool; terms not found |
| Pasker ID | paskerid.kemnaker.go.id | government | BLOCKED | unknown | Exclude automated; seek data-sharing agreement | Terms ban robots/crawlers/spiders; personal non-commercial use only |
| Pasker ID datasets | paskerid.kemnaker.go.id | dataset | REQUIRES_WRITTEN_PERMISSION | manual_import | Ask permission | Aggregate CSV/XLSX available, but no licence; site terms are non-commercial |
| Karirhub | karirhub.kemnaker.go.id | government | REQUIRES_WRITTEN_PERMISSION | unknown | Ask Kemnaker | No terms/licence/API found; sibling Pasker ID bans crawlers |
| SSCASN (BKN) | sscasn.bkn.go.id | government | NEEDS_REVIEW | manual_import | Investigate; manual curation at most | No terms/API found; periodic civil-service selection |
| Greenhouse Job Board API | boards-api.greenhouse.io | ats_api | REQUIRES_WRITTEN_PERMISSION | api | Per-employer consent | Public, documented, unauthenticated GET; intended for the customer's own careers pages; no aggregator terms |
| Lever Postings API | api.lever.co | ats_api | REQUIRES_WRITTEN_PERMISSION | api | Per-employer consent | Public documented API "designed to help you create a job site"; no aggregator licence |
| SmartRecruiters Posting API | api.smartrecruiters.com | ats_api | REQUIRES_WRITTEN_PERMISSION | api | Employer credential + consent | Requires API key/OAuth, which belong to the employer |
| Ashby posting API | api.ashbyhq.com | ats_api | REQUIRES_WRITTEN_PERMISSION | api | Per-employer consent | Unauthenticated, but documented for the customer's own careers page |
| Workday career sites | myworkdayjobs.com | employer_career_page | REQUIRES_WRITTEN_PERMISSION | unknown | Per-employer consent | Workday site terms ban data mining/robots; tenant-site coverage unclear; no public read API |
| schema.org JobPosting / Google for Jobs | developers.google.com | structured_data | NEEDS_REVIEW | html | Parser only, for already-approved pages | Markup guidelines grant no third-party reuse rights |
| Balikpapan open data (vacancies by education) | data.balikpapan.go.id | dataset | APPROVED_WITH_CONDITIONS | manual_import | Include (aggregate stats only) | Licence stated "Other (Public Domain)" |
| Satu Data Indonesia | data.go.id | dataset | NEEDS_REVIEW | manual_import | Check per-dataset licence | No portal-wide licence statement found |
| BPS | bps.go.id | dataset | NEEDS_REVIEW | manual_import | Verify terms directly | Terms pages returned HTTP 403; licence seen only in search snippets |
| Kaggle Indonesian job datasets | kaggle.com | dataset | NEEDS_REVIEW | manual_import | Exclude from product | No licence visible; content likely scraped from boards that ban aggregation |

## 3. Per-source details

Fields not mentioned are "none found". `allowed_fields` is "none" unless stated.

### 3.1 Glints
- terms_url: https://glints.com/id/about/terms. **HTTP 403** on 2026-10-17; https://glints.com/id/en/about/terms and https://glints.com/vn/about/terms also returned 403.
- robots_url: https://glints.com/robots.txt. One `user-agent: *` group. It disallows job explore pages with query parameters, recommended/bookmarked jobs, profiles, `/api/gt/` and tracking endpoints. Sitemaps are listed.
- api_feed_license_url: none found.
- login_required: partial.
- Key evidence: SRS §4.1 records a clause against "screen scraping, data mining, robots, or similar data extraction tools … without prior written consent". **We could not re-read it today.**
- rate_policy: n/a. attribution / retention: unknown.
- regional_coverage: Indonesia and other Southeast Asian countries.
- data_quality_risk: medium (structured fields, but tech/white-collar skew).
- decision: BLOCKED for automated collection. Changes only with written consent from Glints.
- notes: re-verify the clause from a browser before any outreach. Third-party "Glints scrapers" on Apify exist; they are not authorization.

### 3.2 JobStreet (SEEK)
- terms_url: https://id.jobstreet.com/id/terms ("Berlaku efektif 20 Juli 2026").
- robots_url: https://id.jobstreet.com/robots.txt. For `*`, it disallows `*/job/`, `*?`, `/graphql` and `/api/jobsearch/`. AI crawlers (GPTBot, CCBot, anthropic-ai and others) are disallowed from `/companies` and `*/job/`.
- login_required: partial.
- Key evidence:
  - §7(d): "Anda tidak boleh menggunakan penambangan data (data mining), robot, screen scraping, atau alat otomatis serupa".
  - §9(b): bans "proses otomatis, skrip, alat, bot, scraper".
  - §7(b)(ii): bans "mengagregasi, menyalin, atau menggandakan dengan cara apa pun setiap Konten atau informasi", which covers expired job listings.
  - §5(c): use limited to "kepentingan pribadi Anda yang bersifat non-komersial".
- retention_constraints: personal non-commercial use only.
- regional_coverage: national, broad occupations.
- data_quality_risk: low (if it were licensed).
- decision: BLOCKED. Only an express written permission or licence from SEEK changes this.

### 3.3 LinkedIn Jobs
- terms_url: https://www.linkedin.com/legal/user-agreement (effective 3 Nov 2025). Also https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software.
- robots_url: https://www.linkedin.com/robots.txt. It contains `User-agent: *` / `Disallow: /`. The header says "If you would like to apply for permission to crawl LinkedIn, please email whitelist-crawl@linkedin.com."
- api_feed_license_url: https://learn.microsoft.com/en-us/linkedin/talent/job-postings/api/overview. The page says "We are currently not accepting new partnerships", and the API is for posting jobs **to** LinkedIn.
- login_required: partial.
- Key evidence:
  - s.8.2 bans using "software, devices, scripts, robots … to scrape or copy the Services".
  - s.8.2 bans "Copy, use, display or distribute any information (including content) obtained from the Services".
  - s.8.2 bans "Use bots or other unauthorized automated methods".
  - The help page says: "we don't permit the use of any third party software … that scrape … LinkedIn's website".
- decision: BLOCKED.

### 3.4 Indeed Indonesia
- terms_url: https://id.indeed.com/legal ("Pembaruan Terakhir: 1 April 2026"). Characters 0–300,000 of about 370,000 were read; the last section was not read.
- robots_url: https://id.indeed.com/robots.txt. For `*`, it blocks `/viewjob`, `/rc/` and `/job/`, and allows `start=` only up to 90.
- api_feed_license_url: https://docs.indeed.com/job-sync-api. This is an inbound API for ATS partners and is "not available for direct employers"; it is not a search API. A third-party vendor blog claims the Publisher (search) API was shut down in 2023. Indeed has not confirmed this.
- login_required: partial.
- Key evidence:
  - s.21 bans "Menggunakan sistem otomatis apa pun (bot, scraper, spider, AI, atau AI Agentik) untuk mengakses, menambang data … tanpa izin tertulis dari Indeed".
  - s.21 also says "Anda tidak boleh menjelajahi, mengambil, mengekstrak data dari, memperbanyak, menggandakan, menyalin".
  - s.22.4 says the scraping restrictions "tetap berlaku sepenuhnya".
  - Job seeker licence: "untuk tujuan pribadi dan nonkomersial".
- attribution: the Hiring Lab data API reportedly carries a Creative Commons licence with attribution (s.3.2.4). That data is aggregate labour-market data and **not** listings; it was not evaluated further.
- decision: BLOCKED.
- notes: Indeed Hiring Lab aggregate data could be a separate future research item.

### 3.5 Kalibrr
- terms_url: https://kalibrr.com/terms ("Last updated March 2026").
- robots_url: https://www.kalibrr.com/robots.txt. For `*`, it disallows `/root` and `/candidate/profile`.
- login_required: partial.
- Key evidence:
  - "You shall not reproduce, copy, distribute, upload, post, transmit, or disseminate in any manner … without written permission from Kalibrr and the relevant owners."
  - Third parties may syndicate only if they have "obtained Kalibrr's explicit permission".
  - Kalibrr monitors "automated extraction, scraping".
  - Use is limited to "your personal and non-commercial use".
- regional_coverage: Indonesia and the Philippines. The homepage shows Indonesian locations.
- data_quality_risk: medium. The homepage showed "Rekruter terakhir aktif 5 months ago", which suggests stale postings.
- decision: REQUIRES_WRITTEN_PERMISSION. The terms explicitly contemplate a permission path.

### 3.6 Dealls
- terms_url: https://dealls.com/terms-and-condition ("Dimodifikasi pada: 6 Oktober 2026"). https://dealls.com/syarat-dan-ketentuan returned 404.
- robots_url: https://dealls.com/robots.txt contains `Allow: /` and a sitemap.
- login_required: partial.
- Key evidence:
  - The terms govern the Dealls/KantorKu HRIS products. The page does not state that they cover the public job board.
  - s.9.6(2) bans "mengungkapkan, menjual, membagi, memberikan konten, informasi … tanpa persetujuan tertulis dari Dealls Group".
  - No scraping clause was found.
- decision: NEEDS_REVIEW. Ask Dealls (PT SejutaCita Anak Muda Indonesia) which terms govern the job site and request written permission. A permissive robots.txt is not permission.

### 3.7 KitaLulus
- terms_url: https://id.kitalulus.com/en/syarat-dan-ketentuan (no date shown).
- robots_url: https://id.kitalulus.com/robots.txt. It disallows only `/kelas-online/`, `/styleguide/` and one download path.
- login_required: partial.
- Key evidence:
  - The terms ban creating accounts for "harvesting personal information from the Services, scraping content".
  - They ban "Combine, copy, or duplicate any KitaLulus content or information available from the Services".
  - They ban "Reproducing KitaLulus content for public use".
  - "Unauthorized commercial use of the Services is also prohibited."
- data_quality_risk: medium (blue-collar/entry-level focus, valuable coverage).
- decision: BLOCKED.

### 3.8 Karir.com
- terms_url: https://www.karir.com/info/terms-conditions. No date; operator is PT Qerja Manfaat Bangsa.
- robots_url: https://www.karir.com/robots.txt contains `Crawl-delay: 1` and disallows old-site paths.
- login_required: partial.
- Key evidence:
  - s.9.2 bans "menggunakan pengambilan data otomatis tanpa izin" and "menghindari batas akses".
  - s.8.5 bans using "untuk tujuan non-pribadi atau komersial, Konten apa pun pada Platform tanpa izin tertulis".
  - s.8.4 says content is "hanya boleh digunakan untuk kepentingan pribadi Pengguna yang bersifat non-komersial".
- decision: BLOCKED for automated collection. A permission path is implied ("tanpa izin").

### 3.9 Loker.id
- terms_url: https://www.loker.id/disclaimer. **HTTP 403**; not read.
- robots_url: https://www.loker.id/robots.txt (`User-agent: *`, empty Disallow).
- login_required: unknown.
- Key evidence: none decisive. Search snippets show general terms "berlaku pada 1 April 2007" and a statement that the operator may change rules.
- decision: NEEDS_REVIEW. The terms must be read in a browser and the operator asked in writing.

### 3.10 Pintarnya
- terms_url: https://pintarnya.com/landing/termsandconditions/ ("berlaku sejak tanggal November 2023"). Privacy policy: https://pintarnya.com/landing/privacypolicy/ (not read in detail).
- robots_url: https://pintarnya.com/robots.txt. It allows `/lowongan/` and blocks `/perusahaan`, search/sort parameters and application pages.
- login_required: partial.
- Key evidence: s.H.2 bans copying or "menggunakan untuk tujuan komersial setiap materi atau Konten Pintarnya … tanpa izin tertulis dari Pintarnya". No scraping clause was found.
- data_quality_risk: medium (informal/blue-collar roles; valuable but variable quality).
- decision: REQUIRES_WRITTEN_PERMISSION.

### 3.11 TopKarir
- terms_url: not found.
- robots_url: https://www.topkarir.com/robots.txt. **Connection refused**, as was https://topkarir.com/.
- decision: NEEDS_REVIEW. Confirm whether the service is still operating before doing any further work.

### 3.12 HiredToday
- terms_url: https://www.hiredtoday.com/en/term; privacy: https://www.hiredtoday.com/en/policy. Both are **client-rendered**; only template placeholders were returned.
- robots_url: https://www.hiredtoday.com/robots.txt. It blocks account/admin areas and allows the `/jobseeker/jobs` JSON endpoints and `/jobs-detail/`.
- regional_coverage: Indonesia (formerly CareerBuilder Indonesia, per a university thesis; not verified with the operator).
- decision: NEEDS_REVIEW. The open JSON endpoints in robots.txt do **not** establish reuse rights.

### 3.13 Tech in Asia Jobs
- terms_url / robots_url: **not retrievable**. The tool reported it is "unable to fetch from www.techinasia.com", and search did not surface the terms.
- decision: NEEDS_REVIEW.

### 3.14 Pasker ID
- terms_url: https://paskerid.kemnaker.go.id/ketentuan-pengguna (no date; "Copyright © 2026 Pusat Pasar Kerja Indonesia").
- robots_url: https://paskerid.kemnaker.go.id/robots.txt (`User-agent: *`, empty Disallow).
- login_required: partial.
- Key evidence:
  - s.3.2e bans "Menggunakan kode computer otomatis, proses program, robot, net crawler, spider".
  - s.3.1 limits use to "keperluan pribadi dan non-komersil".
  - s.4 bans "menyalin, membagikan ulang, mentransmisi ulang".
- regional_coverage: national public employment service.
- decision: BLOCKED for automated collection. The path forward is a formal data-sharing request (MoU or letter) to Pusat Pasar Kerja, Kemnaker. Government ownership does not imply an open licence.

### 3.15 Pasker ID datasets
- api_feed_license_url: https://paskerid.kemnaker.go.id/datasets. Ten aggregate datasets (job seekers, employers, vacancies by education / occupation group / sector / experience), 38 provinces, 2022–2024, CSV/XLSX.
- Key evidence: "no license statement" on the page. The site terms (s.4) allow content "hanya utuk penggunaan pribadi non-komersil".
- decision: REQUIRES_WRITTEN_PERMISSION before public display. Internal benchmarking also needs counsel's view, because the terms say "non-komersil". Very useful as a coverage benchmark if permission is granted.

### 3.16 Karirhub (SIAPkerja)
- terms_url: none found on the homepage. The footer links only to kemnaker.go.id about/contact/sitemap.
- robots_url: https://karirhub.kemnaker.go.id/robots.txt. It contains only content-signal comments, with no directives and no signals set.
- login_required: partial. Browsing is public; applying needs a SIAPkerja account (third-party guides).
- Key evidence: the homepage shows public listings with salary and closing date. No licence or API was found.
- decision: REQUIRES_WRITTEN_PERMISSION. Same operator family as Pasker ID, which bans crawlers.

### 3.17 SSCASN (BKN)
- terms_url / robots_url: not found or not checked. Helpdesk: https://helpdesk-sscasn.bkn.go.id.
- Key evidence: the homepage shows Sekolah Kedinasan 2026 information; the timeline says "Data tahapan belum tersedia".
- decision: NEEDS_REVIEW. Treat it as a separate public-sector category. At most, manually link to official BKN announcements; no automated formation collection until terms are found.

### 3.18 Greenhouse Job Board API
- api_docs_url: https://docs.greenhouse.io/job-board.html (redirected from developers.greenhouse.io).
- terms_url: https://www.greenhouse.com/legal (index page; no API terms listed). The My Greenhouse User Agreement (https://my.greenhouse.io/users/agreement, eff. 29 Jan 2025) bans "spiders, robots, crawlers" but covers only my.greenhouse.io.
- robots_url: https://boards.greenhouse.io/robots.txt (disallows `/embed/` only).
- login_required: no (GET).
- Key evidence: "Job Board data is publicly available, so authentication is not required for any GET endpoints." The purpose stated is that customers "can build careers pages with a unique look and feel".
- allowed_fields: none established. If an employer consents, the fields of interest are: title, location, department, updated_at, absolute_url, and content (description) only if the employer permits display.
- rate_policy: none documented. Use at most daily polling per board with backoff.
- attribution: link to the employer's `absolute_url`.
- decision: REQUIRES_WRITTEN_PERMISSION per employer (see §4).

### 3.19 Lever Postings API
- api_docs_url: https://github.com/lever/postings-api (README). Base URLs `https://api.lever.co/v0/postings/{site}` and `api.eu.lever.co`.
- terms_url: https://www.lever.co/agreements/tos (customer agreement, updated 25 Aug 2023; no aggregator clause).
- robots_url: https://jobs.lever.co/robots.txt (`Allow: /`, `Crawl-delay: 1`).
- Key evidence:
  - "This API is designed to help you create a job site."
  - "These jobs may be scraped by third parties." This is a warning to customers, not a licence.
  - The 2 requests/second limit applies to application POSTs; CORS is limited to the company's own domains.
- decision: REQUIRES_WRITTEN_PERMISSION per employer. This is the lowest-friction ATS once consent is obtained.

### 3.20 SmartRecruiters Posting API
- api_docs_url: https://developers.smartrecruiters.com/docs/posting-api.
- terms_url: https://www.smartrecruiters.com/legal/terms-of-use/ (candidate terms, "Last modified on 14th May 2019"; does not cover careers sites). Search snippets say API use is governed by the "SAP API Policy"; this was **not verified**.
- Key evidence: the API "supports both API Key and OAuth 2.0 Client Credentials authentication" and is intended for custom career sites.
- login_required: yes (employer credential).
- decision: REQUIRES_WRITTEN_PERMISSION. Needs an employer-issued credential and consent. Do not use keys not issued to TalentScope.

### 3.21 Ashby public job posting API
- api_docs_url: https://developers.ashbyhq.com/docs/public-job-posting-api. Endpoint `GET https://api.ashbyhq.com/posting-api/job-board/{JOB_BOARD_NAME}`.
- terms_url: https://www.ashbyhq.com/terms (customer terms, updated 29 Sep 2025; nothing on aggregators).
- robots_url: https://jobs.ashbyhq.com/robots.txt (disallows `/api/`, which concerns the hosted board host).
- Key evidence: "If you host your own careers page, you can use this data to populate it."
- decision: REQUIRES_WRITTEN_PERMISSION per employer.

### 3.22 Workday career sites
- terms_url: https://www.workday.com/en-us/legal/site-terms.html ("Last Updated: 08/13/2026").
- Key evidence:
  - The terms ban "data mining, robots or similar data gathering or extraction methods designed to scrape or extract data from our Sites".
  - They ban "Bypass or ignore instructions contained in our robots.txt file".
  - It is not stated whether `*.myworkdayjobs.com` tenant sites are "Sites".
- robots_url: www.myworkdayjobs.com did not resolve. Tenant hosts vary and were not checked (they would be employer pages).
- api: no public read API documented.
- decision: REQUIRES_WRITTEN_PERMISSION per employer. Workday's own terms lean restrictive.

### 3.23 schema.org JobPosting / Google for Jobs
- api_docs_url: https://developers.google.com/search/docs/appearance/structured-data/job-posting.
- Key evidence:
  - The guidelines cover how publishers mark up their own pages: "The structured data must appear on the same page as the job description".
  - "Ideally you should remove expired job postings"; use `validThrough`.
  - Third-party job sites must not "modify the job title".
  - No reuse rights are granted.
- decision: NEEDS_REVIEW as a technique. Use JSON-LD parsing only on pages whose owner has approved collection. Mirror Google's freshness rules: drop jobs past `validThrough` and do not alter titles.

### 3.24 Balikpapan open data — registered vacancies by education level
- api_feed_license_url: https://data.balikpapan.go.id/dataset/banyaknya-lowongan-kerja-yang-terdaftar-menurut-tingkat-pendidikan
- Key evidence: Publisher "Dinas Ketenagakerjaan"; License "Other (Public Domain)"; CSV; last updated "Juli 16, 2026, 04:54 (UTC)".
- allowed_fields: all fields of the aggregate dataset (counts by education level).
- rate_policy: manual download; one file.
- attribution: not required by the licence; cite the publisher anyway.
- retention: none stated; keep a snapshot of the licence text.
- regional_coverage: Kota Balikpapan only.
- data_quality_risk: medium. These are registered vacancies only, and a sister dataset showed a failed validation status (per a search snippet).
- decision: APPROVED_WITH_CONDITIONS (manual import; aggregate context only; re-check the licence at each import).
- notes: other regional portals (Blitar, Asahan) appeared in search, but their licences were not verified at the source (Blitar's snippet said "No License Provided").

### 3.25 Satu Data Indonesia (data.go.id)
- The homepage shows "Portal Satu Data Indonesia" (Bappenas). Datasets are labelled "Terbuka"/"Terbatas". No licence or terms statement was found on the homepage, and no API link.
- decision: NEEDS_REVIEW per dataset. No national vacancy-level dataset was found in this pass.

### 3.26 BPS
- terms_url: https://www.bps.go.id/assets/term-of-use. **HTTP 403**; https://www.bps.go.id/id/term-of-use and https://aceh.bps.go.id/id/term-of-use also returned 403.
- Search snippets (unverified) describe a free, worldwide, non-exclusive licence covering commercial use, with credit to BPS required.
- decision: NEEDS_REVIEW. Likely usable for labour-force context (not vacancies) once the terms are read directly.

### 3.27 Kaggle Indonesian job datasets
- Examples: https://www.kaggle.com/datasets/canggih/jog-description-and-salary-in-indonesia, https://www.kaggle.com/datasets/azizainunnajib/jobs-crawling, https://www.kaggle.com/datasets/sryasuka/formasi-cpns-indonesia-2024.
- Key evidence: the pages are client-rendered; **no licence text was retrievable**. Titles indicate data crawled from JobStreet and others.
- decision: NEEDS_REVIEW; exclude from the product. An uploader's licence cannot override JobStreet's ban on aggregation. At most, use for offline ML experiments after a licence and provenance check, and never redisplay.

## 4. Recommended connector order

**Activate first (no outreach needed):**

1. **Manual import of licensed aggregate datasets.** Start with the Balikpapan public-domain dataset, and use the same workflow for other regional CKAN portals whose dataset page states an open licence. This is low value for listings but exercises the `manual_import` connector, the licence-snapshot storage and attribution. It gives market context only, not job listings.

**Next (permission is realistically obtainable; build the connector behind a disabled flag):**

2. **ATS APIs per consenting employer (Lever, Greenhouse, Ashby; then SmartRecruiters with an employer-issued key).** The APIs are documented, stable, JSON, and return only vacancy data.
   - Steps:
     - (a) Identify Indonesian employers from their own careers page links. None were confirmed in this pass; xendit.co/careers returned HTTP 403.
     - (b) Send each employer a short written request covering purpose, fields, display (title, location, link-back, and the description only if allowed), refresh rate, and a removal contact.
     - (c) Record the consent with date and scope in the source registry.
     - (d) Set APPROVED_WITH_CONDITIONS for that employer's board token only.
   - Without step (c), these stay disabled. Lever's "may be scraped by third parties" and Greenhouse's "publicly available" are not licences.
3. **Pasker ID / Karirhub data-sharing request** to Pusat Pasar Kerja (Kemnaker), plus written confirmation of reuse terms for the Pasker ID aggregate datasets. This is the highest-value source for national, blue-collar and regional coverage, and the only sanctioned route, because the user terms ban crawlers.
4. **Partnership requests to boards whose terms contemplate written permission:** Kalibrr, Pintarnya, Karir.com, Dealls. Ask for a feed or API and display rights. Also send a clarification request to Loker.id and HiredToday, whose terms are unread.

**Keep disabled (BLOCKED):** JobStreet, LinkedIn, Indeed, KitaLulus, Glints, Karir.com, and Pasker ID HTML. Any of them changes only if the operator provides a written licence or API agreement covering collection, storage and display.

**Unresolved before any decision:** TopKarir (possibly offline), Tech in Asia (not fetchable), SSCASN (no terms found), BPS and data.go.id (licence text not read).

## 5. Could not verify

- Glints terms (HTTP 403 on all regional terms URLs; again on 2026-10-18). The BLOCKED status relies on SRS §4.1 evidence.
- Loker.id terms (HTTP 403).
- HiredToday terms and privacy (client-rendered; again on 2026-10-18).
- TopKarir (connection refused; again on 2026-10-18).
- Tech in Asia (fetch tool blocked for the domain).
- ~~BPS terms of use (HTTP 403).~~ Read on 2026-10-18; see §7.
- Kaggle dataset licences (client-rendered).
- The last ~70k characters of the Indeed legal page.
- SmartRecruiters "SAP API Policy" text.
- Whether Workday site terms cover tenant career sites.
- Any Indonesian employer confirmed to use Greenhouse, Lever, Ashby or SmartRecruiters (none confirmed from a non-listing page).

## 6. Addendum (2026-10-17, later the same day): bulk sources for the data lake

This addendum covers sources researched for volume, after every listing source above
came back blocked or permission-only. Feasibility and volumes: docs/SOURCE_ACQUISITION.md.

### 6.1 Common Crawl (archive)
- terms_url: https://commoncrawl.org/terms-of-use. The terms grant a licence to use the
  archive and state that the crawled content remains subject to the rights and terms of
  each site owner.
- Access: public columnar index (Parquet) and WARC files over HTTPS; HTTP range requests
  for single records are the documented access pattern. CloudFront rate limiting applies:
  our 8 requests/s run received HTTP 403 within minutes (docs/LAKE.md, incident log).
- decision: **APPROVED_WITH_CONDITIONS** for aggregate analytics, registry id
  `commoncrawl-jobposting`. Conditions: exclude every site rated BLOCKED,
  REQUIRES_WRITTEN_PERMISSION or NEEDS_REVIEW above, plus large commercial portals whose
  terms were not reviewed (`backend/talentscope/lake/domains.py`); keep JobPosting fields
  only; never display archived descriptions; link to and attribute the original page;
  no claim that a vacancy is open; ≤2 requests/s, stop on 403/429.
- **Superseded on 2026-10-18:** the per-site review described below as missing has since
  been done and is enforced as a default-deny allow-list
  (`backend/talentscope/lake/domain_reviews.py`, docs/data-engineering/DOMAIN_REVIEW.md).
  22 sites contribute; 21 have terms silent on reuse and 1 permits copying with a backlink;
  none grants republication explicitly. The paragraph below is kept as the 2026-10-17 record.
- **Residual risk, stated plainly (2026-10-17):** this departs from §3.23's rule ("parse JSON-LD only
  on pages whose owner has approved collection"). The remaining sites are mostly small
  regional vacancy blogs whose terms were *not* reviewed one by one. We rely on the
  archive's licence, on the sites having published JobPosting markup expressly for
  machine consumption by search engines, and on aggregate-only use. Before showing
  individual archived listings on a public deployment, review the top sites' terms (the
  top 10 supply most records; see DATA_INVENTORY.md) or limit the public site to aggregates.

### 6.2 Web Data Commons, schema.org JobPosting subset
- URL: https://webdatacommons.org/structureddata/ (pre-extracted from Common Crawl).
- Status: **blocked by availability**. The download server refused connections or timed
  out on every attempt on 2026-10-17, and refused connections again on 2026-10-18. Same content rights as 6.1 once reachable; it would
  add Indonesian vacancies on non-`.id` domains.

### 6.3 Licensed job-data providers (not contacted; no data obtained)
| Provider | What is offered (vendor statements, unverified) | Path |
|---|---|---|
| Techmap (jobdatafeeds) | Per-country daily JSON files incl. Indonesia, via AWS Data Exchange | Purchase |
| Lightcast | Indonesian job postings since Aug 2020, normalized skills | Enterprise contract |
| TheirStack | Job postings API across 195 countries | Subscription |
| Coresignal, LinkUp | Global job datasets; Indonesian coverage not confirmed | Contract |

Any of these enters through `talentscope lake import-jsonl` after its licence is recorded
on a registry entry. Redistribution terms must be checked before display.

### 6.4 Publisher APIs (Careerjet, Jooble, Adzuna)
- These APIs serve search results for live display to a publisher's visitors, with
  click tracking. They are not bulk-data licences. **Not suitable** for building a stored
  dataset; Indonesian coverage was not confirmed.

## 7. Addendum (2026-10-18): refresh of unresolved items and the ingested datasets

Read-only fetches of policy/API-doc pages only (details and quotes:
docs/data-engineering/SOURCE_ASSESSMENT.md §5).

- **Glints:** terms still HTTP 403 (`/id/about/terms`, `/id/en/about/terms`). Unchanged: BLOCKED.
- **Pintarnya:** terms re-read; §3.10 confirmed (H.2 "tanpa izin tertulis dari Pintarnya";
  no scraping clause). Unchanged: REQUIRES_WRITTEN_PERMISSION.
- **TopKarir:** connection refused again. **HiredToday:** terms still client-rendered.
- **Indeed:** docs.indeed.com root and partners.indeed.com returned HTTP 403; the Job Sync
  API page is for ATS partners and does not mention a publisher/search API. The reported
  retirement of the publisher API is still not confirmed by Indeed. Unchanged: BLOCKED (s.21).
- **Web Data Commons:** connection refused again.
- **BPS:** https://www.bps.go.id/id/term-of-use is now readable. §13 grants a free,
  worldwide, non-exclusive licence for "kepentingan komersial maupun nonkomersial", on
  condition of "memberikan kutipan atau kredit kepada BPS" (title, access date, direct
  link). The registry entry `bps-statistics` (NEEDS_REVIEW, from §3.26) should be re-reviewed
  by the registry owner; this document does not change the registry.
- **Glints snapshot (`glints-snapshot-2026-06`):** not a researched source but an existing
  file. It was produced by the academic project's Selenium scraper of glints.com
  (`legacy/academic_pipeline/scrapers/glints_scraper.py`), which is the kind of collection
  §3.1 records as prohibited without written consent. It is used at the project owner's
  instruction; no permission from Glints exists. See DATA_POLICY.md "Public labels".
