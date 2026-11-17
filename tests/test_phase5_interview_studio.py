"""
tests/test_phase5_interview_studio.py
Comprehensive Phase 5 Test Suite for Interview Studio:
1. Interview session creation with authorized analysis ID.
2. Cross-user isolation and ownership enforcement (two independent Flask clients).
3. Rejection of unauthorized (403) and non-existent (404) analysis IDs.
4. All interview modes (technical, behavioral, hr, mixed).
5. All difficulty levels (beginner, intermediate, advanced, all).
6. Question generation integrity (question_text, category, difficulty, related_skill, reason_for_asking, expected_answer_evaluation_criteria).
7. Zero fabrication of candidate achievements or unsupported technologies.
8. Deterministic 6-criterion answer evaluation (relevance, accuracy, coverage, clarity, specificity, consistency).
9. Honest technical accuracy verification and unverifiable claims flagging.
10. Anti-keyword-stuffing / token repetition safeguards.
11. Evidence-grounding warnings when candidate claims unevidenced technologies.
12. Suggested improved answer structure guidance.
13. SQLite persistent session store (save, retrieve, list, aggregate progress).
14. Safe deletion with strict ownership verification.
15. CSRF protection on state-changing requests.
16. Input validation and error handling (empty submissions, malformed requests, index out-of-bounds).
"""

import json
import secrets
import tempfile
from pathlib import Path
import pytest

from app import app, ANALYSIS_CACHE
from src.interview.interview_session import InterviewSession, InterviewSessionManager
from src.interview.session_store import InterviewSessionStore, get_interview_session_store
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.answer_evaluator import HeuristicAnswerEvaluator
from src.security.csrf import generate_csrf_token


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path):
    """Configures isolated test database and test flags."""
    app.config["TESTING"] = True
    test_db = tmp_path / "test_interview_sessions.sqlite"
    store = InterviewSessionStore(test_db)
    
    # Patch global session store
    import src.interview.interview_session as is_mod
    import src.interview.session_store as ss_mod
    ss_mod._SESSION_STORE = store
    is_mod.ACTIVE_SESSIONS.clear()
    
    yield
    
    is_mod.ACTIVE_SESSIONS.clear()
    ss_mod._SESSION_STORE = None


@pytest.fixture
def sample_candidate_analysis():
    aid = "test_candidate_auth_001"
    ANALYSIS_CACHE[aid] = {
        "analysis_id": aid,
        "filename": "Harsha_ML_Resume.pdf",
        "job_title": "Senior Machine Learning Engineer",
        "detected_job_title": "Senior Machine Learning Engineer",
        "target_role_source": "job_description",
        "predicted_class": "Good Fit",
        "candidate_profile": {
            "name": {"full_name": "Harsha Sri"},
            "skills": ["Python", "PyTorch", "Scikit-Learn", "SQL", "Flask"],
            "projects": [
                {
                    "title": "Multimodal Semantic Matcher",
                    "technologies": "Python, PyTorch, Scikit-Learn",
                    "description": "Implemented cross-modal dense retrieval with PyTorch, achieving 94% Macro F1."
                }
            ],
            "internships": [
                {
                    "organization": "DataTech Labs",
                    "role": "ML Intern",
                    "responsibilities": "Built automated data ingestion pipelines using Python and SQL."
                }
            ],
            "education": [{"degree": "B.Tech in Computer Science", "institution": "Tech University"}]
        },
        "resume_skills": ["Python", "PyTorch", "Scikit-Learn", "SQL", "Flask"],
        "matched_skills": ["Python", "PyTorch", "SQL"],
        "missing_skills": ["Kubernetes", "AWS"]
    }
    return aid


# =========================================================================
# 1. Interview Creation, Modes, and Difficulties
# =========================================================================

