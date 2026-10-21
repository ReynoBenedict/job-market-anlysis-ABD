# Interaction matrix

Every visible interactive element per route, checked against the implementation and the dev API
(`http://localhost:8011`, working-tree backend) through the dev web server (`http://localhost:3002`).
Audit date: 2026-10-18. Expected values were read from the API at check time; no dataset numbers
are hard-coded in tests.

Legend: **Status** `OK` = verified correct; `FIXED` = defect found and fixed in this pass;
`OPEN` = defect found, owned elsewhere (see recommendation). Severity: High / Medium / Low.
Evidence: `E2E <name>` = Playwright journey in `frontend/e2e/journeys.spec.ts`; `unit` =
`frontend/src/lib/lib.test.ts` or `frontend/src/components/components.test.tsx`; `probe` = scripted
browser/API check run during the audit.

## Global (header, footer, error boundary)

| Element | Expected | Actual | Status | Evidence |
|---|---|---|---|---|
| Logo link | Goes to `/` | as expected | OK | layout tests |
| Main nav links (Cari Lowongan, Gaji, Pasar Kerja, Keterampilan, Tentang Data) | Navigate; active section highlighted incl. `/pasar`, `/metodologi`, `/lowongan/<id>` | as expected | OK | unit (`isActiveSection`), E2E journey 9 |
| Mobile menu button | Opens menu; closes after choosing a link | as expected | OK | E2E journey 9 (@mobile) |
| "Tersimpan" header link + count | Count = saved jobs in this browser; updates on save/remove and across tabs (`storage` event) | as expected | OK | E2E journey 4, E |
| Skip link `#konten` | Jumps to main | present, target exists | OK | code |
| Footer links (7) | All resolve (200); `/metodologi#koreksi` anchor exists | as expected | OK | E2E journey J |
| `(app)/error.tsx` "Coba lagi" | Resets the boundary for unexpected render errors | `reset()` wired; expected API failures are handled inline instead | OK | code |

## `/lowongan` (search)

| Element | Expected | Actual (before) | Status | Severity | Fix | Regression test |
|---|---|---|---|---|---|---|
| Search box + "Cari Lowongan" | Trimmed keyword in `q`, page reset, history entry; case-insensitive; multi-word AND; `% _ \ ' "` literal; unicode | as expected (API escapes LIKE wildcards) | OK | – | – | E2E journey A, A2, 1 |
| Search box `maxLength` | 100 = API limit | 100 | OK | – | – | E2E journey A2 |
| `q` > 100 chars via edited URL | Explained | "Parameter pencarian tidak valid" alert | OK | – | – | E2E journey A2 |
| Empty search submit with `sort=relevance` | Removes keyword and the keyword-only sort | sort=relevance stayed in the URL; select showed an option not in its list | FIXED | Low | `withoutKeyword()` in `lib/filters.ts`, used by search bar and keyword chip | unit, E2E journey I |
| Filter checkboxes (status, provinsi, kota, bidang, jenis, pengaturan, pengalaman, pendidikan, sumber) | OR within a group, AND across groups; counts equal `GET /jobs` with the same params; page reset | as expected; option counts equal `/jobs?<key>=<value>` for each group | OK | – | – | E2E journey B, 2; probe (first 5 options of every group) |
| Option counts next to checkboxes | Clear what they count | They are dataset-wide (`/filters` takes no params) but read like faceted counts for the current result | FIXED | Low | Caption "Angka di samping pilihan dihitung dari seluruh data, bukan dari hasil saat ini." | – |
| "Tampilkan semua (n)" | Expands; selected options stay visible when collapsed | as expected | OK | – | – | code |
| Salary min/max + "Terapkan" | Min only, max only, decimal comma; invalid text and min>max rejected client-side | as expected, **but** values above Rp 10 miliar and `1e3` were accepted and the API answered 422 (whole page became an error) | FIXED | Low | `millionsToRupiah` accepts plain decimals ≤ 10.000 juta only; message names the range | unit, E2E journey B2 |
| Salary inputs after chip removal / Back / "Hapus semua filter" | Inputs show the URL's bounds | Inputs kept the old value (state initialised once) — showed "5" while no salary filter was active | FIXED | Medium | `SalaryFilter` remounts when `salary_min`/`salary_max` change (`key`) | E2E journey B2 |
| "Hanya lowongan yang mencantumkan gaji" | `salary_disclosed=true` | as expected | OK | – | – | E2E journey F (drill-down) |
| Active-filter chips | Remove only that value; others kept | as expected | OK | – | – | E2E journey B, 2 |
| "Hapus semua filter" | Removes filters, keeps keyword | also dropped `sort` (and on `/gaji` the comparison tab `by`) | FIXED | Low | `clearFilters()` keeps `q`, `sort`, `by` | unit, E2E journey B, F |
| Sort select | Changes `sort`, resets page; "Paling relevan" only with keyword | as expected; unknown `sort=` in URL made the page a 422 error | FIXED | Low | Unknown sort falls back to default before calling the API; select shows the fallback | E2E journey I |
| Pagination | Keeps filters/sort; `rel=prev/next`; page beyond last explained | as expected; `page` > 10 000 returned 422 | FIXED | Low | page clamped to the API maximum → "Halaman ini tidak ada" | E2E journey I |
| Job card title link | Opens detail with `kembali=<results query>` | as expected | OK | – | – | E2E journey 3, C2 |
| Card bookmark button | Toggle, `aria-pressed`, header count, error when storage blocked | as expected | OK | – | – | E2E journey 4, E2; unit |
| Mobile "Filter" toggle + "Lihat n hasil" | Opens/closes panel | as expected | OK | – | – | E2E journey 9 |
| Error state "Coba lagi" | Outage: retry the same search. Invalid params: reset | Always went to bare `/lowongan`, losing the user's search after an outage | FIXED | Medium | `retryHref()` in `lib/api.ts` (also `/gaji`, `/pasar`) | unit; `stack.spec.ts` assertion (needs local-stack run) |
| Empty state "Mulai pencarian baru" | Visible when filters/keyword active | as expected | OK | – | – | E2E journey 8 |

