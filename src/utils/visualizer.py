"""
Visualization utilities for model evaluation and dataset exploration.
Multimodal Resume-Job Matching & Skill Gap Analysis System.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from collections import Counter
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.preprocessing.skill_extractor import SkillEngine


DEFAULT_PLOTS_DIR = Path(__file__).resolve().parent.parent.parent / "results" / "plots"


def plot_class_distribution(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    save_path: Optional[Union[str, Path]] = None
) -> str:
    """
    Plots and saves the genuine class distribution comparing Train and Test splits.
    """
    out_file = Path(save_path) if save_path else DEFAULT_PLOTS_DIR / "class_distribution.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    train_counts = train_df["label"].value_counts().reset_index()
    train_counts.columns = ["Class", "Count"]
    train_counts["Split"] = f"Train (N={len(train_df):,})"

    test_counts = test_df["label"].value_counts().reset_index()
    test_counts.columns = ["Class", "Count"]
    test_counts["Split"] = f"Held-Out Test (N={len(test_df):,})"

    combined = pd.concat([train_counts, test_counts], ignore_index=True)

    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

    bar_colors = ["#1f77b4", "#aec7e8"]
    sns.barplot(
        data=combined,
        x="Class",
        y="Count",
        hue="Split",
        palette=bar_colors,
        ax=ax,
        edgecolor="#333333",
        linewidth=0.8
    )

    total_train = len(train_df)
    total_test = len(test_df)
    totals = [total_train, total_test]

    for container_idx, container in enumerate(ax.containers):
        split_total = totals[container_idx] if container_idx < len(totals) else total_test
        for bar in container:
            height = bar.get_height()
            if height > 0:
                pct = (height / split_total) * 100
                ax.annotate(
                    f"{int(height):,}\n({pct:.2f}%)",
                    (bar.get_x() + bar.get_width() / 2.0, height + 40),
                    ha="center",
                    va="bottom",
                    fontsize=9.5,
                    fontweight="bold",
                    color="#222222"
                )

    ax.set_title("Dataset Label Distribution (cnamuangtoun/resume-job-description-fit)", fontsize=13, fontweight="bold", pad=14)
    ax.set_xlabel("Compatibility Fit Label", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Number of Resume-Job Pairs", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylim(0, max(combined["Count"]) * 1.18)
    ax.legend(title="Data Partition", frameon=True, facecolor="white", loc="upper right")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_top_skills_distribution(
    train_df: pd.DataFrame,
    save_path: Optional[Union[str, Path]] = None,
    top_k: int = 15
) -> str:
    """
    Computes and plots the top most frequent skills extracted across resumes and jobs.
    """
    out_file = Path(save_path) if save_path else DEFAULT_PLOTS_DIR / "top_skills_distribution.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    engine = SkillEngine()
    resume_counter: Counter = Counter()
    job_counter: Counter = Counter()

    # Sample representative subset for fast accurate frequency plotting
    sample = train_df.sample(min(800, len(train_df)), random_state=42)
    for _, row in sample.iterrows():
        r_skills = engine.extract_skills(row["resume_text"])
        j_skills = engine.extract_skills(row["job_description_text"])
        for s in r_skills:
            resume_counter[s] += 1
        for s in j_skills:
            job_counter[s] += 1

    top_overall = [s for s, _ in (resume_counter + job_counter).most_common(top_k)]

    data = []
    for s in top_overall:
        data.append({"Skill": s.title(), "Frequency": resume_counter[s], "Source": "Resumes"})
        data.append({"Skill": s.title(), "Frequency": job_counter[s], "Source": "Job Descriptions"})

    df_plot = pd.DataFrame(data)

    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, ax = plt.subplots(figsize=(10, 6.5), dpi=300)

    sns.barplot(
        data=df_plot,
        y="Skill",
        x="Frequency",
        hue="Source",
        palette=["#2b5c8f", "#e27c38"],
        ax=ax,
        edgecolor="#333333",
        linewidth=0.6
    )

    ax.set_title(f"Top {top_k} Most Frequent Extracted Skills in Dataset", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Extraction Frequency in Sample", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Skill Phrase", fontsize=11, fontweight="bold", labelpad=8)
    ax.legend(title="Occurrence", frameon=True, facecolor="white", loc="lower right")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_text_length_distributions(
    train_df: pd.DataFrame,
    save_path: Optional[Union[str, Path]] = None
) -> str:
    """
    Plots the character and word length distributions for resumes and job descriptions.
    """
    out_file = Path(save_path) if save_path else DEFAULT_PLOTS_DIR / "text_length_distributions.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    r_words = train_df["resume_text"].apply(lambda t: len(str(t).split()))
    j_words = train_df["job_description_text"].apply(lambda t: len(str(t).split()))

    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    # Resume distribution
    sns.histplot(r_words, bins=35, kde=True, ax=ax1, color="#2b5c8f", edgecolor="#222222")
    ax1.axvline(r_words.median(), color="red", linestyle="--", label=f"Median: {int(r_words.median())} words")
    ax1.set_title("Resume Word Count Distribution", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Word Count", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Density / Count", fontsize=10, fontweight="bold")
    ax1.legend()

    # Job description distribution
    sns.histplot(j_words, bins=35, kde=True, ax=ax2, color="#e27c38", edgecolor="#222222")
    ax2.axvline(j_words.median(), color="red", linestyle="--", label=f"Median: {int(j_words.median())} words")
    ax2.set_title("Job Description Word Count Distribution", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Word Count", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Density / Count", fontsize=10, fontweight="bold")
    ax2.legend()

    plt.suptitle("Document Length Characteristics (cnamuangtoun/resume-job-description-fit)", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)


def plot_preprocessing_summary(
    train_df: pd.DataFrame,
    save_path: Optional[Union[str, Path]] = None
) -> str:
    """
    Plots multi-panel summary of preprocessed metrics:
    - Jaccard skill similarity across fit classes
    - Explicit years of experience distribution
    """
    out_file = Path(save_path) if save_path else DEFAULT_PLOTS_DIR / "preprocessing_summary.png"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    engine = SkillEngine()
    sample = train_df.sample(min(600, len(train_df)), random_state=42).copy()

    jaccards = []
    exp_years = []
    for _, row in sample.iterrows():
        gap = engine.analyze_skill_gap(row["resume_text"], row["job_description_text"])
        struct = parse_structural_features(row["resume_text"])
        jaccards.append(gap["jaccard_similarity"])
        exp_years.append(struct["explicit_years_exp"])

    sample["jaccard_similarity"] = jaccards
    sample["explicit_years_exp"] = exp_years

    sns.set_theme(style="whitegrid", font="sans-serif")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    # Boxplot of skill Jaccard similarity by class
    order = ["No Fit", "Potential Fit", "Good Fit"]
    palette = {"No Fit": "#dc3545", "Potential Fit": "#ffc107", "Good Fit": "#28a745"}
    sns.boxplot(
        data=sample,
        x="label",
        y="jaccard_similarity",
        order=order,
        hue="label",
        palette=palette,
        legend=False,
        ax=ax1
    )
    ax1.set_title("Skill Jaccard Similarity by Ground Truth Class", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Ground Truth Label", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Skill Jaccard Similarity", fontsize=10, fontweight="bold")

    # Histogram of explicit experience years
    exp_filtered = [y for y in exp_years if y > 0]
    sns.histplot(exp_filtered, bins=20, ax=ax2, color="#17a2b8", edgecolor="#222222", kde=True)
    ax2.set_title("Explicitly Stated Experience Years (Resumes)", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Years of Experience", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Frequency", fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return str(out_file)
