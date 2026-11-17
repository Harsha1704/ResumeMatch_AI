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


# =========================================================================
# 7. Phase 5.1 Reliability, Evidence Persistence, and Hardening Tests
# =========================================================================

from src.interview.interview_session import ACTIVE_SESSIONS
from src.interview.evidence_mapper import extract_candidate_evidence
import sqlite3


def test_20_session_restart_and_evidence_restoration(sample_candidate_analysis):
    """Verify candidate evidence is preserved across memory restarts and reloaded correctly."""
    analysis = ANALYSIS_CACHE[sample_candidate_analysis]
    generator = InterviewQuestionGenerator(analysis)
    questions = generator.generate_questions(max_questions=3)

    session = InterviewSessionManager.create_session(
        questions=questions,
        analysis_id=sample_candidate_analysis,
        candidate_filename="Harsha_ML_Resume.pdf",
        job_title="Senior Machine Learning Engineer",
        owner_id="restart_user_001",
        candidate_evidence=generator.evidence
    )
    sid = session.session_id
    assert session.candidate_evidence is not None
    assert "PyTorch" in session.candidate_evidence.get("skills", [])

    # Submit first answer
    session.submit_answer(0, "I developed data pipelines using Python and SQL.")

    # Simulate server restart by clearing in-memory active sessions
    ACTIVE_SESSIONS.clear()
    assert sid not in ACTIVE_SESSIONS

    # Reload from persistent SQLite store
    reloaded = InterviewSessionManager.get_session(sid, owner_id="restart_user_001")
    assert reloaded is not None
    assert reloaded.session_id == sid
    assert reloaded.candidate_evidence is not None
    assert "PyTorch" in reloaded.candidate_evidence.get("skills", [])

    # Evaluate answer with unevidenced technologies on the reloaded session
    # Candidate resume does not have Kubernetes or Docker
    eval_res = reloaded.submit_answer(1, "I deployed the system using Kubernetes and Docker on AWS cloud.")
    warnings = eval_res.get("evidence_grounding_warnings", [])
    assert len(warnings) > 0
    assert any("Kubernetes" in w or "Docker" in w or "Aws" in w for w in warnings)


def test_21_cross_user_isolation_after_restart(sample_candidate_analysis):
    """Verify cross-user ownership isolation remains strictly enforced after in-memory restarts."""
    analysis = ANALYSIS_CACHE[sample_candidate_analysis]
    generator = InterviewQuestionGenerator(analysis)
    questions = generator.generate_questions(max_questions=2)

    session = InterviewSessionManager.create_session(
        questions=questions,
        analysis_id=sample_candidate_analysis,
        owner_id="user_alpha",
        candidate_evidence=generator.evidence
    )
    sid = session.session_id

    # Restart
    ACTIVE_SESSIONS.clear()

    # User Beta attempts retrieval
    beta_session = InterviewSessionManager.get_session(sid, owner_id="user_beta")
    assert beta_session is None

    # Test via Flask API client
    client_b = app.test_client()
    with client_b.session_transaction() as sess:
        sess["interview_owner_id"] = "user_beta"
        sess["csrf_token"] = "valid_beta_token"

    resp_get = client_b.get(f"/api/interview/sessions/{sid}")
    assert resp_get.status_code == 403

    resp_sub = client_b.post(
        "/api/interview-practice/submit",
        data=json.dumps({"session_id": sid, "question_index": 0, "user_answer": "Unauthorized", "csrf_token": "valid_beta_token"}),
        content_type="application/json"
    )
    assert resp_sub.status_code == 403


def test_22_duplicate_and_updated_answer_submissions(sample_candidate_analysis):
    """Verify resubmitting an answer to the same question updates state without duplicating."""
    analysis = ANALYSIS_CACHE[sample_candidate_analysis]
    generator = InterviewQuestionGenerator(analysis)
    questions = generator.generate_questions(max_questions=3)

    session = InterviewSessionManager.create_session(
        questions=questions,
        analysis_id=sample_candidate_analysis,
        owner_id="dup_test_user",
        candidate_evidence=generator.evidence
    )

    # Initial submission
    res1 = session.submit_answer(0, "First attempt answer discussing Python.")
    assert "0" in session.answers
    assert session.answers["0"] == "First attempt answer discussing Python."

    # Resubmission / update
    res2 = session.submit_answer(0, "Refined attempt using Python and PyTorch neural network architecture.")
    assert len(session.answers) == 1
    assert session.answers["0"] == "Refined attempt using Python and PyTorch neural network architecture."
    assert session.evaluations["0"]["overall_score"] >= res1.get("overall_score", 0.0)


def test_23_completed_session_behavior(sample_candidate_analysis):
    """Verify session completion preserves completion timestamp, status, and summary metrics."""
    analysis = ANALYSIS_CACHE[sample_candidate_analysis]
    generator = InterviewQuestionGenerator(analysis)
    questions = generator.generate_questions(max_questions=2)

    session = InterviewSessionManager.create_session(
        questions=questions,
        analysis_id=sample_candidate_analysis,
        owner_id="complete_user",
        candidate_evidence=generator.evidence
    )

    session.submit_answer(0, "Answer for question 0 using Python.")
    session.submit_answer(1, "Answer for question 1 using SQL.")

    summary = session.complete_session()
    assert session.is_completed is True
    assert session.completed_at is not None
    assert summary["completed_questions"] == 2
    assert summary["completion_rate_pct"] == 100.0

    # Ensure restart preserves is_completed
    ACTIVE_SESSIONS.clear()
    reloaded = InterviewSessionManager.get_session(session.session_id, owner_id="complete_user")
    assert reloaded is not None
    assert reloaded.is_completed is True
    assert reloaded.completed_at is not None


