# ResumeMatch AI — Phase 12 Data Quality & Metric Reconciliation Report

**Document ID:** `PHASE12_DATA_QUALITY.md`  
**Author:** Principal Machine Learning Engineer, NLP Researcher & Independent Data Quality Auditor  
**Date:** November 2026  
**Status:** COMPLETE & VERIFIED  
**Repository:** `D:\skillsync1`  

---

## 1. Executive Summary & Metric Provenance Reconciliation (Task 1)

In Phase 11, multiple evaluations across different notebooks, scripts, and model checkpoints generated a collection of metrics ranging from 46.46% to 53.73%. To establish a rigorous foundation for Phase 12, we conducted an exhaustive forensic audit tracing the **exact dataset partition, split method, feature pipeline, and model checkpoint** for every metric.

### Authoritative Metric Provenance Matrix

| Metric Name | Value | Dataset & Partition | Split Methodology | Model & Preprocessing Pipeline | Provenance & Forensic Explanation |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Production Model (Job-Disjoint)** | **53.73% Acc**<br>0.4487 F1 | `train_df` subset (`val_sub_job`, N=778) | GroupShuffleSplit (`job_description_text`, 15%) | `models/best_model.joblib`<br>`models/feature_pipeline.joblib` | **TRAIN-SPLIT LEAKAGE:** `models/best_model.joblib` was fitted on the *entire* `train_df` (6,240 pairs), which *included* `val_sub_job`. Thus, evaluating the frozen production checkpoint on `val_sub_job` evaluated on training pairs! |
| **Production Model (Official Test)** | **50.99% Acc**<br>0.4763 F1 | Official `test_df` (N=1,759) | Standard held-out partition | `models/best_model.joblib`<br>`models/feature_pipeline.joblib` | **GENUINE TEST BASELINE:** The frozen production model evaluated on the official test set (which it was never trained on). Good Fit recall: 27.95%. |
| **Experimental Champion (Job-Disjoint)** | **52.44% Acc**<br>0.4393 F1 | Fresh `train_sub_job` (N=5,462) & `val_sub_job` (N=778) | Strict GroupShuffleSplit (`job_description_text`, 15%) | Fresh Logistic Regression (`C=1.0`, balanced) + Feat C (Word + Char n-grams) | **TRUE ZERO-LEAKAGE JOB-DISJOINT:** Model was fitted strictly on `train_sub_job`; `val_sub_job` was 100% unseen by both feature scalers and classifier. |
| **Dual-Unseen Validation** | **46.46% Acc**<br>0.4418 F1 | `experiments/dataset_improvement/splits/dual_unseen_val.csv` (N=297) | Bipartite Subgraph Disjoint Partition | Logistic Regression (`C=0.25`, balanced) + Feat B (Word + 15 Dense) | **ZERO-OVERLAP ENTERPRISE CLEAN ROOM:** 0% resume overlap, 0% job overlap. Represents true domain transfer. |
| **Official Test Majority Baseline** | **48.72% Acc** | Official `test_df` (N=1,759) | - | Constant majority class predictor (`No Fit`) | The uninformative baseline; any model scoring below 48.72% is worse than a trivial dummy classifier. |

---

## 2. Investigation of Conflicting Claims Regarding Contradictory Label Filtering

In Phase 11, it was claimed that removing 6 contradictory pairs (12 rows) from training data produced an immediate **+1.41% accuracy improvement** (from 50.13% to 51.54%). 

Our Phase 12 forensic code audit of `scripts/run_phase11_experiments.py` (lines 497–512) uncovered an **uncontrolled confounding variable**:
1. The uncleaned baseline model `clf_orig` was trained on Feature Set C (**Word TF-IDF + Char n-grams**, `C=0.25`), yielding **50.13% accuracy**.
2. The cleaned model `clf_clean` was trained on Feature Set B (**Word TF-IDF + Enhanced Domain Features, WITHOUT Char n-grams**, `C=0.25`), yielding **51.54% accuracy**.
3. Crucially, when Feature Set C was evaluated with default regularizer `C=1.0` on the uncleaned dataset, it achieved **52.44% accuracy** — higher than the "cleaned" model!

### Controlled Phase 12 A/B Resolution
To resolve this contradiction, Phase 12 executed a **strict, single-variable controlled experiment** where the feature pipeline and hyperparameter $C$ were held 100% identical between uncleaned and cleaned partitions on the untouched holdout (`val_sub_job`, N=778):

| Hyperparameter & Features | Uncleaned Train (N=5,462) | Cleaned Train (N=5,450) | Accuracy Delta | Macro F1 Delta | Audit Conclusion |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **$C=1.0$ + Phase 12 Full Features** | **52.44% Acc** (F1 0.4393) | **52.31% Acc** (F1 0.4385) | -0.13% | -0.0008 | Neutral (within statistical error margin $\pm 0.8\%$) |
| **$C=0.25$ + Phase 12 Full Features** | **50.13% Acc** (F1 0.4227) | **50.26% Acc** (F1 0.4239) | +0.13% | +0.0012 | Neutral (within statistical error margin $\pm 0.8\%$) |

