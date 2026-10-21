# TalentScope — Software Requirements Specification (SRS)

> **Document version:** 2.0  
> **Status:** Engineering baseline requiring repository audit, deep source research, and architecture decision records before implementation  
> **Document language:** English  
> **Primary product language:** Bahasa Indonesia (`id-ID`)  
> **Product:** Indonesian Job Market Intelligence and Career Intelligence platform  
> **Primary objective:** Build a credible, end-to-end, multi-source job discovery and labor-market analytics product, not merely a dashboard  
> **Monetization:** Out of scope for the initial release  
> **Research snapshot in this document:** 17 October 2026; all source policies and technical facts must be re-verified before implementation

---

## 0. Mandatory Instructions for Claude Code and Engineering Agents

This document is the target product and engineering specification. It is not evidence that a capability already exists. Before changing code, agents MUST inspect the actual repository, investigate the source landscape, verify source-specific access rules, and propose an evidence-based architecture and implementation plan.

### 0.1 Required working sequence

The work MUST proceed in these stages:

1. **Stage A — Read-only repository audit.** Inspect the current repository, Git state, existing data, source code, dependencies, tests, outputs, and execution path. Preserve all existing work.
2. **Stage B — Deep research on Indonesian job sources.** Research a broad list of job portals, public employment services, official company career pages, public ATS/job feeds, university or internship boards, and other relevant sources. Verify technical accessibility and the current terms/policies for each source individually.
3. **Stage C — Source feasibility and legal/policy matrix.** Classify each candidate source as `APPROVED`, `APPROVED_WITH_CONDITIONS`, `REQUIRES_WRITTEN_PERMISSION`, `BLOCKED`, or `NEEDS_REVIEW`. Public visibility or a free-to-view listing MUST NOT automatically mean crawling, storing, aggregating, or redisplaying is allowed.
4. **Stage D — Architecture and stack decision.** Compare feasible architectures and technologies against actual repository findings, source access constraints, expected workload, maintainability, portability, and operational complexity. Write Architecture Decision Records (ADRs) before choosing significant components.
5. **Stage E — Implementation plan.** Produce a phased roadmap with dependencies, risks, acceptance criteria, test plans, and verifiable milestones.
6. **Stage F — Engineering.** Only begin after the audit and proposed plan have been reviewed/approved by the project owner. Implement in small, testable slices.
7. **Stage G — Verification and release.** Run tests, validate source connectors, assess data quality, verify the actual running product, document limitations, and prepare the portfolio release.

Do not skip Stage B or make up a list of “supported” sources based only on search result snippets. Use up-to-date web research where available. If network research is unavailable, document the limitation and create a clear research task list; do not claim source policies have been verified.

### 0.2 Non-negotiable safety and preservation rules

During the initial audit and research phases:

- Do NOT edit, delete, move, rename, overwrite, or generate files inside the existing project.
- Do NOT install or upgrade dependencies.
- Do NOT run scraping against external sources during the research/audit stage.
- Do NOT change Git branches, commits, history, or configuration.
- Do NOT run commands that may overwrite datasets or generated artifacts.
- Inspect `git status` first and preserve uncommitted changes.
- Do NOT expose API keys, cookies, passwords, tokens, private URLs, or other secrets in terminal output or reports.
- Do NOT claim a test, connector, endpoint, or integration works unless it was actually verified.
- Do NOT claim complete national coverage. The product may pursue broad coverage, but the open web is incomplete, dynamic, fragmented, and subject to changing access rules.
- Do NOT treat this SRS as legal advice. Escalate uncertain source rights or re-publication rights for review before activating a connector.

### 0.3 Source access and scraping rules

TalentScope aims to gather the broadest useful coverage of job opportunities in Indonesia from sources that are genuinely accessible **and permitted for the intended collection and display purpose**. This is not authorization to scrape every website.

The system MUST distinguish:

1. A page that can be viewed without payment or login.
2. A page that permits automated retrieval.
3. A page whose content may be stored or transformed.
4. A page whose content may be redistributed or displayed in an aggregator.
5. A source that provides an API, feed, dataset license, or written permission.

These are different questions and must be checked separately.

The system MUST NOT:

- Bypass authentication, paywalls, access controls, CAPTCHAs, anti-bot challenges, IP blocks, request quotas, or other technical restrictions.
- Use stealth browsers, residential proxy rotation, forged identities, stolen cookies, or account automation to evade source protections.
- Scrape candidate/resume/profile data, personal contact details, recruiter private data, or other non-vacancy personal information.
- Crawl sources whose current terms expressly prohibit the proposed activity unless written permission or an applicable authorized API/license is obtained.
- Continue after a clear denial of permission, cease-and-desist request, or repeated blocking signal.
- Infer that `robots.txt` grants permission. It does not; it is only one input in the access review.

The crawler MUST respect applicable terms, documented API rules, `robots.txt` directives, rate limits, and source-specific instructions. It MUST identify itself appropriately, send modest request volumes, implement backoff, and stop safely on denial signals. All source eligibility decisions must be recorded with evidence and a review date.

### 0.4 Principles for all implementation work

- Build one coherent product using a modular architecture; do not create disconnected demos.
- Preserve useful legacy functionality after verifying it.
- Do not use Streamlit as the primary product frontend.
- Use Bahasa Indonesia for user-facing copy, dates, location labels, and currency formatting. Established technical terms may remain in English when clearer.
- Do not prioritize pricing, subscriptions, sales funnels, enterprise tiers, or monetization in the initial release.
- Do not show mock data as current, live, verified, or representative of all Indonesia.
- Do not fabricate users, customers, employers, jobs, source counts, accuracy claims, growth metrics, salary percentiles, or verification badges.
- Expensive batch analytics MUST NOT run on every end-user page request.
- Do not add Kafka, Kubernetes, a search cluster, multiple microservices, Redis, or heavy orchestration solely to make the stack look impressive. Recommend each only if research and workload justify it.
- Do not make an architecture decision before the deep research and repository audit.

---

# 1. Introduction

## 1.1 Purpose

This SRS defines product, data acquisition, source governance, data engineering, analytics, application, security, reliability, testing, deployment, and documentation requirements for TalentScope.

TalentScope is intended to become a multi-source Indonesian job discovery and labor-market intelligence platform. It will consolidate job opportunity metadata from a diverse set of legally and technically eligible sources, normalize it, deduplicate cross-source listings, provide transparent job discovery, and generate useful market and career insights.

This document is the baseline for:

- Repository audit and gap analysis.
- Deep research into Indonesian job data sources and their usage rules.
- Architecture and technology-stack decisions.
- Source registry and adapter-based connector design.
- Scraping/ingestion and data processing.
- Data modeling, API design, frontend implementation, and UX.
- Search, analytics, skill intelligence, salary intelligence, and career matching.
- Security, privacy, source governance, and responsible data use.
- Test strategy, deployment, observability, and reproducible portfolio delivery.

It does not claim the target capabilities already exist. Current status must be confirmed from repository evidence and tests.

## 1.2 Product vision

**TalentScope helps people in Indonesia discover job opportunities and understand the labor market through transparent, multi-source data.**

The platform should answer practical questions such as:

- What job opportunities are currently visible from the sources TalentScope is allowed to use?
- Which sources contribute listings for a particular region or occupation?
- Which occupations appear frequently in the collected sample?
- Which skills appear in job descriptions for a selected occupation?
- How do the requirements for two occupations compare?
- What salary information is explicitly disclosed in the observed listings?
- Which listings match a user's selected skills and preferences?
- How fresh is the dataset, how was it collected, and what does it not represent?

## 1.3 Product positioning

TalentScope is a public-interest-oriented portfolio product for job discovery and market intelligence, initially focused on Indonesia. It is not a recruitment agency, a guarantee of job availability, a hiring decision system, or an authoritative census of the Indonesian labor market.

The product should prioritize utility, breadth of eligible sources, transparent data provenance, data quality, and engineering quality over commercial conversion.

## 1.4 Definitions

| Term | Definition |
|---|---|
| Source | A website, official API, feed, dataset, employer career portal, public employment service, or other origin from which job information may be acquired. |
| Source adapter / connector | A module implementing source-specific discovery, retrieval, parsing, normalization, and error behavior. |
| Crawl | Automated retrieval of source pages or documents. |
| Ingestion | Importing data through an API, feed, file, connector, or permitted crawl. |
| Source record | A job record as represented by one source before cross-source reconciliation. |
| Canonical job | TalentScope's normalized internal representation of a job opportunity. |
| Provenance | Evidence showing where a field or record came from and when it was observed. |
| Source eligibility | A documented decision about whether a source can be used for a specified collection, storage, and display purpose. |
| Snapshot | A dated observation of a source record used to monitor changes over time. |
| Cross-source duplicate | Two source records that appear to describe the same underlying vacancy. |
| Current listing | A listing whose status and freshness satisfy a defined policy; not simply a record that still exists in the database. |
| Skill extraction | Identification of skill mentions from job fields or descriptions. A detected phrase is not automatically a verified requirement. |
| Historical data | Dated observations collected over time; required for valid temporal trend analysis. |
| Demonstration data | Clearly labeled illustrative records used only when the real backend data is unavailable. |
| Source policy evidence | A dated record of the terms, robots instructions, API documentation, license, permission, and other materials reviewed for a source. |

---

# 2. Scope and Success Criteria

## 2.1 In scope

The initial engineering scope includes:

1. A multi-source discovery and research process.
2. A source registry with policy and technical eligibility records.
3. A modular ingestion system with independent source adapters.
4. Support for source types such as permitted public pages, official APIs, documented feeds, public datasets, employer career pages, and public-sector employment portals.
5. A canonical job schema and normalization pipeline.
6. Cross-source duplicate detection with explainable matching.
7. Job lifecycle and freshness handling.
8. Search and filtering across the consolidated eligible dataset.
9. Market overview and occupational analytics.
10. Skill extraction and skill-demand analysis, with measurement of extraction quality.
11. Salary normalization and distribution analytics when data supports them.
12. Career matching with explainable results, after an appropriate baseline is available.
13. A Bahasa Indonesia frontend.
14. Fast, documented backend APIs.
15. Internal data-source, pipeline, and data-quality views restricted to authorized administrators.
16. Tests, observability, security controls, deployment, and technical documentation.
17. Retention and deletion policies that respect source restrictions and reduce unnecessary storage.
18. A documented process for enabling, pausing, reviewing, and disabling sources.

## 2.2 Out of scope for the initial release

- Paid subscription plans, billing, enterprise sales, advertising, and monetization flows.
- Automated applications to jobs on behalf of users.
- Scraping candidate profiles, resumes, recruiter personal information, or private account data.
- Circumventing login requirements, CAPTCHA, access restrictions, or anti-bot defenses.
- Rehosting full third-party job descriptions or copying entire job-board databases without permission.
- Claiming exhaustive coverage of all jobs in Indonesia.
- Hiring probability predictions or claims that the system can guarantee job placement.
- A large microservice architecture or always-on distributed streaming stack without a proven need.
- Real-time claims without validated collection cadence and timestamps.
- Publicly exposing internal source-policy notes, secrets, or administrative controls.

## 2.3 Broad source coverage objective

The product should pursue the broadest practical and permitted coverage of Indonesian job opportunities, covering multiple source categories, industries, employment types, and regions. Coverage is a continuing engineering objective, not a promise that every Indonesian job is captured.

The implementation MUST prefer breadth through many authorized and sustainable connectors rather than aggressive crawling of a few blocked portals.

Coverage should be measured along multiple dimensions:

- Number of eligible active source connectors.
- Source categories represented.
- Geographic coverage across Indonesian provinces and cities, where the source data supports it.
- Occupational/industry coverage.
- Employment-type coverage: full-time, contract, part-time, internship, freelance, temporary, project-based, and other source-defined types.
- Work arrangement: on-site, hybrid, remote, where disclosed.
- Listing freshness and the percentage of records with known last-seen timestamps.
- Available-field completeness.
- Source-specific failure rate.
- Cross-source duplicate rate.

Do not optimize solely for raw record count. A smaller number of reliable, eligible, well-attributed records is preferable to a large, unlawfully copied, stale, or low-quality dataset.

## 2.4 Success criteria

The first stable portfolio release should meet these criteria:

