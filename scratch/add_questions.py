import pprint

ml_data_leakage = {
    'id': 'tb_ml_03',
    'topic': 'Machine Learning',
    'difficulty': 'Medium',
    'question': 'What is Data Leakage in Machine Learning, how does it occur during feature preprocessing and cross-validation, and how do you definitively prevent it?',
    'recommended_framework': 'WHAT-WHY-HOW',
    'short_answer': 'Data leakage occurs when information from outside the training partition leaks into the model during training or feature engineering, resulting in artificially inflated validation scores that collapse on unseen test data. It is prevented by strictly isolating feature transformers inside cross-validation folds using scikit-learn Pipelines.',
    'simpler_answer': 'Data leakage happens when a model accidentally learns from information it would not have in the real world—like calculating normalization statistics or TF-IDF vocabularies on the entire dataset before splitting. To prevent it, always fit scalers and encoders only on training folds, never on validation or test sets.',
    'detailed_answer': 'Data leakage occurs when information from the target variable or evaluation partition inadvertently enters the feature engineering, imputation, or training pipeline. A classic leakage vector is global preprocessing: fitting a `StandardScaler`, `SimpleImputer`, or `TfidfVectorizer` on the entire dataset before performing a train/test split or cross-validation. When this happens, the global mean, variance, or vocabulary contains signals from validation records, exposing test distributions to learned estimators and producing misleadingly optimistic CV metrics. In production, this causes generalization failure. To prevent leakage definitively: 1) Strict Split Hygiene: Split datasets into train, validation, and test partitions before any data transformation; 2) Pipeline Encapsulation: Wrap feature transformers, scalers, and estimators inside scikit-learn `Pipeline` or `ColumnTransformer` objects; 3) Fold-Level Isolation: When performing GroupKFold or StratifiedKFold cross-validation, instantiate fresh, unfitted pipelines for each fold so that `fit` executes strictly on fold-train records while fold-val records receive only `transform`.',
    'curated_answer': 'Data leakage occurs when information from outside the training partition leaks into model training. The definitive engineering defense is wrapping feature transformers inside scikit-learn Pipelines so that fitting occurs strictly inside cross-validation training folds.',
    'why_this_works': 'Interviewers ask this to separate theoretical ML students from experienced production engineers. This answer succeeds by explaining exact leakage vectors (global scaler fitting, cross-fold contamination) and citing the industry-standard architectural solution: scikit-learn Pipeline encapsulation.',
    'code_snippet': 'from sklearn.pipeline import Pipeline\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.linear_model import LogisticRegression\nfrom sklearn.model_selection import cross_val_score\n\n# Leakage-safe pipeline: Scaler is fitted ONLY inside each CV train fold\npipeline = Pipeline([\n    ("scaler", StandardScaler()),\n    ("classifier", LogisticRegression())\n])\n\nscores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring="macro_f1")',
    'common_mistakes': [
        'Calling `fit_transform()` on the entire dataset before train_test_split() or cross_val_score().',
        'Imputing missing values with global column means calculated across all data partitions.',
        'Using target variables or future timestamps during feature extraction.'
    ],
    'important_concepts': ['Data Leakage', 'Train/Test Isolation', 'Fold Preprocessing Isolation', 'scikit-learn Pipeline', 'GroupKFold'],
    'interview_tips': [
        'Explicitly distinguish between train leakage (using test distributions) and target leakage (using features proxying future ground truth).',
        'Emphasize that a Pipeline guarantees `fit` is called on training folds and only `transform` on validation/test folds.'
    ],
    'key_points': [
        'Data leakage inflates validation scores and causes model failure in production.',
        'Global preprocessing on full datasets is a primary leakage source.',
        'scikit-learn Pipelines encapsulate transformers to guarantee fold-level isolation.'
    ],
    'follow_up_questions': [
        {
            'question': 'What is target leakage and how does it differ from train-test leakage?',
            'reference_answer': 'Target leakage occurs when a predictor feature contains information about the target variable that would not be available at the time of inference in production—such as an internal transaction approval flag included in a fraud prediction model. Train-test leakage occurs when evaluation data contaminates the training feature distribution. Both produce artificially high offline validation scores that fail in production.'
        }
    ],
    'examples': 'Fitting TF-IDF on all 5,000 resume-job pairs before CV versus fitting TF-IDF on only the 4,000 fold-training records.',
    'source_reference': 'Scikit-Learn Preprocessing & Cross-Validation Guide',
    'step_by_step_explanation': [
        {
            'step': 'Step 1: Define Data Leakage & Engineering Risks',
            'complete_explanation': 'Explain that data leakage introduces evaluation bias by allowing target or test signals to contaminate the model training phase.',
            'reasoning': 'Proves awareness of production risks where high offline scores collapse online.'
        },
        {
            'step': 'Step 2: Contrast Global Preprocessing with Fold-Level Preprocessing',
            'complete_explanation': 'Demonstrate why fitting scalers or vectorizers globally exposes validation text distributions to learned preprocessing.',
            'reasoning': 'Shows granular understanding of statistical contamination.'
        },
        {
            'step': 'Step 3: Implement Pipeline Encapsulation Defense',
            'complete_explanation': 'Explain how scikit-learn Pipeline objects guarantee that transformers are fitted strictly on training data during each cross-validation fold.',
            'reasoning': 'Provides concrete engineering implementation.'
        }
    ]
}

