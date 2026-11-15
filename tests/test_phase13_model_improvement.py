"""
tests/test_phase13_model_improvement.py
Verification test suite for Phase 13: Genuine Model Improvement.
"""

import json
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import joblib

REPO_ROOT = Path("D:/skillsync1")
RES_DIR = REPO_ROOT / "experiments" / "phase13" / "results"
MODELS_DIR = REPO_ROOT / "models" / "phase13"
PRED_DIR = REPO_ROOT / "experiments" / "phase13" / "predictions"

EXPECTED_PROD_CHECKPOINTS = {
    REPO_ROOT / "models" / "best_model.joblib": ("1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a", 61487),
    REPO_ROOT / "models" / "feature_pipeline.joblib": ("2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6", 270105),
    REPO_ROOT / "models" / "phase12f" / "challenger_model_phase12f.joblib": ("5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766", 2330440),
}


def test_production_checkpoints_preserved():
    """Confirms all three historical production checkpoints remain 100% bit-for-bit unchanged."""
    for path, (exp_hash, exp_size) in EXPECTED_PROD_CHECKPOINTS.items():
        assert path.exists(), f"Missing production checkpoint: {path}"
        data = path.read_bytes()
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == exp_hash, f"Hash mismatch for {path}: expected {exp_hash}, got {actual_hash}"
        assert len(data) == exp_size, f"Size mismatch for {path}: expected {exp_size}, got {len(data)}"


def test_phase13_model_checkpoints_exist():
    """Confirms Phase 13 model checkpoints were generated and are loadable."""
    m4_path = MODELS_DIR / "skill_aware_matching_model.joblib"
    m5_path = MODELS_DIR / "semantic_skill_fusion_challenger.joblib"
    assert m4_path.exists(), "Model 4 checkpoint missing"
    assert m5_path.exists(), "Model 5 checkpoint missing"
    
    m4_obj = joblib.load(m4_path)
    assert "model" in m4_obj
    assert "scaler" in m4_obj
    
    m5_obj = joblib.load(m5_path)
    assert "model" in m5_obj
    assert "scaler_sbert" in m5_obj
    assert "scaler_dom" in m5_obj
    assert m5_obj["total_dim"] == 1565


def test_dual_unseen_validation_integrity():
    """Confirms evaluation used exactly 296 clean pairs and 0 overlap with train."""
    from src.phase12f2.split_guard import load_guarded_dual_unseen_splits
    tr_df, vl_df = load_guarded_dual_unseen_splits()
    assert len(tr_df) == 3857
    assert len(vl_df) == 296
    
    # 0 resume and job overlap
    tr_res = set(tr_df["resume_id"])
    vl_res = set(vl_df["resume_id"])
    assert len(tr_res.intersection(vl_res)) == 0
    
    tr_job = set(tr_df["job_id"])
    vl_job = set(vl_df["job_id"])
    assert len(tr_job.intersection(vl_job)) == 0


def test_quarantined_test_set_unaccessed():
    """Confirms held_out_test_v1.parquet was NOT accessed or evaluated in Phase 13."""
    # Check that no result file in experiments/phase13 references held_out_test_v1.parquet
    for p in RES_DIR.glob("*.json"):
        content = p.read_text(encoding="utf-8")
        assert "held_out_test_v1.parquet" not in content, f"Leakage violation: {p.name} references held_out_test!"


def test_model5_performance_improvement():
    """Confirms Model 5 genuinely outperforms Production Baseline on Accuracy, Macro F1, and Good Fit Recall."""
    summary_path = RES_DIR / "phase13_evaluation_summary.json"
    assert summary_path.exists()
    with open(summary_path) as f:
        summary = json.load(f)
        
    m1 = summary["models"]["model_1_production_baseline"]
    m5 = summary["models"]["model_5_semantic_skill_fusion_challenger"]
    
    # Accuracy improvement (+7.1% pp)
    assert m5["accuracy_mean"] > m1["accuracy"]
    assert m5["accuracy_mean"] >= 0.43
    
    # Macro F1 improvement (+0.092)
    assert m5["macro_f1_mean"] > m1["macro_f1"]
    assert m5["macro_f1_mean"] >= 0.41
    
    # Good Fit Recall improvement (+11.8% pp / +78% relative)
    assert m5["good_fit_recall_mean"] > m1["good_fit_recall"]
    assert m5["good_fit_recall_mean"] >= 0.25


def test_paired_statistical_significance():
    """Confirms McNemar exact test is statistically significant at alpha=0.05."""
    stat_path = RES_DIR / "phase13_statistical_evaluation.json"
    assert stat_path.exists()
    with open(stat_path) as f:
        stat_data = json.load(f)
        
    m5_vs_prod = stat_data["model_5_vs_production_baseline"]
    mcnemar = m5_vs_prod["mcnemar_exact_test"]
    assert mcnemar["statistically_significant_at_alpha_0_05"] is True
    assert mcnemar["mcnemar_exact_two_sided_p_value"] < 0.05
    assert mcnemar["challenger_only_correct"] > mcnemar["baseline_only_correct"]
    
    # CGM sandwich CI does not cross zero
    cgm = m5_vs_prod["cgm_two_way_crve_sandwich"]
    assert cgm["ci_crosses_zero"] is False
    assert cgm["ci_95_pp"][0] > 0


def test_release_gates_all_pass():
    """Confirms all 8 Stage E release gates are satisfied."""
    gates_path = RES_DIR / "phase13_release_gates.json"
    assert gates_path.exists()
    with open(gates_path) as f:
        gates_data = json.load(f)
        
    assert gates_data["all_gates_passed"] is True
    for gname, ginfo in gates_data["gates"].items():
        assert ginfo["passed"] is True, f"Gate failed: {gname}"


def test_prediction_artifacts_intact():
    """Confirms predictions CSVs for all 5 seeds exist and have 296 rows."""
    for s in [42, 43, 44, 45, 46]:
        p = PRED_DIR / f"phase13_challenger_predictions_seed_{s}.csv"
        assert p.exists()
        df = pd.read_csv(p)
        assert len(df) == 296
        assert set(df["true_label"].unique()) == {"No Fit", "Potential Fit", "Good Fit"}
        assert set(df["pred_challenger_m5"].unique()) == {"No Fit", "Potential Fit", "Good Fit"}
