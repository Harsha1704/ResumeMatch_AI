"""
Phase 4 Test Suite: Career Mentor Module Hardening.
Tests:
1. Career profile extraction (identity, education, certs, projects, demonstrated skills).
2. Unsupported claims and hallucination prevention (tracking missing fields, zero invention).
3. Candidate-confirmed vs resume-supported evidence separation (provenance & confidence).
4. Role recommendation relevance and scoring (archetypes, match %, fit tiers, heuristic notes).
5. Role evaluation custom endpoint (/api/career-mentor/evaluate-role).
6. Skill-gap correctness and categorization (4 standard categories, priority, JD citations).
7. Roadmap prioritization and milestones (Short-Term vs Medium-Term, deliverables, criteria).
8. Resume improvement suggestions grounding (quantifiable metrics, before/after rewrites, verbs).
9. Empty and incomplete profile handling (graceful defaults, zero unhandled crashes).
10. API career-mentor contract and session isolation (/api/career-mentor response schema).
"""

import json
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
from src.mentor.mentor_engine import CareerMentorEngine


# ---------------------------------------------------------------------------
# Synthetic Ground-Truth Fixtures
# ---------------------------------------------------------------------------

SAMPLE_FULL_ANALYSIS = {
    "raw_text": "Harsha Vardhan\nEmail: harsha@example.com\nPhone: +1 555-0199\nLinkedIn: linkedin.com/in/harsha\nGitHub: github.com/harsha\nB.Tech Computer Science and Engineering, 2024\nSkills: Python, Scikit-learn, SQL, Flask, Docker, Git",
    "filename": "harsha_cv_2026.pdf",
    "job_title": "Senior Backend & Machine Learning Engineer",
    "candidate_profile": {
        "name": {
            "full_name": "Harsha Vardhan",
            "preferred_name": "Harsha"
        },
        "contact_info": {
            "email": "harsha@example.com",
            "phone": "+1 555-0199",
            "linkedin": "linkedin.com/in/harsha",
            "github": "github.com/harsha",
            "portfolio": None,
            "location": "Hyderabad, India"
        },
        "education": [
            {
                "degree_level": "Bachelor of Technology",
                "degree_name": "B.Tech in Computer Science and Engineering",
                "field_of_study": "Computer Science and Engineering",
                "institution": "JNTU",
                "graduation_year": 2024,
                "gpa": "3.8/4.0"
            }
        ],
        "certifications": [
            {
                "title": "AWS Certified Cloud Practitioner",
                "issuer": "Amazon Web Services",
                "year": 2023
            }
        ],
        "missing_fields": ["portfolio"],
        "conflicts": []
    },
    "education_analysis": {
        "education_verified": True,
        "verification_status": "verified_match",
        "notes": "Candidate Bachelor of Technology matches required STEM degree."
    },
    "experience_summary": {
        "total_years": 1.5,
        "full_time_years": 1.0,
        "internship_months": 6,
        "display_summary": "1.5 years experience with backend APIs and ML pipelines."
    },
    "projects": [
        {
            "title": "Multimodal Resume Matching Engine",
            "description": "Architected low-latency microservice with Python, Docker, and Scikit-Learn. Improved matching throughput by 42%.",
            "technologies": ["Python", "Docker", "Scikit-Learn", "REST APIs", "SQL"]
        },
        {
            "title": "Distributed Task Scheduler",
            "description": "Developed distributed job queue handling 10,000 tasks/minute using Python, Redis, and PostgreSQL.",
            "technologies": ["Python", "PostgreSQL", "Git", "Linux"]
        }
    ],
    "internships": [
        {
            "organization": "Cognitive AI Labs",
            "position": "Backend & ML Intern",
            "responsibilities": ["Maintained REST API endpoints", "Containerized pipelines using Docker"],
            "technologies": ["Python", "Flask", "Docker"]
        }
    ],
    "evidence_registry": {
        "demonstrated_skills": ["Python", "SQL", "Docker", "Scikit-Learn", "REST APIs", "PostgreSQL", "Git", "Linux", "Flask"],
        "user_confirmations": {
            "Kubernetes": {"status": "confirmed", "value": True},
            "AWS": True
        },
        "partially_evidenced_skills": ["C++", "Redis"]
    },
    "missing_required_skills": ["CI/CD", "System Design"],
    "missing_preferred_skills": ["Kafka", "Airflow"]
}


