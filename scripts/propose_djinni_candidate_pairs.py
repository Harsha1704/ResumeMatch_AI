"""
scripts/propose_djinni_candidate_pairs.py
Generates reproducible, stratified candidate pairs from Djinni English CVs and Job Descriptions
for research annotation. Does NOT automatically assign ground-truth labels.
"""

import os
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path

CV_PATH = Path("data/external/djinni/djinni_candidate_profiles_english.parquet")
JD_PATH = Path("data/external/djinni/djinni_job_descriptions_english.parquet")
OUT_DIR = Path("data/external/djinni")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_jd_exp_min(exp_str):
    if not isinstance(exp_str, str):
        return 0.0
    s = exp_str.lower().strip()
    if "no_exp" in s or "0" in s:
        return 0.0
    if "1" in s:
        return 1.0
    if "2" in s:
        return 2.0
    if "3" in s:
        return 3.0
    if "5" in s:
        return 5.0
    return 0.0


def main():
    print("=" * 80)
    print("PROPOSING STRATIFIED CANDIDATE-JOB PAIRS FOR ANNOTATION")
    print("=" * 80)

    print("Loading Djinni datasets...")
    df_cv = pd.read_parquet(CV_PATH)
    df_jd = pd.read_parquet(JD_PATH)

    # Focus on top representative tech domains to maximize annotation density
    target_keywords = ["Python", "JavaScript", "Java", "DevOps", ".NET", "QA Automation"]
    print(f"Filtering to target domains: {target_keywords}")

    cv_sub = df_cv[df_cv["Primary Keyword"].isin(target_keywords)].copy()
    jd_sub = df_jd[df_jd["Primary Keyword"].isin(target_keywords)].copy()

    print(f"  Available CVs in target domains: {len(cv_sub):,}")
    print(f"  Available JDs in target domains: {len(jd_sub):,}")

    # Set deterministic random seed
    rng = np.random.RandomState(42)

    # Sample 100 representative JDs (balanced across the 6 keywords)
    sample_jds = []
    for kw in target_keywords:
        kw_jds = jd_sub[jd_sub["Primary Keyword"] == kw]
        sample_jds.append(kw_jds.sample(min(20, len(kw_jds)), random_state=42))
    sample_jds_df = pd.concat(sample_jds, ignore_index=True)
    print(f"Selected {len(sample_jds_df)} benchmark Job Descriptions.")

    proposed_pairs = []

    for _, jd in sample_jds_df.iterrows():
        jd_id = jd["id"]
        jd_kw = jd["Primary Keyword"]
        jd_pos = jd["Position"]
        jd_desc = jd["Long Description"]
        jd_exp_min = parse_jd_exp_min(jd["Exp Years"])
        jd_eng = str(jd.get("English Level", "None"))

        # 1. Stratum A: Same Keyword, High Experience Match (Likely Candidate for Good Fit / Potential Fit)
        cv_match_kw = cv_sub[cv_sub["Primary Keyword"] == jd_kw]
        cand_high_exp = cv_match_kw[cv_match_kw["Experience Years"] >= jd_exp_min]
        if len(cand_high_exp) > 0:
            for _, cv in cand_high_exp.sample(min(3, len(cand_high_exp)), random_state=42).iterrows():
                pair_id = hashlib.sha256(f"{cv['id']}_{jd_id}".encode()).hexdigest()[:16]
                proposed_pairs.append({
                    "pair_id": pair_id,
                    "candidate_id": cv["id"],
                    "job_id": jd_id,
                    "domain_keyword": jd_kw,
                    "stratum_type": "HIGH_ALIGNMENT_PROPOSAL",
                    "candidate_position": cv["Position"],
                    "job_position": jd_pos,
                    "candidate_exp_years": cv["Experience Years"],
                    "job_exp_years_req": jd["Exp Years"],
                    "candidate_english": cv["English Level"],
                    "job_english_req": jd_eng,
                    "candidate_cv_text": cv["CV"],
                    "job_description_text": jd_desc,
                    "annotator_1_label": "",
                    "annotator_1_evidence": "",
                    "annotator_2_label": "",
                    "annotator_2_evidence": "",
                    "adjudicated_label": "",
                    "adjudication_notes": ""
                })

        # 2. Stratum B: Same Keyword, Lower Experience (Potential Fit or Hard-Negative Candidate / Runner-Up)
        cand_low_exp = cv_match_kw[cv_match_kw["Experience Years"] < jd_exp_min]
        if len(cand_low_exp) > 0:
            for _, cv in cand_low_exp.sample(min(2, len(cand_low_exp)), random_state=42).iterrows():
                pair_id = hashlib.sha256(f"{cv['id']}_{jd_id}".encode()).hexdigest()[:16]
                proposed_pairs.append({
                    "pair_id": pair_id,
                    "candidate_id": cv["id"],
                    "job_id": jd_id,
                    "domain_keyword": jd_kw,
                    "stratum_type": "BORDERLINE_RUNNER_UP_PROPOSAL",
                    "candidate_position": cv["Position"],
                    "job_position": jd_pos,
                    "candidate_exp_years": cv["Experience Years"],
                    "job_exp_years_req": jd["Exp Years"],
                    "candidate_english": cv["English Level"],
                    "job_english_req": jd_eng,
                    "candidate_cv_text": cv["CV"],
                    "job_description_text": jd_desc,
                    "annotator_1_label": "",
                    "annotator_1_evidence": "",
                    "annotator_2_label": "",
                    "annotator_2_evidence": "",
                    "adjudicated_label": "",
                    "adjudication_notes": ""
                })

        # 3. Stratum C: Different Domain Keyword (Definite Negative / No Fit Control)
        cv_diff_kw = cv_sub[cv_sub["Primary Keyword"] != jd_kw]
        if len(cv_diff_kw) > 0:
            for _, cv in cv_diff_kw.sample(min(2, len(cv_diff_kw)), random_state=42).iterrows():
                pair_id = hashlib.sha256(f"{cv['id']}_{jd_id}".encode()).hexdigest()[:16]
                proposed_pairs.append({
                    "pair_id": pair_id,
                    "candidate_id": cv["id"],
                    "job_id": jd_id,
                    "domain_keyword": f"{jd_kw}_vs_{cv['Primary Keyword']}",
                    "stratum_type": "CROSS_DOMAIN_NEGATIVE_CONTROL",
                    "candidate_position": cv["Position"],
                    "job_position": jd_pos,
                    "candidate_exp_years": cv["Experience Years"],
                    "job_exp_years_req": jd["Exp Years"],
                    "candidate_english": cv["English Level"],
                    "job_english_req": jd_eng,
                    "candidate_cv_text": cv["CV"],
                    "job_description_text": jd_desc,
                    "annotator_1_label": "",
                    "annotator_1_evidence": "",
                    "annotator_2_label": "",
                    "annotator_2_evidence": "",
                    "adjudicated_label": "",
                    "adjudication_notes": ""
                })

    df_pairs = pd.DataFrame(proposed_pairs)
    print(f"\nGenerated {len(df_pairs)} proposed pairs across {len(sample_jds_df)} jobs.")
    print("Stratum breakdown:\n", df_pairs["stratum_type"].value_counts())

    out_csv = OUT_DIR / "proposed_candidate_pairs_sample.csv"
    df_pairs.to_csv(out_csv, index=False)
    print(f"Saved proposed pairs to: {out_csv} ({out_csv.stat().st_size:,} bytes)")

    # Also create the required Deliverable 5: PHASE12E2_PAIR_ANNOTATION_TEMPLATE.csv
    template_path = Path("PHASE12E2_PAIR_ANNOTATION_TEMPLATE.csv")
    df_pairs.head(50).to_csv(template_path, index=False)
    print(f"Created annotation template: {template_path} (Sample N=50)")

    print("=" * 80)


if __name__ == "__main__":
    main()
