"""
Unit tests for data loader and dataset acquisition integrity.
Multimodal Resume-Job Matching & Skill Gap Analysis System.
"""

from pathlib import Path
import pytest
import pandas as pd
from src.utils.data_loader import (
    load_primary_dataset,
    load_skills_dataset,
    extract_skill_lexicon,
    create_train_val_split,
    VALID_LABELS,
    EXPECTED_PRIMARY_COLUMNS
)
from src.utils.visualizer import plot_class_distribution


def test_primary_dataset_loading_and_schema():
    """Verify primary dataset files exist, load without error, and match schema."""
    train_df, test_df = load_primary_dataset()
    assert isinstance(train_df, pd.DataFrame)
    assert isinstance(test_df, pd.DataFrame)
    assert len(train_df) > 6000
    assert len(test_df) > 1700

    for col in EXPECTED_PRIMARY_COLUMNS:
        assert col in train_df.columns
        assert col in test_df.columns

    # Verify no nulls in critical text and label fields
    assert train_df["resume_text"].isnull().sum() == 0
    assert train_df["job_description_text"].isnull().sum() == 0
    assert train_df["label"].isnull().sum() == 0
    assert test_df["resume_text"].isnull().sum() == 0
    assert test_df["job_description_text"].isnull().sum() == 0
    assert test_df["label"].isnull().sum() == 0


def test_label_integrity():
    """Verify all class labels match the 3 specified ground-truth classes."""
    train_df, test_df = load_primary_dataset()
    train_labels = set(train_df["label"].unique())
    test_labels = set(test_df["label"].unique())

    assert train_labels == set(VALID_LABELS)
    assert test_labels == set(VALID_LABELS)


def test_skills_dataset_loading_and_lexicon():
    """Verify secondary skills dataset loads and generates normalized lexicon."""
    skills_df = load_skills_dataset()
    assert isinstance(skills_df, pd.DataFrame)
    assert len(skills_df) >= 1000
    assert "job_skill_set" in skills_df.columns

    lexicon = extract_skill_lexicon(skills_df)
    assert isinstance(lexicon, list)
    assert len(lexicon) > 2000
    # Check that skills are lowercase and non-empty
    for skill in lexicon[:50]:
        assert skill == skill.lower()
        assert len(skill) > 0


def test_train_val_split_reproducibility():
    """Verify reproducible stratified train/val split without data alteration."""
    train_df, _ = load_primary_dataset()
    train_sub1, val_sub1 = create_train_val_split(train_df, val_size=0.15, random_state=42)
    train_sub2, val_sub2 = create_train_val_split(train_df, val_size=0.15, random_state=42)

    assert len(train_sub1) + len(val_sub1) == len(train_df)
    assert train_sub1.equals(train_sub2)
    assert val_sub1.equals(val_sub2)

    # Check stratification: label proportions in split should match original train_df within 1%
    for label in VALID_LABELS:
        orig_prop = (train_df["label"] == label).mean()
        val_prop = (val_sub1["label"] == label).mean()
        assert abs(orig_prop - val_prop) < 0.02


def test_repeated_loading_stability():
    """Verify that multiple consecutive loads succeed without state leakage."""
    for _ in range(3):
        t1, te1 = load_primary_dataset()
        assert len(t1) == 6240
        assert len(te1) == 1759


def test_class_distribution_plot_generation(tmp_path):
    """Verify plot generation produces a valid non-empty PNG file."""
    train_df, test_df = load_primary_dataset()
    plot_path = tmp_path / "test_dist.png"
    out_path = plot_class_distribution(train_df, test_df, save_path=plot_path)

    assert Path(out_path).exists()
    assert Path(out_path).stat().st_size > 10000  # Non-trivial image file
