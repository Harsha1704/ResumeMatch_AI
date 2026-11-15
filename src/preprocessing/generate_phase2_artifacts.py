"""
Phase 2 Artifact Generator & Pipeline Pre-fitting.
Generates genuine preprocessing plots, verifies zero-leakage splits,
and saves the fitted feature pipeline to models/feature_pipeline.joblib.
"""

from pathlib import Path
import json
import shutil
import time

from src.utils.data_loader import load_primary_dataset
from src.utils.split_manager import verify_split_leakage_safeguards, get_unseen_jobs_split
from src.features.feature_pipeline import ResumeJobFeaturePipeline
from src.utils.visualizer import (
    plot_class_distribution,
    plot_top_skills_distribution,
    plot_text_length_distributions,
    plot_preprocessing_summary
)


def main():
    print("--- Phase 2: Starting Artifact Generation & Pipeline Fitting ---")
    train_df, test_df = load_primary_dataset()
    print(f"Loaded primary datasets: Train={len(train_df)} pairs, Test={len(test_df)} pairs")

    # 1. Leakage verification
    print("Verifying group-aware leakage safeguards...")
    leakage_report = verify_split_leakage_safeguards()
    print("Leakage Report:")
    print(json.dumps(leakage_report, indent=2))

    # 2. Generate Preprocessing Visualizations
    plots_dir = Path("results/plots")
    static_img_dir = Path("static/images")
    plots_dir.mkdir(parents=True, exist_ok=True)
    static_img_dir.mkdir(parents=True, exist_ok=True)

    print("Generating top skills distribution plot...")
    p1 = plot_top_skills_distribution(train_df)
    shutil.copy2(p1, static_img_dir / "top_skills_distribution.png")

    print("Generating text length distribution plot...")
    p2 = plot_text_length_distributions(train_df)
    shutil.copy2(p2, static_img_dir / "text_length_distributions.png")

    print("Generating preprocessing summary plot...")
    p3 = plot_preprocessing_summary(train_df)
    shutil.copy2(p3, static_img_dir / "preprocessing_summary.png")

    print(f"Saved plots to {plots_dir} and mirrored to {static_img_dir}")

    # 3. Fit Feature Pipeline ONLY on Training Data (Zero Leakage)
    print("Fitting ResumeJobFeaturePipeline on training data...")
    t0 = time.time()
    train_sub, val_sub, held_out_test = get_unseen_jobs_split()

    pipeline = ResumeJobFeaturePipeline(max_tfidf_features=2500)
    pipeline.fit(train_sub)
    t1 = time.time()
    print(f"Pipeline fitted on {len(train_sub)} training pairs in {t1 - t0:.2f}s!")

    # Save fitted pipeline for model training and Flask inference
    pipeline_save_path = Path("models/feature_pipeline.joblib")
    pipeline.save(pipeline_save_path)
    print(f"Fitted pipeline saved to {pipeline_save_path}")

    # 4. Save metadata summary
    summary_data = {
        "pipeline_fitted": True,
        "train_pairs_fitted": len(train_sub),
        "val_pairs": len(val_sub),
        "held_out_test_pairs": len(held_out_test),
        "tfidf_vocabulary_size": len(pipeline.vectorizer.vocabulary_),
        "dense_feature_count": len(pipeline.feature_names) - len(pipeline.vectorizer.vocabulary_) - 3,
        "total_feature_dimensions": len(pipeline.feature_names),
        "leakage_safeguards": leakage_report
    }

    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    summary_path = processed_dir / "preprocessing_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"Preprocessing metadata written to {summary_path}")
    print("--- Phase 2 Artifact Generation Complete ---")


if __name__ == "__main__":
    main()
