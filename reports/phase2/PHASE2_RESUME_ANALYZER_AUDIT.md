# Phase 2 — Resume Analyzer Audit & Implementation Log

## Scope
Improve resume analysis quality without changing the existing dashboard design, retraining or replacing the frozen Logistic Regression production model, or introducing an LLM.

## Baseline audit
The current analyzer already supports PDF, DOCX and TXT input; in-memory upload processing; a 16 MB upload limit; scanned-PDF detection; deterministic skill extraction; section-aware project/internship extraction; and structured experience reporting.

The audit identified these Phase 2 priorities:
1. Let a candidate explicitly clarify the target role when the job description has an ambiguous or missing title.
2. Keep the detected job title separately so the override is transparent and does not rewrite the source job description.
3. Validate the role override consistently in the browser form and JSON API.
4. Continue reducing generic skill false positives with negative-control tests before changing extraction rules.
5. Review parser edge cases and structured evidence output, preserving PDF/DOCX/TXT support and current result-page layout.

## Implemented in this phase (work in progress)
- Added an optional Target Role field to the existing Analyze form.
- Added a 120-character server-side limit.
- Added optional `target_role` support to `/api/match`, including type and length validation.
- Passed the override through the matching engine. The override changes the displayed target title and role-specific recommendations only; required/preferred skill extraction and the supervised model prediction still use the supplied job description.
- Preserved the automatically detected job title in `detected_job_title`.
- Added `target_role_source` metadata (`user_override` or `job_description`).
- Added integration regression coverage for form propagation and API validation.
- Hardened the parser to enforce the 16 MB limit for bytes, in-memory streams, and file paths.
- Added direct file-signature validation for PDF, DOCX, and TXT input, including DOCX ZIP integrity and required document-part checks.
- Changed DOCX extraction to preserve the original interleaved order of paragraphs and tables.
- Added parser regression tests for DOCX reading order, invalid signatures, binary TXT content, and oversized in-memory streams.
- Added a negative-control test ensuring generic corporate wording (for example travel, Zoom, LinkedIn, reporting, and cloud environments) is not surfaced as technical skills.

## Files changed
- `templates/analyze.html`
- `src/analysis/matching_engine.py`
- `app.py`
- `tests/test_analysis_integration.py`
- `tests/test_resume_parser.py`

## Verification status
- Code is committed to `deploy/vercel-render-free`.
- GitHub Actions passed the focused Resume Analyzer suite on commit `697c1af`: **45 passed, 1 skipped**.
- The expanded Phase 2 regression suite passed on commit `4a75928`: **73 passed, 1 skipped in 6.24 seconds**.
- The new generic-jargon negative-control test passed as part of that suite.
- Render deployment of the newest branch revision and laptop-side verification are still pending.
- The broader skill-extraction false-positive audit, live UI verification, and complete regression suite are still outstanding.
- Phase 2 is **not complete** and must not be marked complete until all remaining work, tests, and deployment checks pass.

## Safety and compatibility constraints
- `main` remains untouched.
- The Production Baseline model artifact is not changed.
- No LLM or external paid service is introduced.
- Existing UI structure is retained; the new field is additive.
