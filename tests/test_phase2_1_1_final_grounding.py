"""
Comprehensive Regression Test Suite for Phase 2.1.1:
Final Interview Grounding Repair & Anti-Fabrication Invariants.

Verifies all 12 Phase 2.1.1 requirements:
1. Project with only title and technologies.
2. Project with genuine implementation description.
3. Internship containing only organization and title (NO responsibilities).
4. Internship with documented responsibilities.
5. Missing testing evidence (no ungrounded test base claims).
6. Missing deployment evidence (no ungrounded deployment/merge claims).
7. Missing metrics and outcomes (no unbracketed metric fabrications).
8. Follow-up questions containing hypothetical scenarios clearly labeled.
9. Candidate-confirmed information clearly distinguished from resume evidence.
10. Unsupported first-person statements flagged across all fields.
11. All answer frameworks (STAR, CAR, PAR, SOAR, PEEL, PREP) remain complete and usable.
12. End-to-end question generation passes quality validation across every output field.
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


class TestPhase211FinalGroundingRepair:
    """Verifies that interview evidence mapping and guidance generation ground strictly in verified facts."""

    # -------------------------------------------------------------------------
    # 1. Project with only title and technologies
    # -------------------------------------------------------------------------
    def test_01_project_with_only_title_and_technologies(self):
        """Project with only title and technologies must not invent implementation or testing claims."""
        proj = {
            "title": "Cloud Log Aggregator",
            "technologies": ["Python", "FastAPI"],
            "description": ""
        }

        arch_ans = build_grounded_project_answers(proj, "arch")
        assert any("Project objective details not established" in ev for ev in arch_ans["verified_evidence"])
        assert "General practical development portfolio" not in arch_ans["verified_evidence"]

        # Guidance must use placeholders for missing personal information
        assert "[Candidate to specify:" in arch_ans["simpler_answer"]
        assert "[Candidate to specify:" in arch_ans["detailed_answer"]

        # No unsupported first-person personal claims
        issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(arch_ans["detailed_answer"])
        assert issues == [], f"Found unexpected issues in detailed answer: {issues}"

        # Follow-ups must not assert candidate personally maintained test suites
        for fu in arch_ans["follow_up_questions"]:
            fu_issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(fu["reference_answer"])
            assert fu_issues == [], f"Found unexpected issues in follow-up: {fu_issues}"

    # -------------------------------------------------------------------------
    # 2. Project with genuine implementation description
    # -------------------------------------------------------------------------
    def test_02_project_with_genuine_implementation_description(self):
        """Project with genuine implementation description preserves exact excerpt and adds zero fabrications."""
        exact_desc = "Engineered asynchronous Kafka ingestion consumer processing 10k events/sec with Redis caching."
        proj = {
            "title": "Event Ingestion Pipeline",
            "technologies": ["Python", "Kafka", "Redis"],
            "description": exact_desc
        }

        roadblock_ans = build_grounded_project_answers(proj, "roadblock")
        assert any(exact_desc in ev for ev in roadblock_ans["verified_evidence"])

        star_notes = ground_guidance_in_evidence("STAR", "project", proj)
        assert exact_desc in star_notes["Situation"]

        # Validator check
        val = AnswerQualityValidator.validate_answer({
            "question_text": "Describe a major technical challenge you encountered while building Event Ingestion Pipeline.",
            "detailed_answer": roadblock_ans["detailed_answer"],
            "short_answer": roadblock_ans["short_answer"],
            "step_by_step_explanation": roadblock_ans["step_by_step_explanation"],
            "follow_up_questions": roadblock_ans["follow_up_questions"],
            "category": "B",
            "why_this_works": roadblock_ans["why_this_works"],
            "simpler_answer": roadblock_ans["simpler_answer"]
        })
        assert val["is_valid"] is True, f"Validation issues: {val['issues']}"

    # -------------------------------------------------------------------------
    # 3. Internship containing only organization and title (NO responsibilities)
    # -------------------------------------------------------------------------
    def test_03_internship_with_only_organization_and_title_no_responsibilities(self):
        """Never replaces missing responsibilities with generic positive statements like 'software engineering duties'."""
        internship = {
            "organization": "Acme Software Corp",
            "position": "Junior Intern",
            "dates": "Summer 2024",
            "technologies": [],
            "responsibilities": []
        }

        # Check all three internship question kinds: resp, learn, solve
        for kind in ["resp", "learn", "solve"]:
            ans = build_grounded_internship_answers(internship, kind)

            # Must NEVER use generic fallback 'software engineering duties' or 'software development duties'
            all_text = " ".join([
                ans["short_answer"],
                ans["detailed_answer"],
                ans["examples"],
                " ".join(ans["verified_evidence"]),
                " ".join(s["complete_explanation"] for s in ans["step_by_step_explanation"]),
                " ".join(fu["reference_answer"] for fu in ans["follow_up_questions"])
            ])
            assert "software engineering duties" not in all_text.lower()
            assert "software development duties" not in all_text.lower()

            # Must explicitly note that responsibilities are not established
            assert any("Internship responsibilities not established" in ev for ev in ans["verified_evidence"])

            # Check that examples field does not claim fabricated duties
            assert "completed practical duties (software engineering duties)" not in ans["examples"]

            # Must pass validator with zero issues
            issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(ans["detailed_answer"])
            assert issues == [], f"Found issues in {kind} detailed answer: {issues}"

    # -------------------------------------------------------------------------
    # 4. Internship with documented responsibilities
    # -------------------------------------------------------------------------
    def test_04_internship_with_documented_responsibilities(self):
        """Internship with documented responsibilities preserves them in evidence and guidance."""
        internship = {
            "organization": "DataFlow Labs",
            "position": "Backend Intern",
            "dates": "Jan 2024 - Jun 2024",
            "technologies": ["Python", "FastAPI", "PostgreSQL"],
            "responsibilities": [
                "Built REST endpoints for customer profile management",
                "Optimized database indexing for profile search queries"
            ]
        }

        ans = build_grounded_internship_answers(internship, "resp")
        assert any("Built REST endpoints for customer profile management" in ev for ev in ans["verified_evidence"])
        assert "Built REST endpoints for customer profile management" in ans["detailed_answer"]
        assert "DataFlow Labs" in ans["examples"]

    # -------------------------------------------------------------------------
    # 5. Missing testing evidence
    # -------------------------------------------------------------------------
    def test_05_missing_testing_evidence(self):
        """When testing evidence is missing, answers must not assert ungrounded personal test maintenance."""
        proj = {
            "title": "Minimal Script",
            "technologies": ["Python"],
            "description": "Script that converts CSV files to JSON format."
        }

        eval_ans = build_grounded_project_answers(proj, "eval")
        # Must not claim candidate maintained an extensive base of unit tests
        assert "We maintain an extensive base of unit tests" not in eval_ans["detailed_answer"]
        for fu in eval_ans["follow_up_questions"]:
            assert "We maintain an extensive base of unit tests" not in fu["reference_answer"]
            assert "I authored automated unit tests" not in fu["reference_answer"]

        # Testing guidance must be pedagogical or marked as illustrative scenario
        fu1 = eval_ans["follow_up_questions"][0]
        assert "[Illustrative Scenario — Not candidate resume data]:" in fu1["reference_answer"]
        assert "[Candidate to specify:" in fu1["reference_answer"]

    # -------------------------------------------------------------------------
    # 6. Missing deployment evidence
    # -------------------------------------------------------------------------
    def test_06_missing_deployment_evidence(self):
        """When deployment evidence is missing, answers must not assert ungrounded production merge or deployment."""
        internship = {
            "organization": "Startup Alpha",
            "position": "Web Developer",
            "dates": "2023",
            "technologies": ["React", "JavaScript"],
            "responsibilities": ["Created UI mockups and prototypes"]
        }

        ans = build_grounded_internship_answers(internship, "resp")
        assert "Successfully merged high-quality code" not in ans["detailed_answer"]
        assert "My pull requests were reviewed, approved, and merged" not in ans["detailed_answer"]

        # Step 6 concrete example must use a candidate placeholder rather than claiming actual production merge
        step6 = ans["step_by_step_explanation"][5]
        assert "[Candidate to specify:" in step6["concrete_example"]

    # -------------------------------------------------------------------------
    # 7. Missing metrics and outcomes
    # -------------------------------------------------------------------------
    def test_07_missing_metrics_and_outcomes(self):
        """Missing metrics must never be replaced with unbracketed fabricated numbers or percentages."""
        internship = {
            "organization": "Beta Tech",
            "position": "Intern",
            "dates": "2023",
            "technologies": ["Python"],
            "responsibilities": ["Assisted with script refactoring"]
        }

        solve_ans = build_grounded_internship_answers(internship, "solve")
        # Follow-up 3 had an unbracketed "40%" time reduction previously; verify it is bracketed or removed
        fu3 = solve_ans["follow_up_questions"][2]
        assert "reducing total development time by at least 40%" not in fu3["reference_answer"]
        assert "under 0.3 milliseconds per payload" not in fu3["reference_answer"]

        # Validate answer should pass with zero metric issues
        val = AnswerQualityValidator.validate_answer({
            "question_text": "Can you walk me through a specific engineering problem you solved?",
            "detailed_answer": solve_ans["detailed_answer"],
            "short_answer": solve_ans["short_answer"],
            "step_by_step_explanation": solve_ans["step_by_step_explanation"],
            "follow_up_questions": solve_ans["follow_up_questions"],
            "category": "C",
            "why_this_works": solve_ans["why_this_works"],
            "simpler_answer": solve_ans["simpler_answer"]
        })
        assert val["is_valid"] is True, f"Validation issues: {val['issues']}"

    # -------------------------------------------------------------------------
    # 8. Follow-up questions containing hypothetical scenarios clearly labeled
    # -------------------------------------------------------------------------
    def test_08_follow_up_questions_hypothetical_scenarios_clearly_labeled(self):
        """All follow-up questions containing hypothetical scenarios must be clearly labeled."""
        internship = {
            "organization": "Tech Innovations Inc",
            "position": "Software Engineering Intern",
            "dates": "Summer 2023",
            "technologies": ["Python", "Git", "Docker"],
            "responsibilities": ["Refactored backend microservices"]
        }

        for kind in ["resp", "learn", "solve"]:
            ans = build_grounded_internship_answers(internship, kind)
            assert len(ans["follow_up_questions"]) == 3
            for idx, fu in enumerate(ans["follow_up_questions"]):
                ref = fu["reference_answer"]
                assert "[Illustrative Scenario — Not candidate resume data]:" in ref, (
                    f"Follow-up {idx+1} for {kind} missing illustrative label: {ref}"
                )
                assert "[Candidate to specify:" in ref, (
                    f"Follow-up {idx+1} for {kind} missing candidate placeholder: {ref}"
                )
                assert fu["technical_justification"]
                assert fu["practical_example"]
                assert fu["interview_takeaway"]

    # -------------------------------------------------------------------------
    # 9. Candidate-confirmed information clearly distinguished from resume evidence
    # -------------------------------------------------------------------------
    def test_09_candidate_confirmed_information_clearly_distinguished(self):
        """Candidate confirmations must be categorized separately and never treated as resume evidence."""
        # 1. Candidate confirmed statement
        cand_text = "[Candidate Confirmed: Built Postgres schemas and optimized queries]"
        res_cand = AnswerQualityValidator.classify_statement(cand_text)
        assert res_cand["is_candidate_confirmed"] is True
        assert res_cand["is_resume_supported"] is False  # Must NOT be counted as resume evidence

        # 2. Resume supported statement
        resume_text = "Verified Organization: Google"
        res_resume = AnswerQualityValidator.classify_statement(resume_text, evidence={"organization": "Google"})
        assert res_resume["is_resume_supported"] is True
        assert res_resume["is_candidate_confirmed"] is False

        # 3. Illustrative scenario
        scenario_text = "[Illustrative Scenario — Not candidate resume data]: In production code reviews..."
        res_scenario = AnswerQualityValidator.classify_statement(scenario_text)
        assert res_scenario["is_illustrative_scenario"] is True
        assert res_scenario["is_resume_supported"] is False

        # 4. Missing personal placeholder
        placeholder_text = "[Candidate to specify: Specific deliverable at company]"
        res_placeholder = AnswerQualityValidator.classify_statement(placeholder_text)
        assert res_placeholder["is_missing_info_placeholder"] is True

        # 5. General technical statement
        tech_text = "Modular architecture decouples domain logic from persistence adapters."
        res_tech = AnswerQualityValidator.classify_statement(tech_text)
        assert res_tech["is_general_technical"] is True

    # -------------------------------------------------------------------------
    # 10. Unsupported first-person statements flagged across all fields
    # -------------------------------------------------------------------------
    def test_10_unsupported_first_person_statements_flagged_across_all_fields(self):
        """Validator must catch unsupported personal assertions in detailed answer, steps, and follow-ups."""
        # Record with forbidden claim in detailed answer
        bad_record_1 = {
            "question_text": "What did you do during your internship?",
            "detailed_answer": "At Acme Corp, I designed modular software components and deployed them to production.",
            "short_answer": "I worked on software components.",
            "step_by_step_explanation": [{"step": "Step 1", "complete_explanation": "Explained.", "concrete_example": "Example."}] * 3,
            "category": "C"
        }
        val1 = AnswerQualityValidator.validate_answer(bad_record_1)
        assert val1["is_valid"] is False
        assert any("modular component design" in issue for issue in val1["issues"])

        # Record with forbidden claim in follow-up answer
        bad_record_2 = {
            "question_text": "What did you learn?",
            "detailed_answer": "A pedagogical overview of engineering practices. " * 3,
            "short_answer": "Learned professional practices.",
            "step_by_step_explanation": [{"step": f"Step {i}", "complete_explanation": "Explanation.", "concrete_example": "[Candidate to specify: ...]"} for i in range(3)],
            "follow_up_questions": [
                {
                    "question": "What feedback did you receive?",
                    "reference_answer": "A senior engineer commented: Catching generic Exception masks bugs in our code.",
                    "technical_justification": "Justification.",
                    "practical_example": "Example.",
                    "interview_takeaway": "Takeaway."
                }
            ],
            "category": "C",
            "why_this_works": "Why it works.",
            "simpler_answer": "Simpler answer."
        }
        val2 = AnswerQualityValidator.validate_answer(bad_record_2)
        assert val2["is_valid"] is False
        assert any("Follow-up 1" in issue for issue in val2["issues"])

        # Record with forbidden generic fallback 'software engineering duties'
        bad_record_3 = {
            "question_text": "Describe your tasks.",
            "detailed_answer": "I completed software engineering duties using Python and Git.",
            "short_answer": "Completed software engineering duties.",
            "step_by_step_explanation": [{"step": f"Step {i}", "complete_explanation": "Explanation.", "concrete_example": "[Candidate to specify: ...]"} for i in range(3)],
            "category": "C"
        }
        val3 = AnswerQualityValidator.validate_answer(bad_record_3)
        assert val3["is_valid"] is False
        assert any("software engineering duties" in issue for issue in val3["issues"])

    # -------------------------------------------------------------------------
    # 11. All answer frameworks remain complete and usable
    # -------------------------------------------------------------------------
    def test_11_all_answer_frameworks_remain_complete_and_usable(self):
        """Verifies that all 6 answer frameworks format valid guidance without fabrication."""
        proj = {"title": "Portfolio Web App", "technologies": ["React", "TypeScript"], "description": ""}
        intern = {"organization": "Tech Corp", "position": "Developer Intern", "dates": "2023", "technologies": ["Go"], "responsibilities": []}

        for fw in ["STAR", "CAR", "PAR", "SOAR", "PEEL", "PREP"]:
            proj_notes = ground_guidance_in_evidence(fw, "project", proj)
            proj_tmpl = format_answer_template(fw, proj_notes)
            assert isinstance(proj_tmpl, list)
            assert len(proj_tmpl) >= 3
            for item in proj_tmpl:
                placeholder = item.get("placeholder", "")
                assert placeholder
                assert "software engineering duties" not in placeholder.lower()
                assert "software development duties" not in placeholder.lower()

            intern_notes = ground_guidance_in_evidence(fw, "internship", intern)
            intern_tmpl = format_answer_template(fw, intern_notes)
            assert isinstance(intern_tmpl, list)
            assert len(intern_tmpl) >= 3
            for item in intern_tmpl:
                placeholder = item.get("placeholder", "")
                assert placeholder
                assert "software engineering duties" not in placeholder.lower()
                assert "software development duties" not in placeholder.lower()

    # -------------------------------------------------------------------------
    # 12. End-to-end question generation passes quality validation across every output field
    # -------------------------------------------------------------------------
    def test_12_end_to_end_question_generation_passes_quality_validation(self):
        """End-to-end question generation across all categories passes quality audit with 100% validity."""
        resume_payload = {
            "target_role": "Backend Engineer",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
            "missing_skills": ["AWS", "Kubernetes"],
            "required_skills": ["AWS", "Kubernetes", "Python"],
            "projects": [
                {
                    "title": "API Microservice",
                    "technologies": ["Python", "FastAPI"],
                    "description": ""  # No implementation details
                }
            ],
            "experience": [
                {
                    "organization": "CloudScale Inc",
                    "position": "Software Engineering Intern",
                    "dates": "Summer 2024",
                    "technologies": ["Docker", "Git"],
                    "responsibilities": []  # No responsibilities specified
                }
            ],
            "education": [
                {
                    "institution": "State University",
                    "degree": "B.S. Computer Science",
                    "graduation_year": "2024"
                }
            ]
        }

        generator = InterviewQuestionGenerator(resume_payload)
        questions = generator.generate_questions(category="ALL", max_questions=30)

        assert len(questions) >= 10
        categories_found = set()

        for q in questions:
            categories_found.add(q["category"])

            # 1. Quality validation audit
            validation = AnswerQualityValidator.validate_answer(q)
            assert validation["is_valid"] is True, (
                f"Question {q['question_id']} ({q['category']}) failed validation: {validation['issues']}"
            )
            assert validation["quality_score"] >= 80.0

            # 2. Strict anti-fabrication assertions
            detailed = q.get("detailed_answer", "")
            simpler = q.get("simpler_answer", "")
            examples = q.get("examples", "")
            all_text = f"{detailed} {simpler} {examples}"

            assert "software engineering duties" not in all_text.lower()
            assert "software development duties" not in all_text.lower()

            # 3. Follow-up answers audit
            for fu in q.get("follow_up_questions", []):
                ref_ans = fu.get("reference_answer", "")
                fu_issues = AnswerQualityValidator.audit_answer_for_unsupported_first_person_claims(ref_ans)
                assert fu_issues == [], (
                    f"Question {q['question_id']} follow-up failed audit: {fu_issues}\nRef: {ref_ans}"
                )

        assert "A" in categories_found
        assert "B" in categories_found
        assert "C" in categories_found
        assert "D" in categories_found
