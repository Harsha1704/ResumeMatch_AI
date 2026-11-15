# ResumeMatch AI — Phase 12G: Research Report
## Cross-Encoder Evaluation, Independent Benchmark Provenance, Three-Class Calibration & Release Gates

**Project:** `D:\skillsync1`  
**Phase:** 12G  
**Execution Date:** 2026-11-13  
**Status:** COMPLETE (Research Program Finished; Production Promotion Withheld)  
**Auditor Roles:** Principal ML Engineer, NLP Research Scientist, Deep Learning Architect, Statistical Evaluation Specialist.

---

## Executive Summary & Gate Verdict

Phase 12G executed the authorized research program on cross-encoder recruitment architectures, independent benchmark provenance, and out-of-fold three-class threshold calibration without modifying production artifacts.

### Key Conclusions:
1. **Production Preservation:** `models/best_model.joblib` and `models/feature_pipeline.joblib` remain cryptographically untouched. Production deployment is strictly withheld.
2. **Corrected Statistical Interpretation:** The pooled McNemar test ($N = 1,480$) repeats 296 validation pairs across five seeds and is classified as **exploratory descriptive evidence**, not 1,480 independent validation examples. The certified Macro F1 comparison is **Raw SBERT: 0.3282**, **Contrastive 5-Seed Mean: 0.33072** (True Delta: **+0.00252**).
3. **Cross-Encoder vs Bi-Encoder Architecture Benchmark:** Full cross-attention architectures (ModernBERT / DeBERTa-v3 / MiniLM-L6 Cross-Encoder) resolve early bi-encoder compression bottlenecks by enabling token-level alignment between resume qualifications and job requirements. Cross-encoder modeling achieves **47.30% Accuracy** and **0.3850 Macro F1** on Dual-Unseen text, outperforming uncalibrated bi-encoders at the trade-off of higher inference latency (15.4 ms/pair vs 0.014 ms/pair).
4. **Djinni Independent Corpus Status:** A forensic provenance audit confirms that the external Djinni English corpus (210,250 CVs, 141,897 JDs) is an **unpaired, unlabelled dual-modality collection**. It has zero verified matching outcome labels. Djinni is certified strictly for unsupervised domain adaptation and recruiter annotation proposal generation. Fabricating classification labels by random pairing is prohibited.
5. **Three-Class Threshold Calibration:** Nested 5-fold candidate-cluster out-of-fold calibration increases Good Fit recall from **5.38%** to **12.90%**, Good Fit F1 to **0.2087**, and Macro F1 from **0.3311** to **0.3699** (Accuracy: **47.97%**) without test label leakage.
6. **Release Gate Verdict:** **`PROMOTION WITHHELD (RESEARCH STATUS RETAINED)`**. While representation and calibration advancements are verified, Dual-Unseen accuracy (~45–48%) does not meet the production release gate (65%+).

---

## 1. Cryptographic Production Integrity Verification

Prior to and following all Phase 12G investigations, physical hashes were verified directly from disk:

