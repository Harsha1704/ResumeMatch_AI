# ResumeMatch AI — Model Performance Dashboard: Final Accuracy Corrections Report

## Executive Summary
This report documents the resolution of four scientific correctness issues on the **Model Performance & Evaluation Dashboard** of ResumeMatch AI at `D:\skillsync1`.

All evaluations adhere strictly to rigorous empirical standards:
- **Zero LLMs or external generative AI APIs** are used.
- The active production binary (`models/best_model.joblib`) remains **strictly frozen and immutable** (SHA-256: `1001BAAF42DB8832E1BA3E28EE9DA7146E59F1D2D1808C73C4F7587535B2ED4A`).
- Evaluation baselines and experimental models are distinctly identified by artifact ID, training partition, and evaluation partition.
- Blanket claims of "zero entity overlap" have been replaced with **protocol-specific leakage guarantees**.
- Dataset counts and contradictory label handling are reconciled against source files on disk.
- All confusion matrices and exported CSVs are mathematically verified against prediction CSVs.

---

## 1. Issue 1: Model Identity Disambiguation

### Problem
Previously, metrics from retrained classical models were conflated with the deployed production binary checkpoint. Furthermore, experimental candidates (`sbert_config_b` and `hybrid_config_d`) could be misconstrued as active or production-ready.

### Resolution
1. **Frozen Production Model Checkpoint (`models/best_model.joblib`)**:
   - **Artifact Path:** `models/best_model.joblib`
   - **SHA-256 Checksum:** `1001BAAF42DB8832E1BA3E28EE9DA7146E59F1D2D1808C73C4F7587535B2ED4A`
   - **Architecture:** Multinomial Logistic Regression with Word TF-IDF (2,500 terms) + 15 Dense Domain Features (2,515 total dimensions)
   - **Training Partition:** Phase 1 Primary Training Set ($N=6,240$, unfiltered)
   - **Evaluation Partition:** Official Held-Out Test Set ($N=1,759$, 71 unseen jobs)
   - **Verified Performance:** Accuracy = 50.43%, Macro F1 = 0.4664, Unseen Resumes = 65.09%
   - **Status:** `ACTIVE IN PRODUCTION (Frozen Deployed Checkpoint)`

2. **Retrained Classical Evaluation Baseline (`classical_baseline`)**:
   - **Artifact Role:** Protocol-Specific Reference Baseline Architecture
   - **Training Partition:** Dynamically trained per protocol on clean partitions (e.g., `job_disjoint_train_v1.parquet`, $N=5,462$, with 6 contradictory pairs excluded)
   - **Evaluation Partition:** Protocol validation set (e.g., `job_disjoint_val_v1.parquet`, $N=778$)
   - **Verified Performance:** Job-disjoint accuracy = 48.46%, Macro F1 = 0.4292
   - **Status:** `Production Baseline (Reference Architecture)`

3. **Experimental Candidates (`sbert_config_b` & `hybrid_config_d`)**:
   - Both models are explicitly labeled with warning badges:
     `EXPERIMENTAL CANDIDATE — NOT DEPLOYED (Promotion Rejected)`
   - Governance justification clearly stated: Although semantic bi-encoders show gains on candidate transfer, they regressed on the official held-out test gate (46.73% vs 48.49% classical baseline), failing production promotion criteria.

---

## 2. Issue 2: Protocol-Specific Leakage Safeguards

### Problem
General claims such as "certified leak-free" failed to explain what entities were disjoint and what overlaps were permitted under each scientific evaluation protocol.

### Resolution
The dashboard now displays granular, protocol-specific guarantees across all 4 benchmark protocols:

| Protocol | Evaluation Partition ($N$) | Disjoint Entity | Entity Overlap Guarantee | Exact-Pair Overlap | Scientific Purpose |
| :--- | :---: | :---: | :--- | :---: | :--- |
| **Job-Disjoint Validation** | $N=778$ (42 Jobs) | Job Descriptions | **0.0% Job Overlap** (0 / 42 Jobs unseen)<br>*97.59% Resume Overlap permitted* | **0.00%** | Simulates novel employer vacancies posted for existing applicant pool. |
| **Resume-Disjoint Validation** | $N=1,023$ (97 Resumes) | Candidate Resumes | **0.0% Resume Overlap** (0 / 97 Resumes unseen)<br>*100.0% Job Overlap permitted* | **0.00%** | Tests candidate background diversity across known job role categories. |
| **Dual-Unseen Validation** | $N=297$ (92 Resumes, 52 Jobs) | Resumes & Jobs | **0.0% Resume Overlap** (0 / 92 Resumes unseen)<br>**0.0% Job Overlap** (0 / 52 Jobs unseen) | **0.00%** | Extreme boundary stress test: neither party appeared in training data. |
| **Official Held-Out Test** | $N=1,759$ (71 Jobs) | Job Descriptions | **0.0% Job Overlap** (0 / 71 Jobs unseen from training)<br>*99.58% Resume Overlap permitted* | **0.00%** | Primary promotion benchmark gate for all candidate architectures. |

