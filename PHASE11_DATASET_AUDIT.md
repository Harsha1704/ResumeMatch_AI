# Phase 11 Dataset Audit & Quality Investigation

**Project:** ResumeMatch AI — Multimodal Resume–Job Matching & Skill Gap Analysis System  
**Module:** Machine Learning Classification & Dataset Quality Engineering  
**Date:** November 11, 2026  
**Auditor:** Principal Machine Learning Engineer, Senior Data Scientist, NLP Research Engineer  
**Status:** **AUDIT COMPLETE**

---

## 1. Executive Summary

This investigation performs an exhaustive, reproducible audit of the ~8,000 resume–job description pairs that form the training and evaluation corpus of **ResumeMatch AI** (`data/raw/resume_job_fit_train.csv` and `data/raw/resume_job_fit_test.csv`).

The audit reveals key systemic structural properties that explain why machine learning classifiers on this dataset encounter performance ceilings:
1. **Severe Entity Multi-Pairing:** The 8,000 labeled pairs do not represent 8,000 distinct resumes and jobs. The entire dataset contains only **643 unique resumes** and **351 unique job descriptions**.
2. **Asymmetric Leakage in the Official Split:** While the official test set (1,759 pairs) has **0% job overlap** with the training set (71 unseen jobs), **476 out of 477 unique resumes in the test set (99.8%) also appear in the training set**.
3. **Contradictory Label Noise:** Identical (resume, job) pairs in the training corpus carry contradictory labels (e.g. labeled as both `No Fit` and `Good Fit`).
4. **Extreme Class Imbalance:** `No Fit` constitutes over 50% of the dataset, while `Good Fit` and `Potential Fit` represent approximately 24.8% each.

---

## 2. Dataset Dimensions & Class Distribution

### Overall Corpus Volume
- **Total Labeled Pairs:** 8,000 pairs
  - `data/raw/resume_job_fit_train.csv`: **6,241 pairs** (78.01%)
  - `data/raw/resume_job_fit_test.csv`: **1,759 pairs** (21.99%)
- **Total Unique Resumes (Corpus-wide):** **643**
- **Total Unique Job Descriptions (Corpus-wide):** **351**
- **Unique Pair Hashes:** **7,993** (7 duplicate/conflicting pairs detected)

### Class Distribution Across Splits
| Class Label | Train Count | Train % | Test Count | Test % | Total Count | Total % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **No Fit** | 3,143 | 50.36% | 857 | 48.72% | 4,000 | 50.00% |
| **Potential Fit** | 1,556 | 24.93% | 444 | 25.24% | 2,000 | 25.00% |
| **Good Fit** | 1,542 | 24.71% | 458 | 26.04% | 2,000 | 25.00% |
| **Total** | **6,241** | **100.0%** | **1,759** | **100.0%** | **8,000** | **100.0%** |

*Key Finding:* The label distribution is mathematically partitioned into an exact 2:1:1 ratio across the entire corpus: exactly 50.0% No Fit, 25.0% Potential Fit, and 25.0% Good Fit.

---

## 3. Missing Values & Text Integrity Audit

| Field | Train Nulls | Test Nulls | Train Empty Strings | Test Empty Strings |
| :--- | :---: | :---: | :---: | :---: |
| `resume_text` | 0 | 0 | 0 | 0 |
| `job_description_text` | 0 | 0 | 0 | 0 |
| `label` | 0 | 0 | 0 | 0 |

- **Null / Missing Value Rate:** **0.0%** (Zero null or empty values across all columns).
- **Encoding & Parsing:** Standard UTF-8 encoding. No corrupt byte sequences or unparsed JSON wrappers.

---

## 4. Entity Structure, Re-pairing & Data Leakage

### A. Group Distribution
Because the corpus was created by cross-pairing candidates against a pool of job requisitions:
- **Resumes per Job:**
  - Mean: **22.79 resumes per job description**
  - Minimum: 1
  - Maximum: **67 resumes per job description**
- **Jobs per Resume:**
  - Mean: **12.44 jobs per candidate resume**
  - Minimum: 1
  - Maximum: **32 jobs per candidate resume**

### B. Cross-Split Overlap & Leakage Analysis
| Entity Level | Train Unique | Test Unique | Shared Between Train & Test | Leakage % of Test Set |
| :--- | :---: | :---: | :---: | :---: |
| **Job Descriptions** | 280 | 71 | **0** | **0.0% (Zero Job Leakage)** |
| **Resumes** | 642 | 477 | **476** | **99.79% (Severe Resume Overlap)** |
| **Exact (Resume, Job) Pairs** | 6,241 | 1,759 | **0** | **0.0% (Zero Pair Leakage)** |

