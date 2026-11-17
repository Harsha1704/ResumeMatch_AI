"""
Phase 4.7 Test Suite: Skill-Specific Negation and Evidence Isolation.

Mandatory Test Areas:
1. Python was used in the project and Java was only considered.
   -> Python demonstrated; Java not demonstrated.
2. Python was implemented in the project and Docker was not used.
   -> Python demonstrated; Docker not demonstrated.
3. Python was considered and Java was implemented.
   -> Python not demonstrated; Java demonstrated.
4. Python and Java were used to build the application.
   -> Both demonstrated.
5. Developed the application using Python and React, while Java was only considered.
   -> Python and React demonstrated; Java not demonstrated.
6. Python was not used, but Java was used to build the application.
   -> Python not demonstrated; Java demonstrated.
7. Python was used, although Java was planned for future adoption.
   -> Python demonstrated; Java not demonstrated.
8. Consistent application across all 5 evidence sources (projects, internships, matches, professional experience, raw text).
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
# 1. Mandatory 7 Semantic Negation Scoping Cases
# ---------------------------------------------------------------------------

def test_case_1_used_and_only_considered():
    """1. 'Python was used in the project and Java was only considered.' -> Python demonstrated; Java not demonstrated."""
    text = "Python was used in the project and Java was only considered."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is not None
    assert "Python was used in the project" in py_ex

    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is None


def test_case_2_implemented_and_not_used():
    """2. 'Python was implemented in the project and Docker was not used.' -> Python demonstrated; Docker not demonstrated."""
    text = "Python was implemented in the project and Docker was not used."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is not None
    assert "Python was implemented in the project" in py_ex

    docker_ex = find_supporting_excerpt_for_skill("Docker", text)
    assert docker_ex is None


def test_case_3_considered_and_implemented():
    """3. 'Python was considered and Java was implemented.' -> Python not demonstrated; Java demonstrated."""
    text = "Python was considered and Java was implemented."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is None

    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is not None
    assert "Java was implemented" in java_ex


def test_case_4_coordinated_skills_both_demonstrated():
    """4. 'Python and Java were used to build the application.' -> Both demonstrated."""
    text = "Python and Java were used to build the application."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is not None
    assert "Python and Java were used" in py_ex

    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is not None
    assert "Python and Java were used" in java_ex


def test_case_5_multi_skill_implementation_with_contrasting_considered():
    """5. 'Developed the application using Python and React, while Java was only considered.' -> Python and React demonstrated; Java not demonstrated."""
    text = "Developed the application using Python and React, while Java was only considered."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is not None
    assert "Developed the application using Python and React" in py_ex

    react_ex = find_supporting_excerpt_for_skill("React", text)
    assert react_ex is not None
    assert "Developed the application using Python and React" in react_ex

    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is None


def test_case_6_not_used_but_implemented():
    """6. 'Python was not used, but Java was used to build the application.' -> Python not demonstrated; Java demonstrated."""
    text = "Python was not used, but Java was used to build the application."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is None

    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is not None
    assert "Java was used to build the application" in java_ex


def test_case_7_used_although_planned_future():
    """7. 'Python was used, although Java was planned for future adoption.' -> Python demonstrated; Java not demonstrated."""
    text = "Python was used, although Java was planned for future adoption."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is not None
    assert "Python was used" in py_ex

    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is None


# ---------------------------------------------------------------------------
# 2. Consistent Application across All 5 Evidence Sources
# ---------------------------------------------------------------------------

def test_negation_scoping_in_projects():
    """Projects description applies skill-specific negation scoping without cross-contamination."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Project Negation Candidate"}},
        "projects": [
            {
                "title": "Data Hub",
                "description": "Python was used in the project and Java was only considered.",
                "technologies": ["Python", "Java"]
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    py_s = demonstrated.get("python")
    assert py_s is not None
    assert py_s["evidence_source"] == "project"
    assert py_s["excerpt_status"] == "available"
    assert py_s["confidence"] == 0.95
    assert any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])

    java_s = demonstrated.get("java")
    assert java_s is not None
    assert java_s["evidence_source"] == "registry_derived"
    assert java_s["excerpt_status"] == "unavailable"
    assert java_s["confidence"] == 0.60
    assert not any(s["skill"] == "Java" for s in profile["traceable_demonstrated_competencies"])


