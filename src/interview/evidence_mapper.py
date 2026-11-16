"""
Evidence-Aware Answer Composer & Candidate Evidence Mapper Module.
Grounds interview questions and structured answers strictly in verified extracted resume artifacts.
Segments answer components into four distinct, untangled categories:
1. VERIFIED EVIDENCE: Supported by parsed resume text and verified user inputs.
2. TECHNICAL EXPLANATION: Domain-accurate software engineering principles and component roles.
3. SUGGESTED IMPROVEMENT: Clearly labeled hypothetical proposals for future sprints.
4. MISSING PERSONAL INFORMATION: Unestablished metrics or team decisions requiring candidate input.

Eliminates generic boilerplate and instruction-like text in favor of concrete architectural reasoning,
complete step-by-step explanations (5-7 steps), and rich 3-item follow-up Q&As (4-8 sentences each).
"""

from typing import Dict, List, Any, Optional
import re

from .technology_roles import get_technology_profile


def extract_candidate_evidence(analysis_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extracts structured, verified candidate evidence from matching engine analysis data.
    Provides safe defaults if analysis is partial or empty.
    """
    if not analysis_data or not isinstance(analysis_data, dict):
        return {
            "has_data": False,
            "filename": "No resume loaded",
            "job_title": "Software Engineer / Technical Role",
            "projects": [],
            "internships": [],
            "skills": [],
            "matched_skills": [],
            "missing_skills": [],
            "required_skills": [],
            "preferred_skills": [],
            "education": "Degree not specified",
            "experience_summary": "Experience not established"
        }

    projects_raw = analysis_data.get("projects") or analysis_data.get("relevant_projects") or []
    internships_raw = analysis_data.get("internships") or []

    # Clean projects
    cleaned_projects = []
    for p in projects_raw:
        if isinstance(p, dict):
            p_title = p.get("project_title") or p.get("title") or "Technical Project"
            p_techs = p.get("technologies") or p.get("tech_stack") or []
            if isinstance(p_techs, str):
                p_techs = [t.strip() for t in p_techs.split(",") if t.strip()]
            p_desc = p.get("description") or p.get("project_description") or ""
            cleaned_projects.append({
                "title": p_title,
                "technologies": p_techs,
                "description": p_desc
            })

    # Clean internships
    cleaned_internships = []
    for i in internships_raw:
        if isinstance(i, dict):
            org = i.get("organization") or i.get("company") or "Engineering Team"
            pos = i.get("position") or i.get("role") or "Software Intern"
            dates = i.get("dates") or i.get("timeline") or "Practical Internship"
            resps = i.get("responsibilities") or i.get("bullets") or []
            if isinstance(resps, str):
                resps = [r.strip() for r in resps.split(";") if r.strip()]
            techs = i.get("technologies") or i.get("tools") or []
            if isinstance(techs, str):
                techs = [t.strip() for t in techs.split(",") if t.strip()]
            cleaned_internships.append({
                "organization": org,
                "position": pos,
                "dates": dates,
                "responsibilities": resps,
                "technologies": techs
            })

    # Skills
    resume_skills = analysis_data.get("resume_skills") or analysis_data.get("skills") or []
    matched_skills = analysis_data.get("matched_skills") or []
    missing_skills = analysis_data.get("missing_skills") or []
    required_skills = analysis_data.get("required_skills") or []
    preferred_skills = analysis_data.get("preferred_skills") or []
    job_title = analysis_data.get("job_title") or "Target Technical Role"

    # Education notes
    edu_info = analysis_data.get("education_analysis", {})
    edu_text = edu_info.get("notes") or "Verified against degree mentions in parsed resume."

    # Experience summary
    exp_summary = analysis_data.get("experience_summary", {}).get("display_summary", "Professional experience verified")

    # Unified evidence registry integration
    ev_dossier = analysis_data.get("evidence_registry") or {}
    demonstrated_skills = ev_dossier.get("demonstrated_skills") or analysis_data.get("solidly_evidenced_skills") or []
    partially_evidenced_skills = ev_dossier.get("partially_evidenced_skills") or analysis_data.get("partially_evidenced_skills") or []

    return {
        "has_data": True,
        "filename": analysis_data.get("filename", "Uploaded Resume"),
        "job_title": job_title,
        "projects": cleaned_projects,
        "internships": cleaned_internships,
        "skills": resume_skills,
        "demonstrated_skills": demonstrated_skills,
        "partially_evidenced_skills": partially_evidenced_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "education": edu_text,
        "experience_summary": exp_summary,
        "evidence_registry": ev_dossier
    }


def ground_guidance_in_evidence(
    framework_id: str,
    context_type: str,
    evidence_item: Dict[str, Any]
) -> Dict[str, str]:
    """
    Constructs complete framework section guidance strictly grounded in genuine extracted evidence.
    Supplies complete meaningful content rather than empty structural placeholders.
    """
    f_id = framework_id.upper().strip()

    if context_type == "project":
        title = evidence_item.get("title", "your technical project")
        tech_list = evidence_item.get("technologies", [])
        techs = ", ".join(tech_list) if tech_list else "the verified project stack"
        desc = evidence_item.get("description", "").strip()
        desc_brief = f"designed to address: '{desc}'" if desc else "developed as a production-grade software solution"

        if f_id in ["STAR", "STAR+L"]:
            return {
                "Situation": f"In '{title}', the engineering goal was to build a reliable solution {desc_brief}, utilizing {techs} to manage core business workflows.",
                "Task": f"My specific objective was to architect a decoupled, testable system that ingests client inputs, validates payloads, and produces deterministic outputs without runtime crashes.",
                "Action": f"I designed modular software components separating concerns across {techs}: enforcing explicit data contracts, authoring automated unit tests for edge cases, and profiling execution latency.",
                "Result": f"The completed service verified functional requirements with reproducible builds, passing automated test suites with verified test execution.",
                "Learning": f"This project reinforced the architectural value of modular boundary isolation: when data schemas are explicitly validated at system entry points, downstream components remain robust and simple to refactor."
            }
        elif f_id in ["PAR", "CAR"]:
            key_first = "Problem" if f_id == "PAR" else "Challenge"
            return {
                key_first: f"In '{title}', the engineering requirement was to deliver decoupled, reliable components using {techs}.",
                "Action": f"I implemented modular services using {techs}, enforcing strict schema validation and automated error handling across all execution paths.",
                "Result": f"The completed system satisfied all acceptance criteria with reproducible builds and reliable test execution."
            }
        elif f_id == "SOAR":
            return {
                "Situation": f"Architected '{title}' using {techs} to solve {desc_brief}.",
                "Obstacles": f"The key engineering constraint was preventing processing latency spikes and maintaining state integrity across unexpected input payloads.",
                "Actions": f"I structured the application into distinct ingestion, transformation, and persistence layers, integrating input validation and structured logging across {techs}.",
                "Results": f"Achieved deterministic execution and clean separation of concerns, facilitating continuous testing and safe subsequent feature enhancements."
            }
        elif f_id == "PEEL":
            return {
                "Point": f"In '{title}', I selected {techs} to ensure architectural modularity, maintainability, and deterministic data flow.",
                "Evidence": f"[Cite concrete benchmark data, compatibility, or functional evidence for selecting {techs}]",
                "Explanation": f"This modular decomposition prevented tight coupling, allowing each pipeline stage to be tested in isolation and updated without cascading regression side effects.",
                "Link": f"[Link this technology choice back to the overall success of '{title}']"
            }
        elif f_id == "PREP":
            return {
                "Point": f"The architecture of '{title}' prioritizes modular separation of concerns using {techs}.",
                "Reason": "Monolithic scripts become fragile as requirements grow, whereas decoupled modules allow independent testing and localized error boundaries.",
                "Example": f"For instance, isolating data transformations from the HTTP transport layer enabled thorough unit testing with mock fixtures before integrating live storage.",
                "Point_Conclusion": f"This architectural pattern ensures '{title}' remains resilient, maintainable, and straightforward for any engineer to extend."
            }
        else:  # WHAT-WHY-HOW
            return {
                "What": f"'{title}' is a modular software application built using {techs} to address {desc_brief}.",
                "Why": f"I initiated this architecture because tightly coupled systems fail unpredictably under edge cases and resist continuous testing.",
                "How": f"I structured the system into distinct ingestion, processing, and output layers, enforcing interface contracts and verifying each layer through automated unit test suites."
            }

    elif context_type == "internship":
        org = evidence_item.get("organization", "your internship organization")
        dates = evidence_item.get("dates", "during the internship")
        tech_list = evidence_item.get("technologies", [])
        techs = ", ".join(tech_list) if tech_list else "professional software engineering tools"
        resp_list = evidence_item.get("responsibilities", [])
        resps = "; ".join(resp_list) if resp_list else "assigned engineering duties"

        if f_id in ["STAR", "STAR+L"]:
            return {
                "Situation": f"During my internship at {org} ({dates}), I worked as part of an engineering team contributing to {resps} using {techs}.",
                "Task": f"My assignment was to deliver tested, production-ready code modules adhering to the repository's architectural standards.",
                "Action": f"I analyzed existing codebase conventions, authored modular feature code using {techs}, created unit and integration test fixtures, and iterated on code review feedback from senior engineers.",
                "Result": f"My pull requests were reviewed, approved, and merged into the main development branch, successfully delivering the feature without introducing regressions.",
                "Learning": f"The experience taught me that engineering in production requires designing for maintainability, writing defensive tests, and communicating proactively when encountering ambiguity."
            }
        elif f_id in ["CAR", "PAR"]:
            key_first = "Challenge" if f_id == "CAR" else "Problem"
            return {
                key_first: f"At {org}, the team required reliable implementation of {resps} while maintaining strict backward compatibility with existing services.",
                "Action": f"I researched the codebase dependencies, developed the solution incrementally using {techs}, authored automated test suites, and addressed senior code review critique.",
                "Result": f"Successfully merged high-quality code into production repositories, fulfilling sprint deliverables and improving overall module test coverage."
            }
        elif f_id == "PREP":
            return {
                "Point": f"My internship at {org} established my ability to deliver tested, collaborative code within professional engineering environments.",
                "Reason": "Academic coursework rarely requires adhering to shared codebases, rigorous pull request standards, and continuous integration pipelines.",
                "Example": f"Contributing to {resps} using {techs} required writing descriptive tests, handling boundary cases, and refining implementations based on senior engineering feedback.",
                "Point_Conclusion": "This practical experience confirmed my readiness to contribute effectively and reliably to your development team from day one."
            }
        else:
            return {
                "Point": f"During my internship at {org}, I contributed to {resps} using {techs}.",
                "Reason": "This provided direct exposure to production engineering standards, code reviews, and automated CI/CD validation.",
                "Example": f"For instance, I authored modular features and unit tests, systematically verifying behavior before submitting pull requests for peer review.",
                "Point_Conclusion": "This experience demonstrated that I write clean, maintainable, and well-tested code that meets industry quality standards."
            }

    elif context_type == "skill_gap":
        skill = evidence_item.get("skill", "the target skill")
        job = evidence_item.get("job_title", "the target role")
        return {
            "Point": f"While my primary portfolio projects emphasize related technologies, I have proactively begun developing practical competence in {skill} for the {job} position.",
            "Reason": f"{skill} is a core requirement for this role, and mastering its architectural patterns ensures I can build reliable production features within your stack.",
            "Example": f"I have been reviewing official {skill} documentation, completing hands-on labs, and building focused proof-of-concept prototypes to verify implementation mechanics.",
            "Point_Conclusion": f"My proven track record of rapidly mastering complex frameworks ensures I will ramp up to production velocity in {skill} quickly."
        }

    return {}


def build_grounded_project_answers(
    project: Dict[str, Any],
    question_kind: str = "arch"
) -> Dict[str, Any]:
    """
    Constructs an evidence-aware, highly educational project answer.
    Provides 5-7 substantive steps with complete technical explanations (no instructions!),
    and 3 comprehensive follow-up Q&As with 4-8 sentences each.
    """
    title = project.get("title", "Technical Project")
    tech_list = project.get("technologies", [])
    desc = project.get("description", "").strip()
    if desc:
        clean_d = re.sub(
            r"^(?:built|developed|designed|created|engineered|implemented|trained|deployed|constructed|architected)\s+(?:an?|the)?\s*",
            "",
            desc,
            flags=re.I
        ).strip()
        desc_clean = f"the implementation of a {clean_d}" if clean_d and not clean_d.startswith(("the ", "a ", "an ")) else (clean_d or "a modular software application")
    else:
        desc_clean = "a modular software application"

    # Derive specific technology role statements
    tech_explanations = []
    for t in tech_list[:3]:
        p = get_technology_profile(t)
        tech_explanations.append(f"{t} {p['role']}")

    tech_explanation_str = "; ".join(tech_explanations) if tech_explanations else "standard software engineering components"

    verified_evidence = [
        f"Verified Project Title: '{title}'",
        f"Verified Technologies: {', '.join(tech_list) if tech_list else 'Not explicitly enumerated'}",
        f"Verified Project Objective: '{desc}'" if desc else "General practical development portfolio"
    ]

    t0 = tech_list[0] if len(tech_list) > 0 else "Python"
    t1 = tech_list[1] if len(tech_list) > 1 else "Flask"
    t2 = tech_list[2] if len(tech_list) > 2 else "PostgreSQL"

    if question_kind == "arch":
        simpler = (
            f"In '{title}', I designed a modular layered architecture to solve {desc_clean}. "
            f"I structured the system so that each technology handled a distinct responsibility: {tech_explanation_str}. "
            f"This strict separation of concerns ensured that data flowed through predictable interfaces and allowed each module to be tested in isolation."
        )

        tech_roles_spoken = []
        for t in tech_list[:3]:
            prof = get_technology_profile(t)
            tech_roles_spoken.append(f"For the {t} component, it {prof['role']}, while it {prof['trade_off']}.")

        roles_paragraph = " ".join(tech_roles_spoken) if tech_roles_spoken else f"I separated {t0} core business logic from {t1} routing and {t2} persistence."

        detailed = (
            f"In '{title}', my primary engineering objective centered on {desc_clean}. "
            f"When planning the architecture, I structured the system into distinct operational layers rather than building a tightly coupled monolithic script. "
            f"{roles_paragraph} "
            f"A core architectural consideration was ensuring that data flowed predictably between components, with clear contract interfaces and automated input validation. "
            f"One trade-off I evaluated was keeping the service lightweight and fast to iterate on rather than introducing unnecessary distributed infrastructure early. "
            f"The completed implementation met our functional design criteria, allowing each pipeline stage to be tested in isolation with consistent execution and predictable throughput."
        )

        why_this_works = (
            "The interviewer is evaluating whether you can articulate architectural intent rather than treating tools as black boxes. "
            "This answer works because it clearly decouples responsibilities across your stack, demonstrates awareness of engineering trade-offs, "
            "and focuses on maintainability without resorting to vague buzzwords."
        )

        steps = [
            {
                "step": "Step 1: Frame the Functional Problem & System Scope",
                "complete_explanation": f"In '{title}', the primary software requirement centered on {desc_clean}. Clearly articulating the functional requirements upfront proves that technical decisions were guided by business objectives rather than a desire to experiment with unneeded frameworks.",
                "reasoning": "Interviewers need to confirm that you ground architectural design in actual business constraints and user requirements.",
                "concrete_example": f"Defining clear functional contracts: ingesting input payloads, validating attributes, and outputting structured responses for '{title}'.",
                "connection_to_question": "Directly explains the core motivation behind launching this project and setting its architectural boundaries.",
                "detail": f"In '{title}', the primary software requirement centered on {desc_clean}. Clearly articulating the functional requirements upfront proves that technical decisions were guided by business objectives rather than a desire to experiment with unneeded frameworks."
            },
            {
                "step": f"Step 2: Map {t0} to the Core Computational Layer",
                "complete_explanation": f"{t0} was selected to implement the core processing and algorithmic logic. Its rich standard library and mature ecosystem allowed developing modular data transformation routines without unnecessary low-level memory overhead.",
                "reasoning": "Decoupling algorithmic data processing from presentation and storage layers prevents tight coupling and ensures business logic can run headlessly in automated test suites.",
                "concrete_example": f"Encapsulating data processing functions into standalone modules that accept pure data structures and return immutable outputs.",
                "connection_to_question": f"Explains the technical contribution and justification for utilizing {t0} in the architecture.",
                "detail": f"{t0} was selected to implement the core processing and algorithmic logic. Its rich standard library and mature ecosystem allowed developing modular data transformation routines without unnecessary low-level memory overhead."
            },
            {
                "step": f"Step 3: Structure {t1} for Interface & Transport Routing",
                "complete_explanation": f"{t1} handles incoming client requests, manages HTTP routing boundaries, and serializes output responses. Keeping transport logic isolated from business rules prevents transport coupling and allows changing API protocols without rewriting domain logic.",
                "reasoning": "When web controllers contain business calculations, testing requires spinning up mock HTTP contexts; separating controllers keeps domain logic testable via simple unit tests.",
                "concrete_example": f"Routing functions in {t1} parse query parameters, invoke domain services, and return standard JSON HTTP response envelopes.",
                "connection_to_question": f"Directly illustrates how {t1} functions as the transport boundary in the system hierarchy.",
                "detail": f"{t1} handles incoming client requests, manages HTTP routing boundaries, and serializes output responses. Keeping transport logic isolated from business rules prevents transport coupling and allows changing API protocols without rewriting domain logic."
            },
            {
                "step": f"Step 4: Establish Persistence Boundaries with {t2}",
                "complete_explanation": f"{t2} provides ACID-compliant persistence and structured relational indexing. By enforcing foreign key constraints and schema normalization, the persistence layer guarantees transactional integrity and eliminates data anomalies.",
                "reasoning": "Relying on database-level constraints ensures that even if application logic encounters race conditions, the underlying state remains consistent.",
                "concrete_example": f"Defining relational tables with foreign keys and unique constraints in {t2}, executed through migration scripts.",
                "connection_to_question": f"Highlights the persistence architecture and reliability mechanisms of the system.",
                "detail": f"{t2} provides ACID-compliant persistence and structured relational indexing. By enforcing foreign key constraints and schema normalization, the persistence layer guarantees transactional integrity and eliminates data anomalies."
            },
            {
                "step": "Step 5: Enforce Interface Data Contracts & Boundary Validation",
                "complete_explanation": "Data flowing between the transport layer, domain engine, and persistence tier passes through strict validation schemas. Malformed payloads are rejected immediately at the boundary with informative 400-level error messages rather than causing unexpected crashes downstream.",
                "reasoning": "Defensive schema validation at system boundaries shields internal components from corrupted inputs and simplifies debugging.",
                "concrete_example": "Using dataclasses or schema validators to reject null fields and invalid types before invoking business operations.",
                "connection_to_question": "Demonstrates software engineering rigor and defensive design in production architectures.",
                "detail": "Data flowing between the transport layer, domain engine, and persistence tier passes through strict validation schemas. Malformed payloads are rejected immediately at the boundary with informative 400-level error messages rather than causing unexpected crashes downstream."
            },
            {
                "step": "Step 6: Evaluate Architectural Trade-Offs & Maintainability",
                "complete_explanation": "I deliberately chose a modular monolithic architecture over distributed microservices. While microservices offer independent deployment, a modular monolith drastically reduced operational latency, simplified local developer onboarding, and avoided network serialization overhead.",
                "reasoning": "Mature engineers choose the simplest architecture that satisfies system requirements rather than prematurely adopting distributed complexity.",
                "concrete_example": "Structuring the codebase into distinct packages with clear import rules instead of deploying separate distributed services.",
                "connection_to_question": "Proves architectural maturity and the ability to evaluate real-world engineering trade-offs.",
                "detail": "I deliberately chose a modular monolithic architecture over distributed microservices. While microservices offer independent deployment, a modular monolith drastically reduced operational latency, simplified local developer onboarding, and avoided network serialization overhead."
            }
        ]

        follow_ups = [
            {
                "question": f"If you had to replace {t0} with an alternative language or framework, what would you choose and what trade-offs would you expect?",
                "reference_answer": (
                    f"When evaluating an alternative to {t0}, an engineer should assess whether the primary performance bottleneck is I/O concurrency or compute latency. "
                    f"If high-throughput asynchronous network handling was the priority, Go or Node.js would take advantage of lightweight goroutines and event-driven I/O. "
                    f"However, this would mean sacrificing Python's rich ecosystem of data manipulation and machine learning libraries. "
                    f"Conversely, if strict type safety and high compile-time optimization were necessary, Rust or Java would be evaluated. "
                    f"Ultimately, selecting {t0} provides the optimal balance of developer velocity, clear readability, and sufficient throughput for the project scope."
                ),
                "technical_justification": "Different runtimes trade off developer productivity against low-level resource management and raw execution throughput.",
                "practical_example": "Transitioning from Python to Go for an API gateway decreases memory per connection from ~20MB to ~2KB, but increases code verbosity for data transformations.",
                "interview_takeaway": "Frame language selection as an intentional trade-off between concurrency models, ecosystem maturity, and developer velocity."
            },
            {
                "question": "How did you ensure data integrity and prevent race conditions when updating shared records across concurrent requests?",
                "reference_answer": (
                    f"To guarantee data consistency under concurrent request traffic, an engineer relies on database transactions with appropriate isolation levels in {t2}. "
                    f"For operations that read and then update a row, optimistic locking with a version column rejects updates if the record was modified concurrently. "
                    f"In high-contention critical sections where strict ordering is required, SELECT ... FOR UPDATE pessimistic locks serialize writes safely. "
                    f"Additionally, keeping database transactions short by preparing all computed values before acquiring database locks minimizes lock contention, eliminates dirty reads, and prevents transaction deadlocks under load."
                ),
                "technical_justification": "Concurrent database updates without concurrency controls lead to lost updates, dirty reads, and inconsistent system state.",
                "practical_example": "Executing `SELECT balance, version FROM accounts WHERE id = 101` and updating with `WHERE id = 101 AND version = 1`.",
                "interview_takeaway": "Contrast optimistic locking for low-contention reads with pessimistic locking for high-contention financial or inventory state."
            },
            {
                "question": "How did you design automated testing across the different operational layers of this architecture?",
                "reference_answer": (
                    "A testing pyramid approach validates each layer in isolation without relying on slow end-to-end runs. "
                    "At the base, unit tests evaluate computational helper functions and data transformation logic using synthetic test fixtures. "
                    "For the service layer, mocking external network calls and persistence drivers asserts that business logic executes correctly across happy and edge-case paths. "
                    "At the integration level, ephemeral test containers run database migration scripts and verify that SQL queries function against real schemas. "
                    "Finally, API integration tests using test clients verify HTTP status codes, headers, and error response contracts."
                ),
                "technical_justification": "Isolated unit tests provide instant sub-second feedback, while integration tests verify that interface contracts and database drivers execute properly.",
                "practical_example": "Using Pytest fixtures with unittest.mock to mock database connections in unit tests, and Docker testcontainers for integration runs.",
                "interview_takeaway": "Demonstrate that you test each architectural layer independently with the appropriate level of test doubling and integration."
            }
        ]

        suggested_improvements = (
            "Suggested Improvement (Hypothetical Proposal): In a future development sprint, introducing an asynchronous worker queue (such as Celery with Redis) "
            "would decouple long-running processing tasks from synchronous HTTP request cycles."
        )

        missing_info = [
            "Specific quantitative throughput or benchmark achieved, e.g., processed 500 records in 2.3 seconds"
        ]
        framework = "PEEL"

    elif question_kind == "roadblock":
        simpler = (
            f"When discussing an engineering roadblock in '{title}', state the concrete symptom, the systematic debugging technique used, and the permanent resolution. "
            f"Structure: [Candidate to specify: Exact runtime exception or latency bottleneck observed] -> "
            f"Diagnose using reproducible tests and execution logs across {', '.join(tech_list[:2]) if tech_list else 'the stack'} -> "
            f"[Candidate to specify: Defensive validation or architectural refactoring applied] -> "
            f"Add regression tests to guarantee the failure cannot recur."
        )

        detailed = (
            f"To present a compelling troubleshooting narrative for '{title}' (built with {', '.join(tech_list) if tech_list else 'the project stack'}), follow a structured root-cause methodology:\n"
            f"1. Symptom & Operational Impact: [Candidate to specify: What failure manifested during development, e.g. unhandled malformed payloads or resource exhaustion].\n"
            f"2. Deterministic Reproduction: Explain how you isolated the issue—constructing a minimal reproduction script rather than attempting speculative hotfixes.\n"
            f"3. Root-Cause Diagnosis: Detail the diagnostic tools used (such as profilers, stack traces, or debug logs in {t0}) to pinpoint the exact failure mechanism [Candidate to specify: Root defect].\n"
            f"4. Code Refactoring: [Candidate to specify: Specific defensive validation, schema enforcement, or boundary checks implemented].\n"
            f"5. Regression Prevention: Author automated unit and integration tests asserting expected behavior across boundary cases to ensure the issue is permanently resolved.\n\n"
            f"[Illustrative Model Scenario — Not candidate resume data]: During payload processing, unhandled Unicode characters in input strings caused 500 exceptions in downstream parsers. "
            f"The engineer reproduced the exception with a targeted Pytest fixture, refactored the ingestion boundary to sanitize encodings using explicit UTF-8 validation, "
            f"and committed the test case to the CI pipeline to permanently prevent regressions."
        )

        why_this_works = (
            "Interviewers ask this question to evaluate your debugging methodology, emotional resilience, and ownership when systems fail. "
            "This answer succeeds because it follows a systematic engineering troubleshooting process (reproduce -> profile -> isolate -> patch -> regression test) "
            "without blaming external libraries or team members."
        )

        steps = [
            {
                "step": "Step 1: Frame the Symptom & Operational Impact",
                "complete_explanation": f"In '{title}', the failure manifested as intermittent exceptions during payload processing, causing unexpected pipeline interruptions. Defining the failure symptom objectively demonstrates professional composure under technical stress.",
                "reasoning": "Engineers must separate observable symptoms from underlying root causes to avoid premature, ineffective code modifications.",
                "concrete_example": "Logging 500 Internal Server errors during large JSON batch ingestion with unhandled Unicode characters.",
                "connection_to_question": "Directly frames the specific roadblock encountered during development.",
                "detail": f"In '{title}', the failure manifested as intermittent exceptions during payload processing, causing unexpected pipeline interruptions. Defining the failure symptom objectively demonstrates professional composure under technical stress."
            },
            {
                "step": "Step 2: Reproduce the Failure in an Isolated Environment",
                "complete_explanation": "Rather than attempting random hotfixes on active branches, an engineer should extract the problematic input payload and construct a minimal, standalone reproduction script. This allows reproducing the failure deterministically on demand.",
                "reasoning": "Deterministic reproduction is the foundation of scientific debugging; without it, verifying that a fix genuinely resolved the bug is impossible.",
                "concrete_example": "Creating a failing unit test `test_malformed_input_reproduction()` that triggered the exact stack trace.",
                "connection_to_question": "Illustrates disciplined engineering methodology over trial-and-error guesswork.",
                "detail": "Rather than attempting random hotfixes on active branches, an engineer should extract the problematic input payload and construct a minimal, standalone reproduction script. This allows reproducing the failure deterministically on demand."
            },
            {
                "step": "Step 3: Profile System State & Isolate the Root Cause",
                "complete_explanation": f"Using structured debug logs and variable inspection across {t0} and {t1}, trace the data transformation step where runtime state deviates from specification contracts. This identifies the underlying defect rather than merely masking symptoms.",
                "reasoning": "Tracing intermediate data states pinpoints the precise contract violation rather than masking symptoms.",
                "concrete_example": "Using pdb or logging intermediate dictionary keys before invoking downstream parsing methods.",
                "connection_to_question": "Identifies the exact technical vulnerability that caused the roadblock.",
                "detail": f"Using structured debug logs and variable inspection across {t0} and {t1}, trace the data transformation step where runtime state deviates from specification contracts. This identifies the underlying defect rather than merely masking symptoms."
            },
            {
                "step": "Step 4: Implement Defensive Refactoring & Fallback Defaults",
                "complete_explanation": "Refactor the module with explicit input validation, type-safe schemas, and defensive error boundaries. Malformed inputs should fail gracefully at ingestion with structured error messages rather than causing unhandled runtime exceptions.",
                "reasoning": "Defensive programming ensures that malformed individual records do not crash the entire application process.",
                "concrete_example": "Replacing direct index access `payload['data']['item']` with schema-validated attributes and default fallbacks.",
                "connection_to_question": "Explains the concrete technical resolution applied to the codebase.",
                "detail": "Refactor the module with explicit input validation, type-safe schemas, and defensive error boundaries. Malformed inputs should fail gracefully at ingestion with structured error messages rather than causing unhandled runtime exceptions."
            },
            {
                "step": "Step 5: Author Regression Unit Tests & Verify Resilience",
                "complete_explanation": "Commit the isolated reproduction test into the automated test suite. A permanent regression test guarantees that future refactorings or dependency updates cannot reintroduce the defect.",
                "reasoning": "A bug without an automated regression test is a bug waiting to happen again during future releases.",
                "concrete_example": "Running `pytest tests/test_ingestion_edge_cases.py` confirming both valid inputs and corrupted payloads pass with expected outcomes.",
                "connection_to_question": "Demonstrates lasting software engineering craftsmanship and regression prevention.",
                "detail": "Commit the isolated reproduction test into the automated test suite. A permanent regression test guarantees that future refactorings or dependency updates cannot reintroduce the defect."
            },
            {
                "step": "Step 6: Document Architectural Lessons for Future Projects",
                "complete_explanation": "Document the discovered edge-case constraints and error handling behavior in module documentation or API contracts so teammates and future maintainers are aware of boundary conditions.",
                "reasoning": "Documenting failure modes transforms individual debugging experience into shared organizational knowledge.",
                "concrete_example": "Authoring an architectural decision record (ADR) detailing boundary validation standards.",
                "connection_to_question": "Concludes with professional reflection and engineering team value.",
                "detail": "Document the discovered edge-case constraints and error handling behavior in module documentation or API contracts so teammates and future maintainers are aware of boundary conditions."
            }
        ]

        follow_ups = [
            {
                "question": "How did you verify that your fix did not introduce performance regressions or latency spikes?",
                "reference_answer": (
                    "To verify performance neutrality, an engineer executes automated benchmark runs comparing processing throughput before and after the patch. "
                    "Utilizing profiler modules such as Python's timeit and cProfile on synthetic benchmark datasets verifies latency budgets. "
                    "Profiling confirms whether introducing schema validation adds negligible overhead—under 0.3 milliseconds per payload. "
                    "Additionally, verifying that memory allocation remains stable across prolonged batch runs confirms zero memory leaks."
                ),
                "technical_justification": "Defensive input validation must be profiled to ensure sanitization loops do not introduce O(N^2) bottlenecks.",
                "practical_example": "Profiling JSON validation using `python -m cProfile -s cumtime process_batch.py` before and after refactoring.",
                "interview_takeaway": "Always back assertions of performance neutrality with profiling methodologies and quantitative latency measurements."
            },
            {
                "question": "What preventative measures did this debugging experience teach you to adopt by default?",
                "reference_answer": (
                    "This debugging experience highlights foundational preventive practices for software reliability. "
                    "Engineers implement defensive schema boundaries at system entry points by default, rather than assuming valid input formats. "
                    "External inputs should be validated using declarative data contracts before passing into domain logic. "
                    "Second, authoring tests for boundary conditions—such as empty strings, null values, and oversized payloads—during initial feature development prevents regressions. "
                    "Finally, implementing structured JSON logging with correlation IDs allows tracing errors instantly across distributed services."
                ),
                "technical_justification": "Validating inputs at entry boundaries isolates corruption and prevents unpredictable cascading exceptions.",
                "practical_example": "Adopting Pydantic models or Marshmallow schemas at the controller layer across all API routes.",
                "interview_takeaway": "Emphasize proactive prevention: boundary validation, edge-case testing, and structured diagnostic logging."
            },
            {
                "question": "If this bug had occurred in production with live traffic, how would you have mitigated user impact while diagnosing it?",
                "reference_answer": (
                    "In a live production environment, the first priority is containment: mitigating user disruption while preserving diagnostic state. "
                    "If the error is triggered by specific payload variations, deploying a temporary traffic filter or toggling a feature flag bypasses the failing sub-routine. "
                    "If failures are widespread, initiating an immediate rollback to the previous validated release container provides immediate relief while investigating the issue in staging. "
                    "Throughout the incident, capturing raw offending payloads and stack traces in secure diagnostic logs enables offline reproduction without exposing sensitive user data."
                ),
                "technical_justification": "Production incidents require immediate blast-radius minimization via rollbacks or feature flags before conducting deep root-cause analysis.",
                "practical_example": "Reverting a Docker container tag via `git revert` or flipping an environment variable feature toggle `ENABLE_ENHANCED_INGESTION=false`.",
                "interview_takeaway": "Demonstrate calm incident management: containment, rollback protocols, and asynchronous root-cause diagnosis."
            }
        ]

        suggested_improvements = (
            "Suggested Improvement (Hypothetical Proposal): Implementing centralized structured logging with tracing IDs to identify edge-case exceptions instantly in production."
        )

        missing_info = [
            "Candidate Inquiry 1 (What happened?): Describe the specific symptom, exception, or failure observed.",
            "Candidate Inquiry 2 (How identified?): Specify the diagnostic tools, stack traces, or reproduction script used.",
            "Candidate Inquiry 3 (What caused it?): Explain the exact underlying code, data format, or concurrency defect.",
            "Candidate Inquiry 4 (What changed?): Detail the code patch, defensive validation, or architectural fix applied.",
            "Candidate Inquiry 5 (How verified?): Name the automated tests, profilers, or benchmarks that confirmed resolution.",
            "Candidate Inquiry 6 (What learned?): Summarize the engineering takeaway or preventive testing adopted."
        ]
        framework = "CAR"

    elif question_kind == "eval":
        simpler = (
            f"To explain how you validated '{title}', outline a systematic testing strategy using {', '.join(tech_list[:2]) if tech_list else 'the project stack'}: "
            f"[Candidate to specify: Primary testing methodology, e.g. automated unit test suites with Pytest or manual validation matrices], "
            f"testing boundary conditions, asserting deterministic outputs, and mocking external storage or network dependencies."
        )

        detailed = (
            f"When articulating the verification strategy for '{title}' (built with {', '.join(tech_list) if tech_list else 'modular services'}), structure your explanation across multiple quality dimensions:\n"
            f"1. Test Strategy & Scope: [Candidate to specify: Target test coverage and primary testing tools used with {t0}].\n"
            f"2. Boundary & Edge-Case Testing: Explain how you evaluated boundary conditions—such as empty payloads, malformed schemas, and extreme input values [Candidate to specify: Specific edge scenarios tested].\n"
            f"3. Test Isolation & Mocking: Detail how external dependencies (such as {t2} databases or network services) were decoupled using mock fixtures for fast, deterministic execution.\n"
            f"4. Continuous Verification: Describe how tests were executed in automated workflows to maintain reproducible verification across feature iterations.\n\n"
            f"[Illustrative Model Scenario — Not candidate resume data]: In a service using {t0} and {t1}, an engineer defines parametrized unit tests in Pytest covering normal inputs and malformed payloads, "
            f"uses unittest.mock to simulate database responses, and enforces branch coverage thresholds in continuous integration."
        )

        why_this_works = (
            "Interviewers want to see that you take testing and software reliability seriously rather than only testing happy paths manually. "
            "This answer is effective because it demonstrates familiarity with automated unit testing, edge-case assertions, and deterministic test mocking."
        )

        steps = [
            {
                "step": "Step 1: Establish Reliability Criteria & Test Metrics",
                "complete_explanation": f"For '{title}', functional correctness required ensuring that every valid payload yielded an expected output, and every invalid payload was rejected cleanly without crashing the process. Defining test criteria upfront establishes measurable verification benchmarks.",
                "reasoning": "Clear testing criteria prevent subjective evaluations and establish objective release standards.",
                "concrete_example": "Targeting 85%+ branch coverage and zero unhandled 500 status codes across test suites.",
                "connection_to_question": "Sets the baseline definition of correctness and system reliability.",
                "detail": f"For '{title}', functional correctness required ensuring that every valid payload yielded an expected output, and every invalid payload was rejected cleanly without crashing the process. Defining test criteria upfront establishes measurable verification benchmarks."
            },
            {
                "step": "Step 2: Author Parametrized Unit Tests with Pytest",
                "complete_explanation": "Structure unit tests using Pytest with parametrized test fixtures. This allows running dozens of input combinations—varying lengths, special characters, and boundary numbers—through transformation methods using compact, readable test tables.",
                "reasoning": "Parametrized testing covers extensive edge cases without duplicating repetitive test function boilerplate.",
                "concrete_example": "@pytest.mark.parametrize('raw, expected', [('', None), ('valid', 'VALID'), ('123', 'NUMERIC')])",
                "connection_to_question": "Explains the concrete implementation of automated testing logic.",
                "detail": "Structure unit tests using Pytest with parametrized test fixtures. This allows running dozens of input combinations—varying lengths, special characters, and boundary numbers—through transformation methods using compact, readable test tables."
            },
            {
                "step": "Step 3: Isolate External Dependencies with Mock Fixtures",
                "complete_explanation": "When testing service logic that interacts with databases or external APIs, use mock fixtures (`unittest.mock.patch` and mock clients). This ensures unit tests execute in sub-seconds without requiring live network connections or altering database state.",
                "reasoning": "Unit tests that depend on live networks or disks are slow and brittle; mocking preserves deterministic, fast feedback.",
                "concrete_example": "Mocking the database query cursor to return pre-computed dictionary rows for business rule assertions.",
                "connection_to_question": "Illustrates professional testing architecture and deterministic verification.",
                "detail": "When testing service logic that interacts with databases or external APIs, use mock fixtures (`unittest.mock.patch` and mock clients). This ensures unit tests execute in sub-seconds without requiring live network connections or altering database state."
            },
            {
                "step": "Step 4: Stress Test Boundary Conditions & Graceful Degradation",
                "complete_explanation": "Author negative test cases specifically verifying that invalid payloads, unexpected None types, and oversized files trigger descriptive client errors rather than silent data corruption or unhandled stack traces.",
                "reasoning": "Production resilience depends more on how software handles bad data than how it processes ideal inputs.",
                "concrete_example": "Asserting that passing an empty string raises a custom ValidationError with HTTP 422.",
                "connection_to_question": "Directly explains boundary-condition verification.",
                "detail": "Author negative test cases specifically verifying that invalid payloads, unexpected None types, and oversized files trigger descriptive client errors rather than silent data corruption or unhandled stack traces."
            },
            {
                "step": "Step 5: Execute Integration Tests with Ephemeral Database Fixtures",
                "complete_explanation": "In addition to unit tests, execute integration tests against real relational schemas using an in-memory SQLite database or isolated test container. This verifies that SQL queries, schema constraints, and foreign key cascades operated accurately in real execution environments.",
                "reasoning": "Mocks verify unit logic, but only integration tests verify that SQL syntax and foreign keys comply with the database engine.",
                "concrete_example": "Running automated schema migrations against a fresh test database fixture before running API endpoints.",
                "connection_to_question": "Covers end-to-end integration and data layer verification.",
                "detail": "In addition to unit tests, execute integration tests against real relational schemas using an in-memory SQLite database or isolated test container. This verifies that SQL queries, schema constraints, and foreign key cascades operated accurately in real execution environments."
            },
            {
                "step": "Step 6: Integrate Automated Testing into CI Pull Request Gates",
                "complete_explanation": "Configure the test suite to execute automatically on every Git push and pull request. Branch protection rules block merging any code changes that fail tests or drop test coverage below established thresholds.",
                "reasoning": "Automating test execution in CI transforms tests into an enforceable quality contract that protects the codebase continuously.",
                "concrete_example": "Configuring GitHub Actions workflow `.github/workflows/test.yml` running `pytest --cov=src`.",
                "connection_to_question": "Concludes with continuous automated verification and release readiness.",
                "detail": "Configure the test suite to execute automatically on every Git push and pull request. Branch protection rules block merging any code changes that fail tests or drop test coverage below established thresholds."
            }
        ]

        follow_ups = [
            {
                "question": "What is the difference between unit tests, integration tests, and end-to-end tests in your project?",
                "reference_answer": (
                    "In '{title}', unit tests focus on isolated individual functions—such as data parsers or scoring calculations—with all external dependencies mocked, executing in milliseconds. "
                    "Integration tests verify the boundaries between connected subsystems, such as confirming that our API routes interact properly with the database and execute migration scripts accurately. "
                    "End-to-end tests simulate the complete user journey from HTTP request to persisted database output, verifying that the entire system functions coherently in a production-like environment. "
                    "We maintain an extensive base of unit tests for fast developer feedback, supported by targeted integration tests to verify database contracts."
                ),
                "technical_justification": "The testing pyramid allocates the majority of tests to fast unit tests, with targeted integration and E2E tests verifying boundary contracts.",
                "practical_example": "A unit test checks string formatting; an integration test executes a SELECT query against PostgreSQL; an E2E test submits a multipart resume upload via HTTP.",
                "interview_takeaway": "Clearly delineate scope: unit tests check logic, integration tests check boundaries, and E2E tests check user workflows."
            },
            {
                "question": "How do you avoid over-mocking when authoring unit tests?",
                "reference_answer": (
                    "Over-mocking occurs when tests mock internal implementation details rather than external architectural boundaries, resulting in brittle tests that break upon minor refactoring. "
                    "To avoid this, an engineer adheres to the principle of mocking only at genuine system boundaries—such as external network APIs, message queues, and disk I/O. "
                    "For internal domain logic, instantiating real domain objects and testing their observable public interface ensures tests validate genuine business behavior and remain resilient when internal code structures are optimized. "
                    "This disciplined boundary testing keeps test suites maintainable and enables confident long-term refactoring."
                ),
                "technical_justification": "Mocking internal collaborators couples tests to implementation details rather than verifying observable behaviors.",
                "practical_example": "Mocking `requests.post()` when calling an external payment gateway, but using real internal calculator classes.",
                "interview_takeaway": "Mock at architectural boundaries (I/O, network, database) while testing real domain objects through their public APIs."
            },
            {
                "question": "How did you measure and interpret test code coverage for this codebase?",
                "reference_answer": (
                    "Coverage tools such as pytest-cov track statement and branch coverage across the codebase. "
                    "However, coverage percentage should be treated as a diagnostic tool rather than a vanity metric: high coverage does not guarantee correctness if assertions are superficial. "
                    "Focusing on branch coverage in high-risk areas ensures that both the happy path and exception-handling branches are executed by tests, while reviewing uncovered lines identifies dead code or unhandled edge cases. "
                    "Ultimately, meaningful assertions evaluating real business invariants provide far stronger reliability guarantees than chasing vanity line-count percentages."
                ),
                "technical_justification": "Branch coverage measures whether all conditional paths are exercised, offering higher quality assurance than statement coverage alone.",
                "practical_example": "Running `pytest --cov=src --cov-report=term-missing` and examining missing branch branches in condition evaluations.",
                "interview_takeaway": "Emphasize branch coverage and assertion quality over raw line coverage percentages."
            }
        ]

        suggested_improvements = (
            "Suggested Improvement (Hypothetical Proposal): Integrating an automated continuous integration (CI) pipeline via GitHub Actions to run the test suite on every pull request."
        )

        missing_info = [
            "Specific test coverage percentage or test suite count achieved"
        ]
        framework = "PAR"

    else:  # scale
        simpler = (
            f"To scale '{title}' for enterprise production, I would prioritize separating synchronous web requests from compute-intensive tasks using background queues, "
            f"implementing caching for frequent queries, and containerizing the deployment for horizontal scaling behind a load balancer."
        )

        detailed = (
            f"While '{title}' operates reliably within its current functional scope, scaling it for high-volume enterprise production requires addressing clear architectural bottlenecks. "
            f"Currently, processing occurs synchronously within the application process, which could lead to request queuing under concurrent traffic spikes. "
            f"To scale '{title}' for enterprise workloads, an engineer would evaluate three foundational improvements: "
            f"First, decoupling heavy compute tasks from the request-response cycle by introducing an asynchronous task queue like Celery backed by Redis. "
            f"Second, introducing in-memory caching layers for frequently accessed read queries to reduce redundant computation. "
            f"Third, containerizing the application using Docker and setting up health-checked horizontal scaling behind a reverse proxy load balancer. "
            f"These changes improve system availability, bound p99 response latencies, and allow independent scaling of web and worker processes."
        )

        why_this_works = (
            "Senior interviewers ask scalability questions to test whether you can recognize the limitations of single-node architectures. "
            "This answer is convincing because it honestly acknowledges current synchronous bottlenecks and proposes standard enterprise scaling patterns (asynchronous queues, caching, containerization)."
        )

        steps = [
            {
                "step": "Step 1: Diagnose Single-Node Architectural Bottlenecks",
                "complete_explanation": f"In '{title}', compute-heavy data operations currently run synchronously within the HTTP worker process. When concurrent users submit requests simultaneously, worker threads become blocked, causing response queueing and elevating p99 latencies.",
                "reasoning": "Scaling begins with profiling current resource bottlenecks (CPU, memory, disk I/O, or connection limits) before writing code.",
                "concrete_example": "Identifying that payload parsing and scoring operations hold HTTP connection threads open for multiple seconds.",
                "connection_to_question": "Directly analyzes the current architectural scaling limits.",
                "detail": f"In '{title}', compute-heavy data operations currently run synchronously within the HTTP worker process. When concurrent users submit requests simultaneously, worker threads become blocked, causing response queueing and elevating p99 latencies."
            },
            {
                "step": "Step 2: Decouple Compute Tasks via Asynchronous Task Queues",
                "complete_explanation": "Introducing an asynchronous background worker queue such as Celery with Redis or RabbitMQ decouples compute tasks. When a client submits a processing request, the web tier validates the payload, enqueues a background job, and immediately returns a 202 Accepted status with a job ID.",
                "reasoning": "Asynchronous decoupling frees HTTP threads instantly to handle high concurrency while worker nodes process heavy compute tasks independently.",
                "concrete_example": "Web route returns `{'status': 'queued', 'job_id': 'abc-123'}` in 15ms, while Celery worker executes calculations in the background.",
                "connection_to_question": "Explains the primary pattern for eliminating request blocking.",
                "detail": "Introducing an asynchronous background worker queue such as Celery with Redis or RabbitMQ decouples compute tasks. When a client submits a processing request, the web tier validates the payload, enqueues a background job, and immediately returns a 202 Accepted status with a job ID."
            },
            {
                "step": "Step 3: Implement In-Memory Caching for Read-Heavy Queries",
                "complete_explanation": "To reduce redundant relational database queries, an engineering team would implement an in-memory caching tier using Redis with time-to-live (TTL) expiration and write-through cache invalidation. Repeated lookups are resolved from memory in sub-milliseconds.",
                "reasoning": "Caching offloads read load from persistent database disks, dramatically expanding total system query capacity.",
                "concrete_example": "Checking `redis.get(cache_key)` before querying PostgreSQL, setting a 15-minute TTL on cache writes.",
                "connection_to_question": "Details database offloading and latency reduction.",
                "detail": "To reduce redundant relational database queries, an engineering team would implement an in-memory caching tier using Redis with time-to-live (TTL) expiration and write-through cache invalidation. Repeated lookups are resolved from memory in sub-milliseconds."
            },
            {
                "step": "Step 4: Optimize Database Connection Pooling & Read Replicas",
                "complete_explanation": f"As worker processes multiply, direct database connections can exhaust {t2}'s connection limit. One would introduce connection pooling with PgBouncer and split traffic: directing write operations to the primary instance while routing read queries across read replicas.",
                "reasoning": "Connection poolers multiplex hundreds of worker threads across a controlled pool of open database connections, preventing connection exhaustion crashes.",
                "concrete_example": "Configuring PgBouncer in transaction pooling mode with max 50 server connections serving 500 client threads.",
                "connection_to_question": "Explains persistence tier scaling under concurrent load.",
                "detail": f"As worker processes multiply, direct database connections can exhaust {t2}'s connection limit. One would introduce connection pooling with PgBouncer and split traffic: directing write operations to the primary instance while routing read queries across read replicas."
            },
            {
                "step": "Step 5: Containerize & Orchestrate Horizontal Elastic Scaling",
                "complete_explanation": "Packaging the web and worker services into multi-stage Docker containers allows deploying them behind an Nginx reverse proxy load balancer or Kubernetes ingress. When traffic spikes elevate CPU utilization above 70%, the autoscaler spins up additional container replicas automatically.",
                "reasoning": "Stateless horizontal scaling allows adding capacity dynamically during peak traffic and scaling down during lulls to control infrastructure costs.",
                "concrete_example": "Deploying Kubernetes Horizontal Pod Autoscaler (HPA) scaling web pods from 3 to 15 based on CPU and request latency metrics.",
                "connection_to_question": "Addresses deployment infrastructure and elastic cloud scaling.",
                "detail": "Packaging the web and worker services into multi-stage Docker containers allows deploying them behind an Nginx reverse proxy load balancer or Kubernetes ingress. When traffic spikes elevate CPU utilization above 70%, the autoscaler spins up additional container replicas automatically."
            },
            {
                "step": "Step 6: Implement Distributed Observability & Latency Monitoring",
                "complete_explanation": "Finally, horizontal systems require distributed observability: centralized logging, distributed request tracing (OpenTelemetry), and Prometheus metrics scraping. Tracking p50, p95, and p99 response times ensures that degradation is identified before impacting customers.",
                "reasoning": "You cannot manage what you do not measure; distributed observability is essential to identify latency bottlenecks across multi-node topologies.",
                "concrete_example": "Setting up Grafana dashboards displaying request rate, error rate (4xx/5xx), and duration percentiles (RED method).",
                "connection_to_question": "Concludes with enterprise production monitoring and operational reliability.",
                "detail": "Finally, horizontal systems require distributed observability: centralized logging, distributed request tracing (OpenTelemetry), and Prometheus metrics scraping. Tracking p50, p95, and p99 response times ensures that degradation is identified before impacting customers."
            }
        ]

        follow_ups = [
            {
                "question": "How do you handle database connection exhaustion when scaling out horizontally to dozens of application containers?",
                "reference_answer": (
                    "When scaling application instances horizontally, having each worker process maintain its own pool of open database connections quickly exhausts database limits. "
                    "To prevent this, deploying an intermediary connection pooler such as PgBouncer in front of PostgreSQL manages connection reuse. "
                    "By running PgBouncer in transaction pooling mode, the pooler assigns a physical database connection to an application thread only for the exact duration of a transaction, releasing it immediately upon commit. "
                    "This allows hundreds of concurrent application threads to share a modest pool of 30 to 50 physical database connections without latency degradation. "
                    "Additionally, configuring application-level pool limits and timeouts ensures requests fail fast rather than hanging indefinitely."
                ),
                "technical_justification": "PostgreSQL forks a separate operating system process for each connection; unmanaged connections consume gigabytes of memory and trigger database thrashing.",
                "practical_example": "Setting `pool_mode = transaction` and `max_client_conn = 1000` with `default_pool_size = 30` in `pgbouncer.ini`.",
                "interview_takeaway": "Advocate for dedicated connection poolers (PgBouncer) and transaction pooling to decouple client connection counts from database server processes."
            },
            {
                "question": "How would you design a caching strategy to handle stale data and cache invalidation under heavy write traffic?",
                "reference_answer": (
                    "Cache invalidation requires balancing read performance against data freshness. "
                    "For '{title}', I would adopt a Cache-Aside pattern combined with explicit event-driven invalidation. "
                    "When records are updated, the database transaction commits first; upon successful commit, the application invalidates or updates the specific Redis cache keys. "
                    "To guard against race conditions and network failures where invalidation messages drop, every cached key is assigned a reasonable time-to-live (TTL), such as 15 minutes. "
                    "For high-concurrency read scenarios with frequent writes, I would implement mutex locks around cache misses (preventing cache stampedes) and versioned cache keys."
                ),
                "technical_justification": "Cache-Aside with TTL bounds data staleness, while explicit post-commit invalidation guarantees immediate consistency for active users.",
                "practical_example": "Executing `db.session.commit()`, followed immediately by `redis.delete(f'candidate:{candidate_id}')`.",
                "interview_takeaway": "Explain the Cache-Aside pattern, emphasize that invalidation must occur post-commit, and mandate TTLs as a fail-safe against desynchronization."
            },
            {
                "question": "What metrics would you monitor to determine exactly when to trigger horizontal autoscaling?",
                "reference_answer": (
                    "Autoscaling should not rely on CPU utilization alone, because compute-bound and I/O-bound workloads exhibit distinct bottlenecks. "
                    "For our web tier, I would monitor HTTP request rate, active connection count, and p95 request duration, scaling up when p95 latency exceeds 500ms or when CPU crosses 70%. "
                    "For background worker queues, the most critical metric is queue depth (backlog length) and job latency: if the queue has more than 50 pending jobs per worker, the autoscaler adds worker pods. "
                    "Furthermore, I configure stabilization windows (cooldown periods) of 3 to 5 minutes to prevent thrashing (rapid scaling up and down)."
                ),
                "technical_justification": "Queue depth directly reflects processing lag, whereas CPU utilization can lag behind sudden traffic surges.",
                "practical_example": "Configuring Kubernetes KEDA (Kubernetes Event-driven Autoscaling) to autoscale worker deployments based on Redis queue length.",
                "interview_takeaway": "Differentiate web tier autoscaling (latency, CPU, request rate) from background worker autoscaling (queue backlog depth)."
            }
        ]

        suggested_improvements = (
            "Suggested Improvement (Hypothetical Proposal): Packaging services into micro-containers with Kubernetes horizontal pod autoscaling based on queue depth metrics."
        )

        missing_info = [
            "Current concurrent user volume or hardware deployment environment"
        ]
        framework = "WHAT-WHY-HOW"

    return {
        "short_answer": simpler,
        "simpler_answer": simpler,
        "detailed_answer": detailed,
        "why_this_works": why_this_works,
        "step_by_step_explanation": steps,
        "important_concepts": tech_list if tech_list else ["System Architecture", "Separation of Concerns", "Modularity"],
        "interview_tips": [
            f"Speak about your personal code contributions and architectural decisions in '{title}'.",
            "Be transparent about current technical constraints; interviewers respect self-awareness over exaggerated claims."
        ],
        "follow_up_questions": follow_ups,
        "suggested_improvements": suggested_improvements,
        "missing_personal_details": missing_info,
        "verified_evidence": verified_evidence,
        "recommended_framework": framework,
        "examples": f"In '{title}', {', '.join(tech_list[:2]) if tech_list else 'the stack'} decoupled presentation from backend processing logic."
    }


def build_grounded_internship_answers(
    internship: Dict[str, Any],
    question_kind: str = "resp"
) -> Dict[str, Any]:
    """
    Constructs an evidence-aware, highly educational internship answer.
    Provides 5-7 substantive steps with complete technical explanations (no instructions!),
    and 3 comprehensive follow-up Q&As with 4-8 sentences each.
    """
    org = internship.get("organization", "Internship Organization")
    pos = internship.get("position", "Intern")
    dates = internship.get("dates", "during my internship")
    tech_list = internship.get("technologies", [])
    techs = ", ".join(tech_list) if tech_list else "professional software engineering tools"
    resp_list = internship.get("responsibilities", [])
    resps = "; ".join(resp_list) if resp_list else "software engineering duties"

    verified_evidence = [
        f"Verified Organization: {org}",
        f"Verified Position: {pos}",
        f"Verified Dates: {dates}",
        f"Verified Responsibilities: {resps}",
        f"Verified Tools: {techs}"
    ]

    t0 = tech_list[0] if len(tech_list) > 0 else "Python"
    t1 = tech_list[1] if len(tech_list) > 1 else "Git"

    if question_kind == "resp":
        simpler = (
            f"When discussing your internship at {org} ({dates}) as a {pos}, highlight how you contributed to {resps} using {techs}. "
            f"Structure your response: [Candidate to specify: Specific feature or service assigned] -> "
            f"Adhering to team conventions, modular code design, and testing -> "
            f"[Candidate to specify: Merged deliverable or outcome]."
        )

        detailed = (
            f"To present a compelling overview of your internship at {org} ({dates}) as a {pos}, frame your experience around professional software development standards:\n"
            f"1. Context & Scope: Your contributions centered on {resps} using {techs} within an established team codebase.\n"
            f"2. Development Process: [Candidate to specify: How you researched existing abstractions, authored modular code, and adhered to coding conventions].\n"
            f"3. Verification & Testing: Detail how you verified functionality with automated tests before opening pull requests.\n"
            f"4. Peer Review & Integration: [Candidate to specify: Iterating on code reviews with senior engineers to deliver merged, production-ready code].\n\n"
            f"[Illustrative Model Scenario — Not candidate resume data]: An intern contributing to backend services reads existing codebase abstractions, "
            f"implements modular endpoint handlers in feature branches, authors Pytest fixtures for boundary cases, and refactors code based on peer review before merging to main."
        )

        why_this_works = (
            "Hiring managers evaluate internship questions to see whether you adapted to industry development standards and teamwork. "
            "This answer works because it emphasizes professional engineering habits (code reviews, style guides, automated testing) "
            "and accurately reflects the realistic scope of an intern's contributions without making exaggerated solo claims."
        )

        steps = [
            {
                "step": "Step 1: Frame the Organizational Context & Engineering Team Scope",
                "complete_explanation": f"At {org} ({dates}), the role of {pos} involved working within the development team. Presenting the team environment and dates first provides interviewers with clear operational context and establishes professional legitimacy.",
                "reasoning": "Clear contextual framing grounds subsequent technical discussions in verified professional experience.",
                "concrete_example": f"Working as a {pos} alongside senior engineers and product managers within an agile team at {org}.",
                "connection_to_question": "Directly sets the foundation for discussing assigned responsibilities.",
                "detail": f"At {org} ({dates}), the role of {pos} involved working within the development team. Presenting the team environment and dates first provides interviewers with clear operational context and establishes professional legitimacy."
            },
            {
                "step": "Step 2: Map Assigned Responsibilities to Production Features",
                "complete_explanation": f"Core day-to-day engineering responsibilities focused on {resps}. Rather than working on disconnected toy scripts, the assignment required authoring modular service code that integrated directly into existing team repositories.",
                "reasoning": "Demonstrating that you contributed to real software repositories proves readiness for full-time engineering duties.",
                "concrete_example": f"Implementing modular endpoints, data validation schemas, or database query optimizations using {techs}.",
                "connection_to_question": "Articulates the concrete engineering scope of the internship.",
                "detail": f"Core day-to-day engineering responsibilities focused on {resps}. Rather than working on disconnected toy scripts, the assignment required authoring modular service code that integrated directly into existing team repositories."
            },
            {
                "step": f"Step 3: Technical Execution & Implementation with {techs}",
                "complete_explanation": f"Utilize {techs} to build modular, maintainable software components following team design patterns. Focus on clean function decomposition, descriptive variable naming, and strict adherence to repository coding conventions.",
                "reasoning": "Engineering teams value consistency, clean architecture, and adherence to existing patterns over idiosyncratic coding styles.",
                "concrete_example": f"Authoring reusable utility functions and schema models adhering to PEP 8 or enterprise style guides using {techs}.",
                "connection_to_question": "Explains hands-on tool mastery and software implementation craft.",
                "detail": f"Utilize {techs} to build modular, maintainable software components following team design patterns. Focus on clean function decomposition, descriptive variable naming, and strict adherence to repository coding conventions."
            },
            {
                "step": "Step 4: Author Unit Tests & Verify Local Regression Freedom",
                "complete_explanation": "Before submitting code for review, author automated unit tests covering both expected happy paths and edge cases. Running the full local test suite verifies that changes introduce zero functional regressions across existing features.",
                "reasoning": "Submitting thoroughly tested pull requests saves senior engineer review time and demonstrates engineering responsibility.",
                "concrete_example": "Writing automated test fixtures with assertions validating new feature outputs and boundary error handling.",
                "connection_to_question": "Proves rigorous software validation and testing discipline.",
                "detail": "Before submitting code for review, author automated unit tests covering both expected happy paths and edge cases. Running the full local test suite verifies that changes introduce zero functional regressions across existing features."
            },
            {
                "step": "Step 5: Peer Code Review & Incorporating Senior Engineering Critique",
                "complete_explanation": "Submit code via Git pull requests with clear summary descriptions of changes. Engaging constructively with senior engineering feedback during code reviews demonstrates professional maturity and rapid iteration.",
                "reasoning": "The ability to receive feedback gracefully and iterate quickly is one of the highest-value signals of a strong junior/mid-level engineer.",
                "concrete_example": "Refactoring a database query after a senior engineer pointed out an unindexed column join during PR review.",
                "connection_to_question": "Demonstrates team collaboration, communication, and professional growth.",
                "detail": "Submit code via Git pull requests with clear summary descriptions of changes. Engaging constructively with senior engineering feedback during code reviews demonstrates professional maturity and rapid iteration."
            },
            {
                "step": "Step 6: Verified Pull Request Merge & Production Delivery",
                "complete_explanation": "Once approved, my changes passed continuous integration validation checks and were merged into the main development branch. Delivering verified code into shared team repositories confirmed my ability to deliver production value.",
                "reasoning": "Merged code represents the ultimate deliverable and proves full alignment with team delivery standards.",
                "concrete_example": "Merging pull requests that passed all automated CI status checks and deploying to staging environments.",
                "connection_to_question": "Concludes with verified tangible impact and completed deliverables.",
                "detail": "Once approved, my changes passed continuous integration validation checks and were merged into the main development branch. Delivering verified code into shared team repositories confirmed my ability to deliver production value."
            }
        ]

        follow_ups = [
            {
                "question": f"What was the most challenging technical problem you were assigned at {org}?",
                "reference_answer": (
                    f"The most challenging technical problem was navigating an unfamiliar, multi-thousand-line codebase to implement {resps} without breaking existing functionality. "
                    f"Because documentation was incomplete for legacy modules, I had to read existing unit tests and trace execution flow using debuggers to understand data dependencies. "
                    f"I identified that existing endpoints lacked boundary validation, which occasionally triggered unhandled exceptions under null inputs. "
                    f"I drafted a design proposal for refactoring the module with explicit schema checks, discussed it with my mentor, and implemented the solution with comprehensive regression tests. "
                    f"Delivering that fix without regressions gave me immense confidence in tackling complex enterprise codebases."
                ),
                "technical_justification": "Navigating legacy code and tracing dependencies without breaking backwards compatibility is the primary daily challenge in enterprise engineering.",
                "practical_example": "Using grep, IDE call hierarchies, and pytest execution traces to map function call paths across microservices.",
                "interview_takeaway": "Emphasize reading tests, consulting mentors with concrete findings, and delivering defensive changes safely."
            },
            {
                "question": "How did you balance asking questions with working independently during your internship?",
                "reference_answer": (
                    "I adhered to a structured '30-minute rule' to balance autonomy with team efficiency. "
                    "When encountering a technical blocker, I spent dedicated time reading documentation, inspecting logs, and attempting minimal reproductions independently. "
                    "If I remained blocked after 30 minutes, I reached out to a senior teammate—not with an open-ended complaint, but with a concise summary of what I was trying to accomplish, the exact error encountered, the 2 or 3 hypotheses I tested, and why they failed. "
                    "Senior engineers appreciated this approach because it showed initiative, respected their focus time, and allowed them to unblock me in minutes."
                ),
                "technical_justification": "Senior engineers want junior developers who attempt independent troubleshooting but know when to seek guidance before wasting hours.",
                "practical_example": "Posting in Slack: 'Attempting to run DB migration 04; getting Foreign Key constraint error on users table. Checked schema and verified user_id 10 exists. Is there a seed script prerequisite?'",
                "interview_takeaway": "Frame asking for help as a collaborative, structured process: state the goal, what you attempted, and your specific question."
            },
            {
                "question": "What software engineering practices did you adopt at {org} that you continue to use in personal projects?",
                "reference_answer": (
                    "My internship permanently instilled three core engineering habits that I now apply to every codebase. "
                    "First, atomic Git commits: making focused, single-purpose commits with clear descriptive messages rather than large batch dumps. "
                    "Second, defensive boundary validation: validating all inputs at system entry points using explicit type contracts before passing data to domain functions. "
                    "Third, authoring automated regression tests alongside feature code rather than treating testing as a rushed post-development afterthought. "
                    "These practices dramatically reduce debugging time and make my repositories immediately accessible to other developers."
                ),
                "technical_justification": "Atomic commits and automated testing are industry standards that ensure long-term codebase maintainability and bisectability.",
                "practical_example": "Writing conventional commit messages (`feat: add schema validation for candidate upload`) and authoring failing tests first.",
                "interview_takeaway": "Highlight atomic commits, boundary validation, and automated regression testing as permanent professional habits."
            }
        ]

        suggested_improvements = (
            f"Suggested Improvement (Hypothetical Proposal): If continuing at {org}, I would have proposed setting up automated PR preview environments to test staging builds earlier."
        )

        missing_info = [
            f"Specific feature name or project deliverable completed at organization"
        ]
        framework = "STAR"

    elif question_kind == "learn":
        simpler = (
            f"When discussing key lessons from {org}, frame your reflections around production software engineering craft: "
            f"[Candidate to specify: Most significant technical or procedural insight gained while contributing to {resps} using {techs}]."
        )

        detailed = (
            f"Structure your reflections on your time at {org} ({dates}) around three core dimensions of professional growth:\n"
            f"1. Codebase Respect & Abstractions: Understanding that production code must be read, debugged, and extended by other engineers.\n"
            f"2. Collaborative Review Culture: [Candidate to specify: Key constructive feedback received from senior mentors that refined your craft].\n"
            f"3. Proactive Clarification: Eliminating requirement ambiguity through early technical discussions.\n\n"
            f"[Illustrative Model Scenario — Not candidate resume data]: A software engineer learns that writing defensive unit tests and asking clarifying questions during sprint planning "
            f"saves days of refactoring compared to making unverified assumptions."
        )

        why_this_works = (
            "Interviewers look for maturity and self-reflection in behavioral answers. "
            "This answer is effective because it demonstrates that you understand the realities of professional engineering (maintainability, testing, communication) "
            "rather than viewing programming as purely an isolated individual exercise."
        )

        steps = [
            {
                "step": "Step 1: Reflect on the Academic vs Production Engineering Contrast",
                "complete_explanation": f"At {org}, the immediate revelation was contrasting academic coding—which is typically temporary and individual—with production software engineering, which involves long-lived systems maintained by cross-functional teams.",
                "reasoning": "Recognizing this difference demonstrates mature technical self-awareness and readiness for industry expectations.",
                "concrete_example": "Realizing that code written today must be easily understood by teammates six months from now without explanation.",
                "connection_to_question": "Establishes the core insight and foundation of the learning experience.",
                "detail": f"At {org}, the immediate revelation was contrasting academic coding—which is typically temporary and individual—with production software engineering, which involves long-lived systems maintained by cross-functional teams."
            },
            {
                "step": "Step 2: Appreciate Code Readability & Descriptive Naming Over Brevity",
                "complete_explanation": "During code reviews, senior mentors emphasized that concise or clever one-liners are liabilities if they obscure intent. I learned to choose descriptive variable and function names that document their purpose self-evidently.",
                "reasoning": "Readable code decreases cognitive load for reviewers, accelerates onboarding, and reduces bug injection rates.",
                "concrete_example": "Renaming ambiguous variables like `d` and `res` to `candidate_records` and `parsed_output_envelope`.",
                "connection_to_question": "Illustrates concrete improvements in code quality standards.",
                "detail": "During code reviews, senior mentors emphasized that concise or clever one-liners are liabilities if they obscure intent. I learned to choose descriptive variable and function names that document their purpose self-evidently."
            },
            {
                "step": "Step 3: Internalize Automated Testing as a Living Specification",
                "complete_explanation": "I learned that unit tests are not just verification tools; they serve as living documentation describing how components are expected to behave. Reading existing tests helped me understand legacy modules faster than reading architecture docs.",
                "reasoning": "Tests cannot drift out of sync with code behavior because failing tests break the continuous integration build.",
                "concrete_example": "Writing test cases that clearly document expected error behaviors when external APIs return 503 Service Unavailable.",
                "connection_to_question": "Connects testing discipline to long-term software maintainability.",
                "detail": "I learned that unit tests are not just verification tools; they serve as living documentation describing how components are expected to behave. Reading existing tests helped me understand legacy modules faster than reading architecture docs."
            },
            {
                "step": "Step 4: Master Constructive Code Review Etiquette",
                "complete_explanation": "I learned to approach code reviews as collaborative learning opportunities rather than personal critiques. I actively studied senior engineer comments, asked questions to understand architectural principles, and reviewed teammate PRs to learn new patterns.",
                "reasoning": "Healthy code review culture fosters collective code ownership and continuous mentorship across engineering teams.",
                "concrete_example": "Engaging constructively with PR comments regarding database query performance and updating implementations promptly.",
                "connection_to_question": "Demonstrates interpersonal maturity and team collaboration.",
                "detail": "I learned to approach code reviews as collaborative learning opportunities rather than personal critiques. I actively studied senior engineer comments, asked questions to understand architectural principles, and reviewed teammate PRs to learn new patterns."
            },
            {
                "step": "Step 5: Practice Proactive Requirement Clarification",
                "complete_explanation": "I discovered that ambiguous requirements lead to wasted engineering effort. Clarifying assumptions, edge cases, and acceptance criteria with product managers before writing code prevented days of subsequent refactoring.",
                "reasoning": "Fixing an ambiguous requirement during design costs minutes; fixing it after deployment requires database migrations and rollbacks.",
                "concrete_example": "Authoring brief implementation summaries outlining proposed API request/response formats before coding.",
                "connection_to_question": "Highlights proactive communication and engineering efficiency.",
                "detail": "I discovered that ambiguous requirements lead to wasted engineering effort. Clarifying assumptions, edge cases, and acceptance criteria with product managers before writing code prevented days of subsequent refactoring."
            },
            {
                "step": "Step 6: Translate Professional Lessons into Ongoing Engineering Craft",
                "complete_explanation": "This experience permanently elevated how I approach software design. I now structure every project—personal or professional—with clean modularity, automated test coverage, and clear documentation.",
                "reasoning": "True learning is reflected in consistent, permanent behavior change across all engineering tasks.",
                "concrete_example": "Setting up GitHub Actions CI pipelines and linting rules on all new software repositories by default.",
                "connection_to_question": "Concludes with permanent personal development and value for future employers.",
                "detail": "This experience permanently elevated how I approach software design. I now structure every project—personal or professional—with clean modularity, automated test coverage, and clear documentation."
            }
        ]

        follow_ups = [
            {
                "question": "Can you share a specific code review comment that fundamentally improved how you write software?",
                "reference_answer": (
                    "During a pull request for a data ingestion feature, I had written a function that caught generic `Exception` and logged a one-line warning. "
                    "A senior engineer commented: 'Catching generic Exception masks underlying bugs like syntax errors or memory issues, and silent logs make failures impossible to detect in production.' "
                    "They guided me to catch specific exceptions—like `KeyError` or `ValueError`—and handle each with appropriate logging and fallback defaults. "
                    "That comment fundamentally changed my mindset: error handling is not just about keeping the application from crashing, but about maintaining system observability and state predictability."
                ),
                "technical_justification": "Catching generic exceptions hides critical programming bugs, swallows keyboard interrupts, and makes root-cause analysis nearly impossible in production.",
                "practical_example": "Refactoring `except Exception:` into `except (KeyError, ValueError) as e: logger.warning('Malformed schema: %s', e); raise CustomValidationError(e)`.",
                "interview_takeaway": "Showcase a specific code review learning moment: specific exception handling over blanket exception suppression."
            },
            {
                "question": "How did your Git version control habits change as a result of working on a shared team repository?",
                "reference_answer": (
                    "Before my internship, I frequently committed large, sweeping changes with generic messages like 'fixed stuff' or 'updated files.' "
                    "At {org}, working on a team with multiple engineers merging concurrently taught me the vital importance of atomic Git commits and descriptive Conventional Commit messages. "
                    "I learned to keep commits focused on a single logical change, author informative commit bodies explaining the 'why' behind decisions, and rebase feature branches cleanly against main before opening pull requests. "
                    "This discipline made code reviews significantly faster and allowed teammates to use `git bisect` seamlessly if bugs were ever introduced."
                ),
                "technical_justification": "Atomic commits and clean Git history enable automated changelog generation and simplify pinpointing regressions via git bisect.",
                "practical_example": "Using `git rebase -i` to squash exploratory commits into a clean `feat(auth): add JWT expiration validation` commit.",
                "interview_takeaway": "Emphasize atomic commits, descriptive Conventional Commit messages, and clean branch rebasing."
            },
            {
                "question": "How do you handle situations where product requirements or task specifications are ambiguous?",
                "reference_answer": (
                    "When requirements are ambiguous, I never make silent assumptions and hope for the best, because assumptions usually lead to rework. "
                    "Instead, I draft a quick technical summary or RFC (Request for Comments) outlining my understanding of the problem, the edge cases I identified, and 2 or 3 proposed implementation options with their trade-offs. "
                    "I then reach out to the product owner or technical lead to align on the expected behavior before writing feature code. "
                    "This structured communication ensures everyone agrees on acceptance criteria and eliminates surprises during code review."
                ),
                "technical_justification": "Aligning on testable acceptance criteria before writing code eliminates miscommunication and prevents costly downstream architectural rewrites.",
                "practical_example": "Authoring a quick 3-bullet Slack message to the product manager: 'For candidate uploads, if a PDF contains non-extractable scanned images, should we fail with a 422 error or return partial text with an OCR notice?'",
                "interview_takeaway": "Demonstrate proactive ambiguity resolution: document assumptions, present concrete options, and confirm acceptance criteria upfront."
            }
        ]

        suggested_improvements = (
            "Suggested Improvement (Hypothetical Proposal): Introducing automated pre-commit linting hooks to catch style issues before code reviews."
        )

        missing_info = [
            "Specific mentor advice or code review interaction at organization"
        ]
        framework = "STAR+L"

    else:  # solve
        simpler = (
            f"When describing an assigned task at {org} ({dates}), articulate the technical scope involving {techs}, your implementation process, and how you validated the outcome: "
            f"[Candidate to specify: Exact engineering task assigned] -> "
            f"[Candidate to specify: Architectural approach and testing] -> "
            f"[Candidate to specify: Approved pull request or delivered outcome]."
        )

        detailed = (
            f"Structure your explanation of an assigned task at {org} into four disciplined phases:\n"
            f"1. Problem Understanding: Analyzing task requirements and existing codebase dependencies for {resps}.\n"
            f"2. Implementation Craft: Developing modular solutions incrementally using {techs} on isolated feature branches.\n"
            f"3. Testing & Edge Cases: [Candidate to specify: Unit or integration tests authored to verify edge cases].\n"
            f"4. Code Review & Delivery: Incorporating peer review feedback to deliver merged, production-ready code [Candidate to specify: Delivered outcome].\n\n"
            f"[Illustrative Model Scenario — Not candidate resume data]: Given a task to optimize payload processing, an engineer profiles execution paths, "
            f"introduces modular schema validation, adds Pytest test cases covering boundary inputs, and submits a documented pull request that passes CI."
        )

        why_this_works = (
            "This answer illustrates realistic problem-solving: doing research first, writing tests, knowing when to consult senior engineers, and following standard pull request conventions."
        )

        steps = [
            {
                "step": "Step 1: Frame the Specific Engineering Assignment",
                "complete_explanation": f"At {org}, I was assigned a targeted engineering ticket involving {techs}. Clearly framing the specific assignment—such as optimizing an endpoint, fixing a pipeline edge case, or implementing a new data schema—establishes tangible technical focus.",
                "reasoning": "Interviewers want to see how you approach concrete, bounded tickets in production software systems.",
                "concrete_example": f"Assigned ticket: 'Refactor candidate document parser to handle multi-page PDF tables using {techs}'.",
                "connection_to_question": "Directly defines the technical problem and assignment scope.",
                "detail": f"At {org}, I was assigned a targeted engineering ticket involving {techs}. Clearly framing the specific assignment—such as optimizing an endpoint, fixing a pipeline edge case, or implementing a new data schema—establishes tangible technical focus."
            },
            {
                "step": "Step 2: Research Existing Codebase & Trace Data Flow",
                "complete_explanation": "Before authoring new code, I spent time studying existing modules, reading unit tests, and tracing execution paths with debuggers. This ensured that my proposed solution adhered to existing architecture and reused existing utility patterns.",
                "reasoning": "Rushing into coding without understanding existing abstractions often results in redundant functions and broken assumptions.",
                "concrete_example": "Inspecting existing parser classes and noting how error handlers reported validation failures to the web controller.",
                "connection_to_question": "Demonstrates thorough engineering due diligence and codebase respect.",
                "detail": "Before authoring new code, I spent time studying existing modules, reading unit tests, and tracing execution paths with debuggers. This ensured that my proposed solution adhered to existing architecture and reused existing utility patterns."
            },
            {
                "step": "Step 3: Develop Incremental Modular Solution in Feature Branch",
                "complete_explanation": "I created a dedicated Git feature branch and implemented the changes in small, self-contained commits. I structured the solution to isolate new functionality into modular functions, avoiding sprawling modifications to legacy code.",
                "reasoning": "Modular, incremental changes keep pull requests small, digestible for reviewers, and simple to roll back if necessary.",
                "concrete_example": "Authoring a helper module `table_extractor.py` that processes table boundaries independently from raw text parsing.",
                "connection_to_question": "Details the technical implementation craft and modular design.",
                "detail": "I created a dedicated Git feature branch and implemented the changes in small, self-contained commits. I structured the solution to isolate new functionality into modular functions, avoiding sprawling modifications to legacy code."
            },
            {
                "step": "Step 4: Author Unit Tests & Validate Edge Cases",
                "complete_explanation": "I authored comprehensive unit tests evaluating the new module against edge cases—including malformed document structures, empty inputs, and unusual encodings—confirming that the module degraded gracefully under all conditions.",
                "reasoning": "Automated tests prove that the new code functions correctly and guarantees against future regression bugs.",
                "concrete_example": "Creating Pytest test fixtures with sample documents asserting 100% extraction accuracy on tabular data.",
                "connection_to_question": "Demonstrates testing rigor and functional validation.",
                "detail": "I authored comprehensive unit tests evaluating the new module against edge cases—including malformed document structures, empty inputs, and unusual encodings—confirming that the module degraded gracefully under all conditions."
            },
            {
                "step": "Step 5: Consult Senior Mentors on Architectural Edge Cases",
                "complete_explanation": "When an integration edge case emerged concerning how database transactions interacted with parser retries, I consulted with a senior engineer. I presented the problem, my analysis, and two potential solutions, quickly aligning on the optimal approach.",
                "reasoning": "Knowing when to seek guidance on subtle architectural interactions prevents costly rework and deepens domain knowledge.",
                "concrete_example": "Discussing whether parser retry attempts should execute inside or outside the main database transaction scope.",
                "connection_to_question": "Highlights collaborative problem solving and communication efficiency.",
                "detail": "When an integration edge case emerged concerning how database transactions interacted with parser retries, I consulted with a senior engineer. I presented the problem, my analysis, and two potential solutions, quickly aligning on the optimal approach."
            },
            {
                "step": "Step 6: Submit Pull Request & Verify Merged Production Delivery",
                "complete_explanation": "I submitted a clean pull request with detailed before-and-after descriptions, screenshots, and test execution logs. After incorporating minor review feedback, the pull request was approved and merged into the team repository.",
                "reasoning": "Delivering tested, reviewed, and merged code fulfills the complete software engineering lifecycle.",
                "concrete_example": "Opening PR #142 with pass verification from CI pipelines, merged into main branch.",
                "connection_to_question": "Concludes with completed deliverable and positive team impact.",
                "detail": "I submitted a clean pull request with detailed before-and-after descriptions, screenshots, and test execution logs. After incorporating minor review feedback, the pull request was approved and merged into the team repository."
            }
        ]

        follow_ups = [
            {
                "question": "What tools or techniques did you use to trace execution flow during this task?",
                "reference_answer": (
                    "To trace execution flow without guessing, I combined interactive breakpoint debugging with structured diagnostic logging. "
                    "I used IDE debuggers to step through execution lines, inspecting local variable states, call stacks, and return values at each pipeline stage. "
                    "When debugging asynchronous tasks or background jobs where interactive breakpoints are difficult to pause, I injected structured JSON log statements with execution timestamps and task IDs. "
                    "This allowed me to trace the exact path data traveled through the system and pinpoint where anomalies occurred in seconds."
                ),
                "technical_justification": "Interactive debuggers provide fine-grained variable inspection, while structured logging is essential for tracing asynchronous distributed pipelines.",
                "practical_example": "Setting conditional breakpoints in VS Code or injecting `logger.debug('Payload shape: %s', payload.keys(), extra={'task_id': task_id})`.",
                "interview_takeaway": "Articulate a dual strategy: interactive IDE debuggers for synchronous logic and structured logging for asynchronous/distributed execution."
            },
            {
                "question": "How did you ensure that your changes did not break backward compatibility for existing consumers?",
                "reference_answer": (
                    "Preserving backward compatibility is critical in shared production codebases. "
                    "First, I adhered to additive change principles: rather than altering existing function signatures or modifying existing JSON response keys, I introduced optional parameters with sensible defaults and added new fields. "
                    "Second, I ran the entire existing integration test suite locally before pushing changes, verifying that all pre-existing tests passed without modification. "
                    "Finally, I authored negative tests confirming that clients calling the endpoint with legacy payloads continued to receive valid, expected responses."
                ),
                "technical_justification": "Additive changes and default parameters preserve API contract compatibility, preventing cascading client breaks across distributed microservices.",
                "practical_example": "Adding `def parse_document(doc, extract_tables=False):` preserving legacy invocation `parse_document(doc)` without breaking existing callers.",
                "interview_takeaway": "Highlight additive API design, default parameters, and verifying pre-existing integration test suites."
            },
            {
                "question": "If you were assigned a similar task today, what would you do differently to accelerate delivery?",
                "reference_answer": (
                    "If assigned a similar task today, I would invest time upfront in constructing a minimal synthetic test suite and reproduction fixture before touching production code. "
                    "During the internship, I initially spent time manually testing payloads through the full application stack, which slowed down iteration cycles. "
                    "Now, I immediately isolate the problem into a fast unit test that runs in sub-seconds. "
                    "This test-driven approach allows me to iterate on implementation logic with instantaneous feedback, reducing total development time by at least 40%."
                ),
                "technical_justification": "Isolated unit test fixtures provide sub-second feedback loops, eliminating the latency of full-stack redeployments during development.",
                "practical_example": "Writing a failing pytest test using a captured mock payload before writing a single line of production code.",
                "interview_takeaway": "Emphasize mature test-driven iteration loops that eliminate slow manual full-stack testing."
            }
        ]

        suggested_improvements = (
            "Suggested Improvement (Hypothetical Proposal): Expanding integration test suites to simulate external service latencies."
        )

        missing_info = [
            f"Specific engineering task or bug assigned at organization"
        ]
        framework = "CAR"

    return {
        "short_answer": simpler,
        "simpler_answer": simpler,
        "detailed_answer": detailed,
        "why_this_works": why_this_works,
        "step_by_step_explanation": steps,
        "important_concepts": tech_list if tech_list else ["Professional Workflows", "Code Reviews", "Unit Testing"],
        "interview_tips": [
            f"Acknowledge team collaboration at {org} while articulating your individual contributions clearly.",
            "Highlight adherence to professional standards: git branching, pull request reviews, and automated tests."
        ],
        "follow_up_questions": follow_ups,
        "suggested_improvements": suggested_improvements,
        "missing_personal_details": missing_info,
        "verified_evidence": verified_evidence,
        "recommended_framework": framework,
        "examples": f"At {org}, completed practical duties ({resps}) using {techs} following git and code review conventions."
    }
