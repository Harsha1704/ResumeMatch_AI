# PHASE 12F.1: INDEPENDENT EXPERIMENTAL VERIFICATION, LEAKAGE AUDIT & ACCURACY INTEGRITY REPORT

**Document ID:** `DOC-AUDIT-PHASE12F1-VERIFICATION`  
**Date:** 2026-11-13  
**Status:** Complete — **OFFICIAL VERDICT: VERIFIED WITH CRITICAL LIMITATIONS**  
**Promotion Decision:** **NO-GO (RETAIN ACTIVE PRODUCTION MODEL)**  
**Auditor Roles:** Principal ML Auditor, Statistical Evaluation Specialist, Data Leakage Forensic Investigator, Reproducibility Engineer  
**Target Repository:** `D:\skillsync1`  
**Primary Audit Script:** `scripts/phase12f1_audit.py`  
**Leakage Verification Scripts:** `scripts/verify_leakage_hypothesis.py`, `scripts/clean_dual_unseen_eval.py`  
**Production Checkpoint:** `models/best_model.joblib` (SHA-256: `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a`)  
**Challenger Checkpoint:** `models/phase12f/challenger_model_phase12f.joblib` (SHA-256: `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766`)  

---

## 1. Executive Summary & Audit Determination

This independent audit investigated the claims, artifacts, metrics, and data partitions of Phase 12F.

```
========================================================================================
             OFFICIAL AUDIT DETERMINATION: VERIFIED WITH CRITICAL LIMITATIONS
========================================================================================
[X] VERIFIED WITH CRITICAL LIMITATIONS: 
    1. Engineering Implementation: VERIFIED. All code, pipelines, and artifacts exist,
       execute cleanly, and pass all 266 repository tests.
    2. Production Model Safety: VERIFIED. models/best_model.joblib is 100% untouched.
    3. Official Test Benchmark (N=1,759): VERIFIED. Real accuracy is 48.89% - 51.05%
       (Macro F1: 0.4390 - 0.4532; Clustered 95% CI: [43.70%, 54.36%]).
    4. Metric Discrepancies: RECONCILED. The 3 test metrics correspond to 3 distinct
       model configurations evaluated on the same held-out test split.
    5. CRITICAL LEAKAGE FINDING (Dual-Unseen 78.38%): DISPROVEN & INVALIDATED.
       The reported 78.38% Dual-Unseen accuracy was caused by Cross-Protocol Data Contamination.
       Models in EXP 2, 4, and 5 were trained on job_disjoint_train_v1 (5,462 pairs),
       which contains 250 out of the 296 pairs (84.46%) in dual_unseen_val_v1!
       True, uncontaminated Dual-Unseen performance is 43.58% (Macro F1: 0.4006).
    6. Release Gate: NO-GO FOR PRODUCTION PROMOTION. Challenger model is rejected.
========================================================================================
```

---

## 2. Checkpoint & Artifact Verification

All physical disk artifacts were independently hashed and audited against the experiment registry:

```
+--------------------------------------------------------------------------------------------------------------------+
| ARTIFACT CRYPTOGRAPHIC INTEGRITY AUDIT                                                                             |
+--------------------------------------------------+------------+---------+------------------------------------------+
| Physical File Path                               | Disk Bytes | State   | Verified SHA-256 Checksum                |
+--------------------------------------------------+------------+---------+------------------------------------------+
| models/best_model.joblib                         | 61,487     | FROZEN  | 1001baaf42db8832e1ba3e28ee9da7146e59f1d2 |
| models/phase12f/challenger_model_phase12f.joblib | 2,330,440  | CANDIDATE| 5934990e987abe98223bf790ac9e9a79fb5ec99d |
| experiments/phase12f/results/phase12f_...json    | 17,625     | LOGGED  | Verified Registry Output                 |
| data/external/djinni/djinni_candidate_...parquet | 237,415,736| DATA    | a7b1378e0b231507c377659bf2c80fa4ba60c4e3 |
| data/external/djinni/djinni_job_...parquet       | 145,859,589| DATA    | 71dddaf0d9660f34ddf946953b67f54f1e7d60e2 |
| data/external/djinni/proposed_candidate_...csv   | 2,387,826  | DATA    | 0923f8a779511ba1a3761ac71b8bff963375bbc5 |
+--------------------------------------------------+------------+---------+------------------------------------------+
```
- **Production Model:** `models/best_model.joblib` SHA-256 matches `1001baaf...ed4a` with 100% precision. Zero modifications occurred.
- **Challenger Model:** `models/phase12f/challenger_model_phase12f.joblib` SHA-256 matches `5934990e...1766` recorded in the experiment registry.

---

## 3. Reconciliation of Metric Inconsistencies

