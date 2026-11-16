"""
Phase 2.1.2: Evidence Validator & Final Output Audit Regression Test Suite.
Verifies:
1. Internship with organization and title only: Verified organization and title established,
   responsibilities and tools NOT established, explicit placeholders, no positive fallbacks in any field.
2. Internship with no responsibilities and no technologies: Verified organization, title, and dates established;
   responsibilities and tools NOT established; explicit placeholders; no positive fallbacks.
3. Project with title and technologies only: Verified project title and tech stack established;
   architecture, design rationale, component design, testing, and deployment NOT established;
   examples field cleanly placeholder-bounded.
4. Project with genuine description: Genuine excerpt preserved as evidence; no added claims beyond
   the excerpt; architecture, testing, and deployment remain unbounded unless explicitly in excerpt.
5. Unsupported architecture claims: Flagged by validator across all fields.
6. Unsupported implementation claims: Flagged by validator across all fields.
7. Unsupported testing and deployment claims: Flagged by validator when unevidenced.
8. Candidate-confirmed facts remain separate from resume evidence: Distinct classification tags.
9. General technical explanations remain valid: Educational and pedagogical explanations pass validation.
10. Unsupported first-person claims in every relevant output field: Verification that validator checks all 13 fields.
11. All six answer frameworks remain usable: STAR, CAR, PAR, SOAR, PEEL, PREP produce complete, valid output.
12. End-to-end generation and validation: All categories (A, B, C, D) pass with is_valid=True and quality_score >= 80.
"""

import copy
import pytest
from typing import Dict, Any, List

from src.interview.evidence_mapper import (
    build_grounded_project_answers,
    build_grounded_internship_answers,
    ground_guidance_in_evidence
)
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.answer_validator import AnswerQualityValidator
from src.interview.answer_frameworks import (
    build_completed_framework_demonstration,
    format_answer_template
)


FORBIDDEN_FALLBACKS = [
    "software development tasks",
    "assigned engineering features",
    "practical engineering tools",
    "software engineering duties",
    "software development duties"
]


def assert_no_forbidden_fallbacks(data: Any, path: str = "root"):
    """Recursively checks that no forbidden positive fallbacks appear anywhere in data."""
    if isinstance(data, str):
        for fb in FORBIDDEN_FALLBACKS:
            assert fb not in data.lower(), (
                f"Forbidden fallback '{fb}' found in {path}: '{data}'"
            )
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            assert_no_forbidden_fallbacks(item, f"{path}[{idx}]")
    elif isinstance(data, dict):
        for k, v in data.items():
            assert_no_forbidden_fallbacks(v, f"{path}.{k}")


