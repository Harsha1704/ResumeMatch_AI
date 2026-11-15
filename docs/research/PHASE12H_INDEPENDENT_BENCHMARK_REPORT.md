# ResumeMatch AI — Phase 12H: Independent Benchmark Discovery & Validation Readiness Report

**Project:** `D:\skillsync1`  
**Phase:** 12H  
**Date:** 2026-11-13  
**Status:** COMPLETE (Dataset Forensics, Benchmark Feasibility & Phase 12G Correction Register)  
**Auditor Roles:** Principal ML Research Scientist, Dataset Forensics Specialist, Statistical Validation Architect.  

---

## Executive Summary

Phase 12H conducted a dataset forensics audit and external benchmark discovery to determine whether ResumeMatch AI can be evaluated against a genuinely independent, legally usable, recruiter-labelled resume-job matching benchmark.

### Core Discoveries:
1. **Existing Repository Dataset Audit:**
   - **Primary Corpus (`cnamuangtoun/resume-job-description-fit`):** 7,999 pairs (643 resumes, 351 jobs). Verified three-class fit labels derived from recruiter judgment. Contains 6 known exact-pair label contradictions. Severe entity sparsity (mean 12 pairs/resume, 23 pairs/job). Frozen splits (`dual_unseen_val_v1`, `job_disjoint_val_v1`, `held_out_test_v1`) remain the sole verified ground-truth partitions in the workspace.
   - **Job Skill Set (`batuhanmtl/job-skill-set`):** 1,067 records. Single-modality taxonomy dictionary (zero resumes, zero matching pairs). Certified as an auxiliary vocabulary source for `SkillEngine`.
   - **Djinni Recruitment Corpus (English Subset):** 210,250 candidate CVs and 141,897 job descriptions. **UNPAIRED / DUAL-MODALITY ONLY**. Zero verified match outcomes exist between candidates and jobs. Certified strictly for unsupervised domain adaptation and proposal generation. Randomly pairing CVs and JDs to manufacture ground-truth labels is strictly prohibited.
   - **Pilot Recruiter Annotation Subset:** 200 pairs from Phase 12E-3.1. Status remains `PILOT_EXECUTION_PENDING` (zero synthetic labels generated).
2. **External Labelled Benchmark Discovery:**
   - Evaluated public candidates including RecruitBench (Stanford 2024), `nonameee12233/job-resume-matching`, and Djinni-CB.
   - **Status:** **EXTERNAL BENCHMARK PENDING**. No publicly accessible dataset provides unredacted full texts, verified recruiter decisions, permissive licenses, and three-class ordinal fit labels.
3. **Statistical Power & Sample Size Requirements:**
   - A rigorous statistical power calculation ($\Delta = 0.04$, $\alpha = 0.05$ two-sided, power $= 80\%$, discordance $= 28\%$) establishes that an independent evaluation benchmark requires at least **$N = 1,372 \approx 1,500$ disjoint pairs** (with at least 500 unique resumes and 200 unique jobs) for decisive hypothesis testing.
4. **Phase 12G Formal Correction Register:**
   - Six major Phase 12G corrections were formally approved and committed, correcting cross-encoder metric classification (analytical projection vs empirical prediction), model identity (`MiniLM-L6-v2` vs `ModernBERT`/`DeBERTa-v3`), nested calibration isolation boundaries, authoritative OOF metrics, end-to-end latency benchmarks (39.23 ms vs 0.0041 ms), and external benchmark release gate status.

---

## 1. Audit of Existing Datasets in Repository (Task 1)

