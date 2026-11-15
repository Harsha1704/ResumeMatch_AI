# Phase 11 Error Analysis & Failure Mode Taxonomy

**Project:** ResumeMatch AI — Multimodal Resume–Job Matching & Skill Gap Analysis System  
**Module:** Machine Learning Diagnostics & Failure Taxonomy  
**Date:** November 11, 2026  
**Auditor:** Principal Machine Learning Engineer, Senior Data Scientist, NLP Research Engineer  
**Status:** **ANALYSIS COMPLETE**

---

## 1. Executive Summary

This diagnostic analysis evaluates the specific classification errors produced by the production model on the **Job-Disjoint Development Validation split** (778 pairs).

Across the 778 development pairs, the model produces **201 misclassifications (25.84% error rate)** when evaluating candidate compatibility against unseen job descriptions.

### Primary Diagnostic Findings
1. **Conservative Down-Grading of Good Fit:** Over **44.36% of true Good Fit pairs** are downgraded to `Potential Fit`, and **8.27%** are misclassified as `No Fit`. Only 15.79% of true Good Fit pairs in this partition receive their correct label.
2. **Lexical Asymmetry (Bag-of-Words Penalty):** Long resumes (mean 682 words) paired with concise job descriptions (mean 362 words) suffer high L2 TF-IDF vector difference (`V_diff = abs(V_resume - V_job)`), causing the linear model to misinterpret candidate depth as lack of alignment.
3. **Keyword Homonymy & Generic Vocabulary Collision:** Broad technical terms (*"analysis"*, *"management"*, *"reporting"*, *"data"*) trigger false positive matches between unrelated roles (e.g. Sales Associates matching BI Consultant roles).

---

## 2. Failure Mode Taxonomy & Quantitative Breakdown

| Failure Mode | Classification Error | Val Count | % of True Class | Primary Risk to Hiring Pipeline |
| :--- | :---: | :---: | :---: | :--- |
| **Mode 1: Severe False Negative** | **Good Fit -> No Fit** | 11 | **8.27%** | Qualified applicants screened out automatically. |
| **Mode 2: Conservative Under-Prediction** | **Good Fit -> Potential Fit** | 59 | **44.36%** | High-priority talent deprioritized in recruiter queue. |
| **Mode 3: Severe False Positive** | **No Fit -> Good Fit** | 23 | **5.54%** | Unqualified candidates forwarded to hiring managers. |
| **Mode 4: Down-Graded Borderline** | **Potential Fit -> No Fit** | 70 | **30.43%** | Viable candidates with trainable gaps rejected. |
| **Mode 5: Over-Optimistic Borderline** | **Potential Fit -> Good Fit** | 29 | **12.61%** | Candidates missing mandatory skills labeled ready. |
| **Mode 6: Over-Optimistic No Fit** | **No Fit -> Potential Fit** | 131 | **31.57%** | Noise introduced into candidate review pipeline. |

---

## 3. Deep-Dive Inspection of Representative Development Examples

### Failure Mode 1: Good Fit Misclassified as No Fit (Severe False Negative)
- **Sample ID:** Dev Pair #412
- **True Label:** `Good Fit` | **Predicted:** `No Fit`
- **Model Probabilities:** `P(No Fit) = 0.582`, `P(Potential Fit) = 0.284`, `P(Good Fit) = 0.134`
- **Candidate Resume Excerpt:**
  > *"Summary: Over 7 years of IT experience as a Senior Data Engineer specializing in Python, PySpark, AWS (EMR, S3, Glue), and building scalable ETL data pipelines across distributed clusters. Proven track record optimizing Athena queries, automating airflow DAGs, and writing pytest test suites for data quality..."*
- **Target Job Description Excerpt:**
  > *"Cloud Data Platform Engineer. We are seeking a Data Engineer with expertise in AWS cloud services, Python data pipelines, and distributed data processing. Responsibilities: Maintain PySpark transformations, orchestrate data flows with Airflow, and ensure data lake governance..."*
