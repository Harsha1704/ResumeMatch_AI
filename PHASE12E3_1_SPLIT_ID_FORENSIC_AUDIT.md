# PHASE 12E-3.1: DUAL-UNSEEN SPLIT FORENSIC AUDIT & ID RECONCILIATION

**Document Version:** 1.0.0  
**Date:** 2026-11-13  
**Auditor Roles:** Independent ML Research Auditor, Data Governance Engineer, Lead Evaluation Specialist  
**Project:** ResumeMatch AI (`D:\skillsync1`)  
**Audit Script:** `scripts/run_forensic_split_id_audit.py`  
**Raw Results:** `results/phase12e3_1/split_id_forensic_results.json`  

---

## 1. Executive Forensic Finding: Resolving the Contradiction

Across historical project documentation, conflicting statements have emerged regarding the nature of the evaluation splits:
- **Statement A:** The original test set is "job-disjoint" (71 unseen jobs).
- **Statement B:** An earlier audit noted that "476 of 477 test resumes overlap with training."
- **Statement C:** Recent phase overviews casually referred to the 1,759-row test as "dual-unseen."

### The Definitive Forensic Verdict:
1. **The 1,759-row test set (`data/raw/resume_job_fit_test.csv` / `manifests/v1/held_out_test_v1.parquet`) is STRICTLY JOB-DISJOINT, NOT DUAL-UNSEEN.**
2. **476 out of 477 unique resumes in the test set (99.79%) were present in the training set (`data/raw/resume_job_fit_train.csv`).**
3. While the 71 job descriptions in the test set have **zero overlap (0.0%)** with training jobs, and all 1,759 resume–job pairs have **zero exact overlap (0.0%)**, the candidate resumes themselves were extensively seen by the model during training.
4. **A certified dual-unseen test set of scale $N \ge 1,500$ DOES NOT CURRENTLY EXIST in this repository.**
5. The only partition exhibiting zero resume and zero job overlap in the legacy dataset is the internal validation fold `manifests/v1/dual_unseen_val_v1.parquet` ($N=297$ pairs), which is an internal validation split, not a held-out test set.
6. **Mandate:** The 1,759-row test set must never be labeled or reported as "dual-unseen." A true dual-unseen test set must be constructed from newly acquired data (e.g., Djinni candidates and jobs) and independently labeled by human consensus.

---

## 2. Definitive Evaluation Protocol Definitions

To prevent future ambiguity or misclassification of splits, the evaluation protocols are formally defined:

```
+----------------------------------------------------------------------------------------------------+
| EVALUATION PROTOCOL TAXONOMY & ISOLATION BOUNDARIES                                                |
+----------------------+--------------------+--------------------+-----------------------------------+
| Protocol Name        | Resume Overlap     | Job Overlap        | What It Validates                 |
+----------------------+--------------------+--------------------+-----------------------------------+
| Job-Disjoint         | Permitted (>0%)    | Strictly Zero (0%) | Generalization to new jobs when   |
|                      |                    |                    | candidates are already in system. |
+----------------------+--------------------+--------------------+-----------------------------------+
| Resume-Disjoint      | Strictly Zero (0%) | Permitted (>0%)    | Generalization to new candidates  |
|                      |                    |                    | applying to existing job openings.|
+----------------------+--------------------+--------------------+-----------------------------------+
| Dual-Unseen          | Strictly Zero (0%) | Strictly Zero (0%) | True double-blind cold-start:     |
|                      |                    |                    | new candidates to new jobs.       |
+----------------------+--------------------+--------------------+-----------------------------------+
```

---

## 3. Comprehensive Entity & ID Overlap Matrix

Every split artifact in `data/raw/` and `manifests/v1/` was audited using content-derived cryptographic SHA-256 hashes for both raw text and normalized text (lowercased, alphanumeric tokens only).