def test_negation_scoping_in_internships():
    """Internship responsibilities isolate skill negation without contaminating demonstrated skills."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Internship Negation Candidate"}},
        "internships": [
            {
                "organization": "Cloud AI",
                "position": "Intern",
                "responsibilities": [
                    "Python was implemented in the project and Docker was not used."
                ],
                "technologies": ["Python", "Docker"]
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    py_s = demonstrated.get("python")
    assert py_s is not None
    assert py_s["evidence_source"] == "internship"
    assert py_s["excerpt_status"] == "available"
    assert py_s["confidence"] == 0.90

    docker_s = demonstrated.get("docker")
    assert docker_s is not None
    assert docker_s["evidence_source"] == "registry_derived"
    assert docker_s["excerpt_status"] == "unavailable"
    assert docker_s["confidence"] == 0.60


def test_negation_scoping_in_matches():
    """Matches evidence isolates skill negation without contaminating demonstrated skills."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Match Negation Candidate"}},
        "matches": [
            {
                "skill": "Python",
                "evidence": "Python was used, although Java was planned for future adoption."
            },
            {
                "skill": "Java",
                "evidence": "Python was used, although Java was planned for future adoption."
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    py_s = demonstrated.get("python")
    assert py_s is not None
    assert py_s["evidence_source"] == "professional_experience"
    assert py_s["excerpt_status"] == "available"
    assert py_s["confidence"] == 0.90

    java_s = demonstrated.get("java")
    assert java_s is not None
    assert java_s["evidence_source"] == "registry_derived"
    assert java_s["excerpt_status"] == "unavailable"
    assert java_s["confidence"] == 0.60


def test_negation_scoping_in_professional_experience():
    """Professional experience isolates skill negation without contaminating demonstrated skills."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Prof Exp Negation Candidate"}},
        "evidence_registry": {
            "demonstrated_skills": ["Python", "Java"]
        },
        "professional_experience": [
            {
                "title": "Backend Engineer",
                "company": "Corp",
                "description": "Python was not used, but Java was used to build the application."
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    py_s = demonstrated.get("python")
    assert py_s is not None
    assert py_s["evidence_source"] == "registry_derived"
    assert py_s["excerpt_status"] == "unavailable"
    assert py_s["confidence"] == 0.60

    java_s = demonstrated.get("java")
    assert java_s is not None
    assert java_s["evidence_source"] == "professional_experience"
    assert java_s["excerpt_status"] == "available"
    assert java_s["confidence"] == 0.90


def test_negation_scoping_in_raw_resume_text():
    """Raw resume text isolates skill negation without contaminating demonstrated skills."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Raw Text Negation Candidate"}},
        "evidence_registry": {
            "demonstrated_skills": ["Python", "Java"]
        },
        "raw_text": "Experience Summary\nPython was considered and Java was implemented.\nEducation: B.Tech"
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    py_s = demonstrated.get("python")
    assert py_s is not None
    assert py_s["evidence_source"] == "registry_derived"
    assert py_s["excerpt_status"] == "unavailable"
    assert py_s["confidence"] == 0.60

    java_s = demonstrated.get("java")
    assert java_s is not None
    assert java_s["evidence_source"] == "professional_experience"
    assert java_s["excerpt_status"] == "available"
    assert java_s["confidence"] == 0.90


def test_profile_role_scoring_under_scoped_negations():
    """Role scoring awards 1.0 factor to demonstrated skill and 0.60 factor to scoped-negation skill."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Scoring Candidate"}},
        "projects": [
            {
                "title": "Platform",
                "description": "Python was used in the project and Java was only considered.",
                "technologies": ["Python", "Java"]
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    custom_role = {
        "name": "Custom Backend Specialist",
        "core_skills": ["Python", "Java"],
        "supporting_skills": [],
        "min_experience_years": 0.0,
        "required_education_level": "none"
    }
    eval_result = evaluate_specific_role("Custom Backend Specialist", profile, analysis, custom_role_requirements=custom_role)
    # Python: 1.5 * 1.0 = 1.5
    # Java: 1.5 * 0.60 = 0.90
    # Score = 2.4 / 3.0 = 80.0%
    assert eval_result["match_score"] == pytest.approx(80.0, rel=1e-2)
