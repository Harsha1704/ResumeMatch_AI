"""
Phase 12I.2: Independent Statistical Power Reproduction & Sensitivity Simulation
Workspace: D:\\skillsync1
Roles: Principal Biostatistician, Statistical Simulation Engineer

Performs crossed random-effects Monte Carlo simulation for paired model comparisons
under candidate and job clustering with two-way cluster-robust variance estimation.
"""

import json
import os
import sys
import time
import numpy as np
from scipy import stats

def simulate_crossed_clustered_paired_power(
    N=2850,
    mc=3.0,
    mj=7.5,
    icc_c=0.20,
    icc_j=0.10,
    P_D=0.28,
    delta=0.04,
    B=2000,
    alpha=0.05,
    seed=42,
    unequal_clusters=False,
    class_distribution=None,
    class_deltas=None
):
    """
    Simulates statistical power for testing H0: Delta = 0 vs H1: Delta = delta
    on paired binary accuracy indicators with crossed candidate and job clustering.
    
    Uses two-way cluster-robust variance estimation (Cameron, Gelbach & Miller, 2011).
    """
    rng = np.random.default_rng(seed)
    
    # 1. Determine number of clusters
    n_candidates = int(np.round(N / mc))
    n_jobs = int(np.round(N / mj))
    
    # 2. Assign pairs to clusters
    if not unequal_clusters:
        # Standard balanced assignment
        c_assignment = np.repeat(np.arange(n_candidates), int(np.ceil(N / n_candidates)))[:N]
        j_assignment = np.repeat(np.arange(n_jobs), int(np.ceil(N / n_jobs)))[:N]
        # Shuffle job assignment to ensure crossed structure
        rng.shuffle(j_assignment)
    else:
        # Unequal cluster sizes via Dirichlet / Multinomial proportions
        c_weights = rng.gamma(shape=2.0, scale=1.0, size=n_candidates)
        c_weights /= c_weights.sum()
        c_assignment = rng.choice(n_candidates, size=N, p=c_weights)
        
        j_weights = rng.gamma(shape=2.0, scale=1.0, size=n_jobs)
        j_weights /= j_weights.sum()
        j_assignment = rng.choice(n_jobs, size=N, p=j_weights)
        
    # Variance components
    # Total variance of latent difference D* = sigma_c^2 + sigma_j^2 + sigma_e^2 = 1.0
    sigma_c = np.sqrt(icc_c)
    sigma_j = np.sqrt(icc_j)
    sigma_e = np.sqrt(max(1.0 - icc_c - icc_j, 0.01))
    
    # Discordance probabilities under H1:
    # P(Model 1 correct, Model 0 wrong) = p10
    # P(Model 1 wrong, Model 0 correct) = p01
    # P_D = p10 + p01
    # delta = p10 - p01
    p10 = (P_D + delta) / 2.0
    p01 = (P_D - delta) / 2.0
    p00_or_11 = 1.0 - P_D
    
    if p01 < 0 or p10 > 1:
        raise ValueError(f"Incompatible P_D ({P_D}) and delta ({delta})")
        
    # Analytical Design Effect (DEFF)
    # DEFF = 1 + (m_c* - 1)*icc_c + (m_j* - 1)*icc_j
    # where m* = sum(m^2) / sum(m)
    _, c_counts = np.unique(c_assignment, return_counts=True)
    _, j_counts = np.unique(j_assignment, return_counts=True)
    mc_star = np.sum(c_counts**2) / N
    mj_star = np.sum(j_counts**2) / N
    deff_exact = 1.0 + (mc_star - 1.0) * icc_c + (mj_star - 1.0) * icc_j
    
    # Critical value for two-sided test
    z_crit = stats.norm.ppf(1.0 - alpha / 2.0)
    
    rejections = 0
    t_stats = np.zeros(B)
    deltas = np.zeros(B)
    se_estimates = np.zeros(B)
    
    for b in range(B):
        # Latent cluster random effects
        u = rng.normal(0, sigma_c, size=n_candidates)
        v = rng.normal(0, sigma_j, size=n_jobs)
        
        # Latent pair score
        latent = u[c_assignment] + v[j_assignment] + rng.normal(0, sigma_e, size=N)
        
        # Transform latent score to probabilities via logistic transform centered at log-odds of discordance
        # Latent thresholding to generate discrete outcomes {-1, 0, +1}
        # D_i in {-1, 0, 1}
        # Expected value must be delta, probability of non-zero must be P_D
        probs = stats.norm.cdf(latent)
        
        # Thresholds:
        # [0, p01] -> -1 (Model 0 correct, Model 1 wrong)
        # [p01, p01 + p00_or_11] -> 0 (Concordant)
        # [p01 + p00_or_11, 1.0] -> +1 (Model 1 correct, Model 0 wrong)
        D = np.zeros(N)
        D[probs < p01] = -1.0
        D[probs >= (p01 + p00_or_11)] = 1.0
        
        delta_hat = np.mean(D)
        deltas[b] = delta_hat
        
        # Two-way cluster robust variance (Cameron, Gelbach, & Miller, 2011)
        resid = D - delta_hat
        
        # Candidate cluster sum
        cand_sums = np.bincount(c_assignment, weights=resid)
        V_c = np.sum(cand_sums**2) / (N * N)
        
        # Job cluster sum
        job_sums = np.bincount(j_assignment, weights=resid)
        V_j = np.sum(job_sums**2) / (N * N)
        
        # Intersection sum (individual pairs)
        V_cj = np.sum(resid**2) / (N * N)
        
        V_twoway = V_c + V_j - V_cj
        if V_twoway <= 0:
            V_twoway = V_c + V_j # Fallback if small negative sample variance
            
        se_twoway = np.sqrt(V_twoway)
        se_estimates[b] = se_twoway
        
        t_stat = delta_hat / se_twoway
        t_stats[b] = t_stat
        
        if np.abs(t_stat) >= z_crit:
            rejections += 1
            
    power = rejections / B
    mcse = np.sqrt(power * (1.0 - power) / B)
    
    # Analytical power approximation for comparison
    se_analytical = np.sqrt((P_D - delta**2) / N * deff_exact)
    z_analytical = (delta / se_analytical) - z_crit
    power_analytical = stats.norm.cdf(z_analytical)
    
    return {
        "N": N,
        "n_candidates": int(n_candidates),
        "n_jobs": int(n_jobs),
        "mc_mean": float(N / n_candidates),
        "mj_mean": float(N / n_jobs),
        "mc_star": float(mc_star),
        "mj_star": float(mj_star),
        "icc_c": icc_c,
        "icc_j": icc_j,
        "P_D": P_D,
        "delta": delta,
        "deff_exact": float(deff_exact),
        "power_simulated": float(power),
        "mcse": float(mcse),
        "power_analytical": float(power_analytical),
        "mean_se_simulated": float(np.mean(se_estimates)),
        "se_analytical": float(se_analytical),
        "unequal_clusters": unequal_clusters
    }

