import os
import hashlib
import json
import re
import pandas as pd
import numpy as np

REPO_ROOT = "D:\\skillsync1"

def hash_text(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()[:16]

def norm_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return " ".join(text.split())

def hash_norm_text(text: str) -> str:
    return hashlib.sha256(norm_text(text).encode("utf-8")).hexdigest()[:16]

def analyze_df(name, df):
    df = df.copy()
    df["resume_hash"] = df["resume_text"].apply(hash_text)
    df["job_hash"] = df["job_description_text"].apply(hash_text)
    df["pair_hash"] = df["resume_hash"] + "_" + df["job_hash"]
    
    df["norm_resume_hash"] = df["resume_text"].apply(hash_norm_text)
    df["norm_job_hash"] = df["job_description_text"].apply(hash_norm_text)
    df["norm_pair_hash"] = df["norm_resume_hash"] + "_" + df["norm_job_hash"]
    
    unique_r = set(df["resume_hash"])
    unique_j = set(df["job_hash"])
    unique_p = set(df["pair_hash"])
    
    unique_norm_r = set(df["norm_resume_hash"])
    unique_norm_j = set(df["norm_job_hash"])
    unique_norm_p = set(df["norm_pair_hash"])
    
    labels = df["label"].value_counts().to_dict()
    
    return {
        "name": name,
        "rows": len(df),
        "unique_resumes": len(unique_r),
        "unique_jobs": len(unique_j),
        "unique_pairs": len(unique_p),
        "unique_norm_resumes": len(unique_norm_r),
        "unique_norm_jobs": len(unique_norm_j),
        "unique_norm_pairs": len(unique_norm_p),
        "labels": labels,
        "resume_set": unique_r,
        "job_set": unique_j,
        "pair_set": unique_p,
        "norm_resume_set": unique_norm_r,
        "norm_job_set": unique_norm_j,
        "norm_pair_set": unique_norm_p,
    }

def compare_sets(train_info, test_info):
    r_inter = train_info["resume_set"].intersection(test_info["resume_set"])
    j_inter = train_info["job_set"].intersection(test_info["job_set"])
    p_inter = train_info["pair_set"].intersection(test_info["pair_set"])
    
    norm_r_inter = train_info["norm_resume_set"].intersection(test_info["norm_resume_set"])
    norm_j_inter = train_info["norm_job_set"].intersection(test_info["norm_job_set"])
    norm_p_inter = train_info["norm_pair_set"].intersection(test_info["norm_pair_set"])
    
    return {
        "train_name": train_info["name"],
        "eval_name": test_info["name"],
        "eval_rows": test_info["rows"],
        "eval_unique_resumes": test_info["unique_resumes"],
        "eval_unique_jobs": test_info["unique_jobs"],
        "eval_unique_pairs": test_info["unique_pairs"],
        
        "resume_overlap_exact": len(r_inter),
        "resume_overlap_exact_pct": round(len(r_inter) / test_info["unique_resumes"] * 100, 2),
        "job_overlap_exact": len(j_inter),
        "job_overlap_exact_pct": round(len(j_inter) / test_info["unique_jobs"] * 100, 2),
        "pair_overlap_exact": len(p_inter),
        "pair_overlap_exact_pct": round(len(p_inter) / test_info["rows"] * 100, 2),
        
        "resume_overlap_norm": len(norm_r_inter),
        "resume_overlap_norm_pct": round(len(norm_r_inter) / test_info["unique_norm_resumes"] * 100, 2),
        "job_overlap_norm": len(norm_j_inter),
        "job_overlap_norm_pct": round(len(norm_j_inter) / test_info["unique_norm_jobs"] * 100, 2),
        "pair_overlap_norm": len(norm_p_inter),
        "pair_overlap_norm_pct": round(len(norm_p_inter) / test_info["rows"] * 100, 2),
        
        "is_job_disjoint": (len(norm_j_inter) == 0),
        "is_resume_disjoint": (len(norm_r_inter) == 0),
        "is_dual_unseen": (len(norm_r_inter) == 0 and len(norm_j_inter) == 0 and len(norm_p_inter) == 0)
    }

files = {
    "raw_train": ("data/raw/resume_job_fit_train.csv", "csv"),
    "raw_test": ("data/raw/resume_job_fit_test.csv", "csv"),
    "job_train_v1": ("manifests/v1/job_disjoint_train_v1.parquet", "parquet"),
    "job_val_v1": ("manifests/v1/job_disjoint_val_v1.parquet", "parquet"),
    "resume_train_v1": ("manifests/v1/resume_disjoint_train_v1.parquet", "parquet"),
    "resume_val_v1": ("manifests/v1/resume_disjoint_val_v1.parquet", "parquet"),
    "dual_train_v1": ("manifests/v1/dual_unseen_train_v1.parquet", "parquet"),
    "dual_val_v1": ("manifests/v1/dual_unseen_val_v1.parquet", "parquet"),
    "held_out_test_v1": ("manifests/v1/held_out_test_v1.parquet", "parquet"),
}

dfs = {}
infos = {}

for k, (rel_path, fmt) in files.items():
    p = os.path.join(REPO_ROOT, rel_path)
    if fmt == "csv":
        df = pd.read_csv(p)
    else:
        df = pd.read_parquet(p)
    dfs[k] = df
    infos[k] = analyze_df(k, df)
    print(f"Loaded {k}: {infos[k]['rows']} rows, {infos[k]['unique_resumes']} unique resumes, {infos[k]['unique_jobs']} unique jobs")

comparisons = [
    # 1. Original Official Test vs Raw Train
    compare_sets(infos["raw_train"], infos["raw_test"]),
    
    # 2. Job-Disjoint Validation vs Job-Disjoint Train
    compare_sets(infos["job_train_v1"], infos["job_val_v1"]),
    
    # 3. Resume-Disjoint Validation vs Resume-Disjoint Train
    compare_sets(infos["resume_train_v1"], infos["resume_val_v1"]),
    
    # 4. Dual-Unseen Validation vs Dual-Unseen Train
    compare_sets(infos["dual_train_v1"], infos["dual_val_v1"]),
    
    # 5. Held-Out Test V1 vs Job-Disjoint Train V1
    compare_sets(infos["job_train_v1"], infos["held_out_test_v1"]),
    
    # 6. Held-Out Test V1 vs Dual-Unseen Train V1
    compare_sets(infos["dual_train_v1"], infos["held_out_test_v1"]),
    
    # 7. Held-Out Test V1 vs Raw Train
    compare_sets(infos["raw_train"], infos["held_out_test_v1"]),
]

results = {
    "file_summaries": {k: {prop: v[prop] for prop in v if not prop.endswith("_set")} for k, v in infos.items()},
    "comparisons": comparisons
}

os.makedirs(os.path.join(REPO_ROOT, "results", "phase12e3_1"), exist_ok=True)
out_json = os.path.join(REPO_ROOT, "results", "phase12e3_1", "split_id_forensic_results.json")
with open(out_json, "w") as f:
    json.dump(results, f, indent=2)

print("\nSaved detailed results to:", out_json)
for c in comparisons:
    print(f"\n[{c['train_name']} -> {c['eval_name']}]")
    print(f"  Rows: {c['eval_rows']}")
    print(f"  Exact Resume Overlap: {c['resume_overlap_exact']} / {c['eval_unique_resumes']} ({c['resume_overlap_exact_pct']}%)")
    print(f"  Norm Resume Overlap:  {c['resume_overlap_norm']} / {c['eval_unique_resumes']} ({c['resume_overlap_norm_pct']}%)")
    print(f"  Exact Job Overlap:    {c['job_overlap_exact']} / {c['eval_unique_jobs']} ({c['job_overlap_exact_pct']}%)")
    print(f"  Norm Job Overlap:     {c['job_overlap_norm']} / {c['eval_unique_jobs']} ({c['job_overlap_norm_pct']}%)")
    print(f"  Exact Pair Overlap:   {c['pair_overlap_exact']} / {c['eval_rows']} ({c['pair_overlap_exact_pct']}%)")
    print(f"  Dual-Unseen Certified: {c['is_dual_unseen']}")
    print(f"  Job-Disjoint Certified: {c['is_job_disjoint']}")
    print(f"  Resume-Disjoint Certified: {c['is_resume_disjoint']}")
