"""
scripts/phase12f3_1/benchmark_equal_budget_rge.py
Evaluates equal-budget RGE vs naive head truncation under exact token constraints (256 and 512 tokens).
Reports token stats, skill retention, mandatory skill retention, experience evidence retention,
omitted evidence rate, extraction failure rate, and processing latency.
"""

import time
import json
from pathlib import Path
import numpy as np
import pandas as pd
from transformers import AutoTokenizer

from src.phase12f.long_document_handler import RequirementGatedExtractor
from src.preprocessing.skill_extractor import SkillEngine
from src.preprocessing.text_cleaner import clean_text, parse_structural_features
from src.phase12f2.split_guard import load_guarded_dual_unseen_splits

REPO_ROOT = Path("D:/skillsync1")
OUT_DIR = REPO_ROOT / "experiments" / "phase12f3_1" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

class StrictTokenBudgetRGE:
    """
    RGE variant that enforces strict token budget constraints at the tokenizer level.
    """
    def __init__(self, tokenizer, base_rge: RequirementGatedExtractor):
        self.tokenizer = tokenizer
        self.base_rge = base_rge
        
    def transform_pair_strict(self, resume_text: str, jd_text: str, token_budget: int = 256) -> dict:
        t0 = time.perf_counter()
        # Initial RGE extraction
        raw_res = self.base_rge.transform_pair(resume_text, jd_text)
        structured_text = raw_res["structured_text"]
        
        # Enforce exact token budget via tokenizer
        tokens = self.tokenizer.encode(structured_text, add_special_tokens=False)
        if len(tokens) > token_budget:
            tokens = tokens[:token_budget]
            structured_text = self.tokenizer.decode(tokens)
            
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "structured_text": structured_text,
            "token_count": len(tokens),
            "latency_ms": latency_ms,
            "exp_gap": raw_res.get("exp_gap", 0.0)
        }

