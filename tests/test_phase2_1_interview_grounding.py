"""
Comprehensive Regression Test Suite for Phase 2.1:
Interview Evidence Grounding Correction & Anti-Fabrication Invariants.

Verifies:
1. Project with a title and technology list but no implementation description.
2. Project with a genuine implementation description.
3. Project with no testing evidence.
4. Missing education and experience data (honest fallbacks).
5. Missing personal metrics and outcomes.
6. Detection and elimination of unsupported first-person claims.
7. Candidate-confirmed facts clearly distinguished from resume evidence.
8. Usability and schema consistency of existing STAR/CAR/PAR/SOAR/PEEL/PREP answer frameworks.
9. Grounded internship guidance with pedagogical steps and zero ungrounded first-person claims.
10. Full question generation audit passing AnswerQualityValidator with zero unsupported claims.
"""

import pytest
from typing import Dict, Any

from src.interview.evidence_mapper import (
    extract_candidate_evidence,
    ground_guidance_in_evidence,
    build_grounded_project_answers,
    build_grounded_internship_answers,
)
from src.interview.answer_validator import AnswerQualityValidator
from src.interview.answer_frameworks import format_answer_template, get_framework, FRAMEWORKS
from src.interview.question_generator import InterviewQuestionGenerator


class TestInterviewEvidenceGrounding:
    """Verifies that interview evidence mapping and guidance generation ground strictly in verified facts."""

    # -------------------------------------------------------------------------
    # 1. Project with title & tech stack but NO implementation description
    # -------------------------------------------------------------------------
    def test_01_project_with_no_implementation_description(self):
        """1. Project with a title and technology list but no implementation description."""
        proj = {
            "title": "Network Log Analyzer",
            "technologies": ["Python", "Pandas"],
            "description": ""
        }

        # STAR guidance
        star_notes = ground_guidance_in_evidence("STAR", "project", proj)
        assert "Situation" in star_notes
        assert "Action" in star_notes
        assert "Result" in star_notes
        assert "Task" in star_notes

        # Must NOT claim production-grade implementation or ungrounded actions
        full_star_text = " ".join(star_notes.values())
        assert "developed as a production-grade software solution" not in full_star_text
        assert "I designed modular software components" not in full_star_text
        assert "I implemented modular services" not in full_star_text
        assert "I authored automated unit tests" not in full_star_text
        assert "The completed service verified functional requirements" not in full_star_text
        assert "The completed system satisfied all acceptance criteria" not in full_star_text

        # Must explicitly flag missing details with placeholders
        assert "[Candidate to specify:" in star_notes["Situation"]
        assert "[Candidate to specify:" in star_notes["Action"]
        assert "[Candidate to specify:" in star_notes["Result"]

        # Generated project answers
        arch_ans = build_grounded_project_answers(proj, "arch")
        assert "General practical development portfolio" not in arch_ans["verified_evidence"]
        assert any("Project objective details not established" in ev for ev in arch_ans["verified_evidence"])
        assert "I designed a modular layered architecture" not in arch_ans["simpler_answer"]
        assert "I deliberately chose a modular monolithic architecture" not in arch_ans["detailed_answer"]

        # Quality audit must pass with 0 unsupported personal assertions
        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(arch_ans["detailed_answer"])
        assert issues == [], f"Found unexpected issues: {issues}"

    # -------------------------------------------------------------------------
    # 2. Project with a genuine implementation description
    # -------------------------------------------------------------------------
    def test_02_project_with_genuine_implementation_description(self):
        """2. Project with a genuine implementation description."""
        exact_desc = "Built gRPC endpoints for order catalog and containerized the service using Docker."
        proj = {
            "title": "E-Commerce Microservice",
            "technologies": ["Go", "gRPC", "Docker"],
            "description": exact_desc
        }

        # STAR guidance must preserve exact excerpt
        star_notes = ground_guidance_in_evidence("STAR", "project", proj)
        assert exact_desc in star_notes["Situation"]

        # CAR guidance must preserve exact excerpt
        car_notes = ground_guidance_in_evidence("CAR", "project", proj)
        assert exact_desc in car_notes["Challenge"]

        # Project answers must preserve verified objective in evidence
        arch_ans = build_grounded_project_answers(proj, "arch")
        assert any(exact_desc in ev for ev in arch_ans["verified_evidence"])

        # Steps must connect to genuine functional scope
        step1 = arch_ans["step_by_step_explanation"][0]
        assert "order catalog" in step1["complete_explanation"] or "gRPC" in step1["complete_explanation"] or "Docker" in step1["complete_explanation"]

        # Quality audit must pass
        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(arch_ans["detailed_answer"])
        assert issues == []

    # -------------------------------------------------------------------------
    # 3. Project with NO testing evidence
    # -------------------------------------------------------------------------
    def test_03_project_with_no_testing_evidence(self):
        """3. Project with no testing evidence must not claim unit tests were authored."""
        proj = {
            "title": "Sensor Telemetry Pipeline",
            "technologies": ["Python", "Kafka"],
            "description": "Engineered data ingestion pipeline for real-time sensor telemetry."
        }

        evidence = extract_candidate_evidence({
            "projects": [proj],
            "skills": ["Python", "Kafka"]
        })
        cleaned_p = evidence["projects"][0]
        assert cleaned_p["has_testing_evidence"] is False

        # Framework guidance must not assert automated testing was performed
        star_notes = ground_guidance_in_evidence("STAR", "project", cleaned_p)
        assert "authoring automated unit tests" not in star_notes["Action"]
        assert "passing automated test suites" not in star_notes["Result"]
        assert "reproducible test execution" not in star_notes["Result"]

        # Project arch answer must not assert the candidate personally tested in isolation
        arch_ans = build_grounded_project_answers(cleaned_p, "arch")
        assert "I authored automated unit tests" not in arch_ans["detailed_answer"]
        assert "passing automated test suites with verified test execution" not in arch_ans["detailed_answer"]

    # -------------------------------------------------------------------------
    # 4. Missing education and experience data (honest defaults)
    # -------------------------------------------------------------------------
    def test_04_missing_education_and_experience_data(self):
        """4. Missing education and experience data must return honest values, not positive claims."""
        # A. None input
        ev_none = extract_candidate_evidence(None)
        assert ev_none["education"] == "Education details not established from available resume data."
        assert ev_none["experience_summary"] == "Professional experience not established from available resume data."
        assert ev_none["education"] != "Verified against degree mentions in parsed resume."
        assert ev_none["experience_summary"] != "Professional experience verified"

        # B. Empty dict input
        ev_empty = extract_candidate_evidence({})
        assert ev_empty["education"] == "Education details not established from available resume data."
        assert ev_empty["experience_summary"] == "Professional experience not established from available resume data."

        # C. Partial analysis with skills only
        ev_partial = extract_candidate_evidence({
            "skills": ["Python", "SQL"],
            "projects": []
        })
        assert ev_partial["education"] == "Education details not established from available resume data."
        assert ev_partial["experience_summary"] == "Professional experience not established from available resume data."

        # D. Genuine degree provided
        ev_degree = extract_candidate_evidence({
            "skills": ["Python"],
            "education_analysis": {"notes": "Bachelor of Technology in Computer Science"}
        })
        assert "Bachelor of Technology" in ev_degree["education"]

    # -------------------------------------------------------------------------
    # 5. Missing personal metrics and outcomes
    # -------------------------------------------------------------------------
    def test_05_missing_personal_metrics_and_outcomes(self):
        """5. Projects without numbers/metrics must prompt with placeholders rather than inventing percentages."""
        proj = {
            "title": "Batch Image Resizer",
            "technologies": ["Python", "PIL"],
            "description": "Script that resizes images in a directory."
        }

        evidence = extract_candidate_evidence({"projects": [proj]})
        cleaned_p = evidence["projects"][0]
        assert cleaned_p["has_metrics_evidence"] is False

        star_notes = ground_guidance_in_evidence("STAR", "project", cleaned_p)
        # Result must be a placeholder for the candidate to fill in their actual metric
        assert "[Candidate to specify:" in star_notes["Result"]
        assert "latency" in star_notes["Result"].lower() or "throughput" in star_notes["Result"].lower() or "metric" in star_notes["Result"].lower()

        # Must not fabricate fake metrics
        assert "45%" not in star_notes["Result"]
        assert "99.9%" not in star_notes["Result"]
        assert "satisfied all acceptance criteria with reproducible builds" not in star_notes["Result"]

        # Project answer missing_personal_details must list quantitative throughput
        arch_ans = build_grounded_project_answers(cleaned_p, "arch")
        assert len(arch_ans["missing_personal_details"]) > 0

    # -------------------------------------------------------------------------
    # 6. Interview answers containing unsupported first-person claims
    # -------------------------------------------------------------------------
    def test_06_unsupported_first_person_claims_detected_and_prevented(self):
        """6. Flags unbracketed assertions and confirms newly generated guidance is free of them."""
        # A. Verify validator detects forbidden claims when unbracketed
        bad_texts = [
            "In my project, I designed modular software components across Flask and PostgreSQL.",
            "During sprint 1, I implemented modular services with automated error handling.",
            "To guarantee quality, I authored automated unit tests for edge cases.",
            "The completed service verified functional requirements with reproducible builds.",
            "The completed system satisfied all acceptance criteria with reproducible builds.",
            "I authored modular feature code using Python and created unit and integration test fixtures.",
            "My pull requests were reviewed, approved, and merged into the main development branch.",
            "Successfully merged high-quality code into production repositories, fulfilling sprint deliverables."
        ]

        for bad in bad_texts:
            issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(bad)
            assert len(issues) > 0, f"Validator failed to flag forbidden assertion: '{bad}'"

        # B. Verify newly generated guidance in evidence_mapper produces ZERO issues
        p = {
            "title": "Recommendation Engine",
            "technologies": ["Python", "Scikit-Learn"],
            "description": "Built collaborative filtering recommendation engine."
        }
        for q_kind in ["arch", "roadblock", "eval", "scale"]:
            ans = build_grounded_project_answers(p, q_kind)
            issues_det = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(ans["detailed_answer"])
            issues_simp = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(ans["simpler_answer"])
            assert issues_det == [], f"Found issues in {q_kind} detailed answer: {issues_det}"
            assert issues_simp == [], f"Found issues in {q_kind} simpler answer: {issues_simp}"

    # -------------------------------------------------------------------------
    # 7. Candidate-confirmed fact clearly distinguished from resume evidence
    # -------------------------------------------------------------------------
    def test_07_candidate_confirmed_fact_distinguished_from_resume_evidence(self):
        """7. A candidate-confirmed fact is clearly distinguished from parsed resume evidence."""
        confirmed_fact = "Architected Redis caching tier and reduced query count by 60%"
        proj = {
            "title": "Analytics Dashboard",
            "technologies": ["Python", "PostgreSQL"],
            "description": "Web dashboard displaying sales metrics.",
            "user_confirmed": True,
            "confirmed_details": confirmed_fact
        }

        # STAR guidance must include explicit [Candidate Confirmed: ...] label
        star_notes = ground_guidance_in_evidence("STAR", "project", proj)
        assert f"[Candidate Confirmed: {confirmed_fact}]" in star_notes["Situation"]
        assert f"[Candidate Confirmed Objective: {confirmed_fact}]" in star_notes["Task"]

        # Verified evidence in project answers must separate resume objective from candidate confirmation
        ans = build_grounded_project_answers(proj, "arch")
        ev_list = ans["verified_evidence"]
        assert any("Verified Project Objective: 'Web dashboard displaying sales metrics.'" in ev for ev in ev_list)
        assert any(f"Candidate Confirmed Details: '{confirmed_fact}'" in ev for ev in ev_list)

        # Validator should not flag [Candidate Confirmed: ...] as ungrounded
        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
            f"Context: {star_notes['Situation']} [Candidate to specify: Action]"
        )
        assert issues == []

    # -------------------------------------------------------------------------
    # 8. Existing valid STAR/CAR answer structure remains usable
    # -------------------------------------------------------------------------
    def test_08_existing_answer_frameworks_usable_and_complete(self):
        """8. Existing valid STAR/CAR/PAR/SOAR/PEEL/PREP answer structure remains usable."""
        proj = {
            "title": "Distributed Task Scheduler",
            "technologies": ["Go", "Redis", "Docker"],
            "description": "Constructed asynchronous worker pool for job execution."
        }

        # Check all frameworks return valid expected step keys
        framework_keys = {
            "STAR": ["Situation", "Task", "Action", "Result"],
            "STAR+L": ["Situation", "Task", "Action", "Result", "Learning"],
            "CAR": ["Challenge", "Action", "Result"],
            "PAR": ["Problem", "Action", "Result"],
            "SOAR": ["Situation", "Obstacles", "Actions", "Results"],
            "PEEL": ["Point", "Evidence", "Explanation", "Link"],
            "PREP": ["Point", "Reason", "Example", "Point_Conclusion"],
            "WHAT-WHY-HOW": ["What", "Why", "How"],
        }

        for fw_id, expected_keys in framework_keys.items():
            notes = ground_guidance_in_evidence(fw_id, "project", proj)
            for k in expected_keys:
                assert k in notes, f"Framework {fw_id} missing expected key '{k}'"
                assert len(notes[k]) > 10, f"Framework {fw_id} key '{k}' has empty or stub content"

            # Verify format_answer_template consumes notes seamlessly
            template = format_answer_template(fw_id, notes)
            assert len(template) == len(expected_keys)
            for step in template:
                assert step["placeholder"] == notes[step["key"]]

    # -------------------------------------------------------------------------
    # 9. Grounded internship guidance with pedagogical steps
    # -------------------------------------------------------------------------
    def test_09_internship_evidence_grounding_no_unsupported_claims(self):
        """9. Internship answers explain principles pedagogically without inventing solo actions."""
        internship = {
            "organization": "Nexus Cloud Technologies",
            "position": "Backend Intern",
            "dates": "Summer 2024",
            "technologies": ["Python", "FastAPI"],
            "responsibilities": ["Maintained REST API endpoints and authored documentation."]
        }

        # STAR guidance for internship
        star_notes = ground_guidance_in_evidence("STAR", "internship", internship)
        assert "Nexus Cloud Technologies" in star_notes["Situation"]
        assert "Maintained REST API endpoints" in star_notes["Situation"]
        assert "[Candidate to specify:" in star_notes["Action"]
        assert "[Candidate to specify:" in star_notes["Result"]

        # Must not claim PR was automatically approved and merged without regression
        assert "My pull requests were reviewed, approved, and merged into the main development branch" not in star_notes["Result"]

        # Pedagogical steps in answers
        for q_kind in ["resp", "learn", "solve"]:
            ans = build_grounded_internship_answers(internship, q_kind)
            assert len(ans["step_by_step_explanation"]) >= 5
            # Ensure explanations avoid personal first-person assertions
            for st in ans["step_by_step_explanation"]:
                assert "I created a dedicated Git feature branch" not in st["complete_explanation"]
                assert "I authored comprehensive unit tests" not in st["complete_explanation"]
                assert "I submitted a clean pull request" not in st["complete_explanation"]
                assert "I learned to choose descriptive" not in st["complete_explanation"]

            issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(ans["detailed_answer"])
            assert issues == [], f"Found issues in internship {q_kind}: {issues}"

    # -------------------------------------------------------------------------
    # 10. End-to-end question generation passes quality validation
    # -------------------------------------------------------------------------
    def test_10_end_to_end_question_generator_passes_quality_audit(self):
        """10. End-to-end question generator outputs pass AnswerQualityValidator with zero unsupported claims."""
        analysis_data = {
            "analysis_id": "test_phase2_1_analysis",
            "filename": "candidate_profile.pdf",
            "job_title": "Full Stack Engineer",
            "projects": [
                {
                    "title": "Inventory Management Portal",
                    "technologies": ["React", "TypeScript", "Node.js", "PostgreSQL"],
                    "description": "Developed real-time inventory tracking application."
                }
            ],
            "internships": [
                {
                    "organization": "DataFlow Systems",
                    "position": "Software Engineering Intern",
                    "dates": "January 2024 - April 2024",
                    "technologies": ["Python", "PostgreSQL"],
                    "responsibilities": ["Developed data transformation routines and optimized SQL queries."]
                }
            ],
            "skills": ["React", "TypeScript", "Node.js", "Python", "PostgreSQL", "Docker"],
            "matched_skills": ["React", "TypeScript", "Python"],
            "missing_skills": ["AWS", "Kubernetes"],
            "required_skills": ["React", "TypeScript", "Python", "PostgreSQL"],
            "preferred_skills": ["AWS", "Kubernetes"],
            "education_analysis": {"notes": "Bachelor of Technology in Computer Science"},
            "experience_summary": {"display_summary": "1 Internship, 1 Project"}
        }

        generator = InterviewQuestionGenerator(analysis_data)
        all_qs = generator.generate_questions(category="ALL", max_questions=25)
        assert len(all_qs) >= 15

        for q in all_qs:
            validation = AnswerQualityValidator.validate_answer(q)
            assert validation["is_valid"] is True, (
                f"Question {q.get('question_id')} ({q.get('category')}) failed validation: {validation['issues']}"
            )
            # Ensure no unsupported first-person claims in detailed answer
            fp_issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(
                q.get("detailed_answer", "")
            )
            assert fp_issues == [], f"Question {q.get('question_id')} has unsupported claims: {fp_issues}"
