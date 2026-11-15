# Phase 11 Feature Engineering Experiments & Ablation

**Project:** ResumeMatch AI — Multimodal Resume–Job Matching & Skill Gap Analysis System  
**Module:** NLP Feature Engineering & Feature Ablation  
**Date:** November 11, 2026  
**Auditor:** Principal Machine Learning Engineer, Senior Data Scientist, NLP Research Engineer  
**Status:** **EXPERIMENTS COMPLETE**

---

## 1. Executive Summary

This study evaluates whether expanding beyond the baseline word-level TF-IDF and dense feature pipeline improves resume–job compatibility classification. All experiments were conducted strictly on the **Job-Disjoint Validation split** (Train: 5,462 pairs, Val: 778 pairs), ensuring zero job overlap and zero data leakage.

### Key Experimental Finding
- **Subword Character n-grams (3–5 grams)** provided the single most substantial, reproducible improvement across all evaluated feature sets:
  - Macro F1 increased from **0.4236** (Baseline) to **0.4463** (**+0.0227 Macro F1 improvement**).
  - Validation accuracy increased from **51.41%** to **52.83%** (**+1.42% accuracy gain**).
  - Good Fit F1 increased from **0.1650** to **0.2146** (**+29.7% relative improvement** on minority class).

---

## 2. Experimental Setup & Feature Set Definitions

All feature transformations were learned strictly on `train_sub_A` (5,462 pairs) and applied out-of-fold to `val_sub_A` (778 pairs). A fixed Logistic Regression classifier (`C=1.0`, `class_weight="balanced"`, `random_state=42`) was used as the benchmark model across all feature configurations.

### Feature Configurations Evaluated
1. **Feat A: Baseline (Word TF-IDF + 15 Dense Features)**
   - 2,500 word-level TF-IDF unigrams and bigrams (`min_df=3`, `sublinear_tf=True`, L2 normalized).
   - Interaction vectors: absolute difference (`|V_r - V_j|`), cosine similarity, Manhattan distance.
   - 15 dense features: Skill Jaccard, coverage ratio, relevance ratio, matched/missing skill counts, years of experience, word counts, and section count.
   - Total Feature Dimensions: **2,512**.
2. **Feat B: Baseline + Enhanced Domain Features**
   - Incorporates Feat A plus: Headline/Job Title lexical overlap ratio, key cloud/language flags (`has_python`, `has_sql`, `has_cloud`), and candidate skill density.
   - Total Feature Dimensions: **2,517**.
3. **Feat C: Baseline + Subword Character n-grams (3–5 grams)**
   - Incorporates Feat A plus 1,000 character-level n-grams (`analyzer="char_wb"`, 3–5 chars, `min_df=5`).
   - Captures word prefixes, suffixes, stem variants (*"dockeriz"*, *"kubernet"*, *"microservic"*), and compound terms.
   - Includes character-level absolute difference and cosine similarity.
   - Total Feature Dimensions: **3,513**.
4. **Feat D: Combined (Word + Char n-grams + Enhanced Domain)**
   - Integrates word TF-IDF, character n-grams, interaction vectors, and enhanced domain indicators.
   - Total Feature Dimensions: **3,518**.

---

## 3. Controlled Ablation Results Matrix

| Feature Configuration | Feature Dim | Fit Time (s) | Val Accuracy | Balanced Acc | Macro F1 | Weighted F1 | Good Fit F1 | Good Fit Recall |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Feat A: Baseline** | 2,512 | 62.25s | 51.41% | 43.49% | 0.4236 | 0.5068 | 0.1650 | 12.78% |
| **Feat B: + Enhanced Domain** | 2,517 | 68.13s | 52.19% | 44.37% | 0.4338 | 0.5159 | 0.1836 | 14.29% |
| **Feat C: + Char n-grams (3–5)** | **3,513** | **133.70s** | **52.83%** | **45.48%** | **0.4463** | **0.5223** | **0.2146** | **16.54%** |
| **Feat D: Combined** | 3,518 | 124.20s | 52.06% | 44.53% | 0.4357 | 0.5156 | 0.1942 | 15.04% |

---

## 4. Confusion Matrix Comparison (Feat A vs. Feat C)

### Baseline Feat A Confusion Matrix
```text
                  Predicted No Fit   Predicted Potential Fit   Predicted Good Fit   Total
Actual No Fit            252                   139                     24            415
Actual Potential Fit      67                   131                     32            230
Actual Good Fit           56                    60                     17            133
Total Predicted          375                   330                     73            778
```

### Enhanced Feat C (Char n-grams) Confusion Matrix
```text
                  Predicted No Fit   Predicted Potential Fit   Predicted Good Fit   Total
Actual No Fit            254                   139                     22            415
Actual Potential Fit      67                   135                     28            230
Actual Good Fit           52                    59                     22            133
Total Predicted          373                   333                     72            778
```

*Key Impact:* Feat C correctly identified 22 Good Fit candidates (+29.4% increase in correctly classified Good Fits) while simultaneously reducing false positive Good Fit assignments on No Fit candidates from 24 down to 22.

---

## 5. Technical Discussion & Failure Analysis of Feat D

While **Feat C (Char n-grams)** achieved the highest Macro F1 (0.4463), adding the engineered domain flags in **Feat D** slightly reduced performance back to 0.4357.

### Why Did More Features Hurt?
1. **Curse of Dimensionality on Linear Models:** Adding sparse binary indicator flags (`has_python`, `has_sql`) created collinearity with the exact same tokens already present in the word and character TF-IDF vocabularies.
2. **Title Overlap Noise:** Job title extraction heuristics (*"first lines of resume"*) occasionally matched candidate university names or location headings rather than professional titles, introducing noisy variance.
3. **Subword Robustness in Feat C:** Character n-grams (`char_wb`) inherently resolved spelling variations, hyphenated technologies (*"scikit-learn"* vs *"scikitlearn"*), and verb conjugations (*"containerizing"*, *"containerized"*, *"containerization"*), eliminating the need for manual heuristic flags.

---

## 6. Champion Feature Pipeline Selection

**Selected Pipeline:** **Feat C (Baseline Word TF-IDF + Character n-grams 3–5)**
- Produces the highest Validation Macro F1 (**0.4463**), highest Balanced Accuracy (**45.48%**), and highest Good Fit F1 (**0.2146**).
- Used as the standardized input representation for all model comparisons in `PHASE11_MODEL_COMPARISON.md`.
