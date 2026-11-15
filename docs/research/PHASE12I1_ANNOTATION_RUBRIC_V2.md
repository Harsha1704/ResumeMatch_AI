# RESUMEMATCH AI — ANNOTATION RUBRIC V2: RECRUITER SUITABILITY BENCHMARK
**Phase:** 12I.1 Protocol Hardening  
**Target:** Independent Recruiter-Labelled Evaluation Benchmark  
**Classification Task:** 3-Class Candidate-Job Alignment (`0: No Fit`, `1: Potential Fit`, `2: Good Fit`)  
**Status:** Certified Specification for Pilot & Benchmark Annotation

---

## 1. Executive Summary & Design Principles

The ResumeMatch AI Annotation Rubric V2 establishes rigorous, reproducible, and objective standards for human recruiters to evaluate resume-job pairs. 

### Core Scientific Guardrails:
1. **Suitability Assessment, Not Hiring Decision Automation:**
   - Previous iterations conflated suitability labels with downstream organizational hiring actions (e.g. *"Fast-track to hiring manager interview"* or *"Immediate offer stage"*). 
   - Rubric V2 strictly operationalizes labels as **objective candidate-job suitability and capability alignment**, removing speculative assumptions about recruiter workflows, team headcounts, or interview scheduling.
2. **Explicit Grounding & Evidence Citation:**
   - Annotators must cite specific textual evidence from both the resume and the job description for every assigned class label. Unsubstantiated ratings are discarded during QA.
3. **Pre-Adjudication Independence:**
   - All inter-annotator agreement metrics ($\kappa$, $\kappa_w$) must be computed strictly on independent pre-adjudication ratings prior to discussion or consensus resolution.

---

## 2. Definitive Class Definitions & Operational Thresholds

| Class Code | Label Name | Operational Definition | Core Criteria & Thresholds |
| :--- | :--- | :--- | :--- |
| **0** | **No Fit** | Candidate exhibits a fundamental disqualification, severe competency gap, or critical domain incompatibility. | • Candidate lacks $\ge 50\%$ of mandatory requirements.<br>• Missing mandatory legal, licensure, or clearance requirements.<br>• Domain divergence (e.g. Accounting candidate for Cloud Infrastructure role).<br>• Seniority shortfall $> 50\%$ (e.g. 1-2 years experience for a Lead/Staff role requiring 8+ years). |
| **1** | **Potential Fit** | Candidate possesses adjacent or transferable capabilities, meets the majority of core requirements, or exhibits high growth potential despite minor gaps. | • Candidate meets $60\% - 85\%$ of mandatory competencies.<br>• Demonstrates strong transferable equivalent skills (e.g. GCP instead of AWS, PyTorch instead of TensorFlow).<br>• Minor seniority shortfall (e.g. 3.5 years for a 5-year requirement) with demonstrably senior scope.<br>• Meets all mandatory legal/degree criteria but lacks specific niche preferred toolsets. |
| **2** | **Good Fit** | Candidate directly fulfills all core requirements and demonstrates proven technical and domain mastery for the target role. | • Candidate satisfies $\ge 90\%$ of core mandatory competencies.<br>• Direct hands-on experience in the primary tech stack and target domain.<br>• Seniority matches or exceeds job expectations without severe overqualification mismatch.<br>• Demonstrable track record of relevant achievements matching job responsibilities. |

> [!IMPORTANT]
> **No Hiring Guarantees:** Assigning a candidate to `Good Fit` indicates high technical and experiential alignment with the posted requirements. It does **not** imply a guarantee of employment, corporate culture alignment, salary alignment, or automated scheduling of interviews.

---

## 3. Disentangling Requirements: Mandatory vs. Preferred

A primary driver of annotator discordance is ambiguity between hard prerequisites and aspirational "nice-to-haves". Annotators must apply the following distinction:

### 3.1 Mandatory Requirements (Hard Prerequisites)
- **Identification:** Words such as *"Must have"*, *"Required"*, *"Minimum [N] years"*, *"Eligible for Security Clearance"*, *"Active CPA/Bar license"*.
- **Evaluation Rule:**
  - If a candidate fails a **legally mandated certification or license** explicitly stated as required $\rightarrow$ Automatic **No Fit (0)**.
  - If a candidate fails a **foundational core programming language / architectural requirement** (e.g. Python backend engineer role where the candidate only knows HTML/CSS) $\rightarrow$ Automatic **No Fit (0)**.
  - If a candidate meets 4 out of 5 mandatory requirements, but the 5th has a direct adjacent equivalent (e.g. PostgreSQL instead of MySQL) $\rightarrow$ May qualify as **Potential Fit (1)**.

### 3.2 Preferred Qualifications (Aspirational / Bonus)
- **Identification:** Words such as *"Nice to have"*, *"Preferred"*, *"Bonus points for"*, *"Familiarity with"*.
- **Evaluation Rule:**
  - Absence of preferred qualifications **must never** disqualify a candidate to `No Fit (0)` if core competencies are satisfied.
  - Candidates meeting all mandatory requirements who also possess preferred qualifications represent archetypal **Good Fit (2)**.
  - Candidates meeting mandatory requirements but lacking preferred qualifications remain eligible for **Good Fit (2)** (or high **Potential Fit (1)** depending on depth).

---

## 4. Transferable Skills & Tech Stack Equivalence Matrix

Annotators must recognize common technology substitution groups. A candidate possessing deep production experience in an equivalent technology is considered to meet $80\%$ of that specific requirement, qualifying them for **Potential Fit (1)** or **Good Fit (2)** (if rapid onboarding is realistic):

| Target Domain | Primary Job Tech Stack | Recognized Transferable Equivalents | Equivalence Weighting |
| :--- | :--- | :--- | :--- |
| **Cloud Infrastructure** | AWS (EC2, S3, IAM, EKS) | GCP (Compute Engine, GCS, GKE) or Azure (VMs, Blob, AKS) | $0.85$ (High transferability) |
| **Backend Frameworks** | Django / FastAPI (Python) | Flask / Tornado (Python) or Spring Boot (Java) | $0.80$ (Direct concepts transfer) |
| **Frontend UI** | React.js | Vue.js, Angular, or Svelte | $0.80$ (Component architecture transfer) |
| **Relational Databases** | PostgreSQL | MySQL, Oracle DB, MS SQL Server | $0.90$ (SQL standards overlap) |
| **Container / Orchestration** | Kubernetes | Docker Swarm, Nomad, ECS/Fargate | $0.80$ (Container paradigm transfer) |
| **Data Pipelines** | Apache Spark (PySpark) | Apache Flink, Databricks, Dask | $0.85$ (Distributed data transfer) |
| **Deep Learning** | PyTorch | TensorFlow / Keras, JAX | $0.85$ (Tensor computing transfer) |

*Rule:* If the job requires AWS and the candidate has 6 years of GCP experience, this must be annotated as an equivalent competency and credited towards **Potential Fit (1)** or **Good Fit (2)**, never penalized as a complete skill void.

---

## 5. Seniority & Experience Shortfall Rubric

Experience requirements must be evaluated against the following structured bands:

| Level | Nominal Experience | Scope & Autonomy Expectation |
| :--- | :--- | :--- |
| **Junior / Entry-Level** | $0 - 2$ years | Needs guidance, task-level execution, basic fundamentals. |
| **Mid-Level** | $3 - 5$ years | Independent execution, feature ownership, debugging capability. |
| **Senior** | $5 - 8$ years | System design, cross-functional ownership, mentorship, reliability. |
| **Lead / Staff / Principal**| $8+$ years | Architecture vision, multi-team impact, organizational strategy. |

### Experience Gap Decision Tree:
1. **Gap $\le 1$ Year (or $\le 20\%$ of requirement):**
   - Candidate has 4 years, job asks for 5 years: If the candidate demonstrably performed senior responsibilities $\rightarrow$ **Good Fit (2)**. If standard mid-level execution $\rightarrow$ **Potential Fit (1)**.
