# ResumeMatch AI — Phase 12I.7: Recruiter Rating Intake & Submission Guide

**Document Version:** 1.0  
**Effective Date:** November 2026  
**Audience:** Independent Evaluators (`REC_A_892`, `REC_B_314`), Lead Adjudicator (`LEAD_ADJ_001`), and Study Administrators.  
**Auditor Roles:** Principal Biostatistician, Recruitment Research Lead, Data Governance Engineer, Independent ML Evaluation Auditor.

---

## 1. Executive Protocol Summary

This guide outlines the protocol, validation rules, schema definitions, and cryptographic handling required for submitting candidate-job match evaluations during the ResumeMatch AI 200-pair independent recruiter pilot.

To ensure peer-reviewed scientific validity:
- **Double-Blinded:** Evaluators receive candidate CV snippets and job requirements without model predictions, feature scores, or peer ratings.
- **Evidence-Based:** Every rating requires verbatim textual quotation from the job description and an explicit justification of candidate alignment with mandatory requirements.
- **Cryptographic & Immutable:** Submissions are ingested via an append-only ledger (`data/benchmark_vault/intake/raw_submissions.jsonl`) protected by SHA-256 payload checksums.
- **Strictly Audited:** Evaluator identities remain pseudonymous to protect PII.

---

## 2. Rating Scale & Decision Rubric

Evaluators assign one ordinal rating $r \in \{0, 1, 2\}$ and one confidence score $c \in \{1, 2, 3\}$ to each assigned pair:

| Rating | Classification | Operational Definition | Minimum Evidentiary Requirement |
| :---: | :--- | :--- | :--- |
| **`0`** | **No Fit** | Candidate fails to meet one or more mandatory hard prerequisites (e.g. core technical stack, required degree/certification, or minimum threshold experience). | Verbatim quotation of unmet job prerequisite and clear explanation of absence/contradiction in CV. |
| **`1`** | **Potential Fit** | Candidate demonstrates strong transferable fundamentals and satisfies most core skills, but possesses minor gaps or ambiguous depth in specific secondary competencies. | Identification of demonstrated competencies alongside specific ambiguous or missing secondary requirements. |
| **`2`** | **Good Fit** | Candidate clearly satisfies all mandatory and core qualifications with demonstrated depth, relevant domain tenure, and directly applicable toolsets. | Verification that every core requirement is met or exceeded with supporting resume evidence. |

### Confidence Scale
- **`1` (Low Confidence):** Resume or job description is sparse, ambiguous, or heavily reliant on non-standard terminology.
- **`2` (Medium Confidence):** Sufficient clarity to make a sound hiring judgment, though minor contextual nuances remain unstated.
- **`3` (High Confidence):** Clear, unequivocal CV track record directly aligning with unambiguous job requirements.

---

## 3. Submission JSON Schema Specification

Submissions may be delivered individually or in batches matching the following JSON schema:

```json
{
  "evaluator_id": "REC_A_892",
  "pair_id": "PILOT_P_0001",
  "rating": 1,
  "confidence": 2,
  "job_evidence_quote": "Founded in 2016 by Emilie Legoff, former CEO of a large french staffing group, TROOPS is an all-in-one SaaS platform",
  "decision_rationale": "Candidate possesses relevant data engineering experience but lacks the 5+ years of senior Angular leadership mandated by this posting.",
  "mandatory_justification": "Candidate has solid database architecture skills; however, Angular frontend framework mastery is absent from the documented history.",
  "resume_evidence_status": "UNSTATED_UNVERIFIED",
  "submitted_at": "2026-11-14T20:45:00Z"
}
```

### Field Definitions & Intake Validation Rules

1. **`evaluator_id`** *(string, required)*:
   - Must match authorized pseudonymous ID: `"REC_A_892"`, `"REC_B_314"`, or `"LEAD_ADJ_001"`.
   - Any other identifier will be rejected with `UNAUTHORIZED_EVALUATOR`.
2. **`pair_id`** *(string, required)*:
   - Must match regex pattern `^PILOT_P_\d{4}$` and exist within the frozen 200-pair manifest (`PILOT_P_0001` through `PILOT_P_0200`).
