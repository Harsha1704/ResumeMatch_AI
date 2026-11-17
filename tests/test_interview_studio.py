"""
Comprehensive Phase 8 Test Suite for Interview Intelligence Studio.
Verifies all 25 requirements:
1. Resume-based questions.
2. Project-based questions.
3. Internship-based questions.
4. Job-specific questions.
5. External technical questions.
6. HR questions.
7. STAR answer framework.
8. STAR+L framework.
9. CAR framework.
10. PAR framework.
11. SOAR framework.
12. PREP framework.
13. PEEL framework.
14. WHAT-WHY-HOW framework.
15. No fabricated achievements.
16. No invented technologies.
17. Missing information placeholders.
18. Difficulty selection.
19. Question deduplication.
20. Session isolation.
21. Practice mode.
22. Heuristic feedback.
23. Flask route integration.
24. Empty input handling.
25. Question bank integrity.
"""

import json
import pytest
from app import app
from src.interview import (
    InterviewQuestionGenerator,
    InterviewSessionManager,
    HeuristicAnswerEvaluator,
    get_framework,
    FRAMEWORKS,
    TECHNICAL_QUESTION_BANK,
    HR_QUESTION_BANK,
    get_all_technical_topics,
    extract_candidate_evidence,
    filter_by_difficulty
)

SAMPLE_ANALYSIS = {
    "analysis_id": "test_analysis_123",
    "filename": "harsha_resume.pdf",
    "job_title": "Senior Machine Learning Engineer",
    "projects": [
        {
            "title": "Multimodal Resume Matching System",
            "technologies": ["Python", "PyTorch", "Flask", "Scikit-Learn"],
            "description": "Engineered multimodal resume-job compatibility pipeline."
        },
        {
            "title": "Anomaly Detection Microservice",
            "technologies": ["Python", "Docker", "FastAPI"],
            "description": "Built real-time containerized anomaly detection service."
        }
    ],
    "internships": [
        {
            "organization": "Cognitive AI Labs",
            "position": "Machine Learning Intern",
            "dates": "June 2023 - August 2023",
            "technologies": ["Python", "OpenCV"],
            "responsibilities": ["Implemented computer vision model pipelines and benchmarked inference."]
        }
    ],
    "resume_skills": ["Python", "PyTorch", "Flask", "Scikit-Learn", "Docker", "SQL", "FastAPI"],
    "matched_skills": ["Python", "PyTorch", "Docker"],
    "missing_skills": ["Kubernetes", "AWS", "Terraform"],
    "required_skills": ["Python", "Docker", "Kubernetes"],
    "preferred_skills": ["AWS", "Terraform"],
    "education_analysis": {"notes": "B.Tech in Computer Science and Engineering"},
    "experience_summary": {"display_summary": "1 Internship, 2 Key Projects verified"}
}


# -------------------------------------------------------------------------
# Test 1-6: Question Categories A through F
# -------------------------------------------------------------------------

def test_01_resume_based_questions():
    """1. Test Category A: Resume-based questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_category_a()
    assert len(qs) >= 2
    for q in qs:
        assert q["category"] == "A"
        assert "question_text" in q
        assert q["recommended_answer_framework"] in FRAMEWORKS
        assert len(q["expected_key_points"]) > 0


def test_02_project_based_questions():
    """2. Test Category B: Project-based deep-dive questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_category_b()
    assert len(qs) >= 4  # 4 questions per project * 2 projects = 8 questions
    # Verify both projects appear in question references
    refs = [q["source_reference"] for q in qs]
    assert any("Multimodal Resume Matching System" in r for r in refs)
    assert any("Anomaly Detection Microservice" in r for r in refs)


def test_03_internship_based_questions():
    """3. Test Category C: Internship-based questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_category_c()
    assert len(qs) >= 2
    refs = [q["source_reference"] for q in qs]
    assert any("Cognitive AI Labs" in r for r in refs)
    # Organization and responsibilities are referenced accurately
    q_texts = " ".join([q["question_text"] for q in qs])
    assert "Cognitive AI Labs" in q_texts


def test_04_job_specific_questions():
    """4. Test Category D: Job-specific and skill-gap questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_category_d()
    assert len(qs) >= 2
    # Check that missing skills (Kubernetes, AWS) are included in preparation questions
    q_texts = " ".join([q["question_text"] for q in qs])
    assert "Kubernetes" in q_texts or "Senior Machine Learning Engineer" in q_texts


