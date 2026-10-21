# ML evaluation: K-Means clustering of job titles

Measurements: `docs/ml/clustering_results.json`, produced by
`python analytics/evaluate_title_clustering.py` (PySpark 3.5.1 local mode, scikit-learn
1.6.1 for ARI/NMI, Python 3.10, run 2026-10-17, ~2.5 minutes). Input:
`data/raw/glints_jobs.csv` (1,133 titles).

## 1. Baseline reproduction

The academic configuration (`legacy/academic_pipeline/spark_jobs/mllib_demo.py`):
lower-case → replace `[^a-z\s]` with a space → `Tokenizer` (splits on single spaces) →
English + 14 domain stopwords → `HashingTF(1024)` → `IDF(minDocFreq=3)` →
`KMeans(k=3, seed=42, maxIter=50, k-means||)`; silhouette with squared Euclidean distance.

| | Report | Reproduced |
|---|---|---|
| Silhouette (k = 3, seed 42) | 0.0351 | **0.0351** |
| Cluster sizes | 947 / 63 / 123 | **947 / 123 / 63** |

The committed `clustered_jobs.csv` labels were also reproduced exactly during the audit.
**Reproducibility caveat:** the result holds only with the data in a single Spark
partition (as `spark.read.csv` produces for this small file). The same seed on a
DataFrame spread across partitions gave silhouette 0.3149 and sizes 991/128/14, because
k-means|| initialisation depends on partition layout.

## 2. Defects in the original preprocessing

1. **Empty tokens.** Punctuation becomes spaces, and `Tokenizer` splits on single spaces,
   so titles such as "C++ Software Engineer" or "Finance, Accounting & Tax" contain the
   token `""`. 220 of 1,133 titles (19%) are affected, and **all 123 members of one of
   the three clusters** carry the artifact (audit cross-tabulation). That cluster groups
   titles by punctuation, not by occupation; it contains "C++ Software Engineer" and
   "Backend Developer (.NET)" alongside finance titles.
2. **Destroyed technical terms:** "C++" → "c", ".NET" → "net", "Node.js" → "node js".
3. **Occupation words removed** as stopwords ("officer", "specialist", "staff").
4. **Distance mismatch:** unnormalised TF-IDF with squared Euclidean distance.

## 3. Experiment

