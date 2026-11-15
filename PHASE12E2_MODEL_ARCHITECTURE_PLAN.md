# ResumeMatch AI — Phase 12E-2: Dual-Track Model Architecture & Engineering Plan

**Document ID:** `PHASE12E2-ARCH-PLAN`  
**Classification:** Deep Learning Architectural Specifications & Training Pipeline Design  
**Lead Architect:** Principal Machine Learning Research Scientist & Senior NLP Engineer  
**Effective Target:** Phase 12E Experimental Execution  
**Target Repository:** `D:\skillsync1`  

---

## 1. Architectural Strategy Overview

To determine the scientifically optimal path toward high generalization and 80%+ accuracy, ResumeMatch AI designs two parallel, independently benchmarked model tracks:
- **Track A (The Classification Champion Track):** Fine-Tuned `DeBERTa-v3-small` Cross-Encoder with Structured Feature Gating. Directly targets 3-class classification for single-pair web inference.
- **Track B (The High-Throughput Retrieval Track):** Domain-Adapted Bi-Encoder (`BAAI/bge-base-en-v1.5` or `intfloat/e5-base-v2`) with ConFit v2 Runner-Up Mining (RUM) and FAISS vector indexing. Targets large-scale candidate ranking.

```
                      INCOMING (RESUME, JOB DESCRIPTION) PAIR
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
       TRACK A: CROSS-ENCODER                          TRACK B: BI-ENCODER + FAISS
   (Full Cross-Attention Token Matrix)            (Independent Document Projections)
  [CLS] JD Tokens [SEP] CV Tokens [SEP]             CV -> Emb_u (768d)  |  JD -> Emb_v (768d)
                 │                                               │
                 ▼                                               ▼
     DeBERTa-v3 Transformer Layers                     Cosine Similarity / Mined Negatives
 (12 Layers, Disentangled Attention)                  (Runner-Up Hard-Negative Loss)
                 │                                               │
                 ▼                                               ▼
   Cross-Attention Representation Head              High-Throughput Shortlist Ranker
  (Fused with 15 Dense Domain Features)             (Top-50 Candidates in < 5 ms via FAISS)
                 │                                               │
                 ▼                                               ▼
      3-CLASS SOFTMAX OUTPUT                            CANDIDATE RANKING SCORE
   [No Fit, Potential Fit, Good Fit]                         (nDCG@10, Recall@20)
       Primary Production Target                           Enterprise Search Target
```

---

## 2. Track A: Three-Class Cross-Encoder Architecture (`DeBERTa-v3-small`)

### 2.1 The Rationale for Cross-Attention
In ResumeMatch AI's user workflow, the candidate submits **EXACTLY ONE resume and ONE job description**.
- A Bi-Encoder compresses an entire 600-word CV into a single 384-dimensional vector, losing the fine-grained token connections between specific requirements (e.g. *"FastAPI with async PostgreSQL"*) and candidate achievements.
- A Cross-Encoder processes the concatenated token sequence `[CLS] Job Description [SEP] Resume Text [SEP]` through full bidirectional self-attention across all layers. Every JD requirement directly attends to every resume bullet point.

### 2.2 Handling Long Resumes without Discarding Experience
Unlike `all-MiniLM-L6-v2` (which truncated after 256 tokens), `DeBERTa-v3-small` supports up to 512 tokens natively, and we implement **Section-Aware Hierarchical Windowing**:
1. **Section Demarcation:** The resume is parsed into three segments: (a) Summary & Skills, (b) Recent Professional Experience, and (c) Education & Projects.
2. **Context Budgeting:**
   - Job Description: Allocated first 200 tokens (requirements and core duties).
   - Candidate Skills & Titles: Allocated 100 tokens.
   - Candidate Work Experience: Allocated 200 tokens.
   - Total Sequence: 500 tokens + 3 special tokens $\le 512$ tokens.
3. **Outcome:** Zero truncation of the candidate's core tech stack or primary work achievements.

### 2.3 Fusing Structured Domain Features with Deep Transformer Logits
Deep neural networks can overfit to vocabulary correlations while missing explicit quantitative rules (e.g. candidate has 1 year experience, but JD requires 5).
Track A incorporates **Structured Feature Gating**:

```
DeBERTa-v3 [CLS] Vector (768d) ──► Dense Linear Layer (64d) ──┐
                                                               ├──► Concatenated (79d) ──► Softmax (3 Classes)
Structured Domain Features (15d) ──► Standard Scaler (15d) ────┘
  (Skill overlap, Exp diff, Edu match, Seniority mismatch)
```

