# ResumeMatch AI — Phase 12I.11: Official Held-Out Test Quarantine Policy & Exposure Audit

**Date:** November 14, 2026  
**Authority:** ML Governance, Data Integrity & Statistical Evaluation Committee  
**Quarantined Split:** `manifests/v1/held_out_test_v1.parquet`  
**SHA-256 Checksum:** `d4319c1fb86f7708ece03ddb361514940f7416b22958ec6d9c94dc09f367d39b`  
**Quarantine Status:** **`PERMANENTLY QUARANTINED — HISTORICAL DESCRIPTIVE ONLY`**

---

## 1. Executive Summary & Policy Rationale

`held_out_test_v1.parquet` ($N=1,759$, 477 unique resumes, 71 unique jobs) was originally designated as the official held-out test split for ResumeMatch AI. 

However, forensic audit of the experimental trajectory reveals that this split was subjected to **multiple sequential model evaluations, hyperparameter selections, and architecture screenings** during Phase 12F. Furthermore, entity provenance analysis confirmed that **476 of 477 candidate resumes (99.79%)** were present in the primary training dataset (`resume_job_fit_train.csv`), making this split strictly job-disjoint rather than dual-disjoint.

Due to cumulative adaptive test-set reuse, this dataset has lost its status as an unbiased, blind evaluation benchmark. This document establishes the **permanent quarantine policy** governing `held_out_test_v1.parquet`.

---

## 2. Mandatory Quarantine Rules

```
========================================================================================
                          OFFICIAL TEST QUARANTINE RULES
========================================================================================
1. PROHIBITION OF FUTURE SELECTION:
   The held-out test split must NEVER be evaluated during model training, hyperparameter
   optimization, threshold calibration, architecture search, or checkpoint selection.

2. CLASSIFICATION AS HISTORICAL DESCRIPTIVE:
   All existing scores on held_out_test_v1.parquet are classified strictly as historical
   descriptive records. They may NOT be cited as evidence of unbiased generalization.

3. PRESERVATION OF ARTIFACTS:
   The parquet file, manifests, and historical prediction files are preserved unmodified
   for scientific reproducibility and auditing. No historical files may be deleted.

4. BAN ON PSEUDO-INDEPENDENT REPLACEMENTS:
   Engineering teams are strictly prohibited from generating a "new" test set by randomly
   re-splitting the existing training/validation pools and claiming external independence.
========================================================================================
```

---

## 3. Exposure Forensics: Six Sequentially Evaluated Configurations

During Phase 12F, 6 distinct model configurations were evaluated against `held_out_test_v1.parquet`:

| Configuration ID | Model Architecture | Evaluated Accuracy | Macro-F1 | Historical Phase | Exposure Impact |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **EXP-12F-SUP:LR** | Logistic Regression on SBERT + 25 features | 46.45% | 0.4328 | Phase 12F | Baseline test evaluation |
| **EXP-12F-SUP:Stacking** | Hybrid Stacking (RF + GBDT + LR) | 51.05% | 0.4532 | Phase 12F | Architecture exploration on test set |
| **EXP-12F-WEAK** | Programmatic Weak Supervision Augmented Classifier | 47.30% | 0.4371 | Phase 12F | Data augmentation screening on test set |
| **EXP-12F-SSDA** | Self-Supervised Domain Adaptation on Djinni Corpus | 45.14% | 0.4344 | Phase 12F | Representation tuning screened on test set |
| **EXP-12F-PSEUDO** | Confidence-Gated Pseudo-Labeling (28 pairs admitted) | 50.26% | 0.4321 | Phase 12F | Semi-supervised threshold tuning evaluated on test set |
| **EXP-12F-COMBINED** | Final Automated Challenger (LightGBM Optuna Tuned) | 48.89% | 0.4390 | Phase 12F | Checkpoint promotion evaluated on test set |

---

## 4. Leakage Taxonomy: Direct Contamination vs. Adaptive Selection Bias

It is essential to distinguish between two distinct forms of data compromise:

```
[Direct Label Leakage] -------------------> ABSENT (DISPROVED)
  - Ground-truth test labels were never leaked into training inputs.
  - Pseudo-labels in EXP-12F-PSEUDO were drawn from Djinni candidate pool (0 test overlap).

[Adaptive Test-Set Reuse Bias] -----------> CONFIRMED (PRESENT)
  - 6 sequential model configurations were evaluated on the same 1,759 rows.
  - Freedman's Paradox / Post-selection inference: repeatedly querying a test set
    allows researchers to select models that overfit random sample noise.
```

### Mathematical Consequence (Freedman's Paradox)
When $K=6$ models are evaluated on a finite test set of size $N=1,759$, the maximum observed score $\max_{k} \text{Acc}_k = 51.05\%$ or $50.26\%$ is a positively biased estimator of the true population generalization:
$$\mathbb{E}[\max_{k} \hat{\mu}_k] > \max_{k} \mu_k$$
This selection bias invalidates the highest score as an unbiased benchmark.

---

## 5. Summary of Quarantine Governance

`held_out_test_v1.parquet` remains permanently frozen in `manifests/v1/` as a historical reference dataset. Any future benchmark certification must rely exclusively on isolated, pre-registered evaluation splits that adhere to the Future Evaluation Protocol defined in [PHASE12I11_FUTURE_EVALUATION_PROTOCOL.md](file:///d:/skillsync1/docs/research/PHASE12I11_FUTURE_EVALUATION_PROTOCOL.md).
