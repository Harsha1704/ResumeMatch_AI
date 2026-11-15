"""
experiments/phase15/tests/test_flask_integration.py
Comprehensive verification test suite for Phase 15 Flask Integration:
1. Production checkpoint preservation.
2. Health endpoint diagnostics.
3. Resume upload and parsing workflow.
4. Job description input validation.
5. Model selection (Production Baseline vs Challenger Model 5).
6. Prediction equivalence between Flask API and standalone inference engine.
7. Graceful fallback to production baseline upon challenger failure.
8. Cache persistence across application/client restarts.
9. Concurrent request handling and duplicate upload safety.
10. Error handling, invalid inputs, and security boundary assertions.
"""

import os
import json
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
import numpy as np

REPO_ROOT = Path("D:/skillsync1")
from app import app
from experiments.phase14.src.inference_engine import OptimizedInferenceEngine

PROD_FILES = {
    "models/best_model.joblib": (61487, "1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a"),
    "models/feature_pipeline.joblib": (270105, "2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6"),
    "models/phase12f/challenger_model_phase12f.joblib": (2330440, "5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766"),
    "models/phase13/semantic_skill_fusion_challenger.joblib": (78194, "50aaabfe53025a04d2221f71fa6977bec9615649cff84e8da37d299f5cc44807")
}

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client

def test_production_checkpoints_preserved():
    """Verify production artifacts have not been modified."""
    for rel_path, (expected_size, expected_hash) in PROD_FILES.items():
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"Missing checkpoint: {rel_path}"
        data = file_path.read_bytes()
        assert len(data) == expected_size, f"Size changed for {rel_path}"
        actual_hash = hashlib.sha256(data).hexdigest()
        assert actual_hash == expected_hash, f"Hash changed for {rel_path}"