def test_01_interview_creation_authorized_analysis(sample_candidate_analysis):
    """Verify session creation using authorized analysis ID sets proper attributes."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "valid_csrf_token"

    resp = client.post(
        "/api/interview/sessions",
        data=json.dumps({
            "analysis_id": sample_candidate_analysis,
            "mode": "technical",
            "difficulty": "intermediate",
            "max_questions": 6,
            "csrf_token": "valid_csrf_token"
        }),
        content_type="application/json"
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "success"
    session_obj = data["session"]
    assert session_obj["analysis_id"] == sample_candidate_analysis
    assert session_obj["interview_mode"] == "technical"
    assert session_obj["difficulty"] == "intermediate"
    assert len(session_obj["questions"]) <= 6
    assert data["question"] is not None


def test_02_all_interview_modes(sample_candidate_analysis):
    """Verify all four interview modes: technical, behavioral, hr, mixed."""
    generator = InterviewQuestionGenerator(ANALYSIS_CACHE[sample_candidate_analysis])

    # Technical mode: should emphasize technical skills, projects, and technical knowledge
    tech_qs = generator.generate_questions(mode="technical", max_questions=10)
    for q in tech_qs:
        assert q["category"] in ["A", "B", "D", "E"]
        assert q["related_skill"]

    # Behavioral mode: should emphasize HR & projects
    beh_qs = generator.generate_questions(mode="behavioral", max_questions=10)
    for q in beh_qs:
        assert q["category"] in ["F", "B", "C"]

    # HR mode: should emphasize core behavioral competencies
    hr_qs = generator.generate_questions(mode="hr", max_questions=5)
    for q in hr_qs:
        assert q["category"] == "F"

    # Mixed mode: balanced cross-section
    mixed_qs = generator.generate_questions(mode="mixed", max_questions=10)
    categories = {q["category"] for q in mixed_qs}
    assert len(categories) >= 3


def test_03_all_difficulty_levels(sample_candidate_analysis):
    """Verify beginner, intermediate, advanced, and all difficulty filtering."""
    generator = InterviewQuestionGenerator(ANALYSIS_CACHE[sample_candidate_analysis])

    qs_easy = generator.generate_questions(difficulty="beginner", max_questions=5)
    assert all(q["difficulty"] == "Easy" for q in qs_easy)

    qs_med = generator.generate_questions(difficulty="intermediate", max_questions=5)
    assert all(q["difficulty"] == "Medium" for q in qs_med)

    qs_hard = generator.generate_questions(difficulty="advanced", max_questions=5)
    assert all(q["difficulty"] == "Hard" for q in qs_hard)


def test_04_target_role_customization(sample_candidate_analysis):
    """Verify target role customization adapts question context."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [sample_candidate_analysis]

    resp = client.get(f"/api/interview-studio?id={sample_candidate_analysis}&target_role=Cloud+Data+Architect")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    # Verify questions and evidence reflect the custom target role
    assert data["evidence"]["job_title"] == "Cloud Data Architect"


# =========================================================================
# 2. Question Generation Integrity & Fabrication Prevention
# =========================================================================

def test_05_question_required_fields_integrity(sample_candidate_analysis):
    """Ensure every generated question includes all required Phase 5 fields."""
    generator = InterviewQuestionGenerator(ANALYSIS_CACHE[sample_candidate_analysis])
    questions = generator.generate_questions(max_questions=20)
    assert len(questions) > 0

    for q in questions:
        assert isinstance(q.get("question_id"), str) and len(q["question_id"]) > 0
        assert isinstance(q.get("question_text"), str) and len(q["question_text"]) > 5
        assert isinstance(q.get("category"), str) and len(q["category"]) == 1
        assert q.get("difficulty") in ["Easy", "Medium", "Hard"]
        assert isinstance(q.get("related_skill"), str) and len(q["related_skill"]) > 0
        assert isinstance(q.get("reason_for_asking"), str) and len(q["reason_for_asking"]) > 10
        assert isinstance(q.get("expected_answer_evaluation_criteria"), list)
        assert len(q["expected_answer_evaluation_criteria"]) > 0
        # Backward-compatibility alias
        assert q["expected_key_points"] == q["expected_answer_evaluation_criteria"]


