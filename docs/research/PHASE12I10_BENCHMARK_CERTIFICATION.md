# ResumeMatch AI — Phase 12I.10: Benchmark Certification & Operational Standards

**Date:** November 14, 2026  
**Auditor Roles:** Principal ML Research Auditor & Statistical Evaluation Scientist  
**Authority:** Official Benchmark Standards Committee  
**Certification Status:** **`CONDITIONALLY CERTIFIED — SPECIFIC CLAIMS REQUIRE CORRECTION`**

---

## 1. Scope & Purpose

This document establishes the authoritative benchmark certification and operational evaluation standards for ResumeMatch AI. It supersedes all prior preliminary benchmarks, defining the immutable protocols, datasets, baseline metrics, and promotion criteria for future model development.

---

## 2. Certified Benchmark Protocols

ResumeMatch AI operates under four standardized evaluation protocols, governed by immutable versioned parquet manifests in `manifests/v1/`.

```
========================================================================================
                          STANDARDIZED EVALUATION HIERARCHY
========================================================================================
1. Official Held-Out Test   --> Job Transfer Benchmark (Unseen Jobs, Known Candidates)
2. Dual-Unseen Validation   --> Extreme Generalization Benchmark (Unseen Jobs & Candidates)
3. Job-Disjoint Validation  --> In-Domain Job Transfer Benchmark
4. Resume-Disjoint Val      --> In-Domain Candidate Transfer Benchmark
========================================================================================
```

### Protocol Specifications & Baseline Standards

| Protocol | Parquet Split File | SHA-256 Checksum | Pairs | Candidates | Jobs | True Entity Isolation | Certified Baseline Acc | Certified Challenger Acc |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :---: | :---: |
| **Official Held-Out Test** | `held_out_test_v1.parquet` | `d4319c1fb86f...` | 1,759 | 477 | 71 | **Job-Disjoint** (0% Job Overlap, 99.79% Candidate Overlap) | **48.61%** | **48.89%** |
| **Clean Dual-Unseen Val** | `dual_unseen_val_v1.parquet` | `1b31ae0c5d05...` | 296 | 91 | 52 | **Dual-Disjoint** (0% Job Overlap, 0% Candidate Overlap) | **36.82%** | **44.60%** (5-seed mean) |
| **Job-Disjoint Val** | `job_disjoint_val_v1.parquet` | `8008cbb7d5fd...` | 778 | 373 | 42 | **Job-Disjoint** (0% Job Overlap, Candidates Overlap) | **74.16%** | **75.84%** |
| **Resume-Disjoint Val** | `resume_disjoint_val_v1.parquet` | `f3618ae092c0...` | 1,023 | 97 | 219 | **Candidate-Disjoint** (0% Candidate Overlap, Jobs Overlap) | **77.71%** | **78.98%** |

---

## 3. Mandatory Evaluation Protocols & Safeguards

### Rule 1: Held-Out Test Split Quarantine
The official held-out test split (`held_out_test_v1.parquet`, $N=1,759$) must be strictly quarantined:
- Models may **never** be trained or tuned against the held-out test split.
- Hyperparameter selection, architecture screening, and pseudo-label selection must be performed strictly using cross-validation or isolated validation splits (`dual_unseen_val`, `job_disjoint_val`).
- Final test evaluation may only be executed once when candidate models are frozen for candidate release. Iterative testing is strictly prohibited.

### Rule 2: Two-Way Clustered Inference on Dual-Unseen Data
Because resume-job matching exhibits crossed cluster dependencies across both candidates and jobs:
- All statistical comparisons on `dual_unseen_val_v1.parquet` must report paired two-way clustered standard errors or multi-way clustered bootstrap confidence intervals (Cameron, Gelbach, and Miller 2011).
- Unclustered i.i.d. standard errors and Fisher's combined test across random seeds are **strictly banned**.
- When evaluating multiple random seeds or hyperparameter variations, Family-Wise Error Rate (FWER) must be controlled using step-down Holm-Bonferroni correction.

### Rule 3: Explicit Entity Separation Reporting
Every published evaluation must clearly state the entity provenance:
- Never label a split as "Dual-Unseen" unless both candidates and jobs have 0% overlap with training data.
- The official held-out test split must be explicitly identified as a **Job-Disjoint Test Set**.

---

## 4. Production Checkpoint Promotion Gates

To prevent regression and ensure scientific rigor, no challenger model may replace the production baseline (`models/best_model.joblib`) unless it satisfies **all four** promotion gates:

```
[Candidate Model]
       |
       v
[Gate 1: Dual-Unseen Superiority] ---> Must exceed baseline (36.82%) by >= 4.0 percentage points
       |
       v
[Gate 2: Statistical Significance] --> Two-Way Clustered Bootstrap 95% CI must strictly bound away from 0
       |
       v
[Gate 3: Held-Out Test Non-Regression] --> Must match or exceed baseline (48.61%) on held_out_test
       |
       v
[Gate 4: Latency & Footprint] -------> Inference latency < 50ms/pair; Model size < 50 MB
       |
       v
[APPROVED FOR PRODUCTION PROMOTION]
```

---

## 5. Official Certification Verdict

The benchmark suite is hereby:

**`CONDITIONALLY CERTIFIED — SPECIFIC CLAIMS REQUIRE CORRECTION`**

All machine-readable audit artifacts, correction registers, and test suites are codified in `experiments/phase12i10/` and `docs/research/`.
