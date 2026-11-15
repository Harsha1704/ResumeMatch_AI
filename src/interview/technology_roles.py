"""
Technology Roles and Architectural Trade-offs Knowledge Base.
Provides deterministic, domain-accurate software engineering explanations for technologies.
Eliminates generic boilerplate ("robust ecosystem", "excellent performance") by explaining:
- Specific architectural responsibility in a software pipeline.
- Concrete engineering trade-offs compared to alternatives.
- How the tool integrates with data structures and other components.
- Standard testing, validation, and debugging strategies.
"""

from typing import Dict, Any, Optional

TECHNOLOGY_ROLES: Dict[str, Dict[str, Any]] = {
    "python": {
        "role": "serves as the primary programming language for implementing business logic, data structures, and pipeline automation",
        "trade_off": "prioritizes rapid development velocity, clean readability, and extensive standard library tools over raw CPU execution speed",
        "integration": "interfaces seamlessly with C-extensions for numerical performance and standard WSGI/ASGI web servers",
        "testing": "verified through automated Pytest unit suites, type hints with mypy, and isolated virtual environments"
    },
    "flask": {
        "role": "acts as the lightweight WSGI backend web framework handling HTTP routing, request parsing, and response formatting",
        "trade_off": "provides minimal architectural overhead and modular freedom without imposing heavyweight monolithic ORM constraints",
        "integration": "exposes REST endpoints that receive client payloads and dispatch processing directly to backend analytical modules",
        "testing": "validated using Flask test clients with mocked request fixtures and HTTP status assertion checks"
    },
    "fastapi": {
        "role": "provides high-throughput asynchronous REST API endpoints with automated OpenAPI documentation and Pydantic schema validation",
        "trade_off": "leverages Python async/await for high concurrency on I/O-bound tasks while requiring disciplined coroutine management",
        "integration": "validates incoming JSON schemas at the network boundary before passing typed models to processing pipelines",
        "testing": "tested using Starlette/FastAPI TestClient with asynchronous route fixtures and schema validation checks"
    },
    "django": {
        "role": "provides an enterprise full-stack web framework with an integrated ORM, authentication system, and administrative tooling",
        "trade_off": "accelerates complex relational applications through structured conventions while incurring higher architectural footprint",
        "integration": "encapsulates relational database queries through Django ORM models and manages transactional view workflows",
        "testing": "tested via Django TestCase with automated database rollbacks and client request simulations"
    },
    "scikit-learn": {
        "role": "provides machine learning algorithms, text vectorization (TF-IDF), cross-validation, and performance evaluation metrics",
        "trade_off": "delivers stable, reproducible, CPU-optimized estimators through a standardized fit/transform API without distributed compute overhead",
        "integration": "encapsulated inside scikit-learn Pipeline objects to guarantee strict isolation between feature transformers and classifiers",
        "testing": "evaluated through stratified k-fold cross-validation, confusion matrices, and holdout validation splits"
    },
    "pytorch": {
        "role": "powers deep neural network modeling, automated gradient computation, and tensor-accelerated matrix operations",
        "trade_off": "offers dynamic computational graph flexibility and GPU acceleration, requiring disciplined memory management across CUDA devices",
        "integration": "processes multidimensional embeddings and forward-pass inference connected to downstream classification heads",
        "testing": "verified by tracking loss convergence curves, validation perplexity, and gradient norm monitoring"
    },
    "tensorflow": {
        "role": "manages neural network graph construction, training pipelines, and production model serving via TensorFlow Serving",
        "trade_off": "enables cross-platform enterprise deployment and TPU acceleration with structured static graph optimizations",
        "integration": "utilizes tf.data pipelines for efficient streaming of serialized feature records into neural layers",
        "testing": "monitored using TensorBoard metrics and evaluated on frozen holdout evaluation datasets"
    },
    "docker": {
        "role": "containerizes application runtimes, isolating system dependencies, libraries, and environment variables into immutable images",
        "trade_off": "shares the host Linux kernel via namespaces and cgroups for millisecond startups rather than heavy hardware virtualization",
        "integration": "guarantees consistent execution across local development, continuous integration, and staging environments",
        "testing": "validated through multi-stage build tests and container health-check endpoints"
    },
    "kubernetes": {
        "role": "orchestrates containerized services, managing automated replication, rolling deployments, and service discovery",
        "trade_off": "provides cloud-native resilience and declarative scaling at the cost of cluster configuration complexity",
        "integration": "manages ingress routing, pod lifecycle states, and horizontal pod autoscaling based on CPU/memory utilization",
        "testing": "tested through staging cluster deployments, liveness/readiness probes, and canary rollout strategies"
    },
    "sql": {
        "role": "enforces declarative relational data modeling, query execution, constraints, and relational aggregations",
        "trade_off": "guarantees ACID transactional consistency and relational integrity while requiring upfront schema definitions",
        "integration": "structures normalized business entities connected via foreign keys and indexed primary keys",
        "testing": "tested using transactional fixtures, query EXPLAIN plan inspection, and schema migration rollbacks"
    },
    "postgresql": {
        "role": "delivers robust relational data persistence with advanced indexing (B-tree, GIN), JSONB storage, and MVCC concurrency",
        "trade_off": "provides strict ANSI-SQL compliance and extensible data types while requiring query tuning under heavy write loads",
        "integration": "persists structured candidate profiles and relational entities with indexed foreign key relationships",
        "testing": "analyzed via EXPLAIN ANALYZE for query cost verification and automated migration testing"
    },
    "mysql": {
        "role": "manages high-throughput relational transaction storage utilizing the InnoDB storage engine with row-level locking",
        "trade_off": "delivers fast read-heavy transactional performance with widely established tooling across cloud platforms",
        "integration": "persists application records with foreign key constraints and transactional rollback logging",
        "testing": "benchmarked using query profiling and validated through automated integration suites"
    },
    "mongodb": {
        "role": "stores semi-structured documents in dynamic JSON-like BSON schemas without rigid upfront column definitions",
        "trade_off": "facilitates flexible schema evolution and horizontal sharding while trading away multi-table relational joins",
        "integration": "persists hierarchical document trees such as nested resume sections and arbitrary skill payloads",
        "testing": "tested using schema validation rules and replica set integration tests"
    },
    "redis": {
        "role": "serves as an in-memory key-value cache and pub/sub message broker providing sub-millisecond read/write latency",
        "trade_off": "delivers microsecond response times by operating entirely in RAM, constrained by available memory capacity",
        "integration": "caches frequent query results, session states, and rate-limiting counters to offload primary databases",
        "testing": "validated using TTL expiration assertions and cache-invalidation unit tests"
    },
    "react": {
        "role": "builds declarative, component-driven user interfaces using a virtual DOM to minimize direct browser reflows",
        "trade_off": "provides reactive state management and component reusability while requiring a client-side JavaScript build step",
        "integration": "consumes backend JSON APIs via asynchronous HTTP requests and renders dynamic views based on local state",
        "testing": "tested with Jest and React Testing Library verifying user interactions and component lifecycle rendering"
    },
    "javascript": {
        "role": "executes client-side DOM manipulation, asynchronous network requests, and event-driven browser interactions",
        "trade_off": "provides universal native browser execution with an event loop while requiring careful asynchronous error handling",
        "integration": "attaches event listeners to user interface controls and communicates with backend services via Fetch or Axios",
        "testing": "tested using browser automation and modern unit testing frameworks"
    },
    "typescript": {
        "role": "adds compile-time static type checking and interfaces over standard JavaScript, preventing runtime type errors",
        "trade_off": "catches edge-case type bugs during compilation at the cost of additional compilation tooling and type declarations",
        "integration": "defines shared data contracts between frontend client views and backend API response payloads",
        "testing": "verified through strict compiler type checks (`tsc --noEmit`) and unit tests"
    },
    "git": {
        "role": "manages distributed version control, tracking atomic code changes, branching strategies, and collaboration workflows",
        "trade_off": "enables safe feature branching and collaborative pull requests while requiring merge conflict resolution discipline",
        "integration": "underpins CI/CD automation pipelines triggered on pull requests and tags",
        "testing": "verified through branch protection rules, pre-commit hooks, and continuous integration triggers"
    },
    "opencv": {
        "role": "processes computer vision pipelines including image filtering, edge detection, feature extraction, and matrix transformations",
        "trade_off": "delivers real-time image processing in optimized C++ binaries accessible through Python bindings",
        "integration": "preprocesses visual artifacts and camera frame arrays before passing matrices to neural detectors",
        "testing": "validated on benchmark image suites evaluating perceptual precision and frame processing latency"
    },
    "pandas": {
        "role": "manipulates structured tabular datasets using Series and DataFrame objects for cleaning, transformation, and aggregations",
        "trade_off": "simplifies complex exploratory data operations and joins while loading entire datasets into memory",
        "integration": "cleans raw data inputs, handles missing values, and feeds structured arrays to machine learning algorithms",
        "testing": "tested with deterministic test DataFrames verifying data types and column transformation integrity"
    },
    "numpy": {
        "role": "executes high-performance numerical computing on N-dimensional homogeneous arrays with vectorized C-level operations",
        "trade_off": "eliminates Python loop overhead through vectorized SIMD operations while requiring fixed-type homogeneous arrays",
        "integration": "forms the fundamental numerical backbone for feature matrices, linear algebra, and model predictions",
        "testing": "asserted using numpy.testing assertions verifying numerical tolerances and matrix dimensions"
    },
    "aws": {
        "role": "provides managed cloud infrastructure including compute (EC2), storage (S3), databases (RDS), and serverless execution (Lambda)",
        "trade_off": "eliminates physical datacenter maintenance while requiring strict IAM access controls and cost monitoring",
        "integration": "hosts backend application services, object storage for uploaded files, and automated deployment pipelines",
        "testing": "tested using staging environments, infrastructure-as-code linting, and health-check monitoring"
    },
    "linux": {
        "role": "serves as the foundational operating system environment for server process execution, permissions isolation, and shell scripting",
        "trade_off": "delivers lightweight kernel performance and POSIX predictability while requiring disciplined command-line administration",
        "integration": "manages systemd process supervisors, environment variable scoping, and socket networking for backend daemons",
        "testing": "verified through automated shell test suites, system audit logs, and permission checks"
    },
    "ci/cd": {
        "role": "automates continuous integration testing, code linting, security audits, and deployment pipelines",
        "trade_off": "guarantees reproducible build gates and fast feedback cycles while requiring ongoing pipeline script maintenance",
        "integration": "triggers automated runners on Git commits and pull requests, packaging containers and notifying developers",
        "testing": "validated using simulated branch pull requests, matrix test runners, and automated rollback health checks"
    },
    "mediapipe": {
        "role": "provides accelerated cross-platform machine learning pipelines for real-time perceptual processing, face mesh, and landmark tracking",
        "trade_off": "delivers ultra-low latency inference on edge and CPU devices using optimized graph dataflows while offering fixed topological models",
        "integration": "streams real-time video frames through perception calculators to output normalized spatial coordinates to downstream logic",
        "testing": "benchmarked using frame-rate throughput benchmarks and landmark jitter tolerance suites"
    },
    "kafka": {
        "role": "serves as a high-throughput distributed event-streaming platform for partitioned append-only message logs",
        "trade_off": "delivers millisecond message persistence and decoupled pub/sub scaling while requiring ZooKeeper/KRaft cluster coordination",
        "integration": "buffers producer events from ingest pipelines and fans out ordered message partitions to consumer worker groups",
        "testing": "tested via embedded Kafka test clusters asserting message ordering, consumer lag, and failure recovery"
    },
    "spark": {
        "role": "executes distributed in-memory cluster computing for large-scale data transformation, SQL querying, and analytics",
        "trade_off": "speeds up batch iterations by caching intermediate RDD/DataFrames in memory while requiring high cluster RAM allocations",
        "integration": "ingests raw data partitions from object stores, performs distributed joins and transformations, and sinks outputs to persistent stores",
        "testing": "verified using local SparkSession test fixtures asserting schema integrity and transformation correctness"
    },
    "hadoop": {
        "role": "provides fault-tolerant distributed storage (HDFS) and batch compute (MapReduce/YARN) across commodity server clusters",
        "trade_off": "scales economically to petabytes of unstructured data with 3x replication while incurring disk-bound MapReduce latency",
        "integration": "persists raw event archives and feeds analytical batch jobs through YARN resource management",
        "testing": "validated using MiniDFSCluster fixtures and data node failover tests"
    },
    "nginx": {
        "role": "operates as an asynchronous event-driven reverse proxy, SSL termination gateway, and static file server",
        "trade_off": "handles tens of thousands of concurrent client connections with negligible memory overhead without blocking on worker threads",
        "integration": "terminates TLS at the network perimeter and proxies sanitized HTTP requests to upstream WSGI application servers",
        "testing": "tested via configuration syntax linters (`nginx -t`) and automated integration probes"
    },
    "computer vision": {
        "role": "processes visual frame streams through color-space conversions, edge filtering, and spatial transformations before feature extraction",
        "trade_off": "delivers low-latency pixel-level transformations and frame extraction over higher-level symbolic representations",
        "integration": "ingests raw camera or video frame matrices and outputs normalized tensor arrays to downstream neural models",
        "testing": "evaluated on benchmark visual suites assessing frame throughput, detection precision, and noise resilience"
    },
    "machine learning": {
        "role": "extracts predictive patterns from structured feature matrices and evaluates generalization on unseen validation data",
        "trade_off": "balances model predictive capacity against overfitting risk through regularized objective functions and cross-validation",
        "integration": "transforms preprocessed feature vectors into calibrated class probability distributions and predictions",
        "testing": "verified using stratified k-fold cross-validation, confusion matrices, and holdout evaluation splits"
    },
    "deep learning": {
        "role": "trains multi-layer neural network architectures to learn hierarchical feature representations directly from raw perceptual data",
        "trade_off": "captures complex non-linear representations at the cost of high GPU compute requirements and hyperparameter sensitivity",
        "integration": "feeds batch tensors through forward-pass activation layers to compute loss gradients via backpropagation",
        "testing": "evaluated through training/validation loss curve convergence, gradient norm monitoring, and holdout evaluation"
    },
    "nlp": {
        "role": "tokenizes text corpora, strips noise, and computes semantic vector embeddings for linguistic classification and extraction",
        "trade_off": "preserves syntactic and contextual semantics while managing high vocabulary dimensionality and sparsity",
        "integration": "transforms raw text documents into dense numerical embeddings consumed by downstream classifiers",
        "testing": "evaluated via precision-recall curves, macro F1, and out-of-vocabulary edge-case benchmarks"
    },
    "natural language processing": {
        "role": "tokenizes text corpora, strips noise, and computes semantic vector embeddings for linguistic classification and extraction",
        "trade_off": "preserves syntactic and contextual semantics while managing high vocabulary dimensionality and sparsity",
        "integration": "transforms raw text documents into dense numerical embeddings consumed by downstream classifiers",
        "testing": "evaluated via precision-recall curves, macro F1, and out-of-vocabulary edge-case benchmarks"
    },
    "c++": {
        "role": "executes high-performance compiled application logic with direct memory management and zero-cost abstractions",
        "trade_off": "delivers deterministic microsecond CPU execution and memory efficiency while requiring manual memory lifecycle discipline",
        "integration": "compiles into native binary executables or dynamic libraries exposed to higher-level languages via C-bindings",
        "testing": "tested via GoogleTest unit suites, Valgrind memory leak profiling, and AddressSanitizer checks"
    },
    "java": {
        "role": "provides strongly-typed object-oriented application services running on the cross-platform Java Virtual Machine (JVM)",
        "trade_off": "guarantees type safety, mature concurrency utilities, and rich enterprise tooling while incurring JVM memory footprint",
        "integration": "encapsulates business domain entities and repository layers behind dependency-injected interfaces",
        "testing": "tested using JUnit 5 unit tests, Mockito mock fixtures, and integration test containers"
    },
    "rest api": {
        "role": "exposes stateless HTTP endpoints using standard request methods, JSON payloads, and HTTP status codes",
        "trade_off": "decouples frontend clients from backend services via universal HTTP standards while requiring structured versioning",
        "integration": "routes client HTTP requests to service handlers and serializes response data structures into standard JSON",
        "testing": "validated using automated API test clients asserting status codes, payload schemas, and error boundaries"
    },
    "api": {
        "role": "exposes structured programmatic interfaces and network endpoints for decoupled client-server data exchange",
        "trade_off": "establishes clean architectural boundaries while requiring defensive input validation and error contracts",
        "integration": "serializes request and response payloads across network boundaries to connect decoupled components",
        "testing": "tested using automated integration fixtures verifying contract schemas and HTTP status codes"
    },
    "sqlite": {
        "role": "provides an embedded, zero-configuration relational database engine operating within the application process space",
        "trade_off": "eliminates standalone database server administration and latency while locking on concurrent writes",
        "integration": "persists relational entities directly to a local file, serving as a lightweight local datastore",
        "testing": "tested using in-memory SQLite fixtures (`:memory:`) ensuring fast, isolated test execution"
    }
}


def get_technology_profile(tech_name: str) -> Dict[str, str]:
    """
    Returns specific engineering profile for a technology or a precise software engineering fallback.
    Never returns vague corporate clichés or circular tautologies.
    """
    clean = (tech_name or "").strip().lower()
    for key, profile in TECHNOLOGY_ROLES.items():
        if key in clean or clean in key:
            return profile

    # Domain-aware non-circular fallback
    if any(k in clean for k in ["lang", "script", "code", "syntax"]):
        role_desc = "provides the foundational syntax, type constraints, and runtime logic execution for the system"
    elif any(k in clean for k in ["db", "data", "store", "sql", "cache"]):
        role_desc = "persists application entities, enforces integrity constraints, and executes structured queries"
    elif any(k in clean for k in ["cloud", "deploy", "infra", "ops", "tool"]):
        role_desc = "orchestrates environment configuration, dependencies, and automated pipeline execution"
    else:
        role_desc = "executes core domain operations and data transformations within the application pipeline"

    return {
        "role": role_desc,
        "trade_off": f"balances specialized {clean} capabilities against architectural implementation complexity",
        "integration": f"interfaces with adjacent system modules through defined programmatic contracts",
        "testing": f"validated through automated unit tests and functional boundary assertions"
    }
