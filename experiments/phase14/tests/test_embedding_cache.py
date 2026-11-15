"""
experiments/phase14/tests/test_embedding_cache.py
Comprehensive automated verification test suite for Phase 14:
1. Cache hits and misses.
2. Cache invalidation on text change.
3. Cache invalidation on encoder version change.
4. Persistence across cache instance re-initialization.
5. Concurrency protection (zero duplicate encoding under simultaneous race condition).
6. Separate resume and job namespaces.
7. Exact numerical equivalence between cached and uncached inference (atol=1e-5).
8. Validation label isolation (no labels passed or used).
9. Production checkpoint integrity (hashes untouched).
"""

import time
import hashlib
import threading
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

REPO_ROOT = Path("D:/skillsync1")
from experiments.phase14.src.embedding_cache import (
    PersistentEmbeddingCache,
    normalize_text_for_caching,
    compute_deterministic_cache_key
)
from experiments.phase14.src.inference_engine import (
    OptimizedInferenceEngine,
    ProfileExtractor
)

PROD_FILES = {
    "models/best_model.joblib": (61487, "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"),
    "models/feature_pipeline.joblib": (270105, "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"),
    "models/phase12f/challenger_model_phase12f.joblib": (2330440, "5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766")
}

@pytest.fixture
def temp_cache_db(tmp_path):
    """Provides a fresh temporary SQLite cache database for test isolation."""
    db_file = tmp_path / "test_cache.sqlite"
    return str(db_file)

def test_production_artifacts_unmodified():
    """Verify that production files have not been overwritten or altered."""
    for rel_path, (expected_size, expected_hash) in PROD_FILES.items():
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"Missing production artifact: {rel_path}"
        data = file_path.read_bytes()
        assert len(data) == expected_size, f"Size mismatch for {rel_path}: {len(data)} != {expected_size}"
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"

def test_text_normalization_determinism():
    """Verify text normalization is robust to whitespace, unicode NFKC, and newlines."""
    raw_1 = "  Senior Python Developer\n\nExperience: 5+ years   "
    raw_2 = "senior python developer\r\n\r\nexperience: 5+ years"
    n1 = normalize_text_for_caching(raw_1)
    n2 = normalize_text_for_caching(raw_2)
    assert n1 == n2
    assert "  " not in n1
    assert "\r" not in n1

def test_cache_hits_and_misses(temp_cache_db):
    """Verify cache miss triggers encoder and cache hit returns identical array without encoding."""
    cache = PersistentEmbeddingCache(db_path=temp_cache_db)
    encode_count = 0

    def mock_encoder(text):
        nonlocal encode_count
        encode_count += 1
        return np.ones(384, dtype=np.float32) * 0.42

    text = "Machine Learning Engineer with PyTorch experience"
    
    # 1. First call: Cache miss
    emb1, meta1, was_hit1 = cache.get_or_encode(text, mock_encoder, entity_type="resume")
    assert not was_hit1
    assert encode_count == 1
    assert emb1.shape == (384,)
    assert np.isclose(emb1[0], 0.42)

    # 2. Second call: Cache hit
    emb2, meta2, was_hit2 = cache.get_or_encode(text, mock_encoder, entity_type="resume")
    assert was_hit2
    assert encode_count == 1  # No second encoding!
    assert np.array_equal(emb1, emb2)

def test_separate_resume_and_job_namespaces(temp_cache_db):
    """Verify that identical text in resume vs job gets stored under distinct cache keys."""
    cache = PersistentEmbeddingCache(db_path=temp_cache_db)
    text = "Python developer specializing in backend distributed systems"
    
    emb_res = np.ones(384, dtype=np.float32) * 1.0
    emb_job = np.ones(384, dtype=np.float32) * 2.0

    key_res = cache.set(text, emb_res, entity_type="resume")
    key_job = cache.set(text, emb_job, entity_type="job")

    assert key_res != key_job, "Resume and job keys must be distinct"

    ret_res = cache.get(text, entity_type="resume")
    ret_job = cache.get(text, entity_type="job")

    assert ret_res is not None and ret_job is not None
    assert np.isclose(ret_res[0][0], 1.0)
    assert np.isclose(ret_job[0][0], 2.0)

def test_cache_invalidation_on_text_change(temp_cache_db):
    """Verify modifying text generates a different cache key and does not return old entry."""
    cache = PersistentEmbeddingCache(db_path=temp_cache_db)
    text_v1 = "Software engineer with Java"
    text_v2 = "Software engineer with Python"

    cache.set(text_v1, np.ones(384, dtype=np.float32), entity_type="resume")
    assert cache.get(text_v1, entity_type="resume") is not None
    assert cache.get(text_v2, entity_type="resume") is None

    # Invalidate text_v1
    deleted = cache.invalidate(text_v1, entity_type="resume")
    assert deleted
    assert cache.get(text_v1, entity_type="resume") is None

