"""Phase 1 regression tests for primary dataset integrity and reconciliation."""

import pandas as pd
import pytest

from src.utils.data_loader import load_primary_dataset, compute_dataset_summary


def _write_primary_files(raw_dir, train_rows, test_rows):
    pd.DataFrame(train_rows, columns=["resume_text", "job_description_text", "label"]).to_csv(
        raw_dir / "resume_job_fit_train.csv", index=False
    )
    pd.DataFrame(test_rows, columns=["resume_text", "job_description_text", "label"]).to_csv(
        raw_dir / "resume_job_fit_test.csv", index=False
    )


def test_primary_loader_removes_only_exact_duplicate_rows(tmp_path):
    train = [
        ("Resume A Python developer", "Job A Python engineer", "Good Fit"),
        ("Resume A Python developer", "Job A Python engineer", "Good Fit"),
        ("Resume B Java developer", "Job B Java engineer", "Potential Fit"),
    ]
    test = [("Resume C SQL developer", "Job C SQL engineer", "No Fit")]
    _write_primary_files(tmp_path, train, test)

    train_df, test_df = load_primary_dataset(raw_dir=tmp_path)

    assert len(train_df) == 2
    assert len(test_df) == 1
    assert not train_df.duplicated().any()


@pytest.mark.parametrize(
    "bad_value",
    [None, ""],
)
def test_primary_loader_rejects_missing_or_blank_text(tmp_path, bad_value):
    train = [
        (bad_value, "Job A Python engineer", "Good Fit"),
        ("Resume B Java developer", "Job B Java engineer", "Potential Fit"),
    ]
    test = [("Resume C SQL developer", "Job C SQL engineer", "No Fit")]
    _write_primary_files(tmp_path, train, test)

    with pytest.raises(ValueError, match="missing/blank required values"):
        load_primary_dataset(raw_dir=tmp_path)


def test_primary_loader_rejects_null_labels(tmp_path):
    train = [
        ("Resume A Python developer", "Job A Python engineer", None),
        ("Resume B Java developer", "Job B Java engineer", "Potential Fit"),
    ]
    test = [("Resume C SQL developer", "Job C SQL engineer", "No Fit")]
    _write_primary_files(tmp_path, train, test)

    with pytest.raises(ValueError, match="missing/blank required values"):
        load_primary_dataset(raw_dir=tmp_path)


def test_dataset_summary_reconciles_raw_and_verified_counts(tmp_path):
    train = [
        ("Resume A Python developer", "Job A Python engineer", "Good Fit"),
        ("Resume A Python developer", "Job A Python engineer", "Good Fit"),
        ("Resume B Java developer", "Job B Java engineer", "Potential Fit"),
    ]
    test = [("Resume C SQL developer", "Job C SQL engineer", "No Fit")]
    _write_primary_files(tmp_path, train, test)
    pd.DataFrame([{
        "job_id": "1",
        "category": "IT",
        "job_title": "Engineer",
        "job_skill_set": "['python', 'sql']",
    }]).to_csv(tmp_path / "job_skill_set.csv", index=False)

    summary = compute_dataset_summary(raw_dir=tmp_path)
    primary = summary["primary_dataset"]

    assert primary["raw_total_pairs"] == 4
    assert primary["raw_train_row_count"] == 3
    assert primary["duplicate_train_rows_removed"] == 1
    assert primary["verified_total_pairs"] == 3
    assert primary["exact_pair_overlap"] == 0
    assert summary["secondary_skills_dataset"]["null_cells"] == 0
