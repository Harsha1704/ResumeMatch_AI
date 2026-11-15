# ResumeMatch AI — Phase 12E-2: Three-Class Candidate Compatibility Annotation Rubric

**Document ID:** `PHASE12E2-RUBRIC-SPEC`  
**Classification:** Research-Grade Ground-Truth Annotation Protocol & Gold-Standard Guidelines  
**Author:** Principal Technical Recruiter, Senior HR Interviewer, NLP Research Scientist & Independent QA Auditor  
**Effective Date:** 2026-11-13  
**Status:** APPROVED FOR EXPERIMENTAL RESEARCH ANNOTATION  

---

## 1. Objective and Ethical Mandates

This document establishes the official scientific standard for annotating candidate resumes against employer job descriptions into three mutually exclusive categories:
1. **No Fit** (Class 0)
2. **Potential Fit** (Class 1)
3. **Good Fit** (Class 2)

### 1.1 Strict Non-Discrimination & Protected Attributes Policy
Annotators must evaluate candidates **STRICTLY on documented qualifications, technical skills, relevant work history, and verifiable achievements**.
- **PROHIBITED ATTRIBUTES:** Annotators must NEVER consider, infer, or incorporate candidate:
  - Gender, gender identity, or marital status.
  - Age, graduation year, or perceived career stage.
  - Race, ethnicity, nationality, or native language.
  - Religion, political affiliation, or socio-economic background.
  - Physical appearance, photo, or disability status.
  - Geographical origin or residence (except where a job legally mandates a specific work authorization or time zone overlap).
- Any annotation mentioning or relying upon a prohibited characteristic is **immediately voided and rejected**.

---

## 2. Core Three-Class Definitions & Objective Criteria

```
┌────────────────────────────────────────────────────────────────────────┐
│                    THREE-CLASS DECISION MATRIX                         │
├───────────────┬──────────────────────────────────┬─────────────────────┤
│ Class Label   │ Mandatory Skill & Experience Fit │ Decision Rationale  │
├───────────────┼──────────────────────────────────┼─────────────────────┤
│ GOOD FIT      │ Mandatory Skills: ≥ 80% Satisfied│ Candidate possesses │
│ (Class 2)     │ Experience Years: Meets or Exceed│ direct qualifications│
│               │ Non-Negotiables: 100% Satisfied  │ to perform the job  │
│               │ Secondary Skills: ≥ 60% Satisfied│ from Day 1.         │
├───────────────┼──────────────────────────────────┼─────────────────────┤
│ POTENTIAL FIT │ Mandatory Skills: 50%–79% Met    │ Candidate has strong│
│ (Class 1)     │ Experience Years: Within 1–2 yrs │ transferable base;  │
│               │ Non-Negotiables: No hard blocker │ requires 3–6 months │
│               │ Adjacent Stack: Direct transfer  │ ramp-up / training. │
├───────────────┼──────────────────────────────────┼─────────────────────┤
│ NO FIT        │ Mandatory Skills: < 50% Satisfied│ Candidate lacks core│
│ (Class 0)     │ Experience Years: Deficit > 2 yrs│ competencies;       │
│               │ Non-Negotiables: Critical Gap    │ cannot perform core │
│               │ Domain: Mismatched specialization│ role responsibilities│
└───────────────┴──────────────────────────────────┴─────────────────────┘
```

---

### 2.1 GOOD FIT (Class 2) — "Ready to Interview & Hire"

A candidate is classified as a **Good Fit** when the objective documentary evidence demonstrates that they meet or exceed the primary requirements of the role.

#### Required Evidence Criteria (All Must Apply):
1. **Essential / Mandatory Skills ($\ge 80\%$):**
   The candidate explicitly documents hands-on professional experience with at least 80% of the non-negotiable core technologies, frameworks, or tools listed in the vacancy (e.g., JD requires *Python, FastAPI, PostgreSQL, Docker*; candidate demonstrates all four or at least three with strong depth).
2. **Experience Threshold:**
   The candidate's verified relevant professional experience meets or exceeds the minimum required threshold (e.g., JD requires 3 years; candidate has $\ge 3$ years in an identical or directly equivalent role).
3. **Core Responsibility Alignment:**
   The candidate's previous job titles and bullet points describe duties matching the primary daily responsibilities of the vacancy (e.g., backend API development, system architecture, team leadership).
4. **No Disqualifying Gaps:**
   Zero critical non-negotiable prerequisites are violated (e.g., if a role explicitly requires *"active AWS Solutions Architect certification"* or *"production Kubernetes cluster management"*, the candidate must possess it).

---

### 2.2 POTENTIAL FIT (Class 1) — "Viable with Ramp-Up / Career Transfer"

A candidate is classified as a **Potential Fit** when meaningful technical and domain alignment exists, but one or more secondary criteria are only partially satisfied or require short-term on-the-job ramp-up.

#### Typical Qualification Scenarios (Any Apply):
1. **Partial Mandatory Skills ($50\% \text{ to } 79\%$):**
   The candidate possesses the foundational programming languages and architectural knowledge, but lacks specific proprietary or secondary tools (e.g., JD requires *Python, Django, Celery, Redis, Elasticsearch*; candidate demonstrates strong *Python and PostgreSQL*, but no explicit mention of *Celery or Elasticsearch*).
