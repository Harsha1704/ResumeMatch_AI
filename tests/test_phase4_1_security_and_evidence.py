"""
Phase 4.1 Test Suite: Career Mentor Security & Evidence-Grounding Corrections.

Mandatory Test Areas:
1. Analysis ownership & session isolation across GET /api/career-mentor and POST /api/career-mentor/evaluate-role:
   - Client A registers analysis A.
   - Client B must not access analysis A by supplying its ID (403 Forbidden).
   - Client A must access its own analysis (200 OK).
   - Unknown analysis IDs return controlled 404 Not Found.
   - Sample/demo IDs return authentic sample preview without data leakage.
   - Omitted analysis ID falls back to session-authorized analysis or sample preview.
2. Removal of fabricated resume achievements:
   - Zero emission of invented numbers (35%, 45ms, 12 API endpoints, 5,000+ daily requests, 99.9% uptime).
   - Verifiable placeholders used instead ([measured throughput], [verified latency]).
   - Explicit instructions requiring measured values from logs/telemetry.
3. Correct custom role evaluation:
   - Custom / unlisted role without requirements returns unevaluated (score is None, tier is Unevaluated).
   - Custom role with structured requirements evaluates deterministically.
   - Valid evaluation preserved for all 8 standard archetypes.
   - Malformed/empty/non-string/excessively long role names return 400 Bad Request.
4. Genuine evidence provenance & candidate confirmation separation:
   - Zero fabricated excerpts ("Demonstrated application of X...").
   - Registry-derived skills without source excerpts marked as unavailable/registry_derived.
   - Candidate self-attestations strictly confined to candidate_confirmed and never upgraded.
5. Grounded roadmap recommendations:
   - Absence of universal callback or selection guarantees.
   - Candidate-specific gaps distinguished from general career advice.
   - Profiles with existing GitHub / certifications recognized accurately.
   - Resilient handling of profiles without explicit target-role requirements.
"""

import json
import pytest
from app import app, ANALYSIS_CACHE
from src.mentor.career_profile import build_structured_career_profile

app.config["TESTING"] = True
from src.mentor.role_recommender import (
    recommend_suitable_roles,
    evaluate_specific_role,
    ROLE_ARCHETYPES
)
from src.mentor.resume_advisor import generate_resume_improvement_suggestions
from src.mentor.career_roadmap import generate_structured_career_roadmap
from src.mentor.mentor_engine import CareerMentorEngine


# ---------------------------------------------------------------------------
# Synthetic Test Fixtures
# ---------------------------------------------------------------------------

FIXTURE_CANDIDATE_A = {
    "analysis_id": "analysis_user_alpha_999",
    "raw_text": "Alice Developer\nEmail: alice@alpha.com\nGitHub: github.com/alice\nSkills: Python, Docker, SQL",
    "filename": "alice_resume.pdf",
    "job_title": "Backend Engineer",
    "candidate_profile": {
        "name": {"full_name": "Alice Developer", "preferred_name": "Alice"},
        "contact_info": {
            "email": "alice@alpha.com",
            "github": "github.com/alice",
            "has_github": True
        },
        "education": [
            {
                "degree_level": "Bachelor of Science",
                "degree_name": "B.S. in Computer Science",
                "institution": "State University",
                "graduation_year": 2023
            }
        ],
        "certifications": [
            {
                "title": "AWS Certified Cloud Practitioner",
                "issuer": "Amazon Web Services",
                "year": 2023
            }
        ],
        "missing_fields": ["phone", "portfolio"],
        "conflicts": []
    },
    "projects": [
        {
            "title": "High-Throughput Order Processor",
            "description": "Architected order ingestion pipeline using Python and Docker.",
            "technologies": ["Python", "Docker", "SQL"]
        }
    ],
    "internships": [],
    "evidence_registry": {
        "demonstrated_skills": ["Python", "Docker", "SQL", "Linux"],
        "user_confirmations": {
            "Redis": {"status": "confirmed", "value": True}
        },
        "partially_evidenced_skills": ["Kubernetes"]
    },
    "missing_required_skills": ["CI/CD"],
    "missing_preferred_skills": ["Kafka"]
}


