"""
Comprehensive Phase 9 Test Suite for Personalized Career Mentor and Roadmap System.
Verifies all 20 requirements:
1. Correct candidate name extraction.
2. Missing name fallback.
3. Editable display name.
4. Correct skill-gap integration.
5. No invented competencies.
6. Required/preferred separation.
7. Correct resource mapping.
8. Skill-specific learning paths.
9. Practical project recommendations.
10. Realistic study-plan generation.
11. Preparation timeline selection.
12. Progress tracking.
13. Interview Studio integration.
14. Deterministic message generation.
15. Session isolation.
16. No guaranteed employment claims.
17. Empty resume handling.
18. Empty job description handling.
19. Flask route integration.
20. Real CV verification (4 projects, 2 internships).
"""

import json
import pytest
from app import app
from src.mentor import (
    CareerMentorEngine,
    CandidateProgressTracker,
    extract_candidate_name,
    format_mentor_identity,
    get_learning_resources_for_skill,
    recommend_project_for_skill,
    generate_skill_roadmap,
    generate_realistic_study_plan,
    build_welcome_greeting,
    format_gap_explanation,
    build_progress_encouragement
)
from src.analysis.matching_engine import analyze_resume_and_job
from tests.test_experience_and_projects import SAMPLE_TWO_PAGE_RESUME


SAMPLE_ANALYSIS_DATA = {
    "raw_text": "Harsha Vardhan\nEmail: harsha@example.com\nB.Tech CSE\nSkills: Python, Scikit-learn, SQL, Flask",
    "filename": "harsha_resume.pdf",
    "job_title": "Senior Machine Learning & Cloud Engineer",
    "projects": [
        {
            "title": "Multimodal Resume Matching System",
            "technologies": ["Python", "PyTorch", "Flask", "Scikit-Learn"],
            "description": "Engineered multimodal resume-job compatibility pipeline."
        }
    ],
    "internships": [
        {
            "organization": "Cognitive AI Labs",
            "position": "Machine Learning Intern",
            "dates": "June 2023 - August 2023",
            "technologies": ["Python", "OpenCV"],
            "responsibilities": ["Implemented computer vision model pipelines and benchmarked inference."]
        }
    ],
    "resume_skills": ["Python", "Flask", "Scikit-Learn", "SQL"],
    "matched_skills": ["Python", "Scikit-Learn", "SQL"],
    "missing_required_skills": ["Docker", "Kubernetes"],
    "missing_preferred_skills": ["AWS", "CI/CD"],
    "partially_evidenced_required_skills": ["Microservices"],
    "partially_evidenced_skills": ["Microservices"],
    "education_analysis": {"notes": "B.Tech in Computer Science and Engineering"},
    "experience_summary": {"display_summary": "1 Internship, 1 Key Project verified"}
}


# -------------------------------------------------------------------------
# Test 1-3: Candidate Name Extraction & Customization
# -------------------------------------------------------------------------

def test_01_correct_candidate_name_extraction():
    """1. Test that candidate's preferred name is correctly extracted from header."""
    res1 = extract_candidate_name("Harsha Vardhan\nEmail: harsha@example.com\nSoftware Engineer")
    assert res1["preferred_name"] == "Harsha"
    assert res1["mentor_title"] == "Harsha's Career Mentor"
    assert res1["is_confident"] is True

    res2 = extract_candidate_name("Jane Doe - Senior Machine Learning Engineer\nEmail: jane@test.com")
    assert res2["preferred_name"] == "Jane"
    assert res2["mentor_title"] == "Jane's Career Mentor"


def test_02_missing_name_fallback():
    """2. Test graceful fallback when no clear personal name is found."""
    # When resume text starts with email, contact, or title keywords
    res = extract_candidate_name("contact@example.com\n+1-555-0199\nCurriculum Vitae\nExperience:")
    assert res["preferred_name"] == "Candidate"
    assert res["mentor_title"] == "Your Career Mentor"
    assert res["is_confident"] is False


def test_03_editable_display_name():
    """3. Test user override of display name."""
    extracted = {"preferred_name": "Candidate", "mentor_title": "Your Career Mentor", "is_confident": False}
    updated = format_mentor_identity("Alexander", extracted)
    assert updated["preferred_name"] == "Alexander"
    assert updated["mentor_title"] == "Alexander's Career Mentor"
    assert updated["is_user_override"] is True


# -------------------------------------------------------------------------
# Test 4-6: Canonical Skill Gap Integration & Separation
# -------------------------------------------------------------------------