## URL state and history

| Scenario | Expected | Actual | Status | Evidence |
|---|---|---|---|---|
| Direct open / reload of a filtered URL | Same controls and counts | as expected | OK | E2E journey C |
| Back/Forward after adding/removing filters | URL, checkboxes, counts follow | as expected (an early probe suggested otherwise; it read the page before the router re-rendered — re-checked with waits and in E2E, behaviour is correct) | OK | E2E journey C |
| History entries | One `push` per deliberate change (filter, chip, sort, search); no entry for typing | `history.length` +1 per change | OK | E2E journey C |
| Back after a new search | Box shows the previous keyword | as expected (`SearchBar` keyed by `q`) | OK | E2E journey C |
| Detail → "Kembali ke hasil pencarian" | Restores keyword, filters, sort, page | as expected | OK | E2E journey C2, 3 |
| `kembali` abuse (`//evil`, `https://…`, `javascript:`, CRLF, `\\host`) | Link never leaves `/lowongan` | Already safe (fixed `/lowongan?` prefix), but arbitrary text was echoed into the href | FIXED (hardening) | `resultsHref()` re-parses `kembali` and keeps only known search params | unit, E2E journey C2 |
| `/gaji` tab links, filter changes, chip removal | Keep `by` | as expected; only "Hapus semua filter" dropped it (fixed above) | OK/FIXED | E2E journey F |

## `/lowongan/<id>` (detail) and not-found

| Element / case | Expected | Actual (before) | Status | Severity | Fix / evidence |
|---|---|---|---|---|---|
| Unknown UUID, malformed id (`not-a-uuid`, `12345`, SQL-ish) | HTTP 404 + not-found page | as expected (proxy) | OK | – | E2E journey 8, D |
| Saved job whose record is gone | Understandable way out | Generic 404 only; the job stayed in the saved list with no hint | FIXED | Medium | `MissingSavedJobNotice` on `lowongan/tidak-ditemukan` and new `lowongan/[id]/not-found.tsx`: names the saved job, "Hapus dari tersimpan", link back. E2E journey E, unit |
| "Buka halaman asli" | Only for http(s) URLs; `target=_blank rel=noopener noreferrer nofollow` | as expected | OK | – | E2E journey 3 |
| Missing source URL | No button; explanation shown | as expected | OK | – | E2E journey D |
| Dates: Tanggal tayang / Batas lamaran / Diarsipkan–Dikumpulkan / Diperiksa langsung | Distinct, honest | Missing deadline said "Tidak dicantumkan" — false once template deadlines are nulled by the pipeline | FIXED | Low | "Tidak diketahui" + note "Sumber tidak mencantumkan batas lamaran yang dapat dipakai." E2E journey D |
| Status notice | Expired only with a past deadline; otherwise "Belum tentu masih dibuka" | as expected | OK | – | E2E journey 3 |
| Salary block | Implausible disclosed salary (e.g. Rp 2 – Rp 897, `comparable=false`) not shown as a salary | Shown as "Rp 2 – Rp 897 per bulan" | FIXED | Medium | `isImplausibleSalary()` in `components/jobs/salary.tsx`; card says "Angka gaji di sumber tidak wajar". unit, E2E journey D2 |
| Data-quality notes | Plain-language text per flag | as expected; unknown flags fall back to the code | OK | – | code |
| "Detail teknis" `<details>` | Collapsed by default | as expected | OK | – | code |
| Save button (labelled) | Toggle "Simpan"/"Tersimpan" | as expected | OK | – | E2E journey K |
| Error-state retry link | Encodes the id | id was not URL-encoded | FIXED | Low | `encodeURIComponent(id)` |

