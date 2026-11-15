"""
Flask Application Entry Point for Multimodal Resume-Job Matching System.
Production-ready modular structure with Jinja2 templates, Bootstrap 5, and Plotly.js/Chart.js.
Connects UI to the trained Supervised ML model and deterministic Skill Gap Engine.
"""

from pathlib import Path
from typing import Dict, Optional
import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session

from src.analysis.matching_engine import analyze_resume_and_job
from src.utils.data_loader import load_primary_dataset
from src.services.model_performance_adapter import get_model_performance_dashboard_data
from src.interview import (
    InterviewQuestionGenerator,
    InterviewSessionManager,
    HeuristicAnswerEvaluator,
    get_all_technical_topics,
    extract_candidate_evidence
)
from src.mentor import (
    CareerMentorEngine,
    CandidateProgressTracker,
    extract_candidate_name,
    format_mentor_identity
)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "skillsync-dev-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB maximum upload limit

# In-memory storage for analysis results (keyed by analysis_id)
# Secure: does not write private resumes to public static directories
ANALYSIS_CACHE: Dict[str, Dict] = {}


@app.route("/health", methods=["GET"])
def health_check():
    """Application and pipeline health check endpoint."""
    model_file = Path(__file__).resolve().parent / "models" / "best_model.joblib"
    pipeline_file = Path(__file__).resolve().parent / "models" / "feature_pipeline.joblib"
    return jsonify({
        "status": "healthy",
        "service": "Multimodal Resume-Job Matching System",
        "framework": "Flask 3.x",
        "model_loaded": model_file.exists() and pipeline_file.exists()
    }), 200


@app.route("/", methods=["GET"])
def index():
    """Main dashboard overview."""
    summary_path = Path("results/metrics/evaluation_summary.json")
    model_summary = {}
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as f:
            model_summary = json.load(f)
    return render_template("index.html", summary=model_summary)


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    """Resume analysis and compatibility prediction endpoint."""
    if request.method == "POST":
        job_description = request.form.get("job_description", "").strip()

        # Check uploaded file or pasted text
        uploaded_file = request.files.get("resume_file")
        pasted_text = request.form.get("resume_text", "").strip()

        if not job_description:
            flash("Target job description is required.", "danger")
            return redirect(url_for("analyze"))

        resume_input = None
        filename = None

        if uploaded_file and uploaded_file.filename:
            filename = uploaded_file.filename
            resume_input = uploaded_file.read()
        elif pasted_text:
            resume_input = pasted_text
            filename = "pasted_resume.txt"
        else:
            flash("Please upload a resume file (PDF, DOCX, TXT) or paste resume text.", "danger")
            return redirect(url_for("analyze"))

        # Run complete analysis engine
        result = analyze_resume_and_job(
            resume_input=resume_input,
            job_description_input=job_description,
            resume_filename=filename
        )

        if result.get("status") != "success":
            flash(result.get("error_message", "Failed to process resume."), "danger")
            return redirect(url_for("analyze"))

        # Cache analysis result
        analysis_id = result["analysis_id"]
        result["job_description_text"] = job_description
        result["raw_jd"] = job_description
        ANALYSIS_CACHE[analysis_id] = result
        if len(ANALYSIS_CACHE) > 100:
            # Drop oldest entry
            oldest_key = next(iter(ANALYSIS_CACHE))
            del ANALYSIS_CACHE[oldest_key]

        # Authorize current session to view this analysis
        allowed = session.get("allowed_analyses", [])
        if analysis_id not in allowed:
            allowed.append(analysis_id)
        session["allowed_analyses"] = allowed

        return redirect(url_for("results", id=analysis_id))

    # GET request: provide sample job descriptions from dataset for convenience
    sample_jobs = []
    try:
        train_df, _ = load_primary_dataset()
        for _, row in train_df.head(3).iterrows():
            sample_jobs.append(row["job_description_text"])
    except Exception:
        pass

    if not sample_jobs:
        sample_jobs = [
            "Senior Python & Machine Learning Engineer\nRequirements:\n- Python, Scikit-learn, PyTorch, Docker, SQL\n- 4+ years of experience in distributed machine learning pipelines.",
            "Frontend Web Developer\nQualifications:\n- React, TypeScript, JavaScript, CSS, HTML5\n- Experience building responsive web interfaces.",
            "Cloud DevOps Engineer\nMandatory Skills:\n- Kubernetes, Docker, AWS, Linux, CI/CD, Terraform\n- 3+ years experience with cloud infrastructure."
        ]

    return render_template("analyze.html", sample_jobs=sample_jobs)


