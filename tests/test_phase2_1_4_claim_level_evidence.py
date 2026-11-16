"""
Test Suite: Phase 2.1.4 - Claim-Level Evidence Validation Repair
================================================================
Verifies:
1. Genuine organization marker plus unsupported deployment claim preserves both classifications.
2. Genuine project title marker plus unsupported architecture claim flags architecture.
3. Genuine technology evidence plus unsupported testing claim flags testing.
4. Multiple valid markers alongside one fabricated marker preserves valid while flagging fabricated.
5. Short-token false match prevention (SQL vs NoSQL, Java vs JavaScript, C vs CSS, Go vs Django, Rust vs trust).
6. Mixed candidate-confirmed facts and unsupported claims coexist correctly.
7. Unsupported claims in every audited output field are caught.
8. Existing valid generated interview answers remain fully valid (is_valid=True, score >= 80).
"""

import pytest
from typing import Dict, Any, List

from src.interview.answer_validator import AnswerQualityValidator
from src.interview.question_generator import InterviewQuestionGenerator


class TestPhase214ClaimLevelEvidenceValidation:
    """Test suite for Phase 2.1.4 Claim-Level Evidence Validation Repair."""

    # -------------------------------------------------------------------------
    # 1. Genuine organization marker plus unsupported deployment claim
    # -------------------------------------------------------------------------
    def test_01_genuine_organization_plus_unsupported_deployment_claim(self):
        """A verified organization must not authenticate an unrelated deployment claim."""
        text = "Verified Organization: Acme Corp; I coordinated deployment."
        evidence = {"organization": "Acme Corp"}

        classification = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        # Both classifications must coexist:
        assert classification["is_resume_supported"] is True, "Valid marker must be recognized as resume-supported"
        assert classification["is_unsupported_personal_claim"] is True, "Deployment claim must NOT be authenticated by organization"

        # Audit method must flag the ungrounded deployment coordination
        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            text, verified_evidence=evidence
        )
        assert len(issues) > 0
        assert any("deployment" in iss.lower() for iss in issues)

        # Full validation must fail or penalize the record
        rec = {
            "question_text": "Describe your background at Acme Corp.",
            "detailed_answer": text,
            "short_answer": "Worked at Acme Corp.",
            "simpler_answer": "Acme Corp experience.",
            "curated_answer": "Enterprise experience.",
            "verified_evidence": ["Acme Corp"]
        }
        val_res = AnswerQualityValidator.validate_answer(rec)
        assert val_res["is_valid"] is False or val_res["quality_score"] < 80.0
        assert any("deployment" in iss.lower() for iss in val_res["issues"])

    # -------------------------------------------------------------------------
    # 2. Genuine project title plus unsupported architecture claim
    # -------------------------------------------------------------------------
    def test_02_genuine_project_title_plus_unsupported_architecture_claim(self):
        """A verified project title must not authenticate an ungrounded architecture claim."""
        text = "Verified Project Title: TaskTracker; I deliberately chose a modular monolithic architecture."
        evidence = {"projects": [{"title": "TaskTracker"}]}

        classification = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert classification["is_resume_supported"] is True, "Valid project title must be recognized"
        assert classification["is_unsupported_personal_claim"] is True, "Architecture choice must NOT be authenticated by project title"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            text, verified_evidence=evidence
        )
        assert len(issues) > 0
        assert any("architecture" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 3. Genuine technology evidence plus unsupported testing claim
    # -------------------------------------------------------------------------
    def test_03_genuine_technology_evidence_plus_unsupported_testing_claim(self):
        """Verified technology tokens must not authenticate an ungrounded testing claim."""
        text = "Verified Tools: Python, FastAPI; I authored automated unit tests."
        evidence = {"skills": ["Python", "FastAPI"]}

        classification = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert classification["is_resume_supported"] is True, "Valid tools must be recognized"
        assert classification["is_unsupported_personal_claim"] is True, "Testing claim must NOT be authenticated by tools"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            text, verified_evidence=evidence
        )
        assert len(issues) > 0
        assert any("unit test" in iss.lower() or "testing" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 4. Multiple valid markers alongside one fabricated marker
    # -------------------------------------------------------------------------
    def test_04_multiple_valid_markers_alongside_one_fabricated_marker(self):
        """Multiple valid markers and a fabricated marker can coexist; both classifications preserved."""
        text = "Verified Organization: Acme Corp; Verified Position: Backend Intern; Verified Technologies: BrainfuckFake"
        evidence = {
            "organization": "Acme Corp",
            "position": "Backend Intern",
            "skills": ["Python", "PostgreSQL"]
        }

        classification = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        # Valid markers are present -> is_resume_supported is True
        assert classification["is_resume_supported"] is True, "Valid markers must establish resume support"
        # Fabricated marker is present -> is_unsupported_personal_claim is True
        assert classification["is_unsupported_personal_claim"] is True, "Fabricated marker must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            text, verified_evidence=evidence
        )
        assert len(issues) > 0
        assert any("BrainfuckFake" in iss for iss in issues)

    # -------------------------------------------------------------------------
    # 5. Short-token false matches (SQL vs NoSQL, Java vs JavaScript, etc.)
    # -------------------------------------------------------------------------
    def test_05_short_token_false_matches_prevented(self):
        """Boundary-aware token matching prevents unsafe substring collisions."""
        # 1. Candidate has SQL; text discusses NoSQL -> must NOT be resume-supported
        ev_sql = {"skills": ["SQL"]}
        text_nosql = "I have experience with NoSQL database architectures."
        cls_sql_nosql = AnswerQualityValidator.classify_statement(text_nosql, evidence=ev_sql)
        assert cls_sql_nosql["is_resume_supported"] is False, "SQL must not match inside NoSQL"

        # Marker: Verified Tools: SQL when candidate only has NoSQL -> fabricated
        ev_nosql = {"skills": ["NoSQL"]}
        marker_sql = "Verified Tools: SQL"
        cls_marker_sql = AnswerQualityValidator.classify_statement(marker_sql, evidence=ev_nosql)
        assert cls_marker_sql["is_resume_supported"] is False
        assert cls_marker_sql["is_unsupported_personal_claim"] is True

        # 2. Candidate has Java; text mentions JavaScript -> must NOT match
        ev_java = {"skills": ["Java"]}
        text_js = "I developed frontend components using JavaScript."
        cls_java_js = AnswerQualityValidator.classify_statement(text_js, evidence=ev_java)
        assert cls_java_js["is_resume_supported"] is False, "Java must not match inside JavaScript"

        # 3. Candidate has C; text mentions CSS -> must NOT match
        ev_c = {"skills": ["C"]}
        text_css = "Styled responsive web layouts with CSS and HTML."
        cls_c_css = AnswerQualityValidator.classify_statement(text_css, evidence=ev_c)
        assert cls_c_css["is_resume_supported"] is False, "C must not match inside CSS"

        # 4. Candidate has Go; text mentions Django -> must NOT match
        ev_go = {"skills": ["Go"]}
        text_django = "Built REST services using the Django framework."
        cls_go_django = AnswerQualityValidator.classify_statement(text_django, evidence=ev_go)
        assert cls_go_django["is_resume_supported"] is False, "Go must not match inside Django"

        # 5. Candidate has Rust; text mentions trust -> must NOT match
        ev_rust = {"skills": ["Rust"]}
        text_trust = "Built trust with cross-functional product stakeholders."
        cls_rust_trust = AnswerQualityValidator.classify_statement(text_trust, evidence=ev_rust)
        assert cls_rust_trust["is_resume_supported"] is False, "Rust must not match inside trust"

        # 6. Genuinely matching SQL token DOES match
        text_exact_sql = "Executed optimized SQL queries on relational schemas."
        cls_exact_sql = AnswerQualityValidator.classify_statement(text_exact_sql, evidence=ev_sql)
        assert cls_exact_sql["is_resume_supported"] is True, "Exact SQL token must match"

    # -------------------------------------------------------------------------
    # 6. Mixed candidate-confirmed and unsupported claims
    # -------------------------------------------------------------------------
    def test_06_mixed_candidate_confirmed_and_unsupported_claims(self):
        """Candidate-confirmed fact with an unsupported claim preserves both classifications."""
        text = "[Candidate Confirmed: Configured PostgreSQL replication]; I maintained the production database."
        evidence = None

        classification = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert classification["is_candidate_confirmed"] is True, "Candidate confirmation must be preserved"
        assert classification["is_resume_supported"] is False, "Candidate confirmation is not independent resume evidence"
        assert classification["is_unsupported_personal_claim"] is True, "Unevidenced database maintenance must be flagged"

        # Even if unrelated resume evidence is passed
        ev_unrelated = {"organization": "Acme Corp", "skills": ["Python"]}
        cls_with_ev = AnswerQualityValidator.classify_statement(text, evidence=ev_unrelated)
        assert cls_with_ev["is_candidate_confirmed"] is True
        assert cls_with_ev["is_resume_supported"] is False
        assert cls_with_ev["is_unsupported_personal_claim"] is True

    # -------------------------------------------------------------------------
    # 7. Unsupported claims in every audited output field
    # -------------------------------------------------------------------------
    def test_07_unsupported_claims_in_every_audited_output_field(self):
        """Test detection across all 13 core generated output fields."""
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
            assert len(issues) > 0, f"Field '{field_name}' failed to flag injected unsupported claim: {bad_value}."
            val_res = AnswerQualityValidator.validate_answer(rec)
            assert val_res["is_valid"] is False, f"Field '{field_name}' failed to invalidate answer with injected claim: {bad_value}."

    # -------------------------------------------------------------------------
    # 8. Existing valid generated interview answers remain valid
    # -------------------------------------------------------------------------
    def test_08_existing_valid_generated_interview_answers_remain_valid(self):
        """End-to-end question generation passes quality validation without false rejections."""
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

    # -------------------------------------------------------------------------
    # 9. Illustrative scenario followed by an unsupported deployment claim
    # -------------------------------------------------------------------------
    def test_09_illustrative_scenario_followed_by_unsupported_deployment_claim(self):
        """Illustrative scenario marker must not suppress an unsupported deployment claim following it."""
        text = (
            "[Illustrative Scenario — Not candidate resume data]: When scaling backend services, "
            "rate limiting protects internal endpoints. I coordinated deployment."
        )
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True, "Illustrative scenario must be recognized"
        assert cls_res["is_unsupported_personal_claim"] is True, "Deployment claim outside scenario must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) > 0
        assert any("deployment" in iss.lower() for iss in issues)

        rec = {
            "question_text": "How do you handle production scaling?",
            "detailed_answer": text,
            "short_answer": "Used rate limiting.",
            "simpler_answer": "Rate limiting protects services.",
            "curated_answer": "Standard scaling patterns."
        }
        val = AnswerQualityValidator.validate_answer(rec)
        assert val["is_valid"] is False, "Record with unsupported claim outside scenario must fail validation"

    # -------------------------------------------------------------------------
    # 10. Unsupported personal claim followed by an illustrative scenario
    # -------------------------------------------------------------------------
    def test_10_unsupported_personal_claim_followed_by_illustrative_scenario(self):
        """Unsupported personal claim before an illustrative scenario must be flagged."""
        text = (
            "I coordinated deployment. [Illustrative Scenario — Not candidate resume data]: "
            "When scaling backend services, rate limiting protects internal endpoints."
        )
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is True

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) > 0
        assert any("deployment" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 11. Unsupported claim entirely inside a clearly labeled illustrative block
    # -------------------------------------------------------------------------
    def test_11_unsupported_claim_entirely_inside_illustrative_block(self):
        """Claims inside an illustrative block are not candidate achievements and not falsely flagged."""
        text = (
            "[Illustrative Scenario — Not candidate resume data]: In this hypothetical model scenario, "
            "the engineer deployed the service to production."
        )
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_resume_supported"] is False, "Scenario content must NOT be classified as candidate achievement"
        assert cls_res["is_unsupported_personal_claim"] is False, "Scenario content must not be flagged as candidate claim"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) == 0, f"Expected no issues for claim inside illustrative block, got {issues}"

    # -------------------------------------------------------------------------
    # 12. Valid illustrative guidance without personal claims
    # -------------------------------------------------------------------------
    def test_12_valid_illustrative_guidance_without_personal_claims(self):
        """Valid illustrative guidance remains valid and unflagged."""
        text = (
            "[Illustrative Model Scenario — Not candidate resume data]: In distributed systems, "
            "consensus mechanisms like Raft maintain replica state consistency."
        )
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is False
        assert cls_res["is_resume_supported"] is False

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) == 0

    # -------------------------------------------------------------------------
    # 13. Mixed valid resume marker, illustrative block, and unsupported claim
    # -------------------------------------------------------------------------
    def test_13_mixed_valid_resume_marker_illustrative_block_and_unsupported_claim(self):
        """Preserves all applicable classifications when valid marker, scenario, and claim mix."""
        text = (
            "Verified Organization: Acme Corp. [Illustrative Scenario — Not candidate resume data]: "
            "In production code reviews, teams follow git conventions. I coordinated deployment."
        )
        evidence = {"organization": "Acme Corp"}

        cls_res = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert cls_res["is_resume_supported"] is True, "Acme Corp marker must be recognized"
        assert cls_res["is_illustrative_scenario"] is True, "Illustrative block must be recognized"
        assert cls_res["is_unsupported_personal_claim"] is True, "Deployment claim must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            text, verified_evidence=evidence
        )
        assert len(issues) > 0
        assert any("deployment" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 14. Illustrative block boundary preserves: I led the deployment.
    # -------------------------------------------------------------------------
    def test_14_illustrative_block_boundary_preserves_i_led_the_deployment(self):
        """Block boundary does not depend on a fixed verb list; 'I led' is preserved and flagged."""
        text = "[Illustrative Scenario]: A sample deployment workflow. I led the deployment."
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is True, "Outside claim 'I led the deployment' must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) > 0, "Auditor must see the outside claim"
        assert any("led" in iss.lower() or "deployment" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 15. Illustrative block boundary preserves: I managed the production database.
    # -------------------------------------------------------------------------
    def test_15_illustrative_block_boundary_preserves_i_managed_the_production_database(self):
        """Block boundary preserves and flags ungrounded database management."""
        text = "[Illustrative Scenario]: A sample deployment workflow. I managed the production database."
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is True, "Outside claim 'I managed the production database' must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) > 0
        assert any("database" in iss.lower() or "managed" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 16. Illustrative block boundary preserves: I supervised the engineering team.
    # -------------------------------------------------------------------------
    def test_16_illustrative_block_boundary_preserves_i_supervised_the_engineering_team(self):
        """Block boundary preserves and flags ungrounded engineering team supervision."""
        text = "[Illustrative Scenario]: A sample deployment workflow. I supervised the engineering team."
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is True, "Outside claim 'I supervised the engineering team' must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) > 0
        assert any("supervised" in iss.lower() or "team" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 17. Illustrative block boundary preserves: I owned the architecture decisions.
    # -------------------------------------------------------------------------
    def test_17_illustrative_block_boundary_preserves_i_owned_the_architecture_decisions(self):
        """Block boundary preserves and flags ungrounded architecture ownership."""
        text = "[Illustrative Scenario]: A sample deployment workflow. I owned the architecture decisions."
        cls_res = AnswerQualityValidator.classify_statement(text)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is True, "Outside claim 'I owned the architecture decisions' must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
        assert len(issues) > 0
        assert any("architecture" in iss.lower() or "owned" in iss.lower() for iss in issues)

    # -------------------------------------------------------------------------
    # 18. Illustrative block boundary preserves passive-voice unsupported claims
    # -------------------------------------------------------------------------
    def test_18_illustrative_block_boundary_preserves_passive_voice_unsupported_claims(self):
        """Passive-voice unsupported claims following an illustrative block remain visible to the auditor."""
        passive_cases = [
            ("[Illustrative Scenario]: A sample deployment workflow. Deployment was led by our team.", "deployment"),
            ("[Illustrative Scenario]: A sample deployment workflow. Production database was managed without downtime.", "database"),
            ("[Illustrative Scenario]: A sample deployment workflow. Architecture decisions were owned by me.", "architecture")
        ]

        for text, keyword in passive_cases:
            cls_res = AnswerQualityValidator.classify_statement(text)
            assert cls_res["is_illustrative_scenario"] is True
            assert cls_res["is_unsupported_personal_claim"] is True, f"Passive claim '{text}' must be flagged as unsupported"

            issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text)
            assert len(issues) > 0, f"Auditor must catch passive claim in: {text}"
            assert any(keyword in iss.lower() for iss in issues), f"Expected '{keyword}' in auditor issues for: {text}"

    # -------------------------------------------------------------------------
    # 19. Genuine marker entirely inside an illustrative block must not authenticate
    # -------------------------------------------------------------------------
    def test_19_genuine_marker_entirely_inside_illustrative_block_must_not_authenticate(self):
        """Genuine marker inside an illustrative block cannot establish resume support."""
        text = (
            "[Illustrative Scenario — Not candidate resume data]: In this hypothetical model scenario, "
            "Verified Organization: Acme Corp is a sample company."
        )
        evidence = {"organization": "Acme Corp"}

        cls_res = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_resume_supported"] is False, "Genuine marker inside illustrative block must NOT establish resume support"
        assert cls_res["is_unsupported_personal_claim"] is False

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text, verified_evidence=evidence)
        assert len(issues) == 0, f"Expected no issues for marker inside illustrative block, got: {issues}"

    # -------------------------------------------------------------------------
    # 20. Fabricated marker inside an illustrative block not treated as candidate claim
    # -------------------------------------------------------------------------
    def test_20_fabricated_marker_inside_illustrative_block_not_treated_as_candidate_claim(self):
        """Fabricated marker inside an illustrative block is not treated as a candidate claim."""
        text = (
            "[Illustrative Scenario — Not candidate resume data]: In this hypothetical model scenario, "
            "Verified Organization: Fabricated Corp was simulated."
        )
        evidence = {"organization": "Acme Corp"}

        cls_res = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is False, "Fabricated marker inside illustrative block must NOT be treated as candidate claim"
        assert cls_res["is_resume_supported"] is False

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text, verified_evidence=evidence)
        assert len(issues) == 0, f"Expected no issues for fabricated marker inside illustrative block, got: {issues}"

    # -------------------------------------------------------------------------
    # 21. Genuine marker outside an illustrative block establishes resume support
    # -------------------------------------------------------------------------
    def test_21_genuine_marker_outside_illustrative_block_establishes_resume_support(self):
        """Genuine marker outside an illustrative block establishes resume support."""
        text = (
            "Verified Organization: Acme Corp. [Illustrative Scenario — Not candidate resume data]: "
            "In distributed systems, consensus mechanisms maintain replica state consistency."
        )
        evidence = {"organization": "Acme Corp"}

        cls_res = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert cls_res["is_resume_supported"] is True, "Genuine marker outside illustrative block must establish resume support"
        assert cls_res["is_illustrative_scenario"] is True
        assert cls_res["is_unsupported_personal_claim"] is False

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text, verified_evidence=evidence)
        assert len(issues) == 0

    # -------------------------------------------------------------------------
    # 22. Genuine marker outside plus unsupported claim after illustrative block preserves both
    # -------------------------------------------------------------------------
    def test_22_genuine_marker_outside_plus_unsupported_claim_after_illustrative_block_preserves_both(self):
        """Genuine marker outside plus unsupported claim after illustrative block preserves both classifications."""
        text = (
            "Verified Organization: Acme Corp. [Illustrative Scenario — Not candidate resume data]: "
            "A sample deployment workflow. I led the deployment."
        )
        evidence = {"organization": "Acme Corp"}

        cls_res = AnswerQualityValidator.classify_statement(text, evidence=evidence)
        assert cls_res["is_resume_supported"] is True, "Acme Corp marker must establish resume support"
        assert cls_res["is_illustrative_scenario"] is True, "Illustrative scenario recognized"
        assert cls_res["is_unsupported_personal_claim"] is True, "Outside deployment claim must be flagged"

        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(text, verified_evidence=evidence)
        assert len(issues) > 0
        assert any("led" in iss.lower() or "deployment" in iss.lower() for iss in issues)
