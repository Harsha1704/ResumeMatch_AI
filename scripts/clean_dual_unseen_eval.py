import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, ".")
from src.phase12f.data_pipeline import Phase12FDataLoader
from src.phase12f.models import HybridStackingClassifier
from src.phase12f.evaluation import compute_comprehensive_metrics
from src.features.feature_pipeline import ResumeJobFeaturePipeline
from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text, parse_structural_features

loader = Phase12FDataLoader()
dual_tr, dual_val = loader.load_dual_unseen_splits()
print(f"Clean Dual-Unseen Train: {len(dual_tr)} rows")
print(f"Clean Dual-Unseen Val:   {len(dual_val)} rows")

# Verify 0 entity overlap
r_tr = set(dual_tr["resume_text"])
r_vl = set(dual_val["resume_text"])
j_tr = set(dual_tr["job_description_text"])
j_vl = set(dual_val["job_description_text"])

assert len(r_tr.intersection(r_vl)) == 0, "Resume overlap in dual-unseen!"
assert len(j_tr.intersection(j_vl)) == 0, "Job overlap in dual-unseen!"
print("Verified zero entity overlap between dual_tr and dual_val.")

# Load cached embeddings
cached_data = np.load("results/phase12b_embeddings/minilm_l6_v2_cache.npz", allow_pickle=True)
res_hashes = cached_data["res_hashes"]
job_hashes = cached_data["job_hashes"]
res_emb_dict = {h: cached_data[f"res_{h}"] for h in res_hashes}
job_emb_dict = {h: cached_data[f"job_{h}"] for h in job_hashes}

import hashlib
def hash_text(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode("utf-8")).hexdigest()[:16]

from sentence_transformers import SentenceTransformer
encoder = SentenceTransformer("all-MiniLM-L6-v2")

def get_res_emb(text: str) -> np.ndarray:
    h = hash_text(text)
    if h in res_emb_dict:
        return res_emb_dict[h]
    return encoder.encode(text, show_progress_bar=False)

def get_job_emb(text: str) -> np.ndarray:
    h = hash_text(text)
    if h in job_emb_dict:
        return job_emb_dict[h]
    return encoder.encode(text, show_progress_bar=False)

def build_sbert_pair_features(df: pd.DataFrame) -> np.ndarray:
    feats = []
    for _, row in df.iterrows():
        u = get_res_emb(row["resume_text"])
        v = get_job_emb(row["job_description_text"])
        cos_sim = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))
        feats.append(np.concatenate([u, v, u * v, np.abs(u - v), [cos_sim]]))
    return np.array(feats, dtype=np.float32)

skill_engine = SkillEngine()
def extract_25_dense_features(resumes, jobs):
    rows = []
    for r_raw, j_raw in zip(resumes, jobs):
        r_clean = clean_text(r_raw)
        j_clean = clean_text(j_raw)
        r_struct = parse_structural_features(r_raw)
        j_struct = parse_structural_features(j_raw)
        r_skills = set(skill_engine.extract_skills(r_clean))
        j_skills = set(skill_engine.extract_skills(j_clean))
        n_j_skills = max(len(j_skills), 1)
        skill_overlap = len(r_skills.intersection(j_skills))
        skill_overlap_ratio = skill_overlap / n_j_skills
        jaccard = skill_overlap / max(len(r_skills.union(j_skills)), 1)
        r_words = set(r_clean.split())
        j_words = set(j_clean.split())
        word_overlap = len(r_words.intersection(j_words)) / max(len(j_words), 1)
        r_chars = float(len(r_raw))
        j_chars = float(len(j_raw))
        r_wcnt = float(len(r_words))
        j_wcnt = float(len(j_words))
        char_ratio = r_chars / max(j_chars, 1.0)
        word_ratio = r_wcnt / max(j_wcnt, 1.0)
        r_exp = float(r_struct.get("experience_years", 0))
        j_exp = float(j_struct.get("experience_years", 0))
        exp_diff = r_exp - j_exp
        exp_ratio = r_exp / max(j_exp, 1.0)
        r_has_proj = 1.0 if r_struct.get("project_count", 0) > 0 else 0.0
        r_has_cert = 1.0 if r_struct.get("cert_count", 0) > 0 else 0.0
        r_has_edu = 1.0 if r_struct.get("has_education", False) else 0.0
        senior_mismatch = 1.0 if (j_exp >= 5.0 and r_exp < 3.0) else 0.0
        dense_vec = [
            skill_overlap_ratio, jaccard, word_overlap,
            float(skill_overlap), float(len(r_skills)), float(len(j_skills)),
            r_chars, j_chars, char_ratio, r_wcnt, j_wcnt, word_ratio,
            r_exp, j_exp, exp_diff, exp_ratio,
            r_has_proj, r_has_cert, r_has_edu,
            float(r_struct.get("project_count", 0)),
            float(r_struct.get("cert_count", 0)),
            1.0 if r_exp >= j_exp else 0.0,
            1.0 if skill_overlap >= 3 else 0.0,
            float(len(r_skills.difference(j_skills))),
            senior_mismatch
        ]
        rows.append(dense_vec)
    return np.array(rows, dtype=np.float32)

X_dtr_sbert = build_sbert_pair_features(dual_tr)
X_dvl_sbert = build_sbert_pair_features(dual_val)
X_dtr_dense = extract_25_dense_features(dual_tr["resume_text"].tolist(), dual_tr["job_description_text"].tolist())
X_dvl_dense = extract_25_dense_features(dual_val["resume_text"].tolist(), dual_val["job_description_text"].tolist())

X_dtr_all = np.hstack([X_dtr_sbert, X_dtr_dense])
X_dvl_all = np.hstack([X_dvl_sbert, X_dvl_dense])
y_dtr = dual_tr["label"].values
y_dvl = dual_val["label"].values

print("\n--- Clean Uncontaminated Dual-Unseen Evaluation ---")
# 1. Clean Logistic Regression
scaler = StandardScaler()
X_tr_sc = scaler.fit_transform(X_dtr_all)
X_vl_sc = scaler.transform(X_dvl_all)
lr = LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced", random_state=42)
lr.fit(X_tr_sc, y_dtr)
p_lr = lr.predict(X_vl_sc)
prob_lr = lr.predict_proba(X_vl_sc)
m_lr = compute_comprehensive_metrics(y_dvl, p_lr, prob_lr)
print(f"Clean LogReg on Dual-Unseen Val: Acc={m_lr['accuracy']:.4f}, Macro F1={m_lr['macro_f1']:.4f}, Bal Acc={m_lr['balanced_accuracy']:.4f}")

# 2. Clean Hybrid Stacking
hyb = HybridStackingClassifier(random_state=42)
hyb.fit(X_dtr_all, y_dtr)
p_hyb = hyb.predict(X_dvl_all)
prob_hyb = hyb.predict_proba(X_dvl_all)
m_hyb = compute_comprehensive_metrics(y_dvl, p_hyb, prob_hyb)
print(f"Clean Hybrid on Dual-Unseen Val: Acc={m_hyb['accuracy']:.4f}, Macro F1={m_hyb['macro_f1']:.4f}, Bal Acc={m_hyb['balanced_accuracy']:.4f}")
