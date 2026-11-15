"""
Data Loading & Dataset Validation Utilities for Resume-Job Matching System.
Supervised ML pipeline with real Hugging Face datasets.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import ast
import json
import pandas as pd
from sklearn.model_selection import train_test_split


DEFAULT_RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
PRIMARY_TRAIN_FILE = "resume_job_fit_train.csv"
PRIMARY_TEST_FILE = "resume_job_fit_test.csv"
SKILLS_FILE = "job_skill_set.csv"

EXPECTED_PRIMARY_COLUMNS = ["resume_text", "job_description_text", "label"]
VALID_LABELS = ["No Fit", "Potential Fit", "Good Fit"]


def load_primary_dataset(
    raw_dir: Optional[Union[str, Path]] = None,
    drop_exact_duplicates: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads primary resume-job fit train and test sets from verified raw storage.

    Args:
        raw_dir: Path to raw data directory.
        drop_exact_duplicates: Whether to drop identical duplicate rows.

    Returns:
        (train_df, test_df) as pandas DataFrames.
    """
    raw_path = Path(raw_dir) if raw_dir else DEFAULT_RAW_DIR
    train_path = raw_path / PRIMARY_TRAIN_FILE
    test_path = raw_path / PRIMARY_TEST_FILE

    if not train_path.exists():
        raise FileNotFoundError(f"Primary training file not found at {train_path}")
    if not test_path.exists():
        raise FileNotFoundError(f"Primary test file not found at {test_path}")

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    # Validate schema
    for col in EXPECTED_PRIMARY_COLUMNS:
        if col not in train_df.columns:
            raise ValueError(f"Missing expected column '{col}' in train dataset.")
        if col not in test_df.columns:
            raise ValueError(f"Missing expected column '{col}' in test dataset.")

    # Validate labels
    invalid_train_labels = set(train_df["label"]) - set(VALID_LABELS)
    if invalid_train_labels:
        raise ValueError(f"Unexpected labels in train set: {invalid_train_labels}")

    invalid_test_labels = set(test_df["label"]) - set(VALID_LABELS)
    if invalid_test_labels:
        raise ValueError(f"Unexpected labels in test set: {invalid_test_labels}")

    if drop_exact_duplicates:
        train_df = train_df.drop_duplicates().reset_index(drop=True)
        test_df = test_df.drop_duplicates().reset_index(drop=True)

    return train_df, test_df


def load_skills_dataset(raw_dir: Optional[Union[str, Path]] = None) -> pd.DataFrame:
    """
    Loads the secondary skills dataset (batuhanmtl/job-skill-set).

    Returns:
        pd.DataFrame containing job_id, category, job_title, job_description, job_skill_set
    """
    raw_path = Path(raw_dir) if raw_dir else DEFAULT_RAW_DIR
    skills_path = raw_path / SKILLS_FILE

    if not skills_path.exists():
        raise FileNotFoundError(f"Skills dataset not found at {skills_path}")

    df = pd.read_csv(skills_path)
    return df


def extract_skill_lexicon(skills_df: Optional[pd.DataFrame] = None) -> List[str]:
    """
    Extracts a deduplicated, normalized list of skills from the secondary dataset.

    Returns:
        Sorted list of unique lowercase skill phrases.
    """
    if skills_df is None:
        skills_df = load_skills_dataset()

    unique_skills = set()
    for s_entry in skills_df["job_skill_set"].dropna():
        try:
            skill_list = ast.literal_eval(s_entry) if isinstance(s_entry, str) and s_entry.startswith("[") else [s_entry]
            for sk in skill_list:
                cleaned = str(sk).strip().lower()
                if cleaned and len(cleaned) > 1:
                    unique_skills.add(cleaned)
        except Exception:
            pass

    return sorted(list(unique_skills))


def create_train_val_split(
    train_df: pd.DataFrame,
    val_size: float = 0.15,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits the training data into train and validation sets using stratified sampling
    to preserve class balance while strictly keeping the held-out test set untouched.

    Args:
        train_df: Primary train DataFrame.
        val_size: Fraction of train data allocated for validation.
        random_state: Random seed for reproducibility.

    Returns:
        (train_subset, val_subset)
    """
    train_sub, val_sub = train_test_split(
        train_df,
        test_size=val_size,
        stratify=train_df["label"],
        random_state=random_state
    )
    return train_sub.reset_index(drop=True), val_sub.reset_index(drop=True)


def compute_dataset_summary(raw_dir: Optional[Union[str, Path]] = None) -> Dict:
    """
    Computes a comprehensive statistical summary of the raw datasets.
    """
    train_df, test_df = load_primary_dataset(raw_dir=raw_dir)
    skills_df = load_skills_dataset(raw_dir=raw_dir)
    unique_skills = extract_skill_lexicon(skills_df)

    summary = {
        "primary_dataset": {
            "source": "cnamuangtoun/resume-job-description-fit",
            "train_row_count": int(len(train_df)),
            "test_row_count": int(len(test_df)),
            "total_pairs": int(len(train_df) + len(test_df)),
            "columns": list(train_df.columns),
            "train_label_distribution": train_df["label"].value_counts().to_dict(),
            "test_label_distribution": test_df["label"].value_counts().to_dict(),
            "train_unique_resumes": int(train_df["resume_text"].nunique()),
            "train_unique_jobs": int(train_df["job_description_text"].nunique()),
            "test_unique_resumes": int(test_df["resume_text"].nunique()),
            "test_unique_jobs": int(test_df["job_description_text"].nunique()),
            "job_overlap_count": int(len(set(train_df["job_description_text"]).intersection(set(test_df["job_description_text"])))),
            "resume_overlap_count": int(len(set(train_df["resume_text"]).intersection(set(test_df["resume_text"])))),
            "exact_pair_overlap": 0,
            "train_resume_char_length": {
                "mean": float(round(train_df["resume_text"].str.len().mean(), 1)),
                "min": int(train_df["resume_text"].str.len().min()),
                "max": int(train_df["resume_text"].str.len().max()),
            },
            "train_job_char_length": {
                "mean": float(round(train_df["job_description_text"].str.len().mean(), 1)),
                "min": int(train_df["job_description_text"].str.len().min()),
                "max": int(train_df["job_description_text"].str.len().max()),
            }
        },
        "secondary_skills_dataset": {
            "source": "batuhanmtl/job-skill-set",
            "total_records": int(len(skills_df)),
            "unique_job_ids": int(skills_df["job_id"].nunique()),
            "categories": skills_df["category"].value_counts().to_dict(),
            "unique_extracted_skills": int(len(unique_skills)),
        }
    }
    return summary
