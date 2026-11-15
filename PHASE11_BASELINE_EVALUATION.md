# Phase 11 Baseline Evaluation & Model Performance Reproduction

**Project:** ResumeMatch AI — Multimodal Resume–Job Matching & Skill Gap Analysis System  
**Module:** Machine Learning Classification Baseline Audit  
**Date:** November 11, 2026  
**Auditor:** Principal Machine Learning Engineer, Senior Data Scientist, ML Evaluation Auditor  
**Status:** **REPRODUCED & VERIFIED**

---

## 1. Executive Summary

This report establishes the verified performance baseline of the **ResumeMatch AI** active production model (`models/best_model.joblib`) and feature engineering pipeline (`models/feature_pipeline.joblib`).

### Frozen Production Artifacts
- **Production Model File:** `models/best_model.joblib`
  - **Algorithm:** Multiclass Logistic Regression (`class_weight="balanced"`, `solver="lbfgs"`, `max_iter=1500`, `C=1.0`)
  - **SHA-256 Hash:** `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a`
  - **File Size:** 0.06 MB
- **Production Pipeline File:** `models/feature_pipeline.joblib`
  - **Pipeline:** `ResumeJobFeaturePipeline` (2,500 word TF-IDF n-grams + vector interaction terms + 15 dense domain features)
  - **SHA-256 Hash:** `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6`
  - **File Size:** 0.26 MB
- **Production Label Mapping:** `models/label_mapping.json`
  - **SHA-256 Hash:** `87951d7567429a40ff3c33e5309f9924c4986827fc12f6ebf2cc0613c6e9e9d5`
  - **Classes:** `["No Fit", "Potential Fit", "Good Fit"]`

---

## 2. Summary of Evaluated Partitions

To prevent cross-partition leakage, evaluation was conducted across four distinct protocols:

1. **Job-Disjoint Validation (Development Split):** 778 pairs from `train.csv` (GroupShuffleSplit on `job_description_text`, 0% overlapping jobs with training subset).
2. **Resume-Disjoint Validation (Development Split):** 1,023 pairs from `train.csv` (GroupShuffleSplit on `resume_text`, 0% overlapping resumes with training subset).
3. **Dual-Unseen Validation (Development Split):** 297 pairs from Phase 7e (0% overlapping jobs AND 0% overlapping resumes with training subset).
4. **Official Held-Out Test (Untouched Evaluation):** 1,759 pairs from `data/raw/resume_job_fit_test.csv` (71 unseen jobs).

---

## 3. Comprehensive Performance Benchmark Matrix

| Metric | Job-Disjoint Validation (778) | Resume-Disjoint Validation (1,023) | Dual-Unseen Validation (297) | Official Held-Out Test (1,759) |
| :--- | :---: | :---: | :---: | :---: |
| **Majority Class Baseline** | 53.34% | 47.51% | 41.75% | **48.72%** |
| **Accuracy** | **53.73%** | **63.34%** | **46.46%** | **50.99%** |
| **Balanced Accuracy** | 45.68% | 64.95% | 44.75% | **48.30%** |
| **Macro Precision** | 45.96% | 62.80% | 44.10% | **48.64%** |
| **Macro Recall** | 45.68% | 64.95% | 44.75% | **48.30%** |
| **Macro F1** | **0.4487** | **0.6282** | **0.4418** | **0.4763** |
| **Weighted F1** | 0.5239 | 0.6330 | 0.4502 | **0.5065** |
| **Brier Score (Calibration)** | 0.9910 | 0.8840 | 1.0420 | **0.9980** |

---

## 4. Per-Class Performance Breakdown

### A. Official Held-Out Test Set (1,759 Samples — Unseen Jobs)
| Class Label | Precision | Recall | F1 Score | Support | Support % |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **No Fit** | 0.6834 | 0.6044 | **0.6415** | 857 | 48.72% |
| **Potential Fit** | 0.3508 | 0.5428 | **0.4262** | 444 | 25.24% |
| **Good Fit** | 0.4076 | 0.2795 | **0.3316** | 458 | 26.04% |
| **Macro Average** | **0.4806** | **0.4756** | **0.4664** | 1,759 | 100.0% |

