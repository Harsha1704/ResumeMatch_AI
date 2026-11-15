"""
scripts/audit_phase12e_deliverables.py
Audits the actual deliverables, files, checksums, and proposed pairs from Phase 12E-1 and 12E-2.
"""

import json
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path

REPO_ROOT = Path(".")

def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1048576):
            h.update(chunk)
    return h.hexdigest()

FILES_TO_CHECK = {
    "djinni_cv": Path("data/external/djinni/djinni_candidate_profiles_english.parquet"),
    "djinni_jd": Path("data/external/djinni/djinni_job_descriptions_english.parquet"),
    "proposed_pairs": Path("data/external/djinni/proposed_candidate_pairs_sample.csv"),
    "annotation_template": Path("PHASE12E2_PAIR_ANNOTATION_TEMPLATE.csv"),
    "core_train": Path("data/raw/resume_job_fit_train.csv"),
    "core_test": Path("data/raw/resume_job_fit_test.csv"),
    "manifest_json": Path("PHASE12E1_DATASET_MANIFEST.json"),
    "production_model": Path("models/best_model.joblib")
}

print("=" * 80)
print("PHASE 12E-3: DELIVERABLE AUDIT & CRYPTOGRAPHIC VERIFICATION")
print("=" * 80)

# 1. Check file existence and SHA-256
actual_checksums = {}
for name, p in FILES_TO_CHECK.items():
    if not p.exists():
        print(f"[ERROR] Missing file: {p}")
        continue
    sz = p.stat().st_size
    sha = compute_sha256(p)
    actual_checksums[name] = {"path": str(p), "size_bytes": sz, "sha256": sha}
    print(f"File: {str(p):<65} | Size: {sz:>11,} bytes | SHA: {sha[:16]}...")

# 2. Compare against manifest
print("\n" + "=" * 60)
print("COMPARING AGAINST PHASE12E1_DATASET_MANIFEST.JSON")
print("=" * 60)

with open(FILES_TO_CHECK["manifest_json"], "r", encoding="utf-8") as f:
    manifest = json.load(f)

discrepancies = []

# Check CV
manifest_cv_sha = manifest["external_djinni_sources"]["candidate_profiles"]["sha256"]
actual_cv_sha = actual_checksums["djinni_cv"]["sha256"]
if manifest_cv_sha == actual_cv_sha:
    print("  [PASS] Djinni CV Parquet SHA-256 matches manifest.")
else:
    discrepancies.append(f"Djinni CV SHA mismatch: manifest={manifest_cv_sha}, actual={actual_cv_sha}")

# Check JD
manifest_jd_sha = manifest["external_djinni_sources"]["job_descriptions"]["sha256"]
actual_jd_sha = actual_checksums["djinni_jd"]["sha256"]
if manifest_jd_sha == actual_jd_sha:
    print("  [PASS] Djinni JD Parquet SHA-256 matches manifest.")
else:
    discrepancies.append(f"Djinni JD SHA mismatch: manifest={manifest_jd_sha}, actual={actual_jd_sha}")

# Check Proposed Pairs
manifest_prop_sha = manifest["pairing_and_labeling_status"]["proposed_pairs_pool"]["sha256"]
actual_prop_sha = actual_checksums["proposed_pairs"]["sha256"]
if manifest_prop_sha == actual_prop_sha:
    print("  [PASS] Proposed pairs sample CSV SHA-256 matches manifest.")
else:
    discrepancies.append(f"Proposed pairs SHA mismatch: manifest={manifest_prop_sha}, actual={actual_prop_sha}")

# Check Template
manifest_tpl_sha = manifest["pairing_and_labeling_status"]["annotation_template"]["sha256"]
actual_tpl_sha = actual_checksums["annotation_template"]["sha256"]
if manifest_tpl_sha == actual_tpl_sha:
    print("  [PASS] Annotation template CSV SHA-256 matches manifest.")
else:
    discrepancies.append(f"Annotation template SHA mismatch: manifest={manifest_tpl_sha}, actual={actual_tpl_sha}")

# Check Core Train & Test
manifest_tr_sha = manifest["core_anchor_dataset"]["train_split"]["sha256"]
actual_tr_sha = actual_checksums["core_train"]["sha256"]
if manifest_tr_sha == actual_tr_sha:
    print("  [PASS] Core train CSV SHA-256 matches manifest.")
else:
    discrepancies.append(f"Core train SHA mismatch: manifest={manifest_tr_sha}, actual={actual_tr_sha}")

manifest_te_sha = manifest["core_anchor_dataset"]["held_out_test_split"]["sha256"]
actual_te_sha = actual_checksums["core_test"]["sha256"]
if manifest_te_sha == actual_te_sha:
    print("  [PASS] Core test CSV SHA-256 matches manifest.")
else:
    discrepancies.append(f"Core test SHA mismatch: manifest={manifest_te_sha}, actual={actual_te_sha}")

# Check Production Checkpoint
manifest_prod_sha = manifest["primary_production_checkpoint"]["sha256"].upper()
actual_prod_sha = actual_checksums["production_model"]["sha256"].upper()
if manifest_prod_sha == actual_prod_sha:
    print("  [PASS] Production model SHA-256 matches manifest exactly.")
else:
    discrepancies.append(f"Production model SHA mismatch: manifest={manifest_prod_sha}, actual={actual_prod_sha}")

print(f"\nTotal Cryptographic Discrepancies Found: {len(discrepancies)}")
for d in discrepancies:
    print("  [DISCREPANCY]", d)

# 3. Audit of the 830 proposed pairs in proposed_candidate_pairs_sample.csv
print("\n" + "=" * 60)
print("AUDIT OF 830 PROPOSED PAIRS (PROPOSAL SAMPLE)")
print("=" * 60)
df_prop = pd.read_csv(FILES_TO_CHECK["proposed_pairs"])
print(f"Total rows in proposed pairs: {len(df_prop)}")
print(f"Unique pair_ids: {df_prop['pair_id'].nunique()}")
print(f"Unique candidate_ids: {df_prop['candidate_id'].nunique()}")
print(f"Unique job_ids: {df_prop['job_id'].nunique()}")
print("\nStratum distribution in proposed pairs:")
print(df_prop["stratum_type"].value_counts())
print("\nDomain keyword distribution in proposed pairs:")
print(df_prop["domain_keyword"].value_counts().head(10))

# Check whether any labels are populated
label_cols = ["annotator_1_label", "annotator_2_label", "adjudicated_label"]
for c in label_cols:
    populated = df_prop[c].dropna().apply(lambda x: str(x).strip()).replace("", np.nan).dropna()
    print(f"Populated labels in column '{c}': {len(populated)} / {len(df_prop)}")

# 4. Audit of the 50-row annotation template
print("\n" + "=" * 60)
print("AUDIT OF 50-ROW ANNOTATION TEMPLATE")
print("=" * 60)
df_tpl = pd.read_csv(FILES_TO_CHECK["annotation_template"])
print(f"Rows in template: {len(df_tpl)}")
print("Columns in template:", df_tpl.columns.tolist())
for c in label_cols:
    populated = df_tpl[c].dropna().apply(lambda x: str(x).strip()).replace("", np.nan).dropna()
    print(f"Populated labels in template column '{c}': {len(populated)} / {len(df_tpl)}")
