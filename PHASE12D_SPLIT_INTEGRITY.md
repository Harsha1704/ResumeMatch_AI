# Phase 12D — Split Integrity & Manifest Architecture

## Executive Summary
This document establishes the permanent cryptographic and algorithmic safeguards deployed to eliminate evaluation leakage in **ResumeMatch AI** at `D:\skillsync1`.

In Phase 12C, an independent audit revealed that previous resume-disjoint and dual-unseen experiments suffered from 88.74% and 84.12% training-pair overlap due to ad-hoc cross-split evaluation without retraining. Phase 12D permanently rectifies this flaw by establishing **immutable, versioned split manifests (`manifests/v1/`)**, an automated **`SplitLeakageError` pre-evaluation guard**, and **strict per-protocol model training isolation**.

---

## 1. Immutable Split Manifests (V1)
All evaluation partitions are permanently fixed, cryptographically hashed with SHA-256, and sealed in `manifests/v1/`.

- **Primary Source Dataset**: `data/raw/resume_job_fit_train.csv` (SHA-256: `b86fa488a21258019b5b2927e57c6b75ee16223b2075fc94cf8019688dfec557`)
- **Contradictory Label Filtering**: 6 confirmed contradictory pairs filtered deterministically from training partitions using exact MD5 pair hashes.
- **Master Manifest**: `manifests/v1/manifest_v1.json` (SHA-256: `9f2e34b94694c746f7a89fbff1a882dfa8ac79716afb484ddb26303feb40e287`)

### Manifest File Registry

| Partition File | Protocol | Role | Record Count | Unique Resumes | Unique Jobs | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `job_disjoint_train_v1.parquet` | `job_disjoint` | Train | 5,462 | 633 | 238 | `1a0bb01d84689bd4c0384bc225ec0d53c2ee1ae307779fdfa76f2b380277df60` |
| `job_disjoint_val_v1.parquet` | `job_disjoint` | Val | 778 | 373 | 42 | `8008cbb7d5fda228df776e27ebf279172e2cf573b9e4a30e84b9e2cb924fc8b9` |
| `held_out_test_v1.parquet` | `held_out_test`| Test | 1,759 | 477 | 71 | `d4319c1fb86f7708ce1d5a73e654eb6845348259463990dd283fa7a5cc33405f` |
| `resume_disjoint_train_v1.parquet`| `resume_disjoint`| Train | 5,217 | 546 | 280 | `08aa53fda660e3ccf8c36144e55e5b306b89694e43be4f51fae9488a445d4c8d` |
| `resume_disjoint_val_v1.parquet` | `resume_disjoint`| Val | 1,023 | 97 | 219 | `f3618ae092c029ca9a117b4c803f2a74c20fbfbc76a0868f02930217ec3ef7be` |
| `dual_unseen_train_v1.parquet` | `dual_unseen` | Train | 3,857 | 500 | 221 | `06ac7b0ff524475bb39ec880b9576c024d2d4c0628236718d09873d191ec4d8f` |
| `dual_unseen_val_v1.parquet` | `dual_unseen` | Val | 297 | 92 | 52 | `1b31ae0c5d05ddcca370c97e750ca8b0051e5e8e89445129646b9a84d41fa631` |

---

## 2. Pre-Evaluation Split Isolation Guard

The framework introduces an automated pre-evaluation validator: `src.evaluation.split_validator.validate_split_isolation`.

Before any model training, feature extraction, or inference occurs, the validator computes set intersections across resume texts, job description texts, and exact (resume, job) pairs. If any prohibited overlap is detected, execution halts immediately with a fatal `SplitLeakageError`.

### Mathematical Isolation Proofs Across Protocols

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SPLIT ISOLATION CONTRACT                           │
├─────────────────────┬───────────────────┬───────────────┬───────────────────┤
│ Protocol            │ Shared Resumes    │ Shared Jobs   │ Shared Pairs      │
├─────────────────────┼───────────────────┼───────────────┼───────────────────┤
│ Job-Disjoint Val    │ Allowed           │ STRICTLY 0    │ STRICTLY 0        │
│ Resume-Disjoint Val │ STRICTLY 0        │ Allowed       │ STRICTLY 0        │
│ Dual-Unseen Val     │ STRICTLY 0        │ STRICTLY 0    │ STRICTLY 0        │
│ Held-Out Test       │ Allowed           │ STRICTLY 0    │ STRICTLY 0        │
└─────────────────────┴───────────────────┴───────────────┴───────────────────┘
```

### Measured Overlap Verification on V1 Splits

1. **Job-Disjoint Validation (`job_disjoint_val_v1.parquet` against `job_disjoint_train_v1.parquet`)**:
   - Resumes Overlapping: 364 / 373 (97.59%) — Allowed (tests unseen jobs with seen candidates).
   - Jobs Overlapping: **0 / 42 (0.00%)** — Strictly Disjoint.
   - Exact Pairs Overlapping: **0 / 778 (0.00%)** — Strictly Disjoint.
2. **Resume-Disjoint Validation (`resume_disjoint_val_v1.parquet` against `resume_disjoint_train_v1.parquet`)**:
   - Resumes Overlapping: **0 / 97 (0.00%)** — Strictly Disjoint.
   - Jobs Overlapping: 219 / 219 (100.0%) — Allowed (tests unseen candidates with seen jobs).
   - Exact Pairs Overlapping: **0 / 1,021 (0.00%)** — Strictly Disjoint.
3. **Dual-Unseen Validation (`dual_unseen_val_v1.parquet` against `dual_unseen_train_v1.parquet`)**:
   - Resumes Overlapping: **0 / 92 (0.00%)** — Strictly Disjoint.
   - Jobs Overlapping: **0 / 52 (0.00%)** — Strictly Disjoint.
   - Exact Pairs Overlapping: **0 / 297 (0.00%)** — Strictly Disjoint.
4. **Held-Out Test (`held_out_test_v1.parquet` against `job_disjoint_train_v1.parquet`)**:
   - Resumes Overlapping: 475 / 477 (99.58%) — Allowed.
   - Jobs Overlapping: **0 / 71 (0.00%)** — Strictly Disjoint.
   - Exact Pairs Overlapping: **0 / 1,759 (0.00%)** — Strictly Disjoint.

---

## 3. Pipeline Transformation Isolation
In addition to data-level partitioning, learned transformations are strictly isolated:
- **TF-IDF Vocabulary**: Fitted strictly on the training partition (`tfidf.fit(train_texts)`). Tokens appearing exclusively in validation or test data are mapped to out-of-vocabulary and never bleed into feature weights.
- **StandardScalers**: Mean ($\mu$) and standard deviation ($\sigma$) parameters are estimated exclusively on training records. Validation features are transformed using `scaler.transform()`.
- **Class Balance & Calibrators**: Class weights and decision thresholds are learned solely on the training partition.

---

## 4. Embedding Cache Integrity Guard
The embedding cache `results/phase12b_embeddings/minilm_l6_v2_cache.npz` was validated using `validate_embedding_cache_keys`:
- **643 Unique Resumes**, **351 Unique Jobs**.
- **0 Label or Target Keys Serialized**: Confirmed zero target leakage.
- **Hash Format**: Verified 32-character hexadecimal MD5 hash keys mapping directly to normalized text content.