FIXTURE_CANDIDATE_B = {
    "analysis_id": "analysis_user_beta_888",
    "raw_text": "Bob Engineer\nEmail: bob@beta.com\nSkills: JavaScript, React",
    "filename": "bob_resume.pdf",
    "job_title": "Frontend Engineer",
    "candidate_profile": {
        "name": {"full_name": "Bob Engineer", "preferred_name": "Bob"},
        "contact_info": {"email": "bob@beta.com"},
        "education": [],
        "certifications": [],
        "missing_fields": ["phone", "github", "linkedin", "portfolio", "certifications"],
        "conflicts": []
    },
    "projects": [],
    "internships": []
}


# ---------------------------------------------------------------------------
# 1. Tests for Analysis Ownership and Session Isolation
# ---------------------------------------------------------------------------

def test_career_mentor_analysis_ownership_isolation():
    """Verify Client B cannot access Client A's analysis ID, but Client A can."""
    aid_a = FIXTURE_CANDIDATE_A["analysis_id"]
    aid_b = FIXTURE_CANDIDATE_B["analysis_id"]

    ANALYSIS_CACHE[aid_a] = FIXTURE_CANDIDATE_A
    ANALYSIS_CACHE[aid_b] = FIXTURE_CANDIDATE_B

    client_a = app.test_client()
    client_b = app.test_client()

    # Authorize each client for their respective analysis
    with client_a.session_transaction() as sess_a:
        sess_a["allowed_analyses"] = [aid_a]
        sess_a["csrf_token"] = "tok_a"

    with client_b.session_transaction() as sess_b:
        sess_b["allowed_analyses"] = [aid_b]
        sess_b["csrf_token"] = "tok_b"

    # Client A accesses analysis A -> 200 OK
    resp_a_own = client_a.get(f"/api/career-mentor?id={aid_a}")
    assert resp_a_own.status_code == 200
    assert resp_a_own.get_json()["dossier"]["identity"]["preferred_name"] == "Alice"

    # Client B attempts to access analysis A by supplying its ID -> 403 Forbidden
    resp_b_cross = client_b.get(f"/api/career-mentor?id={aid_a}")
    assert resp_b_cross.status_code == 403
    assert "Unauthorized access" in resp_b_cross.get_json()["message"]

    # Client B evaluates role on analysis A -> 403 Forbidden (CSRF token provided, ownership check fails)
    resp_b_eval_cross = client_b.post(
        "/api/career-mentor/evaluate-role",
        data=json.dumps({"role_name": "Backend Engineer", "analysis_id": aid_a}),
        content_type="application/json",
        headers={"X-CSRF-Token": "tok_b"}
    )
    assert resp_b_eval_cross.status_code == 403
    assert "Unauthorized access" in resp_b_eval_cross.get_json()["message"]

    # Client A evaluates role on its own analysis -> 200 OK
    resp_a_eval_own = client_a.post(
        "/api/career-mentor/evaluate-role",
        data=json.dumps({"role_name": "Backend Engineer", "analysis_id": aid_a}),
        content_type="application/json",
        headers={"X-CSRF-Token": "tok_a"}
    )
    assert resp_a_eval_own.status_code == 200
    assert resp_a_eval_own.get_json()["role_evaluation"]["role_title"] == "Backend Engineer"

    # Cleanup
    ANALYSIS_CACHE.pop(aid_a, None)
    ANALYSIS_CACHE.pop(aid_b, None)


