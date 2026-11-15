import pandas as pd
from pathlib import Path

DJINNI_DIR = Path("data/external/djinni")
cv_path = DJINNI_DIR / "djinni_candidate_profiles_english.parquet"
jd_path = DJINNI_DIR / "djinni_job_descriptions_english.parquet"

cv_df = pd.read_parquet(cv_path)
jd_df = pd.read_parquet(jd_path)

print("CV shape:", cv_df.shape)
print("CV columns:", cv_df.columns.tolist())
print("JD shape:", jd_df.shape)
print("JD columns:", jd_df.columns.tolist())
print("CV sample head:", cv_df.head(1).to_dict(orient="records"))
