# RESUMEMATCH AI — ANNOTATION RUBRIC V3: CANDIDATE-JOB SUITABILITY BENCHMARK
**Phase:** 12I.2 Protocol Hardening & Statistical Verification  
**Workspace:** `D:\skillsync1`  
**Classification Task:** 3-Class Candidate-Job Alignment (`0: No Fit`, `1: Potential Fit`, `2: Good Fit`)  
**Auditor Roles:** Principal Biostatistician, Recruitment Annotation Quality Auditor, Independent ML Evaluation Auditor  
**Status:** Frozen Production Benchmark Standard (V3)

---

## 1. Foundational Design Principles & Scientific Boundaries

The ResumeMatch AI Annotation Rubric V3 establishes an objective, evidence-grounded framework for evaluating candidate-job alignment.

### Core Protocol Guardrails:
1. **Suitability and Capability Alignment, NOT Downstream Hiring Decisions:**
   - Labels measure **intrinsic capability alignment, technical competence overlap, and experiential relevance**.
   - Annotators must **never** interpret `Good Fit (2)` as a guarantee of employment, an interview recommendation, or an offer decision. Organizational factors (headcount constraints, compensation negotiations, team culture match, visa sponsorship) are deliberately out of scope.
2. **Dual-Sided Textual Evidence Mandate:**
   - Every annotation requires exact textual citations from **both** the candidate resume and the job description, accompanied by a structured rationale. Ratings without cited evidence are automatically rejected by the QA pipeline.
3. **Pre-Adjudication Independence:**
   - Inter-annotator agreement metrics ($\kappa, \kappa_w$) must be calculated on **raw, independent rater judgments** prior to any consensus adjudication. Adjudicated labels are preserved separately for the evaluation benchmark.

---

## 2. Definitive Class Definitions & Operational Thresholds

| Class Code | Label Name | Operational Definition | Quantitative & Evidence Thresholds |
| :--- | :--- | :--- | :--- |
| **0** | **No Fit** | Candidate exhibits a fundamental disqualification, severe competency gap, or critical domain incompatibility. | • Fails $\ge 50\%$ of genuinely mandatory core requirements.<br>• Missing non-negotiable legal, regulatory, or clearance prerequisites.<br>• Severe seniority shortfall ($> 50\%$) without exceptional compensating scope.<br>• Incompatible domain divergence (e.g. Retail Store Manager for Distributed Systems Engineer). |
| **1** | **Potential Fit** | Candidate demonstrates foundational competencies, transferable adjacent skills, or viable growth potential despite non-critical gaps. | • Satisfies $60\% - 85\%$ of core technical requirements.<br>• Possesses strong transferable adjacent technologies (context-justified).<br>• Moderate seniority shortfall ($20.1\% - 50.0\%$) with relevant hands-on skills, OR shortfall $\le 20.0\%$ lacking senior leadership scope.<br>• Meets all mandatory prerequisites but lacks non-essential preferred tools. |
| **2** | **Good Fit** | Candidate directly fulfills core mandatory requirements and demonstrates proven technical mastery and experiential depth for the role. | • Satisfies $\ge 90\%$ of core mandatory competencies.<br>• Direct, verified hands-on production experience in the primary tech stack and domain.<br>• Demonstrable track record of relevant scope and execution matching job expectations.<br>• If experience gap is $\le 20.0\%$, candidate demonstrates concrete compensating seniority evidence. |

---

## 3. Disentangling Requirements: Mandatory vs. Preferred

Annotators must strictly distinguish between hard prerequisites and secondary preferences:

### 3.1 Genuinely Mandatory Requirements (Hard Constraints)
- **Linguistic Markers:** *"Must have"*, *"Required"*, *"Minimum [N] years"*, *"Eligible for Security Clearance"*, *"Active Professional Licensure"*.
- **Functional Definition:** A requirement is **genuinely mandatory** only if:
  1. It is legally or regulatory required (e.g. Active Bar Membership, Registered Nurse License, Top Secret Clearance), OR
  2. The day-to-day role cannot function without it (e.g. an iOS Developer must write Swift/Objective-C; a Java Backend engineer must know JVM ecosystems), AND
  3. The employer cannot practically onboard or train the candidate on this skill within a standard ramp-up window ($< 60$ days).
- **Rule:** Failure on a genuinely mandatory requirement $\rightarrow$ Automatic **No Fit (0)**.

### 3.2 Preferred Qualifications (Aspirational / Secondary)
- **Linguistic Markers:** *"Preferred"*, *"Nice to have"*, *"Bonus points for"*, *"Familiarity with"*, *"Exposure to"*.
- **Functional Definition:** Supplemental skills that enhance productivity but are not strictly required for baseline job execution.
- **Rule:** Absence of preferred qualifications **must never** disqualify an otherwise qualified candidate to `No Fit (0)`.