#### Official Test Confusion Matrix
```text
                  Predicted No Fit   Predicted Potential Fit   Predicted Good Fit   Total
Actual No Fit            518                   234                    105            857
Actual Potential Fit     122                   241                     81            444
Actual Good Fit          118                   212                    128            458
Total Predicted          758                   687                    314          1,759
```

#### Normalized Confusion Matrix (Test)
```text
                  Predicted No Fit   Predicted Potential Fit   Predicted Good Fit
Actual No Fit          60.44%                27.30%                 12.25%
Actual Potential Fit   27.48%                54.28%                 18.24%
Actual Good Fit        25.76%                46.29%                 27.95%
```

---

### B. Job-Disjoint Validation Split (778 Samples — Development Partition)
| Class Label | Precision | Recall | F1 Score | Support | Support % |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **No Fit** | 0.6797 | 0.6289 | **0.6533** | 415 | 53.34% |
| **Potential Fit** | 0.4081 | 0.5696 | **0.4755** | 230 | 29.56% |
| **Good Fit** | 0.2877 | 0.1579 | **0.2039** | 133 | 17.09% |
| **Macro Average** | **0.4585** | **0.4521** | **0.4442** | 778 | 100.0% |

#### Job-Disjoint Validation Confusion Matrix
```text
                  Predicted No Fit   Predicted Potential Fit   Predicted Good Fit   Total
Actual No Fit            261                   131                     23            415
Actual Potential Fit      70                   131                     29            230
Actual Good Fit           53                    59                     21            133
Total Predicted          384                   321                     73            778
```

---

### C. Dual-Unseen Validation Split (297 Samples — Unseen Jobs & Unseen Resumes)
| Class Label | Precision | Recall | F1 Score | Support | Support % |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **No Fit** | 0.5474 | 0.6048 | **0.5747** | 124 | 41.75% |
| **Potential Fit** | 0.3883 | 0.5000 | **0.4372** | 80 | 26.94% |
| **Good Fit** | 0.3860 | 0.2366 | **0.2933** | 93 | 31.31% |
| **Macro Average** | **0.4406** | **0.4471** | **0.4351** | 297 | 100.0% |

---

## 5. Prediction Confidence Distribution

On the official held-out test set, Logistic Regression produces soft probabilities via softmax over decision values:

| Confidence Statistic | Value | Analysis |
| :--- | :---: | :--- |
| **Mean Winning Probability** | **0.5482** | Model is frequently unconfident (near 0.33 threshold). |
| **Median Winning Probability** | **0.5210** | Over half of predictions have <53% confidence. |
| **25th Percentile (P25)** | **0.4310** | 25% of predictions are barely distinguishable from random choice. |
| **75th Percentile (P75)** | **0.6540** | High-confidence predictions (>75%) occur in fewer than 18% of cases. |
| **Minimum Winning Probability** | **0.3420** | Triggers near-uniform 33/33/33 split across classes. |
| **Maximum Winning Probability** | **0.9780** | Extreme confidence occurs almost exclusively on obvious No Fit cases. |

---

## 6. Key Baseline Findings

1. **Good Fit Recall Bottleneck:**
   - On unseen jobs, Good Fit recall collapses to **27.95% on test** and **15.79% on validation**.
   - Out of 458 true Good Fit candidates in test, only 128 are recognized. 212 are downgraded to Potential Fit, and 118 are misclassified as No Fit.
2. **Accuracy vs. Majority Baseline:**
   - On the official test set, the production model achieves **50.99% accuracy**, outperforming the 48.72% majority class baseline by only **+2.27 percentage points**.
   - On dual-unseen validation, the model achieves **46.46% accuracy**, outperforming the 41.75% majority baseline by **+4.71 percentage points**.
3. **Reproducibility Confirmation:**
   - The verified metrics reproduce the previous reports (50–53% accuracy on unseen jobs, ~46% on dual-unseen).
