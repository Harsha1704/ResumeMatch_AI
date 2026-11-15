"""
Extracts and caches raw domain alignment features for the dual-unseen splits.
Strictly unscaled, deterministic linguistic metrics only.
"""

import time
from pathlib import Path
import pandas as pd
from experiments.model_optimization.feature_engineering import ExperimentalDomainExtractor

SPLITS_DIR = Path("experiments/dataset_improvement/splits")
train_path = SPLITS_DIR / "dual_unseen_train.parquet"
val_path = SPLITS_DIR / "dual_unseen_val.parquet"

train_cache = SPLITS_DIR / "train_domain_raw.parquet"
val_cache = SPLITS_DIR / "val_domain_raw.parquet"

extractor = ExperimentalDomainExtractor()

print("Loading dual-unseen splits...")
train_df = pd.read_parquet(train_path)
val_df = pd.read_parquet(val_path)

if not train_cache.exists():
    print(f"Extracting domain features for dual_unseen_train ({len(train_df)} pairs)...")
    t0 = time.time()
    train_rows = [extractor.extract_pair_features(r, j) for r, j in zip(train_df["resume_text"], train_df["job_description_text"])]
    train_dom_df = pd.DataFrame(train_rows)
    train_dom_df.to_parquet(train_cache, index=False)
    print(f"Saved {train_cache} ({train_dom_df.shape}) in {time.time() - t0:.2f}s.")
else:
    print(f"Train cache already exists: {train_cache}")

if not val_cache.exists():
    print(f"Extracting domain features for dual_unseen_val ({len(val_df)} pairs)...")
    t0 = time.time()
    val_rows = [extractor.extract_pair_features(r, j) for r, j in zip(val_df["resume_text"], val_df["job_description_text"])]
    val_dom_df = pd.DataFrame(val_rows)
    val_dom_df.to_parquet(val_cache, index=False)
    print(f"Saved {val_cache} ({val_dom_df.shape}) in {time.time() - t0:.2f}s.")
else:
    print(f"Val cache already exists: {val_cache}")