def test_06_zero_fabrication_unsupported_candidate_claims():
    """Verify candidate without Docker/Kubernetes in resume is never credited with them."""
    lean_analysis = {
        "analysis_id": "lean_candidate_002",
        "filename": "Junior_Python_Dev.pdf",
        "job_title": "Backend Developer",
        "candidate_profile": {
            "name": {"full_name": "Junior Dev"},
            "skills": ["Python", "Flask", "SQLite"],
            "projects": [
                {
                    "title": "Personal Blog Engine",
                    "technologies": "Python, Flask",
                    "description": "Built simple blog backend with Flask and SQLite."
                }
            ],
            "internships": [],
            "education": []
        },
        "resume_skills": ["Python", "Flask", "SQLite"],
        "matched_skills": ["Python"],
        "missing_skills": ["Kubernetes", "Docker", "AWS"]
    }
    generator = InterviewQuestionGenerator(lean_analysis)
    questions = generator.generate_questions(max_questions=25)

    for q in questions:
        if q["category"] == "B":
            # Project questions must only reference verified project technologies
            assert "Docker" not in q["question_text"]
            assert "Kubernetes" not in q["question_text"]
            assert "AWS" not in q["question_text"]


# =========================================================================
# 3. Deterministic 6-Criterion Answer Evaluation & Safeguards
# =========================================================================

def test_07_deterministic_answer_evaluation_all_criteria(sample_candidate_analysis):
    """Verify answer evaluator produces all 6 explicit criteria scores and composite overall score."""
    evaluator = HeuristicAnswerEvaluator()
    candidate_evidence = extract_candidate_evidence(ANALYSIS_CACHE[sample_candidate_analysis])

    q_data = {
        "question_text": "Explain how you applied PyTorch in your Multimodal Semantic Matcher project.",
        "related_skill": "PyTorch",
        "reason_for_asking": "Validates hands-on deep learning implementation depth.",
        "expected_answer_evaluation_criteria": [
            "Model architecture design",
            "Training and validation loss monitoring",
            "Handling cross-modal dense embeddings"
        ],
        "important_concepts": ["cross-modal", "embeddings", "loss function"],
        "recommended_answer_framework": "STAR"
    }

    user_ans = (
        "Situation: In our multimodal matcher project, we needed fast cross-modal dense retrieval. "
        "Task: I was responsible for designing the model architecture and training the dense encoder using PyTorch without data leakage. "
        "Action: I developed a two-tower neural network architecture with custom contrastive loss function to produce dense embeddings in PyTorch and monitored validation loss. "
        "Result: The system achieved 94% Macro F1 with an average retrieval latency of 25ms."
    )

    ev = evaluator.evaluate_answer(q_data, user_ans, "STAR", candidate_evidence=candidate_evidence)

    assert ev["status"] == "evaluated"
    assert "overall_score" in ev and ev["overall_score"] > 60.0
    assert ev["score"] == ev["overall_score"]
    
    crit = ev["criterion_scores"]
    assert "relevance" in crit and crit["relevance"]["score"] >= 60.0
    assert "technical_accuracy" in crit and crit["technical_accuracy"]["status"] == "verified"
    assert "concept_coverage" in crit and crit["concept_coverage"]["score"] >= 60.0
    assert "clarity_structure" in crit and crit["clarity_structure"]["score"] >= 60.0
    assert "specificity_examples" in crit and crit["specificity_examples"]["score"] >= 60.0
    assert "evidence_consistency" in crit and crit["evidence_consistency"]["score"] >= 60.0

    assert len(ev["strengths"]) > 0
    assert len(ev["suggested_improved_answer_structure"]["recommended_steps"]) == 4


def test_08_anti_keyword_stuffing_prevention():
    """Verify repeating identical keywords or token dumping is detected and penalized."""
    evaluator = HeuristicAnswerEvaluator()
    q_data = {
        "question_text": "Explain your experience with Python, PyTorch, and deep learning.",
        "expected_key_points": ["Python architecture", "PyTorch models", "Validation"],
        "recommended_answer_framework": "STAR"
    }

    # Stuffed answer repeating keywords with no substantive sentence structure
    stuffed_ans = "Python Python Python PyTorch PyTorch deep learning Python PyTorch models Python PyTorch"
    ev_stuffed = evaluator.evaluate_answer(q_data, stuffed_ans, "STAR")

    assert ev_stuffed["has_repetition"] is True
    assert ev_stuffed["criterion_scores"]["relevance"]["score"] <= 35.0
    assert any("stuffing" in s.lower() or "repeat" in s.lower() for s in ev_stuffed["areas_for_improvement"])


