# RESUMEMATCH AI — PHASE 12F.3.2: FINAL FORENSIC INTEGRITY & STATISTICAL RECONCILIATION

**Standard:** Targeted Forensic Audit, Mathematical & Code-Level Verification, Exact Distributional Significance Testing  
**Audit Directory:** `D:\skillsync1`  
**Auditor Roles:** Independent ML Auditor, MLOps Integrity Engineer, Statistical Research Scientist, Data Leakage Specialist  
**Official Release Decision:** **`CONDITIONALLY CERTIFIED`** (Production checkpoint strictly preserved; promotion of challenger model withheld)

---

## 1. Executive Summary & Verification Decisions

Phase 12F.3.2 provides the definitive, evidence-backed reconciliation of all remaining contradictions in the Phase 12F.3 and 12F.3.1 reports. All production binaries, feature pipelines, and physical manifests were audited on disk without altering a single byte.

| Audit Mandate | Dispute / Contradiction | Forensic Evidence & Certified Ground Truth | Scientific Verdict |
| :--- | :--- | :--- | :---: |
| **Production Checkpoint Shape** | Phase 12F.3: `(3, 778)` vs Phase 12F.3.1: `(3, 2518)` | **Exact Loaded Checkpoint: `(3, 2518)`**<br>SHA-256: `1001baaf...` (61,487 bytes)<br>Pipeline: `models/feature_pipeline.joblib` (2,500 TF-IDF + 18 dense features) | **RESOLVED & CERTIFIED:** `(3, 778)` was an erroneous documentation typo in 12F.3 prose. Checkpoint file has never changed. |
| **Dual-Unseen Entity Census** | Phase 12F.2: 482 res / 226 jobs vs 12F.3.1: 1,223 res / 221 jobs | **Physical Manifest Reality:**<br>3,857 physical rows<br>**500 unique raw resume IDs** (499 normalized text hashes)<br>**221 unique raw job IDs** (221 normalized text hashes) | **RECONCILED:** Manifest on disk has always contained exactly 500 resumes & 221 jobs. Prior figures were clerical draft errors. |
| **Contrastive Confidence Interval** | Reported `[+4.04%, +8.80%]` interval method | **Proper Student-t 95% CI (df=4): `[+2.65%, +10.18%]`**<br>**Paired Bootstrap 95% CI (Seed 42): `[+1.69%, +13.52%]`**<br>**McNemar Exact Test: $p = 0.0152$** | **METHODOLOGICALLY CORRECTED:** Previous interval improperly used normal $z=1.96$ with $N=5$. Positive gain confirmed. |
| **Contrastive Code Leakage Audit** | Risk of validation label/pair contamination | **All 7 leakage assertions passed (100% compliance)**<br>Zero validation label/pair access<br>InfoNCE negatives strictly in-batch training | **CERTIFIED LEAK-FREE** |
| **Scientific Claim Corrections** | Inappropriate "ceiling" & "impossible" rhetoric | Reframed to empirical statements bounded by current architecture and test power | **STANDARDIZED & ACCURATE** |
| **Production Checkpoint Gate 0** | Preservation of production model | Binary SHA-256: `1001baaf...`, Size: 61,487 bytes<br>Reference inputs: Pair 1 $\to$ Good Fit (0.8680) | **CERTIFIED UNCHANGED PRODUCTION CHECKPOINT** |

---

## 2. Production Checkpoint Identity Investigation (CRITICAL)

### 2.1 Direct Binary & Environment Inspection
- **Python Version:** 3.14.8 (tags/v3.14.8, Sep 30 2026)
- **Scikit-Learn Version:** 1.9.1
- **File Path:** `D:\skillsync1\models\best_model.joblib`
- **Physical Size:** **61,487 bytes**
- **SHA-256 Checksum:** `1001BAAF42DB8832E1BA3E28EE9DA7146E59F1D2D1808C73C4F7587535B2ED4A`
- **Loaded Object Type:** `sklearn.linear_model._logistic.LogisticRegression`
- **Class MRO:** `LogisticRegression` $\to$ `CallbackSupportMixin` $\to$ `LinearClassifierMixin` $\to$ `ClassifierMixin` $\to$ `BaseEstimator` $\to$ `object`
- **Pipeline Structure:** Standalone estimator (`hasattr(model, 'steps') == False`).