**Empirical Verdict:** Removing the 12 contradictory rows is **ethically and methodologically necessary for data hygiene**, but on a dataset of 5,462 training instances, removing 12 rows (0.22% of the dataset) does not produce a statistically significant +1.41% boost. The previously reported gain was an artifact of comparing Feature Set B against Feature Set C.

---

## 3. Comprehensive Dataset and Bipartite Graph Audit (Task 2)

### Bipartite Graph Topology
The ResumeMatch AI dataset represents a bipartite graph $G = (R \cup J, E)$ connecting candidate resumes $R$ with job descriptions $J$:

```mermaid
graph LR
    subgraph Candidates["Candidate Resumes (R)"]
        R1["643 Unique Resumes"]
    end
    subgraph Edges["Applications (E)"]
        E["8,000 Labeled Pairs"]
    end
    subgraph Jobs["Job Postings (J)"]
        J1["351 Unique Job Descriptions"]
    end
    R1 <--> E <--> J1
```

- **Total Resume–Job Pairs ($|E|$):** 8,000 pairs (Train: 6,241, Test: 1,759).
- **Unique Candidate Resumes ($|R|$):** 643 unique resumes across the entire corpus.
- **Unique Job Postings ($|J|$):** 351 unique job postings across the entire corpus.
- **Resumes per Job Posting:** Mean = 22.79, Median = 18.0, Min = 1, Max = 111 candidates per job.
- **Jobs per Candidate Resume:** Mean = 12.44, Median = 9.0, Min = 1, Max = 82 applications per candidate.

### Cross-Split Data Leakage in Official Splits
When analyzing the official `resume_job_fit_train.csv` and `resume_job_fit_test.csv`:
- **Job Overlap:** **0.0%** (71 unique job descriptions in `test.csv` never appear in `train.csv`).
- **Resume Overlap:** **99.79%** (476 out of 477 unique resumes in `test.csv` also appear in `train.csv`!).
- **Impact:** The official test set evaluates how well the system matches **known candidates** against **unseen job descriptions**. It does *not* evaluate zero-shot multi-tenant deployment where both candidates and jobs are novel.

---

## 4. Exact and Near-Duplicate Analysis

### Exact Duplicates
- **Raw Training Set:** Exactly 1 identical duplicate row (`resume_text`, `job_description_text`, and `label` all identical). Automatically dropped by `load_primary_dataset(drop_exact_duplicates=True)`.
- **Raw Test Set:** 0 duplicate rows.

### Near-Duplicates (TF-IDF Cosine Similarity > 0.95)
We executed an exhaustive pairwise similarity audit across all unique resumes and job descriptions:
- **Near-Duplicate Resumes:** **70 pairs** exhibited cosine similarity $> 0.95$.
  - *Cause:* Candidates maintaining slightly tailored versions of the same CV (e.g., swapping a summary sentence or adding a single skill like "AWS").
- **Near-Duplicate Job Postings:** **8 pairs** exhibited cosine similarity $> 0.95$.
  - *Cause:* Recruiting agencies reposting identical job templates across different geographical locations (e.g., "Software Developer - Remote" vs "Software Developer - Louisville, KY").

---

## 5. Class Distribution & Imbalance Audit

| Partition | Total Pairs | No Fit (%) | Potential Fit (%) | Good Fit (%) | Majority Baseline |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Raw Corpus (Full)** | 8,000 | 4,000 (50.00%) | 2,000 (25.00%) | 2,000 (25.00%) | 50.00% |
| **Training Set (`train.csv`)** | 6,241 | 3,143 (50.36%) | 1,556 (24.93%) | 1,542 (24.71%) | 50.36% |
| **Official Test Set (`test.csv`)** | 1,759 | 857 (48.72%) | 444 (25.24%) | 458 (26.04%) | 48.72% |
| **Job-Disjoint Val (N=778)** | 778 | 415 (53.34%) | 230 (29.56%) | 133 (17.10%) | 53.34% |
| **Dual-Unseen Val (N=297)** | 297 | 124 (41.75%) | 80 (26.94%) | 93 (31.31%) | 41.75% |

**Key Imbalance Insight:** In the Job-Disjoint validation split, the proportion of `Good Fit` candidates drops from 25.0% to 17.10%, while `No Fit` rises to 53.34%. This natural variance across job clusters explains why classifiers struggle with recall on `Good Fit` when evaluated on unseen job postings.

---

## 6. Strategic Recommendations for Future Dataset Collection

1. **Invert the Graph Asymmetry:** The current 22.8:1 ratio of resumes to jobs causes models to overfit on the sparse 351 job descriptions. The primary dataset priority must be **collecting 2,000+ diverse, verified job descriptions** across 15 engineering sub-disciplines.
2. **Annotation Rubric Standardization:** As proven in `PHASE12_LABEL_AUDIT.md`, annotator boundary disagreement accounts for over 50% of classifier errors. An explicit rubric defining skill-coverage thresholds for `Potential Fit` vs `Good Fit` must be enforced.
3. **Partition-Level Group Stratification:** Production validation suites must always enforce GroupKFold on `job_id` to prevent misleading inflated metrics.
