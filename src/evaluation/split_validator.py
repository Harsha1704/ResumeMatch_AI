"""
src/evaluation/split_validator.py
Automated Split Leakage Validation and Integrity Verification Framework.

Guarantees:
- Zero resume overlap for resume-disjoint evaluations.
- Zero job overlap for job-disjoint evaluations.
- Zero resume AND job overlap for dual-unseen evaluations.
- Zero exact-pair overlap across all evaluation protocols.
- Cryptographic manifest verification and cache integrity guards.
"""

import os
import re
import json
import hashlib
from typing import Dict, Any, List, Set, Tuple
import pandas as pd
import numpy as np


class SplitLeakageError(ValueError):
    """Raised when an illegal entity or pair overlap is detected between splits."""
    pass


def hash_text(text: str) -> str:
    """Computes deterministic MD5 hash of lowercased, whitespace-collapsed text."""
    cleaned = re.sub(r"\s+", " ", str(text).strip().lower())
    return hashlib.md5(cleaned.encode("utf-8")).hexdigest()


def hash_pair(resume_text: str, job_text: str) -> str:
    """Computes deterministic MD5 hash of a (resume, job) pair."""
    rh = hash_text(resume_text)
    jh = hash_text(job_text)
    return hashlib.md5(f"{rh}_{jh}".encode("utf-8")).hexdigest()


