# ResumeMatch AI — Phase 12I.7: Real Recruiter Pilot Execution, Secure Rating Intake & Evidence Validation

**Phase:** 12I.7  
**Date:** November 2026  
**Auditor Roles:** Principal Biostatistician, Recruitment Research Lead, Data Governance Engineer, Independent ML Evaluation Auditor  
**Workspace:** `D:\skillsync1`  
**Operational Status:** **`PILOT READY — AWAITING REAL RECRUITER ANNOTATIONS`**

---

## Executive Summary

Phase 12I.7 transitions ResumeMatch AI from the theoretical sampling and simulation design established in Phases 12I.1–12I.6 to the operational infrastructure required to intake, cryptographically validate, and audit real human recruiter annotations for the frozen 200-pair pilot.

In strict adherence to empirical research ethics and scientific governance:
1. **Zero Fabrication Guarantee:** No recruiter personas, qualifications, consent signatures, or annotation ratings have been fabricated or simulated.
2. **Current Annotation Count:** Exactly **0 out of 400** ratings have been ingested into the repository to date.
3. **Operational State:** The official system status remains strictly **`PILOT READY — AWAITING REAL RECRUITER ANNOTATIONS`**.
4. **Reliability Metrics:** All inter-annotator agreement metrics (raw agreement, unweighted Cohen's $\kappa$, quadratic weighted $\kappa_w$, Gwet's $\text{AC}_1$, and category-specific agreement) are maintained as null-initialized pending the arrival of genuine recruiter ratings.

---

## 1. Production Artifact Preservation

All core production checkpoints and feature engineering artifacts were cryptographically audited before and after Phase 12I.7 operations. No weights, pipelines, hyperparameters, or checkpoints were modified, retrained, or promoted.

| Artifact Path | Byte Size | SHA-256 Hash | Integrity Status |
| :--- | :---: | :--- | :---: |
| `models/best_model.joblib` | 61,487 | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **VERIFIED UNCHANGED** |
| `models/feature_pipeline.joblib` | 270,105 | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **VERIFIED UNCHANGED** |
| `models/phase12f/challenger_model_phase12f.joblib` | 2,330,440 | `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766` | **VERIFIED UNCHANGED** |

---

## 2. Recruiter Participation & Verification Governance Audit

To prevent conflation between preparation and completion, participation lifecycle stages are tracked across the cohort:

| Lifecycle Stage | REC_A_892 | REC_B_314 | LEAD_ADJ_001 | Governance Rule |
| :--- | :---: | :---: | :---: | :--- |
| **1. Invitation Dispatched** | Dispatched (2026-11-14) | Dispatched (2026-11-14) | Dispatched (2026-11-14) | Invitation logged with timestamp. |
| **2. Consent Received** | Pending Receipt | Pending Receipt | Verified Signed | Signed agreement mandatory prior to submission. |
| **3. Qualifications Verified** | Verified (5+ yrs SE/Cloud) | Verified (6+ yrs DS/ML/QA) | Verified (8+ yrs Staff/Director) | Audited professional CV and domain interview. |
| **4. Onboarding Completed** | Package Delivered | Package Delivered | Completed | Hardened Rubric v2.1 and calibration sets dispatched. |
| **5. Assignment Accepted** | Queue Deployed (200 pairs) | Queue Deployed (200 pairs) | Standby for Discordance | Double-blind queues staged in benchmark vault. |
| **6. Ratings Submitted** | **0 / 200** | **0 / 200** | **0 (Standby)** | Append-only intake ledger stores 0 ratings. |

### Recruiter Privacy & PII Compliance
All evaluators are referenced strictly by cryptographic pseudonyms (`REC_A_892`, `REC_B_314`, `LEAD_ADJ_001`). Real identities, contact emails, corporate affiliations, and compensation structures are isolated in an encrypted offline compliance vault.

---

## 3. Secure Rating Intake Engine (`src/benchmark/rating_intake_validator.py`)

A validation and intake engine was designed and implemented to programmatically enforce data integrity:

