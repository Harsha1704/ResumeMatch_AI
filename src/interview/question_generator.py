from src.utils.sanitizer import sanitize_text
"""
Interview Question Generator Module.
Generates, prioritizes, filters, and formats interview questions across six distinct categories:
- CATEGORY A: Resume-based Profile & Skill Questions
- CATEGORY B: Project-based Deep-Dive Questions
- CATEGORY C: Internship & Practical Experience Questions
- CATEGORY D: Target Job Description & Skill Gap Alignment Questions
- CATEGORY E: External Curated Technical Knowledge Questions
- CATEGORY F: HR & Behavioral Competency Questions

Enforces strict rules:
- Zero fabrication of candidate achievements, metrics, or technologies.
- Grounded in genuine extracted resume artifacts.
- Deterministic explainable ranking.
- Complete answers, simpler explanations, "why this works", follow-up questions, and step-by-step breakdowns for every question.
- Session-aware deduplication.
"""

from typing import Dict, List, Any, Optional
import hashlib
import re

from .question_bank import TECHNICAL_QUESTION_BANK, HR_QUESTION_BANK
from .answer_frameworks import FRAMEWORKS, get_framework, format_answer_template, build_completed_framework_demonstration
from .evidence_mapper import (
    extract_candidate_evidence,
    ground_guidance_in_evidence,
    build_grounded_project_answers,
    build_grounded_internship_answers
)
from .difficulty_engine import filter_by_difficulty, classify_question_difficulty

CATEGORY_METADATA = {
    "A": {"name": "Resume Profile & Technical Skills", "code": "CATEGORY_A", "badge": "bg-primary"},
    "B": {"name": "Extracted Project Deep-Dives", "code": "CATEGORY_B", "badge": "bg-info text-dark"},
    "C": {"name": "Internship & Practical Experience", "code": "CATEGORY_C", "badge": "bg-success"},
    "D": {"name": "Target Job & Skill Gap Alignment", "code": "CATEGORY_D", "badge": "bg-warning text-dark"},
    "E": {"name": "Core Technical Knowledge Bank", "code": "CATEGORY_E", "badge": "bg-secondary"},
    "F": {"name": "HR & Behavioral Competencies", "code": "CATEGORY_F", "badge": "bg-dark"}
}


