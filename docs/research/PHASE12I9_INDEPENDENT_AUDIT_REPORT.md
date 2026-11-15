# ResumeMatch AI — Phase 12I.9: Independent Statistical Reconciliation, Benchmark Forensics & Model Evidence Certification

**Phase:** 12I.9  
**Date:** November 2026  
**Roles:** Principal ML Research Auditor, Statistical Evaluation Scientist, NLP Architect, MLOps Engineer, Data Leakage Auditor  
**Workspace:** `D:\skillsync1`  
**Audit Verdict:** **`AUDIT CONDITIONALLY PASSED — CORRECTIONS REQUIRED`**

---

## Executive Summary

Phase 12I.9 delivers an independent, read-only forensic audit and scientific reconciliation of all empirical claims, mathematical derivations, and architecture attributions made in Phase 12I.8.

In strict compliance with zero-human-dependency and empirical research standards:
1. **Production Artifact Preservation:** Verified that all three core checkpoints (`models/best_model.joblib`, `models/feature_pipeline.joblib`, and `models/phase12f/challenger_model_phase12f.joblib`) are physically identical in byte size and SHA-256 hash before and after Phase 12I.9.
2. **Cover-Hart Bayes Error Bound Invalidation:** The Phase 12I.8 claim that the Bayes error rate on the 3-class problem is bounded below by $R^* \ge 28.0\%$ and that 80%+ accuracy is mathematically impossible has been **officially invalidated and retracted**. It resulted from a mathematical category error (substituting an empirical finite-sample parametric classifier error into an asymptotic 1-NN non-parametric bound).
3. **Fisher Combined p-value Invalidation:** The reported Fisher combined p-value ($p = 7.15 \times 10^{-6}$) across 5 random seeds has been **invalidated**. Because all 5 models were evaluated on the **exact same 296 pairs**, the test statistics are strongly positively correlated ($r \approx 0.76$). Applying Fisher's independence assumption produced a spuriously deflated p-value.
4. **Architecture Attribution Corrections:**
   - The **47.64% dual-unseen validation accuracy** was traced to the **nested out-of-fold threshold-calibrated contrastive projector (seed 42)** ($\tau_{Good\_Fit} = 0.15$). The claim of a deep cross-encoder checkpoint (DeBERTa/ModernBERT) is marked **`UNVERIFIED`** as no standalone PyTorch weights exist on disk.
   - The **50.26% official held-out test accuracy** was traced to **Confidence-Gated Pseudo-Labeling with Hybrid Stacking (`EXP-12F-PSEUDO`)**, not a threshold-calibrated decision rule.
5. **Inference Latency Boundary Reconciliation:** The previously reported `0.0041 ms` production latency was measured strictly on classifier-only linear algebra `predict_proba(X)` on pre-extracted in-memory sparse matrices. Standardized end-to-end benchmarking on raw applicant text demonstrates true end-to-end latency of **$16.57 \ \text{ms}$ per pair** ($16.33 \ \text{ms}$ feature extraction, $0.24 \ \text{ms}$ classifier predict).
6. **Production Release Verdict:** Production promotion remains withheld. `models/best_model.joblib` remains the active production checkpoint.

---

## 1. Production Artifact Preservation Audit

All production checkpoints were verified directly from disk before and after Phase 12I.9:

| Checkpoint Path | Size (Bytes) | SHA-256 Hash | Integrity Status |
| :--- | :---: | :--- | :---: |
| `models/best_model.joblib` | 61,487 | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **VERIFIED UNCHANGED** |
| `models/feature_pipeline.joblib` | 270,105 | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **VERIFIED UNCHANGED** |
| `models/phase12f/challenger_model_phase12f.joblib` | 2,330,440 | `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766` | **VERIFIED UNCHANGED** |

---

## 2. Forensic Audit of Five-Seed Significance & Correlated Tests

### Dataset Alignment & McNemar Contingency Tables
All five seed prediction files (`experiments/phase12f3_3/predictions/contrastive_vs_raw_seed_*.csv`) evaluate the exact same 296 pairs with identical resume text hashes and job text hashes in identical order:

| Seed | Raw SBERT Acc | Contrastive Acc | Discordant Pairs ($b+c$) | Raw Right, Cont Wrong ($b$) | Raw Wrong, Cont Right ($c$) | McNemar $\chi^2_{\text{corr}}$ | Exact Binom $p$-value | Two-Way Cluster Bootstrap 95% CI |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 38.18% | 45.95% | 83 | 30 | 53 | 5.8313 | 0.015232 | [37.93%, 54.39%] |
| **43** | 38.18% | 45.61% | 86 | 32 | 54 | 5.1279 | 0.022983 | [38.00%, 54.37%] |
| **44** | 38.18% | 39.19% | 89 | 43 | 46 | 0.0449 | 0.832258 | [32.11%, 46.55%] |
| **45** | 38.18% | 45.95% | 97 | 37 | 60 | 4.9897 | 0.024991 | [38.79%, 54.46%] |
| **46** | 38.18% | 46.28% | 90 | 33 | 57 | 5.8778 | 0.014867 | [38.64%, 54.44%] |

