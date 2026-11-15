"""
Step-by-Step Learning Roadmap & Study Plan Generator Module.
Generates skill-specific 7-stage roadmaps:
- Stage 1: Understand the fundamentals
- Stage 2: Study essential concepts
- Stage 3: Complete guided exercises
- Stage 4: Build a practical mini-project
- Stage 5: Test your understanding
- Stage 6: Prepare interview questions (linking directly to Phase 8 Interview Studio)
- Stage 7: Document genuine skills in your resume

Also generates realistic study schedules for 3, 7, 14, or 30 day timelines.
"""

from typing import Dict, List, Any, Optional
from .resource_mapper import get_learning_resources_for_skill
from .project_recommender import recommend_project_for_skill
from .skill_curricula import get_curriculum_for_skill, build_skill_action_plan


SKILL_SPECIFIC_ROADMAPS: Dict[str, Dict[str, Any]] = {
    "docker": {
        "domain": "DevOps & Containerization",
        "why_it_matters": "Docker provides isolated, reproducible runtimes ensuring software behaves identically across developer laptops, CI pipelines, and production servers.",
        "prerequisites": ["Basic Linux Command Line", "REST API Development"],
        "stages": [
            {"stage_num": 1, "name": "Fundamentals", "task": "Learn container terminology: images, containers, daemon, and registries."},
            {"stage_num": 2, "name": "Essential Concepts", "task": "Understand container isolation via Linux namespaces and cgroups, layering, and caching."},
            {"stage_num": 3, "name": "Guided Exercises", "task": "Write a multi-stage Dockerfile for a Python web service; practice `docker build`, `run`, and port mapping."},
            {"stage_num": 4, "name": "Practical Mini-Project", "task": "Orchestrate an API and PostgreSQL database with Docker Compose and persistent named volumes."},
            {"stage_num": 5, "name": "Test Understanding", "task": "Verify container logs, inspect running container processes, and benchmark image layer footprint."},
            {"stage_num": 6, "name": "Interview Preparation", "task": "Practice explaining differences between VMs and containers, and how to optimize Docker image size in Interview Studio."},
            {"stage_num": 7, "name": "Resume Documentation", "task": "Add a bullet point to your project: 'Containerized multi-service backend with Docker Compose, reducing environment setup time.'"}
        ],
        "estimated_hours": 12
    },
    "kubernetes": {
        "domain": "Cloud Orchestration",
        "why_it_matters": "Kubernetes is the industry standard for automating deployment, scaling, and operational management of containerized workloads.",
        "prerequisites": ["Docker Containerization", "Basic Networking (TCP/IP, DNS)"],
        "stages": [
            {"stage_num": 1, "name": "Fundamentals", "task": "Understand cluster architecture: Control plane (API Server, etcd, Scheduler) and Worker nodes (Kubelet, Kube-proxy)."},
            {"stage_num": 2, "name": "Essential Concepts", "task": "Study foundational API primitives: Pods, ReplicaSets, Deployments, and Services."},
            {"stage_num": 3, "name": "Guided Exercises", "task": "Set up a local Minikube cluster; deploy an application and expose it via NodePort or ClusterIP."},
            {"stage_num": 4, "name": "Practical Mini-Project", "task": "Author declarative YAML manifests for Deployment, Service, ConfigMap, and Ingress routing."},
            {"stage_num": 5, "name": "Test Understanding", "task": "Simulate pod failure by deleting a pod and observing how the ReplicaSet automatically self-heals."},
            {"stage_num": 6, "name": "Interview Preparation", "task": "Prepare questions on Pod lifecycle, Service discovery, and rolling update strategies in Interview Studio."},
            {"stage_num": 7, "name": "Resume Documentation", "task": "Document: 'Configured Kubernetes Deployment manifests and Service networking for local microservice testing.'"}
        ],
        "estimated_hours": 16
    },
    "sql": {
        "domain": "Relational Databases",
        "why_it_matters": "Relational databases store business-critical structured data; mastering SQL is essential for transactional consistency and analytical querying.",
        "prerequisites": ["Data Structures (Arrays, Tables)", "Basic Relational Algebra"],
        "stages": [
            {"stage_num": 1, "name": "Fundamentals", "task": "Learn relational model principles: entities, primary keys, foreign keys, and referential integrity."},
            {"stage_num": 2, "name": "Essential Concepts", "task": "Master ACID properties, transaction isolation levels, normalization (1NF to 3NF), and B-Tree indexes."},
            {"stage_num": 3, "name": "Guided Exercises", "task": "Write complex SQL queries using INNER/LEFT/FULL JOINs, GROUP BY, HAVING, and Window Functions (ROW_NUMBER, RANK)."},
            {"stage_num": 4, "name": "Practical Mini-Project", "task": "Design a normalized database schema in PostgreSQL; run EXPLAIN ANALYZE to compare query plans with and without indexes."},
            {"stage_num": 5, "name": "Test Understanding", "task": "Identify and eliminate SQL injection vulnerabilities by converting dynamic queries into parameterized statements."},
            {"stage_num": 6, "name": "Interview Preparation", "task": "Practice DBMS and SQL questions in Interview Studio: ACID definitions, WHERE vs HAVING, and index trade-offs."},
            {"stage_num": 7, "name": "Resume Documentation", "task": "Document: 'Architected relational PostgreSQL schema with secondary indexes, optimizing query performance for analytical reporting.'"}
        ],
        "estimated_hours": 10
    },
    "aws": {
        "domain": "Cloud Infrastructure",
        "why_it_matters": "AWS provides scalable on-demand compute, storage, and networking that power modern enterprise web applications.",
        "prerequisites": ["Basic Networking (CIDR, Subnets, Ports)", "Linux Command Line"],
        "stages": [
            {"stage_num": 1, "name": "Fundamentals", "task": "Understand core cloud primitives: Global infrastructure (Regions, Availability Zones) and IAM security."},
            {"stage_num": 2, "name": "Essential Concepts", "task": "Study foundational services: EC2 (compute), S3 (object storage), RDS (managed relational DB), and VPC (virtual networking)."},
            {"stage_num": 3, "name": "Guided Exercises", "task": "Launch an EC2 virtual machine, configure security group ingress rules, and attach an IAM execution role."},
            {"stage_num": 4, "name": "Practical Mini-Project", "task": "Deploy a containerized application to AWS ECS or App Runner connected to an S3 bucket for media assets."},
            {"stage_num": 5, "name": "Test Understanding", "task": "Set up CloudWatch metric alarms for CPU utilization and verify automated alerting."},
            {"stage_num": 6, "name": "Interview Preparation", "task": "Review Cloud Computing questions in Interview Studio: IaaS vs PaaS vs SaaS, and shared responsibility security models."},
            {"stage_num": 7, "name": "Resume Documentation", "task": "Document: 'Deployed scalable containerized service to AWS cloud infrastructure with IAM least-privilege policies.'"}
        ],
        "estimated_hours": 14
    },
    "ci/cd": {
        "domain": "DevOps & Automation",
        "why_it_matters": "Automated CI/CD pipelines prevent regression bugs from reaching production and accelerate developer delivery cycles.",
        "prerequisites": ["Git Version Control", "Unit Testing Frameworks (Pytest/JUnit)"],
        "stages": [
            {"stage_num": 1, "name": "Fundamentals", "task": "Learn continuous integration concepts: automated builds, linters, and pull-request verification."},
            {"stage_num": 2, "name": "Essential Concepts", "task": "Study pipeline syntax: workflow triggers, matrix runners, environment secrets, and artifact storage."},
            {"stage_num": 3, "name": "Guided Exercises", "task": "Create a `.github/workflows/test.yml` file that runs linting (flake8/black) and Pytest across Python 3.10 and 3.11."},
            {"stage_num": 4, "name": "Practical Mini-Project", "task": "Build an end-to-end pipeline that runs regression tests, builds a Docker image, and generates a coverage badge."},
            {"stage_num": 5, "name": "Test Understanding", "task": "Submit a PR with a failing unit test to verify that the CI gate correctly blocks merging."},
            {"stage_num": 6, "name": "Interview Preparation", "task": "Prepare to explain your CI/CD workflow, branch protection rules, and testing strategies in Interview Studio."},
            {"stage_num": 7, "name": "Resume Documentation", "task": "Document: 'Engineered automated GitHub Actions CI/CD workflows, executing automated test suites on every pull request.'"}
        ],
        "estimated_hours": 8
    }
}


