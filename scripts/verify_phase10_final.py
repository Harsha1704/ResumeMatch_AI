"""
scripts/verify_phase10_final.py
Executes comprehensive real-world verification for Phase 10:
- Task 1: 5 Candidate Profiles through Career Mentor
- Task 2: 10 Interview Questions with strict Truthfulness Audit
- Task 3: 3 Candidates (A, B, C) on identical JD comparing Personalization
- Task 4: Production ZIP Integrity and Artifact Discrepancy analysis
"""

import os
import sys

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import json
import zipfile
import re
from typing import Dict, Any, List

from src.analysis.matching_engine import ResumeMatchingEngine
from src.mentor.mentor_engine import CareerMentorEngine
from src.interview.question_generator import InterviewQuestionGenerator
from src.interview.answer_validator import AnswerQualityValidator
from src.interview.question_bank import TECHNICAL_QUESTION_BANK, HR_QUESTION_BANK

OUTPUT_DIR = "results/verification_outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =====================================================================
# TASK 1: FIVE CANDIDATE PROFILES
# =====================================================================

CANDIDATE_1_ML_STUDENT = {
    "name": "Aarav Sharma",
    "filename": "aarav_sharma_ml.txt",
    "resume": """Aarav Sharma
aarav.sharma@email.com | Bangalore, India | LinkedIn: /in/aarav-ml

EDUCATION
B.Tech in Computer Science and Engineering | National Institute of Technology | 2021 - 2025 (Expected)
CGPA: 8.7/10

TECHNICAL SKILLS
Languages: Python, C++
Frameworks & Libraries: OpenCV, PyTorch, NumPy, Matplotlib
Concepts: Computer Vision, Image Processing, Object Detection, Convolutional Neural Networks
Developer Tools: Git, Jupyter Notebook, Linux

PROJECTS
Real-Time Edge Defect Detector | Python, OpenCV, PyTorch
- Developed a convolutional defect detection pipeline for industrial surface inspection.
- Applied morphological filters, Gaussian blurring, and contour detection to segment hairline fractures.
- Trained a lightweight MobileNet backbone in PyTorch, achieving 91.4% validation accuracy on test images.

Automated License Plate Recognition | Python, OpenCV
- Implemented edge detection and perspective warping to isolate license plate regions from traffic camera feeds.
- Extracted character contours and passed segmented characters to an OCR classifier.
""",
    "jd": """Computer Vision / ML Engineer
Requirements:
- Strong programming skills in Python and PyTorch.
- Hands-on experience with Computer Vision, OpenCV, and deep learning architectures (CNNs).
- Experience with Docker containerization for deploying ML inference services.
- Knowledge of ONNX runtime or TensorRT for model optimization and latency reduction.
- Experience with REST API frameworks (FastAPI or Flask) for serving predictions.
- Solid understanding of Git version control and Linux environments.
""",
}

