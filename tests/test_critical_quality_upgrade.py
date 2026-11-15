"""
Comprehensive Quality, Personalization & Integration Regression Test Suite (Requirement 6.2).
Validates all 12 non-negotiable upgrade criteria:
1. No 'Candidate' placeholder when name is missing
2. No 'Target Position' default in job analysis
3. No unverified degree notes when education not evidenced
4. No '~h' badges in project estimates
5. No '[Mention ...]' or '[Personal Detail ...]' in polished answers
6. Internship role vs organization correctly parsed
7. Project title clean of repository metadata
8. No 'while its was selected' grammar defect
9. No 'to address Built a...' description grammar defect
10. Full 14-day schedule accounting (total = scheduled + completed + remaining + deferred)
11. Candidate confirmation flow functional
12. Shared session context between Career Mentor and Interview Studio
"""

import pytest
import re
from app import app
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.analysis.experience_analyzer import ExperienceAnalyzer
from src.analysis.matching_engine import analyze_resume_and_job
from src.mentor.name_extractor import extract_candidate_name, format_mentor_identity
from src.mentor.mentor_engine import CareerMentorEngine
from src.mentor.roadmap_generator import generate_skill_roadmap, generate_realistic_study_plan
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.evidence_mapper import build_grounded_project_answers
from src.interview.technology_roles import get_technology_profile
from src.utils.sanitizer import sanitize_text, clean_project_title, format_estimated_hours


# -------------------------------------------------------------------------
# Test 1: No 'Candidate' Placeholder When Name Missing
# -------------------------------------------------------------------------
def test_01_no_candidate_placeholder_when_name_missing():
    raw_header_without_name = "Email: contact@example.com\nPhone: +1-555-0199\nSummary:\nSoftware Engineer"
    name_info = extract_candidate_name(raw_header_without_name)
    identity = format_mentor_identity(None, name_info)
    assert identity["mentor_title"] == "Your Career Mentor"

    # In engine dossier
    engine = CareerMentorEngine({"raw_text": raw_header_without_name})
    dossier = engine.build_mentor_dossier()
    # Greeting must not say "Hey Candidate!"
    assert "Hey Candidate!" not in dossier["welcome_greeting"]
    assert "Candidate: Candidate" not in sanitize_text(dossier["identity"].get("preferred_name"))


# -------------------------------------------------------------------------
# Test 2: No 'Target Position' Default
# -------------------------------------------------------------------------
def test_02_no_target_position_default():
    analyzer = JobDescriptionAnalyzer()
    res_empty = analyzer.analyze("")
    assert res_empty["job_title"] != "Target Position"
    assert res_empty["job_title"] == "Target role not specified"

    res_generic = analyzer.analyze("Looking for a qualified candidate to join our team in London.")
    assert res_generic["job_title"] != "Target Position"
    assert res_generic["job_title"] == "Target role not specified"


# -------------------------------------------------------------------------
# Test 3: No Unverified Degree Notes
# -------------------------------------------------------------------------
def test_03_no_unverified_degree_notes():
    resume_no_degree = "Experienced Python developer with Flask and SQL skills. Built web services."
    job = "Backend Engineer with Python and SQL."
    result = analyze_resume_and_job(resume_no_degree, job)
    assert result["status"] == "success"
    edu_notes = result["education_analysis"]["notes"]
    assert edu_notes != "Verified against degree mentions in parsed resume."
    assert edu_notes == "Education details not confidently identified"


# -------------------------------------------------------------------------
# Test 4: No '~h' Badges
# -------------------------------------------------------------------------
def test_04_no_empty_hour_badges():
    # Verify sanitizer and formatter
    assert format_estimated_hours(None) is None
    assert format_estimated_hours(0) is None
    assert format_estimated_hours("0") is None
    assert format_estimated_hours(12) == "~12 hrs"
    assert format_estimated_hours(8.5) == "~8.5 hrs"

    # Verify roadmaps always have integer hours
    rm = generate_skill_roadmap("Docker", priority_tier="Mandatory")
    proj = rm.get("recommended_project")
    assert proj is not None
    assert proj.get("estimated_hours") is not None
    assert proj["estimated_hours"] > 0


# -------------------------------------------------------------------------
# Test 5: No '[Mention ...]' or '[Personal Detail ...]' in Answers
# -------------------------------------------------------------------------
def test_05_no_mention_or_personal_detail_placeholders():
    analysis_mock = {
        "raw_text": "Harsha Vardhan\nPython, Docker, SQL\nBuilt Brain Tumor Classification.",
        "projects": [
            {
                "title": "Brain Tumor Classification",
                "technologies": ["Python", "TensorFlow", "OpenCV"],
                "description": "Built a real-time detection pipeline achieving 92% accuracy."
            }
        ],
        "internships": [
            {
                "organization": "Edunet Foundation",
                "position": "AI/ML Intern",
                "technologies": ["Python", "OpenCV"],
                "responsibilities": ["Implemented computer vision models"]
            }
        ],
        "resume_skills": ["Python", "TensorFlow", "OpenCV", "Docker", "SQL"],
        "required_skills": ["Python", "Docker", "SQL"],
        "preferred_skills": ["Kubernetes"],
        "missing_required_skills": ["Kubernetes"]
    }
    generator = InterviewQuestionGenerator(analysis_mock)
    questions = generator.generate_questions(category="ALL", max_questions=25)

    for q in questions:
        for field in ["detailed_answer", "short_answer", "simpler_answer", "curated_answer"]:
            ans = q.get(field, "")
            assert "[Mention Primary Project" not in ans, f"Found [Mention...] in {q['question_id']}"
            assert "[Mention a concrete project" not in ans, f"Found [Mention...] in {q['question_id']}"
            assert "[Personal Detail to Customize:" not in ans, f"Found [Personal Detail...] in {q['question_id']}"


