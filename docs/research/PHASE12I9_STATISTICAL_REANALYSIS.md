# ResumeMatch AI — Phase 12I.9: Rigorous Statistical Re-Analysis & Theoretical Invalidation

**Document Version:** 1.0  
**Phase:** 12I.9  
**Roles:** Statistical Evaluation Scientist, Principal ML Research Auditor  
**Date:** November 2026  
**Status:** **CERTIFIED STATISTICAL AUDIT**

---

## Executive Summary

This document presents a rigorous mathematical and statistical re-analysis of the experimental findings in Phase 12I.8. It specifically addresses:
1. The mathematical invalidity of the Cover-Hart Bayes error ceiling claim.
2. The correlation structure across the 5 random seeds and the invalidity of Fisher's combined p-value.
3. The empirical behavior of one-way and two-way crossed cluster bootstrap confidence intervals.
4. Defensible statistical guidance for future benchmark reporting.

---

## 1. Mathematical Invalidation of the Cover–Hart Bayes Error Bound

### The Flawed Derivation in Phase 12I.8
In Phase 12I.8, the following formula was cited as proof that 80%+ accuracy is mathematically impossible:
$$R^* \ge \frac{K-1}{K} \left( 1 - \sqrt{1 - \frac{K}{K-1} R_{1-NN}} \right)$$
Setting $K=3$ classes and substituting an empirical classifier error $R_{1-NN} \approx 0.44$, the document concluded:
$$R^* \ge \frac{2}{3} \left( 1 - \sqrt{1 - \frac{3}{2}(0.44)} \right) = \frac{2}{3} (1 - \sqrt{0.34}) \approx 0.278 \approx 28\% \implies \text{Accuracy} \le 72\%$$

### The Four Fatal Mathematical Flaws

#### 1. Category Error on Classifier Identity
The Cover-Hart Theorem (Cover & Hart, 1967, *IEEE Transactions on Information Theory*) establishes a bound on the asymptotic probability of error of the **1-Nearest Neighbor ($1$-NN) decision rule** relative to the Bayes error $R^*$:
$$\lim_{N \to \infty} R_{1-NN}(N) = R_{NN}$$
$$R^* \le R_{NN} \le R^* \left( 2 - \frac{K}{K-1} R^* \right)$$
Inverting this quadratic gives the lower bound on $R^*$.
**Crucial Condition:** $R_{NN}$ MUST be the true asymptotic 1-NN risk.
In Phase 12I.8, the value $0.44$ was NOT obtained from a 1-NN classifier; it was the empirical accuracy (44.60%) or error (55.4%) of a **parametric Logistic Regression classifier** fitted on projected dense vectors on a sample of $N=296$ pairs! Substituting a parametric classifier's error into a 1-NN non-parametric asymptotic bound is a mathematical category error.

#### 2. Violation of the Infinite-Sample Asymptotic Limit
The Cover-Hart bound holds strictly as $N \to \infty$, where the nearest neighbor $X'_{NN} \to X$ almost surely. In a finite sample ($N=296$) with discrete text representations, the distance to the nearest neighbor is non-negligible, and finite-sample bias dominates.

#### 3. Epistemic vs Aleatoric Conflation
The performance of a specific candidate architecture (e.g. SBERT + InfoNCE) reflects **epistemic uncertainty** (model representation limitations, optimization limits, small training sample). It cannot be used to deduce the **aleatoric Bayes error ceiling** of the true underlying probability distribution $P(Y \mid X)$. An unoptimized model achieving $44\%$ accuracy indicates that the model is weak, not that nature forbids higher accuracy.

#### 4. Official Invalidation
The claim that $R^* \ge 28\%$ is **officially invalidated and retracted**. 80%+ accuracy is not proven to be mathematically impossible.

---

## 2. Multi-Seed Re-Analysis: Correlated Evaluation Structure

### The Exact Per-Seed Contingency Tables
All five seeds were evaluated on the **exact same 296 pairs** from `manifests/v1/dual_unseen_val_v1.parquet`:

| Seed | Raw SBERT Acc | Contrastive Acc | $n_{00}$ (Both Wrong) | $n_{10}$ (Raw Only Right, $b$) | $n_{01}$ (Cont Only Right, $c$) | $n_{11}$ (Both Right) | Total Disc ($b+c$) | McNemar $\chi^2_{\text{corr}}$ | McNemar $p$-value | Exact Binom $p$-value |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **42** | 38.18% | 45.95% | 130 | 30 | 53 | 83 | 83 | 5.8313 | 0.015743 | 0.015232 |
| **43** | 38.18% | 45.61% | 129 | 32 | 54 | 81 | 86 | 5.1279 | 0.023544 | 0.022983 |
| **44** | 38.18% | 39.19% | 137 | 43 | 46 | 70 | 89 | 0.0449 | 0.832107 | 0.832258 |
| **45** | 38.18% | 45.95% | 123 | 37 | 60 | 76 | 97 | 4.9897 | 0.025499 | 0.024991 |
| **46** | 38.18% | 46.28% | 126 | 33 | 57 | 80 | 90 | 5.8778 | 0.015333 | 0.014867 |

### Why Fisher's Combined p-value is Invalid Here
Fisher's method tests the omnibus null hypothesis by computing:
$$X^2 = -2 \sum_{i=1}^k \ln(p_i) \sim \chi^2_{2k}$$
Under $H_0$, this distribution holds **if and only if the $k$ tests are statistically independent**.

In our setting:
- Each seed evaluated the **identical 296 validation pairs**.
- The inter-seed prediction agreement matrix is:
  $$\begin{pmatrix}
  1.000 & 0.807 & 0.747 & 0.770 & 0.804 \\
  0.807 & 1.000 & 0.703 & 0.777 & 0.784 \\
  0.747 & 0.703 & 1.000 & 0.720 & 0.720 \\
  0.770 & 0.777 & 0.720 & 1.000 & 0.767 \\
  0.804 & 0.784 & 0.720 & 0.767 & 1.000
  \end{pmatrix}$$
- The models share on average $76.0\%$ identical classifications!
- The resulting p-values are **heavily positively dependent**.
- Applying Fisher's method under strong positive correlation produces a massive deflation of the combined p-value ($p = 7.15 \times 10^{-6}$), creating the false impression of five independent confirmatory studies.

### Corrected Interpretation
Evaluating across 5 seeds demonstrates **training stochasticity and initialization robustness**. It confirms that the contrastive improvement is consistent across 4 of 5 random initializations ($p < 0.05$ on 4 seeds, with seed 44 showing sensitivity). It **does not** increase the effective sample size beyond $N=296$.

---

## 3. Clustered Bootstrap Analysis & Uncertainty Widening

Because the 296 dual-unseen pairs share 91 unique candidates and 52 unique jobs, standard i.i.d. bootstrap intervals underestimate true sampling uncertainty:

| Seed | Contrastive Accuracy | Candidate Cluster Bootstrap 95% CI (91 clusters) | Job Cluster Bootstrap 95% CI (52 clusters) | Two-Way Crossed Cluster Bootstrap 95% CI |
| :---: | :---: | :---: | :---: | :---: |
| **42** | 45.95% | [40.51%, 52.38%] | [38.83%, 53.43%] | **[37.93%, 54.39%]** |
| **43** | 45.61% | [39.45%, 52.09%] | [38.96%, 53.58%] | **[38.00%, 54.37%]** |
| **44** | 39.19% | [33.24%, 45.17%] | [33.55%, 45.35%] | **[32.11%, 46.55%]** |
| **45** | 45.95% | [40.27%, 53.56%] | [39.46%, 52.68%] | **[38.79%, 54.46%]** |
| **46** | 46.28% | [39.41%, 53.34%] | [40.32%, 52.36%] | **[38.64%, 54.44%]** |

### Statistical Insights:
1. **Uncertainty Inflation:** The two-way crossed bootstrap interval for Seed 42 ($[37.93\%, 54.39\%]$, width $16.46\%$) is significantly wider than standard unclustered intervals ($[40.3\%, 51.7\%]$, width $11.4\%$).
2. **Cluster Transport Risk:** Job clustering introduces more variance than candidate clustering because there are fewer unique jobs (52 jobs vs 91 candidates), resulting in larger cluster sizes.
3. **Rigorous Benchmark Guidance:** Future evaluations must report two-way crossed cluster bootstrap intervals to avoid overstating precision.
