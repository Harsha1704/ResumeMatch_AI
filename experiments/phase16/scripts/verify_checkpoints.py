"""
experiments/phase16/scripts/verify_checkpoints.py
Independent verification of production model checkpoints and preprocessing pipelines.
Calculates SHA-256 hashes and byte lengths; compares against frozen historical hashes.
"""

import os
import json
import hashlib
from pathlib import Path

REPO_ROOT = Path("D:/skillsync1")
CHECKPOINTS = [
    {
        "name": "Production Best Model (Logistic Regression)",
        "path": "models/best_model.joblib",
        "expected_hash": "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a",
        "expected_size": 61487
    },
    {
        "name": "Production Feature Pipeline",
        "path": "models/feature_pipeline.joblib",
        "expected_hash": "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6",
        "expected_size": 270105
    },
    {
        "name": "Challenger Model Phase 12F (Linear Baseline)",
        "path": "models/phase12f/challenger_model_phase12f.joblib",
        "expected_hash": "5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766",
        "expected_size": 2330440
    },
    {
        "name": "Challenger Model 5 (Semantic-Skill Fusion Head)",
        "path": "models/phase13/semantic_skill_fusion_challenger.joblib",
        "expected_hash": "50aaabfe53025a04d2221f71fa6977bec9615649cff84e8da37d299f5cc44807",
        "expected_size": 78194
    }
]

def main():
    print("=" * 80)
    print("PHASE 16 — PRODUCTION CHECKPOINT INTEGRITY VERIFICATION")
    print("=" * 80)

    results = []
    all_passed = True

    header = f"{'MODEL NAME':<45} | {'SIZE (B)':<10} | {'SHA-256 DIGEST (PREFIX)':<24} | {'STATUS'}"
    print(header)
    print("-" * len(header))

    for item in CHECKPOINTS:
        p = REPO_ROOT / item["path"]
        if not p.exists():
            status = "FILE NOT FOUND"
            all_passed = False
            res_item = {**item, "current_hash": None, "current_size": 0, "status": status}
            cur_size = 0
            cur_hash = "N/A"
        else:
            data = p.read_bytes()
            cur_hash = hashlib.sha256(data).hexdigest()
            cur_size = len(data)
            hash_match = (cur_hash == item["expected_hash"])
            size_match = (cur_size == item["expected_size"])
            if hash_match and size_match:
                status = "PASS"
            else:
                status = "FAIL"
                all_passed = False
            res_item = {
                "name": item["name"],
                "path": item["path"],
                "expected_hash": item["expected_hash"],
                "current_hash": cur_hash,
                "expected_size": item["expected_size"],
                "current_size": cur_size,
                "status": status
            }
        results.append(res_item)
        print(f"{item['name'][:43]:<45} | {cur_size:<10} | {cur_hash[:22]:<24} | {status}")

    out_dir = REPO_ROOT / "experiments" / "phase16"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "checkpoint_hashes.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"all_checkpoints_passed": all_passed, "checkpoints": results}, f, indent=2)

    print("-" * len(header))
    print(f"Overall Checkpoint Status: {'ALL PASSED' if all_passed else 'VERIFICATION FAILED'}")
    print(f"Recorded results to: {out_file}")
    print("=" * 80)
    if not all_passed:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