def test_05_external_technical_questions():
    """5. Test Category E: External technical knowledge questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_category_e()
    assert len(qs) >= 15
    for q in qs:
        assert q["category"] == "E"
        assert "curated_answer" in q
        assert len(q["curated_answer"]) > 20


def test_06_hr_behavioral_questions():
    """6. Test Category F: HR and behavioral questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_category_f()
    assert len(qs) >= 10
    q_texts = [q["question_text"] for q in qs]
    assert any("Tell me about yourself" in t for t in q_texts)
    assert any("strengths" in t.lower() for t in q_texts)
    assert any("weakness" in t.lower() for t in q_texts)


# -------------------------------------------------------------------------
# Test 7-14: Answer Frameworks
# -------------------------------------------------------------------------

def test_07_star_framework():
    fw = get_framework("STAR")
    assert fw["id"] == "STAR"
    step_keys = [s["key"] for s in fw["steps"]]
    assert step_keys == ["Situation", "Task", "Action", "Result"]


def test_08_star_plus_l_framework():
    fw = get_framework("STAR+L")
    assert fw["id"] == "STAR+L"
    step_keys = [s["key"] for s in fw["steps"]]
    assert step_keys == ["Situation", "Task", "Action", "Result", "Learning"]


def test_09_car_framework():
    fw = get_framework("CAR")
    assert fw["id"] == "CAR"
    step_keys = [s["key"] for s in fw["steps"]]
    assert step_keys == ["Challenge", "Action", "Result"]


def test_10_par_framework():
    fw = get_framework("PAR")
    assert fw["id"] == "PAR"
    step_keys = [s["key"] for s in fw["steps"]]
    assert step_keys == ["Problem", "Action", "Result"]


def test_11_soar_framework():
    fw = get_framework("SOAR")
    assert fw["id"] == "SOAR"
    step_keys = [s["key"] for s in fw["steps"]]
    assert step_keys == ["Situation", "Obstacles", "Actions", "Results"]


def test_12_prep_framework():
    fw = get_framework("PREP")
    assert fw["id"] == "PREP"
    step_keys = [s["key"] for s in fw["steps"]]
    assert "Point" in step_keys and "Reason" in step_keys and "Example" in step_keys


def test_13_peel_framework():
    fw = get_framework("PEEL")
    assert fw["id"] == "PEEL"
    step_keys = [s["key"] for s in fw["steps"]]
    assert step_keys == ["Point", "Evidence", "Explanation", "Link"]


def test_14_what_why_how_framework():
    fw = get_framework("WHAT-WHY-HOW")
    assert fw["id"] == "WHAT-WHY-HOW"
    step_keys = [s["key"] for s in fw["steps"]]
    assert step_keys == ["What", "Why", "How"]


# -------------------------------------------------------------------------
# Test 15-17: Non-Fabrication & Evidence Grounding
# -------------------------------------------------------------------------

def test_15_no_fabricated_achievements():
    """15. Verify that questions only reference genuine candidate projects and internships."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_questions(category="ALL", max_questions=30)
    for q in qs:
        # If it refers to an organization, it must be the extracted one
        if q["source_type"] == "resume_internship":
            assert "Cognitive AI Labs" in q["question_text"] or "Cognitive AI Labs" in q["source_reference"]
        # If it refers to a project, it must be one of the candidate projects
        if q["source_type"] == "resume_project":
            assert ("Multimodal Resume Matching System" in q["question_text"] or 
                    "Anomaly Detection Microservice" in q["question_text"])


def test_16_no_invented_technologies():
    """16. Verify that project questions only cite candidate's verified technologies."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs_b = generator.generate_category_b()
    for q in qs_b:
        text = q["question_text"]
        if "Multimodal Resume Matching System" in text:
            # Must not invent technologies like Rust or Ruby
            assert "Rust" not in text and "Ruby" not in text and "Go" not in text


