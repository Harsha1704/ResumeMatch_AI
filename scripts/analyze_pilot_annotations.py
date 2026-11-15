"""
scripts/analyze_pilot_annotations.py
Analyzes completed pilot human annotations from Annotator A, Annotator B, and Adjudication.
Computes:
- Raw agreement
- Cohen's Kappa
- Class-wise agreement
- Annotator confusion matrix
- Disagreement rate
- Insufficient-evidence rate
- Adjudication rate
- Final class distribution

If templates are unannotated, generates a status report stating pilot execution is pending.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

REPO_ROOT = "D:\\skillsync1"
ANN_A_PATH = os.path.join(REPO_ROOT, "PHASE12E3_1_ANNOTATOR_A_TEMPLATE.csv")
ANN_B_PATH = os.path.join(REPO_ROOT, "PHASE12E3_1_ANNOTATOR_B_TEMPLATE.csv")
ADJUD_PATH = os.path.join(REPO_ROOT, "PHASE12E3_1_ADJUDICATION_TEMPLATE.csv")
REPORT_PATH = os.path.join(REPO_ROOT, "results", "phase12e3_1", "pilot_annotation_analysis_results.json")

def analyze_pilot():
    print("=" * 80)
    print("RESUMEMATCH AI — PILOT ANNOTATION QUALITY ANALYSIS")
    print("=" * 80)

    if not os.path.exists(ANN_A_PATH) or not os.path.exists(ANN_B_PATH):
        print(f"Error: Annotation templates missing from {REPO_ROOT}.")
        return

    df_a = pd.read_csv(ANN_A_PATH)
    df_b = pd.read_csv(ANN_B_PATH)
    df_adj = pd.read_csv(ADJUD_PATH) if os.path.exists(ADJUD_PATH) else None

    # Align by pair_id
    df_merged = pd.merge(
        df_a[["pair_id", "annotation_label", "confidence_score", "short_justification"]],
        df_b[["pair_id", "annotation_label", "confidence_score", "short_justification"]],
        on="pair_id",
        suffixes=("_annotator_a", "_annotator_b")
    )

    a_labels = df_merged["annotation_label_annotator_a"].fillna("").astype(str).str.strip()
    b_labels = df_merged["annotation_label_annotator_b"].fillna("").astype(str).str.strip()

    filled_a = (a_labels != "").sum()
    filled_b = (b_labels != "").sum()
    total_pairs = len(df_merged)

    print(f"Total Pilot Pairs: {total_pairs}")
    print(f"Annotator A completed: {filled_a} / {total_pairs} ({filled_a / total_pairs * 100:.1f}%)")
    print(f"Annotator B completed: {filled_b} / {total_pairs} ({filled_b / total_pairs * 100:.1f}%)")

    # If annotations are pending
    if filled_a == 0 or filled_b == 0:
        status_report = {
            "status": "PILOT_EXECUTION_PENDING",
            "message": "Human annotation pilot templates are prepared but currently unannotated. Zero synthetic labels generated.",
            "total_pairs": total_pairs,
            "annotator_a_completed": int(filled_a),
            "annotator_b_completed": int(filled_b),
            "adjudication_completed": int((df_adj["adjudicated_label"].fillna("").astype(str).str.strip() != "").sum()) if df_adj is not None else 0,
            "metrics": {
                "raw_agreement": None,
                "cohens_kappa": None,
                "disagreement_rate": None,
                "insufficient_evidence_rate": None,
                "adjudication_rate": None,
            },
            "quality_gate": {
                "target_kappa": 0.70,
                "passed": False,
                "reason": "Human pilot review has not yet been executed."
            }
        }
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w") as f:
            json.dump(status_report, f, indent=2)
        print(f"\n[STATUS: PILOT EXECUTION PENDING] Analysis saved to: {REPORT_PATH}")
        return status_report

    # If completed rows exist, calculate inter-annotator metrics
    from sklearn.metrics import cohen_kappa_score, confusion_matrix, classification_report
    
    # Filter to pairs where both have annotated
    both_mask = (a_labels != "") & (b_labels != "")
    valid_a = a_labels[both_mask]
    valid_b = b_labels[both_mask]
    n_evaluated = len(valid_a)

    raw_agreement = float((valid_a == valid_b).mean())
    kappa = float(cohen_kappa_score(valid_a, valid_b))
    
    unique_classes = sorted(list(set(valid_a).union(set(valid_b))))
    cm = confusion_matrix(valid_a, valid_b, labels=unique_classes).tolist()
    
    insufficient_count = ((valid_a == "Insufficient Evidence") | (valid_b == "Insufficient Evidence")).sum()
    disagreement_count = (valid_a != valid_b).sum()

    status_report = {
        "status": "PILOT_EVALUATION_COMPLETE",
        "total_pairs": total_pairs,
        "pairs_evaluated_by_both": n_evaluated,
        "metrics": {
            "raw_agreement": round(raw_agreement, 4),
            "cohens_kappa": round(kappa, 4),
            "disagreement_rate": round(disagreement_count / n_evaluated, 4),
            "insufficient_evidence_rate": round(insufficient_count / n_evaluated, 4),
            "adjudication_required_rate": round(disagreement_count / n_evaluated, 4),
        },
        "classes": unique_classes,
        "confusion_matrix_annotator_a_vs_b": cm,
        "quality_gate": {
            "target_kappa": 0.70,
            "passed": bool(kappa >= 0.70),
            "interpretation": "Substantial Agreement" if kappa >= 0.70 else "Insufficient Agreement (Rubric Refinement Required)"
        }
    }

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(status_report, f, indent=2)
    print(f"\nCompleted Analysis saved to: {REPORT_PATH}")
    return status_report

if __name__ == "__main__":
    analyze_pilot()