#### Implications for Generalization
1. The official train/test partition was engineered strictly as a **Job-Disjoint Split**.
2. A model evaluated on the official test set evaluates **how well the classifier generalizes to new, unseen job descriptions for candidates it has already seen during training**.
3. It does **not** evaluate a candidate whose resume was never seen before. That requires a **Dual-Unseen Split** (Protocol 4), where performance drops to ~46%.

---

## 5. Duplicate Records & Contradictory Label Noise

### A. Exact Duplicate Rows
- Exactly **1 duplicate row** was identified in `data/raw/resume_job_fit_train.csv` (identical resume, identical job description, identical label).

### B. Contradictory Label Pairs (Severe Labeling Defect)
Six identical (resume, job) pairs exist in `train.csv` that were assigned **mutually contradictory labels**:

| Contradictory Pair Hash | Labels Assigned | Resume Summary Excerpt | Job Description Excerpt |
| :--- | :---: | :--- | :--- |
| `11665d9d..._ec15bf28...` | `['No Fit', 'Good Fit']` | *"Over two years' experience of data analysis at Loyola Chicago University..."* | *"Calling all data nerds who love finance! If you're a data wiz..."* |
| `388dae3f..._87ad0608...` | `['No Fit', 'Potential Fit']` | *"Highly motivated Sales Associate with extensive customer service..."* | *"Alexander Technology Group is currently working with a Food and Beverage Manufacturer..."* |
| `46d1f66a..._60308260...` | `['No Fit', 'Potential Fit']` | *"Business Intelligence Consultant with a 10-year career in data warehousing..."* | *"ROR Partners is a rapidly growing, client-driven digital marketing company..."* |
| `6edd1be3..._23becff4...` | `['No Fit', 'Good Fit']` | *"Dynamic IT professional with around 7 years of experience as Big Data Engineer..."* | *"Business Analyst Location: Remote. Duration: 12+ months..."* |
| `80641268..._d910ee3f...` | `['No Fit', 'Good Fit']` | *"QA Analyst / Software Quality Assurance Specialist in the competitive..."* | *"Cloud and Things is a leading provider of IT solutions in public sector..."* |
| `e10d5bf0..._37c711dc...` | `['No Fit', 'Good Fit']` | *"Over 4 Years of BI / SQL Developer and Data Analyst experience..."* | *"Role - Business Analyst - Mobile Location - Louisville, KY..."* |

#### Root Cause Analysis of Contradictory Labels
These conflicting annotations demonstrate that the original labeling methodology contained human subjective inconsistency or automated heuristic collisions where overlapping keywords produced contradictory compatibility assignments for the exact same text pair.

---

## 6. Text Length & Distribution Statistics

| Statistical Metric | Resume Word Count | Resume Character Count | Job Word Count | Job Character Count |
| :--- | :---: | :---: | :---: | :---: |
| **Minimum** | 84 words | 536 chars | 11 words | 69 chars |
| **25th Percentile (P25)** | 451 words | 3,099 chars | 224 words | 1,595 chars |
| **Median (P50)** | **618 words** | **4,264 chars** | **326 words** | **2,298 chars** |
| **Mean** | 682.35 words | 4,688 chars | 362.40 words | 2,544 chars |
| **75th Percentile (P75)** | 849 words | 5,856 chars | 468 words | 3,248 chars |
| **95th Percentile (P95)** | 1,385 words | 9,456 chars | 693 words | 4,792 chars |
| **Maximum** | 3,134 words | 21,802 chars | 1,254 words | 9,144 chars |

### Truncation & Field Contamination Check
- **Short Resumes (<100 words):** Only 4 resumes in the corpus have fewer than 100 words (minimum is 84 words). None are empty or truncated fragments.
- **Short Jobs (<30 words):** Exactly 3 job descriptions have fewer than 30 words (minimum is 11 words: basic job title and location).
- **Field Contamination:** Zero field leakage detected (e.g. job description text accidentally stored in the resume column).

---

## 7. Versioned Experimental Datasets Created

In accordance with Task 7 rules (*never silently delete or relabel records*):
- `data/raw/resume_job_fit_train.csv` remains **100% preserved and untouched**.
- A versioned experimental dataset has been generated at `results/phase11_experiments/train_cleaned_v1.csv`:
  - Exactly 12 conflicting rows (6 duplicate pairs with contradictory labels) and 1 exact duplicate row were removed.
  - Total records: **6,228 pairs**.
  - Controlled evaluation results on unchanged holdout validation are documented in `PHASE11_MODEL_COMPARISON.md`.
