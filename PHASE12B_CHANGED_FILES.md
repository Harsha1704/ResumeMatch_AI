# ResumeMatch AI — Phase 12B Changed and Created Files Audit Trail

**Document ID:** `PHASE12B_CHANGED_FILES.md`  
**Author:** Principal MLOps Engineer & Systems Auditor  
**Date:** November 2026  
**Status:** COMPLETE & EMPIRICALLY VERIFIED  
**Repository:** `D:\skillsync1`  

---

## 1. Summary of Changes

Phase 12B strictly adhered to the **frozen production model, zero-LLM, and backward-compatible experimentation** mandates:
- **Production Files Modified:** **0** (Production model weights `models/best_model.joblib` and feature pipeline `models/feature_pipeline.joblib` remain 100% untouched with verified SHA-256 hashes).
- **Application Code Modified:** **0** (Career Mentor, Interview Studio, Skill Engine, and Flask routes remain untouched).
- **Regression Test Pass Rate:** **236 / 236 PASSED (100%)**.
- **Libraries Installed:** Permissive, non-generative deep learning dependencies `transformers==5.22.2` and `sentence-transformers==6.2.0`.
- **Pretrained Weights Cached:** `sentence-transformers/all-MiniLM-L6-v2` and `cross-encoder/ms-marco-MiniLM-L-6-v2` (cached locally in standard Hugging Face hub cache).

---

## 2. Inventory of Created Files

### A. Experimentation Scripts
1. **`scripts/run_phase12b_experiments.py`**
   - *Purpose:* End-to-end Phase 12B runner executing SBERT embedding caching, bi-encoder representation ablations (Rep 1–4), hybrid semantic + structured matching (Config A–E), cross-encoder scoring, section-aware truncation, contrastive margin analysis, and multi-protocol generalization.
   - *Size:* 22,410 bytes

### B. Embedding Artifacts & Cache
1. **`results/phase12b_embeddings/minilm_l6_v2_cache.npz`**
   - *Purpose:* Compressed numpy storage containing 384-dimensional normalized SBERT embeddings for all 643 unique resumes and 351 unique job postings in the corpus.
   - *Size:* 1,595,214 bytes (1.52 MB)

### C. Experimental Evaluation Results (`results/phase12b_experiments/`)
1. **`results/phase12b_experiments/experiment_a_embeddings.json`** — Full ablation metrics for Bi-Encoder pair representations (cosine_only, concat, interaction, full).
2. **`results/phase12b_experiments/experiment_b_hybrid.json`** — Metrics across Configurations A through E (TF-IDF baseline, SBERT embeddings, structured features, hybrid, composite).
3. **`results/phase12b_experiments/experiment_c_cross_encoder.json`** — Cross-encoder score distributions by class, section-aware vs straightforward truncation margins, latency, and hybrid augmentation.
4. **`results/phase12b_experiments/experiment_d_contrastive.json`** — SBERT cosine similarity distributions and class margin separation audit.
5. **`results/phase12b_experiments/generalization_summary.json`** — Cross-protocol metrics across Job-Disjoint, Resume-Disjoint, Dual-Unseen, and Official Test partitions.
6. **`results/phase12b_experiments/bootstrap_confidence_intervals.json`** — 1,000 bootstrap iteration confidence intervals.

### D. Phase 12B Documentation Deliverables
1. **`PHASE12B_RESEARCH_REVIEW.md`** — Review of References A through E, architectural applicability, and exclusion rationale.
2. **`PHASE12B_DATA_SPLIT_AUDIT.md`** — Dataset partition manifest, bipartite entity structure, and official test leakage disclosure.
3. **`PHASE12B_SEMANTIC_EMBEDDING_RESULTS.md`** — Bi-encoder representation ablation and pair vector analysis.
4. **`PHASE12B_HYBRID_MODEL_RESULTS.md`** — Hybrid semantic + structured matching ablation (Config A–E).
5. **`PHASE12B_CROSS_ENCODER_RESULTS.md`** — Cross-encoder pair scoring, section-aware truncation, and CPU latency benchmarks.
6. **`PHASE12B_CONTRASTIVE_RESULTS.md`** — Contrastive learning viability analysis and margin separation audit.
7. **`PHASE12B_MODEL_COMPARISON.md`** — Authoritative cross-family benchmark table comparing classical, tree, and transformer models.
8. **`PHASE12B_GENERALIZATION_REPORT.md`** — Multi-protocol evaluation and unseen candidate breakthrough analysis.
9. **`PHASE12B_CHANGED_FILES.md`** — This audit trail of created files and integrity verifications.
10. **`PHASE12B_TEST_RESULTS.md`** — 236 regression tests verification and sub-50ms latency validation.
11. **`PHASE12B_FINAL_RECOMMENDATION.md`** — Strategic promotion decision and deployment roadmap.

---

## 3. Cryptographic Hash Verification of Production Artifacts

| Artifact Path | Description | Verified Status | SHA-256 Hash |
| :--- | :--- | :---: | :--- |
| `models/best_model.joblib` | Production Classifier | **UNTOUCHED** | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` |
| `models/feature_pipeline.joblib` | Production Pipeline | **UNTOUCHED** | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` |
| `models/label_mapping.json` | Label Mapping | **UNTOUCHED** | `87951d7567429a40ff3c33e5309f9924c4986827fc12f6ebf2cc0613c6e9e9d5` |
| `ResumeMatch-AI-Final.backup15.zip` | Prior Backup | **UNTOUCHED** | Preserved intact |
| `ResumeMatch-AI-Final.backup16.zip` | Prior Backup | **UNTOUCHED** | Preserved intact |
| `ResumeMatch-AI-Final.backup17.zip` | Prior Backup | **UNTOUCHED** | Preserved intact |