class InterviewQuestionGenerator:
    """
    Deterministic question generation and ranking engine for Interview Intelligence Studio.
    Supplies complete answers, pedagogical step-by-step breakdowns, and explicit placeholders.
    """

    def __init__(self, analysis_data: Optional[Dict[str, Any]] = None):
        self.evidence = extract_candidate_evidence(analysis_data)
        self.analysis_data = analysis_data or {}

    def _make_id(self, prefix: str, text: str) -> str:
        """Generates a stable deterministic hash identifier."""
        h = hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
        return f"{prefix}_{h}"

    # -------------------------------------------------------------------------
    # Category A: Resume-based Questions
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Category A: Resume Profile & Technical Skills
    # -------------------------------------------------------------------------
    def generate_category_a(self, preferred_framework: Optional[str] = None) -> List[Dict[str, Any]]:
        questions = []
        skills = self.evidence["skills"]
        job_title = self.evidence["job_title"]
        matched_skills = self.evidence["matched_skills"]
        edu_summary = self.evidence["education"]
        has_role = self.evidence.get("has_target_role", True) and job_title and job_title != "Target role not specified"
        role_target_str = job_title if has_role else "target software engineering positions"
        
        primary_proj = self.evidence["projects"][0] if self.evidence.get("projects") else {}
        primary_title = primary_proj.get("title") or primary_proj.get("project_title")
        proj_context_str = f"In my primary project '{primary_title}'" if primary_title else "In my practical software projects"

        # Coherent skill categorization
        cat_map = {
            "languages": [],
            "frameworks": [],
            "ml_ai": [],
            "databases": [],
            "developer_tools": [],
            "behavioral": []
        }
        for s in skills:
            s_clean = s.strip()
            norm = s_clean.lower()
            if norm in ["python", "java", "c++", "c", "c#", "javascript", "typescript", "go", "rust", "ruby", "php", "scala", "r", "swift", "kotlin"]:
                cat_map["languages"].append(s_clean)
            elif any(k in norm for k in ["flask", "django", "fastapi", "react", "angular", "vue", "node", "express", "spring", "asp.net", "html", "css", "rest"]):
                cat_map["frameworks"].append(s_clean)
            elif any(k in norm for k in ["machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "opencv", "computer vision", "nlp", "keras"]):
                cat_map["ml_ai"].append(s_clean)
            elif any(k in norm for k in ["sql", "postgres", "mysql", "sqlite", "mongodb", "redis", "database", "spark", "hadoop"]):
                cat_map["databases"].append(s_clean)
            elif any(k in norm for k in ["docker", "kubernetes", "aws", "gcp", "azure", "git", "ci/cd", "linux", "jenkins", "devops"]):
                cat_map["developer_tools"].append(s_clean)
            elif any(k in norm for k in ["communication", "leadership", "teamwork", "mentorship", "adaptability", "problem solving", "presentation"]):
                cat_map["behavioral"].append(s_clean)
            else:
                cat_map["languages"].append(s_clean)

        # A1: Coherent technical stack overview (avoiding random mixing of soft skills and languages)
        if skills:
            if cat_map["languages"]:
                focus_skills = cat_map["languages"][:3]
                focus_label = "core programming languages"
            elif cat_map["frameworks"]:
                focus_skills = cat_map["frameworks"][:3]
                focus_label = "application frameworks"
            elif cat_map["ml_ai"]:
                focus_skills = cat_map["ml_ai"][:3]
                focus_label = "Machine Learning & AI tools"
            elif cat_map["developer_tools"]:
                focus_skills = cat_map["developer_tools"][:3]
                focus_label = "developer and cloud tools"
            else:
                focus_skills = skills[:3]
                focus_label = "technical skills"

            top_skills_str = ", ".join(focus_skills)
            q_id = self._make_id("qa_skill_overview", top_skills_str)
            q_text = f"Your resume highlights experience with {top_skills_str}. Walk me through how you have applied these {focus_label} in your software projects."
            fw_id = preferred_framework or "PREP"
            short_ans = f"I have applied {top_skills_str} across end-to-end software projects, designing modular architectures, writing automated tests, and optimizing performance."
            simpler_ans = f"My experience with {top_skills_str} focuses on building modular systems where each technology handles a clear responsibility, from data storage to API delivery."
            detailed_ans = (
                f"Throughout my development work, I have focused on applying {top_skills_str} as an integrated engineering toolkit. "
                f"Rather than learning technologies in isolation, I organize applications into decoupled operational layers: using backend frameworks for routing and API validation, "
                f"relational or document databases for persistent storage, and automated testing suites to verify system behavior. "
                f"{proj_context_str}, I combined these tools to deliver end-to-end functionality while adhering to clean code standards and automated test coverage. "
                f"This practical experience allows me to understand both the strengths and the operational constraints of each tool in production environments."
            )
            why_this_works = (
                "Interviewers ask this question to test whether you treat your skills as an active problem-solving toolkit or merely as keywords on a resume. "
                "This answer works because it immediately connects abstract skill names to concrete software development practices like modularity, clean separation of concerns, and automated testing."
            )
            steps = [
                {
                    "step": "Step 1: Frame the Core Technical Toolkit",
                    "complete_explanation": f"Anchor your technical identity in {top_skills_str}. Clearly categorizing tools by their architectural layers demonstrates structured systems thinking rather than reciting an unstructured list.",
                    "reasoning": "Interviewers evaluate whether you understand the architectural role of each technology in a production stack.",
                    "concrete_example": f"Categorizing {focus_skills[0]} for backend processing, {focus_skills[1] if len(focus_skills)>1 else 'SQL'} for persistence, and Git for version control.",
                    "connection_to_question": "Directly sets the structural baseline for your technical overview.",
                    "detail": f"Anchor your technical identity in {top_skills_str}. Clearly categorizing tools by their architectural layers demonstrates structured systems thinking rather than reciting an unstructured list."
                },
                {
                    "step": "Step 2: Explain Modular Architectural Integration",
                    "complete_explanation": f"Explain how you integrate these tools into decoupled architectures: establishing clear contract boundaries between data ingestion, domain business logic, and database persistence layers.",
                    "reasoning": "Decoupled architectures allow individual components to be modified, benchmarked, and maintained without cascading side effects.",
                    "concrete_example": "Structuring code into controllers, service layer business objects, and repository data mappers.",
                    "connection_to_question": "Shows how verified skills translate into organized software systems.",
                    "detail": f"Explain how you integrate these tools into decoupled architectures: establishing clear contract boundaries between data ingestion, domain business logic, and database persistence layers."
                },
                {
                    "step": "Step 3: Ground in a Concrete Production Project",
                    "complete_explanation": f"Cite {primary_title or 'your practical portfolio'} to illustrate these tools operating simultaneously under real functional requirements, referencing automated input validation and error boundaries.",
                    "reasoning": "Grounding claims in an actual project provides verifiable empirical proof of your technical capabilities.",
                    "concrete_example": "Describing how API requests are parsed, validated, processed by business logic, and persisted to relational tables.",
                    "connection_to_question": "Provides tangible evidence backing your technical assertions.",
                    "detail": f"Cite {primary_title or 'your practical portfolio'} to illustrate these tools operating simultaneously under real functional requirements, referencing automated input validation and error boundaries."
                },
                {
                    "step": "Step 4: Highlight Testing & Quality Assurance Rigor",
                    "complete_explanation": "Emphasize that your workflow incorporates automated unit testing, parametrized edge-case validation, and continuous integration checks before code is considered complete.",
                    "reasoning": "Engineering teams value developers who verify their own code with automated tests over those who rely on manual testing.",
                    "concrete_example": "Writing pytest fixtures with mock objects to validate service logic across boundary conditions.",
                    "connection_to_question": "Demonstrates engineering craftsmanship and release reliability.",
                    "detail": "Emphasize that your workflow incorporates automated unit testing, parametrized edge-case validation, and continuous integration checks before code is considered complete."
                },
                {
                    "step": "Step 5: Articulate Trade-Off Awareness & Constraints",
                    "complete_explanation": "Discuss operational trade-offs you observed when working with this stack—such as CPU execution overhead versus developer velocity—and explain how you balanced them.",
                    "reasoning": "Understanding trade-offs proves you do not treat technologies as silver bullets.",
                    "concrete_example": "Evaluating when in-memory caching is necessary to prevent database connection exhaustion under high traffic.",
                    "connection_to_question": "Shows senior-level technical self-awareness.",
                    "detail": "Discuss operational trade-offs you observed when working with this stack—such as CPU execution overhead versus developer velocity—and explain how you balanced them."
                },
                {
                    "step": f"Step 6: Connect Capabilities to {role_target_str} Delivery",
                    "complete_explanation": f"Conclude by tying your demonstrated proficiency directly to {role_target_str}, emphasizing rapid ramp-up and immediate contribution to the team's release goals.",
                    "reasoning": "Connecting past experience to future value reinforces hiring ROI for the interviewer.",
                    "concrete_example": f"Ready to navigate existing codebases, review teammate PRs, and implement features aligned with {role_target_str}.",
                    "connection_to_question": "Concludes with business alignment and candidate readiness.",
                    "detail": f"Conclude by tying your demonstrated proficiency directly to {role_target_str}, emphasizing rapid ramp-up and immediate contribution to the team's release goals."
                }
            ]
            follow_ups = [
                {
                    "question": f"Which of these tools ({', '.join(focus_skills[:3])}) are you most comfortable debugging under time pressure?",
                    "reference_answer": (
                        f"I am most comfortable debugging with {focus_skills[0]} because I regularly use interactive debuggers, read stack traces, and inspect state transitions to isolate logic bugs systematically. "
                        f"When troubleshooting under pressure, I follow a disciplined methodology: reproducing the issue with a minimal test case, inspecting execution logs to identify the exact failing line, and analyzing variable states. "
                        f"I avoid guesswork or modifying multiple files simultaneously, which prevents introducing secondary bugs. "
                        f"Once the root cause is resolved, I commit an automated regression test covering that edge case to permanently prevent recurrence."
                    ),
                    "technical_justification": "Systematic debugging using debuggers and minimal reproductions isolates bugs faster than random trial-and-error hotfixes.",
                    "practical_example": f"Setting breakpoints in pdb or IDE debuggers to inspect local variable bindings at the point of failure.",
                    "interview_takeaway": "Emphasize a calm, systematic debugging protocol: reproduce, isolate via logs/breakpoints, patch, and lock with a regression test."
                },
                {
                    "question": "How do you decide when to adopt a third-party library versus writing a custom in-house implementation?",
                    "reference_answer": (
                        "When evaluating a third-party library, I balance developer velocity against long-term operational maintenance and security overhead. "
                        "I review the library's active maintenance frequency, test coverage, community adoption, license compatibility, and dependency tree depth. "
                        "If the requirement involves complex domain standards—such as cryptographic hashing, JWT verification, or database connection pooling—relying on mature, audited libraries is mandatory. "
                        "However, if the requirement is a lightweight utility that can be solved in 20 lines of clean code, I write an in-house function to avoid bloating dependencies and exposing the project to supply-chain vulnerabilities."
                    ),
                    "technical_justification": "Third-party dependencies accelerate initial delivery but introduce security surface area and version lock-in risks.",
                    "practical_example": "Using standard library `secrets` and `hashlib` for basic hashing instead of pulling in an abandoned multi-megabyte utility library.",
                    "interview_takeaway": "Frame dependency adoption around security auditing, licensing, maintenance activity, and avoiding supply-chain bloat."
                },
                {
                    "question": "How do you ensure code maintainability when collaborating with multiple engineers on the same codebase?",
                    "reference_answer": (
                        "Code maintainability across a team requires shared conventions, automated tooling, and constructive peer reviews. "
                        "First, I advocate for automated code formatters and linters (such as Black, Flake8, or ESLint) integrated into pre-commit hooks and CI pipelines so style debates never clutter pull reviews. "
                        "Second, I enforce modular function design and descriptive variable naming, ensuring each method adheres to the Single Responsibility Principle. "
                        "Finally, I write descriptive pull request summaries detailing the problem, solution, and testing steps, which accelerates review velocity and preserves architectural history in the Git log."
                    ),
                    "technical_justification": "Automating style enforcement and adhering to clean architectural boundaries minimizes merge conflicts and reviewer fatigue.",
                    "practical_example": "Configuring GitHub Actions to run linters and requiring passing status checks before PRs can be merged.",
                    "interview_takeaway": "Highlight automated linting in CI, atomic pull requests, descriptive documentation, and constructive code review habits."
                }
            ]
            common_mistakes = [
                "Reciting the entire skills section of your resume like a grocery list without giving project context.",
                "Claiming deep mastery in tools you have only used once in a brief tutorial.",
                "Failing to explain how the tools worked together in an integrated system."
            ]
            missing_details = ["Cite the primary project where these specific tools were integrated."]

            questions.append({
                "question_id": q_id,
                "question_text": q_text,
                "category": "A",
                "category_name": CATEGORY_METADATA["A"]["name"],
                "category_badge": CATEGORY_METADATA["A"]["badge"],
                "difficulty": "Medium",
                "source_type": "resume_skill",
                "source_reference": f"Extracted Skills: {top_skills_str}",
                "recommended_answer_framework": fw_id,
                "recommended_framework": fw_id,
                "short_answer": short_ans,
                "simpler_answer": simpler_ans,
                "detailed_answer": detailed_ans,
                "curated_answer": detailed_ans,
                "why_this_works": why_this_works,
                "step_by_step_explanation": steps,
                "follow_up_questions": follow_ups,
                "common_mistakes": common_mistakes,
                "examples": f"Applied {top_skills_str} across end-to-end software and data processing implementations.",
                "code_snippet": None,
                "important_concepts": focus_skills,
                "interview_tips": [
                    "Group related skills logically (e.g. languages, frameworks, databases) rather than reciting an unstructured list.",
                    "Highlight one specific project where multiple tools operated together seamlessly."
                ],
                "missing_personal_details": missing_details,
                "suggested_improvements": "Suggested Improvement (Hypothetical Proposal): Containerizing multi-tier environments to ensure identical behavior across developer machines and staging servers.",
                "verified_evidence": [f"Extracted Resume Skills: {top_skills_str}"],
                "evidence_sources": ["Extracted Resume Skills", "Candidate Project Records"],
                "expected_key_points": [
                    "Overview of technical stack proficiency",
                    "Practical application in concrete projects",
                    "How tool selection mapped to project requirements"
                ],
                "framework_template": format_answer_template(fw_id, {
                    "Point": f"My technical background is anchored in {top_skills_str}.",
                    "Reason": "I have developed end-to-end applications utilizing these tools in academic and practical settings.",
                    "Example": f"{proj_context_str}, these technologies were combined to handle data transformation and business logic.",
                    "Point_Conclusion": f"This foundation prepares me to adapt effectively to {role_target_str} requirements."
                })
            })

            # Optional A1b: Focused ML / AI question if candidate has ML skills
            if cat_map["ml_ai"] and focus_label != "Machine Learning & AI tools":
                ml_skills = cat_map["ml_ai"][:3]
                ml_skills_str = ", ".join(ml_skills)
                q_id_ml = self._make_id("qa_ml_overview", ml_skills_str)
                q_text_ml = f"Your background features Machine Learning tools ({ml_skills_str}). Walk me through your methodology for data preprocessing, model selection, and validation to prevent overfitting."
                questions.append({
                    "question_id": q_id_ml,
                    "question_text": q_text_ml,
                    "category": "A",
                    "category_name": CATEGORY_METADATA["A"]["name"],
                    "category_badge": CATEGORY_METADATA["A"]["badge"],
                    "difficulty": "Medium",
                    "source_type": "resume_skill",
                    "source_reference": f"Machine Learning Stack: {ml_skills_str}",
                    "recommended_answer_framework": "STAR",
                    "recommended_framework": "STAR",
                    "short_answer": f"When applying {ml_skills_str}, I enforce strict train/test isolation, clean numerical preprocessing, and evaluate models using stratified cross-validation and Macro F1.",
                    "simpler_answer": f"My workflow with {ml_skills_str} ensures that all data preprocessing occurs inside cross-validation folds, avoiding data leakage and tuning hyperparameters to prevent overfitting.",
                    "detailed_answer": (
                        f"In projects utilizing {ml_skills_str}, my modeling methodology prioritizes inductive generalization over raw memorization. "
                        f"I begin by isolating a holdout test partition before any transformation, handling missing values and feature scaling inside scikit-learn Pipelines. "
                        f"To detect overfitting, I monitor the gap between training accuracy and cross-validation Macro F1, applying L2 regularization or dropout where appropriate. "
                        f"Finally, I evaluate model error slices across challenging boundary cases rather than relying solely on global accuracy metrics."
                    ),
                    "curated_answer": f"My methodology with {ml_skills_str} isolates preprocessing inside cross-validation folds to prevent data leakage and evaluates models using Macro F1 and confusion matrices.",
                    "why_this_works": "Demonstrates rigorous ML hygiene: data leakage prevention, cross-validation isolation, and balanced metric evaluation.",
                    "step_by_step_explanation": [
                        {"step": "Step 1: Strict Partition Hygiene", "complete_explanation": "Split dataset into train, validation, and test before fitting any vectorizers or scalers.", "reasoning": "Prevents data leakage."},
                        {"step": "Step 2: Pipeline Encapsulation", "complete_explanation": "Encapsulate transformers and classifiers inside Pipeline objects.", "reasoning": "Guarantees fold-level preprocessing isolation."},
                        {"step": "Step 3: Multi-Metric Evaluation", "complete_explanation": "Evaluate Precision, Recall, and Macro F1 rather than raw accuracy.", "reasoning": "Detects class imbalance failures."},
                        {"step": "Step 4: Regularization & Overfitting Defense", "complete_explanation": "Monitor train vs cross-validation loss curve divergence and apply dropout or L2 weight decay.", "reasoning": "Maintains inductive bias and generalization capability."},
                        {"step": "Step 5: Error Slice Analysis", "complete_explanation": "Inspect confusion matrix error slices across underrepresented categories before deploying.", "reasoning": "Identifies localized systematic failure patterns."}
                    ],
                    "follow_up_questions": [
                        {"question": "How do you detect data leakage in a pipeline?", "reference_answer": "By inspecting whether preprocessing transformers were fitted globally or strictly inside cross-validation training folds."},
                        {"question": "What regularizations do you apply if validation loss diverges from training loss?", "reference_answer": "I apply L2 weight decay, dropout layers, early stopping, or prune unnecessary feature dimensions to reduce model variance."},
                        {"question": "Why is Macro F1 preferred over Accuracy when evaluating classification models?", "reference_answer": "Macro F1 gives equal weight to every category, preventing majority-class dominance from masking severe failures on minority classes."}
                    ],
                    "common_mistakes": ["Fitting scalers on the full dataset before cross-validation.", "Evaluating only accuracy on imbalanced classes."],
                    "examples": f"Built predictive pipelines using {ml_skills_str} with leakage-free cross-validation.",
                    "code_snippet": None,
                    "important_concepts": ml_skills,
                    "interview_tips": ["Always emphasize that preprocessing occurs strictly inside cross-validation folds."],
                    "missing_personal_details": ["Cite specific dataset and metrics from your projects."],
                    "suggested_improvements": "Implement automated error slice analysis.",
                    "verified_evidence": [f"Machine Learning Tools: {ml_skills_str}"],
                    "evidence_sources": ["Candidate ML Skills"],
                    "expected_key_points": ["Leakage prevention", "Validation strategy", "Overfitting mitigation"],
                    "framework_template": format_answer_template("STAR", {
                        "Situation": f"Developing predictive models using {ml_skills_str}.",
                        "Task": "Ensure model generalizes reliably to unseen data without data leakage.",
                        "Action": "Encapsulated preprocessing inside scikit-learn Pipelines and evaluated using StratifiedKFold.",
                        "Result": "Achieved stable generalization with zero validation data leakage."
                    })
                })

        # A2: Academic foundation / education (Never render internal parser messages)
        is_edu_clean = self.evidence.get("is_edu_verified", True) and edu_summary and "not confirmed" not in edu_summary.lower() and "degree not explicitly" not in edu_summary.lower()
        if is_edu_clean:
            edu_display = edu_summary
            q_text_edu = f"How has your academic background ({edu_summary}) provided the theoretical foundation for your software and engineering work?"
        else:
            edu_display = "computer science and software engineering fundamentals"
            q_text_edu = "How has your foundational study in computer science principles provided the theoretical basis for your software engineering work?"

        fw_edu = preferred_framework or "PREP"
        short_edu = f"My foundational studies in {edu_display} provided the rigorous theoretical grounding in Data Structures, Algorithms, Operating Systems, and DBMS that underpins my engineering work."
        simpler_edu = f"My education in {edu_display} gave me the core computer science principles—like analyzing algorithm complexity and understanding database transactions—that guide how I design reliable software."
        detailed_edu = (
            f"My coursework and technical study in {edu_display} provided the foundational principles behind scalable software engineering. "
            f"Studying Data Structures and Algorithms taught me computational complexity analysis and selecting optimal data structures for memory and speed. "
            f"Courses in Database Management Systems and Operating Systems provided deep insight into transaction isolation, concurrency, and virtual memory management. "
            f"In my practical projects, I continually leverage these theoretical concepts to evaluate architectural trade-offs and write efficient, maintainable code."
        )
        why_this_works_edu = (
            "Hiring managers ask this to determine if you understand core computer science principles or are merely a framework user who copies tutorials. "
            "This answer succeeds because it connects university theory (algorithms, operating systems, databases) directly to daily engineering decisions like complexity analysis and memory safety."
        )
        steps_edu = [
            {
                "step": "Step 1: Anchor in Foundational CS Curriculum",
                "complete_explanation": f"Reference core coursework from {edu_summary}—specifically Data Structures, Algorithms, Operating Systems, Database Management Systems, and Computer Networks. This demonstrates a comprehensive computer science education.",
                "reasoning": "Grounding discussions in formal coursework shows hiring managers that you understand computer science fundamentals.",
                "concrete_example": f"Highlighting coursework in Data Structures, Relational DBMS, and OS Concurrency from {edu_summary}.",
                "connection_to_question": "Directly links academic training to technical depth.",
                "detail": f"Reference core coursework from {edu_summary}—specifically Data Structures, Algorithms, Operating Systems, Database Management Systems, and Computer Networks. This demonstrates a comprehensive computer science education."
            },
            {
                "step": "Step 2: Connect Complexity Analysis to Performance",
                "complete_explanation": "Explain how asymptotic complexity analysis (Big-O notation) informs your choice of data structures, avoiding O(N^2) bottlenecks when processing large datasets in memory.",
                "reasoning": "Understanding time and space complexity is the hallmark of disciplined software engineering.",
                "concrete_example": "Choosing hash maps for O(1) lookups instead of repeated list scans during high-volume data filtering.",
                "connection_to_question": "Bridges classroom theory with real-world code efficiency.",
                "detail": "Explain how asymptotic complexity analysis (Big-O notation) informs your choice of data structures, avoiding O(N^2) bottlenecks when processing large datasets in memory."
            },
            {
                "step": "Step 3: Apply Operating System Internals to Concurrency",
                "complete_explanation": "Discuss how studying operating systems—processes, threads, context switching, and virtual memory—guides your design of asynchronous request pipelines and non-blocking I/O operations.",
                "reasoning": "Systems-level understanding prevents concurrency race conditions and resource leaks.",
                "concrete_example": "Understanding thread safety and avoiding deadlocks when multiple workers access shared in-memory caches.",
                "connection_to_question": "Illustrates how lower-level systems theory informs modern web backend development.",
                "detail": "Discuss how studying operating systems—processes, threads, context switching, and virtual memory—guides your design of asynchronous request pipelines and non-blocking I/O operations."
            },
            {
                "step": "Step 4: Leverage Relational Theory for ACID Integrity",
                "complete_explanation": "Explain how studying relational database normalization (1NF through 3NF) and ACID transaction properties ensures that your applications maintain data consistency under concurrent updates.",
                "reasoning": "Relational database theory guarantees that database schemas are normalized and resistant to insertion/deletion anomalies.",
                "concrete_example": "Designing relational tables with foreign keys and unique constraints verified via migration scripts.",
                "connection_to_question": "Demonstrates database design rigor and transactional safety.",
                "detail": "Explain how studying relational database normalization (1NF through 3NF) and ACID transaction properties ensures that your applications maintain data consistency under concurrent updates."
            },
            {
                "step": "Step 5: Illustrate with Concrete Project Architecture",
                "complete_explanation": "Describe a specific instance in your practical portfolio where an algorithmic optimization or transactional guarantee directly improved system performance or reliability.",
                "reasoning": "Practical illustrations prove that academic theory is actively utilized in production-style code.",
                "concrete_example": "Refactoring an unindexed database query to use composite indexes, reducing query latency from seconds to milliseconds.",
                "connection_to_question": "Provides empirical evidence of applied theory in practical projects.",
                "detail": "Describe a specific instance in your practical portfolio where an algorithmic optimization or transactional guarantee directly improved system performance or reliability."
            },
            {
                "step": "Step 6: Emphasize Long-Term Technology Adaptability",
                "complete_explanation": "Conclude that strong theoretical foundations make adopting new frameworks, languages, or cloud paradigms straightforward, because underlying architectural patterns remain invariant.",
                "reasoning": "Frameworks change every few years, but computer science fundamentals remain invariant throughout an engineering career.",
                "concrete_example": "Ramping up on new asynchronous libraries or distributed engines in days by leveraging core concurrency fundamentals.",
                "connection_to_question": "Concludes with long-term adaptability and hiring value.",
                "detail": "Conclude that strong theoretical foundations make adopting new frameworks, languages, or cloud paradigms straightforward, because underlying architectural patterns remain invariant."
            }
        ]
        follow_ups_edu = [
            {
                "question": "Can you share a time where an algorithm or data structure choice had a noticeable impact on code performance?",
                "reference_answer": (
                    "In a data processing task involving matching candidate profiles against keyword vocabularies, the initial implementation utilized nested loops scanning a list of records, resulting in an O(N*M) quadratic time complexity. "
                    "As the candidate dataset grew to several thousand records, execution latency degraded significantly, taking over 45 seconds to complete. "
                    "I refactored the lookup routine to pre-index the vocabulary into a Python dictionary (hash table), reducing lookup operations to O(1) amortized time. "
                    "This algorithmic optimization dropped total execution time from 45 seconds to under 0.8 seconds—a 50x speedup—while keeping memory utilization within acceptable bounds. "
                    "This experience reinforced the direct, measurable business value of selecting the correct data structure."
                ),
                "technical_justification": "Hash tables leverage hashing algorithms to achieve O(1) amortized lookup complexity, eliminating expensive O(N) linear scans across arrays.",
                "practical_example": "Replacing `[item for item in items if item.id in list_of_ids]` with a `set(list_of_ids)` hash lookup.",
                "interview_takeaway": "Quantify algorithmic speedups with before-and-after execution times and explain the time complexity shift."
            },
            {
                "question": "How has understanding operating system internals influenced the way you write software?",
                "reference_answer": (
                    "Understanding operating system primitives—specifically the distinction between CPU-bound processes and I/O-bound threads—fundamentally guides how I architect backend services. "
                    "For I/O-heavy workloads like handling HTTP requests and database queries, I leverage asynchronous event loops (such as asyncio or Node.js) to handle thousands of concurrent connections with minimal memory overhead. "
                    "Conversely, for CPU-intensive data transformations, I know that thread-based concurrency in languages with a Global Interpreter Lock (like Python) cannot achieve true parallelism, so I delegate work to multi-process pools or background task queues. "
                    "Furthermore, understanding file descriptor limits and socket buffers ensures that I configure connection pools defensively to prevent OS resource exhaustion."
                ),
                "technical_justification": "Asynchronous event loops multiplex I/O without thread context-switching overhead, while multiprocessing circumvents runtime GIL locks.",
                "practical_example": "Using `multiprocessing.Pool` for image processing and `asyncio` for high-volume network web scraping.",
                "interview_takeaway": "Differentiate I/O-bound event loops from CPU-bound multiprocessing, referencing resource limits and context-switching overhead."
            },
            {
                "question": "How do database transaction isolation levels protect application state under high concurrency?",
                "reference_answer": (
                    "Database transaction isolation levels define the degree to which concurrent transactions are shielded from each other's uncommitted modifications. "
                    "The SQL standard specifies four levels: Read Uncommitted, Read Committed, Repeatable Read, and Serializable, each trading performance for consistency. "
                    "In most web applications, Read Committed prevents dirty reads by ensuring queries only observe committed data. "
                    "For financial transactions or inventory deductions where lost updates or non-repeatable reads cannot be tolerated, I configure Repeatable Read or use explicit row-level locking (`SELECT ... FOR UPDATE`). "
                    "Understanding these trade-offs ensures I balance transaction throughput against strict data integrity requirements."
                ),
                "technical_justification": "Lower isolation levels increase concurrency throughput but risk dirty or non-repeatable reads; higher levels enforce strict isolation at the cost of lock contention.",
                "practical_example": "Executing `SELECT balance FROM accounts WHERE id = 1 FOR UPDATE` to serialize concurrent withdrawals.",
                "interview_takeaway": "Explain the progression from Read Committed to Serializable, balancing lock contention against transactional integrity."
            }
        ]
        common_mistakes_edu = [
            "Dismissing academic theory as irrelevant to real-world software development.",
            "Reciting textbook definitions without demonstrating how theory informs daily programming choices.",
            "Focusing solely on grades or courses rather than applied problem-solving rigor."
        ]
        questions.append({
            "question_id": self._make_id("qa_edu", q_text_edu),
            "question_text": q_text_edu,
            "category": "A",
            "category_name": CATEGORY_METADATA["A"]["name"],
            "category_badge": CATEGORY_METADATA["A"]["badge"],
            "difficulty": "Easy",
            "source_type": "resume_education",
            "source_reference": f"Education: {edu_summary}",
            "recommended_answer_framework": fw_edu,
            "recommended_framework": fw_edu,
            "short_answer": short_edu,
            "simpler_answer": simpler_edu,
            "detailed_answer": detailed_edu,
            "curated_answer": detailed_edu,
            "why_this_works": why_this_works_edu,
            "step_by_step_explanation": steps_edu,
            "follow_up_questions": follow_ups_edu,
            "common_mistakes": common_mistakes_edu,
            "examples": "Leveraged algorithmic complexity analysis and database transaction theory across project architectures.",
            "code_snippet": None,
            "important_concepts": ["Data Structures & Algorithms", "Operating Systems", "DBMS", "Computational Complexity"],
            "interview_tips": [
                "Link theoretical computer science coursework directly to real-world code quality and architectural trade-offs.",
                "Emphasize that strong fundamentals make learning new frameworks straightforward."
            ],
            "missing_personal_details": [],
            "suggested_improvements": "Suggested Improvement (Hypothetical Proposal): Profiling algorithmic hot-spots using automated micro-benchmarks before deploying major feature releases.",
            "verified_evidence": [f"Education Mention: {edu_summary}"],
            "evidence_sources": [f"Education Mention: {edu_summary}"],
            "expected_key_points": [
                "Foundational CS coursework (Data Structures, Algorithms, OS, DBMS)",
                "Transition from classroom concepts to working software",
                "Analytical problem-solving methodologies"
            ],
            "framework_template": format_answer_template(fw_edu)
        })

        # A3: Direct matched skills confidence
        if matched_skills:
            m_str = ", ".join(matched_skills[:4])
            q_text_m = f"You possess direct verified experience in {m_str}, which are core requirements for this position. What makes you confident in your mastery of these tools?"
            fw_m = preferred_framework or "CAR"
            short_m = f"I have direct, hands-on experience applying {m_str} to build and debug software systems, giving me confidence in delivering immediate value in this role."
            simpler_m = f"I am confident using {m_str} because I have written, debugged, and tested real code with them, so I understand both their core patterns and their edge-case behaviors."
            detailed_m = (
                f"I am confident in my proficiency with {m_str} because I have worked with them beyond textbook exercises, integrating them into functional project pipelines. "
                f"Working with these technologies taught me how to navigate real-world engineering constraints, read documentation, debug complex stack traces, and write maintainable code. "
                f"{proj_context_str}, I leveraged these tools to implement key operational modules, validating inputs and optimizing performance under load. "
                f"Because this toolset aligns directly with your {role_target_str} tech stack, I can hit the ground running with minimal onboarding overhead."
            )
            why_this_works_m = (
                "Interviewers want to assess your day-one ramp-up speed and verify that your resume matches your real ability. "
                "This answer works because it acknowledges the team's stack directly and highlights practical debugging and testing habits rather than superficial familiarity."
            )
            steps_m = [
                {
                    "step": "Step 1: Acknowledge Tech Stack Alignment (Challenge)",
                    "complete_explanation": f"Acknowledge the core requirement for {m_str} in {role_target_str}, recognizing why these tools are foundational to the team's software delivery.",
                    "reasoning": "Showing immediate awareness of the employer's tech stack demonstrates preparation and respect for their architectural decisions.",
                    "concrete_example": f"Connecting {m_str} to production API reliability and data persistence in {role_target_str}.",
                    "connection_to_question": "Directly sets up your confidence and alignment with role requirements.",
                    "detail": f"Acknowledge the core requirement for {m_str} in {role_target_str}, recognizing why these tools are foundational to the team's software delivery."
                },
                {
                    "step": "Step 2: Demonstrate Hands-On Depth Beyond Tutorials (Action)",
                    "complete_explanation": "Explain that your familiarity is grounded in writing, debugging, and maintaining functional code rather than passive tutorial viewing. Discuss navigating complex error traces and reading official documentation.",
                    "reasoning": "Interviewers frequently encounter candidates with superficial resume keywords; proving debugging depth verifies genuine competence.",
                    "concrete_example": "Resolving runtime exceptions, profiling slow queries, and inspecting network payloads.",
                    "connection_to_question": "Validates hands-on implementation capabilities.",
                    "detail": "Explain that your familiarity is grounded in writing, debugging, and maintaining functional code rather than passive tutorial viewing. Discuss navigating complex error traces and reading official documentation."
                },
                {
                    "step": "Step 3: Cite Concrete Deliverables & Project Impact",
                    "complete_explanation": "Cite a specific technical feature developed using this toolset, explaining the problem it resolved and the design choices made.",
                    "reasoning": "Empirical examples transform abstract confidence claims into verifiable engineering achievements.",
                    "concrete_example": "Building a secure authentication pipeline or high-throughput batch ingestion service using this stack.",
                    "connection_to_question": "Supplies concrete empirical evidence.",
                    "detail": "Cite a specific technical feature developed using this toolset, explaining the problem it resolved and the design choices made."
                },
                {
                    "step": "Step 4: Highlight Defensive Programming & Automated Testing",
                    "complete_explanation": "Discuss how you write automated unit tests, enforce input schema validation, and handle boundary conditions defensively when developing with these tools.",
                    "reasoning": "Senior interviewers value developers who write resilient, test-backed code that prevents production outages.",
                    "concrete_example": "Authoring automated test suites with Pytest or Jest covering edge-case inputs.",
                    "connection_to_question": "Demonstrates engineering craftsmanship and reliability.",
                    "detail": "Discuss how you write automated unit tests, enforce input schema validation, and handle boundary conditions defensively when developing with these tools."
                },
                {
                    "step": "Step 5: Articulate Framework Pitfalls & Best Practices",
                    "complete_explanation": "Discuss common framework anti-patterns—such as state mutation, memory leaks, or unindexed database queries—and explain how you actively avoid them.",
                    "reasoning": "Awareness of subtle pitfalls is the clearest differentiator between intermediate and novice developers.",
                    "concrete_example": "Avoiding N+1 query problems in ORMs or managing resource cleanup via context managers.",
                    "connection_to_question": "Proves deep mechanical familiarity with the toolset.",
                    "detail": "Discuss common framework anti-patterns—such as state mutation, memory leaks, or unindexed database queries—and explain how you actively avoid them."
                },
                {
                    "step": "Step 6: Confirm Rapid Day-One Ramp-Up (Result)",
                    "complete_explanation": f"Conclude by explaining how this verified overlap drastically shortens onboarding duration, enabling you to contribute to sprint velocity within days.",
                    "reasoning": "Minimizing ramp-up overhead is a primary priority for hiring managers.",
                    "concrete_example": f"Familiar with development workflows, testing patterns, and dependency conventions in {m_str}.",
                    "connection_to_question": "Concludes with business value and immediate impact.",
                    "detail": f"Conclude by explaining how this verified overlap drastically shortens onboarding duration, enabling you to contribute to sprint velocity within days."
                }
            ]
            follow_ups_m = [
                {
                    "question": f"What is one subtle pitfall or common trap developers run into when using {matched_skills[0]}?",
                    "reference_answer": (
                        f"A subtle and frequent pitfall in {matched_skills[0]} is unhandled state lifecycle leaks or unindexed resource access. "
                        f"In data and web applications, developers often fail to configure explicit connection pool timeouts or accidentally retain references to large objects in memory. "
                        f"Another common mistake is ignoring database query generation in ORMs, which inadvertently triggers N+1 query cascades across related tables. "
                        f"I mitigate these traps by configuring strict linting rules, profiling queries with database execution explain plans, and writing automated unit tests around resource boundary limits."
                    ),
                    "technical_justification": "N+1 query cascades and unmanaged connection pools cause exponential database latency degradation under concurrent traffic.",
                    "practical_example": f"Using eager loading (`select_related` or `joinedload`) in ORMs to eliminate N+1 query loops in {matched_skills[0]}.",
                    "interview_takeaway": "Identify a specific technical pitfall (like N+1 queries or memory retention) and explain your proactive prevention strategy."
                },
                {
                    "question": "How do you stay up-to-date with new versions, security advisories, and best practices for these tools?",
                    "reference_answer": (
                        "I maintain technical currency through structured engineering channels rather than superficial social media trends. "
                        "I follow official repository release notes and GitHub release tags for core frameworks in my stack, noting deprecated methods and migration paths. "
                        "For security, I utilize automated dependency scanning tools like Dependabot and Snyk to alert me to CVE vulnerabilities in third-party libraries. "
                        "Finally, when major version upgrades are released, I test them in an isolated branch with our automated test suite to evaluate performance changes and breaking syntax before proposing adoption."
                    ),
                    "technical_justification": "Automated security scanners and testing major releases in isolated branches prevents supply-chain vulnerabilities from reaching production.",
                    "practical_example": "Setting up Dependabot in GitHub repositories to open automated PRs for patched security dependencies.",
                    "interview_takeaway": "Emphasize structured release monitoring, automated vulnerability scanning (Dependabot), and staging test verification."
                },
                {
                    "question": f"How would you onboard and mentor a junior engineer who is learning {matched_skills[0]} for the first time?",
                    "reference_answer": (
                        f"When onboarding an engineer to {matched_skills[0]}, I start by providing a reproducible local development environment using Docker to eliminate configuration friction. "
                        f"I walk them through the repository architecture and point them toward our core unit test suite, because reading existing tests is the fastest way to understand expected system behavior. "
                        f"I assign an initial small, bounded bug fix or feature ticket and conduct a collaborative pair-programming session to review development and testing workflows. "
                        f"During code reviews, I provide detailed, encouraging feedback that explains the 'why' behind architectural patterns, empowering them to become autonomous quickly."
                    ),
                    "technical_justification": "Reproducible Docker environments and reading unit tests accelerate developer onboarding while maintaining codebase standards.",
                    "practical_example": "Providing a `docker-compose.yml` and a curated first-ticket issue with clear acceptance criteria.",
                    "interview_takeaway": "Demonstrate supportive mentorship: reproducible environments, test-driven code orientation, and constructive code reviews."
                }
            ]
            common_mistakes_m = [
                "Overstating confidence without providing concrete architectural examples.",
                "Getting defensive when asked about edge cases or deeper framework internals.",
                "Neglecting to mention how you test and maintain code written in these technologies."
            ]
            questions.append({
                "question_id": self._make_id("qa_match", q_text_m),
                "question_text": q_text_m,
                "category": "A",
                "category_name": CATEGORY_METADATA["A"]["name"],
                "category_badge": CATEGORY_METADATA["A"]["badge"],
                "difficulty": "Medium",
                "source_type": "resume_matched_skill",
                "source_reference": f"Direct Skill Match: {m_str}",
                "recommended_answer_framework": fw_m,
                "recommended_framework": fw_m,
                "short_answer": short_m,
                "simpler_answer": simpler_m,
                "detailed_answer": detailed_m,
                "curated_answer": detailed_m,
                "why_this_works": why_this_works_m,
                "step_by_step_explanation": steps_m,
                "follow_up_questions": follow_ups_m,
                "common_mistakes": common_mistakes_m,
                "examples": f"Integrated {m_str} within real project codebases to build resilient features.",
                "code_snippet": None,
                "important_concepts": matched_skills[:4],
                "interview_tips": [
                    f"Mention specific libraries, idioms, or debugging tools you used with {m_str}.",
                    "Emphasize code maintainability and testability."
                ],
                "missing_personal_details": [f"[Provide a concrete example where {m_str} was used to build a key feature or optimize performance]"],
                "suggested_improvements": "Suggested Improvement (Hypothetical Proposal): Establishing automated end-to-end integration tests to validate full workflows across all matched technologies.",
                "verified_evidence": [f"Direct Match: {m_str}"],
                "evidence_sources": ["Matched Skills against Target Job Description"],
                "expected_key_points": [
                    f"Hands-on depth in {m_str}",
                    "Architectural patterns or libraries utilized",
                    "Debugging and testing rigor"
                ],
                "framework_template": format_answer_template(fw_m)
            })

        return questions
    def generate_category_b(self, preferred_framework: Optional[str] = None) -> List[Dict[str, Any]]:
        projects = self.evidence["projects"]
        project_buckets: Dict[int, List[Dict[str, Any]]] = {idx: [] for idx in range(len(projects))}

        for idx, p in enumerate(projects):
            title = p["title"]
            techs = ", ".join(p["technologies"]) or "specified frameworks"

            # B1: Architecture & Technology Selection
            q1_text = f"In your project '{title}', what motivated your architectural design and technology choices ({techs})?"
            fw1 = preferred_framework or "PEEL"
            notes1 = ground_guidance_in_evidence(fw1, "project", p)
            grounded_arch = build_grounded_project_answers(p, "arch")
            if preferred_framework:
                grounded_arch["recommended_framework"] = preferred_framework

            project_buckets[idx].append({
                "question_id": self._make_id(f"qb_arch_{idx}", q1_text),
                "question_text": q1_text,
                "category": "B",
                "category_name": CATEGORY_METADATA["B"]["name"],
                "category_badge": CATEGORY_METADATA["B"]["badge"],
                "difficulty": "Medium",
                "source_type": "resume_project",
                "source_reference": f"Project: {title}",
                "recommended_answer_framework": grounded_arch["recommended_framework"],
                "recommended_framework": grounded_arch["recommended_framework"],
                "short_answer": grounded_arch["short_answer"],
                "simpler_answer": grounded_arch.get("simpler_answer", grounded_arch["short_answer"]),
                "detailed_answer": grounded_arch["detailed_answer"],
                "curated_answer": grounded_arch["detailed_answer"],
                "why_this_works": grounded_arch.get("why_this_works", ""),
                "step_by_step_explanation": grounded_arch["step_by_step_explanation"],
                "follow_up_questions": grounded_arch.get("follow_up_questions", []),
                "common_mistakes": [
                    "Focusing only on buzzwords without articulating why you chose one library over another.",
                    "Claiming you built complex systems from scratch when standard libraries were used.",
                    "Failing to explain how components passed data to each other."
                ],
                "suggested_improvements": grounded_arch.get("suggested_improvements", ""),
                "verified_evidence": grounded_arch.get("verified_evidence", [f"Extracted Project: {title}"]),
                "examples": grounded_arch["examples"],
                "code_snippet": None,
                "important_concepts": grounded_arch["important_concepts"],
                "interview_tips": grounded_arch["interview_tips"],
                "missing_personal_details": grounded_arch["missing_personal_details"],
                "evidence_sources": [f"Extracted Project: {title}", f"Technologies: {techs}"],
                "answer_guidance": f"Explain why you selected {techs} over alternatives. Discuss modularity, performance, and maintenance requirements.",
                "expected_key_points": [
                    f"Engineering rationale for adopting {techs}",
                    "Trade-offs evaluated against alternative libraries or architectures",
                    "System component structure and data flow"
                ],
                "framework_template": format_answer_template(grounded_arch["recommended_framework"], notes1)
            })

            # B2: Technical Obstacle & Debugging
            q2_text = f"What was the most challenging technical roadblock or bug you encountered while developing '{title}', and how did you resolve it?"
            fw2 = preferred_framework or "CAR"
            notes2 = ground_guidance_in_evidence(fw2, "project", p)
            grounded_roadblock = build_grounded_project_answers(p, "roadblock")
            if preferred_framework:
                grounded_roadblock["recommended_framework"] = preferred_framework

            project_buckets[idx].append({
                "question_id": self._make_id(f"qb_roadblock_{idx}", q2_text),
                "question_text": q2_text,
                "category": "B",
                "category_name": CATEGORY_METADATA["B"]["name"],
                "category_badge": CATEGORY_METADATA["B"]["badge"],
                "difficulty": "Hard",
                "source_type": "resume_project",
                "source_reference": f"Project: {title}",
                "recommended_answer_framework": grounded_roadblock["recommended_framework"],
                "recommended_framework": grounded_roadblock["recommended_framework"],
                "short_answer": grounded_roadblock["short_answer"],
                "simpler_answer": grounded_roadblock.get("simpler_answer", grounded_roadblock["short_answer"]),
                "detailed_answer": grounded_roadblock["detailed_answer"],
                "curated_answer": grounded_roadblock["detailed_answer"],
                "why_this_works": grounded_roadblock.get("why_this_works", ""),
                "step_by_step_explanation": grounded_roadblock["step_by_step_explanation"],
                "follow_up_questions": grounded_roadblock.get("follow_up_questions", []),
                "common_mistakes": [
                    "Blaming teammates, external library maintainers, or poor documentation for the roadblock.",
                    "Describing a trivial syntax error as your greatest technical challenge.",
                    "Failing to explain the root cause and how you verified the fix."
                ],
                "suggested_improvements": grounded_roadblock.get("suggested_improvements", ""),
                "verified_evidence": grounded_roadblock.get("verified_evidence", [f"Extracted Project: {title}"]),
                "examples": grounded_roadblock["examples"],
                "code_snippet": None,
                "important_concepts": grounded_roadblock["important_concepts"],
                "interview_tips": grounded_roadblock["interview_tips"],
                "missing_personal_details": grounded_roadblock["missing_personal_details"],
                "evidence_sources": [f"Extracted Project: {title}"],
                "answer_guidance": "Focus on a concrete technical obstacle. Walk through your systematic diagnostic method.",
                "expected_key_points": [
                    "Clear description of technical challenge or symptom",
                    "Root-cause diagnostic methodology (logs, profiling, unit tests)",
                    "Implementation of permanent solution",
                    "Measurable performance or stability verification"
                ],
                "framework_template": format_answer_template(grounded_roadblock["recommended_framework"], notes2)
            })

            # B3: Testing, Verification & Metrics
            q3_text = f"How did you test and validate the reliability, performance, or accuracy of '{title}'?"
            fw3 = preferred_framework or "PAR"
            notes3 = ground_guidance_in_evidence(fw3, "project", p)
            grounded_eval = build_grounded_project_answers(p, "eval")
            if preferred_framework:
                grounded_eval["recommended_framework"] = preferred_framework

            project_buckets[idx].append({
                "question_id": self._make_id(f"qb_eval_{idx}", q3_text),
                "question_text": q3_text,
                "category": "B",
                "category_name": CATEGORY_METADATA["B"]["name"],
                "category_badge": CATEGORY_METADATA["B"]["badge"],
                "difficulty": "Medium",
                "source_type": "resume_project",
                "source_reference": f"Project: {title}",
                "recommended_answer_framework": grounded_eval["recommended_framework"],
                "recommended_framework": grounded_eval["recommended_framework"],
                "short_answer": grounded_eval["short_answer"],
                "simpler_answer": grounded_eval.get("simpler_answer", grounded_eval["short_answer"]),
                "detailed_answer": grounded_eval["detailed_answer"],
                "curated_answer": grounded_eval["detailed_answer"],
                "why_this_works": grounded_eval.get("why_this_works", ""),
                "step_by_step_explanation": grounded_eval["step_by_step_explanation"],
                "follow_up_questions": grounded_eval.get("follow_up_questions", []),
                "common_mistakes": [
                    "Saying 'I tested it manually by running it a few times and it worked'.",
                    "Ignoring edge cases, malformed payloads, or empty inputs.",
                    "Conflating code coverage with true functional verification."
                ],
                "suggested_improvements": grounded_eval.get("suggested_improvements", ""),
                "verified_evidence": grounded_eval.get("verified_evidence", [f"Extracted Project: {title}"]),
                "examples": grounded_eval["examples"],
                "code_snippet": None,
                "important_concepts": grounded_eval["important_concepts"],
                "interview_tips": grounded_eval["interview_tips"],
                "missing_personal_details": grounded_eval["missing_personal_details"],
                "evidence_sources": [f"Extracted Project: {title}"],
                "answer_guidance": "Explain your validation strategy: automated unit tests, cross-validation splits, load testing, or manual edge-case testing.",
                "expected_key_points": [
                    "Testing framework and methodology utilized",
                    "Handling of edge cases and input validation",
                    "Quantitative evaluation metrics or functional verification"
                ],
                "framework_template": format_answer_template(grounded_eval["recommended_framework"], notes3)
            })

            # B4: Scalability & Future Improvements
            q4_text = f"If you had another development sprint to scale '{title}' for enterprise production, what architectural improvements would you prioritize?"
            fw4 = preferred_framework or "WHAT-WHY-HOW"
            notes4 = ground_guidance_in_evidence(fw4, "project", p)
            grounded_scale = build_grounded_project_answers(p, "scale")
            if preferred_framework:
                grounded_scale["recommended_framework"] = preferred_framework

            project_buckets[idx].append({
                "question_id": self._make_id(f"qb_scale_{idx}", q4_text),
                "question_text": q4_text,
                "category": "B",
                "category_name": CATEGORY_METADATA["B"]["name"],
                "category_badge": CATEGORY_METADATA["B"]["badge"],
                "difficulty": "Hard",
                "source_type": "resume_project",
                "source_reference": f"Project: {title}",
                "recommended_answer_framework": grounded_scale["recommended_framework"],
                "recommended_framework": grounded_scale["recommended_framework"],
                "short_answer": grounded_scale["short_answer"],
                "simpler_answer": grounded_scale.get("simpler_answer", grounded_scale["short_answer"]),
                "detailed_answer": grounded_scale["detailed_answer"],
                "curated_answer": grounded_scale["detailed_answer"],
                "why_this_works": grounded_scale.get("why_this_works", ""),
                "step_by_step_explanation": grounded_scale["step_by_step_explanation"],
                "follow_up_questions": grounded_scale.get("follow_up_questions", []),
                "common_mistakes": [
                    "Claiming your current codebase is already perfect and needs no improvements.",
                    "Suggesting complex distributed architecture without explaining what bottleneck it solves.",
                    "Ignoring database query indexing, caching, or asynchronous task processing."
                ],
                "suggested_improvements": grounded_scale.get("suggested_improvements", ""),
                "verified_evidence": grounded_scale.get("verified_evidence", [f"Extracted Project: {title}"]),
                "examples": grounded_scale["examples"],
                "code_snippet": None,
                "important_concepts": grounded_scale["important_concepts"],
                "interview_tips": grounded_scale["interview_tips"],
                "missing_personal_details": grounded_scale["missing_personal_details"],
                "evidence_sources": [f"Extracted Project: {title}"],
                "answer_guidance": "Critically analyze current constraints. Propose concrete engineering upgrades like Redis caching, async queues, or containerization.",
                "expected_key_points": [
                    "Honest appraisal of current limitations",
                    "Concrete architectural upgrades (caching, async tasks, DB indexing)",
                    "Anticipated scalability or latency gains"
                ],
                "framework_template": format_answer_template(grounded_scale["recommended_framework"], notes4)
            })

        # B5: Evidence-Based Probing Questions on Metrics
        for idx, p in enumerate(projects):
            title = p["title"]
            desc = p.get("description", "")
            metrics = re.findall(r"\b(\d{1,3}(?:\.\d+)?%|\d+\s*(?:ms|seconds|minutes|records|queries|requests|users|epochs))\b", desc)
            if metrics:
                metric_val = metrics[0]
                q_probe = f"In '{title}', you noted achieving {metric_val}. What specific baseline were you evaluating against, and how did you verify against overfitting or class imbalance?"
                fw_probe = preferred_framework or "STAR"
                detailed_probe = (
                    f"When evaluating '{title}', my primary goal was to obtain statistically robust and reproducible metrics. "
                    f"To measure {metric_val}, I established an isolated holdout test split that was never exposed to feature preprocessing or training. "
                    f"Rather than relying purely on top-line accuracy, which can be misleading under skewed class distributions, "
                    f"I monitored Precision, Recall, and Macro F1 score across every target category. "
                    f"I compared our model against a heuristic baseline (majority-class predictor and stratified dummy classifier) "
                    f"to verify that our architecture learned genuine predictive signal rather than superficial training patterns."
                )
                project_buckets[idx].append({
                    "question_id": self._make_id(f"qb_probe_{idx}", q_probe),
                    "question_text": q_probe,
                    "category": "B",
                    "category_name": CATEGORY_METADATA["B"]["name"],
                    "category_badge": CATEGORY_METADATA["B"]["badge"],
                    "difficulty": "Hard",
                    "source_type": "resume_project",
                    "source_reference": f"Project: {title}",
                    "recommended_answer_framework": fw_probe,
                    "recommended_framework": fw_probe,
                    "short_answer": f"I verified {metric_val} in '{title}' by comparing against baseline models on an isolated holdout split, monitoring precision, recall, and Macro F1.",
                    "simpler_answer": f"I verified {metric_val} in '{title}' by comparing against baseline models on an isolated holdout split, monitoring precision, recall, and Macro F1.",
                    "detailed_answer": detailed_probe,
                    "curated_answer": detailed_probe,
                    "why_this_works": "Interviewers probe numerical metrics to ensure you didn't overfit, test on training data, or misinterpret accuracy on imbalanced classes.",
                    "step_by_step_explanation": [
                        {"step": "Step 1: Frame the Evaluation Partition", "detail": "State that data was split into train/test before any preprocessing to prevent leakage."},
                        {"step": "Step 2: Identify the Comparative Baseline", "detail": "Specify the baseline model or standard heuristic used as a reference point."},
                        {"step": "Step 3: Articulate Metric Nuance", "detail": "Explain why Precision/Recall/F1 were tracked alongside overall accuracy."}
                    ],
                    "follow_up_questions": [
                        {"question": "How did you prevent cross-validation leakage?", "answer": "By fitting all scalers and vectorizers strictly inside fold training loops."},
                        {"question": "What would you do if validation loss started increasing while train loss decreased?", "answer": "Apply regularization (L1/L2, dropout), reduce model capacity, or collect more data."}
                    ],
                    "common_mistakes": [
                        "Reporting high accuracy without checking class distribution.",
                        "Evaluating on training data.",
                        "Not having a baseline model for comparison."
                    ],
                    "suggested_improvements": "Implement Stratified Group K-Fold to evaluate generalization across unseen entities.",
                    "verified_evidence": [f"Metric mention in {title}: {metric_val}"],
                    "examples": {"STAR": {"Situation": f"Evaluating '{title}'", "Task": f"Establish defensible benchmark for {metric_val}", "Action": "Implemented holdout splits and metric tracking", "Result": "Statistically validated performance"}},
                    "code_snippet": None,
                    "important_concepts": ["Baseline Comparison", "Class Imbalance", "Overfitting vs Generalization"],
                    "interview_tips": ["Always state the baseline model", "Explain precision vs recall trade-offs"],
                    "missing_personal_details": [f"Specific validation partition size and baseline accuracy in '{title}'"],
                    "evidence_sources": [f"Extracted Project: {title}"],
                    "answer_guidance": "Anchor your answer in holdout splits, baseline comparison, and metric choice.",
                    "expected_key_points": ["Holdout validation split", "Baseline comparison", "Precision/Recall/F1 metrics"],
                    "framework_template": format_answer_template(fw_probe)
                })

        # Interleave questions across projects to ensure balanced question diversity
        interleaved_questions = []
        max_q = max((len(q_list) for q_list in project_buckets.values()), default=0)
        for q_idx in range(max_q):
            for p_idx in range(len(projects)):
                if q_idx < len(project_buckets[p_idx]):
                    interleaved_questions.append(project_buckets[p_idx][q_idx])

        return interleaved_questions

    # -------------------------------------------------------------------------
    # Category C: Internship & Work Experience Questions
    # -------------------------------------------------------------------------
    def generate_category_c(self, preferred_framework: Optional[str] = None) -> List[Dict[str, Any]]:
        questions = []
        internships = self.evidence["internships"]

        for idx, it in enumerate(internships):
            org = it["organization"]
            dates = it["dates"]
            techs = ", ".join(it["technologies"]) or "practical engineering tools"
            resps = "; ".join(it["responsibilities"]) or "software development duties"

            # C1: Core Internship Contribution
            q1_text = f"During your internship at {org} ({dates}), what were your primary technical responsibilities and contributions?"
            fw1 = preferred_framework or "STAR"
            notes1 = ground_guidance_in_evidence(fw1, "internship", it)
            grounded_resp = build_grounded_internship_answers(it, "resp")
            if preferred_framework:
                grounded_resp["recommended_framework"] = preferred_framework

            questions.append({
                "question_id": self._make_id(f"qc_resp_{idx}", q1_text),
                "question_text": q1_text,
                "category": "C",
                "category_name": CATEGORY_METADATA["C"]["name"],
                "category_badge": CATEGORY_METADATA["C"]["badge"],
                "difficulty": "Medium",
                "source_type": "resume_internship",
                "source_reference": f"Internship: {org}",
                "recommended_answer_framework": grounded_resp["recommended_framework"],
                "recommended_framework": grounded_resp["recommended_framework"],
                "short_answer": grounded_resp["short_answer"],
                "simpler_answer": grounded_resp.get("simpler_answer", grounded_resp["short_answer"]),
                "detailed_answer": grounded_resp["detailed_answer"],
                "curated_answer": grounded_resp["detailed_answer"],
                "why_this_works": grounded_resp.get("why_this_works", ""),
                "step_by_step_explanation": grounded_resp["step_by_step_explanation"],
                "follow_up_questions": grounded_resp.get("follow_up_questions", []),
                "common_mistakes": [
                    "Using 'we' exclusively without explaining what you personally engineered.",
                    "Exaggerating your scope beyond an intern level, which triggers skeptical follow-up questions.",
                    "Focusing only on administrative tasks rather than engineering contributions."
                ],
                "suggested_improvements": grounded_resp.get("suggested_improvements", ""),
                "verified_evidence": grounded_resp.get("verified_evidence", [f"Internship Record: {org}"]),
                "examples": grounded_resp["examples"],
                "code_snippet": None,
                "important_concepts": grounded_resp["important_concepts"],
                "interview_tips": grounded_resp["interview_tips"],
                "missing_personal_details": grounded_resp["missing_personal_details"],
                "evidence_sources": [f"Internship Record: {org} ({dates})", f"Technologies: {techs}"],
                "answer_guidance": f"Describe your specific deliverables at {org}. Focus on {resps} and how you applied {techs}.",
                "expected_key_points": [
                    f"Team context and objective at {org}",
                    f"Hands-on contributions using {techs}",
                    "Verified deliverables and team impact"
                ],
                "framework_template": format_answer_template(grounded_resp["recommended_framework"], notes1)
            })

            # C2: Engineering Learning & Industry Standards
            q2_text = f"What was the most valuable technical or professional lesson you learned during your time at {org}?"
            fw2 = preferred_framework or "STAR+L"
            notes2 = ground_guidance_in_evidence(fw2, "internship", it)
            grounded_learn = build_grounded_internship_answers(it, "learn")
            if preferred_framework:
                grounded_learn["recommended_framework"] = preferred_framework

            questions.append({
                "question_id": self._make_id(f"qc_learn_{idx}", q2_text),
                "question_text": q2_text,
                "category": "C",
                "category_name": CATEGORY_METADATA["C"]["name"],
                "category_badge": CATEGORY_METADATA["C"]["badge"],
                "difficulty": "Easy",
                "source_type": "resume_internship",
                "source_reference": f"Internship: {org}",
                "recommended_answer_framework": grounded_learn["recommended_framework"],
                "recommended_framework": grounded_learn["recommended_framework"],
                "short_answer": grounded_learn["short_answer"],
                "simpler_answer": grounded_learn.get("simpler_answer", grounded_learn["short_answer"]),
                "detailed_answer": grounded_learn["detailed_answer"],
                "curated_answer": grounded_learn["detailed_answer"],
                "why_this_works": grounded_learn.get("why_this_works", ""),
                "step_by_step_explanation": grounded_learn["step_by_step_explanation"],
                "follow_up_questions": grounded_learn.get("follow_up_questions", []),
                "common_mistakes": [
                    "Saying you didn't learn much because you already knew the technologies.",
                    "Complaining about legacy code or organizational politics.",
                    "Focusing only on non-technical perks rather than engineering growth and code standards."
                ],
                "suggested_improvements": grounded_learn.get("suggested_improvements", ""),
                "verified_evidence": grounded_learn.get("verified_evidence", [f"Internship Record: {org}"]),
                "examples": grounded_learn["examples"],
                "code_snippet": None,
                "important_concepts": grounded_learn["important_concepts"],
                "interview_tips": grounded_learn["interview_tips"],
                "missing_personal_details": grounded_learn["missing_personal_details"],
                "evidence_sources": [f"Internship Record: {org}"],
                "answer_guidance": "Reflect on how working in a professional team differed from individual coursework (code review, git branching, automated CI/CD).",
                "expected_key_points": [
                    "Exposure to industry development workflows",
                    "Collaboration with senior engineers and stakeholders",
                    "Personal technical growth"
                ],
                "framework_template": format_answer_template(grounded_learn["recommended_framework"], notes2)
            })

            # C3: Technical Problem Solving at Organization
            q3_text = f"Can you walk me through a specific engineering problem you solved while working at {org} using {techs}?"
            fw3 = preferred_framework or "CAR"
            notes3 = ground_guidance_in_evidence(fw3, "internship", it)
            grounded_solve = build_grounded_internship_answers(it, "solve")
            if preferred_framework:
                grounded_solve["recommended_framework"] = preferred_framework

            questions.append({
                "question_id": self._make_id(f"qc_solve_{idx}", q3_text),
                "question_text": q3_text,
                "category": "C",
                "category_name": CATEGORY_METADATA["C"]["name"],
                "category_badge": CATEGORY_METADATA["C"]["badge"],
                "difficulty": "Hard",
                "source_type": "resume_internship",
                "source_reference": f"Internship: {org}",
                "recommended_answer_framework": grounded_solve["recommended_framework"],
                "recommended_framework": grounded_solve["recommended_framework"],
                "short_answer": grounded_solve["short_answer"],
                "simpler_answer": grounded_solve.get("simpler_answer", grounded_solve["short_answer"]),
                "detailed_answer": grounded_solve["detailed_answer"],
                "curated_answer": grounded_solve["detailed_answer"],
                "why_this_works": grounded_solve.get("why_this_works", ""),
                "step_by_step_explanation": grounded_solve["step_by_step_explanation"],
                "follow_up_questions": grounded_solve.get("follow_up_questions", []),
                "common_mistakes": [
                    "Failing to articulate the initial technical problem clearly.",
                    "Skipping the diagnostic and testing phases to jump straight to the conclusion.",
                    "Not giving credit to teammates who reviewed your code or provided guidance."
                ],
                "suggested_improvements": grounded_solve.get("suggested_improvements", ""),
                "verified_evidence": grounded_solve.get("verified_evidence", [f"Internship Record: {org}"]),
                "examples": grounded_solve["examples"],
                "code_snippet": None,
                "important_concepts": grounded_solve["important_concepts"],
                "interview_tips": grounded_solve["interview_tips"],
                "missing_personal_details": grounded_solve["missing_personal_details"],
                "evidence_sources": [f"Internship Record: {org}", f"Technologies: {techs}"],
                "answer_guidance": "Frame a specific task: define the initial challenge, describe your implementation using the tools, and report the concrete outcome delivered to the team.",
                "expected_key_points": [
                    "Concrete problem statement within organization",
                    "Independent research and technical implementation",
                    "Resolution confirmed by team"
                ],
                "framework_template": format_answer_template(grounded_solve["recommended_framework"], notes3)
            })

        return questions

    # -------------------------------------------------------------------------
    # Category D: Target Job Description & Skill Gap Alignment
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Category D: Target Job Description & Skill Gap Alignment
    # -------------------------------------------------------------------------
    def generate_category_d(self, preferred_framework: Optional[str] = None) -> List[Dict[str, Any]]:
        questions = []
        raw_job_title = (self.evidence.get("job_title") or "").strip()
        if not raw_job_title or raw_job_title.lower() in ["target role not specified", "unspecified", "not specified", "none"]:
            job_title = "software engineering"
            job_phrase = "software engineering roles"
        else:
            job_title = raw_job_title
            job_phrase = f"the {raw_job_title} role"

        req_skills = self.evidence["required_skills"]
        missing_skills = self.evidence["missing_skills"]
        resume_skills = self.evidence["skills"]
        projects = self.evidence.get("projects", [])
        if projects:
            p_ref = projects[0]
            p_title = p_ref.get("title", "my primary project")
            p_techs = ", ".join(p_ref.get("technologies", [])[:3]) or "relevant frameworks"
            project_alignment_sentence = f"In my project '{p_title}', I applied these principles directly while architecting solutions using {p_techs}."
        else:
            project_alignment_sentence = "In my practical engineering coursework and lab assignments, I applied these principles directly through iterative development and automated testing."

        # D1: Target Role Alignment
        if req_skills:
            req_top_str = ", ".join(req_skills[:4])
            q1_text = f"This {job_title} role requires strong expertise in {req_top_str}. How does your background prepare you to excel against these requirements?"
            fw1 = preferred_framework or "PREP"
            short_d1 = f"My hands-on experience developing projects with {', '.join(resume_skills[:3])} directly aligns with your requirements for {req_top_str}, enabling me to contribute to your engineering goals immediately."
            simpler_d1 = f"My hands-on experience developing projects with {', '.join(resume_skills[:3])} gives me a strong technical foundation to hit the ground running with {req_top_str} in this {job_title} role."
            detailed_d1 = (
                f"My engineering background directly supports the requirements of {job_phrase}. "
                f"Your team prioritizes {req_top_str}, and I have developed practical systems exercising related tools such as {', '.join(resume_skills[:4])}. "
                f"I focus on designing clean API contracts, writing automated unit tests, and understanding system bottlenecks. "
                f"{project_alignment_sentence} "
                f"This background gives me confidence that I will rapidly become productive within your technical stack."
            )
            why_this_works_d1 = (
                f"The hiring manager wants to ensure you understand what {job_phrase} entails and that you can be productive quickly. "
                f"This answer succeeds because it demonstrates genuine interest in {job_phrase} and maps your proven skills directly to their technical priorities."
            )
            steps_d1 = [
                {
                    "step": "Step 1: Direct Technical Alignment (Point)",
                    "complete_explanation": f"Acknowledge the core requirement for {req_top_str} in the {job_title} position. Clearly articulating the target stack upfront confirms that you have thoroughly analyzed the job description and understand the team's engineering priorities.",
                    "reasoning": "Proving that you understand the target role's core technical priorities establishes immediate relevance for the interviewer.",
                    "concrete_example": f"Highlighting requirements for {req_top_str} in building scalable {job_title} systems.",
                    "connection_to_question": "Directly frames your alignment with the employer's specified stack.",
                    "detail": f"Acknowledge the core requirement for {req_top_str} in the {job_title} position. Clearly articulating the target stack upfront confirms that you have thoroughly analyzed the job description and understand the team's engineering priorities."
                },
                {
                    "step": "Step 2: Map Verified Foundations to Target Requirements (Reason)",
                    "complete_explanation": f"Connect your verified experience with {', '.join(resume_skills[:3])} to the job requirements. Explain how your understanding of architecture, data flow, and error handling translates directly across technologies.",
                    "reasoning": "Experienced engineers recognize that software engineering patterns—modularity, testing, API contracts—remain consistent across languages and frameworks.",
                    "concrete_example": f"Transferring RESTful API design and database query optimization from {resume_skills[0] if resume_skills else 'Python'} to the target stack.",
                    "connection_to_question": "Demonstrates technical transferability and analytical capability.",
                    "detail": f"Connect your verified experience with {', '.join(resume_skills[:3])} to the job requirements. Explain how your understanding of architecture, data flow, and error handling translates directly across technologies."
                },
                {
                    "step": "Step 3: Cite Concrete Deliverables as Empirical Proof (Example)",
                    "complete_explanation": "Cite a specific project where you delivered functional software under production-style requirements, referencing automated testing, clean modularity, and quantifiable outcomes.",
                    "reasoning": "Concrete deliverables eliminate skepticism and verify that you can execute beyond theoretical understanding.",
                    "concrete_example": "Detailing a multi-tier service where modular architecture enabled isolated testing and high availability.",
                    "connection_to_question": "Supplies concrete empirical evidence supporting your alignment.",
                    "detail": "Cite a specific project where you delivered functional software under production-style requirements, referencing automated testing, clean modularity, and quantifiable outcomes."
                },
                {
                    "step": "Step 4: Emphasize Professional Engineering Disciplines",
                    "complete_explanation": "Discuss your commitment to industry best practices: automated continuous integration testing, atomic Git commits, constructive peer code reviews, and structured documentation.",
                    "reasoning": "Hiring managers prioritize candidates who will raise team engineering standards rather than creating technical debt.",
                    "concrete_example": "Setting up GitHub Actions to execute automated pytest runs with coverage enforcement on pull requests.",
                    "connection_to_question": "Proves cultural and operational alignment with mature engineering teams.",
                    "detail": "Discuss your commitment to industry best practices: automated continuous integration testing, atomic Git commits, constructive peer code reviews, and structured documentation."
                },
                {
                    "step": "Step 5: Address Architectural Trade-Offs & Scaling Considerations",
                    "complete_explanation": f"Discuss how you evaluate system trade-offs relevant to {job_title}—such as latency vs consistency, or synchronous processing vs background worker queues—showing you think like an architect.",
                    "reasoning": "Architectural maturity distinguishes mid-level and senior engineers from junior developers who only consider happy paths.",
                    "concrete_example": "Decoupling compute-heavy processing from synchronous HTTP threads using Celery task queues.",
                    "connection_to_question": "Illustrates systems design rigor directly applicable to the target role.",
                    "detail": f"Discuss how you evaluate system trade-offs relevant to {job_title}—such as latency vs consistency, or synchronous processing vs background worker queues—showing you think like an architect."
                },
                {
                    "step": "Step 6: Confirm Rapid Onboarding & Business Delivery (Point Conclusion)",
                    "complete_explanation": f"Conclude by articulating your 30-day onboarding strategy: setting up environments, understanding codebase architecture, and delivering verified bug fixes to accelerate team velocity.",
                    "reasoning": "A structured 30-day plan gives the interviewer total confidence that you will become productive quickly.",
                    "concrete_example": f"Delivering small, well-tested contributions during week two and autonomous feature tickets by week four.",
                    "connection_to_question": "Concludes with business alignment, enthusiasm, and candidate readiness.",
                    "detail": f"Conclude by articulating your 30-day onboarding strategy: setting up environments, understanding codebase architecture, and delivering verified bug fixes to accelerate team velocity."
                }
            ]
            follow_ups_d1 = [
                {
                    "question": f"What would be your primary technical goal during your first 30 days in this {job_title} role?",
                    "reference_answer": (
                        "During my first 30 days, my primary technical objective is establishing deep familiarity with the team's codebase architecture and development workflows. "
                        "During week one, I set up a reproducible local development environment, verify our test suite passes locally, and study deployment architecture documentation. "
                        "During week two, I review recent pull requests to adopt team conventions and take on small, bounded bug fixes to learn the release pipeline. "
                        "By week three and four, I aim to deliver a fully tested, verified feature contribution, demonstrating autonomous velocity and positive team impact."
                    ),
                    "technical_justification": "A structured 30-day plan prioritizing environment setup, test verification, and small PRs minimizes onboarding friction.",
                    "practical_example": "Cloning repository, running Docker Compose, executing test suite, and claiming a 'good first issue' ticket in Jira.",
                    "interview_takeaway": "Present a clear 30-day ramp-up timeline: setup and testing (week 1), bug fixes (week 2), feature delivery (weeks 3-4)."
                },
                {
                    "question": "How do you handle ambiguous requirements when assigned a new feature ticket?",
                    "reference_answer": (
                        "When handed an ambiguous specification, I avoid making unverified assumptions, because assumptions often lead to costly architectural rework. "
                        "Instead, I draft an implementation summary outlining my understanding of the requirement, edge cases, and proposed API contracts. "
                        "I schedule a brief 10-minute alignment sync with the product manager or tech lead to validate the acceptance criteria before writing code. "
                        "Once aligned, I write automated integration test cases encoding those criteria, ensuring the implementation satisfies business expectations precisely."
                    ),
                    "technical_justification": "Validating acceptance criteria and API schemas upfront prevents architectural misalignment and rework during code reviews.",
                    "practical_example": "Writing a 3-bullet Slack RFC: 'For candidate matching, if a resume lacks text, should we return 422 or empty array with OCR warning?'",
                    "interview_takeaway": "Demonstrate proactive communication: document assumptions, confirm acceptance criteria with leads, and write tests first."
                },
                {
                    "question": f"How would you approach code review for a teammate working in {req_skills[0]}?",
                    "reference_answer": (
                        f"When reviewing a teammate's pull request in {req_skills[0]}, I focus on code correctness, security, readability, and test coverage rather than subjective styling. "
                        f"I verify that automated tests pass and that boundary conditions—like empty inputs, null pointers, and connection timeouts—are defensively handled. "
                        f"I check for performance pitfalls like unindexed database queries or race conditions in concurrent execution blocks. "
                        f"When offering feedback, I frame comments constructively with explanations of the underlying trade-offs, and I celebrate clever, elegant solutions to foster a positive team culture."
                    ),
                    "technical_justification": "Constructive code reviews focus on boundary correctness, performance, and test coverage rather than stylistic nitpicks.",
                    "practical_example": "Commenting: 'Consider using `.get(key, default)` here to avoid raising a KeyError if the payload omits this field under edge cases.'",
                    "interview_takeaway": "Emphasize respectful, high-value code reviews: boundary validation, security, test coverage, and clear trade-off explanations."
                }
            ]
            common_mistakes_d1 = [
                "Giving a generic answer that could apply to any software role at any company.",
                "Failing to mention the specific technologies requested in the job description.",
                "Assuming you already know everything about the company's internal architecture."
            ]
            questions.append({
                "question_id": self._make_id("qd_align", q1_text),
                "question_text": q1_text,
                "category": "D",
                "category_name": CATEGORY_METADATA["D"]["name"],
                "category_badge": CATEGORY_METADATA["D"]["badge"],
                "difficulty": "Medium",
                "source_type": "job_description",
                "source_reference": f"Mandatory Requirements: {req_top_str}",
                "recommended_answer_framework": fw1,
                "recommended_framework": fw1,
                "short_answer": short_d1,
                "simpler_answer": simpler_d1,
                "detailed_answer": detailed_d1,
                "curated_answer": detailed_d1,
                "why_this_works": why_this_works_d1,
                "step_by_step_explanation": steps_d1,
                "follow_up_questions": follow_ups_d1,
                "common_mistakes": common_mistakes_d1,
                "examples": f"Leveraged related technical skills to deliver robust software aligned with {job_title}.",
                "code_snippet": None,
                "important_concepts": req_skills[:4],
                "interview_tips": [
                    f"Directly acknowledge the {job_title} requirements and cite matching experience.",
                    "Show enthusiasm for learning internal architecture while highlighting day-one readiness."
                ],
                "missing_personal_details": [f"Specific production deliverables and metrics in '{p_title}'"] if projects else ["Specific team deployment metrics"],
                "suggested_improvements": "Suggested Improvement (Hypothetical Proposal): Authoring an architectural decision record (ADR) to document how newly integrated features map to the target stack.",
                "verified_evidence": [f"Target Role: {job_title}", f"Required Skills: {req_top_str}"],
                "evidence_sources": ["Job Description Mandatory Requirements", "Candidate Extracted Skills"],
                "expected_key_points": [
                    f"Understanding of {job_title} responsibilities",
                    f"Mapping verified skills to {req_top_str}",
                    "Rapid onboarding and team contribution plan"
                ],
                "framework_template": format_answer_template(fw1)
            })

        # D2: Missing / Skill Gap Questions
        if missing_skills:
            gap_skill = missing_skills[0]
            q2_text = f"This position requires experience with {gap_skill}, which is not explicitly evidenced on your resume. How will you ramp up and deliver value in this area?"
            fw2 = preferred_framework or "PREP"
            short_d2 = f"While my resume does not explicitly feature {gap_skill}, my strong foundation in {', '.join(resume_skills[:2])} and proven track record of rapid learning enable me to ramp up to production speed quickly."
            simpler_d2 = f"I am already actively learning {gap_skill} by reviewing documentation and building prototypes. My strong background in related tools like {', '.join(resume_skills[:2])} will allow me to become productive in your stack rapidly."
            detailed_d2 = (
                f"While my resume does not explicitly evidence {gap_skill}, I view this as an active growth opportunity rather than a barrier. "
                f"Because I already have verified experience with related technologies like {', '.join(resume_skills[:3])}, "
                f"I understand the underlying architectural patterns—such as modularity, automated testing, and error handling—that {gap_skill} builds upon. "
                f"I have already begun ramping up by reviewing official documentation, studying standard design patterns, and building focused proof-of-concept prototypes. "
                f"My track record of quickly adopting complex technical frameworks gives me confidence that I will achieve production velocity in {gap_skill} within my first few weeks."
            )
            why_this_works_d2 = (
                "Interviewers ask about missing skills to test your intellectual honesty, humility, and proactive learning habits. "
                "This answer succeeds because it honestly acknowledges the gap without becoming defensive, bridges the gap using verified related skills, and outlines a concrete learning plan."
            )
            steps_d2 = [
                {
                    "step": f"Step 1: Honest & Confident Gap Acknowledgment (Point)",
                    "complete_explanation": f"Acknowledge transparently that {gap_skill} is not currently evidenced on your resume. Intellectual honesty earns immediate respect from senior technical interviewers and eliminates defensive posturing.",
                    "reasoning": "Never attempt to bluff or exaggerate familiarity; interviewers easily expose superficial knowledge with deep follow-ups.",
                    "concrete_example": f"Stating: 'While my resume does not yet showcase production implementations of {gap_skill}, I am actively bridging that gap.'",
                    "connection_to_question": "Directly confronts the core premise of the question with integrity.",
                    "detail": f"Acknowledge transparently that {gap_skill} is not currently evidenced on your resume. Intellectual honesty earns immediate respect from senior technical interviewers and eliminates defensive posturing."
                },
                {
                    "step": "Step 2: Bridge via Verified Related Foundations (Reason)",
                    "complete_explanation": f"Explain how your verified experience with {', '.join(resume_skills[:3])} provides the architectural foundation for mastering {gap_skill}. Core engineering concepts—data serialization, interface design, testing—transfer seamlessly.",
                    "reasoning": "Showing that you possess related prerequisites proves that the learning curve will be brief and manageable.",
                    "concrete_example": f"Leveraging experience with {resume_skills[0] if resume_skills else 'software design'} to grasp the operational idioms of {gap_skill}.",
                    "connection_to_question": "Demonstrates technical transferability and conceptual competence.",
                    "detail": f"Explain how your verified experience with {', '.join(resume_skills[:3])} provides the architectural foundation for mastering {gap_skill}. Core engineering concepts—data serialization, interface design, testing—transfer seamlessly."
                },
                {
                    "step": "Step 3: Detail Proactive Learning Actions Underway (Example)",
                    "complete_explanation": f"Detail specific learning actions already undertaken: reviewing official {gap_skill} documentation, completing practical tutorials, and building self-contained prototype labs.",
                    "reasoning": "Demonstrating that you started learning before the interview shows genuine initiative and self-motivation.",
                    "concrete_example": f"Building an isolated proof-of-concept module using {gap_skill} and authoring unit tests verifying its behavior.",
                    "connection_to_question": "Provides empirical evidence of active skill acquisition.",
                    "detail": f"Detail specific learning actions already undertaken: reviewing official {gap_skill} documentation, completing practical tutorials, and building self-contained prototype labs."
                },
                {
                    "step": "Step 4: Emphasize Past Rapid Framework Ramp-Up History",
                    "complete_explanation": f"Cite a prior instance where you had to master an unfamiliar library or framework under deadline pressure, successfully delivering a working, tested module.",
                    "reasoning": "A proven history of rapid technical adoption is the strongest predictor of future learning velocity.",
                    "concrete_example": "Learning a new framework or database in two weeks to deliver a critical project milestone.",
                    "connection_to_question": "Reinforces confidence with historical track-record evidence.",
                    "detail": "Cite a prior instance where you had to master an unfamiliar library or framework under deadline pressure, successfully delivering a working, tested module."
                },
                {
                    "step": "Step 5: Leverage Team Code Reviews & Mentorship",
                    "complete_explanation": f"Explain how you will accelerate ramp-up by studying the team's existing production codebase, reading merged pull requests, and soliciting constructive feedback from senior mentors.",
                    "reasoning": "Effective learners leverage team wisdom and existing codebase conventions to avoid rookie mistakes.",
                    "concrete_example": "Inspecting existing production implementations of {gap_skill} in the team's repositories to adopt established design patterns.",
                    "connection_to_question": "Shows collaborative learning maturity.",
                    "detail": f"Explain how you will accelerate ramp-up by studying the team's existing production codebase, reading merged pull requests, and soliciting constructive feedback from senior mentors."
                },
                {
                    "step": "Step 6: Outline a Realistic 30-Day Velocity Target (Point Conclusion)",
                    "complete_explanation": f"Conclude with a concrete timeline: achieving foundational fluency within two weeks and contributing production-ready, peer-reviewed code in {gap_skill} within 30 days.",
                    "reasoning": "A bounded commitment provides hiring managers with a clear, realistic ramp-up expectation.",
                    "concrete_example": f"Delivering autonomous feature contributions using {gap_skill} by sprint two.",
                    "connection_to_question": "Concludes with professional confidence and quantifiable commitment.",
                    "detail": f"Conclude with a concrete timeline: achieving foundational fluency within two weeks and contributing production-ready, peer-reviewed code in {gap_skill} within 30 days."
                }
            ]
            follow_ups_d2 = [
                {
                    "question": f"What is your strategy for evaluating whether you have achieved production readiness in {gap_skill}?",
                    "reference_answer": (
                        f"I define production readiness in {gap_skill} by three objective criteria: implementation ability, debugging fluency, and testing rigor. "
                        f"First, I must be able to write idiomatic, clean code that integrates with our existing stack without relying on copy-pasting from tutorials. "
                        f"Second, when errors arise, I must be able to interpret stack traces and diagnose the root cause independently using debuggers and official docs. "
                        f"Third, I must be able to author automated unit and integration tests covering boundary edge cases. "
                        f"Once my pull requests pass senior engineer code review with minimal architectural revisions, I consider myself fully production-ready."
                    ),
                    "technical_justification": "Production readiness is verified through autonomous debugging, automated testing, and passing peer code review.",
                    "practical_example": "Authoring comprehensive unit tests with 80%+ branch coverage and delivering merged PRs without senior architectural rework.",
                    "interview_takeaway": "Define readiness objectively: independent debugging, thorough automated testing, and passing senior peer review."
                },
                {
                    "question": "Can you describe a specific time when you had to learn an unfamiliar technology under tight deadline pressure?",
                    "reference_answer": (
                        "During a recent project milestone, our team required integrating a technology I had never previously used in production. "
                        "With only two weeks before delivery, I established an intensive study roadmap: I spent the first two days reading official documentation and writing focused micro-benchmarks to understand core API mechanics. "
                        "By day four, I had authored a standalone prototype verifying that our data could flow through the component without latency degradation. "
                        "I then integrated the module into the main service branch, authored automated unit tests for failure edge cases, and requested an early architectural review from a senior teammate. "
                        "We shipped the feature on schedule with zero post-release regressions, proving that structured learning produces reliable code under pressure."
                    ),
                    "technical_justification": "Timeboxed prototyping and early test verification de-risks new technology adoption under tight release schedules.",
                    "practical_example": "Building an isolated prototype script verifying API payloads before integrating the library into the production codebase.",
                    "interview_takeaway": "Emphasize structured learning: read docs, build a minimal proof-of-concept, test edge cases, and ship on time."
                },
                {
                    "question": f"If you encounter a subtle bug in {gap_skill} that is not documented in standard StackOverflow threads, how do you proceed?",
                    "reference_answer": (
                        f"When encountering undocumented bugs in {gap_skill}, I avoid surface-level trial-and-error and dive into first principles. "
                        f"First, I extract the failing operation into a minimal, standalone reproduction script to eliminate noise from other application layers. "
                        f"Second, I inspect structured debug logs and use step-through debuggers to inspect internal variable states right before the failure occurs. "
                        f"Third, I inspect the open-source repository on GitHub, searching recent issues, pull requests, and the source code itself to understand how the library handles that internal code branch. "
                        f"This first-principles approach has consistently allowed me to resolve subtle edge-case bugs that generic web searches could not answer."
                    ),
                    "technical_justification": "Reading library source code and isolating minimal reproductions resolves undocumented edge cases that search engines cannot index.",
                    "practical_example": "Searching GitHub Issues with the exact error string and inspecting the library's internal `try/except` handler in site-packages.",
                    "interview_takeaway": "Showcase deep troubleshooting: minimal isolated reproduction, debugger state inspection, and reading the library's GitHub source code."
                }
            ]
            common_mistakes_d2 = [
                "Pretending you know the skill and bluffing, which gets instantly exposed by senior interviewers.",
                "Apologizing profusely and sounding defeated or underqualified.",
                "Failing to explain how your existing verified skills shorten the ramp-up time."
            ]
            questions.append({
                "question_id": self._make_id("qd_gap", q2_text),
                "question_text": q2_text,
                "category": "D",
                "category_name": CATEGORY_METADATA["D"]["name"],
                "category_badge": CATEGORY_METADATA["D"]["badge"],
                "difficulty": "Hard",
                "source_type": "skill_gap",
                "source_reference": f"Identified Skill Gap: {gap_skill}",
                "recommended_answer_framework": fw2,
                "recommended_framework": fw2,
                "short_answer": short_d2,
                "simpler_answer": simpler_d2,
                "detailed_answer": detailed_d2,
                "curated_answer": detailed_d2,
                "why_this_works": why_this_works_d2,
                "step_by_step_explanation": steps_d2,
                "follow_up_questions": follow_ups_d2,
                "common_mistakes": common_mistakes_d2,
                "examples": f"Demonstrated rapid adoption of complex frameworks to deliver working software.",
                "code_snippet": None,
                "important_concepts": [gap_skill, "Rapid Learning", "Prerequisite Transfer", "Production Readiness"],
                "interview_tips": [
                    "Acknowledge the gap honestly and without defensiveness.",
                    f"Highlight how verified skills like {', '.join(resume_skills[:2])} accelerate your learning of {gap_skill}."
                ],
                "missing_personal_details": ["[Cite specific coursework or prototype completed for this skill]"],
                "suggested_improvements": f"Suggested Improvement (Hypothetical Proposal): Completing a verified portfolio project showcasing {gap_skill} integrated with existing services.",
                "verified_evidence": [f"Target Role: {job_title}", f"Unestablished Skill: {gap_skill}"],
                "evidence_sources": ["Job Description Skill Requirements", "Candidate Resume Gaps"],
                "expected_key_points": [
                    f"Honest acknowledgment of {gap_skill} gap",
                    "Bridge via existing related competencies",
                    "Concrete ramp-up plan and 30-day timeline"
                ],
                "framework_template": format_answer_template(fw2)
            })

        return questions
    def generate_category_e(self, preferred_framework: Optional[str] = None) -> List[Dict[str, Any]]:
        questions = []
        candidate_skills_lower = {s.lower() for s in self.evidence["skills"]}
        req_skills_lower = {s.lower() for s in self.evidence["required_skills"]}
        all_relevant = candidate_skills_lower.union(req_skills_lower)

        for item in TECHNICAL_QUESTION_BANK:
            topic = item["topic"]
            is_matched = any(topic.lower() in s or s in topic.lower() for s in all_relevant)
            fw_id = preferred_framework or item.get("recommended_framework", "WHAT-WHY-HOW")

            short_ans = item.get("short_answer") or item.get("curated_answer")[:180] + "..."
            detailed_ans = item.get("detailed_answer") or item.get("curated_answer")

            questions.append({
                "question_id": item["id"],
                "question_text": item["question"],
                "category": "E",
                "category_name": CATEGORY_METADATA["E"]["name"],
                "category_badge": CATEGORY_METADATA["E"]["badge"],
                "difficulty": item["difficulty"],
                "topic": topic,
                "source_type": "technical_bank",
                "source_reference": f"Technical Domain: {topic}",
                "recommended_answer_framework": fw_id,
                "recommended_framework": fw_id,
                "short_answer": short_ans,
                "simpler_answer": item.get("simpler_answer") or short_ans,
                "detailed_answer": detailed_ans,
                "curated_answer": detailed_ans,
                "why_this_works": item.get("why_this_works", "Interviewers ask this question to evaluate your deep mechanical sympathy and fundamental conceptual understanding of the technology."),
                "step_by_step_explanation": item.get("step_by_step_explanation", []),
                "follow_up_questions": item.get("follow_up_questions", []),
                "common_mistakes": item.get("common_mistakes", []),
                "suggested_improvements": item.get("suggested_improvements", "Suggested Improvement (Hypothetical Proposal): Benchmark edge-case performance under synthetic stress conditions to verify scaling boundaries."),
                "verified_evidence": [],
                "examples": item.get("examples") or item.get("code_snippet"),
                "code_snippet": item.get("code_snippet"),
                "important_concepts": item.get("important_concepts") or item.get("key_points", []),
                "interview_tips": item.get("interview_tips", []),
                "missing_personal_details": [],
                "evidence_sources": [item.get("source_reference", "Curated Technical Question Bank")],
                "answer_guidance": detailed_ans,
                "expected_key_points": item.get("key_points", []),
                "framework_template": format_answer_template(fw_id),
                "_relevance_priority": 2 if is_matched else 1
            })

        # Sort so relevant technical topics appear first
        questions.sort(key=lambda q: q.get("_relevance_priority", 1), reverse=True)
        return questions

    # -------------------------------------------------------------------------
    # Category F: HR & Behavioral Competency Questions
    # -------------------------------------------------------------------------
    def generate_category_f(self, preferred_framework: Optional[str] = None) -> List[Dict[str, Any]]:
        questions = []
        for item in HR_QUESTION_BANK:
            fw_id = preferred_framework or item.get("recommended_framework", "STAR")
            template_notes = item.get("template_notes", {})

            short_ans = item.get("short_answer", "")
            detailed_ans = item.get("detailed_answer", "")

            questions.append({
                "question_id": item["id"],
                "question_text": item["question"],
                "category": "F",
                "category_name": CATEGORY_METADATA["F"]["name"],
                "category_badge": CATEGORY_METADATA["F"]["badge"],
                "difficulty": item["difficulty"],
                "topic": item["topic"],
                "source_type": "hr_behavioral",
                "source_reference": "Core Behavioral Competency",
                "recommended_answer_framework": fw_id,
                "recommended_framework": fw_id,
                "short_answer": short_ans,
                "simpler_answer": item.get("simpler_answer") or short_ans,
                "detailed_answer": detailed_ans,
                "curated_answer": detailed_ans,
                "why_this_works": item.get("why_this_works", "Interviewers ask this question to evaluate communication, collaboration, conflict resolution, and self-awareness in team environments."),
                "step_by_step_explanation": item.get("step_by_step_explanation", []),
                "follow_up_questions": item.get("follow_up_questions", []),
                "common_mistakes": item.get("common_mistakes", []),
                "suggested_improvements": item.get("suggested_improvements", "Suggested Improvement (Hypothetical Proposal): Conduct post-mortem debriefs after high-pressure situations to document learnings and refine team agreements."),
                "illustrative_example": item.get("illustrative_example", ""),
                "verified_evidence": [],
                "examples": item.get("examples"),
                "code_snippet": None,
                "important_concepts": item.get("important_concepts", []),
                "interview_tips": item.get("interview_tips", []),
                "missing_personal_details": item.get("missing_personal_details", []),
                "evidence_sources": ["Core Behavioral Interview Standards"],
                "answer_guidance": item.get("answer_guidance", detailed_ans),
                "expected_key_points": item.get("key_points", []),
                "framework_template": format_answer_template(fw_id, template_notes)
            })
        return questions

    # -------------------------------------------------------------------------
    # Master Unified Generator & Prioritizer
    # -------------------------------------------------------------------------
    def generate_questions(
        self,
        category: str = "ALL",
        difficulty: str = "All",
        max_questions: int = 15,
        preferred_framework: Optional[str] = None,
        technical_topic: Optional[str] = None,
        priority_skills: Optional[List[str]] = None,
        candidate_confirmations: Optional[Dict[str, bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates, filters, ranks, and deduplicates questions across requested categories.
        Guarantees balanced question distribution across Profile, Projects, Internships,
        Job Requirements, Technical Bank, and Behavioral Bank.
        """
        cat_upper = category.upper().strip() if category else "ALL"
        pool: List[Dict[str, Any]] = []

        if cat_upper in ["ALL", "A", "CATEGORY_A", "RESUME"]:
            qs_a = self.generate_category_a(preferred_framework)
        else:
            qs_a = []

        if cat_upper in ["ALL", "B", "CATEGORY_B", "PROJECTS"]:
            qs_b = self.generate_category_b(preferred_framework)
        else:
            qs_b = []

        if cat_upper in ["ALL", "C", "CATEGORY_C", "INTERNSHIPS"]:
            qs_c = self.generate_category_c(preferred_framework)
        else:
            qs_c = []

        if cat_upper in ["ALL", "D", "CATEGORY_D", "JOB"]:
            qs_d = self.generate_category_d(preferred_framework)
        else:
            qs_d = []

        if cat_upper in ["ALL", "E", "CATEGORY_E", "TECHNICAL"]:
            tech_qs = self.generate_category_e(preferred_framework)
            if technical_topic and technical_topic != "All":
                tech_qs = [q for q in tech_qs if q.get("topic") == technical_topic]
            qs_e = tech_qs
        else:
            qs_e = []

        if cat_upper in ["ALL", "F", "CATEGORY_F", "HR", "BEHAVIORAL"]:
            qs_f = self.generate_category_f(preferred_framework)
        else:
            qs_f = []

        # If priority_skills provided, boost matching questions to front
        if priority_skills:
            norm_priorities = [p.lower().strip() for p in priority_skills if p]
            for lst in [qs_d, qs_e, qs_b]:
                lst.sort(
                    key=lambda q: (
                        0 if any(np in q.get("question_text", "").lower() or np in q.get("topic", "").lower() for np in norm_priorities) else 1
                    )
                )

        if cat_upper == "ALL":
            # Assemble balanced interleaved distribution:
            # 1-2 Profile, 2-3 Projects, 1-2 Internships, 2-3 Job/Gaps, 2-3 Tech, 2-3 HR
            interleaved: List[Dict[str, Any]] = []
            interleaved.extend(qs_a[:2])
            interleaved.extend(qs_b[:3])
            interleaved.extend(qs_c[:2])
            interleaved.extend(qs_d[:3])
            interleaved.extend(qs_e[:3])
            interleaved.extend(qs_f[:2])

            # Fill up from remaining pools if needed
            remaining = qs_b[3:] + qs_d[3:] + qs_e[3:] + qs_f[2:] + qs_a[2:] + qs_c[2:]
            interleaved.extend(remaining)
            pool = interleaved
        else:
            pool = qs_a or qs_b or qs_c or qs_d or qs_e or qs_f

        # Filter by difficulty
        filtered = filter_by_difficulty(pool, target_difficulty=difficulty, max_count=None)

        # Deduplicate by question text hash and sanitize visible text
        seen_texts = set()
        deduped = []
        for q in filtered:
            clean_txt = q["question_text"].strip().lower()
            if clean_txt not in seen_texts:
                seen_texts.add(clean_txt)
                # Sanitize detailed_answer, simpler_answer, short_answer
                if "detailed_answer" in q:
                    q["detailed_answer"] = sanitize_text(q["detailed_answer"])
                if "curated_answer" in q:
                    q["curated_answer"] = sanitize_text(q["curated_answer"])
                if "short_answer" in q:
                    q["short_answer"] = sanitize_text(q["short_answer"])
                if "simpler_answer" in q:
                    q["simpler_answer"] = sanitize_text(q["simpler_answer"])

                # Build fully completed framework answer demonstration
                fw_id = q.get("recommended_framework") or q.get("recommended_answer_framework") or "STAR"
                q["completed_framework_answer"] = build_completed_framework_demonstration(fw_id, q)

                deduped.append(q)

        # Return requested count
        limit = max(1, min(max_questions, 50))
        return deduped[:limit]