def test_24_technical_terms_distinguish_recognized_from_verified():
    """Verify simply mentioning Python, React, SQL, or Docker does NOT mark them as verified."""
    evaluator = HeuristicAnswerEvaluator()
    q_data = {
        "question_text": "Describe your software stack and implementation experience.",
        "expected_key_points": ["Software architecture", "Tool selection"],
        "important_concepts": ["architecture"],
        "recommended_answer_framework": "STAR"
    }

    # Case A: Name-dropping technical entities without contextual validation rules
    answer_name_drop = (
        "Situation: In my software engineering journey, I worked across multiple stacks. "
        "Task: I was responsible for choosing appropriate frameworks and databases. "
        "Action: I used Python, React, SQL, and Docker to develop the application. "
        "Result: The system was delivered cleanly and fulfilled all user requirements."
    )
    ev_dropped = evaluator.evaluate_answer(q_data, answer_name_drop, "STAR")
    assert ev_dropped["status"] == "evaluated"
    tech_crit = ev_dropped["criterion_scores"]["technical_accuracy"]

    # Must be recognized, NOT verified!
    assert tech_crit["status"] == "recognized"
    assert "Recognized technical terms" in tech_crit["details"]
    claims = ev_dropped["claims_analysis"]
    assert len(claims["recognized_technical_entities"]) > 0
    assert len(claims["verified_technical_entities"]) == 0

    # Case B: Concrete technical usage matching validation rules
    answer_verified_sql = (
        "Situation: In our data tier, query performance was slow. "
        "Task: My goal was to optimize SQL queries for relational data retrieval. "
        "Action: I wrote optimized SQL queries using SELECT, JOIN, and WHERE clauses with indexing on user_id. "
        "Result: Query execution completed efficiently with verified data integrity."
    )
    ev_sql = evaluator.evaluate_answer(q_data, answer_verified_sql, "STAR")
    assert ev_sql["criterion_scores"]["technical_accuracy"]["status"] == "verified"
    assert "sql" in ev_sql["claims_analysis"]["verified_technical_entities"]

    # Case C: Concrete Docker validation rule
    answer_verified_docker = (
        "Situation: We needed containerized deployments. "
        "Task: I was assigned to package our microservices into containers. "
        "Action: I created a Dockerfile using multi-stage builds and configured docker-compose volumes for local testing. "
        "Result: The container deployment reduced image footprint and passed all smoke tests."
    )
    ev_docker = evaluator.evaluate_answer(q_data, answer_verified_docker, "STAR")
    assert ev_docker["criterion_scores"]["technical_accuracy"]["status"] == "verified"
    assert "docker" in ev_docker["claims_analysis"]["verified_technical_entities"]


def test_25_unsupported_metrics_and_achievement_grounding(sample_candidate_analysis):
    """Verify unestablished metrics trigger warnings while truthful disclosures and verified metrics are handled honestly."""
    evaluator = HeuristicAnswerEvaluator()
    candidate_evidence = extract_candidate_evidence(ANALYSIS_CACHE[sample_candidate_analysis])
    q_data = {
        "question_text": "Describe the scale and performance of your projects.",
        "expected_key_points": ["Performance metrics", "System throughput"],
        "recommended_answer_framework": "STAR"
    }

    # Case A: Fabricated / unsupported performance metrics
    ans_unsupported = (
        "Situation: Our backend service handled production traffic. "
        "Task: I was responsible for performance tuning under extreme load. "
        "Action: I scaled the service and optimized connection pooling. "
        "Result: I achieved 99.99% uptime, reduced latency by 85%, and scaled the system to 500000 users."
    )
    ev_unsupported = evaluator.evaluate_answer(q_data, ans_unsupported, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_unsupported["claims_analysis"]["unsupported_claims"]) > 0
    assert ev_unsupported["criterion_scores"]["evidence_consistency"]["status"] == "warning"
    assert any("not established by your submitted resume" in w for w in ev_unsupported["evidence_grounding_warnings"])

    # Case B: Resume-supported metric (94% Macro F1 is in Harsha_ML_Resume.pdf project description)
    ans_supported = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: I was tasked with fine-tuning the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: I achieved 94% Macro F1 on the validation benchmark suite."
    )
    ev_supported = evaluator.evaluate_answer(q_data, ans_supported, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_supported["claims_analysis"]["resume_supported_claims"]) > 0
    assert ev_supported["criterion_scores"]["evidence_consistency"]["status"] == "pass"

    # Case C: Truthful candidate disclosure
    ans_disclosure = (
        "Situation: In this coursework project, we developed a prototype recommendation engine. "
        "Task: My responsibility was implementing the core matrix factorization algorithm. "
        "Action: I have not yet deployed this to production, as this was an academic project. "
        "Result: We validated the offline precision and recall on the test dataset."
    )
    ev_disclosure = evaluator.evaluate_answer(q_data, ans_disclosure, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_disclosure["claims_analysis"]["truthful_disclosures"]) > 0
    assert any("candid and honest" in s.lower() for s in ev_disclosure["strengths"])

    # Case D: General technical explanation
    ans_general = (
        "Situation: When architecting distributed databases, timeout configuration is important. "
        "Task: Explaining connection pooling behavior. "
        "Action: By default, PostgreSQL connection poolers limit threads with default timeout typically 30 seconds. "
        "Result: This prevents out-of-memory errors on concurrent client spikes."
    )
    ev_general = evaluator.evaluate_answer(q_data, ans_general, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_general["claims_analysis"]["general_technical_explanations"]) > 0
    assert len(ev_general["claims_analysis"]["unsupported_claims"]) == 0


def test_26_csrf_enforcement_all_state_changing_endpoints(sample_candidate_analysis):
    """Verify CSRF fail-closed policy on every state-changing endpoint when in production mode."""
    client = app.test_client()
    original_testing = app.config.get("TESTING")
    try:
        app.config["TESTING"] = False
        token = secrets.token_hex(32)

        # 1. POST /api/interview/evaluate
        with client.session_transaction() as sess:
            sess["csrf_token"] = token
            sess["allowed_analyses"] = [sample_candidate_analysis]

        resp_no_csrf = client.post("/api/interview/evaluate", data=json.dumps({"user_answer": "test"}), content_type="application/json")
        assert resp_no_csrf.status_code == 403

        resp_bad_csrf = client.post("/api/interview/evaluate", data=json.dumps({"user_answer": "test", "csrf_token": "bad"}), content_type="application/json")
        assert resp_bad_csrf.status_code == 403

        resp_ok_csrf = client.post("/api/interview/evaluate", data=json.dumps({"user_answer": "test", "csrf_token": token}), content_type="application/json")
        assert resp_ok_csrf.status_code == 200

        # 2. POST /api/interview/confirm-activity
        resp_confirm_no_csrf = client.post("/api/interview/confirm-activity", data=json.dumps({"activity_key": "k"}), content_type="application/json")
        assert resp_confirm_no_csrf.status_code == 403

        resp_confirm_ok = client.post("/api/interview/confirm-activity", data=json.dumps({"activity_key": "k", "csrf_token": token}), content_type="application/json")
        assert resp_confirm_ok.status_code == 200

        # 3. POST /api/interview/reset
        resp_reset_no_csrf = client.post("/api/interview/reset", data=json.dumps({}), content_type="application/json")
        assert resp_reset_no_csrf.status_code == 403

        resp_reset_ok = client.post("/api/interview/reset", data=json.dumps({"csrf_token": token}), content_type="application/json")
        assert resp_reset_ok.status_code == 200

        # 4. POST /api/interview/sessions
        resp_sess_no_csrf = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": sample_candidate_analysis}), content_type="application/json")
        assert resp_sess_no_csrf.status_code == 403

        resp_sess_ok = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": sample_candidate_analysis, "csrf_token": token}), content_type="application/json")
        assert resp_sess_ok.status_code == 201
        created_sid = resp_sess_ok.get_json()["session"]["session_id"]

        # 5. POST /api/interview-practice/submit
        resp_sub_no_csrf = client.post("/api/interview-practice/submit", data=json.dumps({"session_id": created_sid, "question_index": 0, "user_answer": "abc"}), content_type="application/json")
        assert resp_sub_no_csrf.status_code == 403

        resp_sub_ok = client.post("/api/interview-practice/submit", data=json.dumps({"session_id": created_sid, "question_index": 0, "user_answer": "abc", "csrf_token": token}), content_type="application/json")
        assert resp_sub_ok.status_code == 200

        # 6. DELETE /api/interview/sessions/<session_id>
        resp_del_no_csrf = client.delete(f"/api/interview/sessions/{created_sid}")
        assert resp_del_no_csrf.status_code == 403

        resp_del_ok = client.delete(f"/api/interview/sessions/{created_sid}", headers={"X-CSRF-Token": token})
        assert resp_del_ok.status_code == 200

    finally:
        app.config["TESTING"] = original_testing


