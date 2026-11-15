"""
Curated Educational Resource Mapping Module.
Provides verified official documentation links, interactive tutorials, and vendor learning portals:
- Python Official Documentation
- Scikit-learn Official User Guide
- PyTorch Official Tutorials
- PostgreSQL Official Manual
- Docker Official Documentation
- Kubernetes Official Basics
- AWS Skill Builder & Documentation
- Google Cloud Training & Architecture Center
- Microsoft Learn Portal
- MDN Web Docs
- Linux Documentation Project & Ubuntu Server Guide
- Pro Git Book
"""

from typing import Dict, List, Any, Optional

VERIFIED_RESOURCE_REGISTRY: Dict[str, List[Dict[str, str]]] = {
    "python": [
        {
            "title": "Python 3 Official Documentation & Tutorial",
            "url": "https://docs.python.org/3/tutorial/",
            "provider": "Python Software Foundation",
            "type": "Official Documentation",
            "description": "Comprehensive walkthrough of Python syntax, data structures, standard library, and modules."
        },
        {
            "title": "Python Developer's Guide to Packaging & Best Practices",
            "url": "https://packaging.python.org/en/latest/",
            "provider": "PyPA",
            "type": "Guide",
            "description": "Standardized virtual environment setup, dependency management (pip), and project layout."
        }
    ],
    "docker": [
        {
            "title": "Docker Official Getting Started Guide",
            "url": "https://docs.docker.com/get-started/",
            "provider": "Docker Inc.",
            "type": "Official Documentation",
            "description": "Hands-on containerization tutorial covering Dockerfiles, multi-stage builds, and container networking."
        },
        {
            "title": "Docker Compose Multi-Container Specification",
            "url": "https://docs.docker.com/compose/",
            "provider": "Docker Inc.",
            "type": "Documentation",
            "description": "How to define and run multi-container applications (e.g. Flask app connected to PostgreSQL)."
        }
    ],
    "kubernetes": [
        {
            "title": "Kubernetes Official Basics Interactive Tutorial",
            "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
            "provider": "Cloud Native Computing Foundation",
            "type": "Official Interactive Tutorial",
            "description": "Deploy, expose, scale, and update containerized applications on a Kubernetes cluster."
        },
        {
            "title": "Kubernetes Core Concepts & Architecture",
            "url": "https://kubernetes.io/docs/concepts/",
            "provider": "Kubernetes Documentation",
            "type": "Official Guide",
            "description": "Deep dive into Pods, Deployments, Services, ConfigMaps, Ingress, and cluster architecture."
        }
    ],
    "sql": [
        {
            "title": "PostgreSQL Official Documentation & Tutorial",
            "url": "https://www.postgresql.org/docs/current/tutorial.html",
            "provider": "PostgreSQL Global Development Group",
            "type": "Official Documentation",
            "description": "Relational database fundamentals, SQL queries, table schemas, joins, and transaction isolation."
        },
        {
            "title": "PostgreSQL Performance Optimization & Indexing Guide",
            "url": "https://www.postgresql.org/docs/current/indexes.html",
            "provider": "PostgreSQL Docs",
            "type": "Documentation",
            "description": "B-Tree, GIN, and GiST indexes, EXPLAIN query planning, and performance tuning."
        }
    ],
    "postgresql": [
        {
            "title": "PostgreSQL Official Documentation",
            "url": "https://www.postgresql.org/docs/current/",
            "provider": "PostgreSQL Global Development Group",
            "type": "Official Documentation",
            "description": "Complete reference for PostgreSQL database administration, SQL dialects, and concurrency controls."
        }
    ],
    "scikit-learn": [
        {
            "title": "Scikit-learn User Guide & Model Evaluation",
            "url": "https://scikit-learn.org/stable/user_guide.html",
            "provider": "Scikit-learn Consortium",
            "type": "Official Documentation",
            "description": "Supervised learning models, pipeline feature transformers, cross-validation metrics, and preprocessing."
        }
    ],
    "pytorch": [
        {
            "title": "PyTorch Official Tutorials: Deep Learning with PyTorch",
            "url": "https://pytorch.org/tutorials/",
            "provider": "PyTorch Foundation / Linux Foundation",
            "type": "Official Tutorials",
            "description": "Tensors, autograd, torch.nn neural network modules, Dataset loaders, and GPU acceleration."
        }
    ],
    "aws": [
        {
            "title": "AWS Skill Builder: Cloud Practitioner Essentials",
            "url": "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/",
            "provider": "Amazon Web Services",
            "type": "Official Free Training",
            "description": "Foundational cloud computing concepts, IAM security, EC2 compute, S3 storage, and RDS databases."
        },
        {
            "title": "AWS Architecture Center: Best Practices & Well-Architected Framework",
            "url": "https://aws.amazon.com/architecture/",
            "provider": "AWS Documentation",
            "type": "Architecture Guide",
            "description": "Reference architectures and reliability principles for production cloud deployments."
        }
    ],
    "gcp": [
        {
            "title": "Google Cloud Architecture Framework & Learning Center",
            "url": "https://cloud.google.com/architecture/framework",
            "provider": "Google Cloud",
            "type": "Official Architecture Guide",
            "description": "Design guidance and reference patterns for compute, storage, security, and automated pipelines on GCP."
        }
    ],
    "azure": [
        {
            "title": "Microsoft Learn: Azure Fundamentals",
            "url": "https://learn.microsoft.com/en-us/training/paths/azure-fundamentals/",
            "provider": "Microsoft Learn",
            "type": "Official Learning Path",
            "description": "Cloud service models, core architectural components, management tools, and Azure governance."
        }
    ],
    "linux": [
        {
            "title": "Ubuntu Server Guide & Linux Documentation Project",
            "url": "https://ubuntu.com/server/docs",
            "provider": "Canonical / Linux Foundation",
            "type": "Official Documentation",
            "description": "Bash command line, systemd services, SSH configuration, file permissions, and process monitoring."
        }
    ],
    "git": [
        {
            "title": "Pro Git Book (Official Free Edition)",
            "url": "https://git-scm.com/book/en/v2",
            "provider": "Git Official Project",
            "type": "Official Book",
            "description": "Git branching models, merge conflict resolution, rebase workflows, and remote repository collaboration."
        }
    ],
    "javascript": [
        {
            "title": "MDN Web Docs: JavaScript Guide & Reference",
            "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
            "provider": "Mozilla Developer Network",
            "type": "Official Documentation",
            "description": "Modern ECMAScript, asynchronous promises, async/await, DOM manipulation, and browser APIs."
        }
    ],
    "react": [
        {
            "title": "React Official Documentation: Quick Start & Core Concepts",
            "url": "https://react.dev/learn",
            "provider": "React Team / Meta Open Source",
            "type": "Official Documentation",
            "description": "Component hierarchy, state management, hooks (useState, useEffect), and component lifecycles."
        }
    ],
    "fastapi": [
        {
            "title": "FastAPI Official Interactive Tutorial",
            "url": "https://fastapi.tiangolo.com/tutorial/",
            "provider": "FastAPI Documentation",
            "type": "Official Documentation",
            "description": "High-performance Python APIs, Pydantic data schemas, dependency injection, and OpenAPI swagger docs."
        }
    ],
    "flask": [
        {
            "title": "Flask Official Documentation & Tutorial",
            "url": "https://flask.palletsprojects.com/en/latest/tutorial/",
            "provider": "Pallets Projects",
            "type": "Official Documentation",
            "description": "Application factory, URL routing, Jinja2 templating, sessions, and blueprint organization."
        }
    ],
    "ci/cd": [
        {
            "title": "GitHub Actions Documentation: Continuous Integration",
            "url": "https://docs.github.com/en/actions",
            "provider": "GitHub / Microsoft",
            "type": "Official Documentation",
            "description": "Workflow YAML configuration, automated testing pipelines, multi-OS runners, and release artifacts."
        }
    ],
    "spark": [
        {
            "title": "Apache Spark Official Documentation & Quick Start",
            "url": "https://spark.apache.org/docs/latest/quick-start.html",
            "provider": "Apache Software Foundation",
            "type": "Official Documentation",
            "description": "In-memory distributed computing, DataFrame transformations, Spark SQL, and pipeline optimization."
        }
    ],
    "hadoop": [
        {
            "title": "Apache Hadoop Official Documentation",
            "url": "https://hadoop.apache.org/docs/stable/",
            "provider": "Apache Software Foundation",
            "type": "Official Documentation",
            "description": "Hadoop Distributed File System (HDFS), YARN architecture, and distributed batch processing."
        }
    ],
    "kafka": [
        {
            "title": "Apache Kafka Official Quickstart & Architecture",
            "url": "https://kafka.apache.org/documentation/",
            "provider": "Apache Software Foundation",
            "type": "Official Documentation",
            "description": "Distributed event streaming, topic partitioning, producer/consumer APIs, and log retention."
        }
    ],
    "git": [
        {
            "title": "Pro Git Book & Official Reference",
            "url": "https://git-scm.com/doc",
            "provider": "Git Project",
            "type": "Official Guide",
            "description": "Atomic commits, branching models, interactive rebasing, merge conflict resolution, and internal object storage."
        }
    ],
    "linux": [
        {
            "title": "The Linux Documentation Project & Core Utilities",
            "url": "https://tldp.org/",
            "provider": "TLDP / Linux Foundation",
            "type": "Official Documentation",
            "description": "Kernel architecture, POSIX permissions, process signals, bash shell automation, and system administration."
        }
    ]
}