Two configurations × k ∈ {3, 4, 5, 6, 8, 10, 15} × seeds {42, 1, 7, 123, 2024}.
*Corrected* = `RegexTokenizer` splitting on runs of non-`[a-z0-9+#]` (no empty tokens,
keeps c++/c#), stopwords without occupation words but with seniority/location noise,
`IDF(minDocFreq=2)`, L2 normalisation (cosine geometry).

Metrics: silhouette (squared Euclidean, and cosine); **seed stability** = mean pairwise
adjusted Rand index (ARI) between the five seeds (1 = identical partitions, 0 = chance);
share of the largest cluster; NMI against TalentScope's rule-based role families
(a weak reference, not ground truth).

| Config | k | Sil. (sq. Eucl.) | Sil. (cosine), mean ± sd | Seed ARI mean (min) | Largest cluster | NMI vs. role families |
|---|---|---|---|---|---|---|
| original | 3 | -0.007 | 0.066 ± 0.026 | 0.26 (-0.09) | 80% | 0.16 |
| original | 4 | 0.030 | 0.063 ± 0.013 | 0.10 (-0.10) | 80% | 0.18 |
| original | 5 | -0.043 | 0.054 ± 0.032 | 0.08 (-0.08) | 78% | 0.20 |
| original | 6 | -0.044 | 0.072 ± 0.043 | 0.15 (-0.10) | 74% | 0.21 |
| original | 8 | 0.061 | 0.103 ± 0.021 | 0.25 (0.03) | 68% | 0.29 |
| original | 10 | 0.057 | 0.093 ± 0.019 | 0.32 (0.16) | 68% | 0.29 |
| original | 15 | 0.095 | 0.155 ± 0.029 | 0.23 (0.02) | 55% | 0.40 |
| corrected | 3 | 0.072 | 0.071 ± 0.020 | 0.17 (-0.08) | 78% | 0.22 |
| corrected | 4 | 0.085 | 0.084 ± 0.028 | 0.09 (-0.10) | 74% | 0.27 |
| corrected | 5 | 0.109 | 0.108 ± 0.038 | 0.16 (-0.01) | 65% | 0.34 |
| corrected | 6 | 0.112 | 0.111 ± 0.017 | 0.08 (-0.18) | 67% | 0.35 |
| corrected | 8 | 0.136 | 0.135 ± 0.016 | 0.09 (-0.04) | 62% | 0.40 |
| corrected | 10 | 0.190 | 0.189 ± 0.030 | 0.13 (0.03) | 52% | 0.49 |
| corrected | 15 | 0.264 | 0.264 ± 0.019 | 0.23 (0.07) | 35% | 0.56 |

At k = 3 with the original pipeline, the five seeds give silhouettes from −0.067 to
0.065, and the largest cluster always holds 73–84% of jobs.

## 4. Interpretation

- **0.0351 is not evidence of segments.** A silhouette near zero means points are about as
  close to other clusters as to their own. Across seeds, the original k = 3 scores range
  from negative to 0.065; 0.0351 is one draw.
- **The fix helps cohesion but not stability.** Corrected preprocessing raises cosine
  silhouette at every k (e.g. 0.19 vs 0.09 at k = 10) and agreement with the role
  taxonomy (NMI 0.49 vs 0.29). However, seed-to-seed agreement stays low (mean ARI
  ≤ 0.23, some pairs below 0): different seeds produce substantially different groupings.
- **Silhouette rises with k** on short, sparse title vectors partly mechanically, so the
  higher scores at k = 15 do not by themselves indicate natural structure.
- Not done: human review of cluster coherence, embedding representations. The data has
  titles only; an embedding model was not justified for a feature that is not shipped.

## 5. Decision

Clustering is **not** used in the product. Occupation groupings use the rule-based,
versioned role taxonomy (`backend/talentscope/normalization/role_family.py`), which is
deterministic, testable, and explainable per job. 31 of 1,133 titles (2.7%) are not
matched by any rule at taxonomy version 2026.10.1 and are shown as "Lainnya / Belum
terklasifikasi". A manual spot check of 40 random titles found the assignments sensible,
but **no formal precision measurement has been done**. That is the next evaluation step.

Clustering could be revisited for exploratory analysis when job descriptions from
permitted sources are available, with a reviewed sample and stability reported alongside
any score.

## 6. Role taxonomy review (2026-10-17)

The rule-based taxonomy replaced K-Means. Coverage (share of titles assigned a family) and
precision (share of assigned titles in the right family) are measured separately,
because high coverage alone says nothing about correctness.

**Reviewer:** the AI coding assistant that wrote the rules, **not a human annotator**.
Random samples of 60 app jobs (both sources), drawn with `setseed()` in PostgreSQL.

| Taxonomy | Sample seed | Coverage | Precision | Errors |
|---|---|---|---|---|
| `2026.10.2` | 0.2026 | 51/60 = 85% | 47/51 = 92% | "SPG (Sales Promotion Girl)" → Desain (matched "motion"); "Relation Officer Mobile" → Software ("mobile"); "Operasional Kereta Api" → Administrasi; "Helper Operasional" → Produksi |
| `2026.10.3` (after fixes) | 0.7 | 51/60 = 85% | 48/51 = 94% | "Mechanical Design Engineering" → Desain; "Helper AC" → Produksi; "Station Staff MRT" → Administrasi |

Changes in `2026.10.2`: new families for food & hospitality, retail, transport &
delivery, production, and security & facilities (the archived regional sites are mostly
blue-collar and service roles); "Lainnya" fell from 34% to 16% of app jobs. Changes in
`2026.10.3`: word boundary on "motion", "mobile" only with a tech word, "kereta api" →
transport, "budget" → finance, "reservation" → hospitality, "CSSD/steril" → health.

Limits: 60-title samples give wide uncertainty (±~7 points); the second sample was drawn
after the fixes, but the rules were not tuned on it. A human-labelled sample of ~150
titles is still the open item in ROADMAP.md.

## 7. Role taxonomy: documented evaluation (2026-10-18)

Procedure and labelling guideline: [ml/ROLE_EVALUATION.md](ml/ROLE_EVALUATION.md). This
replaces the informal 60-title self-checks in §6, whose 92–94% "precision" turned out to
be optimistic.

**Reviewers.** Reviewer A: the AI coding assistant that also wrote the rules and
adjudicated disagreements (a conflict of interest; disagreements were few and each
adjudication is recorded in the CSV). Reviewer B: a separate AI agent instance that saw
only the written guideline and the titles, never the rules, the classifier output, or
reviewer A's labels. **No human annotator was involved**; agreement between two AI
reviewers measures labelling consistency, not ground truth.

**Samples** (seeded, drawn from all app jobs with `talentscope roles sample`, titles only,
each later sample excluding earlier ones):

| Round | File | Seed | Used for | Taxonomy scored | Coverage | Precision | Recall | Accuracy | Reviewer agreement (κ) |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | ml/role_eval_2026-10-18.csv | 0.1018 | baseline, then tuning | 2026.10.3 | 87.5% | 87.4% | 80.5% | 79.0% | 95.0% (0.95) |
| 2 | ml/role_validation_2026-10-18.csv | −0.377 | validation of 2026.10.4, then tuning | 2026.10.4 | 81.0% | 89.5% | 76.3% | 77.0% | 98.0% (0.98) |
| 3 | ml/role_test_2026-10-18.csv | 0.6413 | **held-out test** (no rule changed after) | **2026.10.5 (shipped)** | **84.0%** | **94.6%** | **84.6%** | **84.0%** | 96.5% (0.96) |

Scores of a taxonomy on a sample used to tune it are not reported as validation (on its
own tuning samples 2026.10.5 scores 98.4%/97.9% and 92.5%/90.5%; these are training
figures only).

**What the held-out errors show** (n = 200, so each family has few examples; roughly
±5 points on the headline figures):
- Most errors are **misses** (title → "Lainnya"): Indonesian words without a rule
  ("pengemudi", "tentor", "pemasak"), bank roles ("relationship officer", "wealth
  management advisor"), and role names outside the families (translator, beautician).
- **Cross-family collisions** that remain: an employer word in the title (Apoteker at a
  pharma *production* site → Produksi), "admin" + function (the guideline treats "admin"
  as the head noun; the rules sometimes follow the function word), "kitchen equipment
  technician" → Makanan & Minuman.
- Weak families: SALES_BUSINESS recall 76% (bank and agent sales titles), SUPPLY_CHAIN
  recall 77%, SECURITY_FACILITIES and TRANSPORT_DELIVERY (few examples, missed spellings).

**Changes between rounds.** 2026.10.4: "office" no longer matches "officer"; generic
words (staff, assistant, koordinator) no longer imply Administrasi; employer names
(Indomaret, Alfamart) no longer imply Ritel; SPG/SPB/promotor → Penjualan; quality,
inspection, distribution, tender, payable/receivable, fraud, live streaming and other
terms added. 2026.10.5: Indonesian spellings (konten, resepsionis, kernet, kolektor,
farmasi, tata usaha, kepala sekolah, …).

**Next:** a human-labelled sample (≥ 300 titles, two annotators) before quoting accuracy
publicly; fix the misses listed above and re-test on a new sample whose titles do not
occur in any earlier sample.

### 7.1 Audit of the held-out figures (2026-10-18, data engineering)

Reproduce: `talentscope roles score --labels docs/ml/role_test_2026-10-18.csv` (taxonomy
2026.10.5). The figures below are **not human-validated**: both labels and the
adjudication come from AI reviewers.

- **No rule changed after the test was scored.** The current code reproduces the
  documented test result exactly (coverage 84.0%, precision 94.6%, recall 84.6%,
  accuracy 84.0%), and every test error listed in §7 is still an error (e.g.
  "PENGEMUDI", "TENTOR BIMBEL", "PEMASAK BAKMI JAWA" → OTHER). The rule files are not
  under version control yet, so this is the only available evidence; it rules out tuning
  that changed test outcomes, not edits that left them unchanged.
- **Title overlap between splits (leakage by duplicate titles).** Later samples excluded
  earlier *jobs* but not identical *titles*: 39 of the 200 test titles (19.5%) are, after
  normalization, identical to a title in the two tuning samples ("admin gudang",
  "barista", "perawat", "management trainee", ...). All 39 are classified correctly. On
  the 161 test titles not seen during tuning: **coverage 80.1%, precision 93.0%, recall
  80.5%, accuracy 80.1%**. These are the better estimate for unseen titles; the
  documented figures are optimistic by about 4 points in coverage, recall and accuracy.
- **Adjudication leans to the rule author.** Reviewer A (who wrote the rules) also
  adjudicated; in the test sample 6 of 7 disagreements were resolved to A's label (9 of
  10 in round 1, 1 of 4 in round 2). Scored against each reviewer alone: A 95.2% precision
  / 84.7% recall, B 94.0% / 83.2%. The effect is about one point.
- **Shared reviewer behaviour that departs from the written guideline** (both reviewers
  agree, so agreement/kappa cannot reveal it):
  - "admin + function": both reviewers label admin + finance/warehouse/logistics/supply
    chain as the function's family ("ADMIN KEUANGAN" → FINANCE_ACCOUNTING, "ADMIN
    LOGISTIK" → SUPPLY_CHAIN) but "Admin marketing" as ADMIN_OPERATIONS. The guideline's
    tie-break says both "a specific function beats a generic one" and "ADMIN_OPERATIONS
    when 'admin' is the head noun", so it does not decide these titles; the classifier is
    counted wrong on "ADMIN LOGISTIK" and "Admin Marketing & Communication" because of
    this ambiguity, not because of a clear rule error.
  - "BEAUTY THERAPIST" → OTHER by both reviewers, although the guideline lists
    "therapists" under HEALTHCARE; "FULL TERAPIS" → HEALTHCARE. Beauty/spa therapists need
    an explicit guideline line.
- **Per-family errors** (test, n = 200; each family has few examples, so per-family rates
  have wide uncertainty): misses dominate (OTHER predicted for 23 titles with a named
  label). Weakest recall: TRANSPORT_DELIVERY 2/4, SECURITY_FACILITIES 3/5,
  ADMIN_OPERATIONS 8/12, SALES_BUSINESS 19/25, SUPPLY_CHAIN 10/13.
- **Edge cases checked in the app data (2026-10-18), documented, not tuned:**
  - Domestic workers ("ART (Pembantu Rumah Tangga)", "Asisten Rumah Tangga"): 10 app
    jobs (8 of them bisakerja.id campaign vacancies that the campaign fix merges), all
    OTHER. Correct under the guideline (no family covers household work), but it
    hides a real occupation; "ART" is ambiguous in titles ("Nail Art", "Art
    Illustrator"). Day-care "pengasuh" → EDUCATION, boarding-school "pengasuh asrama" →
    OTHER.
  - Drivers written "pengemudi": 3 app jobs → OTHER (missed; "driver", "sopir", "supir" are
    covered).
  - Tutors written "tentor": 9 app jobs → OTHER (missed).
  No rule was added. Adding these words would create a new taxonomy version whose
  evaluation is **not yet validated**: the held-out figures above apply only to 2026.10.5,
  and a new version must be scored on a fresh sample (with titles that do not occur in
  any earlier sample) before any figure is quoted for it.
