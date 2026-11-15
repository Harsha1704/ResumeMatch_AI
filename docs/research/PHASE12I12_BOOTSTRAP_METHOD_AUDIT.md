# ResumeMatch AI — Phase 12I.12: Independent Multiway Bootstrap & Uncertainty Estimation Audit

**Date:** November 14, 2026  
**Auditor Roles:** Principal Statistical Methodologist, Biostatistician, ML Evaluation Scientist, Reproducibility Auditor  
**Audit Objective:** Independently verify the crossed-cluster bootstrap implementation, evaluate the finite-cluster correction, and compare empirical resampling with analytical multiway cluster-robust variance estimation.  
**Official Verdict:** **`CERTIFIED — BOOTSTRAP AND SEED PROVENANCE REPRODUCED`**

---

## Executive Summary

Phase 12I.12 conducts a rigorous mathematical audit of the crossed candidate-job uncertainty estimation framework implemented in ResumeMatch AI. 

Key audit conclusions:
1. **Pigeonhole Bootstrap Verified:** The resampling scheme implemented in Phase 12I.10 and Phase 12I.11 is the **Pigeonhole Bootstrap** (Owen 2007, *The Annals of Applied Statistics*), which independently resamples rows (candidates, $C=91$) and columns (jobs, $J=52$) with replacement, inducing multiplicative pair weights $w_i = k_{c(i)} \cdot k_{j(i)}$ over the sparse bipartite evaluation graph ($N=296$).
2. **Distinct Resampling Frameworks Disentangled:** The Pigeonhole Bootstrap, the Cameron-Gelbach-Miller (2011) multiway cluster-robust sandwich estimator (CRVE), and the multiway wild cluster bootstrap (MacKinnon et al. 2021) are distinct methodologies with different mathematical properties. They must **not** be cited interchangeably.
3. **Pigeonhole Bootstrap vs. Analytical CRVE:** Both methods were independently evaluated on all 296 pairs across 10,000 replicates. 
   - Under the Pigeonhole Bootstrap, standard errors range from $5.20\%$ to $6.19\%$, and the 95% percentile confidence intervals **cross zero across all 5 seeds for both comparators**.
   - Under analytical CGM two-way CRVE, standard errors range from $3.11\%$ to $4.25\%$ ($\text{DEFF} \approx 1.05 - 1.77$, $N_{\text{eff}} \approx 167 - 285$).
   - The Pigeonhole Bootstrap yields larger standard errors because the number of realized bipartite edges $N^* = \sum w_i$ varies randomly across resamples in sparse networks.
4. **Finite-Cluster Correction Invalidation:** The factor $\sqrt{\frac{91}{90} \times \frac{52}{51}} = 1.0153$ (+1.53% adjustment) is an asymptotic degrees-of-freedom correction derived for parametric sandwich covariance matrices. Applying it to an empirical non-parametric bootstrap standard error is theoretically inappropriate and double-counts finite-sample cluster dispersion. However, its numerical impact is negligible (+0.08 percentage points SE) and does not alter the substantive conclusion: under crossed-cluster resampling, the 95% confidence intervals span zero.

---

## 1. Audit of the Pigeonhole Bootstrap Implementation

### 1.1 Resampling Algorithm Mechanics
In resume-job matching, evaluation data form a sparse bipartite graph $G = (C, J, E)$, where $C=91$ unique candidates, $J=52$ unique jobs, and $|E|=296$ observed resume-job pairs. Observations sharing a candidate or job are mutually dependent.

The algorithm implemented in the codebase operates as follows:
1. Let $C=91$ candidate clusters and $J=52$ job clusters.
2. In replicate $b \in \{1, \dots, B\}$ ($B=10,000$):
   - Sample candidate multiplicities $k_c \sim \text{Multinomial}(C, [1/C, \dots, 1/C])$.
   - Sample job multiplicities $k_j \sim \text{Multinomial}(J, [1/J, \dots, 1/J])$.
3. For each observed pair $i = (c(i), j(i)) \in E$:
   - Calculate pair weight: $w_i = k_{c(i)} \cdot k_{j(i)}$.
