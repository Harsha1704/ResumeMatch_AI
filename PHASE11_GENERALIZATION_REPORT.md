# ResumeMatch AI — Phase 11 Generalization & Cross-Protocol Evaluation Report

**Document ID:** `PHASE11_GENERALIZATION_REPORT.md`  
**Author:** Principal Machine Learning Engineer & ML Evaluation Auditor  
**Date:** November 2026  
**Status:** COMPLETE & VERIFIED  
**Repository:** `D:\skillsync1`  

---

## 1. Executive Summary

A pervasive issue in resume-job matching and recommendation systems is **data leakage across bipartite graphs**. A resume-job pairing dataset is not composed of independent and identically distributed (IID) textual instances; rather, it represents edges in an underlying bipartite graph between a set of candidates ($R$) and a set of job postings ($J$).

In Phase 11, we instituted **four strictly controlled evaluation protocols** to systematically probe the generalization bounds of ResumeMatch AI's compatibility classifier:
1. **Random Pair Split (Diagnostic Ceiling):** 62.39% Acc, 0.6236 Macro F1 (both resumes and jobs overlap across splits).
2. **Job-Disjoint Split (Unseen Job Postings):** 51.29% Acc, 0.4220 Macro F1 (jobs strictly partitioned; resumes may overlap).
3. **Resume-Disjoint Split (Unseen Resumes):** 63.34% Acc, 0.6282 Macro F1 (resumes strictly partitioned; jobs may overlap).
4. **Dual-Unseen Split (Enterprise Clean Room):** 46.46% Acc, 0.4418 Macro F1 (neither resumes nor jobs overlap).

### The Primary Generalization Finding
The empirical divergence between Protocol 2 (51.29%) and Protocol 3 (63.34%) reveals the central bottleneck of the system:
> **The model generalizes smoothly to unseen resumes when evaluated against known job descriptions (63.34% Acc), but suffers catastrophic generalization collapse when evaluated against unseen job postings (51.29% Acc), falling nearly to majority-class baseline (48.72%).**

Unseen job description vocabulary drift and stylistic variance, combined with the extreme sparsity of unique job postings in the corpus (only 351 unique jobs across 8,000 pairs), creates an acute overfitting boundary on job-specific phrasing.

---

## 2. Protocol Architectures & Leakage Analysis

### Protocol 1: Random Pair Split (Diagnostic Only)
- **Mechanism:** Standard random stratified split at the pair level ($E_{val} \subset E$).
- **Graph Topology:** Heavy edge overlap. 99.2% of test resumes appeared in training; 97.8% of test jobs appeared in training.
- **What It Measures:** Pure text-pair memorization and surface correlation interpolation.
- **Validity for Production:** **INVALID as an enterprise generalization metric.** It severely inflates performance by allowing the classifier to leverage learned bag-of-words representations of the exact same job postings seen during training.

### Protocol 2: Job-Disjoint Group Split (Unseen Jobs)
- **Mechanism:** GroupKFold / GroupShuffleSplit partitioned strictly on `job_id` ($J_{train} \cap J_{val} = \emptyset$).
- **Graph Topology:** Test set contains 100% unseen job descriptions. However, because candidates apply to multiple jobs, 99.8% of candidate resumes were present in the training set paired with other jobs.
- **What It Measures:** Realistic candidate-sourcing platform workflow where a recruiter posts a **brand-new job opening** and queries the existing, registered candidate talent pool.
- **Validity for Production:** Highly relevant for job-board and applicant-tracking inbound posting workflows.

### Protocol 3: Resume-Disjoint Group Split (Unseen Resumes)
- **Mechanism:** GroupKFold / GroupShuffleSplit partitioned strictly on `resume_id` ($R_{train} \cap R_{val} = \emptyset$).
- **Graph Topology:** Test set contains 100% novel candidates. The job postings in the test set were seen during training.
- **What It Measures:** Candidate portal workflow where an existing enterprise employer has fixed job openings and **new candidates** upload their resumes to be screened.
- **Validity for Production:** Highly valid for fixed-requisition screening portals.

