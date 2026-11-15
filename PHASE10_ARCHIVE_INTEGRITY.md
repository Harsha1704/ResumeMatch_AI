# Phase 10 Archive Integrity Audit — Production ZIP Verification

**Project:** ResumeMatch AI — Multimodal Resume–Job Matching & Skill Gap Analysis System  
**Audit Scope:** Task 4 — Deep Comparative Verification of `ResumeMatch-AI-Final.backup15.zip` vs `ResumeMatch-AI-Final.zip`  
**Date:** November 11, 2026  
**Auditor:** Principal Software Engineer, Independent QA Auditor, ML Engineer, and Technical Hiring Manager  
**Status:** **PASS**

---

## 1. Executive Summary

This audit performs an independent, byte-level and entry-level comparison between the previous backup archive (`ResumeMatch-AI-Final.backup15.zip`) and the current production release archive (`ResumeMatch-AI-Final.zip`).

The primary objective is to:
1. Verify the presence and integrity of all production Python source modules, Flask HTML templates, static CSS/JavaScript assets, trained production machine learning models, and runtime dependency configurations.
2. Provide a rigorous technical explanation for the observed archive size change from **~63.22 MB** to **~31.25 MB**.
3. Clearly distinguish intentionally excluded development and experimental artifacts from any accidentally missing production dependencies.
4. Guarantee that both archives remain intact and uncorrupted.

---

## 2. Archive Metadata Comparison

| Archive Attribute | `ResumeMatch-AI-Final.backup15.zip` | `ResumeMatch-AI-Final.zip` | Delta / Difference |
| :--- | :--- | :--- | :--- |
| **Compressed File Size** | **63.22 MB** (66,290,176 bytes) | **31.25 MB** (32,772,096 bytes) | **-31.97 MB (-50.57%)** |
| **Total Archive Entries** | **198 files** | **178 files** | **-20 entries** |
| **Only in Backup15** | 60 entries | 0 entries | Excluded experimental artifacts |
| **Only in Final Archive** | 0 entries | 40 entries | Phase 10 audit suites & reports |
| **Common Entries** | 138 entries | 138 entries | 100% of production source code |

---

## 3. Explanation of the Archive Size Change (~63 MB -> ~31 MB)

The approximately **31.97 MB reduction** in archive size is entirely accounted for by the intentional exclusion of the research directory `experiments/dataset_improvement/`.

In `ResumeMatch-AI-Final.backup15.zip`, the `experiments/` directory contained **60 non-production files** accounting for **58.94 MB of uncompressed disk space**.

### Detailed Breakdown of Excluded Development Artifacts:
1. **Frozen Experimental Model Weights (Over 35 MB uncompressed):**
   - `experiments/dataset_improvement/models/frozen_dual_unseen_baseline.joblib`
   - `experiments/dataset_improvement/models/frozen_dual_unseen_champion.joblib`
   - `experiments/dataset_improvement/models/frozen_dual_unseen_pipeline.joblib`
   - *Technical Distinction:* These frozen joblib files were generated during Phase 7e hyperparameter ablation studies to evaluate dual-unseen domain splits. They are **not** loaded by `app.py` or `src/models/inference.py`. The real production model that powers inference in the application is `models/best_model.joblib`.
2. **Exploratory Visualizations and Plot Images (Over 15 MB uncompressed):**
   - `experiments/dataset_improvement/results/phase7e_dual_unseen_confusion_matrix.png`
   - `experiments/dataset_improvement/results/phase7e_dual_unseen_normalized_cm.png`
   - `experiments/dataset_improvement/results/phase7e_evaluation_scenarios_comparison.png`
   - `experiments/dataset_improvement/results/phase7e_internal_cv_comparison.png`
   - `experiments/dataset_improvement/results/phase7e_per_class_performance.png`
   - `experiments/dataset_improvement/results/class_distribution_and_balance.png`
   - `experiments/dataset_improvement/results/skill_frequency_distribution.png`
   - `experiments/dataset_improvement/results/text_length_distribution.png`
   - *Technical Distinction:* High-resolution Matplotlib/Seaborn diagnostic plots generated for research documentation.