def test_09_unverifiable_technical_claims_honest_status():
    """Verify esoteric/unverified claims are marked 'unverifiable' rather than falsely verified."""
    evaluator = HeuristicAnswerEvaluator()
    q_data = {
        "question_text": "Describe your architectural pattern for quantum microkernel compilation.",
        "expected_key_points": ["Kernel architecture", "Compilation efficiency"],
        "recommended_answer_framework": "STAR"
    }

    user_ans = (
        "Situation: Working on quantum microkernels. "
        "Task: I had to compile q-circuits on exotic ion-trap hardware. "
        "Action: I developed a custom compiler flux-gate optimizer. "
        "Result: Optimized gate execution by 40%."
    )
    ev = evaluator.evaluate_answer(q_data, user_ans, "STAR")
    assert ev["criterion_scores"]["technical_accuracy"]["status"] == "unverifiable"


def test_10_evidence_grounding_warnings_on_unsupported_skills(sample_candidate_analysis):
    """Verify warning banner when candidate claims technologies absent from their verified resume."""
    evaluator = HeuristicAnswerEvaluator()
    # Candidate resume has Python, PyTorch, SQL, Flask (NO Rust, NO Kafka, NO Kubernetes)
    evidence = extract_candidate_evidence(ANALYSIS_CACHE[sample_candidate_analysis])

    q_data = {
        "question_text": "Explain your backend microservices experience.",
        "expected_key_points": ["Microservices", "Messaging", "Containerization"],
        "recommended_answer_framework": "STAR"
    }

    user_ans = (
        "Situation: In my previous company, our messaging throughput was slow. "
        "Task: I was assigned to build a stream processing platform using Rust and Kafka deployed on Kubernetes. "
        "Action: I wrote 50 microservices in Rust and managed 200 Kafka topics on Kubernetes clusters. "
        "Result: Handled 500k messages per second."
    )
    ev = evaluator.evaluate_answer(q_data, user_ans, "STAR", candidate_evidence=evidence)

    assert len(ev["evidence_grounding_warnings"]) >= 1
    assert any("Kafka" in w or "Kubernetes" in w for w in ev["evidence_grounding_warnings"])
    assert ev["criterion_scores"]["evidence_consistency"]["status"] == "warning"


# =========================================================================
# 4. Persistence, Session History, and Safe Deletion
# =========================================================================

def test_11_session_persistence_lifecycle(sample_candidate_analysis):
    """Verify complete persistence lifecycle: create, submit answers, persist, reload from SQLite."""
    generator = InterviewQuestionGenerator(ANALYSIS_CACHE[sample_candidate_analysis])
    questions = generator.generate_questions(max_questions=3)

    session_obj = InterviewSessionManager.create_session(
        questions=questions,
        analysis_id=sample_candidate_analysis,
        candidate_filename="Candidate.pdf",
        job_title="Senior ML Engineer",
        interview_mode="technical",
        difficulty="intermediate",
        owner_id="owner_alpha_101"
    )
    sid = session_obj.session_id

    # Submit an answer
    eval_res = session_obj.submit_answer(0, "Situation: Fast data processing. Action: Built Python pipeline. Result: 20ms latency.")
    assert eval_res["status"] == "evaluated"

    # Clear memory cache to prove SQLite persistence
    import src.interview.interview_session as is_mod
    is_mod.ACTIVE_SESSIONS.clear()

    # Re-retrieve from SQLite via Manager
    reloaded = InterviewSessionManager.get_session(sid, owner_id="owner_alpha_101")
    assert reloaded is not None
    assert reloaded.session_id == sid
    assert reloaded.owner_id == "owner_alpha_101"
    assert reloaded.answers.get("0") is not None
    assert reloaded.evaluations.get("0") is not None


def test_12_practice_history_listing_and_progress(sample_candidate_analysis):
    """Verify user session history listing and aggregated practice progress."""
    generator = InterviewQuestionGenerator(ANALYSIS_CACHE[sample_candidate_analysis])
    qs = generator.generate_questions(max_questions=2)

    sess1 = InterviewSessionManager.create_session(qs, owner_id="owner_beta_202", job_title="ML Engineer")
    sess1.submit_answer(0, "Situation: Model training. Action: Used PyTorch and Scikit-Learn. Result: 90% F1.")
    sess1.complete_session()

    sess2 = InterviewSessionManager.create_session(qs, owner_id="owner_beta_202", job_title="ML Engineer")

    history = InterviewSessionManager.list_sessions(owner_id="owner_beta_202")
    assert len(history) == 2
    assert history[0]["session_id"] in [sess1.session_id, sess2.session_id]

    progress = InterviewSessionManager.get_progress(owner_id="owner_beta_202")
    assert progress["total_sessions"] == 2
    assert progress["completed_sessions"] == 1
    assert progress["total_questions_attempted"] >= 1


