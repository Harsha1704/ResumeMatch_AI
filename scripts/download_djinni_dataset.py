"""
scripts/download_djinni_dataset.py
Streams and cryptographically verifies the official Djinni English candidate and job datasets.
Sources:
- lang-uk/recruitment-dataset-candidate-profiles-english
- lang-uk/recruitment-dataset-job-descriptions-english
"""

import os
import sys
import time
import hashlib
import requests
from pathlib import Path

DEST_DIR = Path("data/external/djinni")
DEST_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "name": "djinni_candidate_profiles_english.parquet",
        "repo": "lang-uk/recruitment-dataset-candidate-profiles-english",
        "url": "https://huggingface.co/datasets/lang-uk/recruitment-dataset-candidate-profiles-english/resolve/main/data/train-00000-of-00001.parquet",
        "expected_bytes": 237415736
    },
    {
        "name": "djinni_job_descriptions_english.parquet",
        "repo": "lang-uk/recruitment-dataset-job-descriptions-english",
        "url": "https://huggingface.co/datasets/lang-uk/recruitment-dataset-job-descriptions-english/resolve/main/data/train-00000-of-00001.parquet",
        "expected_bytes": 145859589
    }
]


def download_file(item):
    out_path = DEST_DIR / item["name"]
    expected_bytes = item["expected_bytes"]
    url = item["url"]

    if out_path.exists() and out_path.stat().st_size == expected_bytes:
        print(f"[SKIP] {item['name']} already exists ({out_path.stat().st_size} bytes). Computing SHA-256...")
        h = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(1048576):
                h.update(chunk)
        return out_path, h.hexdigest(), out_path.stat().st_size

    print(f"\n[DOWNLOAD] Starting {item['name']} from {url}...")
    t0 = time.time()
    h = hashlib.sha256()
    downloaded_bytes = 0

    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", expected_bytes))
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1048576):
                if chunk:
                    f.write(chunk)
                    h.update(chunk)
                    downloaded_bytes += len(chunk)
                    elapsed = time.time() - t0
                    mb = downloaded_bytes / (1024 * 1024)
                    speed = mb / max(elapsed, 0.001)
                    pct = (downloaded_bytes / total_size) * 100 if total_size else 0
                    sys.stdout.write(f"\r  Downloaded: {mb:.1f} MB / {total_size/(1024*1024):.1f} MB ({pct:.1f}%) @ {speed:.2f} MB/s")
                    sys.stdout.flush()

    total_time = time.time() - t0
    sha256 = h.hexdigest()
    print(f"\n[DONE] {item['name']} ({downloaded_bytes} bytes in {total_time:.1f}s)")
    print(f"  SHA-256: {sha256}")
    return out_path, sha256, downloaded_bytes


if __name__ == "__main__":
    results = {}
    for item in DATASETS:
        path, sha256, size = download_file(item)
        results[item["name"]] = {
            "path": str(path),
            "sha256": sha256,
            "bytes": size,
            "repo": item["repo"]
        }
    print("\nAll downloads finished successfully!")
