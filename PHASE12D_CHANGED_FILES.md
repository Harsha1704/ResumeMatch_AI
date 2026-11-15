# Phase 12D — Changed Files & Audit Trail

## Summary of File Modifications
During Phase 12D (Permanent ML Evaluation Repair), all changes were strictly architectural and focused on split integrity, pre-evaluation leakage guards, reproducible evaluation pipelines, and regression testing.

The production model (`models/best_model.joblib`), Flask application routes, matching engine, and candidate evidence registry were held **strictly frozen and immutable**.

---

## 1. Split Manifest & Validation Engine (`manifests/v1/` & `src/evaluation/`)

| File Path | Action | Description |
| :--- | :---: | :--- |
| `src/evaluation/__init__.py` | **Created** | Package initialization exporting split validation and leakage guard APIs. |
| `src/evaluation/split_validator.py` | **Created** | Core split leakage validator, entity and pair overlap computer, cryptographic manifest verifier, and cache guard (`SplitLeakageError`). |
| `manifests/v1/manifest_v1.json` | **Created** | Master sealed manifest documenting SHA-256 hashes, record counts, and isolation contracts for all 7 split files. |
| `manifests/v1/job_disjoint_train_v1.parquet` | **Created** | Canonical job-disjoint training split ($N=5,462$, clean). |
| `manifests/v1/job_disjoint_val_v1.parquet` | **Created** | Canonical job-disjoint validation split ($N=778$, 42 unseen jobs). |
| `manifests/v1/held_out_test_v1.parquet` | **Created** | Canonical official held-out test split ($N=1,759$, 71 unseen jobs). |
| `manifests/v1/resume_disjoint_train_v1.parquet` | **Created** | Canonical resume-disjoint training split ($N=5,217$, clean). |
| `manifests/v1/resume_disjoint_val_v1.parquet` | **Created** | Canonical resume-disjoint validation split ($N=1,023$, 97 unseen resumes). |
| `manifests/v1/dual_unseen_train_v1.parquet` | **Created** | Canonical dual-unseen training split ($N=3,857$, clean). |
| `manifests/v1/dual_unseen_val_v1.parquet` | **Created** | Canonical dual-unseen validation split ($N=297$, 92 unseen resumes, 52 unseen jobs). |

---

## 2. Benchmark Scripts & Automated Regression Tests

| File Path | Action | Description |
| :--- | :---: | :--- |
| `scripts/generate_split_manifests_v1.py` | **Created** | Deterministic generator and cryptographic sealer for V1 split manifests. |
| `scripts/run_phase12d_evaluation.py` | **Created** | Master reproducible evaluation runner enforcing pre-evaluation guards, per-protocol model fitting, and prediction logging. |
| `tests/test_split_leakage_guards.py` | **Created** | 8 automated regression tests verifying active rejection of deliberate resume, job, and pair leakage, manifest corruption, and cache violations. |

---

## 3. Benchmark Outputs & Prediction Logs (`results/phase12d_experiments/`)

| File Path | Action | Description |
| :--- | :---: | :--- |
| `results/phase12d_experiments/reproducible_evaluation_results.json` | **Created** | Full benchmark metrics, confusion matrices, per-class F1, and isolation audits across all 4 protocols. |
| `results/phase12d_experiments/predictions/*.csv` (12 files) | **Created** | Auditable prediction logs containing pair hashes, actual labels, predicted labels, and class probabilities for every model and protocol. |

---

## 4. Phase 12D Audit Reports (Root Workspace)

| File Path | Action | Description |
| :--- | :---: | :--- |
| `PHASE12D_SPLIT_INTEGRITY.md` | **Created** | Report 1: Split integrity, immutable manifest architecture, and cryptographic checksums. |
| `PHASE12D_REPRODUCIBLE_EVALUATION.md` | **Created** | Report 2: Reproducible evaluation pipeline workflow, per-protocol model fitting, and tracking. |
| `PHASE12D_MODEL_COMPARISON.md` | **Created** | Report 3: Rigorous head-to-head comparison of Classical Baseline vs SBERT Config B vs Hybrid Config D across all 4 protocols. |
| `PHASE12D_TEST_RESULTS.md` | **Created** | Report 4: Automated regression test report (244/244 passed, 100%). |
| `PHASE12D_CHANGED_FILES.md` | **Created** | Report 5: This comprehensive audit trail and changed files list. |

---

## 5. Certified Production Status
- `models/best_model.joblib`: **FROZEN & CERTIFIED** (SHA-256: `1001BAAF42DB8832E1BA3E28EE9DA7146E59F1D2D1808C73C4F7587535B2ED4A`).
- Zero LLMs or external generative APIs introduced.
- Model promotion: **REJECTED** (Classical baseline achieves superior accuracy on the official held-out test split, 48.49% vs 46.73%).
- Overall Evaluation Repair Status: **PASS**.
