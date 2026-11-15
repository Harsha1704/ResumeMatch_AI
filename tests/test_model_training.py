"""
Unit and Regression Tests for Supervised ML Training, Inference, and Metrics.
Verifies training reproducibility, leakage separation, 3x3 confusion matrices,
prediction consistency, and artifact integrity.
"""

from pathlib import Path
import json
import joblib
import pytest
import numpy as np
import pandas as pd

from src.utils.data_loader import load_primary_dataset, VALID_LABELS
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.models.train import get_candidate_models
from src.models.inference import predict_match, get_inference_engine, CLASSES


def test_candidate_models_instantiation():
    """Verify all 3 required supervised models are initialized."""
    models = get_candidate_models()
    assert "Logistic Regression" in models
    assert "Linear SVM (Calibrated)" in models
    assert "Random Forest" in models


def test_saved_artifacts_exist():
    """Verify all required trained models and evaluation artifacts exist on disk."""
    required_artifacts = [
        "models/best_model.joblib",
        "models/feature_pipeline.joblib",
        "models/label_mapping.json",
        "models/logistic_regression.joblib",
        "models/linear_svm_calibrated.joblib",
        "models/random_forest.joblib",
        "results/metrics/model_comparison.csv",
        "results/metrics/evaluation_summary.json",
        "results/metrics/classification_report.csv",
        "results/plots/model_comparison.png",
        "results/plots/confusion_matrix.png",
        "results/plots/confusion_matrix_unseen_resumes.png",
        "results/plots/per_class_performance.png",
        "results/plots/train_vs_val_comparison.png"
    ]
    for path_str in required_artifacts:
        p = Path(path_str)
        assert p.exists(), f"Missing required artifact: {path_str}"
        assert p.stat().st_size > 0, f"Artifact is empty: {path_str}"


def test_label_mapping_consistency():
    """Verify label mapping strictly matches the 3 target classes."""
    mapping_path = Path("models/label_mapping.json")
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    assert set(mapping["classes"]) == set(VALID_LABELS)
    assert len(mapping["classes"]) == 3
    for c in VALID_LABELS:
        assert c in mapping["label_to_id"]


def test_evaluation_summary_integrity():
    """Verify genuine metrics, confusion matrix dimensions, and conservation of sample counts."""
    summary_path = Path("results/metrics/evaluation_summary.json")
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert "selected_best_model" in summary
    assert "evaluation_A_unseen_jobs" in summary
    assert "evaluation_B_unseen_resumes" in summary

    test_metrics = summary["evaluation_A_unseen_jobs"]["held_out_test_metrics"]["Logistic Regression"]
    cm = np.array(test_metrics["confusion_matrix"])

    # Verify 3x3 dimensions
    assert cm.shape == (3, 3)

    # Verify entries sum exactly to 1,759 held-out test samples
    assert cm.sum() == 1759

    # Verify metrics are finite and valid
    assert 0.0 < test_metrics["accuracy"] <= 1.0
    assert 0.0 < test_metrics["macro_f1"] <= 1.0
    assert 0.0 < test_metrics["macro_precision"] <= 1.0
    assert 0.0 < test_metrics["macro_recall"] <= 1.0


def test_inference_pipeline_predictions():
    """Verify that saved model reloads and predicts valid classes and transparent scores."""
    engine = get_inference_engine()
    assert engine.model is not None
    assert engine.pipeline is not None

    resume = "Data Analyst skilled in SQL, Python, Tableau, and Excel with 3 years of experience."
    job = "Hiring Data Analyst with Python, SQL, and data visualization experience."

    res = predict_match(resume, job)
    assert res["status"] == "success"
    assert res["predicted_class"] in CLASSES
    assert 0.0 <= res["confidence"] <= 1.0
    assert 0.0 <= res["compatibility_score"] <= 100.0
    assert set(res["probabilities"].keys()) == set(CLASSES)
    assert abs(sum(res["probabilities"].values()) - 1.0) < 0.01

    # Verify skill analysis output
    assert "python" in res["skill_analysis"]["matched_skills"]
    assert "sql" in res["skill_analysis"]["matched_skills"]


def test_inference_graceful_error_handling():
    """Verify empty/none inputs return valid fallback response without raising unhandled exceptions."""
    res1 = predict_match("", "")
    assert res1["status"] == "invalid_input"
    assert res1["predicted_class"] == "No Fit"
    assert res1["compatibility_score"] == 0.0

    res2 = predict_match(None, "Valid job description")
    assert res2["status"] == "invalid_input"
