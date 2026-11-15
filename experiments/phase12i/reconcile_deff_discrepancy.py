"""
Phase 12I.4: Mathematical and Empirical Reconciliation of DEFF, Manifest ICC,
and Paired Correctness-Difference DGP.
"""

import numpy as np
from scipy import stats

def analyze_dgp_and_deff():
    # Parameters
    N = 2850
    mc = 3.0
    mj = 7.5
    icc_c_latent = 0.20
    icc_j_latent = 0.10
    P_D = 0.28
    delta = 0.04
    
    n_candidates = int(N / mc) # 950
    n_jobs = int(N / mj)       # 380
    
    p10 = (P_D + delta) / 2.0 # 0.16
    p01 = (P_D - delta) / 2.0 # 0.12
    p00_11 = 1.0 - P_D        # 0.72
    
    sigma_c = np.sqrt(icc_c_latent)
    sigma_j = np.sqrt(icc_j_latent)
    sigma_e = np.sqrt(1.0 - icc_c_latent - icc_j_latent)
    
    # Run large simulation to estimate exact manifest covariances and correlations
    rng = np.random.default_rng(42)
    B = 5000
    
    # Standard assignment
    c_assignment = np.repeat(np.arange(n_candidates), 3)[:N]
    
    # Calculate exact mc* and mj*
    # If job assignment has unequal sizes due to ceiling/modulo
    j_base = np.repeat(np.arange(n_jobs), int(np.ceil(N / n_jobs)))[:N]
    
    _, c_counts = np.unique(c_assignment, return_counts=True)
    _, j_counts = np.unique(j_base, return_counts=True)
    mc_star = np.sum(c_counts**2) / N # 3.0
    mj_star = np.sum(j_counts**2) / N # 7.9958
    
    # Estimate manifest ICC directly from paired latent thresholding
    # Covariance for pairs sharing candidate only (different jobs)
    # Covariance for pairs sharing job only (different candidates)
    N_pairs_test = 100000
    
    # Pair sharing candidate: same u, different v1, v2, e1, e2
    u_c = rng.normal(0, sigma_c, size=N_pairs_test)
    v_c1 = rng.normal(0, sigma_j, size=N_pairs_test)
    v_c2 = rng.normal(0, sigma_j, size=N_pairs_test)
    e_c1 = rng.normal(0, sigma_e, size=N_pairs_test)
    e_c2 = rng.normal(0, sigma_e, size=N_pairs_test)
    
    Z_c1 = u_c + v_c1 + e_c1
    Z_c2 = u_c + v_c2 + e_c2
    
    D_c1 = np.zeros(N_pairs_test)
    D_c1[stats.norm.cdf(Z_c1) < p01] = -1.0
    D_c1[stats.norm.cdf(Z_c1) >= (p01 + p00_11)] = 1.0
    
    D_c2 = np.zeros(N_pairs_test)
    D_c2[stats.norm.cdf(Z_c2) < p01] = -1.0
    D_c2[stats.norm.cdf(Z_c2) >= (p01 + p00_11)] = 1.0
    
    var_D = np.var(D_c1)
    cov_cand = np.cov(D_c1, D_c2)[0, 1]
    icc_c_manifest_exact = cov_cand / var_D
    
    # Pair sharing job: same v, different u1, u2, e1, e2
    v_j = rng.normal(0, sigma_j, size=N_pairs_test)
    u_j1 = rng.normal(0, sigma_c, size=N_pairs_test)
    u_j2 = rng.normal(0, sigma_c, size=N_pairs_test)
    e_j1 = rng.normal(0, sigma_e, size=N_pairs_test)
    e_j2 = rng.normal(0, sigma_e, size=N_pairs_test)
    
    Z_j1 = u_j1 + v_j + e_j1
    Z_j2 = u_j2 + v_j + e_j2
    
    D_j1 = np.zeros(N_pairs_test)
    D_j1[stats.norm.cdf(Z_j1) < p01] = -1.0
    D_j1[stats.norm.cdf(Z_j1) >= (p01 + p00_11)] = 1.0
    
    D_j2 = np.zeros(N_pairs_test)
    D_j2[stats.norm.cdf(Z_j2) < p01] = -1.0
    D_j2[stats.norm.cdf(Z_j2) >= (p01 + p00_11)] = 1.0
    
    cov_job = np.cov(D_j1, D_j2)[0, 1]
    icc_j_manifest_exact = cov_job / var_D
    
    # Formula DEFF with exact manifest ICCs:
    deff_formula_exact = 1.0 + (mc_star - 1.0) * icc_c_manifest_exact + (mj_star - 1.0) * icc_j_manifest_exact
    deff_formula_balanced = 1.0 + (3.0 - 1.0) * icc_c_manifest_exact + (7.5 - 1.0) * icc_j_manifest_exact
    
    # Now simulate B whole datasets under crossed clustering to get empirical DEFF
    deltas = []
    for _ in range(B):
        u = rng.normal(0, sigma_c, size=n_candidates)
        v = rng.normal(0, sigma_j, size=n_jobs)
        j_perm = rng.permutation(j_base)
        
        latent = u[c_assignment] + v[j_perm] + rng.normal(0, sigma_e, size=N)
        probs = stats.norm.cdf(latent)
        
        D = np.zeros(N)
        D[probs < p01] = -1.0
        D[probs >= (p01 + p00_11)] = 1.0
        deltas.append(np.mean(D))
        
    var_delta_empirical = np.var(deltas)
    var_indep = (P_D - delta**2) / N
    deff_empirical = var_delta_empirical / var_indep
    
    print(f"Var(D) theoretical: {P_D - delta**2:.6f}, empirical: {var_D:.6f}")
    print(f"Mean(D) empirical: {np.mean(D_c1):.6f} (target delta: {delta})")
    print(f"P(D!=0) empirical: {np.mean(D_c1 != 0):.6f} (target P_D: {P_D})")
    print(f"Exact Manifest ICC Candidate: {icc_c_manifest_exact:.6f} (attenuation: {icc_c_manifest_exact/icc_c_latent:.4f})")
    print(f"Exact Manifest ICC Job:       {icc_j_manifest_exact:.6f} (attenuation: {icc_j_manifest_exact/icc_j_latent:.4f})")
    print(f"mc_star: {mc_star:.4f}, mj_star: {mj_star:.4f}")
    print(f"Formula DEFF (with exact manifest ICCs and mc*, mj*): {deff_formula_exact:.6f}")
    print(f"Formula DEFF (with balanced 3.0, 7.5):               {deff_formula_balanced:.6f}")
    print(f"Empirical DEFF (from {B} dataset simulations):      {deff_empirical:.6f}")
    print(f"Theoretical Latent DEFF:                             {1.0 + 2.0*0.20 + 6.5*0.10:.6f}")

if __name__ == '__main__':
    analyze_dgp_and_deff()
