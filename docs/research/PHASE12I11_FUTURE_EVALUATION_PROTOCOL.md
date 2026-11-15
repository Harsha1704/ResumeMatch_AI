# ResumeMatch AI — Phase 12I.11: Future Evaluation Protocol & Pre-Registration Standards

**Date:** November 14, 2026  
**Auditor Roles:** Principal ML Evaluation Scientist, Data Governance Engineer, Statistical Evaluation Scientist  
**Version:** 2.0.0-PreRegistration  
**Scope:** Architecture search, hyperparameter optimization, threshold calibration, and benchmark certification for future ResumeMatch AI iterations

---

## 1. Principles of Future Model Evaluation

To eliminate data leakage, adaptive selection bias, and clustering variance artifacts, all future ResumeMatch AI modeling must adhere strictly to this protocol.

```
========================================================================================
                          FUTURE EVALUATION ARCHITECTURE
========================================================================================
[Raw Corpus Pool]
       |
       +---> [Training & Development Data] (Strictly isolated)
       |           |
       |           +---> Nested Grouped Cross-Validation (K-Fold GroupKFold)
       |           |       - Preprocessing & Scalers fit INSIDE training folds
       |           |       - Feature Selection fit INSIDE training folds
       |           |       - Temperature & Threshold calibration INSIDE training folds
       |           |
       |           +---> Model & Hyperparameter Selection strictly on OOF metrics
       |
       +---> [Frozen Pre-Registered Final Benchmark]
                   - Dual-Unseen Entity Separation (0% candidate, 0% job overlap)
                   - Immutable SHA-256 Manifest Frozen BEFORE model training
                   - Single-Query Evaluation Gate (No iterative query loop)
                   - Two-Way Clustered Bootstrap Inference (Cameron-Gelbach-Miller)
========================================================================================
```

---

## 2. Seven Mandatory Evaluation Standards

### Standard 1: Physical Data Separation
Training/development data and final evaluation data must be physically partitioned into separate, versioned manifests before any model exploration begins.

### Standard 2: Nested Grouped Cross-Validation for Tuning
All architecture comparison, hyperparameter optimization, and threshold calibration must be performed using **nested grouped cross-validation**:
- For candidate-transfer modeling: GroupKFold on `candidate_id`.
- For job-transfer modeling: GroupKFold on `job_id`.
- For dual-transfer modeling: Two-way block partitioning (bipartite cluster cross-validation).
The official evaluation split may **never** be used for threshold tuning or checkpoint picking.

### Standard 3: Strict Encapsulation of Learned Transformations
All data transformations must be fit strictly on the inner training folds:
- TF-IDF vectorizers, PCA, and standard scalers.
- Feature selection masks and correlation filters.
- Temperature scaling parameters ($\tau$) and probability thresholds.
Applying any fit transformation across fold boundaries or onto evaluation splits constitutes fatal leakage.

### Standard 4: Full Transparency on External Corpora
Any self-supervised pre-training, contrastive representation learning, or domain adaptation using unlabelled external datasets (e.g., Djinni pool) must be fully logged:
- Explicit corpus SHA-256 and pair counts.
- Strict hashing audit confirming 0% entity overlap with final evaluation sets.

### Standard 5: Pre-Registration & Manifest Freezing
Before candidate models are trained:
1. The evaluation manifest (e.g., `manifests/v2/dual_unseen_benchmark_v2.parquet`) must be generated, checked for disjointness, and frozen with a published SHA-256 hash.
2. The primary metric and statistical test must be pre-registered (e.g., paired difference under Cameron-Gelbach-Miller two-way cluster bootstrap with $\alpha=0.05$).

### Standard 6: Single-Query Final Evaluation Gate
The frozen evaluation split may be queried **exactly once** per release candidate:
- Multiple iterations, sequential trial-and-error, or post-hoc threshold adjustment on the final evaluation set are strictly prohibited.
- If a candidate fails, subsequent research must return to the development folds.

### Standard 7: Honest Acknowledgment of Dataset Limitations
If an external, genuinely independent dataset is unavailable:
- The limitation must be explicitly documented in all reports.
- Recycled, re-split, or re-partitioned splits of existing data must **never** be described as "independent external benchmarks".

---

## 3. Production Checkpoint Promotion Criteria

A challenger model may only be promoted to replace `models/best_model.joblib` if it satisfies all 4 promotion gates:

| Gate | Criterion | Threshold | Verification Method |
| :---: | :--- | :--- | :--- |
| **1** | **Generalization Gain** | $\ge +4.0$ percentage points over baseline | Evaluated on frozen pre-registered dual-unseen split |
| **2** | **Clustered Statistical Significance** | 95% Confidence Interval strictly bounds away from zero | Cameron-Gelbach-Miller (2011) two-way clustered bootstrap ($B=10,000$) |
| **3** | **Non-Regression on Historical Sets** | No regression ($< -1.0$ pp) on job-disjoint and resume-disjoint sets | Evaluated on frozen historical splits |
| **4** | **Latency & Model Footprint** | Latency $< 50$ ms per pair; Checkpoint size $< 50$ MB | Automated latency & footprint benchmark |

---

## 4. Operational Sign-Off

This protocol is certified and locked as the official standard for Phase 12I.11 and all subsequent development phases.