def generate_skill_roadmap(
    skill_name: str,
    priority_tier: str = "Mandatory",
    candidate_evidence: Optional[Dict[str, Any]] = None,
    daily_hours: float = 2.0,
    timeline_days: int = 14
) -> Dict[str, Any]:
    """
    Generates a structured, educational 7-stage learning roadmap for a specific skill.
    Uses domain-specific and skill-specific curricula for high-demand technologies,
    or generates an honest general engineering curriculum explicitly marked if unverified.
    Provides complete explanations, concrete examples, exercises, and deliverables.
    """
    norm = skill_name.lower().strip()
    resources = get_learning_resources_for_skill(skill_name)
    project_rec = recommend_project_for_skill(skill_name)

    # Fetch curriculum from comprehensive domain & skill curricula
    curriculum = get_curriculum_for_skill(skill_name)
    mini_proj = curriculum.get("mini_project")
    
    domain = curriculum.get("domain_display") or curriculum.get("domain_key", "Core Engineering Competency")
    why_it_matters = curriculum.get("why_it_matters", f"Mastering {skill_name} is essential to fulfill target job responsibilities.")
    prerequisites = curriculum.get("prerequisites", ["Computer Science Fundamentals", "Practical Programming Experience"])
    
    # 7 Canonical stages enriched with educational depth from curriculum
    canonical_names = [
        "Fundamentals",
        "Essential Concepts",
        "Guided Exercises",
        "Practical Mini-Project",
        "Test Understanding",
        "Interview Preparation",
        "Resume Documentation"
    ]
    raw_curriculum_stages = curriculum.get("stages", [])
    stages = []
    for idx in range(7):
        c_st = raw_curriculum_stages[idx] if idx < len(raw_curriculum_stages) else {}
        base_task = c_st.get("task", f"Study {canonical_names[idx]} for {skill_name}.")
        if idx == 5 and "Interview Studio" not in base_task:
            base_task = f"Practice conceptual and problem-solving interview questions relating to {skill_name} in Interview Studio. {base_task}"
        elif idx == 6 and "resume" not in base_task.lower():
            base_task = f"Document genuine, verified skills for {skill_name} in your resume bullets. {base_task}"
            
        stages.append({
            "stage_num": idx + 1,
            "name": canonical_names[idx],
            "curriculum_name": c_st.get("name", canonical_names[idx]),
            "task": base_task,
            "complete_explanation": c_st.get("complete_explanation", ""),
            "concrete_example": c_st.get("concrete_example", ""),
            "exercise": c_st.get("exercise", ""),
            "deliverable": c_st.get("deliverable", ""),
            "verification_method": c_st.get("verification_method", "")
        })

    est_hours = 12 if priority_tier == "Mandatory" else 8

    # Generate full 10-section action plan
    action_plan = build_skill_action_plan(
        skill_name=skill_name,
        priority_tier=priority_tier,
        candidate_evidence=candidate_evidence,
        daily_hours=daily_hours,
        timeline_days=timeline_days
    )

    # Augment practical project: enforce domain-accurate, logical relevance
    project_rec = build_logical_project_recommendation(
        skill_name=skill_name,
        priority_tier=priority_tier,
        candidate_evidence=candidate_evidence,
        mini_proj=mini_proj,
        curated_template=project_rec
    )

    return {
        "skill_name": curriculum.get("skill_name", skill_name),
        "priority_tier": priority_tier,
        "domain": domain,
        "domain_display": domain,
        "why_it_matters": why_it_matters,
        "prerequisites": prerequisites,
        "estimated_hours": est_hours,
        "stages": stages,
        "curriculum_stages": raw_curriculum_stages,
        "resources": resources,
        "recommended_project": project_rec,
        "is_verified_specialized": curriculum.get("is_verified_specialized", False),
        "curriculum_notice": curriculum.get("curriculum_notice"),
        "interview_prep": curriculum.get("interview_prep", []),
        "resume_evidence": curriculum.get("resume_evidence", {}),
        "action_plan": action_plan
    }