CANDIDATE_2_BACKEND_DEV = {
    "name": "Elena Rostova",
    "filename": "elena_backend.txt",
    "resume": """Elena Rostova
elena.rostova@email.com | Berlin, Germany | GitHub: /elena-backend

PROFESSIONAL SUMMARY
Backend developer with 3 years of production experience designing RESTful APIs, optimizing relational databases, and architecting scalable backend services using Python, Flask, and PostgreSQL.

TECHNICAL SKILLS
Languages: Python, SQL
Frameworks: Flask, SQLAlchemy, Celery
Databases: PostgreSQL, MySQL, Redis
Tools: Git, Linux, Postman, pytest

EXPERIENCE
Backend Software Engineer | FinTech Systems GmbH | 2022 - Present
- Designed and maintained 25+ RESTful API endpoints for financial transaction processing using Flask.
- Optimized slow relational queries with PostgreSQL indexing and query execution plan analysis, improving p95 response time by 40%.
- Integrated Celery with Redis for asynchronous payment webhook dispatching and background reporting.
- Wrote unit and integration test suites using pytest achieving 92% code coverage.

PROJECTS
Distributed Payment Gateway Service | Python, Flask, PostgreSQL, Redis
- Architected an idempotent payment reconciliation service handling high concurrency transaction webhooks.
- Implemented strict database transaction boundaries with ACID guarantees using SQLAlchemy.

High-Throughput Order Ingestion Engine | Python, Flask, PostgreSQL, Celery
- Designed an asynchronous order processing pipeline using Celery and Redis message queues.
- Optimized database indexing to reduce lock contention during peak batch write events.
""",
    # SHARED JD WITH CANDIDATE 5 (DevOps) to verify different recommendations on SAME JD!
    "jd": """Senior Cloud Backend Engineer
Requirements:
- Expert proficiency in Python and backend frameworks (Flask or FastAPI).
- Strong relational database design and optimization with SQL and PostgreSQL.
- Production experience with Docker containerization and multi-container orchestration.
- Cloud deployment and architecture experience on AWS (ECS, RDS, S3).
- Experience designing and maintaining CI/CD automation pipelines (GitHub Actions, Jenkins).
- Solid Linux systems administration and Git version control practices.
""",
}

CANDIDATE_3_FRONTEND_DEV = {
    "name": "Marcus Vance",
    "filename": "marcus_frontend.txt",
    "resume": """Marcus Vance
marcus.vance@email.com | Austin, TX | Portfolio: /marcus-ui

PROFESSIONAL SUMMARY
Frontend engineer with 2+ years of experience crafting responsive, accessible user interfaces and web applications using HTML5, CSS3, JavaScript (ES6+), and React.

TECHNICAL SKILLS
Languages: JavaScript, HTML5, CSS3
Frameworks & Libraries: React, Redux, Tailwind CSS, Bootstrap
Tools: Git, Webpack, npm, Chrome DevTools, Figma

EXPERIENCE
Frontend Developer | PixelCraft Studio | 2022 - Present
- Built responsive client dashboard interfaces using React, JavaScript, and Tailwind CSS.
- Migrated legacy multi-page UI components into reusable React functional components with hooks.
- Implemented global state management using Redux Toolkit for multi-step onboarding forms.

PROJECTS
Interactive Analytics Dashboard | React, JavaScript, CSS3
- Designed an interactive analytics visualization interface supporting real-time filter controls and chart updates.
- Optimized client-side rendering performance, cutting initial DOM render time by 28%.
""",
    "jd": """Senior Frontend / Web Application Engineer
Requirements:
- Advanced proficiency in JavaScript (ES6+), HTML5, and modern CSS3.
- Production experience with React and state management (Redux).
- Strong proficiency in TypeScript for scalable frontend development.
- Hands-on experience with Next.js for server-side rendering and static site generation.
- Experience writing automated frontend tests using Jest and React Testing Library.
- Knowledge of Webpack bundling optimization and web performance vitals.
""",
}