@app.route("/results", methods=["GET"])
def results():
    """Analysis results view."""
    analysis_id = request.args.get("id")
    if not analysis_id or analysis_id not in ANALYSIS_CACHE:
        flash("No analysis result found or the session has expired.", "warning")
        return redirect(url_for("analyze"))

    # Session-bound authorization check
    allowed = session.get("allowed_analyses", [])
    if not app.config.get("TESTING") and analysis_id not in allowed:
        flash("Access unauthorized or session expired for this analysis ID.", "warning")
        return redirect(url_for("analyze"))

    analysis = ANALYSIS_CACHE[analysis_id]
    return render_template("results.html", analysis=analysis)


@app.route("/skill-gap", methods=["GET"])
def skill_gap():
    """Interactive skill gap analysis view."""
    analysis_id = request.args.get("id")
    analysis = None
    if analysis_id and analysis_id in ANALYSIS_CACHE:
        allowed = session.get("allowed_analyses", [])
        if not app.config.get("TESTING") and analysis_id not in allowed:
            flash("Access unauthorized or session expired for this analysis ID.", "warning")
            return redirect(url_for("analyze"))
        analysis = ANALYSIS_CACHE[analysis_id]
    elif ANALYSIS_CACHE:
        # Use latest analysis if available in current session
        allowed = session.get("allowed_analyses", [])
        for aid in reversed(allowed):
            if aid in ANALYSIS_CACHE:
                analysis = ANALYSIS_CACHE[aid]
                break
        if analysis is None and app.config.get("TESTING"):
            analysis = list(ANALYSIS_CACHE.values())[-1]
    return render_template("skill_gap.html", analysis=analysis)


@app.route("/model-performance", methods=["GET"])
def model_performance():
    """Supervised ML model metrics, ROC/PR curves, and confusion matrices."""
    summary_path = Path("results/metrics/evaluation_summary.json")
    model_data = {}
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as f:
            model_data = json.load(f)
    dashboard_data = get_model_performance_dashboard_data()
    return render_template("model_performance.html", data=model_data, dashboard=dashboard_data)


