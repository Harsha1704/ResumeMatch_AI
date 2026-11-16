"""
Phase 4.3 Test Suite: Skill-Level Evidence Traceability & Resume Advisor Neutrality.

Mandatory Test Areas:
1. Project technology not mentioned in its description must NOT receive traceable 1.0 credit (must be registry-derived, 0.60).
2. Project technology explicitly supported by its description can receive traceable 1.0 credit.
3. Internship technology not supported by responsibilities must NOT receive traceable 1.0 credit (0.60).
4. Internship technology supported by responsibilities can receive traceable 1.0 credit.
5. C, C++, C#, and .NET matching must not produce substring-based false positives.
6. Registry-derived and candidate-confirmed skills must retain their correct evidence tiers;
   duplicate skills resolve without allowing weaker sources to overwrite stronger genuine evidence.
7. Candidate with no project descriptions receives neutral Resume Advisor placeholders, not invented project claims.
8. Candidate with an existing project receives suggestions that do not invent architecture or implementation details.
9. Verification of actual evidence classification, excerpt content, confidence, and resulting role scores.
"""

import json
import pytest
from app import app, ANALYSIS_CACHE
from src.mentor.career_profile import (
    build_structured_career_profile,
    find_supporting_excerpt_for_skill
)
from src.mentor.role_recommender import (
    recommend_suitable_roles,
    evaluate_specific_role,
    ROLE_ARCHETYPES
)
from src.mentor.resume_advisor import generate_resume_improvement_suggestions
from src.common.evidence_registry import matches_skill_token

app.config["TESTING"] = True


# ---------------------------------------------------------------------------
# Test 1: Project Technology Not In Description Does Not Receive Traceable 1.0 Credit
# ---------------------------------------------------------------------------

def test_project_tech_not_in_description_no_traceable_credit():
    """Project technology not supported by description must receive 0.60 registry credit, not 1.0 full credit."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Frontend Dev"},
            "skills": [
                {"name": "React", "category": "Frontend"},
                {"name": "Python", "category": "Backend"}
            ],
            "education": []
        },
        "projects": [
            {
                "title": "Interactive Client Portal",
                "description": "Developed responsive user interface and interactive state management in React.",
                "technologies": ["React", "Python"]  # Python is in metadata tag but NOT in description
            }
        ]
    }

    profile = build_structured_career_profile(analysis)

    # 1. Assert skill-level evidence classification
    skills_by_name = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    react_skill = skills_by_name.get("react")
    python_skill = skills_by_name.get("python")

    assert react_skill is not None
    assert react_skill["evidence_source"] == "project"
    assert react_skill["excerpt_status"] == "available"
    assert react_skill["confidence"] == 0.95
    assert "React" in react_skill["excerpt"]

    assert python_skill is not None
    assert python_skill["evidence_source"] == "registry_derived"
    assert python_skill["excerpt_status"] == "unavailable"
    assert python_skill["excerpt"] is None
    assert python_skill["confidence"] == 0.60
    assert "not supported by descriptive" in python_skill["provenance_note"].lower() or "without descriptive excerpt" in python_skill["provenance_note"].lower()

    # Verify membership in separated collections
    assert any(s["skill"] == "React" for s in profile["traceable_demonstrated_competencies"])
    assert not any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])
    assert any(s["skill"] == "Python" for s in profile["registry_derived_competencies"])

    # 2. Evaluate against a custom role requiring React and Python as core skills (1.5 weight each)
    custom_role = {
        "name": "Fullstack Engineer",
        "core_skills": ["React", "Python"],
        "supporting_skills": [],
        "min_experience_years": 0.0,
        "required_education_level": "none"
    }

    eval_result = evaluate_specific_role("Fullstack Engineer", profile, analysis, custom_role_requirements=custom_role)

    # React core: 1.5 * 1.0 = 1.5
    # Python core: 1.5 * 0.60 = 0.90
    # Total score = (1.5 + 0.90) / 3.0 = 2.4 / 3.0 = 80.0% (NOT 100.0%)
    assert eval_result["match_score"] == 80.0
    assert eval_result["match_score"] < 100.0


# ---------------------------------------------------------------------------
# Test 2: Project Technology Supported By Description Receives Traceable 1.0 Credit
# ---------------------------------------------------------------------------

def test_project_tech_supported_by_description_receives_traceable_credit():
    """Project technologies genuinely supported by description receive 1.0 full credit."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Backend Dev"},
            "skills": [
                {"name": "Python", "category": "Backend"},
                {"name": "Docker", "category": "DevOps"}
            ],
            "education": []
        },
        "projects": [
            {
                "title": "Cloud Microservice",
                "description": "Engineered REST service in Python. Containerized local deployments using Docker.",
                "technologies": ["Python", "Docker"]
            }
        ]
    }

    profile = build_structured_career_profile(analysis)

    skills_by_name = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    py = skills_by_name.get("python")
    dk = skills_by_name.get("docker")

    assert py["evidence_source"] == "project"
    assert py["excerpt_status"] == "available"
    assert py["confidence"] == 0.95
    assert "Python" in py["excerpt"]

    assert dk["evidence_source"] == "project"
    assert dk["excerpt_status"] == "available"
    assert dk["confidence"] == 0.95
    assert "Docker" in dk["excerpt"]

    assert any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])
    assert any(s["skill"] == "Docker" for s in profile["traceable_demonstrated_competencies"])

    custom_role = {
        "name": "Backend Container Engineer",
        "core_skills": ["Python", "Docker"],
        "supporting_skills": [],
        "min_experience_years": 0.0,
        "required_education_level": "none"
    }

    eval_result = evaluate_specific_role("Backend Container Engineer", profile, analysis, custom_role_requirements=custom_role)
    assert eval_result["match_score"] == 100.0