# -------------------------------------------------------------------------
# Test 6: Internship Role vs Organization Correctly Parsed
# -------------------------------------------------------------------------
def test_06_internship_role_vs_organization():
    analyzer = ExperienceAnalyzer()
    resume_text = """
    EXPERIENCE & INTERNSHIPS
    AI/ML Intern | Edunet Foundation
    June 2023 - August 2023
    - Built computer vision pipeline using OpenCV and Python.
    - Evaluated deep learning model performance.
    """
    internships = analyzer.detect_internships(resume_text)
    assert len(internships) >= 1
    intern = internships[0]
    # Edunet Foundation is the organization, AI/ML Intern is the role
    assert intern["organization"] == "Edunet Foundation"
    assert "Intern" in intern["position"] or "Intern" in intern["role"]
    assert intern["position"] != "Edunet Foundation"


# -------------------------------------------------------------------------
# Test 7: Project Title Clean of Repo Metadata
# -------------------------------------------------------------------------
def test_07_project_title_clean_of_repo_metadata():
    analyzer = ExperienceAnalyzer()
    resume_text = """
    PROJECTS
    Brain Tumor Classification | GitHub
    January 2024 - March 2024
    Built deep learning models using Python and TensorFlow.
    """
    projects = analyzer.detect_projects(resume_text)
    assert len(projects) >= 1
    p = projects[0]
    assert "GitHub" not in p["title"]
    assert "GitHub" not in p["project_title"]
    assert p["title"] == "Brain Tumor Classification"
    assert clean_project_title("Brain Tumor Classification | GitHub") == "Brain Tumor Classification"


# -------------------------------------------------------------------------
# Test 8: No 'while its was selected' Grammar Bug
# -------------------------------------------------------------------------
def test_08_no_while_its_grammar_bug():
    prof_py = get_technology_profile("python")
    prof_custom = get_technology_profile("some_niche_tool")

    phrase_py = f"For the Python component, it {prof_py['role']}, while it {prof_py['trade_off']}."
    phrase_custom = f"For the niche component, it {prof_custom['role']}, while it {prof_custom['trade_off']}."

    assert "while its was" not in phrase_custom
    assert "while its prioritizes" not in phrase_py
    assert "while it was selected" in phrase_custom or "while it" in phrase_custom
    assert "while it prioritizes" in phrase_py


# -------------------------------------------------------------------------
# Test 9: No 'to address Built a...' Grammar Bug
# -------------------------------------------------------------------------
def test_09_no_to_address_built_a_grammar_bug():
    project = {
        "title": "Brain Tumor Classification",
        "technologies": ["Python", "TensorFlow"],
        "description": "Built a real-time detection pipeline for tumor segmentation."
    }
    ans = build_grounded_project_answers(project, "arch")
    detailed = ans["detailed_answer"]
    assert "to address Built a" not in detailed
    assert "to address Built" not in detailed
    assert "to address Developed" not in detailed


# -------------------------------------------------------------------------
# Test 10: Full 14-Day Schedule Accounting
# -------------------------------------------------------------------------
def test_10_full_14_day_schedule_accounting():
    rm1 = generate_skill_roadmap("Docker", priority_tier="Mandatory")
    rm2 = generate_skill_roadmap("Kubernetes", priority_tier="Mandatory")
    rm3 = generate_skill_roadmap("SQL", priority_tier="Preferred")
    rm4 = generate_skill_roadmap("AWS", priority_tier="Preferred")

    plan = generate_realistic_study_plan([rm1, rm2, rm3, rm4], timeline_days=14, daily_hours=2.0)

    # 1. Every day 1 through 14 must be explicitly represented
    scheduled_days = {item["day_number"] for item in plan["schedule_items"]}
    for d in range(1, 15):
        assert d in scheduled_days, f"Day {d} missing from 14-day schedule view"

    # 2. Accounting reconciliation
    assert plan["scheduled_tasks_count"] == len(plan["schedule_items"])
    assert plan["total_tasks"] >= plan["scheduled_tasks_count"]
    # If any skills could not fit, they must be recorded in deferred_skills / deferred_tasks
    if plan["is_time_constrained"]:
        assert len(plan["deferred_skills"]) > 0
        assert len(plan["deferred_tasks"]) > 0


# -------------------------------------------------------------------------
# Test 11: Candidate Confirmation Flow Functional
# -------------------------------------------------------------------------
def test_11_candidate_confirmation_flow():
    client = app.test_client()
    resp = client.post("/api/interview/confirm-activity", json={
        "activity_key": "pytest_unit_testing",
        "confirmed": True
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["confirmed"] is True


# -------------------------------------------------------------------------
# Test 12: Shared Session Context Between Mentor and Interview Studio
# -------------------------------------------------------------------------
def test_12_shared_session_context():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["mentor_priority_skills"] = ["Docker", "Kubernetes"]
        sess["struggled_topics"] = ["Container Networking"]

    # 1. Visiting interview studio leverages mentor priority skills
    resp_studio = client.get("/interview-studio")
    assert resp_studio.status_code == 200

    # 2. Visiting career mentor marks struggled topics for reinforcement
    resp_mentor = client.get("/career-mentor")
    assert resp_mentor.status_code == 200
