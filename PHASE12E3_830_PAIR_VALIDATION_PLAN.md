# ResumeMatch AI — Phase 12E-3: 830-Pair Proposal Pool Validation & Bias Audit

**Document ID:** `PHASE12E3-PROPOSAL-AUDIT`  
**Classification:** Sampling Methodology Audit, Stratification Analysis & Pilot Validation Plan  
**Auditor:** Senior Data Quality Auditor & Principal ML Engineer  
**Target Artifact:** `data/external/djinni/proposed_candidate_pairs_sample.csv` ($N=830$)  
**Target Repository:** `D:\skillsync1`  

---

## 1. Executive Summary & Objective

In Phase 12E-1 and 12E-2, `scripts/propose_djinni_candidate_pairs.py` generated an initial stratified candidate-pair proposal pool of **830 pairs** across 120 benchmark job descriptions from Djinni.

This document provides a critical forensic analysis of this proposal pool, evaluates its sampling biases, and outlines the pilot-to-scale validation plan.

### Key Audit Findings:
1. **Sampling Bias Acknowledgment:**
   The 830 proposed pairs **DO NOT represent a random or representative sample of the 352,147 documents in Djinni**. They were intentionally stratified across six dominant software engineering keywords (`Python`, `JavaScript`, `Java`, `DevOps`, `.NET`, `QA Automation`) and filtered by experience constraints.
2. **Current Label Status:**
   **All 830 pairs are currently 100% UNLABELLED.** Zero labels have been fabricated or inferred.
3. **The 50-Row Template Reality:**
   The 50-row CSV `PHASE12E2_PAIR_ANNOTATION_TEMPLATE.csv` represents an initial **pilot validation exercise** designed to calibrate human annotators, test rubric clarity, and measure initial Cohen's Kappa. It is **NOT a training dataset**.

---

## 2. Forensic Stratification Breakdown of the 830 Pairs

| Stratum Type | Sample Count ($N$) | Percentage | Generation Rationale & Heuristics | Expected Class Yield |
| :--- | :---: | :---: | :--- | :--- |
| **High Alignment Proposals** | 360 | 43.37% | Exact primary keyword match + candidate experience meets/exceeds JD requirement. | High yield of **Good Fit** and high-qualification **Potential Fit**. |
| **Borderline Runner-Up Proposals** | 230 | 27.71% | Exact primary keyword match, but candidate experience is 1–2 years below requirement. | High yield of **Potential Fit** and borderline hard-negative **No Fit**. |
| **Cross-Domain Negative Controls** | 240 | 28.92% | Deliberate mismatch of primary keyword (e.g. QA Automation CV paired with DevOps JD). | High yield of unambiguous **No Fit** anchor baselines. |
| **Total Proposal Pool** | **830** | **100.0%** | Derived from 120 unique JDs and 136 unique candidate CVs. | Balanced 3-class candidate pool. |

---

## 3. Sampling Bias Analysis & Representativeness Limitations

Why can this proposal pool NOT be treated as representative of the general job market?

```
┌────────────────────────────────────────────────────────────────────────┐
│                     FOUR INHERENT SAMPLING BIASES                      │
├────────────────────────────────┬───────────────────────────────────────┤
│ 1. Domain Concentration Bias   │ 100% of pairs come from 6 tech stacks │
│                                │ (Python, JS, Java, DevOps, .NET, QA). │
│                                │ Marketing, Design, Sales omitted.     │
├────────────────────────────────┼───────────────────────────────────────┤
│ 2. Artificial Class Balancing  │ Real recruitment has ~80% No Fit      │
│                                │ applicants. Proposal pool forces a    │
│                                │ ~40/30/30 synthetic distribution.    │
├────────────────────────────────┼───────────────────────────────────────┤
│ 3. English-Only Filter         │ Only English-language CVs and JDs are │
│                                │ included, excluding bilingual items.  │
├────────────────────────────────┼───────────────────────────────────────┤
│ 4. Platform Selection Bias     │ Djinni candidates are tech freelancers│
│                                │ and full-time IT engineers in Europe. │
└────────────────────────────────┴───────────────────────────────────────┘
```

1. **Tech-Stack Concentration:**
   The pool focuses on 6 high-volume software domains. Non-technical roles (Finance, Executive Leadership, Sales, Legal) present in the broader economy are completely unrepresented in this batch.
2. **Artificial Class Prior:**
   In real job boards, random applicants have a ~75%–85% No Fit rate. The stratified proposal pipeline artificially forces roughly 43% high alignment, 28% borderline, and 29% cross-domain. While mathematically beneficial for training balanced classifiers, test metrics measured on this stratified sample must be explicitly designated as **Stratified Benchmark Metrics**, not random-market accuracy.
3. **Candidate Re-Use Density:**
   The 830 pairs use 136 unique candidates (averaging 6.1 pairs per candidate) across 120 jobs (averaging 6.9 pairs per job). While vastly superior to the legacy dataset, entity-disjoint validation protocols must be strictly enforced.

---

## 4. The Phased Validation & Scaling Roadmap

```
                                  VALIDATION ROADMAP
  ┌────────────────────────────────────────────────────────────────────────┐
  │ PHASE A: PILOT CALIBRATION (N = 50 Pairs)                              │
  │ - 2 Independent Annotators evaluate PHASE12E2_PAIR_ANNOTATION_TEMPLATE │
  │ - Calculate Initial Cohen's Kappa (Target: κ ≥ 0.65)                   │
  │ - Identify ambiguous clauses in Rubric V2; adjust adjudication rules.   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ PHASE B: BENCHMARK SAMPLE ANNOTATION (N = 830 Pairs)                   │
  │ - Deploy blinded workflow across full proposed pool                    │
  │ - Two independent passes + Senior Recruiter Adjudication               │
  │ - Compute final inter-annotator matrix and class-conditional agreement │
  │ - Forms the initial Djinni Gold Benchmark                              │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ PHASE C: ACTIVE-LEARNING SCALE-UP (Target: N = 3,000 - 5,000 Pairs)    │
  │ - Use model uncertainty to sample high-entropy borderline pairs        │
  │ - Ingest additional domains (Data Science, Cloud Architecture, Mobile) │
  │ - Expand unique job descriptions to ≥ 1,000 entities                   │
  └────────────────────────────────────────────────────────────────────────┘
```

### Protocol Gate for Advancing Beyond Pilot:
The project must NOT claim that the Djinni dataset is labelled based on the 50-pair pilot. Moving from Phase A to Phase B requires:
1. Human completion of all 50 pilot pairs by two independent reviewers.
2. A measured Cohen's Kappa $\kappa \ge 0.65$.
3. Formal documentation of adjudication rationales for all disagreement cases.