# ---------------------------------------------------------------------------
# Test 3: Internship Technology Not Supported by Responsibilities
# ---------------------------------------------------------------------------

def test_internship_tech_not_supported_by_responsibilities_no_traceable_credit():
    """Internship technology listed in metadata but omitted from responsibilities receives 0.60 credit."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Data Intern"},
            "skills": [],
            "education": []
        },
        "internships": [
            {
                "organization": "DataCorp",
                "position": "Analytics Intern",
                "responsibilities": [
                    "Built automated ETL ingestion pipelines using Python.",
                    "Monitored scheduled daily data transfers."
                ],
                "technologies": ["Python", "Flask"]  # Flask is in tag but not in responsibilities
            }
        ]
    }

    profile = build_structured_career_profile(analysis)

    skills_by_name = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    py = skills_by_name.get("python")
    flask = skills_by_name.get("flask")

    assert py["evidence_source"] == "internship"
    assert py["excerpt_status"] == "available"
    assert py["confidence"] == 0.90
    assert "Python" in py["excerpt"]

    assert flask["evidence_source"] == "registry_derived"
    assert flask["excerpt_status"] == "unavailable"
    assert flask["confidence"] == 0.60
    assert flask["excerpt"] is None

    assert any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])
    assert not any(s["skill"] == "Flask" for s in profile["traceable_demonstrated_competencies"])
    assert any(s["skill"] == "Flask" for s in profile["registry_derived_competencies"])

    custom_role = {
        "name": "Flask Pipeline Engineer",
        "core_skills": ["Python", "Flask"],
        "supporting_skills": [],
        "min_experience_years": 0.0,
        "required_education_level": "none"
    }

    eval_result = evaluate_specific_role("Flask Pipeline Engineer", profile, analysis, custom_role_requirements=custom_role)
    assert eval_result["match_score"] == 80.0


# ---------------------------------------------------------------------------
# Test 4: Internship Technology Supported by Responsibilities
# ---------------------------------------------------------------------------

def test_internship_tech_supported_by_responsibilities_receives_traceable_credit():
    """Internship technologies genuinely supported by responsibilities receive 0.90 confidence and 1.0 factor."""
    analysis = {
        "candidate_profile": {"name": {"full_name": "Web Intern"}, "skills": [], "education": []},
        "internships": [
            {
                "organization": "WebStudio",
                "position": "Software Intern",
                "responsibilities": [
                    "Engineered RESTful web services with Flask framework.",
                    "Optimized relational database queries in PostgreSQL."
                ],
                "technologies": ["Flask", "PostgreSQL"]
            }
        ]
    }

    profile = build_structured_career_profile(analysis)

    skills_by_name = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}
    flask = skills_by_name.get("flask")
    pg = skills_by_name.get("postgresql")

    assert flask["evidence_source"] == "internship"
    assert flask["excerpt_status"] == "available"
    assert flask["confidence"] == 0.90
    assert "Flask" in flask["excerpt"]

    assert pg["evidence_source"] == "internship"
    assert pg["excerpt_status"] == "available"
    assert pg["confidence"] == 0.90
    assert "PostgreSQL" in pg["excerpt"]


# ---------------------------------------------------------------------------
# Test 5: C, C++, C#, and .NET Substring Isolation
# ---------------------------------------------------------------------------

def test_c_cpp_csharp_dotnet_no_substring_false_positives():
    """Verify C, C++, C#, and .NET do not produce substring false positives."""
    text_cpp_csharp = "Engineered real-time graphics simulator in C++ and tools in C# with .NET 8."
    text_c_only = "Developed embedded kernel firmware modules in C and assembly."
    text_network = "High-speed ethernet cabling and network subnet configuration."

    # 1. Plain 'C' matching
    assert find_supporting_excerpt_for_skill("C", text_cpp_csharp) is None
    assert find_supporting_excerpt_for_skill("C", text_c_only) is not None
    assert find_supporting_excerpt_for_skill("C", text_network) is None

    # 2. 'C++' matching
    assert find_supporting_excerpt_for_skill("C++", text_cpp_csharp) is not None
    assert find_supporting_excerpt_for_skill("C++", text_c_only) is None

    # 3. 'C#' matching
    assert find_supporting_excerpt_for_skill("C#", text_cpp_csharp) is not None
    assert find_supporting_excerpt_for_skill("C#", text_c_only) is None

    # 4. '.NET' matching
    assert find_supporting_excerpt_for_skill(".NET", text_cpp_csharp) is not None
    assert find_supporting_excerpt_for_skill(".NET", text_network) is None

    # 5. Profile-level test with C listed in metadata but only C++ in description
    analysis_c = {
        "candidate_profile": {"name": {"full_name": "Graphics Dev"}, "skills": [], "education": []},
        "projects": [
            {
                "title": "Shader Engine",
                "description": "Implemented procedural graphics shaders using C++ rendering pipelines.",
                "technologies": ["C", "C++"]  # C is in tags, but description ONLY has C++
            }
        ]
    }

    profile_c = build_structured_career_profile(analysis_c)
    skills_by_name = {s["skill"].lower(): s for s in profile_c["demonstrated_competencies"]}

    c_skill = skills_by_name.get("c")
    cpp_skill = skills_by_name.get("c++")

    assert cpp_skill["excerpt_status"] == "available"
    assert cpp_skill["confidence"] == 0.95
    assert "C++" in cpp_skill["excerpt"]

    assert c_skill["excerpt_status"] == "unavailable"
    assert c_skill["confidence"] == 0.60
    assert c_skill["excerpt"] is None
    assert c_skill["evidence_source"] == "registry_derived"


