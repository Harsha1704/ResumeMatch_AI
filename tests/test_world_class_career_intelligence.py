"""
Comprehensive Quality Evaluation Suite for World-Class Career Intelligence Upgrade.
Tests all 10 candidate scenarios across:
1. Unified Candidate Evidence Registry & Invariants.
2. Context-Aware Job Requirement Intelligence.
3. 9-Point Career Counseling Profiles & Prerequisite DAG.
4. Realistic Study Plan Mathematical Reconciliation.
5. Complete Reference Answers & Completed Framework Demonstrations.
6. Multi-Project & Internship Question Balancing.
"""

import pytest
from src.analysis.matching_engine import ResumeMatchingEngine
from src.analysis.job_analyzer import JobDescriptionAnalyzer
from src.common.evidence_registry import build_unified_evidence_registry, resolve_canonical_skill
from src.mentor.mentor_engine import CareerMentorEngine
from src.mentor.dependency_graph import evaluate_candidate_prerequisites
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.answer_frameworks import FRAMEWORKS, build_completed_framework_demonstration
from tests.fixtures.candidate_scenarios import CANDIDATE_SCENARIOS


class TestWorldClassCareerIntelligence:

    @pytest.fixture
    def engine(self):
        return ResumeMatchingEngine()

    def test_ten_scenarios_evidence_registry_invariants(self, engine):
        """Validates consistency invariants across all 10 candidate scenarios."""
        for sc_name, sc_data in CANDIDATE_SCENARIOS.items():
            analysis = engine.analyze(
                resume_input=sc_data["raw_text"],
                job_description_input=sc_data["job_description"]
            )
            assert analysis["status"] == "success", f"Failed analysis for {sc_name}"

            reg = build_unified_evidence_registry(analysis)
            is_valid, violations = reg.verify_consistency_invariants()
            assert is_valid, f"Invariant violations in {sc_name}: {violations}"

            # Ensure evidence registry is attached to analysis output
            assert "evidence_registry" in analysis
            ev_summary = analysis["evidence_registry"]
            assert ev_summary["total_evidenced_skills"] >= 0

    def test_context_aware_requirement_classification(self):
        """Compound requirement clauses must inherit uniform status (Docker, Kubernetes, CI/CD, AWS)."""
        analyzer = JobDescriptionAnalyzer()
        jd_text = (
            "We are hiring a DevOps Engineer. "
            "Experience with Docker, Kubernetes, CI/CD, and AWS is required. "
            "Experience with Apache Spark and Power BI is preferred."
        )
        res = analyzer.analyze(jd_text)
        req_intel = {item["canonical_name"].lower(): item for item in res["requirement_intelligence"]}

        # All four skills in the required clause must be Required
        for skill in ["docker", "kubernetes", "ci/cd", "aws"]:
            assert skill in req_intel, f"Skill {skill} missing from requirement intelligence"
            assert req_intel[skill]["tier"] == "Required", f"{skill} was not classified as Required"
            assert "Experience with Docker, Kubernetes, CI/CD, and AWS is required." in req_intel[skill]["supporting_sentence"]

        # Preferred skills must be Preferred
        for skill in ["spark", "power bi"]:
            assert skill in req_intel, f"Skill {skill} missing from requirement intelligence"
            assert req_intel[skill]["tier"] == "Preferred", f"{skill} was not classified as Preferred"

    def test_prerequisite_directed_dependency_model(self):
        """Verifies adaptive starting point guidance based on prerequisite foundations."""
        # Candidate with JavaScript learning TypeScript
        eval_with_prereq = evaluate_candidate_prerequisites("typescript", ["JavaScript", "HTML", "CSS"])
        assert eval_with_prereq["has_all_prerequisites"] is True
        assert "bypass introductory syntax" in eval_with_prereq["recommended_starting_point"].lower()

        # Candidate without JavaScript learning TypeScript
        eval_without_prereq = evaluate_candidate_prerequisites("typescript", ["Python", "SQL"])
        assert eval_without_prereq["has_all_prerequisites"] is False
        assert "prerequisite" in eval_without_prereq["recommended_starting_point"].lower()

        # Candidate with Python & Pandas learning PySpark
        spark_eval = evaluate_candidate_prerequisites("pyspark", ["Python", "Pandas", "SQL"])
        assert spark_eval["has_all_prerequisites"] is True

    def test_nine_point_counseling_profile_generation(self, engine):
        """Every prioritized gap must contain the complete 9-point counseling profile."""
        ml_data = CANDIDATE_SCENARIOS["scenario_1_ml_student"]
        analysis = engine.analyze(ml_data["raw_text"], ml_data["job_description"])

        mentor = CareerMentorEngine(analysis)
        dossier = mentor.build_mentor_dossier()

        assert len(dossier["gaps"]["prioritized_gaps"]) > 0
        for gap in dossier["gaps"]["prioritized_gaps"]:
            prof = gap.get("counseling_profile")
            assert prof is not None, f"Missing counseling profile for {gap['skill_name']}"

            # Check all 9 points
            assert len(prof["q1_why_it_matters"]) > 20
            assert len(prof["q2_candidate_foundations"]) > 15
            assert len(prof["q3_demonstration_gap"]) > 15
            assert len(prof["q4_initial_learning_step"]) > 15
            assert len(prof["q5_practical_exercise_step"]) > 15
            assert len(prof["q6_practical_deliverable"]) > 15
            assert len(prof["q7_verification_method"]) > 15
            assert len(prof["q8_interview_talking_point"]) > 15
            assert "AFTER completing and verifying" in prof["q9_resume_bullet_guidance"]

    def test_realistic_study_plan_mathematical_reconciliation(self, engine):
        """Study plans for 3, 7, 14, and 30 days must reconcile mathematically with all 7 fields."""
        dev_data = CANDIDATE_SCENARIOS["scenario_2_backend_dev"]
        analysis = engine.analyze(dev_data["raw_text"], dev_data["job_description"])
        mentor = CareerMentorEngine(analysis)

        for days in [3, 7, 14, 30]:
            dossier = mentor.build_mentor_dossier(timeline_days=days, daily_hours=2.0)
            sp = dossier["study_plan"]
            assert sp["timeline_days"] == days
            assert sp["total_available_hours"] == round(days * 2.0, 1)

            # Mathematical reconciliation
            assert len(sp["schedule_items"]) >= days
            assert sp["total_tasks"] >= sp["scheduled_tasks_count"]

            # Validate 7 required fields on every schedule item
            for item in sp["schedule_items"]:
                assert "learning_objective" in item
                assert "explanation" in item
                assert "exercise" in item
                assert "expected_output" in item
                assert "verification_method" in item
                assert "estimated_duration" in item
                assert "relevant_resource" in item

    def test_interview_completed_framework_demonstrations(self, engine):
        """Every generated interview question must have populated framework demonstration."""
        fe_data = CANDIDATE_SCENARIOS["scenario_3_frontend_dev"]
        analysis = engine.analyze(fe_data["raw_text"], fe_data["job_description"])

        gen = InterviewQuestionGenerator(analysis)
        questions = gen.generate_questions(max_questions=10)

        for q in questions:
            demo = q.get("completed_framework_answer")
            assert demo is not None, f"Missing framework demonstration for question: {q['question_text']}"
            assert len(demo) >= 3, f"Framework demonstration too brief for {q['recommended_answer_framework']}"
            for step in demo:
                assert "label" in step
                assert "demonstration" in step
                assert len(step["demonstration"]) > 10

    def test_roadblock_question_structured_inquiry_when_undocumented(self, engine):
        """Technical obstacle questions must prompt the 6 candidate inquiries when resume lacks details."""
        backend_data = CANDIDATE_SCENARIOS["scenario_2_backend_dev"]
        analysis = engine.analyze(backend_data["raw_text"], backend_data["job_description"])

        gen = InterviewQuestionGenerator(analysis)
        cat_b = gen.generate_category_b()

        roadblock_q = next((q for q in cat_b if "roadblock" in q.get("question_id", "") or "bug" in q.get("question_text", "").lower()), None)
        assert roadblock_q is not None, "Roadblock question missing in Category B"

        missing_details = roadblock_q.get("missing_personal_details", [])
        assert len(missing_details) == 6, f"Expected 6 candidate inquiry prompts, got {len(missing_details)}"
        assert any("What happened?" in d for d in missing_details)
        assert any("How identified?" in d for d in missing_details)
        assert any("What caused it?" in d for d in missing_details)
        assert any("What changed?" in d for d in missing_details)
        assert any("How verified?" in d for d in missing_details)
        assert any("What learned?" in d for d in missing_details)

    def test_multi_project_question_diversity(self, engine):
        """When candidate has multiple projects, questions must not concentrate exclusively on one."""
        multi_proj_resume = (
            "Karthik Nair\n"
            "Software Engineer\n"
            "Skills: Python, Go, Docker, PostgreSQL\n"
            "Projects:\n"
            "Alpha Service\n"
            "Built high-throughput microservice in Go and PostgreSQL.\n"
            "Beta Ingestion\n"
            "Engineered Python data pipeline with Docker containers.\n"
            "Gamma Gateway\n"
            "Developed API routing proxy using Python and Redis."
        )
        analysis = engine.analyze(multi_proj_resume, "Software Engineer position requiring Python, Go, and Docker.")
        gen = InterviewQuestionGenerator(analysis)
        cat_b = gen.generate_category_b()

        projects_represented = {q["source_reference"] for q in cat_b if "source_reference" in q}
        assert len(projects_represented) == 3, f"Expected all 3 projects represented, got: {projects_represented}"