def evaluate_method_benchmark(
    sample_df: pd.DataFrame,
    tokenizer,
    skill_engine: SkillEngine,
    base_rge: RequirementGatedExtractor
) -> dict:
    strict_rge = StrictTokenBudgetRGE(tokenizer, base_rge)
    
    methods = {
        "truncation_256": {"tokens": [], "skill_ret": [], "mand_ret": [], "exp_ret": [], "latencies": [], "failures": 0},
        "rge_256": {"tokens": [], "skill_ret": [], "mand_ret": [], "exp_ret": [], "latencies": [], "failures": 0},
        "truncation_512": {"tokens": [], "skill_ret": [], "mand_ret": [], "exp_ret": [], "latencies": [], "failures": 0},
        "rge_512": {"tokens": [], "skill_ret": [], "mand_ret": [], "exp_ret": [], "latencies": [], "failures": 0},
    }
    
    omitted_cases_256 = []
    
    for idx, row in sample_df.iterrows():
        r_text = row["resume_text"]
        j_text = row["job_description_text"]
        
        clean_r = clean_text(r_text)
        clean_j = clean_text(j_text)
        
        full_skills_r = set(skill_engine.extract_skills(clean_r))
        full_skills_j = set(skill_engine.extract_skills(clean_j))
        full_all_skills = full_skills_r.union(full_skills_j)
        mandatory_skills = full_skills_r.intersection(full_skills_j)
        
        struct_r = parse_structural_features(r_text)
        has_exp_in_full = struct_r.get("explicit_years_exp", 0) > 0 or struct_r.get("years_experience", 0) > 0
        
        # 1. Truncation 256
        t0 = time.perf_counter()
        toks_r_256 = tokenizer.encode(r_text, add_special_tokens=False)[:128]
        toks_j_256 = tokenizer.encode(j_text, add_special_tokens=False)[:128]
        text_trunc_256 = tokenizer.decode(toks_r_256) + "\n" + tokenizer.decode(toks_j_256)
        lat_t256 = (time.perf_counter() - t0) * 1000.0
        
        # 2. Strict RGE 256
        res_rge_256 = strict_rge.transform_pair_strict(r_text, j_text, token_budget=256)
        
        # 3. Truncation 512
        t0 = time.perf_counter()
        toks_r_512 = tokenizer.encode(r_text, add_special_tokens=False)[:256]
        toks_j_512 = tokenizer.encode(j_text, add_special_tokens=False)[:256]
        text_trunc_512 = tokenizer.decode(toks_r_512) + "\n" + tokenizer.decode(toks_j_512)
        lat_t512 = (time.perf_counter() - t0) * 1000.0
        
        # 4. Strict RGE 512
        res_rge_512 = strict_rge.transform_pair_strict(r_text, j_text, token_budget=512)
        
        pairs = [
            ("truncation_256", text_trunc_256, len(toks_r_256) + len(toks_j_256), lat_t256),
            ("rge_256", res_rge_256["structured_text"], res_rge_256["token_count"], res_rge_256["latency_ms"]),
            ("truncation_512", text_trunc_512, len(toks_r_512) + len(toks_j_512), lat_t512),
            ("rge_512", res_rge_512["structured_text"], res_rge_512["token_count"], res_rge_512["latency_ms"]),
        ]
        
        curr_retentions = {}
        for m_name, m_text, m_toks, m_lat in pairs:
            m_skills = set(skill_engine.extract_skills(clean_text(m_text)))
            n_all = max(len(full_all_skills), 1)
            all_ret = len(m_skills.intersection(full_all_skills)) / n_all
            
            if len(mandatory_skills) > 0:
                mand_ret = len(m_skills.intersection(mandatory_skills)) / len(mandatory_skills)
            else:
                mand_ret = 1.0  # None required => full coverage
                
            m_struct = parse_structural_features(m_text)
            exp_found = (m_struct.get("explicit_years_exp", 0) > 0 or m_struct.get("years_experience", 0) > 0)
            exp_ret = 1.0 if (not has_exp_in_full or exp_found) else 0.0
            
            methods[m_name]["tokens"].append(m_toks)
            methods[m_name]["skill_ret"].append(all_ret)
            methods[m_name]["mand_ret"].append(mand_ret)
            methods[m_name]["exp_ret"].append(exp_ret)
            methods[m_name]["latencies"].append(m_lat)
            if len(m_skills) == 0 and len(full_all_skills) > 0:
                methods[m_name]["failures"] += 1
            curr_retentions[m_name] = all_ret
            
        # Omitted evidence check between RGE 256 and Trunc 256
        if curr_retentions["rge_256"] < curr_retentions["truncation_256"]:
            omitted_cases_256.append(int(idx))
            
    summary_report = {}
    for m_name, vals in methods.items():
        toks = np.array(vals["tokens"])
        lats = np.array(vals["latencies"])
        summary_report[m_name] = {
            "token_stats": {
                "mean": round(float(np.mean(toks)), 1),
                "median": round(float(np.median(toks)), 1),
                "p95": round(float(np.percentile(toks, 95)), 1),
                "max": int(np.max(toks))
            },
            "skill_retention_mean": round(float(np.mean(vals["skill_ret"])), 4),
            "mandatory_skill_retention_mean": round(float(np.mean(vals["mand_ret"])), 4),
            "experience_evidence_retention_mean": round(float(np.mean(vals["exp_ret"])), 4),
            "extraction_failure_rate": round(vals["failures"] / len(sample_df), 4),
            "processing_latency_ms": {
                "mean": round(float(np.mean(lats)), 2),
                "p95": round(float(np.percentile(lats, 95)), 2)
            }
        }
        
    summary_report["omitted_evidence_analysis"] = {
        "omitted_cases_count_256": len(omitted_cases_256),
        "omitted_cases_rate_256": round(len(omitted_cases_256) / len(sample_df), 4),
        "omitted_row_indices": omitted_cases_256[:10]
    }
    
    return summary_report

def main():
    print("Executing Strict Equal-Token-Budget RGE Benchmark...")
    _, val_df = load_guarded_dual_unseen_splits()
    sample_100 = val_df.head(100).copy()
    
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    base_rge = RequirementGatedExtractor(max_total_tokens=256)
    skill_engine = SkillEngine()
    
    results = evaluate_method_benchmark(sample_100, tokenizer, skill_engine, base_rge)
    
    with open(OUT_DIR / "equal_budget_rge_benchmark.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("Results saved to experiments/phase12f3_1/results/equal_budget_rge_benchmark.json")
    for m in ["truncation_256", "rge_256", "truncation_512", "rge_512"]:
        t = results[m]["token_stats"]
        print(f"[{m:15s}] Tok Mean={t['mean']}, Max={t['max']} | Skill Ret={results[m]['skill_retention_mean']*100:.2f}% | Mand Ret={results[m]['mandatory_skill_retention_mean']*100:.2f}% | Latency={results[m]['processing_latency_ms']['mean']:.2f}ms")

if __name__ == "__main__":
    main()