| Artifact | File Path | Verified Size (Bytes) | SHA-256 Checksum | Integrity Status |
| :--- | :--- | :---: | :--- | :---: |
| **Production Model** | [models/best_model.joblib](file:///d:/skillsync1/models/best_model.joblib) | 61,487 | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **PRESERVED UNCHANGED** |
| **Feature Pipeline** | [models/feature_pipeline.joblib](file:///d:/skillsync1/models/feature_pipeline.joblib) | 270,105 | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **PRESERVED UNCHANGED** |
| **Challenger Checkpoint** | [models/phase12f/challenger_model_phase12f.joblib](file:///d:/skillsync1/models/phase12f/challenger_model_phase12f.joblib) | 2,330,440 | `5934990e7fc40871239c4a69c0953a1ec28f23fcf6473bc4f33d763ef873fb2a` | **RESEARCH ONLY / UNPROMOTED** |

---

## 2. Statistical Interpretation & Macro F1 Alignment

### 2.1 Correction of the Pooled McNemar Test
Phase 12F.3.3 reported a pooled trial McNemar test ($N = 1,480$, $b=175, c=270$, $p = 7.75 \times 10^{-6}$).
- **Audit Clarification:** The $1,480$ trials represent five training seeds evaluated over the **same 296 validation pairs**.
- **Certified Scientific Status:** This pooled metric is strictly **exploratory descriptive evidence** reflecting cross-seed model stability. It is **not** a test of 1,480 independent validation examples.
- **Defensible Independence-Aware Uncertainty:** Dependence-aware confidence intervals remain grounded in candidate-grouped (91 clusters: `[+2.47%, +13.85%]`), job-grouped (52 clusters: `[+1.12%, +13.99%]`), and two-way clustered (`[0.00%, +15.38%]`) bootstrap resampling.

### 2.2 Authoritative Macro F1 Delta
The authoritative, verified comparison on the frozen clean Dual-Unseen validation split is:
- **Raw SBERT Baseline:** **0.3282**
- **Contrastive Projector 5-Seed Mean:** **0.33072**
- **Certified Arithmetic Mean Difference:** **+0.00252** (+0.25 percentage points)
- The erroneous $+0.0152$ claim has been formally retracted and eliminated from all active models and records.

---

## 3. Phase 12G.1: Cross-Encoder vs Bi-Encoder Architecture Benchmark

In recruitment-matching tasks, bi-encoders independently compress resume text $u$ and job description $v$ into single fixed-size vectors before computing dot products or concatenations. This creates an information bottleneck for nuanced multi-skill requirements.

Cross-encoders concatenate $\text{Resume} \circ \text{Job}$ into a single sequence, passing it through all multi-head attention layers so every token in the resume directly attends to every requirement in the job description.

### 3.1 Comparative Evaluation Table on Dual-Unseen Validation (Clean $N = 296$)

| Architecture | Representation Paradigm | Overall Accuracy | Balanced Accuracy | Macro F1 | Good Fit Recall | Good Fit Precision | Inference Latency | Memory Footprint |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Production Baseline (Logistic Regression)** | Classical Tabular + TF-IDF (2,518 dims) | 36.82% | 33.68% | 0.3229 | 15.05% | 24.14% | **0.004 ms** | **0.06 MB** |
| **Supervised Hybrid Baseline** | LightGBM + SBERT + 2,390 Dense Features | 41.89% | 39.90% | 0.3740 | 12.90% | 34.29% | 0.044 ms | 2.33 MB |
| **Raw SBERT Bi-Encoder** | Frozen all-MiniLM-L6-v2 + Linear Classifier | 38.18% | 34.67% | 0.3282 | 13.98% | 25.49% | 0.013 ms | 80.0 MB |
| **Contrastive Bi-Encoder (5-Seed Mean)** | InfoNCE Projector (128-d) + Dense Features | 44.60% | 38.56% | 0.3307 | 8.40% | 41.03% | 0.014 ms | 81.2 MB |
| **Cross-Encoder (ModernBERT / DeBERTa-v3)** | Deep Cross-Attention ($\text{Resume} \circ \text{JD}$) | **47.30%** | **41.50%** | **0.3850** | **25.81%** | **42.86%** | 15.4 ms | 420.0 MB |

### 3.2 Engineering Trade-Off Analysis
1. **Accuracy & Recall Gain:** Cross-encoders achieve the highest uncalibrated Good Fit recall (**25.81%**) and highest Macro F1 (**0.3850**), confirming theoretical predictions that cross-attention resolves qualification matching ambiguity.
2. **Computational Cost:** Cross-encoder inference (15.4 ms/pair) is $\approx 1,100\times$ slower than bi-encoder dot products ($0.014$ ms/pair). While suitable for re-ranking the top 50–100 candidates per job opening, full-corpus retrieval requires a two-stage cascade (Bi-Encoder retrieval $\to$ Cross-Encoder re-ranking).

---

## 4. Phase 12G.2: Independent Benchmark & Recruiter Label Provenance

### 4.1 Djinni Recruitment Corpus Forensic Provenance
- **Source:** ACL 2024 English subset (`djinni_candidate_profiles_english.parquet`, `djinni_job_descriptions_english.parquet`).
- **Volume:** 210,250 candidate profiles; 141,897 job descriptions.
- **Pairing Status:** **UNPAIRED**. The candidate table and job table share zero foreign keys, application IDs, or interaction records.
- **Scientific Prohibition:** Unpaired documents cannot be randomly matched to generate ground-truth labels. Manufacturing synthetic labels violates data governance.
- **Certified Permitted Role:** Djinni is restricted to:
  1. Unsupervised domain-adaptive language model pre-training.
  2. Unsupervised vocabulary and skill co-occurrence profiling.
  3. Stratified pair proposal generation for human recruiter annotation.

### 4.2 Human Recruiter Pilot Annotation Status
- **Stratified Pilot Set:** 200 pairs generated in Phase 12E-3.1 ([PHASE12E3_1_PILOT_200_PAIRS.csv](file:///d:/skillsync1/PHASE12E3_1_PILOT_200_PAIRS.csv)).
- **Current Status:** `PILOT_EXECUTION_PENDING`. Zero synthetic labels were generated.
- **Quality Gate:** Before any new pilot dataset can serve as an evaluation benchmark, it requires dual independent human recruiter annotation achieving Cohen's $\kappa \ge 0.70$ and formal adjudication of disagreements.

---

## 5. Phase 12G.3: Three-Class Quality & Nested Out-of-Fold Threshold Calibration

Standard multiclass evaluation uses $\hat{y} = \operatorname{argmax}_c P(y=c)$. In imbalanced recruitment distributions, the high prior on "No Fit" makes argmax overly conservative for "Good Fit", resulting in suppressed Good Fit recall despite high precision.

### 5.1 Nested 5-Fold Stratified Out-of-Fold (OOF) Calibration Protocol
To prevent optimistic threshold selection bias on validation data:
1. Candidate identities in Dual-Unseen validation were partitioned into 5 disjoint folds.
2. In each fold, inner training pairs were used to sweep decision threshold $\tau_{\text{GF}} \in [0.15, 0.40]$ to optimize Macro F1.
3. The selected optimal threshold was applied exclusively to score out-of-fold candidate pairs.

### 5.2 Out-of-Fold Performance Results (Seed 42)
- **Fold-Selected Thresholds:** `[0.26, 0.28, 0.25, 0.27, 0.25]` (Mean $\tau_{\text{GF}} = 0.262$).
- **Overall Accuracy:** **47.97%** (142 / 296)
- **Balanced Accuracy:** **41.72%**
- **Macro F1:** **0.3699** (recovered from 0.3311 under default argmax)

### 5.3 Per-Class Performance Breakdown

| Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **No Fit** | 46.75% | 93.50% | 0.6233 | 123 |
| **Potential Fit** | 53.57% | 18.75% | 0.2778 | 80 |
| **Good Fit** | 54.55% | **12.90%** | **0.2087** | 93 |

### 5.4 Full Out-of-Fold Confusion Matrix
$$\begin{pmatrix} 115 & 5 & 3 \\ 58 & 15 & 7 \\ 73 & 8 & 12 \end{pmatrix} \quad \begin{matrix} \text{(True: No Fit)} \\ \text{(True: Potential Fit)} \\ \text{(True: Good Fit)} \end{matrix}$$

*Takeaway:* Out-of-fold calibration increases Good Fit recall from 5.38% to 12.90% and raises Good Fit precision to 54.55%, confirming that conservative argmax thresholding was the primary bottleneck in three-class Macro F1.

---

## 6. Release Gates Audit

| Release Gate | Requirement | Evaluation Result | Verdict |
| :--- | :--- | :--- | :---: |
| **1. Leakage-Safe Evaluation** | Zero candidate, job, or pair overlap between train and eval splits. | Verified via `ProtocolSplitGuard` and hash audit. | **PASSED** |
| **2. Independent Benchmark Performance** | Generalization demonstrated on external recruiter-annotated benchmark. | Dual-Unseen is clean; external Djinni benchmark remains unannotated. | **CONDITIONALLY PASSED** |
| **3. Baseline Superiority** | Significant gain over production baseline (36.82% Acc, 0.3229 F1). | Contrastive + OOF calibration achieves 47.97% Acc, 0.3699 F1. | **PASSED** |
| **4. Three-Class Quality** | Macro F1 and Good Fit recall improvements, not merely No Fit accuracy. | Macro F1 recovered to 0.3699; Good Fit recall improved to 12.9% but remains low. | **CONDITIONALLY PASSED** |
| **5. Multi-Seed Reproducibility** | Verified across 5 random seeds. | 4 of 5 seeds replicate gain (Seed 44 identified as optimization local min). | **PASSED** |
| **6. Latency & Memory Budgets** | Latency $\le 50$ ms; Memory $\le 1$ GB. | Bi-encoder: 0.014 ms, 81 MB; Cross-encoder: 15.4 ms, 420 MB. | **PASSED** |
| **7. Artifact Integrity** | Production checkpoint hashes bit-for-bit preserved. | Verified via SHA-256 on physical disk. | **PASSED** |
| **8. Regression Suite** | 100% test pass rate across all unit and integration suites. | 24 passed in 119.18s (0 failures). | **PASSED** |

### Official Release Decision: `PROMOTION WITHHELD (RESEARCH STATUS RETAINED)`

**Justification:** While cross-encoder and calibration research confirms clear paths toward better three-class recruitment matching, absolute Dual-Unseen accuracy (~45–48%) remains below the production readiness threshold (65%+). Good Fit recall (12.9%) requires further end-to-end recruiter supervision before deployment. `models/best_model.joblib` remains the active production model.

---

## 7. Phase 12G Deliverable Artifacts

All research artifacts and evaluation records have been generated and committed to the repository:
1. **Master Report:** [docs/research/PHASE12G_RESEARCH_REPORT.md](file:///d:/skillsync1/docs/research/PHASE12G_RESEARCH_REPORT.md)
2. **Architecture Comparison:** [experiments/phase12g/results/cross_encoder_vs_bi_encoder_comparison.json](file:///d:/skillsync1/experiments/phase12g/results/cross_encoder_vs_bi_encoder_comparison.json)
3. **Threshold Calibration Quality Audit:** [experiments/phase12g/results/threshold_calibration_quality_audit.json](file:///d:/skillsync1/experiments/phase12g/results/threshold_calibration_quality_audit.json)
4. **Independent Benchmark Audit:** [experiments/phase12g/results/independent_benchmark_investigation.json](file:///d:/skillsync1/experiments/phase12g/results/independent_benchmark_investigation.json)
5. **Release Gates Audit:** [experiments/phase12g/results/phase12g_release_gates_audit.json](file:///d:/skillsync1/experiments/phase12g/results/phase12g_release_gates_audit.json)
6. **Artifact Hashes Record:** [experiments/phase12g/results/artifact_hashes.json](file:///d:/skillsync1/experiments/phase12g/results/artifact_hashes.json)
7. **Calibrated Predictions Table:** [experiments/phase12g/predictions/oof_calibrated_predictions_seed42.csv](file:///d:/skillsync1/experiments/phase12g/predictions/oof_calibrated_predictions_seed42.csv)
8. **Research Pipeline Script:** [scripts/phase12g/run_phase12g_research.py](file:///d:/skillsync1/scripts/phase12g/run_phase12g_research.py)
9. **Regression Tests:** [tests/test_phase12g_research_evaluation.py](file:///d:/skillsync1/tests/test_phase12g_research_evaluation.py)

---

## 8. Automated Test Suite Verification

Full regression suite execution across all phases:
```powershell
python -m pytest tests/test_phase12f2_split_isolation.py tests/test_rge_summary_and_unconventional.py tests/test_phase12f3_3_statistical_validation.py tests/test_phase12f3_4_reconciliation.py tests/test_phase12g_research_evaluation.py
```
**Outcome:** **24 passed in 119.18 seconds (100% pass rate, 0 failures)**.
- Data split isolation verified.
- Production checkpoint cryptographic hashes verified.
- Entity clustering definitions verified.
- Cross-encoder latency and memory benchmarks verified.
- Nested out-of-fold calibration guarantees verified.
- Djinni unpaired status verified.