### 2.2 Model Architecture & Feature Dimensions
```python
model = joblib.load('models/best_model.joblib')
classes = ['Good Fit', 'No Fit', 'Potential Fit']
n_features_in_ = 2518
coef_.shape = (3, 2518)
intercept_ = [1.83103857, -2.97741569, 1.14637712]
```

### 2.3 Feature Pipeline Lineage
The production model receives inputs transformed by `models/feature_pipeline.joblib`:
- **File Size:** 270,105 bytes
- **SHA-256 Checksum:** `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6`
- **Pipeline Type:** `src.features.feature_pipeline.ResumeJobFeaturePipeline`
- **Composition:**
  - `vectorizer`: `TfidfVectorizer` (2,500 word n-gram features)
  - `scaler`: `StandardScaler` (15 scaled structural features + 3 unscaled categorical flags = 18 dense features)
  - **Total Extracted Features:** $2,500 + 18 = 2,518$ features.

### 2.4 Prediction Consistency on Fixed Reference Inputs

| Reference Pair | Candidate Summary | Job Summary | Predicted Class | Class Probabilities (GF / NF / PF) |
| :---: | :--- | :--- | :---: | :---: |
| **Pair 1** | Python Dev (5 yrs Django, Docker, AWS) | Python Software Engineer (SQL, Docker, Cloud) | **Good Fit** | `[0.868015, 0.017209, 0.114776]` |
| **Pair 2** | Senior Accountant (CPA, 10 yrs audit) | Staff Data Scientist (PhD ML, PyTorch, LLMs) | **No Fit** | `[0.022762, 0.961382, 0.015856]` |
| **Pair 3** | Entry marketing graduate (internship) | Python Software Engineer (SQL, Docker, Cloud) | **Good Fit** | `[0.549396, 0.136794, 0.313810]` |

### 2.5 Forensic Conclusion on the (3, 778) vs (3, 2518) Discrepancy
The citation `(3, 778)` in Phase 12F.3 report prose was an **accidental clerical typo** during report authoring, caused by transcription contamination from the row count of `job_disjoint_val_v1.parquet` ($N=778$). The physical production model binary `models/best_model.joblib` (SHA-256 `1001baaf...`) has **never possessed 778 features** and has always had shape `(3, 2518)`.

---

## 3. Dual-Unseen Entity Identity Reconciliation

A forensic investigation of `dual_unseen_train_v1.parquet` ($N=3,857$) was performed to resolve the conflicting counts of resumes (482 vs 500 vs 1,223) and jobs (221 vs 226):

### 3.1 Certified Entity Census of `dual_unseen_train_v1.parquet`
- **Physical Rows:** 3,857
- **Unique Raw Resume IDs (`resume_id`):** **500**
- **Unique Normalized Resume Text Hashes (`norm_hash`):** **499**
- **Near-Duplicate Resume Cluster:** Exactly 1 pair of IDs shares an identical normalized document hash:
  - Cluster `45f4d94a4a906cfaa31c928b0e20fbc8`: IDs `R_3ed5dbf090962b7b` and `R_6e9fcafc88feaa96`.
- **Unique Raw Job IDs (`job_id`):** **221**
- **Unique Normalized Job Text Hashes:** **221**
- **Unique Exact Pairs:** 3,851 (6 pairs contain near-duplicate texts).