def run_full_reproduction():
    print("Starting Phase 12I.2 Statistical Power Reproduction & Sensitivity Simulation...")
    t0 = time.time()
    
    sample_sizes = [1500, 2000, 2500, 2850, 3500]
    
    # 1. Five Core Protocol Scenarios
    core_scenarios = {
        "Baseline": {"icc_c": 0.20, "icc_j": 0.10, "P_D": 0.28, "delta": 0.04},
        "Optimistic": {"icc_c": 0.10, "icc_j": 0.05, "P_D": 0.28, "delta": 0.04},
        "Pessimistic": {"icc_c": 0.30, "icc_j": 0.15, "P_D": 0.28, "delta": 0.04},
        "Low_Discordance": {"icc_c": 0.20, "icc_j": 0.10, "P_D": 0.22, "delta": 0.04},
        "High_Discordance": {"icc_c": 0.20, "icc_j": 0.10, "P_D": 0.35, "delta": 0.04}
    }
    
    reproduction_results = {}
    
    for s_name, params in core_scenarios.items():
        reproduction_results[s_name] = {}
        for N in sample_sizes:
            print(f"  Running scenario {s_name} at N={N}...")
            res = simulate_crossed_clustered_paired_power(
                N=N,
                mc=3.0,
                mj=7.5,
                icc_c=params["icc_c"],
                icc_j=params["icc_j"],
                P_D=params["P_D"],
                delta=params["delta"],
                B=2000,
                seed=42 + N
            )
            reproduction_results[s_name][f"N_{N}"] = res
            
    # 2. Sensitivity: Unequal Cluster Sizes (Gamma/Dirichlet distributed sizes)
    print("  Running Unequal Cluster Size Sensitivity...")
    unequal_results = {}
    for N in sample_sizes:
        res = simulate_crossed_clustered_paired_power(
            N=N,
            mc=3.0,
            mj=7.5,
            icc_c=0.20,
            icc_j=0.10,
            P_D=0.28,
            delta=0.04,
            B=2000,
            seed=100 + N,
            unequal_clusters=True
        )
        unequal_results[f"N_{N}"] = res
        
    # 3. Sensitivity: 3x3 Full Grid (Candidate ICC x Job ICC) at N=2850
    print("  Running 3x3 ICC Grid Sensitivity at N=2850...")
    icc_grid_results = []
    for icc_c in [0.10, 0.20, 0.30]:
        for icc_j in [0.05, 0.10, 0.15]:
            for P_D in [0.22, 0.28, 0.35]:
                res = simulate_crossed_clustered_paired_power(
                    N=2850,
                    mc=3.0,
                    mj=7.5,
                    icc_c=icc_c,
                    icc_j=icc_j,
                    P_D=P_D,
                    delta=0.04,
                    B=1000,
                    seed=200 + int(icc_c*100) + int(icc_j*100) + int(P_D*100)
                )
                icc_grid_results.append({
                    "icc_candidate": icc_c,
                    "icc_job": icc_j,
                    "P_D": P_D,
                    "deff": res["deff_exact"],
                    "power_simulated": res["power_simulated"],
                    "mcse": res["mcse"],
                    "power_analytical": res["power_analytical"]
                })

    # Save to JSON
    output_artifact = {
        "phase": "12I.2",
        "timestamp": "2026-11-14T08:24:00Z",
        "description": "Independent reproduction and sensitivity analysis of crossed-clustered power simulations",
        "simulation_parameters": {
            "B": 2000,
            "alpha": 0.05,
            "test_type": "Two-way cluster-robust Wald test on paired difference",
            "null_hypothesis": "H0: Delta = 0.00",
            "alternative_hypothesis": "H1: Delta = 0.04",
            "rejection_rule": "|Z_twoway| >= 1.95996"
        },
        "core_scenarios": reproduction_results,
        "unequal_clusters_scenario": unequal_results,
        "icc_grid_sensitivity_N2850": icc_grid_results,
        "elapsed_seconds": time.time() - t0
    }
    
    out_dir = os.path.join("experiments", "phase12i", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "phase12i2_power_reproduction.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_artifact, f, indent=2)
        
    print(f"Reproduction complete in {time.time()-t0:.2f}s. Artifact saved to {out_path}.")

if __name__ == "__main__":
    run_full_reproduction()
