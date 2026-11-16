"""
Phase 4.2 Test Suite: Final Career Mentor Evidence Integrity Audit & CSRF Protection.

Mandatory Test Areas:
1. Correct registry-derived role scoring:
   - Registry-derived competencies without source excerpts must receive 60% factor (0.60), NOT full demonstrated weight.
   - Traceable demonstrated: 1.0 (100%).
   - Candidate-confirmed: 0.75 (75%).
   - Registry-derived: 0.60 (60%).
   - Partially evidenced: 0.50 (50%).
   - Proves registry-only skill cannot receive full demonstrated credit.
2. Removal of invented implementation claims from resume advisor:
   - Zero occurrences of 'scalable caching', 'asynchronous task queuing', or 'PostgreSQL schema and composite B-Tree indexes'.
   - Templates use honest placeholders and instructions requiring description of only work actually performed.
3. CSRF fail-closed policy:
   - In production mode (TESTING=False), missing session CSRF token fails closed (403).
   - Missing request token with session token present fails closed (403).
   - Invalid request token fails closed (403).
   - Valid matching CSRF token succeeds (200).
   - Test mode exceptions remain isolated.
4. Safe analysis_id validation:
   - Numbers, objects, arrays, and whitespace strings return controlled 400 Bad Request without unhandled exceptions.
   - Unknown string IDs return controlled 404 Not Found.
   - Unauthorized string IDs return controlled 403 Forbidden.
"""

import json
import secrets
import pytest
from app import app, ANALYSIS_CACHE
from src.mentor.career_profile import build_structured_career_profile
from src.mentor.role_recommender import (
    recommend_suitable_roles,
    evaluate_specific_role,
    ROLE_ARCHETYPES
)
from src.mentor.resume_advisor import generate_resume_improvement_suggestions
from src.mentor.career_roadmap import generate_structured_career_roadmap

app.config["TESTING"] = True


# ---------------------------------------------------------------------------
# Test 1: Registry-Derived Competency Scoring Tier
# ---------------------------------------------------------------------------

def test_registry_derived_skill_scoring_tier():
    """Verify registry-derived skills without source excerpts receive 60% weight, not full credit."""
    # Analysis with one traceable skill (Python), one candidate-confirmed (SQL), and one registry-only (Docker)
    analysis_registry_test = {
        "candidate_profile": {
            "name": {"full_name": "Test Candidate"},
            "skills": [
                {"name": "Python", "category": "Programming Languages"},
                {"name": "Docker", "category": "DevOps & Cloud"}
            ],
            "education": []
        },
        "projects": [
            {
                "title": "Data Pipeline",
                "technologies": ["Python"],
                "description": "Engineered core data parsing service using Python with unit tests."
            }
        ],
        "solidly_evidenced_skills": ["Docker"],
        "user_confirmations": {"SQL": {"status": "confirmed"}}
    }

    profile = build_structured_career_profile(analysis_registry_test)

    # 1. Inspect profile competencies
    skills_map = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    python_comp = skills_map.get("python")
    docker_comp = skills_map.get("docker")

    assert python_comp is not None
    assert python_comp["evidence_source"] == "project"
    assert python_comp["excerpt_status"] == "available"
    assert python_comp["confidence"] >= 0.90

    assert docker_comp is not None
    assert docker_comp["evidence_source"] == "registry_derived"
    assert docker_comp["excerpt_status"] == "unavailable"
    assert docker_comp["confidence"] == 0.60
    assert "Registry-derived" in docker_comp["provenance_note"]

    # Verify separated collections
    assert any(s["skill"] == "Docker" for s in profile["registry_derived_competencies"])
    assert not any(s["skill"] == "Docker" for s in profile["traceable_demonstrated_competencies"])
    assert any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])

    # 2. Evaluate against a custom role that requires Python and Docker as core skills (weight 1.5 each)
    custom_role_reqs = {
        "name": "DevOps Junior",
        "description": "Junior DevOps role",
        "core_skills": ["Python", "Docker"],
        "supporting_skills": [],
        "min_experience_years": 0.0,
        "required_education_level": "none"
    }

    eval_result = evaluate_specific_role("DevOps Junior", profile, analysis_registry_test, custom_role_requirements=custom_role_reqs)

    # Max possible score = 100.0% (if both were full demonstrated)
    # Python (traceable demonstrated) = 1.5 * 1.0 = 1.5
    # Docker (registry-derived without excerpt) = 1.5 * 0.60 = 0.90
    # Earned = 2.40 / 3.00 = 80.0%
    assert eval_result["match_score"] == 80.0
    assert eval_result["match_score"] < 100.0
    assert set(eval_result["matching_skills"]) == {"Python", "Docker"}

    # Compare with a hypothetical profile where Docker is fully evidenced in a project
    analysis_full_demonstrated = {
        "candidate_profile": {
            "name": {"full_name": "Test Candidate"},
            "skills": [
                {"name": "Python", "category": "Programming Languages"},
                {"name": "Docker", "category": "DevOps & Cloud"}
            ],
            "education": []
        },
        "projects": [
            {
                "title": "Data Pipeline",
                "technologies": ["Python", "Docker"],
                "description": "Engineered core data parsing service using Python and Docker containers."
            }
        ]
    }
    profile_full = build_structured_career_profile(analysis_full_demonstrated)
    eval_full = evaluate_specific_role("DevOps Junior", profile_full, analysis_full_demonstrated, custom_role_requirements=custom_role_reqs)
    assert eval_full["match_score"] == 100.0

    # Registry-derived score (80.0%) is strictly lower than fully demonstrated score (100.0%)
    assert eval_result["match_score"] < eval_full["match_score"]

    # Compare with candidate-confirmed Docker: 1.5 + (1.5 * 0.75) = 2.625 / 3.0 = 87.5%
    analysis_cand_confirmed = {
        "candidate_profile": {"name": {"full_name": "Test Candidate"}, "skills": [], "education": []},
        "projects": [
            {
                "title": "Data Pipeline",
                "technologies": ["Python"],
                "description": "Engineered core data parsing service using Python with unit tests."
            }
        ],
        "user_confirmations": {"Docker": {"status": "confirmed"}}
    }
    profile_confirmed = build_structured_career_profile(analysis_cand_confirmed)
    eval_confirmed = evaluate_specific_role("DevOps Junior", profile_confirmed, analysis_cand_confirmed, custom_role_requirements=custom_role_reqs)
    assert eval_confirmed["match_score"] == 87.5

    # Verify strict tier ordering: Missing (50.0%) < Partial (75.0%) < Registry (80.0%) < Confirmed (87.5%) < Full (100.0%)
    assert eval_result["match_score"] < eval_confirmed["match_score"] < eval_full["match_score"]


