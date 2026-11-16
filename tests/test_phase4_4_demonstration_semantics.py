"""
Phase 4.4 Test Suite: Demonstration Semantics & Resume Advisor Neutrality.

Mandatory Test Areas:
1. "Used Python to implement the data-processing module." — demonstrated.
2. "Python was considered but not used." — not demonstrated.
3. "Planned to migrate the application to Python." — not demonstrated.
4. "The project uses React; Python is listed as a possible future tool." — React demonstrated, Python not demonstrated.
5. "Tested the application using Python." — demonstrated.
6. Existing project/internship alias, duplicate precedence, and boundary tests remain passing.
7. Complete generated suggestion objects inspection (actionable examples, before/after examples, rationales,
   practical next actions, evidence context) for candidate with no project description or unrelated projects
   (no assumed APIs, databases, queries, latency, requests, services, caching, or queuing).
8. End-to-end profile extraction and role scoring assertions on demonstrated vs non-demonstrated semantics.
"""

import json
import pytest
from app import app, ANALYSIS_CACHE
from src.mentor.career_profile import (
    build_structured_career_profile,
    find_supporting_excerpt_for_skill
)
from src.mentor.role_recommender import evaluate_specific_role
from src.mentor.resume_advisor import generate_resume_improvement_suggestions

app.config["TESTING"] = True


# ---------------------------------------------------------------------------
# Test 1-5: Demonstration Semantics Scenarios
# ---------------------------------------------------------------------------

def test_demonstrated_use_active_implementation():
    """1. 'Used Python to implement the data-processing module.' must establish demonstrated use."""
    text = "Used Python to implement the data-processing module."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is not None
    assert "Used Python to implement" in excerpt


def test_negated_mention_not_demonstrated():
    """2. 'Python was considered but not used.' must NOT establish demonstrated use."""
    text = "Python was considered but not used."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is None


def test_planned_future_migration_not_demonstrated():
    """3. 'Planned to migrate the application to Python.' must NOT establish demonstrated use."""
    text = "Planned to migrate the application to Python."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is None


def test_multiclause_demonstrated_vs_future_tool():
    """4. 'The project uses React; Python is listed as a possible future tool.' -> React demonstrated, Python not."""
    text = "The project uses React; Python is listed as a possible future tool."
    react_excerpt = find_supporting_excerpt_for_skill("React", text)
    python_excerpt = find_supporting_excerpt_for_skill("Python", text)

    assert react_excerpt is not None
    assert "React" in react_excerpt

    assert python_excerpt is None


def test_demonstrated_testing_use():
    """5. 'Tested the application using Python.' must establish demonstrated use."""
    text = "Tested the application using Python."
    excerpt = find_supporting_excerpt_for_skill("Python", text)
    assert excerpt is not None
    assert "Tested the application using Python" in excerpt


# ---------------------------------------------------------------------------
# Test 6: Additional Non-Demonstrated Phrases & Semantic Variants
# ---------------------------------------------------------------------------

def test_additional_non_demonstrated_phrases():
    """Ensure proposed, potential, and evaluated-against tools are not credited as demonstrated."""
    cases = [
        ("Evaluated Docker and Kubernetes but decided against adopting them.", "Docker", False),
        ("Evaluated Docker and Kubernetes but decided against adopting them.", "Kubernetes", False),
        ("Proposal to use Go for upcoming batch jobs.", "Go", False),
        ("Team intends to transition to TypeScript next quarter.", "TypeScript", False),
        ("System built in Java; Rust was investigated as a potential future tool.", "Java", True),
        ("System built in Java; Rust was investigated as a potential future tool.", "Rust", False),
    ]

    for sample_text, skill, should_demonstrate in cases:
        res = find_supporting_excerpt_for_skill(skill, sample_text)
        if should_demonstrate:
            assert res is not None, f"Expected {skill} to be demonstrated in '{sample_text}'"
        else:
            assert res is None, f"Expected {skill} NOT to be demonstrated in '{sample_text}', got: {res}"