def test_13_safe_deletion_ownership_enforcement(sample_candidate_analysis):
    """Verify a user can delete their own session, but unauthorized deletion is rejected."""
    generator = InterviewQuestionGenerator(ANALYSIS_CACHE[sample_candidate_analysis])
    qs = generator.generate_questions(max_questions=2)

    sess = InterviewSessionManager.create_session(qs, owner_id="user_owner_777")
    sid = sess.session_id

    # Attempt delete by another user -> must be rejected
    rejected = InterviewSessionManager.delete_session(sid, owner_id="malicious_user_999")
    assert rejected is False
    assert InterviewSessionManager.get_session(sid) is not None

    # Delete by legitimate owner -> succeeds
    allowed = InterviewSessionManager.delete_session(sid, owner_id="user_owner_777")
    assert allowed is True
    assert InterviewSessionManager.get_session(sid) is None


# =========================================================================
# 5. Cross-User Isolation & Security Controls (Two Independent Clients)
# =========================================================================

def test_14_cross_user_access_isolation_api(sample_candidate_analysis):
    """Verify Client B cannot access or view Client A's interview session data."""
    client_a = app.test_client()
    client_b = app.test_client()

    with client_a.session_transaction() as sess_a:
        sess_a["allowed_analyses"] = [sample_candidate_analysis]
        sess_a["csrf_token"] = "token_a"

    # Client A creates an interview session
    resp_a = client_a.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis, "csrf_token": "token_a"}),
        content_type="application/json"
    )
    assert resp_a.status_code == 201
    session_id_a = resp_a.get_json()["session"]["session_id"]

    # Client B attempts to fetch Client A's session detail -> 403 Forbidden
    resp_b_get = client_b.get(f"/api/interview/sessions/{session_id_a}")
    assert resp_b_get.status_code == 403

    # Client B attempts to access Client A's practice session -> 403 Forbidden
    resp_b_practice = client_b.get(f"/api/interview-practice?session_id={session_id_a}")
    assert resp_b_practice.status_code == 403

    # Client B attempts to submit answer to Client A's session -> 403 Forbidden
    with client_b.session_transaction() as sess_b:
        sess_b["csrf_token"] = "token_b"

    resp_b_submit = client_b.post(
        "/api/interview-practice/submit",
        data=json.dumps({"session_id": session_id_a, "question_index": 0, "user_answer": "Hacked", "csrf_token": "token_b"}),
        content_type="application/json"
    )
    assert resp_b_submit.status_code == 403

    # Client B attempts to view Client A's practice results -> 403 Forbidden
    resp_b_results = client_b.get(f"/api/interview-results?session_id={session_id_a}")
    assert resp_b_results.status_code == 403

    # Client B attempts to delete Client A's session -> 403 Forbidden
    resp_b_del = client_b.delete(
        f"/api/interview/sessions/{session_id_a}",
        headers={"X-CSRF-Token": "token_b"}
    )
    assert resp_b_del.status_code == 403


def test_15_unauthorized_and_nonexistent_analysis_ids(sample_candidate_analysis):
    """Verify unauthorized analysis ID returns 403 and unknown analysis ID returns 404."""
    client = app.test_client()

    # Client with no access to sample_candidate_analysis
    resp_unauth = client.get(f"/api/interview-studio?id={sample_candidate_analysis}")
    assert resp_unauth.status_code == 403
    assert "Unauthorized" in resp_unauth.get_json()["message"]

    # Client requesting non-existent ID
    resp_notfound = client.get("/api/interview-studio?id=completely_unknown_id_9999")
    assert resp_notfound.status_code == 404
    assert "not found" in resp_notfound.get_json()["message"].lower()