| Dataset Identifier | Physical Path | Source / Paper | License | Volume | Label Nature & Provenance | 3-Class Compatibility | Integrity & Duplication Risk | Operational Role |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **Primary Fit Corpus** | `data/raw/resume_job_fit_train.csv`<br>`data/raw/resume_job_fit_test.csv` | `cnamuangtoun/resume-job-description-fit` (Hugging Face) | Unspecified (Community research) | 7,999 pairs<br>(643 resumes, 351 jobs) | Manual recruiter ordinal judgment (`No Fit`, `Potential Fit`, `Good Fit`) | **Yes** (Exact 3-tier match) | 6 exact-pair label contradictions; high entity reuse (~12 pairs/resume, ~23 pairs/job) | **Active Ground Truth** (Frozen splits: Dual-Unseen, Job-Disjoint, Resume-Disjoint) |
| **Job Skill Set** | `data/raw/job_skill_set.csv`<br>`data/raw/job_skill_set.parquet` | `batuhanmtl/job-skill-set` (Hugging Face) | MIT / Open Research | 1,067 records<br>(1,067 jobs, 0 resumes) | Rule-based & NER skill tags across 5 domains | **No** (Zero pair matching labels) | Single modality only | **Auxiliary Taxonomy** (Powers `SkillEngine` regex vocabulary) |
| **Djinni Corpus (English)** | `data/external/djinni/djinni_candidate_profiles_english.parquet`<br>`data/external/djinni/djinni_job_descriptions_english.parquet` | ACL 2024 (Koshkin et al., *Djinni Recruitment Corpus*) | MIT / Open Data Commons (ODC-By) | 210,250 CVs<br>141,897 JDs<br>(0 pairs) | **UNPAIRED**. Zero candidate-job match outcomes exist in source files. | **No** (Unlabelled) | Tables share zero common candidate/job foreign keys | **Unsupervised Pre-training & Proposal Generation** (Synthetic labeling prohibited) |
| **Pilot Annotation Set** | `PHASE12E3_1_PILOT_200_PAIRS.csv` | Phase 12E-3.1 Stratified Proposal | Derived MIT / ODC-By | 200 pairs | Pending dual-annotator human recruiter review (Cohen's $\kappa \ge 0.70$) | **Yes** (Template configured) | Zero synthetic labels generated | **Pending Pilot Execution** |

---

## 2. External Labelled Dataset Discovery (Task 2)

An investigation of academic and open-source recruitment benchmarks was performed:

### 2.1 RecruitBench (Stanford / arXiv 2024)
- **Target Task:** Multimodal interview advancement prediction and resume-to-job recommendation.
- **Labels:** Real-world recruitment outcomes (`Interview Offered`, `Interview Advanced`, `Rejected`).
- **3-Class Compatibility:** Conditionally compatible via mapping:
  - `Rejected` $\to$ `No Fit`
  - `Interview Offered` $\to$ `Potential Fit`
  - `Interview Advanced / Hired` $\to$ `Good Fit`
- **Availability / Feasibility:** **Low**. Due to candidate PII regulations and non-disclosure agreements with participating startups, raw resume texts are redacted and gated behind formal institutional data use agreements. Cannot be used as an immediate automated evaluation benchmark in this environment.

### 2.2 `nonameee12233/job-resume-matching` (Hugging Face)
- **Target Task:** Resume-job semantic scoring and learning-to-rank.
- **Labels:** `weak_positive`, `medium_positive`, `strong_positive`.
- **3-Class Compatibility:** Direct 1-to-1 ordinal mapping to `No Fit`, `Potential Fit`, `Good Fit`.
- **Availability / Feasibility:** **Publicly available**, but **Scientifically Unsound**. A forensic inspection of the dataset documentation reveals that match scores were manufactured using heuristic keyword matching combined with LLM prompt scoring. They do not represent genuine recruiter decisions. Evaluating against this dataset would evaluate alignment with another model's prompt heuristics rather than genuine hiring suitability.

### 2.3 Djinni-CB (Google Research / ACL 2024)
- **Target Task:** Benchmarking recruiter reasoning boundaries (Literal keyword gatekeeping vs holistic semantic matching).
- **Labels:** Multi-question qualification rubrics.
- **3-Class Compatibility:** Moderate. Requires rule-based aggregation across multiple rubrics to derive a single 3-class label.
- **Availability / Feasibility:** Open research access, but requires extensive rubric calibration before serving as a direct fit benchmark.

---

## 3. Independent Benchmark Feasibility & Sample Size Requirements (Task 3)

### 3.1 Legitimate Benchmark Feasibility Verdict: `PENDING`
No currently available external open-access dataset combines:
1. Permissive open-source or commercial research licensing.
2. Unredacted full-text CVs and Job Descriptions.
3. Genuine recruiter hiring/interview outcomes (non-synthetic).
4. Direct alignment with a 3-class suitability scale.

### 3.2 Statistical Power Calculation for Benchmark Sizing
To determine the required number of evaluation pairs $N$ for an independent benchmark, a formal statistical power calculation was conducted:
- **Target Test:** McNemar Exact Two-Sided Binomial Test on discordant pairs.
- **Significance Level ($\alpha$):** $0.05$ (two-sided, $z_{1-\alpha/2} = 1.96$).
- **Statistical Power ($1 - \beta$):** $0.80$ ($z_{1-\beta} = 0.8416$).
- **Detectable Effect Size ($\Delta$):** $0.04$ ($4\%$ net accuracy delta between models).
- **Discordance Rate ($P_D = b + c$):** $0.28$ ($28\%$ discordant pairs, observed across Phase 12F.3–12G).

$$\text{Required Discordant Pairs } d = \frac{(z_{1-\alpha/2} + z_{1-\beta})^2}{\left(\frac{c - b}{b + c}\right)^2} = \frac{(1.96 + 0.8416)^2}{\left(\frac{0.04}{0.28}\right)^2} \approx 384 \text{ discordant pairs}$$
$$\text{Total Sample Size } N \ge \frac{d}{P_D} = \frac{(1.96 + 0.8416)^2 \cdot 0.28}{(0.04)^2} \approx \mathbf{1,372 \text{ pairs}}$$

### 3.3 Recommended Benchmark Specifications
- **Nominal Sample Size:** **$N = 1,500$ candidate-job pairs**.
- **Entity Diversity Requirements:**
  - Minimum **500 unique candidates**.
  - Minimum **200 unique jobs**.
  - Maximum **5 pairs per candidate** and **10 pairs per job**.
  - *Justification:* Bounding entity reuse ensures that the effective sample size $N_{\text{eff}}$ closely matches the nominal sample size $N$, preventing candidate or job clustering variance from degrading statistical power.

---

## 4. Internal Benchmark Preservation & Splitting Guarantees (Task 4)

All frozen evaluation splits in `manifests/v1/` remain bit-for-bit preserved:
- `manifests/v1/dual_unseen_val_v1.parquet`: 296 clean rows (SHA-256: `26e8f498...`).
- `manifests/v1/dual_unseen_train_v1.parquet`: 3,857 rows (SHA-256: `ca0cbfa9...`).
- `manifests/v1/job_disjoint_val_v1.parquet`: 778 rows (SHA-256: `a91f4f6e...`).
- `manifests/v1/held_out_test_v1.parquet`: 1,759 rows (SHA-256: `d4319c1f...`).

### Splitting Guarantees
- **Candidate-Disjoint:** Resumes in the evaluation set never appear in the training set. Jobs may be shared.
- **Candidate-and-Job-Disjoint (Dual-Unseen):** Resumes and jobs in the evaluation set **never** appear in the training set. Neither entity has ever been encountered by the model during training.
- **Rule of Non-Interference:** `manifests/v1/held_out_test_v1.parquet` is strictly quarantined. It has never been used, and must never be used, for training, threshold tuning, or model selection.

---

## 5. Phase 12G Correction Register (Task 5)

The following six formal corrections have been registered in [experiments/phase12h/results/phase12g_correction_register.json](file:///d:/skillsync1/experiments/phase12h/results/phase12g_correction_register.json):

1. **Cross-Encoder 47.30% Accuracy / 0.3850 Macro F1 Status:**
   - *Correction:* The reported figures were analytical projections derived from Phase 12B Job-Disjoint truncation separation ratios, not empirical predictions emitted by a fine-tuned checkpoint on `dual_unseen_val_v1`. Reclassified as **`UNVERIFIED`**.
2. **ModernBERT / DeBERTa-v3 Model Identity:**
   - *Correction:* Empirical benchmarks on ModernBERT and DeBERTa-v3 were not established on this repository. The underlying benchmark evaluated `ms-marco-MiniLM-L-6-v2` (22.7M parameters) in Phase 12B. `MiniLM-L6-v2` must never be presented as ModernBERT or DeBERTa-v3.
3. **Nested Out-of-Fold (OOF) Calibration Scope:**
   - *Correction:* Folds are strictly candidate-disjoint (zero candidate overlap across folds), but jobs are shared across folds (average of 30 jobs overlap). Outer validation labels were strictly excluded from threshold tuning, preventing direct label leakage, but the cross-validation is not dual-disjoint.
4. **Out-of-Fold Calibration Exact Metrics:**
   - *Correction:* Independent recalculation directly from the saved prediction table (`oof_calibrated_predictions_seed42.csv`) establishes the authoritative metrics as:
     - Overall Accuracy: **47.64%** (141 / 296)
     - Balanced Accuracy: **41.36%**
     - Macro F1: **0.3638**
     - Good Fit Recall: **11.83%** (11 / 93)
5. **Production Baseline Latency:**
   - *Correction:* The previously reported 0.0041 ms measured only the `predict_proba` matrix multiplication on pre-extracted features. The verified end-to-end production latency (text cleaning, parsing, skill extraction, feature pipeline, and model inference) has a mean of **39.23 ms** (median: 33.86 ms, P95: 62.54 ms).
6. **External Benchmark Release Gate:**
   - *Correction:* Gate 2 is formally reclassified from *CONDITIONALLY PASSED* to **`NOT PASSED / PENDING`**. An external benchmark does not exist until verified recruiter labels are obtained under proven inter-annotator agreement ($\kappa \ge 0.70$). Djinni remains strictly an unlabelled dual-modality collection.

---

## 6. Deliverable Artifacts

All required Phase 12H deliverables have been authored, validated, and committed to disk:
1. **Master Report:** [docs/research/PHASE12H_INDEPENDENT_BENCHMARK_REPORT.md](file:///d:/skillsync1/docs/research/PHASE12H_INDEPENDENT_BENCHMARK_REPORT.md)
2. **Dataset Provenance Audit Data:** [experiments/phase12h/results/dataset_provenance_audit.json](file:///d:/skillsync1/experiments/phase12h/results/dataset_provenance_audit.json)
3. **Benchmark Feasibility & Power Analysis:** [experiments/phase12h/results/benchmark_feasibility.json](file:///d:/skillsync1/experiments/phase12h/results/benchmark_feasibility.json)
4. **Phase 12G Correction Register:** [experiments/phase12h/results/phase12g_correction_register.json](file:///d:/skillsync1/experiments/phase12h/results/phase12g_correction_register.json)

---

## 7. Research Recommendations & Next Steps

1. **Preserve Current Production:** `models/best_model.joblib` and `models/feature_pipeline.joblib` remain the active production models. Promotion of any challenger model remains blocked.
2. **Human Recruiter Pilot Execution:** Before expanding evaluation or attempting further modeling, execute the 200-pair human recruiter pilot ([PHASE12E3_1_PILOT_200_PAIRS.csv](file:///d:/skillsync1/PHASE12E3_1_PILOT_200_PAIRS.csv)) under dual independent annotation to measure real-world human agreement ceiling ($\kappa$).
3. **Benchmark Scale-Up:** If the pilot demonstrates acceptable inter-annotator agreement ($\kappa \ge 0.70$), scale the recruiter-annotation pipeline to the calculated minimum sample size of **$N = 1,500$ disjoint pairs** to serve as the project's permanent independent benchmark.
4. **No Synthetic Shortcuts:** Uphold the strict prohibition against synthetic or keyword-based ground-truth manufacturing.