CANDIDATE_4_DATA_ANALYST = {
    "name": "Priya Nair",
    "filename": "priya_analyst.txt",
    "resume": """Priya Nair
priya.nair@email.com | Chicago, IL

PROFESSIONAL SUMMARY
Data analyst with 3 years of experience transforming complex business datasets into actionable operational dashboards, executive reports, and KPI trackers using Advanced Excel, SQL, and Tableau.

TECHNICAL SKILLS
Data Analysis: SQL, Advanced Excel (VLOOKUP, Pivot Tables, Power Query), Tableau, Power BI
Databases: PostgreSQL, MySQL, SQL Server
Concepts: Data Cleaning, KPI Dashboards, Cohort Analysis, Statistical Aggregation
Tools: Git, Jira

EXPERIENCE
Business Intelligence Analyst | OmniRetail Logistics | 2021 - Present
- Authored complex SQL aggregation queries and window functions across 2M+ rows of order fulfillment data.
- Built 12 interactive Tableau executive dashboards tracking shipping SLA compliance and inventory turn rates.
- Automated weekly financial reconciliation reports in Excel using Power Query, saving 6 hours per week.

PROJECTS
E-Commerce Churn Analytics Dashboard | SQL, Tableau, Excel
- Cleaned and transformed 50,000 customer transaction records using SQL queries.
- Identified drop-off funnels and visualized retention cohorts in Tableau, uncovering a 14% cart abandonment trend.
""",
    "jd": """Senior Analytics Engineer / BI Developer
Requirements:
- Advanced SQL proficiency including CTEs, window functions, and query optimization.
- Proven experience building executive dashboards in Tableau or Power BI.
- Hands-on experience with Python for data manipulation (pandas, NumPy).
- Experience with modern data stack tools: dbt (data build tool) for SQL transformations.
- Experience with cloud data warehouses such as Snowflake or BigQuery.
- Solid understanding of dimensional data modeling (Star Schema, Kimball methodology).
""",
}

CANDIDATE_5_DEVOPS = {
    "name": "Jordan Rivera",
    "filename": "jordan_devops.txt",
    "resume": """Jordan Rivera
jordan.rivera@email.com | Seattle, WA | GitHub: /jrivera-ops

PROFESSIONAL SUMMARY
DevOps engineer with 3 years of experience automating infrastructure provisioning, containerizing services, managing CI/CD pipelines, and maintaining Linux server infrastructure.

TECHNICAL SKILLS
Infrastructure & Cloud: AWS (EC2, S3, IAM, CloudWatch), Linux (Ubuntu, Debian, Bash)
Containerization: Docker, Docker Compose
CI/CD: GitHub Actions, Jenkins, Git
Monitoring: Prometheus, Grafana
Networking: DNS, TCP/IP, SSL/TLS, NGINX

EXPERIENCE
DevOps Engineer | StratoCloud Labs | 2022 - Present
- Built and maintained GitHub Actions CI/CD workflows automating testing, container building, and deployment.
- Containerized internal services with multi-stage Dockerfiles, standardizing dev and staging environments.
- Managed AWS cloud infrastructure across EC2, S3, and VPC networking with automated bash maintenance scripts.
- Configured NGINX reverse proxies and managed SSL/TLS certificate rotation.

PROJECTS
Automated GitOps Deployment Pipeline | Docker, GitHub Actions, AWS
- Configured a continuous deployment workflow deploying containerized microservices to AWS EC2.
- Integrated automated vulnerability scanning with Trivy in the CI pipeline.
""",
    # IDENTICAL JD AS CANDIDATE 2 (Backend Dev) TO VERIFY DIFFERENT RECOMMENDATIONS ON SAME JD
    "jd": """Senior Cloud Backend Engineer
Requirements:
- Expert proficiency in Python and backend frameworks (Flask or FastAPI).
- Strong relational database design and optimization with SQL and PostgreSQL.
- Production experience with Docker containerization and multi-container orchestration.
- Cloud deployment and architecture experience on AWS (ECS, RDS, S3).
- Experience designing and maintaining CI/CD automation pipelines (GitHub Actions, Jenkins).
- Solid Linux systems administration and Git version control practices.
""",
}