### 3.2 Root Cause of Historical Discrepancies
1. **Resumes (482 vs 500):** In Phase 12F.2, exploratory code filtered out 18 singleton resumes before final split creation, noting "482 core candidates". However, the physical split on disk committed in manifest v1 retained all 500 candidates.
2. **Jobs (226 vs 221):** In Phase 12F.2, an external unpartitioned pilot pool containing 5 supplementary jobs was temporarily cited before finalizing the 221-job bipartite cut.
3. **Erroneous "1,223 Raw Resume IDs" in 12F.3.1 Table:** In the Phase 12F.3.1 Section 2.1 markdown table, the number 1,223 was mistakenly copied from a draft script aggregating candidate IDs across the Job-Disjoint train and val splits. The physical manifest on disk has always contained exactly 500 unique resume IDs.

---

## 4. Contrastive Representation Statistical Reconciliation

In Phase 12F.3.1, a 95% confidence interval of `[+4.04%, +8.80%]` was reported for contrastive downstream accuracy gain.

### 4.1 Root Cause of Previous Calculation
The interval `[+4.04%, +8.80%]` was derived using the large-sample asymptotic normal approximation:
$$\text{CI} = \bar{d} \pm 1.96 \times \frac{\sigma_{\text{pop}}}{\sqrt{N}} = 0.0642 \pm 1.96 \times \frac{0.0271}{\sqrt{5}} = [0.0404, 0.0880]$$
This calculation had two statistical defects:
1. It used population standard deviation ($\text{ddof}=0$, $\sigma = 0.0271$) instead of sample standard deviation ($\text{ddof}=1$, $s = 0.0303$).
2. For $N=5$ training seeds, the normal critical value ($z=1.96$) severely underestimates small-sample uncertainty. The Student-t distribution with $df = 4$ ($t_{0.975} = 2.776$) must be used.

### 4.2 Rigorous Cross-Seed & Paired Statistical Tests

| Metric / Test | Value / Interval | Statistical Interpretation |
| :--- | :---: | :--- |
| **5 Paired Accuracy Deltas** | `[+7.77%, +7.43%, +1.01%, +7.77%, +8.11%]` | Contrastive projection outperforms raw SBERT on 5 of 5 seeds |
| **Mean Accuracy Delta ($\bar{d}$)** | **+6.42%** (+0.0642) | Substantial empirical accuracy advancement |
| **Sample Standard Deviation ($s$, ddof=1)** | **3.03%** (0.0303) | Measure of cross-seed representation variance |
| **Standard Error of Mean (SEM)** | **1.36%** (0.0136) | Sampling error of the mean across seeds |
| **Certified Student-t 95% CI (df=4)** | **`[+2.65%, +10.18%]`** | Strictly positive; lower bound $> 0$ across initialization seeds |
| **Validation Paired Bootstrap 95% CI** | **`[+1.69%, +13.52%]`** | 10,000 resamples on Seed 42 across $N=296$ validation pairs |
| **McNemar's Exact Binomial Test** | Discordant: 83 ($b=30, c=53$)<br>**$p = 0.0152$** | **Statistically significant at $\alpha = 0.05$** ($p < 0.05$) |
| **Macro F1 Delta (Mean ± Std)** | **+0.0025 ± 0.0365** | Macro F1 remains neutral due to class decision boundary shifts |
| **Balanced Accuracy Delta (Mean ± Std)** | **+3.89% ± 3.09%** | Positive cross-class representation improvement |

### 4.3 Uncertainty Separation
- **Training-Seed Variation:** Yields a Student-t interval of `[+2.65%, +10.18%]`.
- **Validation-Sample Uncertainty:** Evaluated on the $N=296$ sample pairs, paired bootstrap yields `[+1.69%, +13.52%]`, and McNemar's exact test confirms $p = 0.0152 < 0.05$.
- **Conclusion:** Downstream representation gain from the train-only InfoNCE contrastive projection is **statistically verified and robust** to both seed initialization and validation sampling.

---

## 5. Contrastive Representation Code-Level Leakage Audit

To guarantee that the +6.42% downstream accuracy gain is mathematically legitimate and leak-free, `scripts/phase12f3_1/reproduce_contrastive_downstream.py` was forensically audited:

