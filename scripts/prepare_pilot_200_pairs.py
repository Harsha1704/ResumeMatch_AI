import os
import pandas as pd
import numpy as np

REPO_ROOT = "D:\\skillsync1"
INPUT_CSV = os.path.join(REPO_ROOT, "data", "external", "djinni", "proposed_candidate_pairs_sample.csv")
PILOT_CSV = os.path.join(REPO_ROOT, "PHASE12E3_1_PILOT_200_PAIRS.csv")
RESTRICTED_META_CSV = os.path.join(REPO_ROOT, "PHASE12E3_1_PILOT_200_RESTRICTED_METADATA.csv")

df = pd.read_csv(INPUT_CSV)
print(f"Loaded input proposed pool: {len(df)} rows")
print("Stratum breakdown in 830 pool:")
print(df["stratum_type"].value_counts())

# Stratified allocation to achieve exactly 200 pairs:
# High Alignment: 86
# Borderline Runner-Up: 56
# Cross-Domain Negative: 58
# Total: 200

# Sub-stratify within each stratum by domain_keyword to ensure domain balance
def stratified_sample(sub_df, n_samples, random_state=42):
    # Proportional sampling across domain_keywords within stratum
    domains = sub_df["domain_keyword"].value_counts()
    sampled = []
    
    # Calculate base per domain
    per_domain = n_samples // len(domains)
    remainder = n_samples % len(domains)
    
    rng = np.random.RandomState(random_state)
    
    # Sort domains for deterministic ordering
    sorted_domains = sorted(domains.index.tolist())
    for i, dom in enumerate(sorted_domains):
        dom_df = sub_df[sub_df["domain_keyword"] == dom]
        n_to_take = per_domain + (1 if i < remainder else 0)
        n_to_take = min(n_to_take, len(dom_df))
        s = dom_df.sample(n=n_to_take, random_state=random_state)
        sampled.append(s)
    
    res = pd.concat(sampled, ignore_index=True)
    if len(res) < n_samples:
        missing = n_samples - len(res)
        remaining = sub_df[~sub_df["pair_id"].isin(res["pair_id"])]
        fill = remaining.sample(n=missing, random_state=random_state)
        res = pd.concat([res, fill], ignore_index=True)
    elif len(res) > n_samples:
        res = res.sample(n=n_samples, random_state=random_state)
    return res

high_df = df[df["stratum_type"] == "HIGH_ALIGNMENT_PROPOSAL"]
border_df = df[df["stratum_type"] == "BORDERLINE_RUNNER_UP_PROPOSAL"]
cross_df = df[df["stratum_type"] == "CROSS_DOMAIN_NEGATIVE_CONTROL"]

sampled_high = stratified_sample(high_df, 86, random_state=42)
sampled_border = stratified_sample(border_df, 56, random_state=42)
sampled_cross = stratified_sample(cross_df, 58, random_state=42)

pilot_df = pd.concat([sampled_high, sampled_border, sampled_cross], ignore_index=True)

# Randomize the presentation order so annotators cannot guess strata by ordering!
pilot_df_shuffled = pilot_df.sample(frac=1.0, random_state=2026).reset_index(drop=True)

print("\nSampled 200 pairs stratum breakdown:")
print(pilot_df_shuffled["stratum_type"].value_counts())
print("\nSampled 200 pairs domain breakdown:")
print(pilot_df_shuffled["domain_keyword"].value_counts())

# Save restricted metadata with heuristic stratum labels and proposed tags
meta_cols = [
    "pair_id", "candidate_id", "job_id", "domain_keyword", "stratum_type",
    "candidate_position", "job_position", "candidate_exp_years", "job_exp_years_req",
    "candidate_english", "job_english_req"
]
pilot_df_shuffled[meta_cols].to_csv(RESTRICTED_META_CSV, index=False)
print(f"\nSaved restricted metadata to: {RESTRICTED_META_CSV}")

# Clean pilot dataset: do NOT expose heuristic proposal stratum to annotators!
# Present candidate and job texts and objective metadata
pilot_cols = [
    "pair_id", "candidate_id", "job_id",
    "candidate_position", "job_position",
    "candidate_exp_years", "job_exp_years_req",
    "candidate_english", "job_english_req",
    "candidate_cv_text", "job_description_text"
]
pilot_df_shuffled[pilot_cols].to_csv(PILOT_CSV, index=False)
print(f"Saved unblinded pilot dataset to: {PILOT_CSV}")
