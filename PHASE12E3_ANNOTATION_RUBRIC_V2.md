# ResumeMatch AI — Phase 12E-3: Enhanced 8-Dimensional Annotation Rubric (V2)

**Document ID:** `PHASE12E3-RUBRIC-V2`  
**Classification:** Research-Grade Ground-Truth Annotation Protocol & Gold-Standard Guidelines  
**Author:** Principal Technical Recruiter, Senior HR Interviewer, NLP Research Scientist & Independent QA Auditor  
**Effective Date:** 2026-11-13  
**Status:** APPROVED FOR EXPERIMENTAL RESEARCH ANNOTATION  

---

## 1. Ethical Foundations & Prohibited Attributes

Annotators must evaluate candidates **EXCLUSIVELY on documented competencies, professional experience, verifiable technical achievements, and explicit job requirements**.

### Strict Non-Discrimination Policy:
Annotators are strictly forbidden from considering, inferring, or recording:
- Candidate gender, gender expression, or perceived marital/parental status.
- Age, graduation year, or perceived biological generation.
- Race, ethnicity, national origin, or cultural identity.
- Religion, philosophical beliefs, or political associations.
- Physical characteristics, photograph, or disability status.
- Geographical origin or postal address (unless an explicit legal prerequisite mandates citizenship, security clearance, or specific tax residency).

*Enforcement:* Any annotation that references or relies upon a prohibited personal characteristic is **immediately invalidated, struck from the corpus, and subject to re-annotation by an independent reviewer**.

---

## 2. The Eight Evaluation Dimensions

Rather than relying on vague holistic impressions, annotators must evaluate candidate-job compatibility across eight distinct, orthogonal dimensions:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   THE EIGHT EVALUATION DIMENSIONS                      │
├────────────────────────────────┬───────────────────────────────────────┤
│ 1. Mandatory Technical Skills  │ Core non-negotiable tools/languages   │
│ 2. Preferred Secondary Skills  │ "Nice-to-have" auxiliary tools        │
│ 3. Relevant Work Experience    │ Direct tenure in identical/like roles │
│ 4. Minimum Qualifications      │ Baseline professional thresholds      │
│ 5. Education / Certifications  │ Formally mandated degrees or certs    │
│ 6. Transferable Skills         │ Isomorphic stacks (e.g. AWS -> GCP)   │
│ 7. Seniority & Scope Alignment │ IC vs Lead vs Architect scope         │
│ 8. Essential Job Constraints   │ Security clearance, time zone, travel │
└────────────────────────────────┴───────────────────────────────────────┘
```

1. **Mandatory Technical Skills (Weight: Critical):**
   Technologies explicitly designated as core, non-negotiable requirements (e.g., *"Must have 3+ years production Python and PostgreSQL"*).
2. **Preferred Secondary Skills (Weight: Moderate):**
   Auxiliary technologies listed as advantageous or preferred (e.g., *"Experience with Redis or Elasticsearch is a plus"*).
3. **Relevant Work Experience (Weight: High):**
   Documented tenure performing duties directly equivalent to the primary responsibilities described in the vacancy.
4. **Minimum Qualifications (Weight: High):**
   Baseline career milestones (e.g., prior experience delivering customer-facing production microservices).
5. **Education & Certifications (Weight: Conditional):**
   Relevant degrees or professional certifications ONLY when genuinely required by the vacancy or legally mandated (e.g., AWS Certified Solutions Architect, Professional Engineer license).
6. **Transferable Skills & Domain Equivalence (Weight: Moderate):**
   Proven mastery in an adjacent, directly substitutable framework or language (e.g., 5 years of senior Vue.js/TypeScript applying to React/TypeScript; or 4 years Terraform applying to CloudFormation).
7. **Seniority & Responsibility Alignment (Weight: High):**
   Match between the candidate's demonstrated scope of ownership and the target role (Junior IC vs Mid-Level vs Senior vs Staff Architect vs Engineering Manager).
8. **Essential Job-Specific Constraints (Weight: Veto):**
   Hard constraints such as explicit time-zone availability, language proficiency requirements (e.g., "Fluent English required for international stakeholder calls"), or active security clearances.

---

## 3. Explicit Conflict Resolution Rules

In recruitment matching, different dimensions frequently conflict (e.g., high skill overlap but low experience, or high experience but missing a mandatory tool).

Annotators must adhere strictly to the following **Precedence Hierarchy**:

```
                       HIERARCHY OF DIMENSIONAL PRECEDENCE
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Level 1 (VETO POWER): Essential Constraints & Mandatory Minimums       │
  │ - If an essential constraint (Dim 8) or mandatory minimum (Dim 4) is   │
  │   violated, the candidate CANNOT be Good Fit under any circumstance.   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Level 2 (PRIMARY QUALIFICATION): Mandatory Skills & Seniority Scope    │
  │ - Candidate must satisfy ≥ 80% mandatory skills (Dim 1) AND align with │
  │   seniority scope (Dim 7) to qualify for Good Fit.                     │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Level 3 (COMPENSATORY MECHANISM): Transferable Skills & Experience     │
  │ - Strong transferable skills (Dim 6) can elevate a No Fit to Potential │
  │   Fit, but CANNOT replace a missing core mandatory skill for Good Fit.  │
  └────────────────────────────────────────────────────────────────────────┘
