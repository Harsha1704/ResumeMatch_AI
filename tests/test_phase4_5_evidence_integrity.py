"""
Phase 4.5 Test Suite: Final Demonstration Evidence Integrity Repair.

Mandatory Test Areas:
1. Action-Word False Positives:
   - "Python development was discussed during planning." -> NOT demonstrated.
   - "Python implementation is required for this role." -> NOT demonstrated.
   - "Python was used to implement the data-processing module." -> demonstrated.
   - "Developed the application using Python." -> demonstrated.
   - Additional nominal forms (architecture, analysis, configuration, management) without action verbs are rejected.

2. Evidence-Validation Bypass Closure:
   - Match evidence: "Python was considered but not used." -> not fully demonstrated.
   - Match evidence: "Planned to migrate the application to Python." -> not fully demonstrated.
   - Match evidence: "Used Python to implement the processing module." -> demonstrated.
   - Empty (""), malformed (None, non-string, punctuation), and unrelated excerpts must not receive full credit.

3. Complete Provenance & Scoring Integrity:
   - Valid match evidence upgrades an unevidenced project technology.
   - Strong project evidence is preserved against weaker or negated match evidence.
   - Candidate confirmation remains in candidate_confirmed_competencies and never becomes resume-demonstrated.
   - Role evaluation applies strict 1.0 (demonstrated), 0.75 (confirmed), and 0.60 (registry-derived) scoring tiers.
"""

import json
import pytest
from app import app, ANALYSIS_CACHE
from src.mentor.career_profile import (
    build_structured_career_profile,
    find_supporting_excerpt_for_skill
)
from src.mentor.role_recommender import evaluate_specific_role

app.config["TESTING"] = True


# ---------------------------------------------------------------------------
# 1. Action-Word False Positives & Nominal Form Rejection
# ---------------------------------------------------------------------------

def test_nominal_forms_not_demonstrated_general_discussion():
    """'Python development was discussed during planning.' must NOT establish demonstrated use."""
    text = "Python development was discussed during planning."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is None


def test_nominal_forms_not_demonstrated_role_requirement():
    """'Python implementation is required for this role.' must NOT establish demonstrated use."""
    text = "Python implementation is required for this role."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is None


def test_action_verb_used_to_implement_demonstrated():
    """'Python was used to implement the data-processing module.' must establish demonstrated use."""
    text = "Python was used to implement the data-processing module."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is not None
    assert "Python was used to implement" in excerpt


def test_action_verb_developed_using_demonstrated():
    """'Developed the application using Python.' must establish demonstrated use."""
    text = "Developed the application using Python."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is not None
    assert "Developed the application using Python" in excerpt


def test_additional_nominal_exclusions_and_genuine_action_verbs():
    """Test nominals (architecture, analysis, configuration, management) vs genuine active engineering verbs."""
    rejection_cases = [
        ("Python architecture was under discussion.", "Python"),
        ("Python configuration management.", "Python"),
        ("Python analysis was requested by stakeholders.", "Python"),
        ("Python is preferred for this position.", "Python"),
        ("Role requirement: Python development.", "Python"),
    ]
    for sample, skill in rejection_cases:
        res = find_supporting_excerpt_for_skill(skill, sample)
        assert res is None, f"Expected '{sample}' NOT to demonstrate {skill}, got: {res}"

    acceptance_cases = [
        ("Configured the backend microservices using Python.", "Python"),
        ("Automated the test pipeline with Python scripts.", "Python"),
        ("Maintained and optimized Python data loaders.", "Python"),
        ("Architected the service and implemented it with Python.", "Python"),
    ]
    for sample, skill in acceptance_cases:
        res = find_supporting_excerpt_for_skill(skill, sample)
        assert res is not None, f"Expected '{sample}' to demonstrate {skill}"


# ---------------------------------------------------------------------------
# 2. Evidence-Validation Bypass Closure in Matches
# ---------------------------------------------------------------------------

def test_match_evidence_negated_not_fully_demonstrated():
    """Match evidence 'Python was considered but not used.' must NOT receive full credit."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Test Candidate"}},
        "matches": [
            {
                "skill": "Python",
                "evidence": "Python was considered but not used."
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    python_s = demonstrated.get("python")

    assert python_s is not None
    assert python_s["evidence_source"] == "registry_derived"
    assert python_s["excerpt_status"] == "unavailable"
    assert python_s["excerpt"] is None
    assert python_s["confidence"] == 0.60

    assert not any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])
    assert any(s["skill"] == "Python" for s in profile["registry_derived_competencies"])


def test_match_evidence_prospective_not_fully_demonstrated():
    """Match evidence 'Planned to migrate the application to Python.' must NOT receive full credit."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Test Candidate"}},
        "matches": [
            {
                "skill": "Python",
                "evidence": "Planned to migrate the application to Python."
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    python_s = demonstrated.get("python")

    assert python_s is not None
    assert python_s["evidence_source"] == "registry_derived"
    assert python_s["excerpt_status"] == "unavailable"
    assert python_s["confidence"] == 0.60
    assert not any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])


