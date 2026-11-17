"""
Phase 4.6 Test Suite: Unrelated Skill / Action Verb Isolation.

Mandatory Test Areas:
1. Specific Semantic Isolation Cases:
   - "Python is listed in my skills, and I developed a project using Java." -> Python: NOT demonstrated, Java: demonstrated.
   - "Python was mentioned in the requirements; I built the application using Java." -> Python: NOT demonstrated, Java: demonstrated.
   - "I considered Python, but implemented the project using Java." -> Python: NOT demonstrated, Java: demonstrated.
   - "Developed the application using Python and React." -> Python: demonstrated; React: demonstrated.
   - "Built a data pipeline using Python, then tested it with pytest." -> Python: demonstrated.
   - "Python was used in the project, while Java was only considered." -> Python: demonstrated; Java: NOT demonstrated.

2. Consistent Application across All 5 Evidence Sources:
   - Project descriptions
   - Internship responsibilities
   - Match evidence
   - Professional experience
   - Raw resume text
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
# 1. Dedicated Semantic Isolation Cases
# ---------------------------------------------------------------------------

def test_skills_listing_vs_action_verb():
    """'Python is listed in my skills, and I developed a project using Java.' -> Python: NOT demonstrated, Java: demonstrated."""
    text = "Python is listed in my skills, and I developed a project using Java."
    assert find_supporting_excerpt_for_skill("Python", text) is None
    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is not None
    assert "developed a project using Java" in java_ex


def test_requirements_mention_vs_action_verb():
    """'Python was mentioned in the requirements; I built the application using Java.' -> Python: NOT demonstrated, Java: demonstrated."""
    text = "Python was mentioned in the requirements; I built the application using Java."
    assert find_supporting_excerpt_for_skill("Python", text) is None
    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is not None
    assert "built the application using Java" in java_ex


def test_considered_vs_implemented_action():
    """'I considered Python, but implemented the project using Java.' -> Python: NOT demonstrated, Java: demonstrated."""
    text = "I considered Python, but implemented the project using Java."
    assert find_supporting_excerpt_for_skill("Python", text) is None
    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is not None
    assert "implemented the project using Java" in java_ex


def test_multiple_skills_in_single_genuine_implementation():
    """'Developed the application using Python and React.' -> Python: demonstrated; React: demonstrated."""
    text = "Developed the application using Python and React."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    react_ex = find_supporting_excerpt_for_skill("React", text)

    assert py_ex is not None
    assert "Developed the application using Python and React" in py_ex

    assert react_ex is not None
    assert "Developed the application using Python and React" in react_ex


def test_sequential_genuine_actions():
    """'Built a data pipeline using Python, then tested it with pytest.' -> Python: demonstrated."""
    text = "Built a data pipeline using Python, then tested it with pytest."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is not None
    assert "Built a data pipeline using Python" in py_ex


def test_contrasting_used_vs_only_considered():
    """'Python was used in the project, while Java was only considered.' -> Python: demonstrated; Java: NOT demonstrated."""
    text = "Python was used in the project, while Java was only considered."
    py_ex = find_supporting_excerpt_for_skill("Python", text)
    assert py_ex is not None
    assert "Python was used in the project" in py_ex

    java_ex = find_supporting_excerpt_for_skill("Java", text)
    assert java_ex is None


def test_additional_isolation_variants():
    """Additional variants covering multi-clause boundaries and contrasting tools."""
    cases = [
        ("Python was used to build the pipeline, but Docker was not used.", "Python", True),
        ("Python was used to build the pipeline, but Docker was not used.", "Docker", False),
        ("I considered Python and implemented the project using Java.", "Python", False),
        ("I considered Python and implemented the project using Java.", "Java", True),
        ("Designed the UI in Figma and developed the backend in Go.", "Figma", True),
        ("Designed the UI in Figma and developed the backend in Go.", "Go", True),
    ]
    for text, skill, expected in cases:
        res = find_supporting_excerpt_for_skill(skill, text)
        if expected:
            assert res is not None, f"Expected {skill} to be demonstrated in '{text}'"
        else:
            assert res is None, f"Expected {skill} NOT to be demonstrated in '{text}', got: {res}"


# ---------------------------------------------------------------------------
# 2. Consistent Application across All 5 Evidence Sources
# ---------------------------------------------------------------------------

def test_isolation_in_project_descriptions():
    """Project description mentioning skill without action verb does not grant full credit."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Project Isolation Candidate"}},
        "projects": [
            {
                "title": "Service Hub",
                "description": "Python is listed in my skills, and I developed a project using Java.",
                "technologies": ["Python", "Java"]
            }
        ]
    }
    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    # Python is not demonstrated in the project description
    py_s = demonstrated.get("python")
    assert py_s is not None
    assert py_s["evidence_source"] == "registry_derived"
    assert py_s["excerpt_status"] == "unavailable"
    assert py_s["confidence"] == 0.60
    assert not any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])

    # Java is demonstrated
    java_s = demonstrated.get("java")
    assert java_s is not None
    assert java_s["evidence_source"] == "project"
    assert java_s["excerpt_status"] == "available"
    assert java_s["confidence"] == 0.95
    assert any(s["skill"] == "Java" for s in profile["traceable_demonstrated_competencies"])


def test_isolation_in_internship_responsibilities():
    """Internship responsibilities mentioning skill without action verb does not grant full credit."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Internship Isolation Candidate"}},
        "internships": [
            {
                "organization": "Tech Corp",
                "position": "Intern",
                "responsibilities": [
                    "Python was mentioned in the requirements; I built the application using Java."
                ],
                "technologies": ["Python", "Java"]
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
    assert java_s["evidence_source"] == "internship"
    assert java_s["excerpt_status"] == "available"
    assert java_s["confidence"] == 0.90


def test_isolation_in_matches_evidence():
    """Matches evidence with unrelated action verb does not grant full credit."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Match Isolation Candidate"}},
        "matches": [
            {
                "skill": "Python",
                "evidence": "I considered Python, but implemented the project using Java."
            },
            {
                "skill": "Java",
                "evidence": "I considered Python, but implemented the project using Java."
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


def test_isolation_in_professional_experience():
    """Professional experience description isolates unrelated skill from action verb."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Prof Exp Isolation Candidate"}},
        "evidence_registry": {
            "demonstrated_skills": ["Python", "Java"]
        },
        "professional_experience": [
            {
                "title": "Software Engineer",
                "company": "Apex",
                "description": "Python is listed in my skills, and I developed a project using Java."
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


def test_isolation_in_raw_resume_text():
    """Raw resume text isolates unrelated skill from action verb."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Raw Text Isolation Candidate"}},
        "evidence_registry": {
            "demonstrated_skills": ["Python", "Java"]
        },
        "raw_text": "Experience Summary\nPython is listed in my skills, and I developed a project using Java.\nEducation: B.S. CS"
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