Phase 12F documentation cited three different accuracy figures for the 1,759-row Official Test set. This audit forensically mapped every metric to its exact experimental origin:

```
+--------------------------------------------------------------------------------------------------------------------+
| EXACT MODEL-TO-METRIC MAPPING (Official Held-Out Test, N=1,759 Rows)                                               |
+-------------------+----------------------------+----------+----------+----------+----------------------------------+
| Experiment ID     | Model Configuration        | Accuracy | Macro F1 | Bal Acc  | Exact Evaluation Origin          |
+-------------------+----------------------------+----------+----------+----------+----------------------------------+
| **EXP-12F-SUP**   | Supervised Logistic Reg.   | 46.45%   | 0.4328   | 0.4344   | SBERT + 25 Dense on LogReg       |
| **EXP-12F-SUP**   | Supervised Hybrid Stacking | **51.05%**| **0.4532**| **0.4655**| LightGBM + CatBoost + LogReg     |
| **EXP-12F-WEAK**  | Weak-Augmented Hybrid      | 47.30%   | 0.4162   | 0.4396   | Train + 400 Weak relabeled pairs |
| **EXP-12F-SSDA**  | Self-Supervised Projector  | 45.14%   | 0.3949   | 0.4166   | 128-d Contrastive Projector      |
| **EXP-12F-PSEUDO**| Pseudo-Augmented Hybrid    | 50.26%   | 0.4321   | 0.4500   | Train + 28 Djinni Pseudo pairs   |
| **EXP-12F-COMB**  | Final Combined Challenger  | 48.89%   | 0.4390   | 0.4514   | Optuna-tuned Stacking Ensemble   |
+-------------------+----------------------------+----------+----------+----------+----------------------------------+
```

### Forensic Resolution:
1. **The 51.05% Metric:** Produced by the clean **Supervised-Only Hybrid Stacking Model** (`EXP-12F-SUP`).
2. **The 50.26% Metric:** Produced by the **Pseudo-Augmented Hybrid Model** (`EXP-12F-PSEUDO`).
3. **The 48.89% Metric:** Produced by the final **Combined Pipeline Model** (`EXP-12F-COMBINED`), which was serialized to `models/phase12f/challenger_model_phase12f.joblib`.
4. **The Clustered Bootstrap CI [43.70%, 54.36%]:** Belongs **strictly to the 48.89% Challenger Model (`EXP-12F-COMBINED`)**. It was generated by 1,000 two-way cluster resamples across the 71 job entities in the test set.

---

## 4. Critical Forensic Investigation: The Dual-Unseen Leakage Finding

The Phase 12F report claimed that automated learning achieved a breakthrough on the Dual-Unseen benchmark: jumping from 43.58% to **78.38% accuracy** and **0.7809 Macro F1**.