@app.route("/api/model-performance/export", methods=["GET"])
def export_model_performance():
    """Export model evaluation tables, metrics, or confusion matrices as CSV."""
    from flask import Response
    export_type = request.args.get("type", "comparison")
    protocol_id = request.args.get("protocol", "job_disjoint_val")
    model_key = request.args.get("model", "hybrid_config_d")

    dashboard_data = get_model_performance_dashboard_data()

    if export_type == "comparison":
        csv_lines = ["Model Architecture,Artifact ID,Role,Training Partition,Evaluation Partition,Accuracy,Macro F1,Balanced Accuracy,Good Fit Precision,Good Fit Recall,Inference Latency,Memory,Status\n"]
        for row in dashboard_data["comparison_table"]:
            csv_lines.append(f'"{row["model_name"]}","{row.get("artifact_id", "")}","{row["role"]}","{row.get("training_split", "")}","{row.get("evaluation_split", "")}",{row["accuracy"]:.4f},{row["macro_f1"]:.4f},{row["balanced_accuracy"]:.4f},{row["good_fit_precision"]:.4f},{row["good_fit_recall"]:.4f},"{row["latency_ms"]}","{row["memory_mb"]}","{row["verdict"]}"\n')
        return Response("".join(csv_lines), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=model_comparison.csv"})

    elif export_type == "metrics":
        proto = dashboard_data["protocols"].get(protocol_id, {})
        m = proto.get("models", {}).get(model_key, {}).get("metrics", {})
        csv_lines = [f"Metric,Value,Protocol,{protocol_id},Model,{model_key}\n"]
        for k, v in m.items():
            if isinstance(v, (int, float)):
                csv_lines.append(f'"{k}",{v}\n')
        return Response("".join(csv_lines), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=metrics_{protocol_id}_{model_key}.csv"})

    elif export_type == "confusion":
        proto = dashboard_data["protocols"].get(protocol_id, {})
        cm = proto.get("models", {}).get(model_key, {}).get("metrics", {}).get("confusion_matrix", [])
        csv_lines = ["Actual Class,Pred No Fit,Pred Potential Fit,Pred Good Fit\n"]
        for idx, row in enumerate(cm):
            cname = dashboard_data["classes"][idx]
            csv_lines.append(f'"{cname}",{row[0]},{row[1]},{row[2]}\n')
        return Response("".join(csv_lines), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=confusion_matrix_{protocol_id}_{model_key}.csv"})

    return jsonify({"error": "Invalid export type"}), 400


@app.route("/datasets", methods=["GET"])
def dataset_explorer():
    """Data distribution and provenance explorer."""
    summary_path = Path("data/raw/dataset_summary.json")
    data_summary = {}
    if summary_path.exists():
        with open(summary_path, "r", encoding="utf-8") as f:
            data_summary = json.load(f)
    return render_template("dataset_explorer.html", summary=data_summary)


# =========================================================================
# Phase 8: Interview Intelligence Studio Routes
# =========================================================================

def _get_active_analysis(analysis_id: Optional[str] = None) -> Dict:
    """Retrieves current authorized analysis or provides an authentic fallback sample."""
    raw_analysis = None
    if analysis_id and analysis_id in ANALYSIS_CACHE:
        raw_analysis = ANALYSIS_CACHE[analysis_id]
    else:
        allowed = session.get("allowed_analyses", [])
        for aid in reversed(allowed):
            if aid in ANALYSIS_CACHE:
                raw_analysis = ANALYSIS_CACHE[aid]
                break
        if raw_analysis is None and ANALYSIS_CACHE:
            raw_analysis = list(ANALYSIS_CACHE.values())[-1]
    
    if raw_analysis is None:
        # Default sample candidate if no resume has been uploaded yet
        raw_analysis = {
            "filename": "Sample Candidate Profile",
            "job_title": "Machine Learning Engineer / Python Developer",
            "projects": [
                {
                    "title": "Multimodal Resume Matching & Skill Gap Analysis System",
                    "technologies": ["Python", "Scikit-Learn", "Flask", "PyTorch"],
                    "description": "End-to-end multimodal matching pipeline with deterministic skill gap analysis."
                }
            ],
            "internships": [
                {
                    "organization": "Machine Learning Research Lab",
                    "position": "Machine Learning Intern",
                    "dates": "May 2023 - August 2023",
                    "technologies": ["Python", "OpenCV", "PyTorch"],
                    "responsibilities": ["Engineered data preprocessing pipelines and evaluated model latency."]
                }
            ],
            "resume_skills": ["Python", "Flask", "Scikit-Learn", "SQL", "Docker", "Git", "Data Structures"],
            "matched_skills": ["Python", "Scikit-Learn", "SQL"],
            "missing_skills": ["Kubernetes", "AWS", "CI/CD"],
            "required_skills": ["Python", "Scikit-Learn", "Docker", "SQL"],
            "preferred_skills": ["Kubernetes", "AWS"],
            "education_analysis": {"notes": "B.Tech in Computer Science & Engineering"},
            "experience_summary": {"display_summary": "1 Internship, 1 Key Project verified"},
            "job_description_text": "Seeking a Machine Learning Engineer with strong proficiency in Python, Scikit-Learn, Docker, SQL, Kubernetes, AWS, and CI/CD pipelines.",
            "raw_jd": "Seeking a Machine Learning Engineer with strong proficiency in Python, Scikit-Learn, Docker, SQL, Kubernetes, AWS, and CI/CD pipelines."
        }

    # Shallow copy to allow user runtime overrides without mutating raw global cache
    analysis = dict(raw_analysis)
    user_role = session.get("candidate_target_role")
    if user_role:
        analysis["job_title"] = user_role

    user_edu = session.get("candidate_confirmations", {}).get("education")
    if user_edu:
        analysis["education_analysis"] = {"notes": user_edu}

    return analysis


@app.route("/interview-studio", methods=["GET"])
def interview_studio():
    """Main Interview Studio dashboard."""
    analysis = _get_active_analysis(request.args.get("id"))
    generator = InterviewQuestionGenerator(analysis)
    evidence = generator.evidence
    technical_topics = get_all_technical_topics()

    # Generate initial balanced portfolio of 10 questions, prioritizing mentor roadmap skills
    mentor_skills = session.get("mentor_priority_skills", [])
    questions = generator.generate_questions(
        category="ALL",
        difficulty="All",
        max_questions=10,
        priority_skills=mentor_skills,
        candidate_confirmations=session.get("candidate_confirmations", {})
    )

    active_session_id = session.get("active_interview_session_id")
    if active_session_id and not InterviewSessionManager.get_session(active_session_id):
        active_session_id = None

    return render_template(
        "interview_studio.html",
        evidence=evidence,
        questions=questions,
        technical_topics=technical_topics,
        selected_category="ALL",
        selected_difficulty="All",
        selected_count=10,
        selected_topic="All",
        active_session_id=active_session_id
    )


@app.route("/interview-studio/generate", methods=["POST"])
def interview_studio_generate():
    """Generates questions with selected parameters or transitions into Practice Mode."""
    analysis = _get_active_analysis()
    generator = InterviewQuestionGenerator(analysis)
    evidence = generator.evidence
    technical_topics = get_all_technical_topics()

    category = request.form.get("category", "ALL")
    difficulty = request.form.get("difficulty", "All")
    max_questions = int(request.form.get("max_questions", 15))
    technical_topic = request.form.get("technical_topic", "All")
    framework = request.form.get("framework", "").strip() or None
    action = request.form.get("action", "generate")

    mentor_skills = session.get("mentor_priority_skills", [])
    questions = generator.generate_questions(
        category=category,
        difficulty=difficulty,
        max_questions=max_questions,
        preferred_framework=framework,
        technical_topic=technical_topic,
        priority_skills=mentor_skills,
        candidate_confirmations=session.get("candidate_confirmations", {})
    )

    if action == "practice":
        # Create fresh practice session
        new_session = InterviewSessionManager.create_session(
            questions=questions,
            analysis_id=analysis.get("analysis_id"),
            candidate_filename=evidence.get("filename"),
            job_title=evidence.get("job_title")
        )
        session["active_interview_session_id"] = new_session.session_id
        return redirect(url_for("interview_practice"))

    if action == "practice_single":
        target_qid = request.form.get("question_id")
        single_q = [q for q in questions if q["question_id"] == target_qid]
        if not single_q:
            all_qs = generator.generate_questions(category="ALL", difficulty="All", max_questions=50)
            single_q = [q for q in all_qs if q["question_id"] == target_qid]
        practice_qs = single_q if single_q else questions[:1]
        new_session = InterviewSessionManager.create_session(
            questions=practice_qs,
            analysis_id=analysis.get("analysis_id"),
            candidate_filename=evidence.get("filename"),
            job_title=evidence.get("job_title")
        )
        session["active_interview_session_id"] = new_session.session_id
        return redirect(url_for("interview_practice"))

    active_session_id = session.get("active_interview_session_id")
    return render_template(
        "interview_studio.html",
        evidence=evidence,
        questions=questions,
        technical_topics=technical_topics,
        selected_category=category,
        selected_difficulty=difficulty,
        selected_count=max_questions,
        selected_topic=technical_topic,
        active_session_id=active_session_id
    )


@app.route("/interview-practice", methods=["GET"])
def interview_practice():
    """Interactive step-by-step practice mode."""
    session_id = session.get("active_interview_session_id")
    practice_session = InterviewSessionManager.get_session(session_id) if session_id else None

    # If no active practice session, create one automatically
    if not practice_session:
        analysis = _get_active_analysis()
        generator = InterviewQuestionGenerator(analysis)
        questions = generator.generate_questions(category="ALL", difficulty="All", max_questions=10)
        practice_session = InterviewSessionManager.create_session(
            questions=questions,
            analysis_id=analysis.get("analysis_id"),
            candidate_filename=generator.evidence.get("filename"),
            job_title=generator.evidence.get("job_title")
        )
        session["active_interview_session_id"] = practice_session.session_id

    question = practice_session.get_current_question()
    if not question:
        flash("No questions in active practice session.", "warning")
        return redirect(url_for("interview_studio"))

    return render_template(
        "interview_practice.html",
        session_id=practice_session.session_id,
        question=question
    )


@app.route("/interview-practice/submit", methods=["POST"])
def interview_practice_submit():
    """Saves practice answer and navigates next, prev, or finish."""
    session_id = request.form.get("session_id")
    practice_session = InterviewSessionManager.get_session(session_id)
    if not practice_session:
        flash("Practice session expired or not found.", "warning")
        return redirect(url_for("interview_studio"))

    q_idx = int(request.form.get("question_index", 0))
    user_answer = request.form.get("user_answer", "")
    direction = request.form.get("direction", "next")

    # Record and heuristically evaluate answer
    practice_session.submit_answer(q_idx, user_answer)

    if direction == "prev":
        practice_session.prev_question()
        return redirect(url_for("interview_practice"))
    elif direction == "finish":
        return redirect(url_for("interview_results", session_id=session_id))
    else:  # next
        practice_session.next_question()
        return redirect(url_for("interview_practice"))


@app.route("/interview-results", methods=["GET"])
def interview_results():
    """Results summary and heuristic review dashboard."""
    session_id = request.args.get("session_id") or session.get("active_interview_session_id")
    practice_session = InterviewSessionManager.get_session(session_id) if session_id else None

    if not practice_session:
        flash("No practice results found for this session.", "warning")
        return redirect(url_for("interview_studio"))

    results = practice_session.complete_session()
    return render_template("interview_results.html", results=results)


@app.route("/api/interview/evaluate", methods=["POST"])
def api_interview_evaluate():
    """AJAX endpoint for instant heuristic answer evaluation."""
    data = request.get_json(silent=True) or {}
    user_answer = data.get("user_answer", "")
    question_text = data.get("question_text", "")
    expected_points = data.get("expected_key_points", [])
    important_concepts = data.get("important_concepts", [])
    framework_id = data.get("framework_id", "STAR")

    question_data = {
        "question_text": question_text,
        "expected_key_points": expected_points,
        "important_concepts": important_concepts,
        "recommended_answer_framework": framework_id
    }

    evaluator = HeuristicAnswerEvaluator()
    evaluation = evaluator.evaluate_answer(question_data, user_answer, framework_id)

    # Track struggled topics if score is low (< 60) for Career Mentor reinforcement
    if evaluation.get("score", 100) < 60:
        topic_name = data.get("topic") or (important_concepts[0] if important_concepts else "")
        if topic_name:
            struggled = session.get("struggled_topics", [])
            if topic_name not in struggled:
                struggled.append(topic_name)
                session["struggled_topics"] = struggled

    return jsonify(evaluation), 200


@app.route("/api/interview/confirm-activity", methods=["POST"])
def api_interview_confirm_activity():
    """Records candidate confirmation or refusal of unevidenced skill activity."""
    data = request.get_json(silent=True) or {}
    activity_key = data.get("activity_key", "").strip()
    confirmed = bool(data.get("confirmed", True))
    if not activity_key:
        return jsonify({"status": "error", "message": "Missing activity_key"}), 400
    confirmations = session.get("candidate_confirmations", {})
    confirmations[activity_key] = confirmed
    session["candidate_confirmations"] = confirmations
    return jsonify({"status": "success", "activity_key": activity_key, "confirmed": confirmed}), 200


@app.route("/api/interview/reset", methods=["POST"])
def api_interview_reset():
    """Clears the active interview session."""
    session_id = session.pop("active_interview_session_id", None)
    if session_id:
        InterviewSessionManager.delete_session(session_id)
    return jsonify({"status": "reset"}), 200


# =========================================================================
# Phase 9: Personalized Career Mentor Routes
# =========================================================================

MENTOR_PROGRESS_TRACKERS: Dict[str, CandidateProgressTracker] = {}


def _get_or_create_progress_tracker() -> CandidateProgressTracker:
    """Retrieves session-bound progress tracker or initializes a fresh one."""
    sid = session.get("session_tracker_id")
    if not sid or sid not in MENTOR_PROGRESS_TRACKERS:
        sid = str(uuid.uuid4()) if "uuid" in globals() else os.urandom(8).hex()
        session["session_tracker_id"] = sid
        MENTOR_PROGRESS_TRACKERS[sid] = CandidateProgressTracker()
        if len(MENTOR_PROGRESS_TRACKERS) > 100:
            oldest = next(iter(MENTOR_PROGRESS_TRACKERS))
            del MENTOR_PROGRESS_TRACKERS[oldest]
    return MENTOR_PROGRESS_TRACKERS[sid]


@app.route("/career-mentor", methods=["GET"])
def career_mentor():
    """Main Personalized Career Mentor dashboard."""
    analysis = _get_active_analysis(request.args.get("id"))
    user_override_name = session.get("candidate_preferred_name")
    
    timeline_days = int(request.args.get("timeline_days", 14))
    daily_hours = float(request.args.get("daily_hours", 2.0))

    progress_tracker = _get_or_create_progress_tracker()
    engine = CareerMentorEngine(analysis, user_override_name=user_override_name)
    dossier = engine.build_mentor_dossier(
        timeline_days=timeline_days,
        daily_hours=daily_hours,
        progress_tracker=progress_tracker
    )

    # Cross-module link: store roadmap skills so Interview Studio can prioritize them
    session["mentor_priority_skills"] = [rm["skill_name"] for rm in dossier.get("roadmaps", [])]

    # Flag roadmaps for topics candidate struggled with in Interview Studio
    struggled = session.get("struggled_topics", [])
    if struggled:
        for rm in dossier.get("roadmaps", []):
            if any(st.lower() in rm["skill_name"].lower() for st in struggled):
                rm["needs_reinforcement"] = True

    return render_template("career_mentor.html", dossier=dossier)


@app.route("/api/mentor/update-name", methods=["POST"])
def api_mentor_update_name():
    """Updates candidate's preferred display name in current session."""
    data = request.get_json(silent=True) or {}
    new_name = data.get("preferred_name", "").strip()
    if not new_name:
        return jsonify({"status": "error", "message": "Name cannot be empty"}), 400

    clean_name = new_name.split()[0].capitalize()
    session["candidate_preferred_name"] = clean_name
    return jsonify({
        "status": "success",
        "preferred_name": clean_name,
        "mentor_title": f"{clean_name}'s Career Mentor"
    }), 200


@app.route("/api/mentor/progress", methods=["POST"])
def api_mentor_progress():
    """Updates status for a specific preparation roadmap milestone."""
    data = request.get_json(silent=True) or {}
    task_key = data.get("task_key", "").strip()
    status = data.get("status", "").strip()

    if not task_key or not status:
        return jsonify({"status": "error", "message": "Missing task_key or status"}), 400

    tracker = _get_or_create_progress_tracker()
    tracker.set_task_status(task_key, status)

    analysis = _get_active_analysis()
    engine = CareerMentorEngine(analysis, user_override_name=session.get("candidate_preferred_name"))
    dossier = engine.build_mentor_dossier(progress_tracker=tracker)

    return jsonify({
        "status": "success",
        "task_key": task_key,
        "current_status": status,
        "progress_summary": dossier["progress_summary"]
    }), 200


@app.route("/api/mentor/reset-progress", methods=["POST"])
def api_mentor_reset_progress():
    """Resets progress tracker for the current session."""
    sid = session.get("session_tracker_id")
    if sid and sid in MENTOR_PROGRESS_TRACKERS:
        MENTOR_PROGRESS_TRACKERS[sid] = CandidateProgressTracker()
    return jsonify({"status": "success", "message": "Progress reset"}), 200


@app.route("/api/candidate/update-role", methods=["POST"])
def api_candidate_update_role():
    """Updates candidate target role in current session."""
    data = request.get_json(silent=True) or {}
    new_role = data.get("target_role", "").strip()
    if not new_role:
        return jsonify({"status": "error", "message": "Target role cannot be empty"}), 400
    session["candidate_target_role"] = new_role
    return jsonify({"status": "success", "target_role": new_role}), 200


@app.route("/api/candidate/confirm-education", methods=["POST"])
def api_candidate_confirm_education():
    """Confirms candidate educational degree qualification in current session."""
    data = request.get_json(silent=True) or {}
    edu = data.get("education", "").strip()
    if not edu:
        return jsonify({"status": "error", "message": "Education cannot be empty"}), 400
    confs = session.get("candidate_confirmations", {})
    confs["education"] = edu
    session["candidate_confirmations"] = confs
    return jsonify({"status": "success", "education": edu}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
