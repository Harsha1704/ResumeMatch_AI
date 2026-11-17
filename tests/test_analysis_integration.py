"""
End-to-End Integration tests for Flask Resume Analysis routes (/analyze, /results, /health).
"""

import io
import pytest
from app import app, ANALYSIS_CACHE


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_analyze_page_get(client):
    """Verify /analyze renders the submission form."""
    resp = client.get("/analyze")
    assert resp.status_code == 200
    assert b"Resume" in resp.data
    assert b"Job Description" in resp.data


def test_analyze_flow_with_pasted_text(client):
    """Verify POST /analyze with pasted text processes and redirects to /results."""
    tok = client.get("/api/csrf-token").get_json()["csrf_token"]
    form_data = {
        "resume_text": "Senior Developer with 6 years experience in Python, Django, SQL, and Docker.",
        "job_description": "Wanted: Senior Python Engineer with Python, Django, Docker, and Kubernetes. Minimum 5 years exp.",
        "target_role": "Platform Automation Engineer",
        "csrf_token": tok
    }

    resp = client.post("/analyze", data=form_data, follow_redirects=False)
    assert resp.status_code == 302
    assert "/results?id=" in resp.headers["Location"]

    # Follow redirect to results page
    results_url = resp.headers["Location"]
    analysis_id = results_url.rsplit("=", 1)[-1]
    cached_analysis = ANALYSIS_CACHE[analysis_id]
    assert cached_analysis["job_title"] == "Platform Automation Engineer"
    assert cached_analysis["target_role_source"] == "user_override"
    assert cached_analysis["detected_job_title"]
    assert "python" in {skill.lower() for skill in cached_analysis["required_skills"]}

    res_resp = client.get(results_url)
    assert res_resp.status_code == 200
    assert b"Compatibility Score" in res_resp.data
    assert b"Matched Skills" in res_resp.data
    assert b"Resume Improvement Recommendations" in res_resp.data
    assert b"Platform Automation Engineer" in res_resp.data
    assert b"Skill requirements and ML prediction remain based on the supplied job description." in res_resp.data


def test_analyze_flow_with_uploaded_file(client):
    """Verify POST /analyze with uploaded file processes cleanly."""
    file_content = b"Data Scientist with 3 years of experience in Python, Machine Learning, and PyTorch."
    file_bytes = (io.BytesIO(file_content), "candidate_resume.txt")

    tok = client.get("/api/csrf-token").get_json()["csrf_token"]
    form_data = {
        "resume_file": file_bytes,
        "job_description": "Data Scientist required with Python, Machine Learning, Scikit-learn, and AWS.",
        "csrf_token": tok
    }

    resp = client.post("/analyze", data=form_data, content_type="multipart/form-data", follow_redirects=False)
    assert resp.status_code == 302
    assert "/results?id=" in resp.headers["Location"]


def test_empty_submission_validation(client):
    """Verify submitting empty form triggers redirect back with warning."""
    tok = client.get("/api/csrf-token").get_json()["csrf_token"]
    resp = client.post("/analyze", data={"csrf_token": tok}, follow_redirects=True)
    assert resp.status_code == 200
    # Should stay on analyze page
    assert b"Target Job Description" in resp.data


def test_results_expired_or_invalid_id(client):
    """Verify accessing /results with non-existent ID redirects to /analyze."""
    resp = client.get("/results?id=non_existent_uuid_12345", follow_redirects=False)
    assert resp.status_code == 302
    assert "/analyze" in resp.headers["Location"]


def test_unauthorized_session_access_protection():
    """Verify that cross-session access to an analysis without session permission is blocked."""
    app.config["TESTING"] = False
    with app.test_client() as c1:
        # Submit analysis in session 1
        tok1 = c1.get("/api/csrf-token").get_json()["csrf_token"]
        form_data = {
            "resume_text": "Python Developer with 3 years experience.",
            "job_description": "Seeking Python engineer with 2 years experience.",
            "csrf_token": tok1
        }
        res1 = c1.post("/analyze", data=form_data, follow_redirects=False)
        assert res1.status_code == 302
        analysis_url = res1.headers["Location"]
        analysis_id = analysis_url.split("=")[-1]

        # Valid owner can access
        res_owner = c1.get(analysis_url)
        assert res_owner.status_code == 200

    with app.test_client() as c2:
        # Separate session (no cookie/session for this analysis) tries to access analysis_id
        res_intruder = c2.get(f"/results?id={analysis_id}", follow_redirects=False)
        assert res_intruder.status_code == 302
        assert "/analyze" in res_intruder.headers["Location"]

    app.config["TESTING"] = True



def test_target_role_length_validation(client):
    """Reject overly long role overrides before running model inference."""
    tok = client.get("/api/csrf-token").get_json()["csrf_token"]
    form_data = {
        "resume_text": "Senior Developer with Python and Docker experience.",
        "job_description": "Python developer required with Python and Docker.",
        "target_role": "A" * 121,
        "csrf_token": tok
    }
    response = client.post("/analyze", data=form_data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Target role must be 120 characters or fewer." in response.data


def test_api_rejects_non_string_target_role(client):
    """The JSON API accepts only string target-role overrides."""
    response = client.post(
        "/api/match",
        json={
            "resume_text": "Senior Developer with Python and Docker experience.",
            "job_description": "Python developer required with Python and Docker.",
            "target_role": ["not", "a", "string"],
        },
    )
    assert response.status_code == 400
    assert b"'target_role' must be a string" in response.data


def test_api_rejects_overlong_target_role(client):
    """The JSON API enforces the same 120-character role-title limit."""
    response = client.post(
        "/api/match",
        json={
            "resume_text": "Senior Developer with Python and Docker experience.",
            "job_description": "Python developer required with Python and Docker.",
            "target_role": "A" * 121,
        },
    )
    assert response.status_code == 400
    assert b"120 characters or fewer" in response.data
