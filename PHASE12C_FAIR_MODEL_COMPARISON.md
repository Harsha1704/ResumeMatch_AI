# Phase 12C — Fair Head-to-Head Model Comparison

## Executive Summary
This report presents a fair, rigorous, apples-to-apples comparison between the Classical TF-IDF baseline and the Pretrained Semantic (Sentence-BERT `all-MiniLM-L6-v2`) architectures.

All models were evaluated on the **exact same training records** (`train_sub_job_clean`, $N=5,463$) and the **exact same validation records** (`val_sub_job`, $N=778$, 42 unseen job descriptions, 0% pair leakage, 0% job leakage).

---

## 1. Job-Disjoint Benchmark ($N=778$, Unseen Jobs)

| Metric | Classical Baseline (Word TF-IDF + 15 Dense) | SBERT Config B (MiniLM-L6-v2 Bi-Encoder) | Hybrid Config D (SBERT + 25 Dense) | Delta (Config B vs Baseline) | Delta (Config D vs Baseline) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Accuracy** | 48.20% | **50.90%** | **51.80%** | +2.70% | +3.60% |
| **Balanced Accuracy** | 0.4301 | **0.4762** | **0.4786** | +0.0461 | +0.0485 |
| **Macro Precision** | 0.4333 | **0.4703** | **0.4766** | +0.0370 | +0.0433 |
| **Macro Recall** | 0.4301 | **0.4762** | **0.4786** | +0.0461 | +0.0485 |
| **Macro F1** | 0.4265 | **0.4726** | **0.4775** | **+0.0461** | **+0.0510** |
| **Weighted F1** | 0.4997 | 0.5122 | **0.5189** | +0.0125 | +0.0192 |
| **Brier Score (Cal.)** | **0.8766** | 1.4741 | 1.4747 | +0.5975 (Worse) | +0.5981 (Worse) |
| **Feature Dimensions** | 2,515 | 1,537 | 1,562 | -978 dims | -953 dims |
| **Train Time (sec)** | **2.25s** | 7.56s | 12.10s | +5.31s | +9.85s |
| **Inf. Latency (CPU)**| **0.85 ms** | 62.73 ms | 66.47 ms | +61.88 ms | +65.62 ms |

---

## 2. Per-Class Performance Breakdown

### A. No Fit Class ($N=415$)
- **Classical Baseline**: Precision 71.30% | Recall 58.07% | F1 64.01%
- **SBERT Config B**: Precision 61.66% | Recall 57.35% | F1 59.43%
- **Hybrid Config D**: Precision 61.27% | Recall 60.24% | F1 60.75%
*Analysis*: The classical TF-IDF model has higher precision on the negative class because distinct keyword absences provide strong signals for non-fit.

### B. Potential Fit Class ($N=230$)
- **Classical Baseline**: Precision 37.75% | Recall 40.87% | F1 39.25%
- **SBERT Config B**: Precision 41.83% | Recall 45.65% | F1 43.66%
- **Hybrid Config D**: Precision 42.74% | Recall 43.48% | F1 43.10%
*Analysis*: SBERT models improve Potential Fit F1 by +4.4 percentage points, capturing partial semantic overlaps that lexical models miss.

### C. Good Fit Class ($N=133$) — The Critical Production Metric
- **Classical Baseline**: Precision 20.94% | Recall 30.08% | F1 24.69%
- **SBERT Config B**: Precision **37.59%** | Recall **39.85%** | F1 **38.69%**
- **Hybrid Config D**: Precision **38.97%** | Recall **39.85%** | F1 **39.41%**
*Analysis*: SBERT provides a decisive advantage on Good Fit identification:
- **Precision rises from 20.94% to 37.59% (+16.65 percentage points)**.
- **Recall rises from 30.08% to 39.85% (+9.77 percentage points)**.
- **F1 rises from 24.69% to 38.69% (+14.00 percentage points)**.

---

## 3. Confusion Matrix Comparisons

```
1. Classical Baseline (TF-IDF + 15 Dense):
                  Pred No Fit   Pred Potential   Pred Good Fit   Total
Actual No Fit         241            107               67         415
Actual Potential       52             94               84         230
Actual Good Fit        45             48               40         133

2. SBERT Config B (MiniLM-L6-v2 Embeddings Only):
                  Pred No Fit   Pred Potential   Pred Good Fit   Total
Actual No Fit         238            124               53         415
Actual Potential       90            105               35         230
Actual Good Fit        58             22               53         133

3. Hybrid Config D (SBERT + 25 Dense):
                  Pred No Fit   Pred Potential   Pred Good Fit   Total
Actual No Fit         250            115               50         415
Actual Potential       97            100               33         230
Actual Good Fit        61             19               53         133
```

---

## 4. Key Comparative Findings
1. **Modest Overall Accuracy Gain**: SBERT produces a modest overall accuracy gain of +2.70% (50.90% vs 48.20%).
2. **Substantial Good Fit Gain**: The primary benefit of SBERT is not overall accuracy, but reducing false positives in Good Fit (false positive count drops from 151 in Baseline to 88 in SBERT Config B and 83 in Hybrid Config D).
3. **Probability Calibration Regression**: Brier score worsens from 0.8766 to 1.4741. Logistic regression probabilities on dense high-dimensional SBERT embeddings are less well-calibrated out of the box than on sparse TF-IDF vectors, requiring Platt scaling or Isotonic calibration before production thresholding.
4. **Latency Trade-off**: SBERT requires ~66 ms per pair on CPU compared to ~0.85 ms for TF-IDF (a ~77x latency multiplier).