- Repository setup is documented and reproducible.
- The system has a documented source inventory and a source eligibility process.
- Multiple independently implemented source adapters work for sources verified as eligible. The source count is set after research, not invented before it.
- Sources prohibited from automated collection are not activated without documented authorization.
- Each record contains source provenance and collection metadata.
- Listings can be searched and filtered in Bahasa Indonesia.
- Duplicate handling is explainable and does not silently discard potentially distinct vacancies.
- Expired or unobserved listings are not presented as definitely active without evidence.
- Analytics clearly communicate the dataset's source, period, coverage, and limitations.
- Salary figures are calculated only from valid normalized salary records.
- Skill analytics are backed by extracted/normalized fields and include quality caveats.
- APIs have validation, error handling, pagination, and tests.
- Administrative pipeline/source views reflect actual operational data, not decorative mocks.
- The app can be started from documented commands and deployed using a documented repeatable process.
- No critical secrets are committed, and applicable data-source restrictions are documented.

---

# 3. Mandatory Deep Research Before Architecture or Scraping

## 3.1 Research objective

Before selecting final technologies or implementing a scraper, the agent MUST conduct deep research to identify the widest reasonable landscape of job sources in Indonesia and determine which can actually be used for TalentScope's intended purpose.

Research must cover both **where job vacancies exist** and **what acquisition/use methods are permitted**. Technical accessibility and permission are separate dimensions.

Use up-to-date primary sources wherever possible. Prefer the source owner's current terms, API documentation, developer documentation, robots.txt, licensing statement, privacy notice, and written permission over third-party blog posts. Record the date accessed and exact evidence URL.

The output of this phase must include:

1. A source discovery inventory.
2. A per-source permission and access matrix.
3. A per-source technical feasibility assessment.
4. A list of source candidates that are explicitly excluded or blocked.
5. A shortlist of safe, useful sources for the first release.
6. A proposed connector implementation order.
7. An architecture proposal and technology comparison.
8. Architecture Decision Records (ADRs) explaining chosen technologies and rejected alternatives.

## 3.2 Source categories to investigate

The researcher MUST investigate a wide range of categories, not stop after two commercial portals.

### A. Government and public employment services

Investigate current publicly available vacancy listings and official feeds from relevant Indonesian public employment services, including but not limited to:

- Pasker ID / Karirhub under the Ministry of Manpower (Kementerian Ketenagakerjaan).
- Public job or labor-market information pages published by relevant government agencies.
- Publicly accessible recruitment announcements from government agencies when appropriate to the product scope.
- Official public-sector employment pages that expose public vacancy data without requiring prohibited access.

Treat civil-service recruitment and general labor-market vacancies as different categories. Verify whether each portal's data is current, public, and permitted for the intended use. A government domain does not automatically imply a reusable dataset or API.

### B. General job boards and aggregators

Investigate, but do not automatically activate, sources such as:

- JobStreet / SEEK / JobsDB ecosystem.
- Glints Indonesia.
- LinkedIn Jobs.
- Indeed Indonesia or Indonesia-relevant listings.
- Kalibrr.
- Dealls.
- KitaLulus.
- Karir.com.
- Loker.id.
- Pintarnya.
- TopKarir.
- HiredToday and other active Indonesia-focused job boards.
- Tech in Asia Jobs, where relevant.
- Other active sources discovered through research.

These are **research candidates**, not pre-approved scraping targets. Current terms may restrict automated collection, aggregation, reproduction, or re-publication. Some may be available only through accounts or may not offer a permitted public data interface.

### C. Direct employer career pages

Investigate official careers pages of Indonesian employers across a broad range of sectors, for example:

- Technology and digital services.
- Banking, financial services, and insurance.
- Manufacturing and industrial operations.
- Retail and consumer goods.
- Logistics and transportation.
- Energy and natural resources.
- Healthcare and pharmaceuticals.
- Telecommunications.
- Education.
- Hospitality and tourism.
- Professional services.
- Agriculture and food.
- Government-linked companies and state-owned enterprises.
- Nonprofits and development organizations.

Do not hard-code a handful of major companies as the entire source universe. Maintain a source discovery workflow that can add newly discovered eligible employer pages without changes to core ingestion logic.

Check whether the employer's recruitment site is hosted on a vendor/ATS platform. Possible ATS categories include public job-board pages or APIs from platforms such as Greenhouse, Lever, Workday, SmartRecruiters, Ashby, and other providers. Do not presume that a public ATS page or an endpoint visible in browser developer tools grants authorization. Verify provider and employer terms, allowed API use, and data-display restrictions.

### D. Internship, entry-level, and campus career sources

Investigate sources focused on:

- Internships and apprenticeships.
- Fresh-graduate openings.
- Graduate development programs and management trainee positions.
- University career centers.
- Campus hiring and career-fair announcements.
- Vocational and training-to-employment opportunities.

Collect only publicly available vacancy information for which the acquisition and display are permitted. Do not collect student or applicant profiles.

### E. Sector-specific, professional, and niche boards

Investigate sources for roles or sectors that may be underrepresented in general portals, including creative work, healthcare, education, maritime work, hospitality, remote work, non-profit work, technical trades, and freelance/project-based work. Evaluate each source's quality and eligibility individually.

### F. Official feeds, structured data, open datasets, and syndication

Search for:

- Official APIs and developer programs.
- Public RSS/Atom feeds.
- Public XML sitemaps or job sitemaps where use is permitted.
- Public JSON feeds or documented job-board endpoints.
- Open datasets with explicit licenses.
- Employer-provided feeds or written syndication agreements.
- Public structured JobPosting data on individual employer pages, where its retrieval and use are permitted.

Structured data is a parsing opportunity, not a permission bypass. A feed or sitemap must be evaluated under the source's terms and license.

### G. New-source discovery process

Design a repeatable process for finding and evaluating additional sources. It should support manual curation initially and future assisted discovery of likely employer career pages. A candidate source MUST NOT automatically become crawlable merely because it is discovered.

For every candidate, record how it was found, the source's canonical domain, source category, relevant regions and job families, and the next required research step.

## 3.3 Per-source research checklist

For every candidate, investigate the following and provide evidence:

1. Canonical website/domain and country/region scope.
2. Source category and types of jobs offered.
3. Whether vacancy listings are viewable without login or payment.
4. Whether official API/feed/dataset options exist.
5. Current terms of service / acceptable-use policy.
6. Current `robots.txt` and relevant disallow/allow instructions.
7. Privacy policy and relevant personal-data implications.
8. Copyright, database, or redistribution restrictions where stated.
9. Rate limits, API quotas, attribution requirements, and expiration rules.
10. Whether search result pages, detail pages, descriptions, or structured data may be fetched.
11. Whether automated extraction is expressly prohibited or requires written consent.
12. Whether local law or other legal questions require further review.
13. Technical access style: API, feed, static HTML, structured JSON-LD, dynamic public HTML, downloadable file, or manual import.
14. Stability of field layout and expected maintenance effort.
15. Availability of stable job identifiers and publication/expiry dates.
16. Geographic and occupational coverage in Indonesia.
17. Expected duplicate overlap with existing sources.
18. Data display/storage rights and any restrictions on retaining full descriptions.
19. Contact or permission path if use is not clearly allowed.
20. Recommended decision and evidence supporting it.

Do not infer legal permission merely from the absence of a prohibition. If policy language is unclear, mark `NEEDS_REVIEW` or `REQUIRES_WRITTEN_PERMISSION` and do not activate the scraper.

## 3.4 Source eligibility states

Use these controlled states:

- `DISCOVERED`: candidate found; not yet researched.
- `NEEDS_REVIEW`: technical or policy situation is unclear.
- `APPROVED`: reviewed evidence supports the specified acquisition, storage, and display use.
- `APPROVED_WITH_CONDITIONS`: approved only with explicit limits such as rate, fields, attribution, retention, or API quota.
- `REQUIRES_WRITTEN_PERMISSION`: do not crawl/store/display until permission is obtained and recorded.
- `BLOCKED`: current terms/access restrictions prohibit the proposed method, permission was denied, or technical controls prohibit continuation.
- `PAUSED`: formerly usable but disabled due to policy change, repeated failures, source request, or quality problem.
- `RETIRED`: source connector no longer maintained or source is no longer relevant.

`APPROVED` is not permanent. Re-review periodically and whenever terms, robots rules, endpoints, or source behavior change materially.

## 3.5 Required research deliverables

Create a research report with a table at minimum:

| Field | Description |
|---|---|
| `source_name` | Human-readable source name |
| `canonical_domain` | Primary domain |
| `category` | Government, general board, employer, ATS, internship, niche, feed/dataset, etc. |
| `discovery_evidence_url` | Evidence that the source exists and offers job listings |
| `terms_url` | Current terms/acceptable-use policy |
| `robots_url` | Current robots.txt URL or reason not applicable |
| `api_feed_license_url` | Documentation/license if present |
| `accessed_at` | UTC timestamp of the review |
| `login_required` | Yes / no / partial / unknown |
| `technical_method` | API, feed, HTML, structured data, dataset, manual, etc. |
| `permission_status` | Controlled state from section 3.4 |
| `allowed_fields` | Fields allowed to collect/store/display, with evidence |
| `rate_policy` | Source-specific limits and safe request guidance |
| `attribution_requirements` | Required source attribution |
| `retention_constraints` | Limits on retention/cache/snapshot storage |
| `regional_coverage` | What Indonesia coverage is evidenced |
| `data_quality_risk` | High / medium / low with explanation |
| `decision` | Include, investigate, ask permission, or exclude |
| `notes` | Explicit caveats and unresolved questions |

The research report MUST include primary-source links and a brief reason for each eligibility decision. Do not claim that all candidate sites are permitted or that every site is technically reachable.

---

# 4. Preliminary Source Research Findings and Evidence

This section is a research starting point, not a final allowlist. The agent MUST re-open the current source policies and verify all decisions at implementation time.

## 4.1 Confirmed policy cautions from initial research

### Glints

Glints' published terms include a restriction against using screen scraping, data mining, robots, or similar data extraction tools to establish, maintain, advance, or reproduce information from its site without prior written consent. Therefore, **do not activate automated Glints scraping without verified written consent or another expressly authorized mechanism**.

Evidence: <https://glints.com/id/about/terms>

### JobStreet / SEEK / JobsDB

The JobStreet terms effective 20 July 2026 prohibit unauthorized aggregation, copying, reproduction, and automated data-gathering tools such as robots or screen scraping, except where permission is provided. Therefore, **do not treat public visibility as permission to scrape or republish JobStreet/SEEK/JobsDB data**. Investigate any official authorized interfaces or written permission instead.

Evidence: <https://id.jobstreet.com/id/terms>

### LinkedIn

LinkedIn's User Agreement and help documentation prohibit unauthorized scraping, crawling, bots, and automation used to copy its services and content. Therefore, **LinkedIn must remain blocked for direct scraping unless a specific, applicable written authorization or permitted official interface expressly supports the intended use**. Do not bypass login, rate limits, or anti-bot controls.

Evidence: <https://www.linkedin.com/legal/user-agreement>  
Evidence: <https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software>

### Pasker ID / Karirhub

Pasker ID and Karirhub are official Indonesian public employment-service candidates with publicly visible vacancy information. Their existence makes them important research targets. However, public visibility alone does not establish permission for automated bulk collection, retention, or re-publication. Verify current terms, privacy notices, robots directives, official interfaces, and any relevant limitations before activating a connector.

Evidence: <https://paskerid.kemnaker.go.id/>  
Evidence: <https://karirhub.kemnaker.go.id/>

### Dealls

Dealls publishes publicly viewable vacancy pages and search results. It is a relevant candidate to investigate, but the engineering agent must verify the current terms, robots rules, permitted methods, and reuse/display conditions before scraping or storing its listings.

Evidence: <https://dealls.com/loker>

### KitaLulus

KitaLulus provides a website and app for job search. It is a candidate for source research, but current policy and technical permissions for automated collection and aggregation must be verified independently.

Evidence: <https://id.kitalulus.com/help-qa/bagaimana-cara-saya-mendapatkan-pekerjaan-di-kitalulus>

### Robots Exclusion Protocol

The IETF Robots Exclusion Protocol specifies how site owners can communicate crawler rules. Its rules are not a substitute for access authorization or legal permission. TalentScope must evaluate robots instructions together with terms, API conditions, and the intended usage.

Evidence: <https://www.rfc-editor.org/rfc/rfc9309.html>  
Google's explanatory documentation: <https://developers.google.com/search/docs/crawling-indexing/robots/intro>

### Indonesian Personal Data Protection Law

Indonesia's Law No. 27 of 2022 concerns Personal Data Protection. The agent must examine its applicability to user accounts, operational logs, and any collected data, and should minimize collection of personal information. Vacancy collection must not expand into collecting candidate profiles or applicant information.

Official reference: <https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/>

## 4.2 Candidate-source list for further research

At a minimum, investigate the following source families. The list is deliberately broader than two portals and is not an authorization list.

