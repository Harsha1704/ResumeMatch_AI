# Phase 1 — Data Integrity & Dataset Governance

**Status:** Implementation committed; automated CI result pending  
**Branch:** `deploy/vercel-render-free`  
**Scope:** Primary dataset validation, source/clean count reconciliation, split-manifest verification, and Dataset Explorer provenance.

## 1. Canonical primary dataset counts

The source CSVs contain 8,000 rows:

| Stage | Train | Held-out test | Total |
|---|---:|---:|---:|
| Raw source files | 6,241 | 1,759 | 8,000 |
| Exact duplicate rows removed | 1 | 0 | 1 |
| Verified records used by the application loader | 6,240 | 1,759 | 7,999 |

The one removed row is an exact duplicate in the training source. The raw source is retained; deduplication is applied by the loader. This explains why the Dataset Explorer and production training metadata use 7,999 verified records while source provenance totals 8,000.

The primary schema is `resume_text`, `job_description_text`, and `label`. The loader now rejects null values and blank resume/job text before deduplication, and continues to reject labels outside the three supported classes.

## 2. Source split overlap is reported precisely

The original source train/test split has:
- 0 of 71 test job descriptions shared with training (0% job overlap).
- 476 of 477 test resumes shared with training (99.79% resume overlap).
- 0 exact resume/job pairs shared.

This is not a fully entity-disjoint split. It supports evaluation on unseen jobs with mostly known resumes. The Dataset Explorer now states this explicitly rather than displaying only the zero job-overlap result.

## 3. Manifest verification hardening

The Phase 12D split manifest remains the source of truth for the seven versioned Parquet partitions. The validator now:
- Reads the declared `manifest_version` field correctly.
- Requires a non-empty manifest file registry and valid 64-character SHA-256 checksums.
- Rejects absolute paths and paths that escape the permitted manifest/repository directories.
- Verifies every referenced split artifact's SHA-256 checksum.
- Verifies declared Parquet row counts when present.
- Verifies the primary raw dataset checksum when source path/checksum metadata is declared.

The existing protocol-specific overlap guards remain in place. The frozen production model and its feature pipeline were not modified.

## 4. Dataset Explorer reconciliation

The existing page design is preserved. Its primary dataset card now distinguishes:
- 8,000 raw source rows;
- 7,999 verified rows after removing one exact duplicate;
- the one-row training deduplication;
- 0% job overlap and 99.79% resume overlap across the original source split.

The saved dataset summary now includes raw/verified counts, duplicate counts, null counts, and explicit overlap percentages. The summary generator computes these fields from the source files rather than assuming raw and cleaned counts are identical.

## 5. Regression coverage added

- `tests/test_data_integrity_phase1.py`: duplicate handling, null/blank rejection, and raw-versus-verified count reconciliation.
- `tests/test_split_leakage_guards.py`: existing leakage tests updated for strict SHA-256 validation, plus manifest version/source-checksum and path-traversal tests.
- `tests/test_frontend_dashboard.py`: Dataset Explorer count and overlap disclosures asserted.
- `.github/workflows/phase1-data-integrity.yml`: runs the focused data-integrity regression suite on pushes to this deployment branch and pull requests targeting it.

## 6. Verification boundary

The changes are committed to the deployment branch. The GitHub Actions run result has not yet been confirmed from the available repository connection, so Phase 1 is **not certified complete** until the CI workflow passes. The deployed Render service has not yet been redeployed or smoke-tested with these commits.

No model retraining, production checkpoint replacement, dashboard redesign, or paid service was introduced.