SAMPLE_MINIMAL_ANALYSIS = {
    "raw_text": "Alex Smith\nEmail: alex@example.com\nSkills: Python, SQL",
    "candidate_profile": {
        "name": {"full_name": "Alex Smith", "preferred_name": "Alex"},
        "contact_info": {"email": "alex@example.com"},
        "education": [],
        "certifications": [],
        "missing_fields": ["phone", "github", "linkedin", "portfolio", "education", "certifications"]
    },
    "projects": [],
    "internships": []
}


# ---------------------------------------------------------------------------
# Test 1: Career Profile Extraction
# ---------------------------------------------------------------------------

def test_career_profile_extraction():
    """Verify structured career profile extracts identity, education, experience, and skills accurately."""
    profile = build_structured_career_profile(SAMPLE_FULL_ANALYSIS)

    # 1. Identity & Contact Details
    identity = profile["identity"]
    assert identity["full_name"] == "Harsha Vardhan"
    assert identity["preferred_name"] == "Harsha"
    assert identity["email"] == "harsha@example.com"
    assert identity["phone"] == "+1 555-0199"
    assert identity["linkedin"] == "linkedin.com/in/harsha"
    assert identity["github"] == "github.com/harsha"
    assert identity["has_github"] is True
    assert identity["has_portfolio"] is False

    # 2. Education
    edu = profile["education"]
    assert edu["total_degrees_count"] == 1
    assert edu["records"][0]["degree_name"] == "B.Tech in Computer Science and Engineering"
    assert edu["education_verified"] is True
    assert edu["verification_status"] == "verified_match"

    # 3. Certifications
    certs = profile["certifications"]
    assert len(certs) == 1
    assert certs[0]["title"] == "AWS Certified Cloud Practitioner"
    assert certs[0]["issuer"] == "Amazon Web Services"

    # 4. Experience & Projects
    exp = profile["experience"]
    assert exp["total_experience_years"] == 1.5
    assert exp["projects_count"] == 2
    assert exp["internships_count"] == 1

    # 5. Demonstrated competencies (confidence >= 0.90)
    demonstrated = profile["demonstrated_competencies"]
    demonstrated_skills = [d["skill"].lower() for d in demonstrated]
    assert "python" in demonstrated_skills
    assert "docker" in demonstrated_skills
    assert "scikit-learn" in demonstrated_skills
    for d in demonstrated:
        assert d["confidence"] >= 0.90
        assert d["evidence_source"] in ["project", "internship", "professional_experience"]


# ---------------------------------------------------------------------------
# Test 2: Unsupported Claims and Hallucination Prevention
# ---------------------------------------------------------------------------

def test_unsupported_claims_and_hallucination_prevention():
    """Verify unprovided fields are tracked as missing and never hallucinated."""
    profile = build_structured_career_profile(SAMPLE_MINIMAL_ANALYSIS)

    # Contact fields must be None/False, not hallucinated
    assert profile["identity"]["phone"] is None
    assert profile["identity"]["has_phone"] is False
    assert profile["identity"]["github"] is None
    assert profile["identity"]["has_github"] is False
    assert profile["identity"]["linkedin"] is None
    assert profile["identity"]["has_linkedin"] is False

    # Education & certs should be empty lists, not invented
    assert len(profile["education"]["records"]) == 0
    assert len(profile["certifications"]) == 0

    # Missing fields must be documented in missing_or_uncertain_information
    missing_fields = [m["field"] for m in profile["missing_or_uncertain_information"]]
    assert "github_link" in missing_fields
    assert "certifications" in missing_fields

    # No ungrounded demonstrated skills when no projects/internships
    demonstrated = profile["demonstrated_competencies"]
    assert len(demonstrated) == 0


# ---------------------------------------------------------------------------
# Test 3: Candidate-Confirmed vs Resume-Supported Separation
# ---------------------------------------------------------------------------