def build_logical_project_recommendation(
    skill_name: str,
    priority_tier: str = "Mandatory",
    candidate_evidence: Optional[Dict[str, Any]] = None,
    mini_proj: Optional[Dict[str, Any]] = None,
    curated_template: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs a domain-accurate, logically consistent project recommendation.
    Enforces strict rules:
    - Non-software skills (Excel, Communication, Agile/Scrum) NEVER recommend "services" or "APIs".
    - Software skills evaluate genuine relevance against candidate's primary project (e.g. Flask + Docker -> Containerization).
    - If no relevant candidate project exists or integration is illogical, recommends a standalone mini-project.
    - All recommendations are explicitly marked as future work.
    """
    clean_skill = (skill_name or "").strip()
    norm = clean_skill.lower()
    if isinstance(candidate_evidence, list):
        candidate_projects = candidate_evidence
    elif isinstance(candidate_evidence, dict):
        candidate_projects = candidate_evidence.get("projects") or []
    else:
        candidate_projects = []
    primary_proj = candidate_projects[0] if candidate_projects else {}
    primary_title = primary_proj.get("title") or primary_proj.get("project_title")
    primary_techs = [t.lower() for t in primary_proj.get("technologies", [])]
    primary_desc = primary_proj.get("description", "").lower()

    # Rule 1: Communication / Soft Skills
    if any(k in norm for k in ["communication", "presentation", "public speaking", "soft skill"]):
        if primary_title:
            return {
                "skill_name": clean_skill,
                "project_title": f"Technical Architecture & Walkthrough Presentation for '{primary_title}'",
                "title": f"Technical Architecture & Walkthrough Presentation for '{primary_title}'",
                "description": f"Prepare and deliver a structured technical slide presentation and recorded architectural walkthrough explaining system design choices, component trade-offs, and failure recovery for '{primary_title}'.",
                "architecture_pattern": "Technical Stakeholder Presentation & Structured Communication",
                "key_deliverables": [
                    f"Slide deck covering architecture, data flow, and trade-offs of '{primary_title}'",
                    "Recorded 5-minute technical walkthrough delivered using the PREP framework",
                    "Executive 1-page project summary written for non-technical stakeholders"
                ],
                "deliverables": [
                    f"Slide deck covering architecture, data flow, and trade-offs of '{primary_title}'",
                    "Recorded 5-minute technical walkthrough delivered using the PREP framework",
                    "Executive 1-page project summary written for non-technical stakeholders"
                ],
                "interview_talking_points": [
                    f"Articulate how you communicated complex technical decisions in '{primary_title}' to varied technical and non-technical stakeholders."
                ],
                "suggested_technologies": ["PREP Framework", "Slide Presentation", "Technical Writing"],
                "estimated_hours": 4,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }
        return {
            "skill_name": clean_skill,
            "project_title": "Technical Project Presentation & Architecture Walkthrough",
            "title": "Technical Project Presentation & Architecture Walkthrough",
            "description": "Prepare and deliver a structured 10-minute technical slide presentation and recorded architectural walkthrough explaining project design choices, trade-offs, and failure recovery.",
            "architecture_pattern": "Technical Stakeholder Presentation & Structured Communication",
            "key_deliverables": [
                "Structured slide deck covering Problem, Architecture, Trade-Offs, and Results",
                "Recorded 5-minute technical presentation delivered using the PREP framework",
                "Executive 1-page project summary written for non-technical stakeholders"
            ],
            "deliverables": [
                "Structured slide deck covering Problem, Architecture, Trade-Offs, and Results",
                "Recorded 5-minute technical presentation delivered using the PREP framework",
                "Executive 1-page project summary written for non-technical stakeholders"
            ],
            "interview_talking_points": ["Explain how you structure complex technical explanations under the PREP methodology."],
            "suggested_technologies": ["Technical Writing", "PREP Framework", "Slide Deck"],
            "estimated_hours": 4,
            "is_future_work": True,
            "status": "Recommended Future Enhancement"
        }

    # Rule 2: Excel / Spreadsheet Modeling
    if any(k in norm for k in ["excel", "spreadsheet", "sheets"]):
        if primary_title:
            return {
                "skill_name": clean_skill,
                "project_title": f"Structured Analytical Performance & KPI Model for '{primary_title}'",
                "title": f"Structured Analytical Performance & KPI Model for '{primary_title}'",
                "description": f"Construct a structured analytical workbook modeling performance metrics, latency benchmarks, and scenario variance inspired by '{primary_title}'.",
                "architecture_pattern": "Analytical Spreadsheet Modeling & Business Intelligence",
                "key_deliverables": [
                    f"Structured Excel data model tracking '{primary_title}' operational logs",
                    "Interactive PivotTable and PivotChart dashboard with slicers and variance indicators",
                    "Automated summary worksheet evaluating scenario sensitivities"
                ],
                "deliverables": [
                    f"Structured Excel data model tracking '{primary_title}' operational logs",
                    "Interactive PivotTable and PivotChart dashboard with slicers and variance indicators",
                    "Automated summary worksheet evaluating scenario sensitivities"
                ],
                "interview_talking_points": [
                    f"Explain how analytical spreadsheet modeling helped quantify performance metrics and variance for '{primary_title}'."
                ],
                "suggested_technologies": ["Microsoft Excel", "PivotTables", "Data Analysis"],
                "estimated_hours": 5,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }
        return {
            "skill_name": clean_skill,
            "project_title": "Analytical Performance & Financial Modeling Workbook",
            "title": "Analytical Performance & Financial Modeling Workbook",
            "description": "Construct a structured analytical spreadsheet model featuring dynamic formulas, PivotTables, scenario analysis, and executive KPI summary charts.",
            "architecture_pattern": "Analytical Spreadsheet Modeling & Business Intelligence",
            "key_deliverables": [
                "Dynamic data model using INDEX/MATCH, XLOOKUP, and nested logical formulas",
                "Interactive PivotTable and PivotChart dashboard with slicers and conditional formatting",
                "Automated summary worksheet evaluating scenario sensitivities and variance"
            ],
            "deliverables": [
                "Dynamic data model using INDEX/MATCH, XLOOKUP, and nested logical formulas",
                "Interactive PivotTable and PivotChart dashboard with slicers and conditional formatting",
                "Automated summary worksheet evaluating scenario sensitivities and variance"
            ],
            "interview_talking_points": ["Discuss how structured spreadsheet modeling provides rapid analytical validation."],
            "suggested_technologies": ["Microsoft Excel", "XLOOKUP", "PivotTables"],
            "estimated_hours": 5,
            "is_future_work": True,
            "status": "Recommended Future Enhancement"
        }

    # Rule 3: Project Management / Agile / Scrum / Jira / Trello
    if any(k in norm for k in ["project management", "jira", "trello", "agile", "scrum", "kanban"]):
        if primary_title:
            return {
                "skill_name": clean_skill,
                "project_title": f"Agile Delivery Backlog & Sprint Planning for '{primary_title}'",
                "title": f"Agile Delivery Backlog & Sprint Planning for '{primary_title}'",
                "description": f"Decompose future milestones for '{primary_title}' into an Agile sprint backlog with epics, user stories, acceptance criteria, and estimation story points.",
                "architecture_pattern": "Agile Product Backlog & Sprint Planning",
                "key_deliverables": [
                    f"Sprint backlog containing 10 user stories for '{primary_title}' with Gherkin acceptance criteria",
                    "Configured sprint board with WIP limits, estimation story points, and definition of done",
                    "Sprint retrospective summary analyzing development velocity and risk mitigation"
                ],
                "deliverables": [
                    f"Sprint backlog containing 10 user stories for '{primary_title}' with Gherkin acceptance criteria",
                    "Configured sprint board with WIP limits, estimation story points, and definition of done",
                    "Sprint retrospective summary analyzing development velocity and risk mitigation"
                ],
                "interview_talking_points": [
                    f"Describe how Agile backlog decomposition and sprint cadence kept development on '{primary_title}' structured and predictable."
                ],
                "suggested_technologies": ["Agile", "Jira", "Sprint Planning", "User Stories"],
                "estimated_hours": 4,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }
        return {
            "skill_name": clean_skill,
            "project_title": "Agile Sprint Backlog & Delivery Workflow Configuration",
            "title": "Agile Sprint Backlog & Delivery Workflow Configuration",
            "description": "Decompose a full-stack product initiative into an Agile sprint backlog with epics, user stories, acceptance criteria, and estimation story points.",
            "architecture_pattern": "Agile Product Backlog & Sprint Planning",
            "key_deliverables": [
                "Product backlog breakdown containing 10 user stories with Gherkin acceptance criteria",
                "Configured sprint board with WIP limits, estimation points, and definition of done",
                "Sprint retrospective summary analyzing velocity bottlenecks and mitigation steps"
            ],
            "deliverables": [
                "Product backlog breakdown containing 10 user stories with Gherkin acceptance criteria",
                "Configured sprint board with WIP limits, estimation points, and definition of done",
                "Sprint retrospective summary analyzing velocity bottlenecks and mitigation steps"
            ],
            "interview_talking_points": ["Explain how you write clear acceptance criteria and manage sprint velocity bottlenecks."],
            "suggested_technologies": ["Agile", "Jira", "Sprint Planning"],
            "estimated_hours": 4,
            "is_future_work": True,
            "status": "Recommended Future Enhancement"
        }

    # Rule 4: Docker / Containerization
    if any(k in norm for k in ["docker", "container"]):
        if primary_title and (any(t in primary_techs for t in ["python", "flask", "django", "fastapi", "react", "node", "javascript"]) or any(w in primary_desc for w in ["web", "api", "service", "backend"])):
            return {
                "skill_name": clean_skill,
                "project_title": f"Containerize '{primary_title}' with Docker & Docker Compose",
                "title": f"Containerize '{primary_title}' with Docker & Docker Compose",
                "description": f"Package the application and dependencies of '{primary_title}' into an optimized multi-stage Docker image and orchestrate service runtime with Docker Compose.",
                "architecture_pattern": "Containerized Service Architecture",
                "key_deliverables": [
                    f"Multi-stage Dockerfile optimizing image layer footprint for '{primary_title}'",
                    "docker-compose.yml orchestrating application service and persistent volumes",
                    "Container health checks and automated startup verification scripts"
                ],
                "deliverables": [
                    f"Multi-stage Dockerfile optimizing image layer footprint for '{primary_title}'",
                    "docker-compose.yml orchestrating application service and persistent volumes",
                    "Container health checks and automated startup verification scripts"
                ],
                "interview_talking_points": [
                    f"Explain how containerizing '{primary_title}' eliminated local environment discrepancy and accelerated automated testing."
                ],
                "suggested_technologies": [clean_skill, "Docker Compose", "Linux"],
                "estimated_hours": 6,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }

    # Rule 5: CI/CD / Continuous Integration
    if any(k in norm for k in ["ci/cd", "continuous integration", "github actions", "gitlab"]):
        if primary_title:
            return {
                "skill_name": clean_skill,
                "project_title": f"Automate Testing & Linting CI/CD Workflow for '{primary_title}'",
                "title": f"Automate Testing & Linting CI/CD Workflow for '{primary_title}'",
                "description": f"Author an automated GitHub Actions CI/CD workflow for '{primary_title}' executing automated test suites, linting, and build verification on every pull request.",
                "architecture_pattern": "Automated Build & Test Pipeline",
                "key_deliverables": [
                    f".github/workflows/ci.yml running pytest and linting on PRs for '{primary_title}'",
                    "Automated test coverage badge reporting and security scanning",
                    "Branch protection rules enforcing passing CI status before merging"
                ],
                "deliverables": [
                    f".github/workflows/ci.yml running pytest and linting on PRs for '{primary_title}'",
                    "Automated test coverage badge reporting and security scanning",
                    "Branch protection rules enforcing passing CI status before merging"
                ],
                "interview_talking_points": [
                    f"Describe how CI/CD automation prevented regressions and caught edge-case defects in '{primary_title}'."
                ],
                "suggested_technologies": [clean_skill, "GitHub Actions", "Pytest"],
                "estimated_hours": 5,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }

    # Rule 6: Spark / PySpark / Big Data
    if any(k in norm for k in ["spark", "pyspark", "hadoop", "big data"]):
        if primary_title and any(t in primary_techs for t in ["python", "pandas", "numpy", "data", "machine learning", "tensorflow", "scikit-learn"]):
            return {
                "skill_name": clean_skill,
                "project_title": f"PySpark Distributed Batch Transformation Pipeline for '{primary_title}' Datasets",
                "title": f"PySpark Distributed Batch Transformation Pipeline for '{primary_title}' Datasets",
                "description": f"Build a standalone PySpark batch processing pipeline scaling the data transformation and aggregation logic of '{primary_title}' across distributed cluster partitions.",
                "architecture_pattern": "Distributed In-Memory Batch Computing",
                "key_deliverables": [
                    f"PySpark batch processing pipeline transforming '{primary_title}' record schemas",
                    "BroadcastHashJoin execution benchmark reducing shuffle latency",
                    "Partitioned Parquet storage output with schema validation unit tests"
                ],
                "deliverables": [
                    f"PySpark batch processing pipeline transforming '{primary_title}' record schemas",
                    "BroadcastHashJoin execution benchmark reducing shuffle latency",
                    "Partitioned Parquet storage output with schema validation unit tests"
                ],
                "interview_talking_points": [
                    f"Articulate when and why transitioning data transformations to PySpark distributed computing is necessary."
                ],
                "suggested_technologies": ["Apache Spark", "PySpark", "Parquet"],
                "estimated_hours": 8,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }

    # Rule 7: Model Evaluation / Validation / Machine Learning / Computer Vision
    if any(k in norm for k in ["model evaluation", "validation", "cross-validation", "computer vision", "machine learning", "deep learning"]):
        if primary_title and (any(t in primary_techs for t in ["opencv", "tensorflow", "pytorch", "scikit-learn", "keras"]) or any(w in primary_desc for w in ["classification", "detection", "model", "prediction", "accuracy", "vision"])):
            return {
                "skill_name": clean_skill,
                "project_title": f"Rigorous Cross-Validation & Error Analysis Pipeline for '{primary_title}'",
                "title": f"Rigorous Cross-Validation & Error Analysis Pipeline for '{primary_title}'",
                "description": f"Enhance '{primary_title}' by implementing leakage-safe k-fold cross-validation, comprehensive error slice analysis, and threshold calibration.",
                "architecture_pattern": "Supervised ML Validation & Error Diagnosis",
                "key_deliverables": [
                    f"Leakage-free cross-validation pipeline with isolated preprocessing for '{primary_title}'",
                    "Error confusion matrix and slice analysis across challenging edge cases",
                    "Precision-Recall trade-off benchmarks and calibrated probability thresholds"
                ],
                "deliverables": [
                    f"Leakage-free cross-validation pipeline with isolated preprocessing for '{primary_title}'",
                    "Error confusion matrix and slice analysis across challenging edge cases",
                    "Precision-Recall trade-off benchmarks and calibrated probability thresholds"
                ],
                "interview_talking_points": [
                    f"Explain how rigorous validation and error analysis improved predictive reliability in '{primary_title}'."
                ],
                "suggested_technologies": [clean_skill, "Scikit-Learn", "Evaluation Metrics"],
                "estimated_hours": 8,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }

    # Rule 8: SQL / Relational Databases
    if any(k in norm for k in ["sql", "database", "postgres", "mysql"]):
        if primary_title:
            return {
                "skill_name": clean_skill,
                "project_title": f"Relational Schema Design & Query Optimization for '{primary_title}'",
                "title": f"Relational Schema Design & Query Optimization for '{primary_title}'",
                "description": f"Design a normalized 3NF relational PostgreSQL schema with secondary indexes to persist entities and benchmark query plans for '{primary_title}'.",
                "architecture_pattern": "Relational Persistence & Index Optimization",
                "key_deliverables": [
                    f"Normalized 3NF relational schema with foreign key constraints for '{primary_title}'",
                    "Optimized multi-table aggregation queries with Window Functions",
                    "EXPLAIN ANALYZE query plan benchmarks demonstrating index speedup"
                ],
                "deliverables": [
                    f"Normalized 3NF relational schema with foreign key constraints for '{primary_title}'",
                    "Optimized multi-table aggregation queries with Window Functions",
                    "EXPLAIN ANALYZE query plan benchmarks demonstrating index speedup"
                ],
                "interview_talking_points": [
                    f"Discuss how relational normalization and indexing guaranteed data integrity for '{primary_title}'."
                ],
                "suggested_technologies": [clean_skill, "PostgreSQL", "Database Indexing"],
                "estimated_hours": 6,
                "is_future_work": True,
                "status": "Recommended Future Enhancement"
            }

    # Rule 9: Curated mini_project or template fallback
    base_template = curated_template or mini_proj
    if base_template:
        t_title = base_template.get("title") or f"{clean_skill} Practical Project"
        t_desc = base_template.get("description") or f"A complete end-to-end implementation demonstrating core capabilities of {clean_skill}."
        t_dels = base_template.get("deliverables") or base_template.get("steps") or [
            f"Implement core functional module utilizing {clean_skill}",
            f"Author unit test suite validating behavior under edge cases",
            f"Document configuration parameters and architectural trade-offs"
        ]
        return {
            "skill_name": clean_skill,
            "project_title": t_title,
            "title": t_title,
            "description": t_desc,
            "architecture_pattern": "Modular Service Architecture",
            "key_deliverables": t_dels,
            "deliverables": t_dels,
            "interview_talking_points": [f"Explain engineering design choices and trade-offs made when implementing {clean_skill}."],
            "suggested_technologies": [clean_skill],
            "estimated_hours": base_template.get("estimated_hours", 8),
            "is_future_work": True,
            "status": "Recommended Future Enhancement"
        }

    # Rule 10: Standalone default
    return {
        "skill_name": clean_skill,
        "project_title": f"{clean_skill} Standalone Portfolio Implementation",
        "title": f"{clean_skill} Standalone Portfolio Implementation",
        "description": f"Build a tested, production-ready prototype demonstrating core principles and architectural patterns of {clean_skill}.",
        "architecture_pattern": "Modular Component Architecture",
        "key_deliverables": [
            f"Implement core functional module utilizing {clean_skill}",
            f"Author unit test suite validating behavior under edge cases",
            f"Document configuration parameters and architectural trade-offs"
        ],
        "deliverables": [
            f"Implement core functional module utilizing {clean_skill}",
            f"Author unit test suite validating behavior under edge cases",
            f"Document configuration parameters and architectural trade-offs"
        ],
        "interview_talking_points": [f"Explain engineering design choices and trade-offs made when implementing {clean_skill}."],
        "suggested_technologies": [clean_skill],
        "estimated_hours": 8 if priority_tier == "Mandatory" else 6,
        "is_future_work": True,
        "status": "Recommended Future Enhancement"
    }


def cluster_skill_gaps(skill_names: List[str]) -> List[Dict[str, Any]]:
    """
    Groups interdependent skill gaps into coherent learning pathways:
    - Git -> CI/CD -> GitHub Actions / automated deployment
    - Flask/FastAPI/Django -> Docker -> Kubernetes
    - SQL -> Data modeling -> Query optimization
    - Hadoop -> Spark -> Kafka (Big Data pipeline)
    """
    norm_skills = {s.lower().strip(): s for s in skill_names}
    clusters = []

    # Pathway 1: Version Control & Automated Delivery
    vc_skills = [norm_skills[s] for s in ["git", "ci/cd", "github actions", "gitlab"] if s in norm_skills]
    if len(vc_skills) >= 2 or (len(vc_skills) == 1 and any(k in norm_skills for k in ["docker", "linux"])):
        clusters.append({
            "pathway_name": "Automated Delivery & DevOps Pipeline",
            "skills": vc_skills if len(vc_skills) >= 2 else vc_skills + [norm_skills.get("docker", "Docker")],
            "unlocks": "Enables automated testing, PR validation, and continuous deployment workflows.",
            "lead_skill": vc_skills[0] if vc_skills else "Git"
        })

    # Pathway 2: Containerization & Cloud Deployment
    deploy_skills = [norm_skills[s] for s in ["docker", "kubernetes", "aws", "gcp", "azure", "linux"] if s in norm_skills]
    if len(deploy_skills) >= 2:
        clusters.append({
            "pathway_name": "Containerization & Cloud Infrastructure",
            "skills": deploy_skills,
            "unlocks": "Containerizing services in Docker unlocks reliable Kubernetes orchestration and cloud deployments.",
            "lead_skill": "Docker" if "docker" in norm_skills else deploy_skills[0]
        })

    # Pathway 3: Persistence & Query Optimization
    db_skills = [norm_skills[s] for s in ["sql", "postgresql", "mysql", "mongodb", "redis"] if s in norm_skills]
    if len(db_skills) >= 2:
        clusters.append({
            "pathway_name": "Relational Modeling & Query Optimization",
            "skills": db_skills,
            "unlocks": "Mastering SQL schema design accelerates caching strategies with Redis and NoSQL document modeling.",
            "lead_skill": "SQL" if "sql" in norm_skills else db_skills[0]
        })

    # Pathway 4: Big Data & Streaming Pipelines
    bd_skills = [norm_skills[s] for s in ["hadoop", "spark", "kafka", "hive"] if s in norm_skills]
    if len(bd_skills) >= 2:
        clusters.append({
            "pathway_name": "Distributed Big Data & Event Streaming",
            "skills": bd_skills,
            "unlocks": "Foundational distributed storage in Hadoop accelerates in-memory Spark analytics and real-time Kafka streaming.",
            "lead_skill": "Hadoop" if "hadoop" in norm_skills else bd_skills[0]
        })

    # Pathway 5: Agile Delivery & Project Management
    pm_skills = [norm_skills[s] for s in ["project management", "jira", "trello", "agile", "scrum", "kanban", "confluence"] if s in norm_skills]
    if len(pm_skills) >= 2:
        clusters.append({
            "pathway_name": "Agile Delivery & Project Management",
            "skills": pm_skills,
            "unlocks": "Decomposing feature initiatives into sprint user stories and acceptance criteria ensures predictable delivery velocity.",
            "lead_skill": "Project Management" if "project management" in norm_skills else pm_skills[0]
        })

    # Pathway 6: Machine Learning & Predictive Modeling
    ml_skills = [norm_skills[s] for s in ["machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "computer vision", "nlp"] if s in norm_skills]
    if len(ml_skills) >= 2:
        clusters.append({
            "pathway_name": "Machine Learning & Predictive Modeling",
            "skills": ml_skills,
            "unlocks": "Statistical learning foundations and leakage-safe validation enable reliable neural model deployment and error analysis.",
            "lead_skill": "Machine Learning" if "machine learning" in norm_skills else ml_skills[0]
        })

    # Pathway 7: Professional Communication & Engineering Leadership
    comm_skills = [norm_skills[s] for s in ["communication", "presentation", "mentorship", "leadership", "teamwork", "public speaking"] if s in norm_skills]
    if len(comm_skills) >= 2:
        clusters.append({
            "pathway_name": "Professional Communication & Engineering Leadership",
            "skills": comm_skills,
            "unlocks": "Structured technical explanations and constructive mentorship amplify engineering team velocity and stakeholder alignment.",
            "lead_skill": "Communication" if "communication" in norm_skills else comm_skills[0]
        })

    return clusters


def generate_realistic_study_plan(
    roadmaps: List[Dict[str, Any]],
    timeline_days: int = 14,
    daily_hours: float = 2.0
) -> Dict[str, Any]:
    """
    Constructs a realistic, prerequisite-aware study schedule for the candidate.
    Accounts for every day from Day 1 through Day timeline_days.
    Reconciles: total_tasks = scheduled_tasks + completed_tasks + remaining_tasks + deferred_tasks.
    """
    total_available_hours = round(timeline_days * daily_hours, 1)

    # Multi-factor sort: Mandatory first, then priority score and estimated hours
    sorted_roadmaps = sorted(
        roadmaps,
        key=lambda r: (
            0 if r.get("priority_tier") == "Mandatory" else 1,
            -r.get("priority_score", 0),
            r.get("estimated_hours", 10)
        )
    )

    schedule_items = []
    current_day = 1
    current_day_hours_used = 0.0
    accumulated_hours = 0.0
    covered_skills = []
    deferred_skills = []
    deferred_tasks = []

    # Calculate total stages across all roadmaps
    total_stages = sum(len(r.get("stages", [])) for r in roadmaps)

    for r in sorted_roadmaps:
        s_name = r["skill_name"]
        stages = r["stages"]
        hours_per_stage = round(r["estimated_hours"] / len(stages), 1) if stages else 1.0

        skill_fully_scheduled = True
        for st in stages:
            if accumulated_hours + hours_per_stage > total_available_hours:
                skill_fully_scheduled = False
                deferred_tasks.append({
                    "skill_name": s_name,
                    "stage_name": st["name"],
                    "task_description": st["task"],
                    "priority": r.get("priority_tier", "Preferred")
                })
                continue

            resource_entry = r.get("official_resources", [f"Official {s_name} Documentation"])
            primary_resource = resource_entry[0]["title"] if (resource_entry and isinstance(resource_entry[0], dict)) else (resource_entry[0] if resource_entry else f"Official {s_name} Documentation")

            schedule_items.append({
                "day_number": current_day,
                "skill_name": s_name,
                "stage_name": st["name"],
                "task_description": st["task"],
                "learning_objective": f"Master {st['name']} architectural concepts and implementation patterns for {s_name}.",
                "explanation": st.get("complete_explanation") or f"In this stage, focus on core mechanisms and industry patterns for {s_name} ({st['name']}).",
                "exercise": st.get("exercise") or f"Complete hands-on exercise exploring {st['name']} in {s_name}.",
                "expected_output": st.get("deliverable") or f"Working implementation artifact and test notes for {s_name} {st['name']}.",
                "verification_method": st.get("verification_method") or "Verify artifact functionality against automated unit test suites and peer review.",
                "estimated_duration": hours_per_stage,
                "allocated_hours": hours_per_stage,
                "relevant_resource": primary_resource,
                "priority": r.get("priority_tier", "Mandatory")
            })

            accumulated_hours += hours_per_stage
            current_day_hours_used += hours_per_stage
            if current_day_hours_used >= daily_hours and current_day < timeline_days:
                current_day += 1
                current_day_hours_used = 0.0

        if skill_fully_scheduled:
            covered_skills.append(s_name)
        else:
            deferred_skills.append(s_name)

    # Guarantee every day from 1 to timeline_days is explicitly represented in schedule_items
    days_present = {item["day_number"] for item in schedule_items}
    for day in range(1, timeline_days + 1):
        if day not in days_present:
            focus_skill = covered_skills[day % len(covered_skills)] if covered_skills else "Portfolio Review"
            schedule_items.append({
                "day_number": day,
                "skill_name": focus_skill,
                "stage_name": f"Sprint Reinforcement & Review (Day {day})",
                "task_description": f"Perform end-to-end integration testing, refactor modules, and practice technical interview questions in Interview Studio for {focus_skill}.",
                "learning_objective": f"Consolidate learning and verify integration stability for {focus_skill}.",
                "explanation": f"Review sprint achievements, run complete regression test suite, and practice interview articulation.",
                "exercise": f"Run automated test suites and practice answering technical interview questions in Interview Studio.",
                "expected_output": f"Verified passing test suite run and practiced STAR interview answers for {focus_skill}.",
                "verification_method": "All regression tests pass with clean test runner exit and zero unhandled errors.",
                "estimated_duration": daily_hours,
                "allocated_hours": daily_hours,
                "relevant_resource": f"Interview Intelligence Studio & Official {focus_skill} Documentation",
                "priority": "Review"
            })

    schedule_items.sort(key=lambda item: item["day_number"])
    scheduled_task_count = len(schedule_items)
    is_constrained = len(deferred_skills) > 0

    feasibility_note = (
        f"Within {timeline_days} days ({daily_hours} hrs/day = {total_available_hours} total hours), you can "
        f"thoroughly cover {len(covered_skills)} priority competencies ({', '.join(covered_skills)})."
    )
    if is_constrained:
        feasibility_note += (
            f" Note: {len(deferred_skills)} skills ({', '.join(deferred_skills)}) have tasks deferred to next sprint. "
            "Master your scheduled priority competencies first, then tackle deferred competencies."
        )

    # Skill clustering pathways
    skill_names = [r["skill_name"] for r in roadmaps]
    clusters = cluster_skill_gaps(skill_names)

    return {
        "timeline_days": timeline_days,
        "daily_hours": daily_hours,
        "total_available_hours": total_available_hours,
        "total_scheduled_hours": round(accumulated_hours, 1),
        "total_tasks": max(total_stages, scheduled_task_count + len(deferred_tasks)),
        "scheduled_tasks_count": scheduled_task_count,
        "deferred_tasks_count": len(deferred_tasks),
        "covered_skills": covered_skills,
        "deferred_skills": deferred_skills,
        "deferred_tasks": deferred_tasks,
        "is_time_constrained": is_constrained,
        "feasibility_note": feasibility_note,
        "schedule_items": schedule_items,
        "skill_clusters": clusters,
        "disclaimer": "Time allocations are realistic estimates. True mastery depends on deliberate coding practice and independent troubleshooting."
    }
