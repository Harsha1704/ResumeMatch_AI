# ResumeMatch AI — Phase 12I.11: Paired Comparator Reconciliation, Multiway Bootstrap Verification & Final-Test Quarantine

**Date:** November 14, 2026  
**Auditor Roles:** Principal Statistical Auditor, ML Evaluation Scientist, Data Leakage Auditor, MLOps Engineer  
**Audit Objective:** Resolve comparator inconsistencies, recalculate every paired result using separated and verified comparators, rigorously evaluate the multiway clustered bootstrap, and enforce the permanent quarantine of the exposed official test split.  
**Operational Constraints Satisfied:**
- Zero human dependency.
- Production checkpoints preserved (`best_model.joblib`, `feature_pipeline.joblib`, `challenger_model_phase12f.joblib`).
- Zero training, tuning, or selection on the official test set.
- Zero fabricated evidence.

**Official Audit Verdict:** **`STATISTICAL AUDIT PASSED — COMPARATORS AND METHODS REPRODUCED`**

---

## Executive Summary & Classification of Reported Improvements

Phase 12I.11 establishes definitive statistical clarity across all historical benchmarks and experimental claims. By auditing the raw prediction files at the byte level, this audit resolves the root cause of earlier discrepancies: **the conflation of two distinct comparators**:
1. **Comparator A: Production Baseline (Logistic Regression / `best_model.joblib`)** — Accuracy: **36.82%** (109 / 296 pairs).
2. **Comparator B: Raw SBERT Bi-Encoder (Unprojected Cosine Similarity)** — Accuracy: **38.18%** (113 / 296 pairs).

Earlier reports cited contingency counts from Comparison B ($b=30, c=53$, difference $+7.77\%$) while labeling the comparator as "Production Baseline (36.82%)", creating confusion. With both comparators cleanly separated, every paired result is recalculated and verified.

### Formal 5-Tier Classification of Reported Improvements

| Reported Result / Claim | Historical Scope | Audited Finding | Official Classification |
| :--- | :--- | :--- | :--- |
| **Contrastive InfoNCE Gain (+7.4% to +9.5% pp)** | Dual-Unseen Val ($N=296$) | Point estimates are consistently positive across all 5 seeds against both comparators (mean $+7.78\%$ vs Baseline, $+6.42\%$ vs Raw SBERT). However, 95% CIs cross zero under two-way clustering. | **Reproduced descriptive improvement** |
| **Unadjusted Paired McNemar vs Production Baseline** | Dual-Unseen Val ($N=296$) | 4 of 5 seeds achieve $p < 0.01$ and pass Holm-Bonferroni FWER control ($p_{\text{adj}} = 0.0226 < 0.05$) under unclustered paired assumptions. | **Reproduced unclustered paired difference** (not robust to clustering) |
| **Paired McNemar vs Raw SBERT under FWER** | Dual-Unseen Val ($N=296$) | Unadjusted $p = 0.0149$ yields Holm-adjusted $p = 0.0743 > 0.05$. Zero seeds achieve significance at $\alpha = 0.05$ under FWER control. | **Invalidated as statistically significant** |
| **Fisher's Combined p-value ($p = 7.15 \times 10^{-6}$)** | Dual-Unseen Val ($N=296$) | Seeds evaluated on identical 296 pairs violate independence assumption (76% inter-seed agreement). | **Invalidated** (violates statistical independence) |
| **47.64% Dual-Unseen Metric & Deep Cross-Encoder** | Dual-Unseen Val | 47.64% was produced by 5-fold candidate-grouped CV with heavy job overlap across folds. No Transformer cross-encoder weights exist. | **Unverified / Reclassified as Candidate-Disjoint OOF** |
| **50.26% Test Accuracy (`EXP-12F-PSEUDO`)** | Held-Out Test ($N=1,759$) | Pseudo-labels were uncorrupted, but sequential evaluation of 6 configurations against test data created Freedman post-selection bias. | **Exploratory** (quarantined from benchmark) |
| **Cover–Hart Bayes Error Bound ($\le 60\%$)** | Human Recruitment | Asymptotic nearest-neighbor bound for continuous features inappropriately applied to qualitative multi-rater agreement. | **Invalidated (Category Error)** |

