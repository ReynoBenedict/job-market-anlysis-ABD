# Archive domain review (2026-10-18)

Every site whose archived pages contribute vacancies is reviewed individually, because
the Common Crawl licence covers the archive, not the sites' content. The decisions are
enforced in code (`backend/talentscope/lake/domain_reviews.py`): silver uses only archived
pages from sites with a usable status; any other site, including one never reviewed, is
kept in bronze but excluded (default deny). Counts per status are in `lake/gold/report.json`
→ `domain_governance`.

**Method.** Read-only review on 2026-10-18 of each site's homepage, terms / disclaimer /
about pages, and robots.txt (no listing pages fetched in bulk). Quotes are short excerpts
as returned by the fetch tool; re-check them on the live page before relying on them
legally. Not legal advice.

## Summary

- No site grants an explicit reuse licence. No site prohibits scraping in its terms, and
  no robots.txt has rules aimed at AI crawlers or CCBot.
- **One site explicitly prohibits reuse** (groove.co.id): excluded.
- Several sites declare that they **aggregate vacancies from other sources**; their records
  are second-hand and the app says so on the job page.
- Silent terms ("no statement") are used only under research conditions: non-commercial,
  structured fields only, no descriptions shown, attribution and a link to the original
  page, removal on request. This is a residual risk, stated here and in DATA_POLICY.md.

| Status | Effect | Sites (archive observations) |
|---|---|---|
| no_statement | used | lokeraceh.id, lokerbekasi.id, lowongankerjacirebon.id, lokerbogor.co.id (one template/operator); gaji.co.id†; aksesinfo.my.id; lokerbekasi.my.id†; mediaanalisindonesia.co.id; bisakerja.id; lokerbandung.or.id; sportsmatters.id†; inaba.ac.id; jogjaterkini.id; lokersamarinda.biz.id†; bursaloker.id; lokerjakarta.id; openkerja.id†; sokacoke.id†; lokerjogja.id; promag.id†; pixelninja.id; pekerjamigran.id (all rejected: overseas jobs) |
| permits_with_conditions | used (we link back) | kusnendar.web.id† ("dilarang … copy paste … tanpa memberikan backlink") |
| prohibits | excluded | groove.co.id ("tidak diperbolehkan untuk menyalin, mendistribusikan … tanpa izin tertulis") |
| excluded_quality | excluded | bukaloker.web.id† (admits using copyrighted material without permission; Indeed-derived), generalist.biz.id (scam-pattern listings, injected gambling spam) |
| unreadable | excluded until verified | aloka.id (redirects to an unrelated, likely hijacked domain), tempatbelajar.my.id (DNS), infobumn.web.id (connection refused), lorong.my.id (TLS), pressrelease.co.id (DNS), jac-recruitment.co.id (terms truncated; robots.txt disallows deep job paths) |
| unreviewed | excluded | lokermu.id (all its records were already invalid: the site name is used as the employer) |

† self-declared aggregator ("dari berbagai sumber", "portal agregator", "dikumpulkan dari
beberapa sumber publik"): second-hand provenance.

Measured effect of the review on the lake (rebuild of 2026-10-18): 2,045 observations from
unreadable sites, 170 from quality-excluded sites, 19 from the prohibiting site, and 103
from the unreviewed site no longer reach silver; canonical vacancies went from 6,582 to
6,186 (together with the campaign-rule refinement in LAKE.md); the audit fix for SEO
campaigns (no date split) brought it to 6,174.

## Contributing sites in the app database (2026-10-18)

Read-only query on `jobs` (host of `source_url`, `primary_source_id = 'commoncrawl-jobposting'`):
**22 publisher sites** supply the 6,174 archive vacancies (republished 2026-10-18 09:40 WIB). All 22 are in `DOMAIN_REVIEWS`
with a usable status (the 23rd usable entry, pekerjamigran.id, contributes 0 because its
listings are abroad). Every archive vacancy has a `source_url`; no snapshot listing has one.

| Site | Vacancies | Self-declared aggregator |
|---|---:|---|
| lokeraceh.id | 1,582 | |
| lokerbekasi.id | 1,266 | |
| lowongankerjacirebon.id | 1,254 | |
| gaji.co.id | 739 | yes |
| aksesinfo.my.id | 515 | |
| lokerbekasi.my.id | 418 | yes |
| lokerbogor.co.id | 132 | |
| mediaanalisindonesia.co.id | 128 | |
| sportsmatters.id | 57 | yes |
| bisakerja.id | 43 | |
| lokerbandung.or.id | 23 | |
| pusatkarir.inaba.ac.id | 3 | |
| jogjaterkini.id, kusnendar.web.id†, bursaloker.id, lokersamarinda.biz.id† | 2 each | † yes |
| promag.id†, pixelninja.id, openkerja.id†, lokerjakarta.id, sokacoke.id†, lokerjogja.id | 1 each | † yes |

- Top 10 sites: 6,134 of 6,174 (99.4%). Self-declared aggregators: 1,221 (19.8%).
- 21 of the 22 sites are `no_statement` (terms silent on reuse); only kusnendar.web.id
  (2 vacancies) states a condition we meet. **No contributing site grants reuse or
  republication explicitly.** Public wording must therefore say "used for research under
  conditions", never "approved" or "permitted by the site".
- Terms: a *publisher site* is where the archived page was published; an *aggregator* is a
  publisher site that republishes other sites' listings; the *employer* is the
  `hiringOrganization` named in the listing (3,827 distinct `company_name` strings in the
  archive and 917 in the snapshot by exact match in the database; DATA_INVENTORY.md reports
  3,674 archive employers, presumably after normalization, which is not documented here). The app has 2 *ingestion datasets*, 22 publisher sites and thousands
  of employers; see DATA_POLICY.md "Terms the UI keeps apart".

## Live re-checking of listings

No site's terms address automated access, so none explicitly permits a periodic "does
this listing page still exist" check, and none forbids it. Robots.txt on the main sites
allows all agents. Because the terms are silent and the content is often second-hand, the
app does **not** re-check listings live; no listing is labelled "verified active". A
re-check would need, per site, either explicit permission or an owner-approved method
(see SOURCE_ASSESSMENT.md).

## Adding or changing a review

Add the domain with its status and a short evidence note to `DOMAIN_REVIEWS`, record the
evidence here, run `talentscope lake run --publish`. Opt-out: set the status to
`prohibits` (or add the domain to `domains.EXCLUDED_DOMAINS`) and republish; publishing
retires the site's app records.
