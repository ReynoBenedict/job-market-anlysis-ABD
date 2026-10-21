# Skill extraction review (dictionary `skills-2026.10.1`)

**What was measured:** precision of skill *mentions* only. Recall (skills the dictionary
misses) was not measured.

**Sample:** 60 mentions drawn with `random.seed(20261017)` from 4,575 dictionary matches
in the descriptions of the Common Crawl bronze captures available on 2026-10-17. Each
mention was shown with ~70 characters of context on either side.

**Reviewer:** the AI coding assistant that built the pipeline, **not a human annotator**.
Treat the figure as an indicative engineering check, not a validated benchmark.

**Criterion:** correct when the matched phrase refers to the named skill as something the
job asks for, prefers, or involves. Fields of study (e.g. "S1 Bahasa Inggris") were
counted as *incorrect*, because they name a degree, not a skill.

## Result

| | Count |
|---|---|
| Correct | 54 |
| Incorrect | 6 |
| **Precision** | **90% (54/60)** |

| Item | Skill | Why it was wrong |
|---|---|---|
| 16 | English | "S1 di bidang Bahasa Inggris": a field of study |
| 28 | Communication | "Sarjana (…/Komunikasi/…)": a field of study |
| 35 | English | "Bahasa Inggris" as a school subject in a list of teaching posts |
| 37 | Communication | "jaringan komunikasi": a communications network |
| 47 | Accounting | "Pendidikan D3 Akuntansi": a field of study |
| 49 | Google Workspace | "spreadsheet" used generically for Excel |

Correct mentions spanned Microsoft Office/Excel/Word/PowerPoint, communication,
leadership, negotiation, teamwork, driving licences (SIM A/B1/C), Canva, Adobe tools,
AutoCAD, SQL, SEO, social media, data analysis, and Microsoft Azure.

## Changes made after the review

- `skills-2026.10.2`: "Communication" no longer matches "jaringan komunikasi";
  "spreadsheet" alone no longer maps to Google Workspace.
- `skills-2026.10.3`: for skills that double as degree majors (English, Communication,
  Accounting, Taxation, Statistics), a match preceded in the same clause by a degree
  marker (S1/D3/sarjana/jurusan/prodi/bidang studi/mata pelajaran/lulusan/pendidikan) is
  ignored. This addresses items 16, 28, 35, and 47.
- Regression tests: `tests/unit/test_lake_parsing.py::test_skill_patterns_avoid_ambiguous_matches`.

All six reviewed errors are addressed by these rules, but **precision of the revised
dictionary has not been re-measured** on a fresh sample; the 90% figure applies to
`skills-2026.10.1`. The degree rule can also hide a genuine skill that happens to follow
a degree marker in the same clause.
