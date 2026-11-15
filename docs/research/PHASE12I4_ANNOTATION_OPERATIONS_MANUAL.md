# RESUMEMATCH AI — ANNOTATION OPERATIONS MANUAL
**Phase:** 12I.4 Operational Standard  
**Target:** Benchmark Study Coordinators, Lead Adjudicators, and QA Engineers  
**Scope:** Pilot & Main Benchmark Annotation Operations

---

## 1. Operational Overview & Roles

The ResumeMatch AI annotation architecture utilizes a **Double-Blind Independent Annotation with Senior Adjudication** workflow:

```
[200-Pair Sampling Manifest]
          │
          ├──► Queue 1: Recruiter A (Blind to Models & Peer)
          │         │
          │         ▼ Raw Submission A
          │
          ├──► Queue 2: Recruiter B (Blind to Models & Peer)
                    │
                    ▼ Raw Submission B
                    │
           [Cryptographic Append-Only Intake Log]
                    │
                    ├─► Agreement Check (R_A == R_B?): Consensus Benchmark Label
                    │
                    └─► Discordance (R_A != R_B?):
                              ▼
                    [Senior Lead Adjudicator Review]
                              ▼
                    Final Adjudicated Benchmark Ground Truth
```

### Key Role Responsibilities:
1. **Study Administrator:** Dispatches blinded queues, monitors completion velocity, runs automated QA linters.
2. **Primary Annotators (Raters A & B):** Two independent certified recruiters rating all pairs without communication.
3. **Lead Adjudicator:** Principal Recruiter / Staff Hiring Manager ($\ge 7$ years domain experience) resolving discordant pairs.
4. **Data Integrity Auditor:** Verifies SHA-256 hashes, pre-adjudication reliability calculations, and permanent pilot quarantine.

---

## 2. Queue Dispatch & Double-Blind Enforcement

1. **Model Masking:** Model predictions (Production Model, Challenger, Baselines) are stripped from all rater-facing files.
2. **Peer Blinding:** Rater A and Rater B have isolated user accounts and cannot inspect peer scores, timestamps, or comments.
3. **PII Sanitization:** All candidate contact info, personal URLs, and company identifying headers are redacted.
4. **Pair Randomization:** Pairs are presented in randomized order to each annotator to prevent sequence fatigue bias.

---

## 3. Automated Intake QA Linters

Upon submission of an annotation batch, the ingestion script automatically verifies:
1. **Completeness Linter:** All 200 pairs contain a valid `rating` $\in \{0, 1, 2\}$ and `confidence` $\in \{1, 2, 3\}$.
2. **Quote Verification Linter:**
   - `job_evidence_quote` must be a non-empty substring of the job description.
   - `resume_evidence_status` must be valid enum (`CONFIRMED_PRESENT`, `CONFIRMED_CONTRADICTED`, `UNSTATED_UNVERIFIED`).
3. **Rationale Length Linter:** `decision_rationale` must exceed 25 characters and explain the rating logic.
*Any pair failing automated linting is rejected and returned to the annotator before submission to the database.*

---

## 4. Pre-Adjudication Reliability Calculation

Before any discordant pair is revealed to the Lead Adjudicator:
1. The system computes **raw agreement**, **unweighted Cohen's $\kappa$**, **linear-weighted $\kappa$**, **quadratic-weighted $\kappa_w$**, and **Gwet's AC1**.
2. If $\kappa_w < 0.70$ or severe disagreement rate ($|R_A - R_B| = 2$) exceeds $3.0\%$, the batch is flagged:
   - Pipeline pauses.
   - Ambiguity workshop is triggered.
   - Re-annotation is mandated.
3. Reliability metrics are logged to immutable storage. **Computing reliability on adjudicated labels is permanently prohibited.**

---

## 5. Adjudication Protocol

When Rater A and Rater B assign different labels ($R_A \ne R_B$):
1. The pair is routed to the Lead Adjudicator.
2. The Lead Adjudicator inspects:
   - Candidate CV snippet.
   - Job description snippet.
   - Rater A quote, status, and rationale.
   - Rater B quote, status, and rationale.
3. The Adjudicator makes an independent determination from $\{0, 1, 2\}$ and writes an `adjudication_rationale`.
4. The adjudicated label becomes the benchmark ground-truth label $Y^*_{ij}$.

---

## 6. Permanent Quarantine Policy

1. **Segregation:** Completed pilot records are stored strictly in `data/benchmark_vault/pilot_quarantine/`.
2. **Zero Evaluation Overlap:** Pilot pairs are permanently excluded from model evaluation, hyperparameter optimization, threshold tuning, and prompt engineering.
3. **Final Benchmark Purity:** The main evaluation benchmark ($N \ge 2,850$ pairs) will be sampled from fresh, untouched candidate-job pairs evaluated under the frozen finalized rubric.
