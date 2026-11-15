"""
Executes verification and artifact generation for Phase 1.
Computes dataset statistics, writes summary JSON, and renders genuine class distribution plot.
"""

from pathlib import Path
import json
from src.utils.data_loader import (
    load_primary_dataset,
    load_skills_dataset,
    compute_dataset_summary
)
from src.utils.visualizer import plot_class_distribution


def main():
    print("Loading verified datasets...")
    train_df, test_df = load_primary_dataset()
    print(f"Loaded primary dataset: Train={len(train_df)}, Test={len(test_df)}")

    skills_df = load_skills_dataset()
    print(f"Loaded skills dataset: {len(skills_df)} job entries")

    print("Computing comprehensive statistical summary...")
    summary = compute_dataset_summary()
    summary_path = Path("data/raw/dataset_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary written to {summary_path}")

    print("Rendering genuine class distribution plot...")
    plot_file = plot_class_distribution(train_df, test_df)
    print(f"Saved plot to {plot_file}")


if __name__ == "__main__":
    main()
