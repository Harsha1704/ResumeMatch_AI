"""
Evaluation and split validation framework for ResumeMatch AI.
Ensures zero-leakage, reproducible, entity-disjoint model evaluation.
"""

from src.evaluation.split_validator import (
    SplitLeakageError,
    validate_split_isolation,
    compute_overlap_metrics,
    validate_manifest_integrity,
    validate_embedding_cache_keys,
    hash_text,
    hash_pair
)

__all__ = [
    "SplitLeakageError",
    "validate_split_isolation",
    "compute_overlap_metrics",
    "validate_manifest_integrity",
    "validate_embedding_cache_keys",
    "hash_text",
    "hash_pair"
]