def test_career_mentor_unknown_id_and_sample_behavior():
    """Verify unknown IDs return 404 and sample IDs return sample preview without leakage."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["csrf_token"] = "valid_tok"
    token_hdr = {"X-CSRF-Token": "valid_tok"}

    # 1. Unknown analysis ID -> 404 Not Found
    resp_unknown = client.get("/api/career-mentor?id=non_existent_analysis_xyz")
    assert resp_unknown.status_code == 404
    assert "not found" in resp_unknown.get_json()["message"].lower()

    resp_eval_unknown = client.post(
        "/api/career-mentor/evaluate-role",
        data=json.dumps({"role_name": "Backend Engineer", "analysis_id": "non_existent_xyz"}),
        content_type="application/json",
        headers=token_hdr
    )
    assert resp_eval_unknown.status_code == 404
    assert "not found" in resp_eval_unknown.get_json()["message"].lower()

    # 2. Sample ID -> 200 OK with sample candidate preview
    for sample_id in ["sample", "demo", "sample-preview"]:
        resp_sample = client.get(f"/api/career-mentor?id={sample_id}")
        assert resp_sample.status_code == 200
        dossier = resp_sample.get_json()["dossier"]
        assert dossier["target_role"] != ""

        resp_eval_sample = client.post(
            "/api/career-mentor/evaluate-role",
            data=json.dumps({"role_name": "Machine Learning Engineer", "analysis_id": sample_id}),
            content_type="application/json",
            headers=token_hdr
        )
        assert resp_eval_sample.status_code == 200
        assert resp_eval_sample.get_json()["role_evaluation"]["role_title"] == "Machine Learning Engineer"

    # 3. Omitting ID with empty session -> falls back to sample preview, never leaking cached users
    aid_secret = "secret_candidate_123"
    ANALYSIS_CACHE[aid_secret] = FIXTURE_CANDIDATE_A
    resp_no_id = client.get("/api/career-mentor")
    assert resp_no_id.status_code == 200
    # Must NOT return Alice's data to an unauthenticated client!
    assert resp_no_id.get_json()["dossier"]["identity"]["preferred_name"] != "Alice"
    ANALYSIS_CACHE.pop(aid_secret, None)


# ---------------------------------------------------------------------------
# 2. Tests for Removal of Fabricated Resume Achievements
# ---------------------------------------------------------------------------

def test_zero_fabricated_metrics_emitted():
    """Assert invented metrics (35%, 45ms, 12 API, 5,000+, 99.9%) are never emitted as candidate facts."""
    profile = build_structured_career_profile(FIXTURE_CANDIDATE_A)
    suggestions = generate_resume_improvement_suggestions(profile, FIXTURE_CANDIDATE_A)

    invented_phrases = [
        "35%",
        "45ms",
        "12 API",
        "12 REST",
        "5,000+",
        "5000+",
        "99.9%"
    ]

    for sug in suggestions:
        # Check suggestion text fields
        full_text = json.dumps(sug)
        for phrase in invented_phrases:
            assert phrase not in full_text, f"Fabricated metric '{phrase}' found in suggestion: {sug}"

        # Ensure explicit instruction is provided when quantifiable metrics are suggested
        if sug["suggestion_id"] == "quantifiable_metrics":
            assert "instruction" in sug
            assert "Insert only measured, verifiable values" in sug["instruction"]
            # Ensure placeholders are present in suggestions
            assert "[measured throughput" in full_text or "[count]" in full_text


# ---------------------------------------------------------------------------
# 3. Tests for Correct Custom Role Evaluation
# ---------------------------------------------------------------------------

def test_custom_role_evaluation_behavior():
    """Verify unlisted custom roles return 'unevaluated' without fabricating a 50% score."""
    profile = build_structured_career_profile(FIXTURE_CANDIDATE_A)

    # 1. Custom unlisted role without requirements
    custom_res = evaluate_specific_role("Autonomous Robotics Specialist", profile, FIXTURE_CANDIDATE_A)
    assert custom_res["evaluation_status"] == "unevaluated"
    assert custom_res["match_score"] is None
    assert custom_res["match_score_pct"] is None
    assert custom_res["fit_tier"] == "Unevaluated"
    assert "reliable competency assessment requires role-specific skills" in custom_res["fit_reason"].lower()

    # 2. Custom role WITH structured requirements
    custom_reqs = {"core_skills": ["Python", "Docker", "ROS"]}
    evaluated_res = evaluate_specific_role(
        "Robotics Software Engineer",
        profile,
        FIXTURE_CANDIDATE_A,
        custom_role_requirements=custom_reqs
    )
    assert evaluated_res["evaluation_status"] == "evaluated"
    assert evaluated_res["match_score"] is not None
    assert evaluated_res["match_score"] > 0
    assert evaluated_res["fit_tier"] in ["Strong Fit", "Potential Fit", "Growth Fit"]

    # 3. Standard 8 archetypes preserved
    for archetype in ROLE_ARCHETYPES:
        arch_res = evaluate_specific_role(archetype["title"], profile, FIXTURE_CANDIDATE_A)
        assert arch_res["match_score"] is not None
        assert arch_res["fit_tier"] in ["Strong Fit", "Potential Fit", "Growth Fit"]


def test_role_evaluation_input_validation():
    """Verify malformed, empty, non-string, or excessively long role names return 400 Bad Request."""
    client = app.test_client()

    # 1. Empty role_name
    r1 = client.post("/api/career-mentor/evaluate-role",
                     data=json.dumps({"role_name": "   "}),
                     content_type="application/json")
    assert r1.status_code == 400

    # 2. Non-string role_name (e.g., number or None)
    r2 = client.post("/api/career-mentor/evaluate-role",
                     data=json.dumps({"role_name": 12345}),
                     content_type="application/json")
    assert r2.status_code == 400

    r3 = client.post("/api/career-mentor/evaluate-role",
                     data=json.dumps({"role_name": None}),
                     content_type="application/json")
    assert r3.status_code == 400

    # 3. Excessively long role_name (> 100 characters)
    r4 = client.post("/api/career-mentor/evaluate-role",
                     data=json.dumps({"role_name": "A" * 125}),
                     content_type="application/json")
    assert r4.status_code == 400
    assert "exceeds maximum allowable length" in r4.get_json()["message"].lower()


# ---------------------------------------------------------------------------
# 4. Tests for Evidence Provenance & Candidate Confirmation Separation
# ---------------------------------------------------------------------------

def test_evidence_provenance_and_no_fabricated_excerpts():
    """Verify zero fabricated excerpts and proper handling of registry-derived skills."""
    # Candidate with a skill in registry ("Linux") that has no explicit project excerpt
    profile = build_structured_career_profile(FIXTURE_CANDIDATE_A)

    demonstrated = profile["demonstrated_competencies"]
    for d in demonstrated:
        # Must NEVER contain fabricated placeholder string
        assert "Demonstrated application of" not in (d.get("excerpt") or "")

        # If excerpt is unavailable, must be marked honestly
        if d.get("excerpt") is None:
            assert d.get("excerpt_status") == "unavailable"
            assert "registry-derived" in (d.get("provenance_note") or "").lower() or "technology listed in" in (d.get("provenance_note") or "").lower()

    # Candidate self-confirmations must remain separated and never upgraded
    confirmed = profile["candidate_confirmed_competencies"]
    confirmed_skills = [c["skill"].lower() for c in confirmed]
    assert "redis" in confirmed_skills
    for c in confirmed:
        assert c["evidence_source"] == "candidate_confirmed"
        assert c["confidence"] == 0.75
        assert c["excerpt"] is None
        # Confirmed skill must NOT appear in demonstrated_competencies
        demonstrated_skills = [d["skill"].lower() for d in demonstrated]
        assert c["skill"].lower() not in demonstrated_skills


# ---------------------------------------------------------------------------
# 5. Tests for Grounded Roadmap Recommendations
# ---------------------------------------------------------------------------

def test_grounded_roadmap_no_unsupported_universal_claims():
    """Verify roadmap does not claim guaranteed callbacks or falsely assume missing links."""
    # Complete profile test: Alice already has GitHub and AWS Certification
    profile_a = build_structured_career_profile(FIXTURE_CANDIDATE_A)
    roadmap_a = generate_structured_career_roadmap(profile_a, FIXTURE_CANDIDATE_A, target_role="Backend Engineer")

    full_roadmap_text = json.dumps(roadmap_a)
    # Check no unsupported callback / selection guarantees
    assert "callback rate" not in full_roadmap_text.lower()
    assert "guaranteed" not in full_roadmap_text.lower()

    # Alice has GitHub, so the resume milestone must acknowledge that she has repository links
    resume_milestone = next(m for m in roadmap_a["milestones"] if m["milestone_id"] == "st_resume_and_github_polish")
    assert "profile has verifiable repository links" in resume_milestone["supporting_evidence_or_gap"].lower() or "repository links" in resume_milestone["supporting_evidence_or_gap"].lower()

    # Alice has AWS certification, so the certification milestone must acknowledge existing credential
    cert_milestone = next(m for m in roadmap_a["milestones"] if m["milestone_id"] == "mt_industry_certification")
    assert "candidate holds verified credential" in cert_milestone["supporting_evidence_or_gap"].lower()

    # Check guidance_type tagging
    for m in roadmap_a["milestones"]:
        assert m["guidance_type"] in ["candidate_specific", "general_career_development"]

    # Incomplete profile test: Bob has no GitHub and no target role
    profile_b = build_structured_career_profile(FIXTURE_CANDIDATE_B)
    roadmap_b = generate_structured_career_roadmap(profile_b, FIXTURE_CANDIDATE_B, target_role="Target Engineering Role")
    assert roadmap_b["total_milestones_count"] >= 2
    # Bob lacks GitHub, so his resume milestone must address that gap
    bob_resume_m = next(m for m in roadmap_b["milestones"] if m["milestone_id"] == "st_resume_and_github_polish")
    assert "lacks" in bob_resume_m["supporting_evidence_or_gap"].lower()