def run_task_1():
    print("=" * 80)
    print("EXECUTING TASK 1: CAREER MENTOR REAL-OUTPUT VERIFICATION (5 CANDIDATES)")
    print("=" * 80)
    
    candidates = [
        CANDIDATE_1_ML_STUDENT,
        CANDIDATE_2_BACKEND_DEV,
        CANDIDATE_3_FRONTEND_DEV,
        CANDIDATE_4_DATA_ANALYST,
        CANDIDATE_5_DEVOPS,
    ]
    
    engine = ResumeMatchingEngine()
    results = {}
    all_sentences = []

    for idx, c in enumerate(candidates, 1):
        print(f"\nProcessing Candidate {idx}: {c['name']} ({c['filename']})...")
        analysis = engine.analyze(
            resume_input=c["resume"],
            job_description_input=c["jd"],
            resume_filename=c["filename"]
        )
        mentor = CareerMentorEngine(analysis)
        dossier = mentor.build_mentor_dossier(timeline_days=14, daily_hours=2.0)
        
        # Extract fields
        detected_skills = analysis.get("resume_skills", [])
        missing_skills = analysis.get("missing_skills", [])
        prioritized_gaps = dossier.get("gaps", {}).get("prioritized_gaps", [])
        top_5 = prioritized_gaps[:5]
        
        # Check recommendations
        rec_actions = [g.get("recommended_action", "") for g in prioritized_gaps]
        why_matters = [g.get("counseling_profile", {}).get("q1_why_it_matters", "") for g in prioritized_gaps]
        practical_exercises = [g.get("counseling_profile", {}).get("q5_practical_exercise_step", "") for g in prioritized_gaps]
        schedule = dossier.get("study_plan", {}).get("schedule_items", [])
        
        # Repetition check
        for text in rec_actions + why_matters + practical_exercises:
            sents = re.split(r"(?<=[.!?])\s+", text)
            for s in sents:
                clean = s.strip()
                if len(clean) > 20:
                    all_sentences.append(clean)
        
        cand_summary = {
            "candidate_name": c["name"],
            "profile_type": c["filename"],
            "detected_skills": detected_skills,
            "missing_skills": missing_skills,
            "top_5_priorities": [
                {
                    "skill": g.get("skill_name"),
                    "priority_tier": g.get("priority_tier"),
                    "priority_level": g.get("priority"),
                    "why_it_matters": g.get("counseling_profile", {}).get("q1_why_it_matters"),
                    "related_experience": g.get("related_experience"),
                    "recommended_action": g.get("recommended_action"),
                    "practical_exercise": g.get("counseling_profile", {}).get("q5_practical_exercise_step"),
                    "deliverable": g.get("practical_deliverable"),
                    "starting_point": g.get("counseling_profile", {}).get("q4_initial_learning_step"),
                }
                for g in top_5
            ],
            "action_plans_count": len(dossier.get("action_plans", [])),
            "study_plan": {
                "timeline_days": dossier.get("study_plan", {}).get("timeline_days"),
                "total_scheduled_hours": dossier.get("study_plan", {}).get("total_scheduled_hours"),
                "scheduled_tasks_count": dossier.get("study_plan", {}).get("scheduled_tasks_count"),
                "schedule_days_sample": schedule[:5],
            }
        }
        results[f"candidate_{idx}"] = cand_summary
        
        print(f"  Detected skills ({len(detected_skills)}): {', '.join(detected_skills[:6])}")
        print(f"  Missing skills ({len(missing_skills)}): {', '.join(missing_skills[:6])}")
        print(f"  Top priorities: {[g.get('skill') for g in cand_summary['top_5_priorities']]}")
    
    # Measure sentence repetition
    sentence_counts = {}
    for s in all_sentences:
        sentence_counts[s] = sentence_counts.get(s, 0) + 1
    repeated = [s for s, count in sentence_counts.items() if count > 1]
    rep_rate = len(repeated) / max(1, len(sentence_counts)) * 100
    
    print(f"\nTask 1 Repetition Audit: {len(sentence_counts)} unique sentences, {len(repeated)} repeated across all 5 profiles.")
    print(f"Sentence Repetition Rate: {rep_rate:.2f}%")
    
    with open(os.path.join(OUTPUT_DIR, "task1_career_mentor_verification.json"), "w") as f:
        json.dump(results, f, indent=2)
        
    return results, rep_rate


# =====================================================================
# TASK 2: TEN INTERVIEW QUESTIONS & TRUTHFULNESS AUDIT
# =====================================================================