4. Evaluate weighted paired accuracy difference:
   $$\hat{\theta}^*_b = \frac{\sum_{i=1}^N w_i \Delta_i}{\sum_{i=1}^N w_i}$$
   where $\Delta_i = I(\text{challenger}_i == y_i) - I(\text{comparator}_i == y_i) \in \{-1, 0, +1\}$.

### 1.2 Verification Checklist
- **Independent Cluster Sampling:** Candidates and jobs are sampled from independent multinomial distributions. Verified.
- **Product Multiplicities:** $w_i = k_{c(i)} \cdot k_{j(i)}$. If either candidate $c$ or job $j$ is omitted ($k=0$), pair weight is 0. If both are selected multiple times, weight scales multiplicatively. Verified.
- **Paired Alignment:** Because weights apply to row $i$, the challenger prediction and comparator prediction are evaluated on the identical pair. Paired alignment is 100% preserved. Verified.
- **Sparse Graph Handling:** Zero-weight pairs contribute zero to numerator and denominator. No unobserved candidate-job edges are synthesized. Verified.
- **Interval Type:** Empirical percentile intervals $[q_{0.025}, q_{0.975}]$ are transformation-invariant and robust for bounded proportion differences. Verified.
- **Replicate Stability:** Across 10,000 replicates with fixed seed 42, zero degenerate replicates occurred ($\sum w_i > 0$ on all 10,000 replicates). Verified.

