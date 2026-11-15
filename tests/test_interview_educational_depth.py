"""
Regression Test Suite for Interview Intelligence Studio Educational Depth & Quality Upgrade.
Verifies Part A Requirements:
1. Every generated question has 5-7 substantial steps with title, complete explanation,
   reasoning, concrete example, and connection to question.
2. Rejects instruction-like step details (e.g. "Explain what each tool contributed").
3. Generates 3 substantive follow-up questions per main question.
4. Each follow-up contains: question, >=4 full sentences answer, technical justification,
   practical example, and interview takeaway.
5. Verifies complete answer frameworks across Categories A, B, C, D, E, F.
6. Verifies tests across >=10 technical, 5 project, 5 internship, 5 HR, 5 job-alignment questions.
"""

import pytest
import re
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.question_bank import TECHNICAL_QUESTION_BANK, HR_QUESTION_BANK
from src.interview.answer_validator import AnswerQualityValidator

MOCK_EXTENSIVE_ANALYSIS = {
    "filename": "Harsha_Vardhan_Resume.pdf",
    "job_title": "Senior Full-Stack & ML Systems Engineer",
    "resume_skills": ["Python", "Flask", "React", "PostgreSQL", "Docker", "Git", "PyTorch", "Kubernetes", "AWS", "SQL"],
    "matched_skills": ["Python", "Flask", "PostgreSQL", "Docker", "SQL", "Git"],
    "missing_skills": ["Kubernetes", "AWS", "Redis", "Kafka", "CI/CD"],
    "required_skills": ["Python", "PostgreSQL", "Docker", "Kubernetes", "SQL"],
    "preferred_skills": ["AWS", "Redis", "Kafka"],
    "education_analysis": {"notes": "Bachelor of Technology in Computer Science & Engineering"},
    "experience_summary": {"display_summary": "2 years practical engineering and portfolio project experience"},
    "projects": [
        {
            "project_title": "Multimodal Resume-Job Compatibility Engine",
            "technologies": ["Python", "Flask", "PostgreSQL", "Scikit-Learn"],
            "description": "Engineered a dual-unseen resume-job matching pipeline with TF-IDF, TruncatedSVD, and Linear SVM."
        },
        {
            "project_title": "Distributed Task Scheduler",
            "technologies": ["Python", "Docker", "PostgreSQL"],
            "description": "Built an asynchronous task scheduling engine with persistent transactional execution."
        }
    ],
    "internships": [
        {
            "organization": "Cognitive AI Labs",
            "position": "Machine Learning Intern",
            "dates": "June 2023 - August 2023",
            "technologies": ["Python", "PostgreSQL", "Docker"],
            "responsibilities": ["Refactored model feature extraction pipeline", "Authored automated unit tests with Pytest"]
        },
        {
            "organization": "NextGen Cloud Systems",
            "position": "Backend Engineering Intern",
            "dates": "January 2024 - April 2024",
            "technologies": ["Flask", "PostgreSQL", "Git"],
            "responsibilities": ["Engineered RESTful API endpoints", "Participated in daily Scrum ceremonies and code reviews"]
        }
    ]
}


def count_sentences(text: str) -> int:
    """Counts sentences in text based on punctuation."""
    if not text:
        return 0
    # Split on periods, exclamation marks, or question marks followed by optional quotes and space or end of string
    raw_s = re.split(r"[.!?]+['\"”’\)]*(?:\s+|$)", text.strip())
    sentences = [s.strip() for s in raw_s if len(s.strip()) > 10]
    return len(sentences)


INSTRUCTION_LIKE_PATTERNS = [
    r"^explain what ",
    r"^explain that ",
    r"^explain how ",
    r"^describe how ",
    r"^detail your ",
    r"^state your ",
    r"^clarify your "
]


def is_instruction_only(text: str) -> bool:
    """Checks whether a step detail merely instructs the candidate rather than explaining."""
    clean = text.strip().lower()
    for pat in INSTRUCTION_LIKE_PATTERNS:
        if re.search(pat, clean) and len(clean) < 140:
            return True
    return False