def run_task_2():
    print("\n" + "=" * 80)
    print("EXECUTING TASK 2: INTERVIEW STUDIO TRUTHFULNESS & GROUNDING AUDIT (10 QUESTIONS)")
    print("=" * 80)
    
    # We use Candidate 2 (Elena Rostova - Backend Dev)
    c = CANDIDATE_2_BACKEND_DEV
    engine = ResumeMatchingEngine()
    analysis = engine.analyze(
        resume_input=c["resume"],
        job_description_input=c["jd"],
        resume_filename=c["filename"]
    )
    generator = InterviewQuestionGenerator(analysis)
    validator = AnswerQualityValidator()
    
    # Generate directly from categories to ensure target types are present
    cat_b = generator.generate_category_b()
    cat_e = generator.generate_category_e()
    cat_f = generator.generate_category_f()
    
    # Select target 10 questions:
    # - 3 technical knowledge questions (Category E: curated technical)
    # - 2 project architecture questions (Category B: B1)
    # - 2 technical troubleshooting questions (Category B: B2)
    # - 2 behavioral questions (Category F)
    # - 1 system design question (Category E / System Design)
    
    tech_knowledge = [q for q in cat_e if "caching" not in q.get("question_text", "").lower() and "system design" not in q.get("question_text", "").lower()][:3]
    proj_arch = [q for q in cat_b if "architectural design" in q.get("question_text", "").lower()][:2]
    proj_debug = [q for q in cat_b if "technical roadblock" in q.get("question_text", "").lower()][:2]
    behavioral = cat_f[:2]
    
    sys_design = [q for q in cat_e if "caching layer" in q.get("question_text", "").lower()][:1]
    if not sys_design:
        for qb in TECHNICAL_QUESTION_BANK:
            if qb.get("id") == "tb_sys_01":
                sys_design = [{
                    "question_id": qb["id"],
                    "question_text": qb["question"],
                    "category": "E",
                    "category_name": "Technical Knowledge & System Design",
                    "difficulty": qb["difficulty"],
                    "recommended_framework": qb["recommended_framework"],
                    "short_answer": qb["short_answer"],
                    "detailed_answer": qb["detailed_answer"],
                    "step_by_step_explanation": qb["step_by_step_explanation"],
                    "why_this_works": qb.get("why_this_works", ""),
                    "follow_up_questions": qb.get("follow_up_questions", []),
                    "common_mistakes": qb.get("common_mistakes", []),
                    "examples": qb.get("examples", {}),
                    "important_concepts": qb.get("important_concepts", []),
                    "interview_tips": qb.get("interview_tips", []),
                    "source_reference": "Topic: System Design",
                }]
                break
                
    selected_10 = tech_knowledge + proj_arch + proj_debug + behavioral + sys_design
    print(f"Selected {len(selected_10)} specific questions for audit:")
    print(f"  - Technical Knowledge: {len(tech_knowledge)}")
    print(f"  - Project Architecture: {len(proj_arch)}")
    print(f"  - Technical Troubleshooting: {len(proj_debug)}")
    print(f"  - Behavioral Competencies: {len(behavioral)}")
    print(f"  - System Design: {len(sys_design)}")
    
    audited_questions = []
    
    # Verifier rules
    for idx, q in enumerate(selected_10, 1):
        q_id = q.get("question_id", f"q_{idx}")
        q_text = q.get("question_text", q.get("question", ""))
        short_ans = q.get("short_answer", "")
        detailed_ans = q.get("detailed_answer", "")
        full_text = f"{short_ans}\n{detailed_ans}"
        
        val_res = validator.validate_answer(q)
        
        # Check specific truthfulness constraints:
        # 1. Zero unverified metrics in candidate claims
        # 2. Candidate placeholders present where personal details are missing
        # 3. Objective framing for conceptual questions
        # 4. Illustrative model scenarios explicitly labeled
        has_invented_metrics = bool(re.search(r"\b(improved|reduced|increased)\s+by\s+\d+%\s+in\s+my\s+project", full_text, re.IGNORECASE))
        has_first_person_personal = bool(re.search(r"\b(I designed|I built|I implemented|I discovered|I committed)\b", detailed_ans))
        has_labeled_scenarios = "[Illustrative Model Scenario" in full_text
        has_candidate_slots = "[Candidate to specify:" in full_text or "Candidate Guidance:" in full_text or "[Candidate Metric:" in full_text
        
        audit_record = {
            "index": idx,
            "question_id": q_id,
            "category": q.get("category"),
            "category_name": q.get("category_name", ""),
            "question_text": q_text,
            "short_answer": short_ans,
            "detailed_answer": detailed_ans,
            "why_this_works": q.get("why_this_works", ""),
            "validation_passed": val_res.get("is_valid", False),
            "validation_score": val_res.get("quality_score", 0.0),
            "violations": val_res.get("issues", []),
            "truthfulness_checks": {
                "no_invented_metrics": not has_invented_metrics,
                "no_unsupported_first_person_claims": not has_first_person_personal,
                "has_candidate_specification_slots": has_candidate_slots,
                "has_labeled_illustrative_scenario": has_labeled_scenarios,
                "is_truthful_and_grounded": val_res.get("is_valid", False) and not has_invented_metrics,
            }
        }
        audited_questions.append(audit_record)
        print(f"  Q{idx} [{q.get('category')}]: {q_text[:70]}... -> Valid: {val_res.get('is_valid', False)} (Score: {val_res.get('quality_score')})")
        
    with open(os.path.join(OUTPUT_DIR, "task2_interview_truthfulness_audit.json"), "w") as f:
        json.dump(audited_questions, f, indent=2)
        
    return audited_questions
        
    with open(os.path.join(OUTPUT_DIR, "task2_interview_truthfulness_audit.json"), "w") as f:
        json.dump(audited_questions, f, indent=2)
        
    return audited_questions


