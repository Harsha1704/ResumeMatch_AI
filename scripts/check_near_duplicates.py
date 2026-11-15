import os
import hashlib
import json
import re
import pandas as pd
import numpy as np

def normalize_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    tokens = text.split()
    return " ".join(tokens)

def check_near_duplicates(df_a, df_b, col_name, threshold=0.9):
    # Normalized text check
    norm_a = set(df_a[col_name].apply(normalize_text))
    norm_b = set(df_b[col_name].apply(normalize_text))
    exact_norm_overlap = norm_a.intersection(norm_b)
    
    # 3-gram Jaccard check on a sample if distinct
    print(f"Near-duplicate audit on '{col_name}':")
    print(f"  Exact normalized overlap: {len(exact_norm_overlap)} / {len(norm_b)}")
    return len(exact_norm_overlap)

raw_train = pd.read_csv("data/raw/resume_job_fit_train.csv")
raw_test = pd.read_csv("data/raw/resume_job_fit_test.csv")

print("Checking Raw Train vs Raw Test jobs:")
check_near_duplicates(raw_train, raw_test, "job_description_text")

print("\nChecking Raw Train vs Raw Test resumes:")
check_near_duplicates(raw_train, raw_test, "resume_text")

p_dual_tr = pd.read_parquet("manifests/v1/dual_unseen_train_v1.parquet")
p_dual_vl = pd.read_parquet("manifests/v1/dual_unseen_val_v1.parquet")

print("\nChecking Dual-Unseen Train vs Val jobs:")
check_near_duplicates(p_dual_tr, p_dual_vl, "job_description_text")

print("\nChecking Dual-Unseen Train vs Val resumes:")
check_near_duplicates(p_dual_tr, p_dual_vl, "resume_text")
