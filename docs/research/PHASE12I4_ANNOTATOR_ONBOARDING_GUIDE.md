# RESUMEMATCH AI — RECRUITER ANNOTATOR ONBOARDING GUIDE
**Phase:** 12I.4 Recruiter Pilot Preparation  
**Target Audience:** Independent Human Technical Recruiters & Hiring Assessors  
**Task:** 3-Class Candidate-Job Suitability Alignment (`0: No Fit`, `1: Potential Fit`, `2: Good Fit`)  
**Status:** Certified Operational Standard

---

## 1. Welcome & Study Objective

Thank you for participating in the ResumeMatch AI Independent Evaluation Benchmark. Your professional recruitment judgment establishes the ground truth against which machine learning algorithms are objectively measured.

### The Core Mindset:
> [!IMPORTANT]
> **Evaluate Candidate-Job Suitability, NOT Downstream Hiring Logistics.**
> You are assessing the intrinsic technical and experiential alignment between the candidate's demonstrated background and the job requirements.
> - **Do NOT** factor in corporate culture, compensation negotiations, interview scheduling availability, or headcount constraints.
> - **`Good Fit (2)`** means the candidate meets or exceeds all core qualifications and would be technically viable for the role. It is **not** an employment guarantee.

---

## 2. Definitive Class Definitions

| Label Code | Label Name | High-Level Meaning | Key Practical Thresholds |
| :---: | :--- | :--- | :--- |
| **0** | **No Fit** | Fundamental gap or disqualification | • Lacks $\ge 50\%$ of mandatory technical core.<br>• Missing non-negotiable legal/regulatory credential (e.g. Bar license, Clearance).<br>• Seniority shortfall $> 50\%$ with no compensating scope.<br>• Irreconcilable domain mismatch. |
| **1** | **Potential Fit** | Foundational capabilities or transferable skills present | • Meets $60\% - 85\%$ of core technical requirements.<br>• Strong adjacent/transferable technologies (e.g. GCP instead of AWS).<br>• Moderate seniority shortfall ($20.1\% - 50.0\%$), OR $\le 20.0\%$ shortfall lacking senior scope.<br>• Missing preferred nice-to-haves only. |
| **2** | **Good Fit** | Strong, direct qualification match | • Directly fulfills $\ge 90\%$ of core mandatory competencies.<br>• Verified hands-on production experience in the primary tech stack.<br>• Meets or exceeds seniority expectations.<br>• If experience gap is $\le 20.0\%$, candidate exhibits concrete compensating leadership/architecture evidence. |

---

## 3. Mandatory 4-Field Documentation Requirement

To ensure scientific reproducibility and auditability, **every single pair requires four mandatory evidence fields**:

1. **`job_evidence_quote`:** Verbatim text copied from the job description identifying the requirement.
2. **`mandatory_justification`:** Explanation of why this requirement is genuinely mandatory (e.g., legally mandated, architectural core, or cannot be learned in $< 60$ days).
3. **`resume_evidence_status`:** Strictly select one of:
   - `CONFIRMED_PRESENT`: Resume explicitly states production experience.
   - `CONFIRMED_CONTRADICTED`: Resume explicitly states transition, lack of skill, or disqualification.
   - `UNSTATED_UNVERIFIED`: Skill is not mentioned on the resume.
4. **`decision_rationale`:** Clear justification connecting the cited evidence to your final assigned label.

> [!WARNING]
> **Rule on Unstated Evidence:**
> A missing keyword in a resume does **not** automatically mean the candidate is incompetent. Resumes are summaries. If a required skill is unstated, mark `UNSTATED_UNVERIFIED` and assess whether surrounding technical competencies permit rapid on-the-job ramp-up ($< 60$ days).

---

## 4. Seniority Evaluation & The 20% Boundary

Years of experience are a fallible proxy for capability. Seniority is defined by **autonomy, architectural scope, system complexity, and technical leadership**.

### Shortfall Formula:
$$\text{Shortfall } (\%) = \max\left(0, \frac{\text{Required Years} - \text{Demonstrated Years}}{\text{Required Years}}\right) \times 100\%$$

### The 20.0% Boundary Rule:
- **Shortfall $\le 20.0\%$ (e.g. 4.0 years on a 5.0-year requirement):**
  - **Class 2 (Good Fit):** Permitted ONLY IF the candidate demonstrates **compensating seniority evidence** (e.g. led architecture, mentored engineers, owned production CI/CD or scaling).
  - **Class 1 (Potential Fit):** Defaults to Potential Fit if the candidate performed standard task-level execution without scope expansion.
- **Shortfall Between $20.1\%$ and $50.0\%$:** Restricted to Class 1 (Potential Fit).
- **Shortfall $> 50.0\%$:** Automatic Class 0 (No Fit).

---

## 5. Transferable Skills: Advisory Guidance

Technologies in the same family share conceptual paradigms. However, equivalence weights are **advisory guidelines, NOT automatic substitutions**:
- **AWS $\leftrightarrow$ GCP / Azure:** Transferable for general cloud software engineering; **NOT** transferable if the role requires deep proprietary AWS IAM/Security auditing.
- **React $\leftrightarrow$ Vue / Angular:** Transferable for frontend component architecture ($< 30$ days ramp-up).
- **PostgreSQL $\leftrightarrow$ MySQL / Oracle:** Highly transferable relational SQL fundamentals ($0.90$).
- **PyTorch $\leftrightarrow$ TensorFlow / JAX:** Transferable deep learning tensor computing ($0.85$).

*Mandate:* You must explicitly explain in your rationale why an adjacent technology is or is not transferable for the specific job description.

---

## 6. How to Submit Your Ratings

1. You will receive an independent assigned batch file: `pilot_queue_annotator_<ID>.json`.
2. Evaluate each pair independently in a quiet environment. **Do not consult with colleagues.**
3. Complete all 4 documentation fields for each pair.
4. Submit the completed JSON file to the secure intake repository. Incomplete or unquoted entries will be returned for correction.
