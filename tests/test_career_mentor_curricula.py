"""
Regression Test Suite for Career Mentor Curricula, Action Plans & Personalization Upgrade.
Verifies Part B Requirements:
- B1 & B2: 14 domain roadmap families populated.
- B3: Comprehensive SQL Roadmap (7 distinct stages: relational modeling -> basic queries -> joins -> CTEs -> project -> indexing -> docs).
- B4: Comprehensive Docker Roadmap (7 distinct stages: containers vs VMs -> CLI -> Dockerfile layers -> Flask container -> Compose -> security -> verification).
- B5: Comprehensive Communication Roadmap (strictly non-coding! 7 stages: PREP -> 60s pitch -> filler words -> non-tech audience -> STAR -> mock interviews -> presentation).
- B6: Complete 10-section action plans for every gap.
- B7: Realistic schedules accounting for available hours, difficulty, and pacing.
- B8: Mentor personalization references candidate's preferred name and verified strengths without assuming lack of capability.
- B9: Honest fallback for unverified skills marked with is_verified_specialized=False.
"""

import pytest
from src.mentor.skill_curricula import (
    DOMAIN_ROADMAP_FAMILIES,
    SKILL_SPECIFIC_CURRICULA,
    get_domain_for_skill,
    get_curriculum_for_skill,
    build_skill_action_plan
)
from src.mentor.mentor_engine import CareerMentorEngine
from src.mentor.roadmap_generator import generate_skill_roadmap, generate_realistic_study_plan
from src.mentor.message_templates import format_gap_explanation, build_welcome_greeting

SAMPLE_ANALYSIS_HARSHA = {
    "raw_text": "Harsha Vardhan\nEmail: harsha@example.com\nSkills: Python, Scikit-Learn, Pandas, Git, Flask",
    "filename": "Harsha_Resume.pdf",
    "job_title": "Full-Stack Cloud & ML Engineer",
    "resume_skills": ["Python", "Scikit-Learn", "Pandas", "Git", "Flask"],
    "matched_skills": ["Python", "Flask", "Git"],
    "missing_required_skills": ["SQL", "Docker", "AWS"],
    "missing_preferred_skills": ["Kubernetes", "Power BI", "Communication"],
    "partially_evidenced_required_skills": [],
    "partially_evidenced_skills": [],
    "projects": [
        {
            "title": "Machine Learning Prediction Engine",
            "technologies": ["Python", "Scikit-Learn", "Pandas", "Flask"],
            "description": "Engineered supervised machine learning classification pipeline with cross-validation."
        }
    ],
    "internships": [
        {
            "organization": "DataCore Systems",
            "position": "Data Science Intern",
            "dates": "May 2023 - July 2023",
            "technologies": ["Python", "Pandas"],
            "responsibilities": ["Data cleansing and preprocessing", "Authored feature transformation scripts"]
        }
    ]
}


def test_14_domain_roadmap_families():
    """Verify all 14 domain roadmap families are present with descriptions, prerequisites, and stages."""
    required_domains = [
        "programming_languages",
        "data_structures_algorithms",
        "backend_frameworks",
        "frontend_development",
        "databases_sql",
        "machine_learning_ai",
        "data_analytics_visualization",
        "cloud_computing",
        "devops_infrastructure",
        "cybersecurity",
        "productivity_software",
        "project_management",
        "communication_soft_skills",
        "professional_methodologies"
    ]
    assert len(required_domains) == 14
    for dom_key in required_domains:
        assert dom_key in DOMAIN_ROADMAP_FAMILIES, f"Domain family '{dom_key}' missing!"
        dom = DOMAIN_ROADMAP_FAMILIES[dom_key]
        assert "domain_name" in dom and dom["domain_name"]
        assert "description" in dom and len(dom["description"]) > 20
        assert "prerequisites" in dom and len(dom["prerequisites"]) >= 1
        assert "stages" in dom and len(dom["stages"]) == 7


def test_high_demand_specialized_curricula():
    """Verify rich specialized curricula exist for high-demand skills."""
    skills = [
        "python", "sql", "docker", "kubernetes", "power bi",
        "excel", "communication", "project management",
        "machine learning", "cybersecurity", "aws", "react", "ci/cd",
        "git", "linux"
    ]
    for s in skills:
        curr = get_curriculum_for_skill(s)
        assert curr["is_verified_specialized"] is True, f"Skill '{s}' must be specialized!"
        assert len(curr["stages"]) == 7, f"Skill '{s}' must have 7 stages!"
        assert curr["why_it_matters"] and len(curr["why_it_matters"]) > 30
        assert len(curr["fundamental_concepts"]) >= 3
        assert len(curr["intermediate_concepts"]) >= 3
        assert len(curr["advanced_concepts"]) >= 3
        assert len(curr["interview_prep"]) >= 2
        assert "resume_evidence" in curr and curr["resume_evidence"]["bullet_template"]