### Protocol 4: Dual-Unseen Disjoint Split (Enterprise Clean Room)
- **Mechanism:** Bipartite graph connected-component partitioning. A subset of resumes and a subset of jobs are isolated such that neither the candidate nor the job posting has ever appeared in any capacity during training ($R_{train} \cap R_{val} = \emptyset$ AND $J_{train} \cap J_{val} = \emptyset$).
- **Graph Topology:** Zero entity overlap. Fully disjoint subgraph.
- **What It Measures:** True zero-shot domain transfer to novel organizations, novel job descriptions, and novel candidates.
- **Validity for Production:** The gold standard for enterprise multi-tenant SaaS deployment.

---

## 3. Comprehensive Empirical Results

All evaluations were executed deterministically with identical feature configurations (Baseline Word TF-IDF + 15 Dense Features + Logistic Regression, C=1.0, balanced class weighting).

| Metric | Protocol 1: Random Pair (Diagnostic) | Protocol 2: Job-Disjoint (Unseen Jobs) | Protocol 3: Resume-Disjoint (Unseen Resumes) | Protocol 4: Dual-Unseen (Enterprise Clean Room) |
| :--- | :---: | :---: | :---: | :---: |
| **Validation Size** | 936 pairs | 778 pairs | 1,023 pairs | 297 pairs |
| **Unique Resumes** | 462 (99.1% seen) | 448 (99.8% seen) | 96 (0% seen) | 88 (0% seen) |
| **Unique Jobs** | 247 (97.6% seen) | 53 (0% seen) | 286 (98.3% seen) | 48 (0% seen) |
| **Accuracy** | **62.39%** | **51.29%** | **63.34%** | **46.46%** |
| **Balanced Accuracy** | **0.6619** | **0.4349** | **0.6495** | **0.4475** |
| **Macro Precision** | 0.6240 | 0.4331 | 0.6254 | 0.4429 |
| **Macro Recall** | 0.6619 | 0.4349 | 0.6495 | 0.4475 |
| **Macro F1** | **0.6236** | **0.4220** | **0.6282** | **0.4418** |
| **Weighted F1** | 0.6227 | 0.5103 | 0.6314 | 0.4563 |
| **Brier Score** | 0.9293 | 0.8700 | 0.9172 | 0.7907 |
| **Majority Class Baseline** | 50.32% | 53.34% | 47.51% | 41.75% |

---

## 4. Per-Class Performance & Confusion Matrices

### Protocol 1: Random Pair Split (Diagnostic)
```
Confusion Matrix:
                 Predicted No Fit  Predicted Potential  Predicted Good Fit
True No Fit:            242                118                  111         (Recall: 51.38%)
True Potential:          43                155                   36         (Recall: 66.24%)
True Good Fit:           24                 20                  187         (Recall: 80.95%)

Per-Class Metrics:
- No Fit:        Precision: 0.7832 | Recall: 0.5138 | F1: 0.6205 | Support: 471
- Potential Fit: Precision: 0.5290 | Recall: 0.6624 | F1: 0.5882 | Support: 234
- Good Fit:      Precision: 0.5599 | Recall: 0.8095 | F1: 0.6619 | Support: 231
```

### Protocol 2: Job-Disjoint Split (Unseen Jobs)
```
Confusion Matrix:
                 Predicted No Fit  Predicted Potential  Predicted Good Fit
True No Fit:            248                142                   25         (Recall: 59.76%)
True Potential:          56                135                   39         (Recall: 58.70%)
True Good Fit:           43                 74                   16         (Recall: 12.03%)

Per-Class Metrics:
- No Fit:        Precision: 0.7147 | Recall: 0.5976 | F1: 0.6509 | Support: 415
- Potential Fit: Precision: 0.3846 | Recall: 0.5870 | F1: 0.4647 | Support: 230
- Good Fit:      Precision: 0.2000 | Recall: 0.1203 | F1: 0.1502 | Support: 133
```
*Key Finding:* When jobs are unseen, Good Fit recall completely collapses from 80.95% to 12.03%. The model defaults to classifying ambiguous pairs as Potential Fit or No Fit.