sys_caching = {
    'id': 'tb_sys_01',
    'topic': 'System Design',
    'difficulty': 'Medium',
    'question': 'How do you design a high-throughput, low-latency caching layer for a web application using Redis, and what cache invalidation strategies (Cache-Aside, Write-Through, Write-Behind) do you apply?',
    'recommended_framework': 'WHAT-WHY-HOW',
    'short_answer': 'A caching layer places an in-memory datastore (like Redis) between the application backend and relational database to serve hot read traffic in sub-milliseconds. Common invalidation patterns include Cache-Aside (lazy loading on misses), Write-Through (synchronously updating DB and cache), and Write-Behind (asynchronously batching DB writes).',
    'simpler_answer': 'Caching keeps frequently requested data in fast RAM so you do not hit the slower disk-based database for every request. With Cache-Aside, the app checks Redis first; if missing, it reads from SQL and saves the result in Redis with an expiration time (TTL).',
    'detailed_answer': 'Designing a high-throughput caching layer with Redis optimizes read-heavy web applications by avoiding expensive database disk I/O and query compilation. Architecture patterns include: 1) Cache-Aside (Lazy Loading): The application queries Redis first; on a cache miss, it reads from the primary database, populates Redis with an explicit Time-To-Live (TTL), and returns data to the client. This handles read spikes cleanly without caching unused records; 2) Write-Through: The application writes updates synchronously to the cache and the primary database simultaneously, guaranteeing cache freshness at the cost of higher write latency; 3) Write-Behind (Write-Back): Updates are written immediately to Redis RAM and acknowledged, while an asynchronous background worker batches updates into the relational database, providing maximum write throughput but risking data loss if Redis crashes before flushing. Critical failure mitigations include: Eviction Policies (e.g. volatile-lru to prevent out-of-memory errors), Cache Stampede Protection (using mutex locks or probabilistic early expiration to prevent thousands of concurrent requests from hammering the database when a popular key expires), and Defensive TTL Expiration on all keys.',
    'curated_answer': 'A caching layer uses in-memory stores like Redis to offload databases. Cache-Aside balances low memory overhead with lazy loading, while Write-Through prioritizes transactional freshness. Setting explicit TTLs and LRU eviction policies is mandatory for production stability.',
    'why_this_works': 'System design interviewers look for trade-off awareness rather than just mentioning Redis. This answer succeeds by clearly comparing Cache-Aside, Write-Through, and Write-Behind, and explicitly addressing operational hazards like Cache Stampedes and memory eviction.',
    'code_snippet': 'import redis\nimport json\n\nr = redis.Redis(host="localhost", port=6379, db=0)\n\ndef get_user_profile(user_id: int):\n    cache_key = f"user:profile:{user_id}"\n    cached = r.get(cache_key)\n    if cached:\n        return json.loads(cached)  # Cache hit (<1ms)\n    \n    # Cache miss: fetch from PostgreSQL\n    profile = db.query("SELECT * FROM users WHERE id = %s", (user_id,))\n    if profile:\n        r.setex(cache_key, 3600, json.dumps(profile))  # TTL 1 hour\n    return profile',
    'common_mistakes': [
        'Setting no TTL on cache keys, causing Redis memory to grow unbounded until OOM termination.',
        'Assuming Redis eliminates the need for database indexing; unindexed cache misses will still bring down the database.',
        'Failing to handle Cache Stampede (thundering herd problem) when high-traffic keys expire.'
    ],
    'important_concepts': ['In-Memory Caching', 'Cache-Aside Pattern', 'Write-Through vs Write-Behind', 'Cache Stampede', 'Time-To-Live (TTL)', 'Redis LRU Eviction'],
    'interview_tips': [
        'Always mention Time-To-Live (TTL) as a baseline safety net against stale data and unbounded memory growth.',
        'Differentiate between Read-Heavy vs Write-Heavy architectures when recommending a caching pattern.'
    ],
    'key_points': [
        'Redis delivers sub-millisecond responses by serving requests from RAM.',
        'Cache-Aside lazily loads on demand; Write-Through maintains synchronous freshness.',
        'Defensive configurations require explicit TTLs, LRU eviction, and stampede guards.'
    ],
    'follow_up_questions': [
        {
            'question': 'How do you prevent a Cache Stampede (Thundering Herd) when a key expires under heavy traffic?',
            'reference_answer': 'To prevent a cache stampede: 1) Implement distributed mutex locking (Redlock or SETNX) so only one worker queries the database while others wait; 2) Employ probabilistic early expiration (XFetch algorithm) where background workers refresh the key before it strictly expires; 3) Use asynchronous background refresh jobs for predictable high-traffic keys.'
        }
    ],
    'examples': 'Caching rendered candidate compatibility reports in Redis with 1-hour TTLs to offload scikit-learn model inference during repeated page reloads.',
    'source_reference': 'Redis Architecture & Caching Design Best Practices',
    'step_by_step_explanation': [
        {
            'step': 'Step 1: Frame the Operational Problem & Performance Target',
            'complete_explanation': 'State the latency objectives (sub-5ms) and explain how RAM-based key-value lookups eliminate database disk I/O bottlenecks.',
            'reasoning': 'Grounds caching architecture in concrete latency and throughput benchmarks.'
        },
        {
            'step': 'Step 2: Contrast Cache-Aside with Write-Through Strategies',
            'complete_explanation': 'Compare read/write trade-offs: Cache-Aside loads on demand with minimal memory footprint; Write-Through maintains instant consistency.',
            'reasoning': 'Proves technical trade-off evaluation capabilities.'
        },
        {
            'step': 'Step 3: Establish Operational Resilience Safeguards',
            'complete_explanation': 'Implement mandatory TTL expiration, LRU memory eviction policies, and distributed mutex locking against cache stampedes.',
            'reasoning': 'Demonstrates production reliability and defense-in-depth engineering.'
        }
    ]
}

with open('src/interview/question_bank.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Check if tb_ml_03 already in question_bank
if 'tb_ml_03' in text:
    print('tb_ml_03 already exists!')
else:
    # Format and insert before HR_QUESTION_BANK
    q1_str = pprint.pformat(ml_data_leakage, indent=4, width=120)
    q2_str = pprint.pformat(sys_caching, indent=4, width=120)
    
    marker = "HR_QUESTION_BANK: List"
    idx = text.find(marker)
    if idx != -1:
        # Find closing bracket of TECHNICAL_QUESTION_BANK
        # Just before marker
        sub = text[:idx]
        last_bracket = sub.rfind("]")
        if last_bracket != -1:
            insert_content = f",\n    {q1_str},\n    {q2_str}\n]"
            text = text[:last_bracket] + insert_content + text[last_bracket+1:]
            with open('src/interview/question_bank.py', 'w', encoding='utf-8') as f:
                f.write(text)
            print('Successfully added tb_ml_03 and tb_sys_01 to TECHNICAL_QUESTION_BANK!')
