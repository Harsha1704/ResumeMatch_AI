# PHASE 12E-3.1: DUAL-BLIND HUMAN ANNOTATION PROTOCOL & INSTRUCTIONS

**Document Version:** 1.0.0  
**Target Workflow:** 200-Pair Calibration Pilot  
**Roles:** Independent Human Annotators (Annotator A & Annotator B), Senior Adjudication Lead  
**Governing Standard:** `PHASE12E3_ANNOTATION_RUBRIC_V2.md`  
**Project:** ResumeMatch AI (`D:\skillsync1`)  

---

## 1. Core Principles of the Dual-Blind Review

1. **Absolute Independence:** Annotator A and Annotator B must never discuss specific candidate profiles, share spreadsheets, or view each other's decisions during active review.
2. **Order Randomization:** Rows in Annotator A's template and Annotator B's template are independently shuffled with distinct random seeds. Row numbers do not correspond to the same pair. Use `pair_id` for tracking.
3. **Evidence-Based Reasoning:** No label may be selected without citing specific textual evidence in the provided fields. "Intuition" or "hunch" is strictly inadmissible.
4. **Non-Discrimination Mandate:** Evaluation must be strictly blind to personal characteristics. Age, gender, nationality, location, and non-job-related affiliations must play zero role in classification.
5. **No Exposure to Heuristic Strata:** The candidate pairs were sampled from algorithmic strata (High Alignment, Borderline Runner-Up, Cross-Domain Controls). Annotators have not been provided these stratum labels and must not attempt to guess them.

---

## 2. Four-Class Decision Taxonomy

Every resume–job pair must receive one of four mutually exclusive ratings:

```
+----------------------------------------------------------------------------------------------------+
| FOUR-CLASS EVALUATION TAXONOMY                                                                    |
+-----------------------+----------------------------------------------------------------------------+
| Rating Class          | Definitive Qualification Criteria                                          |
+-----------------------+----------------------------------------------------------------------------+
| **Good Fit**          | Candidate satisfies ALL mandatory skills and minimum qualifications.       |
|                       | Experience level meets or exceeds the stated requirement.                  |
|                       | The candidate is an immediate strong candidate for a first-round interview.|
+-----------------------+----------------------------------------------------------------------------+
| **Potential Fit**     | Candidate satisfies core foundational competencies or adjacent skills, but|
|                       | exhibits minor gaps (e.g. 1 year below target experience, missing a nice-   |
|                       | to-have framework, or demonstrates strong transferable skills).            |
|                       | The recruiter would consider interviewing if the talent pool is tight.     |
+-----------------------+----------------------------------------------------------------------------+
| **No Fit**            | Candidate fails one or more essential, non-negotiable requirements.        |
|                       | Severe technology mismatch, major experience deficit (>2 years short for   |
|                       | senior roles), or critical constraint violation. Immediate rejection.      |
+-----------------------+----------------------------------------------------------------------------+
| **Insufficient        | The CV or Job Description text is corrupt, truncated, non-English, or      |
| Evidence**            | contains fewer than 15 meaningful words. Cannot be fairly evaluated.       |
+-----------------------+----------------------------------------------------------------------------+
```

---

## 3. Strict Veto Hierarchy (Precedence Rules)

When evaluating a pair, annotators must apply the following hierarchical veto checks **in sequential order**. If any veto condition is met, the rating must be **No Fit**, regardless of other positive attributes:

```
[ STEP 1: Core Technology Veto ]
Does the job description mandate a specific primary programming language or platform 
(e.g., "Senior Python Developer" or "Production Kubernetes Administrator")?
  --> If candidate has ZERO demonstrated experience in this technology:
      RATING = NO FIT (Veto Rule 1 Triggered). Stop review.

[ STEP 2: Seniority / Experience Deficit Veto ]
Does the job require Senior / Lead level (e.g., 5+ years required)?
  --> If candidate has less than 2 years total experience:
      RATING = NO FIT (Veto Rule 2 Triggered). Stop review.

[ STEP 3: Language Constraint Veto ]
Does the job require Upper-Intermediate or Fluent English communication?
  --> If candidate is explicitly Basic / Elementary English:
      RATING = NO FIT (Veto Rule 3 Triggered). Stop review.

[ STEP 4: Transferable Skill Evaluation (No Veto Triggered) ]
If no veto applies:
  --> If candidate meets all mandatory skills + experience >= requirement:
      RATING = GOOD FIT
  --> If candidate meets core tech, has transferable skills, but is 1-2 years below req:
      RATING = POTENTIAL FIT
```

---

## 4. Required Field-by-Field Documentation

For every row in your assigned template (`PHASE12E3_1_ANNOTATOR_A_TEMPLATE.csv` or `PHASE12E3_1_ANNOTATOR_B_TEMPLATE.csv`), complete the following fields:

| Field Name | Type | Instructions |
|---|---|---|
| `annotation_label` | Dropdown / Text | Exactly one of: `Good Fit`, `Potential Fit`, `No Fit`, `Insufficient Evidence` |
| `mandatory_skill_evidence` | Text | Quote or list matching core skills found in both CV and JD (e.g., `Python, FastAPI, Docker`). |
| `preferred_skill_evidence` | Text | List secondary / nice-to-have skills matched (e.g., `AWS, Redis`). |
| `relevant_experience_evidence` | Text | Note total relevant years vs required (e.g., `Candidate: 4 yrs; JD requires: 3 yrs`). |
| `essential_requirement_failures` | Text | If `No Fit`, state the exact missing mandatory qualification that caused rejection. |
| `transferable_skills` | Text | If `Potential Fit`, state transferable capabilities (e.g., `Strong Django transfers to Flask`). |
| `confidence_score` | Integer (1–5) | 1 = Very Low Confidence, 2 = Low, 3 = Moderate, 4 = High, 5 = Absolute Certainty |
| `short_justification` | Text | 1–2 sentences summarizing the hiring decision (e.g., `Meets all backend requirements and has 5 years Python experience. Clear Good Fit.`). |

---

## 5. Adjudication Workflow for Discrepancies

After Annotator A and Annotator B submit their completed files:
1. An automated script computes inter-annotator agreement and populates `PHASE12E3_1_ADJUDICATION_TEMPLATE.csv`.
2. Pairs with **Exact Match** are automatically ratified.
3. Pairs with **Disagreements** are routed to the Senior Adjudication Lead:
   - **Minor Disagreement (`Potential Fit` vs `Good Fit`):** Lead reviews candidate portfolio and transferable skills.
   - **Major Disagreement (`No Fit` vs `Good Fit`):** Lead checks whether a Veto Rule was triggered or missed.
4. The Adjudicator enters the final binding label in `adjudicated_label` along with the `adjudication_rationale`.