def test_17_missing_information_placeholders():
    """17. Verify that unestablished metrics/results use explicit student prompt placeholders."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs_b = generator.generate_category_b()
    placeholders_found = False
    for q in qs_b:
        template = q.get("framework_template", [])
        for step in template:
            ph = step.get("placeholder", "")
            if ph.startswith("[") and ph.endswith("]"):
                placeholders_found = True
                break
    assert placeholders_found, "Expected explicit editable placeholders like [Describe...] in answer templates"


# -------------------------------------------------------------------------
# Test 18-20: Difficulty, Deduplication & Session Isolation
# -------------------------------------------------------------------------

def test_18_difficulty_selection():
    """18. Test difficulty filtering across Easy, Medium, Hard, and All."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs_easy = generator.generate_questions(difficulty="Easy", max_questions=10)
    for q in qs_easy:
        assert q["difficulty"] == "Easy"

    qs_hard = generator.generate_questions(difficulty="Hard", max_questions=10)
    for q in qs_hard:
        assert q["difficulty"] == "Hard"

    qs_all = generator.generate_questions(difficulty="All", max_questions=10)
    diffs = {q["difficulty"] for q in qs_all}
    assert len(diffs) > 1, "Expected balanced distribution across difficulty levels when 'All' is selected"


def test_19_question_deduplication():
    """19. Verify that generated questions are strictly unique."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_questions(category="ALL", max_questions=25)
    texts = [q["question_text"].strip().lower() for q in qs]
    assert len(texts) == len(set(texts)), "Duplicate questions found in generated portfolio"


def test_20_session_isolation():
    """20. Verify that two practice sessions maintain independent state and answers."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs1 = generator.generate_questions(max_questions=3)
    qs2 = generator.generate_questions(max_questions=3)

    sess1 = InterviewSessionManager.create_session(qs1)
    sess2 = InterviewSessionManager.create_session(qs2)

    assert sess1.session_id != sess2.session_id

    sess1.submit_answer(0, "User 1 Answer for Question 1")
    sess2.submit_answer(0, "User 2 Answer for Question 1")

    assert sess1.answers["0"] == "User 1 Answer for Question 1"
    assert sess2.answers["0"] == "User 2 Answer for Question 1"
    assert sess1.answers["0"] != sess2.answers["0"]


# -------------------------------------------------------------------------
# Test 21-22: Practice Mode & Heuristic Evaluation
# -------------------------------------------------------------------------

