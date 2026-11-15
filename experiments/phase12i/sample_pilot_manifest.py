"""
Phase 12I.4: Generate frozen 200-pair recruiter pilot sampling manifest.
Workspace: D:\\skillsync1
"""

import json
import os
import re
import hashlib
import numpy as np
import pandas as pd

def parse_exp(val):
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).lower()
    m = re.search(r'(\d+(\.\d+)?)', val_str)
    return float(m.group(1)) if m else 0.0

def clean_pii(text):
    if not isinstance(text, str):
        return ""
    # Email regex
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    # Phone regex
    text = re.sub(r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}', '[REDACTED_PHONE]', text)
    # URLs
    text = re.sub(r'https?://\S+|www\.\S+', '[REDACTED_URL]', text)
    # LinkedIn
    text = re.sub(r'linkedin\.com/\S+', '[REDACTED_LINKEDIN]', text)
    # Telegram
    text = re.sub(r'@\w{4,}', '[REDACTED_HANDLE]', text)
    return text.strip()

def build_pilot_manifest():
    print("Loading Djinni English datasets...")
    df_c = pd.read_parquet('data/external/djinni/djinni_candidate_profiles_english.parquet')
    df_j = pd.read_parquet('data/external/djinni/djinni_job_descriptions_english.parquet')
    
    # Load historical project manifests to ensure zero contamination
    manifest_dir = os.path.join("manifests", "v1")
    hist_texts = set()
    hist_hashes = set()
    for f in os.listdir(manifest_dir):
        if f.endswith(".parquet"):
            df_hist = pd.read_parquet(os.path.join(manifest_dir, f))
            for col in ['resume_text', 'job_description_text', 'clean_resume', 'clean_job_description']:
                if col in df_hist.columns:
                    for t in df_hist[col].dropna().astype(str):
                        norm = " ".join(t.lower().split())
                        hist_texts.add(norm)
                        hist_hashes.add(hashlib.sha256(norm.encode('utf-8')).hexdigest())
                        
    print(f"Loaded {len(hist_hashes)} historical text hashes for zero-contamination quarantine.")
    
    # Stratum mappings
    strata_definitions = [
        {
            "stratum": "Software Engineering / Full-Stack / Backend",
            "pairs_target": 80,
            "candidates_target": 48,
            "jobs_target": 24,
            "candidate_keywords": ['Python', 'Java', 'JavaScript', 'Node.js', '.NET'],
            "job_keywords": ['Python', 'Java', 'JavaScript', 'Node.js', '.NET']
        },
        {
            "stratum": "DevOps / SRE / Cloud Infrastructure",
            "pairs_target": 40,
            "candidates_target": 24,
            "jobs_target": 12,
            "candidate_keywords": ['DevOps'],
            "job_keywords": ['DevOps']
        },
        {
            "stratum": "Data Science / Machine Learning / Data Engineering",
            "pairs_target": 40,
            "candidates_target": 24,
            "jobs_target": 12,
            "candidate_keywords": ['Data Science'],
            "job_keywords": ['Data Science']
        },
        {
            "stratum": "Quality Assurance / Test Automation",
            "pairs_target": 20,
            "candidates_target": 12,
            "jobs_target": 6,
            "candidate_keywords": ['QA Automation', 'QA'],
            "job_keywords": ['QA Automation', 'QA']
        },
        {
            "stratum": "Technical Product / Project Management",
            "pairs_target": 20,
            "candidates_target": 12,
            "jobs_target": 6,
            "candidate_keywords": ['Project Manager'],
            "job_keywords": ['Project Manager', 'Product Manager']
        }
    ]
    
    # Filter candidates and jobs with non-trivial text
    df_c['clean_cv'] = df_c['CV'].fillna('').astype(str)
    df_j['clean_desc'] = df_j['Long Description'].fillna('').astype(str)
    
    valid_c = df_c[df_c['clean_cv'].str.len() > 150].copy()
    valid_j = df_j[df_j['clean_desc'].str.len() > 150].copy()
    
    rng = np.random.default_rng(20261114)
    all_pairs = []
    unique_candidates_global = set()
    unique_jobs_global = set()
    candidate_pair_counts = {}
    job_pair_counts = {}
    
    for s_idx, s in enumerate(strata_definitions):
        stratum_name = s["stratum"]
        n_pairs = s["pairs_target"]
        n_c = s["candidates_target"]
        n_j = s["jobs_target"]
        
        # Candidate pool
        c_pool = valid_c[
            (valid_c['Primary Keyword'].isin(s["candidate_keywords"])) & 
            (~valid_c['id'].astype(str).isin(unique_candidates_global))
        ].copy()
        
        # Job pool
        j_pool = valid_j[
            (valid_j['Primary Keyword'].isin(s["job_keywords"])) & 
            (~valid_j['id'].astype(str).isin(unique_jobs_global))
        ].copy()
        
        # Sample candidate entities
        sampled_c = c_pool.sample(n=n_c, random_state=42 + s_idx)
        # Sample job entities
        sampled_j = j_pool.sample(n=n_j, random_state=100 + s_idx)
        
        c_ids = [f"C_{cid}" for cid in sampled_c['id'].astype(str).tolist()]
        j_ids = [f"J_{jid}" for jid in sampled_j['id'].astype(str).tolist()]
        
        unique_candidates_global.update(sampled_c['id'].astype(str).tolist())
        unique_jobs_global.update(sampled_j['id'].astype(str).tolist())
        
        c_map = dict(zip(c_ids, sampled_c.to_dict('records')))
        j_map = dict(zip(j_ids, sampled_j.to_dict('records')))
        
        # Create crossed pairs respecting constraints:
        # Candidate max 3 pairs, Job max 6 pairs
        # Target pairs = n_pairs
        c_repeats = int(np.ceil(n_pairs / n_c)) # 2
        j_repeats = int(np.ceil(n_pairs / n_j)) # 4
        
        c_pair_seq = (c_ids * c_repeats)[:n_pairs]
        j_pair_seq = (j_ids * j_repeats)[:n_pairs]
        rng.shuffle(j_pair_seq)
        
        # Ensure no identical (c, j) duplicate pairs
        pair_set = set()
        for idx in range(n_pairs):
            cid = c_pair_seq[idx]
            jid = j_pair_seq[idx]
            # If collision, swap with next
            if (cid, jid) in pair_set:
                for alt_idx in range(idx + 1, n_pairs):
                    if (cid, j_pair_seq[alt_idx]) not in pair_set:
                        j_pair_seq[idx], j_pair_seq[alt_idx] = j_pair_seq[alt_idx], j_pair_seq[idx]
                        jid = j_pair_seq[idx]
                        break
            pair_set.add((cid, jid))
            
            # Text snippets
            c_row = c_map[cid]
            j_row = j_map[jid]
            
            raw_cv = clean_pii(c_row['clean_cv'])
            raw_jd = clean_pii(j_row['clean_desc'])
            
            # Check zero-contamination against historical hashes
            c_norm = " ".join(raw_cv.lower().split())
            j_norm = " ".join(raw_jd.lower().split())
            c_hash = hashlib.sha256(c_norm.encode('utf-8')).hexdigest()
            j_hash = hashlib.sha256(j_norm.encode('utf-8')).hexdigest()
            
            assert c_hash not in hist_hashes, f"Contamination detected on candidate {cid}!"
            assert j_hash not in hist_hashes, f"Contamination detected on job {jid}!"
            
            pair_obj = {
                "pair_id": f"PILOT_P_{len(all_pairs) + 1:04d}",
                "stratum": stratum_name,
                "candidate_id": cid,
                "job_id": jid,
                "candidate_position": str(c_row.get('Position', '')),
                "candidate_experience_years": parse_exp(c_row.get('Experience Years', 0)),
                "candidate_cv_snippet": raw_cv[:500] + ("..." if len(raw_cv) > 500 else ""),
                "candidate_sha256": c_hash,
                "job_position": str(j_row.get('Position', '')),
                "job_experience_years_required": parse_exp(j_row.get('Exp Years', 0)),
                "job_description_snippet": raw_jd[:500] + ("..." if len(raw_jd) > 500 else ""),
                "job_sha256": j_hash,
                "model_predictions_blinded": True,
                "peer_annotations_blinded": True,
                "evidence_required": True
            }
            all_pairs.append(pair_obj)
            candidate_pair_counts[cid] = candidate_pair_counts.get(cid, 0) + 1
            job_pair_counts[jid] = job_pair_counts.get(jid, 0) + 1
            
    print(f"Generated {len(all_pairs)} pilot pairs.")
    print(f"Unique candidates: {len(unique_candidates_global)} (Target: 120)")
    print(f"Unique jobs: {len(unique_jobs_global)} (Target: 60)")
    print(f"Max pairs per candidate: {max(candidate_pair_counts.values())} (Constraint <= 3)")
    print(f"Max pairs per job: {max(job_pair_counts.values())} (Constraint <= 6)")
    
    assert len(all_pairs) == 200
    assert len(unique_candidates_global) == 120
    assert len(unique_jobs_global) == 60
    assert max(candidate_pair_counts.values()) <= 3
    assert max(job_pair_counts.values()) <= 6
    
    manifest_data = {
        "phase": "12I.4",
        "created_at": "2026-11-14T20:26:00Z",
        "pilot_name": "Frozen 200-Pair Recruiter Pilot Sampling Manifest",
        "total_pairs": len(all_pairs),
        "total_unique_candidates": len(unique_candidates_global),
        "total_unique_jobs": len(unique_jobs_global),
        "candidate_cluster_cap": 3,
        "job_cluster_cap": 6,
        "cluster_statistics": {
            "mean_candidate_cluster_mc": round(200.0 / 120.0, 4),
            "max_candidate_cluster": max(candidate_pair_counts.values()),
            "mean_job_cluster_mj": round(200.0 / 60.0, 4),
            "max_job_cluster": max(job_pair_counts.values())
        },
        "domain_distribution": {
            "Software Engineering / Full-Stack / Backend": 80,
            "DevOps / SRE / Cloud Infrastructure": 40,
            "Data Science / Machine Learning / Data Engineering": 40,
            "Quality Assurance / Test Automation": 20,
            "Technical Product / Project Management": 20
        },
        "quarantine_and_blinding_status": {
            "historical_manifest_overlap_count": 0,
            "model_predictions_exposed": False,
            "peer_ratings_exposed": False,
            "quarantine_rule": "These 200 pilot pairs are permanently quarantined and excluded from all model training, threshold tuning, and the final frozen evaluation benchmark."
        },
        "pairs": all_pairs
    }
    
    out_path = os.path.join("experiments", "phase12i", "results", "phase12i4_pilot_sampling_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Sampling manifest written to: {out_path}")

if __name__ == "__main__":
    build_pilot_manifest()
