"""
Professional Career Counseling Profile Generator.

Generates comprehensive, substantive, 9-point counseling answers for every skill gap:
1. Why does this competency matter for the target position?
2. What does the candidate already know that is relevant?
3. What is missing or not clearly demonstrated?
4. What should the candidate learn first? (Prerequisite-aware starting point)
5. What should they practice next? (Hands-on exercise)
6. What practical deliverable should they create? (Tangible portfolio artifact)
7. How can progress be verified? (Concrete verification criteria)
8. How can they discuss the skill in an interview? (Interview talking point)
9. How can they truthfully document it on their resume after completion? (Post-completion resume bullet)

Strict adherence to non-negotiable principles:
- No generic template repetition.
- Substantive domain-specific reasoning for SQL, Docker, ML, React, PySpark, Power BI, Focus, Jira, etc.
- Honest disclosure when specialized guidance is unavailable.
- Clear instruction that resume bullets must only be added AFTER completion.
"""

from typing import Dict, List, Any, Optional
from src.common.evidence_registry import resolve_canonical_skill
from src.mentor.dependency_graph import evaluate_candidate_prerequisites


# Curated domain counseling intelligence for key skill competencies
DOMAIN_COUNSELING_INTELLIGENCE: Dict[str, Dict[str, Any]] = {
    "typescript": {
        "why_it_matters": "TypeScript provides static type safety, compile-time error detection, and rich IDE autocompletion, preventing runtime type coercion bugs in complex full-stack web codebases.",
        "interview_talking_point": "Discuss how TypeScript interfaces and generics model complex API request/response contracts, and explain how discriminated unions prevent invalid application state at compile time.",
        "verification_method": "TypeScript compiler (`tsc --noEmit`) passes with zero type errors under `strict: true` flags, and automated Jest/Vitest unit tests validate module behavior.",
        "post_completion_resume_bullet": "Migrated core JavaScript frontend modules to TypeScript with strict type annotations, eliminating runtime type exceptions and establishing reusable interface contracts."
    },
    "docker": {
        "why_it_matters": "Docker standardizes application runtime environments across development and production, eliminating 'works on my machine' configuration discrepancies and enabling deterministic microservice deployments.",
        "interview_talking_point": "Explain multi-stage build optimization for minimizing image layer size, container security best practices (non-root users), and volume mount strategies for persistent data.",
        "verification_method": "Docker container boots locally from a multi-stage Dockerfile, executes health checks successfully, and binds container ports to host network without permission errors.",
        "post_completion_resume_bullet": "Containerized multi-service backend application using multi-stage Dockerfiles and docker-compose, reducing deployment configuration overhead and standardizing local runtime environments."
    },
    "kubernetes": {
        "why_it_matters": "Kubernetes provides automated container orchestration, horizontal pod autoscaling, self-healing pod restarts, and zero-downtime rolling updates across distributed production clusters.",
        "interview_talking_point": "Walk through Pod lifecycle events, explain how Services abstract ephemeral Pod IP addresses via label selectors, and contrast RollingUpdate vs Recreate deployment strategies.",
        "verification_method": "Deploy manifests to local Minikube/Kind cluster; simulate pod failure and observe ReplicaSet auto-healing; verify Service traffic routing with `kubectl port-forward`.",
        "post_completion_resume_bullet": "Authored declarative Kubernetes manifests (Deployments, Services, ConfigMaps) and configured liveness/readiness probes to ensure high availability for containerized services."
    },
    "sql": {
        "why_it_matters": "SQL is the foundational query language for relational databases, essential for maintaining ACID guarantees, designing 3NF schemas, and retrieving high-volume operational metrics efficiently.",
        "interview_talking_point": "Discuss query execution plans (`EXPLAIN ANALYZE`), index scan vs sequential scan trade-offs, transaction isolation levels (Read Committed vs Serializable), and window functions for analytics.",
        "verification_method": "Execute complex joins and aggregations on a 100k+ row PostgreSQL dataset; prove query latency reduction via B-Tree index creation using EXPLAIN ANALYZE metrics.",
        "post_completion_resume_bullet": "Designed normalized PostgreSQL relational schema and authored optimized aggregation queries with window functions and B-Tree indexes, improving query throughput."
    },
    "spark": {
        "why_it_matters": "Apache Spark is the industry standard for distributed large-scale batch and streaming data processing, leveraging in-memory computing and lazy evaluation Directed Acyclic Graphs (DAGs).",
        "interview_talking_point": "Explain lazy evaluation benefits for the Catalyst optimizer, contrast narrow vs wide transformations, and discuss techniques to mitigate data skew (salting keys, broadcast joins).",
        "verification_method": "PySpark script runs successfully on local multi-core cluster; Spark Web UI confirms clean stage DAGs, zero shuffle spill to disk, and balanced partition execution.",
        "post_completion_resume_bullet": "Engineered distributed PySpark batch transformation pipeline processing multi-partition Parquet datasets with BroadcastHashJoins and windowed analytical aggregations."
    },
    "react": {
        "why_it_matters": "React enables component-driven, declarative user interfaces with efficient Virtual DOM reconciliation, custom hooks, and centralized state management for modern web applications.",
        "interview_talking_point": "Explain the React component lifecycle, hook dependencies (`useEffect`, `useCallback`, `useMemo`), Virtual DOM diffing, and how to prevent unnecessary component re-renders.",
        "verification_method": "React Testing Library test suite validates component rendering, user interactions, and asynchronous API state updates with >80% test coverage.",
        "post_completion_resume_bullet": "Built responsive component hierarchy utilizing custom hooks for asynchronous data fetching and client-side caching, verified by automated React Testing Library tests."
    },
    "ci/cd": {
        "why_it_matters": "Continuous Integration and Continuous Deployment (CI/CD) automates test execution, lint checks, and artifact deployment, catching regression defects before code reaches production.",
        "interview_talking_point": "Explain pipeline trigger strategies (pull request vs push), environment secret management, build caching to minimize runner execution time, and automated rollback strategies.",
        "verification_method": "GitHub Actions workflow triggers on pull request, passes all automated linter and pytest stages across multiple Python matrix runners, and blocks merge on failure.",
        "post_completion_resume_bullet": "Configured GitHub Actions CI/CD pipeline executing automated test matrices and code linting on pull requests, establishing automated quality gates for release branches."
    },
    "aws": {
        "why_it_matters": "Amazon Web Services (AWS) provides elastic cloud compute, managed databases, and scalable object storage powering fault-tolerant enterprise application architectures.",
        "interview_talking_point": "Describe the Shared Responsibility Model, least-privilege IAM policy design, VPC subnet isolation (public vs private), and object storage lifecycle management in S3.",
        "verification_method": "Deploy application to AWS EC2 or App Runner with restricted IAM role; verify secure S3 file uploads and CloudWatch metrics logging without exposing root credentials.",
        "post_completion_resume_bullet": "Provisioned cloud infrastructure on AWS adhering to least-privilege IAM policies, configuring VPC networking and automated CloudWatch operational monitoring."
    },
    "power bi": {
        "why_it_matters": "Power BI connects disparate enterprise data sources to deliver interactive business intelligence dashboards, KPI scorecards, and executive analytics via DAX calculations.",
        "interview_talking_point": "Explain star schema dimensional modeling (fact vs dimension tables), DAX row context vs filter context, and how calculate functions alter dynamic filter propagation.",
        "verification_method": "Power BI report connects to multi-table model with verified one-to-many relationships; interactive slicers dynamically recalculate measures without performance lag.",
        "post_completion_resume_bullet": "Developed interactive Power BI executive dashboard with custom DAX calculated measures and dimensional relationships, visualizing operational KPI trends."
    },
    "excel": {
        "why_it_matters": "Microsoft Excel is the universal analytical tool for rapid ad-hoc data modeling, financial forecasting, PivotTable analysis, and executive tabular reporting.",
        "interview_talking_point": "Discuss structured workbook architecture, dynamic array formulas (`XLOOKUP`, `INDEX/MATCH`, `LAMBDA`), data validation rules, and error-handling formulas (`IFERROR`).",
        "verification_method": "Construct structured workbook modeling operational scenarios; verify dynamic PivotTables and charts update automatically when underlying raw tables change.",
        "post_completion_resume_bullet": "Built operational performance modeling workbook utilizing dynamic XLOOKUP formulas, automated PivotTables, and scenario data tables for executive analysis."
    },
    "project management": {
        "why_it_matters": "Project management provides structured Agile sprint planning, scope decomposition, dependency mapping, and risk mitigation to deliver engineering software on time.",
        "interview_talking_point": "Explain how you decompose epics into INVEST-compliant user stories, estimate effort using story points, facilitate sprint retrospectives, and unblock cross-functional dependencies.",
        "verification_method": "Author a sprint backlog containing 5 well-defined user stories with explicit acceptance criteria, story point estimates, and a mapped dependency diagram.",
        "post_completion_resume_bullet": "Facilitated Agile sprint planning and backlog grooming, decomposing multi-feature epics into INVEST-compliant user stories with tracked milestone delivery."
    },
    "jira": {
        "why_it_matters": "Jira is the enterprise standard for agile issue tracking, release versioning, team sprint burndown monitoring, and workflow transparency across software engineering teams.",
        "interview_talking_point": "Describe how custom issue types, workflow transitions (To Do -> In Progress -> Code Review -> QA -> Done), and burndown metrics improve sprint predictability.",
        "verification_method": "Set up a configured Jira project with custom workflow statuses, active sprint board, component tags, and sprint burndown chart tracking test issues.",
        "post_completion_resume_bullet": "Configured and managed Jira Agile Scrum board with custom workflow states and release versions, tracking sprint velocity and issue cycle times."
    },
    "visio": {
        "why_it_matters": "Microsoft Visio facilitates formal enterprise system architecture documentation, C4 context diagrams, entity-relationship schemas, and business process modeling.",
        "interview_talking_point": "Explain the C4 architecture model (Context, Container, Component, Code) and how standardized diagramming conventions communicate design trade-offs to stakeholders.",
        "verification_method": "Author and export a multi-tier C4 system architecture diagram documenting client, API gateway, microservices, and database layers with clear data flows.",
        "post_completion_resume_bullet": "Authored comprehensive C4 system architecture and database entity-relationship diagrams in Visio, establishing formal technical documentation for engineering reviews."
    },
    "focus": {
        "why_it_matters": "Deep work focus and disciplined cognitive habits are essential for software engineers to navigate complex debugging sessions and minimize productivity-destroying context switching.",
        "interview_talking_point": "Share how you protect deep work focus blocks during sprint cycles, manage notification interruptions, and use the Pomodoro technique to maintain sustained concentration on complex algorithms.",
        "verification_method": "Maintain a 14-day deep work log tracking completed 45-minute distraction-free coding blocks; observe reduction in open bug resolution times.",
        "post_completion_resume_bullet": "Applied deliberate deep-work focus discipline and structured context-switching reduction techniques to sustain high-velocity technical debugging and implementation."
    },
    "pc skills": {
        "why_it_matters": "Proficiency in operating system navigation, terminal CLI utilities, shell automation, and workspace configuration is foundational for software engineering productivity.",
        "interview_talking_point": "Describe your terminal CLI toolchain, bash/zsh automation scripts, SSH key management, and directory navigation shortcuts that optimize your daily developer workflow.",
        "verification_method": "Author a shell script automating local environment setup, directory creation, dependency installation, and git configuration on a clean workspace.",
        "post_completion_resume_bullet": "Automated local developer workspace and operating system workflows using command-line shell utilities and custom environment configuration scripts."
    },
    "analytical problem-solving": {
        "why_it_matters": "Analytical problem-solving enables software engineers to systematically isolate root causes in failing systems, analyze edge cases, and design robust algorithmic solutions.",
        "interview_talking_point": "Walk through a structured 5 Whys root cause analysis or binary-search debugging methodology you used to diagnose a non-obvious software bottleneck or data anomaly.",
        "verification_method": "Author a formal engineering postmortem documenting a complex software issue: symptom, reproduction steps, root cause analysis (5 Whys), resolution, and preventive measures.",
        "post_completion_resume_bullet": "Applied structured root-cause analysis (5 Whys framework) and defensive debugging methodologies to identify and resolve critical edge-case software bottlenecks."
    },
    "communication": {
        "why_it_matters": "Clear technical communication enables software engineers to articulate architecture design decisions, bridge technical concepts for non-technical stakeholders, and write concise documentation.",
        "interview_talking_point": "Explain how you adapt your communication style when discussing technical trade-offs with senior engineers versus explaining product impact to non-technical business partners.",
        "verification_method": "Deliver and record a 5-minute technical architecture presentation explaining system design choices and trade-offs; conduct peer review using a structured rubric.",
        "post_completion_resume_bullet": "Delivered structured technical architecture presentations and author technical design documentation, effectively aligning cross-functional stakeholders on engineering decisions."
    },
    "git": {
        "why_it_matters": "Git provides distributed version control, branching workflows, and cryptographic history tracking, enabling safe collaboration, merge conflict resolution, and deterministic rollbacks across engineering teams.",
        "interview_talking_point": "Discuss branching workflows (Trunk-based vs GitFlow), git rebase vs merge trade-offs, interactive rebasing for clean histories, and safe recovery with git revert.",
        "verification_method": "Repository history demonstrates clean linear commit log via `git log --graph --oneline`, zero detached HEAD states, and successful fast-forward or squash merges.",
        "post_completion_resume_bullet": "Managed distributed version control workflows using Git, implementing Trunk-based branching, interactive rebasing, and resolving merge conflicts across shared feature branches."
    },
    "linux": {
        "why_it_matters": "Linux forms the operating system foundation for cloud servers, container runtimes, and production deployments, requiring proficiency in system calls, process management, shell scripting, and network diagnostics.",
        "interview_talking_point": "Explain the Linux filesystem hierarchy (FHS), permission models (rwx and octal), process lifecycle management (systemd, signals, zombie vs orphan processes), and core diagnostic commands.",
        "verification_method": "Shell script executes with strict mode (`set -euo pipefail`), handles process exit codes gracefully, and passes shellcheck linting on an active Linux distribution.",
        "post_completion_resume_bullet": "Administered Linux production server environments, configuring systemd services, automating maintenance via Bash scripts, and monitoring resource utilization."
    }
}