# =====================================================================
# TASK 3: PERSONALIZATION COMPARISON (CANDIDATES A, B, C ON SAME JD)
# =====================================================================

def run_task_3():
    print("\n" + "=" * 80)
    print("EXECUTING TASK 3: PERSONALIZATION COMPARISON (CANDIDATES A, B, C ON IDENTICAL JD)")
    print("=" * 80)
    
    common_jd = """Senior Cloud Backend Engineer
Requirements:
- Python
- Flask
- Docker
- AWS
- SQL
- CI/CD
"""
    
    # Candidate A: Python and Flask only
    cand_a_resume = """Candidate A
Junior Python Developer
Languages: Python
Frameworks: Flask
Tools: Git

PROJECTS
Simple Web App | Python, Flask
- Created a lightweight blog web application using Flask routing and Jinja templates.
"""
    
    # Candidate B: Python, Flask, Docker, SQL, and Git
    cand_b_resume = """Candidate B
Mid-Level Backend Engineer
Languages: Python, SQL
Frameworks: Flask, SQLAlchemy
Databases: PostgreSQL, MySQL
Containers: Docker, Docker Compose
Tools: Git, Linux

EXPERIENCE
Software Engineer | TechCore Inc. | 2022 - Present
- Developed containerized backend services using Flask and PostgreSQL.
- Authored multi-stage Dockerfiles and managed local testing with Docker Compose.

PROJECTS
Inventory Management API | Python, Flask, Docker, PostgreSQL
- Architected REST APIs with SQLAlchemy ORM and relational database indexing.
- Containerized the application with Docker and orchestrated database services.
"""
    
    # Candidate C: Experienced DevOps engineer with Docker, AWS, CI/CD, Linux, Git
    cand_c_resume = """Candidate C
Senior DevOps Engineer
Cloud: AWS (ECS, EKS, RDS, S3, IAM, CloudFormation)
Containerization: Docker, Docker Compose, Kubernetes
CI/CD: GitHub Actions, Jenkins, GitLab CI
Systems: Linux (Ubuntu, RedHat, Bash), Git
Monitoring: Prometheus, Grafana

EXPERIENCE
Lead DevOps Engineer | CloudSolutions Corp | 2020 - Present
- Designed automated CI/CD deployment pipelines on AWS using GitHub Actions and ECS.
- Containerized enterprise workloads with multi-stage Dockerfiles and automated vulnerability scans.
- Managed multi-region AWS cloud infrastructure with Terraform and IAM least-privilege policies.
"""
    
    candidates = [
        ("Candidate A (Python + Flask)", cand_a_resume, "cand_a.txt"),
        ("Candidate B (Python + Flask + Docker + SQL + Git)", cand_b_resume, "cand_b.txt"),
        ("Candidate C (DevOps: Docker + AWS + CI/CD + Linux + Git)", cand_c_resume, "cand_c.txt"),
    ]
    
    engine = ResumeMatchingEngine()
    comparison_results = {}
    
    for label, resume_text, fname in candidates:
        print(f"\nAnalyzing {label}...")
        analysis = engine.analyze(
            resume_input=resume_text,
            job_description_input=common_jd,
            resume_filename=fname
        )
        mentor = CareerMentorEngine(analysis)
        dossier = mentor.build_mentor_dossier(timeline_days=14, daily_hours=2.0)
        
        detected = analysis.get("resume_skills", [])
        missing = analysis.get("missing_skills", [])
        prioritized = dossier.get("gaps", {}).get("prioritized_gaps", [])
        
        comparison_results[label] = {
            "detected_skills": detected,
            "missing_skills": missing,
            "missing_count": len(missing),
            "priority_order": [g.get("skill_name") for g in prioritized],
            "top_priorities_detailed": [
                {
                    "skill": g.get("skill_name"),
                    "priority_tier": g.get("priority_tier"),
                    "priority": g.get("priority"),
                    "starting_point": g.get("counseling_profile", {}).get("q4_initial_learning_step"),
                    "practical_exercise": g.get("counseling_profile", {}).get("q5_practical_exercise_step"),
                    "deliverable": g.get("practical_deliverable"),
                    "related_experience": g.get("related_experience"),
                }
                for g in prioritized[:4]
            ],
            "study_plan": {
                "total_scheduled_hours": dossier.get("study_plan", {}).get("total_scheduled_hours"),
                "scheduled_tasks_count": dossier.get("study_plan", {}).get("scheduled_tasks_count"),
                "covered_skills": dossier.get("study_plan", {}).get("covered_skills"),
            }
        }
        
        print(f"  Detected: {detected}")
        print(f"  Missing: {missing}")
        print(f"  Priority Ranking: {[g.get('skill_name') for g in prioritized]}")
        if prioritized:
            print(f"  #1 Starting point: {prioritized[0].get('counseling_profile', {}).get('q4_initial_learning_step')[:80]}...")
            print(f"  #1 Exercise: {prioritized[0].get('counseling_profile', {}).get('q5_practical_exercise_step')[:80]}...")
            
    with open(os.path.join(OUTPUT_DIR, "task3_personalization_comparison.json"), "w") as f:
        json.dump(comparison_results, f, indent=2)
        
    return comparison_results