def test_04_correct_skill_gap_integration():
    """4. Test that mentor integrates canonical skill gaps from analysis."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_DATA)
    dossier = engine.build_mentor_dossier()
    gaps = dossier["gaps"]
    
    assert "Docker" in gaps["missing_required"]
    assert "Kubernetes" in gaps["missing_required"]
    assert "AWS" in gaps["missing_preferred"]
    assert "CI/CD" in gaps["missing_preferred"]


def test_05_no_invented_competencies():
    """5. Test that candidate's verified skills only reflect extracted resume skills."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_DATA)
    strengths = engine.strengths
    for s in strengths["verified_skills"]:
        assert s in SAMPLE_ANALYSIS_DATA["resume_skills"]
    assert "Ruby" not in strengths["verified_skills"]
    assert "Rust" not in strengths["verified_skills"]


def test_06_required_preferred_separation():
    """6. Test clear separation of mandatory vs preferred gaps."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_DATA)
    prioritized = engine.gaps["prioritized_gaps"]
    
    tier_map = {p["skill_name"]: p["priority_tier"] for p in prioritized}
    assert tier_map["Docker"] == "Mandatory"
    assert tier_map["Kubernetes"] == "Mandatory"
    assert tier_map["AWS"] == "Preferred"
    assert tier_map["CI/CD"] == "Preferred"


# -------------------------------------------------------------------------
# Test 7-9: Learning Resources & Project Recommendations
# -------------------------------------------------------------------------

def test_07_correct_resource_mapping():
    """7. Test verified official educational resource mapping."""
    docker_res = get_learning_resources_for_skill("Docker")
    assert len(docker_res) > 0
    assert any("docs.docker.com" in r["url"] for r in docker_res)

    k8s_res = get_learning_resources_for_skill("Kubernetes")
    assert any("kubernetes.io" in r["url"] for r in k8s_res)

    # Empty resource handling for non-existent niche tools
    unknown_res = get_learning_resources_for_skill("CustomNonExistentFramework999")
    assert unknown_res == []


def test_08_skill_specific_learning_paths():
    """8. Test 7-stage learning roadmap generation."""
    rm = generate_skill_roadmap("Docker", priority_tier="Mandatory")
    assert rm["skill_name"] == "Docker"
    assert len(rm["stages"]) == 7
    stage_names = [st["name"] for st in rm["stages"]]
    assert stage_names == [
        "Fundamentals", "Essential Concepts", "Guided Exercises",
        "Practical Mini-Project", "Test Understanding",
        "Interview Preparation", "Resume Documentation"
    ]


def test_09_practical_project_recommendations():
    """9. Test project recommendation grounding."""
    proj = recommend_project_for_skill("Docker")
    assert proj is not None
    assert "Containerization" in proj["title"] or "Docker" in proj["description"]
    assert len(proj["deliverables"]) >= 2
    assert "Docker" in proj["demonstrable_skills"]


# -------------------------------------------------------------------------
# Test 10-12: Realistic Study Plans & Progress Tracking
# -------------------------------------------------------------------------

def test_10_realistic_study_plan_generation():
    """10. Test schedule generation and total hours calculation."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_DATA)
    plan = generate_realistic_study_plan(engine.roadmaps, timeline_days=14, daily_hours=2.0)
    assert plan["timeline_days"] == 14
    assert plan["daily_hours"] == 2.0
    assert plan["total_available_hours"] == 28.0
    assert len(plan["schedule_items"]) > 0


def test_11_preparation_timeline_selection():
    """11. Test behavior across different timelines (3, 7, 30 days)."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_DATA)
    plan_3d = generate_realistic_study_plan(engine.roadmaps, timeline_days=3, daily_hours=1.0)
    assert plan_3d["total_available_hours"] == 3.0
    # Constrained schedule should report deferred skills honestly
    assert plan_3d["is_time_constrained"] is True

    plan_30d = generate_realistic_study_plan(engine.roadmaps, timeline_days=30, daily_hours=3.0)
    assert plan_30d["total_available_hours"] == 90.0
    assert len(plan_30d["covered_skills"]) > len(plan_3d["covered_skills"])


def test_12_progress_tracking():
    """12. Test independent task state updates."""
    tracker = CandidateProgressTracker()
    assert tracker.get_task_status("docker_stage_1") == "Not started"

    tracker.set_task_status("docker_stage_1", "Learning")
    assert tracker.get_task_status("docker_stage_1") == "Learning"

    tracker.set_task_status("docker_stage_1", "Completed")
    assert tracker.get_task_status("docker_stage_1") == "Completed"

    summary = tracker.calculate_progress_summary(["docker_stage_1", "docker_stage_2"])
    assert summary["completed_tasks"] == 1
    assert summary["completion_percentage"] == 50.0


# -------------------------------------------------------------------------
# Test 13-16: Interview Studio Integration & Disclaimers
# -------------------------------------------------------------------------

def test_13_interview_studio_integration():
    """13. Test that roadmaps include Interview Studio stage and practice questions."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_DATA)
    dossier = engine.build_mentor_dossier()
    for rm in dossier["roadmaps"]:
        prep_stage = next(st for st in rm["stages"] if st["stage_num"] == 6)
        assert "Interview Preparation" in prep_stage["name"]
        assert "Interview Studio" in prep_stage["task"]