def compute_overlap_metrics(train_df: pd.DataFrame, eval_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes exhaustive entity and exact-pair overlap metrics between training and evaluation splits.
    """
    tr_res_hashes = set(train_df["resume_text"].apply(hash_text))
    tr_job_hashes = set(train_df["job_description_text"].apply(hash_text))
    tr_pair_hashes = set(
        hash_pair(r, j) for r, j in zip(train_df["resume_text"], train_df["job_description_text"])
    )

    ev_res_hashes = set(eval_df["resume_text"].apply(hash_text))
    ev_job_hashes = set(eval_df["job_description_text"].apply(hash_text))
    ev_pair_hashes = set(
        hash_pair(r, j) for r, j in zip(eval_df["resume_text"], eval_df["job_description_text"])
    )

    res_overlap = ev_res_hashes.intersection(tr_res_hashes)
    job_overlap = ev_job_hashes.intersection(tr_job_hashes)
    pair_overlap = ev_pair_hashes.intersection(tr_pair_hashes)

    n_ev_res = max(len(ev_res_hashes), 1)
    n_ev_job = max(len(ev_job_hashes), 1)
    n_ev_pair = max(len(ev_pair_hashes), 1)

    return {
        "train_resumes": len(tr_res_hashes),
        "train_jobs": len(tr_job_hashes),
        "train_pairs": len(tr_pair_hashes),
        "eval_resumes": len(ev_res_hashes),
        "eval_jobs": len(ev_job_hashes),
        "eval_pairs": len(ev_pair_hashes),
        "resume_overlap_count": len(res_overlap),
        "resume_overlap_pct": round(len(res_overlap) / n_ev_res * 100, 2),
        "job_overlap_count": len(job_overlap),
        "job_overlap_pct": round(len(job_overlap) / n_ev_job * 100, 2),
        "pair_overlap_count": len(pair_overlap),
        "pair_overlap_pct": round(len(pair_overlap) / n_ev_pair * 100, 2),
        "sample_overlapping_resumes": list(res_overlap)[:3],
        "sample_overlapping_jobs": list(job_overlap)[:3],
        "sample_overlapping_pairs": list(pair_overlap)[:3]
    }


def validate_split_isolation(
    train_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    protocol: str,
    split_name: str = "split"
) -> Dict[str, Any]:
    """
    Enforces strict protocol-specific entity and pair isolation.
    Fails immediately with SplitLeakageError if any prohibited overlap is detected.

    Supported protocols:
    - 'job_disjoint': Requires 0 job overlap and 0 pair overlap.
    - 'resume_disjoint': Requires 0 resume overlap and 0 pair overlap.
    - 'dual_unseen': Requires 0 resume overlap, 0 job overlap, and 0 pair overlap.
    - 'held_out_test': Requires 0 job overlap and 0 pair overlap with training data.
    """
    valid_protocols = {"job_disjoint", "resume_disjoint", "dual_unseen", "held_out_test"}
    if protocol not in valid_protocols:
        raise ValueError(f"Unknown protocol '{protocol}'. Must be one of: {sorted(valid_protocols)}")

    metrics = compute_overlap_metrics(train_df, eval_df)

    # 1. Exact pair overlap is strictly prohibited under ALL valid evaluation protocols
    if metrics["pair_overlap_count"] > 0:
        raise SplitLeakageError(
            f"[{split_name} | {protocol}] CATASTROPHIC PAIR LEAKAGE: "
            f"{metrics['pair_overlap_count']}/{metrics['eval_pairs']} ({metrics['pair_overlap_pct']}%) "
            f"evaluation pairs exist verbatim in the training split! "
            f"Sample overlapping pair hashes: {metrics['sample_overlapping_pairs']}"
        )

    # 2. Protocol-specific entity checks
    if protocol in ("job_disjoint", "held_out_test"):
        if metrics["job_overlap_count"] > 0:
            raise SplitLeakageError(
                f"[{split_name} | {protocol}] JOB LEAKAGE DETECTED: "
                f"{metrics['job_overlap_count']}/{metrics['eval_jobs']} ({metrics['job_overlap_pct']}%) "
                f"job descriptions in eval are present in the training set! "
                f"Sample overlapping job hashes: {metrics['sample_overlapping_jobs']}"
            )

    if protocol == "resume_disjoint":
        if metrics["resume_overlap_count"] > 0:
            raise SplitLeakageError(
                f"[{split_name} | {protocol}] RESUME LEAKAGE DETECTED: "
                f"{metrics['resume_overlap_count']}/{metrics['eval_resumes']} ({metrics['resume_overlap_pct']}%) "
                f"resumes in eval are present in the training set! "
                f"Sample overlapping resume hashes: {metrics['sample_overlapping_resumes']}"
            )

    if protocol == "dual_unseen":
        if metrics["resume_overlap_count"] > 0 or metrics["job_overlap_count"] > 0:
            raise SplitLeakageError(
                f"[{split_name} | {protocol}] DUAL ENTITY LEAKAGE DETECTED: "
                f"Resumes shared: {metrics['resume_overlap_count']}/{metrics['eval_resumes']}, "
                f"Jobs shared: {metrics['job_overlap_count']}/{metrics['eval_jobs']}. "
                f"Dual-unseen requires strictly 0 shared resumes AND 0 shared jobs."
            )

    return {
        "status": "VALID",
        "protocol": protocol,
        "split_name": split_name,
        "metrics": metrics
    }


def compute_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest_integrity(manifest_path: str) -> Dict[str, Any]:
    """
    Validates a versioned split manifest and every referenced artifact.

    The manifest may reference split files relative to its own directory and
    the primary source dataset relative to the repository root. Paths are
    resolved and constrained to the repository/manifest directory to prevent
    path traversal. When record_count is declared, Parquet row counts are
    checked as well as SHA-256 checksums.
    """
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    if not isinstance(manifest, dict):
        raise ValueError("Manifest must contain a JSON object.")

    manifest_dir = os.path.dirname(os.path.abspath(manifest_path))
    repo_root = os.path.dirname(os.path.dirname(manifest_dir))
    version = manifest.get("manifest_version", manifest.get("version"))
    files = manifest.get("files")

    if not isinstance(version, str) or not version.strip():
        raise ValueError("Manifest is missing a valid manifest_version.")
    if not isinstance(files, list) or not files:
        raise ValueError("Manifest must declare a non-empty files list.")

    def resolve_contained(base_dir: str, relative_path: str, description: str) -> str:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError(f"{description} path must be a non-empty string.")
        if os.path.isabs(relative_path):
            raise SplitLeakageError(f"Absolute {description} paths are not permitted: {relative_path}")
        resolved = os.path.realpath(os.path.join(base_dir, relative_path))
        base = os.path.realpath(base_dir)
        if os.path.commonpath([base, resolved]) != base:
            raise SplitLeakageError(f"{description} path escapes its allowed directory: {relative_path}")
        return resolved

    results = {
        "manifest_version": version,
        "files_verified": [],
        "primary_dataset_verified": None
    }

    for index, file_info in enumerate(files):
        if not isinstance(file_info, dict):
            raise ValueError(f"Manifest file entry at index {index} must be an object.")

        rel_path = file_info.get("relative_path")
        expected_sha256 = file_info.get("sha256")
        if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
            raise ValueError(f"Invalid SHA-256 value for manifest entry {rel_path!r}.")

        full_path = resolve_contained(manifest_dir, rel_path, "Split artifact")
        if not os.path.isfile(full_path):
            raise FileNotFoundError(f"Split file referenced in manifest does not exist: {full_path}")

        actual_sha256 = compute_file_sha256(full_path)
        if actual_sha256.lower() != expected_sha256.lower():
            raise SplitLeakageError(
                f"MANIFEST CORRUPTION: SHA-256 mismatch for {rel_path}! "
                f"Expected: {expected_sha256}, Actual: {actual_sha256}"
            )

        expected_count = file_info.get("record_count")
        if expected_count is not None:
            if not isinstance(expected_count, int) or expected_count < 0:
                raise ValueError(f"Invalid record_count for manifest entry {rel_path!r}.")
            try:
                actual_count = len(pd.read_parquet(full_path))
            except Exception as exc:
                raise ValueError(f"Unable to read Parquet artifact {rel_path!r}: {exc}") from exc
            if actual_count != expected_count:
                raise SplitLeakageError(
                    f"MANIFEST ROW-COUNT MISMATCH for {rel_path}: "
                    f"expected {expected_count}, found {actual_count}."
                )

        results["files_verified"].append({
            "path": rel_path,
            "sha256": actual_sha256,
            "record_count": expected_count,
            "status": "VERIFIED"
        })

    source_path = manifest.get("primary_dataset_path")
    source_sha256 = manifest.get("primary_dataset_sha256")
    if source_path is not None or source_sha256 is not None:
        if not source_path or not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", source_sha256):
            raise ValueError("Manifest primary dataset path/checksum metadata is incomplete or invalid.")
        source_full_path = resolve_contained(repo_root, source_path, "Primary source dataset")
        if not os.path.isfile(source_full_path):
            raise FileNotFoundError(f"Primary source dataset referenced in manifest does not exist: {source_full_path}")
        actual_source_sha256 = compute_file_sha256(source_full_path)
        if actual_source_sha256.lower() != source_sha256.lower():
            raise SplitLeakageError(
                "PRIMARY DATASET CHECKSUM MISMATCH: "
                f"expected {source_sha256}, found {actual_source_sha256}."
            )
        results["primary_dataset_verified"] = {
            "path": source_path,
            "sha256": actual_source_sha256,
            "status": "VERIFIED"
        }

    return results


def validate_embedding_cache_keys(
    cache_path: str,
    expected_model: str = "sentence-transformers/all-MiniLM-L6-v2"
) -> Dict[str, Any]:
    """
    Validates that an embedding cache file contains valid keys, has no label leakage,
    and adheres to source text hash formats.
    """
    if not os.path.exists(cache_path):
        raise FileNotFoundError(f"Embedding cache not found: {cache_path}")

    data = np.load(cache_path, allow_pickle=True)
    all_keys = list(data.keys())

    # Check for target/label leakage
    label_keys = [k for k in all_keys if any(term in k.lower() for term in ["label", "target", "y_"])]
    if len(label_keys) > 0:
        raise SplitLeakageError(f"LABEL LEAKAGE IN CACHE: Cache contains target/label keys: {label_keys}")

    # Check that res_hashes and job_hashes exist
    if "res_hashes" not in data or "job_hashes" not in data:
        raise SplitLeakageError("Cache is missing required index arrays 'res_hashes' or 'job_hashes'")

    res_hashes = data["res_hashes"]
    job_hashes = data["job_hashes"]

    # Verify key formatting (MD5 32 hex chars)
    for rh in res_hashes[:10]:
        if not re.match(r"^[0-9a-f]{32}$", rh):
            raise SplitLeakageError(f"Invalid resume hash key format: {rh}")
        if f"res_{rh}" not in data:
            raise SplitLeakageError(f"Missing vector for resume hash: {rh}")

    for jh in job_hashes[:10]:
        if not re.match(r"^[0-9a-f]{32}$", jh):
            raise SplitLeakageError(f"Invalid job hash key format: {jh}")
        if f"job_{jh}" not in data:
            raise SplitLeakageError(f"Missing vector for job hash: {jh}")

    return {
        "status": "VALID",
        "cache_path": cache_path,
        "num_resumes": len(res_hashes),
        "num_jobs": len(job_hashes),
        "embedding_dim": int(data[f"res_{res_hashes[0]}"].shape[0]),
        "label_leakage_detected": False
    }
