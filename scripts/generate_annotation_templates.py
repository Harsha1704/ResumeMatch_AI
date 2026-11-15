import os
import pandas as pd

REPO_ROOT = "D:\\skillsync1"
PILOT_CSV = os.path.join(REPO_ROOT, "PHASE12E3_1_PILOT_200_PAIRS.csv")
ANN_A_CSV = os.path.join(REPO_ROOT, "PHASE12E3_1_ANNOTATOR_A_TEMPLATE.csv")
ANN_B_CSV = os.path.join(REPO_ROOT, "PHASE12E3_1_ANNOTATOR_B_TEMPLATE.csv")
ADJUD_CSV = os.path.join(REPO_ROOT, "PHASE12E3_1_ADJUDICATION_TEMPLATE.csv")

pilot_df = pd.read_csv(PILOT_CSV)

# Columns to provide context to annotator
base_cols = [
    "pair_id", "candidate_id", "job_id",
    "candidate_position", "job_position",
    "candidate_exp_years", "job_exp_years_req",
    "candidate_english", "job_english_req",
    "candidate_cv_text", "job_description_text"
]

# Rename candidate_id to resume_id for consistency with prompt
ann_df = pilot_df[base_cols].copy()
ann_df.rename(columns={"candidate_id": "resume_id"}, inplace=True)

# Add blank annotation fields
annotation_fields = [
    "annotation_label",                # No Fit | Potential Fit | Good Fit | Insufficient Evidence
    "mandatory_skill_evidence",        # List of matched mandatory skills
    "preferred_skill_evidence",        # List of matched nice-to-have skills
    "relevant_experience_evidence",    # Summary of relevant roles / tenure
    "essential_requirement_failures",  # Disqualifying missing items / veto triggers
    "transferable_skills",             # Closely related adjacent skills
    "confidence_score",                # 1 (lowest) to 5 (highest)
    "short_justification"              # Brief qualitative explanation
]

for col in annotation_fields:
    ann_df[col] = ""

# For blind review: shuffle Annotator B's presentation order differently so neither annotator
# can discuss "Row 15" or align by position!
ann_a_df = ann_df.copy()
ann_b_df = ann_df.sample(frac=1.0, random_state=101).reset_index(drop=True)

ann_a_df.to_csv(ANN_A_CSV, index=False)
ann_b_df.to_csv(ANN_B_CSV, index=False)
print(f"Created Annotator A Template: {ANN_A_CSV} ({len(ann_a_df)} rows)")
print(f"Created Annotator B Template: {ANN_B_CSV} ({len(ann_b_df)} rows)")

# Adjudication template:
adjud_cols = [
    "pair_id", "resume_id", "job_id",
    "candidate_position", "job_position",
    "candidate_exp_years", "job_exp_years_req",
    "candidate_english", "job_english_req",
    "annotator_a_label",
    "annotator_a_confidence",
    "annotator_a_justification",
    "annotator_b_label",
    "annotator_b_confidence",
    "annotator_b_justification",
    "disagreement_type",               # Exact Match | Minor Disagreement (Potential vs Good) | Major Disagreement (No Fit vs Good Fit) | Insufficient Evidence
    "adjudicated_label",               # No Fit | Potential Fit | Good Fit | Insufficient Evidence
    "adjudicator_confidence",          # 1 to 5
    "adjudication_rationale",          # Binding reason
    "veto_rule_triggered",             # None | Rule 1 (Hard Skill) | Rule 2 (Experience Deficit) | Rule 3 (Language) | Other
    "adjudicated_by",                  # Senior Recruiter ID
    "adjudication_timestamp"           # ISO-8601 string
]

adjud_df = pd.DataFrame(columns=adjud_cols)
# Pre-populate pair identifiers and candidate metadata from pilot
for _, r in pilot_df.iterrows():
    adjud_df.loc[len(adjud_df)] = {
        "pair_id": r["pair_id"],
        "resume_id": r["candidate_id"],
        "job_id": r["job_id"],
        "candidate_position": r["candidate_position"],
        "job_position": r["job_position"],
        "candidate_exp_years": r["candidate_exp_years"],
        "job_exp_years_req": r["job_exp_years_req"],
        "candidate_english": r["candidate_english"],
        "job_english_req": r["job_english_req"],
        "annotator_a_label": "",
        "annotator_a_confidence": "",
        "annotator_a_justification": "",
        "annotator_b_label": "",
        "annotator_b_confidence": "",
        "annotator_b_justification": "",
        "disagreement_type": "",
        "adjudicated_label": "",
        "adjudicator_confidence": "",
        "adjudication_rationale": "",
        "veto_rule_triggered": "",
        "adjudicated_by": "",
        "adjudication_timestamp": ""
    }

adjud_df.to_csv(ADJUD_CSV, index=False)
print(f"Created Adjudication Template: {ADJUD_CSV} ({len(adjud_df)} rows)")