def test_candidate_confirmed_vs_resume_supported_separation():
    """Verify candidate self-confirmations are separated from resume-demonstrated evidence."""
    profile = build_structured_career_profile(SAMPLE_FULL_ANALYSIS)

    demonstrated_skills = [d["skill"].lower() for d in profile["demonstrated_competencies"]]
    candidate_confirmed = profile["candidate_confirmed_competencies"]
    confirmed_skills = [c["skill"].lower() for c in candidate_confirmed]

    # Kubernetes was in user_confirmations, not in project text
    assert "kubernetes" in confirmed_skills
    # Check that confirmed competencies are labeled with candidate_confirmed source and disclaimer note
    k8s_entry = next(c for c in candidate_confirmed if c["skill"].lower() == "kubernetes")
    assert k8s_entry["evidence_source"] == "candidate_confirmed"
    assert k8s_entry["confidence"] == 0.75
    assert "Candidate self-attestation" in k8s_entry["notes"]

    # Python was demonstrated in projects, so it must not be in candidate_confirmed
    assert "python" in demonstrated_skills
    assert "python" not in confirmed_skills

    # Partially evidenced skills
    partial = profile["partially_evidenced_competencies"]
    partial_skills = [p["skill"].lower() for p in partial]
    assert "c++" in partial_skills or "redis" in partial_skills


# ---------------------------------------------------------------------------
# Test 4: Role Recommendation Relevance and Scoring
# ---------------------------------------------------------------------------

def test_role_recommendation_relevance_and_scoring():
    """Verify deterministic scoring across archetypes, fit tiers, and heuristic notice."""
    profile = build_structured_career_profile(SAMPLE_FULL_ANALYSIS)
    recommendations = recommend_suitable_roles(profile, SAMPLE_FULL_ANALYSIS)

    # Must recommend all 8 archetypes
    assert len(recommendations) == len(ROLE_ARCHETYPES)

    # Check top recommendation is either Backend Engineer or ML Engineer given candidate's skills
    top_role = recommendations[0]
    assert top_role["role_title"] in ["Backend Engineer", "Machine Learning Engineer", "Systems / Software Engineer"]
    assert top_role["match_score_pct"] > 50

    # Fit tier must be valid
    for role in recommendations:
        assert role["fit_tier"] in ["Strong Fit", "Potential Fit", "Growth Fit"]
        assert 0.0 <= role["match_score_pct"] <= 100.0
        assert "evidence_grounded_fit_reason" in role
        assert "matching_competencies" in role
        assert "primary_gaps" in role
        assert "practical_next_action" in role
        # Methodology must disclaim real-time market/salary data
        assert "heuristic alignment" in role["heuristic_note"].lower()

    # Test evaluating a specific role directly
    backend_eval = evaluate_specific_role("Backend Engineer", profile, SAMPLE_FULL_ANALYSIS)
    assert backend_eval["role_title"] == "Backend Engineer"
    assert backend_eval["match_score_pct"] >= 60.0
    matching = [m.lower() for m in backend_eval["matching_competencies"]]
    assert "python" in matching
    assert "sql" in matching
    assert "docker" in matching


# ---------------------------------------------------------------------------
# Test 5: Role Evaluation Custom Endpoint
# ---------------------------------------------------------------------------

def test_role_evaluation_custom_endpoint():
    """Test POST /api/career-mentor/evaluate-role route with valid, invalid, and missing payloads."""
    client = app.test_client()

    # Setup active analysis in cache
    test_aid = "test_eval_session_001"
    ANALYSIS_CACHE[test_aid] = SAMPLE_FULL_ANALYSIS
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [test_aid]

    # 1. Missing role_name -> 400 Bad Request
    resp_empty = client.post("/api/career-mentor/evaluate-role",
                             data=json.dumps({"analysis_id": test_aid}),
                             content_type="application/json")
    assert resp_empty.status_code == 400
    assert "Missing role_name" in resp_empty.get_json()["message"]

    # 2. Valid role_name -> 200 OK
    resp_valid = client.post("/api/career-mentor/evaluate-role",
                             data=json.dumps({"role_name": "Backend Engineer", "analysis_id": test_aid}),
                             content_type="application/json")
    assert resp_valid.status_code == 200
    payload = resp_valid.get_json()
    assert payload["status"] == "success"
    eval_res = payload["role_evaluation"]
    assert eval_res["role_title"] == "Backend Engineer"
    assert eval_res["fit_tier"] in ["Strong Fit", "Potential Fit", "Growth Fit"]
    assert len(eval_res["matching_competencies"]) > 0

    # 3. Custom / unlisted role title -> 200 OK with heuristic evaluation
    resp_custom = client.post("/api/career-mentor/evaluate-role",
                              data=json.dumps({"role_name": "Distributed Cloud Architect", "analysis_id": test_aid}),
                              content_type="application/json")
    assert resp_custom.status_code == 200
    eval_custom = resp_custom.get_json()["role_evaluation"]
    assert eval_custom["role_title"] == "Distributed Cloud Architect"
    assert "heuristic_note" in eval_custom

    # Cleanup cache
    ANALYSIS_CACHE.pop(test_aid, None)


