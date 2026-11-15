# Phase 12D — Rigorous Head-to-Head Model Comparison Across Protocols

## Executive Summary
This report presents the clean, leak-free, apples-to-apples comparison between the **Frozen Classical Baseline** (Word TF-IDF + 15 Dense Domain Features + Cosine Similarity) and the **Pretrained Semantic Transformers** (SBERT `all-MiniLM-L6-v2` Config B and Hybrid Config D).

All models were evaluated using the sealed, immutable split manifests (`manifests/v1/`), where **each protocol trains its own dedicated model on its designated training partition with strictly zero leakage**.

---

## 1. Master Cross-Protocol Benchmark Summary

| Evaluation Protocol | Evaluation Partition | Evaluated Model | Accuracy | Balanced Acc | Macro F1 | Weighted F1 | Good Fit Recall | Good Fit Precision | Brier Score |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Job-Disjoint Val** ($N=778$, 42 Unseen Jobs) | `job_disjoint_val_v1` | **Classical Baseline** | 48.46% | 0.4330 | 0.4292 | 0.5018 | 30.08% | 21.05% | **0.8770** |
| | | **SBERT Config B** | 51.16% | **0.4795** | 0.4759 | 0.5146 | **40.60%** | 38.03% | 1.4741 |
| | | **Hybrid Config D** | **51.80%** | 0.4786 | **0.4781** | **0.5192** | 39.85% | **38.97%** | 1.4755 |
| **Resume-Disjoint Val** ($N=1,023$, 97 Unseen Resumes)| `resume_disjoint_val_v1`| **Classical Baseline** | 47.80% | 0.4571 | 0.4440 | 0.4851 | 43.25% | 34.63% | **0.9080** |
| | | **SBERT Config B** | 54.45% | 0.5463 | 0.5376 | 0.5484 | **56.75%** | 56.90% | 1.4746 |
| | | **Hybrid Config D** | **55.23%** | **0.5543** | **0.5460** | **0.5562** | 55.71% | **57.54%** | 1.4742 |
| **Dual-Unseen Val** ($N=297$, Dual Disjoint) | `dual_unseen_val_v1` | **Classical Baseline** | **39.39%** | **0.3802** | **0.3633** | **0.3951** | **39.78%** | **30.08%** | **0.9702** |
| | | **SBERT Config B** | 38.72% | 0.3524 | 0.3339 | 0.3614 | 15.05% | 28.00% | 1.3060 |
| | | **Hybrid Config D** | 36.70% | 0.3316 | 0.3169 | 0.3441 | 15.05% | 25.00% | 1.2885 |
| **Held-Out Test** ($N=1,759$, 71 Unseen Jobs) | `held_out_test_v1` | **Classical Baseline** | **48.49%** | **0.4729** | **0.4707** | **0.4851** | **47.60%** | **43.60%** | **0.9234** |
| | | **SBERT Config B** | 47.30% | 0.4468 | 0.4422 | 0.4746 | 44.76% | 40.76% | 1.3683 |
| | | **Hybrid Config D** | 46.73% | 0.4412 | 0.4368 | 0.4691 | 43.89% | 40.32% | 1.3680 |

---

## 2. In-Depth Protocol Analysis

### A. Protocol 1: Job-Disjoint Validation ($N=778$, 42 Unseen Jobs)
- **Observations**: SBERT models demonstrate a moderate advantage on unseen job descriptions.
  - SBERT Config B reaches **51.16% accuracy** and **0.4759 Macro F1** (+0.0467 over baseline).
  - Hybrid Config D reaches **51.80% accuracy** and **0.4781 Macro F1** (+0.0489 over baseline).
  - Good Fit Precision improves from **21.05% to 38.97%** (+17.92 percentage points), significantly reducing false-positive candidate recommendations.

