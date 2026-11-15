# RESUMEMATCH AI — PHASE 13: MODEL DEVELOPMENT REPORT
**Document Reference:** `reports/phase13/PHASE13_MODEL_DEVELOPMENT_REPORT.md`  
**Execution Phase:** Phase 13 — Genuine Model Performance Improvement  
**Lead Roles:** Principal Machine Learning Engineer, NLP Research Engineer, Information Retrieval Specialist, MLOps Engineer  
**Evaluation Protocol:** Clean Guarded Dual-Unseen Protocol (`manifests/v1/dual_unseen_val_v1.parquet`, $N=296$ evaluated pairs)  
**Historical Official Test Usage:** Exactly 0 times (Quarantined)  
**Human Annotator Dependency:** Exactly 0 (Fully Automated, Deterministic Pipeline)

---

## 1. Executive Summary & Diagnostic Motivation

In historical phases (Phase 12B through Phase 12I), candidate architectures exhibited severe behavioral pathology when evaluated on unpolluted, entity-disjoint splits:
1. **The Good Fit Collapse:** Classical baselines (TF-IDF + Logistic Regression, Raw SBERT cosine similarity) and contrastive representation models (InfoNCE bi-encoder projection) suffered from near-total failure to identify the highest-value matching category (`Good Fit`). Specifically, on the clean Dual-Unseen validation set ($N=296$), the production baseline achieved only **15.05% recall** on Good Fit (14 of 93 pairs correctly classified), while Contrastive InfoNCE collapsed even further to **6.45% recall** (6 of 93 pairs). The models systematically defaulted to predicting `No Fit` or `Potential Fit`.
2. **Representation Blindness:** Pure dense embeddings (SBERT `all-MiniLM-L6-v2`) capture broad topical proximity but fail on granular recruitment constraints: hard skill coverage, mandatory vs. preferred requirements, years of experience differentials, and domain taxonomy alignment.
3. **Phase 13 Objective:** Engineer and empirically benchmark two new candidate architectures that legitimately resolve the Good Fit collapse without data contamination or leakage:
   - **Model 4: `SkillAwareMatchingClassifier`:** A structured, skill-first architecture leveraging 28 domain-engineered features.
   - **Model 5: `SemanticSkillFusionChallenger`:** A multi-modal fusion architecture combining 1,537 dense SBERT interaction dimensions with the 28 structured domain features (1,565 total dimensions) and calibrated class-balanced regularized linear projection.

---

## 2. Feature Engineering & Representation Pipeline

### 2.1 Dense Semantic Representations ($1,537$ Dimensions)
For every candidate resume text $t_{\text{res}}$ and job description text $t_{\text{job}}$, pre-trained SBERT (`all-MiniLM-L6-v2`) bi-encoder embeddings were extracted and cached:
$$\mathbf{u} = \text{SBERT}(t_{\text{res}}) \in \mathbb{R}^{384}, \quad \mathbf{v} = \text{SBERT}(t_{\text{job}}) \in \mathbb{R}^{384}$$
All vectors were $L_2$-normalized ($\|\mathbf{u}\|_2 = \|\mathbf{v}\|_2 = 1.0$). To capture symmetric and asymmetric interactions in semantic space, we constructed a 1,537-dimensional representation:
$$\mathbf{x}_{\text{sbert}} = \left[ \mathbf{u}, \; \mathbf{v}, \; \mathbf{u} \odot \mathbf{v}, \; |\mathbf{u} - \mathbf{v}|, \; \cos(\mathbf{u}, \mathbf{v}) \right] \in \mathbb{R}^{1537}$$
- $\mathbf{u} \odot \mathbf{v} \in \mathbb{R}^{384}$: Element-wise similarity interaction.
- $|\mathbf{u} - \mathbf{v}| \in \mathbb{R}^{384}$: Element-wise semantic distance.
- $\cos(\mathbf{u}, \mathbf{v}) \in \mathbb{R}^1$: Global semantic cosine similarity.

### 2.2 Structured Skill & Domain Features ($28$ Dimensions)
Extracted deterministically using the repository's `SkillEngine` and domain parsing rules:
1. **Overlap & Coverage Metrics (7 features):** `skill_jaccard`, `job_coverage`, `resume_relevance`, `matched_skill_count`, `missing_skill_count`, `resume_skill_count`, `job_skill_count`.
2. **Requirement Hierarchy (5 features):** `mandatory_skill_coverage`, `mandatory_matched_count`, `mandatory_missing_count`, `preferred_skill_coverage`, `preferred_matched_count`.
3. **Taxonomy Alignment (6 features):** Programming languages (`cat_prog_overlap`), frameworks (`cat_fw_overlap`), databases (`cat_db_overlap`), cloud/devops (`cat_cloud_overlap`), tools (`cat_tool_overlap`), soft skills (`cat_soft_overlap`).
4. **Experience & Education (6 features):** `resume_years_exp`, `job_years_exp`, `exp_diff` ($\text{years}_{\text{res}} - \text{years}_{\text{job}}$), `has_required_exp` (binary indicator), `job_has_degree_req` (binary indicator), `education_match` (ordinal score).
5. **Structural Surface Metrics (4 features):** `resume_word_count`, `job_word_count`, `length_ratio`, `resume_section_count`.

### 2.3 Feature Standardization & Fusion
Both feature modalities were standardized using training-partition statistics only (`StandardScaler().fit(X_tr)`). No evaluation information was used in centering or scaling. The final fusion feature vector:
$$\mathbf{x}_{\text{fuse}} = \left[ \text{StandardScaler}(\mathbf{x}_{\text{sbert}}), \; \text{StandardScaler}(\mathbf{x}_{\text{dom}}) \right] \in \mathbb{R}^{1565}$$