# ---------------------------------------------------------------------------
# Test 2: Resume Advisor - Removal of Invented Implementation Claims
# ---------------------------------------------------------------------------

def test_resume_advisor_no_invented_activities():
    """Verify suggestions contain no invented claims (caching, queuing, B-tree indexes) and require actual work."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Junior Developer"},
            "projects": [
                {
                    "title": "Basic Portfolio Site",
                    "technologies": ["HTML", "CSS"],
                    "description": "Worked on a static portfolio website."
                }
            ],
            "skills": [
                {"name": "HTML", "category": "Frontend"},
                {"name": "CSS", "category": "Frontend"}
            ]
        },
        "resume_skills": ["HTML", "CSS", "SQL", "Docker"],
        "partially_evidenced_skills": ["SQL", "Docker"]
    }

    profile = build_structured_career_profile(analysis)
    suggestions = generate_resume_improvement_suggestions(profile, analysis)

    assert len(suggestions) > 0

    all_text = []
    for sugg in suggestions:
        all_text.append(str(sugg.get("reason", "")))
        all_text.append(str(sugg.get("instruction", "")))
        all_text.append(str(sugg.get("evidence_context", "")))
        all_text.append(str(sugg.get("practical_next_action", "")))
        act_ex = sugg.get("actionable_example", {})
        all_text.append(str(act_ex.get("before", "")))
        all_text.append(str(act_ex.get("after", "")))
        for be in sugg.get("before_after_examples", []):
            all_text.append(str(be.get("original", "")))
            all_text.append(str(be.get("suggested", "")))
            all_text.append(str(be.get("rationale", "")))

    combined_text = " ".join(all_text).lower()

    # Prohibited invented claims must not appear anywhere:
    assert "scalable caching" not in combined_text, "Found forbidden 'scalable caching'"
    assert "asynchronous task queuing" not in combined_text, "Found forbidden 'asynchronous task queuing'"
    assert "composite b-tree" not in combined_text, "Found forbidden 'composite B-Tree'"
    assert "postgresql schema" not in combined_text, "Found forbidden 'PostgreSQL schema'"

    # Verify that the suggested rewrites instruct candidate to describe only work actually performed
    assert "describe only work actually performed" in combined_text or "[actual component or task]" in combined_text
    assert "describe only features, tasks, or modules you genuinely built" in combined_text or "insert only measured, verifiable values" in combined_text


# ---------------------------------------------------------------------------
# Test 3: CSRF Fail-Closed Policy in Production & Test Modes
# ---------------------------------------------------------------------------

def test_csrf_fail_closed_production():
    """Verify POST /api/career-mentor/evaluate-role fails closed on missing/invalid CSRF tokens when TESTING=False."""
    client = app.test_client()

    test_aid = "csrf_test_aid_001"
    ANALYSIS_CACHE[test_aid] = {
        "candidate_profile": {"name": {"full_name": "Test CSRF"}, "skills": [], "projects": []},
        "resume_skills": []
    }

    # Temporarily switch to production mode (TESTING=False)
    original_testing = app.config.get("TESTING")
    try:
        app.config["TESTING"] = False

        # Case A: Missing session CSRF token -> 403 Forbidden
        with client.session_transaction() as sess:
            sess["allowed_analyses"] = [test_aid]
            # No csrf_token in session
            sess.pop("csrf_token", None)

        resp_no_session_csrf = client.post(
            "/api/career-mentor/evaluate-role",
            data=json.dumps({"role_name": "Backend Engineer", "analysis_id": test_aid}),
            content_type="application/json",
            headers={"X-CSRF-Token": "some_random_token"}
        )
        assert resp_no_session_csrf.status_code == 403
        assert "CSRF token missing or invalid" in resp_no_session_csrf.get_json()["message"]

        # Case B: Session has CSRF token, but request has no CSRF token -> 403 Forbidden
        token = secrets.token_hex(32)
        with client.session_transaction() as sess:
            sess["allowed_analyses"] = [test_aid]
            sess["csrf_token"] = token

        resp_no_request_csrf = client.post(
            "/api/career-mentor/evaluate-role",
            data=json.dumps({"role_name": "Backend Engineer", "analysis_id": test_aid}),
            content_type="application/json"
        )
        assert resp_no_request_csrf.status_code == 403
        assert "CSRF token missing or invalid" in resp_no_request_csrf.get_json()["message"]

        # Case C: Invalid request CSRF token -> 403 Forbidden
        resp_invalid_csrf = client.post(
            "/api/career-mentor/evaluate-role",
            data=json.dumps({"role_name": "Backend Engineer", "analysis_id": test_aid}),
            content_type="application/json",
            headers={"X-CSRF-Token": "completely_invalid_token"}
        )
        assert resp_invalid_csrf.status_code == 403
        assert "CSRF token missing or invalid" in resp_invalid_csrf.get_json()["message"]

        # Case D: Valid CSRF token in header -> 200 OK
        resp_valid_header = client.post(
            "/api/career-mentor/evaluate-role",
            data=json.dumps({"role_name": "Backend Engineer", "analysis_id": test_aid}),
            content_type="application/json",
            headers={"X-CSRF-Token": token}
        )
        assert resp_valid_header.status_code == 200
        assert resp_valid_header.get_json()["status"] == "success"

        # Case E: Valid CSRF token in JSON body -> 200 OK
        resp_valid_body = client.post(
            "/api/career-mentor/evaluate-role",
            data=json.dumps({"role_name": "Backend Engineer", "analysis_id": test_aid, "csrf_token": token}),
            content_type="application/json"
        )
        assert resp_valid_body.status_code == 200
        assert resp_valid_body.get_json()["status"] == "success"

    finally:
        app.config["TESTING"] = original_testing


# ---------------------------------------------------------------------------
# Test 4: Safe analysis_id Validation
# ---------------------------------------------------------------------------

def test_analysis_id_safe_validation():
    """Verify safe analysis_id validation: rejects non-string types with 400, preserves 404/403."""
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["allowed_analyses"] = ["valid_auth_aid_001"]

    ANALYSIS_CACHE["valid_auth_aid_001"] = {
        "candidate_profile": {"name": {"full_name": "Authorized Candidate"}, "skills": [], "projects": []},
        "resume_skills": []
    }
    ANALYSIS_CACHE["unauthorized_aid_999"] = {
        "candidate_profile": {"name": {"full_name": "Other Candidate"}, "skills": [], "projects": []},
        "resume_skills": []
    }

    # 1. Non-string types return 400 Bad Request
    invalid_cases = [
        12345,
        12.34,
        {"id": "valid_auth_aid_001"},
        ["valid_auth_aid_001"],
        True,
        "",
        "   "
    ]

    for val in invalid_cases:
        resp = client.post(
            "/api/career-mentor/evaluate-role",
            data=json.dumps({"role_name": "Backend Engineer", "analysis_id": val}),
            content_type="application/json"
        )
        assert resp.status_code == 400, f"Expected 400 for analysis_id={val!r}, got {resp.status_code}"
        assert "Invalid analysis_id parameter" in resp.get_json()["message"]

    # 2. Unknown string ID returns 404 Not Found
    resp_404 = client.post(
        "/api/career-mentor/evaluate-role",
        data=json.dumps({"role_name": "Backend Engineer", "analysis_id": "non_existent_id_abc"}),
        content_type="application/json"
    )
    assert resp_404.status_code == 404
    assert "not found" in resp_404.get_json()["message"].lower()

    # 3. Unauthorized string ID returns 403 Forbidden
    resp_403 = client.post(
        "/api/career-mentor/evaluate-role",
        data=json.dumps({"role_name": "Backend Engineer", "analysis_id": "unauthorized_aid_999"}),
        content_type="application/json"
    )
    assert resp_403.status_code == 403
    assert "Unauthorized access" in resp_403.get_json()["message"]

    # 4. Authorized valid string ID returns 200 OK
    resp_200 = client.post(
        "/api/career-mentor/evaluate-role",
        data=json.dumps({"role_name": "Backend Engineer", "analysis_id": "valid_auth_aid_001"}),
        content_type="application/json"
    )
    assert resp_200.status_code == 200
    assert resp_200.get_json()["status"] == "success"
