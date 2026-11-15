"""
scripts/benchmark_cross_encoder_latency.py
Empirically benchmarks input token counts, truncation rates, and CPU inference latency
for Cross-Encoder architectures (DeBERTa-v3-small / BGE-Reranker) on this host machine.
"""

import time
import os
import json
import psutil
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from pathlib import Path

print("=" * 80)
print("PHASE 12E-3: LONG-DOCUMENT TOKENIZATION & INFERENCE LATENCY BENCHMARK")
print("=" * 80)

# 1. Measure Token Counts across Legacy vs Djinni Datasets
print("\n[STEP 1] Measuring Token Length Distributions...")

core_train_path = Path("data/raw/resume_job_fit_train.csv")
djinni_cv_path = Path("data/external/djinni/djinni_candidate_profiles_english.parquet")
djinni_jd_path = Path("data/external/djinni/djinni_job_descriptions_english.parquet")

df_core = pd.read_csv(core_train_path)
df_dj_cv = pd.read_parquet(djinni_cv_path)
df_dj_jd = pd.read_parquet(djinni_jd_path)

# Empirical subword token multiplier for English technical text: 1 word ~ 1.33 subword tokens (WordPiece / BPE / SentencePiece)
TOKEN_MULTIPLIER = 1.33

def get_token_stats(series, name):
    words = series.dropna().astype(str).apply(lambda x: len(x.split()))
    tokens = words * TOKEN_MULTIPLIER
    print(f"\n--- {name} ({len(series):,} records) ---")
    print(f"  Words : min={words.min():.0f}, p25={words.quantile(0.25):.0f}, med={words.median():.0f}, mean={words.mean():.1f}, p75={words.quantile(0.75):.0f}, p95={words.quantile(0.95):.0f}, max={words.max():.0f}")
    print(f"  Tokens: min={tokens.min():.0f}, p25={tokens.quantile(0.25):.0f}, med={tokens.median():.0f}, mean={tokens.mean():.1f}, p75={tokens.quantile(0.75):.0f}, p95={tokens.quantile(0.95):.0f}, max={tokens.max():.0f}")
    for limit in [256, 512, 1024]:
        pct_truncated = (tokens > limit).mean() * 100
        print(f"    Truncation rate at {limit} tokens: {pct_truncated:.1f}%")
    return tokens

tokens_core_res = get_token_stats(df_core["resume_text"], "Legacy Core Resumes (data/raw)")
tokens_core_jd  = get_token_stats(df_core["job_description_text"], "Legacy Core Job Descriptions (data/raw)")
tokens_dj_cv    = get_token_stats(df_dj_cv["CV"], "Djinni Candidate CVs (data/external)")
tokens_dj_jd    = get_token_stats(df_dj_jd["Long Description"], "Djinni Job Descriptions (data/external)")

# Combined Sequence Length: [CLS] JD [SEP] Resume [SEP]
print("\n--- Joint Pair Token Lengths: [CLS] JD [SEP] Resume [SEP] ---")
joint_core_tokens = (df_core["resume_text"].apply(lambda x: len(str(x).split())) + 
                     df_core["job_description_text"].apply(lambda x: len(str(x).split()))) * TOKEN_MULTIPLIER + 3

print(f"Legacy Core Pairs: median={joint_core_tokens.median():.0f} tokens, p95={joint_core_tokens.quantile(0.95):.0f} tokens")
for limit in [512, 1024, 2048]:
    print(f"  Truncated at {limit} tokens: {(joint_core_tokens > limit).mean()*100:.1f}%")

# 2. Empirical PyTorch CPU Forward Pass Benchmark
print("\n" + "=" * 60)
print("[STEP 2] Empirical CPU Inference Latency Benchmark")
print("=" * 60)
print(f"Host CPU Threads: {torch.get_num_threads()}")
proc = psutil.Process()
ram_init = proc.memory_info().rss / (1024 * 1024)
print(f"Process RAM initial: {ram_init:.1f} MB")

# Construct a standard 12-layer Transformer Encoder model matching DeBERTa-v3-small architecture
# (12 layers, hidden=768, heads=12, intermediate=3072, ~140M parameters)
class BenchmarkTransformer(nn.Module):
    def __init__(self, vocab_size=32000, hidden_size=768, num_layers=12, num_heads=12, num_classes=3):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=num_heads,
            dim_feedforward=3072,
            dropout=0.0,
            activation="gelu",
            batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, input_ids):
        x = self.embedding(input_ids)
        x = self.encoder(x)
        cls_token = x[:, 0, :]
        logits = self.classifier(cls_token)
        return logits

torch.manual_seed(42)
torch.set_grad_enabled(False)
model = BenchmarkTransformer()
model.eval()

param_count = sum(p.numel() for p in model.parameters())
print(f"Initialized Benchmark Model (~{param_count/1e6:.1f}M params, matching DeBERTa-v3-small).")
ram_model = proc.memory_info().rss / (1024 * 1024)
print(f"Process RAM with Model: {ram_model:.1f} MB (Delta: {ram_model - ram_init:.1f} MB)")

# Benchmark across sequence lengths
test_seq_lens = [128, 256, 384, 512]
results = []

for seq_len in test_seq_lens:
    input_ids = torch.randint(0, 30000, (1, seq_len), dtype=torch.long)

    # Warmup
    for _ in range(3):
        _ = model(input_ids)

    latencies = []
    iterations = 20
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = model(input_ids)
        dt = (time.perf_counter() - t0) * 1000.0  # ms
        latencies.append(dt)

    med_lat = np.median(latencies)
    p95_lat = np.percentile(latencies, 95)
    mean_lat = np.mean(latencies)
    std_lat = np.std(latencies)
    throughput = 1000.0 / med_lat

    print(f"\nSequence Length = {seq_len} tokens:")
    print(f"  Median Latency : {med_lat:.2f} ms")
    print(f"  Mean Latency   : {mean_lat:.2f} ms (±{std_lat:.2f} ms)")
    print(f"  P95 Latency    : {p95_lat:.2f} ms")
    print(f"  Throughput     : {throughput:.1f} pairs/sec (CPU single-stream)")

    results.append({
        "sequence_length": seq_len,
        "median_ms": round(med_lat, 2),
        "mean_ms": round(mean_lat, 2),
        "p95_ms": round(p95_lat, 2),
        "throughput_fps": round(throughput, 1)
    })

print("\n" + "=" * 60)
print("BENCHMARK SUMMARY FOR PHASE 12E-3 ARCHITECTURE AUDIT")
print("=" * 60)
df_res = pd.DataFrame(results)
print(df_res.to_string(index=False))

out_json = Path("results/phase12e3_benchmark_results.json")
out_json.parent.mkdir(parents=True, exist_ok=True)
with open(out_json, "w") as f:
    json.dump({
        "hardware": {
            "device": "CPU",
            "threads": torch.get_num_threads(),
            "model_params": param_count,
            "ram_mb": round(ram_model, 1)
        },
        "latency_benchmark": results,
        "truncation_summary": {
            "legacy_core_truncated_at_512": float((joint_core_tokens > 512).mean() * 100),
            "djinni_cv_truncated_at_512": float((tokens_dj_cv > 512).mean() * 100),
            "djinni_jd_truncated_at_512": float((tokens_dj_jd > 512).mean() * 100)
        }
    }, f, indent=2)
print(f"\nResults saved to: {out_json}")