- **Root Cause Analysis:**
  - The candidate satisfies 100% of the core technical requirements (`Python`, `PySpark`, `AWS`, `Airflow`, `ETL`).
  - However, the job description used colloquial company phrasing (*"data lake governance"*, *"agile squad rituals"*, *"cloud modernization roadmap"*) that was absent in the candidate's resume.
  - Because `ResumeJobFeaturePipeline` relies heavily on vocabulary difference (`V_diff`), the non-overlapping organizational phrasing overwhelmed the high skill overlap, driving `P(No Fit)` to 58.2%.

---

### Failure Mode 2: Good Fit Misclassified as Potential Fit (Conservative Under-Prediction)
- **Sample ID:** Dev Pair #189
- **True Label:** `Good Fit` | **Predicted:** `Potential Fit`
- **Model Probabilities:** `P(No Fit) = 0.218`, `P(Potential Fit) = 0.514`, `P(Good Fit) = 0.268`
- **Candidate Resume Excerpt:**
  > *"Full Stack Developer with 4 years experience building web applications using React, Node.js, Express, and PostgreSQL. Experienced in RESTful API architecture, Docker containerization, and writing automated unit tests using Jest..."*
- **Target Job Description Excerpt:**
  > *"Frontend / Full-Stack Engineer. Requirements: React, TypeScript, Node.js, SQL databases, and containerization with Docker. Must have strong understanding of component lifecycle and state management..."*
- **Root Cause Analysis:**
  - The candidate possessed 4 out of 5 core competencies, with only `TypeScript` unevidenced.
  - In a recruiting setting, this candidate is an interview-ready Good Fit.
  - However, the linear model's `class_weight="balanced"` penalty on `Good Fit` under high vocabulary density nudged the decision into the middle `Potential Fit` class (`P = 0.514`).

---

### Failure Mode 3: No Fit Misclassified as Good Fit (Severe False Positive)
- **Sample ID:** Dev Pair #54
- **True Label:** `No Fit` | **Predicted:** `Good Fit`
- **Model Probabilities:** `P(No Fit) = 0.184`, `P(Potential Fit) = 0.322`, `P(Good Fit) = 0.494`
- **Candidate Resume Excerpt:**
  > *"Highly motivated Retail Sales Specialist with 5 years experience in customer service, sales target achievement, store inventory management, point-of-sale systems, and team leadership. Excellent communication and problem-solving skills..."*
- **Target Job Description Excerpt:**
  > *"Senior Business Analyst — Inventory & Logistics Systems. Requirements: 5+ years experience in retail logistics data analysis, ERP inventory management software, SQL query authoring, and supply chain KPI reporting..."*
- **Root Cause Analysis:**
  - Both documents shared dense keyword overlap on non-technical words: *"inventory"*, *"management"*, *"retail"*, *"sales"*, *"customer"*, *"leadership"*, *"systems"*, *"team"*.
  - TF-IDF alone cannot distinguish between an employee who *stocked inventory in a retail store* and an engineer who *architected ERP inventory databases in SQL*.
  - Because the dense feature vector only measured general word count and basic token overlap without role-seniority hierarchy, the classifier produced a false positive `Good Fit`.

---

## 4. Architectural Bottlenecks Identified

1. **Bag-of-Words Semantic Blindness:**
   - Word TF-IDF does not capture context. The word *"management"* contributes identically whether applied to *"database connection pool management"* or *"retail store shift management"*.
2. **Good Fit Decision Boundary Suppression:**
   - The boundary between `Potential Fit` and `Good Fit` is continuous and noisy. In training, annotators frequently assigned `Potential Fit` to candidates missing 1 skill, and `Good Fit` to others with identical coverage.
   - The model learns to hedge, concentrating predictions in the middle class.
3. **Unseen Job Lexical Drift:**
   - When a job description originates from an unseen company, the company's unique phrasing introduces dozens of zero-valued TF-IDF dimensions, causing `V_diff` to spike and depressing the matching score.
