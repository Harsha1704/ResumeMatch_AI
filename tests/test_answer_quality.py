"""
Answer Quality and Interview Studio Upgrade Tests.
Validates:
- 100% adherence to AnswerQualityValidator standards.
- Zero generic boilerplate ("robust ecosystem and excellent performance").
- Complete pedagogical fields across all categories (A, B, C, D, E, F).
- Why This Answer Works, Simpler Answer, Follow-up Questions, Common Mistakes, Step-by-Step.
- Strict zero-fabrication defense for personal projects and internships.
- Syntax validity of all executable Python snippets.
"""

import pytest
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.answer_validator import AnswerQualityValidator
from src.interview.technology_roles import get_technology_profile, TECHNOLOGY_ROLES
from src.interview.question_bank import TECHNICAL_QUESTION_BANK, HR_QUESTION_BANK

MOCK_ANALYSIS = {
    "filename": "Harsha_Resume.pdf",
    "job_title": "Full-Stack Software Engineer",
    "resume_skills": ["Python", "Flask", "React", "PostgreSQL", "Docker", "Git"],
    "matched_skills": ["Python", "Flask", "PostgreSQL", "Git"],
    "missing_skills": ["Kubernetes", "AWS", "Redis"],
    "required_skills": ["Python", "PostgreSQL", "Docker", "AWS"],
    "preferred_skills": ["Kubernetes", "Redis"],
    "education_analysis": {"notes": "Bachelor of Technology in Computer Science & Engineering"},
    "experience_summary": {"display_summary": "1 year practical software engineering and project experience"},
    "projects": [
        {
            "project_title": "Distributed Task Processing Service",
            "technologies": ["Python", "Flask", "PostgreSQL", "Docker"],
            "description": "Engineered a distributed background task engine with persistent job tracking and transactional safety."
        }
    ],
    "internships": [
        {
            "organization": "CloudScale Solutions",
            "position": "Software Engineering Intern",
            "dates": "May 2024 - July 2024",
            "technologies": ["Python", "Flask", "PostgreSQL"],
            "responsibilities": ["Refactored REST endpoints for user authentication", "Implemented automated integration test suites"]
        }
    ]
}


def test_technology_profiles_coverage():
    """Verify that concrete architectural profiles exist for key frameworks."""
    for tech in ["Python", "Flask", "FastAPI", "Docker", "PostgreSQL", "React", "Redis"]:
        profile = get_technology_profile(tech)
        assert profile is not None
        assert "role" in profile and len(profile["role"]) > 20
        assert "trade_off" in profile and len(profile["trade_off"]) > 20
        assert "testing" in profile and len(profile["testing"]) > 20


def test_all_categories_pass_quality_validator():
    """Verify all questions generated across Categories A-F pass AnswerQualityValidator."""
    gen = InterviewQuestionGenerator(MOCK_ANALYSIS)
    for cat in ["A", "B", "C", "D", "E", "F"]:
        qs = gen.generate_questions(category=cat, max_questions=50)
        assert len(qs) > 0, f"Category {cat} produced 0 questions"
        for q in qs:
            val = AnswerQualityValidator.validate_answer(q)
            assert val["is_valid"], f"Question {q['question_id']} failed validation: {val['issues']}"
            assert val["quality_score"] >= 90.0, f"Quality score too low for {q['question_id']}: {val['quality_score']}"


def test_extended_pedagogical_fields():
    """Verify that all questions supply the complete suite of pedagogical learning fields."""
    gen = InterviewQuestionGenerator(MOCK_ANALYSIS)
    qs = gen.generate_questions(category="ALL", max_questions=30)
    for q in qs:
        # 1. Spoken detailed answer
        assert len(q["detailed_answer"]) >= 80, f"Detailed answer too short in {q['question_id']}"
        # 2. Simpler answer
        assert len(q.get("simpler_answer", "")) >= 30, f"Simpler answer missing in {q['question_id']}"
        # 3. Why this works
        assert len(q.get("why_this_works", "")) >= 40, f"Why this works missing in {q['question_id']}"
        # 4. Step-by-step explanation
        steps = q.get("step_by_step_explanation", [])
        assert len(steps) >= 3, f"Fewer than 3 pedagogical steps in {q['question_id']}"
        for s in steps:
            assert "step" in s and "detail" in s
        # 5. Follow-up questions
        follow_ups = q.get("follow_up_questions", [])
        assert len(follow_ups) >= 2, f"Fewer than 2 follow-ups in {q['question_id']}"
        for fu in follow_ups:
            assert "question" in fu and len(fu["question"]) > 10
            assert "reference_answer" in fu and len(fu["reference_answer"]) > 20
        # 6. Common mistakes
        mistakes = q.get("common_mistakes", [])
        assert len(mistakes) >= 2, f"Fewer than 2 common mistakes in {q['question_id']}"


def test_zero_personal_metric_fabrication():
    """Verify that project and internship answers contain separate notes rather than raw inline placeholders."""
    gen = InterviewQuestionGenerator(MOCK_ANALYSIS)
    proj_qs = gen.generate_category_b()
    for q in proj_qs:
        ans = q["detailed_answer"]
        assert "[Personal Detail to Customize:" not in ans and "[Mention Primary Project" not in ans
        assert len(q["missing_personal_details"]) >= 1

    intern_qs = gen.generate_category_c()
    for q in intern_qs:
        ans = q["detailed_answer"]
        assert "[Personal Detail to Customize:" not in ans and "[Mention Primary Project" not in ans
        assert len(q["missing_personal_details"]) >= 1


def test_technical_code_snippets_compile():
    """Verify all Python code snippets in the technical bank are valid syntax."""
    for item in TECHNICAL_QUESTION_BANK:
        code = item.get("code_snippet")
        if code and item["topic"] == "Python":
            # Attempt compile
            try:
                compile(code, f"<test_{item['id']}>", "exec")
            except SyntaxError as e:
                pytest.fail(f"Invalid Python syntax in {item['id']}: {e}")
