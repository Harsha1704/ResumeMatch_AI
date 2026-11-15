import os
import hashlib
import json
import pandas as pd
import numpy as np

def hash_text(text: str) -> str:
    return hashlib.md5(str(text).strip().encode("utf-8")).hexdigest()[:16]

def audit_pair_sets(name_a, df_a, name_b, df_b):
    r_a = set(df_a["resume_text"].apply(hash_text))
    j_a = set(df_a["job_description_text"].apply(hash_text))
    p_a = set(df_a.apply(lambda r: (hash_text(r["resume_text"]), hash_text(r["job_description_text"])), axis=1))

    r_b = set(df_b["resume_text"].apply(hash_text))
    j_b = set(df_b["job_description_text"].apply(hash_text))
    p_b = set(df_b.apply(lambda r: (hash_text(r["resume_text"]), hash_text(r["job_description_text"])), axis=1))

    r_inter = r_a.intersection(r_b)
    j_inter = j_a.intersection(j_b)
    p_inter = p_a.intersection(p_b)

    print(f"=== {name_a} vs {name_b} ===")
    print(f"  {name_a}: {len(df_a)} rows, {len(r_a)} unique resumes, {len(j_a)} unique jobs, {len(p_a)} unique pairs")
    print(f"  {name_b}: {len(df_b)} rows, {len(r_b)} unique resumes, {len(j_b)} unique jobs, {len(p_b)} unique pairs")
    print(f"  Resume Overlap: {len(r_inter)} / {len(r_b)} in {name_b} ({len(r_inter)/len(r_b)*100:.2f}%)")
    print(f"  Job Overlap:    {len(j_inter)} / {len(j_b)} in {name_b} ({len(j_inter)/len(j_b)*100:.2f}%)")
    print(f"  Exact Pair Overlap: {len(p_inter)} / {len(p_b)} in {name_b} ({len(p_inter)/len(p_b)*100:.2f}%)")
    print()
    return {
        "df_a_rows": len(df_a), "df_a_resumes": len(r_a), "df_a_jobs": len(j_a), "df_a_pairs": len(p_a),
        "df_b_rows": len(df_b), "df_b_resumes": len(r_b), "df_b_jobs": len(j_b), "df_b_pairs": len(p_b),
        "resume_overlap": len(r_inter), "job_overlap": len(j_inter), "pair_overlap": len(p_inter)
    }

raw_train = pd.read_csv("data/raw/resume_job_fit_train.csv")
raw_test = pd.read_csv("data/raw/resume_job_fit_test.csv")

audit_pair_sets("Raw Train (resume_job_fit_train.csv)", raw_train,
                "Raw Test (resume_job_fit_test.csv)", raw_test)

# Check Manifest V1 files
p_job_tr = pd.read_parquet("manifests/v1/job_disjoint_train_v1.parquet")
p_job_vl = pd.read_parquet("manifests/v1/job_disjoint_val_v1.parquet")
audit_pair_sets("Job-Disjoint Train V1", p_job_tr, "Job-Disjoint Val V1", p_job_vl)

p_res_tr = pd.read_parquet("manifests/v1/resume_disjoint_train_v1.parquet")
p_res_vl = pd.read_parquet("manifests/v1/resume_disjoint_val_v1.parquet")
audit_pair_sets("Resume-Disjoint Train V1", p_res_tr, "Resume-Disjoint Val V1", p_res_vl)

p_dual_tr = pd.read_parquet("manifests/v1/dual_unseen_train_v1.parquet")
p_dual_vl = pd.read_parquet("manifests/v1/dual_unseen_val_v1.parquet")
audit_pair_sets("Dual-Unseen Train V1", p_dual_tr, "Dual-Unseen Val V1", p_dual_vl)

p_held_out = pd.read_parquet("manifests/v1/held_out_test_v1.parquet")
audit_pair_sets("Raw Train", raw_train, "Held-Out Test V1", p_held_out)
audit_pair_sets("Dual-Unseen Train V1", p_dual_tr, "Held-Out Test V1", p_held_out)