## `/tersimpan`

| Element | Expected | Actual (before) | Status | Evidence |
|---|---|---|---|---|
| Saved list, persistence across reload | as stored | as expected | OK | E2E journey 4 |
| Remove (trash) per job | Removes one | as expected | OK | E2E journey 4 |
| "Hapus semua" → "Ya, hapus" / "Batal" | Confirm step | as expected | OK | code |
| Storage blocked | Explained | Showed "Belum ada lowongan tersimpan" (misleading); write failures in this page were silent | FIXED (Low) | `useSavedJobsAvailable()`; blocked-storage empty state; failure message on remove/clear. E2E journey E2, unit |

## `/gaji`

| Element | Expected | Actual | Status | Evidence |
|---|---|---|---|---|
| Headline median, p25/p75, "Dihitung dari n" | Equal `/salaries/overview` for the same filters | as expected | OK | E2E journey 5, F |
| Excluded implausible salaries | Disclosed | Not mentioned | FIXED | Sentence using `excluded_implausible` / `min_monthly_midpoint` |
| Comparison tabs (Bidang, Provinsi, Pengalaman, Jenis pekerjaan, Pendidikan) | Rows, labels, `n` equal `/salaries/compare?by=` | as expected | OK | E2E journey F |
| Sparse groups | No statistics below minimum | as expected | OK | E2E journey 5 |
| Group label link (drill-down) | Opens matching search | as expected but leaked `by=` into the search URL | FIXED (Low) | `jobsHref` drops `by`; E2E journey F asserts total equals API and ≥ group `n` |
| Histogram bars vs "Tampilkan sebagai tabel" | Same counts as API | as expected | OK | E2E journey F |
| "Apa arti angka ini?" `<details>`, "Cara perhitungan" link | Work | as expected | OK | code |

## `/ringkasan` and `/pasar`

| Element | Expected | Actual | Status | Evidence |
|---|---|---|---|---|
| Stat tiles (total, % with salary, median) | Equal `/market/overview`, `/salaries/overview` | as expected | OK | E2E journey G |
| Bar lists (bidang, provinsi, kota, jenis, pengaturan, pengalaman, pendidikan) | Count and share equal breakdown API; bar link total equals bar count | as expected (probe: every top-4 row of every dimension, filtered and unfiltered) | OK | E2E journey G, 6; probe |
| "Tidak dicantumkan" province / company rows | Not linkable | as expected | OK | code |
| `/pasar` filters, chips, clear-all, "Lihat daftar lowongannya" | Same as search | as expected | OK | E2E journey 6 |
| Invalid enum in URL (`role_family=NOPE`) | Explained | as expected | OK | E2E journey I |

## `/keterampilan`, `/sumber-data`, `/metodologi` (not owned by this workstream)

| Element | Expected | Actual | Status | Severity |
|---|---|---|---|---|
| Category links | Switch tags; `aria-current` | as expected | OK | E2E journey H |
| Tag bar link | Opens the listings counted for the tag | Free-text `q=<tag>` over title/company/location/tags in **all** sources and drops the selected role family: e.g. "Customer Service" tag 20 vs search 109, "Accounting" 18 vs 195 | OPEN | Medium |
| Source `<details>` groups, methodology links, `#teknis` details | Work | as expected | OK | E2E journey 7 |

## Runtime quality

E2E journey J visits every public route plus a job detail and fails on any console error, page
error, failed request (other than aborted prefetches) or HTTP ≥ 400; it also waits for no
`[aria-busy=true]` (no indefinite loading). Result on the dev server: **no problems recorded**.
The only 404 seen in the audit was the intentional 404 document for a missing job.

## Open items / recommendations for other owners

1. **Keterampilan tag links (worker 2 + backend).** Exact fix needs an API filter on source tags
   (e.g. `tag=` matching `source_tags` exactly). Until then, in `keterampilan/page.tsx` build the
   link with the selected role family and the tag source, e.g.
   `` `/lowongan?q=${encodeURIComponent(tag.value)}&source=glints-snapshot-2026-06${selectedRole ? `&role_family=${selectedRole}` : ""}` ``,
   and label it as a keyword search. Tracked by `test.fixme("journey H2 …")`.
2. **`ErrorState` (worker 2, `components/ui.tsx`).** Add an optional `retryLabel`; for invalid
   parameters the link resets the search, so "Atur ulang pencarian" is more accurate than "Coba lagi".
3. **`NotFoundContent` (worker 2).** Accept `children` so page-specific notices (the saved-job
   notice) sit inside the centred block instead of below it.
