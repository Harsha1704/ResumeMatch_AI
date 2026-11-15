import pandas as pd

df = pd.read_csv("data/external/djinni/proposed_candidate_pairs_sample.csv")
print("Columns:", df.columns.tolist())
print("Shape:", df.shape)
for col in df.columns:
    if col not in ["resume_text", "job_description_text", "notes"]:
        print(f"Value counts for {col}:")
        print(df[col].value_counts(dropna=False).head(10))
        print()
print("Sample head(2):")
print(df.drop(columns=["resume_text", "job_description_text"], errors="ignore").head(2))
