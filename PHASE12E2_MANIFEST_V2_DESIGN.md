# ResumeMatch AI — Phase 12E-2: Manifest V2 Partition Design & Zero-Leakage Architecture

**Document ID:** `PHASE12E2-MANIFEST-V2`  
**Classification:** MLOps Data Partitioning Architecture & Evaluation Integrity Standard  
**Architect:** Principal MLOps Architect & Independent Evaluation Auditor  
**Effective Version:** Manifest V2.0.0-rc  
**Target Repository:** `D:\skillsync1`  

---

## 1. Executive Design Principles

Evaluation leakage in recruitment machine learning typically occurs not through careless code, but through subtle entity and bipartite graph dependencies:
1. When resumes appear across multiple pairs, a standard random K-fold split places the *same candidate's text* in both training and test folds. The model learns candidate-specific phrasing rather than generalizable compatibility rules.
2. When jobs appear across multiple pairs, the model memorizes idiosyncratic requirements of specific employers.
3. In Phase 12B, an 84.12% pair overlap caused an artificial 85.19% dual-unseen metric that collapsed to 36.70% upon proper zero-leakage retraining.

**Manifest V2 permanently eliminates all four vectors of evaluation contamination.**

---

## 2. Manifest V2 Bipartite Graph Partitioning Model

Manifest V2 enforces cryptographic, entity-disjoint boundaries between Candidate Profiles ($U$) and Job Descriptions ($V$):

```
       CANDIDATE PROFILES (U)                      JOB DESCRIPTIONS (V)
  ┌───────────────────────────────┐           ┌───────────────────────────────┐
  │ U_train: 80% Candidates       │           │ V_train: 80% Jobs             │
  │ (Resumes seen during training)│           │ (Jobs seen during training)   │
  └───────────────┬───────────────┘           └───────────────┬───────────────┘
                  │                                           │
                  ▼                                           ▼
          TRAINING PARTITION                           JOB-DISJOINT VAL
      Pairs: (U_train x V_train)                   Pairs: (U_train x V_val)
      - Used strictly for training                 - Evaluates novel jobs
      - 0% Job Overlap with Test                   - 0% Job Overlap with Train
                  │                                           │
  ┌───────────────┴───────────────┐           ┌───────────────┴───────────────┐
  ▼                               ▼           ▼                               ▼
RESUME-DISJOINT VAL       DUAL-UNSEEN VAL           OFFICIAL HELD-OUT TEST GATE
Pairs: (U_val x V_train)  Pairs: (U_val x V_val)    Pairs: (U_test x V_test)
- Evaluates novel CVs     - NEITHER CV NOR JOB      - The Primary Release Gate
- 0% CV Overlap w/ Train    appeared in training    - 71 Frozen Unseen Jobs
                          - Extreme boundary test   - ZERO Test-Set Tuning Allowed
```

---

## 3. Four Certified Evaluation Protocols

| Protocol ID | Candidate Overlap Guarantee | Job Overlap Guarantee | Exact Pair Overlap | Primary Evaluation Metric | Scientific Simulation |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Protocol 1: Job-Disjoint Validation** | Permitted ($\le 98\%$) | **0.0% (Strictly Disjoint)** | **0.00%** | Macro F1 & 3-Class Accuracy | Platform employer posts novel vacancy for existing applicant pool. |
| **Protocol 2: Resume-Disjoint Validation** | **0.0% (Strictly Disjoint)** | Permitted ($100\%$) | **0.00%** | Macro F1 & 3-Class Accuracy | New candidate signs up and applies to existing employer vacancies. |
| **Protocol 3: Dual-Unseen Validation** | **0.0% (Strictly Disjoint)** | **0.0% (Strictly Disjoint)** | **0.00%** | Macro F1 & Balanced Accuracy | Platform expands into a completely new city or industry vertical. |
| **Protocol 4: Official Held-Out Test Gate** | Permitted ($\le 99\%$) | **0.0% (Strictly Disjoint)** | **0.00%** | 3-Class Accuracy & Macro F1 | The official benchmark gate required for production promotion. |

---

## 4. Separation of Core Legacy Benchmark from Expanded Corpora

To maintain backward comparability with Phase 1–12 benchmarks while scaling to Djinni:
1. **Core Legacy Benchmark ($N=8,000$):**
   - Kept in its own sub-namespace: `manifests/v2/core_8k/`.
   - The 71 unseen jobs in `data/raw/resume_job_fit_test.csv` ($N=1,759$) remain an **immutable, untouched reference gate**.
2. **Expanded Research Benchmark (Djinni Ingestion):**
   - Stored under: `manifests/v2/expanded_djinni/`.
   - Only human-audited, annotated pairs from `data/external/djinni/` enter the validation/test splits.
   - Any runner-up hard negatives mined from unlabelled Djinni pools are restricted **strictly to the training partition** (`train_v2.parquet`).

---

## 5. Non-Negotiable Leakage Rejection Gates

Before any model training script is permitted to load a batch from Manifest V2, the automated validator `src/evaluation/split_validator.py` executes pre-flight assertions:

```python
# PRE-FLIGHT LEAKAGE ASSERTIONS (Enforced in Code)
assert len(train_jobs.intersection(val_jobs)) == 0, "FATAL: Job leakage detected in Job-Disjoint Split!"
assert len(train_resumes.intersection(val_resumes)) == 0, "FATAL: Resume leakage detected in Resume-Disjoint Split!"
assert len(train_pairs.intersection(val_pairs)) == 0, "FATAL: Exact-pair leakage detected!"
assert len(train_pairs.intersection(test_pairs)) == 0, "FATAL: Contamination of Official Test Gate!"
```

If any condition evaluates to `False`, the system raises a `SplitLeakageError` and terminates the run immediately.

---

## 6. Official Test Gate Protection Rules
- **Rule 1: No Test-Set Hyperparameter Tuning.** Hyperparameters (learning rates, weight decay, classification thresholds) must be tuned exclusively on the validation partitions.
- **Rule 2: No Hard-Negative Mining on Test Candidates.** Mined runner-up negatives must never be drawn from the candidate or job pools assigned to the test gate.
- **Rule 3: No Synthetic Hallucinations in Test.** Only verified, human-adjudicated pairs are permitted in the held-out test partition.
- **Rule 4: One-Way Release Gate.** A new candidate model is promoted to replace `models/best_model.joblib` ONLY IF its official test set Macro F1 strictly exceeds 0.55 and accuracy exceeds 50.43% without latency regressions.