def get_learning_resources_for_skill(skill_name: str) -> List[Dict[str, str]]:
    """
    Retrieves verified, legitimate educational resources for a skill name.
    If no verified resources are mapped, returns an honest empty list.
    """
    if not skill_name or not isinstance(skill_name, str):
        return []

    norm_name = skill_name.lower().strip()
    
    # Direct match
    if norm_name in VERIFIED_RESOURCE_REGISTRY:
        return VERIFIED_RESOURCE_REGISTRY[norm_name]

    # Partial / alias match
    for key, resources in VERIFIED_RESOURCE_REGISTRY.items():
        if key in norm_name or norm_name in key:
            return resources

    # Common aliases
    alias_map = {
        "postgres": "sql",
        "mysql": "sql",
        "database": "sql",
        "rdbms": "sql",
        "k8s": "kubernetes",
        "container": "docker",
        "containers": "docker",
        "amazon web services": "aws",
        "google cloud": "gcp",
        "google cloud platform": "gcp",
        "microsoft azure": "azure",
        "bash": "linux",
        "shell": "linux",
        "github": "git",
        "deep learning": "pytorch",
        "machine learning": "scikit-learn",
        "nlp": "python",
        "natural language processing": "python"
    }

    if norm_name in alias_map:
        target_key = alias_map[norm_name]
        return VERIFIED_RESOURCE_REGISTRY.get(target_key, [])

    return []