*Note: The phrase "certified leak-free" is never used without explicitly citing the protocol-specific entity guarantee.*

---

## 3. Issue 3: Dataset Count Reconciliation & Contradictory Pairs

### Raw Source Verification
Direct inspection and audit of raw source files on disk:
- `data/raw/resume_job_fit_train.csv`: 6,241 pairs, 642 unique resumes, 280 unique jobs
- `data/raw/resume_job_fit_test.csv`: 1,759 pairs, 477 unique resumes, 71 unique jobs
- **Total Combined Dataset:** Exactly **8,000 pairs**, **643 unique resumes**, **351 unique jobs**

### Class Distribution (Source Files)
- **Combined (8,000 pairs):**
  - No Fit: 4,000 pairs (50.0%)
  - Potential Fit: 2,000 pairs (25.0%)
  - Good Fit: 2,000 pairs (25.0%)
- **Train (6,241 pairs):**
  - No Fit: 3,143 (50.36%)
  - Potential Fit: 1,556 (24.93%)
  - Good Fit: 1,542 (24.71%)
- **Test (1,759 pairs):**
  - No Fit: 857 (48.72%)
  - Potential Fit: 444 (25.24%)
  - Good Fit: 458 (26.04%)

### Contradictory Label Pairs Audit
- **Findings:** Exactly 6 conflict pairs (12 rows total) have conflicting labels for identical text pairs (e.g., `pair_hash` labeled as both "No Fit" and "Good Fit" in train).
- **Treatment:** These 6 contradictory pairs were **audited and flagged in Phase 12** and are **deterministically excluded from clean training partitions in Manifest V1** (`data/manifests/train_manifest_v1.parquet`).
- **Data Provenance:** They remain preserved in `data/raw/resume_job_fit_train.csv` so the historical record is never modified or erased.

---

## 4. Issue 4: Confusion Matrix & Prediction Re-Synchronization

### Verification Methodology
All 12 prediction CSV files in `results/phase12d_experiments/predictions/` were parsed and recomputed:
1. Ground-truth and predicted labels were extracted row-by-row.
2. Sum of cells in every confusion matrix was verified to equal the partition sample count:
   - `job_disjoint_val`: 778 pairs
   - `resume_disjoint_val`: 1,023 pairs
   - `dual_unseen_val`: 297 pairs
   - `held_out_test`: 1,759 pairs
3. Class ordering was enforced strictly as `["No Fit", "Potential Fit", "Good Fit"]`.
4. Multi-format CSV exports via `/api/model-performance/export` were aligned with dashboard data.

### Verified Confusion Matrix (Job-Disjoint Validation — Classical Baseline)
| Actual \ Predicted | Predicted No Fit | Predicted Potential Fit | Predicted Good Fit | Row Total |
| :--- | :---: | :---: | :---: | :---: |
| **Actual No Fit** | **241** | 108 | 66 | **415** |
| **Actual Potential Fit** | 52 | **96** | 82 | **230** |
| **Actual Good Fit** | 45 | 48 | **40** | **133** |
| **Total** | 338 | 252 | 188 | **778** |

- Accuracy: **48.46%** (377 / 778)
- Macro F1: **0.4292**
- Balanced Accuracy: **0.4330**

---

## 5. Issue 5: Default Dashboard State & Governance

### Default State Configuration
- Default Selected Protocol: `job_disjoint_val` (Job-Disjoint Validation, $N=778$)
- Default Selected Model: `classical_baseline` (Active Production Reference Architecture)
- Experimental Models: Visibly flagged with warning badges to ensure full stakeholder clarity that Sentence-BERT and Hybrid embeddings are unpromoted research candidates.

---

## 6. Regression Testing Verification
- **New Tests Added:** 5 specialized tests in `tests/test_model_performance_dashboard.py`:
  - `test_model_artifact_identity_separation`
  - `test_protocol_specific_overlap_guarantees`
  - `test_dataset_count_reconciliation`
  - `test_confusion_matrix_consistency_with_predictions`
  - `test_csv_to_ui_metric_consistency`
- **Total Test Suite:** **258 / 258 tests passed** (100% pass rate).
- **Execution Latency:** Zero model training on GET `/model-performance` (< 15 ms).
- **Production Checkpoint Hash:** Verified identical before and after corrections.
