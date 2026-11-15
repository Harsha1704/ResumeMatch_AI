# Phase 12C — Changed Files & Audit Trail

## Summary of File Modifications
During Phase 12C (Independent Transformer Validation & Model Integrity Audit), the active production application, model weights, and inference pipelines were held **strictly immutable**.

No production code, web routes, Career Mentor logic, or model binaries were modified. All modifications were confined to auditing scripts, empirical measurement outputs, and forensic documentation.

---

## 1. Auditing Scripts & Code

| File Path | Action | Purpose |
| :--- | :---: | :--- |
| `scripts/run_phase12c_audit.py` | **Created** | Comprehensive audit harness executing reproduction, cross-split leakage checks, paired bootstrap resampling (1,000 iterations), CPU latency benchmarks, and cache integrity verification. |

---

## 2. Empirical Audit Artifacts (`results/phase12c_audit/`)

| File Path | Action | Purpose |
| :--- | :---: | :--- |
| `results/phase12c_audit/reproduction_results.json` | **Created** | Machine-readable metrics reproducing Phase 12B claims across all 4 partitions. |
| `results/phase12c_audit/leakage_audit.json` | **Created** | Detailed resume, job, and exact pair overlap counts and leakage percentages across all split combinations. |
| `results/phase12c_audit/fair_comparison.json` | **Created** | Apples-to-apples comparison between Classical Baseline, SBERT Config B, and Hybrid Config D on uncontaminated vs contaminated partitions. |
| `results/phase12c_audit/statistical_bootstrap.json` | **Created** | Paired bootstrap resampling statistics (1,000 resamples), means, standard deviations, 95% confidence intervals, and two-tailed p-values. |
| `results/phase12c_audit/latency_benchmark.json` | **Created** | End-to-end CPU inference latency profile (cold-start, warm median, p95, p99, throughput in pairs/sec, memory in MB). |
| `results/phase12c_audit/cache_integrity.json` | **Created** | Cryptographic hash audit and numerical alignment verification ($L_2$ distance $< 10^{-6}$) against fresh MiniLM-L6-v2 encodings. |

---

## 3. Audit Deliverables (Root Workspace)

| File Path | Action | Description |
| :--- | :---: | :--- |
| `PHASE12C_REPRODUCTION_REPORT.md` | **Created** | Deliverable 1: End-to-end reproduction of reported Phase 12B claims. |
| `PHASE12C_SPLIT_LEAKAGE_AUDIT.md` | **Created** | Deliverable 2: Cross-split leakage forensic audit with exact counts and entity overlap tables. |
| `PHASE12C_DUAL_UNSEEN_INVESTIGATION.md` | **Created** | Deliverable 3: Root cause breakdown of the 85.19% dual-unseen & 87.59% resume-disjoint anomaly. |
| `PHASE12C_FAIR_MODEL_COMPARISON.md` | **Created** | Deliverable 4: Fair head-to-head comparison of Classical Baseline vs SBERT Config B vs Hybrid Config D. |
| `PHASE12C_STATISTICAL_VALIDATION.md` | **Created** | Deliverable 5: Statistical hypothesis testing, paired bootstrap CIs, and significance verdicts. |
| `PHASE12C_INFERENCE_BENCHMARK.md` | **Created** | Deliverable 6: Real-time CPU latency, throughput, memory footprint, and production suitability profile. |
| `PHASE12C_CACHE_INTEGRITY.md` | **Created** | Deliverable 7: Embedding cache cryptographic and numerical integrity audit. |
| `PHASE12C_CHANGED_FILES.md` | **Created** | Deliverable 8: This audit trail document. |
| `PHASE12C_TEST_RESULTS.md` | **Created** | Deliverable 9: Full 236-test pytest regression confirmation. |
| `PHASE12C_FINAL_VERDICT.md` | **Created** | Deliverable 10: Official audit decision and deployment governance policy. |

---

## 4. Immutable Production Artifacts Preserved

| Protected Artifact | Hash / State | Verification Status |
| :--- | :---: | :---: |
| `models/best_model.joblib` | SHA-256: `1001BAAF42DB8832E1BA3E28EE9DA7146E59F1D2D1808C73C4F7587535B2ED4A` | **FROZEN & UNTOUCHED** |
| `src/matching_engine.py` | Production Match Engine Logic | **PRESERVED & UNCHANGED** |
| `src/routes/` & `src/services/` | Flask Application Endpoints & Career Mentor | **PRESERVED & UNCHANGED** |
| Backups | `backup15.zip` through `backup18.zip` | **PRESERVED & INTACT** |
