# ResumeMatch AI — Phase 12I.10: Formal Scientific Correction Register

**Date:** November 14, 2026  
**Auditor:** Independent ML Research Audit & Statistical Verification Team  
**Scope:** Historical claims, statistical derivations, architectural attributions, and split provenance across Phases 12F through 12I.9  
**Status:** **AUTHORITATIVE & FINAL**

---

## Purpose of this Register

This register documents all formal scientific corrections, recalibrations, and claim withdrawals established during the Phase 12I.10 audit. Each entry records the original claim, the offending assumption or methodology, the audited empirical evidence, the corrected finding, and the resulting operational policy.

---

## Itemized Correction Register

### Entry CR-01: Fisher's Combined p-value on Five Random Seeds
* **Original Claim (Phase 12I.8):** Combining p-values across 5 random seeds yields Fisher's combined statistic $X^2 = 54.12$ ($p = 7.15 \times 10^{-6}$), demonstrating definitive statistical significance over the production baseline.
* **Flaw / Violation:** Fisher's method mathematically requires independent test statistics ($X^2 = -2 \sum_{i=1}^k \ln p_i \sim \chi^2_{2k}$ under independent $H_0$). The 5 random seeds were evaluated on the **exact same 296 pairs**, sharing identical candidate resumes, job postings, and ground-truth labels. The tests are strongly correlated, rendering Fisher's combined p-value invalid.
* **Audited Empirical Finding:** Individual exact paired McNemar two-sided p-values range from $0.0149$ to $0.8323$.
* **Corrected Result:** Under step-down Holm-Bonferroni correction controlling Family-Wise Error Rate (FWER) across the 5 correlated evaluations:
  $$\text{Adjusted } p_{(1)} = 5 \times 0.01486 = 0.07432 > 0.05$$
* **Operational Status:** Fisher's combined test is **FORMALLY INVALIDATED AND WITHDRAWN**. Under strict FWER control, individual seed significance is **NOT established** at $\alpha = 0.05$.

---

### Entry CR-02: Two-Way Clustered Bootstrap Confidence Intervals
* **Original Claim (Phase 12I.8):** Contrastive Projector accuracy improvement $\Delta \text{Acc} \approx +7.77\%$ is statistically significant with a narrow 95% confidence interval that does not cross zero.
* **Flaw / Violation:** The standard error was calculated under an independent i.i.d. assumption ($\text{SE} \approx 2.9\%$), ignoring the crossed candidate ($C=91$) and job ($J=52$) clustering in `dual_unseen_val_v1.parquet`.
* **Audited Empirical Finding:** Implementing the Cameron, Gelbach, and Miller (2011) two-way multi-cluster bootstrap across $B=10,000$ replicates yields an empirical bootstrap standard error of $5.23\% - 5.89\%$.
* **Corrected Result:** The 95% percentile confidence intervals for paired improvement $\Delta \text{Acc}$ cross zero for all 5 seeds:
  - Seed 42: $+7.77\%$, 95% CI $[-2.28\%, +18.18\%]$
  - Seed 123: $+7.09\%$, 95% CI $[-3.21\%, +17.58\%]$
  - Seed 456: $+3.38\%$, 95% CI $[-8.11\%, +14.86\%]$
  - Seed 789: $+7.43\%$, 95% CI $[-3.03\%, +18.06\%]$
  - Seed 2024: $+7.77\%$, 95% CI $[-2.65\%, +18.24\%]$
* **Operational Status:** Corrected in all records. The point estimate is acknowledged as consistently positive (mean improvement $+6.42\%$), but the sample size $N=296$ is underpowered to reject zero under crossed clustering.

---

### Entry CR-03: Official Held-Out Test Set Overlap Provenance
* **Original Claim (Phase 12I.9):** The official held-out test set (`held_out_test_v1.parquet`, $N=1,759$) has "0 Overlap" across all entities.
* **Historical Contradiction:** An earlier forensic audit reported that **476 out of 477 resumes** in the held-out test set appeared in the primary training dataset.
* **Audited Empirical Finding:**
  - Unique jobs in held-out test: 71. Jobs overlapping with training: 0 (0.00%).
  - Pairs in held-out test: 1,759. Pairs overlapping with training: 0 (0.00%).
  - Unique resumes in held-out test: 477. Resumes overlapping with training: 476 (99.79%).
