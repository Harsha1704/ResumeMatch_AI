"""
scripts/audit_djinni_raw.py
Deep forensic audit of the downloaded Djinni English Candidate Profiles and Job Descriptions.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

CV_PATH = Path("data/external/djinni/djinni_candidate_profiles_english.parquet")
JD_PATH = Path("data/external/djinni/djinni_job_descriptions_english.parquet")

print("=" * 80)
print("DJINNI DATASET DEEP FORENSIC AUDIT")
print("=" * 80)

# 1. Load Parquet files
print("\n[1] Loading Candidate Profiles...")
df_cv = pd.read_parquet(CV_PATH)
print(f"  Rows loaded: {len(df_cv):,}")
print(f"  Columns: {df_cv.columns.tolist()}")

print("\n[2] Loading Job Descriptions...")
df_jd = pd.read_parquet(JD_PATH)
print(f"  Rows loaded: {len(df_jd):,}")
print(f"  Columns: {df_jd.columns.tolist()}")

# 2. Null Value Analysis
print("\n" + "=" * 60)
print("NULL / MISSING VALUE ANALYSIS")
print("=" * 60)
print("\n--- Candidate Profiles Nulls ---")
for col in df_cv.columns:
    null_cnt = df_cv[col].isnull().sum()
    pct = (null_cnt / len(df_cv)) * 100
    print(f"  {col:<20}: {null_cnt:>7,} nulls ({pct:>5.2f}%)")

print("\n--- Job Descriptions Nulls ---")
for col in df_jd.columns:
    null_cnt = df_jd[col].isnull().sum()
    pct = (null_cnt / len(df_jd)) * 100
    print(f"  {col:<20}: {null_cnt:>7,} nulls ({pct:>5.2f}%)")

# 3. Uniqueness and Identifiers
print("\n" + "=" * 60)
print("UNIQUENESS & IDENTIFIER ANALYSIS")
print("=" * 60)
print(f"CV unique IDs: {df_cv['id'].nunique():,} / {len(df_cv):,}")
print(f"JD unique IDs: {df_jd['id'].nunique():,} / {len(df_jd):,}")

# Check text uniqueness
cv_text_col = "CV" if "CV" in df_cv.columns else "Moreinfo"
jd_text_col = "Long Description" if "Long Description" in df_jd.columns else "Description"

print(f"CV unique full text ({cv_text_col}): {df_cv[cv_text_col].nunique():,}")
print(f"JD unique full text ({jd_text_col}): {df_jd[jd_text_col].nunique():,}")

# 4. Check whether any shared ID or foreign key exists
print("\n" + "=" * 60)
print("CRITICAL PAIRING AUDIT: IS THERE A FOREIGN KEY?")
print("=" * 60)
cv_ids = set(df_cv["id"].dropna())
jd_ids = set(df_jd["id"].dropna())
shared_ids = cv_ids.intersection(jd_ids)
print(f"Intersection of CV IDs and JD IDs: {len(shared_ids)}")

# Check column names for candidate/job pairing indicators
print("Checking for pairing/application columns...")
cv_pair_cols = [c for c in df_cv.columns if any(k in c.lower() for k in ["job", "apply", "hire", "app", "match", "pair"])]
jd_pair_cols = [c for c in df_jd.columns if any(k in c.lower() for k in ["candidate", "cv", "resume", "apply", "hire", "match", "pair"])]
print(f"  Pairing columns in CV table: {cv_pair_cols}")
print(f"  Pairing columns in JD table: {jd_pair_cols}")

# 5. Language consistency
print("\n" + "=" * 60)
print("LANGUAGE CONSISTENCY ANALYSIS")
print("=" * 60)
if "CV_lang" in df_cv.columns:
    print("CV Languages:\n", df_cv["CV_lang"].value_counts(dropna=False).head(10))
if "Long Description_lang" in df_jd.columns:
    print("\nJD Languages:\n", df_jd["Long Description_lang"].value_counts(dropna=False).head(10))

# 6. Job Category & Keywords Analysis
print("\n" + "=" * 60)
print("JOB CATEGORIES & KEYWORDS")
print("=" * 60)
if "Primary Keyword" in df_cv.columns:
    print("\nTop 15 CV Primary Keywords:\n", df_cv["Primary Keyword"].value_counts(dropna=False).head(15))
if "Primary Keyword" in df_jd.columns:
    print("\nTop 15 JD Primary Keywords:\n", df_jd["Primary Keyword"].value_counts(dropna=False).head(15))

# Keyword intersection
cv_keywords = set(df_cv["Primary Keyword"].dropna().str.lower())
jd_keywords = set(df_jd["Primary Keyword"].dropna().str.lower())
shared_kw = cv_keywords.intersection(jd_keywords)
print(f"\nUnique CV Keywords: {len(cv_keywords)}, Unique JD Keywords: {len(jd_keywords)}")
print(f"Shared Primary Keywords: {len(shared_kw)} ({len(shared_kw)/max(len(cv_keywords),1)*100:.1f}%)")

# 7. Experience Distribution
print("\n" + "=" * 60)
print("EXPERIENCE DISTRIBUTION")
print("=" * 60)
if "Experience Years" in df_cv.columns:
    exp_cv = df_cv["Experience Years"].dropna()
    print("CV Experience Years:")
    print(f"  min={exp_cv.min()}, med={exp_cv.median()}, mean={exp_cv.mean():.2f}, p75={exp_cv.quantile(0.75)}, p95={exp_cv.quantile(0.95)}, max={exp_cv.max()}")

if "Exp Years" in df_jd.columns:
    print("\nJD Exp Years values (sample counts):")
    print(df_jd["Exp Years"].value_counts(dropna=False).head(10))

# 8. English Level Distribution
print("\n" + "=" * 60)
print("ENGLISH LEVEL DISTRIBUTION")
print("=" * 60)
if "English Level" in df_cv.columns:
    print("CV English Level:\n", df_cv["English Level"].value_counts(dropna=False))
if "English Level" in df_jd.columns:
    print("\nJD English Level:\n", df_jd["English Level"].value_counts(dropna=False))

# 9. Text Length Profiling
print("\n" + "=" * 60)
print("TEXT LENGTH PROFILING (WORDS & CHARACTERS)")
print("=" * 60)
cv_texts = df_cv[cv_text_col].dropna().astype(str)
jd_texts = df_jd[jd_text_col].dropna().astype(str)

cv_words = cv_texts.apply(lambda x: len(x.split()))
jd_words = jd_texts.apply(lambda x: len(x.split()))

print("Candidate CVs (Words):")
print(f"  min={cv_words.min()}, p25={cv_words.quantile(0.25):.0f}, med={cv_words.median():.0f}, mean={cv_words.mean():.1f}, p75={cv_words.quantile(0.75):.0f}, p95={cv_words.quantile(0.95):.0f}, max={cv_words.max()}")

print("\nJob Descriptions (Words):")
print(f"  min={jd_words.min()}, p25={jd_words.quantile(0.25):.0f}, med={jd_words.median():.0f}, mean={jd_words.mean():.1f}, p75={jd_words.quantile(0.75):.0f}, p95={jd_words.quantile(0.95):.0f}, max={jd_words.max()}")