# ---------------------------------------------------------------------------
# Test 6: Evidence Tier Integrity & Duplicate Skill Resolution
# ---------------------------------------------------------------------------

def test_registry_derived_and_candidate_confirmed_tiers_and_duplicate_resolution():
    """Verify duplicate skills resolve without weaker sources overwriting stronger evidence."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Tier Candidate"},
            "skills": [],
            "education": []
        },
        "projects": [
            {
                "title": "Project A (Unsupported Tag)",
                "description": "General administrative automation script.",
                "technologies": ["Python", "Docker"]  # Python unsupported here
            },
            {
                "title": "Project B (Supported Excerpt)",
                "description": "Architected low-latency microservice using Python with extensive unit testing.",
                "technologies": ["Python"]  # Python genuinely supported here
            }
        ],
        "user_confirmations": {
            "SQL": {"status": "confirmed"}
        },
        "partially_evidenced_skills": ["AWS"]
    }

    profile = build_structured_career_profile(analysis)
    skills_by_name = {s["skill"].lower(): s for s in profile["demonstrated_competencies"]}

    # Python was in Project A (unsupported) and Project B (supported):
    # Stronger genuine evidence from Project B must NOT be overwritten by Project A
    py = skills_by_name.get("python")
    assert py is not None
    assert py["evidence_source"] == "project"
    assert py["excerpt_status"] == "available"
    assert py["confidence"] == 0.95
    assert "Python" in py["excerpt"]
    assert any(s["skill"] == "Python" for s in profile["traceable_demonstrated_competencies"])

    # Docker was only in Project A (unsupported):
    dk = skills_by_name.get("docker")
    assert dk is not None
    assert dk["evidence_source"] == "registry_derived"
    assert dk["excerpt_status"] == "unavailable"
    assert dk["confidence"] == 0.60

    # SQL is candidate-confirmed
    sql_conf = next((c for c in profile["candidate_confirmed_competencies"] if c["skill"] == "SQL"), None)
    assert sql_conf is not None
    assert sql_conf["confidence"] == 0.75
    assert sql_conf["evidence_source"] == "candidate_confirmed"

    # AWS is partially evidenced
    aws_part = next((p for p in profile["partially_evidenced_competencies"] if p["skill"] == "AWS"), None)
    assert aws_part is not None
    assert aws_part["confidence"] == 0.50
    assert aws_part["evidence_source"] == "skills_section"


# ---------------------------------------------------------------------------
# Test 7: Candidate With No Project Descriptions Receives Neutral Placeholders
# ---------------------------------------------------------------------------

def test_candidate_no_project_descriptions_receives_neutral_advisor_placeholders():
    """Candidate with no project descriptions receives neutral templates without invented project claims."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "New Candidate"},
            "skills": [],
            "education": [],
            "projects": []
        },
        "projects": []
    }

    profile = build_structured_career_profile(analysis)
    suggestions = generate_resume_improvement_suggestions(profile, analysis)

    assert len(suggestions) > 0
    quant_sug = next(s for s in suggestions if s["suggestion_id"] == "quantifiable_metrics")

    full_text = json.dumps(quant_sug)

    # Must contain required neutral placeholders
    assert "[Describe the actual project or task completed]" in full_text or "[Describe the actual project or task you completed]" in full_text
    assert "[Explain the specific contribution]" in full_text or "[Explain your genuine contribution]" in full_text
    assert "[Describe the verified outcome, if measurable" in full_text or "[Add a measured result only if you have verified evidence" in full_text

    # Must NOT contain candidate-sounding claims or assumed architectures
    forbidden = [
        "built a backend service using python and flask",
        "worked on rest apis and database queries",
        "process customer telemetry data",
        "composite b-tree",
        "scalable caching",
        "asynchronous task queuing"
    ]
    for f in forbidden:
        assert f not in full_text.lower(), f"Forbidden phrase '{f}' found in suggestion"


# ---------------------------------------------------------------------------
# Test 8: Candidate With Existing Project Suggestions Do Not Invent Architecture
# ---------------------------------------------------------------------------

def test_candidate_with_existing_project_does_not_invent_architecture():
    """Suggestions for an existing project must not assume it is a service, API, or database system."""
    analysis = {
        "candidate_profile": {
            "name": {"full_name": "Designer Dev"},
            "skills": [],
            "education": []
        },
        "projects": [
            {
                "title": "Interactive Portfolio Website",
                "description": "Created interactive styling and responsive UI layouts."
            }
        ]
    }

    profile = build_structured_career_profile(analysis)
    suggestions = generate_resume_improvement_suggestions(profile, analysis)

    quant_sug = next(s for s in suggestions if s["suggestion_id"] == "quantifiable_metrics")
    full_text = json.dumps(quant_sug)

    # Must not assume the portfolio is a 'service', 'API endpoint', or 'database'
    assert "interactive portfolio website service" not in full_text.lower()
    assert "rest api endpoints" not in full_text.lower()
    assert "database queries" not in full_text.lower()
    assert "[Interactive Portfolio Website: Describe the actual project or task completed]" in full_text or "[Interactive Portfolio Website: Describe the actual project or task you completed]" in full_text
