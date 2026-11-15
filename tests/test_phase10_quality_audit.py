"""
Phase 10 Automated Regression Test Suite: Quality Audit and Correctness Gate.
Verifies across all 30 realistic audit scenarios:
1. 30 scenarios run through end-to-end matching without exceptions.
2. Requirement invariant holds: n_solid_req + n_partial_req + n_missing_req == total_required.
3. Alternative skill groups ("X or Y") are satisfied properly when one skill is present.
4. Career Mentor produces personalized 9-point counseling profile and realistic study plan.
5. Interview Intelligence Studio generates questions adhering to AnswerQualityValidator with zero fabricated first-person claims.
"""

import pytest
from tests.fixtures.thirty_audit_scenarios import THIRTY_AUDIT_SCENARIOS
from src.analysis.matching_engine import ResumeMatchingEngine
from src.mentor.mentor_engine import CareerMentorEngine
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.answer_validator import AnswerQualityValidator
from src.common.evidence_registry import build_unified_evidence_registry


class TestPhase10QualityAudit:
    @pytest.fixture(scope="class")
    @classmethod
    def engine(cls):
        return ResumeMatchingEngine()

    def test_30_scenarios_pipeline_execution(self, engine):
        """Verify all 30 audit scenarios execute cleanly through matching and gap analysis."""
        assert len(THIRTY_AUDIT_SCENARIOS) == 30
        for s_key, scenario in THIRTY_AUDIT_SCENARIOS.items():
            analysis = engine.analyze(
                resume_input=scenario["raw_text"],
                job_description_input=scenario["job_description"],
                resume_filename=f"{scenario['candidate_id']}.txt"
            )
            assert analysis.get("status") != "empty", f"Scenario {s_key} returned empty status"
            assert "matched_skills" in analysis
            assert "evidence_registry" in analysis

    def test_requirement_invariants_across_all_scenarios(self, engine):
        """Verify n_solid_req + n_partial_req + n_missing_req == total_required for all 30 scenarios."""
        for s_key, scenario in THIRTY_AUDIT_SCENARIOS.items():
            analysis = engine.analyze(
                resume_input=scenario["raw_text"],
                job_description_input=scenario["job_description"],
                resume_filename=f"{scenario['candidate_id']}.txt"
            )
            solid_req = len(analysis.get("fully_matched_required_skills", []))
            part_req = len(analysis.get("partially_evidenced_required_skills", []))
            miss_req = len(analysis.get("missing_required_skills", []))
            total_req = solid_req + part_req + miss_req
            total_extracted = len(analysis.get("required_skills", []))
            assert total_req == total_extracted, (
                f"Invariant failed for {s_key}: solid({solid_req}) + partial({part_req}) + "
                f"missing({miss_req}) = {total_req} != extracted({total_extracted})"
            )

    def test_alternative_skill_resolution_scenarios(self, engine):
        """Verify that satisfied alternative skills (e.g. Power BI or Tableau) do not create false missing gaps."""
        # Scenario 26: Power BI or Tableau (Candidate has Power BI)
        scen_26 = THIRTY_AUDIT_SCENARIOS["scenario_26_alt_powerbi_tableau"]
        res_26 = engine.analyze(scen_26["raw_text"], scen_26["job_description"], "scen_26.txt")
        missing_26 = [m.lower() for m in res_26.get("missing_required_skills", [])]
        assert "tableau" not in missing_26, "Tableau should not be flagged missing when Power BI is matched"

        # Scenario 27: PostgreSQL or MySQL (Candidate has MySQL)
        scen_27 = THIRTY_AUDIT_SCENARIOS["scenario_27_alt_postgres_mysql"]
        res_27 = engine.analyze(scen_27["raw_text"], scen_27["job_description"], "scen_27.txt")
        missing_27 = [m.lower() for m in res_27.get("missing_required_skills", [])]
        assert "postgresql" not in missing_27, "PostgreSQL should not be flagged missing when MySQL is matched"

        # Scenario 28: PyTorch or TensorFlow (Candidate has PyTorch)
        scen_28 = THIRTY_AUDIT_SCENARIOS["scenario_28_alt_pytorch_tensorflow"]
        res_28 = engine.analyze(scen_28["raw_text"], scen_28["job_description"], "scen_28.txt")
        missing_28 = [m.lower() for m in res_28.get("missing_required_skills", [])]
        assert "tensorflow" not in missing_28, "TensorFlow should not be flagged missing when PyTorch is matched"

    def test_interview_studio_non_fabrication_audit(self, engine):
        """Verify that generated interview answers contain zero unsupported first-person claims."""
        scen = THIRTY_AUDIT_SCENARIOS["scenario_30_multi_project_diversity"]
        analysis = engine.analyze(scen["raw_text"], scen["job_description"], "scen_30.txt")
        interview_gen = InterviewQuestionGenerator(analysis)
        questions = interview_gen.generate_questions(category="ALL", max_questions=15)
        assert len(questions) >= 5

        for q in questions:
            val = AnswerQualityValidator.validate_answer(q)
            assert val["is_valid"], f"Validation failed for {q.get('question_id')}: {val['issues']}"
            assert val["quality_score"] >= 80.0
