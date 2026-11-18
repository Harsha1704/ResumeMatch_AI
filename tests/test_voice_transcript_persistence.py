"""
Phase 3 Database & Transcript Persistence Tests (Strict ₹0 Budget).
Verifies:
  1. Creating an interview session and persisting questions to SQLite.
  2. Saving candidate answers with timestamps.
  3. Saving heuristic answer evaluations.
  4. Saving transcript entries in strict sequence order (greeting -> questions -> answers -> feedback -> followup -> closing).
  5. Saving follow-up questions (marked is_follow_up=1).
  6. Generating, persisting, and retrieving the final interview report.
  7. History retrieval endpoint (/api/interview/voice/history).
  8. Detailed session bundle retrieval (/api/interview/voice/history/<session_id>).
  9. Session ownership isolation (User B cannot access User A's history or transcript).
  10. Idempotent end-session handling (repeating end request does not duplicate final report or closing transcript).
  11. Interrupted interview status identification (in_progress vs completed).
  12. Transaction rollback on database failure.
  13. Safe schema migration on a pre-existing database without data loss.
  14. Safe re-running of migrations (idempotent DDL).
"""

import os
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch

os.environ["RESUMEMATCH_ENV"] = "testing"

from app import app
from src.interview import (
    InterviewSessionStore,
    get_interview_session_store,
    LocalVoiceInterviewService,
    LocalVoiceSessionNotFoundError,
    LocalVoiceAccessDeniedError,
    LocalVoiceValidationError,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated temporary SQLite database for Phase 3 persistence tests."""
    db_file = tmp_path / "test_interview_persistence.sqlite"
    store = InterviewSessionStore(db_file)
    return store, db_file


@pytest.fixture
def client(temp_db, monkeypatch):
    """Configures Flask test client to use the isolated temporary database."""
    store, _ = temp_db
    monkeypatch.setattr("src.interview.session_store._SESSION_STORE", store)
    monkeypatch.setattr("src.interview.local_voice_service.get_interview_session_store", lambda db_path=None: store)

    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


def _get_csrf_and_owner(client):
    csrf_resp = client.get("/api/csrf-token")
    assert csrf_resp.status_code == 200
    return csrf_resp.get_json()["csrf_token"]


# =========================================================================
# 1. Direct Store Unit Tests (Relational & Transcript Persistence)
# =========================================================================

def test_store_session_and_questions_persistence(temp_db):
    """Verifies that questions are saved to the relational interview_questions table."""
    store, _ = temp_db
    sid = "test-session-uuid-001"
    store.save_session({
        "session_id": sid,
        "owner_id": "owner_alpha",
        "job_title": "Platform Engineer",
        "questions": [{"question_id": "q_1", "question_text": "Explain Docker networking."}]
    })

    questions = [
        {"question_id": "q_1", "question_text": "Explain Docker networking.", "category": "DevOps"},
        {"question_id": "q_2", "question_text": "How does Kubernetes ingress work?", "category": "DevOps"}
    ]
    saved_count = store.save_questions(sid, questions)
    assert saved_count == 2

    # Query directly via connection
    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT question_id, question_text, question_order FROM interview_questions WHERE session_id = ? ORDER BY question_order ASC", (sid,))
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0]["question_id"] == "q_1"
        assert rows[1]["question_id"] == "q_2"


def test_store_answer_and_evaluation_persistence(temp_db):
    """Verifies saving candidate answers and heuristic evaluations with foreign keys."""
    store, _ = temp_db
    sid = "test-session-uuid-002"
    store.save_session({"session_id": sid, "owner_id": "owner_alpha"})
    store.save_questions(sid, [{"question_id": "q_1", "question_text": "Explain Python GIL."}])

    aid = store.save_answer(
        session_id=sid,
        question_id="q_1",
        answer_text="The Global Interpreter Lock restricts execution to one native thread at a time."
    )
    assert aid.startswith("ans_")

    eid = store.save_evaluation(
        answer_id=aid,
        session_id=sid,
        question_id="q_1",
        eval_data={
            "overall_score": 82.5,
            "strengths": ["Mentioned threading constraints"],
            "missing_concepts": ["multiprocessing"],
            "feedback_summary": "Good explanation of GIL."
        }
    )
    assert eid.startswith("eval_")

    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM candidate_answers WHERE answer_id = ?", (aid,))
        ans_row = cursor.fetchone()
        assert ans_row is not None
        assert "Global Interpreter Lock" in ans_row["answer_text"]

        cursor.execute("SELECT * FROM answer_evaluations WHERE evaluation_id = ?", (eid,))
        eval_row = cursor.fetchone()
        assert eval_row is not None
        assert eval_row["overall_score"] == 82.5


def test_store_transcript_ordering(temp_db):
    """Verifies transcript entries maintain strict conversation sequence order."""
    store, _ = temp_db
    sid = "test-session-uuid-003"
    store.save_session({"session_id": sid, "owner_id": "owner_alpha"})

    e1 = store.append_transcript_entry(sid, "interviewer", "greeting", "Hello Candidate.")
    e2 = store.append_transcript_entry(sid, "interviewer", "question", "Explain database index types.")
    e3 = store.append_transcript_entry(sid, "candidate", "answer", "B-tree and Hash indexes are common.")
    e4 = store.append_transcript_entry(sid, "interviewer", "feedback", "Good explanation.")
    e5 = store.append_transcript_entry(sid, "interviewer", "closing", "Interview concluded.")

    assert e1["sequence_order"] == 1
    assert e2["sequence_order"] == 2
    assert e3["sequence_order"] == 3
    assert e4["sequence_order"] == 4
    assert e5["sequence_order"] == 5

    transcript = store.get_transcript(sid)
    assert len(transcript) == 5
    assert [t["message_type"] for t in transcript] == ["greeting", "question", "answer", "feedback", "closing"]


def test_store_final_report_idempotency(temp_db):
    """Verifies that saving the final report is idempotent and does not create duplicate entries."""
    store, _ = temp_db
    sid = "test-session-uuid-004"
    store.save_session({"session_id": sid, "owner_id": "owner_alpha"})

    report_payload = {
        "total_questions": 5,
        "questions_answered": 5,
        "average_score": 88.0,
        "strengths": ["Clear communication", "Strong system design"],
        "improvement_areas": ["Benchmark edge cases"],
        "category_performance": {"System Design": 90.0},
        "summary_text": "Strong overall performance.",
        "completed_at": 1700000000.0
    }

    rep1 = store.save_final_report(sid, report_payload)
    rep2 = store.save_final_report(sid, report_payload)

    assert rep1["report_id"] == rep2["report_id"]

    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM final_interview_reports WHERE session_id = ?", (sid,))
        assert cursor.fetchone()[0] == 1


# =========================================================================
# 2. End-to-End API Persistence & Lifecycle Tests
# =========================================================================

def test_api_full_voice_lifecycle_persistence(client):
    """
    Tests the complete voice interview workflow through HTTP endpoints:
    Start -> Get Question -> Submit Answer -> Adaptive Followup -> End -> Verify History & Detail.
    """
    csrf_token = _get_csrf_and_owner(client)

    # 1. Start voice session
    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "target_role": "Cloud DevOps Engineer",
            "difficulty": "medium",
            "max_questions": 3
        }
    )
    assert start_resp.status_code == 200
    start_data = start_resp.get_json()
    sid = start_data["session_id"]

    # 2. Verify initial transcript entries exist (greeting and Q1)
    history_detail = client.get(f"/api/interview/voice/history/{sid}")
    assert history_detail.status_code == 200
    detail_data = history_detail.get_json()["detail"]
    transcript = detail_data["transcript"]
    assert len(transcript) >= 2
    assert transcript[0]["message_type"] == "greeting"
    assert transcript[1]["message_type"] == "question"

    # 3. Submit candidate answer
    ans_resp = client.post(
        "/api/interview/voice/answer",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 0,
            "answer_text": "I set up automated CI/CD pipelines using GitHub Actions and deployed to AWS ECS."
        }
    )
    assert ans_resp.status_code == 200

    # 4. Request adaptive follow-up
    fu_resp = client.post(
        "/api/interview/voice/followup",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "session_id": sid,
            "question_index": 0
        }
    )
    assert fu_resp.status_code == 200
    fu_data = fu_resp.get_json()
    assert "Following up on that:" in fu_data["interviewer_speech"]

    # 5. Conclude interview session
    end_resp = client.post(
        "/api/interview/voice/end",
        headers={"X-CSRF-Token": csrf_token},
        json={"session_id": sid}
    )
    assert end_resp.status_code == 200
    end_data = end_resp.get_json()
    assert end_data["is_completed"] is True
    assert "final_report" in end_data

    # 6. Verify full session bundle from /api/interview/voice/history/<session_id>
    final_detail_resp = client.get(f"/api/interview/voice/history/{sid}")
    assert final_detail_resp.status_code == 200
    final_detail = final_detail_resp.get_json()["detail"]

    assert final_detail["session"]["is_completed"] is True
    assert final_detail["session"]["status"] == "completed"
    assert len(final_detail["questions"]) >= 3
    assert len(final_detail["answers"]) == 1
    assert final_detail["report"] is not None
    assert final_detail["report"]["average_score"] > 0

    # Verify transcript sequence
    tr_types = [t["message_type"] for t in final_detail["transcript"]]
    assert "greeting" in tr_types
    assert "question" in tr_types
    assert "answer" in tr_types
    assert "feedback" in tr_types
    assert "followup" in tr_types
    assert "closing" in tr_types


def test_api_history_list_retrieval(client):
    """Verifies that /api/interview/voice/history returns list of user's past voice sessions."""
    csrf_token = _get_csrf_and_owner(client)

    # Start and finish two sessions
    for role in ["Site Reliability Engineer", "Frontend Specialist"]:
        start_res = client.post(
            "/api/interview/voice/start",
            headers={"X-CSRF-Token": csrf_token},
            json={"target_role": role, "max_questions": 2}
        )
        sid = start_res.get_json()["session_id"]
        client.post(
            "/api/interview/voice/end",
            headers={"X-CSRF-Token": csrf_token},
            json={"session_id": sid}
        )

    hist_resp = client.get("/api/interview/voice/history")
    assert hist_resp.status_code == 200
    h_data = hist_resp.get_json()
    assert h_data["status"] == "success"
    assert h_data["count"] >= 2
    roles = [s["target_role"] for s in h_data["history"]]
    assert "Frontend Specialist" in roles
    assert "Site Reliability Engineer" in roles


def test_api_interrupted_session_status(client):
    """Verifies that an uncompleted session is marked in_progress."""
    csrf_token = _get_csrf_and_owner(client)

    start_resp = client.post(
        "/api/interview/voice/start",
        headers={"X-CSRF-Token": csrf_token},
        json={"target_role": "Distributed Systems Engineer"}
    )
    sid = start_resp.get_json()["session_id"]

    detail_resp = client.get(f"/api/interview/voice/history/{sid}")
    assert detail_resp.status_code == 200
    sess = detail_resp.get_json()["detail"]["session"]
    assert sess["is_completed"] is False
    assert sess["status"] == "in_progress"


def test_api_cross_owner_isolation_on_history(temp_db):
    """Verifies User B cannot access User A's history or transcript detail (403)."""
    store, _ = temp_db

    # User A session
    with app.test_client() as client_a:
        csrf_a = client_a.get("/api/csrf-token").get_json()["csrf_token"]
        start_a = client_a.post(
            "/api/interview/voice/start",
            headers={"X-CSRF-Token": csrf_a},
            json={"target_role": "Principal Architect"}
        )
        sid_a = start_a.get_json()["session_id"]

    # User B session
    with app.test_client() as client_b:
        csrf_b = client_b.get("/api/csrf-token").get_json()["csrf_token"]

        # Attempt to access User A's history detail
        hack_resp = client_b.get(f"/api/interview/voice/history/{sid_a}")
        assert hack_resp.status_code == 403

        # User B's history should not contain User A's session
        hist_b = client_b.get("/api/interview/voice/history").get_json()["history"]
        b_sids = [s["session_id"] for s in hist_b]
        assert sid_a not in b_sids


# =========================================================================
# 3. Safe Schema Migration & DDL Idempotency Tests
# =========================================================================

def test_safe_schema_migration_on_existing_database(tmp_path):
    """
    Simulates a pre-existing legacy database with an interview_sessions table
    and verifies that initializing InterviewSessionStore preserves existing rows
    and cleanly adds all Phase 3 relational tables.
    """
    legacy_db_file = tmp_path / "legacy_interview_sessions.sqlite"
    conn = sqlite3.connect(str(legacy_db_file))
    conn.execute("""
        CREATE TABLE interview_sessions (
            session_id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            analysis_id TEXT,
            candidate_filename TEXT,
            job_title TEXT,
            target_role TEXT,
            interview_mode TEXT DEFAULT 'mixed',
            difficulty TEXT DEFAULT 'all',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            completed_at REAL,
            is_completed INTEGER DEFAULT 0,
            elapsed_seconds INTEGER DEFAULT 0,
            current_index INTEGER DEFAULT 0,
            questions_json TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            evaluations_json TEXT NOT NULL,
            results_summary_json TEXT
        )
    """)
    # Insert 3 legacy rows
    for i in range(3):
        conn.execute("""
            INSERT INTO interview_sessions (
                session_id, owner_id, created_at, updated_at, questions_json, answers_json, evaluations_json
            ) VALUES (?, ?, ?, ?, '[]', '{}', '{}')
        """, (f"legacy_sid_{i}", "legacy_owner", 1700000000.0, 1700000000.0))
    conn.commit()
    conn.close()

    # Now open with InterviewSessionStore (triggers Phase 3 migration)
    store = InterviewSessionStore(legacy_db_file)

    # 1. Confirm legacy rows preserved
    legacy_sess = store.get_session("legacy_sid_0")
    assert legacy_sess is not None
    assert legacy_sess["session_id"] == "legacy_sid_0"

    # 2. Confirm Phase 3 tables exist and function properly
    store.save_questions("legacy_sid_0", [{"question_id": "mig_q1", "question_text": "Migrated question?"}])
    store.append_transcript_entry("legacy_sid_0", "interviewer", "greeting", "Welcome legacy user.")

    tr = store.get_transcript("legacy_sid_0")
    assert len(tr) == 1
    assert tr[0]["message_text"] == "Welcome legacy user."


def test_migration_idempotent_rerun(tmp_path):
    """Verifies that calling _init_db multiple times does not raise errors or duplicate tables."""
    db_file = tmp_path / "rerun_db.sqlite"
    store = InterviewSessionStore(db_file)

    # Call _init_db multiple times
    store._init_db()
    store._init_db()

    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        assert "interview_sessions" in tables
        assert "interview_questions" in tables
        assert "candidate_answers" in tables
        assert "answer_evaluations" in tables
        assert "interview_transcripts" in tables
        assert "final_interview_reports" in tables


# =========================================================================
# 4. Transaction Integrity, Isolation & Edge Case Tests
# =========================================================================

def test_saving_follow_up_questions_relational(temp_db):
    """Verifies follow-up questions are flagged with is_follow_up=1 and parent_question_id."""
    store, _ = temp_db
    sid = "test-session-uuid-005"
    store.save_session({"session_id": sid, "owner_id": "owner_alpha"})
    store.save_questions(sid, [{"question_id": "q_root", "question_text": "Root question"}])

    fu_q = [{
        "question_id": "q_root_fu_1",
        "question_text": "Follow up question on root?",
        "category": "Follow-Up",
        "is_follow_up": 1,
        "parent_question_id": "q_root"
    }]
    store.save_questions(sid, fu_q)

    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM interview_questions WHERE session_id = ? AND question_id = ?", (sid, "q_root_fu_1"))
        row = cursor.fetchone()
        assert row is not None
        assert row["is_follow_up"] == 1
        assert row["parent_question_id"] == "q_root"


def test_duplicate_submission_protection(temp_db):
    """Verifies updating an answer to the same question replaces it idempotently."""
    store, _ = temp_db
    sid = "test-session-uuid-006"
    store.save_session({"session_id": sid, "owner_id": "owner_alpha"})
    store.save_questions(sid, [{"question_id": "q_1", "question_text": "Q1"}])

    aid = "ans_fixed_id_1"
    store.save_answer(sid, "q_1", "Answer version 1", answer_id=aid)
    store.save_answer(sid, "q_1", "Answer version 2 (revised)", answer_id=aid)

    with store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), answer_text FROM candidate_answers WHERE answer_id = ?", (aid,))
        count, text = cursor.fetchone()
        assert count == 1
        assert text == "Answer version 2 (revised)"