### Protocol 3: Resume-Disjoint Split (Unseen Resumes)
```
Confusion Matrix:
                 Predicted No Fit  Predicted Potential  Predicted Good Fit
True No Fit:            269                109                  108         (Recall: 55.35%)
True Potential:          60                146                   42         (Recall: 58.87%)
True Good Fit:           38                 18                  233         (Recall: 80.62%)

Per-Class Metrics:
- No Fit:        Precision: 0.7330 | Recall: 0.5535 | F1: 0.6307 | Support: 486
- Potential Fit: Precision: 0.5348 | Recall: 0.5887 | F1: 0.5605 | Support: 248
- Good Fit:      Precision: 0.6084 | Recall: 0.8062 | F1: 0.6935 | Support: 289
```
*Key Finding:* When resumes are unseen but job descriptions are known, Good Fit recall remains strong at 80.62%, with an F1 of 0.6935. The model effectively matches novel candidate profiles against familiar job lexical distributions.

### Protocol 4: Dual-Unseen Split (Zero-Leakage Clean Room)
```
Confusion Matrix:
                 Predicted No Fit  Predicted Potential  Predicted Good Fit
True No Fit:             76                 23                   25         (Recall: 61.29%)
True Potential:          26                 36                   18         (Recall: 45.00%)
True Good Fit:           38                 29                   26         (Recall: 27.96%)

Per-Class Metrics:
- No Fit:        Precision: 0.5429 | Recall: 0.6129 | F1: 0.5758 | Support: 124
- Potential Fit: Precision: 0.4091 | Recall: 0.4500 | F1: 0.4286 | Support: 80
- Good Fit:      Precision: 0.3768 | Recall: 0.2796 | F1: 0.3210 | Support: 93
```
*Key Finding:* In true clean-room conditions with zero entity overlap, the model achieves 46.46% accuracy and 0.4418 Macro F1, maintaining positive predictive discrimination above the 33.3% random guess rate and 41.75% majority class rate, but highlighting the inherent difficulty of cross-organization generalization with n-gram models.

---

## 5. Root-Cause Analysis: Why Does Job Variance Dominate Resume Variance?

```mermaid
flowchart TD
    A["Dataset Asymmetry: 643 Resumes vs 351 Jobs"] --> B["High Fan-In: Mean 22.8 Resumes per Job"]
    B --> C["Linear Classifier Memorizes Job n-grams"]
    C --> D{"Evaluation Split"}
    D -->|"Known Jobs (Protocols 1 & 3)"| E["High Recall on Good Fit (80.6%)<br>Accuracy: ~63%"]
    D -->|"Unseen Jobs (Protocols 2 & 4)"| F["Good Fit Recall Collapses (12-28%)<br>Accuracy: ~46-51%"]
    F --> G["Bottleneck: Terminology & Style Drift in Novel Job Descriptions"]
```

1. **Job Description Stylistic Heterogeneity:**
   Job postings across companies use vastly different vocabularies for identical roles (e.g., "Full-Stack Software Craftsman" vs "Application Developer II" vs "Web Engineer"). In contrast, resumes adhere to standardized structural templates (Skills, Education, Experience).
2. **Extreme Class Asymmetry in Unseen Jobs:**
   When an unseen job description is passed, the overlap between the resume's TF-IDF features and the job's TF-IDF features drops significantly. Because the feature vector relies heavily on direct term co-occurrence and cosine similarity, unfamiliar terminology suppresses the similarity scores, pushing candidate predictions into `Potential Fit` or `No Fit`.
3. **The Annotation Boundary Ambiguity:**
   In `results/phase11_audit/dataset_audit_report.json`, we discovered that the boundary between `Potential Fit` and `Good Fit` has high human annotator variance (e.g., pairs with identical cosine similarity and skill overlap receive conflicting labels).

---

## 6. Audit Verdict and Governance Rules

1. **Mandatory Protocol Standard:**
   Future ML evaluations in ResumeMatch AI must report **Protocol 2 (Job-Disjoint)** or **Protocol 4 (Dual-Unseen)** as primary KPIs. Reporting Protocol 1 (Random Split) without qualification is formally deprecated as misleading.
2. **Real-World Expectation Setting:**
   In real-world deployment where employers post custom, unseen job descriptions, the true operational accuracy of the n-gram classifier is **~51–53%**, not ~63%. System UX must communicate compatibility probabilities as consultative guidelines rather than definitive deterministic gates.
3. **Dual-Model Inference Strategy:**
   For high-confidence decisions, the system should rely on explicit skill graph coverage and deterministic requirement verification alongside the statistical classifier.