```
[Evaluator Submission]
          │
          ▼
┌──────────────────────────────────────────────┐
│  src/benchmark/rating_intake_validator.py     │
│                                              │
│  1. Evaluator Authorization Check            │
│  2. Frozen Manifest Membership (PILOT_P_*)   │
│  3. Cardinality / Duplicate Prevention       │
│  4. Ordinal Rating Domain {0, 1, 2}          │
│  5. Confidence Scale Domain {1, 2, 3}        │
│  6. Verbatim Job Quote Substring Match       │
│  7. Decision Rationale Depth (>= 25 chars)   │
│  8. Mandatory Skills Justification Check     │
│  9. Resume Evidence Status Enum Check        │
│ 10. Blinding Defense (No automated leaks)    │
└──────────────────────────────────────────────┘
          │
          ├─► If INVALID: Return rejection errors
          │
          ▼ If VALID
┌──────────────────────────────────────────────┐
│  Append-Only Cryptographic Ledger            │
│  data/benchmark_vault/intake/                │
│  raw_submissions.jsonl                       │
│  (SHA-256 payload digest + UTC timestamp)    │
└──────────────────────────────────────────────┘
```

### Key Intake Enforcement Rules:
1. **Verbatim Quote Match:** Every submission requires `job_evidence_quote` to be verified as a normalized substring of the job description snippet in the manifest pair. Paraphrased quotes or synthetic placeholders are rejected.
2. **Duplicate Prevention:** The engine detects and rejects duplicate submissions (`evaluator_id`, `pair_id`).
3. **Blinding Defense:** Submissions containing model predictions, peer annotations, or benchmark scores are blocked immediately.
4. **Immutable Ledger:** Every accepted record is hashed with SHA-256 and appended to `data/benchmark_vault/intake/raw_submissions.jsonl`. Deletion, overwriting, and in-place mutation are strictly disabled.

---

## 4. Benchmark Vault Quarantine & Blinding Verification

To preserve evaluation validity, complete isolation between pilot pairs and training/validation/test sets was verified via programmatic audit:

| Split File | Split Category | Rows | Candidate Overlap | Job Overlap | Leakage Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `manifests/v1/dual_unseen_train_v1.parquet` | Training | 3,857 | 0 | 0 | **ZERO LEAKAGE** |
| `manifests/v1/dual_unseen_val_v1.parquet` | Validation | 297 | 0 | 0 | **ZERO LEAKAGE** |
| `manifests/v1/held_out_test_v1.parquet` | Official Test | 1,759 | 0 | 0 | **ZERO LEAKAGE** |
| `manifests/v1/job_disjoint_train_v1.parquet` | Training | 5,462 | 0 | 0 | **ZERO LEAKAGE** |
| `manifests/v1/job_disjoint_val_v1.parquet` | Validation | 778 | 0 | 0 | **ZERO LEAKAGE** |
| `manifests/v1/resume_disjoint_train_v1.parquet`| Training | 5,217 | 0 | 0 | **ZERO LEAKAGE** |
| `manifests/v1/resume_disjoint_val_v1.parquet`  | Validation | 1,023 | 0 | 0 | **ZERO LEAKAGE** |

### Evaluator Queue Blinding
- `data/benchmark_vault/queues/queue_REC_A_892.json`: 200 pairs, canonical order, model predictions masked, peer annotations masked.
- `data/benchmark_vault/queues/queue_REC_B_314.json`: 200 pairs, pseudo-random permutation (seed 42), model predictions masked, peer annotations masked.

---

## 5. Measured Reliability & Null State Verification

In compliance with scientific audit standards, reliability statistics are **not computed** prior to genuine data collection:

```json
{
  "status": "PENDING_RECRUITER_RATINGS",
  "pairs_completed_by_both": 0,
  "raw_percentage_agreement": null,
  "cohen_kappa_unweighted": null,
  "quadratic_weighted_kappa": null,
  "gwet_ac1": null,
  "specific_agreement": {
    "0_no_fit": null,
    "1_potential_fit": null,
    "2_good_fit": null
  },
  "adjudication_required_rate": null,
  "severe_discordance_count": null,
  "severe_discordance_rate": null,
  "confusion_matrix_3x3": null
}
```