def test_cache_invalidation_on_encoder_version_change(temp_cache_db):
    """Verify changing encoder version invalidates lookups for the old version."""
    cache_v1 = PersistentEmbeddingCache(db_path=temp_cache_db, encoder_version="sbert:v1")
    text = "Data Scientist with NLP expertise"
    cache_v1.set(text, np.ones(384, dtype=np.float32), entity_type="resume")

    assert cache_v1.get(text, entity_type="resume") is not None

    # New cache instance with encoder_version="sbert:v2"
    cache_v2 = PersistentEmbeddingCache(db_path=temp_cache_db, encoder_version="sbert:v2")
    assert cache_v2.get(text, entity_type="resume") is None, "Version mismatch must result in cache miss"

def test_cache_persistence_across_instances(temp_cache_db):
    """Verify embeddings persist to disk and can be retrieved by a completely new cache instance."""
    text = "Full Stack Engineer React and Node.js"
    expected_emb = np.linspace(0, 1, 384, dtype=np.float32)

    # Instance 1 writes to DB
    cache1 = PersistentEmbeddingCache(db_path=temp_cache_db)
    cache1.set(text, expected_emb, entity_type="resume", metadata={"skills": ["React", "Node.js"]})
    del cache1

    # Instance 2 reads from DB
    cache2 = PersistentEmbeddingCache(db_path=temp_cache_db)
    retrieved = cache2.get(text, entity_type="resume")
    assert retrieved is not None
    emb_ret, meta_ret = retrieved
    assert np.allclose(emb_ret, expected_emb)
    assert meta_ret["skills"] == ["React", "Node.js"]

def test_concurrency_and_race_condition_prevention(temp_cache_db):
    """
    Simulate 10 concurrent threads simultaneously requesting the SAME uncached text.
    Assert that the heavy encoder function is called EXACTLY ONCE.
    """
    cache = PersistentEmbeddingCache(db_path=temp_cache_db)
    encode_call_count = 0
    call_lock = threading.Lock()

    def heavy_encoder(text):
        nonlocal encode_call_count
        with call_lock:
            encode_call_count += 1
        time.sleep(0.05)  # Simulate transformer encoding time
        return np.ones(384, dtype=np.float32) * 7.7

    text = "Concurrent requests benchmark candidate resume text"
    results = [None] * 10

    def worker(idx):
        emb, meta, hit = cache.get_or_encode(text, heavy_encoder, entity_type="resume")
        results[idx] = (emb, hit)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # The encoder function must have been called EXACTLY ONCE despite 10 concurrent requests
    assert encode_call_count == 1, f"Expected 1 encoder call, got {encode_call_count}"
    for emb, hit in results:
        assert emb is not None
        assert np.isclose(emb[0], 7.7)

def test_inference_prediction_numerical_equivalence(temp_cache_db):
    """
    Verify that cached inference and uncached inference produce:
    1. Identical predicted class.
    2. Identical probabilities within np.allclose(atol=1e-5).
    """
    engine = OptimizedInferenceEngine(cache_db_path=temp_cache_db)

    # 3 representative resume-job pairs
    pairs = [
        (
            "Experienced Python backend engineer with 6 years designing microservices, Docker, Kubernetes, and PostgreSQL.",
            "Senior Backend Engineer required. Must have 5+ years Python, Docker, Kubernetes, microservices architecture, and SQL databases."
        ),
        (
            "Junior Graphic Designer proficient in Photoshop, Illustrator, Figma, and creative branding.",
            "Staff DevOps Engineer needed for AWS Cloud infrastructure, Terraform, CI/CD pipelines, and Linux administration."
        ),
        (
            "Data Analyst with SQL, Tableau, and basic Python data visualization skills.",
            "Data Scientist position requiring machine learning, Python, SQL, and predictive modeling experience."
        )
    ]

    for resume_text, job_text in pairs:
        # 1. Uncached prediction (direct SBERT + direct feature extraction)
        res_uncached = engine.predict(resume_text, job_text, use_cache=False)
        
        # 2. First cached prediction (populates cache)
        res_cached_miss = engine.predict(resume_text, job_text, use_cache=True)

        # 3. Second cached prediction (pure cache hit)
        res_cached_hit = engine.predict(resume_text, job_text, use_cache=True)

        # Assert identical predicted classes
        assert res_uncached["predicted_class"] == res_cached_hit["predicted_class"], (
            f"Class mismatch: {res_uncached['predicted_class']} vs {res_cached_hit['predicted_class']}"
        )

        # Assert probabilities equivalent within 1e-5 numerical tolerance
        for c in ["No Fit", "Potential Fit", "Good Fit"]:
            p_un = res_uncached["probabilities"][c]
            p_ca = res_cached_hit["probabilities"][c]
            assert np.isclose(p_un, p_ca, atol=1e-5), f"Probability mismatch for {c}: {p_un} vs {p_ca}"

        # Assert cache hits on warm call
        assert res_cached_hit["cache_status"]["both_hit"] is True
        assert res_cached_hit["latency_ms"] < res_uncached["latency_ms"]

def test_zero_validation_labels_in_inference():
    """Verify that inference functions accept only text and contain no ground truth label leakage."""
    import inspect
    engine = OptimizedInferenceEngine
    sig = inspect.signature(engine.predict)
    param_names = list(sig.parameters.keys())
    assert "label" not in param_names
    assert "y_true" not in param_names
    assert "target" not in param_names