# ---------------------------------------------------------------------------
# Test 6: Skill Gap Correctness and Categories
# ---------------------------------------------------------------------------

def test_skill_gap_correctness_and_categories():
    """Verify skill gaps are properly prioritized and categorized into 4 standard categories."""
    engine = CareerMentorEngine(SAMPLE_FULL_ANALYSIS)
    dossier = engine.build_mentor_dossier()

    gaps = dossier["gaps"]
    assert "prioritized_gaps" in gaps
    assert "category_breakdown" in gaps

    breakdown = gaps["category_breakdown"]
    # Check 4 standard categories exist
    assert "core_technical" in breakdown
    assert "tooling_frameworks" in breakdown
    assert "architecture_design" in breakdown
    assert "soft_skills_practices" in breakdown

    # Required skills (CI/CD, System Design) must be marked High priority / Mandatory
    prioritized = gaps["prioritized_gaps"]
    skill_names = [p["skill_name"] for p in prioritized]
    assert any("ci/cd" in s.lower() or "cicd" in s.lower() for s in skill_names)
    assert any("system design" in s.lower() for s in skill_names)

    for p in prioritized:
        assert any(term in p["priority"] for term in ["Critical", "High", "Moderate", "Medium", "Foundational", "Low", "Mandatory", "Preferred"])
        assert len(p["explanation"]) > 0


# ---------------------------------------------------------------------------
# Test 7: Roadmap Prioritization and Milestones
# ---------------------------------------------------------------------------

def test_roadmap_prioritization_and_milestones():
    """Verify career roadmap separates Short-Term and Medium-Term milestones with deliverables."""
    profile = build_structured_career_profile(SAMPLE_FULL_ANALYSIS)
    roadmap = generate_structured_career_roadmap(profile, SAMPLE_FULL_ANALYSIS)

    assert "milestones" in roadmap
    assert "total_milestones_count" in roadmap
    assert "short_term_focus" in roadmap
    assert "medium_term_focus" in roadmap

    milestones = roadmap["milestones"]
    assert len(milestones) >= 2

    # Check phase horizons
    phases = [m["phase"] for m in milestones]
    assert any("Short-Term" in p for p in phases)
    assert any("Medium-Term" in p for p in phases)

    # Check required fields per milestone
    for m in milestones:
        assert "milestone_id" in m
        assert "goal" in m
        assert "reason" in m
        assert "deliverables" in m
        assert len(m["deliverables"]) > 0
        assert "verification_criteria" in m
        assert "estimated_timeline" in m


# ---------------------------------------------------------------------------
# Test 8: Resume Improvement Suggestions Grounding
# ---------------------------------------------------------------------------

