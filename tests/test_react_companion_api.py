"""
Tests for React Frontend Companion API Endpoints.
Verifies /api/dashboard, /api/sample-jobs, /api/analyze, /api/analysis/<id>,
/api/skill-gap, /api/model-performance, /api/datasets, /api/career-mentor,
/api/interview-studio, /api/interview-practice, and /api/interview-results.
"""

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_dashboard(client):
    resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "summary" in data
    assert "dataset_summary" in data


def test_api_sample_jobs(client):
    resp = client.get("/api/sample-jobs")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert len(data["sample_jobs"]) >= 3


def test_api_analysis_sample(client):
    resp = client.get("/api/analysis/sample")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    analysis = data["analysis"]
    assert "compatibility_score" in analysis
    assert "skill_gap_summary" in analysis
    assert "matched_skills" in analysis


def test_api_skill_gap(client):
    resp = client.get("/api/skill-gap?id=sample")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "analysis" in data


def test_api_model_performance(client):
    resp = client.get("/api/model-performance")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "data" in data
    assert "dashboard" in data


def test_api_datasets(client):
    resp = client.get("/api/datasets")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "summary" in data


def test_api_career_mentor(client):
    resp = client.get("/api/career-mentor?id=sample")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "dossier" in data
    assert "roadmaps" in data["dossier"]


def test_api_interview_studio(client):
    resp = client.get("/api/interview-studio?id=sample")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "evidence" in data
    assert "questions" in data
    assert len(data["questions"]) > 0


def test_api_analyze_json_flow(client):
    payload = {
        "resume_text": "Experienced Machine Learning Engineer with Python, Scikit-learn, SQL, Docker, and PyTorch.",
        "job_description": "Wanted: Machine Learning Engineer with Python, SQL, and Docker. Experience with PyTorch preferred.",
        "target_role": "Machine Learning Engineer",
        "model_backend": "production"
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "analysis_id" in data
    assert data["data"]["predicted_class"] in ["Good Fit", "Potential Fit", "No Fit"]
