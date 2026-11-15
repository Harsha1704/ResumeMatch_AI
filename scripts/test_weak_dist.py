import sys
sys.path.insert(0, ".")
from src.phase12f.weak_supervision import WeakLabelingSystem
from src.phase12f.data_pipeline import Phase12FDataLoader
import pandas as pd
import numpy as np

loader = Phase12FDataLoader()
job_tr, _, _ = loader.load_job_disjoint_splits()
weak_sys = WeakLabelingSystem()
L = weak_sys.apply_lfs(job_tr["resume_text"].iloc[:500].tolist(), job_tr["job_description_text"].iloc[:500].tolist())
weak_labels, weak_conf = weak_sys.aggregate_weak_labels(L)
s = pd.Series([weak_sys.labeling_functions[0][0]] * len(weak_labels))
print("Label counts:", pd.Series(weak_labels).value_counts())
print("Mean confidence:", np.mean(weak_conf))