1. Pasker ID / Karirhub and relevant public employment-service pages.
2. Direct employer career pages across multiple sectors and regions.
3. Employer-hosted public job feeds or APIs where documented and permitted.
4. Public job boards from Greenhouse, Lever, Workday, SmartRecruiters, Ashby, or other ATS providers, only where provider/employer terms allow intended access and use.
5. Dealls.
6. KitaLulus.
7. Kalibrr.
8. Karir.com.
9. Loker.id.
10. Pintarnya.
11. TopKarir.
12. HiredToday and other active Indonesian job boards discovered through research.
13. Tech in Asia Jobs, subject to policy and permission review.
14. JobStreet / SEEK / JobsDB, as a research candidate only; no direct scraper without authorization.
15. Glints, as a research candidate only; no direct scraper without prior written consent or other verified authorization.
16. LinkedIn Jobs, as a research candidate only; no direct scraping absent an applicable authorization.
17. Indeed and other international platforms that show Indonesia vacancies, subject to their current policies.
18. Internship, graduate program, campus career center, and vocational career sources.
19. Public recruitment pages from government-linked entities and state-owned companies.
20. Public sector and civil service vacancy announcements, where distinct from private employment listings.
21. Sector-specific sources for healthcare, education, creative industries, hospitality, logistics, manufacturing, energy, and nonprofit work.
22. Licensed/open datasets or employer-authorized vacancy feeds discovered during research.

For each source, the agent must investigate current existence and relevance. If a domain is inactive, redirects to another product, or provides no appropriate Indonesian vacancies, record that result instead of implementing a dead connector.

---

# 5. Target User Groups and Core User Journeys

## 5.1 User groups

### U-01: Anonymous visitor

Can browse publicly available TalentScope pages and a permitted subset of current listings/insights without creating an account, subject to product policy.

### U-02: Job seeker

Can search and filter listings, open source-attributed job details, save jobs, create a skills profile if account functionality is implemented, and access explainable career matching.

### U-03: Analyst / researcher

Can explore aggregate statistics, inspect data source coverage, understand methodology, and export only permitted derived data under the product's published rules.

### U-04: Administrator / data operator

Can manage source eligibility, inspect ingestion runs, review data quality, pause connectors, and investigate failures. Must not be able to activate a blocked source without a documented authorization record and explicit privileged action.

## 5.2 Core journeys

1. Visitor opens TalentScope → sees an Indonesian-language product overview → searches a job → sees eligible source-attributed results.
2. User filters by location, job title, employment type, experience, and salary when available → opens a detail view → follows the original source/application link.
3. User opens Market Overview → chooses a filter → sees metrics with data scope and freshness information → navigates to related jobs.
4. User opens Skill Intelligence → selects an occupation → compares detected skills and co-occurrences → opens source examples.
5. User opens Salary Intelligence → chooses role/location → sees valid normalized salary distributions and sample counts, without invented statistics.
6. User creates a skill profile → receives a ranked, explainable list of matching jobs → can inspect matching and not-yet-listed skills.
7. Administrator discovers a source → reviews policy evidence → approves it with restrictions or declines it → configures a connector → runs a controlled test → monitors data quality and pause conditions.
8. Administrator reviews a failed crawl → inspects sanitized logs → identifies cause → retries only when safe and permitted.
9. An eligible listing disappears from its source or reaches a verified expiry date → system updates its lifecycle state without misleading users into thinking the job is definitely still open.

---

# 6. Functional Requirements

Requirement IDs are stable references for implementation and tests. A requirement marked `P0` is necessary for a credible first release, `P1` is a valuable follow-up, and `P2` is optional/future. Priority may be adjusted after research, with the reason recorded.

## 6.1 Repository audit and architecture decision requirements

- **FR-ARCH-001 (P0):** Before implementation, inventory all source directories, entry points, dependency files, environment templates, tests, datasets, generated outputs, and workflows.
- **FR-ARCH-002 (P0):** Trace the actual existing execution path from data ingestion through cleaning, storage, analytics, ML, and visualization.
- **FR-ARCH-003 (P0):** Classify existing features as `CONFIRMED`, `PARTIALLY_VERIFIED`, `INFERRED`, `MISSING`, or `BLOCKED`, with repository evidence.
- **FR-ARCH-004 (P0):** Compare the current code to this SRS and produce a gap report before editing files.
- **FR-ARCH-005 (P0):** Conduct and document deep web research on sources and source policies as defined in section 3.
- **FR-ARCH-006 (P0):** Evaluate the proposed technology stack and produce ADRs for key choices before installing or replacing dependencies.
- **FR-ARCH-007 (P0):** Preserve useful working code and existing local changes. Any rewrite proposal must identify why incremental evolution is insufficient.
- **FR-ARCH-008 (P1):** Document a dependency graph of packages, services, scripts, and data artifacts.

## 6.2 Source registry and permissions

- **FR-SRC-001 (P0):** Maintain a source registry with canonical domain, source category, country/region scope, source owner, discovery evidence, terms URL, robots URL, API/feed/license documentation, last review date, permission state, technical method, supported fields, retention rules, attribution rules, rate limits, and operator notes.
- **FR-SRC-002 (P0):** A source connector MUST be disabled by default until it reaches `APPROVED` or `APPROVED_WITH_CONDITIONS` for its intended method and use.
- **FR-SRC-003 (P0):** A source's technical accessibility MUST NOT automatically be interpreted as permission to crawl or redistribute.
- **FR-SRC-004 (P0):** Store source-policy evidence and the decision rationale with the registry record.
- **FR-SRC-005 (P0):** Support per-source allowed/denied field lists. A connector must not store fields excluded by its permission decision.
- **FR-SRC-006 (P0):** Support per-source request cadence, concurrency, timeouts, quotas, cache policy, and backoff configuration.
- **FR-SRC-007 (P0):** Provide source states `DISCOVERED`, `NEEDS_REVIEW`, `APPROVED`, `APPROVED_WITH_CONDITIONS`, `REQUIRES_WRITTEN_PERMISSION`, `BLOCKED`, `PAUSED`, and `RETIRED`.
- **FR-SRC-008 (P0):** Prevent an operator from activating a `BLOCKED`, `NEEDS_REVIEW`, or `REQUIRES_WRITTEN_PERMISSION` connector through ordinary UI actions.
- **FR-SRC-009 (P0):** Record every source status change, actor, timestamp, and reason in an audit log.
- **FR-SRC-010 (P1):** Schedule policy re-review or generate reminders based on a configurable review interval and policy-change signals.
- **FR-SRC-011 (P1):** Allow source owners to be contacted through a documented permission-request workflow when appropriate; do not send unsolicited or automated legal requests without human approval.
- **FR-SRC-012 (P0):** Support pausing a source immediately and stopping queued jobs for that source.
- **FR-SRC-013 (P0):** The system must recognize explicit source-owner requests to stop, delete, or limit processing and route them to an auditable review/response workflow.

## 6.3 Ingestion and scraping

- **FR-ING-001 (P0):** Provide a common connector interface for eligible APIs, feeds, downloadable licensed datasets, employer career pages, and permitted public-page crawlers.
- **FR-ING-002 (P0):** Source-specific parsing must be implemented in separate adapters. A failure in one adapter must not break all source ingestion.
- **FR-ING-003 (P0):** Prefer acquisition methods in this order when available and authorized: official API → licensed/open feed or dataset → documented RSS/Atom/structured feed → permitted public HTML retrieval → browser automation only where permitted and technically necessary.
- **FR-ING-004 (P0):** Before each crawl run, check source eligibility and effective configuration. A disabled, paused, blocked, or expired-approval source must not be crawled.
- **FR-ING-005 (P0):** Honor robots instructions and all applicable terms/API conditions. Treat robots.txt as a crawler rule, not as a legal grant of permission.
- **FR-ING-006 (P0):** Use a transparent, configurable user-agent identifying TalentScope or the operator and providing a contact/about URL when appropriate.
- **FR-ING-007 (P0):** Default to conservative per-host request rates and concurrency. Initial default may be one concurrent request per host and at least a five-second interval, unless source-specific permission/API documentation requires a stricter limit. Never exceed documented limits.
- **FR-ING-008 (P0):** Support request timeouts, bounded retries, exponential backoff, `Retry-After`, conditional requests (`ETag`/`Last-Modified`) when available, caching where allowed, and graceful cancellation.
- **FR-ING-009 (P0):** Treat HTTP 401/403, repeated 429 responses, CAPTCHA/challenge pages, access-denied pages, cease-and-desist notices, and similar signals as stop/pause signals. Do not evade them.
- **FR-ING-010 (P0):** Do not use proxy rotation or stealth mechanisms to bypass a source's controls. Do not automate login or scrape behind authentication unless specifically authorized and designed under an explicit approved integration.
- **FR-ING-011 (P0):** Normalize connector output into a documented source-record schema before core pipeline processing.
- **FR-ING-012 (P0):** Each source record must include source ID, original URL or permitted locator, retrieval time, stable source key when present, parser/version identifier, and relevant run ID.
- **FR-ING-013 (P0):** Persist ingestion run status, start/end time, pages/records attempted, records parsed, records rejected, errors, rate-limit events, and checkpoint/cursor where permitted.
- **FR-ING-014 (P0):** Support pagination and incremental checkpoints for sources whose interfaces permit them.
- **FR-ING-015 (P0):** Make repeated ingestion idempotent so that retries do not blindly create duplicate records.
- **FR-ING-016 (P0):** Keep raw storage minimal and permission-aware. Do not retain full source pages or entire job descriptions by default when short-lived processing or a subset of fields satisfies the product need and retention rights are unclear.
- **FR-ING-017 (P0):** Do not fetch binary attachments/resumes, images, or unrelated resources unless required, permitted, and explicitly justified.
- **FR-ING-018 (P0):** Support manual import of a permitted CSV/JSON dataset for sources where automated access is not approved, with provenance and license metadata.
- **FR-ING-019 (P1):** Support feed/webhook ingestion if a source offers an authorized and documented mechanism.
- **FR-ING-020 (P0):** A connector must expose health/last-success status without leaking source credentials or sensitive response bodies.
- **FR-ING-021 (P0):** Every connector must have parser tests based on sanitized, legally retained fixtures or synthetic fixtures—not copied content whose retention is prohibited.
- **FR-ING-022 (P1):** Support configurable crawl boundaries and maximum pages/records per run to prevent accidental unbounded crawls.
- **FR-ING-023 (P0):** An ingestion run must be stoppable and must stop scheduling new requests after an authorized pause or stop signal.

## 6.4 Job data normalization and canonicalization

- **FR-DATA-001 (P0):** Define a canonical job schema independent of any one source.
- **FR-DATA-002 (P0):** Preserve original field values where permitted and store normalized values separately when practical.
- **FR-DATA-003 (P0):** Normalize whitespace, encoding, dates, currencies, location representations, employment types, and work arrangements without altering the meaning of source content.
- **FR-DATA-004 (P0):** Use a stable canonical identifier independent of an individual source's database primary key.
- **FR-DATA-005 (P0):** Preserve source-specific IDs and the relationship between the canonical job and its source records.
- **FR-DATA-006 (P0):** Distinguish unknown, not disclosed, not applicable, parsing failure, and actual zero values. Do not coerce missing values to zero.
- **FR-DATA-007 (P0):** Validate that salary lower bounds do not exceed upper bounds, date ranges are plausible, source URLs are valid where applicable, and required identifiers exist.
- **FR-DATA-008 (P0):** Store all timestamps in UTC internally and display dates in the user's chosen locale/time zone; default to Indonesian presentation.
- **FR-DATA-009 (P0):** Standardize employment types without losing the original source label. Suggested normalized values include full-time, part-time, contract, temporary, internship, freelance, apprenticeship, project-based, volunteer, and other/unknown.
- **FR-DATA-010 (P0):** Normalize work arrangement into on-site, hybrid, remote, field-based, or unknown only when evidence supports the classification.
- **FR-DATA-011 (P0):** Normalize locations hierarchically when confidence allows: country, province, city/regency, subdistrict or locality, and source text. Do not geocode exact residential or sensitive locations.
- **FR-DATA-012 (P0):** Preserve currency and pay period with salary values. Convert to a normalized monthly representation only when original period and conversion assumptions are known and documented.
- **FR-DATA-013 (P0):** Do not convert negotiable/undisclosed salaries into invented numeric values.
- **FR-DATA-014 (P0):** Track data-quality flags and transformation version for each canonical record.
- **FR-DATA-015 (P1):** Maintain a versioned occupational taxonomy mapping source job titles into normalized titles/categories while preserving original job titles.
- **FR-DATA-016 (P1):** Maintain location and skill dictionaries with aliases, Indonesian and English variants, and provenance.

