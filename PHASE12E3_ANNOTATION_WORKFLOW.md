# ResumeMatch AI — Phase 12E-3: Human Annotation Workflow & Blinding Protocol

**Document ID:** `PHASE12E3-WORKFLOW-SPEC`  
**Classification:** Operational Human Annotation SOP & Quality Control Protocol  
**Author:** Principal MLOps Engineer & Data Quality Auditor  
**Effective Date:** 2026-11-13  
**Target Repository:** `D:\skillsync1`  

---

## 1. Workflow Architecture & The Blinding Principle

To eliminate confirmation bias, annotators must evaluate candidate-job pairs without knowing the algorithmic stratum that generated the proposal.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RAW PROPOSED PAIR POOL                          │
│               (High Alignment, Borderline, Cross-Domain)               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               STAGE 1: RANDOMIZATION & STRATUM BLINDING                │
│ - Pair presentation order is cryptographically shuffled.               │
│ - Column 'stratum_type' is stripped from active annotator spreadsheets │
│   and archived in secure metadata index.                               │
│ - Pair IDs are hashed: pair_id = SHA256(cv_id + jd_id)[:16]            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│       STAGE 2A: ANNOTATOR 1          │  │       STAGE 2B: ANNOTATOR 2          │
│ - Evaluates candidate profile & JD   │  │ - Evaluates candidate profile & JD   │
│ - Applies 8-Dimensional Rubric V2    │  │ - Applies 8-Dimensional Rubric V2    │
│ - Assigns Class: No / Pot / Good     │  │ - Assigns Class: No / Pot / Good     │
│ - Cites mandatory evidence & gaps    │  │ - Cites mandatory evidence & gaps    │
│ - Records confidence rating (1 to 5) │  │ - Records confidence rating (1 to 5) │
└───────────────────┬──────────────────┘  └───────────────────┬──────────────────┘
                    │                                         │
                    └───────────────────┬─────────────────────┘
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│              STAGE 3: DISAGREEMENT & CONSENSUS TRIAGE                  │
│                                                                        │
│   Case A: Perfect Agreement (Ann 1 == Ann 2) ──► Provisional Label     │
│                                                                        │
│   Case B: Minor Disagreement (Potential vs Good) ──► Route to Senior   │
│   Case C: Severe Disagreement (No Fit vs Good)   ──►   Adjudication    │
│   Case D: Low Confidence / Insufficient Evidence ──►                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                STAGE 4: SENIOR RECRUITER ADJUDICATION                  │
│ - Senior Adjudicator reviews full CV, JD, Ann 1 notes, Ann 2 notes.    │
│ - Resolves conflict using Precedence Hierarchy (Veto Rules).           │
│ - Assigns binding 'adjudicated_label' and 'adjudication_notes'.        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│             STAGE 5: RE-INTEGRATION & STRATUM RE-LINKING               │
│ - Stratum metadata re-attached to finalized pairs.                     │
│ - Inter-annotator agreement metrics computed (Cohen's Kappa).          │
│ - Adjudicated pairs formatted into Manifest V2 Parquet partitions.     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Operating Procedures

### Step 1: Pre-Processing and Blinding Preparation
1. The unlabelled proposal pool (e.g. `data/external/djinni/proposed_candidate_pairs_sample.csv`, $N=830$) is loaded.
2. The dataset is shuffled using a deterministic pseudo-random seed (`seed=42`) to destroy any grouping by company, job, or domain.
3. The `stratum_type` column (which indicates whether a pair was sampled as "High Alignment", "Borderline Runner-Up", or "Cross-Domain Negative") is **removed from the annotator sheets** and stored in an internal audit table (`data/external/djinni/pair_stratum_metadata_private.csv`).
4. Two separate blinded review templates are generated:
   - `annotator_1_sheet.csv`: Contains `[pair_id, job_position, candidate_position, candidate_cv_text, job_description_text]` + empty columns for `assigned_class`, `evidence`, `missing_skills`, `transferable_skills`, `confidence`.
   - `annotator_2_sheet.csv`: Contains identical pairs in a differently randomized order.

### Step 2: Independent Blind Annotation
- Annotators review each pair in complete isolation.
- Annotators are forbidden from discussing specific pairs during the active review cycle.
- Permitted values for `assigned_class`:
  - `Good Fit`: Candidate satisfies all essential requirements ($\ge 80\%$ mandatory skills, meets experience).
  - `Potential Fit`: Candidate has core foundation (50%–79%) or strong transferable stack; minor gap.
  - `No Fit`: Candidate has severe qualification gap, lacks mandatory prerequisites, or seniority mismatch.
  - `Uncertain`: Text lacks sufficient information to determine qualification (e.g., CV consists only of job titles without tech stack).

### Step 3: Automated Consensus & Triage Detection
Upon completion of an annotation batch, an automated consensus triage script executes:
- **Agreement Group:** Rows where `annotator_1_label == annotator_2_label`.
  - These rows bypass adjudication and receive `adjudicated_label = annotator_1_label`.
- **Disagreement Group:** Rows where `annotator_1_label != annotator_2_label`.
  - These rows are extracted and flagged with `disagreement_severity`:
    - `ADJ_BORDERLINE`: Disagreement between *Potential Fit* and *Good Fit*, or between *No Fit* and *Potential Fit*.
    - `ADJ_CRITICAL`: Disagreement between *No Fit* and *Good Fit*.
    - `ADJ_UNCERTAIN`: One or both annotators selected *Uncertain*.

### Step 4: Senior Adjudication
- The Senior Technical Recruiter / HR Lead reviews the flagged disagreement rows.
- The adjudicator reads both annotator evidence summaries and full source texts.
- The adjudicator applies the **Hierarchical Precedence Rules** from `PHASE12E3_ANNOTATION_RUBRIC_V2.md`:
  - Did the candidate violate a mandatory non-negotiable requirement? If yes, rule `No Fit`.
  - Is the missing technology an easily learnable secondary library? If yes, rule `Potential Fit`.
  - Does candidate experience truly satisfy the seniority level?
- The adjudicator enters `adjudicated_label` and documents the reason in `adjudication_notes`.

### Step 5: Metadata Re-linking and Metric Certification
- The original proposal metadata (`stratum_type`, keyword pair, experience delta) is re-joined using `pair_id`.
- The system computes:
  - Overall Cohen's Kappa ($\kappa$).
  - Per-class confusion matrix between Annotator 1 and Annotator 2.
  - Adjudication overturn rates (how often Ann 1 vs Ann 2 was upheld).
- Only adjudicated pairs with non-null labels are admitted into the gold-standard evaluation set.

---

## 3. Duplicate Prevention & Quality Control Safeguards

1. **Cryptographic Idempotence:**
   Every pair is assigned a permanent identifier based on SHA-256:
   $$\text{pair\_id} = \text{SHA256}(\text{candidate\_id} + \text{"\_"} + \text{job\_id})[:16]$$
   An automated database constraint prevents the same candidate-job pair from ever appearing twice across any batch.
2. **Speed & Fatigue Detection:**
   Annotators who log review times under 15 seconds per pair are flagged for quality audits. Thorough resume-job comparison requires at least 45–90 seconds per pair.
3. **Gold-Standard Sentinel Trap Pairs:**
   In large batches ($N > 200$), the pipeline inserts 5% "sentinel pairs" (clear-cut benchmark examples with known answers). Annotators must achieve $\ge 90\%$ accuracy on sentinel pairs to validate their submission.
