# ResumeMatch AI — Phase 12B Hybrid Semantic + Structured Matching Report

**Document ID:** `PHASE12B_HYBRID_MODEL_RESULTS.md`  
**Author:** Principal Machine Learning Research Scientist & Systems Architect  
**Date:** November 2026  
**Status:** COMPLETE & EMPIRICALLY VERIFIED  
**Repository:** `D:\skillsync1`  

---

## 1. Executive Summary & Architectural Motivation (Experiment B)

Guided by Reference B (*A Hybrid Semantic Resume Screening Framework*, IEEE 2026), Experiment B investigated whether combining dense pretrained SBERT semantic representations with ResumeMatch AI's validated deterministic domain features yields a superior compatibility classifier.

### The Hybrid Hypothesis:
- **Pure Semantic Embeddings (SBERT):** Understands synonyms (*"Golang"* $\approx$ *"Go"*, *"AWS"* $\approx$ *"Cloud Infrastructure"*) and semantic context, but can be fooled by candidates who write extensive prose while lacking hard prerequisites.
- **Pure Structured Matching (25 Dense Features):** Strictly checks required skill coverage, experience differences, and education levels, but lacks lexical flexibility.
- **Hybrid Fusion:** An additive representation combining dense semantic vectors ($u, v, |u-v|, u \odot v, \cos$) with scaled structured verification metrics.

---

## 2. Controlled Hybrid Feature Ablation Benchmark

All configurations were evaluated on the **Job-Disjoint Validation split** ($N=778$ pairs, 53 unseen job descriptions) using regularized Logistic Regression ($C=1.0$, balanced class weights) fitted on `train_sub_job_clean`:

| Configuration & Architecture | Dimensions | Accuracy | Balanced Accuracy | Macro Precision | Macro Recall | Macro F1 | Good Fit Recall | Good Fit Precision | Good Fit F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Config A: TF-IDF Baseline**<br>(Word TF-IDF 2500 + 15 Dense) | 2,515 | 49.74% | 0.4220 | 0.4256 | 0.4220 | **0.4177** | 16.54% | 25.58% | 0.2009 |
| **Config B: Semantic Embeddings Only**<br>(SBERT Bi-Encoder Composite) | 1,537 | **50.90%** | **0.4762** | **0.4703** | **0.4762** | **0.4726** | **39.85%** | **37.59%** | **0.3869** |
| **Config C: Structured Matching Only**<br>(25 Handcrafted Dense Domain Feats) | 25 | 43.44% | 0.4034 | 0.4207 | 0.4034 | **0.3877** | 31.58% | 22.95% | 0.2658 |
| **Config D: Semantic + Structured**<br>(SBERT 1537 + 25 Dense Features) | 1,562 | 48.46% | 0.4569 | 0.4528 | 0.4569 | **0.4529** | 38.35% | 37.50% | 0.3792 |
| **Config E: Composite Full Fusion**<br>(Word TF-IDF + SBERT + 25 Dense) | 4,062 | 48.97% | 0.4616 | 0.4568 | 0.4616 | **0.4571** | 39.10% | 36.62% | 0.3782 |

---

## 3. Confusion Matrix Breakdown: Config B (Champion Architecture)

```
                       Predicted No Fit   Predicted Potential   Predicted Good Fit
True No Fit (N=415):         238                  124                   53          (Recall: 57.35%)
True Potential (N=230):       90                  105                   35          (Recall: 45.65%)
True Good Fit (N=133):        58                   22                   53          (Recall: 39.85%)

Per-Class Performance:
- No Fit:        Precision: 0.6166 | Recall: 0.5735 | F1: 0.5943
- Potential Fit: Precision: 0.4183 | Recall: 0.4565 | F1: 0.4366
- Good Fit:      Precision: 0.3759 | Recall: 0.3985 | F1: 0.3869
```

---

## 4. Key Comparative Findings

1. **Config B (Semantic Embeddings Only) is the Standout Winner:**
   - Achieves **0.4726 Macro F1**, outperforming the classical TF-IDF baseline (0.4177) by **+0.0549 Macro F1 (+13.1% relative gain)**.
   - Raises `Good Fit` recall from **16.54% to 39.85%**, while simultaneously increasing `Good Fit` precision from **25.58% to 37.59%**, yielding an F1 leap on Good Fit from **0.2009 to 0.3869 (+92.6% relative gain)**!
2. **Dense Features in Hybrid (Config D & E) Introduce Slight Regularization Penalty:**
   - While adding the 25 dense domain features (Config D) retains strong Good Fit recall (38.35%), its Macro F1 (0.4529) is slightly lower than Config B alone (0.4726).
   - *Reason:* Standard scaling of diverse non-linear features (e.g., skill counts and ratios) creates weight competition in the linear loss landscape against the 1,537 normalized embedding dimensions.
3. **Structured Matching Alone (Config C) is Insufficient:**
   - Relying purely on the 25 dense metrics without text or semantic embeddings drops accuracy to 43.44% (Macro F1: 0.3877), confirming that symbolic features cannot replace semantic prose understanding.
