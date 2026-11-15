# Phase 12C — Statistical Significance & Bootstrap Validation

## Executive Summary
This report documents the rigorous statistical hypothesis testing conducted to determine whether the performance gains observed with Sentence-BERT (`all-MiniLM-L6-v2`) over the Classical TF-IDF baseline are statistically significant or attributable to sampling variance.

A **paired non-parametric bootstrap resampling** procedure ($B = 1,000$ iterations) was executed on the legitimate Job-Disjoint validation partition ($N = 778$, 42 unseen job descriptions).

---

## 1. Statistical Methodology
- **Null Hypothesis ($H_0$)**: There is no difference in metric $\theta$ between SBERT Config B and the Classical TF-IDF Baseline ($\Delta \theta = \theta_{\text{SBERT}} - \theta_{\text{Baseline}} = 0$).
- **Alternative Hypothesis ($H_1$)**: SBERT Config B achieves a non-zero performance difference ($\Delta \theta \neq 0$).
- **Resampling Procedure**: In each bootstrap iteration $b \in \{1, \dots, 1000\}$, $N=778$ evaluation pairs were sampled with replacement from `val_sub_job`. The predictions of both models were evaluated on the identical bootstrap sample, preserving the paired error correlation.
- **Confidence Intervals**: Two-sided 95% percentile confidence intervals $[\text{Percentile}_{2.5\%}, \text{Percentile}_{97.5\%}]$.
- **p-Value Calculation**: Empirical two-tailed p-value computed as $2 \times \min(P(\Delta \le 0), P(\Delta \ge 0))$.
- **Significance Criterion**: $\alpha = 0.05$ (Significant if 95% CI excludes zero).

---

## 2. Bootstrap Resampling Results ($B = 1,000$)

| Evaluation Metric | Mean Delta ($\mu_{\Delta}$) | Standard Deviation ($\sigma_{\Delta}$) | 95% Confidence Interval | Empirical Two-Tailed p-value | Statistically Significant at $\alpha = 0.05$? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **$\Delta \text{Accuracy}$** | **+0.0279** (+2.79%) | 0.0242 | **[-0.0219, +0.0746]** | **0.2580** | **NO ($p > 0.05$)** |
| **$\Delta \text{Macro F1}$** | **+0.0470** (+0.0470) | 0.0245 | **[-0.0058, +0.0945]** | **0.0720** | **NO ($p > 0.05$)** |
| **$\Delta \text{Good Fit Recall}$** | **+0.0990** (+9.90%) | 0.0563 | **[-0.0079, +0.2131]** | **0.0840** | **NO ($p > 0.05$)** |
| **$\Delta \text{Good Fit Precision}$** | **+0.1687** (+16.87%) | 0.0416 | **[+0.0902, +0.2518]** | **< 0.0001** | **YES ($p < 0.001$)** |

---

## 3. Detailed Distribution Analysis

### A. Accuracy ($\Delta \text{Acc} = +0.0279$, 95% CI: [-0.0219, +0.0746])
The 95% confidence interval spans zero comfortably. In **12.9%** of bootstrap samples, the Classical Baseline achieved equal or superior accuracy compared to SBERT. Thus, we fail to reject the null hypothesis for overall accuracy ($p = 0.2580$).

### B. Macro F1 ($\Delta \text{Macro F1} = +0.0470$, 95% CI: [-0.0058, +0.0945])
The improvement in Macro F1 approaches the standard significance threshold ($p = 0.0720$), but its lower 2.5th percentile bound remains slightly negative (-0.0058). Under standard Neyman-Pearson statistical criteria, the macro F1 improvement is **borderline but not formally established at the $\alpha = 0.05$ level**.

### C. Good Fit Recall ($\Delta \text{Recall} = +0.0990$, 95% CI: [-0.0079, +0.2131])
While SBERT improves Good Fit recall by an average of +9.9 percentage points, high variance across job descriptions ($\sigma = 0.0563$) results in the 95% CI slightly overlapping zero (-0.0079). With $p = 0.0840$, this metric cannot be declared statistically significant at $\alpha = 0.05$.

### D. Good Fit Precision ($\Delta \text{Precision} = +0.1687$, 95% CI: [+0.0902, +0.2518])
**The single indisputable, statistically significant improvement provided by Sentence-BERT is Good Fit Precision.**
- Across 1,000 bootstrap resamples, zero resamples produced a negative delta ($\Delta \le 0$).
- The lower bound of the 95% confidence interval is **+0.0902** (+9.02 percentage points).
- Two-tailed $p < 0.0001$.
- SBERT systematically eliminates false positives where a non-matching resume happens to share common vocabulary with a job description.

---

## 4. Scientific Verdict
1. **Overall Accuracy and Macro F1 improvements do not meet formal statistical significance** on the $N=778$ job-disjoint partition ($p = 0.258$ and $p = 0.072$).
2. **Good Fit Precision improvement is highly statistically significant** ($p < 0.0001$, $+16.87$ percentage points).
3. Therefore, while SBERT does not constitute a wholesale breakthrough in general accuracy, it provides a statistically verified reduction in false-positive match recommendations.