def test_21_practice_mode_navigation():
    """21. Test practice mode step navigation, answer recording, and completion."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_questions(max_questions=4)
    sess = InterviewSessionManager.create_session(qs)

    q0 = sess.get_current_question()
    assert q0["question_number"] == 1

    sess.submit_answer(0, "First question answer with Python and Docker.")
    sess.next_question()

    q1 = sess.get_current_question()
    assert q1["question_number"] == 2

    sess.prev_question()
    q0_again = sess.get_current_question()
    assert q0_again["question_number"] == 1
    assert q0_again["user_answer"] == "First question answer with Python and Docker."

    summary = sess.complete_session()
    assert summary["is_completed"] is True
    assert summary["total_questions"] == 4
    assert summary["completed_questions"] == 1


def test_22_heuristic_feedback():
    """22. Test deterministic heuristic feedback evaluation."""
    evaluator = HeuristicAnswerEvaluator()
    q_data = {
        "question_text": "Explain how you applied Python and PyTorch in your project.",
        "expected_key_points": [
            "Overview of technical stack proficiency",
            "Practical application in concrete projects",
            "How tool selection mapped to project requirements"
        ],
        "recommended_answer_framework": "STAR"
    }

    # Evaluate answer with partial framework coverage
    user_ans = "Situation: In our multimodal project, we needed a fast matcher. Action: I built the pipeline using Python and PyTorch. We tested the model thoroughly."
    eval_res = evaluator.evaluate_answer(q_data, user_ans, "STAR")

    assert eval_res["evaluator_label"] == "Heuristic Answer Feedback"
    assert eval_res["status"] == "evaluated"
    assert "Situation" in eval_res["framework_adherence"]["sections_addressed"]
    assert "Action" in eval_res["framework_adherence"]["sections_addressed"]
    assert eval_res["key_point_coverage"]["coverage_pct"] > 0.0
    assert len(eval_res["actionable_feedback"]) > 10


# -------------------------------------------------------------------------
# Test 23-25: Flask Routes, Empty Inputs, and Question Bank
# -------------------------------------------------------------------------

def test_23_flask_routes_integration():
    """23. Test Flask routes for Interview Studio."""
    client = app.test_client()

    # 1. Studio dashboard
    resp = client.get("/interview-studio")
    assert resp.status_code == 200
    assert b"Interview Intelligence Studio" in resp.data

    # 2. Studio question generation
    tok = client.get("/api/csrf-token").get_json()["csrf_token"]
    resp_gen = client.post("/interview-studio/generate", data={
        "category": "E",
        "difficulty": "Easy",
        "max_questions": "5",
        "action": "generate",
        "csrf_token": tok
    })
    assert resp_gen.status_code == 200

    # 3. Practice session generation
    resp_prac = client.post("/interview-studio/generate", data={
        "category": "ALL",
        "difficulty": "Medium",
        "max_questions": "5",
        "action": "practice",
        "csrf_token": tok
    }, follow_redirects=True)
    assert resp_prac.status_code == 200
    assert b"Your Interview Answer:" in resp_prac.data

    # 4. Instant AJAX evaluation endpoint
    token = client.get("/api/csrf-token").get_json()["csrf_token"]
    eval_payload = {
        "user_answer": "Situation: We used Flask. Action: I implemented REST routes. Result: The latency was 20ms.",
        "question_id": "test_q_1",
        "framework_id": "STAR",
        "question_text": "Describe your Flask API experience.",
        "expected_key_points": ["REST routes", "Flask architecture"]
    }
    resp_eval = client.post("/api/interview/evaluate",
                            data=json.dumps(eval_payload),
                            content_type="application/json",
                            headers={"X-CSRF-Token": token})
    assert resp_eval.status_code == 200
    eval_json = resp_eval.get_json()
    assert eval_json["evaluator_label"] == "Heuristic Answer Feedback"
    assert eval_json["evidence_detected"] is True


def test_24_empty_input_handling():
    """24. Test graceful handling of empty inputs."""
    evaluator = HeuristicAnswerEvaluator()
    res = evaluator.evaluate_answer({"expected_key_points": []}, "", "STAR")
    assert res["status"] == "empty"
    assert res["word_count"] == 0

    # Empty candidate analysis
    generator = InterviewQuestionGenerator(None)
    qs = generator.generate_questions(max_questions=5)
    assert len(qs) > 0, "Generator should gracefully supply core technical and HR questions even with None analysis"


def test_25_question_bank_integrity():
    """25. Verify that all 17 technical domains and HR questions exist and are valid."""
    topics = get_all_technical_topics()
    required_topics = [
        "Python", "Java", "C/C++", "Data Structures", "Algorithms",
        "DBMS", "SQL", "Operating Systems", "Computer Networks",
        "Machine Learning", "Data Science", "NLP", "Cybersecurity",
        "Cloud Computing", "DevOps", "Web Development", "Software Engineering"
    ]
    for req_top in required_topics:
        assert req_top in topics, f"Missing topic in technical question bank: {req_top}"

    assert len(TECHNICAL_QUESTION_BANK) >= 17
    assert len(HR_QUESTION_BANK) >= 12
    for hr_q in HR_QUESTION_BANK:
        assert "question" in hr_q
        assert "recommended_framework" in hr_q
        assert hr_q["recommended_framework"] in FRAMEWORKS


# -------------------------------------------------------------------------
# Tests 26-32: Phase 8 Upgrade Complete Answers & Extended Schema Validation
# -------------------------------------------------------------------------

def test_26_extended_answer_data_structure():
    """26. Verify extended answer schema across generated questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    qs = generator.generate_questions(category="ALL", difficulty="All", max_questions=30)
    assert len(qs) >= 15

    required_fields = [
        "question_id", "question_text", "category", "category_name",
        "category_badge", "difficulty", "short_answer", "detailed_answer",
        "step_by_step_explanation", "important_concepts", "interview_tips",
        "recommended_framework", "evidence_sources", "missing_personal_details"
    ]
    for q in qs:
        for field in required_fields:
            assert field in q, f"Question {q.get('question_id')} missing field: {field}"
            assert q[field] is not None, f"Field {field} is None in {q.get('question_id')}"
        assert len(q["short_answer"]) > 20
        assert len(q["detailed_answer"]) > 50
        assert len(q["step_by_step_explanation"]) >= 3