def test_git_and_linux_specialized_curricula_and_actions():
    """Verify Git and Linux provide dedicated, non-generic counseling and practical actions."""
    from src.mentor.counseling_profile import DOMAIN_COUNSELING_INTELLIGENCE
    from src.mentor.mentor_engine import recommend_gap_action

    for s in ["git", "linux"]:
        assert s in DOMAIN_COUNSELING_INTELLIGENCE, f"'{s}' must be in DOMAIN_COUNSELING_INTELLIGENCE"
        intel = DOMAIN_COUNSELING_INTELLIGENCE[s]
        assert "why_it_matters" in intel and len(intel["why_it_matters"]) > 40
        assert "interview_talking_point" in intel and len(intel["interview_talking_point"]) > 40
        assert "verification_method" in intel and len(intel["verification_method"]) > 40

        action = recommend_gap_action(s, "Engineering Tools and Practices", [])
        assert "Specialized learning guidance is not yet available" not in action
        assert len(action) > 30


def test_comprehensive_sql_curriculum_stages():
    """Verify SQL roadmap contains the 7 distinct required stages (B3)."""
    sql = get_curriculum_for_skill("SQL")
    assert sql["is_verified_specialized"] is True
    stages = sql["stages"]
    assert len(stages) == 7

    # 1. Relational fundamentals & schema design
    assert "Relational Fundamentals" in stages[0]["name"] or "Schema" in stages[0]["name"]
    # 2. Querying basics (SELECT, WHERE, GROUP BY)
    assert "Querying" in stages[1]["name"] or "SELECT" in stages[1]["task"]
    # 3. Multi-table joins & aggregates
    assert "Join" in stages[2]["name"] or "Aggregat" in stages[2]["name"]
    # 4. Subqueries, CTEs, Window functions
    assert "CTE" in stages[3]["name"] or "Subquer" in stages[3]["name"] or "Window" in stages[3]["name"]
    # 5. Database project
    assert "Project" in stages[4]["name"] or "Schema" in stages[4]["name"]
    # 6. Indexing & optimization
    assert "Optimiz" in stages[5]["name"] or "Index" in stages[5]["name"] or "Execution Plan" in stages[5]["name"]
    # 7. Verification & documentation
    assert "Verification" in stages[6]["name"] or "Evidence" in stages[6]["name"] or "Resume" in stages[6]["name"]

    for st in stages:
        assert len(st["complete_explanation"]) >= 80
        assert st["concrete_example"]
        assert st["exercise"]
        assert st["deliverable"]
        assert st["verification_method"]


def test_comprehensive_docker_curriculum_stages():
    """Verify Docker roadmap contains the 7 distinct required stages (B4)."""
    docker = get_curriculum_for_skill("Docker")
    assert docker["is_verified_specialized"] is True
    stages = docker["stages"]
    assert len(stages) == 7

    # 1. Containers vs VMs
    assert "Virtual Machines" in stages[0]["name"] or "Fundamentals" in stages[0]["name"]
    # 2. CLI & Lifecycle
    assert "CLI" in stages[1]["name"] or "Lifecycle" in stages[1]["name"]
    # 3. Dockerfile & Layers
    assert "Dockerfile" in stages[2]["name"] or "Layer" in stages[2]["name"]
    # 4. Containerizing Flask
    assert "Flask" in stages[3]["name"] or "Application" in stages[3]["name"]
    # 5. Docker Compose
    assert "Compose" in stages[4]["name"] or "Orchestrat" in stages[4]["name"]
    # 6. Security & Optimization
    assert "Security" in stages[5]["name"] or "Optimiz" in stages[5]["name"]
    # 7. Production Verification & Docs
    assert "Verification" in stages[6]["name"] or "Production" in stages[6]["name"]