def test_resume_improvement_suggestions_grounding():
    """Verify resume improvement suggestions identify metrics, provide rewrites, and check repo links."""
    profile = build_structured_career_profile(SAMPLE_FULL_ANALYSIS)
    suggestions = generate_resume_improvement_suggestions(profile, SAMPLE_FULL_ANALYSIS)

    assert len(suggestions) > 0
    categories = [s["category"] for s in suggestions]

    # Check categories of suggestions
    assert any("Quantifiable" in c and "Impact" in c for c in categories)

    # Check before/after rewrite structure
    quant_sug = next(s for s in suggestions if "Quantifiable" in s["category"])
    assert "before_after_examples" in quant_sug
    for ex in quant_sug["before_after_examples"]:
        assert "original" in ex
        assert "suggested" in ex
        assert "rationale" in ex

    # Test with profile missing GitHub
    minimal_profile = build_structured_career_profile(SAMPLE_MINIMAL_ANALYSIS)
    min_suggestions = generate_resume_improvement_suggestions(minimal_profile, SAMPLE_MINIMAL_ANALYSIS)
    assert any(s["suggestion_id"] == "repository_traceability" or "Portfolio" in s["category"] for s in min_suggestions)


# ---------------------------------------------------------------------------
# Test 9: Empty and Incomplete Profiles
# ---------------------------------------------------------------------------

def test_empty_and_incomplete_profiles():
    """Verify zero crashes and compliant fallback structures on empty, None, and partial inputs."""
    # 1. None inputs
    p_none = build_structured_career_profile(None)
    assert p_none["identity"]["preferred_name"] == "Candidate"
    assert p_none["education"]["total_degrees_count"] == 0
    assert len(p_none["demonstrated_competencies"]) == 0

    roles_none = recommend_suitable_roles(p_none, None)
    assert len(roles_none) == len(ROLE_ARCHETYPES)
    for r in roles_none:
        assert r["fit_tier"] == "Growth Fit"

    sug_none = generate_resume_improvement_suggestions(p_none, None)
    assert isinstance(sug_none, list)

    rm_none = generate_structured_career_roadmap(p_none, None)
    assert "milestones" in rm_none

    dossier_none = CareerMentorEngine(None).build_mentor_dossier()
    assert dossier_none["identity"]["preferred_name"] == "Candidate"
    assert "career_profile" in dossier_none
    assert "recommended_roles" in dossier_none

    # 2. Empty dict input
    dossier_empty = CareerMentorEngine({}).build_mentor_dossier()
    assert dossier_empty["identity"]["preferred_name"] == "Candidate"
    assert len(dossier_empty["strengths"]["demonstrated_skills"]) == 0


# ---------------------------------------------------------------------------
# Test 10: API Career-Mentor Contract and Session Isolation
# ---------------------------------------------------------------------------

def test_api_career_mentor_contract_and_session_isolation():
    """Verify /api/career-mentor response schema, status codes, and session isolation."""
    client = app.test_client()

    aid = "test_phase4_dossier_session"
    ANALYSIS_CACHE[aid] = SAMPLE_FULL_ANALYSIS
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [aid]

    # Request dossier via query param
    resp = client.get(f"/api/career-mentor?id={aid}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    dossier = data["dossier"]

    # Verify new Phase 4 keys in dossier
    assert "career_profile" in dossier
    assert "recommended_roles" in dossier
    assert "resume_improvement_suggestions" in dossier
    assert "career_roadmap" in dossier

    # Verify backward compatibility keys
    assert "identity" in dossier
    assert "target_role" in dossier
    assert "strengths" in dossier
    assert "gaps" in dossier
    assert "roadmaps" in dossier
    assert "study_plan" in dossier
    assert "disclaimer" in dossier

    # Verify session isolation between clients
    client_a = app.test_client()
    client_b = app.test_client()

    with client_a.session_transaction() as sess:
        sess["allowed_analyses"] = [aid]
    with client_b.session_transaction() as sess:
        sess["allowed_analyses"] = [aid]

    client_a.post("/api/mentor/update-name",
                  data=json.dumps({"preferred_name": "Alice"}),
                  content_type="application/json")
    client_b.post("/api/mentor/update-name",
                  data=json.dumps({"preferred_name": "Bob"}),
                  content_type="application/json")

    resp_a = client_a.get(f"/api/career-mentor?id={aid}")
    resp_b = client_b.get(f"/api/career-mentor?id={aid}")

    assert resp_a.get_json()["dossier"]["identity"]["preferred_name"] == "Alice"
    assert resp_b.get_json()["dossier"]["identity"]["preferred_name"] == "Bob"

    # Cleanup
    ANALYSIS_CACHE.pop(aid, None)
