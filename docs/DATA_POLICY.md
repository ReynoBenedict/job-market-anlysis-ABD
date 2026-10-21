# Data policy: sources, permissions, retention, attribution

This is an engineering policy, not legal advice.

## Principles
1. Viewable ≠ collectable ≠ storable ≠ republishable. Each is decided per source and
   recorded in the registry with evidence and a review date (`docs/RESEARCH_SOURCES.md`).
2. Only `APPROVED` or `APPROVED_WITH_CONDITIONS` sources can run, and network sources
   additionally need a review younger than 365 days (`ingestion/policy.py`).
3. Never: CAPTCHA solving, stealth browsers, proxy rotation, login automation, scraping
   personal profiles or applicant data, or continuing after a denial signal.

## Current sources
| Source | Status | Use |
|---|---|---|
| `glints-snapshot-2026-06` | APPROVED_WITH_CONDITIONS | Historical academic snapshot imported read-only at the project owner's instruction (2026-10-17). |
| `glints` (live) | BLOCKED | Terms prohibit scraping/data extraction without written consent. Not collected. |
| `commoncrawl-jobposting` | APPROVED_WITH_CONDITIONS | Archived `.id` pages with schema.org JobPosting markup, read from Common Crawl's public archive (docs/LAKE.md, ADR-0015). |
| 26 other researched sources | see registry | None activated; see `/sumber-data` and the research matrix. |

The registry status `APPROVED_WITH_CONDITIONS` on the two ingested datasets is an internal
eligibility gate. It records *our* decision to use them under conditions; **neither rests
on a permission from the owner of the content** (Glints, or the 22 publisher sites). Public
wording must not call them "approved" (see "Public labels" below).

**Provenance of the snapshot:** the file `data/raw/glints_jobs.csv` (1,133 listings, no
per-listing URL) was produced by the earlier academic project's Selenium scraper of
glints.com search pages (`legacy/academic_pipeline/scrapers/glints_scraper.py`). Glints'
terms, as recorded in TALENTSCOPE_SRS.md §4.1, prohibit screen scraping and similar
extraction without prior written consent; the terms page itself returned HTTP 403 on
2026-10-17 and again on 2026-10-18, so the clause has not been re-read. No permission
from Glints is on record. The snapshot is used because the project owner instructed it
(2026-10-17), not because Glints agreed.

**Conditions on the snapshot:** labelled historical everywhere; attributed to Glints; no
refresh; no claim that listings are open; links to the original are not fabricated.
**Before any public deployment**, the right to republish the snapshot's listing
details should be confirmed with Glints, or the public site should be limited to
aggregate statistics. Until then, treat the deployment as a local/portfolio demo.

**Conditions on the Common Crawl archive:** Common Crawl's terms licence use of the
archive but leave crawled content subject to each site's own terms. Therefore:
- sites whose terms prohibit extraction, require permission, or have not been reviewed
  are excluded at discovery *and* dropped again at every silver rebuild
  (`backend/talentscope/lake/domains.py`);
- only the structured JobPosting fields are kept; page HTML is never stored, and the app
  never shows descriptions from archived pages (they are used only for skill counts);
- every vacancy links to its original page and is labelled as archived, with the capture
  dates; nothing is described as currently open;
- collection stays at ≤2 requests/s and stops on HTTP 403/429;
- the purpose is aggregate labour-market analytics. Republishing individual listings
  publicly needs the same review as the Glints snapshot (below).

**Per-site review:** every site that contributes archived pages is reviewed individually
(terms, disclaimer, robots.txt, provenance); only sites with a usable status are used,
others are excluded by default (docs/data-engineering/DOMAIN_REVIEW.md). Sites that say
they copy vacancies from elsewhere are marked second-hand on the job page.

On 2026-10-18 the 6,174 archive vacancies came from 22 publisher sites: 21 whose terms are
silent on reuse and 1 (kusnendar.web.id, 2 vacancies) that allows copying with a backlink.
No site grants republication explicitly; 1,221 vacancies (19.8%) come from sites that say
they aggregate others' listings (DOMAIN_REVIEW.md).

**Site owner opt-out:** add the domain to `EXCLUDED_DOMAINS`, run `talentscope lake run`,
and remove its published jobs (docs/LAKE.md "Recovery"). Licensed feeds loaded with
`talentscope lake import-jsonl` keep the licence's own conditions, recorded on their
registry entry before the import is allowed.

## Terms the UI keeps apart