def test_27_step_by_step_explanation_pedagogy():
    """27. Verify step-by-step pedagogical explanations for technical and behavioral questions."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    tech_qs = generator.generate_category_e()
    for q in tech_qs:
        steps = q["step_by_step_explanation"]
        assert len(steps) >= 4, f"Technical question {q['question_id']} has fewer than 4 explanation steps"
        for st in steps:
            assert "step" in st and "detail" in st
            assert len(st["detail"]) > 10

    hr_qs = generator.generate_category_f()
    for q in hr_qs:
        steps = q["step_by_step_explanation"]
        assert len(steps) >= 3, f"HR question {q['question_id']} has fewer than 3 explanation steps"


def test_28_resume_grounding_zero_fabrication():
    """28. Verify project and internship questions provide complete answers and separate customization notes."""
    generator = InterviewQuestionGenerator(SAMPLE_ANALYSIS)
    proj_qs = generator.generate_category_b()
    assert len(proj_qs) >= 4
    for q in proj_qs:
        assert "[Personal Detail to Customize:" not in q["detailed_answer"], "Unsanitized placeholder in project answer"
        assert "[Mention Primary Project" not in q["detailed_answer"], "Unsanitized mention placeholder in project answer"
        assert len(q["detailed_answer"]) > 50
        assert len(q["missing_personal_details"]) > 0

    intern_qs = generator.generate_category_c()
    assert len(intern_qs) >= 3
    for q in intern_qs:
        assert "[Personal Detail to Customize:" not in q["detailed_answer"], "Unsanitized placeholder in internship answer"
        assert len(q["detailed_answer"]) > 50
        assert len(q["missing_personal_details"]) > 0


def test_29_technical_answers_substantive_not_verbatim():
    """29. Verify that technical answers are substantive and not mere repetitions of questions."""
    for item in TECHNICAL_QUESTION_BANK:
        short_a = item["short_answer"]
        detailed_a = item["detailed_answer"]
        q_text = item["question"]

        assert detailed_a.strip().lower() != q_text.strip().lower()
        assert len(detailed_a) > 100, f"Detailed answer too brief for {item['id']}"
        assert len(short_a) > 30, f"Short answer too brief for {item['id']}"
        assert len(item["important_concepts"]) >= 3
        assert len(item["interview_tips"]) >= 1


def test_30_practice_mode_concept_tracking():
    """30. Verify heuristic feedback tracks important concepts and supplies missing concepts."""
    evaluator = HeuristicAnswerEvaluator()
    q_data = {
        "question_text": "Explain Python generators and yield vs return.",
        "expected_key_points": ["Generators produce items lazily", "yield pauses function state"],
        "important_concepts": ["Iterator Protocol", "Lazy Evaluation", "StopIteration"],
        "recommended_answer_framework": "WHAT-WHY-HOW"
    }

    # User answer mentions lazy evaluation but misses StopIteration and Iterator Protocol
    user_attempt = "Generators provide lazy evaluation of items on-demand using yield rather than return."
    res = evaluator.evaluate_answer(q_data, user_attempt, "WHAT-WHY-HOW")

    assert res["status"] == "evaluated"
    assert "Iterator Protocol" in res["important_concepts_coverage"]["missing"]
    assert "Lazy Evaluation" in res["important_concepts_coverage"]["covered"]
    assert "heuristic" in res["disclaimer"].lower()


def test_31_practice_single_question_route():
    """31. Verify launching practice mode for a specific question ID."""
    client = app.test_client()
    tok = client.get("/api/csrf-token").get_json()["csrf_token"]
    resp = client.post(
        "/interview-studio/generate",
        data={"action": "practice_single", "question_id": "tb_py_01", "csrf_token": tok},
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Practice Mode" in resp.data or b"practice-container" in resp.data


def test_32_studio_renders_complete_answers():
    """32. Verify /interview-studio renders complete answers and copy button."""
    client = app.test_client()
    resp = client.get("/interview-studio")
    assert resp.status_code == 200
    assert b"Complete Answer" in resp.data
    assert b"Copy Answer" in resp.data
    assert b"Step-by-Step Reasoning" in resp.data