```

### Specific Binding Rules:
- **Rule 1 (The Mandatory Veto Rule):**
  *A candidate MUST NOT be labeled Good Fit merely because a percentage of skills matches if an essential mandatory requirement is missing.*
  - *Example:* A candidate has 10 out of 12 skills listed in the job description, but the vacancy explicitly mandates *"5+ years production Go experience"* and the candidate has never written a line of Go. -> **Label: NO FIT** (or Potential Fit only if the role explicitly welcomes language transfer).
- **Rule 2 (The Seniority Mismatch Rule):**
  *A junior candidate applying for a senior/lead role, or an executive applying for an entry-level role, cannot be Good Fit regardless of keyword overlap.*
  - *Example:* A candidate with 1 year of total experience applies for a Staff Architect vacancy requiring 8+ years. The candidate lists Docker, Python, and AWS on their resume. -> **Label: NO FIT.** (The seniority gap exceeds 2 years; candidate cannot perform role responsibilities).
- **Rule 3 (The Transferable Equivalence Rule):**
  *Directly isomorphic technology stacks elevate candidate classification from No Fit to Potential Fit, but require explicit documentation in the evidence field.*
  - *Example:* Role requires GCP cloud infrastructure. Candidate has 6 years deep AWS and Terraform experience. Candidate has 0% GCP keywords. -> **Label: POTENTIAL FIT** (Reason: Transferable cloud architecture skills).
- **Rule 4 (The Education Exemption Rule):**
  *Do not penalize candidates for lacking a specific degree (e.g., Bachelor's in CS) if their documented professional work experience clearly demonstrates equivalent technical competency, unless the degree is a strict legal/regulatory prerequisite.*

---

## 4. Formal Three-Class Decision Matrix

| Dimension | NO FIT (Class 0) | POTENTIAL FIT (Class 1) | GOOD FIT (Class 2) |
| :--- | :--- | :--- | :--- |
| **Mandatory Skills** | $< 50\%$ satisfied. Critical tool missing. | $50\% \text{ to } 79\%$ satisfied. Core base present; secondary tools missing. | $\ge 80\%$ satisfied. Demonstrates direct hands-on depth in all core requirements. |
| **Preferred Skills** | Ignored if mandatory skills fail. | Partial match ($25\% \text{ to } 50\%$). | Strong match ($\ge 50\%$). |
| **Work Experience** | Deficit $> 2$ years below minimum. | Within $1 \text{ to } 2$ years of requirement, or equivalent velocity. | Meets or exceeds required years in equivalent role. |
| **Seniority Scope** | Mismatched scope (e.g., Junior -> Staff). | Transitioning scope (e.g., Senior -> Lead). | Directly aligned seniority scope. |
| **Transferable Skills**| None / Irrelevant. | Strong isomorphic stack (e.g. React -> Vue). | Direct matching stack. |
| **Constraints / Veto**| Hard constraint violated. | Minor constraint requiring short ramp-up. | All constraints 100% satisfied. |

---

## 5. Required Annotation Schema & Evidence Recording

Every record in the annotation pipeline must contain all 10 verified data fields:

```csv
pair_id,job_id,candidate_id,assigned_class,evidence_summary,missing_mandatory_skills,transferable_skills,annotator_id,confidence_score,disagreement_reason
```

### Field Definitions:
1. **`pair_id`:** SHA-256 hash unique identifier (`hashlib.sha256(candidate_id + job_id)[:16]`).
2. **`job_id`:** Identifier of the job posting.
3. **`candidate_id`:** Identifier of the candidate profile.
4. **`assigned_class`:** Strictly one of: `No Fit`, `Potential Fit`, `Good Fit`, or `Uncertain`.
5. **`evidence_summary`:** 1–3 factual sentences citing specific resume bullet points and job requirements.
6. **`missing_mandatory_skills`:** Semicolon-delimited list of essential skills present in JD but absent in CV (e.g., `"Kubernetes; Kafka; Go"`).
7. **`transferable_skills`:** Semicolon-delimited list of substitutable competencies (e.g., `"Terraform for CloudFormation; RabbitMQ for Kafka"`).
8. **`annotator_id`:** Identifier of the individual human reviewer (e.g., `ANN_01`, `ANN_02`).
9. **`confidence_score`:** Integer rating from 1 to 5:
   - `5`: Absolute certainty; clear-cut documentary evidence.
   - `4`: High confidence; minor ambiguity in secondary skill.
   - `3`: Moderate confidence; borderline classification requiring adjudication.
   - `2`: Low confidence; conflicting evidence across dimensions.
   - `1`: Insufficient evidence to determine qualification.
10. **`disagreement_reason`:** Populated during adjudication if Annotator 1 and Annotator 2 assigned different classes (e.g., `"Annotator 1 weighted Vue as transferable; Annotator 2 enforced strict React mandatory rule"`).

---

## 6. Inter-Annotator Agreement & Statistical Validity

### 6.1 Dual Annotation and Blind Adjudication
- Every pair in the gold-standard benchmark must be evaluated independently by **Annotator 1** and **Annotator 2** without seeing each other's decisions.
- When Annotator 1 and Annotator 2 agree, the agreed label becomes the provisional label.
- When they disagree (e.g., `Potential Fit` vs `Good Fit`), the pair is routed to a **Senior Adjudicator** who reviews both evidence summaries and assigns the final binding label with documented `adjudication_notes`.

### 6.2 Measuring Agreement: Cohen's Kappa ($\kappa$)
- Inter-annotator agreement is computed using Cohen's Kappa with quadratic weighting for ordinal classes:
  $$\kappa = \frac{p_o - p_e}{1 - p_e}$$
- **Disagreement Pattern Matrix:** Annotators must analyze where disagreements cluster:
  - Disagreements between *Potential Fit* and *Good Fit* represent natural boundary subjectivity.
  - Disagreements between *No Fit* and *Good Fit* represent rubric failure or annotator oversight, requiring rubric review.
- **Scientific Caveat:** A high Kappa ($\kappa \ge 0.70$) proves **annotator consistency**, but does NOT automatically prove label validity if both annotators share a systematic blind spot. Gold-standard quality requires rubric adherence, verifiable evidence, and post-hoc error audits.