* **Corrected Result:** The shorthand "0 Overlap" in Phase 12I.9 referred strictly to 0 job overlap and 0 pair overlap. `held_out_test_v1.parquet` is strictly a **Job-Disjoint Test Set** evaluating unseen jobs with known candidate resumes. It is **NOT** a dual-disjoint test set.
* **Operational Status:** Split provenance formally reclassified and certified as **Job-Disjoint Test Protocol**.

---

### Entry CR-04: 47.64% Metric and Deep Cross-Encoder Attribution
* **Original Claim (Phase 12H / 12I):** A "Deep Cross-Encoder" achieved 47.64% accuracy on "Dual-Unseen" data.
* **Flaw / Violation:** No Transformer cross-encoder model was ever trained. The 47.64% score originated from nested 5-fold candidate-grouped cross-validation of the Contrastive InfoNCE Projector at temperature threshold $\tau = 0.15$.
* **Audited Empirical Finding:** In the 5-fold cross-validation scheme, candidate resumes were partitioned with 0 overlap across folds, but jobs overlapped heavily (24 to 34 overlapping jobs between training and validation per fold).
* **Corrected Result:**
  - Architecture: Contrastive InfoNCE Projector (SBERT bi-encoder + linear/MLP projection head).
  - Protocol: Strictly **Candidate-Disjoint Out-Of-Fold (OOF)**, not dual-unseen across folds.
  - On the true clean dual-unseen validation split (`dual_unseen_val_v1.parquet`), uncalibrated accuracy is **45.95%** (Seed 42) and **44.60%** (5-seed mean).
* **Operational Status:** Deep cross-encoder claim is **WITHDRAWN AS UNVERIFIED**. The 47.64% metric is reclassified as Candidate-Disjoint OOF.

---

### Entry CR-05: 50.26% Pseudo-Labeling Benchmark Metric (`EXP-12F-PSEUDO`)
* **Original Claim (Phase 12F):** Confidence-gated pseudo-labeling achieved 50.26% test accuracy on `held_out_test_v1.parquet`.
* **Flaw / Violation:** During Phase 12F, 6 distinct model configurations were evaluated sequentially against the official held-out test split, violating blind evaluation principles and introducing post-selection bias (Freedman's paradox).
* **Audited Empirical Finding:** Pseudo-labels were derived from an external pool of 830 Djinni pairs (28 admitted, 0 test overlap leakage). Direct label contamination was absent, but adaptive test set reuse occurred.
* **Corrected Result:** 50.26% represents exploratory semi-supervised ablation performance, not an unbiased out-of-sample benchmark estimate.
* **Operational Status:** Formally classified as **EXPLORATORY PSEUDO-LABELING RESEARCH** and withdrawn as a certified benchmark score.

---

### Entry CR-06: Cover–Hart Theorem Invalidation
* **Original Claim (Phase 12I.8):** A derivation utilizing the Cover–Hart inequality bounded the Bayes error rate and claimed human recruiter accuracy could not exceed 60%.
* **Flaw / Violation:** Category error. The Cover-Hart inequality ($R^* \le R_{NN} \le R^*(2 - c/(c-1) R^*)$) relates asymptotic 1-nearest-neighbor error to Bayes optimal error in continuous feature spaces under i.i.d. sampling. It does not apply to inter-rater recruitment consensus or human qualitative agreement.
* **Corrected Result:** The mathematical derivation is invalid and inapplicable to recruitment annotation.
* **Operational Status:** Formally **WITHDRAWN AND EXPUNGED**.

---

## Certification of Register

This register is locked and certified as part of Phase 12I.10. All benchmark reports and evaluation pipelines must strictly reference the corrected findings and statuses detailed herein.
