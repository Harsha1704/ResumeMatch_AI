# ResumeMatch AI — Phase 12E-3: Research-Safe Runner-Up Mining (RUM) Design

**Document ID:** `PHASE12E3-RUM-SAFETY`  
**Classification:** Contrastive Hard-Negative Mining Protocol & Scientific Safeguards Specification  
**Author:** Principal ML Engineer, NLP Research Scientist & Independent Evaluation Specialist  
**Reference Paper:** *ConFit v2: Improving Resume-Job Matching using Hypothetical Resume Embedding and Runner-Up Hard-Negative Mining* (Yu et al., ACL Findings 2025; [arXiv:2502.12361](https://arxiv.org/abs/2502.12361))  
**Target Repository:** `D:\skillsync1`  

---

## 1. Scientific Context: Why Hard Negatives Are Dangerous

In contrastive learning for recruitment, models trained only on in-batch random negatives (e.g. comparing a Java backend candidate to a Marketing Director vacancy) achieve superficially high loss reduction while remaining incapable of distinguishing subtle qualification boundaries.

ConFit v2 introduced **Runner-Up Mining (RUM)** to harvest high-scoring candidates who look plausible but are non-matches.

However, unsupervised hard-negative mining carries severe scientific risks:
- **False Negative Inversion:** If an algorithm retrieves unlabelled candidates with high similarity to a job and automatically labels them as "No Fit", it will frequently label *actual highly qualified candidates* as negatives! This introduces poisoned gradients during training.
- **Evaluation Contamination:** If runner-up candidates are mined from the candidate pool assigned to the held-out test set, the model memorizes test-entity features, invalidating the benchmark.

---

## 2. Six Non-Negotiable RUM Safety Rules

ResumeMatch AI establishes strict MLOps guardrails for any experimental adoption of RUM:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   SIX NON-NEGOTIABLE RUM SAFETY RULES                  │
├────────────────────────────────┬───────────────────────────────────────┤
│ Rule 1: High-Similarity Stays  │ Unlabelled candidates retrieved by    │
│         Unlabelled             │ similarity remain UNLABELLED. Zero    │
│                                │ auto-conversion to "No Fit".          │
├────────────────────────────────┼───────────────────────────────────────┤
│ Rule 2: Absolute Test-Gate     │ Mining is restricted STRICTLY to the  │
│         Isolation              │ training entity partition (U_train).  │
│                                │ 0% test candidate/job exposure.       │
├────────────────────────────────┼───────────────────────────────────────┤
│ Rule 3: No Percentile Ground   │ Similarity rank (e.g. 85th-95th pct)  │
│         Truth                  │ is a proposal filter, NOT a label.    │
├────────────────────────────────┼───────────────────────────────────────┤
│ Rule 4: Human-in-the-Loop or   │ Hard negatives for supervised training│
│         Veto Gating            │ require human audit or rule veto.     │
├────────────────────────────────┼───────────────────────────────────────┤
│ Rule 5: Immutable Provenance   │ Every mined pair records mining score,│
│         Logging                │ source model, date, and reason.       │
├────────────────────────────────┼───────────────────────────────────────┤
│ Rule 6: Mandatory No-RUM       │ Every RUM model must be benchmarked   │
│         Baseline Comparison    │ against an identical no-RUM baseline. │
└────────────────────────────────┴───────────────────────────────────────┘
```

---

## 3. The Research-Safe RUM Architecture

```
                    TRAINING ENTITY PARTITION ONLY (U_train x V_train)
                                         │
                                         ▼
                             RETRIEVAL SIMILARITY PASS
                       (BM25 + Dense Bi-Encoder Cosine Search)
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
          TOP-1 POSITIVE MATCH                      RUNNER-UP CANDIDATE POOL
         (Human-Verified Good Fit)                   (Rank 2 to Rank 15 Pool)
                 │                                               │
                 │                                               ▼
                 │                                   OBJECTIVE VETO FILTERING
                 │                                   - Does candidate have an explicit
                 │                                     mandatory disqualifying gap?
                 │                                   - Seniority gap > 2 years?
                 │                                   - Missing non-negotiable stack?
                 │                                               │
                 │                               ┌───────────────┴───────────────┐
                 │                               ▼                               ▼
                 │                      [GAP CONFIRMED]                 [GAP UNCONFIRMED]
                 │                   True Runner-Up Negative        (Potential Ambiguity)
                 │                   (Admitted to InfoNCE Loss)      REJECTED from Loss
                 │                               │
                 └───────────────────────┬───────┘
                                         ▼
                            CONTRASTIVE InfoNCE TRAINING
                     - Learns subtle qualification boundary
                     - Zero false-negative label noise
```

---

## 4. Controlled Experimental Protocol: RUM vs No-RUM

To prevent ungrounded claims of "reproducing ConFit v2", any future Phase 12E-4 experiment must follow a controlled A/B evaluation:
- **Model Track 1 (Control Baseline):**
  - Bi-Encoder fine-tuned with standard InfoNCE using in-batch random negatives only.
- **Model Track 2 (Safe-RUM Experimental):**
  - Identical model architecture fine-tuned with in-batch random negatives + verified runner-up hard negatives (with veto gating).
- **Evaluation Gate:**
  - Both models are evaluated on the exact same **Manifest V2 Held-Out Test Gate**.
  - A claim of improvement is certified ONLY IF Track 2 demonstrates statistically significant gains in Macro F1 and Good Fit precision ($p < 0.05$) without degrading recall.