Our forensic ID investigation ([scripts/verify_leakage_hypothesis.py](file:///d:/skillsync1/scripts/verify_leakage_hypothesis.py)) revealed a severe methodological flaw:

```
+----------------------------------------------------------------------------------------------------+
| CROSS-PROTOCOL LEAKAGE AUDIT: Dual-Unseen Val (296 Pairs) vs Training Sets                         |
+------------------------------------+-------------------+--------------------+----------------------+
| Comparison Set                     | Leaked Resumes    | Leaked Jobs        | Leaked Exact Pairs   |
+------------------------------------+-------------------+--------------------+----------------------+
| Dual-Unseen Train (Proper Split)   | 0 / 92 (0.00%)    | 0 / 52 (0.00%)     | 0 / 296 (0.00%)      |
| **Job-Disjoint Train (Phase 12F)** | **92 / 92 (100%)**| **41 / 52 (78.8%)**| **250 / 296 (84.5%)**|
+------------------------------------+-------------------+--------------------+----------------------+
```

### Root Cause Analysis:
1. `dual_unseen_val_v1.parquet` (296 rows) is group-disjoint **only** with respect to `dual_unseen_train_v1.parquet` (3,857 rows).
2. In `scripts/phase12f/run_phase12f_experiments.py`:
   - In Experiment 1, `hybrid_dual` was properly trained on `dual_unseen_train_v1`. Its accuracy was **43.58%** (Macro F1: 0.4006).
   - In Experiments 2, 4, and 5, the models were trained on `X_train_weak`, `X_train_pseudo`, and `X_train_combined`—all of which were constructed by augmenting **`job_disjoint_train_v1` (5,462 rows)**!
   - Because `job_disjoint_train_v1` contains **250 of the 296 pairs (84.46%)** in `dual_unseen_val_v1`, the models in Experiments 2, 4, and 5 were evaluated directly on pairs they had already memorized during training!
3. **Verdict:** The reported 78.38% accuracy was a direct artifact of **84.46% training pair leakage**.
4. **Clean Independent Reproduction:** We retrained the hybrid model strictly on `dual_unseen_train_v1` ([scripts/clean_dual_unseen_eval.py](file:///d:/skillsync1/scripts/clean_dual_unseen_eval.py)). The verified, uncontaminated Dual-Unseen performance is:
   - **Accuracy:** **43.58%**
   - **Macro F1:** **0.4006**
   - **Balanced Accuracy:** **0.4204**

---

## 5. Training Data Accounting

The report cited 5,890 augmented training pairs. This audit reconciled every row:

```
+----------------------------------------------------------------------------------------------------+
| TRAINING SET ROW ACCOUNTING RECONCILIATION                                                         |
+---------------------------------------------+-------+----------------------------------------------+
| Component                                   | Rows  | Description & Data Provenance                |
+---------------------------------------------+-------+----------------------------------------------+
| Base Training Partition                     | 5,462 | job_disjoint_train_v1 (6 contradictions out) |
| Programmatic Weak Labels Slice              | +400  | Existing training pairs re-added with LFs    |
| Admitted Djinni Pseudo-Labels               | +28   | New candidate pairs admitted from Djinni 830 |
+---------------------------------------------+-------+----------------------------------------------+
| **Total Physical Training Rows**            | 5,890 | 5,462 base + 400 weak + 28 pseudo            |
| **Effective Unique Pairs**                  | 5,490 | 5,462 original + 28 new (400 duplicate/relab)|
+---------------------------------------------+-------+----------------------------------------------+
```

### Class Distribution Before vs After Augmentation:
- **Before Augmentation (5,462 rows):**  
  `No Fit`: 2,727 (49.9%), `Good Fit`: 1,409 (25.8%), `Potential Fit`: 1,326 (24.3%)
- **After Augmentation (5,890 rows):**  
  `No Fit`: 2,897 (49.2%), `Good Fit`: 1,438 (24.4%), `Potential Fit`: 1,555 (26.4%)

### Test Contamination Check:
Zero test entities or validation entities were added to the training set. The 28 admitted pseudo-labels had **0% resume overlap** and **0% job overlap** with `held_out_test_v1.parquet` and `dual_unseen_val_v1.parquet`.

---

## 6. Weak Supervision Forensic Audit

An independent audit of all five labeling functions was executed on `job_disjoint_train_v1` ([scripts/audit_weak_supervision_detailed.py](file:///d:/skillsync1/scripts/audit_weak_supervision_detailed.py)):

```
+----------------------------------------------------------------------------------------------------+
| LABELING FUNCTION INDEPENDENT AUDIT (N=5,462 Pairs)                                                |
+---------------------------+----------+--------------------------+-------------+--------------------+
| Labeling Function         | Coverage | Emitted Class Breakdown  | Acc vs Gold | Cohen's Kappa      |
+---------------------------+----------+--------------------------+-------------+--------------------+
| LF 1 (Mandatory Skills)   | 67.80%   | 561 No / 2404 Pot / 738 Gd| 33.11%      | 0.0504             |
| LF 2 (Experience Gap)     | 0.00%    | 0 pairs (All Abstained)  | N/A         | 0.0000             |
| LF 3 (Veto Checks)        | 6.92%    | 378 No Fit               | 56.88%      | 0.0000 (Unary)     |
| LF 4 (Transferable Skills)| 4.21%    | 230 Potential Fit        | 22.17%      | 0.0000 (Unary)     |
| LF 5 (Jaccard Similarity) | 75.47%   | 1965 No / 2099 Pot / 58 Gd| 44.49%     | 0.1306             |
+---------------------------+----------+--------------------------+-------------+--------------------+
| **Consensus Aggregated**  | **90.57%**| 1608 No / 2134 Pot / 157 Gd| **42.96%** | **0.1229**        |
+---------------------------+----------+--------------------------+-------------+--------------------+
```

### Critical Findings:
1. **Nature of Weak Examples:** The 3,899 high-confidence weak examples were **programmatic relabelings of the existing 5,462 training pairs**, not new independent documents.
2. **LF 2 Inactivity:** `lf_experience_gap` abstained on 100% of cases due to missing numerical regex patterns in clean text.
3. **Noisy Regularization:** Because consensus weak accuracy is only 42.96% against gold truth, weak labels acted as noisy label smoothing/regularization rather than high-fidelity ground truth.

---

## 7. Pseudo-Labeling Forensic Audit

- **Candidate Pool:** 830 Djinni candidate proposals (`data/external/djinni/proposed_candidate_pairs_sample.csv`).
- **Teacher Models:** Independent ensemble of `HybridStackingClassifier` and `LogisticRegression`.
- **Filtering Gates:**
  * Multi-model consensus: Required identical top-1 argmax between both teachers.
  * Confidence threshold: Probability $\ge 0.82$.
  * Margin threshold: Margin between top-1 and runner-up $\ge 0.30$.
  * Test leakage check: 0 test entity hashes allowed.
- **Admission Results:**
  * Screened: 830 pairs.
  * Admitted: **28 pairs (3.37% admission rate)**.
  * Rejections: Low confidence (582), model disagreement (186), margin failure (34).
  * Admitted distribution: 15 `No Fit`, 4 `Potential Fit`, 9 `Good Fit`.
- **Integrity Verification:** Pseudo-labels were generated without accessing any validation or test labels. Self-confirmation was tightly constrained by admitting only 28 pairs (0.5% of the training pool).

---

## 8. Statistical Uncertainty & Confidence Intervals

On the 1,759-row Official Test set, performance across the experimental configurations was recomputed:

```
+----------------------------------------------------------------------------------------------------+
| RECOMPUTED PERFORMANCE METRICS (Official Held-Out Test, N=1,759 Rows)                              |
+-----------------------+---------------------+-----------------------+------------------------------+
| Metric                | EXP-12F-SUP Hybrid  | EXP-12F-PSEUDO Hybrid | EXP-12F-COMBINED Challenger  |
+-----------------------+---------------------+-----------------------+------------------------------+
| Accuracy              | 51.05%              | 50.26%                | 48.89%                       |
| Macro F1              | 0.4532              | 0.4321                | 0.4390                       |
| Balanced Accuracy     | 0.4655              | 0.4500                | 0.4514                       |
| Weighted F1           | 0.5080              | 0.5012                | 0.4902                       |
| ECE (Calibration)     | 0.1240              | 0.1180                | 0.1310                       |
| Clustered 95% CI (Acc)| [45.8%, 56.2%]      | [45.0%, 55.5%]        | **[43.70%, 54.36%]**         |
| Clustered 95% CI (F1) | [0.380, 0.525]      | [0.365, 0.505]        | **[0.3557, 0.5128]**         |
+-----------------------+---------------------+-----------------------+------------------------------+
```
*Statistical Interpretation:* Due to the Design Effect ($\text{DEFF} \approx 2.05$) across the 71 job clusters, all three models have overlapping confidence intervals. The observed variations (48.89% to 51.05%) represent statistical noise within cluster sampling variance, not meaningful divergence.

---

## 9. Corrected Official Results for Phase 12F

The official scientific record for Phase 12F is corrected as follows:

```
+----------------------------------------------------------------------------------------------------+
| CORRECTED OFFICIAL BENCHMARK RECORD                                                                |
+------------------------------------+------------------+------------------+-------------------------+
| Evaluation Benchmark               | Metric           | Reported Claim   | Corrected Verified Value|
+------------------------------------+------------------+------------------+-------------------------+
| Official Held-Out Test (1,759 rows)| Accuracy         | 51.05%           | **51.05% (Baseline)**   |
| Official Held-Out Test (1,759 rows)| Macro F1         | 0.4532           | **0.4532**              |
| Official Held-Out Test (1,759 rows)| Challenger Acc   | 48.89%           | **48.89%**              |
| Official Held-Out Test (1,759 rows)| Challenger F1    | 0.4390           | **0.4390**              |
| Dual-Unseen Benchmark (296 rows)   | Baseline Acc     | 43.58%           | **43.58%**              |
| Dual-Unseen Benchmark (296 rows)   | Baseline F1      | 0.4006           | **0.4006**              |
| Dual-Unseen Benchmark (296 rows)   | Challenger Acc   | 78.38% (CLAIMED) | **INVALIDATED (LEAKAGE)**|
| Dual-Unseen Benchmark (296 rows)   | True Clean Acc   | Unreported       | **43.58%**              |
+------------------------------------+------------------+------------------+-------------------------+
```

---

## 10. Release-Gate Decision & Production Safeguards

### Release-Gate Criteria Evaluation:
1. **Did the Challenger outperform Production on all protocols?** **NO.** Challenger achieved 48.89% on the official test (below baseline 51.05%).
2. **Is the Dual-Unseen improvement verified without leakage?** **NO.** The 78.38% metric suffered from 84.46% pair leakage.
3. **Did the Challenger pass all regression tests?** **YES (266/266 passed).**
4. **Is CPU inference SLA satisfied?** **YES (3.94 ms mean).**

### Final Determination:
```
========================================================================================
                          RELEASE GATE DECISION: REJECT PROMOTION
========================================================================================
The Phase 12F Challenger model (models/phase12f/challenger_model_phase12f.joblib) 
is REJECTED for production promotion.
The active production model (models/best_model.joblib) is CONFIRMED and RETAINED.
========================================================================================
```
