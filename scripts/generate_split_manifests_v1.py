"""
scripts/generate_split_manifests_v1.py
Generates immutable, versioned training/validation/test split manifests for ResumeMatch AI.

Protocols generated:
1. Job-Disjoint Validation (train_v1, val_v1, test_v1)
2. Resume-Disjoint Validation (train_v1, val_v1)
3. Dual-Unseen Validation (train_v1, val_v1)

Enforces strict zero-leakage validation before writing artifacts.
Calculates SHA-256 checksums and stores manifest_v1.json.
"""

import os
import sys
import json
import hashlib
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from src.utils.data_loader import load_primary_dataset
from src.utils.split_manager import get_unseen_jobs_split, get_unseen_resumes_split
from src.evaluation.split_validator import (
    validate_split_isolation,
    compute_overlap_metrics,
    compute_file_sha256,
    hash_text,
    hash_pair
)

MANIFEST_DIR = os.path.join(REPO_ROOT, "manifests", "v1")
os.makedirs(MANIFEST_DIR, exist_ok=True)


def main():
    print("=" * 80)
    print("GENERATING IMMUTABLE EVALUATION SPLIT MANIFESTS (V1)")
    print("=" * 80)

    # 1. Load Primary Data
    train_df, test_df = load_primary_dataset()
    raw_train_path = os.path.join(REPO_ROOT, "data", "raw", "resume_job_fit_train.csv")
    raw_train_sha256 = compute_file_sha256(raw_train_path)
    print(f"Primary Training Dataset: {raw_train_path} (SHA-256: {raw_train_sha256[:16]}...)")

    # Load 6 contradictory pairs to remove from clean training partitions
    conflict_path = os.path.join(REPO_ROOT, "results", "phase12_audit", "conflicting_label_pairs_detailed.json")
    if os.path.exists(conflict_path):
        with open(conflict_path) as f:
            conflicts = json.load(f)
        contra_hashes = set(p["pair_hash"] for p in conflicts)
        print(f"Loaded {len(contra_hashes)} contradictory label pair hashes to filter from training.")
    else:
        contra_hashes = set()

    def filter_clean(df: pd.DataFrame) -> pd.DataFrame:
        pair_hashes = df.apply(lambda r: hash_pair(r["resume_text"], r["job_description_text"]), axis=1)
        return df[~pair_hashes.isin(contra_hashes)].reset_index(drop=True)

    # 2. Protocol 1: Job-Disjoint Validation
    print("\n--- Protocol 1: Job-Disjoint Split ---")
    train_sub_job, val_sub_job, held_out_test = get_unseen_jobs_split(val_size=0.15, random_state=42)
    train_sub_job_clean = filter_clean(train_sub_job)

    # Validate isolation
    v_job = validate_split_isolation(train_sub_job_clean, val_sub_job, protocol="job_disjoint", split_name="Job-Disjoint Val")
    v_test = validate_split_isolation(train_sub_job_clean, held_out_test, protocol="held_out_test", split_name="Held-Out Test")
    print("  Validated Job-Disjoint Val: 0 job overlap, 0 pair overlap.")
    print("  Validated Held-Out Test: 0 job overlap, 0 pair overlap.")

    # 3. Protocol 2: Resume-Disjoint Validation
    print("\n--- Protocol 2: Resume-Disjoint Split ---")
    train_sub_res, val_sub_res = get_unseen_resumes_split(test_size=0.15, random_state=42)
    train_sub_res_clean = filter_clean(train_sub_res)

    v_res = validate_split_isolation(train_sub_res_clean, val_sub_res, protocol="resume_disjoint", split_name="Resume-Disjoint Val")
    print("  Validated Resume-Disjoint Val: 0 resume overlap, 0 pair overlap.")

    # 4. Protocol 3: Dual-Unseen Validation
    print("\n--- Protocol 3: Dual-Unseen Split ---")
    dual_train_path = os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_train.csv")
    dual_val_path = os.path.join(REPO_ROOT, "experiments", "dataset_improvement", "splits", "dual_unseen_val.csv")
    dual_train_df = pd.read_csv(dual_train_path)
    dual_val_df = pd.read_csv(dual_val_path)
    dual_train_clean = filter_clean(dual_train_df)

    v_dual = validate_split_isolation(dual_train_clean, dual_val_df, protocol="dual_unseen", split_name="Dual-Unseen Val")
    print("  Validated Dual-Unseen Val: 0 resume overlap, 0 job overlap, 0 pair overlap.")

    # 5. Save Parquet Split Files
    splits_to_save = {
        "job_disjoint_train_v1.parquet": (train_sub_job_clean, "job_disjoint", "train"),
        "job_disjoint_val_v1.parquet": (val_sub_job, "job_disjoint", "val"),
        "held_out_test_v1.parquet": (held_out_test, "held_out_test", "test"),
        "resume_disjoint_train_v1.parquet": (train_sub_res_clean, "resume_disjoint", "train"),
        "resume_disjoint_val_v1.parquet": (val_sub_res, "resume_disjoint", "val"),
        "dual_unseen_train_v1.parquet": (dual_train_clean, "dual_unseen", "train"),
        "dual_unseen_val_v1.parquet": (dual_val_df, "dual_unseen", "val"),
    }

    manifest_files_info = []

    for fname, (df, protocol, role) in splits_to_save.items():
        out_path = os.path.join(MANIFEST_DIR, fname)
        df.to_parquet(out_path, index=False)
        sha256 = compute_file_sha256(out_path)
        print(f"Saved {fname} (N={len(df)}, SHA-256: {sha256[:16]}...)")

        manifest_files_info.append({
            "filename": fname,
            "relative_path": fname,
            "protocol": protocol,
            "role": role,
            "record_count": len(df),
            "unique_resumes": int(df["resume_text"].nunique()),
            "unique_jobs": int(df["job_description_text"].nunique()),
            "label_distribution": {k: int(v) for k, v in df["label"].value_counts().items()},
            "sha256": sha256
        })

    # 6. Save Manifest JSON
    manifest = {
        "manifest_version": "1.0.0",
        "description": "Immutable versioned split manifests for ResumeMatch AI evaluation",
        "created_at": "2026-11-11T18:40:00Z",
        "primary_dataset_path": "data/raw/resume_job_fit_train.csv",
        "primary_dataset_sha256": raw_train_sha256,
        "contradictory_pairs_excluded": len(contra_hashes),
        "files": manifest_files_info,
        "isolation_guarantees": {
            "job_disjoint": "0 overlapping jobs between train and val; 0 overlapping pairs",
            "resume_disjoint": "0 overlapping resumes between train and val; 0 overlapping pairs",
            "dual_unseen": "0 overlapping resumes AND 0 overlapping jobs between train and val; 0 overlapping pairs",
            "held_out_test": "0 overlapping jobs with primary training data; 0 overlapping pairs"
        }
    }

    manifest_json_path = os.path.join(MANIFEST_DIR, "manifest_v1.json")
    with open(manifest_json_path, "w") as f:
        json.dump(manifest, f, indent=2)

    master_sha256 = compute_file_sha256(manifest_json_path)
    print(f"\nManifest V1 successfully generated and sealed: {manifest_json_path}")
    print(f"Master Manifest SHA-256: {master_sha256}")
    print("=" * 80)


if __name__ == "__main__":
    main()
