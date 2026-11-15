"""
Unit and Integration Tests for Durable SQLite Analysis Persistence and Authorization.
Verifies Phase 2 Requirements:
1. Durable analysis persistence across memory cache clearing (SQLite L2 fallback).
2. Strict session authorization (cross-session access rejected with 403 Forbidden).
3. Non-existent IDs rejected with 404 Not Found (never silently returns demo data).
4. Explicit demo/sample identifier returns authentic demo candidate with is_demo=True.
5. Session continuity (subsequent queries without ?id= use active session analysis).
6. Pruning and JSON serialization integrity (zero pickle).
"""

import json
import pytest
from app import app, ANALYSIS_CACHE
from src.services.analysis_store import AnalysisStore, get_analysis_store


@pytest.fixture(autouse=True)
def set_testing_mode():
    app.config["TESTING"] = True
    yield


@pytest.fixture
def clean_store(tmp_path):
    """Provides a fresh isolated AnalysisStore in a temporary directory."""
    test_db = tmp_path / "test_analysis.sqlite"
    store = AnalysisStore(db_path=str(test_db), max_records=5)
    return store


def test_sqlite_store_crud_and_serialization(clean_store):
    """Verify SQLite store CRUD operations with strict JSON serialization."""
    sample_data = {
        "analysis_id": "test-uuid-001",
        "job_title": "Python Engineer",
        "compatibility_score": 89.5,
        "is_demo": False,
        "matched_skills": ["Python", "Docker"]
    }
    # 1. Save
    clean_store.save("test-uuid-001", sample_data, session_id="sess_abc")
    assert clean_store.has("test-uuid-001") is True
    assert clean_store.count() == 1

    # 2. Get
    loaded = clean_store.get("test-uuid-001")
    assert loaded is not None
    assert loaded["analysis_id"] == "test-uuid-001"
    assert loaded["job_title"] == "Python Engineer"
    assert loaded["compatibility_score"] == 89.5

    # 3. Capacity pruning
    for i in range(2, 8):
        clean_store.save(f"test-uuid-{i:03d}", {"analysis_id": f"test-uuid-{i:03d}", "val": i})

    # Should have pruned oldest entries to respect max_records=5
    assert clean_store.count() <= 5
    # Earliest entry should be pruned
    assert clean_store.has("test-uuid-001") is False
    # Most recent entry should exist
    assert clean_store.has("test-uuid-007") is True


def test_analysis_persistence_across_cache_clear():
    """Verify analysis retrieval succeeds from SQLite store after ANALYSIS_CACHE is cleared."""
    with app.test_client() as client:
        payload = {
            "resume_text": "Senior Machine Learning Engineer with Python, Scikit-learn, SQL, Docker, and PyTorch.",
            "job_description": "Seeking Machine Learning Engineer with Python, SQL, Docker, and PyTorch.",
            "target_role": "Machine Learning Engineer"
        }
        create_res = client.post("/api/analyze", json=payload)
        assert create_res.status_code == 200
        analysis_id = create_res.get_json()["analysis_id"]

        # Ensure it exists in in-memory cache
        assert analysis_id in ANALYSIS_CACHE

        # Simulate in-memory cache eviction or worker process restart
        ANALYSIS_CACHE.clear()
        assert analysis_id not in ANALYSIS_CACHE

        # Request via companion API; should transparently recover from SQLite L2 store
        get_res = client.get(f"/api/analysis/{analysis_id}")
        assert get_res.status_code == 200
        body = get_res.get_json()
        assert body["status"] == "success"
        assert body["analysis"]["analysis_id"] == analysis_id
        assert body["analysis"]["job_title"] == "Machine Learning Engineer"

        # Check that ANALYSIS_CACHE was repopulated
        assert analysis_id in ANALYSIS_CACHE


