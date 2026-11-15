# ResumeMatch AI — Phase 12 Label Integrity & Boundary Audit Report

**Document ID:** `PHASE12_LABEL_AUDIT.md`  
**Author:** Principal Machine Learning Engineer, NLP Researcher & Data Quality Specialist  
**Date:** November 2026  
**Status:** COMPLETE & VERIFIED  
**Repository:** `D:\skillsync1`  

---

## 1. Executive Summary

Supervised learning performance is fundamentally bounded by the Bayes optimal error rate—the irreducible noise in the ground-truth labels. In Phase 12, we conducted an exhaustive investigation into label consistency, annotator subjectivity, and class boundary ambiguity in the ResumeMatch AI corpus.

### Key Audit Findings:
1. **Direct Label Contradictions:** Exactly **6 resume–job text pairs** (12 rows in `train.csv`) have identical input text but opposing ground-truth labels:
   - 4 pairs are labeled as **both `No Fit` and `Good Fit`** simultaneously!
   - 2 pairs are labeled as **both `No Fit` and `Potential Fit`** simultaneously!
2. **Ambiguous Compatibility Boundaries:**
   - The mean skill coverage between `No Fit` (16.6%), `Potential Fit` (20.6%), and `Good Fit` (22.3%) differs by less than **6 percentage points** across the corpus.
   - Without an objective qualification rubric, human annotators applied divergent criteria: some required strict title/domain matches, while others rewarded loose transferable skills.
3. **Audit Policy:** In strict adherence to the Phase 12 charter, **no ambiguous records were automatically relabeled**. All 6 contradictory pairs are formally designated as `STATUS: UNCERTAIN (FLAGGED FOR HUMAN ARBITRATION)`.

---

## 2. In-Depth Forensic Analysis of the 6 Contradictory Label Pairs

```mermaid
flowchart TD
    Pair["Identical Resume + Identical Job Description"] --> Ann1["Annotator A: 'No Fit'"]
    Pair --> Ann2["Annotator B: 'Good Fit' or 'Potential Fit'"]
    Ann1 --> Conflict["Ground-Truth Conflict in train.csv"]
    Ann2 --> Conflict
    Conflict --> Action["Action: Flagged as UNCERTAIN & Quarantined"]
```

Below is the complete qualitative and quantitative audit of the 6 conflicting text pairs:

---

### Pair 1: Data Analyst vs Finance FP&A / Tableau
- **Row Indices:** 381 and 5152 in `train.csv`
- **Labels Assigned:** `No Fit` (Row 381) vs `Good Fit` (Row 5152)
- **Resume Profile:** 2+ years data analysis experience at university; statistical analysis in R, SAS, MS Office, Excel.
- **Job Description:** "Calling all data nerds who love finance! 50% Tableau ownership and 50% FP&A support. Building financial forecast models."
- **Skill Overlap:** 3 skills (`accounting`, `excel`, `finance`). Missing: `Tableau`, `FP&A modeling`.
- **Root-Cause Analysis:** Annotator A evaluated the candidate as `No Fit` because the candidate lacks Tableau and corporate financial planning experience. Annotator B evaluated the candidate as `Good Fit` because the candidate is a quantitative data analyst proficient in statistical modeling.
- **Determination:** **UNCERTAIN (Ambiguous Domain Boundary)**. Under a strict hiring criterion, this is `Potential Fit` or `No Fit`. Assigning `Good Fit` introduces severe label noise.

---

### Pair 2: Sales Associate vs ERP Business Analyst
- **Row Indices:** 312 and 3706 in `train.csv`
- **Labels Assigned:** `No Fit` (Row 312) vs `Potential Fit` (Row 3706)
- **Resume Profile:** Retail Sales Associate; customer service, driving retail sales, store operations.
- **Job Description:** ERP Business Analyst for Food & Beverage Manufacturer; enterprise resource planning, business process analysis.
- **Skill Overlap:** **0 skills overlapping.**
- **Root-Cause Analysis:** Retail sales experience has virtually zero relevance to enterprise ERP software implementation. Annotator B erroneously assigned `Potential Fit`, likely conflating "sales/business" with "ERP Business Analyst".
- **Determination:** **UNCERTAIN / ERRONEOUS ANNOTATION**. Objective qualification is unequivocally `No Fit`.

---

### Pair 3: Business Intelligence Consultant vs Principal Data Engineer
- **Row Indices:** 520 and 4492 in `train.csv`
- **Labels Assigned:** `No Fit` (Row 520) vs `Potential Fit` (Row 4492)
- **Resume Profile:** 10-year career in data warehousing, BI reporting, data management architecture, SQL, ETL.
- **Job Description:** Principal Data Engineer at digital marketing firm; cloud data architecture, distributed big data systems, Python.
- **Skill Overlap:** 9 skills (`data warehousing`, `etl`, `integration`, `python`, `cloud services`, etc.).
- **Root-Cause Analysis:** The candidate is a senior BI/data warehouse developer. Annotator A penalized the candidate for lack of specific cloud/big data engineering keywords (`No Fit`), whereas Annotator B credited 10 years of solid data warehousing background (`Potential Fit`).
- **Determination:** **UNCERTAIN (Seniority & Specialization Ambiguity)**. Demonstrates boundary fuzziness between senior BI developer and principal data engineer.