| Concept | Meaning | Indonesian label | Count on 2026-10-18 |
|---|---|---|---|
| Ingestion dataset (collection mechanism) | How records entered TalentScope: the Common Crawl archive or the one-time Glints snapshot. This is a registry `sources` row. | **cara pengumpulan** / **kumpulan data** ("arsip web Common Crawl", "snapshot sekali ambil") | 2 |
| Publisher site | The domain that published the job page that was archived. | **situs asal** / **situs penayang** | 22 (archive); the snapshot's publisher is Glints itself |
| Aggregator | A publisher site that says it republishes listings from other sites; its records are second-hand. | **situs agregator (menayangkan ulang lowongan dari sumber lain)** | 8 of the 22 sites, 1,221 vacancies |
| Employer | The `hiringOrganization` / company named in the listing. | **pemberi kerja** / **perusahaan** | 3,827 distinct names (archive, exact match), 917 (snapshot) |
| Licensed / authorized source | A source whose owner has granted collection and display rights in writing, or whose licence grants them. | **sumber berizin** / **sumber berlisensi** | 0 vacancy sources; 1 aggregate dataset (Balikpapan, public domain), not ingested |
| Researched source | Any source evaluated in RESEARCH_SOURCES.md / SOURCE_ASSESSMENT.md, used or not. | **sumber yang sudah diperiksa** | 29 registry rows (27 not used) |

Counting rule: never write "N sumber" on its own. Write "dari 2 kumpulan data (arsip web
dan satu snapshot)" or "dari 22 situs asal", and never add the two numbers together.

## Public labels for the ingested datasets

The generic label for `APPROVED_WITH_CONDITIONS` ("Disetujui dengan syarat") implies that a
rights holder approved the use. For the two ingested datasets that is not true, so the
public pages should show these labels instead (recommended; the UI and registry are not
owned by this document):

| Dataset | Public label | One-sentence condition |
|---|---|---|
| `commoncrawl-jobposting` | **Dipakai untuk riset, dengan syarat** | Arsip Common Crawl boleh dipakai dengan lisensi terbatas, tetapi isi halamannya tetap tunduk pada ketentuan situs asal; karena itu kami hanya memakai situs yang sudah ditinjau dan tidak melarang, hanya menampilkan data ringkas lowongan beserta tautan ke situs asal, dan menghapus situs yang meminta keluar. |
| `glints-snapshot-2026-06` | **Data historis — hak tayang ulang belum dipastikan** | Snapshot ini dikumpulkan sekali untuk proyek akademik pada Juni 2026 dan dipakai atas keputusan pemilik proyek, bukan atas izin Glints; sebelum situs ini dibuka untuk umum, hak menampilkan ulang lowongannya harus dikonfirmasi ke Glints atau tampilannya dibatasi pada angka ringkasan. |
| `glints` (live site) | **Tidak dipakai: ketentuan situs melarang** | Kami tidak mengambil data dari situs Glints; ketentuannya (tercatat di SRS, belum bisa dibaca ulang karena halaman menolak akses) melarang pengambilan data otomatis tanpa izin tertulis. |
| `balikpapan-opendata-vacancies` | **Boleh dipakai (domain publik), belum diimpor** | Datanya berlisensi domain publik dan hanya berisi angka ringkasan, bukan lowongan. |

Unresolved, not decided here (not legal advice):
1. Whether republishing individual snapshot listings (title, company, city, salary, tags)
   publicly requires Glints' permission, given how the snapshot was collected.
2. Whether silent terms on the 21 publisher sites allow public display of their listings'
   structured fields; Common Crawl §3 itself recommends counsel before any use.
3. Whether Indonesian copyright or database protection covers the factual fields kept.
4. Whether the aggregator sites had rights to the listings they republished.

## Changing a source's status
```bash
talentscope sources set-status <source> APPROVED_WITH_CONDITIONS \
  --reason "Written consent from <org> dated <date>; fields: title, location, URL" \
  --evidence-url "<link to stored permission record>" --actor "<name>"
```
Every change is written to `audit_events`. The admin web UI cannot change eligibility.

## Retention
- Lake bronze keeps extracted JobPosting objects with provenance (crawl, WARC file and
  offset, capture time, digest); it is local and git-ignored. Synthetic benchmark data
  lives separately under `lake/synthetic/` and never enters silver, gold, or the app.
- Raw files are never modified by TalentScope. Only permitted fields are kept in
  `source_records.raw_fields`; no HTML pages, images, cookies, or attachments.
- Descriptions are stored in the app database only when a source's permission covers
  them (2026-10-18: 0 of 7,307 jobs have one). Archived descriptions remain in the local,
  git-ignored lake for skill counting and are never served (see the archive conditions
  above); no source grants a right to them.
- Listings not seen again are kept but labelled by freshness; they are not presented as open.

## Removal and correction requests
Open an issue in the project repository with the TalentScope job link and the reason.
A verified request from a source owner leads to: pausing the source
(`talentscope sources pause`), deleting the affected rows (manual SQL on `jobs` cascades
to `source_records`), recording an audit event, and replying with what was done.
TalentScope cannot delete data from third-party systems.

## Personal data
TalentScope stores no data about job seekers: there are no accounts, and saved jobs stay
in the browser. Job listings may name a company but contain no personal contact data in
the current snapshot. API request logs contain method, path, status, and duration, not
client identities.