*Artifact:* [bootstrap_reproduction.json](file:///d:/skillsync1/experiments/phase12i12/results/bootstrap_reproduction.json)

---

## 2. Rigorous Differentiation of Resampling Frameworks

Historical documentation occasionally referred to the bootstrap implementation interchangeably as "Cameron-Gelbach-Miller bootstrap", "two-way clustering", or "multiway wild bootstrap". Methodological precision requires separating these three distinct approaches:

```
========================================================================================
                       CROSS-CLUSTER UNCERTAINTY FRAMEWORKS
========================================================================================
1. PIGEONHOLE BOOTSTRAP (Owen 2007):
   - Non-parametric resampling of row and column clusters with replacement.
   - Pair weights w_ij = k_i * k_j.
   - Naturally suited for non-parametric evaluation of network arrays and match pairs.
   - Captures non-linear and non-normal dispersion in ratio estimators.

2. MULTIWAY CLUSTER-ROBUST SANDWICH (CRVE) (Cameron, Gelbach, & Miller 2011):
   - Analytical, asymptotic sandwich formula: V_CGM = V_C + V_J - V_CJ.
   - Evaluates variance at fixed sample size N without random resampling.
   - Derived for linear regression and GEE estimating equations.
   - Assumes large cluster counts (min(C, J) -> infinity).

3. MULTIWAY WILD CLUSTER BOOTSTRAP (MacKinnon, Nielsen, & Webb 2021):
   - Semi-parametric bootstrap preserving original design matrix X.
   - Multiplies regression residuals by auxiliary random variables (Rademacher/Mammen).
   - Designed for regression models with few clusters (G < 30) to correct t-statistics.
   - Inapplicable to non-parametric discrete paired accuracy differences.
========================================================================================
```

---

## 3. Empirical Comparison: Pigeonhole Bootstrap vs. Analytical Two-Way CRVE

We computed both the Pigeonhole Bootstrap ($B=10,000$, seed 42) and the Cameron-Gelbach-Miller (2011) Analytical Two-Way Sandwich Estimator on all 296 pairs:

### Comparison A: Contrastive Seeds vs. Production Baseline (36.82%)

| Seed | Point Gain ($\Delta \text{Acc}$) | Pigeonhole Boot SE | Pigeonhole 95% Percentile CI | Analytical CGM SE | Analytical CGM 95% CI | Design Effect ($\text{DEFF}$) | Effective Sample Size ($N_{\text{eff}}$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | **+9.12%** | 5.47% | **[-1.34%, +19.92%]** | 3.47% | [+2.31%, +15.93%] | 1.28 | 231.8 |
| **43** | **+8.78%** | 5.89% | **[-2.83%, +20.12%]** | 3.90% | [+1.14%, +16.43%] | 1.59 | 186.4 |
| **44** | **+2.36%** | 5.85% | **[-9.25%, +13.76%]** | 3.66% | [-4.82%, +9.55%] | 1.26 | 234.5 |
| **45** | **+9.12%** | 6.14% | **[-2.67%, +21.43%]** | 3.98% | [+1.31%, +16.93%] | 1.44 | 206.2 |
| **46** | **+9.46%** | 6.19% | **[-3.01%, +21.40%]** | 4.25% | [+1.13%, +17.79%] | 1.77 | 167.6 |

---

### Comparison B: Contrastive Seeds vs. Raw SBERT (38.18%)

| Seed | Point Gain ($\Delta \text{Acc}$) | Pigeonhole Boot SE | Pigeonhole 95% Percentile CI | Analytical CGM SE | Analytical CGM 95% CI | Design Effect ($\text{DEFF}$) | Effective Sample Size ($N_{\text{eff}}$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | **+7.77%** | 5.20% | **[-2.18%, +18.10%]** | 3.11% | [+1.68%, +13.86%] | 1.04 | 284.8 |
| **43** | **+7.43%** | 5.73% | **[-3.77%, +18.72%]** | 3.68% | [+0.21%, +14.65%] | 1.40 | 210.8 |
| **44** | **+1.01%** | 5.55% | **[-9.61%, +12.03%]** | 3.28% | [-5.41%, +7.44%] | 1.05 | 280.7 |
| **45** | **+7.77%** | 5.91% | **[-3.61%, +19.63%]** | 3.69% | [+0.53%, +15.01%] | 1.25 | 236.6 |
| **46** | **+8.11%** | 5.80% | **[-3.55%, +19.59%]** | 3.70% | [+0.86%, +15.36%] | 1.36 | 218.3 |

### Methodological Sensitivity Analysis
- **Why Pigeonhole Bootstrap SE ($5.2\% - 6.2\%$) > Analytical CGM SE ($3.1\% - 4.3\%$):**  
  In a sparse bipartite graph, sampling nodes with replacement causes the number of sampled edges $N^* = \sum w_i$ to fluctuate randomly around $N=296$ (effective sample size per replicate ranges from $\approx 60$ to $\approx 280$, mean 148.6). Because the denominator of $\hat{\theta}^* = \sum w_i \Delta_i / \sum w_i$ is a random variable, ratio variance inflation occurs (Owen 2007, Menzel 2021). The analytical CGM sandwich fixes $N=296$ deterministically, isolating only the covariance of residuals across clusters.
- **Substantive Impact:** Under the Pigeonhole Bootstrap, the confidence intervals cross zero across all seeds. Under the analytical CGM sandwich, the confidence intervals exclude zero for seeds 42, 43, 45, and 46. Because the Pigeonhole Bootstrap directly captures finite-graph density variability, conservative reporting requires adhering to the bootstrap finding: **the sample size $N=296$ is underpowered to establish significance under non-parametric crossed resampling.**

*Artifact:* [bootstrap_method_comparison.json](file:///d:/skillsync1/experiments/phase12i12/results/bootstrap_method_comparison.json)

---

## 4. Audit of the Finite-Cluster Correction Factor

In Phase 12I.10 and Phase 12I.11, the factor $\sqrt{\frac{91}{90} \times \frac{52}{51}}$ was investigated.

### Mathematical Derivation & Evaluation
- The factor originates from the degrees-of-freedom small-sample correction in linear regression sandwich estimation:
  $$\text{Adjustment} = \sqrt{\frac{C}{C - 1} \times \frac{J}{J - 1}} = \sqrt{\frac{91}{90} \times \frac{52}{51}} = \sqrt{1.01111 \times 1.01961} = \sqrt{1.03093} = 1.01534$$
- This yields a **+1.53% standard error inflation** (e.g., $5.20\% \to 5.28\%$).

### Audit Verdict
1. **Theoretically Inappropriate for Bootstrap:** The non-parametric cluster bootstrap inherently models cluster-level sampling variability by drawing candidate and job clusters with replacement. Applying an asymptotic degrees-of-freedom multiplier borrowed from linear regression double-counts finite-cluster dispersion.
2. **Empirical Inconsequence:** Whether evaluated with the correction ($5.28\%$) or without ($5.20\%$), the 95% percentile confidence intervals cross zero for all seeds. The correction is formally documented but **not required** for bootstrap estimation.

*Artifact:* [finite_cluster_correction_audit.json](file:///d:/skillsync1/experiments/phase12i12/results/finite_cluster_correction_audit.json)
