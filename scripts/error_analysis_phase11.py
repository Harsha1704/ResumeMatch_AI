"""
scripts/error_analysis_phase11.py
Comprehensive Error Analysis on the Production Model (models/best_model.joblib).
Evaluates strictly on internal validation splits (Development splits):
1. Job-Disjoint Validation (from train_df via GroupShuffleSplit on job_description_text)
2. Resume-Disjoint Validation (from train_df via GroupShuffleSplit on resume_text)
3. Dual-Unseen Validation (from experiments/dataset_improvement/splits/dual_unseen_val.csv)
4. Official Test (for diagnostic baseline comparison only)

Computes:
- Confusion matrix
- Per-class precision, recall, F1, support
- Accuracy, Balanced Accuracy, Macro F1, Weighted F1
- Majority Class baseline
- Confidence distribution
- Isolates concrete misclassified examples for qualitative failure analysis
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import json
import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score,
    precision_recall_fscore_support, confusion_matrix,
    classification_report
)

from src.utils.data_loader import load_primary_dataset, VALID_LABELS
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.features.feature_pipeline import ResumeJobFeaturePipeline

OUTPUT_DIR = "results/phase11_error_analysis"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CLASSES = ["No Fit", "Potential Fit", "Good Fit"]

def evaluate_split(model, pipeline, df, split_name):
    print(f"\n--- Evaluating on {split_name} ({len(df)} samples) ---")
    X = pipeline.transform(df)
    y_true = df["label"].tolist()
    y_pred = model.predict(X)
    
    # Probabilities if available
    probs = None
    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)
        confidences = np.max(probs, axis=1)
    else:
        confidences = np.ones(len(y_pred))
        
    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    
    # Majority baseline
    maj_class = pd.Series(y_true).mode()[0]
    maj_acc = float((pd.Series(y_true) == maj_class).mean())
    
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    p_weight, r_weight, f1_weight, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES).tolist()
    
    per_class_p, per_class_r, per_class_f1, per_class_sup = precision_recall_fscore_support(
        y_true, y_pred, labels=CLASSES, zero_division=0
    )
    
    per_class = {}
    for idx, c in enumerate(CLASSES):
        per_class[c] = {
            "precision": float(round(per_class_p[idx], 4)),
            "recall": float(round(per_class_r[idx], 4)),
            "f1": float(round(per_class_f1[idx], 4)),
            "support": int(per_class_sup[idx]),
        }
        
    results = {
        "split_name": split_name,
        "n_samples": len(df),
        "majority_class": maj_class,
        "majority_baseline_accuracy": float(round(maj_acc, 4)),
        "accuracy": float(round(acc, 4)),
        "balanced_accuracy": float(round(bal_acc, 4)),
        "macro_precision": float(round(p_macro, 4)),
        "macro_recall": float(round(r_macro, 4)),
        "macro_f1": float(round(f1_macro, 4)),
        "weighted_f1": float(round(f1_weight, 4)),
        "confusion_matrix": cm,
        "label_order": CLASSES,
        "per_class": per_class,
        "confidence_stats": {
            "mean": float(round(confidences.mean(), 4)),
            "median": float(round(np.median(confidences), 4)),
            "min": float(round(confidences.min(), 4)),
            "max": float(round(confidences.max(), 4)),
            "p25": float(round(np.percentile(confidences, 25), 4)),
            "p75": float(round(np.percentile(confidences, 75), 4)),
        }
    }
    
    # Attach predictions back to dataframe for error taxonomy
    df_eval = df.copy()
    df_eval["pred"] = y_pred
    df_eval["confidence"] = confidences
    if probs is not None:
        for idx, c in enumerate(CLASSES):
            df_eval[f"prob_{c}"] = probs[:, idx]
            
    print(f"  Accuracy: {acc:.4f} (Majority Baseline: {maj_acc:.4f})")
    print(f"  Balanced Accuracy: {bal_acc:.4f}")
    print(f"  Macro F1: {f1_macro:.4f} | Weighted F1: {f1_weight:.4f}")
    print(f"  Confusion Matrix (No Fit, Pot Fit, Good Fit):\n    {cm[0]}\n    {cm[1]}\n    {cm[2]}")
    for c in CLASSES:
        print(f"    {c:15s} P={per_class[c]['precision']:.3f} R={per_class[c]['recall']:.3f} F1={per_class[c]['f1']:.3f} (N={per_class[c]['support']})")
        
    return results, df_eval


def run_error_analysis():
    print("Loading production model and feature pipeline...")
    model = joblib.load("models/best_model.joblib")
    pipeline = joblib.load("models/feature_pipeline.joblib")
    
    # 1. Job-Disjoint Validation Split (from train_df)
    train_sub_job, val_sub_job, test_df = get_unseen_jobs_split(val_size=0.15, random_state=42)
    
    # 2. Resume-Disjoint Validation Split (from train_df)
    train_sub_res, val_sub_res = get_unseen_resumes_split(test_size=0.15, random_state=42)
    
    # 3. Dual-Unseen Validation Split (Phase 7e)
    dual_val_df = pd.read_csv("experiments/dataset_improvement/splits/dual_unseen_val.csv")
    
    all_results = {}
    
    res_job, df_job = evaluate_split(model, pipeline, val_sub_job, "Job-Disjoint Validation (Dev)")
    res_res, df_res = evaluate_split(model, pipeline, val_sub_res, "Resume-Disjoint Validation (Dev)")
    res_dual, df_dual = evaluate_split(model, pipeline, dual_val_df, "Dual-Unseen Validation (Dev)")
    res_test, df_test = evaluate_split(model, pipeline, test_df, "Held-Out Test (Official)")
    
    all_results["job_disjoint_val"] = res_job
    all_results["resume_disjoint_val"] = res_res
    all_results["dual_unseen_val"] = res_dual
    all_results["held_out_test"] = res_test
    
    # Error Taxonomy on Job-Disjoint Validation (Development Split)
    print("\n--- Categorizing Failure Modes on Job-Disjoint Validation ---")
    
    # Pattern 1: Good Fit -> No Fit (Catastrophic False Negative)
    p1 = df_job[(df_job["label"] == "Good Fit") & (df_job["pred"] == "No Fit")]
    # Pattern 2: Good Fit -> Potential Fit (Under-prediction / Conservative)
    p2 = df_job[(df_job["label"] == "Good Fit") & (df_job["pred"] == "Potential Fit")]
    # Pattern 3: No Fit -> Good Fit (Severe False Positive)
    p3 = df_job[(df_job["label"] == "No Fit") & (df_job["pred"] == "Good Fit")]
    # Pattern 4: Potential Fit -> No Fit or Good Fit
    p4 = df_job[(df_job["label"] == "Potential Fit") & (df_job["pred"] != "Potential Fit")]
    
    error_summary = {
        "total_val_samples": len(df_job),
        "total_errors": int((df_job["label"] != df_job["pred"]).sum()),
        "error_rate": float(round((df_job["label"] != df_job["pred"]).mean(), 4)),
        "failure_modes": {
            "good_fit_misclassified_as_no_fit": {
                "count": len(p1),
                "pct_of_good_fit": float(round(len(p1) / max(1, (df_job["label"] == "Good Fit").sum()) * 100, 2)),
                "sample_case": {
                    "resume_excerpt": p1.iloc[0]["resume_text"][:250].replace("\n", " ") if len(p1) > 0 else "",
                    "jd_excerpt": p1.iloc[0]["job_description_text"][:250].replace("\n", " ") if len(p1) > 0 else "",
                    "confidence": float(round(p1.iloc[0]["confidence"], 4)) if len(p1) > 0 else 0.0,
                    "prob_no_fit": float(round(p1.iloc[0]["prob_No Fit"], 4)) if len(p1) > 0 else 0.0,
                    "prob_good_fit": float(round(p1.iloc[0]["prob_Good Fit"], 4)) if len(p1) > 0 else 0.0,
                }
            },
            "good_fit_misclassified_as_potential_fit": {
                "count": len(p2),
                "pct_of_good_fit": float(round(len(p2) / max(1, (df_job["label"] == "Good Fit").sum()) * 100, 2)),
                "sample_case": {
                    "resume_excerpt": p2.iloc[0]["resume_text"][:250].replace("\n", " ") if len(p2) > 0 else "",
                    "jd_excerpt": p2.iloc[0]["job_description_text"][:250].replace("\n", " ") if len(p2) > 0 else "",
                    "confidence": float(round(p2.iloc[0]["confidence"], 4)) if len(p2) > 0 else 0.0,
                    "prob_potential_fit": float(round(p2.iloc[0]["prob_Potential Fit"], 4)) if len(p2) > 0 else 0.0,
                }
            },
            "no_fit_misclassified_as_good_fit": {
                "count": len(p3),
                "pct_of_no_fit": float(round(len(p3) / max(1, (df_job["label"] == "No Fit").sum()) * 100, 2)),
                "sample_case": {
                    "resume_excerpt": p3.iloc[0]["resume_text"][:250].replace("\n", " ") if len(p3) > 0 else "",
                    "jd_excerpt": p3.iloc[0]["job_description_text"][:250].replace("\n", " ") if len(p3) > 0 else "",
                    "confidence": float(round(p3.iloc[0]["confidence"], 4)) if len(p3) > 0 else 0.0,
                    "prob_good_fit": float(round(p3.iloc[0]["prob_Good Fit"], 4)) if len(p3) > 0 else 0.0,
                }
            },
            "potential_fit_confusions": {
                "count": len(p4),
                "pct_of_potential_fit": float(round(len(p4) / max(1, (df_job["label"] == "Potential Fit").sum()) * 100, 2)),
            }
        }
    }
    
    print(f"Total Errors on Job-Disjoint Val: {error_summary['total_errors']} / {len(df_job)} ({error_summary['error_rate']*100:.1f}%)")
    print(f"Good Fit -> No Fit: {len(p1)} ({error_summary['failure_modes']['good_fit_misclassified_as_no_fit']['pct_of_good_fit']}%)")
    print(f"Good Fit -> Potential Fit: {len(p2)} ({error_summary['failure_modes']['good_fit_misclassified_as_potential_fit']['pct_of_good_fit']}%)")
    print(f"No Fit -> Good Fit: {len(p3)} ({error_summary['failure_modes']['no_fit_misclassified_as_good_fit']['pct_of_no_fit']}%)")
    
    with open(os.path.join(OUTPUT_DIR, "production_baseline_evaluation.json"), "w") as f:
        json.dump(all_results, f, indent=2)
        
    with open(os.path.join(OUTPUT_DIR, "error_taxonomy_analysis.json"), "w") as f:
        json.dump(error_summary, f, indent=2)
        
    return all_results, error_summary

if __name__ == "__main__":
    run_error_analysis()