class TestPhase212EvidenceValidator:

    # -------------------------------------------------------------------------
    # 1. Internship with organization and title only
    # -------------------------------------------------------------------------
    def test_01_internship_with_organization_and_title_only(self):
        """
        Verified organization and title established, responsibilities and tools
        NOT established, explicit placeholders, no positive fallbacks in any field.
        """
        internship = {
            "organization": "Acme Innovations",
            "position": "Software Engineering Intern",
            "dates": "Summer 2023",
            "technologies": [],
            "responsibilities": []
        }

        for kind in ["resp", "learn", "solve"]:
            ans = build_grounded_internship_answers(internship, kind)

            # Verified facts established
            assert any("Acme Innovations" in ev for ev in ans["verified_evidence"])
            assert any("Software Engineering Intern" in ev for ev in ans["verified_evidence"])

            # Tools and responsibilities not established
            assert not any("Verified Tools:" in ev for ev in ans["verified_evidence"])
            assert not any("Verified Responsibilities:" in ev for ev in ans["verified_evidence"])

            # Explicit missing info placeholders present
            assert "[Candidate to specify:" in ans["detailed_answer"]
            assert len(ans["missing_personal_details"]) >= 1

            # No positive fallbacks in any field
            assert_no_forbidden_fallbacks(ans)

            # Must pass validator
            val = AnswerQualityValidator.validate_answer({
                "question_text": f"Tell me about your internship at {internship['organization']}.",
                "detailed_answer": ans["detailed_answer"],
                "short_answer": ans["short_answer"],
                "simpler_answer": ans["simpler_answer"],
                "step_by_step_explanation": ans["step_by_step_explanation"],
                "follow_up_questions": ans["follow_up_questions"],
                "examples": ans.get("examples"),
                "why_this_works": ans["why_this_works"],
                "category": "C",
                "verified_evidence": ans["verified_evidence"]
            })
            assert val["is_valid"] is True, f"Validation issues: {val['issues']}"
            assert val["quality_score"] >= 80.0

    # -------------------------------------------------------------------------
    # 2. Internship with no responsibilities and no technologies
    # -------------------------------------------------------------------------
    def test_02_internship_with_no_responsibilities_and_no_technologies(self):
        """
        Verified organization, title, and dates established; responsibilities and
        tools NOT established; explicit placeholders; no positive fallbacks in questions.
        """
        internship = {
            "organization": "NextGen Cloud",
            "position": "Junior Developer Intern",
            "dates": "June 2023 - August 2023",
            "technologies": [],
            "responsibilities": []
        }

        generator = InterviewQuestionGenerator({
            "target_role": "Backend Engineer",
            "experience": [internship],
            "projects": [],
            "skills": ["Python"]
        })
        c_questions = generator.generate_category_c()
        assert len(c_questions) == 3

        for q in c_questions:
            # Check question text does not claim tools
            assert "using practical engineering tools" not in q["question_text"]
            assert "using software development tasks" not in q["question_text"]
            # No forbidden fallbacks anywhere in question record
            assert_no_forbidden_fallbacks(q)

            # Must pass validator
            val = AnswerQualityValidator.validate_answer(q)
            assert val["is_valid"] is True, f"Question {q['question_id']} failed: {val['issues']}"

    # -------------------------------------------------------------------------
    # 3. Project with title and technologies only
    # -------------------------------------------------------------------------
    def test_03_project_with_title_and_technologies_only(self):
        """
        Verified project title and tech stack established; architecture, design
        rationale, component design, testing, and deployment NOT established;
        examples field cleanly placeholder-bounded.
        """
        project = {
            "title": "DistributedKV",
            "technologies": ["Go", "Raft", "gRPC"],
            "description": ""
        }

        ans_arch = build_grounded_project_answers(project, "arch")
        assert any("DistributedKV" in ev for ev in ans_arch["verified_evidence"])
        assert any("Go" in ev for ev in ans_arch["verified_evidence"])
        assert "General Technical Guidance" in ans_arch["detailed_answer"]
        assert "[General Technical Guidance]:" in ans_arch["simpler_answer"]
        assert "[Candidate to specify:" in ans_arch["detailed_answer"]

        for kind in ["arch", "tradeoff", "failure"]:
            ans = build_grounded_project_answers(project, kind)

            # examples field must NOT claim decoupled presentation from backend logic
            ex = ans.get("examples", "")
            assert "decoupled presentation from backend processing logic" not in ex
            assert "[Candidate to specify:" in ex

            # No forbidden fallbacks
            assert_no_forbidden_fallbacks(ans)

            # Must pass validator
            val = AnswerQualityValidator.validate_answer({
                "question_text": f"Walk me through the architecture of {project['title']}.",
                "detailed_answer": ans["detailed_answer"],
                "short_answer": ans["short_answer"],
                "simpler_answer": ans["simpler_answer"],
                "step_by_step_explanation": ans["step_by_step_explanation"],
                "follow_up_questions": ans["follow_up_questions"],
                "examples": ans.get("examples"),
                "why_this_works": ans["why_this_works"],
                "category": "B",
                "verified_evidence": ans["verified_evidence"]
            })
            assert val["is_valid"] is True, f"Validation issues: {val['issues']}"

    # -------------------------------------------------------------------------
    # 4. Project with genuine description
    # -------------------------------------------------------------------------
    def test_04_project_with_genuine_description(self):
        """
        Genuine excerpt preserved as evidence; no added claims beyond the excerpt;
        architecture, testing, and deployment remain unbounded unless explicitly in excerpt.
        """
        project = {
            "title": "Sentiment Analyzer",
            "technologies": ["Python", "PyTorch"],
            "description": "Built custom LSTM neural network to classify sentiment from user reviews."
        }

        ans = build_grounded_project_answers(project, "arch")

        # Excerpt preserved
        assert any("Built custom LSTM neural network" in ev for ev in ans["verified_evidence"])

        # No added claims beyond excerpt
        assert "AWS" not in ans["detailed_answer"]
        assert "Kubernetes" not in ans["detailed_answer"]
        assert "microservices" not in ans["detailed_answer"]
        assert "decoupled presentation from backend processing logic" not in ans["detailed_answer"]

        # Architecture and trade-offs remain explicit placeholders in detailed answer
        assert "Component Decomposition: [Candidate to specify:" in ans["detailed_answer"]
        assert "Trade-Off Evaluation: [Candidate to specify:" in ans["detailed_answer"]
        assert len(ans["missing_personal_details"]) >= 1

        # Validates cleanly
        val = AnswerQualityValidator.validate_answer({
            "question_text": f"Explain the architecture of {project['title']}.",
            "detailed_answer": ans["detailed_answer"],
            "short_answer": ans["short_answer"],
            "simpler_answer": ans["simpler_answer"],
            "step_by_step_explanation": ans["step_by_step_explanation"],
            "follow_up_questions": ans["follow_up_questions"],
            "examples": ans.get("examples"),
            "why_this_works": ans["why_this_works"],
            "category": "B",
            "verified_evidence": ans["verified_evidence"]
        })
        assert val["is_valid"] is True, f"Validation issues: {val['issues']}"

    # -------------------------------------------------------------------------
    # 5. Unsupported architecture claims
    # -------------------------------------------------------------------------
    def test_05_unsupported_architecture_claims(self):
        """Validator flags unsupported architecture claims across all fields."""
        base_record = {
            "question_text": "Describe your architectural approach.",
            "detailed_answer": "Objective architectural overview with clean separation of concerns. The system isolates data persistence behind abstraction interfaces. Transport layers route network requests to isolated domain handlers.",
            "short_answer": "Separation of concerns overview.",
            "simpler_answer": "Simpler technical summary of components.",
            "curated_answer": "Curated technical explanation.",
            "why_this_works": "Modular separation ensures code maintainability.",
            "examples": "Reference pattern documentation.",
            "step_by_step_explanation": [
                {"step": f"Step {i+1}", "detail": f"Technical detail {i+1}.", "concrete_example": f"Pedagogical example {i+1}."}
                for i in range(3)
            ],
            "follow_up_questions": [
                {
                    "question": "How do you scale?",
                    "reference_answer": "Scale by horizontal replication of stateless nodes.",
                    "practical_example": "Replication example."
                }
            ],
            "completed_framework_answer": [
                {"key": "Situation", "demonstration": "Technical scenario overview."},
                {"key": "Task", "demonstration": "System requirement overview."},
                {"key": "Action", "demonstration": "Implementation steps."},
                {"key": "Result", "demonstration": "Predictable system execution."}
            ],
            "framework_template": [
                {"placeholder": "[Candidate to specify: ...]", "prompt": "Prompt", "guidance": "Guidance"}
            ],
            "suggested_improvements": ["Improve caching layer."],
            "missing_personal_details": ["[Candidate to specify: ...]"],
            "verified_evidence": ["Project: System Core"],
            "category": "B"
        }

        # Verify base record is valid
        assert AnswerQualityValidator.validate_answer(base_record)["is_valid"] is True

        # Field-by-field injection of unsupported architecture claims
        arch_claims = [
            "I designed a modular layered architecture to decouple components.",
            "I deliberately chose a modular monolithic architecture for simplicity.",
            "I designed modular software components and service interfaces.",
            "decoupled presentation from backend processing logic without baseline evidence."
        ]

        fields_to_test = [
            "detailed_answer",
            "short_answer",
            "simpler_answer",
            "curated_answer",
            "why_this_works",
            "examples"
        ]

        for field in fields_to_test:
            for claim in arch_claims:
                rec = copy.deepcopy(base_record)
                rec[field] = claim
                val = AnswerQualityValidator.validate_answer(rec)
                assert val["is_valid"] is False, f"Failed to flag architecture claim in {field}: '{claim}'"
                assert any("architecture" in iss.lower() or "modular" in iss.lower() for iss in val["issues"])

        # Test in steps
        for claim in arch_claims:
            rec = copy.deepcopy(base_record)
            rec["step_by_step_explanation"][0]["concrete_example"] = claim
            val = AnswerQualityValidator.validate_answer(rec)
            assert val["is_valid"] is False, f"Failed to flag architecture claim in steps: '{claim}'"

        # Test in follow-up
        for claim in arch_claims:
            rec = copy.deepcopy(base_record)
            rec["follow_up_questions"][0]["reference_answer"] = claim
            val = AnswerQualityValidator.validate_answer(rec)
            assert val["is_valid"] is False, f"Failed to flag architecture claim in follow-up: '{claim}'"

        # Test in completed framework answer
        for claim in arch_claims:
            rec = copy.deepcopy(base_record)
            rec["completed_framework_answer"][2]["demonstration"] = claim
            val = AnswerQualityValidator.validate_answer(rec)
            assert val["is_valid"] is False, f"Failed to flag architecture claim in framework answer: '{claim}'"

    # -------------------------------------------------------------------------
    # 6. Unsupported implementation claims
    # -------------------------------------------------------------------------
    def test_06_unsupported_implementation_claims(self):
        """Validator flags unsupported implementation claims across all fields."""
        base_record = {
            "question_text": "Explain your implementation methodology.",
            "detailed_answer": "Implementation follows deterministic software engineering practices. " * 3,
            "short_answer": "Deterministic software practices.",
            "simpler_answer": "Simpler technical summary.",
            "curated_answer": "Curated technical summary.",
            "why_this_works": "Deterministic patterns prevent unexpected race conditions.",
            "examples": "Standard library references.",
            "step_by_step_explanation": [
                {"step": f"Step {i+1}", "detail": "Implementation phase.", "concrete_example": "Objective example."}
                for i in range(3)
            ],
            "follow_up_questions": [
                {"question": "How do you handle errors?", "reference_answer": "Explicit error handling at boundaries."}
            ],
            "completed_framework_answer": [
                {"key": "What", "demonstration": "Core technical concept overview."},
                {"key": "Why", "demonstration": "Prevents runtime failures."},
                {"key": "How", "demonstration": "Systematic implementation."}
            ],
            "framework_template": [{"placeholder": "[Candidate to specify: ...]"}],
            "suggested_improvements": ["Add rate limiting."],
            "missing_personal_details": ["[Candidate to specify: ...]"],
            "verified_evidence": ["Project: DataPipeline"],
            "category": "B"
        }

        impl_claims = [
            "I implemented modular services to handle transaction processing.",
            "I implemented optimistic locking to resolve concurrency conflicts.",
            "I discovered the failure was occurring because of thread deadlocks.",
            "I refactored the module with defensive error handling patterns.",
            "I authored clean, modular code following design patterns.",
            "I authored modular feature code for the customer portal."
        ]

        for claim in impl_claims:
            # Test in detailed answer
            rec = copy.deepcopy(base_record)
            rec["detailed_answer"] = claim + " " * 40
            val = AnswerQualityValidator.validate_answer(rec)
            assert val["is_valid"] is False, f"Failed to flag implementation claim in detailed_answer: '{claim}'"

            # Test in short answer
            rec = copy.deepcopy(base_record)
            rec["short_answer"] = claim
            val = AnswerQualityValidator.validate_answer(rec)
            assert val["is_valid"] is False, f"Failed to flag implementation claim in short_answer: '{claim}'"

            # Test in completed framework answer
            rec = copy.deepcopy(base_record)
            rec["completed_framework_answer"][2]["demonstration"] = claim
            val = AnswerQualityValidator.validate_answer(rec)
            assert val["is_valid"] is False, f"Failed to flag implementation claim in completed_framework_answer: '{claim}'"

    # -------------------------------------------------------------------------
    # 7. Unsupported testing and deployment claims
    # -------------------------------------------------------------------------
    def test_07_unsupported_testing_and_deployment_claims(self):
        """Validator flags unsupported testing and deployment claims when unevidenced."""
        base_record = {
            "question_text": "How did you verify and release software?",
            "detailed_answer": "Verification requires comprehensive test automation and disciplined release pipelines. " * 3,
            "short_answer": "Automated verification and releases.",
            "simpler_answer": "Simpler overview of testing and release workflows.",
            "curated_answer": "Curated overview of testing strategies.",
            "why_this_works": "Automated verification prevents regressions in production systems.",
            "examples": "Test framework documentation.",
            "step_by_step_explanation": [
                {"step": f"Step {i+1}", "detail": "Test stage.", "concrete_example": "Pedagogical test setup."}
                for i in range(3)
            ],
            "follow_up_questions": [
                {"question": "How do you test?", "reference_answer": "Unit tests isolate module behavior."}
            ],
            "completed_framework_answer": [
                {"key": "What", "demonstration": "Verification concept."},
                {"key": "Why", "demonstration": "Prevents bugs."},
                {"key": "How", "demonstration": "Continuous integration."}
            ],
            "framework_template": [{"placeholder": "[Candidate to specify: ...]"}],
            "suggested_improvements": ["Add integration coverage."],
            "missing_personal_details": ["[Candidate to specify: ...]"],
            "verified_evidence": ["Project: WebApp"],
            "category": "B"
        }

        test_deploy_claims = [
            "I authored automated unit tests to achieve 90% code coverage.",
            "I authored comprehensive unit tests verifying all edge cases.",
            "created unit and integration test fixtures using Pytest fixtures.",
            "I committed the failing test case to establish a regression baseline.",
            "I deployed this service to AWS ECS with Docker containers.",
            "deployed to Kubernetes with Helm charts.",
            "I authored CI/CD pipelines in GitHub Actions.",
            "My pull requests were reviewed, approved, and merged into main.",
            "Successfully merged high-quality code into production."
        ]

        for claim in test_deploy_claims:
            rec = copy.deepcopy(base_record)
            rec["detailed_answer"] = claim + " " * 30
            val = AnswerQualityValidator.validate_answer(rec)
            assert val["is_valid"] is False, f"Failed to flag testing/deployment claim: '{claim}'"
            assert any(
                "test" in iss.lower() or "deploy" in iss.lower() or "merge" in iss.lower() or "pipeline" in iss.lower()
                for iss in val["issues"]
            )

        # However, if genuine evidence DOES contain the claim, it must NOT be flagged as unsupported
        rec_evidenced = copy.deepcopy(base_record)
        rec_evidenced["verified_evidence"] = ["I authored CI/CD pipelines in GitHub Actions"]
        rec_evidenced["detailed_answer"] = "I authored CI/CD pipelines in GitHub Actions to ensure build integrity. " * 3
        val_evidenced = AnswerQualityValidator.validate_answer(rec_evidenced)
        # Should not flag CI/CD pipeline authoring since evidence explicitly supports it
        assert not any("Claims ungrounded CI/CD pipeline" in iss for iss in val_evidenced["issues"])

    # -------------------------------------------------------------------------
    # 8. Candidate-confirmed facts remain separate from resume evidence
    # -------------------------------------------------------------------------
    def test_08_candidate_confirmed_facts_remain_separate_from_resume_evidence(self):
        """Candidate confirmations are correctly tagged and never counted as resume evidence."""
        confirmed_text = "[Candidate Confirmed: Contributed to REST API development using Flask]"
        classification = AnswerQualityValidator.classify_statement(confirmed_text)

        # Invariants:
        assert classification["is_candidate_confirmed"] is True
        assert classification["is_resume_supported"] is False  # Invariant: NEVER treated as resume evidence
        assert classification["is_unsupported_personal_claim"] is False
        assert classification["is_general_technical"] is False

        # Even if evidence dict is provided, candidate confirmation must NOT become resume evidence
        ev_ctx = {"description": "Contributed to REST API development using Flask"}
        classification_with_ev = AnswerQualityValidator.classify_statement(confirmed_text, evidence=ev_ctx)
        assert classification_with_ev["is_candidate_confirmed"] is True
        assert classification_with_ev["is_resume_supported"] is False

        # Resume evidence markers must classify as resume evidence
        resume_text = "Verified Organization: Acme Corp. Verified Position: Backend Intern."
        resume_classification = AnswerQualityValidator.classify_statement(resume_text)
        assert resume_classification["is_resume_supported"] is True
        assert resume_classification["is_candidate_confirmed"] is False

    # -------------------------------------------------------------------------
    # 9. General technical explanations remain valid
    # -------------------------------------------------------------------------
    def test_09_general_technical_explanations_remain_valid(self):
        """Educational and pedagogical explanations without first-person claims pass validation."""
        # Labeled guidance
        guidance_text = "[General Technical Guidance]: In relational databases, B-trees provide logarithmic lookup complexity."
        cls1 = AnswerQualityValidator.classify_statement(guidance_text)
        assert cls1["is_general_technical"] is True
        assert cls1["is_unsupported_personal_claim"] is False

        # Objective pedagogical explanation without explicit tag
        pedagogical_text = "Microservice architectures communicate via HTTP REST APIs or gRPC to decouple service lifecycles."
        cls2 = AnswerQualityValidator.classify_statement(pedagogical_text)
        assert cls2["is_general_technical"] is True
        assert cls2["is_unsupported_personal_claim"] is False

        # Arbitrary unverified personal claims must NEVER be classified as general technical content
        personal_claim = "I deployed microservices to AWS and reduced latency by 45%."
        cls3 = AnswerQualityValidator.classify_statement(personal_claim)
        assert cls3["is_general_technical"] is False  # INVARIANT: never general technical!
        assert cls3["is_unsupported_personal_claim"] is True

    # -------------------------------------------------------------------------
    # 10. Unsupported first-person claims in every relevant output field
    # -------------------------------------------------------------------------
    def test_10_unsupported_first_person_claims_in_every_relevant_output_field(self):
        """Verification that validator checks all 13 output fields."""
        base_record = {
            "question_text": "Explain standard software design principles.",
            "detailed_answer": "Software design principles prioritize modularity and low coupling across components. Independent layers communicate via well-defined contracts. Encapsulation prevents internal state leakage across module boundaries.",
            "short_answer": "Modularity and low coupling across components.",
            "simpler_answer": "Simpler technical summary of modularity.",
            "curated_answer": "Curated technical explanation of design principles.",
            "examples": "Standard pedagogical architectural diagrams.",
            "step_by_step_explanation": [
                {"step": f"Step {i+1}", "detail": f"Technical concept {i+1}.", "concrete_example": f"Concrete example {i+1}."}
                for i in range(3)
            ],
            "follow_up_questions": [
                {
                    "question": "What is high cohesion?",
                    "reference_answer": "High cohesion means related responsibilities stay together in a module."
                }
            ],
            "completed_framework_answer": [
                {"key": "What", "demonstration": "Concept definition."},
                {"key": "Why", "demonstration": "Prevents tight coupling."},
                {"key": "How", "demonstration": "Systematic design approach."}
            ],
            "framework_template": [
                {"placeholder": "[Candidate to specify: ...]", "prompt": "Prompt text", "guidance": "Guidance text"}
            ],
            "why_this_works": "Decoupled modules are easier to unit test and maintain.",
            "suggested_improvements": ["Apply interface segregation."],
            "missing_personal_details": ["[Candidate to specify: ...]"],
            "verified_evidence": ["Project: ArchitectureFramework"],
            "category": "B"
        }

        # Baseline must pass
        assert AnswerQualityValidator.validate_answer(base_record)["is_valid"] is True

        # Test each of the 13 fields with forbidden positive fallback 'software development tasks'
        fields_tested = []

        # 1. detailed_answer
        r1 = copy.deepcopy(base_record)
        r1["detailed_answer"] = "I completed software development tasks across the repository. Independent layers communicate via contracts. Encapsulation prevents state leakage."
        assert AnswerQualityValidator.validate_answer(r1)["is_valid"] is False
        fields_tested.append("detailed_answer")

        # 2. short_answer
        r2 = copy.deepcopy(base_record)
        r2["short_answer"] = "Completed assigned engineering features."
        assert AnswerQualityValidator.validate_answer(r2)["is_valid"] is False
        fields_tested.append("short_answer")

        # 3. simpler_answer
        r3 = copy.deepcopy(base_record)
        r3["simpler_answer"] = "Performed software development tasks."
        assert AnswerQualityValidator.validate_answer(r3)["is_valid"] is False
        fields_tested.append("simpler_answer")

        # 4. curated_answer
        r4 = copy.deepcopy(base_record)
        r4["curated_answer"] = "Completed assigned engineering features."
        assert AnswerQualityValidator.validate_answer(r4)["is_valid"] is False
        fields_tested.append("curated_answer")

        # 5. examples
        r5 = copy.deepcopy(base_record)
        r5["examples"] = "decoupled presentation from backend processing logic without evidence."
        assert AnswerQualityValidator.validate_answer(r5)["is_valid"] is False
        fields_tested.append("examples")

        # 6. step_by_step_explanation
        r6 = copy.deepcopy(base_record)
        r6["step_by_step_explanation"][1]["concrete_example"] = "I authored automated unit tests for the core service."
        assert AnswerQualityValidator.validate_answer(r6)["is_valid"] is False
        fields_tested.append("step_by_step_explanation")

        # 7. follow_up_questions
        r7 = copy.deepcopy(base_record)
        r7["follow_up_questions"][0]["reference_answer"] = "I implemented optimistic locking to solve the race condition."
        assert AnswerQualityValidator.validate_answer(r7)["is_valid"] is False
        fields_tested.append("follow_up_questions")

        # 8. completed_framework_answer
        r8 = copy.deepcopy(base_record)
        r8["completed_framework_answer"][1]["demonstration"] = "I designed modular software components and service APIs."
        assert AnswerQualityValidator.validate_answer(r8)["is_valid"] is False
        fields_tested.append("completed_framework_answer")

        # 9. framework_template
        r9 = copy.deepcopy(base_record)
        r9["framework_template"][0]["placeholder"] = "software development tasks"
        assert AnswerQualityValidator.validate_answer(r9)["is_valid"] is False
        fields_tested.append("framework_template")

        # 10. why_this_works
        r10 = copy.deepcopy(base_record)
        r10["why_this_works"] = "I deployed this service to AWS and reduced latency by 45%."
        assert AnswerQualityValidator.validate_answer(r10)["is_valid"] is False
        fields_tested.append("why_this_works")

        # 11. suggested_improvements
        r11 = copy.deepcopy(base_record)
        r11["suggested_improvements"] = ["software engineering duties"]
        assert AnswerQualityValidator.validate_answer(r11)["is_valid"] is False
        fields_tested.append("suggested_improvements")

        # 12. missing_personal_details
        r12 = copy.deepcopy(base_record)
        r12["missing_personal_details"] = ["assigned engineering features"]
        assert AnswerQualityValidator.validate_answer(r12)["is_valid"] is False
        fields_tested.append("missing_personal_details")

        # 13. verified_evidence
        r13 = copy.deepcopy(base_record)
        r13["verified_evidence"] = ["software development tasks"]
        assert AnswerQualityValidator.validate_answer(r13)["is_valid"] is False
        fields_tested.append("verified_evidence")

        assert len(fields_tested) == 13, f"Expected 13 fields tested, got {len(fields_tested)}"

    # -------------------------------------------------------------------------
    # 11. All six answer frameworks remain usable
    # -------------------------------------------------------------------------
    def test_11_all_six_answer_frameworks_remain_usable(self):
        """STAR, CAR, PAR, SOAR, PEEL, PREP produce valid, complete output."""
        frameworks = ["STAR", "CAR", "PAR", "SOAR", "PEEL", "PREP"]

        internship = {
            "organization": "DataCore Systems",
            "position": "Software Engineering Intern",
            "dates": "Summer 2023",
            "technologies": ["Python", "Docker"],
            "responsibilities": ["Refactored internal data ingestion scripts"]
        }

        project = {
            "title": "QueryOptimizer",
            "technologies": ["Python", "SQLAlchemy", "PostgreSQL"],
            "description": "Analyzed SQL query execution plans to identify missing indexes."
        }

        for fw in frameworks:
            # Internship answer
            notes_it = ground_guidance_in_evidence(fw, "internship", internship)
            assert len(notes_it) >= 3

            # Project answer
            notes_pr = ground_guidance_in_evidence(fw, "project", project)
            assert len(notes_pr) >= 3

            # Framework templates
            tmpl = format_answer_template(fw, notes_pr)
            assert len(tmpl) >= 3
            assert_no_forbidden_fallbacks(tmpl)

            # Framework demonstration
            q_dict = {
                "question_text": f"Walk me through your project using {fw}.",
                "topic": "Query Optimization",
                "detailed_answer": f"Verified Project Evidence: 'QueryOptimizer'. [General Technical Guidance]: In SQL optimization, indexes accelerate execution. [Candidate to specify: Metrics].",
                "short_answer": "Query optimization using PostgreSQL.",
                "why_this_works": "Indexes reduce full table scans.",
                "step_by_step_explanation": [
                    {"step": f"Step {i+1}", "detail": "Step detail.", "concrete_example": "[Candidate to specify: ...]"}
                    for i in range(3)
                ],
                "verified_evidence": ["Project: QueryOptimizer", "SQLAlchemy", "PostgreSQL"],
                "category": "B"
            }
            demo = build_completed_framework_demonstration(fw, q_dict)
            assert len(demo) >= 3
            assert_no_forbidden_fallbacks(demo)

    # -------------------------------------------------------------------------
    # 12. End-to-end generation and validation
    # -------------------------------------------------------------------------
    def test_12_end_to_end_generation_and_validation(self):
        """All questions across Categories A, B, C, D pass with is_valid=True and quality_score >= 80."""
        profiles = [
            # Minimal candidate: title-only internship and title-only project
            {
                "target_role": "Backend Engineer",
                "required_skills": ["Go", "Docker", "Kubernetes"],
                "missing_skills": ["Kubernetes"],
                "experience": [
                    {
                        "organization": "Startup Alpha",
                        "position": "Software Engineer Intern",
                        "dates": "Summer 2023",
                        "technologies": [],
                        "responsibilities": []
                    }
                ],
                "projects": [
                    {
                        "title": "MicroServiceLab",
                        "technologies": ["Go"],
                        "description": ""
                    }
                ],
                "skills": ["Go", "Python", "Docker"]
            },
            # Rich candidate: detailed internship and project description
            {
                "target_role": "Full Stack Developer",
                "required_skills": ["React", "TypeScript", "Node.js", "GraphQL"],
                "missing_skills": ["GraphQL"],
                "experience": [
                    {
                        "organization": "Enterprise Beta",
                        "position": "Full Stack Intern",
                        "dates": "January - June 2023",
                        "technologies": ["React", "TypeScript", "Node.js"],
                        "responsibilities": ["Maintained component library", "Resolved UI accessibility bugs"]
                    }
                ],
                "projects": [
                    {
                        "title": "E-Commerce Gateway",
                        "technologies": ["Node.js", "Express", "MongoDB"],
                        "description": "Implemented payment webhook handling with idempotent transaction deduplication."
                    }
                ],
                "skills": ["TypeScript", "React", "Node.js", "MongoDB"]
            }
        ]

        for p_idx, prof in enumerate(profiles):
            generator = InterviewQuestionGenerator(prof)
            questions = generator.generate_questions(category="ALL", max_questions=30)
            assert len(questions) >= 10, f"Profile {p_idx+1} produced only {len(questions)} questions"

            # Track categories generated
            categories_seen = set()

            for q in questions:
                cat = q.get("category", "")
                categories_seen.add(cat)

                # Check for forbidden fallbacks
                assert_no_forbidden_fallbacks(q, path=f"q_{q['question_id']}")

                # Validate answer
                val = AnswerQualityValidator.validate_answer(q)
                assert val["is_valid"] is True, (
                    f"Profile {p_idx+1} Question {q['question_id']} ({cat}) failed validation:\n"
                    f"Issues: {val['issues']}\n"
                    f"Question: {q['question_text']}"
                )
                assert val["quality_score"] >= 80.0, (
                    f"Profile {p_idx+1} Question {q['question_id']} score {val['quality_score']} < 80"
                )

            # Ensure all required categories exist
            for req_cat in ["A", "B", "C", "D"]:
                assert req_cat in categories_seen, f"Profile {p_idx+1} missing category {req_cat}"