```
+--------------------------------------------------------------------------------------------------------------------------+
| PHYSICAL SPLIT INVENTORY & CHARACTERISTICS                                                                               |
+------------------------------------+-------+----------------+-------------+----------------------------------------------+
| Split File Path                    | Rows  | Unique Resumes | Unique Jobs | Class Distribution (No / Potential / Good)   |
+------------------------------------+-------+----------------+-------------+----------------------------------------------+
| data/raw/resume_job_fit_train.csv  | 6,241 | 642            | 280         | 3,142 No Fit / 1,556 Potential / 1,543 Good  |
| data/raw/resume_job_fit_test.csv   | 1,759 | 477            | 71          | 857 No Fit / 444 Potential / 458 Good        |
| job_disjoint_train_v1.parquet      | 5,462 | 633            | 238         | 2,727 No Fit / 1,326 Potential / 1,409 Good  |
| job_disjoint_val_v1.parquet        | 778   | 373            | 42          | 415 No Fit / 230 Potential / 133 Good        |
| resume_disjoint_train_v1.parquet   | 5,217 | 545            | 280         | 2,656 No Fit / 1,308 Potential / 1,253 Good  |
| resume_disjoint_val_v1.parquet     | 1,023 | 97             | 219         | 486 No Fit / 248 Potential / 289 Good        |
| dual_unseen_train_v1.parquet       | 3,857 | 500            | 221         | 1,980 No Fit / 926 Potential / 951 Good      |
| dual_unseen_val_v1.parquet         | 297   | 92             | 52          | 124 No Fit / 80 Potential / 93 Good          |
| held_out_test_v1.parquet           | 1,759 | 477            | 71          | 857 No Fit / 444 Potential / 458 Good        |
+------------------------------------+-------+----------------+-------------+----------------------------------------------+
```

### Forensic Overlap Audit Across All Evaluation Partitions

```
+--------------------------------------------------------------------------------------------------------------------------+
| PAIRWISE PARTITION OVERLAP AUDIT                                                                                         |
+--------------------------------+-----------------+-------------+-------------+-------------+---------------+-------------+
| Training Partition             | Evaluation Split| Eval Rows   | Resume O/L  | Job O/L     | Pair O/L      | Protocol    |
+--------------------------------+-----------------+-------------+-------------+-------------+---------------+-------------+
| Raw Train (6,241)              | Raw Test (1,759)| 1,759       | 476 (99.79%)| 0 (0.00%)   | 0 (0.00%)     | Job-Disjoint|
| Job-Disjoint Train V1 (5,462)  | Job Val V1 (778)| 778         | 364 (97.59%)| 0 (0.00%)   | 0 (0.00%)     | Job-Disjoint|
| Resume-Disjoint Train V1(5,217)| Res Val V1(1023)| 1,023       | 0 (0.00%)   | 219 (100.0%)| 0 (0.00%)     | Resume-Disj |
| Dual-Unseen Train V1 (3,857)   | Dual Val V1(297)| 297         | 0* (0.00%)  | 0 (0.00%)   | 0 (0.00%)     | Dual-Unseen |
| Job-Disjoint Train V1 (5,462)  | Held-Out (1,759)| 1,759       | 475 (99.58%)| 0 (0.00%)   | 0 (0.00%)     | Job-Disjoint|
| Dual-Unseen Train V1 (3,857)   | Held-Out (1,759)| 1,759       | 376 (78.83%)| 0 (0.00%)   | 0 (0.00%)     | Contaminated|
| Raw Train (6,241)              | Held-Out (1,759)| 1,759       | 476 (99.79%)| 0 (0.00%)   | 0 (0.00%)     | Job-Disjoint|
+--------------------------------+-----------------+-------------+-------------+-------------+---------------+-------------+
```
*\*Note on Dual-Unseen Val: Exact raw string hash overlap is 0/92 (0.0%). Normalized text analysis revealed 1 resume differing by a single punctuation character (`|` vs `–`). Corrected dual-unseen val contains 296 uncontaminated pairs.*

---

## 4. Analysis of the Original Official Test (`held_out_test_v1.parquet`)