## 6.5 Cross-source duplicate detection

- **FR-DUP-001 (P0):** Detect likely duplicates using a layered strategy, starting with stable source identifiers and canonical URLs, then normalized company/title/location/date signals.
- **FR-DUP-002 (P0):** Candidate similarity may use normalized text similarity, dates, company identity, location, and source relationships; do not merge based only on a common job title.
- **FR-DUP-003 (P0):** Store duplicate-match rationale, score/signals, and decision version when a merge is performed.
- **FR-DUP-004 (P0):** Support a conservative uncertain state rather than automatically merging ambiguous records.
- **FR-DUP-005 (P0):** When the same vacancy is present on multiple permitted sources, retain source attribution for each source record and provide links to original sources when allowed.
- **FR-DUP-006 (P0):** Avoid counting a known cross-source duplicate multiple times in aggregate canonical-job metrics. Offer source-record counts separately when useful.
- **FR-DUP-007 (P1):** Provide an administrative review workflow for false-positive/false-negative duplicate cases.
- **FR-DUP-008 (P0):** Test deduplication for repeated ingestion, reposted jobs, similar roles at one employer, different locations for the same role, and job updates.

## 6.6 Job lifecycle and freshness

- **FR-LIFE-001 (P0):** Maintain lifecycle states such as `OBSERVED`, `POTENTIALLY_ACTIVE`, `EXPIRED_BY_SOURCE`, `NOT_SEEN_RECENTLY`, `REMOVED_BY_SOURCE`, `SOURCE_UNAVAILABLE`, and `REVIEW_REQUIRED` where supported.
- **FR-LIFE-002 (P0):** Do not mark a listing active solely because it exists in the local database.
- **FR-LIFE-003 (P0):** Use an explicit freshness policy based on source-reported publication/expiry dates, repeated observations, source behavior, and source-specific rules.
- **FR-LIFE-004 (P0):** Distinguish `published_at`, `first_seen_at`, `last_seen_at`, `source_updated_at`, and `expires_at` when information is available.
- **FR-LIFE-005 (P0):** Show the last-observed or last-updated time when relevant and available.
- **FR-LIFE-006 (P0):** Mark stale records clearly rather than asserting they are open.
- **FR-LIFE-007 (P1):** Detect likely removed/expired listings through authorized rechecks or source feeds, within source-specific quotas.

## 6.7 Job search and discovery

- **FR-JOB-001 (P0):** Users can search eligible consolidated listings by title, keyword, company, location, and relevant indexed fields.
- **FR-JOB-002 (P0):** Search must support Bahasa Indonesia and common English job terminology.
- **FR-JOB-003 (P0):** Filters must include supported dimensions only: location, normalized occupation, employment type, work arrangement, experience level, education, salary range, detected skills, date/freshness, and source.
- **FR-JOB-004 (P0):** Sorting may include relevance, newest published/observed, salary when valid, and company/title. A sort option must not be shown if required fields are unavailable.
- **FR-JOB-005 (P0):** Results must use pagination or another bounded result-window strategy.
- **FR-JOB-006 (P0):** Search responses must report total/approximate result count as defined and must not confuse source records with canonical jobs.
- **FR-JOB-007 (P0):** Job cards must show only known fields, indicate missing salary clearly, identify the source, and link to the original listing where permitted.
- **FR-JOB-008 (P0):** Job detail pages must show source attribution, last observed date, and a clear original-source/application action when a valid URL exists.
- **FR-JOB-009 (P0):** The product must not claim that TalentScope itself accepts applications unless a separate authorized application feature is built.
- **FR-JOB-010 (P1):** Support related-job suggestions using transparent similarity criteria.
- **FR-JOB-011 (P1):** Support saved searches for authenticated users.
- **FR-JOB-012 (P0):** The UI must support empty, loading, validation, source-unavailable, stale-listing, and API-failure states.

## 6.8 Market intelligence

- **FR-MKT-001 (P0):** Provide a market overview containing counts of eligible canonical listings, represented companies when identifiable, locations, and source coverage with explicit metric definitions.
- **FR-MKT-002 (P0):** Provide distributions by location, occupation, employment type, and work arrangement where data supports them.
- **FR-MKT-003 (P0):** Provide company and job-title rankings from the observed eligible dataset.
- **FR-MKT-004 (P0):** Analytics filters must be consistent with job search filters when the dimensions overlap.
- **FR-MKT-005 (P0):** Every analytical page must disclose the dataset scope, relevant time period, and source coverage/limitations.
- **FR-MKT-006 (P0):** Do not claim that the collected sample represents the whole Indonesian labor market.
- **FR-MKT-007 (P0):** Do not display time-series trends without valid dated observations across multiple time points.
- **FR-MKT-008 (P1):** Allow comparison across regions, occupations, sources, and supported employment types.
- **FR-MKT-009 (P1):** Allow export of derived analytical tables only where source licenses and applicable policy permit it; exports must contain provenance and limitations.
- **FR-MKT-010 (P0):** Any comparison involving different source coverage must disclose that sources may cover different subsets of the market.

## 6.9 Skill intelligence

- **FR-SKL-001 (P0):** Build a skill taxonomy and extraction approach based on actual job fields and descriptions available from eligible sources.
- **FR-SKL-002 (P0):** Preserve skill mentions and normalized skill entities separately, with confidence/provenance where feasible.
- **FR-SKL-003 (P0):** Report the number of eligible listings used as the denominator for each frequency or percentage.
- **FR-SKL-004 (P0):** Users can inspect commonly detected skills by normalized occupation and location when sample sizes support it.
- **FR-SKL-005 (P1):** Support skill co-occurrence analysis with a documented definition and minimum-support rule.
- **FR-SKL-006 (P1):** Support comparisons between occupations using a matrix/heatmap or equivalent accessible visualization.
- **FR-SKL-007 (P0):** Distinguish a phrase found by a rule-based extractor from a manually or otherwise verified skill requirement.
- **FR-SKL-008 (P0):** Evaluate extraction quality on a manually reviewed sample. Report precision/recall or another fit-for-purpose metric only if measured.
- **FR-SKL-009 (P0):** Do not claim comprehensive skill coverage until the extraction process and taxonomy have been evaluated.
- **FR-SKL-010 (P1):** Support aliases and multilingual variants, e.g. common English skill names embedded in Indonesian job descriptions.
- **FR-SKL-011 (P0):** A job's full description may be processed only within its source-specific permitted use and retention rules.

## 6.10 Salary intelligence

- **FR-SAL-001 (P0):** Store salary minimum/maximum, currency, pay period, original text where permitted, normalized value, and normalization confidence separately.
- **FR-SAL-002 (P0):** Distinguish numeric disclosed salary, negotiable salary, undisclosed salary, invalid salary, and unparseable salary.
- **FR-SAL-003 (P0):** Only use records with valid compatible amounts and pay periods for a given calculation.
- **FR-SAL-004 (P0):** Display sample size and missing salary coverage alongside salary analysis.
- **FR-SAL-005 (P0):** Use median/percentiles only after calculating them from eligible normalized records; clearly identify the sample and period.
- **FR-SAL-006 (P0):** Do not label mean reported minimum/maximum as median salary or market salary.
- **FR-SAL-007 (P1):** Compare salary data by role/location/experience only when sample size and field consistency are adequate.
- **FR-SAL-008 (P0):** Treat outliers transparently; document inclusion/exclusion rules and do not silently remove plausible salaries.
- **FR-SAL-009 (P0):** Display salary in Indonesian Rupiah for relevant Indonesian listings and show the reported period.
- **FR-SAL-010 (P0):** Do not derive or fabricate salary values from title, seniority, or third-party estimates without clear labeling and a separately justified model.

## 6.11 Career matching and recommendations

- **FR-MATCH-001 (P1):** Allow a user to store or temporarily enter skills, target occupations, preferred locations, work arrangements, employment types, experience, and optional salary preferences.
- **FR-MATCH-002 (P1):** Provide a transparent baseline recommender based on explicit filters and skill/title similarity.
- **FR-MATCH-003 (P1):** Show why each result matches, which selected skills overlap, which terms are absent from the profile, and what data was available.
- **FR-MATCH-004 (P0):** Do not present a match score as the probability of being hired or the probability of application success.
- **FR-MATCH-005 (P1):** Evaluate recommendation relevance on a reviewed test set or documented human assessment before describing the feature as accurate.
- **FR-MATCH-006 (P1):** Compare baseline methods before adopting embeddings or heavier models.
- **FR-MATCH-007 (P0):** Do not use protected or sensitive personal characteristics to rank jobs. Recommendations must remain career-related and explainable.
- **FR-MATCH-008 (P1):** Provide an anonymous/demo path where practical so users can try core value without creating an account.

## 6.12 Saved jobs and user profile

- **FR-USER-001 (P1):** Users may register/sign in if account functionality is included in the approved architecture.
- **FR-USER-002 (P1):** Authenticated users can save/unsave canonical jobs and view saved items.
- **FR-USER-003 (P1):** Users can maintain a skill profile and preferences; only fields needed for product functionality should be collected.
- **FR-USER-004 (P0):** Provide a privacy notice and clear explanation of how profile information is used.
- **FR-USER-005 (P1):** Users can export or delete their profile information according to the finalized privacy/retention policy.
- **FR-USER-006 (P0):** Never collect or store a user's resume or sensitive personal information unless a specifically approved requirement and security design exist.

## 6.13 Administration and operations

- **FR-ADMIN-001 (P0):** Provide an administrator-only source registry view.
- **FR-ADMIN-002 (P0):** Show source eligibility, last policy review, last successful ingestion, last failure, and recent run history.
- **FR-ADMIN-003 (P0):** Allow safe pause/resume of approved connectors subject to state-transition rules.
- **FR-ADMIN-004 (P0):** Provide ingestion run history with records attempted, parsed, accepted, rejected, duplicate candidates, duration, and sanitized error category.
- **FR-ADMIN-005 (P0):** Provide data quality summaries for missingness, invalid salary records, date anomalies, location normalization, duplicate rates, and schema drift.
- **FR-ADMIN-006 (P0):** Clearly distinguish live system status from demonstration fixtures.
- **FR-ADMIN-007 (P0):** Apply authentication and role-based access control to all administrative operations.
- **FR-ADMIN-008 (P0):** Record administrative changes and destructive or policy-affecting actions in an audit log.
- **FR-ADMIN-009 (P1):** Provide sanitized parser error samples without exposing cookies, credentials, personal data, or excessive third-party content.
- **FR-ADMIN-010 (P1):** Support connector dry-run/preview mode on a small bounded sample only after the source is approved for access.

## 6.14 Product localization and UI

- **FR-UI-001 (P0):** Bahasa Indonesia is the default language for all user-facing navigation, forms, filters, charts, messages, errors, empty states, and marketing pages.
- **FR-UI-002 (P0):** Preserve established technical names such as Apache Spark, Spark SQL, K-Means, TF-IDF, and API where translation would be confusing; provide Indonesian explanations where useful.
- **FR-UI-003 (P0):** Use Indonesian date, number, percentage, and currency formatting consistently.
- **FR-UI-004 (P0):** Do not show pricing plans, billing pages, subscription upgrades, enterprise sales flows, or monetization CTAs in the initial release.
- **FR-UI-005 (P0):** Preserve the reviewed TalentScope visual direction from Stitch while correcting language consistency, data accuracy, responsiveness, and interaction gaps.
- **FR-UI-006 (P0):** Every important control must have a defined and testable outcome; avoid decorative buttons that imply unavailable functionality.
- **FR-UI-007 (P0):** Include loading, empty, error, unavailable-data, stale-listing, and success states where relevant.
- **FR-UI-008 (P0):** Charts and tables must provide readable labels, units, tooltips or accessible alternatives, and sample-size/context information.
- **FR-UI-009 (P0):** Mobile layouts must remain functional; long Indonesian text must not be clipped or create unintentional horizontal overflow.
- **FR-UI-010 (P0):** Clearly label demo data; never make static mock records look like real, verified, currently open jobs.
- **FR-UI-011 (P1):** Keep components and copy ready for future English localization, but do not make English the default user experience.

---

# 7. Data Requirements and Canonical Schema

The exact schema must be reconciled with the existing repository after audit. The following is the target logical model, not an instruction to create every field blindly.

## 7.1 Canonical Job fields

Suggested fields include:

- `job_id`: internal stable canonical ID.
- `source_record_id`: source-specific record identifier.
- `source_id`: foreign key to source registry.
- `source_job_key`: stable ID from source when present.
- `canonical_url`: canonical or permitted original job URL.
- `title_original`.
- `title_normalized`.
- `company_name_original`.
- `company_id` / normalized company reference when reliable.
- `location_original`.
- `country_code`.
- `province_normalized`.
- `city_or_regency_normalized`.
- `location_confidence`.
- `employment_type_original`.
- `employment_type_normalized`.
- `work_arrangement`.
- `experience_requirement_original`.
- `experience_min_years` / `experience_max_years` when parseable.
- `education_requirement_original`.
- `salary_original_text` only if retention is permitted.
- `salary_min` / `salary_max`.
- `salary_currency`.
- `salary_period`.
- `salary_normalized_monthly_min` / `salary_normalized_monthly_max` only when safe and justified.
- `salary_parse_status` and `salary_confidence`.
- `description` or a permitted minimal representation; source-specific retention rules apply.
- `description_hash` for matching only when legally/technically appropriate.
- `published_at`.
- `expires_at`.
- `source_updated_at`.
- `first_seen_at`.
- `last_seen_at`.
- `lifecycle_status`.
- `source_attribution_text`.
- `source_record_url`.
- `ingestion_run_id`.
- `parser_version`.
- `schema_version`.
- `data_quality_flags`.
- `created_at` / `updated_at`.

Do not store every field for every source if the source does not provide it or does not permit its retention.

## 7.2 Related logical entities

Potential entities include:

- `Source`.
- `SourcePolicyReview`.
- `IngestionRun`.
- `SourceRecord`.
- `Job` (canonical listing).
- `JobSnapshot` or field-change event if retention is permitted.
- `Company`.
- `Location`.
- `Skill`.
- `JobSkillMention`.
- `JobSkill` normalized relationship.
- `DuplicateCandidate` / `DuplicateDecision`.
- `DataQualityFinding`.
- `User` and `UserSkill` only if user accounts/profile are approved.
- `SavedJob` only if accounts are implemented.
- `AuditEvent`.
- `AnalyticsSnapshot` or precomputed result when helpful.

The agent must justify each table/entity and avoid unnecessary schema complexity.

## 7.3 Source record versus canonical job

A source record preserves one source's representation and provenance. A canonical job represents the reconciled opportunity across eligible sources. They must not be conflated.

For example, one vacancy syndicated to multiple permitted sources may have one canonical job and multiple source records. If the evidence suggests similar but distinct vacancies, they must remain separate until a safe matching decision is made.

## 7.4 Historical snapshots

Historical snapshots are useful for data freshness, job lifecycle, repost detection, and trend analysis. However, storing snapshots must respect source retention requirements and use only permitted data fields.

For every stored snapshot, record:

- Observation timestamp.
- Source and source record key.
- Schema/parser version.
- Fields observed or changed.
- Retention policy.
- Provenance.

Do not claim a trend from repeated query results unless distinct observation times and valid comparisons exist. Do not retain full HTML snapshots by default.

## 7.5 Data retention and minimization

- Retain only data needed for product functionality, analytics, audit, and source obligations.
- Apply per-source retention rules.
- Support deletion or expiry of data when required by a source's terms, license, permission, or applicable law.
- Keep derived aggregate statistics only when they can be retained and published under the applicable source conditions.
- Avoid retaining entire HTML pages, JavaScript bundles, unrelated images, cookies, profiles, or contact data.
- Never store authentication cookies or browser session credentials as scrape configuration.

---

# 8. Data Acquisition and Crawler Architecture

## 8.1 Adapter-based connector design

Use a common interface while allowing each source adapter to handle source-specific details. A conceptual interface might include:

- `validate_policy_and_config()`
- `discover_records(checkpoint)`
- `fetch_record(reference)`
- `parse_record(payload)`
- `normalize_record(parsed)`
- `get_next_checkpoint()`
- `health_check()`

Names may differ according to the selected framework. The design objective is separation of concerns, explicit source policy, testability, and safe per-source failure isolation.

The shared pipeline should own common validation, canonicalization, deduplication, persistence, quality checks, and run reporting. Adapters should not independently invent their own canonical database schema.

## 8.2 Acquisition method selection

For each eligible source, select a method based on the research findings:

1. Official, documented API with appropriate terms.
2. Explicitly licensed data feed or downloadable dataset.
3. Official RSS/Atom or other documented feed.
4. Permitted public structured data or sitemap references.
5. Modest, permitted HTML retrieval and parsing.
6. Browser automation only when expressly allowed, necessary, and not prohibited by the source.

Do not infer permission from the fact that a site's frontend requests an undocumented JSON endpoint. Do not reverse engineer a private API or bypass controls.

## 8.3 Parser strategy

- Prefer structured API fields and JSON-LD when their use is permitted.
- Use robust HTML selectors and resilient parser logic for permitted HTML.
- Avoid brittle selectors tied to generated class names when alternatives exist.
- Keep source-specific fixtures sanitized or synthetic.
- Version parsers and detect schema/DOM changes.
- If required fields disappear or parsing quality falls below thresholds, pause or degrade the connector and raise an operational finding rather than ingesting corrupted records silently.

## 8.4 Rate limiting and retry policy

Every connector must apply:

- Per-host concurrency limits.
- Configurable delay between requests.
- Request timeouts.
- Limited retries only for transient errors.
- Exponential backoff with jitter where appropriate.
- Respect for `Retry-After` and source-documented rate limits.
- Conditional GET where possible and allowed.
- Circuit breakers for repeated failures or denial signals.
- Global run limits (pages, time, or records) to avoid unbounded operations.
- Safe cancellation.

Never retry a prohibited operation indefinitely. Never bypass rate limits using multiple IP addresses or accounts.

## 8.5 Crawl scheduling

The initial scheduling mechanism should be as lightweight as practical. The architecture research must compare:

- A CLI invoked manually or by system scheduler.
- A lightweight in-process scheduler or cron-like job.
- A task queue and worker if concurrent workloads require it.
- A dedicated orchestrator such as Prefect, Dagster, or Airflow only if dependency management, retries, run history, and operational complexity justify it.

Do not choose Airflow merely because the project uses Big Data. A first release may use a controlled command/worker model while preserving a clean seam for future orchestration.

Scheduling frequency must be source-specific and comply with source restrictions. A portal that disallows automated access must not be scheduled.

## 8.6 Manual/import connectors

Where scraping is not allowed but a licensed public dataset or permitted file is available, support controlled import with:

- File validation.
- Schema mapping.
- License/source metadata.
- Import timestamp.
- Row-level validation.
- Duplicate handling.
- Reproducible error report.

Manual imports must not be treated as live ingestion.

---

# 9. Target Architecture and Technology Selection

## 9.1 Architecture selection is research-gated

The stack below is a **candidate architecture**. Claude must audit existing code, perform the source research, compare alternatives, and document final decisions in ADRs before implementation. Preserve compatible existing components where they work.

The goal is a maintainable application for a solo developer or small team. Prefer a modular monolith and a few clear runtime processes over premature distributed services.

## 9.2 Candidate architecture

### Web application

- **Next.js + React + TypeScript** for the primary user interface.
- **Tailwind CSS** and reusable accessible components, retaining the approved TalentScope visual direction from Stitch.
- **Apache ECharts** or another justified visualization library for analytical charts.
- Client-side state only where needed; URL query parameters should capture shareable search/filter state where appropriate.
- Bahasa Indonesia as the default interface language.

### API and application backend

- **Python + FastAPI** for documented REST endpoints, schema validation, and service logic.
- Pydantic models for request/response contracts.
- SQLAlchemy 2.x or another justified persistence layer.
- Alembic or equivalent database migrations if SQLAlchemy is selected.
- A service/repository separation where it improves maintainability; avoid unnecessary abstraction layers.

### Database and search

- **PostgreSQL** as the initial relational database for canonical jobs, source records, source governance, ingestion metadata, users (if required), and analytics metadata.
- Use PostgreSQL full-text search and appropriate indexes as a baseline.
- Consider `pg_trgm` or an equivalent lightweight fuzzy-search method if needed.
- Do not add Elasticsearch/OpenSearch or a separate search service until measured search requirements justify it.

### Acquisition and parsing

Research a primary framework appropriate for the existing code and sources. Candidate libraries include **Scrapy**, **HTTPX**, **BeautifulSoup**, **selectolax**, and **Playwright**. They are not all mandatory.

Potential split:

- An efficient HTTP client and HTML parser for permitted static/public sources.
- A crawling framework with throttling, checkpoints, and middleware when the connector count/workflow justifies it.
- Browser automation only for approved sources that need it; do not use it to evade controls.
- Reusable adapter interfaces and source-specific parser modules.

Avoid running a headless browser for every source if structured data or ordinary HTTP requests suffice.

### Analytics and data processing

- Audit and preserve the existing **Apache Spark / PySpark, Spark SQL, and Spark MLlib** work where useful.
- Separate batch/analytical jobs from interactive API requests.
- Precompute costly aggregates and publish results for efficient reads.
- Evaluate whether routine current-scale transformations are more maintainable with standard Python, Polars, DuckDB, or SQL. Do not force a large Spark runtime into every request simply to use the brand name.
- If Spark is retained for educational evidence and future batch scale, isolate it as a batch/analytics job and document execution requirements.
- Do not replace the original K-Means implementation without documenting the experimental reason and reproducing a baseline.

### Data files/object storage

- Use versioned schema and columnar formats such as Parquet where they are appropriate for processed analytical snapshots.
- Evaluate simple local/object storage first. A separate managed object-storage service is optional and requires justification.
- Avoid storing complete HTML pages, duplicate raw files, or full third-party content without a clear permitted use.

### Background tasks and orchestration

- Use a simple worker/CLI/scheduler model for the initial implementation if it satisfies reliability requirements.
- Add a queue or dedicated orchestrator only if concurrent tasks, recovery, scheduling, visibility, or dependencies demand it.
- Avoid requiring Redis solely to schedule a few batch tasks.

### Deployment and engineering quality

- Docker and Docker Compose for a reproducible local development setup where suitable.
- GitHub Actions or existing CI tooling for linting, type checks, tests, and build verification.
- `pytest` for backend/data tests; suitable frontend unit and E2E tools such as Vitest and Playwright if compatible with the chosen stack.
- Structured logs, health endpoints, migrations, environment-variable configuration, and documented backup/recovery expectations.

## 9.3 Required architecture comparison

Before final selection, the agent MUST compare at least these options:

1. Next.js + FastAPI + PostgreSQL versus a single Python web framework for the application.
2. Scrapy versus a smaller HTTPX/parser-based adapter system for source acquisition.
3. Playwright versus non-browser retrieval, source by source.
4. Spark/PySpark versus Python/SQL/Polars/DuckDB for specific tasks.
5. Simple scheduling versus Prefect/Dagster/Airflow.
6. PostgreSQL full-text search versus a separate search engine.
7. Local files/Parquet versus separate object storage.
8. Modular monolith versus multiple deployable services.

The comparison must consider: existing repository, source policy, reliability, ease of testing, runtime complexity, learning/portfolio value, maintenance burden, resource use, deployability, and expected data volume. Choose the simplest approach that meets requirements without closing off reasonable growth.

## 9.4 Conceptual system diagram

The final diagram must reflect the selected architecture, but it will likely resemble:

```text
                 SOURCE RESEARCH / POLICY REGISTRY
                               |
                  only eligible sources enabled
                               |
        +----------------------+----------------------+
        |                      |                      |
 Official APIs/feeds     Permitted HTML       Licensed datasets /
   /public datasets       source adapters       manual imports
        |                      |                      |
        +----------------------+----------------------+
                               |
                   Connector / Ingestion Worker
                               |
             Policy checks, rate limits, retries
                               |
                   Source-record validation
                               |
                Normalization and provenance
                               |
             Cross-source duplicate resolution
                               |
              Canonical jobs + source records
                               |
           +-------------------+-------------------+
           |                   |                   |
        PostgreSQL        Parquet / files      Run & quality
       application data   if justified         metadata
           |                   |
           +---------+---------+
                     |
          Batch analytics / NLP / ML
           Spark jobs where justified
                     |
             Precomputed aggregates
                     |
                FastAPI REST API
                     |
         Next.js / TypeScript website
                     |
  Search, market insights, skills, salary, career match
```

---

# 10. API Requirements (Candidate Contract)

The actual route design must be finalized after auditing existing code and data model. The following are candidate endpoint groups, not a requirement to create every route in one sprint.

## 10.1 Public read endpoints

