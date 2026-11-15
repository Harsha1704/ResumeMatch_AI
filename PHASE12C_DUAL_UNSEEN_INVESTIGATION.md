# Phase 12C — Dual-Unseen & Resume-Disjoint Investigation

## Executive Summary
This report presents the mathematical and empirical resolution of the "85.19% Dual-Unseen Anomaly" and the "87.59% Resume-Disjoint Anomaly" reported in Phase 12B.

In Phase 12B, the reported dual-unseen accuracy jumped unexpectedly from **46.46%** (Phase 11) to **85.19%**, and resume-disjoint accuracy jumped to **87.59%**, while job-disjoint accuracy remained stagnant at **50.90%**.

Our independent forensic audit proves that **the 85.19% and 87.59% figures are completely artificial artifacts caused by train-test leakage across evaluation splits**. When properly evaluated with zero leakage, true dual-unseen accuracy is **37.04% – 37.71%** and true resume-disjoint accuracy is **54.55%**.

---

## 1. Forensic Deconstruction of the 85.19% Anomaly

### How the Leakage Occurred
In `scripts/run_phase12b_experiments.py` (lines 605–635):
1. The experiment created a model `champ_model` trained exclusively on `train_sub_job_clean` ($N=5,463$).
2. Instead of fitting a new model on `dual_train_df` ($N=4,996$), the code passed `dual_val_df` ($N=296$) directly to `champ_model.predict()`.
3. Forensic analysis of the 296 pairs in `dual_val_df` revealed:
   - **92 out of 92 unique resumes (100.0%)** were already present in `train_sub_job_clean`.
   - **41 out of 52 unique job descriptions (78.85%)** were already present in `train_sub_job_clean`.
   - **249 out of 296 exact (resume, job) pairs (84.12%)** were literally copied from `train_sub_job_clean`!

Because 84.12% of the test samples were verbatim training samples, the logistic regression model simply recalled memorized training labels. The reported 85.19% accuracy was essentially the training accuracy on those overlapping samples!

---

## 2. Empirical Verification: Contaminated vs Uncontaminated Truth

We conducted controlled retraining experiments in `scripts/run_phase12c_audit.py`:
1. **Contaminated Protocol (Phase 12B Replication)**: Evaluated the `train_sub_job_clean` model directly on `dual_val_df` and `val_sub_res`.
2. **Strict Uncontaminated Protocol (Phase 12C Corrected)**:
   - Fitted Config B (SBERT only) and Config D (Hybrid) on `dual_train_df_clean` ($N=4,996$) and evaluated on `dual_val_df` ($N=296$).
   - Fitted Config B on `train_sub_res_clean` ($N=4,440$) and evaluated on `val_sub_res` ($N=1,021$).

### Dual-Unseen Evaluation ($N=296$)

| Metric | Phase 12B Claim (Contaminated) | Phase 12C Strict SBERT (Config B) | Phase 12C Strict Hybrid (Config D) | Delta (Truth vs Illusion) |
| :--- | :---: | :---: | :---: | :---: |
| **Accuracy** | **85.19%** (85.86% repr.) | **37.04%** | **37.71%** | **-48.15%** |
| **Balanced Accuracy** | 0.8598 | 0.3334 | 0.3417 | -0.5181 |
| **Macro Precision** | 0.8479 | 0.3207 | 0.3276 | -0.5203 |
| **Macro Recall** | 0.8598 | 0.3334 | 0.3417 | -0.5181 |
| **Macro F1** | **0.8502** (0.8565 repr.) | **0.3163** | **0.3256** | **-0.5246** |
| **Good Fit Recall** | 96.77% | 15.05% | 15.05% | -81.72% |
| **Good Fit Precision** | 84.11% | 26.92% | 25.93% | -58.18% |
| **Pair Leakage** | **84.12%** | **0.00%** | **0.00%** | -84.12% |

### Resume-Disjoint Evaluation ($N=1,021$)

| Metric | Phase 12B Claim (Contaminated) | Phase 12C Strict SBERT (Config B) | Delta (Truth vs Illusion) |
| :--- | :---: | :---: | :---: |
| **Accuracy** | **87.59%** (88.17% repr.) | **54.55%** | **-33.04%** |
| **Balanced Accuracy** | 0.8845 | 0.5474 | -0.3371 |
| **Macro Precision** | 0.8660 | 0.5380 | -0.3280 |
| **Macro Recall** | 0.8845 | 0.5474 | -0.3371 |
| **Macro F1** | **0.8736** (0.8795 repr.) | **0.5389** | **-0.3347** |
| **Good Fit Recall** | 94.12% | 57.09% | -37.03% |
| **Good Fit Precision** | 87.74% | 56.90% | -30.84% |
| **Pair Leakage** | **88.74%** | **0.00%** | -88.74% |

---

## 3. Confusion Matrix Breakdown: The True Dual-Unseen Failure Mode

Under strict dual-unseen conditions (where the model has seen neither the candidate resumes nor the job descriptions), the confusion matrix of SBERT Config B reveals substantial collapse:

```
                  Predicted No Fit   Predicted Potential   Predicted Good Fit   Total
Actual No Fit            79                  25                    20            124
Actual Potential Fit     45                  17                    18             80
Actual Good Fit          49                  30                    14             93
```

### Critical Observations:
1. **Low Good Fit Detection**: Out of 93 true Good Fit candidates in the dual-unseen partition, the model successfully identifies only **14** (Recall: **15.05%**), while misclassifying **49 as No Fit** and **30 as Potential Fit**.
2. **Majority Class Bias**: Over 58% of all predictions default to "No Fit" (173 out of 296).
3. **Severe Generalization Barrier**: Neither SBERT bi-encoder representations nor dense feature cross-products can overcome the distribution shift when both candidate profiles and job descriptions are completely novel. Performance degrades to **37.04%**, barely above random baseline (33.33%).

---

## 4. Scientific Verdict on Task 3
The hypothesis that Sentence-BERT achieved an 85% breakthrough on dual-unseen data is **decisively refuted**.
The reported 85.19% accuracy was entirely an artifact of evaluation against training data. In reality, dual-unseen compatibility prediction remains a difficult open challenge, achieving approximately 37% genuine accuracy under strict isolation.