def test_communication_roadmap_is_strictly_non_coding():
    """Verify Communication roadmap contains ZERO code references and focuses purely on spoken/interpersonal delivery (B5)."""
    comm = get_curriculum_for_skill("Communication")
    assert comm["is_verified_specialized"] is True
    stages = comm["stages"]
    assert len(stages) == 7

    # 1. PREP structure
    assert "PREP" in stages[0]["name"] or "Spoken" in stages[0]["name"]
    # 2. 60-second pitch
    assert "60-Second" in stages[1]["name"] or "Pitch" in stages[1]["name"]
    # 3. Eliminating filler words & pacing
    assert "Filler" in stages[2]["name"] or "Pacing" in stages[2]["name"]
    # 4. Non-technical audiences & analogies
    assert "Non-Technical" in stages[3]["name"] or "Audiences" in stages[3]["name"]
    # 5. Behavioral storytelling with STAR
    assert "Behavioral" in stages[4]["name"] or "STAR" in stages[4]["name"]
    # 6. Mock interviews & peer feedback
    assert "Mock" in stages[5]["name"] or "Peer" in stages[5]["name"]
    # 7. Presentation & Q&A
    assert "Presentation" in stages[6]["name"] or "Q&A" in stages[6]["name"]

    # Verify that NONE of the communication exercises or deliverables require writing code
    coding_keywords = ["write python", "sql query", "import", "class ", "def ", "dockerfile", "npm install"]
    for st in stages:
        text = (st["task"] + " " + st["exercise"] + " " + st["deliverable"]).lower()
        for kw in coding_keywords:
            assert kw not in text, f"Communication stage {st['stage_num']} illegally contains coding instruction: '{kw}'"


def test_action_plan_synthesis_ten_sections():
    """Verify build_skill_action_plan returns all 10 required educational sections (B6)."""
    plan = build_skill_action_plan(
        skill_name="SQL",
        priority_tier="Mandatory",
        candidate_evidence={"verified_skills": ["Python", "Pandas", "Flask"]},
        daily_hours=2.0,
        timeline_days=14
    )
    # Section 1: Why it matters
    assert plan["why_it_matters"] and len(plan["why_it_matters"]) > 20
    # Section 2: What candidate knows
    assert "Python" in plan["what_candidate_knows"] or "Pandas" in plan["what_candidate_knows"]
    # Section 3: What is missing
    assert plan["what_is_missing"] and len(plan["what_is_missing"]) > 20
    # Section 4: What to learn next (fundamentals, intermediate, advanced)
    assert len(plan["what_to_learn_next"]["fundamentals"]) >= 3
    assert len(plan["what_to_learn_next"]["intermediate"]) >= 3
    assert len(plan["what_to_learn_next"]["advanced"]) >= 3
    # Section 5: Daily action plan
    assert len(plan["daily_action_plan"]) == 7
    # Section 6: Practical exercise
    assert plan["practical_exercise"] and len(plan["practical_exercise"]) > 10
    # Section 7: Deliverable
    assert plan["deliverable"] and len(plan["deliverable"]) > 10
    # Section 8: Verification method
    assert plan["verification_method"] and len(plan["verification_method"]) > 10
    # Section 9: Interview preparation
    assert len(plan["interview_prep"]) >= 2
    # Section 10: Resume improvement
    assert plan["resume_improvement"]["bullet_template"] and plan["resume_improvement"]["keywords"]


def test_realistic_study_schedules_pacing():
    """Verify schedule generator adapts accurately across 3, 7, 14, and 30 day timelines (B7)."""
    for days, expected_items in [(3, 3), (7, 7), (14, 7), (30, 7)]:
        plan = build_skill_action_plan("Docker", timeline_days=days, daily_hours=1.5)
        assert len(plan["daily_action_plan"]) == expected_items
        assert plan["timeline_days"] == days
        assert plan["total_estimated_hours"] == round(days * 1.5, 1)


def test_mentor_personalization_requirement_b8():
    """Verify Requirement B8: Respectful personalization referencing verified skills without assuming lack of capability."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_HARSHA)
    dossier = engine.build_mentor_dossier()

    # Preferred name correctly identified
    assert dossier["identity"]["preferred_name"] == "Harsha"

    # Prioritized gaps explanations conform to B8
    for gap in dossier["gaps"]["prioritized_gaps"]:
        exp = gap["explanation"]
        # Must address Harsha respectfully
        assert "Harsha, your resume" in exp or "your resume" in exp
        # Must reference verified skills
        assert "Python" in exp or "Pandas" in exp or "verified" in exp
        # Must NOT assume lack of ability
        assert "lacks ability" not in exp.lower()
        assert "you cannot" not in exp.lower()
        assert "incompetent" not in exp.lower()


def test_unsupported_skills_honest_fallback():
    """Verify unsupported skills receive an honest general engineering framework marked is_verified_specialized=False (B9)."""
    curr = get_curriculum_for_skill("Quantum Computing Assembly")
    assert curr["is_verified_specialized"] is False
    assert curr["curriculum_notice"] == "General Engineering Learning Framework (Skill-Specific Curriculum Under Review)"
    assert len(curr["stages"]) == 7
    assert "Quantum Computing Assembly" in curr["skill_name"]
