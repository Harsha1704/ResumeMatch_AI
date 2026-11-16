"""
Test Suite: Phase 2.1.3 - Validator Import & Evidence-Trust Repair
==================================================================
Verifies:
1. Direct module import of answer_validator and proper typing inspection (no NameError).
2. 'Verified ...:' markers with fabricated or missing evidence are classified as unverified/unsupported.
3. 'Verified ...:' markers with genuine supplied resume evidence are classified as resume-supported.
4. Candidate-confirmed facts remain distinct from resume-supported evidence.
5. 'evidence_sources' metadata is NEVER treated as proof of candidate achievements.
6. Unsupported personal claims across 1st person, 3rd person, passive voice, and bare action verbs
   are caught across all 13 core generated output fields.
7. General technical guidance and pedagogical explanations remain valid.
8. Full end-to-end interview question generation passes validation (is_valid=True, score >= 80).
"""

import pytest
import typing
from typing import Dict, Any, List

from src.interview.answer_validator import AnswerQualityValidator
from src.interview.question_generator import InterviewQuestionGenerator


class TestPhase213ValidatorImportAndEvidenceTrust:
    """Test suite for Phase 2.1.3 Validator Import & Evidence-Trust Repair."""

    # -------------------------------------------------------------------------
    # 1. Direct module import & type hints inspection
    # -------------------------------------------------------------------------
    def test_01_direct_module_import_and_type_hints(self):
        """Direct module import and get_type_hints succeeds without NameError."""
        import src.interview.answer_validator as validator_module

        assert hasattr(validator_module, "AnswerQualityValidator")
        cls = validator_module.AnswerQualityValidator

        # Inspect type hints of all key methods to verify typing annotations resolve cleanly
        hints_audit = typing.get_type_hints(cls.audit_record_fields)
        assert "question_record" in hints_audit
        assert "return" in hints_audit

        hints_classify = typing.get_type_hints(cls.classify_statement)
        assert "text" in hints_classify
        assert "return" in hints_classify

        hints_claims = typing.get_type_hints(cls.audit_answer_for_unsupported_first_person_claims)
        assert "text" in hints_claims
        assert "return" in hints_claims

        hints_validate = typing.get_type_hints(cls.validate_answer)
        assert "question_record" in hints_validate
        assert "return" in hints_validate

    # -------------------------------------------------------------------------
    # 2. 'Verified ...:' marker with fabricated value
    # -------------------------------------------------------------------------
    def test_02_verified_marker_with_fabricated_value(self):
        """Verified marker with fabricated/unevidenced value is flagged as unsupported."""
        fabricated_marker = "Verified Organization: FakeGlobalCorp; Verified Position: Principal Architect"

        # When evidence is unavailable / empty
        res_no_ev = AnswerQualityValidator.classify_statement(fabricated_marker, evidence=None)
        assert res_no_ev["is_resume_supported"] is False
        assert res_no_ev["is_unsupported_personal_claim"] is True

        # When evidence is provided but does NOT contain FakeGlobalCorp
        genuine_ev = {"organization": "Acme Corp", "position": "Software Engineer"}
        res_with_ev = AnswerQualityValidator.classify_statement(fabricated_marker, evidence=genuine_ev)
        assert res_with_ev["is_resume_supported"] is False
        assert res_with_ev["is_unsupported_personal_claim"] is True

        # Audit method must flag the unevidenced value
        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            fabricated_marker, verified_evidence=genuine_ev
        )
        assert len(issues) > 0
        assert any("FakeGlobalCorp" in iss for iss in issues)

    # -------------------------------------------------------------------------
    # 3. 'Verified ...:' marker with genuine evidence value
    # -------------------------------------------------------------------------
    def test_03_verified_marker_with_genuine_evidence_value(self):
        """Verified marker with genuine supplied evidence is classified as resume-supported."""
        genuine_marker = "Verified Organization: Acme Corp; Verified Position: Backend Intern; Verified Tools: Python, PostgreSQL"
        evidence_data = {
            "organization": "Acme Corp",
            "position": "Backend Intern",
            "skills": ["Python", "PostgreSQL"],
            "technologies": ["Python", "PostgreSQL"]
        }

        classification = AnswerQualityValidator.classify_statement(genuine_marker, evidence=evidence_data)
        assert classification["is_resume_supported"] is True
        assert classification["is_candidate_confirmed"] is False
        assert classification["is_unsupported_personal_claim"] is False

        # Audit method must report NO issues for genuinely evidenced markers
        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            genuine_marker, verified_evidence=evidence_data
        )
        assert len(issues) == 0

    # -------------------------------------------------------------------------
    # 4. Candidate-confirmed fact without resume evidence
    # -------------------------------------------------------------------------
    def test_04_candidate_confirmed_fact_without_resume_evidence(self):
        """Candidate-confirmed facts remain distinct from resume evidence."""
        confirmed_fact = "[Candidate Confirmed: Configured Kafka event topics and consumer groups]"

        # Without evidence
        res = AnswerQualityValidator.classify_statement(confirmed_fact, evidence=None)
        assert res["is_candidate_confirmed"] is True
        assert res["is_resume_supported"] is False
        assert res["is_unsupported_personal_claim"] is False

        # Even with unrelated resume evidence, candidate confirmation is NEVER counted as resume evidence
        res_with_ev = AnswerQualityValidator.classify_statement(
            confirmed_fact, evidence={"organization": "TechCorp", "skills": ["Python"]}
        )
        assert res_with_ev["is_candidate_confirmed"] is True
        assert res_with_ev["is_resume_supported"] is False

    # -------------------------------------------------------------------------
    # 5. evidence_sources label without candidate evidence
    # -------------------------------------------------------------------------
    def test_05_evidence_source_label_without_candidate_evidence(self):
        """evidence_sources metadata is never treated as proof of candidate achievements."""
        question_with_source_only = {
            "question_text": "Describe your background with distributed databases.",
            "evidence_sources": [
                "Candidate Project Records",
                "Job Description Mandatory Requirements",
                "Matched Skills against Target Job Description"
            ],
            # Note: No 'verified_evidence' or 'candidate_evidence' provided
            "detailed_answer": "I maintained the production database and debugged the payment workflow.",
            "short_answer": "Maintained the production database.",
            "simpler_answer": "Database operations.",
            "curated_answer": "Production database tuning.",
        }

        # audit_record_fields must NOT use evidence_sources to vindicate the claims
        issues = AnswerQualityValidator.audit_record_fields(question_with_source_only)
        assert len(issues) >= 2
        assert any("production database" in iss.lower() for iss in issues)
        assert any("payment workflow" in iss.lower() for iss in issues)

        # Full validation must fail or heavily penalize the record
        val_result = AnswerQualityValidator.validate_answer(question_with_source_only)
        assert val_result["is_valid"] is False or val_result["quality_score"] < 80
        assert any("production database" in iss.lower() for iss in val_result["issues"])

    # -------------------------------------------------------------------------
    # 6. Unsupported personal claims across all 13 audited fields
    # -------------------------------------------------------------------------
    def test_06_unsupported_personal_claims_in_every_audited_field(self):
        """Test active, 3rd-person, passive, and bare claims across all 13 output fields."""
        base_valid_record = {
            "question_text": "Explain relational database indexing and performance characteristics.",
            "detailed_answer": "Relational database indexing structures organize key pointers for logarithmic query complexity. B-Trees balance read and write latency across tree depth.",
            "short_answer": "B-Tree indexes provide logarithmic lookups.",
            "simpler_answer": "Indexes speed up data search.",
            "curated_answer": "Balanced tree index structures.",
            "examples": ["Standard B-Tree diagram."],
            "step_by_step_explanation": [
                {"step": "Analyze", "detail": "Inspect index selectivity.", "concrete_example": "EXPLAIN ANALYZE select"}
            ],
            "follow_up_questions": [
                {
                    "question": "What is index overhead?",
                    "reference_answer": "Insert operations require index tree updates.",
                    "practical_example": "High write-frequency tables experience insert latency."
                }
            ],
            "completed_framework_answer": [
                {"demonstration": "Context: Index architecture.", "content": "Pedagogical explanation of B-Trees.", "detail": "Clustered indexes."}
            ],
            "framework_template": [
                {"placeholder": "[Candidate to specify: schema]", "prompt": "Identify table", "guidance": "Focus on high volume"}
            ],
            "why_this_works": "Indexing reduces full-table scan operations.",
            "suggested_improvements": ["Review composite index column ordering."],
            "missing_personal_details": ["[Candidate to specify: database table name]"],
            "verified_evidence": ["PostgreSQL indexing documentation"]
        }

        # 5 required claim variations (1st person, 3rd person, passive voice, bare action)
        unsupported_claims = [
            "I contributed to production features.",
            "The candidate contributed to production features.",
            "Production features were contributed.",
            "Contributed to production features.",
            "I collaborated with the engineering team.",
            "Collaborated with the engineering team.",
            "I debugged the payment workflow.",
            "The payment workflow was debugged.",
            "Debugged the payment workflow.",
            "I maintained the production database.",
            "The production database was maintained.",
            "Maintained the production database.",
            "I coordinated deployment.",
            "Deployment was coordinated.",
            "Coordinated deployment."
        ]

        # Verify each of the 5 core claims is detected individually
        for claim in [
            "I contributed to production features.",
            "I collaborated with the engineering team.",
            "I debugged the payment workflow.",
            "I maintained the production database.",
            "I coordinated deployment.",
            "Production features were contributed.",
            "The payment workflow was debugged.",
            "The production database was maintained.",
            "Deployment was coordinated."
        ]:
            iss = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(claim, verified_evidence=None)
            assert len(iss) > 0, f"Expected claim '{claim}' to be flagged as unsupported!"

        # Audit each of the 13 fields with an injected unsupported claim
        fields_to_test = [
            ("detailed_answer", "I contributed to production features."),
            ("short_answer", "I collaborated with the engineering team."),
            ("simpler_answer", "I debugged the payment workflow."),
            ("curated_answer", "I maintained the production database."),
            ("examples", "Production features were contributed."),
            ("step_by_step_explanation", [{"step": "Action", "detail": "Deployment was coordinated.", "concrete_example": "Script"}]),
            ("follow_up_questions", [{"question": "Followup?", "reference_answer": "I debugged the payment workflow."}]),
            ("completed_framework_answer", [{"demonstration": "I coordinated deployment.", "content": "Done"}]),
            ("framework_template", [{"placeholder": "P", "prompt": "I contributed to production features.", "guidance": "G"}]),
            ("why_this_works", "I maintained the production database."),
            ("suggested_improvements", ["I collaborated with the engineering team."]),
            ("missing_personal_details", ["Contributed to production features."]),
            ("verified_evidence", ["Debugged the payment workflow."])
        ]

        assert len(fields_to_test) == 13

        for field_name, bad_value in fields_to_test:
            rec = dict(base_valid_record)
            rec[field_name] = bad_value
            issues = AnswerQualityValidator.audit_record_fields(rec, verified_evidence=None)
            assert len(issues) > 0, (
                f"Field '{field_name}' failed to flag injected unsupported claim: {bad_value}."
            )
            val_res = AnswerQualityValidator.validate_answer(rec)
            assert val_res["is_valid"] is False, (
                f"Field '{field_name}' failed to invalidate answer with injected claim: {bad_value}."
            )

    # -------------------------------------------------------------------------
    # 7. General technical guidance remains valid
    # -------------------------------------------------------------------------
    def test_07_general_technical_guidance_remains_valid(self):
        """Pedagogical and general technical explanations pass validation without penalty."""
        # Labeled guidance
        labeled_guidance = (
            "[General Technical Guidance]: In distributed architectures, idempotent consumer "
            "handlers prevent duplicate message processing when network acknowledgments fail."
        )
        c1 = AnswerQualityValidator.classify_statement(labeled_guidance)
        assert c1["is_general_technical"] is True
        assert c1["is_unsupported_personal_claim"] is False

        # Objective pedagogical explanation
        pedagogical_explanation = (
            "Database connection pools manage reusable database socket handles across application "
            "worker threads, eliminating per-query TCP connection setup overhead."
        )
        c2 = AnswerQualityValidator.classify_statement(pedagogical_explanation)
        assert c2["is_general_technical"] is True
        assert c2["is_unsupported_personal_claim"] is False

        # Illustrative scenario
        illustrative_scenario = (
            "[Illustrative Model Scenario — Not candidate resume data]: When scaling backend services, "
            "implementing rate limiting protects internal microservice endpoints."
        )
        c3 = AnswerQualityValidator.classify_statement(illustrative_scenario)
        assert c3["is_illustrative_scenario"] is True
        assert c3["is_unsupported_personal_claim"] is False

        # Missing info placeholder
        placeholder = "[Candidate to specify: exact throughput requirement in RPS]"
        c4 = AnswerQualityValidator.classify_statement(placeholder)
        assert c4["is_missing_info_placeholder"] is True
        assert c4["is_unsupported_personal_claim"] is False

    # -------------------------------------------------------------------------
    # 8. Full end-to-end interview question generation passes validation
    # -------------------------------------------------------------------------
    def test_08_full_end_to_end_interview_generation(self):
        """End-to-end generation produces fully grounded questions passing quality validation."""
        analysis_payload = {
            "candidate_name": "Jane Doe",
            "detected_target_role": "Backend Software Engineer",
            "extracted_skills": ["Python", "Flask", "Docker", "PostgreSQL"],
            "projects": [
                {
                    "title": "Inventory Management API",
                    "technologies": ["Python", "Flask", "PostgreSQL"],
                    "description": "Developed RESTful API endpoints for catalog search and order placement."
                }
            ],
            "internships": [
                {
                    "organization": "DataFlow Systems",
                    "position": "Software Engineering Intern",
                    "dates": "June 2024 - August 2024",
                    "responsibilities": ["Wrote automated data ingestion pipelines using Python and SQL."]
                }
            ],
            "job_requirements": {
                "required_skills": ["Python", "PostgreSQL", "REST APIs"],
                "preferred_skills": ["Docker", "Kubernetes"]
            }
        }

        generator = InterviewQuestionGenerator(analysis_payload)
        questions = generator.generate_questions(category="ALL", max_questions=25)
        assert len(questions) > 0

        for q in questions:
            val_res = AnswerQualityValidator.validate_answer(q)
            assert val_res["is_valid"] is True, f"Question failed validation: {val_res['issues']}"
            assert val_res["quality_score"] >= 80.0, f"Quality score too low ({val_res['quality_score']}): {val_res['issues']}"