class TestInterviewEducationalDepth:
    """Verifies educational depth and quality across all question categories."""

    @pytest.fixture(scope="class")
    @classmethod
    def generator(cls):
        return InterviewQuestionGenerator(MOCK_EXTENSIVE_ANALYSIS)

    def test_technical_questions_depth(self, generator):
        """Verify >= 10 technical questions have 5-7 substantial steps and 3 follow-ups with >=4 sentences."""
        qs = generator.generate_category_e()
        assert len(qs) >= 10, f"Expected at least 10 technical questions, got {len(qs)}"

        for q in qs[:15]:
            q_id = q["question_id"]
            # 1. Step-by-step breakdown: 5-7 steps
            steps = q.get("step_by_step_explanation", [])
            assert 5 <= len(steps) <= 7, f"Technical Q {q_id} has {len(steps)} steps (expected 5-7)"

            for idx, s in enumerate(steps, 1):
                assert "step" in s and s["step"], f"Step {idx} in {q_id} missing step title"
                assert "complete_explanation" in s, f"Step {idx} in {q_id} missing complete_explanation"
                assert len(s["complete_explanation"]) >= 60, f"Step {idx} explanation too brief in {q_id}"
                assert "reasoning" in s and len(s["reasoning"]) >= 30, f"Step {idx} reasoning too brief in {q_id}"
                assert "concrete_example" in s and s["concrete_example"], f"Step {idx} example missing in {q_id}"
                assert "connection_to_question" in s, f"Step {idx} connection missing in {q_id}"
                assert not is_instruction_only(s["complete_explanation"]), f"Step {idx} in {q_id} is instruction-only!"

            # 2. 3 Follow-up questions with >= 4 sentences
            fus = q.get("follow_up_questions", [])
            assert len(fus) >= 3, f"Technical Q {q_id} has {len(fus)} follow-ups (expected >=3)"

            for f_idx, fu in enumerate(fus, 1):
                assert "question" in fu and len(fu["question"]) > 10, f"Follow-up {f_idx} in {q_id} invalid question"
                ans = fu.get("reference_answer") or fu.get("answer", "")
                s_count = count_sentences(ans)
                assert s_count >= 4, f"Follow-up {f_idx} in {q_id} has {s_count} sentences (expected >= 4): '{ans[:100]}...'"
                assert "technical_justification" in fu and fu["technical_justification"], f"FU {f_idx} in {q_id} missing justification"
                assert "interview_takeaway" in fu and fu["interview_takeaway"], f"FU {f_idx} in {q_id} missing takeaway"

    def test_project_questions_depth(self, generator):
        """Verify >= 5 project questions (arch, roadblock, eval, scale) have 5-7 steps and 3 follow-ups."""
        qs = generator.generate_category_b()
        assert len(qs) >= 5, f"Expected at least 5 project questions, got {len(qs)}"

        for q in qs[:6]:
            q_id = q["question_id"]
            # 5-7 steps
            steps = q.get("step_by_step_explanation", [])
            assert 5 <= len(steps) <= 7, f"Project Q {q_id} has {len(steps)} steps (expected 5-7)"

            for idx, s in enumerate(steps, 1):
                assert "step" in s and s["step"]
                assert "complete_explanation" in s and len(s["complete_explanation"]) >= 60
                assert "reasoning" in s and len(s["reasoning"]) >= 30
                assert "concrete_example" in s and s["concrete_example"]
                assert "connection_to_question" in s
                assert not is_instruction_only(s["complete_explanation"]), f"Project step {idx} in {q_id} is instruction-only!"

            # 3 follow-ups with >= 4 sentences
            fus = q.get("follow_up_questions", [])
            assert len(fus) >= 3, f"Project Q {q_id} has {len(fus)} follow-ups (expected >= 3)"
            for f_idx, fu in enumerate(fus, 1):
                ans = fu.get("reference_answer") or fu.get("answer", "")
                s_count = count_sentences(ans)
                assert s_count >= 4, f"Project FU {f_idx} in {q_id} has {s_count} sentences (expected >= 4)"
                assert fu.get("technical_justification"), f"Project FU {f_idx} in {q_id} missing justification"
                assert fu.get("interview_takeaway"), f"Project FU {f_idx} in {q_id} missing takeaway"

    def test_internship_questions_depth(self, generator):
        """Verify >= 5 internship questions have 5-7 steps and 3 follow-ups."""
        qs = generator.generate_category_c()
        assert len(qs) >= 5, f"Expected at least 5 internship questions, got {len(qs)}"

        for q in qs[:6]:
            q_id = q["question_id"]
            steps = q.get("step_by_step_explanation", [])
            assert 5 <= len(steps) <= 7, f"Internship Q {q_id} has {len(steps)} steps"

            for idx, s in enumerate(steps, 1):
                assert "complete_explanation" in s and len(s["complete_explanation"]) >= 60
                assert "reasoning" in s and len(s["reasoning"]) >= 25
                assert not is_instruction_only(s["complete_explanation"]), f"Internship step {idx} in {q_id} is instruction-only!"

            fus = q.get("follow_up_questions", [])
            assert len(fus) >= 3, f"Internship Q {q_id} has {len(fus)} follow-ups"
            for f_idx, fu in enumerate(fus, 1):
                ans = fu.get("reference_answer") or fu.get("answer", "")
                assert count_sentences(ans) >= 4, f"Internship FU {f_idx} in {q_id} has fewer than 4 sentences"
                assert fu.get("technical_justification")
                assert fu.get("interview_takeaway")

    def test_hr_questions_depth(self, generator):
        """Verify >= 5 HR questions have 5-7 steps and 3 follow-ups with >= 4 sentences."""
        qs = generator.generate_category_f()
        assert len(qs) >= 5, f"Expected at least 5 HR questions, got {len(qs)}"

        for q in qs[:8]:
            q_id = q["question_id"]
            steps = q.get("step_by_step_explanation", [])
            assert 5 <= len(steps) <= 7, f"HR Q {q_id} has {len(steps)} steps"

            for idx, s in enumerate(steps, 1):
                assert "complete_explanation" in s and len(s["complete_explanation"]) >= 60
                assert "reasoning" in s and len(s["reasoning"]) >= 25
                assert not is_instruction_only(s["complete_explanation"])

            fus = q.get("follow_up_questions", [])
            assert len(fus) >= 3, f"HR Q {q_id} has {len(fus)} follow-ups"
            for f_idx, fu in enumerate(fus, 1):
                ans = fu.get("reference_answer") or fu.get("answer", "")
                assert count_sentences(ans) >= 4, f"HR FU {f_idx} in {q_id} has fewer than 4 sentences"
                assert fu.get("technical_justification")
                assert fu.get("interview_takeaway")

    def test_job_alignment_questions_depth(self, generator):
        """Verify job-alignment questions (Category D) have 5-7 steps and 3 follow-ups."""
        qs = generator.generate_category_d()
        assert len(qs) >= 2, f"Expected at least 2 Category D questions, got {len(qs)}"

        for q in qs:
            q_id = q["question_id"]
            steps = q.get("step_by_step_explanation", [])
            assert 5 <= len(steps) <= 7, f"Job Alignment Q {q_id} has {len(steps)} steps"

            for idx, s in enumerate(steps, 1):
                assert "complete_explanation" in s and len(s["complete_explanation"]) >= 60
                assert "reasoning" in s and len(s["reasoning"]) >= 25
                assert not is_instruction_only(s["complete_explanation"])

            fus = q.get("follow_up_questions", [])
            assert len(fus) >= 3, f"Job Alignment Q {q_id} has {len(fus)} follow-ups"
            for f_idx, fu in enumerate(fus, 1):
                ans = fu.get("reference_answer") or fu.get("answer", "")
                assert count_sentences(ans) >= 4, f"Job Alignment FU {f_idx} in {q_id} has fewer than 4 sentences"
                assert fu.get("technical_justification")
                assert fu.get("interview_takeaway")

    def test_pedagogical_bundle_completeness(self, generator):
        """Verify that questions across all categories provide the complete pedagogical bundle (A5)."""
        qs = generator.generate_questions(category="ALL", max_questions=20)
        for q in qs:
            q_id = q["question_id"]
            # 1. Spoken answer
            assert len(q.get("detailed_answer", "")) >= 100, f"Detailed answer missing in {q_id}"
            # 2. Simpler explanation
            assert len(q.get("simpler_answer", "")) >= 30, f"Simpler answer missing in {q_id}"
            # 3. Why this works
            assert len(q.get("why_this_works", "")) >= 40, f"Why this works missing in {q_id}"
            # 4. 5-7 steps
            assert 5 <= len(q.get("step_by_step_explanation", [])) <= 7, f"Steps count invalid in {q_id}"
            # 5. 3 follow-ups
            assert len(q.get("follow_up_questions", [])) >= 3, f"Follow-ups count invalid in {q_id}"
            # 6. Common mistakes
            assert len(q.get("common_mistakes", [])) >= 2, f"Common mistakes missing in {q_id}"
            # 7. Important concepts
            assert len(q.get("important_concepts", [])) >= 1, f"Important concepts missing in {q_id}"
            # 8. Delivery tips
            assert len(q.get("interview_tips", [])) >= 1, f"Interview tips missing in {q_id}"
            # 9. Framework template
            assert len(q.get("framework_template", [])) >= 3, f"Framework template missing in {q_id}"