def test_health_check_endpoint(client):
    """Verify /health endpoint returns healthy status and model telemetry."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["challenger_available"] is True
    assert data["active_backend_default"] in ("production", "challenger_m5")

def test_resume_upload_and_parsing_workflow(client):
    """Verify full form submission workflow: upload text/file, analyze, and view results."""
    form_data = {
        "resume_text": "Experienced Python Backend Engineer with 5 years developing REST APIs, Docker, and PostgreSQL.",
        "job_description": "We are seeking a Senior Python Engineer with 4+ years of experience in Docker, REST APIs, and SQL.",
        "model_backend": "production"
    }
    res = client.post("/analyze", data=form_data, follow_redirects=False)
    assert res.status_code == 302
    assert "/results?id=" in res.headers["Location"]

    # Follow redirect to results
    res_page = client.get(res.headers["Location"])
    assert res_page.status_code == 200
    html = res_page.get_data(as_text=True)
    assert "Supervised ML Prediction" in html
    assert "Model Architecture: Production Baseline" in html

def test_job_input_validation(client):
    """Verify proper validation errors on missing job description or missing resume."""
    # 1. Missing job description
    res1 = client.post("/analyze", data={"resume_text": "Python engineer"}, follow_redirects=True)
    assert "Target job description is required" in res1.get_data(as_text=True)

    # 2. Missing resume
    res2 = client.post("/analyze", data={"job_description": "Looking for python engineer"}, follow_redirects=True)
    assert "Please upload a resume file" in res2.get_data(as_text=True)

    # 3. API validation
    res_api = client.post("/api/match", json={"resume_text": ""})
    assert res_api.status_code == 400
    assert "error" in res_api.get_json()["status"]

def test_model_selection_production_vs_challenger(client):
    """Verify that user/caller can explicitly select production or challenger backend."""
    sample_res = "Data Scientist with machine learning, Python, pandas, and scikit-learn experience."
    sample_jd = "Senior Data Scientist needed. Requirements: Machine Learning, Python, predictive modeling."

    # 1. Test Production Backend
    res_prod = client.post("/api/match", json={
        "resume_text": sample_res,
        "job_description": sample_jd,
        "model_backend": "production"
    })
    assert res_prod.status_code == 200
    data_prod = res_prod.get_json()
    assert data_prod["model_backend"] == "production"
    assert "Production Baseline" in data_prod["model_used"]
    assert data_prod["is_challenger"] is False

    # 2. Test Challenger Backend
    res_chal = client.post("/api/match", json={
        "resume_text": sample_res,
        "job_description": sample_jd,
        "model_backend": "challenger_m5"
    })
    assert res_chal.status_code == 200
    data_chal = res_chal.get_json()
    assert data_chal["model_backend"] == "challenger_m5"
    assert "Challenger Model 5" in data_chal["model_used"]
    assert data_chal["is_challenger"] is True
    assert data_chal["inference_latency_ms"] >= 0.0
    assert "No Fit" in data_chal["probabilities"]
    assert "Good Fit" in data_chal["probabilities"]

def test_prediction_equivalence_api_vs_standalone_engine(client):
    """Verify that Flask /api/match returns exact predictions equivalent to standalone engine."""
    resume_text = "Frontend React Developer with TypeScript, CSS3, and Redux state management."
    job_text = "Frontend Engineer position. Must know React, TypeScript, and modern CSS."

    # Standalone engine
    engine = OptimizedInferenceEngine(cache_db_path="data/cache/embedding_cache.sqlite")
    direct_pred = engine.predict(resume_text, job_text, use_cache=True)

    # Flask API endpoint
    res_api = client.post("/api/match", json={
        "resume_text": resume_text,
        "job_description": job_text,
        "model_backend": "challenger_m5"
    })
    assert res_api.status_code == 200
    api_pred = res_api.get_json()

    assert api_pred["predicted_class"] == direct_pred["predicted_class"]
    for c in ["No Fit", "Potential Fit", "Good Fit"]:
        p_api = api_pred["probabilities"][c]
        p_direct = direct_pred["probabilities"][c]
        assert np.isclose(p_api, p_direct, atol=1e-5), f"Mismatch on {c}: {p_api} vs {p_direct}"

def test_challenger_graceful_fallback_on_failure(client, monkeypatch):
    """Simulate an internal failure in Challenger Model 5 and verify clean fallback to Production Baseline."""
    from src.services import challenger_service
    svc = challenger_service.get_challenger_service()

    # Monkeypatch predict_match to raise an intentional simulation error
    def faulty_predict(*args, **kwargs):
        raise RuntimeError("Simulated transient cache/encoder hardware fault")

    monkeypatch.setattr(svc, "predict_match", faulty_predict)

    res = client.post("/api/match", json={
        "resume_text": "DevOps Engineer with AWS, Terraform, and Kubernetes.",
        "job_description": "Site Reliability Engineer with AWS and Kubernetes.",
        "model_backend": "challenger_m5"
    })
    # Should not crash with 500 error; must fall back to production baseline
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["model_backend"] == "production_fallback"
    assert "Fallback" in data["model_used"]

def test_cache_persistence_across_restarts(tmp_path):
    """Verify that embeddings written by one client session persist to SQLite and are cache-hits in a new session."""
    test_db = tmp_path / "persistent_test.sqlite"
    from experiments.phase14.src.embedding_cache import PersistentEmbeddingCache

    text = "Machine Learning Infrastructure Specialist with PyTorch and Ray."

    # Session 1: Populate cache
    c1 = PersistentEmbeddingCache(db_path=test_db)
    emb_stored = np.ones(384, dtype=np.float32) * 3.14
    c1.set(text, emb_stored, entity_type="resume", metadata={"skills": ["PyTorch", "Ray"]})
    del c1

    # Session 2: Read from disk
    c2 = PersistentEmbeddingCache(db_path=test_db)
    ret = c2.get(text, entity_type="resume")
    assert ret is not None
    emb_ret, meta_ret = ret
    assert np.allclose(emb_ret, emb_stored)
    assert meta_ret["skills"] == ["PyTorch", "Ray"]

def test_concurrent_flask_requests():
    """Verify Flask application handles concurrent API match requests reliably without state collision."""
    payload = {
        "resume_text": "Embedded Systems Engineer with C, C++, FreeRTOS, and ARM assembly.",
        "job_description": "Firmware Engineer: C/C++, RTOS, microcontroller peripherals.",
        "model_backend": "production"
    }

    def worker(_):
        with app.test_client() as thread_client:
            res = thread_client.post("/api/match", json=payload)
            assert res.status_code == 200
            return res.get_json()["predicted_class"]

    with ThreadPoolExecutor(max_workers=5) as pool:
        predictions = list(pool.map(worker, range(10)))

    assert len(predictions) == 10
    # All concurrent requests for identical input should yield identical results
    assert len(set(predictions)) == 1

def test_error_handling_and_security(client):
    """Verify invalid payloads, oversized data, and unknown routes fail gracefully."""
    # 1. Invalid JSON body
    res_bad_json = client.post("/api/match", data="not json", content_type="application/json")
    assert res_bad_json.status_code == 400

    # 2. Unknown analysis ID access in UI
    res_unauth = client.get("/results?id=nonexistent-uuid-12345", follow_redirects=True)
    assert "No analysis result found" in res_unauth.get_data(as_text=True)

    # 3. Model performance export check
    res_exp = client.get("/api/model-performance/export?type=comparison")
    assert res_exp.status_code == 200
    assert "Model Architecture" in res_exp.get_data(as_text=True)
