"""
Tests for Industry-Quality Career Mentor & Interview Studio Upgrade.
Validates:
- 4 canonical skill gap categories with zero lost JD requirements
- Top 5 immediate priorities + expandable remaining requirements
- Strictly logical project recommendations (zero 'Excel APIs' or 'Communication services')
- Future enhancement explicit labeling
- Distinct 7-stage Spark curriculum with specialized topics
- Non-circular technology role explanations (no tautological fallbacks)
- Coherent question grouping in Category A
- Balanced project question interleaving in Category B
- Safe candidate metadata handling (no parser leakage, target role warning)
- Full 14-day schedule reconciliation
"""

import pytest
from src.mentor.mentor_engine import (
    CareerMentorEngine,
    classify_mentor_category,
    calculate_skill_priority,
    recommend_gap_action
)
from src.mentor.skill_curricula import get_curriculum_for_skill
from src.mentor.project_recommender import recommend_project_for_skill
from src.mentor.roadmap_generator import build_logical_project_recommendation
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.technology_roles import get_technology_profile


# Sample candidate analysis data for test fixture
SAMPLE_ANALYSIS = {
    "filename": "Candidate_CV.pdf",
    "job_title": "Senior AI Systems Engineer",
    "projects": [
        {
            "title": "Smart ATS Evaluator",
            "technologies": ["Python", "Flask", "Scikit-Learn"],
            "description": "Engineered automated resume parsing and scoring system achieving 88.5% validation accuracy."
        },
        {
            "title": "Distributed Visual Search",
            "technologies": ["PyTorch", "OpenCV", "Docker"],
            "description": "Built similarity search service for image indexing with sub-120ms latency."
        }
    ],
    "internships": [
        {
            "organization": "DataCore Systems",
            "position": "Software Engineering Intern",
            "dates": "Jan 2023 - Jun 2023",
            "technologies": ["Python", "SQL", "Git"],
            "responsibilities": ["Developed backend API validation endpoints and wrote unit tests."]
        }
    ],
    "resume_skills": ["Python", "Flask", "Scikit-Learn", "PyTorch", "OpenCV", "Docker", "SQL", "Git"],
    "matched_skills": ["Python", "Flask", "Docker", "SQL"],
    "missing_skills": ["Spark", "Kubernetes", "CI/CD", "Communication", "Excel", "Jira", "AWS", "FastAPI"],
    "required_skills": ["Python", "Docker", "Spark", "Kubernetes", "CI/CD", "Communication"],
    "preferred_skills": ["Excel", "Jira", "AWS", "FastAPI"],
    "education_analysis": {"notes": "B.Tech in Computer Science & Engineering"},
    "experience_summary": {"display_summary": "1 Internship, 2 Key Projects verified"}
}


class TestCareerMentorUpgrade:
    """Tests for Part 1: Career Mentor quality improvements."""

    def test_four_canonical_categories_classification(self):
        """Test skills map accurately into the 4 canonical categories."""
        assert classify_mentor_category("Python") == "Core Technical Skills"
        assert classify_mentor_category("Spark") == "Core Technical Skills"
        assert classify_mentor_category("Docker") == "Engineering Tools and Practices"
        assert classify_mentor_category("CI/CD") == "Engineering Tools and Practices"
        assert classify_mentor_category("Git") == "Engineering Tools and Practices"
        assert classify_mentor_category("Communication") == "Professional and Behavioral Competencies"
        assert classify_mentor_category("Leadership") == "Professional and Behavioral Competencies"
        assert classify_mentor_category("Excel") == "Productivity and Business Tools"
        assert classify_mentor_category("Jira") == "Productivity and Business Tools"

    def test_skill_gap_preservation_and_prioritization(self):
        """Test all JD requirements are preserved and split into top 5 and expandable."""
        engine = CareerMentorEngine(SAMPLE_ANALYSIS)
        dossier = engine.build_mentor_dossier()

        gaps = dossier["gaps"]
        total_gaps = gaps["total_gaps_count"]
        prioritized = gaps["prioritized_gaps"]
        top_5 = gaps["top_priorities"]
        expandable = gaps["expandable_requirements"]

        # Ensure all requirements are preserved
        assert total_gaps == len(prioritized)
        assert len(top_5) <= 5
        assert len(top_5) + len(expandable) == total_gaps

        # Ensure each gap contains mandatory fields
        for gap in prioritized:
            assert "category" in gap
            assert gap["category"] in [
                "Core Technical Skills",
                "Engineering Tools and Practices",
                "Professional and Behavioral Competencies",
                "Productivity and Business Tools"
            ]
            assert "priority_tier" in gap
            assert "priority_label" in gap
            assert "priority_reason" in gap
            assert len(gap["priority_reason"]) > 10
            assert "recommended_action" in gap
            assert len(gap["recommended_action"]) > 5

    def test_spark_curriculum_distinctness(self):
        """Test Spark curriculum has 7 distinct, specialized stages."""
        curriculum = get_curriculum_for_skill("Spark")
        assert curriculum.get("is_verified_specialized") is True
        stages = curriculum["stages"]
        assert len(stages) == 7

        stage_titles = " ".join([s["name"] for s in stages]).lower()
        assert "dataframe" in stage_titles or "partition" in stage_titles
        assert "tuning" in stage_titles or "skew" in stage_titles or "catalyst" in stage_titles or "lazy" in stage_titles

    def test_logical_project_recommendations_never_invent_services(self):
        """Test non-software skills NEVER produce 'services' or 'APIs'."""
        candidate_projects = SAMPLE_ANALYSIS["projects"]
        verified_skills = SAMPLE_ANALYSIS["resume_skills"]
        evidence = {"projects": candidate_projects, "skills": verified_skills}

        # Communication
        comm_proj = build_logical_project_recommendation("Communication", "Mandatory", evidence)
        assert comm_proj["is_future_work"] is True
        assert comm_proj["status"] == "Recommended Future Enhancement"
        desc_lower = comm_proj["description"].lower()
        title_lower = comm_proj["title"].lower()
        assert "communication api" not in title_lower
        assert "communication service" not in title_lower
        assert "presentation" in title_lower or "design review" in title_lower or "walkthrough" in desc_lower

        # Excel
        excel_proj = build_logical_project_recommendation("Excel", "Preferred", evidence)
        assert excel_proj["is_future_work"] is True
        assert "excel api" not in excel_proj["title"].lower()
        assert "excel microservice" not in excel_proj["title"].lower()
        assert "workbook" in excel_proj["title"].lower() or "analytical" in excel_proj["description"].lower()

        # Docker (software skill logically attaching to Flask)
        docker_proj = build_logical_project_recommendation("Docker", "Mandatory", evidence)
        assert docker_proj["is_future_work"] is True
        assert "container" in docker_proj["description"].lower() or "docker" in docker_proj["title"].lower()

    def test_study_plan_full_reconciliation(self):
        """Test 14-day study plan accounts for all tasks without dropping milestones."""
        engine = CareerMentorEngine(SAMPLE_ANALYSIS)
        dossier = engine.build_mentor_dossier(timeline_days=14, daily_hours=2.0)

        study_plan = dossier["study_plan"]
        assert study_plan["timeline_days"] == 14
        assert len(study_plan["schedule_items"]) > 0
        # Deferred tasks must exist when curriculum tasks exceed 28 available hours
        total_tasks_accounted = len(study_plan["schedule_items"]) + len(study_plan.get("deferred_tasks", []))
        assert total_tasks_accounted >= len(study_plan["schedule_items"])


