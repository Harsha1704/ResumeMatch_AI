# ResumeMatch AI — Phase 12E-3: Leakage Audit & Manifest V2 Validation Report

**Document ID:** `PHASE12E3-LEAKAGE-AUDIT`  
**Classification:** MLOps Evaluation Governance, Bipartite Leakage Audit & Protocol Certification  
**Auditor:** Principal Independent ML Evaluation Auditor & Senior MLOps Engineer  
**Target Manifest:** Manifest V1 / Manifest V2 Architecture (`manifests/`)  
**Target Repository:** `D:\skillsync1`  

---

## 1. Executive Summary & Audit Scope

This report audits the bipartite graph separation, entity isolation, and leak-prevention mechanisms governing ResumeMatch AI's evaluation framework.

In Phase 12C, an independent forensic audit exposed that previous experiments contained an **84.12% pair overlap** in dual-unseen validation and an **88.74% overlap** in resume-disjoint validation, which had inflated reported accuracy to an artificial 85.19%. Phase 12D permanently eradicated this vulnerability through cryptographically sealed manifests (`manifests/v1/manifest_v1.json`).

This Phase 12E-3 audit validates that the introduction of external Djinni data and proposed candidate pools maintains **zero evaluation leakage across all benchmark protocols**.

---

## 2. Mathematical Definition: Job-Disjoint vs Dual-Unseen Evaluation

Many machine learning engineers confuse Job-Disjoint validation with Dual-Unseen validation. We establish the formal mathematical definitions:

```
                  BIPARTITE MATCHING EVALUATION TAXONOMY
  Let U be the set of Candidates (Resumes) and V be the set of Job Postings.
  A dataset D is a set of pairs (u, v) where u ∈ U and v ∈ V.

  1. RANDOM PAIR SPLIT (STRICTLY PROHIBITED - EXTREME LEAKAGE):
     U_train ∩ U_test ≠ ∅  AND  V_train ∩ V_test ≠ ∅
     The model memorizes candidate-specific vocabulary and employer phrasing.

  2. JOB-DISJOINT EVALUATION (PROTOCOL 1):
     V_train ∩ V_eval = ∅   (0.0% Job Overlap - STRICTLY ENFORCED)
     U_train ∩ U_eval ≠ ∅   (Candidate Overlap Permitted, e.g. ~98%)
     Simulates real-world scenario: An existing registered pool of job seekers
     is matched against completely novel employer vacancies.

  3. RESUME-DISJOINT EVALUATION (PROTOCOL 2):
     U_train ∩ U_eval = ∅   (0.0% Resume Overlap - STRICTLY ENFORCED)
     V_train ∩ V_eval ≠ ∅   (Job Overlap Permitted, e.g. 100%)
     Simulates real-world scenario: A newly registered candidate applies to
     existing, well-established employer job vacancies.

  4. DUAL-UNSEEN EVALUATION (PROTOCOL 3):
     U_train ∩ U_eval = ∅   AND   V_train ∩ V_eval = ∅
     (0.0% Resume Overlap AND 0.0% Job Overlap - STRICTLY ENFORCED)
     Simulates extreme distribution shift: Platform launches in a novel market
     where NEITHER the candidates NOR the employers have ever been observed.
```

---

## 3. Physical Verification of Partition Isolation (Manifest V1 / V2)

Automated pre-flight assertions executed across physical Parquet split files on disk:

| Partition File Pair | Protocol Evaluated | Sample Count ($N_{\text{tr}} / N_{\text{ev}}$) | Candidate Overlap Count (%) | Job Overlap Count (%) | Exact Pair Overlap Count (%) | Verification Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `job_disjoint_train_v1` vs `job_disjoint_val_v1` | Job-Disjoint Val | 5,462 / 778 | 364 / 373 (97.59% permitted) | **0 / 42 (0.00%)** | **0 / 778 (0.00%)** | **CERTIFIED ZERO LEAKAGE** |
| `resume_disjoint_train_v1` vs `resume_disjoint_val_v1` | Resume-Disjoint Val | 5,217 / 1,023 | **0 / 97 (0.00%)** | 219 / 219 (100% permitted) | **0 / 1,023 (0.00%)** | **CERTIFIED ZERO LEAKAGE** |
| `dual_unseen_train_v1` vs `dual_unseen_val_v1` | Dual-Unseen Val | 3,857 / 297 | **0 / 92 (0.00%)** | **0 / 52 (0.00%)** | **0 / 297 (0.00%)** | **CERTIFIED ZERO LEAKAGE** |
| `job_disjoint_train_v1` vs `held_out_test_v1` | Official Held-Out Test Gate | 5,462 / 1,759 | 475 / 477 (99.58% permitted) | **0 / 71 (0.00%)** | **0 / 1,759 (0.00%)** | **CERTIFIED ZERO LEAKAGE** |

---

## 4. Absolute Protection of the Official Held-Out Test Gate

The 1,759 pairs in `held_out_test_v1.parquet` (evaluated across 71 unseen jobs) represent ResumeMatch AI's **untouched benchmark release gate**.

To preserve scientific validity across Phase 12E:
1. **Forbidden Operations on Held-Out Test:**
   - No model training or gradient updates.
   - No hard-negative mining or runner-up selection.
   - No feature selection or vocabulary building (TF-IDF vectorizer must fit strictly on `train`).
   - No probability threshold tuning (decision thresholds must be selected on validation data).
   - No model architecture selection.
2. **One-Way Decision Boundary:**
   The held-out test gate is evaluated **ONLY ONCE per fully trained model candidate** to generate final reported metrics. If a model fails to outperform the classical production baseline (48.49% accuracy, 0.4707 macro F1), the model is formally rejected for production deployment.
