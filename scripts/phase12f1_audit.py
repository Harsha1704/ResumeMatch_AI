import os
import sys
import json
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np

REPO_ROOT = Path("D:/skillsync1")

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

prod_path = REPO_ROOT / "models" / "best_model.joblib"
chal_path = REPO_ROOT / "models" / "phase12f" / "challenger_model_phase12f.joblib"
reg_path = REPO_ROOT / "experiments" / "phase12f" / "results" / "phase12f_experiment_registry.json"

prod_sha = get_sha256(prod_path)
chal_sha = get_sha256(chal_path)

print("=== CHECKPOINT AUDIT ===")
print(f"Production Checkpoint: {prod_path}")
print(f"  Size: {os.path.getsize(prod_path)} bytes")
print(f"  SHA-256: {prod_sha}")
expected_prod_sha = "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"
print(f"  Integrity Match: {prod_sha.lower() == expected_prod_sha.lower()}")

print(f"\nChallenger Checkpoint: {chal_path}")
print(f"  Size: {os.path.getsize(chal_path)} bytes")
print(f"  SHA-256: {chal_sha}")

with open(reg_path, "r", encoding="utf-8") as f:
    reg = json.load(f)

print("\n=== EXPERIMENT REGISTRY AUDIT ===")
print(f"Phase: {reg.get('phase')}")
print(f"Created At: {reg.get('created_at')}")
print(f"Total Runtime Sec: {reg.get('total_runtime_seconds')}")
print(f"Registry Recorded Prod SHA: {reg.get('production_sha256')}")
print(f"Registry Recorded Chal SHA: {reg.get('challenger_sha256')}")
print(f"Challenger SHA matches registry: {chal_sha.lower() == reg.get('challenger_sha256').lower()}")

print("\nExperiments recorded in registry:")
for exp_id, exp_data in reg.get("experiments", {}).items():
    print(f"\n--- {exp_id} ---")
    print(f"  Description: {exp_data.get('description')}")
    if "models" in exp_data:
        for m_name, m_metrics in exp_data["models"].items():
            print(f"  Model '{m_name}':")
            for split_name, s_m in m_metrics.items():
                print(f"    {split_name}: Acc={s_m.get('accuracy')}, Macro F1={s_m.get('macro_f1')}, Bal Acc={s_m.get('balanced_accuracy')}")
    else:
        for k in ["held_out_test", "dual_unseen_val", "clustered_bootstrap_ci"]:
            if k in exp_data:
                v = exp_data[k]
                if isinstance(v, dict) and "accuracy" in v:
                    print(f"    {k}: Acc={v.get('accuracy')}, Macro F1={v.get('macro_f1')}, Bal Acc={v.get('balanced_accuracy')}")
                elif k == "clustered_bootstrap_ci":
                    print(f"    {k}: {v}")