```python
def train_contrastive_encoder_on_train_only(u_tr, v_tr, y_tr, seed=42):
    # Only training data tensors enter the DataLoader
    pos_mask = (y_tr == "Good Fit") | (y_tr == "Potential Fit")
    u_pos = torch.tensor(u_tr[pos_mask], dtype=torch.float32)
    v_pos = torch.tensor(v_tr[pos_mask], dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(u_pos, v_pos)
    loader = torch.utils.data.DataLoader(dataset, batch_size=128, shuffle=True, drop_last=True)
    ...
```

### Certified Leakage Invariants:
1. **Training-Only Fit:** Projector network weights are updated strictly using `u_pos` and `v_pos` derived from `dual_unseen_train_v1.parquet`.
2. **Zero Validation Label Access:** `y_vl` is never passed to or referenced by `train_contrastive_encoder_on_train_only`.
3. **Zero Test Label Access:** `held_out_test_v1.parquet` is neither loaded nor transformed.
4. **Zero Entity Overlap:** Resume text hash overlap = 0; Job text hash overlap = 0.
5. **In-Batch Negatives Strictly Training-Derived:** In the InfoNCE loss matrix (`sim = torch.matmul(z_u, z_v.T) / 0.07`), negative examples are strictly other training job descriptions present in the mini-batch.
6. **Feature Normalization Isolated:** `StandardScaler` is fitted on training representations (`StandardScaler().fit(X_proj_tr)`), and used in inference-only mode on validation representations.
7. **No Hyperparameter Snooping:** Network architecture (Linear 384 $\to$ 256 $\to$ LayerNorm $\to$ ReLU $\to$ Linear 128 $\to$ L2 norm) and optimization hyperparameters ($\tau=0.07, \text{lr}=10^{-3}, 10 \text{ epochs}$) were fixed a priori.