---

## 1. Prediction Provenance & Row Alignment Audit

We audited the physical prediction files on disk to confirm that all comparisons operate on the identical set of pairs in identical order.

| Model / Checkpoint | Checkpoint Path & SHA-256 | Prediction File & SHA-256 | Prediction Column | Row Count | Correct / Total | Accuracy |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **Production Baseline** | `models/best_model.joblib`<br>`1001baaf42db...` | `experiments/phase12f2/predictions/phase12f2_dual_unseen_val_predictions.csv`<br>`0d3ef5ce452e...` | `pred_baseline_logreg` | 296 | 109 / 296 | **36.82%** |
| **Supervised Hybrid Stacking** | `experiments/phase12f2/models/...` | `experiments/phase12f2/predictions/phase12f2_dual_unseen_val_predictions.csv`<br>`0d3ef5ce452e...` | `pred_supervised_hybrid` | 296 | 124 / 296 | **41.89%** |
| **Raw SBERT Bi-Encoder** | `sentence-transformers/all-MiniLM-L6-v2` | `experiments/phase12f3_3/predictions/contrastive_vs_raw_seed_42.csv`<br>`2953c9657af9...` | `pred_raw_sbert` | 296 | 113 / 296 | **38.18%** |
| **Contrastive Projector (Seed 42)** | `experiments/phase12f3/models/contrastive_head_seed_42.pt` | `experiments/phase12f3_3/predictions/contrastive_vs_raw_seed_42.csv`<br>`2953c9657af9...` | `pred_contrastive` | 296 | 136 / 296 | **45.95%** |
| **Contrastive Projector (Seed 43)** | `experiments/phase12f3/models/contrastive_head_seed_43.pt` | `experiments/phase12f3_3/predictions/contrastive_vs_raw_seed_43.csv`<br>`7c10b7b62900...` | `pred_contrastive` | 296 | 135 / 296 | **45.61%** |
| **Contrastive Projector (Seed 44)** | `experiments/phase12f3/models/contrastive_head_seed_44.pt` | `experiments/phase12f3_3/predictions/contrastive_vs_raw_seed_44.csv`<br>`215443fa7a34...` | `pred_contrastive` | 296 | 116 / 296 | **39.19%** |
| **Contrastive Projector (Seed 45)** | `experiments/phase12f3/models/contrastive_head_seed_45.pt` | `experiments/phase12f3_3/predictions/contrastive_vs_raw_seed_45.csv`<br>`d3257bcfa6d4...` | `pred_contrastive` | 296 | 136 / 296 | **45.95%** |
| **Contrastive Projector (Seed 46)** | `experiments/phase12f3/models/contrastive_head_seed_46.pt` | `experiments/phase12f3_3/predictions/contrastive_vs_raw_seed_46.csv`<br>`8b19ce8d9f13...` | `pred_contrastive` | 296 | 137 / 296 | **46.28%** |

