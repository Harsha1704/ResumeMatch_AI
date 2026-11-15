"""
Precomputes and caches domain alignment features for train and val splits.
Saves to experiments/model_optimization/data_cache/.
"""

import time
from pathlib import Path
import pandas as pd
from src.utils.split_manager import get_unseen_jobs_split
from experiments.model_optimization.feature_engineering import ExperimentalDomainExtractor

CACHE_DIR = Path("experiments/model_optimization/data_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

train_cache = CACHE_DIR / "train_domain_features.parquet"
val_cache = CACHE_DIR / "val_domain_features.parquet"

train_df, val_df, test_df = get_unseen_jobs_split()

extractor = ExperimentalDomainExtractor()

if not train_cache.exists():
    print(f"Extracting domain features for train_df ({len(train_df)} pairs)...")
    t0 = time.time()
    train_rows = [extractor.extract_pair_features(r, j) for r, j in zip(train_df["resume_text"], train_df["job_description_text"])]
    train_domain_df = pd.DataFrame(train_rows)
    train_domain_df.to_parquet(train_cache)
    print(f"Train domain features saved ({train_domain_df.shape}) in {time.time() - t0:.2f}s.")
else:
    print(f"Train domain features cache already exists at {train_cache}")

if not val_cache.exists():
    print(f"Extracting domain features for val_df ({len(val_df)} pairs)...")
    t0 = time.time()
    val_rows = [extractor.extract_pair_features(r, j) for r, j in zip(val_df["resume_text"], val_df["job_description_text"])]
    val_domain_df = pd.DataFrame(val_rows)
    val_domain_df.to_parquet(val_cache)
    print(f"Val domain features saved ({val_domain_df.shape}) in {time.time() - t0:.2f}s.")
else:
    print(f"Val domain features cache already exists at {val_cache}")