def test_match_evidence_used_to_implement_demonstrated():
    """Match evidence 'Used Python to implement the processing module.' must receive demonstrated credit."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Test Candidate"}},
        "matches": [
            {
                "skill": "Python",
                "evidence": "Used Python to implement the processing module."
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    python_s = demonstrated.get("python")

    assert python_s is not None
    assert python_s["evidence_source"] == "professional_experience"
    assert python_s["excerpt_status"] == "available"
    assert python_s["confidence"] == 0.90
    assert python_s["excerpt"] is not None
    assert "Used Python to implement" in python_s["excerpt"]
    assert any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])


def test_match_evidence_empty_malformed_unrelated_not_fully_demonstrated():
    """Empty, malformed, and unrelated match excerpts must not receive full credit."""
    test_cases = [
        {"desc": "empty string", "evidence": ""},
        {"desc": "whitespace only", "evidence": "    "},
        {"desc": "None value", "evidence": None},
        {"desc": "integer value", "evidence": 12345},
        {"desc": "punctuation only", "evidence": ".... ;;;; !!!!"},
        {"desc": "unrelated skill excerpt", "evidence": "Experienced in React and CSS styling."},
        {"desc": "general discussion", "evidence": "Python development was discussed during planning."},
        {"desc": "role requirement", "evidence": "Python implementation is required for this role."},
    ]

    for tc in test_cases:
        analysis = {
            "candidate_profile": {"name": {"full_name": "Test Candidate"}},
            "matches": [
                {
                    "skill": "Python",
                    "evidence": tc["evidence"]
                }
            ]
        }
        profile = build_structured_career_profile(analysis)
        python_s = next((s for s in profile["demonstrated_competencies"] if s["skill"].lower() == "python"), None)

        assert python_s is not None, f"Python should be recorded for case: {tc['desc']}"
        assert python_s["excerpt_status"] == "unavailable", f"Case {tc['desc']} should have unavailable excerpt"
        assert python_s["excerpt"] is None, f"Case {tc['desc']} should have None excerpt"
        assert python_s["evidence_source"] == "registry_derived", f"Case {tc['desc']} should be registry_derived"
        assert python_s["confidence"] == 0.60, f"Case {tc['desc']} should have 0.60 confidence"
        assert not any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"]), \
            f"Case {tc['desc']} must NOT be in traceable_demonstrated_competencies"


# ---------------------------------------------------------------------------
# 3. Provenance Precedence, Candidate Confirmation & Role Scoring
# ---------------------------------------------------------------------------

def test_provenance_precedence_and_candidate_confirmation():
    """
    Verify:
    1. Legitimate match evidence upgrades unevidenced project technology.
    2. Strong project evidence is preserved against negated match evidence.
    3. Candidate self-confirmation remains candidate_confirmed (0.75 factor), never resume-demonstrated.
    """
    analysis = {
        "candidate_profile": {"name": {"full_name": "Precedence Candidate"}},
        "projects": [
            {
                "title": "API Gateway",
                "description": "Architected backend service using Go.",
                "technologies": ["Go", "Python"]  # Go demonstrated in desc, Python is not
            }
        ],
        "matches": [
            {
                "skill": "Python",
                "evidence": "Used Python to implement the processing module."  # Valid match evidence for Python
            },
            {
                "skill": "Go",
                "evidence": "Go was considered but not used."  # Negated match evidence for Go
            }
        ],
        "evidence_registry": {
            "user_confirmations": {
                "SQL": True  # Self-attestation only
            }
        }
    }

    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    # Go: Preserves strong project evidence (0.95), not downgraded by negated match evidence
    go_s = demonstrated.get("go")
    assert go_s is not None
    assert go_s["evidence_source"] == "project"
    assert go_s["excerpt_status"] == "available"
    assert go_s["confidence"] == 0.95
    assert "Architected backend service using Go" in go_s["excerpt"]

    # Python: Upgraded from unavailable project tag to verified match evidence (0.90)
    py_s = demonstrated.get("python")
    assert py_s is not None
    assert py_s["evidence_source"] == "professional_experience"
    assert py_s["excerpt_status"] == "available"
    assert py_s["confidence"] == 0.90
    assert "Used Python to implement" in py_s["excerpt"]

    # SQL: Candidate-confirmed only (0.75), never in demonstrated
    assert not any(s["skill"].lower() == "sql" for s in profile["demonstrated_competencies"])
    assert not any(s["skill"].lower() == "sql" for s in profile["traceable_demonstrated_competencies"])
    confirmed_sql = next((c for c in profile["candidate_confirmed_competencies"] if c["skill"].lower() == "sql"), None)
    assert confirmed_sql is not None
    assert confirmed_sql["evidence_source"] == "candidate_confirmed"
    assert confirmed_sql["confidence"] == 0.75

    # Role evaluation test with explicit tiers
    custom_role = {
        "name": "Backend Specialist",
        "core_skills": ["Go", "Python", "SQL"],
        "supporting_skills": [],
        "min_experience_years": 0.0,
        "required_education_level": "none"
    }

    eval_result = evaluate_specific_role("Backend Specialist", profile, analysis, custom_role_requirements=custom_role)
    # Go: 1.5 * 1.0 = 1.5 (demonstrated)
    # Python: 1.5 * 1.0 = 1.5 (demonstrated via match)
    # SQL: 1.5 * 0.75 = 1.125 (candidate confirmed)
    # Total earned = 4.125 / 4.5 = 91.7%
    assert eval_result["match_score"] == pytest.approx(91.7, rel=1e-2)