def test_27_malformed_json_field_types_rejection(sample_candidate_analysis):
    """Verify controlled 400 responses for malformed types across all endpoints without unhandled 500s."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "valid_tok"

    token_hdr = {"X-CSRF-Token": "valid_tok"}

    # 1. Invalid mode type (int instead of str)
    r1 = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": sample_candidate_analysis, "mode": 12345}), content_type="application/json", headers=token_hdr)
    assert r1.status_code == 400
    assert "mode" in r1.get_json()["message"]

    # 2. Invalid difficulty type (list instead of str)
    r2 = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": sample_candidate_analysis, "difficulty": ["hard"]}), content_type="application/json", headers=token_hdr)
    assert r2.status_code == 400
    assert "difficulty" in r2.get_json()["message"]

    # 3. Invalid max_questions type (bool or invalid string)
    r3 = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": sample_candidate_analysis, "max_questions": True}), content_type="application/json", headers=token_hdr)
    assert r3.status_code == 400
    assert "max_questions" in r3.get_json()["message"]

    r3_str = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": sample_candidate_analysis, "max_questions": "many"}), content_type="application/json", headers=token_hdr)
    assert r3_str.status_code == 400

    # 4. Invalid target_role type (int)
    r4 = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": sample_candidate_analysis, "target_role": 999}), content_type="application/json", headers=token_hdr)
    assert r4.status_code == 400

    # 5. Invalid analysis_id type (dict)
    r5 = client.post("/api/interview/sessions", data=json.dumps({"analysis_id": {"id": 1}}), content_type="application/json", headers=token_hdr)
    assert r5.status_code == 400

    # 6. Invalid evaluate payload types (user_answer as int, expected_key_points as str)
    r6 = client.post("/api/interview/evaluate", data=json.dumps({"user_answer": 123}), content_type="application/json", headers=token_hdr)
    assert r6.status_code == 400

    r7 = client.post("/api/interview/evaluate", data=json.dumps({"expected_key_points": "not_a_list"}), content_type="application/json", headers=token_hdr)
    assert r7.status_code == 400

    r8 = client.post("/api/interview/evaluate", data=json.dumps({"important_concepts": 456}), content_type="application/json", headers=token_hdr)
    assert r8.status_code == 400

    # 7. Invalid submit types (session_id as int, question_index as bool)
    r9 = client.post("/api/interview-practice/submit", data=json.dumps({"session_id": 1234, "question_index": 0}), content_type="application/json", headers=token_hdr)
    assert r9.status_code == 400

    r10 = client.post("/api/interview-practice/submit", data=json.dumps({"session_id": "sid_str", "question_index": True}), content_type="application/json", headers=token_hdr)
    assert r10.status_code == 400


def test_28_sqlite_write_failure_observable_handling(sample_candidate_analysis, monkeypatch):
    """Verify SQLite persistence errors return 500 and are observably handled without silent data corruption."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "valid_tok"

    token_hdr = {"X-CSRF-Token": "valid_tok"}

    # Mock save_session to simulate disk I/O failure
    def mock_failing_save(self, session_data):
        raise sqlite3.OperationalError("disk I/O error: disk full")

    monkeypatch.setattr(InterviewSessionStore, "save_session", mock_failing_save)

    resp = client.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis}),
        content_type="application/json",
        headers=token_hdr
    )
    assert resp.status_code == 500
    err_json = resp.get_json()
    assert err_json["status"] == "error"
    assert "Failed to persist practice session" in err_json["message"]


# =========================================================================
# 8. Phase 5.2 Scoring, Metric Matching, Isolation & Reliability Tests
# =========================================================================