2. **Directly Adjacent / Transferable Tech Stack:**
   The candidate has deep mastery of an isomorphic technology stack and demonstrates rapid adaptability (e.g., JD requires *AWS CloudFormation*; candidate has 4 years of deep *Terraform / GCP* experience; or JD requires *React*; candidate has 5 years of senior *Vue.js* experience).
3. **Slight Experience Deficit ($\le 1 \text{ to } 2 \text{ years}$):**
   The candidate has 2.5 to 3 years of high-velocity experience for a role seeking 4 years, but demonstrates strong project depth, code quality, or promotion velocity.
4. **Seniority / Scope Transition:**
   A high-performing Individual Contributor (Senior Developer) applying for their first Lead / Engineering Manager position where technical skills are 100% satisfied but management experience is nascent.

---

### 2.3 NO FIT (Class 0) — "Disqualified / Substantial Mismatch"

A candidate is classified as **No Fit** when documentary evidence shows a fundamental mismatch in specialization, technical competencies, or seniority level that would prevent successful job performance.

#### Typical Disqualification Scenarios (Any Apply):
1. **Severe Skill Deficit ($< 50\%$ Mandatory Skills):**
   The candidate satisfies less than half of the core required stack (e.g., JD requires *Go distributed systems backend*; candidate is an *HTML/CSS WordPress designer*).
2. **Severe Seniority / Experience Deficit ($> 2 \text{ years}$):**
   A recent boot camp graduate or junior applicant (0–1 year experience) applying for a Staff, Principal, or Lead role requiring 7+ years of architectural decision-making.
3. **Mismatched Technical Sub-Discipline:**
   Cross-discipline applications with no transferable bridge (e.g., Manual QA applying for Embedded C++ Firmware Engineer; Graphic Designer applying for Quantitative Trader).
4. **Missing Non-Negotiable Regulatory or Security Prerequisite:**
   Absence of a strictly mandated legal qualification (e.g., Medical license, Bar admission, Top Secret security clearance, or explicit country work authorization).

---

## 3. Mandatory Annotation Evidence Schema

Every annotated pair in `PHASE12E2_PAIR_ANNOTATION_TEMPLATE.csv` must populate structured evidence fields justifying the decision:

```csv
pair_id,candidate_id,job_id,domain_keyword,stratum_type,candidate_position,job_position,candidate_exp_years,job_exp_years_req,candidate_english,job_english_req,candidate_cv_text,job_description_text,annotator_1_label,annotator_1_evidence,annotator_2_label,annotator_2_evidence,adjudicated_label,adjudication_notes
```

### Evidence Field Guidelines:
- **`annotator_label`:** Strictly one of `Good Fit`, `Potential Fit`, or `No Fit`.
- **`annotator_evidence`:** Concise factual rationale (1–2 sentences) citing specific requirements and matching/missing resume lines:
  - *Example Good Fit Evidence:* `"Meets 4/4 core requirements (Python, FastAPI, Postgres, Docker); has 4.5 years backend exp exceeding the 3y requirement."`
  - *Example Potential Fit Evidence:* `"Has strong Python and SQL background (3y), but lacks explicit Kubernetes and Kafka experience requested in JD."`
  - *Example No Fit Evidence:* `"Candidate is a manual QA specialist with no programming experience; JD is for a Senior Go Backend Engineer."`

---

## 4. Dual-Annotator Workflow & Adjudication Protocol

To guarantee scientific objectivity and eliminate individual annotator bias:

```
[Candidate-Job Pair (Unlabelled)]
                │
        ┌───────┴───────┐
        ▼               ▼
  ANNOTATOR 1      ANNOTATOR 2  (Independent blind evaluations)
   (Reviews CV)     (Reviews CV)
        │               │
        └───────┬───────┘
                ▼
        [LABEL COMPARISON]
                │
      ┌─────────┴─────────┐
      ▼                   ▼
[AGREEMENT]         [DISAGREEMENT]
(Labels Match)      (e.g., Potential vs Good)
      │                   │
      ▼                   ▼
Final Gold Label     SENIOR ADJUDICATOR
Recorded directly    (Reviews both rationales, reads full CV & JD,
                     issues binding adjudicated_label and adjudication_notes)
```

### 4.1 Inter-Annotator Reliability Metric
- Prior to finalizing any benchmark evaluation set, the **Cohen's Kappa ($\kappa$)** inter-annotator agreement coefficient must be calculated:
  $$\kappa = \frac{p_o - p_e}{1 - p_e}$$
- **Acceptance Gate:** The annotation batch is certified for gold-standard benchmark evaluation ONLY IF $\kappa \ge 0.65$ (substantial agreement). If $\kappa < 0.65$, annotators must convene for rubric realignment and re-annotate ambiguous edge cases.

---

## 5. Human Annotation Availability & Research Protocol Rule

In strict compliance with user instructions:
> *"If human annotation is unavailable, create the templates and stop before claiming that the dataset is labelled."*

- **Current Operational Status:**
  The reproducible proposal pipeline (`scripts/propose_djinni_candidate_pairs.py`) has generated 830 stratified candidate pairs, and the annotation template `PHASE12E2_PAIR_ANNOTATION_TEMPLATE.csv` has been created with 50 sample pairs ready for human annotation.
- **Scientific Integrity Pledge:**
  The system **DOES NOT claim that the 830 pairs are labelled**. They are formally classified as **`UNLABELLED_READY_FOR_HUMAN_ANNOTATION`**. Ground-truth labels will be recorded ONLY after certified independent human reviewers complete the protocol defined herein.