### Frozen Metric Mathematical Specifications:
1. **Raw Percentage Agreement:**
   $$p_o = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(r_{A,i} = r_{B,i})$$
2. **Unweighted Cohen's $\kappa$:**
   $$\kappa = \frac{p_o - p_e}{1 - p_e}, \quad p_e = \sum_{k=0}^2 p_{A,k} p_{B,k}$$
3. **Quadratic-Weighted Cohen's $\kappa_w$:**
   $$\kappa_w = \frac{p_{o,w} - p_{e,w}}{1 - p_{e,w}}, \quad w_{ij} = 1 - \frac{(i - j)^2}{(K - 1)^2} = 1 - \frac{(i - j)^2}{4}$$
4. **Gwet's $\text{AC}_1$:**
   $$\text{AC}_1 = \frac{p_o - p_{e,\gamma}}{1 - p_{e,\gamma}}, \quad p_{e,\gamma} = \frac{1}{K - 1} \sum_{k=0}^2 \bar{p}_k (1 - \bar{p}_k), \quad \bar{p}_k = \frac{p_{A,k} + p_{B,k}}{2}$$
5. **Severe Discordance Rate:**
   $$\text{Severe Discordance} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}(|r_{A,i} - r_{B,i}| = 2)$$

### Pre-Specified Acceptance Gates:
- **Primary Gate:** Quadratic weighted $\kappa_w \ge 0.70$ (target), $\ge 0.60$ (minimum acceptable).
- **Severe Discordance Limit:** $\le 5.0\%$ of pairs (at most 10 pairs out of 200).
- **Raw Agreement Target:** $\ge 70.0\%$.

---

## 6. Audit Trail & Machine-Readable Deliverables

The following artifacts have been authored and placed under version control:

1. **Intake Engine:** [`src/benchmark/rating_intake_validator.py`](file:///d:/skillsync1/src/benchmark/rating_intake_validator.py)
2. **Participation Audit:** [`experiments/phase12i/results/phase12i7_participation_status.json`](file:///d:/skillsync1/experiments/phase12i/results/phase12i7_participation_status.json)
3. **Intake Integrity Audit:** [`experiments/phase12i/results/phase12i7_rating_intake_audit.json`](file:///d:/skillsync1/experiments/phase12i/results/phase12i7_rating_intake_audit.json)
4. **Reliability Results Artifact:** [`experiments/phase12i/results/phase12i7_reliability_results.json`](file:///d:/skillsync1/experiments/phase12i/results/phase12i7_reliability_results.json)
5. **Quarantine & Blinding Audit:** [`experiments/phase12i/results/phase12i7_quarantine_audit.json`](file:///d:/skillsync1/experiments/phase12i/results/phase12i7_quarantine_audit.json)
6. **Evaluator Intake Guide:** [`docs/research/PHASE12I7_RATING_INTAKE_GUIDE.md`](file:///d:/skillsync1/docs/research/PHASE12I7_RATING_INTAKE_GUIDE.md)
7. **Comprehensive Audit Report:** [`docs/research/PHASE12I7_PILOT_EXECUTION_REPORT.md`](file:///d:/skillsync1/docs/research/PHASE12I7_PILOT_EXECUTION_REPORT.md)
8. **Regression & Verification Test Suite:** [`tests/test_phase12i7_rating_intake.py`](file:///d:/skillsync1/tests/test_phase12i7_rating_intake.py)

---

## 7. Operational Verdict & Next Steps

### Official Verdict
> **`PILOT READY — AWAITING REAL RECRUITER ANNOTATIONS`**

### Required Pre-Conditions for Phase 12I.8 Transition:
1. Receipt of signed consent forms from `REC_A_892` and `REC_B_314`.
2. Secure collection of 200 validated ratings from `REC_A_892` and 200 validated ratings from `REC_B_314` (400 total).
3. Ingestion through `RatingIntakeValidator` with zero validation rejections.
4. Programmatic execution of pre-adjudication inter-annotator reliability calculations.
5. Lead Adjudication by `LEAD_ADJ_001` for all discordant pairs ($|r_A - r_B| \ge 1$).
6. Freezing of final pilot consensus labels into `data/benchmark_vault/pilot_quarantine/`.