3. **`rating`** *(integer, required)*:
   - Strictly one of `0`, `1`, or `2`. Non-integer or out-of-bounds values are rejected.
4. **`confidence`** *(integer, required)*:
   - Strictly one of `1`, `2`, or `3`.
5. **`job_evidence_quote`** *(string, required)*:
   - Must be a verbatim normalized substring ($\ge 8$ characters) found within the `job_description_snippet` of the designated pair.
   - Paraphrasing is rejected by the intake linter.
6. **`decision_rationale`** *(string, required)*:
   - Must be $\ge 25$ characters explaining the hiring assessment.
7. **`mandatory_justification`** *(string, required)*:
   - Must be $\ge 10$ characters articulating whether mandatory technical skills are present, contradicted, or missing.
8. **`resume_evidence_status`** *(string, required)*:
   - Strictly one of:
     - `"CONFIRMED_PRESENT"`: Candidate CV explicitly documents the required skill/experience.
     - `"CONFIRMED_CONTRADICTED"`: Candidate CV explicitly states experience that contradicts the requirement (e.g. junior tenure for a principal role).
     - `"UNSTATED_UNVERIFIED"`: Candidate CV omits mention of the required competency.
9. **`submitted_at`** *(string, optional)*:
   - ISO 8601 UTC timestamp. Defaults to system intake time if omitted.

---

## 4. Operational Ingestion & Error Codes

The validation engine is implemented in `src/benchmark/rating_intake_validator.py`.

```python
from src.benchmark.rating_intake_validator import RatingIntakeValidator

validator = RatingIntakeValidator()
result = validator.ingest_submission(submission_dict)

if result["status"] == "ACCEPTED":
    print(f"Accepted: {result['pair_id']} (Hash: {result['intake_hash']})")
else:
    print(f"Rejected: {result['errors']}")
```

### Standard Intake Errors

| Error Code | Trigger Condition | Remediation |
| :--- | :--- | :--- |
| `UNAUTHORIZED_EVALUATOR` | `evaluator_id` not in authorized roster. | Ensure correct pseudonym token is provided. |
| `UNKNOWN_PAIR` | `pair_id` not found in frozen 200-pair pilot manifest. | Verify pair identifier against assigned queue file. |
| `DUPLICATE_SUBMISSION` | Evaluator has already submitted a rating for this pair. | Submissions are immutable; contact Lead Adjudicator if correction needed. |
| `JOB_QUOTE_UNVERIFIED` | Quote does not appear verbatim in job description. | Copy exact phrase directly from job description snippet. |
| `INSUFFICIENT_RATIONALE` | Rationale string length $< 25$ characters. | Provide detailed evaluation context. |
| `BLINDING_VIOLATION` | Payload contains model predictions or peer ratings. | Strip automated fields prior to intake. |

---

## 5. Queue Locations & Delivery

Evaluator queues are deployed in the secure benchmark vault:
- **Evaluator A Queue:** `data/benchmark_vault/queues/queue_REC_A_892.json`
- **Evaluator B Queue:** `data/benchmark_vault/queues/queue_REC_B_314.json`

Both queues contain identical 200 candidate-job pairs. Evaluator B's queue is pseudo-randomly permuted (seed 42) to prevent order and fatigue bias across the cohort.

---

## 6. Adjudication & Pilot Completion Triggers

1. **Intake Completion:** Evaluators A and B must both submit all 200 pairs (400 total ratings).
2. **Pre-Adjudication Reliability Calculation:** The system computes raw agreement, unweighted Cohen's $\kappa$, quadratic weighted $\kappa_w$, Gwet's $\text{AC}_1$, and specific agreement.
3. **Adjudication Routing:** All discordant pairs ($r_A \neq r_B$) are automatically routed to `LEAD_ADJ_001`.
4. **Final Consensus Freeze:** After adjudication, consensus labels are frozen into `data/benchmark_vault/pilot_quarantine/pilot_consensus_labels_v1.parquet`.