Full audit records preserved in [contrastive_leakage_audit.json](file:///d:/skillsync1/experiments/phase12f3_2/results/contrastive_leakage_audit.json).

---

## 6. Scientific Claim Corrections in Documentation

To adhere to rigorous empirical standards, hyperbolic and ungrounded statements in project documentation were corrected:

1. **"True Generalization Ceiling of 42–45%" Reframed:**
   - *Previous:* "The true Dual-Unseen generalization ceiling is certified at ~42–45%."
   - *Corrected:* "Under current empirical benchmarks on Dual-Unseen candidate-job pairs ($N=296$), models trained with frozen general-domain encoders (such as `all-MiniLM-L6-v2`) and tabular stacking achieve ~42–45% accuracy."
2. **"80%+ is Scientifically Impossible" Reframed:**
   - *Previous:* "80%+ accuracy is scientifically impossible."
   - *Corrected:* "Reaching higher performance targets (such as 80%+) will require end-to-end recruiter-supervised transformer fine-tuning on thousands of curated domain pairs, rather than frozen sentence embeddings."
3. **Contrastive Learning Wording Reframed:**
   - Clarified that contrastive learning is proven to improve representation alignment and linear classification accuracy on unseen pairs, but has not yet replaced the production TF-IDF feature pipeline.
4. **RGE Document Understanding Claims Reframed:**
   - Clarified that RGE proves higher skill retention within a $\le 256$ token budget compared to naive head truncation, while downstream classification gains remain dependent on downstream classifier capacity.

---

## 7. Production Model Preservation

Physical and cryptographic verification of the production environment confirms:
- **Production Checkpoint:** `models/best_model.joblib`
  - **Physical File Size:** 61,487 bytes (Unchanged)
  - **SHA-256 Checksum:** `1001BAAF42DB8832E1BA3E28EE9DA7146E59F1D2D1808C73C4F7587535B2ED4A` (Bit-for-bit identical)
  - **Model Type:** `sklearn.linear_model.LogisticRegression`
  - **Coefficients:** Shape `(3, 2518)`
  - **Status:** **ACTIVE IN PRODUCTION — UNTOUCHED**
- **Feature Pipeline:** `models/feature_pipeline.joblib`
  - **Physical File Size:** 270,105 bytes
  - **SHA-256 Checksum:** `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` (Bit-for-bit identical)
- **Challenger Checkpoint:** `models/phase12f/challenger_model_phase12f.joblib`
  - **Physical File Size:** 2,330,440 bytes
  - **SHA-256 Checksum:** `5934990E987ABE98223BF790AC9E9A79FB5EC99DAAC4509093E8EB0036461766`
  - **Status:** **PROMOTION STRICTLY WITHHELD**

---

## 8. Outstanding Scientific Limitations

1. **Validation Margin of Error ($\pm 2.87\%$):** On $N=296$ validation pairs, random sampling error is $\pm 2.87\%$. Distinguishing incremental model advances $<2.5\%$ requires expanding to an independent benchmark of $N \ge 1,500$ pairs.
2. **Contrastive Macro F1 Neutrality:** While contrastive learning boosts accuracy by +6.42% and balanced accuracy by +3.89%, Macro F1 delta is +0.0025 due to conservative decision thresholds on the minor "Good Fit" class.
3. **Recruiter-Supervised Fine-Tuning Gap:** Reaching 80%+ three-class accuracy requires deep transformer fine-tuning (e.g. ModernBERT or DeBERTa-v3 cross-encoder) on domain-specific recruiter judgments, which remains the recommended focus for subsequent research phases.

---

## 9. Official Release Decision

### Verdict: **`CONDITIONALLY CERTIFIED`**

1. **Certification Justification:**
   - Production checkpoint architecture `(3, 2518)` is confirmed bit-for-bit with physical proof, explaining historical `(3, 778)` typos.
   - Dual-Unseen train entity counts are reconciled at exactly 500 raw resumes and 221 jobs on disk.
   - Contrastive representation statistics are methodologically corrected with Student-t ($df=4$) and paired bootstrap intervals, verifying genuine representation gains ($p = 0.0152$).
   - Contrastive code is certified 100% leak-free across all 7 protocol invariants.
   - Scientific claims across project documentation have been sanitized of dogmatic rhetoric.
2. **Release Directives:**
   - **Production Frozen:** `models/best_model.joblib` remains the sole active production model.
   - **Promotion Withheld:** Challenger models are withheld from deployment.
   - **No 80% Claims:** Accuracy claims are restricted to empirical, reproducible measurements.

---

### Artifacts & Reproduction Manifest

- **Comprehensive Report:** [docs/research/PHASE12F3_2_FORENSIC_INTEGRITY_REPORT.md](file:///d:/skillsync1/docs/research/PHASE12F3_2_FORENSIC_INTEGRITY_REPORT.md)
- **Production Checkpoint Forensic:** [experiments/phase12f3_2/results/production_checkpoint_forensic.json](file:///d:/skillsync1/experiments/phase12f3_2/results/production_checkpoint_forensic.json)
- **Dual-Unseen Entity Reconciliation:** [experiments/phase12f3_2/results/dual_unseen_entity_reconciliation.json](file:///d:/skillsync1/experiments/phase12f3_2/results/dual_unseen_entity_reconciliation.json)
- **Contrastive Statistical Reconciliation:** [experiments/phase12f3_2/results/contrastive_statistical_reconciliation.json](file:///d:/skillsync1/experiments/phase12f3_2/results/contrastive_statistical_reconciliation.json)
- **Contrastive Code Leakage Audit:** [experiments/phase12f3_2/results/contrastive_leakage_audit.json](file:///d:/skillsync1/experiments/phase12f3_2/results/contrastive_leakage_audit.json)
- **Reproduction Scripts:**
  - `scripts/phase12f3_2/audit_production_checkpoint.py`
  - `scripts/phase12f3_2/audit_dual_unseen_entities.py`
  - `scripts/phase12f3_2/compute_contrastive_statistics.py`
  - `scripts/phase12f3_2/audit_contrastive_leakage.py`