### Forensic Invalidation of the Fisher Combined p-value ($p = 7.15 \times 10^{-6}$)
Fisher's combined test assumes independent test statistics ($p_i \sim \text{Uniform}(0, 1)$ independently under $H_0$). However:
- The five models were evaluated on the **identical 296 validation pairs**.
- Pairwise prediction agreement across seeds ranges from $70.3\%$ to $80.7\%$ (mean $76.0\%$).
- When evaluation instances are reused, the p-values are strongly positively dependent.
- Applying Fisher's method under positive correlation severely underestimates the joint p-value, creating a false impression of independent replication.
- **Audit Correction:** The multi-seed test proves that contrastive domain adaptation is robust to random initialization on a single sample, but does **not** constitute independent dataset replication.

---

## 3. Forensic Audit of Cover–Hart & Bayes Error Invalidation

### The Invalid Derivation
In Phase 12I.8, the Cover-Hart asymptotic bound:
$$R^* \ge \frac{K-1}{K} \left( 1 - \sqrt{1 - \frac{K}{K-1} R_{1-NN}} \right)$$
was evaluated with $K=3$ and an empirical classifier error $R \approx 0.44$, claiming $R^* \ge 28.0\%$ and that 80%+ accuracy is mathematically impossible.

### Audit Findings & Category Error
1. **Classifier Identity Mismatch:** The Cover-Hart Theorem applies strictly to the asymptotic error of a **1-Nearest Neighbor classifier**. In Phase 12I.8, $0.44$ was the empirical accuracy (44.60%) or error of a **parametric Logistic Regression classifier** on projected vectors. Substituting a parametric classifier's error into a 1-NN non-parametric bound is a severe category error.
2. **Infinite Sample Violation:** The bound holds strictly as $N \to \infty$. $N=296$ is a small, finite sample.
3. **Conflating Model Error with Bayes Error:** Poor performance of an empirical model reflects model capacity/feature limitations, not the Bayes error ceiling of the underlying distribution.

### Official Audit Verdict
> **CLAIM INVALIDATED AND RETRACTED.**  
> The mathematical claim that Bayes error is at least 28.0% and that 80%+ accuracy is mathematically impossible is officially retracted. 80%+ accuracy remains an open empirical challenge for future multi-modal research.

---

## 4. Architecture Attribution Forensic Audit

| Evaluated Result | Phase 12I.8 Claimed Architecture | Traced True Architecture | Audit Verdict |
| :--- | :--- | :--- | :---: |
| **47.64% Accuracy** (Dual-Unseen Val) | Cross-Encoder (DeBERTa-v3 / ModernBERT) | Nested 5-fold candidate-cluster threshold-calibrated contrastive projector (seed 42, $\tau=0.15$) | **MISATTRIBUTED (Cross-Encoder UNVERIFIED)** |
| **50.26% Accuracy** (Official Held-Out Test) | Threshold-calibrated decision rule | Confidence-Gated Pseudo-Labeling with Hybrid Stacking (`EXP-12F-PSEUDO`) | **MISATTRIBUTED (Corrected to EXP-12F-PSEUDO)** |

- **Physical Checkpoint Audit:** Zero fine-tuned transformer cross-encoder weights exist on disk. The 47.64% result is verified, but achieved via threshold calibration rather than deep cross-attention.

---

## 5. Four-Protocol Dataset Reconciliation

| Protocol | Split File | Rows | Resumes | Jobs | Baseline Acc | Challenger Acc | Entity Separation |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Official Held-Out Test** | `held_out_test_v1.parquet` | 1,759 | 477 | 71 | 48.61% | 48.89% (Stacking) / 50.26% (Pseudo) | **0 Overlap** |
| **Clean Dual-Unseen Val** | `dual_unseen_val_v1.parquet` | 296 | 91 | 52 | 36.82% | 44.60% (Cont) / 47.64% (Calib) | **0 Overlap** |
| **Job-Disjoint Val** | `job_disjoint_val_v1.parquet` | 778 | 373 | 42 | 74.16% | 75.84% (Stacking) | **0 Overlap** |
| **Resume-Disjoint Val** | `resume_disjoint_val_v1.parquet` | 1,023 | 97 | 219 | 77.71% | 78.98% (Stacking) | **0 Overlap** |

* **Historical Discrepancy Resolved:** The production baseline achieves $74-77\%$ on `job_disjoint` and `resume_disjoint` because those splits were carved out from `resume_job_fit_train.csv` (which the production pipeline had seen during initial corpus training). On truly unseen entities (`held_out_test` and `dual_unseen`), accuracy normalizes to $48.61\%$ and $36.82\%$.

---

## 6. Standardized Latency & Resource Footprint Benchmark