def test_29_fabricated_metrics_never_improve_scores(sample_candidate_analysis):
    """Verify unsupported/fabricated metrics never improve specificity or overall composite scores."""
    evaluator = HeuristicAnswerEvaluator()
    candidate_evidence = extract_candidate_evidence(ANALYSIS_CACHE[sample_candidate_analysis])

    q_data = {
        "question_text": "Describe your backend architecture and service performance.",
        "expected_key_points": ["Architecture design", "Service reliability"],
        "recommended_answer_framework": "STAR"
    }

    # Answer A: Honest response using verified technologies without fabricated metrics
    ans_honest = (
        "Situation: In our backend system, we needed a robust data processing service. "
        "Task: I was responsible for implementing the pipeline architecture. "
        "Action: I built the backend service using Python scripts and packaged it with Docker containers. "
        "Result: The service passed all integration tests and was deployed cleanly to the cluster."
    )
    ev_honest = evaluator.evaluate_answer(q_data, ans_honest, "STAR", candidate_evidence=candidate_evidence)

    # Answer B: Exactly identical to Answer A, but appends an unverified/fabricated metric claim
    ans_fabricated = (
        "Situation: In our backend system, we needed a robust data processing service. "
        "Task: I was responsible for implementing the pipeline architecture. "
        "Action: I built the backend service using Python scripts and packaged it with Docker containers. "
        "Result: I achieved a 99.9% latency reduction and scaled the service to 500000 concurrent users."
    )
    ev_fabricated = evaluator.evaluate_answer(q_data, ans_fabricated, "STAR", candidate_evidence=candidate_evidence)

    # 1. Fabricated answer must classify the claims as unsupported
    assert len(ev_fabricated["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_honest["claims_analysis"]["unsupported_claims"]) == 0

    # 2. Unsupported metrics must NOT increase the specificity score
    honest_spec = ev_honest["individual_criterion_scores"]["specificity_examples"]["score"]
    fab_spec = ev_fabricated["individual_criterion_scores"]["specificity_examples"]["score"]
    assert fab_spec <= honest_spec, f"Fabricated specificity ({fab_spec}) must not exceed honest ({honest_spec})"

    # 3. Overall composite score with fabricated metrics must NOT improve over honest answer
    honest_overall = ev_honest["overall_score"]
    fab_overall = ev_fabricated["overall_score"]
    assert fab_overall < honest_overall, f"Fabricated overall ({fab_overall}) must be lower than honest ({honest_overall})"


def test_30_metric_type_and_context_mismatch_rejected(sample_candidate_analysis):
    """Verify different metric types cannot support one another merely because the numeric value matches."""
    evaluator = HeuristicAnswerEvaluator()
    candidate_evidence = extract_candidate_evidence(ANALYSIS_CACHE[sample_candidate_analysis])

    q_data = {
        "question_text": "Describe your model optimization and performance accomplishments.",
        "expected_key_points": ["Model metrics", "Performance optimization"],
        "recommended_answer_framework": "STAR"
    }

    # Harsha_ML_Resume.pdf contains: 94% Macro F1 in Multimodal Semantic Matcher
    # Case A: Candidate claims 94% latency reduction (latency != accuracy/quality)
    ans_mismatched = (
        "Situation: In our multimodal semantic search project, query speed was critical. "
        "Task: My goal was to accelerate inference throughput on GPU hardware. "
        "Action: I optimized model weights and implemented custom batching routines in PyTorch. "
        "Result: I achieved a 94% reduction in latency across all endpoint requests."
    )
    ev_mismatch = evaluator.evaluate_answer(q_data, ans_mismatched, "STAR", candidate_evidence=candidate_evidence)

    # Must NOT be classified as resume_supported_claims!
    assert len(ev_mismatch["claims_analysis"]["resume_supported_claims"]) == 0
    assert len(ev_mismatch["claims_analysis"]["unsupported_claims"]) > 0
    warnings = ev_mismatch["evidence_grounding_warnings"]
    assert any("latency" in w.lower() and "different context" in w.lower() for w in warnings)

    # Case B: Candidate claims 94% Macro F1 (matches both number AND metric type)
    ans_matched = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: My goal was fine-tuning the dense encoder on domain data. "
        "Action: I trained the two-tower neural network using custom contrastive loss in PyTorch. "
        "Result: I achieved 94% Macro F1 on the validation benchmark suite."
    )
    ev_matched = evaluator.evaluate_answer(q_data, ans_matched, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_matched["claims_analysis"]["resume_supported_claims"]) > 0
    assert len(ev_matched["claims_analysis"]["unsupported_claims"]) == 0
    assert ev_matched["criterion_scores"]["evidence_consistency"]["status"] == "pass"


def test_31_sentence_scoped_technical_validation_isolation_and_negation():
    """Verify technical terms in unrelated sentences do not become verified, and negation/hypothetical usage is not verified."""
    evaluator = HeuristicAnswerEvaluator()
    q_data = {
        "question_text": "Detail your software and database implementation background.",
        "expected_key_points": ["Database design", "Language implementation"],
        "recommended_answer_framework": "STAR"
    }

    # Case A: Unrelated sentence combination
    # Python is in Sentence 1 without code/script rules.
    # SQL is in Sentence 2 with SELECT and FROM clauses.
    ans_unrelated = (
        "I have general background working with Python. "
        "In our database tier, I wrote SQL queries using SELECT, JOIN, and WHERE clauses. "
        "We also used Git repositories for version tracking."
    )
    ev_unrelated = evaluator.evaluate_answer(q_data, ans_unrelated, "STAR")
    claims = ev_unrelated["claims_analysis"]

    # SQL is verified in sentence 2
    assert "sql" in claims["verified_technical_entities"]
    # Python is in sentence 1 without rule match: must be recognized, NOT verified!
    assert "python" in claims["recognized_technical_entities"]
    assert "python" not in claims["verified_technical_entities"]

    # Case B: Negation - explicitly unused or denied technologies
    ans_negated = (
        "Situation: We evaluated several scripting languages for our pipeline. "
        "Task: Choose the appropriate technology. "
        "Action: I have never used Python for production scripts, and we did not use Docker containers. "
        "Result: We completed the deployment using alternate internal tools."
    )
    ev_negated = evaluator.evaluate_answer(q_data, ans_negated, "STAR")
    neg_claims = ev_negated["claims_analysis"]
    assert "python" not in neg_claims["verified_technical_entities"]
    assert "docker" not in neg_claims["verified_technical_entities"]

    # Case C: Hypothetical / future / merely considered statements
    ans_hypothetical = (
        "Situation: Planning future machine learning architectures. "
        "Task: Explore potential deep learning frameworks. "
        "Action: If I were to use PyTorch, I would train neural network architectures with custom loss functions. "
        "Result: This hypothetical design could improve future model iterations."
    )
    ev_hypothetical = evaluator.evaluate_answer(q_data, ans_hypothetical, "STAR")
    hypo_claims = ev_hypothetical["claims_analysis"]
    assert "pytorch" not in hypo_claims["verified_technical_entities"]
    assert "pytorch" in hypo_claims["recognized_technical_entities"]

    # Case D: Genuine technical example
    ans_genuine = (
        "Situation: We needed a data processing script. "
        "Task: Implement the processing pipeline. "
        "Action: I developed Python scripts and modules using pytest for automated test coverage. "
        "Result: All tests passed cleanly in CI."
    )
    ev_genuine = evaluator.evaluate_answer(q_data, ans_genuine, "STAR")
    assert "python" in ev_genuine["claims_analysis"]["verified_technical_entities"]


def test_32_database_read_failures_produce_observable_errors(sample_candidate_analysis, monkeypatch):
    """Verify database read failures produce observable 500 errors and do not mask outages as empty history."""
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["interview_owner_id"] = "db_failure_user"
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "valid_token"

    token_hdr = {"X-CSRF-Token": "valid_token"}

    # Mock get_session, list_sessions, get_progress to simulate SQLite database read failure
    def mock_failing_get(self, session_id, owner_id=None):
        raise sqlite3.OperationalError("disk I/O error: database is locked")

    def mock_failing_list(self, owner_id, analysis_id=None, limit=50):
        raise sqlite3.OperationalError("disk I/O error: database is corrupted")

    def mock_failing_progress(self, owner_id, analysis_id=None):
        raise sqlite3.OperationalError("disk I/O error: disk failure")

    # 1. Test InterviewSessionManager raises on read error (does not swallow)
    monkeypatch.setattr(InterviewSessionStore, "get_session", mock_failing_get)
    ACTIVE_SESSIONS.clear()
    with pytest.raises(sqlite3.OperationalError):
        InterviewSessionManager.get_session("nonexistent_sid")

    # 2. Test GET /api/interview/sessions produces 500 (not 200 empty list)
    monkeypatch.setattr(InterviewSessionStore, "list_sessions", mock_failing_list)
    resp_list = client.get("/api/interview/sessions")
    assert resp_list.status_code == 500
    assert "Database failure" in resp_list.get_json()["message"]

    # 3. Test GET /api/interview/progress produces 500 (not 200 with 0s)
    monkeypatch.setattr(InterviewSessionStore, "get_progress", mock_failing_progress)
    resp_prog = client.get("/api/interview/progress")
    assert resp_prog.status_code == 500
    assert "Database failure" in resp_prog.get_json()["message"]

    # 4. Test GET /api/interview/sessions/<id> produces 500 on database error
    resp_get = client.get("/api/interview/sessions/some_session_id")
    assert resp_get.status_code == 500
    assert "Database failure" in resp_get.get_json()["message"]

    # 5. Undo monkeypatch and verify legitimate 404 for genuinely missing record
    monkeypatch.undo()
    ACTIVE_SESSIONS.clear()
    resp_404 = client.get("/api/interview/sessions/truly_nonexistent_session")
    assert resp_404.status_code == 404
    assert "not found" in resp_404.get_json()["message"].lower()


def test_33_failed_persistence_rollback_and_no_inconsistent_in_memory_state(sample_candidate_analysis, monkeypatch):
    """Verify failed SQLite writes roll back in-memory state and do not leave orphaned sessions."""
    analysis = ANALYSIS_CACHE[sample_candidate_analysis]
    generator = InterviewQuestionGenerator(analysis)
    questions = generator.generate_questions(max_questions=2)

    # 1. Failed session creation must not leave session in ACTIVE_SESSIONS
    def mock_fail_save(self, data):
        raise sqlite3.OperationalError("disk I/O error: disk full")

    monkeypatch.setattr(InterviewSessionStore, "save_session", mock_fail_save)

    with pytest.raises(sqlite3.OperationalError):
        InterviewSessionManager.create_session(
            questions=questions,
            analysis_id=sample_candidate_analysis,
            owner_id="rollback_test_user"
        )
    # Ensure no lingering unpersisted session exists in ACTIVE_SESSIONS
    assert not any(s.owner_id == "rollback_test_user" for s in ACTIVE_SESSIONS.values())

    # 2. Failed answer submission must rollback in-memory answers and evaluations
    monkeypatch.undo()
    session = InterviewSessionManager.create_session(
        questions=questions,
        analysis_id=sample_candidate_analysis,
        owner_id="rollback_answer_user"
    )
    sid = session.session_id

    # Submit valid first answer successfully
    res1 = session.submit_answer(0, "Valid initial answer using Python.")
    assert "0" in session.answers
    assert session.answers["0"] == "Valid initial answer using Python."

    # Now make store fail on subsequent answer save
    monkeypatch.setattr(InterviewSessionStore, "save_session", mock_fail_save)

    with pytest.raises(sqlite3.OperationalError):
        session.submit_answer(0, "Attempted corrupting answer text.")

    # State must be rolled back to original initial answer!
    assert session.answers["0"] == "Valid initial answer using Python."
    assert session.evaluations["0"]["overall_score"] == res1["overall_score"]

    # 3. Failed completion must rollback is_completed and completed_at
    assert session.is_completed is False
    assert session.completed_at is None

    with pytest.raises(sqlite3.OperationalError):
        session.complete_session()

    assert session.is_completed is False
    assert session.completed_at is None


def test_34_cross_user_reset_and_deletion_rejected(sample_candidate_analysis):
    """Verify cross-user session reset and deletion are strictly rejected with 403 Forbidden."""
    client_a = app.test_client()
    with client_a.session_transaction() as sess:
        sess["interview_owner_id"] = "legit_user_a"
        sess["allowed_analyses"] = [sample_candidate_analysis]
        sess["csrf_token"] = "token_a"

    token_hdr_a = {"X-CSRF-Token": "token_a"}

    # User A creates a session
    resp_create = client_a.post(
        "/api/interview/sessions",
        data=json.dumps({"analysis_id": sample_candidate_analysis}),
        content_type="application/json",
        headers=token_hdr_a
    )
    assert resp_create.status_code == 201
    sid_a = resp_create.get_json()["session"]["session_id"]

    # User B attempts to delete User A's session via DELETE endpoint
    client_b = app.test_client()
    with client_b.session_transaction() as sess:
        sess["interview_owner_id"] = "attacker_user_b"
        sess["csrf_token"] = "token_b"

    token_hdr_b = {"X-CSRF-Token": "token_b"}

    resp_del_b = client_b.delete(f"/api/interview/sessions/{sid_a}", headers=token_hdr_b)
    assert resp_del_b.status_code == 403
    assert "unauthorized" in resp_del_b.get_json()["message"].lower()

    # User B attempts to reset User A's session via POST /api/interview/reset
    resp_reset_b = client_b.post(
        "/api/interview/reset",
        data=json.dumps({"session_id": sid_a}),
        content_type="application/json",
        headers=token_hdr_b
    )
    assert resp_reset_b.status_code == 403
    assert "unauthorized" in resp_reset_b.get_json()["message"].lower()

    # Verify User A's session was NOT deleted and is still intact
    resp_check = client_a.get(f"/api/interview/sessions/{sid_a}")
    assert resp_check.status_code == 200

    # User A performs legitimate reset of their own session
    resp_reset_a = client_a.post(
        "/api/interview/reset",
        data=json.dumps({"session_id": sid_a}),
        content_type="application/json",
        headers=token_hdr_a
    )
    assert resp_reset_a.status_code == 200
    assert resp_reset_a.get_json()["status"] == "reset"


# =========================================================================
# 9. Phase 5.3 Adversarial Metric Grounding & Scoring Integrity Tests
# =========================================================================


def test_35_adversarial_metric_grounding_and_scoring_integrity(sample_candidate_analysis):
    """
    Adversarial test suite covering all 8 Phase 5.3 metric verification and scoring constraints:
    1. No resume evidence + fabricated personal metric: no specificity bonus.
    2. Resume has 94% Macro F1; answer claims 94% latency reduction: unsupported.
    3. Resume has 94 seconds; answer claims 94%: unit mismatch, unsupported.
    4. Same number appears in an unrelated project: project attribution mismatch, unsupported.
    5. Same metric category appears in a different achievement: task context mismatch, unsupported.
    6. General theoretical numeric explanation: not classified as a personal achievement.
    7. Truthful disclosure of missing metrics: no penalty for honesty.
    8. Existing supported metric test continues to pass with full credit.
    """
    evaluator = HeuristicAnswerEvaluator()
    candidate_evidence = extract_candidate_evidence(ANALYSIS_CACHE[sample_candidate_analysis])

    q_data = {
        "question_text": "Describe your technical implementation results and performance outcomes.",
        "expected_key_points": ["Implementation architecture", "Verified results"],
        "recommended_answer_framework": "STAR"
    }

    # Case 1: No resume evidence + fabricated personal metric: no specificity bonus
    ans_honest_no_resume = (
        "Situation: In our data tier, we needed reliable processing. "
        "Task: I was responsible for data transformation. "
        "Action: I developed Python scripts to transform records and tested them with pytest. "
        "Result: The pipeline ran smoothly and passed all unit tests."
    )
    ev_h_no_res = evaluator.evaluate_answer(q_data, ans_honest_no_resume, "STAR", candidate_evidence=None)

    ans_fab_no_resume = (
        "Situation: In our data tier, we needed reliable processing. "
        "Task: I was responsible for data transformation. "
        "Action: I developed Python scripts to transform records and tested them with pytest. "
        "Result: I achieved 99.9% uptime and scaled the system to 500000 concurrent users."
    )
    ev_f_no_res = evaluator.evaluate_answer(q_data, ans_fab_no_resume, "STAR", candidate_evidence=None)

    assert len(ev_f_no_res["claims_analysis"]["candidate_self_reported_claims"]) > 0
    # Assert NO specificity bonus is awarded for unverified personal metrics without resume
    h_spec = ev_h_no_res["individual_criterion_scores"]["specificity_examples"]["score"]
    f_spec = ev_f_no_res["individual_criterion_scores"]["specificity_examples"]["score"]
    assert f_spec <= h_spec, f"Self-reported metrics ({f_spec}) must not increase specificity over honest answer ({h_spec})"
    # Assert overall composite score with fabricated metrics never improves over honest answer
    assert ev_f_no_res["overall_score"] < ev_h_no_res["overall_score"]

    # Case 2: Resume has 94% Macro F1; answer claims 94% latency reduction: unsupported
    ans_c2 = (
        "Situation: In our multimodal semantic search project, query speed was critical. "
        "Task: Accelerate inference pipeline throughput. "
        "Action: I optimized model weights and batching routines in PyTorch. "
        "Result: I achieved 94% reduction in latency across all endpoint requests."
    )
    ev_c2 = evaluator.evaluate_answer(q_data, ans_c2, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c2["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c2["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("latency" in w.lower() and "different context" in w.lower() for w in ev_c2["evidence_grounding_warnings"])

    # Case 3: Resume has 94 seconds; answer claims 94%: do not assume equivalent units
    ev_seconds = {
        "projects": [{
            "title": "Compilation Pipeline",
            "description": "Optimized container build pipeline and reduced compile time to 94 seconds.",
            "exact_excerpt": "reduced compile time to 94 seconds."
        }]
    }
    ans_c3 = (
        "Situation: Build times were excessively slow. "
        "Task: Optimize compiler runtime. "
        "Action: I tuned build scripts and docker layers. "
        "Result: I achieved a 94% reduction in build overhead."
    )
    ev_c3 = evaluator.evaluate_answer(q_data, ans_c3, "STAR", candidate_evidence=ev_seconds)
    assert len(ev_c3["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c3["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("unit" in w.lower() for w in ev_c3["evidence_grounding_warnings"])

    # Case 4: Same number appears in an unrelated project: not sufficient evidence
    ev_unrelated_proj = {
        "projects": [
            {
                "title": "Fraud Detection Pipeline",
                "description": "Processed financial transactions using XGBoost and Pandas.",
                "exact_excerpt": "Processed financial transactions."
            },
            {
                "title": "Multimodal Semantic Matcher",
                "description": "Dense vector retrieval achieving 94% Macro F1.",
                "exact_excerpt": "Dense vector retrieval achieving 94% Macro F1."
            }
        ]
    }
    ans_c4 = (
        "Situation: We were classifying fraudulent financial transactions. "
        "Task: Maximize precision on rare fraud classes. "
        "Action: I developed tree-based models and tuned hyperparameters. "
        "Result: In my Fraud Detection Pipeline project, I achieved 94% Macro F1 on the benchmark."
    )
    ev_c4 = evaluator.evaluate_answer(q_data, ans_c4, "STAR", candidate_evidence=ev_unrelated_proj)
    assert len(ev_c4["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c4["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("fraud detection pipeline" in w.lower() and "multimodal semantic matcher" in w.lower() for w in ev_c4["evidence_grounding_warnings"])

    # Case 5: Same metric category appears in a different achievement: not sufficient evidence
    ans_c5 = (
        "Situation: Developing an automated audio transcription system. "
        "Task: Maximize acoustic classification accuracy. "
        "Action: I built an acoustic feature extractor and acoustic classifier. "
        "Result: In our audio pipeline, I achieved 94% accuracy in speech audio recognition."
    )
    ev_c5 = evaluator.evaluate_answer(q_data, ans_c5, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c5["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c5["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("speech" in w.lower() or "audio" in w.lower() for w in ev_c5["evidence_grounding_warnings"])

    # Case 6: General theoretical numeric explanation: not classified as a personal achievement
    ans_c6 = (
        "Situation: When configuring distributed architectures, timeout values matter. "
        "Task: Explain connection architecture. "
        "Action: By default, Python worker processes typically timeout after 30 seconds. "
        "Result: This prevents runaway transactions on saturated connection pools."
    )
    ev_c6 = evaluator.evaluate_answer(q_data, ans_c6, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c6["claims_analysis"]["general_technical_explanations"]) > 0
    assert len(ev_c6["claims_analysis"]["unsupported_claims"]) == 0
    assert not any("30" in w or "timeout" in w.lower() or "metric" in w.lower() for w in ev_c6["evidence_grounding_warnings"])

    # Case 7: Truthful disclosure of missing metrics: no penalty for honesty
    ans_c7 = (
        "Situation: In this coursework project, we developed an experimental recommendation prototype. "
        "Task: Design the core collaborative filtering matrix. "
        "Action: I have not yet deployed this to production, as this was an academic project, so I do not have real-world metrics. "
        "Result: We verified offline accuracy on the validation split."
    )
    ev_c7 = evaluator.evaluate_answer(q_data, ans_c7, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c7["claims_analysis"]["truthful_disclosures"]) > 0
    assert len(ev_c7["claims_analysis"]["unsupported_claims"]) == 0
    assert len(ev_c7["evidence_grounding_warnings"]) == 0
    assert any("candid and honest" in s.lower() for s in ev_c7["strengths"])

    # Case 8: Existing supported metric test continues to pass with full credit
    ans_c8 = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: Fine-tune the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: In our multimodal semantic search project, I achieved 94% Macro F1 on the validation benchmark suite."
    )
    ev_c8 = evaluator.evaluate_answer(q_data, ans_c8, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c8["claims_analysis"]["resume_supported_claims"]) > 0
    assert len(ev_c8["claims_analysis"]["unsupported_claims"]) == 0
    assert ev_c8["criterion_scores"]["evidence_consistency"]["status"] == "pass"
    assert ev_c8["individual_criterion_scores"]["specificity_examples"]["score"] >= 60.0


def test_36_strict_numeric_and_unit_verification(sample_candidate_analysis):
    """
    Phase 5.4 regression test suite covering strict numeric and unit verification:
    1. Resume 94.5%, answer 94% -> unsupported.
    2. Resume 94%, answer 94.5% -> unsupported.
    3. Resume 94.0%, answer 94% -> unsupported under explicit strict precision policy.
    4. Resume 94 with no unit, answer 94% -> unsupported (fail closed on missing resume unit).
    5. Resume 94 with no unit, answer 94 seconds -> unsupported (fail closed on missing resume unit).
    6. Resume 1,000 requests, answer 1000 requests -> accepted as equivalent through safe normalization.
    7. Resume 50%, answer 5% -> unsupported.
    8. Existing valid 94% Macro F1 evidence -> still supported.
    9. Existing project attribution and domain mismatch tests -> remain passing.
    Asserts both claim classification and specificity/overall scoring: unsupported claims never receive metric credit.
    """
    evaluator = HeuristicAnswerEvaluator()
    candidate_evidence = extract_candidate_evidence(ANALYSIS_CACHE[sample_candidate_analysis])

    q_data = {
        "question_text": "Describe your technical implementation results and quantified outcomes.",
        "expected_key_points": ["Implementation architecture", "Verified results"],
        "recommended_answer_framework": "STAR"
    }

    # Baseline honest answer without any numeric metric
    ans_baseline = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: Fine-tune the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: In our multimodal semantic search project, the model demonstrated superior ranking on validation benchmarks."
    )
    ev_baseline = evaluator.evaluate_answer(q_data, ans_baseline, "STAR", candidate_evidence=candidate_evidence)
    baseline_spec = ev_baseline["individual_criterion_scores"]["specificity_examples"]["score"]
    baseline_score = ev_baseline["overall_score"]

    # Case 1: Resume 94.5%, answer 94% -> unsupported
    ev_94_5 = {
        "projects": [{
            "title": "Multimodal Semantic Matcher",
            "description": "Dense vector retrieval achieving 94.5% Macro F1 with PyTorch.",
            "exact_excerpt": "achieving 94.5% Macro F1 with PyTorch."
        }]
    }
    ans_c1 = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: Fine-tune the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: In our multimodal semantic search project, I achieved 94% Macro F1 on the benchmark."
    )
    ev_c1 = evaluator.evaluate_answer(q_data, ans_c1, "STAR", candidate_evidence=ev_94_5)
    assert len(ev_c1["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c1["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("94" in w and ("94.5" in w or "not evidenced" in w.lower()) for w in ev_c1["evidence_grounding_warnings"])
    assert ev_c1["individual_criterion_scores"]["specificity_examples"]["score"] <= baseline_spec
    assert ev_c1["overall_score"] < baseline_score

    # Case 2: Resume 94%, answer 94.5% -> unsupported
    ans_c2 = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: Fine-tune the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: In our multimodal semantic search project, I achieved 94.5% Macro F1 on the benchmark."
    )
    ev_c2 = evaluator.evaluate_answer(q_data, ans_c2, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c2["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c2["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("94.5" in w for w in ev_c2["evidence_grounding_warnings"])
    assert ev_c2["individual_criterion_scores"]["specificity_examples"]["score"] <= baseline_spec
    assert ev_c2["overall_score"] < baseline_score

    # Case 3: Resume 94.0%, answer 94% -> unsupported under explicit strict precision policy
    ev_94_0 = {
        "projects": [{
            "title": "Multimodal Semantic Matcher",
            "description": "Dense vector retrieval achieving 94.0% Macro F1 with PyTorch.",
            "exact_excerpt": "achieving 94.0% Macro F1 with PyTorch."
        }]
    }
    ans_c3 = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: Fine-tune the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: In our multimodal semantic search project, I achieved 94% Macro F1 on the benchmark."
    )
    ev_c3 = evaluator.evaluate_answer(q_data, ans_c3, "STAR", candidate_evidence=ev_94_0)
    assert len(ev_c3["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c3["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("94" in w and ("precision" in w.lower() or "strict precision" in w.lower() or "94.0" in w) for w in ev_c3["evidence_grounding_warnings"])
    assert ev_c3["individual_criterion_scores"]["specificity_examples"]["score"] <= baseline_spec
    assert ev_c3["overall_score"] < baseline_score

    # Case 4: Resume 94 with no unit, answer 94% -> unsupported (fail closed on missing resume unit)
    ev_94_no_unit = {
        "projects": [{
            "title": "Multimodal Semantic Matcher",
            "description": "Implemented cross-modal dense retrieval with PyTorch, completing 94 benchmark runs.",
            "exact_excerpt": "completing 94 benchmark runs."
        }]
    }
    ans_c4 = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: Fine-tune the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: In our multimodal semantic search project, I achieved 94% Macro F1 on the benchmark."
    )
    ev_c4 = evaluator.evaluate_answer(q_data, ans_c4, "STAR", candidate_evidence=ev_94_no_unit)
    assert len(ev_c4["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c4["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("compatible unit" in w.lower() or "unit" in w.lower() for w in ev_c4["evidence_grounding_warnings"])
    assert ev_c4["individual_criterion_scores"]["specificity_examples"]["score"] <= baseline_spec
    assert ev_c4["overall_score"] < baseline_score

    # Case 5: Resume 94 with no unit, answer 94 seconds -> unsupported (fail closed on missing resume unit)
    ans_c5 = (
        "Situation: Build times were excessively slow. "
        "Task: Optimize compiler runtime. "
        "Action: I tuned build scripts and docker layers. "
        "Result: I achieved 94 seconds runtime for the full compilation suite."
    )
    ev_c5 = evaluator.evaluate_answer(q_data, ans_c5, "STAR", candidate_evidence=ev_94_no_unit)
    assert len(ev_c5["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c5["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("compatible unit" in w.lower() or "unit" in w.lower() for w in ev_c5["evidence_grounding_warnings"])
    assert ev_c5["individual_criterion_scores"]["specificity_examples"]["score"] <= baseline_spec
    assert ev_c5["overall_score"] < baseline_score

    # Case 6: Resume 1,000 requests, answer 1000 requests -> accept only if safely normalized
    ev_1000_comma = {
        "skills": ["Python", "Flask"],
        "projects": [{
            "title": "High-Throughput API Gateway",
            "technologies": "Python, Flask",
            "description": "Engineered asynchronous API Gateway with Python and Flask, serving 1,000 requests per second.",
            "exact_excerpt": "serving 1,000 requests per second."
        }]
    }
    ans_c6 = (
        "Situation: Our API gateway needed to handle heavy traffic spikes. "
        "Task: Optimize request processing concurrency in Python and Flask. "
        "Action: I implemented non-blocking asynchronous event loops with connection pooling. "
        "Result: In our High-Throughput API Gateway project, I served 1000 requests per second with high stability."
    )
    ev_c6 = evaluator.evaluate_answer(q_data, ans_c6, "STAR", candidate_evidence=ev_1000_comma)
    assert len(ev_c6["claims_analysis"]["resume_supported_claims"]) > 0
    assert len(ev_c6["claims_analysis"]["unsupported_claims"]) == 0
    assert ev_c6["criterion_scores"]["evidence_consistency"]["status"] == "pass"
    assert ev_c6["individual_criterion_scores"]["specificity_examples"]["score"] >= 60.0

    # Case 7: Resume 50%, answer 5% -> unsupported
    ev_50 = {
        "projects": [{
            "title": "Model Compression",
            "description": "Quantized deep neural networks with PyTorch, achieving 50% reduction in memory.",
            "exact_excerpt": "achieving 50% reduction in memory."
        }]
    }
    ans_c7 = (
        "Situation: Embedded inference required minimal memory footprints. "
        "Task: Compress model weights without degrading accuracy. "
        "Action: I applied 8-bit dynamic quantization in PyTorch. "
        "Result: In our Model Compression project, I achieved 5% reduction in model size."
    )
    ev_c7 = evaluator.evaluate_answer(q_data, ans_c7, "STAR", candidate_evidence=ev_50)
    assert len(ev_c7["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c7["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("5%" in w or "not evidenced" in w.lower() for w in ev_c7["evidence_grounding_warnings"])
    assert ev_c7["individual_criterion_scores"]["specificity_examples"]["score"] <= baseline_spec
    assert ev_c7["overall_score"] < baseline_score

    # Case 8: Existing valid 94% Macro F1 evidence -> still supported
    ans_c8 = (
        "Situation: In our multimodal semantic search project, retrieval accuracy was critical. "
        "Task: Fine-tune the dense encoder without overfitting. "
        "Action: I developed a two-tower neural network with custom contrastive loss in PyTorch. "
        "Result: In our multimodal semantic search project, I achieved 94% Macro F1 on the benchmark."
    )
    ev_c8 = evaluator.evaluate_answer(q_data, ans_c8, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c8["claims_analysis"]["resume_supported_claims"]) > 0
    assert len(ev_c8["claims_analysis"]["unsupported_claims"]) == 0
    assert ev_c8["criterion_scores"]["evidence_consistency"]["status"] == "pass"
    assert ev_c8["individual_criterion_scores"]["specificity_examples"]["score"] >= 60.0

    # Case 9: Existing project attribution and domain mismatch tests remain passing
    # Attribution mismatch
    ev_attr_mismatch = {
        "projects": [
            {"title": "Fraud Detection Pipeline", "description": "Processed financial transactions."},
            {"title": "Multimodal Semantic Matcher", "description": "Dense vector retrieval achieving 94% Macro F1."}
        ]
    }
    ans_c9_attr = (
        "Situation: We were classifying fraudulent financial transactions. "
        "Task: Maximize precision on rare fraud classes. "
        "Action: I developed tree-based models and tuned hyperparameters. "
        "Result: In my Fraud Detection Pipeline project, I achieved 94% Macro F1 on the benchmark."
    )
    ev_c9_attr = evaluator.evaluate_answer(q_data, ans_c9_attr, "STAR", candidate_evidence=ev_attr_mismatch)
    assert len(ev_c9_attr["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c9_attr["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("fraud detection pipeline" in w.lower() and "multimodal semantic matcher" in w.lower() for w in ev_c9_attr["evidence_grounding_warnings"])

    # Domain mismatch
    ans_c9_domain = (
        "Situation: Developing an automated audio transcription system. "
        "Task: Maximize acoustic classification accuracy. "
        "Action: I built an acoustic feature extractor and acoustic classifier. "
        "Result: In our audio pipeline, I achieved 94% accuracy in speech audio recognition."
    )
    ev_c9_domain = evaluator.evaluate_answer(q_data, ans_c9_domain, "STAR", candidate_evidence=candidate_evidence)
    assert len(ev_c9_domain["claims_analysis"]["unsupported_claims"]) > 0
    assert len(ev_c9_domain["claims_analysis"]["resume_supported_claims"]) == 0
    assert any("speech" in w.lower() or "audio" in w.lower() for w in ev_c9_domain["evidence_grounding_warnings"])