- `GET /api/v1/jobs` — paginated eligible canonical job search.
- `GET /api/v1/jobs/{job_id}` — job details with permitted provenance and lifecycle state.
- `GET /api/v1/filters` — supported filter values and counts where available.
- `GET /api/v1/market/overview` — aggregate market overview with scope/freshness metadata.
- `GET /api/v1/market/locations` — job counts by location.
- `GET /api/v1/market/occupations` — normalized occupation summaries.
- `GET /api/v1/market/employment-types` — employment type distribution.
- `GET /api/v1/skills` — skill list/search and supported aggregate metadata.
- `GET /api/v1/skills/{skill_id}` — skill detail, eligible-listing denominator, co-occurrence and example references as permitted.
- `GET /api/v1/skills/compare` — occupation/skill comparison if implemented.
- `GET /api/v1/salaries/overview` — salary aggregate and sample-size metadata.
- `GET /api/v1/salaries/compare` — role/location comparisons supported by valid records.
- `GET /api/v1/sources/coverage` — user-safe, public source coverage summary without revealing internal sensitive policy notes.

## 10.2 Authenticated endpoints, if accounts are approved

- `GET /api/v1/me` / `PATCH /api/v1/me`.
- `GET /api/v1/me/skills` / `PUT /api/v1/me/skills`.
- `GET /api/v1/me/saved-jobs`.
- `PUT /api/v1/me/saved-jobs/{job_id}`.
- `DELETE /api/v1/me/saved-jobs/{job_id}`.
- `POST /api/v1/career-match` — return explainable recommendations from a documented algorithm.
- `GET /api/v1/me/saved-searches` and corresponding management routes if prioritized.

## 10.3 Admin endpoints

- `GET /api/v1/admin/sources`.
- `GET /api/v1/admin/sources/{source_id}`.
- `POST /api/v1/admin/sources/{source_id}/pause`.
- `POST /api/v1/admin/sources/{source_id}/resume` — only if eligibility and approval rules allow it.
- `GET /api/v1/admin/source-reviews`.
- `GET /api/v1/admin/ingestion-runs`.
- `GET /api/v1/admin/ingestion-runs/{run_id}`.
- `POST /api/v1/admin/ingestion-runs` — bounded, policy-checked execution trigger if supported.
- `GET /api/v1/admin/data-quality`.
- `GET /api/v1/admin/audit-events`.

Every admin route requires actual authorization. Never rely on hiding buttons in the frontend as the sole access control.

## 10.4 API conventions

- Version routes under `/api/v1`.
- Validate and bound every user-provided filter, search query, sort field, and page size.
- Use stable error envelopes and appropriate HTTP status codes.
- Avoid returning full third-party descriptions when source terms or retention policies do not permit it.
- Set explicit timeouts and limits.
- Define pagination contract and stable sorting.
- Document endpoints using OpenAPI.
- Do not expose source secrets, raw cookies, internal filesystem paths, full exception traces, or private operations notes.
- Protect against SQL injection by using parameterized queries/ORM patterns.
- Add rate limiting or abuse controls where justified by deployment and threat model.

---

# 11. Analytics and Machine Learning Requirements

## 11.1 Baseline reproducibility

The existing report states that the original project collected 1,133 listings and selected K-Means with `k = 3` and a Silhouette Score of `0.0351`. The repository must be checked to verify the input data, configuration, feature pipeline, seed handling, and reproducibility before relying on those values.

- **FR-ML-001 (P0):** Preserve a reproducible baseline of the existing feature extraction and K-Means experiment if the code/data can be verified.
- **FR-ML-002 (P0):** Record feature fields, tokenizer/stopword configuration, HashingTF settings, IDF configuration, K-Means parameters, random seed, evaluation settings, and data version.
- **FR-ML-003 (P0):** Explain that a Silhouette Score of 0.0351 is low and does not support a claim of clearly separated clusters.
- **FR-ML-004 (P1):** Compare title-only representations with richer permitted job fields if suitable data is available.
- **FR-ML-005 (P1):** Compare TF-IDF and semantic embeddings only when there is a clear hypothesis, a repeatable evaluation, and a feasible deployment cost.
- **FR-ML-006 (P1):** Evaluate stability across seeds and cluster sizes where relevant.
- **FR-ML-007 (P0):** Use representative reviewed examples and quantitative metrics together; do not declare clusters meaningful based only on selected anecdotes.

## 11.2 Skill extraction

Start with an understandable baseline—such as a versioned bilingual skill dictionary and phrase matching—if it fits the actual data. Evaluate more advanced NLP only after baseline quality is measured.

Required design considerations:

- Indonesian and English wording.
- Canonical skill names and aliases.
- Context-sensitive ambiguity where a token can mean a general word or a skill.
- Phrase boundaries and variants.
- Source/record provenance.
- Manual review sample.
- Precision/recall or another valid evaluation method.
- Versioning of skill dictionary/model and extraction output.
- Handling skill mentions as a signal, not necessarily a formal job requirement.

Do not train or host a large model unless measured value warrants the operational cost.

## 11.3 Career matching baseline

Begin with transparent filters and a simple similarity/scoring baseline. Clearly define how skill overlap, title similarity, location, experience, and employment preferences affect the ranking. Do not overstate accuracy. Collect human feedback or create a reviewed evaluation set before treating the ranking as reliable.

## 11.4 Analytics correctness

- All metrics must have documented definitions and denominators.
- Canonical job counts and source-record counts must be distinct.
- Time comparisons must use consistent source coverage and time windows or disclose changes in coverage.
- Salary analysis must disclose the number of usable records.
- Percentages must be calculated from a defined denominator and rounded consistently.
- Sparse categories must be identified; do not infer a national market pattern from a tiny sample.
- All chart data must originate from real query results or be explicitly labeled demonstration data.

---

# 12. Nonfunctional Requirements

## 12.1 Performance

Initial targets should be measured in the deployed environment and adjusted based on evidence:

- **NFR-PERF-001:** Typical cached/optimized read APIs should target p95 under 500 ms at the first-release dataset scale, excluding external source calls and expensive ad-hoc computations.
- **NFR-PERF-002:** Job search should use bounded queries, appropriate indexes, and pagination.
- **NFR-PERF-003:** End-user page rendering must not trigger a new source crawl.
- **NFR-PERF-004:** Expensive analytics should be precomputed or executed asynchronously where appropriate.
- **NFR-PERF-005:** Measure load time, query performance, crawl duration, and batch job runtime; never fabricate performance metrics.

These are target objectives, not a claim of measured performance.

## 12.2 Reliability

- **NFR-REL-001:** A failed source connector must not prevent healthy connectors from completing.
- **NFR-REL-002:** Ingestion must be restartable, bounded, and idempotent.
- **NFR-REL-003:** Transient errors and policy/access denials must be treated differently.
- **NFR-REL-004:** Source denial or policy changes must trigger a safe pause, not an evasion mechanism.
- **NFR-REL-005:** Database migrations and backups/recovery procedures must be documented before production deployment.
- **NFR-REL-006:** The application must show stale/unavailable data states honestly.

## 12.3 Maintainability

- **NFR-MAINT-001:** Use clear module boundaries between source registry, adapters, pipeline, normalization, persistence, analytics, API, and frontend.
- **NFR-MAINT-002:** Each connector must be independently testable and configurable.
- **NFR-MAINT-003:** Avoid hard-coded absolute local paths and machine-specific assumptions.
- **NFR-MAINT-004:** Use centralized configuration and safe environment-variable handling.
- **NFR-MAINT-005:** Document important architecture decisions and trade-offs.
- **NFR-MAINT-006:** Use automated formatting, linting, type checks, and tests where compatible with the selected stack.

## 12.4 Security and privacy

- **NFR-SEC-001:** Never commit credentials, cookies, tokens, private keys, or production secrets.
- **NFR-SEC-002:** Use least privilege for database credentials and admin roles.
- **NFR-SEC-003:** Protect admin endpoints with server-side authentication and authorization.
- **NFR-SEC-004:** Validate all request parameters and uploaded files.
- **NFR-SEC-005:** Avoid logging credentials, full descriptions, or personal data unnecessarily.
- **NFR-SEC-006:** Collect only the user data required for the feature.
- **NFR-SEC-007:** Provide a privacy notice and user data deletion/export process if accounts are implemented.
- **NFR-SEC-008:** Follow an applicable-law review, including Indonesia's Personal Data Protection Law where relevant.
- **NFR-SEC-009:** Avoid scraping personal profiles, resumes, application records, or recruiter contact details.
- **NFR-SEC-010:** Source-specific licenses, terms, attribution, and retention rules must be represented in system configuration or policy metadata.

## 12.5 Accessibility and localization

- **NFR-UX-001:** Default user experience is Bahasa Indonesia (`id-ID`).
- **NFR-UX-002:** Provide keyboard navigation, visible focus, meaningful labels, and suitable contrast.
- **NFR-UX-003:** Important chart insights must not rely on color alone.
- **NFR-UX-004:** Forms require labels and actionable validation messages.
- **NFR-UX-005:** Pages must remain usable on laptop, desktop, tablet, and mobile widths.
- **NFR-UX-006:** Long Indonesian labels must not overlap or clip.
- **NFR-UX-007:** Date, number, percent, and currency formatting must be consistent.

## 12.6 Observability

- **NFR-OBS-001:** Use structured logs with run IDs, source IDs, and error categories.
- **NFR-OBS-002:** Expose application health/readiness checks as appropriate.
- **NFR-OBS-003:** Track source-level success/failure, duration, parse yield, validation rejection, duplicates, and rate-limit events.
- **NFR-OBS-004:** Log sanitization must prevent sensitive or excessive source content from being exposed.
- **NFR-OBS-005:** Admin views must be based on operational events, not static design data.

## 12.7 Reproducibility

- **NFR-REP-001:** Include lockable dependency versions or a reproducible dependency-management strategy.
- **NFR-REP-002:** Provide environment examples without credentials.
- **NFR-REP-003:** Provide deterministic tests and a controlled sample dataset/fixture set.
- **NFR-REP-004:** Document how to run migrations, tests, the frontend, API, and bounded pipeline jobs.
- **NFR-REP-005:** Document which components need external network access and which can be demonstrated offline.

## 12.8 Resource efficiency

- **NFR-RES-001:** Prefer resource-efficient parsing, bounded concurrency, and incremental processing.
- **NFR-RES-002:** Do not launch browser automation when ordinary HTTP retrieval is enough and permitted.
- **NFR-RES-003:** Avoid redundant full copies of raw and processed data; define retention and cleanup policies.
- **NFR-RES-004:** Use batch processing and compact formats where beneficial, and avoid loading entire datasets into memory unnecessarily.
- **NFR-RES-005:** Keep optional infrastructure optional until measured requirements justify it.
- **NFR-RES-006:** Provide limits for crawl duration, response size, number of pages, and records per run.
- **NFR-RES-007:** Provide a cleanup command for regenerable caches and temporary artifacts, with safeguards against deleting canonical data.

---

# 13. Source, Copyright, and Responsible Aggregation Policy

## 13.1 Minimal display policy

TalentScope should show only the fields needed for job discovery and analysis, and only when the applicable source terms/license permit the specific display. When rights to reproduce a description are unclear, prefer concise normalized metadata, a short factual summary generated from permitted data, and a link to the original source—subject to review and permissions. Do not assume that a link alone makes copying the full content permissible.

## 13.2 Attribution

For each listing, retain and display source attribution as required. Include the original source's name and a link where permitted. Do not remove ownership notices or present third-party jobs as TalentScope-originated listings.

## 13.3 Removal and correction requests

Provide a documented contact/process for a source owner or employer to raise a data correction/removal request. Authenticate the request reasonably, record the resolution, stop affected ingestion when appropriate, and remove/update data in accordance with verified obligations. Do not promise deletion from third-party systems TalentScope does not control.

## 13.4 Fraud and suspicious listing signals

The platform may display a cautious informational signal for suspicious or incomplete listings only if a documented rule produces it. It must not mark an employer as fraudulent or verified without sufficient evidence and a review process. Make users aware that they should confirm details on the original source before applying.

## 13.5 Coverage transparency

A public methodology page must explain:

- What source categories are used.
- That sources may be excluded because their terms do not permit automated collection.
- That sources differ in regional, occupational, and salary coverage.
- That some vacancies may be duplicated, outdated, or incomplete.
- That a public aggregation cannot guarantee every job in Indonesia is represented.
- How timestamps and lifecycle statuses are assigned.
- How skills and salary fields are normalized.
- How correction or removal requests can be submitted.

---

# 14. Database, Search, and Persistence Design Requirements

## 14.1 Candidate schema groups

The final schema should be derived from the audited repository and requirements. Likely logical groups include:

- `sources` and `source_policy_reviews`.
- `ingestion_runs` and optional run events.
- `source_records`.
- `jobs` (canonical jobs).
- `job_snapshots` or allowed field-change records.
- `companies`.
- `locations` or location normalization tables.
- `skills`, `job_skill_mentions`, and normalized `job_skills`.
- `duplicate_candidates` and `duplicate_decisions` if needed.
- `data_quality_findings`.
- `users`, `user_skills`, `saved_jobs`, and `saved_searches` only if the account features are approved.
- `audit_events`.
- Precomputed analytical tables/materialized views only where measured performance benefits justify them.

## 14.2 Indexing

Candidate indexes include:

- Canonical job ID and source record relationships.
- Canonical URL/source key uniqueness constraints where valid.
- Normalized title and company.
- Location IDs/normalized fields.
- Lifecycle and date fields.
- Skill join tables.
- Salary filter fields where useful.
- Search vectors/trigram indexes if selected.
- Source status and run timestamps for admin pages.

The agent must justify indexes and validate query plans for important queries instead of adding indexes indiscriminately.

## 14.3 Search behavior

- Use parameterized queries and bounded result sizes.
- Decide how Indonesian/English term variants, aliases, and fuzzy matches are handled.
- Preserve stable ordering across pagination.
- Clearly distinguish exact matches and relevance ranking if the UI communicates relevance.
- Use a more complex search engine only after baseline search has been evaluated against real usage.

---

# 15. Frontend and User Experience Requirements

## 15.1 Design direction

Continue the existing TalentScope Stitch design rather than redesigning from scratch. Preserve the current professional teal/neutral visual language where effective, but make the product genuinely Indonesian-first and fix inconsistent labels, navigation, values, and responsive issues.

Primary app sections:

- Beranda / Ringkasan Pasar Kerja.
- Cari Lowongan.
- Analisis Pasar.
- Analisis Keterampilan.
- Analisis Gaji.
- Kecocokan Karier.
- Lowongan Tersimpan.
- Profil Saya (if account support is implemented).
- Methodology / Tentang Data.

Administrative sections must be separate and protected:

- Sumber Data.
- Status Pipeline.
- Kualitas Data.
- Riwayat Eksekusi.
- Audit Perubahan.

## 15.2 Required page states

Every important page must handle:

- Initial/loading state.
- Valid data state.
- Empty state.
- No search matches.
- Partial/incomplete data.
- Stale results.
- Source temporarily unavailable.
- API failure.
- Unauthorized/access denied.
- Form validation error.
- Successful save/update.

## 15.3 Product trust

Do not show unsupported “verified”, “real-time”, “live”, “market-leading”, “99% accurate”, or similar claims. If a connector has not run recently, the UI should show its actual freshness. If a statistic is from a historical snapshot, label it as historical.

## 15.4 No monetization UI for the initial release

Do not create pricing pages, paid-tier cards, subscription CTAs, paywalls, trial funnels, or enterprise-sales pages in the initial product. Prioritize discovery, insight quality, and trust.

---

# 16. Machine Learning and Analytics Evaluation Plan

## 16.1 Existing clustering baseline

The original report described:

- Dataset size: 1,133 listings.
- Feature: job title text.
- Text transformation involving lowercasing, regular-expression cleanup, tokenization, stopword removal, HashingTF and IDF.
- K-Means experiment with `k` values 3, 4, 5, and 6.
- Selected configuration: `k = 3`.
- Reported Silhouette Score: `0.0351`.

These facts are historical report claims and must be checked against the repository and experiment artifacts before being treated as reproducible baseline results.

## 16.2 Required ML findings

The audit must answer:

- Is the existing code reproducible from the available environment?
- Are feature transformation, random seed, and model parameters explicit?
- Are there data leakage or evaluation issues?
- Is a low Silhouette Score being interpreted appropriately?
- Do cluster examples support the stated labels?
- Are clusters stable across seeds and reasonable preprocessing changes?
- Does clustering solve a meaningful user problem compared with skill extraction, search, or matching?

## 16.3 Experiment candidates

Potential experiments include:

1. Title-only TF-IDF baseline.
2. Combined title and permitted skill/description features.
3. Alternative text normalization and bilingual token handling.
4. Embedding-based representations, if operationally justified.
5. Alternative clustering approaches, if supported by the data geometry.
6. Stability evaluation across random seeds.
7. Human-reviewed cluster coherence sample.
8. Job title normalization/classification as an alternative to unsupervised clustering.
9. Skill extraction baseline evaluation.
10. Job search/recommendation relevance evaluation.

For each experiment, document hypothesis, dataset version, parameters, metrics, compute/runtime implications, and interpretation. Do not promise better performance before conducting the experiment.

---

# 17. Testing Requirements

## 17.1 Unit tests

Test at least:

- Source policy state gating.
- Request configuration and rate-limit logic.
- Parser behavior for valid, malformed, and changed layouts.
- Field normalization.
- Date and salary parsing.
- Location normalization.
- Employment type normalization.
- Deduplication rules.
- Lifecycle transitions.
- Skill extraction and alias normalization.
- Analytics denominators and aggregates.
- Recommendation scoring.
- API validation and error mapping.

## 17.2 Integration tests

Test:

- Source adapter → normalizer → validation → persistence using fixtures.
- Repeated ingestion idempotency.
- Cross-source duplicate handling.
- Database constraints/migrations.
- API search/filter/pagination against seeded test records.
- Admin source state gating.
- Batch analytics output and publication.
- User save/unsave behavior if accounts are implemented.

Do not call external job sites from ordinary CI tests. Use mocks, synthetic fixtures, permitted static test fixtures, or a separately controlled manual integration test where approved.

## 17.3 Contract and parser regression tests

Each active source adapter must have tests that cover its documented fields, source identifiers, pagination/checkpoints, empty results, throttling behavior, parsing failures, and schema/layout change detection. Fixtures must comply with source content retention rules; use synthetic fixtures if copying source HTML into the repository is not permitted.

## 17.4 End-to-end tests

Test core user journeys:

1. Open homepage and search for a job.
2. Apply supported filters and change sorting.
3. Open details and follow the external source link.
4. Open market analytics and drill down into a filtered result set.
5. Compare skills between occupations.
6. View salary insight with its sample size and limitations.
7. Save/unsave a job if account features exist.
8. Administrator pauses an approved connector and confirms no subsequent fetch is scheduled.
9. Administrator cannot activate a blocked connector.
10. Inspect an ingestion run and its quality summary.

## 17.5 Security tests

Include appropriate checks for authentication, authorization, input validation, SQL injection resistance, unsafe file uploads if any, secrets exposure, and log sanitization. Run dependency/security checks as appropriate to the selected tooling.

## 17.6 Test truthfulness

Never fabricate test pass/fail counts or coverage. Every reported test must state whether it was executed, the relevant command/environment, and the actual result. If tests cannot run because dependencies/services are unavailable, document that limitation.

---

# 18. Deployment, Operations, and Documentation

## 18.1 Deployment

The final architecture should support a repeatable local environment and a documented deployable configuration. Choose the lightest appropriate setup that meets the verified requirements.

Docker Compose is a candidate for local development and a small deployment. The architecture research should determine whether frontend, API, and ingestion worker should run as separate processes/containers or whether an even simpler arrangement fits better. Do not split components solely for aesthetics.

## 18.2 Configuration

- Use environment variables or a validated configuration module.
- Provide `.env.example` without real secrets.
- Separate local, test, and production configuration.
- Validate required settings at startup.
- Ensure secrets are never bundled into frontend code.

## 18.3 Database lifecycle

- Provide repeatable migrations.
- Document initial bootstrap and seed/demo data handling.
- Avoid accidental reseeding of demonstration records into production data.
- Document backup and recovery for the deployed system.
- Use explicit cleanup procedures for temporary data and regenerable caches.

## 18.4 Required documentation

The repository should eventually contain:

- `README.md` — project overview and quick start.
- `TALENTSCOPE_SRS.md` — this requirements specification.
- `docs/RESEARCH_SOURCES.md` — source research matrix and primary references.
- `docs/ARCHITECTURE.md` — chosen architecture and diagrams.
- `docs/adr/` — architecture decision records.
- `docs/DATA_DICTIONARY.md` — dataset schemas and field definitions.
- `docs/DATA_POLICY.md` — source permissions, retention, attribution, and removal workflow.
- `docs/PIPELINE.md` — ingestion, processing, run/recovery procedures.
- `docs/API.md` or OpenAPI-generated docs.
- `docs/ML_EVALUATION.md` — reproducible baseline and experiments.
- `docs/TESTING.md` — test commands and coverage of user journeys.
- `docs/DEPLOYMENT.md` — build/deploy/environment/backup instructions.
- `.env.example` — safe configuration template.
- Automated tests and sanitized fixtures.

Do not claim an artifact exists until it has been created and verified.

---

# 19. Phased Development Roadmap

The agent must adjust this roadmap after auditing actual code and completing source research. These phases are dependency-oriented, not fixed deadlines.

## Phase 0 — Repository audit and source deep research (P0)

Deliverables:
- Repository map and execution flow.
- Data/dataset inventory.
- Existing feature status matrix with evidence.
- Broad candidate source list and per-source policy/access review.
- Source eligibility decisions and excluded-source rationale.
- Technology comparison and ADRs.
- Architecture diagram and risk register.

Acceptance criteria:
- No code changes during the audit.
- The current system's real state is distinguished from report claims.
- Every source candidate is classified or explicitly marked unverified.
- No disallowed source is activated.
- A reviewable implementation plan exists.

## Phase 1 — Reproducible foundation and source governance (P0)

Deliverables:
- Reproducible setup and test baseline.
- Configuration cleanup where justified.
- Source registry model and policy gating.
- Source research documentation.
- Common connector interface.
- Run logging and basic validation.

Acceptance criteria:
- A blocked or unreviewed source cannot run.
- A synthetic/mock connector can pass through the core pipeline.
- Run status and failure reason are recorded.
- No external crawler is activated before review.

## Phase 2 — Canonical data model and ingestion MVP (P0)

Deliverables:
- Canonical job/source schemas.
- Normalization and data-quality rules.
- Deduplication baseline.
- Lifecycle/freshness logic.
- First few connectors selected from the approved source matrix.

The number and order of initial connectors must follow actual research; do not preselect a source that is not eligible.

Acceptance criteria:
- All records have provenance.
- Repeated ingestion is idempotent.
- Per-source errors are isolated.
- Salary and date parsing errors are visible, not silently coerced.
- Each active connector has tests and a documented policy review.

## Phase 3 — Searchable API and user application (P0)

Deliverables:
- Database migrations and core data access.
- FastAPI or the reviewed backend choice.
- Next.js or the reviewed frontend choice.
- Indonesian search/filter experience.
- Job details and source-attributed external links.
- Loading/empty/error/stale states.

Acceptance criteria:
- Search results match database queries and filters.
- Pagination is stable and bounded.
- UI does not misrepresent demo data as live.
- End-to-end search journey passes.

## Phase 4 — Market, skill, and salary intelligence (P1)

Deliverables:
- Verified analytics definitions.
- Market overview.
- Skill extraction baseline and review sample.
- Salary normalization/quality controls.
- Drill-down from insights to relevant jobs.

Acceptance criteria:
- Each metric has a documented denominator and time/scope label.
- Skill extraction quality is measured on a reviewed sample.
- Salary analytics use only compatible normalized records.
- No unsupported trend or accuracy claims are displayed.

## Phase 5 — Career matching (P1)

Deliverables:
- Optional user skill profile.
- Explainable recommendation baseline.
- Skill overlap and missing/unlisted-skill explanations.
- Relevance evaluation plan and results where measured.

Acceptance criteria:
- Scores have a documented definition.
- Scores are not presented as hiring probabilities.
- Recommendations link to actual eligible records.

## Phase 6 — Reliability and scheduling (P1)

Deliverables:
- Source-specific scheduler configuration.
- Retry/backoff/circuit breaker.
- Incremental checkpoints where available.
- Reprocessing/recovery procedures.
- Source policy re-review process.
- Admin run/quality views.

Acceptance criteria:
- Repeated runs do not create unintended duplicates.
- A source denial stops that connector.
- Failed connectors do not disable healthy sources.
- Pipeline events are accurately reflected in admin views.

## Phase 7 — Production-style engineering and deployment (P1)

Deliverables:
- CI checks.
- Tests and regression fixtures.
- Structured logs and health checks.
- Security and dependency review.
- Deployable configuration.
- Documentation and demo walkthrough.

Acceptance criteria:
- Fresh setup can be reproduced from documentation.
- Required tests pass in the declared environment.
- No secrets are committed.
- The running app's claims match implemented behavior.