# =====================================================================
# TASK 4: ARCHIVE INTEGRITY AUDIT (BACKUP15 VS FINAL ZIP)
# =====================================================================

def run_task_4():
    print("\n" + "=" * 80)
    print("EXECUTING TASK 4: PRODUCTION ZIP INTEGRITY AUDIT")
    print("=" * 80)
    
    b15_path = "ResumeMatch-AI-Final.backup15.zip"
    final_path = "ResumeMatch-AI-Final.zip"
    
    b15_size = os.path.getsize(b15_path)
    final_size = os.path.getsize(final_path)
    
    with zipfile.ZipFile(b15_path, "r") as z1:
        b15_entries = set(z1.namelist())
        b15_infolist = {i.filename: i.file_size for i in z1.infolist()}
        
    with zipfile.ZipFile(final_path, "r") as z2:
        final_entries = set(z2.namelist())
        final_infolist = {i.filename: i.file_size for i in z2.infolist()}
        
    only_in_b15 = b15_entries - final_entries
    only_in_final = final_entries - b15_entries
    common = b15_entries & final_entries
    
    # Calculate bytes attributed to experiments directory in backup15
    experiments_bytes = sum(b15_infolist[k] for k in b15_infolist if k.startswith("experiments/"))
    experiments_count = len([k for k in b15_entries if k.startswith("experiments/")])
    
    # Verify core production modules
    essential_checks = {
        "models/best_model.joblib": "models/best_model.joblib" in final_entries,
        "models/feature_pipeline.joblib": "models/feature_pipeline.joblib" in final_entries,
        "models/label_mapping.json": "models/label_mapping.json" in final_entries,
        "app.py": "app.py" in final_entries,
        "requirements.txt": "requirements.txt" in final_entries,
        "templates/base.html": "templates/base.html" in final_entries,
        "templates/career_mentor.html": "templates/career_mentor.html" in final_entries,
        "templates/interview_studio.html": "templates/interview_studio.html" in final_entries,
        "static/css/career_mentor.css": "static/css/career_mentor.css" in final_entries,
        "static/js/career_mentor.js": "static/js/career_mentor.js" in final_entries,
        "src/mentor/mentor_engine.py": "src/mentor/mentor_engine.py" in final_entries,
        "src/interview/question_generator.py": "src/interview/question_generator.py" in final_entries,
        "src/analysis/matching_engine.py": "src/analysis/matching_engine.py" in final_entries,
    }
    
    audit_summary = {
        "backup15_size_bytes": b15_size,
        "backup15_size_mb": round(b15_size / 1024 / 1024, 2),
        "backup15_entry_count": len(b15_entries),
        "final_size_bytes": final_size,
        "final_size_mb": round(final_size / 1024 / 1024, 2),
        "final_entry_count": len(final_entries),
        "size_reduction_mb": round((b15_size - final_size) / 1024 / 1024, 2),
        "experiments_uncompressed_bytes": experiments_bytes,
        "experiments_uncompressed_mb": round(experiments_bytes / 1024 / 1024, 2),
        "experiments_files_count": experiments_count,
        "only_in_b15_count": len(only_in_b15),
        "only_in_b15_sample": sorted(list(only_in_b15))[:25],
        "only_in_final_count": len(only_in_final),
        "only_in_final_sample": sorted(list(only_in_final))[:25],
        "essential_production_checks": essential_checks,
        "all_essentials_present": all(essential_checks.values()),
    }
    
    print(f"Backup15 Size: {audit_summary['backup15_size_mb']} MB ({len(b15_entries)} files)")
    print(f"Final Size: {audit_summary['final_size_mb']} MB ({len(final_entries)} files)")
    print(f"Experiments Directory in Backup15: {experiments_count} files, {audit_summary['experiments_uncompressed_mb']} MB uncompressed")
    print(f"Essential Production Assets Verified: {all(essential_checks.values())}")
    for k, v in essential_checks.items():
        print(f"  - {k}: {'PRESENT' if v else 'MISSING'}")
        
    with open(os.path.join(OUTPUT_DIR, "task4_archive_integrity.json"), "w") as f:
        json.dump(audit_summary, f, indent=2)
        
    return audit_summary


if __name__ == "__main__":
    t1_res, t1_rep = run_task_1()
    t2_res = run_task_2()
    t3_res = run_task_3()
    t4_res = run_task_4()
    print("\nALL TASKS EXECUTED SUCCESSFULLY.")