Standardized single-thread benchmarking on real applicant pairs (`experiments/phase12i9/run_standardized_latency_benchmark.py`):

| Pipeline Stage | Operations Included | Mean Latency | Median Latency | P95 Latency | P99 Latency |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Stage 1: Feature Extraction** | Clean text + parse structure + skill engine + TF-IDF + scale | $16.331 \ \text{ms}$ | $14.824 \ \text{ms}$ | $26.912 \ \text{ms}$ | $37.840 \ \text{ms}$ |
| **Stage 2: Classifier Predict** | LogisticRegression `predict_proba` | $0.242 \ \text{ms}$ | $0.212 \ \text{ms}$ | $0.418 \ \text{ms}$ | $0.620 \ \text{ms}$ |
| **Full End-to-End Pipeline** | **Raw text $\to$ Predicted Probabilities** | **$16.573 \ \text{ms}$** | **$15.035 \ \text{ms}$** | **$27.361 \ \text{ms}$** | **$38.237 \ \text{ms}$** |

* **Reconciliation:** The previously reported `0.0041 ms` represented linear algebra operations in BLAS on pre-computed in-memory sparse matrices. True end-to-end user inference takes **$16.57 \ \text{ms}$ per pair** ($188.6 \ \text{MB}$ peak process RAM).

---

## 7. Certified Scientific Conclusions (6-Tier Separation)

1. **Demonstrated Engineering Improvements:** Automated, append-only intake validation engine (`rating_intake_validator.py`); verified zero-leakage split manifests (`manifests/v1/*`); standardized latency benchmark harness.
2. **Demonstrated Validation Improvements:** Contrastive InfoNCE domain adaptation improves accuracy over raw SBERT ($44.60\%$ vs $38.18\%$) on clean dual-unseen validation.
3. **Statistically Supported Paired Improvements:** Paired McNemar tests on seeds 42, 43, 45, 46 show statistically significant gains ($p < 0.05$) over frozen raw SBERT representations.
4. **Independently Replicated Improvements:** Evaluated across multiple seeds on a single frozen validation set. True independent replication on separate external datasets remains pending.
5. **Unverified Model Results:** The "Cross-Encoder DeBERTa/ModernBERT" claim is **`UNVERIFIED`** due to absence of PyTorch weights. The 47.64% result is re-attributed to calibrated contrastive projection.
6. **Unsupported Theoretical Claims:** The Cover-Hart Bayes error bound ($R^* \ge 28\%$) and the "80% mathematically impossible" claim are **`INVALIDATED AND RETRACTED`**.

---

## 8. Summary of Phase 12I.9 Deliverables

1. **Independent Audit Report:** [`docs/research/PHASE12I9_INDEPENDENT_AUDIT_REPORT.md`](file:///d:/skillsync1/docs/research/PHASE12I9_INDEPENDENT_AUDIT_REPORT.md)
2. **Scientific Correction Register:** [`docs/research/PHASE12I9_CORRECTION_REGISTER.md`](file:///d:/skillsync1/docs/research/PHASE12I9_CORRECTION_REGISTER.md)
3. **Statistical Re-Analysis:** [`docs/research/PHASE12I9_STATISTICAL_REANALYSIS.md`](file:///d:/skillsync1/docs/research/PHASE12I9_STATISTICAL_REANALYSIS.md)
4. **Seed Significance Audit:** [`experiments/phase12i9/results/seed_significance_audit.json`](file:///d:/skillsync1/experiments/phase12i9/results/seed_significance_audit.json)
5. **Bayes Bound Audit:** [`experiments/phase12i9/results/bayes_bound_audit.json`](file:///d:/skillsync1/experiments/phase12i9/results/bayes_bound_audit.json)
6. **Architecture Attribution Audit:** [`experiments/phase12i9/results/architecture_attribution_audit.json`](file:///d:/skillsync1/experiments/phase12i9/results/architecture_attribution_audit.json)
7. **Four-Protocol Reconciliation:** [`experiments/phase12i9/results/four_protocol_reconciliation.json`](file:///d:/skillsync1/experiments/phase12i9/results/four_protocol_reconciliation.json)
8. **Threshold Leakage Audit:** [`experiments/phase12i9/results/threshold_leakage_audit.json`](file:///d:/skillsync1/experiments/phase12i9/results/threshold_leakage_audit.json)
9. **Latency Reconciliation:** [`experiments/phase12i9/results/latency_reconciliation.json`](file:///d:/skillsync1/experiments/phase12i9/results/latency_reconciliation.json)
10. **Production Preservation Audit:** [`experiments/phase12i9/results/production_preservation.json`](file:///d:/skillsync1/experiments/phase12i9/results/production_preservation.json)
11. **Regression Test Suite:** [`tests/test_phase12i9_independent_audit.py`](file:///d:/skillsync1/tests/test_phase12i9_independent_audit.py)

---

## 9. Final Operational Verdict

> **`AUDIT CONDITIONALLY PASSED — CORRECTIONS REQUIRED`**