## Phase 8 — Coverage expansion and advanced analytics (P2)

Deliverables may include:
- More approved source connectors.
- Additional niche and direct-employer sources.
- Improved occupation normalization.
- Improved skill extraction.
- Semantic search/recommendation if evaluated.
- Trend monitoring from genuine longitudinal observations.

Acceptance criteria:
- Each new source receives policy review and isolated tests.
- Coverage improvement is measured, not assumed.
- Architecture complexity is justified by demonstrated benefit.

---

# 20. Prioritization Framework

Prioritize each opportunity using:

1. **Permission/legality:** Is the source/data use allowed or explicitly authorized?
2. **User value:** Does the capability solve a real job discovery or research problem?
3. **Data availability:** Are required fields actually available and sufficiently complete?
4. **Coverage improvement:** Does it add new regions, roles, sectors, or listings rather than duplicates?
5. **Data quality:** Is the source reliable enough to include?
6. **Implementation effort:** Can the feature be developed and maintained responsibly?
7. **Portfolio value:** Does it demonstrate useful software/data engineering skills?
8. **Operating complexity:** Does it introduce a new service or dependency that is justified?
9. **Verification:** Can success be objectively tested?

A source with high raw volume but prohibited collection is not a valid priority. A small official feed with clear permission and high incremental coverage may be more valuable.

---

# 21. Acceptance Criteria by Product Area

## 21.1 Source ingestion acceptance

An adapter is not “done” until:

- Its source is approved for the exact collection/storage/display purpose.
- Evidence URLs and review date are recorded.
- It respects configured host policies and request limits.
- It parses the documented fields.
- It can handle empty results and transient errors.
- It stops on denial/blocking signals.
- It emits provenance and run metrics.
- It is idempotent across repeat runs.
- It has parser and integration tests.
- It has documented known limitations.

## 21.2 Job explorer acceptance

- Queries return real canonical records from the selected source set.
- Filters work with normalized fields.
- Unknown values do not behave as numeric zero.
- Pagination is bounded and stable.
- Cross-source duplicate jobs are handled consistently.
- Source and freshness information is visible.
- External links work when present and permitted.
- Stale/unknown status is not mislabeled as active.
- Loading, empty, error, and no-match states are tested.

## 21.3 Analytics acceptance

- Metric formulas and denominators are documented.
- Counts distinguish canonical jobs from source records.
- Salary calculations are based on valid comparable records.
- Skill metrics use a validated extraction output.
- Historical trends use genuine multiple-date observations.
- Charts include enough context to interpret the sample.
- Tests cover representative edge cases.

## 21.4 Career matching acceptance

- User inputs are validated.
- Matching logic is documented and deterministic or appropriately seeded.
- Every recommendation has a reason grounded in the job fields.
- Unsupported job attributes are never fabricated.
- Model/scoring limitations are explained.
- The system does not claim a hiring-success probability.

## 21.5 Deployment acceptance

- Setup/build/test/deploy instructions are reproducible.
- Runtime configuration is documented without secrets.
- Health checks and logs are available.
- Database migrations run predictably.
- Test/demo data is clearly separated from real ingestion data.
- The deployed UI, API, and pipeline status reflect the actual system.
- Major known limitations are documented.

---

# 22. Current Project Baseline to Verify

The original project report describes a pipeline for Indonesian job listings using Glints, Python/Selenium/BeautifulSoup, Apache Spark SQL, and Spark MLlib. It reports a dataset of 1,133 listings, location/employment-type/salary analyses, and K-Means clustering with three clusters and a Silhouette Score of 0.0351.

These figures should be treated as historical report statements until verified from files and reproducible code.

The report's initial source must not define the future platform's source coverage. TalentScope is explicitly intended to investigate many eligible source categories, including government/public employment services, job boards, direct employer career sites, authorized ATS feeds, internship/campus sources, and licensed/open data.

The agent must check whether the current repository contains reusable scrapers, datasets, SQL, notebooks, feature pipelines, visualizations, dependencies, or tests. Do not assume any of them exists until inspected.

---

# 23. Risks and Mitigations

| Risk | Impact | Required mitigation |
|---|---|---|
| Source terms prohibit scraping or aggregation | Legal/policy risk and forced redesign | Per-source review; keep blocked connectors disabled; request written permission or use another source |
| Public accessibility mistaken for reuse permission | Unlawful or unauthorized collection/display | Separate access, collection, storage, and publication decisions |
| Source changes HTML/API | Broken or silently corrupted data | Adapter isolation, parser tests, schema/layout checks, alerts, safe pause |
| Overlapping listings across sources | Inflated counts and misleading trends | Source records separated from canonical jobs; explainable dedupe |
| Expired jobs remain visible as active | User frustration and loss of trust | Lifecycle and freshness model; show last-seen/expiry uncertainty |
| Missing/inconsistent salaries | Misleading salary analytics | Explicit missing categories, normalized pay periods, sample-size disclosure |
| Inaccurate skill extraction | Misleading career advice | Versioned taxonomy, reviewed sample, measured quality, clear caveat |
| Sparse or biased source coverage | False national-market claims | Source coverage labels, geographic/sector breakdowns, cautious interpretation |
| Over-engineering infrastructure | Maintenance burden for a small project | Modular monolith; architecture ADRs; add services only after evidence |
| Large model or browser dependency becomes hard to operate | Reliability and runtime burden | Baseline methods first; browser automation only when needed and permitted |
| Secrets or cookies committed | Security compromise | Secret scanning, environment templates, sanitized logs, no stored login cookies |
| Unclear deletion/retention rights | Compliance and source relationship risk | Per-source retention rules, removal process, documented audit trail |
| Demo figures confused with current data | Misrepresentation | Explicit demo labels and source timestamps; do not invent current status |
| One source dominates results | Coverage imbalance | Multi-category source discovery and source-wise coverage metrics |
| Excessive crawling load | Source harm and blocking | Rate limits, caching, quotas, backoff, bounded runs, stop controls |

---

# 24. Required Architecture Decision Records (ADRs)

Before implementation, create concise ADRs for at least these decisions:

- **ADR-001:** Application architecture: modular monolith versus multiple services.
- **ADR-002:** Frontend stack and component/chart libraries.
- **ADR-003:** API/backend framework and persistence strategy.
- **ADR-004:** Database model and search method.
- **ADR-005:** Source adapter/crawling framework.
- **ADR-006:** Browser automation policy and boundaries.
- **ADR-007:** Scheduling/orchestration approach.
- **ADR-008:** Routine analytics engine versus isolated Spark batch execution.
- **ADR-009:** Raw/processed data storage and retention approach.
- **ADR-010:** Cross-source canonicalization and deduplication strategy.
- **ADR-011:** Skill taxonomy/extraction baseline and evaluation.
- **ADR-012:** Career matching/recommendation baseline.
- **ADR-013:** Authentication, authorization, and privacy scope.
- **ADR-014:** Deployment and CI/testing strategy.

Each ADR must contain:

- Context and problem.
- Options considered.
- Decision.
- Evidence and trade-offs.
- Consequences and risks.
- Conditions that would justify revisiting the decision.

Do not create ADRs that merely rubber-stamp a predetermined stack; actual research and repository evidence must be considered.

---

# 25. Final Deliverables Required from the Engineering Agent

Before implementation, the agent must deliver:

1. `docs/REPOSITORY_AUDIT.md` — actual code/data inventory and execution path.
2. `docs/RESEARCH_SOURCES.md` — broad source discovery inventory, current policy evidence, decisions, and review dates.
3. `docs/SOURCE_POLICY_MATRIX.md` or equivalent structured table — explicit connector eligibility and field/retention rules.
4. `docs/ARCHITECTURE.md` — selected architecture and data-flow diagrams.
5. `docs/TECH_STACK_EVALUATION.md` — alternative technologies, trade-offs, and final choices.
6. `docs/adr/` — architecture decision records.
7. `docs/DATA_DICTIONARY.md` — real schemas and field definitions.
8. `docs/IMPLEMENTATION_ROADMAP.md` — phased tasks and acceptance criteria.
9. `docs/RISK_REGISTER.md` — risks and mitigations.
10. A first-sprint proposal with precise tasks, affected files, tests, and acceptance criteria.

These deliverables must distinguish observed facts, research findings, assumptions, and recommendations. The agent must not create misleading evidence or claim tasks completed when they have not been completed.

---

# 26. Final Instructions to Claude Code

You are expected to act as a careful principal engineer, data engineer, product architect, and research analyst.

**Do not start by writing scrapers. Start by researching which sources can be used, auditing the current repository, and designing a safe source strategy.**

The long-term aim is broad Indonesian job coverage from many legitimate sources—not to scrape every domain regardless of its rules. Build the system so new approved connectors can be added independently and monitored without rewriting the core platform.

After the repository audit and deep research, explain:

1. Which source families are genuinely feasible and why.
2. Which popular job portals cannot be scraped under their current terms without authorization.
3. Which sources offer official APIs, feeds, licensed datasets, or suitable public vacancy pages.
4. Which connectors should be implemented first to maximize lawful incremental coverage.
5. What the final system architecture should be and why.
6. What the selected technology stack should be and which candidates should be postponed.
7. Which existing repository components should be preserved, improved, or replaced.
8. What the first implementation sprint should contain.
9. How each major feature will be tested and verified.
10. What limitations must be disclosed to users.

Be explicit when information remains uncertain. Do not equate “freely viewable” with “free to scrape, retain, aggregate, and republish.” Do not bypass access controls or use evasive crawling techniques.

Only after the research, source eligibility matrix, repository audit, architecture proposal, and first-sprint plan are ready should implementation begin, subject to owner approval.

The final product should be a polished, Indonesian-language Job Market Intelligence platform with credible multi-source coverage, reliable data engineering, clear provenance, useful search and analytics, and professional implementation quality—without premature monetization or unsupported claims.

---

# Appendix A — Initial Research References

The following references informed the initial research cautions in this SRS. They are starting points and must be rechecked for current applicability during implementation.

1. **Glints — Terms of Use & Privacy Policy:** <https://glints.com/id/about/terms>  
   Initial finding: published terms include a restriction on automated scraping/data extraction without prior written consent.
2. **JobStreet Indonesia — Website Terms:** <https://id.jobstreet.com/id/terms>  
   Initial finding: terms effective 20 July 2026 prohibit unauthorized aggregation/copying and automated extraction tools except where permitted/authorized.
3. **LinkedIn — User Agreement:** <https://www.linkedin.com/legal/user-agreement>  
   Initial finding: the agreement restricts unauthorized scraping/copying and automated access.
4. **LinkedIn — Prohibited scraping software and extensions:** <https://www.linkedin.com/help/linkedin/answer/a1341387/prohibition-of-scraping-software>  
   Initial finding: LinkedIn explicitly describes crawlers, bots, and scraping software as prohibited absent authorization.
5. **Pasker ID:** <https://paskerid.kemnaker.go.id/>  
   Initial finding: an official Indonesian labor-market/public employment-service candidate with vacancy pages; collection and reuse rights still need investigation.
6. **Karirhub Kemnaker:** <https://karirhub.kemnaker.go.id/>  
   Initial finding: an official public employment-service candidate; do not assume there is a permitted API or scraping right without verifying.
7. **Dealls — Public job listings:** <https://dealls.com/loker>  
   Initial finding: publicly discoverable listings exist; current terms and automated reuse permissions still need separate verification.
8. **KitaLulus — Job search help page:** <https://id.kitalulus.com/help-qa/bagaimana-cara-saya-mendapatkan-pekerjaan-di-kitalulus>  
   Initial finding: website/app job search is offered; this does not establish scraping or republication permission.
9. **IETF RFC 9309 — Robots Exclusion Protocol:** <https://www.rfc-editor.org/rfc/rfc9309.html>  
   Initial finding: describes crawler rules; robots.txt is not access authorization.
10. **Google Search Central — Robots.txt introduction:** <https://developers.google.com/search/docs/crawling-indexing/robots/intro>  
    Initial finding: explanatory documentation on crawler behavior and limits of robots.txt.
11. **Indonesia Law No. 27 of 2022 on Personal Data Protection — official legal reference:** <https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/>  
    Initial finding: relevant legal reference for personal-data handling; evaluate applicability with appropriate care.
12. **Tech in Asia Jobs help center:** <https://help.techinasia.com/support/home>  
    Initial finding: relevant job platform and help resources; current automated access and content reuse terms must be independently verified.

**Research status warning:** The references above do not constitute blanket authorization to collect or republish any source's content. Every connector requires its own current review, evidence, and explicit eligibility decision.