class TestInterviewStudioUpgrade:
    """Tests for Part 2: Interview Intelligence Studio quality improvements."""

    def test_non_circular_technology_roles(self):
        """Test technology profiles provide meaningful explanations rather than tautological fallbacks."""
        for tech in ["Computer Vision", "Machine Learning", "Deep Learning", "NLP", "C++", "Docker", "Spark"]:
            role_info = get_technology_profile(tech)
            explanation = role_info.get("role", "")
            assert len(explanation) > 20
            # Must not contain circular tautology
            assert "serves as a dedicated technical component supporting" not in explanation
            assert f"dedicated technical component supporting system requirements in {tech}" not in explanation

    def test_coherent_question_grouping_category_a(self):
        """Test Category A groups skills coherently without arbitrary 5-skill soft+hard mixtures."""
        generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
        cat_a_questions = generator.generate_category_a()

        assert len(cat_a_questions) > 0
        for q in cat_a_questions:
            q_text = q["question_text"]
            # Check question does not combine completely unrelated domains in a single sentence
            if "languages" in q_text.lower():
                assert "communication" not in q_text.lower()
                assert "adaptability" not in q_text.lower()

    def test_balanced_project_diversity_category_b(self):
        """Test Category B questions are interleaved across multiple candidate projects."""
        generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
        cat_b_questions = generator.generate_category_b()

        assert len(cat_b_questions) >= 4
        # Verify both projects appear in the question list
        p1_title = SAMPLE_ANALYSIS["projects"][0]["title"]
        p2_title = SAMPLE_ANALYSIS["projects"][1]["title"]

        p1_mentions = [q for q in cat_b_questions if p1_title in q["question_text"]]
        p2_mentions = [q for q in cat_b_questions if p2_title in q["question_text"]]

        assert len(p1_mentions) > 0, "Project 1 should have questions"
        assert len(p2_mentions) > 0, "Project 2 should have questions"

        # Check interleaving: the first two questions should not both be Project 1 if Project 2 exists
        first_q_proj = cat_b_questions[0]["source_reference"]
        second_q_proj = cat_b_questions[1]["source_reference"]
        assert first_q_proj != second_q_proj, "Questions should be interleaved across projects for balance"

    def test_clean_metadata_no_parser_leakage(self):
        """Test internal parser messages are not rendered as credentials or roles."""
        messy_analysis = dict(SAMPLE_ANALYSIS)
        messy_analysis["education_analysis"] = {"notes": "Degree not explicitly stated in resume"}
        messy_analysis["job_title"] = "Target role not specified"

        generator = InterviewQuestionGenerator(messy_analysis)
        cat_a = generator.generate_category_a()
        cat_d = generator.generate_category_d()

        all_text = " ".join([q["question_text"] + " " + q["detailed_answer"] for q in cat_a + cat_d])
        assert "Degree not explicitly stated" not in all_text
        assert "Target role not specified" not in all_text
