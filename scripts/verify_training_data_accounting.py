import os
import hashlib
import json
import pandas as pd
import numpy as np

job_tr = pd.read_parquet("manifests/v1/job_disjoint_train_v1.parquet")
dual_tr = pd.read_parquet("manifests/v1/dual_unseen_train_v1.parquet")
dual_val = pd.read_parquet("manifests/v1/dual_unseen_val_v1.parquet")
held_out = pd.read_parquet("manifests/v1/held_out_test_v1.parquet")
proposed = pd.read_csv("data/external/djinni/proposed_candidate_pairs_sample.csv")

def hash_text(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()[:16]

ts_res_hashes = set(held_out["resume_text"].apply(hash_text))
ts_job_hashes = set(held_out["job_description_text"].apply(hash_text))
ts_pair_hashes = set(held_out.apply(lambda r: (hash_text(r["resume_text"]), hash_text(r["job_description_text"])), axis=1))

dv_res_hashes = set(dual_val["resume_text"].apply(hash_text))
dv_job_hashes = set(dual_val["job_description_text"].apply(hash_text))
dv_pair_hashes = set(dual_val.apply(lambda r: (hash_text(r["resume_text"]), hash_text(r["job_description_text"])), axis=1))

print("=== TRAINING DATA ACCOUNTING AUDIT ===")
print(f"Original Job-Disjoint Train rows: {len(job_tr)}")
print(f"Class distribution before augmentation:")
print(job_tr["label"].value_counts())

# In Phase 12F Experiment 5:
# 5462 base + 400 weak + 28 pseudo = 5890
print("\nCheck if proposed 830 Djinni pairs have overlap with Test or Val:")
prop_res_hashes = set(proposed["candidate_cv_text"].apply(hash_text))
prop_job_hashes = set(proposed["job_description_text"].apply(hash_text))
prop_pair_hashes = set(proposed.apply(lambda r: (hash_text(r["candidate_cv_text"]), hash_text(r["job_description_text"])), axis=1))

print(f"  Proposed vs Held-Out Test Resume Overlap: {len(prop_res_hashes.intersection(ts_res_hashes))}")
print(f"  Proposed vs Held-Out Test Job Overlap:    {len(prop_job_hashes.intersection(ts_job_hashes))}")
print(f"  Proposed vs Held-Out Test Pair Overlap:   {len(prop_pair_hashes.intersection(ts_pair_hashes))}")

print(f"  Proposed vs Dual-Unseen Val Resume Overlap: {len(prop_res_hashes.intersection(dv_res_hashes))}")
print(f"  Proposed vs Dual-Unseen Val Job Overlap:    {len(prop_job_hashes.intersection(dv_job_hashes))}")
print(f"  Proposed vs Dual-Unseen Val Pair Overlap:   {len(prop_pair_hashes.intersection(dv_pair_hashes))}")
