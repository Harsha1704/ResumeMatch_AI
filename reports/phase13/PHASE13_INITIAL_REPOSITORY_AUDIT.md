# ResumeMatch AI — Phase 13: Initial Repository, Baseline & Provenance Audit

**Date:** November 14, 2026  
**Auditor Roles:** Principal Machine Learning Engineer, NLP Research Engineer, Information Retrieval Specialist, Statistical Evaluation Scientist, MLOps and Reproducibility Engineer  
**Objective:** Perform a comprehensive Stage A pre-experimental repository inspection, verify production checkpoint hashes, validate split provenances, confirm label distributions, and reproduce historical comparators on the permitted Dual-Unseen validation dataset prior to developing the Phase 13 challenger architecture.

---

## 1. Production Artifact Pre-Experiment Preservation Audit

Before executing any experiments or creating new models, the production checkpoints and pipelines were hashed and verified. These files are strictly immutable and will not be overwritten:

| Artifact Path | File Size (Bytes) | SHA-256 Checksum | Pre-Experiment Status |
| :--- | :---: | :--- | :---: |
| `models/best_model.joblib` | 61,487 | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **VERIFIED & PRESERVED** |
| `models/feature_pipeline.joblib` | 270,105 | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **VERIFIED & PRESERVED** |
| `models/phase12f/challenger_model_phase12f.joblib` | 2,330,440 | `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766` | **VERIFIED & PRESERVED** |

---

## 2. Repository Infrastructure & Module Inventory

The repository provides a rich set of deterministic, leakage-safe components in `src/`:

```
D:\skillsync1\
├── data/
│   ├── raw/
│   │   ├── resume_job_fit_train.csv (6,488 rows, primary raw dataset)
│   │   ├── resume_job_fit_test.csv (1,759 rows, official test source)
│   │   ├── job_skill_set.parquet (2.5 MB, skill taxonomy database)
│   │   └── dataset_summary.json
│   └── external/djinni/ (Unlabelled Djinni corpus for domain adaptation)
├── manifests/v1/
│   ├── dual_unseen_train_v1.parquet (3,857 rows, 500 candidates, 221 jobs)
│   ├── dual_unseen_val_v1.parquet (297 rows, 296 evaluated pairs, 91 candidates, 52 jobs)
│   ├── job_disjoint_train_v1.parquet / job_disjoint_val_v1.parquet
│   ├── resume_disjoint_train_v1.parquet / resume_disjoint_val_v1.parquet
│   └── held_out_test_v1.parquet (1,759 rows, PERMANENTLY QUARANTINED)
├── src/
│   ├── preprocessing/
│   │   ├── text_cleaner.py (Deterministic text normalization and structural parsing)
│   │   └── skill_extractor.py (32 KB deterministic skill extraction, alias normalization, 8-category taxonomy)
│   ├── analysis/
│   │   ├── job_analyzer.py (NLP extractor for REQUIRED, PREFERRED, and UNSPECIFIED skill tiers)
│   │   ├── skill_gap.py (Mathematical skill gap accounting and Jaccard coverage)
│   │   ├── experience_analyzer.py (39 KB tenure parser, project extractor, unestablished experience handling)
│   │   └── matching_engine.py (Master deterministic matching orchestrator)
│   ├── features/
│   │   └── feature_pipeline.py (ResumeJobFeaturePipeline: TF-IDF n-grams + 15 dense structural features)
│   ├── phase12f/
│   │   ├── domain_adaptation.py (InfoNCE contrastive projector, skill co-occurrence graph)
│   │   ├── long_document_handler.py (Requirement-Gated Extractor for sequence budgeting)
│   │   └── models.py (BiEncoderSimilarityMatcher, HybridStackingClassifier)
│   └── models/
│       ├── train.py, evaluate.py, inference.py
└── experiments/
    ├── phase12f3_3/predictions/ (Physical prediction files for contrastive seeds 42–46)
    └── phase13/ (Workspace for Phase 13 model improvement)
```

---

## 3. Label Mappings & Permitted Dataset Distributions

Evaluation strictly operates under the **Dual-Unseen Protocol**, guaranteeing zero candidate overlap and zero job overlap between training and validation:

### Label Mapping (3-Class Taxonomy)
- `0`: **No Fit**
- `1`: **Potential Fit**
- `2`: **Good Fit**

### Class Distributions