---

## 4. Seniority Evaluation & The 20% Shortfall Boundary

### 4.1 Years of Experience as a Fallible Proxy
> [!IMPORTANT]
> **Years of experience do NOT independently establish seniority.**
> Title inflation (e.g. "Lead" after 1.5 years) and lateral stagnation (e.g. 8 years executing routine maintenance tasks) frequently decouple tenure from capability. Annotators must evaluate **scope of ownership, architectural autonomy, system complexity, and organizational impact**.

### 4.2 Mathematical Definition of Shortfall
Shortfall is defined as:
$$\text{Shortfall } (\%) = \max\left(0, \frac{\text{Required Years} - \text{Demonstrated Relevant Years}}{\text{Required Years}}\right) \times 100\%$$

### 4.3 Precise Operational Boundary Rules:
1. **Shortfall $\le 20.0\%$ (e.g. 4.0 years on a 5.0-year requirement; 2.4 years on a 3.0-year requirement):**
   - **Boundary Resolution:** Exactly $20.0\%$ is the upper threshold of a minor shortfall.
   - **Good Fit (2) Qualification:** The candidate may receive **Good Fit (2)** ONLY IF the resume exhibits explicit **compensating seniority evidence**:
     - Proven technical leadership (e.g. architecting major modules, mentoring junior engineers, owning CI/CD pipelines, driving SLAs).
     - Tangible high-impact production achievements (e.g. reducing latency by 40%, scaling database to 1M DAU).
   - **Potential Fit (1) Default:** If the candidate performed standard task-level execution without scope expansion, a $\le 20.0\%$ shortfall **defaults to Potential Fit (1)**.
2. **Shortfall Between $20.1\%$ and $50.0\%$ (e.g. 3.0 years on a 5.0-year requirement):**
   - Candidate is restricted to **Potential Fit (1)**, provided foundational skills are sound. Candidate **cannot** receive `Good Fit (2)`.
3. **Shortfall $> 50.0\%$ (e.g. 1.0 year on a 5.0-year requirement):**
   - Candidate lacks baseline experiential foundation $\rightarrow$ Automatic **No Fit (0)**.

---

## 5. Transferable Skills: Advisory Equivalencies vs. Contextual Justification

Technology stacks frequently share conceptual paradigms. However, **transferable-skill weights are advisory guidelines, NOT universal or automatic algorithmic substitutions**. Annotators must explicitly justify whether an adjacent technology is transferable **in the specific job context**:

### 5.1 Advisory Equivalence Matrix
| Domain | Primary Requirement | Common Adjacent Stacks | Baseline Advisory Weight |
| :--- | :--- | :--- | :---: |
| **Cloud Computing** | AWS (EC2, S3, IAM, EKS) | GCP (Compute, GCS, GKE) or Azure | $0.85$ |
| **Backend Frameworks** | FastAPI / Django (Python) | Spring Boot (Java), Go (Gin/Echo), Express (Node) | $0.80$ |
| **Frontend Frameworks**| React.js | Vue.js, Angular, Svelte | $0.80$ |
| **Relational Data** | PostgreSQL | MySQL, Oracle, SQL Server | $0.90$ |
| **Distributed Data** | Apache Spark / Databricks | Apache Flink, Snowflake, Presto/Trino | $0.85$ |
| **Deep Learning** | PyTorch | TensorFlow / Keras, JAX | $0.85$ |

### 5.2 Contextual Disqualification of Transferability:
- **Example A (Transferable):** General Cloud Software Engineer job asks for AWS. Candidate has 5 years of production GCP and Kubernetes.  
  *Context:* Underlying container and microservices principles transfer seamlessly. $\rightarrow$ **Permitted as Potential Fit (1) or Good Fit (2)**.
- **Example B (Non-Transferable):** Cloud Security Architect job specifically requires AWS IAM Identity Federation, AWS Organizations SCPs, and CloudTrail auditing. Candidate only knows GCP IAM.  
  *Context:* Deep proprietary governance nuances do not transfer without extensive vendor-specific retraining. $\rightarrow$ **Transferability Rejected; defaults to Potential Fit (1) or No Fit (0)**.

---

## 6. Guidelines for Unstated, Absent, and Insufficient Evidence

> [!CAUTION]
> **A missing keyword does NOT automatically confirm a candidate's incompetence.**
> Resumes are constrained summaries, not exhaustive logs of every technology ever touched. Annotators must distinguish between confirmed gaps and unverified evidence.

### 6.1 Evidence Categories & Protocol:
1. **Explicit Presence:** Resume explicitly cites production usage with tenure and project scope.
2. **Explicit Contradiction / Negation:** Resume explicitly states candidate is transitioning domains, disclaims capability, or confirms lack of credential.
3. **Unstated / Missing Evidence:** Resume does not mention the term.
   - *Protocol:* Unstated evidence **must not automatically be classified as confirmed absence**. Resumes are summaries, not exhaustive catalogs. If a mandatory skill is unstated, annotator logs `evidence_status: "UNSTATED_UNVERIFIED"` and evaluates whether adjacent experience permits rapid onboarding ($< 60$ days).