def test_unauthorized_cross_session_access_blocked():
    """Verify that accessing another user's analysis from a different session returns 403 Forbidden."""
    # Session 1: uploads and analyzes resume
    with app.test_client() as client1:
        payload = {
            "resume_text": "Frontend Developer with React, TypeScript, Tailwind CSS, and HTML5.",
            "job_description": "Wanted: Frontend Engineer skilled in React and TypeScript.",
            "target_role": "Frontend Developer"
        }
        res1 = client1.post("/api/analyze", json=payload)
        assert res1.status_code == 200
        analysis_id = res1.get_json()["analysis_id"]

        # Session 1 owner can access analysis
        owner_res = client1.get(f"/api/analysis/{analysis_id}")
        assert owner_res.status_code == 200

    # Session 2: completely separate session (no shared cookie)
    with app.test_client() as client2:
        # Cross-session access to /api/analysis/<id> must be 403
        intruder_analysis = client2.get(f"/api/analysis/{analysis_id}")
        assert intruder_analysis.status_code == 403
        assert "unauthorized" in intruder_analysis.get_json()["error_message"].lower()

        # Cross-session access to /api/skill-gap?id=<id> must be 403
        intruder_skillgap = client2.get(f"/api/skill-gap?id={analysis_id}")
        assert intruder_skillgap.status_code == 403

        # Cross-session access to /api/career-mentor?id=<id> must be 403
        intruder_mentor = client2.get(f"/api/career-mentor?id={analysis_id}")
        assert intruder_mentor.status_code == 403

        # Cross-session access to /api/interview-studio?id=<id> must be 403
        intruder_interview = client2.get(f"/api/interview-studio?id={analysis_id}")
        assert intruder_interview.status_code == 403


def test_nonexistent_analysis_id_returns_404():
    """Verify that requesting an invalid or non-existent ID returns 404 (never silently falls back to sample)."""
    with app.test_client() as client:
        # Non-existent ID on /api/analysis/<id>
        res = client.get("/api/analysis/nonexistent-uuid-99999")
        assert res.status_code == 404
        data = res.get_json()
        assert data["status"] == "error"
        assert "not found" in data["error_message"].lower()

        # Non-existent ID on /api/skill-gap?id=...
        res_sg = client.get("/api/skill-gap?id=nonexistent-uuid-99999")
        assert res_sg.status_code == 404

        # Non-existent ID on /api/career-mentor?id=...
        res_cm = client.get("/api/career-mentor?id=nonexistent-uuid-99999")
        assert res_cm.status_code == 404

        # Non-existent ID on /api/interview-studio?id=...
        res_is = client.get("/api/interview-studio?id=nonexistent-uuid-99999")
        assert res_is.status_code == 404


def test_explicit_demo_sample_identifier():
    """Verify that explicit 'sample' and 'demo' identifiers return authentic demo preview candidate."""
    with app.test_client() as client:
        for demo_key in ("sample", "demo", "sample-preview"):
            res = client.get(f"/api/analysis/{demo_key}")
            assert res.status_code == 200
            data = res.get_json()
            assert data["status"] == "success"
            analysis = data["analysis"]
            assert analysis["is_demo"] is True
            assert "Sample" in analysis["filename"]
            assert "compatibility_score" in analysis


def test_session_continuity_without_id():
    """Verify that requests without ?id= automatically load active analysis from current session."""
    with app.test_client() as client:
        payload = {
            "resume_text": "Cloud Infrastructure Engineer with Kubernetes, Docker, AWS, and Linux.",
            "job_description": "Seeking DevOps Engineer with Kubernetes and AWS experience.",
            "target_role": "Cloud DevOps Engineer"
        }
        res = client.post("/api/analyze", json=payload)
        assert res.status_code == 200
        analysis_id = res.get_json()["analysis_id"]

        # Call /api/skill-gap with NO ?id= parameter
        sg_res = client.get("/api/skill-gap")
        assert sg_res.status_code == 200
        sg_data = sg_res.get_json()
        assert sg_data["analysis"]["analysis_id"] == analysis_id
        assert sg_data["analysis"]["job_title"] == "Cloud DevOps Engineer"

        # Call /api/career-mentor with NO ?id= parameter
        cm_res = client.get("/api/career-mentor")
        assert cm_res.status_code == 200
        cm_data = cm_res.get_json()
        assert "dossier" in cm_data
        assert cm_data["dossier"]["target_role"] == "Cloud DevOps Engineer"
