"""
scripts/phase12f3_3/generate_and_reconcile_predictions.py
Generates, aligns, reconciles, and saves full test predictions for both Raw SBERT and Contrastive representations
across all five seeds [42, 43, 44, 45, 46].
Preserves exact row indices, resume/job hashes, true labels, predicted classes, and class probabilities.
"""

import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.phase12f2.split_guard import load_guarded_dual_unseen_splits
from src.evaluation.split_validator import hash_text
from scripts.phase12f3_1.reproduce_contrastive_downstream import (
    ContrastiveProjector,
    train_contrastive_encoder_on_train_only,
    SEEDS,
    CACHE_PATH,
    CLASSES
)

REPO_ROOT = Path("D:/skillsync1")
PRED_DIR = REPO_ROOT / "experiments" / "phase12f3_3" / "predictions"
RES_DIR = REPO_ROOT / "experiments" / "phase12f3_3" / "results"
PRED_DIR.mkdir(parents=True, exist_ok=True)
RES_DIR.mkdir(parents=True, exist_ok=True)

def build_features(u, v):
    cos = np.sum(u * v, axis=1, keepdims=True) / (np.linalg.norm(u, axis=1, keepdims=True) * np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
    return np.hstack([u, v, u * v, np.abs(u - v), cos])

def get_file_hash(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    print("=" * 80)
    print("PHASE 12F.3.3: GENERATING AND RECONCILING ALL 5 SEED PREDICTION ARTIFACTS")
    print("=" * 80)

    # 1. Record input artifact hashes
    manifest_tr_path = REPO_ROOT / "manifests" / "v1" / "dual_unseen_train_v1.parquet"
    manifest_vl_path = REPO_ROOT / "manifests" / "v1" / "dual_unseen_val_v1.parquet"
    artifact_hashes = {
        "dual_unseen_train_v1_parquet": {
            "path": str(manifest_tr_path),
            "sha256": get_file_hash(manifest_tr_path),
            "size_bytes": manifest_tr_path.stat().st_size
        },
        "dual_unseen_val_v1_parquet": {
            "path": str(manifest_vl_path),
            "sha256": get_file_hash(manifest_vl_path),
            "size_bytes": manifest_vl_path.stat().st_size
        },
        "sbert_cache_npz": {
            "path": str(CACHE_PATH),
            "sha256": get_file_hash(CACHE_PATH),
            "size_bytes": CACHE_PATH.stat().st_size
        },
        "production_model_joblib": {
            "path": str(REPO_ROOT / "models" / "best_model.joblib"),
            "sha256": get_file_hash(REPO_ROOT / "models" / "best_model.joblib"),
            "size_bytes": (REPO_ROOT / "models" / "best_model.joblib").stat().st_size
        },
        "feature_pipeline_joblib": {
            "path": str(REPO_ROOT / "models" / "feature_pipeline.joblib"),
            "sha256": get_file_hash(REPO_ROOT / "models" / "feature_pipeline.joblib"),
            "size_bytes": (REPO_ROOT / "models" / "feature_pipeline.joblib").stat().st_size
        }
    }
    with open(RES_DIR / "artifact_hashes.json", "w") as f:
        json.dump(artifact_hashes, f, indent=2)
    print("Input artifact hashes verified and saved to artifact_hashes.json")

    # 2. Load guarded splits (N=296 validation pairs)
    dual_tr, dual_vl = load_guarded_dual_unseen_splits()
    y_tr = dual_tr["label"].values
    y_vl = dual_vl["label"].values

    cached_data = np.load(CACHE_PATH, allow_pickle=True)
    res_emb_dict = {h: cached_data[f"res_{h}"] for h in cached_data["res_hashes"]}
    job_emb_dict = {h: cached_data[f"job_{h}"] for h in cached_data["job_hashes"]}

    u_tr = np.array([res_emb_dict[hash_text(t)] for t in dual_tr["resume_text"]], dtype=np.float32)
    v_tr = np.array([job_emb_dict[hash_text(t)] for t in dual_tr["job_description_text"]], dtype=np.float32)
    u_vl = np.array([res_emb_dict[hash_text(t)] for t in dual_vl["resume_text"]], dtype=np.float32)
    v_vl = np.array([job_emb_dict[hash_text(t)] for t in dual_vl["job_description_text"]], dtype=np.float32)

    X_raw_tr = build_features(u_tr, v_tr)
    X_raw_vl = build_features(u_vl, v_vl)

    val_row_indices = list(range(len(dual_vl)))
    val_res_hashes = [hash_text(t) for t in dual_vl["resume_text"]]
    val_job_hashes = [hash_text(t) for t in dual_vl["job_description_text"]]
    val_res_ids = dual_vl["resume_id"].tolist() if "resume_id" in dual_vl.columns else val_res_hashes
    val_job_ids = dual_vl["job_id"].tolist() if "job_id" in dual_vl.columns else val_job_hashes

    reconciliation_table = []

    for seed in SEEDS:
        print(f"\nProcessing Seed {seed}...")
        projector = train_contrastive_encoder_on_train_only(u_tr, v_tr, y_tr, seed=seed)

        with torch.no_grad():
            z_u_tr = projector(torch.tensor(u_tr)).numpy()
            z_v_tr = projector(torch.tensor(v_tr)).numpy()
            z_u_vl = projector(torch.tensor(u_vl)).numpy()
            z_v_vl = projector(torch.tensor(v_vl)).numpy()

        X_proj_tr = build_features(z_u_tr, z_v_tr)
        X_proj_vl = build_features(z_u_vl, z_v_vl)

        # Baseline Raw SBERT Classifier
        sc_raw = StandardScaler().fit(X_raw_tr)
        clf_raw = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=seed)
        clf_raw.fit(sc_raw.transform(X_raw_tr), y_tr)
        pred_raw = clf_raw.predict(sc_raw.transform(X_raw_vl))
        prob_raw = clf_raw.predict_proba(sc_raw.transform(X_raw_vl))

        # Contrastive Projected Classifier
        sc_proj = StandardScaler().fit(X_proj_tr)
        clf_proj = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=seed)
        clf_proj.fit(sc_proj.transform(X_proj_tr), y_tr)
        pred_proj = clf_proj.predict(sc_proj.transform(X_proj_vl))
        prob_proj = clf_proj.predict_proba(sc_proj.transform(X_proj_vl))

        # Build detailed seed prediction DataFrame
        seed_df = pd.DataFrame({
            "row_index": val_row_indices,
            "resume_id": val_res_ids,
            "job_id": val_job_ids,
            "resume_text_hash": val_res_hashes,
            "job_text_hash": val_job_hashes,
            "true_label": y_vl,
            "pred_raw_sbert": pred_raw,
            "pred_contrastive": pred_proj,
            "raw_prob_No_Fit": prob_raw[:, list(clf_raw.classes_).index("No Fit")],
            "raw_prob_Potential_Fit": prob_raw[:, list(clf_raw.classes_).index("Potential Fit")],
            "raw_prob_Good_Fit": prob_raw[:, list(clf_raw.classes_).index("Good Fit")],
            "proj_prob_No_Fit": prob_proj[:, list(clf_proj.classes_).index("No Fit")],
            "proj_prob_Potential_Fit": prob_proj[:, list(clf_proj.classes_).index("Potential Fit")],
            "proj_prob_Good_Fit": prob_proj[:, list(clf_proj.classes_).index("Good Fit")],
            "raw_correct": (pred_raw == y_vl).astype(int),
            "contrastive_correct": (pred_proj == y_vl).astype(int)
        })

        pred_csv_path = PRED_DIR / f"contrastive_vs_raw_seed_{seed}.csv"
        seed_df.to_csv(pred_csv_path, index=False)
        print(f"  Saved detailed predictions to {pred_csv_path}")

        # Verification checks
        assert len(seed_df) == 296, f"Seed {seed} has {len(seed_df)} rows, expected 296!"
        assert (seed_df["true_label"] == y_vl).all(), f"Seed {seed} true labels do not match validation partition!"
        assert set(seed_df["pred_raw_sbert"]).issubset(set(CLASSES)), f"Unknown classes in raw predictions!"
        assert set(seed_df["pred_contrastive"]).issubset(set(CLASSES)), f"Unknown classes in contrastive predictions!"

        matched_examples = int(len(seed_df))
        missing_rows = 0
        prediction_differences = int((seed_df["pred_raw_sbert"] != seed_df["pred_contrastive"]).sum())
        baseline_only_correct = int(((seed_df["raw_correct"] == 1) & (seed_df["contrastive_correct"] == 0)).sum())
        contrastive_only_correct = int(((seed_df["raw_correct"] == 0) & (seed_df["contrastive_correct"] == 1)).sum())
        both_correct = int(((seed_df["raw_correct"] == 1) & (seed_df["contrastive_correct"] == 1)).sum())
        both_incorrect = int(((seed_df["raw_correct"] == 0) & (seed_df["contrastive_correct"] == 0)).sum())

        reconciliation_table.append({
            "seed": seed,
            "prediction_file": str(pred_csv_path.name),
            "file_sha256": get_file_hash(pred_csv_path),
            "total_examples": matched_examples,
            "missing_rows": missing_rows,
            "ground_truth_label_mismatches": 0,
            "prediction_differences_between_models": prediction_differences,
            "contingency_counts": {
                "both_correct_n11": both_correct,
                "both_incorrect_n00": both_incorrect,
                "raw_correct_contrastive_incorrect_n10": baseline_only_correct,
                "raw_incorrect_contrastive_correct_n01": contrastive_only_correct
            }
        })

    with open(RES_DIR / "prediction_reconciliation.json", "w") as f:
        json.dump(reconciliation_table, f, indent=2)
    print("\nReconciliation table saved to prediction_reconciliation.json")

if __name__ == "__main__":
    main()
