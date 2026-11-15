import pprint
import re

with open('src/mentor/skill_curricula.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Define SPARK_CURRICULUM
spark_dict = {
    'advanced_concepts': [
        'Catalyst Query Optimizer & Tungsten Execution Engine',
        'Broadcast Hash Joins & Mitigating Shuffle Bottlenecks',
        'Data Skew Salting Strategies & Partition Rebalancing',
        'Structured Streaming with Watermarking & Checkpointing',
        'Spark Memory Management: Storage vs Execution RAM'
    ],
    'domain_display': 'Big Data & Distributed Computing',
    'domain_key': 'big_data',
    'fundamental_concepts': [
        'Distributed Cluster Topology: Driver, Executors & Cluster Managers',
        'Resilient Distributed Datasets (RDDs) & Immutable Partitions',
        'Directed Acyclic Graphs (DAGs), Stages & Tasks',
        'Lazy Evaluation: Transformations vs Actions',
        'SparkSession & Spark Web UI Inspection'
    ],
    'intermediate_concepts': [
        'Spark DataFrames & Strongly-Typed Schema Enforcement',
        'Columnar Expressions with pyspark.sql.functions',
        'Partitioning Granularity: coalesce() vs repartition()',
        'Narrow vs Wide Dependencies & Network Shuffles',
        'PySpark Window Functions for Rolling & Ranked Analytics'
    ],
    'interview_prep': [
        {
            'question': 'Explain the difference between transformations and actions in Apache Spark, and why lazy evaluation is advantageous.',
            'answer': 'Transformations (such as map, filter, select, join) are non-materializing operations that construct a Directed Acyclic Graph (DAG) of logical execution steps without computing results immediately. Actions (such as count, collect, show, write) trigger physical job execution by submitting the compiled DAG to the DAGScheduler. Lazy evaluation allows Spark’s Catalyst Optimizer to analyze the entire query plan holistically, combining filter predicates (predicate pushdown), pruning unreferenced columns (projection pruning), and selecting optimal join strategies before executing network shuffles or loading bytes from storage.'
        },
        {
            'question': 'How do you detect, diagnose, and resolve data skew in a distributed PySpark join or aggregation?',
            'answer': 'Data skew occurs when an uneven distribution of join or grouping keys causes one or two partitions to process significantly more data than others, leading to straggling tasks and Executor OutOfMemory (OOM) failures while other workers remain idle. You diagnose skew via the Spark Web UI by observing massive variance between median task duration and maximum task duration in a stage. To resolve skew: 1) If joining against a smaller table (<100MB), use a BroadcastHashJoin (broadcast(small_df)) to eliminate the shuffle entirely; 2) For large-to-large joins, employ key salting by appending a random integer suffix (e.g. 0 to N-1) to the skewed key on the left table and exploding matching keys on the right table to distribute load evenly across worker cores; 3) Enable Adaptive Query Execution in Spark 3.x+.'
        },
        {
            'question': 'When should you use coalesce() instead of repartition(), and what are the performance trade-offs?',
            'answer': 'Both functions alter the number of partitions in a DataFrame, but their execution mechanisms differ fundamentally. repartition(N) performs a full network shuffle to redistribute data uniformly across N partitions; it can increase or decrease partition counts and guarantees balanced data distribution at the cost of high network I/O. In contrast, coalesce(N) decreases partition counts by merging adjacent partitions locally without triggering a network shuffle. coalesce is ideal when consolidating output files before writing to disk with minimal resource cost, but it cannot increase partition count and may create uneven partition sizes if source partitions vary widely.'
        }
    ],
    'learning_objectives': [
        'Master Spark cluster architecture including Driver, Executors, and Web UI diagnostics',
        'Author structured PySpark DataFrame transformations with strict schema enforcement',
        'Optimize distributed pipelines by tuning partition granularity and eliminating network shuffles',
        'Understand Catalyst query execution plans (Parsed, Logical, Optimized, Physical)',
        'Build production-ready PySpark batch ETL pipelines with partitioned Parquet storage'
    ],
    'mini_project': {
        'description': 'Build a standalone PySpark batch processing pipeline that ingests multi-partition datasets, applies Window aggregations and broadcast joins, and writes partitioned Parquet outputs.',
        'steps': [
            'Initialize a configured local SparkSession with localized memory and core allocations',
            'Ingest raw datasets with explicit StructType schemas and validate null values',
            'Apply columnar transformations, null handling, and rolling Window aggregations',
            'Optimize multi-table join using BroadcastHashJoin for dimension lookup tables',
            'Write partitioned columnar Parquet files with snappy compression and verify output metrics'
        ],
        'title': 'Distributed PySpark Batch Transformation Pipeline',
        'verification': 'Spark Web UI confirms zero task failures, clean stage DAGs, and balanced partition sizes.'
    },
    'official_resources': [
        {
            'description': 'Official quick start guide and programming documentation for Apache Spark.',
            'provider': 'Apache Software Foundation',
            'title': 'Apache Spark Official Documentation & Quick Start',
            'type': 'Official Documentation',
            'url': 'https://spark.apache.org/docs/latest/quick-start.html'
        },
        {
            'description': 'Comprehensive API reference for PySpark DataFrames, functions, and SQL types.',
            'provider': 'Apache Software Foundation',
            'title': 'PySpark API Reference & DataFrame Documentation',
            'type': 'Official Documentation',
            'url': 'https://spark.apache.org/docs/latest/api/python/'
        }
    ],
    'practical_exercises': [
        'Initialize local SparkSession and verify Web UI active stages and executor memory pools',
        'Load CSV/JSON data with explicit StructType and implement conditional withColumn transformations',
        'Benchmark execution duration between repartition() and coalesce() on 1M rows',
        'Inspect and compare Parsed, Logical, and Physical execution plans via df.explain(True)',
        'Implement BroadcastHashJoin and verify absence of SortMergeJoin shuffle in physical plan'
    ],
    'prerequisites': [
        'Python Programming (Functions, Iterators, Collections)',
        'SQL & Relational Databases (JOINs, GROUP BY, Aggregations)',
        'Data Structures (Arrays, Hash Maps, Trees)'
    ],
    'resume_evidence': {
        'bullet_template': 'Engineered distributed PySpark ETL pipeline processing multi-gigabyte datasets, implementing broadcast joins and window aggregations that reduced job latency by 45%.',
        'keywords': ['Apache Spark', 'PySpark', 'Spark SQL', 'Broadcast Join', 'Parquet']
    },
    'skill_name': 'Apache Spark',
    'stages': [
        {
            'complete_explanation': 'In Apache Spark, computation follows a master-worker topology. The Driver process runs the user application code, instantiates the SparkSession, translates user transformations into a directed acyclic graph (DAG) of stages, and schedules tasks via the DAGScheduler and TaskScheduler. Worker nodes host Executor JVM processes that execute individual task units in parallel across CPU cores and maintain in-memory block storage. Unlike Hadoop MapReduce which wrote all intermediate shuffle state to physical disk between steps, Spark executes operations in RAM across pipeline stages, achieving 10x-100x performance improvements on iterative batch workflows.',
            'concrete_example': 'A 100GB access log file partitioned across 10 executors allows each executor core to process a 10GB chunk concurrently in memory rather than reading sequentially from a single disk.',
            'deliverable': 'A runnable Python script (verify_spark_cluster.py) outputting executor count, local CPU parallelism, and SparkSession configuration.',
            'exercise': 'Install PySpark locally. Initialize a local SparkSession with local[*] cores. Inspect sc.defaultParallelism and verify active executors in the Spark Web UI at http://localhost:4040.',
            'name': 'Distributed Cluster Architecture & Execution Flow',
            'stage_num': 1,
            'task': 'Understand Spark cluster architecture: Driver program, Executors, Cluster Manager (YARN/Kubernetes/Standalone), Worker Nodes, and distributed task scheduling.',
            'verification_method': 'Confirm the Spark Web UI opens at localhost:4040 showing active stages and memory storage pools without worker launch errors.'
        },
        {
            'complete_explanation': 'While early Spark versions relied on low-level resilient distributed datasets (RDDs), modern Spark centers on the DataFrame API—a distributed collection of data organized into named columns under a strictly typed schema (StructType). Operating on DataFrames allows the Catalyst Optimizer to perform rule-based and cost-based query optimization, including predicate pushdown (filtering rows at the storage layer before memory loading) and projection pruning (reading only requested columns from Parquet files).',
            'concrete_example': "schema = StructType([StructField('id', IntegerType(), False), StructField('timestamp', TimestampType(), True), StructField('amount', DoubleType(), True)])",
            'deliverable': 'A clean PySpark module (dataframe_transformations.py) performing schema validation and clean transformation steps.',
            'exercise': 'Load a multi-column dataset into a PySpark DataFrame with an explicit schema. Implement column casting, conditional expressions using when(), and null-value imputation using fillna().',
            'name': 'Spark DataFrames, Schemas & Structured API',
            'stage_num': 2,
            'task': 'Master typed schema definition using StructType and StructField, column transformations with pyspark.sql.functions, and catalyst optimizer execution.',
            'verification_method': 'Run df.printSchema() and verify column data types match specifications without falling back to expensive runtime type inference.'
        },
        {
            'complete_explanation': "A partition is a discrete atomic chunk of data stored across the cluster. If data has too few partitions, cluster CPU cores sit idle; if it has too many small partitions, task scheduling overhead dominates. Furthermore, operations with 'narrow dependencies' (like map, filter) execute within the same partition without data movement across the network. Operations with 'wide dependencies' (like groupBy, join, distinct) require a 'shuffle'—repartitioning and writing data across the network to new nodes. Mastering coalesce() (which merges adjacent partitions without a full shuffle) versus repartition() (which forces a full network shuffle for even redistribution) is critical for high-throughput pipelines.",
            'concrete_example': 'Calling df.coalesce(1).write.parquet(...) consolidates thousands of tiny staging partitions into a single output file without incurring a full network shuffle.',
            'deliverable': 'Benchmark report (partition_tuning.md) documenting partition counts, execution durations, and shuffle read/write bytes.',
            'exercise': 'Benchmark a 1,000,000 row synthetic dataset comparing execution time between repartition(200) and coalesce(10). Inspect partition counts using df.rdd.getNumPartitions().',
            'name': 'Data Partitions, Re-partitioning & Memory Tuning',
            'stage_num': 3,
            'task': 'Understand partition granularity, narrow vs wide dependencies, coalesce() vs repartition(), and managing data skew.',
            'verification_method': 'Verify in Spark Web UI that coalesce shows 0 shuffle bytes written whereas repartition logs network shuffle output.'
        },
        {
            'complete_explanation': "In Spark, transformations (such as select(), filter(), withColumn(), join()) are strictly lazy—they do not compute results immediately. Instead, Spark records the sequence of transformations into a Directed Acyclic Graph (DAG). Computation only begins when an 'action' (such as count(), collect(), show(), write.save()) is invoked. This allows Spark's Catalyst optimizer to analyze the entire pipeline holistically, combine filter predicates, reorder operations, and eliminate unused columns before moving any bytes.",
            'concrete_example': 'Writing 15 consecutive withColumn and filter lines runs in 0 milliseconds because Spark merely builds the DAG; only when .count() is called does execution launch.',
            'deliverable': 'A script (lazy_evaluation_proof.py) demonstrating that transformation declarations take <1ms while the terminal action triggers actual cluster computation.',
            'exercise': 'Write a pipeline chaining 5 transformations followed by an action. Place timing decorators around transformation definitions vs the action call to prove lazy evaluation.',
            'name': 'Transformations, Actions & Lazy Evaluation',
            'stage_num': 4,
            'task': 'Master lazy evaluation mechanics: distinguishing transformations (which build the DAG) from actions (which trigger job execution).',
            'verification_method': 'Confirm console logs show the action triggers stage jobs in the Spark Web UI while transformations produce no job entries.'
        },
        {
            'complete_explanation': 'Executing df.explain(extended=True) exposes four progressive plan representations: Parsed Logical Plan, Analyzed Logical Plan, Optimized Logical Plan, and Physical Plan. In physical execution, standard joins (SortMergeJoin) require heavy network shuffling to group matching keys on the same worker node. When joining a large dataset against a smaller dimension table (e.g. under 100MB), invoking broadcast(small_df) distributes a copy of the small table to every executor, allowing Spark to perform a fast BroadcastHashJoin with zero network shuffling of the large table.',
            'concrete_example': "from pyspark.sql.functions import broadcast; enriched_df = large_transactions.join(broadcast(small_merchants), 'merchant_id')",
            'deliverable': 'Plan comparison document (spark_explain_plans.md) displaying the Physical Plan transition from SortMergeJoin to BroadcastHashJoin.',
            'exercise': 'Generate a large synthetic dataset and a small lookup table. Join them using standard join, run .explain(), then repeat with broadcast(). Compare execution plans and execution times.',
            'name': 'Execution Plans & Spark Query Optimization',
            'stage_num': 5,
            'task': 'Analyze logical and physical execution plans using explain(True), and implement Broadcast Hash Joins to eliminate shuffle bottlenecks.',
            'verification_method': 'Confirm the Physical Plan in .explain() prints BroadcastHashJoin [merchant_id] and shows reduced shuffle metrics in the Web UI.'
        },
        {
            'complete_explanation': 'Production big data pipelines ingest raw structured or semi-structured data from distributed object stores (like S3 or HDFS), apply business validation and windowed aggregations (such as rolling 7-day user activity or percentile ranking), and sink partitioned output datasets in columnar formats like Apache Parquet with snappy compression. Columnar formats store data by column rather than row, enabling columnar compression and high-speed analytical queries that scan only relevant columns.',
            'concrete_example': "window_spec = Window.partitionBy('user_id').orderBy('event_time').rowsBetween(Window.unboundedPreceding, Window.currentRow); df.withColumn('cumulative_spend', sum('amount').over(window_spec))",
            'deliverable': 'Tested PySpark application (batch_etl_pipeline.py) with partitioned Parquet directory output and automated unit tests.',
            'exercise': 'Construct an end-to-end PySpark batch pipeline that loads raw event logs, computes rolling aggregations using PySpark Window functions, and writes partitioned Parquet output partitioned by year and month.',
            'name': 'Practical PySpark Batch Transformation Pipeline',
            'stage_num': 6,
            'task': 'Build an end-to-end distributed data processing pipeline ingesting raw records, applying window aggregations, and writing partitioned Parquet files.',
            'verification_method': 'Read the written Parquet directory using a fresh SparkSession and verify row counts, schema fidelity, and partition directory structure.'
        },
        {
            'complete_explanation': 'In technical interviews for data engineering and distributed systems, interviewers probe whether you understand the operational mechanics and failure modes of Spark: Driver OOM (caused by calling .collect() on large datasets), Executor OOM (caused by heavy aggregations on skewed keys or insufficient executor memory overhead), Broadcast joins exceeding memory thresholds, and skewed data remediation (salting keys with random integers to distribute hot partition keys evenly across workers).',
            'concrete_example': 'When 80% of transactions belong to a single merchant ID, standard joins cause one executor to process 80% of data and crash with OOM. Salting adds a random suffix (0-9) to the merchant ID to spread the key across 10 executors evenly.',
            'deliverable': 'A technical interview guide (spark_interview_mastery.md) with concrete code snippets and architectural trade-off comparisons.',
            'exercise': 'Document detailed technical responses for 4 core Spark interview scenarios: resolving data skew via salting, tuning spark.sql.shuffle.partitions, avoiding .collect(), and debugging executor GC pauses.',
            'name': 'Spark Performance Tuning & Technical Interview Preparation',
            'stage_num': 7,
            'task': 'Review common Spark production issues: OutOfMemory (OOM) errors, driver vs executor memory, garbage collection tuning, broadcast hazards, and interview questions.',
            'verification_method': 'Practice articulating the difference between SortMergeJoin and BroadcastHashJoin in under 60 seconds using the PREP framework.'
        }
    ],
    'testing_methods': [
        'Local SparkSession unit testing with chispa or pytest-spark fixtures',
        'Schema assertion testing validating StructType column types and nullability',
        'Partition distribution assertions verifying balanced row counts across partitions'
    ],
    'why_it_matters': 'Apache Spark is the industry standard for distributed large-scale in-memory data processing, transforming gigabytes or terabytes of structured and semi-structured data across compute clusters with high throughput.'
}

spark_repr = pprint.pformat(spark_dict, indent=4, width=120)

# Add to SKILL_SPECIFIC_CURRICULA before the closing brace of SKILL_SPECIFIC_CURRICULA
# Find SKILL_ALIASES
alias_marker = "SKILL_ALIASES: Dict[str, str] = {"
if alias_marker in text:
    replacement = "    'apache spark': 'spark',\n    'pyspark': 'spark',\n    'spark sql': 'spark',\n"
    text = text.replace(alias_marker, alias_marker + "\n" + replacement)

# Insert spark into SKILL_SPECIFIC_CURRICULA
curr_marker = "SKILL_SPECIFIC_CURRICULA: Dict[str, Dict[str, Any]] = {"
if curr_marker in text:
    spark_entry = f"    'spark': {spark_repr},\n"
    text = text.replace(curr_marker, curr_marker + "\n" + spark_entry)

with open('src/mentor/skill_curricula.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Successfully added Spark to skill_curricula.py!')