### 4.1 Provenance and Physical Structure
- **File:** `data/raw/resume_job_fit_test.csv` (SHA-256: `f3c48f4cc3559bf192ebb9c241a30c601b5b8b3eee6f1656dd4d26dfd4b0887a`)
- **Row Count:** 1,759 rows.
- **Unique Jobs:** 71 jobs. None appear in `resume_job_fit_train.csv` (0/71 overlap).
- **Unique Resumes:** 477 resumes. **476 appear in `resume_job_fit_train.csv` (99.79% overlap).**
- **Exact Pair Overlap:** 0 pairs appear in both train and test.

### 4.2 Why Was It Misdescribed?
The original dataset split was created using a **job-grouped split** (`GroupShuffleSplit` on `job_description_text`). In a job-grouped split, jobs are completely isolated between train and test. However, because candidates in the legacy synthetic dataset applied to multiple jobs across both partitions, candidates were repeated. Early reports noted "0 pair overlap" and "0 job overlap", which was misinterpreted in subsequent documentation as "dual-unseen".

### 4.3 Evaluation Implications
Because 99.79% of test resumes are seen during training:
- The model has already memorized candidate vocabulary, structure, formatting, and skill phrasing.
- A classifier evaluated on this test is measuring **unseen-job adaptation for known candidates**, NOT true double-blind matching.
- **Accuracy on this test (~46%–54%) reflects Job-Disjoint generalization.**

---

## 5. Construction Plan for a True Dual-Unseen Test Partition

Since no true dual-unseen test set of $N \ge 1,500$ exists in the legacy repository, a certified test partition must be formally constructed:

```
                  CONSTRUCTION OF TRUE DUAL-UNSEEN TEST BENCHMARK
+---------------------------------------------------------------------------------+
| 1. Candidate Source: Unseen Djinni Profiles (from 210,250 cv_df_eng inventory)  |
|    - 0% intersection with legacy core resumes (different candidate pool).       |
|    - 0% intersection with training profiles.                                    |
+---------------------------------------------------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
| 2. Job Source: Unseen Djinni Job Postings (from 141,897 jd_df_eng inventory)    |
|    - 0% intersection with legacy core jobs.                                     |
|    - 0% intersection with training job postings.                                |
+---------------------------------------------------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
| 3. Sampling & Stratification:                                                   |
|    - Target: N = 1,500 - 2,000 distinct pairs.                                  |
|    - Unique Candidates >= 500; Unique Jobs >= 300.                              |
|    - Multi-domain coverage (Backend, Frontend, DevOps, Data, QA, Cloud).        |
+---------------------------------------------------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
| 4. Dual-Blind Human Annotation & Consensus Adjudication:                        |
|    - 100% human-verified using PHASE12E3_ANNOTATION_RUBRIC_V2.                  |
|    - Cohen's Kappa >= 0.70 required. Zero synthetic ground truth.               |
+---------------------------------------------------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
| 5. Cryptographic Sealing & Isolation:                                           |
|    - Staged in manifests/v2/certified_dual_unseen_test.parquet                  |
|    - Frozen and air-gapped from all training, scaling, and feature selection.   |
+---------------------------------------------------------------------------------+
```

---

## 6. Reproducible Verification Code

The exact audit script used to verify these findings is committed to the repository at:
`scripts/run_forensic_split_id_audit.py`

To re-run and verify the forensic ID overlap independently:
```powershell
python scripts/run_forensic_split_id_audit.py
```
Outputs are permanently logged to:
`results/phase12e3_1/split_id_forensic_results.json`

---

## 7. Audit Conclusion & Mandates

1. **Terminology Correction:** Update all documentation, dashboards, and reporting to designate the 1,759-row test as the **"Official Job-Disjoint Test Set"**.
2. **Cease Dual-Unseen Claims on Legacy Test:** Do not cite the 1,759-row test as dual-unseen in any report, artifact, or dashboard.
3. **Dual-Unseen Status:** The repository currently has only a small internal validation dual-unseen fold ($N=296$). A full-scale test ($N \ge 1,500$) must be constructed and annotated before certifying true dual-unseen generalization.