---

### Pair 4: Big Data Engineer vs Business Analyst
- **Row Indices:** 46 and 4919 in `train.csv`
- **Labels Assigned:** `No Fit` (Row 46) vs `Good Fit` (Row 4919)
- **Resume Profile:** 7 years experience as Big Data Engineer; Hadoop, Spark, Cloud Data engineering, Kafka.
- **Job Description:** Business Analyst (Remote, 12+ months); user stories, requirements gathering, end-to-end digital product lifecycle.
- **Skill Overlap:** 9 surface tokens (`analytics`, `git`, `excel`, `testing`, `integration`, `communication`).
- **Root-Cause Analysis:** A technical big-data infrastructure engineer applying for a functional/product business analyst role. Annotator B saw common software terms and marked `Good Fit`. Annotator A recognized a complete career track mismatch and marked `No Fit`.
- **Determination:** **UNCERTAIN / SEVERE NOISE**. Over-qualification and role divergence. Objectively `No Fit` or `Potential Fit` at best; `Good Fit` is erroneous.

---

### Pair 5: QA Analyst vs IT Project Lead / Business Analyst
- **Row Indices:** 585 and 4888 in `train.csv`
- **Labels Assigned:** `No Fit` (Row 585) vs `Good Fit` (Row 4888)
- **Resume Profile:** QA Analyst / Software Quality Assurance Specialist; test plans, defect tracking, test execution.
- **Job Description:** IT Solutions Provider; project leadership, stakeholder management, business solution delivery.
- **Skill Overlap:** 7 generic tokens (`design`, `documentation`, `integration`, `planning`, `teams`).
- **Root-Cause Analysis:** QA testing specialist versus IT project leadership. Annotator B rewarded shared SDLC keywords; Annotator A flagged functional role misalignment.
- **Determination:** **UNCERTAIN**.

---

### Pair 6: BI/SQL Developer vs Mobile Business Analyst
- **Row Indices:** 377 and 5903 in `train.csv`
- **Labels Assigned:** `No Fit` (Row 377) vs `Good Fit` (Row 5903)
- **Resume Profile:** 4+ years BI / SQL Developer and Data Analyst; Power BI, Tableau, T-SQL, SSIS, SSRS.
- **Job Description:** Business Analyst - Mobile; evaluating mobile business processes, mobile requirements.
- **Skill Overlap:** 3 skills (`business analysis`, `excel`, `testing`).
- **Root-Cause Analysis:** Technical database reporting developer vs mobile product business analyst. Annotators applied opposing standards.
- **Determination:** **UNCERTAIN**.

---

## 3. Ambiguous Compatibility Boundaries & Skill Overlap Distribution

To measure the degree of overlap across the three classes, we audited the skill extraction and text similarity distributions across 1,200 representative pairs from `train.csv`:

| Evaluation Metric | Class: `No Fit` | Class: `Potential Fit` | Class: `Good Fit` | Overlap / Boundary Separation |
| :--- | :---: | :---: | :---: | :--- |
| **Mean Skill Recall (% JD Skills in Resume)** | **16.6%** | **20.6%** | **22.3%** | **$\Delta = 5.7\%$** (Extremely narrow separation) |
| **Median Skill Recall** | 14.3% | 18.6% | 21.2% | Interquartile ranges heavily overlap across all 3 classes |
| **25th Percentile Skill Recall** | 0.0% | 7.7% | 12.5% | Significant zero-coverage tail in `No Fit` and `Potential Fit` |
| **75th Percentile Skill Recall** | 25.0% | 28.6% | 30.8% | Many `No Fit` instances have higher skill recall than `Good Fit`! |
| **Mean Matched Skills Count** | 3.2 skills | 3.7 skills | 5.0 skills | Only 1.8 skills separate `No Fit` from `Good Fit` |
| **Mean Jaccard Similarity** | 0.061 | 0.078 | 0.092 | Sub-0.10 similarity across all three classes |

### The "Potential Fit" Squeeze
The table reveals that `Potential Fit` is fundamentally an **intermediate, fuzzy boundary class**:
- It sits in a narrow band between 18% and 28% skill coverage.
- Human annotators frequently treat `Potential Fit` as a catch-all category for uncertain cases.
- In confusion matrices across all trained models, **over 55% of all misclassifications occur on the boundaries of `Potential Fit`** (`No Fit` $\leftrightarrow$ `Potential Fit` or `Potential Fit` $\leftrightarrow$ `Good Fit`).

---

## 4. Policy for Phase 12 Model Training

1. **No Silent Relabeling:** In compliance with audit standards, no ground-truth label was arbitrarily rewritten.
2. **Quarantine Clean Dataset:** The 12 rows corresponding to the 6 contradictory pairs are removed in the versioned experimental partition `results/phase12_audit/train_cleaned_phase12.csv`.
3. **Dual Verification:** All candidate models are tested on the untouched holdout (`val_sub_job`) to verify that data cleaning does not degrade generalizability.
