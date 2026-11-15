# PHASE 12E-3.1: PILOT ANNOTATION QUALITY AUDIT & INTER-ANNOTATOR FRAMEWORK

**Document Version:** 1.0.0  
**Date:** 2026-11-13  
**Status:** Pilot Workflow Staged — Human Review Execution Pending  
**Auditor Roles:** Senior Data Quality Auditor, NLP Research Scientist, Independent ML Evaluation Auditor  
**Project:** ResumeMatch AI (`D:\skillsync1`)  
**Analysis Script:** `scripts/analyze_pilot_annotations.py`  
**Registry Output:** `results/phase12e3_1/pilot_annotation_analysis_results.json`  

---

## 1. Executive Status: Zero Synthetic Labels Policy

In strict accordance with scientific integrity guidelines:
- **Total Pilot Pairs Prepared:** 200 pairs ([PHASE12E3_1_PILOT_200_PAIRS.csv](file:///d:/skillsync1/PHASE12E3_1_PILOT_200_PAIRS.csv)).
- **Annotator A Progress:** **0 / 200 (0.0% completed)**.
- **Annotator B Progress:** **0 / 200 (0.0% completed)**.
- **Adjudication Completed:** **0 / 200 (0.0% completed)**.
- **Synthetic / Hallucinated Labels:** **0 (Zero)**.

**Pilot Status:** **EXECUTION PENDING HUMAN ANNOTATION.**  
The evaluation pipeline refuses to simulate or fabricate human judgements. The quantitative evaluation script has been physically implemented, tested on null states, and is primed for immediate execution when human recruiters populate the blinded templates.

---

## 2. Statistical Formulation of Pilot Quality Metrics

When Annotator A and Annotator B complete their independent evaluations, the quality pipeline executes the following statistical calculations:

### 2.1 Observed Raw Agreement ($P_o$)
The proportion of pairs where both annotators assign the identical rating class:
$$P_o = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(y_{i,A} = y_{i,B})$$
Where $N = 200$ pilot pairs, and $\mathbb{I}$ is the indicator function.

### 2.2 Chance-Corrected Agreement (Cohen's Kappa $\kappa$)
Raw agreement does not account for chance concordance. Cohen's Kappa corrects for expected chance agreement ($P_e$):
$$\kappa = \frac{P_o - P_e}{1 - P_e}$$
Where $P_e$ is derived from the marginal proportions of each class $k \in \{\text{Good Fit}, \text{Potential Fit}, \text{No Fit}, \text{Insufficient Evidence}\}$:
$$P_e = \sum_{k} P(A = k) \cdot P(B = k)$$

### 2.3 Interpretation and Limitations of the $\kappa \ge 0.70$ Gate
We establish a target gate of **$\kappa \ge 0.70$** (Landis & Koch "Substantial Agreement") for advancing from the 200-pair pilot to full-scale dataset annotation.

> [!WARNING]
> **Methodological Caveat on Cohen's Kappa:**  
> A high Cohen's Kappa ($\kappa \ge 0.70$) indicates that annotators are applying the rubric consistently with each other. It is **NOT mathematical proof that the rubric itself is objectively correct or aligned with real-world hiring outcomes.** Annotators can consistently agree on an imperfect rule (e.g., both agreeing to penalize a candidate because of a non-standard phrasing). Therefore, adjudication and qualitative error inspection remain mandatory even if $\kappa > 0.80$.

Additionally, Cohen's Kappa is sensitive to class imbalance (the *prevalence paradox*, where extreme marginal skew artificially depresses $\kappa$ despite high raw agreement). Our pilot mitigates this by stratifying the 200 pairs across High Alignment (86), Borderline Runner-Up (56), and Cross-Domain Controls (58).

---

## 3. Disagreement Triage & Adjudication Protocol

The analysis script monitors three critical quality operational rates:

```
+---------------------------------------------------------------------------------------+
| PILOT QUALITY OPERATIONAL GATES                                                       |
+------------------------------+--------------------+-----------------------------------+
| Metric                       | Formulation        | Operational Action Threshold      |
+------------------------------+--------------------+-----------------------------------+
| **Disagreement Rate**        | $N_{\text{disagree}} / N$ | $> 25\%$ triggers rubric ambiguity review  |
| **Insufficient Evidence Rate**| $N_{\text{insufficient}} / N$ | $> 5\%$ triggers data extraction overhaul|
| **Major Polarization Rate**  | $N(\text{No vs Good}) / N$| $> 5\%$ triggers mandatory veto retraining|
+------------------------------+--------------------+-----------------------------------+
```

### 3.1 Disagreement Categorization
When $y_{i,A} \neq y_{i,B}$, the case is classified into one of three triage buckets in [PHASE12E3_1_ADJUDICATION_TEMPLATE.csv](file:///d:/skillsync1/PHASE12E3_1_ADJUDICATION_TEMPLATE.csv):
1. **Adjacent Borderline (`Potential Fit` vs `Good Fit`):** Disagreement on whether missing preferred skills or 1-year experience gap warrants an interview invitation. Adjudicator evaluates candidate project depth.
2. **Polarized Disagreement (`No Fit` vs `Good Fit`):** Critical breakdown. Indicates one annotator identified a disqualifying veto trigger (e.g., zero Python experience) that the other annotator overlooked.
3. **Evidence Dispute (`Insufficient Evidence` vs Any Class):** Disagreement on whether truncated text contains sufficient signals to evaluate competence.

---

## 4. Reproducible Execution Instructions

Once human annotators have filled in `PHASE12E3_1_ANNOTATOR_A_TEMPLATE.csv` and `PHASE12E3_1_ANNOTATOR_B_TEMPLATE.csv`:

### Step 1: Execute Analysis Script
```powershell
python scripts/analyze_pilot_annotations.py
```

### Step 2: Review Generated Artifacts
1. **Console Output:** Instant display of raw agreement, Cohen's Kappa, and confusion matrix.
2. **Machine-Readable JSON:** `results/phase12e3_1/pilot_annotation_analysis_results.json` records complete class-wise distributions.
3. **Adjudication Queue:** Open `PHASE12E3_1_ADJUDICATION_TEMPLATE.csv` to review discordances with the Senior Recruiter.

---

## 5. Current Baseline Summary

```json
{
  "status": "PILOT_EXECUTION_PENDING",
  "total_pairs": 200,
  "annotator_a_completed": 0,
  "annotator_b_completed": 0,
  "adjudication_completed": 0,
  "quality_gate": {
    "target_kappa": 0.70,
    "passed": false,
    "reason": "Human pilot review has not yet been executed."
  }
}
```
All infrastructure, blinded templates, and mathematical validation pipelines are operational and awaiting human annotator submissions.