| Dataset Split | File Path | Total Rows | No Fit | Potential Fit | Good Fit | Unique Candidates | Unique Jobs |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Dual-Unseen Train** | `manifests/v1/dual_unseen_train_v1.parquet` | **3,857** | 1,980 (51.3%) | 926 (24.0%) | 951 (24.7%) | 500 | 221 |
| **Dual-Unseen Val** | `manifests/v1/dual_unseen_val_v1.parquet` | **296** | 123 (41.6%) | 80 (27.0%) | 93 (31.4%) | 91 | 52 |

*Note on Validation Row Count:* `dual_unseen_val_v1.parquet` contains 297 rows. Pair `R_08e03096c790d399__J_230ff2f033d48f54` (row 46) was quarantined in Phase 12F due to contradictory duplicate labeling, leaving exactly 296 evaluated pairs.

---

## 4. Physical Contrastive Run Provenance (Seeds 42–46)

The five physical contrastive runs were verified directly from their execution artifacts in `experiments/phase12f3_3/predictions/`:
- All 5 files exist on disk with verified SHA-256 hashes.
- Each file contains exactly 296 evaluation rows matching `dual_unseen_val` row-by-row:
  - **Seed 42:** `contrastive_vs_raw_seed_42.csv` (SHA-256: `2953c9657af9...`, 136/296 correct, 45.95%)
  - **Seed 43:** `contrastive_vs_raw_seed_43.csv` (SHA-256: `7c10b7b62900...`, 135/296 correct, 45.61%)
  - **Seed 44:** `contrastive_vs_raw_seed_44.csv` (SHA-256: `215443fa7a34...`, 116/296 correct, 39.19%)
  - **Seed 45:** `contrastive_vs_raw_seed_45.csv` (SHA-256: `d3257bcfa6d4...`, 136/296 correct, 45.95%)
  - **Seed 46:** `contrastive_vs_raw_seed_46.csv` (SHA-256: `8b19ce8d9f13...`, 137/296 correct, 46.28%)
- **5-Seed Mean Accuracy:** **44.60%** (132.0 / 296 pairs).

---

## 5. Reproduction of Baseline Comparators on Dual-Unseen Validation Data

We reproduced the baseline comparators on the exact 296 evaluated pairs:

| Baseline Model | Source File / Checkpoint | Correct / 296 | Accuracy | Macro F1 | Balanced Acc | Good Fit Recall | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Production Baseline (LogReg)** | `models/best_model.joblib` / `phase12f2` | 109 / 296 | **36.82%** | 0.3284 | 0.3467 | 0.1398 (13/93) | **REPRODUCED** |
| **Raw SBERT Bi-Encoder** | `sentence-transformers/all-MiniLM-L6-v2` | 113 / 296 | **38.18%** | 0.3282 | 0.3467 | 0.1398 (13/93) | **REPRODUCED** |
| **Contrastive InfoNCE (Seed 42)** | `experiments/phase12f3/models/...` | 136 / 296 | **45.95%** | 0.3311 | 0.3962 | 0.1613 (15/93) | **REPRODUCED** |
| **Contrastive InfoNCE (5-Seed Mean)** | Seeds 42, 43, 44, 45, 46 | 132.0 / 296 | **44.60%** | 0.3307 | 0.3856 | 0.1505 (14/93) | **REPRODUCED** |

### Critical Baseline Weakness Identified: Good Fit Collapse
Across all historical baselines, **Good Fit Recall is severely depressed**:
- Production Baseline: only 13 of 93 Good Fit pairs are correctly identified (Recall = 13.98%).
- Raw SBERT: only 13 of 93 Good Fit pairs are identified (Recall = 13.98%).
- Contrastive InfoNCE: only 15 of 93 Good Fit pairs are identified (Recall = 16.13%).
All models disproportionately predict "No Fit" (160 to 180 predictions out of 296) and fail to capture genuine high-suitability matches.

### Key Targets for Phase 13 Architectural Improvement
1. **Skill Intelligence:** Integrate deterministic tier extraction (Required vs. Preferred vs. Unspecified) from `JobDescriptionAnalyzer` and normalized skill overlap from `SkillEngine`.
2. **Experience & Role Alignment:** Integrate tenure classification, project relevance, and role family matching from `ExperienceAnalyzer`.
3. **Semantic Fusion:** Combine SBERT semantic embeddings with structured skill/experience features.
4. **Calibrated Three-Class Prediction:** Train a gradient boosted decision tree (LightGBM/CatBoost) with class-balanced weighting and temperature/probability calibration to prevent Good Fit collapse and elevate Macro F1 above 0.45.