### 2.4 Training Hyperparameters & Loss Formulation
- **Base Checkpoint:** `microsoft/deberta-v3-small` (141M parameters).
- **Objective Function:** Weighted Cross-Entropy Loss (penalizing Good Fit false positives more heavily than Potential Fit):
  $$\mathcal{L} = -\sum_{c=1}^3 w_c \cdot y_c \log(\hat{y}_c)$$
- **Optimizer:** AdamW ($\beta_1 = 0.9, \beta_2 = 0.999$, weight decay $= 0.01$).
- **Learning Rate:** $2 \times 10^{-5}$ for transformer backbone; $1 \times 10^{-4}$ for classification head.
- **Warmup:** Linear warmup over first 10% of training steps, followed by cosine decay.
- **Batch Size:** 16 per device (effective batch size 32 via gradient accumulation).
- **Epochs:** 4 to 6 epochs with early stopping monitored on Validation Macro F1.

---

## 3. Track B: Bi-Encoder Retrieval with ConFit v2 Runner-Up Mining (RUM)

### 3.1 Model Backbone & Asymmetric Prefixing
- **Base Checkpoint:** `BAAI/bge-base-en-v1.5` (768 dimensions) or `intfloat/e5-base-v2`.
- **Directional Prompting:**
  - Job descriptions are prefixed with: `"Represent this job requirement for finding candidate profiles: "`
  - Resumes are prefixed with: `"Represent this candidate profile for job matching: "`

### 3.2 Contrastive Runner-Up Mining (RUM) Objective
Following the methodology of Yu et al. (ACL 2025):
- In a standard batch of $B$ pairs, random in-batch negatives are too easy (e.g., matching a Java developer against a Marketing job).
- **Offline RUM Implementation:**
  1. For every job $j$ in the training partition, retrieve all candidates from the training pool using BM25 or initial dense cosine similarity.
  2. Identify candidates ranked between rank 2 and rank 10 who were NOT accepted as Good Fit. These are the **Runner-Up Candidates** (they possess high surface-level keyword overlap, but have subtle disqualifying gaps).
  3. Formulate the InfoNCE loss with hard negatives:
     $$\mathcal{L}_{\text{InfoNCE}} = -\log \frac{\exp(\text{sim}(u^+, v) / \tau)}{\exp(\text{sim}(u^+, v) / \tau) + \sum_{k \in \mathcal{N}_{\text{random}}} \exp(\text{sim}(u_k, v) / \tau) + \sum_{r \in \mathcal{N}_{\text{runner-up}}} \exp(\text{sim}(u_r, v) / \tau)}$$
     where $\tau = 0.05$ is the temperature hyperparameter.

---

## 4. Hardware, Latency & Resource Specifications

| Architectural Dimension | Track A: DeBERTa-v3 Cross-Encoder | Track B: BGE Bi-Encoder + FAISS | Current Production: TF-IDF + LR |
| :--- | :---: | :---: | :---: |
| **Model Parameters** | 141 Million | 109 Million | 3,500 Weights |
| **Training Hardware Required** | 1x NVIDIA GPU ($\ge 16$ GB VRAM) | 1x NVIDIA GPU ($\ge 16$ GB VRAM) | CPU (Any multi-core) |
| **Training Time (10k pairs)** | ~25 minutes on RTX 3090 / A10G | ~18 minutes on RTX 3090 / A10G | < 15 seconds on CPU |
| **Single-Pair CPU Inference Latency** | **35 – 50 ms** | **18 – 25 ms** | **0.85 ms** |
| **RAM Footprint (Serving)** | ~380 MB | ~310 MB | **~25 MB** |
| **Batch Indexing Speed** | Infeasible ($O(N)$ transformer passes) | **100,000 CVs in < 5 ms** (FAISS) | Moderate |
| **Multi-Class Suitability** | **Native 3-Class Softmax** | Cosine Thresholding Required | Native 3-Class Softmax |
| **Expected Generalization (Unseen Jobs)**| **Highest (74% – 82%)** | Moderate-High (62% – 68%) | Baseline (48% – 50%) |

---

## 5. Comparative Evaluation & Production Promotion Criteria

Both tracks will be evaluated against the exact same Manifest V2 partitions:
- **Promotion Gate:** A candidate model will replace `models/best_model.joblib` ONLY IF:
  1. Official Held-Out Test 3-Class Accuracy $\ge 55.0\%$ (surpassing Classical Baseline 48.49%).
  2. Official Held-Out Test Macro F1 $\ge 0.5200$ (surpassing Classical Baseline 0.4707).
  3. Single-pair CPU inference latency remains under **75 ms** (comfortably under web UI budget).
  4. Memory consumption remains under **500 MB RAM**.