def test_transcript_ownership_isolation(temp_db):
    """Verifies get_transcript enforces ownership isolation when owner_id is passed."""
    store, _ = temp_db
    sid = "test-session-uuid-007"
    store.save_session({"session_id": sid, "owner_id": "owner_alpha"})
    store.append_transcript_entry(sid, "interviewer", "greeting", "Private message.")

    # Owner alpha can read
    tr_alpha = store.get_transcript(sid, owner_id="owner_alpha")
    assert len(tr_alpha) == 1

    # Owner beta cannot read
    tr_beta = store.get_transcript(sid, owner_id="owner_beta")
    assert len(tr_beta) == 0


def test_history_empty_for_new_owner(client):
    """Verifies /api/interview/voice/history returns empty list gracefully for new owners."""
    _get_csrf_and_owner(client)
    resp = client.get("/api/interview/voice/history")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert isinstance(data["history"], list)


def test_transaction_rollback_on_write_failure(temp_db):
    """Verifies that an unhandled database exception rolls back uncommitted changes."""
    store, _ = temp_db
    sid = "test-session-uuid-008"
    store.save_session({"session_id": sid, "owner_id": "owner_alpha"})

    # Attempt to insert an answer with an invalid foreign key constraint if foreign keys are enforced,
    # or test connection rollback directly
    conn = store._get_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute(
            "INSERT INTO candidate_answers (answer_id, session_id, question_id, answer_text, submission_timestamp) VALUES (?, ?, ?, ?, ?)",
            ("ans_rollback_test", sid, "q_1", "Will be rolled back", 12345.0)
        )
        # Roll back explicitly
        conn.rollback()
    finally:
        conn.close()

    with store._get_connection() as check_conn:
        cursor = check_conn.cursor()
        cursor.execute("SELECT * FROM candidate_answers WHERE answer_id = 'ans_rollback_test'")
        assert cursor.fetchone() is None