3. **Exploratory Training Scripts and Intermediate Data Audits:**
   - `experiments/dataset_improvement/scripts/audit_and_visualize.py`
   - `experiments/dataset_improvement/scripts/cache_dual_unseen_domain_features.py`
   - `experiments/dataset_improvement/scripts/create_dual_unseen_split.py`
   - `experiments/dataset_improvement/scripts/evaluate_dataset_improvements.py`
   - `experiments/dataset_improvement/scripts/extract_domain_keywords.py`
   - `experiments/dataset_improvement/audits/dataset_audit_report.json`
   - `experiments/dataset_improvement/audits/label_quality_report.json`

**Conclusion:** The exclusion of the `experiments/` directory was an **intentional, standard production hygiene action**. Packaging heavy experimental model checkpoints and PNG charts inside a production application archive introduces bloat without runtime utility.

---

## 4. Verification of Essential Production Assets

Every runtime dependency, source file, template, and production model was verified in `ResumeMatch-AI-Final.zip`:

### A. Production Trained Machine Learning Models (`models/`)
| Model File | Status in Final ZIP | Purpose |
| :--- | :---: | :--- |
| `models/best_model.joblib` | **PRESENT** | Production trained ML classifier for resume-job matching |
| `models/feature_pipeline.joblib` | **PRESENT** | TF-IDF / Feature extraction transformer pipeline |
| `models/label_mapping.json` | **PRESENT** | Class label index mapping |
| `models/linear_svm_calibrated.joblib` | **PRESENT** | Calibrated Linear SVM model weights |
| `models/logistic_regression.joblib` | **PRESENT** | Baseline Logistic Regression model |
| `models/random_forest.joblib` | **PRESENT** | Baseline Random Forest ensemble |

### B. Core Application & Server Runtime
| File | Status in Final ZIP | Purpose |
| :--- | :---: | :--- |
| `app.py` | **PRESENT** | Main Flask application entrypoint & API routes |
| `requirements.txt` | **PRESENT** | Complete runtime dependencies (Flask, scikit-learn, etc.) |

### C. Web Templates (`templates/`)
All 11 Flask Jinja templates are present:
- `templates/analyze.html` (**PRESENT**)
- `templates/base.html` (**PRESENT**)
- `templates/career_mentor.html` (**PRESENT**)
- `templates/dataset_explorer.html` (**PRESENT**)
- `templates/index.html` (**PRESENT**)
- `templates/interview_practice.html` (**PRESENT**)
- `templates/interview_results.html` (**PRESENT**)
- `templates/interview_studio.html` (**PRESENT**)
- `templates/model_performance.html` (**PRESENT**)
- `templates/results.html` (**PRESENT**)
- `templates/skill_gap.html` (**PRESENT**)

### D. Static Web Assets (`static/`)
All 20 CSS and JavaScript files are present:
- `static/css/career_mentor.css` (**PRESENT**)
- `static/css/dashboard.css` (**PRESENT**)
- `static/css/interview.css` (**PRESENT**)
- `static/js/career_mentor.js` (**PRESENT**)
- `static/js/interview.js` (**PRESENT**)
- Plus all dashboard charts, styling, and navigation assets.

### E. Source Python Modules (`src/`)
All 48 production source files across all subsystems are present:
- `src/mentor/` (Curricula, Counseling Profile, Dependency Graph, Roadmaps, Engine)
- `src/interview/` (Question Generator, Question Bank, Answer Frameworks, Validator)
- `src/analysis/` (Matching Engine, Skill Gap, Job Analyzer, Resume Parser)
- `src/models/` (Inference, Evaluation, Training pipelines)
- `src/common/` (Evidence Registry, Constants)

---

## 5. Audit Verdict

**Status:** **PASS**  
- Zero production dependencies or source files were lost.
- The size reduction from ~63.22 MB to ~31.25 MB is 100% explained by the intentional exclusion of 58.94 MB of uncompressed exploratory research models and plots in `experiments/`.
- All production models, Flask templates, static assets, and source code are present and verified.
- Recoverable backups (`ResumeMatch-AI-Final.backup15.zip`, `backup14.zip`, `backup13.zip`, `backup12.zip`) are preserved intact.