# ---------------------------------------------------------------------------
# Test 7: Profile Integration & Role Scoring with Semantic Differentiation
# ---------------------------------------------------------------------------

def test_profile_semantic_differentiation_role_scoring():
    """Assert non-demonstrated skill in project tag drops to registry tier (0.60 factor) in role evaluation."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Semantic Candidate"},
            "skills": [],
            "education": []
        },
        "projects": [
            {
                "title": "Legacy Portal",
                "description": "Built interactive frontend in React. Python was considered but not used.",
                "technologies": ["React", "Python"]
            }
        ]
    }

    profile = build_structured_career_profile(analysis)
    demonstrated = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    react_s = demonstrated.get("react")
    python_s = demonstrated.get("python")

    assert react_s["evidence_source"] == "project"
    assert react_s["excerpt_status"] == "available"
    assert react_s["confidence"] == 0.95

    assert python_s["evidence_source"] == "registry_derived"
    assert python_s["excerpt_status"] == "unavailable"
    assert python_s["confidence"] == 0.60
    assert python_s["excerpt"] is None

    assert any(s["skill"] == "React" for s in profile["traceable_demonstrated_competencies"])
    assert not any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])
    assert any(s["skill"] == "Python" for s in profile["registry_derived_competencies"])

    custom_role = {
        "name": "Fullstack Lead",
        "core_skills": ["React", "Python"],
        "supporting_skills": [],
        "min_experience_years": 0.0,
        "required_education_level": "none"
    }

    eval_result = evaluate_specific_role("Fullstack Lead", profile, analysis, custom_role_requirements=custom_role)
    # React: 1.5 * 1.0 = 1.5
    # Python: 1.5 * 0.60 = 0.90
    # Score = 2.4 / 3.0 = 80.0%
    assert eval_result["match_score"] == 80.0


# ---------------------------------------------------------------------------
# Test 8: Resume Advisor Complete Neutrality & No Assumed Architecture
# ---------------------------------------------------------------------------

def test_resume_advisor_complete_neutrality_across_all_fields():
    """Verify complete suggestion objects contain zero assumed APIs, databases, query latency, or requests."""
    # Candidate with an unrelated project (graphics/audio design)
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Creative Designer"},
            "skills": [
                {"name": "Photoshop", "category": "Design"},
                {"name": "Figma", "category": "Design"}
            ],
            "education": []
        },
        "projects": [
            {
                "title": "Brand Identity Design",
                "description": "Created typography guidelines, vector icon sets, and responsive visual mockups."
            }
        ]
    }

    profile = build_structured_career_profile(analysis)
    suggestions = generate_resume_improvement_suggestions(profile, analysis)

    assert len(suggestions) > 0

    prohibited_architectures = [
        "rest api",
        "api endpoint",
        "database quer",
        "query latency",
        "telemetry",
        "caching",
        "task queue",
        "handling [count] requests",
        "handled project assignments and updates",
        "service integration",
        "postgresql schema",
        "b-tree"
    ]

    for sug in suggestions:
        full_json = json.dumps(sug).lower()

        # Check all text fields
        for term in prohibited_architectures:
            assert term not in full_json, (
                f"Prohibited architecture assumption '{term}' found in suggestion {sug.get('suggestion_id')}: {full_json}"
            )

        # Check required neutral templates in quantifiable_metrics
        if sug["suggestion_id"] == "quantifiable_metrics":
            assert "[describe the actual project or task completed]" in full_json
            assert "[explain the specific contribution]" in full_json
            assert "[describe the verified outcome, if measurable" in full_json

            # Verify action items and rationales do not assume database queries or latency
            action_text = sug.get("practical_next_action", "").lower()
            assert "query latency" not in action_text
            assert "requests" not in action_text

            reason_text = sug.get("reason", "").lower()
            assert "api" not in reason_text
            assert "database" not in reason_text