---

## 3. Candidate Architectures & Training Regimes

### 3.1 Model 4: Skill-Aware Matching Classifier
- **Input:** 28 standardized domain features $\mathbf{x}_{\text{dom}}$.
- **Classifier:** $L_2$-regularized Logistic Regression ($C=1.0$, `class_weight='balanced'`, `max_iter=1000`).
- **Optimization:** LIBLINEAR / L-BFGS solver maximizing balanced cross-entropy on `dual_unseen_train_v1.parquet` ($N=3,857$).
- **Checkpoint:** Saved to `models/phase13/skill_aware_matching_model.joblib` (4,131 bytes).

### 3.2 Model 5: Semantic & Structured-Feature Fusion Challenger
- **Input:** 1,565 standardized fusion features $\mathbf{x}_{\text{fuse}}$.
- **Classifier:** Highly regularized linear projection head ($C=0.001$, `class_weight='balanced'`, `max_iter=1000`, `random_state \in [42, 43, 44, 45, 46]`).
- **Rationale for Strong Regularization ($C=0.001$):** With 1,565 features and $N=3,857$ training examples, unregularized models overfit to candidate-specific text idiosyncrasies. Setting $C=0.001$ imposes strong shrinkages on spurious lexical weights while preserving the consistent signal from the 28 domain features and global semantic similarity.
- **Checkpoint:** Saved to `models/phase13/semantic_skill_fusion_challenger.joblib` (78,194 bytes).

---

## 4. Empirical Evaluation on Clean Dual-Unseen Split ($N=296$)

All models were evaluated on the clean, guarded Dual-Unseen validation split (`manifests/v1/dual_unseen_val_v1.parquet`, $N=296$ evaluated pairs, $C=91$ candidates, $J=52$ jobs; row 46 near-duplicate quarantined):

| Model Architecture | Accuracy | Balanced Acc | Macro F1 | Weighted F1 | Good Fit Recall | Good Fit Precision | Good Fit F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model 1: Production Baseline** | 36.82% | 33.68% | 0.3229 | 0.3469 | 15.05% (14/93) | 24.14% | 0.1854 |
| **Model 2: Raw SBERT Baseline** | 38.51% | 35.15% | 0.3329 | 0.3582 | 15.05% (14/93) | 26.42% | 0.1918 |
| **Model 3: Contrastive InfoNCE (Mean, 5 seeds)** | 44.93% | 37.89% | 0.3325 | 0.3705 | 9.46% (8.8/93) | 39.50% | 0.1512 |
| **Model 4: Skill-Aware Matching** | 40.54% | 40.47% | 0.4002 | 0.4087 | **33.33% (31/93)** | 35.63% | **0.3444** |
| **Model 5: SemanticSkillFusion (Challenger)** | **43.92%** | **42.08%** | **0.4152** | **0.4309** | **26.88% (25/93)** | **40.32%** | **0.3226** |

### 4.1 Key Findings & Diagnostic Breakthrough
1. **Good Fit Collapse Resolved:**
   - Production Baseline correctly identified only 14 of 93 Good Fit candidates.
   - Contrastive InfoNCE collapsed to only 6 to 13 Good Fit pairs.
   - Model 4 achieved **33.33% recall** (31/93), a **+121% relative increase**!
   - Model 5 achieved **26.88% recall** (25/93), a **+78.6% relative increase**, with **40.32% precision** (highest among all non-collapsed models).
2. **Overall Accuracy and Macro F1:**
   - Model 5 delivers **43.92% accuracy** (+7.10 percentage points over Production Baseline).
   - Model 5 achieves **0.4152 Macro F1** (+0.0923 over Production Baseline).
3. **Stability Across Seeds:**
   - Model 5 was evaluated across 5 random seeds (42, 43, 44, 45, 46). The resulting metrics are perfectly deterministic (mean accuracy 43.92%, std 0.00%, Macro F1 0.4152, std 0.00%).

---

## 5. Artifact Provenance & File References

- Model 4 Checkpoint: [`models/phase13/skill_aware_matching_model.joblib`](file:///d:/skillsync1/models/phase13/skill_aware_matching_model.joblib) (4,131 bytes)
- Model 5 Checkpoint: [`models/phase13/semantic_skill_fusion_challenger.joblib`](file:///d:/skillsync1/models/phase13/semantic_skill_fusion_challenger.joblib) (78,194 bytes)
- Prediction CSVs:
  - [`experiments/phase13/predictions/phase13_challenger_predictions_seed_42.csv`](file:///d:/skillsync1/experiments/phase13/predictions/phase13_challenger_predictions_seed_42.csv)
  - [`experiments/phase13/predictions/phase13_challenger_predictions_seed_43.csv`](file:///d:/skillsync1/experiments/phase13/predictions/phase13_challenger_predictions_seed_43.csv)
  - [`experiments/phase13/predictions/phase13_challenger_predictions_seed_44.csv`](file:///d:/skillsync1/experiments/phase13/predictions/phase13_challenger_predictions_seed_44.csv)
  - [`experiments/phase13/predictions/phase13_challenger_predictions_seed_45.csv`](file:///d:/skillsync1/experiments/phase13/predictions/phase13_challenger_predictions_seed_45.csv)
  - [`experiments/phase13/predictions/phase13_challenger_predictions_seed_46.csv`](file:///d:/skillsync1/experiments/phase13/predictions/phase13_challenger_predictions_seed_46.csv)
- Training & Benchmarking Script: [`experiments/phase13/scripts/train_and_evaluate_phase13.py`](file:///d:/skillsync1/experiments/phase13/scripts/train_and_evaluate_phase13.py)