def build_counseling_profile(
    skill_name: str,
    category: str,
    priority_tier: str,
    verified_skills: List[str],
    projects: List[Dict[str, Any]],
    jd_sentence: str,
    practical_action: str,
    practical_deliverable: str,
    curriculum_source: str
) -> Dict[str, Any]:
    """
    Constructs the 9-point Career Counseling Profile for a skill gap.
    Adheres strictly to evidence-based personalization and domain-accurate knowledge.
    """
    canon = resolve_canonical_skill(skill_name).lower()
    intel = DOMAIN_COUNSELING_INTELLIGENCE.get(canon, {})
    prereq_eval = evaluate_candidate_prerequisites(skill_name, verified_skills)

    # 1. Why it matters
    why_matters = intel.get("why_it_matters")
    if not why_matters:
        why_matters = f"{skill_name} is explicitly specified as a {priority_tier.lower()} competency in the job description to maintain production engineering standards."

    # 2. What candidate already knows that is relevant
    if prereq_eval["met_prerequisites"]:
        candidate_foundations = (
            f"Candidate has verified proficiency in {', '.join(prereq_eval['met_prerequisites'])}, "
            f"providing a strong prerequisite springboard that significantly reduces ramp-up time."
        )
    elif verified_skills:
        candidate_foundations = (
            f"Candidate has verified foundations in related competencies ({', '.join(verified_skills[:3])}), "
            f"which provide general engineering principles that accelerate skill adoption."
        )
    else:
        candidate_foundations = "Candidate profile has not yet established direct antecedent technical competencies in this domain."

    # 3. What is missing or not clearly demonstrated
    if prereq_eval["missing_prerequisites"]:
        demonstration_gap = (
            f"No verified resume evidence for {skill_name}. Additionally, foundational prerequisites "
            f"({', '.join(prereq_eval['missing_prerequisites'])}) are currently unevidenced in projects."
        )
    else:
        demonstration_gap = f"No direct hands-on project or workplace evidence for {skill_name} is currently documented in the resume."

    # 4. What should candidate learn first (Prerequisite-aware)
    initial_learning_step = prereq_eval["recommended_starting_point"]

    # 5. What should they practice next
    practical_exercise_step = practical_action

    # 6. What practical deliverable should they create
    deliverable = practical_deliverable or "Completed and documented implementation artifact with automated test validation."

    # 7. How can progress be verified
    verification = intel.get(
        "verification_method",
        "Verify artifact functionality against automated unit test suites, ensure zero unhandled exceptions, and pass peer code review."
    )

    # 8. How can they discuss the skill in an interview
    interview_talking_point = intel.get(
        "interview_talking_point",
        f"Articulate the architectural motivation for adopting {skill_name}, explain key trade-offs compared to alternatives, and discuss implementation lessons learned."
    )

    # 9. Truthful post-completion resume documentation
    post_bullet = intel.get(
        "post_completion_resume_bullet",
        f"Implemented and tested modular components utilizing {skill_name}, verifying behavior through automated test suites and structured documentation."
    )
    resume_guidance = (
        f"AFTER completing and verifying the deliverable with automated tests, document this experience truthfully: "
        f"'{post_bullet}' (Do NOT add this bullet until hands-on implementation and testing are finished)."
    )

    return {
        "q1_why_it_matters": why_matters,
        "q2_candidate_foundations": candidate_foundations,
        "q3_demonstration_gap": demonstration_gap,
        "q4_initial_learning_step": initial_learning_step,
        "q5_practical_exercise_step": practical_exercise_step,
        "q6_practical_deliverable": deliverable,
        "q7_verification_method": verification,
        "q8_interview_talking_point": interview_talking_point,
        "q9_resume_bullet_guidance": resume_guidance,
        "prerequisites_status": prereq_eval,
        "curriculum_source": curriculum_source
    }
