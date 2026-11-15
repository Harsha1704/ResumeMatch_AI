# RESUMEMATCH AI — PHASE 12I.5: RECRUITER ONBOARDING & PARTICIPATION STATUS
**Workspace:** `D:\skillsync1`  
**Phase:** 12I.5  
**Auditor Roles:** Principal Biostatistician, Recruitment Research Lead, ML Evaluation Auditor  
**Date:** November 14, 2026  
**Operational Status:** **`PILOT READY — AWAITING RECRUITERS`**

---

## 1. Recruiter Cohort Architecture & Recruitment Criteria

The 200-pair pilot evaluation protocol mandates two independent, blinded ratings for every candidate-job pair ($200 \times 2 = 400$ total evaluations). To eliminate bias while preserving scientific rigor, annotators operate under pseudonymous identifiers:

| Identifier | Assigned Role | Required Domain Competency Criteria | Onboarding Package Status |
| :--- | :--- | :--- | :--- |
| **`REC_A_892`** | Independent Primary Evaluator A | $\ge 5$ years technical recruiting experience specializing in Software Engineering, Full-Stack, and DevOps/Cloud Infrastructure hiring. | **Package Prepared / Dispatched** |
| **`REC_B_314`** | Independent Primary Evaluator B | $\ge 6$ years technical recruitment experience specializing in Data Science, Machine Learning, QA Automation, and Technical Management. | **Package Prepared / Dispatched** |
| **`LEAD_ADJ_001`** | Senior Consensus Adjudicator | $\ge 8$ years Principal Technical Recruiter / Director of Engineering Hiring. Acts strictly as tie-breaker for discordant pairs. | **Protocol Standby** |

> [!IMPORTANT]
> **Zero Invention Policy:**
> Under strict evaluation guidelines, real human participation is required. No fake recruiter identities, simulated resumes, or synthetic ratings have been created. The study infrastructure is deployed, awaiting human annotator queue execution.

---

## 2. Onboarding Curriculum & Mandatory Evaluation Standards

Every recruiter undergoes calibration against the frozen **Annotation Rubric V3**:

### 2.1 The Three Evaluation Classes:
- **Class 0 (No Fit):** Fundamental disqualification, severe competency gap ($> 50\%$ mandatory shortfall), missing legal/licensure prerequisite, or severe domain divergence.
- **Class 1 (Potential Fit):** Foundational capabilities present ($60\% - 85\%$ core match), verified transferable skills, moderate seniority shortfall ($20.1\% - 50.0\%$), or $\le 20.0\%$ shortfall lacking senior scope.
- **Class 2 (Good Fit):** Fulfills $\ge 90\%$ of core mandatory competencies, direct hands-on experience in primary stack, meets seniority expectations, or exhibits $\le 20.0\%$ shortfall with demonstrated compensating leadership/architectural impact.

### 2.2 Mandatory vs. Preferred Requirements:
- **Mandatory Requirements:** Non-negotiable prerequisites (licensure, clearances, foundational language/architecture that cannot be trained in $< 60$ days). Missing a mandatory prerequisite results in Class 0.
- **Preferred Qualifications:** Secondary bonuses. Absence of preferred qualifications **never** drops an otherwise qualified candidate to Class 0.

### 2.3 Mandatory 4-Field Documentation Schema:
For every assigned pair, recruiters must complete:
1. `job_evidence_quote`: Verbatim excerpt from job description.
2. `mandatory_justification`: Explanation of why requirement is non-negotiable.
3. `resume_evidence_status`: Strictly one of `CONFIRMED_PRESENT`, `CONFIRMED_CONTRADICTED`, or `UNSTATED_UNVERIFIED`.
4. `decision_rationale`: Explicit justification connecting evidence to label.

> [!CAUTION]
> **Unstated Evidence Rule:**
> A missing keyword in a resume is **never** automatically treated as confirmed absence. Annotators mark `UNSTATED_UNVERIFIED` and assess whether adjacent competencies support rapid onboarding.

---

## 3. Queue Dispatch & Blinding Safeguards

1. **Model Masking:** Model predictions (Production Model, Challenger, Baselines) are 100% stripped from all recruiter files.
2. **Peer Isolation:** `REC_A_892` and `REC_B_314` work in completely isolated task queues without access to peer ratings or comments.
3. **Candidate / Company PII Redaction:** All direct identifying contact info and company URLs are sanitized to generic placeholders.
4. **Append-Only Intake Storage:** Raw submissions are written directly to append-only storage with cryptographic timestamps prior to adjudication.

---

## 4. Remaining Human Actions for Pilot Completion

The operational software and data pipeline is 100% complete. The following human actions are required to reach `PILOT COMPLETED`:
- **Action 1:** Recruiter login and review of the Onboarding Guide (`docs/research/PHASE12I4_ANNOTATOR_ONBOARDING_GUIDE.md`).
- **Action 2:** Independent annotation of all 200 pairs by `REC_A_892`.
- **Action 3:** Independent annotation of all 200 pairs by `REC_B_314`.
- **Action 4:** Automated intake QA linting of all 400 raw ratings.
- **Action 5:** Calculation of pre-adjudication inter-annotator reliability ($\kappa, \kappa_w, \text{AC1}$).
- **Action 6:** Lead Adjudicator resolution of discordant pairs to establish ground-truth labels.
