# Role taxonomy evaluation: procedure and guideline

Replaces the informal 60-title self-checks in ML_EVALUATION.md §6.

## Procedure
1. **Sample.** `talentscope roles sample --size 200 --seed <s> --out docs/ml/role_eval_<date>.csv`
   draws a seeded random sample of app job titles (all sources). The file contains titles
   only, never the classifier's output, so reviewers label blind.
2. **Two independent labels.** Reviewer A and reviewer B each assign one family code per
   title (columns `reviewer_a`, `reviewer_b`) using the guideline below, without seeing
   each other's labels or the classifier output.
3. **Adjudication.** Where A and B disagree, an adjudicator chooses the final label
   (column `adjudicated`), applying the guideline.
4. **Score.** `talentscope roles score --labels <file>` reports, against the final labels:
   - **coverage**: share of titles the classifier assigns to a named family (not OTHER);
   - **precision**: share of those named assignments that match the final label;
   - **recall**: share of titles whose final label is a named family that the classifier
     found;
   - **accuracy** over all titles, **per-family precision/recall**, every error, and
     **inter-reviewer agreement** (raw and Cohen's kappa).
5. Re-run with a new seed after changing rules; never tune rules on the scored sample
   and then report that same sample as validation. Exclude from a new sample every title
   that (after normalization) already occurs in an earlier sample, not only the same
   jobs: identical titles in tuning and test inflate the test score (ML_EVALUATION.md §7.1).
6. The adjudicator should not be one of the two reviewers (in the 2026-10-18 rounds it
   was reviewer A, the rule author).

## Who reviewed (be explicit)
Report each reviewer's identity in the results. An AI reviewer is not a human annotator;
agreement between two AI reviewers measures consistency, not ground truth.

## Labelling guideline
Label the **occupation the title describes**, not the employer's industry. One code per
title. Use OTHER when the title names no occupation (an employer name, a location, a
generic word such as "Karyawan", "Staff", "Internship" without a field) or an occupation
outside every family.

| Code | Use for |
|---|---|
| SOFTWARE_ENGINEERING | software/web/mobile developers, programmers, software engineers, tech leads |
| DATA_ANALYTICS | data analysts/scientists/engineers, BI, statisticians, business analysts |
| INFRASTRUCTURE_DEVOPS | DevOps, SRE, cloud, network/system administrators, security engineers, DBAs |
| QUALITY_ASSURANCE | QA/QC in any industry, testers, quality inspectors |
| IT_SUPPORT | IT support/helpdesk/IT staff |
| PRODUCT_PROJECT | product managers/owners, project managers/coordinators, scrum masters |
| DESIGN_CREATIVE | graphic/UI/UX designers, video, photo, animation, content creators, multimedia |
| MARKETING | marketing, digital marketing, social media, brand, PR, SEO, content strategy |
| SALES_BUSINESS | sales, account executives/managers, business development, canvassers, SPG/SPB when the role is selling |
| FINANCE_ACCOUNTING | finance, accounting, tax, audit, treasury, billing, collection, budget |
| HUMAN_RESOURCES | HR, recruitment, payroll, people/talent, L&D |
| ADMIN_OPERATIONS | administrative and office roles, secretaries, receptionists, general affairs, generic operations staff |
| CUSTOMER_SERVICE | customer service/support/care, call centre |
| SUPPLY_CHAIN | logistics, warehouse, inventory, procurement, purchasing, PPIC, export/import |
| ENGINEERING | non-software engineering, technicians, mechanics, electricians, drafters, architects, surveyors, welders |
| GRADUATE_PROGRAM | management trainee, officer development / graduate programmes |
| EDUCATION | teachers, tutors, lecturers, trainers |
| HEALTHCARE | nurses, doctors, midwives, pharmacists, therapists, lab/medical staff |
| LEGAL | legal, compliance, lawyers, notary staff |
| FOOD_HOSPITALITY | cooks, chefs, kitchen, waiters, baristas, bartenders, housekeeping, hotel, restaurant |
| RETAIL_STORE | cashiers, shop/store crew, store heads, pramuniaga, merchandisers, retail outlet roles |
| TRANSPORT_DELIVERY | drivers, couriers, riders, train/air crew, delivery |
| PRODUCTION | factory/production operators, helpers, packers, assembly, production supervisors |
| SECURITY_FACILITIES | security guards, cleaners, office boys, gardeners |
| OTHER | no occupation named, or an occupation outside all families |

Tie-breaks: a specific function beats a generic one ("Admin Gudang" → SUPPLY_CHAIN,
"Sales Admin" → SALES_BUSINESS only if the duties are selling; otherwise ADMIN_OPERATIONS
when "admin" is the head noun). Seniority words (supervisor, manager, head, staff) do not
change the family. When the head noun is ambiguous across two families, choose the one
the job seeker would search under.

## Results
See ML_EVALUATION.md §7. Held-out test of the shipped taxonomy 2026.10.5: coverage 84.0%,
precision 94.6%, recall 84.6% (200 titles, two AI reviewers, κ 0.96; no human annotator,
so **not human-validated**). On the 161 test titles that do not also occur in the tuning
samples: coverage 80.1%, precision 93.0%, recall 80.5% (§7.1). These figures apply to
taxonomy 2026.10.5 only.

Open guideline gaps found in the audit (§7.1): "admin + function" titles (the tie-break
text supports both readings), beauty/spa therapists (guideline lists "therapists" under
HEALTHCARE; reviewers chose OTHER), household workers (no family; labelled OTHER).
