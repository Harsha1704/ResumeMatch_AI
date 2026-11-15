"""
Frontend Integration and UI Route Verification Tests for ResumeMatch AI.
Ensures templates render correctly with genuine backend context and without template errors.
"""

import pytest
from app import app, ANALYSIS_CACHE


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_dashboard_page_rendering(client):
    """Verify GET / renders ResumeMatch AI branding and real metric cards."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "ResumeMatch AI" in html
    assert "7,999" in html
    assert "Logistic Regression" in html
    assert "50.43%" in html


def test_analyzer_page_rendering(client):
    """Verify GET /analyze renders the drag-and-drop uploader and sample jobs."""
    resp = client.get("/analyze")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Resume File Here" in html
    assert "Target Job Description" in html
    assert "Sample Position" in html


def test_skill_gap_page_empty_and_active_states(client):
    """Verify GET /skill-gap renders clean empty state when no analysis exists."""
    resp = client.get("/skill-gap")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Skill Gap Analytics" in html

    # Inject mock analysis to test active state rendering
    ANALYSIS_CACHE["test_uuid_999"] = {
        "analysis_id": "test_uuid_999",
        "job_title": "Software Engineer",
        "skill_coverage": 75.0,
        "matched_skills": ["python", "docker"],
        "required_skills": ["python", "docker", "kubernetes"],
        "missing_required_skills": ["kubernetes"],
        "missing_preferred_skills": [],
        "partially_evidenced_skills": [],
        "prioritized_gaps": [],
        "learning_resources": []
    }

    resp_active = client.get("/skill-gap?id=test_uuid_999")
    assert resp_active.status_code == 200
    html_active = resp_active.data.decode("utf-8")
    assert "75.0%" in html_active
    assert "Required Skill Coverage" in html_active


def test_model_performance_page_rendering(client):
    """Verify GET /model-performance displays real comparison table and confusion matrices."""
    resp = client.get("/model-performance")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Logistic Regression" in html
    assert "Linear SVM" in html
    assert "Random Forest" in html
    assert "50.43%" in html  # Held-out test accuracy
    assert "0.4664" in html  # Held-out test macro F1
    assert "65.09%" in html  # Unseen resumes accuracy
    assert "confusion_matrix.png" in html


def test_dataset_explorer_page_rendering(client):
    """Verify GET /datasets displays real dataset statistics and image references."""
    resp = client.get("/datasets")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "cnamuangtoun/resume-job-description-fit" in html
    assert "batuhanmtl/job-skill-set" in html
    assert "4,476" in html
    assert "8,000 (6,241 Train / 1,759 Held-Out Test)" in html
    assert "7,999 (6,240 Train / 1,759 Held-Out Test)" in html
    assert "1 exact duplicate training row removed" in html
    assert "476 / 477 Test Resumes (99.79%)" in html
    assert "top_skills_distribution.png" in html
    assert "text_length_distributions.png" in html


def test_static_css_and_js_served(client):
    """Verify critical static CSS and JS files return HTTP 200."""
    static_assets = [
        "/static/css/dashboard.css",
        "/static/js/main.js",
        "/static/js/charts.js",
        "/static/js/analyzer.js",
        "/static/images/class_distribution.png",
        "/static/images/model_comparison.png",
        "/static/images/confusion_matrix.png"
    ]
    for asset in static_assets:
        resp = client.get(asset)
        assert resp.status_code == 200, f"Failed to serve asset: {asset}"