2. **Gap Between $20\%$ and $50\%$:**
   - Candidate has 3 years, job asks for 5 years: Candidate may achieve **Potential Fit (1)** if technical competencies are pristine, but cannot achieve **Good Fit (2)**.
3. **Gap $> 50\%$:**
   - Candidate has 1 year, job asks for 5+ years: Automatic **No Fit (0)**.
4. **Overqualification Policy:**
   - A candidate with 12 years applying for a 3-year mid-level role is **not** penalized to `No Fit` unless their background is purely administrative/executive with lost hands-on technical skills. If technical skills are present $\rightarrow$ **Potential Fit (1)** or **Good Fit (2)**.

---

## 6. Mandatory Certifications, Licensure, and Education

1. **Strict Legal / Regulatory Licenses:**
   - Example: Medical Doctor (MD/DO license), Registered Nurse (RN), Professional Engineer (PE), Active Bar Member (for Legal Counsel), Active Top Secret / SCI Security Clearance.
   - **Protocol:** If the job states that active licensure is required on day 1, and the candidate resume has no evidence or claims pending status without current holding $\rightarrow$ **No Fit (0)**.
2. **Vendor Certifications (AWS Solutions Architect, PMP, Scrum Master, CCNA):**
   - **Protocol:** Treat as preferred credentials unless explicitly stated as an uncompromising client mandate. If candidate lacks the cert but has 5 years of equivalent engineering practice $\rightarrow$ **Potential Fit (1)** or **Good Fit (2)**.
3. **Academic Degrees:**
   - If job states *"BS in CS or equivalent practical experience"*: 4+ years of relevant software engineering satisfies the equivalent clause.
   - If job requires a terminal degree (*"PhD in Computer Science or Statistics required"* for Research Scientist role) and candidate has only BS $\rightarrow$ **Potential Fit (1)** only if peer-reviewed top-tier publications exist; otherwise **No Fit (0)**.

---

## 7. Evidence Documentation Protocol for Annotators

Every single annotation row in the benchmark dataset must contain:
1. `candidate_id` and `job_id`.
2. `annotator_id` (anonymized unique identifier).
3. `assigned_label` $\in \{0, 1, 2\}$.
4. `evidence_quote_resume` (exact snippet, max 250 chars).
5. `evidence_quote_job` (exact snippet, max 250 chars).
6. `rationale` (structured justification citing skills, seniority, or gaps).
7. `transferable_skill_flag` (boolean: true if label relies on tech stack equivalence).
8. `annotator_confidence` (Likert scale: 1 = Low, 2 = Medium, 3 = High).

### Example Annotation Row:
```json
{
  "pair_id": "P_000142",
  "candidate_id": "C_DEV_089",
  "job_id": "J_SRE_014",
  "assigned_label": 1,
  "confidence": 3,
  "evidence_quote_resume": "Senior Cloud Engineer with 4 years designing Kubernetes clusters on Google Cloud Platform (GKE).",
  "evidence_quote_job": "Seeking AWS DevOps Engineer with 5+ years experience managing EKS and Terraform infrastructure.",
  "rationale": "Candidate has 4 years (vs 5 required) and deep GKE experience which transfers directly to EKS. Strong Terraform knowledge demonstrated. Graded Potential Fit due to cloud vendor difference and minor seniority gap.",
  "transferable_skill_flag": true
}
```

---

## 8. Summary of Protocol Hardening Changes (V1 $\rightarrow$ V2)

1. **Purged Hiring Pipeline Jargon:** Eliminated terms like "Hire", "Reject", "Advance to Next Round", and "Interview Guarantee".
2. **Codified Equivalence Matrix:** Introduced explicit equivalence weights across Cloud, Frameworks, DBs, and ML toolchains.
3. **Formal Seniority Decision Tree:** Replaced subjective "experience feel" with quantitative percentage gap thresholds ($\le 20\%$, $20-50\%$, $>50\%$).
4. **Mandatory Evidence Logging:** Added non-negotiable requirements for dual-sided textual evidence citation.
