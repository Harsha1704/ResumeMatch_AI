"""
Supervised Model Training, Leakage-Safe Cross-Validation, and Comprehensive Evaluation.
Trains:
1. Logistic Regression (Multiclass with balanced class weights)
2. Calibrated Linear Support Vector Machine (LinearSVC + 3-fold internal calibration)
3. Random Forest Classifier (Optimized tree depth and balanced class weights)
Evaluates across:
- Evaluation A: Generalization to Unseen Job Descriptions (Validation & Official Held-Out Test)
- Evaluation B: Generalization to Unseen Candidate Resumes (Group-Disjoint Split)
"""

from pathlib import Path
from typing import Dict, List, Tuple
import json
import shutil
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier

from src.utils.data_loader import load_primary_dataset, VALID_LABELS
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.features.feature_pipeline import ResumeJobFeaturePipeline
from src.models.evaluate import (
    CLASSES,
    compute_metrics,
    plot_model_comparison,
    plot_confusion_matrices,
    plot_per_class_performance,
    plot_roc_curves,
    plot_precision_recall_curves,
    plot_train_vs_val
)


MODELS_DIR = Path("models")
METRICS_DIR = Path("results/metrics")
PLOTS_DIR = Path("results/plots")
STATIC_IMG_DIR = Path("static/images")

