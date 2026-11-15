import os
import hashlib
import json
import pandas as pd
import numpy as np

def hash_text(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()[:16]

job_tr = pd.read_parquet("manifests/v1/job_disjoint_train_v1.parquet")
dual_tr = pd.read_parquet("manifests/v1/dual_unseen_train_v1.parquet")
dual_val = pd.read_parquet("manifests/v1/dual_unseen_val_v1.parquet")
held_out = pd.read_parquet("manifests/v1/held_out_test_v1.parquet")

def get_hashes(df):
    r = set(df["resume_text"].apply(hash_text))
    j = set(df["job_description_text"].apply(hash_text))
    p = set(df.apply(lambda row: (hash_text(row["resume_text"]), hash_text(row["job_description_text"])), axis=1))
    return r, j, p

r_job_tr, j_job_tr, p_job_tr = get_hashes(job_tr)
r_dual_tr, j_dual_tr, p_dual_tr = get_hashes(dual_tr)
r_dual_val, j_dual_val, p_dual_val = get_hashes(dual_val)
r_test, j_test, p_test = get_hashes(held_out)

print("=== OVERLAP AUDIT ===")
print("1. dual_unseen_val vs dual_unseen_train (The proper protocol):")
print(f"  Resume Overlap: {len(r_dual_val.intersection(r_dual_tr))} / {len(r_dual_val)}")
print(f"  Job Overlap:    {len(j_dual_val.intersection(j_dual_tr))} / {len(j_dual_val)}")
print(f"  Pair Overlap:   {len(p_dual_val.intersection(p_dual_tr))} / {len(p_dual_val)}")

print("\n2. dual_unseen_val vs job_disjoint_train (WHAT PHASE 12F TRAINED ON in EXP 2, 4, 5!):")
print(f"  Resume Overlap: {len(r_dual_val.intersection(r_job_tr))} / {len(r_dual_val)} ({len(r_dual_val.intersection(r_job_tr))/len(r_dual_val)*100:.2f}%)")
print(f"  Job Overlap:    {len(j_dual_val.intersection(j_job_tr))} / {len(j_dual_val)} ({len(j_dual_val.intersection(j_job_tr))/len(j_dual_val)*100:.2f}%)")
print(f"  Pair Overlap:   {len(p_dual_val.intersection(p_job_tr))} / {len(p_dual_val)} ({len(p_dual_val.intersection(p_job_tr))/len(p_dual_val)*100:.2f}%)")

print("\n3. Training set sizes in Phase 12F:")
print(f"  job_disjoint_train: {len(job_tr)}")
print(f"  dual_unseen_train:  {len(dual_tr)}")