### B. Protocol 2: Resume-Disjoint Validation ($N=1,023$, 97 Unseen Resumes)
- **Observations**: When evaluated against unseen candidates with seen job descriptions, SBERT demonstrates its strongest generalization.
  - Accuracy improves from **47.80% to 55.23%** (+7.43 percentage points).
  - Macro F1 improves from **0.4440 to 0.5460** (+0.1020).
  - Good Fit Precision improves from **34.63% to 57.54%** (+22.91 percentage points).
  - Semantic embeddings successfully generalize candidate phrasing and varied resume section structures.

### C. Protocol 3: Dual-Unseen Validation ($N=297$, Both Resumes & Jobs Unseen)
- **Observations**: **Severe distribution shift degrades all architectures**.
  - **The Classical Baseline actually outperforms SBERT**: 39.39% Accuracy / 0.3633 Macro F1 vs SBERT Config B's 38.72% Accuracy / 0.3339 Macro F1.
  - SBERT Good Fit Recall collapses to **15.05%** (identifying only 14 of 93 actual matches).
  - Neither architecture achieves viable performance; dual-unseen generalization remains near random guessing.
  - This empirical reality completely refutes the contaminated Phase 12B claim of 85.19%.

### D. Protocol 4: Official Held-Out Test ($N=1,759$, 71 Unseen Jobs)
- **Observations**: **The Classical Baseline outperforms the Semantic Transformer on the official held-out test split**.
  - Classical Baseline: **48.49% Accuracy** and **0.4707 Macro F1**.
  - SBERT Config B: **47.30% Accuracy** and **0.4422 Macro F1** (-0.0285 F1 deficit).
  - Hybrid Config D: **46.73% Accuracy** and **0.4368 Macro F1** (-0.0339 F1 deficit).
  - On the largest unseen test set ($N=1,759$), the classical baseline exhibits superior stability and better probability calibration (Brier 0.9234 vs 1.3683).

---

## 3. Confusion Matrix Breakdown

### Job-Disjoint Validation ($N=778$)
```
Classical Baseline:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit           241           108             66
Potential         52            96             82
Good Fit          45            48             40

Hybrid Config D:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit           250           115             50
Potential         97           100             33
Good Fit          61            19             53
```

### Resume-Disjoint Validation ($N=1,023$)
```
Classical Baseline:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit           271           137             78
Potential         75            93             80
Good Fit          67            97            125

Hybrid Config D:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit           266           132             88
Potential         80           138             30
Good Fit          72            56            161
```

### Dual-Unseen Validation ($N=297$)
```
Classical Baseline:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit            66            32             26
Potential         32            14             34
Good Fit          31            25             37

Hybrid Config D:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit            76            27             21
Potential         43            19             18
Good Fit          48            31             14
```

### Official Held-Out Test ($N=1,759$)
```
Classical Baseline:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit           460           203            194
Potential        163           175            106
Good Fit         125           115            218

Hybrid Config D:
             Pred No Fit  Pred Potential  Pred Good Fit
No Fit           479           187            191
Potential        182           142            120
Good Fit         150           107            201
```

---

## 4. Scientific Conclusions
1. **No Universal Transformer Superiority**: Pretrained Sentence-BERT (`all-MiniLM-L6-v2`) does not universally beat the classical baseline across all evaluation splits. On the official held-out test split, the Classical Baseline achieves higher accuracy (48.49% vs 46.73%) and higher macro F1 (0.4707 vs 0.4368).
2. **Dual-Unseen Performance Reality**: When evaluated without leakage, dual-unseen accuracy is 36%–39%, with severe recall collapse on true matches.
3. **Targeted Value**: SBERT's primary empirical strength lies in **unseen candidate matching (Resume-Disjoint)**, where it achieves +7.4% accuracy and +22.9% Good Fit precision.
4. **Promotion Ruling**: Because SBERT regresses on the official held-out test split (46.73% vs 48.49%), **promoting SBERT as a replacement for the production model is formally rejected**.
