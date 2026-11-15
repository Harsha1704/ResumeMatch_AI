"""
experiments/phase13_1/scripts/benchmark_end_to_end_inference.py
Task 6: Measure the complete end-to-end inference pipeline for:
1. Production Baseline (Model 1)
2. Skill-Aware Matching Classifier (Model 4)
3. Semantic & Structured-Feature Fusion Challenger (Model 5)

Under identical conditions:
- Full text preprocessing
- SBERT tokenization and encoding (or TF-IDF transformation)
- Structured domain feature extraction
- Feature scaling
- Classifier prediction
- Complete model loading and initialization (Cold Start)
- Process RSS memory
- Deployable artifact sizes on disk
"""

import sys
import os
import time
import json
import psutil
from pathlib import Path
REPO_ROOT = Path("D:/skillsync1")
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd
import joblib

def measure_disk_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())

def main():
    print("=" * 80)
    print("PHASE 13.1 — TASK 6: COMPLETE END-TO-END INFERENCE BENCHMARK")
    print("=" * 80)
    
    val_m = pd.read_parquet(REPO_ROOT / "manifests" / "v1" / "dual_unseen_val_v1.parquet")
    # Clean val (296 pairs)
    tr_norm_res = set(pd.read_parquet(REPO_ROOT / "manifests/v1/dual_unseen_train_v1.parquet")["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" "))
    vl_norm_res = val_m["resume_text"].str.lower().str.replace(r"[^a-z0-9]", " ", regex=True).str.split().str.join(" ")
    clean_mask = ~vl_norm_res.isin(tr_norm_res)
    val_clean = val_m[clean_mask].reset_index(drop=True)
    
    sample_pairs = val_clean.iloc[:100] # 100 representative pairs for warm benchmark
    print(f"Loaded {len(sample_pairs)} evaluation pairs for end-to-end benchmarking.")
    
    process = psutil.Process()
    rss_init = process.memory_info().rss / (1024 * 1024)
    print(f"Initial process RSS: {rss_init:.2f} MB")
    
    # -------------------------------------------------------------
    # 1. BENCHMARK PRODUCTION BASELINE (Model 1)
    # -------------------------------------------------------------
    print("\n[Benchmarking Model 1: Production Baseline]")
    t0 = time.perf_counter()
    pipe_prod = joblib.load(REPO_ROOT / "models" / "feature_pipeline.joblib")
    clf_prod = joblib.load(REPO_ROOT / "models" / "best_model.joblib")
    cold_start_prod_ms = (time.perf_counter() - t0) * 1000.0
    rss_after_load_prod = process.memory_info().rss / (1024 * 1024)
    
    size_pipe = measure_disk_size(REPO_ROOT / "models" / "feature_pipeline.joblib")
    size_clf = measure_disk_size(REPO_ROOT / "models" / "best_model.joblib")
    total_size_prod = size_pipe + size_clf
    
    # Warmup
    for i in range(5):
        row = sample_pairs.iloc[i]
        df_single = pd.DataFrame([{"resume_text": row["resume_text"], "job_description_text": row["job_description_text"]}])
        X = pipe_prod.transform(df_single)
        _ = clf_prod.predict_proba(X)
        
    latencies_prod = []
    for i in range(len(sample_pairs)):
        row = sample_pairs.iloc[i]
        df_single = pd.DataFrame([{"resume_text": row["resume_text"], "job_description_text": row["job_description_text"]}])
        t_start = time.perf_counter()
        X = pipe_prod.transform(df_single)
        _ = clf_prod.predict_proba(X)
        t_end = time.perf_counter()
        latencies_prod.append((t_end - t_start) * 1000.0) # ms
        
    rss_peak_prod = process.memory_info().rss / (1024 * 1024)
    
    prod_metrics = {
        "model_name": "Model 1: Production Baseline",
        "deployable_artifact_bytes": total_size_prod,
        "deployable_artifact_mb": round(total_size_prod / (1024 * 1024), 3),
        "external_transformer_weights_required": False,
        "cold_start_load_ms": round(cold_start_prod_ms, 2),
        "post_load_rss_mb": round(rss_after_load_prod, 2),
        "peak_rss_mb": round(rss_peak_prod, 2),
        "latency_mean_ms": round(float(np.mean(latencies_prod)), 3),
        "latency_p50_ms": round(float(np.percentile(latencies_prod, 50)), 3),
        "latency_p95_ms": round(float(np.percentile(latencies_prod, 95)), 3),
        "latency_p99_ms": round(float(np.percentile(latencies_prod, 99)), 3)
    }
    print(f"  Artifact Size: {prod_metrics['deployable_artifact_mb']} MB")
    print(f"  Cold Start:    {prod_metrics['cold_start_load_ms']} ms")
    print(f"  Mean Latency:  {prod_metrics['latency_mean_ms']} ms/pair (p50: {prod_metrics['latency_p50_ms']}, p95: {prod_metrics['latency_p95_ms']})")

    # -------------------------------------------------------------
    # 2. BENCHMARK MODEL 4: Skill-Aware Matching Classifier
    # -------------------------------------------------------------
    print("\n[Benchmarking Model 4: Skill-Aware Matching Classifier]")
    from experiments.model_optimization.feature_engineering import ExperimentalDomainExtractor
    t0 = time.perf_counter()
    m4_obj = joblib.load(REPO_ROOT / "models" / "phase13" / "skill_aware_matching_model.joblib")
    extractor_m4 = ExperimentalDomainExtractor()
    cold_start_m4_ms = (time.perf_counter() - t0) * 1000.0
    rss_after_load_m4 = process.memory_info().rss / (1024 * 1024)
    
    size_m4 = measure_disk_size(REPO_ROOT / "models" / "phase13" / "skill_aware_matching_model.joblib")
    
    # Warmup
    for i in range(5):
        row = sample_pairs.iloc[i]
        d_feats = extractor_m4.extract_pair_features(row["resume_text"], row["job_description_text"])
        feats_df = pd.DataFrame([d_feats])[m4_obj["features"]]
        feats_sc = m4_obj["scaler"].transform(feats_df)
        _ = m4_obj["model"].predict_proba(feats_sc)
        
    latencies_m4 = []
    for i in range(len(sample_pairs)):
        row = sample_pairs.iloc[i]
        t_start = time.perf_counter()
        d_feats = extractor_m4.extract_pair_features(row["resume_text"], row["job_description_text"])
        feats_df = pd.DataFrame([d_feats])[m4_obj["features"]]
        feats_sc = m4_obj["scaler"].transform(feats_df)
        _ = m4_obj["model"].predict_proba(feats_sc)
        t_end = time.perf_counter()
        latencies_m4.append((t_end - t_start) * 1000.0)
        
    rss_peak_m4 = process.memory_info().rss / (1024 * 1024)
    
    m4_metrics = {
        "model_name": "Model 4: Skill-Aware Matching Classifier",
        "deployable_artifact_bytes": size_m4,
        "deployable_artifact_mb": round(size_m4 / (1024 * 1024), 3),
        "external_transformer_weights_required": False,
        "cold_start_load_ms": round(cold_start_m4_ms, 2),
        "post_load_rss_mb": round(rss_after_load_m4, 2),
        "peak_rss_mb": round(rss_peak_m4, 2),
        "latency_mean_ms": round(float(np.mean(latencies_m4)), 3),
        "latency_p50_ms": round(float(np.percentile(latencies_m4, 50)), 3),
        "latency_p95_ms": round(float(np.percentile(latencies_m4, 95)), 3),
        "latency_p99_ms": round(float(np.percentile(latencies_m4, 99)), 3)
    }
    print(f"  Artifact Size: {m4_metrics['deployable_artifact_mb']} MB")
    print(f"  Cold Start:    {m4_metrics['cold_start_load_ms']} ms")
    print(f"  Mean Latency:  {m4_metrics['latency_mean_ms']} ms/pair (p50: {m4_metrics['latency_p50_ms']}, p95: {m4_metrics['latency_p95_ms']})")

    # -------------------------------------------------------------
    # 3. BENCHMARK MODEL 5: Semantic & Structured-Feature Fusion Challenger
    # -------------------------------------------------------------
    print("\n[Benchmarking Model 5: Semantic & Skill Fusion Challenger]")
    t0 = time.perf_counter()
    from sentence_transformers import SentenceTransformer
    sbert_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    m5_obj = joblib.load(REPO_ROOT / "models" / "phase13" / "semantic_skill_fusion_challenger.joblib")
    extractor_m5 = ExperimentalDomainExtractor()
    cold_start_m5_ms = (time.perf_counter() - t0) * 1000.0
    rss_after_load_m5 = process.memory_info().rss / (1024 * 1024)
    
    hf_cache_dir = Path(os.path.expanduser("~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"))
    size_sbert = measure_disk_size(hf_cache_dir)
    size_m5_joblib = measure_disk_size(REPO_ROOT / "models" / "phase13" / "semantic_skill_fusion_challenger.joblib")
    total_size_m5 = size_sbert + size_m5_joblib
    
    # Warmup
    for i in range(5):
        row = sample_pairs.iloc[i]
        u = sbert_model.encode([row["resume_text"]], normalize_embeddings=True)[0]
        v = sbert_model.encode([row["job_description_text"]], normalize_embeddings=True)[0]
        cos = np.dot(u, v).reshape(1, 1)
        x_sbert = np.hstack([u, v, u * v, np.abs(u - v), cos.flatten()]).reshape(1, -1)
        d_feats = extractor_m5.extract_pair_features(row["resume_text"], row["job_description_text"])
        feats_df = pd.DataFrame([d_feats])[m5_obj["domain_feature_names"]]
        x_sc_sbert = m5_obj["scaler_sbert"].transform(x_sbert)
        x_sc_dom = m5_obj["scaler_dom"].transform(feats_df)
        x_fuse = np.hstack([x_sc_sbert, x_sc_dom])
        _ = m5_obj["model"].predict_proba(x_fuse)
        
    latencies_m5 = []
    latencies_m5_sbert_only = []
    latencies_m5_domain_only = []
    
    for i in range(len(sample_pairs)):
        row = sample_pairs.iloc[i]
        t_start = time.perf_counter()
        
        # Step 1: SBERT Encoding
        t_sb0 = time.perf_counter()
        u = sbert_model.encode([row["resume_text"]], normalize_embeddings=True)[0]
        v = sbert_model.encode([row["job_description_text"]], normalize_embeddings=True)[0]
        cos = np.dot(u, v).reshape(1, 1)
        x_sbert = np.hstack([u, v, u * v, np.abs(u - v), cos.flatten()]).reshape(1, -1)
        t_sb1 = time.perf_counter()
        latencies_m5_sbert_only.append((t_sb1 - t_sb0) * 1000.0)
        
        # Step 2: Domain Feature Extraction
        t_dm0 = time.perf_counter()
        d_feats = extractor_m5.extract_pair_features(row["resume_text"], row["job_description_text"])
        feats_df = pd.DataFrame([d_feats])[m5_obj["domain_feature_names"]]
        t_dm1 = time.perf_counter()
        latencies_m5_domain_only.append((t_dm1 - t_dm0) * 1000.0)
        
        # Step 3: Scaling & Classification
        x_sc_sbert = m5_obj["scaler_sbert"].transform(x_sbert)
        x_sc_dom = m5_obj["scaler_dom"].transform(feats_df)
        x_fuse = np.hstack([x_sc_sbert, x_sc_dom])
        _ = m5_obj["model"].predict_proba(x_fuse)
        t_end = time.perf_counter()
        
        latencies_m5.append((t_end - t_start) * 1000.0)
        
    rss_peak_m5 = process.memory_info().rss / (1024 * 1024)
    
    m5_metrics = {
        "model_name": "Model 5: Semantic & Structured-Feature Fusion Challenger",
        "deployable_artifact_bytes": total_size_m5,
        "deployable_artifact_mb": round(total_size_m5 / (1024 * 1024), 2),
        "transformer_weights_mb": round(size_sbert / (1024 * 1024), 2),
        "classifier_head_kb": round(size_m5_joblib / 1024, 1),
        "external_transformer_weights_required": True,
        "cold_start_load_ms": round(cold_start_m5_ms, 2),
        "post_load_rss_mb": round(rss_after_load_m5, 2),
        "peak_rss_mb": round(rss_peak_m5, 2),
        "latency_mean_ms": round(float(np.mean(latencies_m5)), 3),
        "latency_p50_ms": round(float(np.percentile(latencies_m5, 50)), 3),
        "latency_p95_ms": round(float(np.percentile(latencies_m5, 95)), 3),
        "latency_p99_ms": round(float(np.percentile(latencies_m5, 99)), 3),
        "component_breakdown_ms": {
            "sbert_encoding_mean_ms": round(float(np.mean(latencies_m5_sbert_only)), 3),
            "domain_features_mean_ms": round(float(np.mean(latencies_m5_domain_only)), 3),
            "classifier_head_mean_ms": round(float(np.mean(latencies_m5)) - float(np.mean(latencies_m5_sbert_only)) - float(np.mean(latencies_m5_domain_only)), 3)
        }
    }
    print(f"  Deployable Size: {m5_metrics['deployable_artifact_mb']} MB (SBERT: {m5_metrics['transformer_weights_mb']} MB, Classifier: {m5_metrics['classifier_head_kb']} KB)")
    print(f"  Cold Start:      {m5_metrics['cold_start_load_ms']} ms")
    print(f"  Mean Latency:    {m5_metrics['latency_mean_ms']} ms/pair (p50: {m5_metrics['latency_p50_ms']}, p95: {m5_metrics['latency_p95_ms']}, p99: {m5_metrics['latency_p99_ms']})")
    print(f"    - SBERT Encoding: {m5_metrics['component_breakdown_ms']['sbert_encoding_mean_ms']} ms")
    print(f"    - Domain Extract: {m5_metrics['component_breakdown_ms']['domain_features_mean_ms']} ms")
    print(f"    - Classify Head:  {m5_metrics['component_breakdown_ms']['classifier_head_mean_ms']} ms")
    print(f"  Peak Process RSS:{m5_metrics['peak_rss_mb']} MB")

    benchmark_summary = {
        "audit_phase": "Phase 13.1",
        "task": "Task 6 — Correct Performance Measurements (End-to-End Inference)",
        "sample_size": len(sample_pairs),
        "hardware_environment": {
            "cpu_cores": psutil.cpu_count(logical=True),
            "platform": sys.platform
        },
        "models": {
            "production_baseline": prod_metrics,
            "skill_aware_matching": m4_metrics,
            "semantic_skill_fusion_challenger": m5_metrics
        }
    }
    
    out_path = REPO_ROOT / "experiments" / "phase13_1" / "results" / "end_to_end_latency_benchmark.json"
    with open(out_path, "w") as f:
        json.dump(benchmark_summary, f, indent=2)
    print(f"\nSaved complete benchmark summary: {out_path}")

if __name__ == "__main__":
    main()