for d in [MODELS_DIR, METRICS_DIR, PLOTS_DIR, STATIC_IMG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def get_candidate_models() -> Dict:
    """Instantiates the 3 required supervised models with reproducible parameters."""
    return {
        "Logistic Regression": LogisticRegression(
            C=1.0,
            max_iter=1500,
            tol=1e-3,
            class_weight="balanced",
            random_state=42,
            solver="lbfgs"
        ),
        "Linear SVM (Calibrated)": CalibratedClassifierCV(
            estimator=LinearSVC(
                C=0.5,
                class_weight="balanced",
                random_state=42,
                max_iter=2000,
                dual="auto"
            ),
            cv=3
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100,
            max_depth=16,
            min_samples_split=4,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )
    }


def train_and_evaluate():
    print("=================================================================")
    print("PHASE 3: SUPERVISED MODEL TRAINING & DUAL LEAKAGE-SAFE EVALUATION")
    print("=================================================================")

    start_total_time = time.time()
    train_df, test_df = load_primary_dataset()
    print(f"Verified Dataset Loaded: Train={len(train_df):,} pairs, Test={len(test_df):,} pairs\n")

    # -------------------------------------------------------------
    # 1. EVALUATION A: UNSEEN JOB DESCRIPTIONS
    # -------------------------------------------------------------
    print("--- 1. EVALUATION A: Unseen Job Descriptions (Model Selection) ---")
    train_sub_A, val_sub_A, held_out_test = get_unseen_jobs_split(val_size=0.15, random_state=42)
    print(f"Train Partition A: {len(train_sub_A)} pairs | Val Partition A: {len(val_sub_A)} pairs (0 overlapping jobs)")
    print(f"Held-out Test: {len(held_out_test)} pairs (0 overlapping jobs with train)\n")

    print("Fitting Feature Pipeline A strictly on Train Partition A...")
    t0 = time.time()
    pipe_A = ResumeJobFeaturePipeline(max_tfidf_features=2500)
    pipe_A.fit(train_sub_A)
    print(f"Pipeline A fitted in {time.time() - t0:.2f}s! Transforming splits...")

    X_train_A = pipe_A.transform(train_sub_A)
    y_train_A = np.array(train_sub_A["label"].tolist(), dtype=object)

    X_val_A = pipe_A.transform(val_sub_A)
    y_val_A = np.array(val_sub_A["label"].tolist(), dtype=object)

    X_test_A = pipe_A.transform(held_out_test)
    y_test_A = np.array(held_out_test["label"].tolist(), dtype=object)

    models_A = get_candidate_models()
    trained_models_A = {}
    val_metrics_A = {}
    train_metrics_A = {}
    test_metrics_A = {}

    comparison_rows = []

    for name, model in models_A.items():
        print(f"\nTraining {name}...")
        t_m0 = time.time()
        model.fit(X_train_A, y_train_A)
        t_m1 = time.time()
        print(f"  {name} trained in {t_m1 - t_m0:.2f}s.")
        trained_models_A[name] = model

        # Evaluate on Train
        y_train_pred = model.predict(X_train_A)
        train_metrics = compute_metrics(y_train_A, y_train_pred)
        train_metrics_A[name] = train_metrics

        # Evaluate on Validation (Unseen Jobs)
        y_val_pred = model.predict(X_val_A)
        y_val_prob = model.predict_proba(X_val_A) if hasattr(model, "predict_proba") else None
        val_metrics = compute_metrics(y_val_A, y_val_pred, y_prob=y_val_prob)
        val_metrics_A[name] = val_metrics

        # Evaluate on Held-Out Test (Official Unseen Jobs)
        y_test_pred = model.predict(X_test_A)
        y_test_prob = model.predict_proba(X_test_A) if hasattr(model, "predict_proba") else None
        test_metrics = compute_metrics(y_test_A, y_test_pred, y_prob=y_test_prob)
        test_metrics_A[name] = test_metrics

        print(f"  Validation Macro F1: {val_metrics['macro_f1']:.4f} | Accuracy: {val_metrics['accuracy']:.4f}")
        print(f"  Held-Out Test Macro F1: {test_metrics['macro_f1']:.4f} | Accuracy: {test_metrics['accuracy']:.4f}")

        comparison_rows.append({
            "Model": name,
            "Accuracy": val_metrics["accuracy"],
            "Macro Precision": val_metrics["macro_precision"],
            "Macro Recall": val_metrics["macro_recall"],
            "Macro F1": val_metrics["macro_f1"],
            "Weighted F1": val_metrics["weighted_f1"],
            "Test Accuracy": test_metrics["accuracy"],
            "Test Macro F1": test_metrics["macro_f1"]
        })

    comparison_df = pd.DataFrame(comparison_rows)
    print("\nModel Validation Comparison (Unseen Jobs):")
    print(comparison_df.to_string(index=False))

    # Select Best Model based strictly on Validation Macro F1
    best_model_name = max(val_metrics_A, key=lambda k: val_metrics_A[k]["macro_f1"])
    best_val_f1 = val_metrics_A[best_model_name]["macro_f1"]
    print(f"\n>>> Selected Best Model: {best_model_name} (Validation Macro F1: {best_val_f1:.4f}) <<<\n")

    # -------------------------------------------------------------
    # 2. EVALUATION B: UNSEEN RESUMES (Group-Disjoint)
    # -------------------------------------------------------------
    print("--- 2. EVALUATION B: Unseen Resumes (Group-Disjoint Validation) ---")
    r_train_B, r_val_B = get_unseen_resumes_split(test_size=0.20, random_state=42)
    print(f"Train Partition B: {len(r_train_B)} pairs | Val Partition B: {len(r_val_B)} pairs (0 overlapping resumes)")

    print("Fitting Feature Pipeline B strictly on Train Partition B...")
    pipe_B = ResumeJobFeaturePipeline(max_tfidf_features=2500)
    pipe_B.fit(r_train_B)

    X_train_B = pipe_B.transform(r_train_B)
    y_train_B = np.array(r_train_B["label"].tolist(), dtype=object)

    X_val_B = pipe_B.transform(r_val_B)
    y_val_B = np.array(r_val_B["label"].tolist(), dtype=object)

    models_B = get_candidate_models()
    val_metrics_B = {}

    for name, model in models_B.items():
        model.fit(X_train_B, y_train_B)
        y_val_pred_B = model.predict(X_val_B)
        y_val_prob_B = model.predict_proba(X_val_B) if hasattr(model, "predict_proba") else None
        val_metrics_B[name] = compute_metrics(y_val_B, y_val_pred_B, y_prob=y_val_prob_B)
        print(f"  {name} Unseen Resumes Validation Macro F1: {val_metrics_B[name]['macro_f1']:.4f} | Accuracy: {val_metrics_B[name]['accuracy']:.4f}")

    # -------------------------------------------------------------
    # 3. PRODUCTION RETRAINING & ARTIFACT PERSISTENCE
    # -------------------------------------------------------------
    print("\n--- 3. Production Pipeline Fitting & Model Persistence ---")
    print("Fitting final feature pipeline on full training dataset (6,240 pairs)...")
    prod_pipeline = ResumeJobFeaturePipeline(max_tfidf_features=2500)
    prod_pipeline.fit(train_df)
    X_train_full = prod_pipeline.transform(train_df)
    y_train_full = np.array(train_df["label"].tolist(), dtype=object)

    # Fit all comparison models on production training features and save
    prod_models = get_candidate_models()
    for name, model in prod_models.items():
        print(f"Fitting production {name}...")
        model.fit(X_train_full, y_train_full)
        fname = name.lower().replace(" ", "_").replace("(", "").replace(")", "") + ".joblib"
        joblib.dump(model, MODELS_DIR / fname)

    # Save best model
    best_prod_model = prod_models[best_model_name]
    joblib.dump(best_prod_model, MODELS_DIR / "best_model.joblib")
    prod_pipeline.save(MODELS_DIR / "feature_pipeline.joblib")

    # Save label mapping
    label_mapping = {
        "classes": CLASSES,
        "label_to_id": {cls: i for i, cls in enumerate(CLASSES)},
        "id_to_label": {str(i): cls for i, cls in enumerate(CLASSES)}
    }
    with open(MODELS_DIR / "label_mapping.json", "w", encoding="utf-8") as f:
        json.dump(label_mapping, f, indent=2)

    print("Saved all model artifacts to models/")

    # -------------------------------------------------------------
    # 4. GENERATE MANDATORY EVALUATION GRAPHS
    # -------------------------------------------------------------
    print("\n--- 4. Generating Genuine Evaluation Plots ---")
    # 1. Model comparison bar chart
    p_comp = plot_model_comparison(comparison_df, PLOTS_DIR / "model_comparison.png")
    shutil.copy2(p_comp, STATIC_IMG_DIR / "model_comparison.png")

    # 2. Confusion Matrices for Best Model on Official Unseen-Job Test Data
    best_model_A = trained_models_A[best_model_name]
    y_test_pred_best = best_model_A.predict(X_test_A)
    cm_test = np.array(test_metrics_A[best_model_name]["confusion_matrix"])
    cm_test_norm = np.array(test_metrics_A[best_model_name]["normalized_confusion_matrix"])

    p_cm = plot_confusion_matrices(
        cm_test,
        cm_test_norm,
        CLASSES,
        title=f"Held-Out Test Set (Unseen Jobs, N={len(y_test_A):,}) — {best_model_name}",
        save_path=PLOTS_DIR / "confusion_matrix.png"
    )
    shutil.copy2(p_cm, STATIC_IMG_DIR / "confusion_matrix.png")

    # 3. Confusion Matrix for Unseen-Resume Disjoint Validation
    cm_resume = np.array(val_metrics_B[best_model_name]["confusion_matrix"])
    cm_resume_norm = np.array(val_metrics_B[best_model_name]["normalized_confusion_matrix"])
    p_cm_res = plot_confusion_matrices(
        cm_resume,
        cm_resume_norm,
        CLASSES,
        title=f"Unseen Resumes Group-Disjoint Validation (N={len(y_val_B):,}) — {best_model_name}",
        save_path=PLOTS_DIR / "confusion_matrix_unseen_resumes.png"
    )
    shutil.copy2(p_cm_res, STATIC_IMG_DIR / "confusion_matrix_unseen_resumes.png")

    # 4. Per-Class Performance Comparison
    p_per = plot_per_class_performance(
        test_metrics_A[best_model_name]["per_class"],
        CLASSES,
        model_name=f"{best_model_name} (Held-Out Test)",
        save_path=PLOTS_DIR / "per_class_performance.png"
    )
    shutil.copy2(p_per, STATIC_IMG_DIR / "per_class_performance.png")

    # 5. Training vs Validation Performance
    train_f1s = [train_metrics_A[m]["macro_f1"] for m in comparison_df["Model"]]
    val_f1s = [val_metrics_A[m]["macro_f1"] for m in comparison_df["Model"]]
    p_tv = plot_train_vs_val(
        comparison_df["Model"].tolist(),
        train_f1s,
        val_f1s,
        save_path=PLOTS_DIR / "train_vs_val_comparison.png"
    )
    shutil.copy2(p_tv, STATIC_IMG_DIR / "train_vs_val_comparison.png")

    # 6. ROC Curves & PR Curves (using probabilities on held-out test)
    y_test_prob_best = best_model_A.predict_proba(X_test_A) if hasattr(best_model_A, "predict_proba") else None
    if y_test_prob_best is not None:
        p_roc = plot_roc_curves(
            y_test_A,
            y_test_prob_best,
            CLASSES,
            model_name=best_model_name,
            save_path=PLOTS_DIR / "roc_curves.png"
        )
        shutil.copy2(p_roc, STATIC_IMG_DIR / "roc_curves.png")

        p_pr = plot_precision_recall_curves(
            y_test_A,
            y_test_prob_best,
            CLASSES,
            model_name=best_model_name,
            save_path=PLOTS_DIR / "precision_recall_curves.png"
        )
        shutil.copy2(p_pr, STATIC_IMG_DIR / "precision_recall_curves.png")

    print(f"All evaluation plots successfully written to {PLOTS_DIR} and mirrored to {STATIC_IMG_DIR}")

    # -------------------------------------------------------------
    # 5. EXPORT METRICS & AUDIT FILES
    # -------------------------------------------------------------
    comparison_df.to_csv(METRICS_DIR / "model_comparison.csv", index=False)

    # Per-class classification report
    report_rows = []
    for cls_name in CLASSES:
        info = test_metrics_A[best_model_name]["per_class"][cls_name]
        report_rows.append({
            "Class": cls_name,
            "Precision": info["precision"],
            "Recall": info["recall"],
            "F1-Score": info["f1"],
            "Support": info["support"]
        })
    pd.DataFrame(report_rows).to_csv(METRICS_DIR / "classification_report.csv", index=False)

    summary_payload = {
        "selected_best_model": best_model_name,
        "evaluation_A_unseen_jobs": {
            "validation_metrics": val_metrics_A,
            "held_out_test_metrics": test_metrics_A
        },
        "evaluation_B_unseen_resumes": {
            "validation_metrics": val_metrics_B
        },
        "classes": CLASSES,
        "training_time_seconds": round(time.time() - start_total_time, 2)
    }
    with open(METRICS_DIR / "evaluation_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)

    print(f"Metrics saved to {METRICS_DIR}/")
    print(f"Total training and evaluation completed in {time.time() - start_total_time:.2f}s!")
    return summary_payload


if __name__ == "__main__":
    train_and_evaluate()