def test_16_csrf_fail_closed_production(sample_candidate_analysis):
    """Verify CSRF fail-closed behavior on state-changing endpoints in production mode."""
    client = app.test_client()
    original_testing = app.config.get("TESTING")
    try:
        app.config["TESTING"] = False
        token = secrets.token_hex(32)

        with client.session_transaction() as sess:
            sess["allowed_analyses"] = [sample_candidate_analysis]
            sess["csrf_token"] = token

        # Missing CSRF in request -> 403 Forbidden
        resp_missing = client.post(
            "/api/interview-studio/generate",
            data=json.dumps({"id": sample_candidate_analysis, "action": "practice"}),
            content_type="application/json"
        )
        assert resp_missing.status_code == 403

        # Invalid CSRF in request -> 403 Forbidden
        resp_invalid = client.post(
            "/api/interview-studio/generate",
            data=json.dumps({"id": sample_candidate_analysis, "action": "practice", "csrf_token": "wrong_token"}),
            content_type="application/json"
        )
        assert resp_invalid.status_code == 403

        # Valid CSRF in request -> 200 OK
        resp_valid = client.post(
            "/api/interview-studio/generate",
            data=json.dumps({"id": sample_candidate_analysis, "action": "practice", "csrf_token": token}),
            content_type="application/json"
        )
        assert resp_valid.status_code == 200
        assert resp_valid.get_json()["status"] == "success"

    finally:
        app.config["TESTING"] = original_testing


# =========================================================================
# 6. Input Validation and Edge Cases
# =========================================================================

def test_17_invalid_mode_and_difficulty_validation(sample_candidate_analysis):
    """Verify bad request rejection for invalid mode, difficulty, or question count."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "valid_token"

    # Invalid mode
    resp_mode = client.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis, "mode": "invalid_mode_xyz", "csrf_token": "valid_token"}),
        content_type="application/json"
    )
    assert resp_mode.status_code == 400
    assert "mode" in resp_mode.get_json()["message"].lower()

    # Invalid difficulty
    resp_diff = client.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis, "difficulty": "super_impossible", "csrf_token": "valid_token"}),
        content_type="application/json"
    )
    assert resp_diff.status_code == 400
    assert "difficulty" in resp_diff.get_json()["message"].lower()

    # Out of range max_questions
    resp_count = client.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis, "max_questions": 999, "csrf_token": "valid_token"}),
        content_type="application/json"
    )
    assert resp_count.status_code == 400


def test_18_empty_and_placeholder_submission_handling(sample_candidate_analysis):
    """Verify empty or single-character placeholder submissions do not break evaluation."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "token_valid"

    # Create session
    resp = client.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis, "csrf_token": "token_valid"}),
        content_type="application/json"
    )
    sid = resp.get_json()["session"]["session_id"]

    # Submit empty answer
    resp_empty = client.post(
        "/api/interview-practice/submit",
        data=json.dumps({"session_id": sid, "question_index": 0, "user_answer": "   ", "csrf_token": "token_valid"}),
        content_type="application/json"
    )
    assert resp_empty.status_code == 200
    ev = resp_empty.get_json()["evaluation"]
    assert ev["status"] == "empty"
    assert ev["overall_score"] == 0.0

    # Submit placeholder answer
    resp_placeholder = client.post(
        "/api/interview-practice/submit",
        data=json.dumps({"session_id": sid, "question_index": 0, "user_answer": "test test none", "csrf_token": "token_valid"}),
        content_type="application/json"
    )
    assert resp_placeholder.status_code == 200
    ev_pl = resp_placeholder.get_json()["evaluation"]
    assert ev_pl["status"] == "insufficient"
    assert ev_pl["overall_score"] == 0.0


def test_19_question_index_out_of_bounds(sample_candidate_analysis):
    """Verify question index out-of-bounds returns 400."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "token_valid"

    resp = client.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis, "max_questions": 3, "csrf_token": "token_valid"}),
        content_type="application/json"
    )
    sid = resp.get_json()["session"]["session_id"]

    resp_oob = client.post(
        "/api/interview-practice/submit",
        data=json.dumps({"session_id": sid, "question_index": 99, "user_answer": "Valid text", "csrf_token": "token_valid"}),
        content_type="application/json"
    )
    assert resp_oob.status_code == 400
    assert "range" in resp_oob.get_json()["message"].lower()


from src.interview.evidence_mapper import extract_candidate_evidence