4. **Ambiguous / Insufficient Resume:** The resume text is truncated, poorly formatted, or lacks detail to determine scope.
   - *Protocol:* Annotator flags `flag_ambiguous_evidence: true`, notes confidence = 1 (Low), and records the best conservative estimate. If unresolved, senior adjudicator reviews the pair.

### 6.2 Mandatory Documentation Schema for Every Decision
For every annotated pair, the annotator must record:
1. `job_evidence_quote`: Exact verbatim text from the job description defining the requirement.
2. `mandatory_justification`: Why the requirement is genuinely mandatory (legal prerequisite, foundational architectural core, or ramp-up $< 60$ days infeasible).
3. `resume_evidence_status`: Strictly one of `CONFIRMED_PRESENT`, `CONFIRMED_CONTRADICTED`, or `UNSTATED_UNVERIFIED`.
4. `decision_rationale`: Structured explanation tying evidence to the final assigned label (`0`, `1`, or `2`).

---

## 7. Concrete Case Examples Across All Classes

### Example 1: Clear-Cut Good Fit (Class 2)
- **Job:** Senior Backend Engineer (5+ years required; Python, FastAPI, PostgreSQL, AWS).
- **Resume:** Backend Engineer with 6 years experience. Built microservices in Python (FastAPI/Django) processing 10k req/sec on AWS (ECS/RDS Postgres). Mentored 3 engineers.
- **Rating:** `Good Fit (2)`
- **Rationale:** Exceeds 5 years experience, direct match on primary language, framework, database, and cloud platform. Proven high-throughput production scope.

### Example 2: Borderline Good Fit (Class 2) — 20% Shortfall with Compensating Seniority Evidence
- **Job:** Lead SRE (5 years required; Kubernetes, Terraform, Observability, incident response).
- **Resume:** SRE with 4.0 years experience (exactly 20% shortfall). Led migration of 120 microservices to Kubernetes; architected multi-region Terraform modules; served as Primary On-Call Lead reducing MTTR by 35%.
- **Rating:** `Good Fit (2)`
- **Rationale:** Candidate has 4 years (20% gap), but demonstrates verified technical leadership, architectural ownership, and measurable operational impact that compensates for the nominal 1-year gap.

### Example 3: Borderline Potential Fit (Class 1) — 20% Shortfall Without Compensating Scope
- **Job:** Senior Data Engineer (5 years required; Spark, SQL, Airflow, Snowflake).
- **Resume:** Data Engineer with 4.0 years experience (20% shortfall). Maintained existing Spark batch jobs and updated SQL queries in Snowflake. Executed assigned tickets from senior engineers.
- **Rating:** `Potential Fit (1)`
- **Rationale:** Candidate meets core stack (Spark/Snowflake), but work exhibits mid-level task execution without independent architecture or technical leadership. Without compensating scope, the 20% shortfall remains Class 1.

### Example 4: Transferable Skill Potential Fit (Class 1) — Contextually Transferable
- **Job:** Frontend Engineer (React.js, Redux, TypeScript).
- **Resume:** Frontend Developer with 4 years building reactive enterprise single-page applications using Vue.js and TypeScript.
- **Rating:** `Potential Fit (1)`
- **Rationale:** Candidate lacks direct React experience, but demonstrates 4 years of TypeScript and component-based SPA architecture (Vue). Strong transferability with expected ramp-up $< 30$ days.

### Example 5: Non-Transferable Disqualification (Class 0) — Context-Specific Proprietary Stack
- **Job:** Salesforce Technical Architect (5+ years; Apex, Visualforce, Salesforce CPQ, SOQL).
- **Resume:** Senior Full-Stack Engineer with 8 years Java, Spring Boot, and PostgreSQL.
- **Rating:** `No Fit (0)`
- **Rationale:** Despite strong general software engineering tenure, Salesforce CPQ and Apex require proprietary platform knowledge and certification that cannot be substituted with standard Java enterprise development.

### Example 6: Ambiguous / Insufficient Evidence Case
- **Job:** Machine Learning Engineer (PyTorch, NLP, Transformers, LLM Fine-Tuning).
- **Resume:** "Software Developer interested in AI. Completed online course in Deep Learning. Experienced in Python and Git." (Single-page brief summary, no project details or dates).
- **Rating:** `No Fit (0)` (with `flag_ambiguous_evidence: true`, confidence = 1)
- **Rationale:** Resume does not provide evidence of production ML engineering, model deployment, or framework proficiency. Insufficient evidence to justify Class 1.