def test_14_deterministic_message_generation():
    """14. Test respectful, deterministic wording."""
    greeting = build_welcome_greeting("Harsha", "ML Engineer", 4, 2)
    assert "Hey Harsha!" in greeting
    assert "ML Engineer" in greeting

    explanation = format_gap_explanation("Docker", "Mandatory", ["Python", "Flask"])
    assert "Your resume does not clearly demonstrate Docker" in explanation
    assert "You do not know" not in explanation
    # Mentions bridge skill
    assert "Flask" in explanation or "Python" in explanation


def test_15_session_isolation():
    """15. Test progress tracker isolation between sessions."""
    t1 = CandidateProgressTracker()
    t2 = CandidateProgressTracker()

    t1.set_task_status("task_a", "Completed")
    assert t1.get_task_status("task_a") == "Completed"
    assert t2.get_task_status("task_a") == "Not started"


def test_16_no_guaranteed_employment_claims():
    """16. Verify that disclaimers strictly deny guaranteed employment or selection."""
    engine = CareerMentorEngine(SAMPLE_ANALYSIS_DATA)
    dossier = engine.build_mentor_dossier()
    disclaimer = dossier["disclaimer"].lower()
    
    assert "does not guarantee employment" in disclaimer
    assert "guaranteed to succeed" not in disclaimer
    assert "you will definitely get selected" not in disclaimer


# -------------------------------------------------------------------------
# Test 17-20: Edge Cases, Flask Routes & Real Resume Verification
# -------------------------------------------------------------------------

def test_17_empty_resume_handling():
    """17. Test graceful handling when resume text is empty."""
    engine = CareerMentorEngine({"raw_text": ""})
    dossier = engine.build_mentor_dossier()
    assert dossier["identity"]["preferred_name"] == "Candidate"
    assert dossier["identity"]["mentor_title"] == "Your Career Mentor"
    assert dossier["strengths"]["total_skills"] == 0


def test_18_empty_job_description_handling():
    """18. Test graceful handling when job description is missing."""
    engine = CareerMentorEngine({"raw_text": "Alex\nSkills: Python", "job_title": None})
    dossier = engine.build_mentor_dossier()
    assert dossier["target_role"] == "Target Technical Role"


def test_19_flask_routes_integration():
    """19. Test Flask endpoints for Career Mentor."""
    client = app.test_client()

    # 1. Main mentor dashboard
    resp = client.get("/career-mentor")
    assert resp.status_code == 200
    assert b"Career Mentor" in resp.data

    # 2. Update display name
    resp_name = client.post("/api/mentor/update-name",
                            data=json.dumps({"preferred_name": "Harsha"}),
                            content_type="application/json")
    assert resp_name.status_code == 200
    assert resp_name.get_json()["preferred_name"] == "Harsha"

    # 3. Update task progress
    resp_prog = client.post("/api/mentor/progress",
                            data=json.dumps({"task_key": "docker_stage_1", "status": "Completed"}),
                            content_type="application/json")
    assert resp_prog.status_code == 200
    assert resp_prog.get_json()["status"] == "success"

    # 4. Reset progress
    resp_rst = client.post("/api/mentor/reset-progress")
    assert resp_rst.status_code == 200


def test_20_real_cv_verification():
    """20. Real CV verification: 4 projects, 2 internships from test fixture."""
    job_desc = """
    Senior Cloud & DevOps Engineer
    Requirements:
    - Python, Docker, Kubernetes, AWS, SQL
    - 3+ years experience with container orchestration and cloud CI/CD
    """
    analysis = analyze_resume_and_job(SAMPLE_TWO_PAGE_RESUME, job_desc, "final_cv_2026.txt")
    assert analysis["status"] == "success"
    assert len(analysis["projects"]) == 4, f"Expected 4 projects, got {len(analysis['projects'])}"
    assert len(analysis["internships"]) == 2, f"Expected 2 internships, got {len(analysis['internships'])}"

    engine = CareerMentorEngine(analysis)
    dossier = engine.build_mentor_dossier()

    # Verify extracted candidate name or fallback
    assert dossier["identity"]["preferred_name"] in ["Candidate", "Harsha"]
    # Verify strengths extracted accurately
    assert dossier["strengths"]["projects_count"] == 4
    assert dossier["strengths"]["internships_count"] == 2
    # Verify identified skill gaps (Docker/Kubernetes/AWS/SQL)
    gap_names = [g["skill_name"].lower() for g in dossier["gaps"]["prioritized_gaps"]]
    assert any("kubernetes" in g or "docker" in g or "amazon web services" in g or "aws" in g or "sql" in g for g in gap_names)