### Row Alignment Verification
Row-by-row comparisons across all 296 pairs confirmed:
- `resume_text_hash` matches on 296 / 296 rows (100.0%).
- `job_text_hash` matches on 296 / 296 rows (100.0%).
- `true_label` matches on 296 / 296 rows (100.0%): 123 No Fit, 93 Good Fit, 80 Potential Fit.
- *Artifact:* [prediction_provenance.json](file:///d:/skillsync1/experiments/phase12i11/results/prediction_provenance.json)

---

## 2. Rigorous Separation of the Two Comparators

### Comparison A: Contrastive Seeds vs Production Baseline (36.82%, 109/296)

| Seed | Contrastive Acc | Baseline Acc | $\Delta \text{Acc}$ | $n_{11}$ (Both Right) | $n_{00}$ (Both Wrong) | $b$ (Base Only) | $c$ (Cont Only) | Discordant ($b+c$) | McNemar $\chi^2_{\text{corr}}$ | Exact $p$-value | Two-Way Bootstrap SE | Two-Way Bootstrap 95% CI |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 45.95% | 36.82% | **+9.12%** | 80 | 131 | 29 | 56 | 85 | 7.9529 | **0.004512** | 5.47% | [-1.34%, +19.92%] |
| **43** | 45.61% | 36.82% | **+8.78%** | 79 | 131 | 30 | 56 | 86 | 7.2674 | **0.006674** | 5.89% | [-2.83%, +20.12%] |
| **44** | 39.19% | 36.82% | **+2.36%** | 66 | 137 | 43 | 50 | 93 | 0.3871 | 0.534060 | 5.85% | [-9.25%, +13.76%] |
| **45** | 45.95% | 36.82% | **+9.12%** | 73 | 124 | 36 | 63 | 99 | 6.8283 | **0.008634** | 6.14% | [-2.67%, +21.43%] |
| **46** | 46.28% | 36.82% | **+9.46%** | 77 | 127 | 32 | 60 | 92 | 7.9239 | **0.004609** | 6.19% | [-3.01%, +21.40%] |

*Artifact:* [production_comparator_analysis.json](file:///d:/skillsync1/experiments/phase12i11/results/production_comparator_analysis.json)

---

### Comparison B: Contrastive Seeds vs Raw SBERT (38.18%, 113/296)

| Seed | Contrastive Acc | Raw SBERT Acc | $\Delta \text{Acc}$ | $n_{11}$ (Both Right) | $n_{00}$ (Both Wrong) | $b$ (Raw Only) | $c$ (Cont Only) | Discordant ($b+c$) | McNemar $\chi^2_{\text{corr}}$ | Exact $p$-value | Two-Way Bootstrap SE | Two-Way Bootstrap 95% CI |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 45.95% | 38.18% | **+7.77%** | 83 | 130 | 30 | 53 | 83 | 5.8313 | **0.015232** | 5.20% | [-2.18%, +18.10%] |
| **43** | 45.61% | 38.18% | **+7.43%** | 81 | 129 | 32 | 54 | 86 | 5.1279 | **0.022983** | 5.73% | [-3.77%, +18.72%] |
| **44** | 39.19% | 38.18% | **+1.01%** | 70 | 137 | 43 | 46 | 89 | 0.0449 | 0.832258 | 5.55% | [-9.61%, +12.03%] |
| **45** | 45.95% | 38.18% | **+7.77%** | 76 | 123 | 37 | 60 | 97 | 4.9897 | **0.024991** | 5.91% | [-3.61%, +19.63%] |
| **46** | 46.28% | 38.18% | **+8.11%** | 80 | 126 | 33 | 57 | 90 | 5.8778 | **0.014867** | 5.80% | [-3.55%, +19.59%] |

*Artifact:* [raw_sbert_comparator_analysis.json](file:///d:/skillsync1/experiments/phase12i11/results/raw_sbert_comparator_analysis.json)

---

## 3. Multiple-Testing Analysis (Holm-Bonferroni FWER Control)

To prevent multiple-testing inflation, step-down Holm-Bonferroni correction was applied to each distinct family ($m=5$). Tests from different comparators were strictly **not pooled**.

```
========================================================================================
                                 HOLM-BONFERRONI AUDIT
========================================================================================
Family A: Contrastive vs Production Baseline (36.82%)
  - Seed 42: Raw p = 0.004512  --> Adjusted p = 0.022560 (< 0.05) [SIGNIFICANT]
  - Seed 46: Raw p = 0.004609  --> Adjusted p = 0.022560 (< 0.05) [SIGNIFICANT]
  - Seed 43: Raw p = 0.006674  --> Adjusted p = 0.022560 (< 0.05) [SIGNIFICANT]
  - Seed 45: Raw p = 0.008634  --> Adjusted p = 0.022560 (< 0.05) [SIGNIFICANT]
  - Seed 44: Raw p = 0.534060  --> Adjusted p = 0.534060 (> 0.05) [NOT SIGNIFICANT]
  Outcome: 4 of 5 seeds reject H0 under unclustered paired McNemar tests.

Family B: Contrastive vs Raw SBERT (38.18%)
  - Seed 46: Raw p = 0.014867  --> Adjusted p = 0.074335 (> 0.05) [NOT SIGNIFICANT]
  - Seed 42: Raw p = 0.015232  --> Adjusted p = 0.074335 (> 0.05) [NOT SIGNIFICANT]
  - Seed 43: Raw p = 0.022983  --> Adjusted p = 0.074335 (> 0.05) [NOT SIGNIFICANT]
  - Seed 45: Raw p = 0.024991  --> Adjusted p = 0.074335 (> 0.05) [NOT SIGNIFICANT]
  - Seed 44: Raw p = 0.832258  --> Adjusted p = 0.832258 (> 0.05) [NOT SIGNIFICANT]
  Outcome: 0 of 5 seeds reject H0 under unclustered paired McNemar tests.
========================================================================================
```

*Artifact:* [holm_correction.json](file:///d:/skillsync1/experiments/phase12i11/results/holm_correction.json)

---

## 4. Multiway Cluster Bootstrap Verification (Cameron-Gelbach-Miller 2011)

We audited the Phase 12I.10 implementation of the two-way clustered bootstrap against the theoretical standards of Cameron, Gelbach, and Miller (2011) (*Multi-Way Clustering*, JBES):

### Methodological Verification Checks
1. **Crossed Cluster Resampling:** Candidates ($C=91$) and jobs ($J=52$) are resampled independently with replacement. A pair $(c, j)$ receives non-zero weight if and only if both candidate $c$ and job $j$ are selected.
2. **Paired Prediction Alignment:** Challenger and comparator predictions are evaluated on the identical pair row $i$ with weight $w_i$. Paired alignment is 100% preserved.
3. **Duplicate Cluster Multiplicity:** If candidate $c$ is selected $k_c$ times and job $j$ is selected $k_j$ times, pair weight is $w_i = k_c \cdot k_j$. Joint incidence multiplicity is correctly preserved.
4. **Graph Incidence Structure:** Only the 296 observed edges in the bipartite candidate-job graph are weighted. No synthetic pairs are created.
5. **Finite Cluster Correction:** The finite adjustment factor is $\sqrt{\frac{C}{C-1} \cdot \frac{J}{J-1}} = \sqrt{\frac{91}{90} \cdot \frac{52}{51}} = 1.0152$ (+1.52% SE). Incorporating this factor slightly widens the standard error, further confirming that 95% CIs span zero.
6. **Replicate Stability:** Across $B=10,000$ replicates, zero failed or degenerate replicates occurred ($\sum w_i > 0$ for all replicates).

### Mathematical Explanation: Why 95% CIs Span Zero
Under independent i.i.d. assumptions, standard error is $\text{SE} \approx 2.9\%$, yielding a narrow confidence interval. However, because candidates and jobs are clustered, positive intracluster correlations inflate the variance by a Design Effect ($\text{DEFF} \approx 3.5 - 4.5$), doubling the standard error to $5.2\% - 6.2\%$.  
With $\text{SE} \approx 5.5\%$, the 95% margin of error is $1.96 \times 5.5\% = 10.78\%$. Because the point estimates range from $+7.4\%$ to $+9.5\%$, the margin of error exceeds the point estimate, causing the 95% confidence interval to cross zero on both comparators.  
*Artifact:* [bootstrap_method_verification.json](file:///d:/skillsync1/experiments/phase12i11/results/bootstrap_method_verification.json)

---

## 5. Production Checkpoint Preservation

Production baseline checkpoints and feature pipelines remain untouched and identical in size and hash:

| Checkpoint Path | Expected Size (Bytes) | Observed Size (Bytes) | SHA-256 Hash | Status |
| :--- | :---: | :---: | :--- | :---: |
| `models/best_model.joblib` | 61,487 | 61,487 | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **PRESERVED** |
| `models/feature_pipeline.joblib` | 270,105 | 270,105 | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **PRESERVED** |
| `models/phase12f/challenger_model_phase12f.joblib` | 2,330,440 | 2,330,440 | `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766` | **PRESERVED** |

*Artifact:* [production_preservation.json](file:///d:/skillsync1/experiments/phase12i11/results/production_preservation.json)

---

## 6. Official Final Verdict

**`STATISTICAL AUDIT PASSED — COMPARATORS AND METHODS REPRODUCED`**

Both comparators (Production Baseline and Raw SBERT) have been fully separated, verified, and reconciled across all 5 seeds. The multiway cluster bootstrap is confirmed to be methodologically sound, and the official test split is permanently quarantined.
