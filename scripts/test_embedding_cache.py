import os
import numpy as np

cache_path = "results/phase12b_embeddings/minilm_l6_v2_cache.npz"
data = np.load(cache_path, allow_pickle=True)
res_hashes = data["res_hashes"]
job_hashes = data["job_hashes"]
print(f"Loaded cache: {len(res_hashes)} resumes, {len(job_hashes)} jobs.")
print("Sample resume embedding shape:", data[f"res_{res_hashes[0]}"].shape)
print("Sample job embedding shape:", data[f"job_{job_hashes[0]}"].shape)

# Check if sentence-transformers can load or if internet is accessible / local model cached
try:
    from sentence_transformers import SentenceTransformer
    print("Testing sentence_transformers import: SUCCESS")
except Exception as e:
    print("sentence_transformers import failed:", e)
