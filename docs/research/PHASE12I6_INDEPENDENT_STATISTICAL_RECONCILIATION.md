# RESUMEMATCH AI — PHASE 12I.6: INDEPENDENT STATISTICAL RECONCILIATION REPORT
**Workspace:** `D:\skillsync1`  
**Phase:** 12I.6  
**Auditor Roles:** Principal Biostatistician, Statistical Simulation Auditor, Data Governance Engineer  
**Date:** November 14, 2026  
**Final Audit Verdict:** **`STATISTICAL RECONCILIATION PASSED — PILOT HANDOFF READY`**

---

## 1. Executive Summary & Objective

Phase 12I.6 delivers the independent, definitive biostatistical reconciliation of the crossed-cluster Design Effect ($\text{DEFF}$) and variance estimator for the ResumeMatch AI evaluation benchmark. 

In accordance with strict audit requirements:
1. **Mathematical Derivation of Crossed-Cluster Variance:** We rigorously derived the population variance of the paired correctness-difference mean $\bar{D}$ from first principles under the crossed candidate/job random-effects model with the exact benchmark incidence structure.
2. **Exact Formula Recalculation:** With candidate manifest ICC $\rho_c = 0.142610$, job manifest ICC $\rho_j = 0.075726$, candidate cluster size $m_c^* = 3.0000$, and job cluster size $m_j^* = 7.533333$, the exact population DEFF is:
   $$\text{DEFF}_{\text{theoretical}} = \mathbf{1.779963} \approx \mathbf{1.7800}$$
3. **Resolution of Simulation Discrepancy:** We audited the previous reported empirical variance ratio of $1.7367$ (from $B = 5,000$ runs). Calculating the exact Monte Carlo standard error ($\text{SE} = 0.0356$), the discrepancy corresponds to a $z$-score of $-1.2152$ ($p = 0.2243$). The result is **completely consistent with standard Monte Carlo variability**.
4. **Independent High-Precision Reproduction ($B = 10,000$):** We executed an independent replication of $10,000$ whole-dataset draws under the exact incidence structure. The empirical variance ratio converged to $\widehat{\text{DEFF}} = \mathbf{1.785894}$ with a $95\%$ confidence interval of $[\mathbf{1.7366}, \mathbf{1.8352}]$, encompassing the theoretical value $1.779963$.
5. **Methodological Disavowals:** We explicitly disavow any claim that sample-centering identities imply a negative population covariance or that ad-hoc finite-sample corrections are required. The true population covariance between unshared pairs is identically zero.

---

## 2. Production Checkpoint Integrity Verification

Before executing any simulation runs or audit calculations, all three protected model artifacts were verified directly from disk via SHA-256 cryptographic hashing and exact byte counting:

| Artifact Path | Physical Size | Audited SHA-256 Checksum | Integrity Status |
| :--- | :---: | :---: | :---: |
| `models/best_model.joblib` | 61,487 bytes | `1001baaf42db8832e1ba3e28ee9da7146e59f1d2d1808c73c4f7587535b2ed4a` | **Pristine / Unmodified** |
| `models/feature_pipeline.joblib` | 270,105 bytes | `2ebf209f691b7084decb5d3a183b82e9b425fe89335345a4af661fed2fc88ae6` | **Pristine / Unmodified** |
| `models/phase12f/challenger_model_phase12f.joblib` | 2,330,440 bytes | `5934990e987abe98223bf790ac9e9a79fb5ec99daac4509093e8eb0036461766` | **Pristine / Unpromoted** |

---

## 3. Theoretical Derivation of Crossed-Cluster Variance

### 3.1 The Crossed Random-Effects Model
Let pair $k = (i, j)$ index candidate $i \in \{1, \dots, C\}$ and job $j \in \{1, \dots, J\}$.
The paired correctness-difference indicator is $D_{ij} = \mathbb{I}(\text{Model 1 correct}) - \mathbb{I}(\text{Model 0 correct}) \in \{-1, 0, 1\}$.
Under the crossed random-effects formulation:
$$D_{ij} = \mu + u_i + v_j + \epsilon_{ij}$$
where:
- $u_i \overset{\text{iid}}{\sim} (0, \sigma_c^2)$ represents the candidate cluster effect across $C = 950$ candidates.
- $v_j \overset{\text{iid}}{\sim} (0, \sigma_j^2)$ represents the job cluster effect across $J = 380$ jobs.
- $\epsilon_{ij} \overset{\text{iid}}{\sim} (0, \sigma_e^2)$ represents the residual pair-level variance.
- $u_i$, $v_j$, and $\epsilon_{ij}$ are mutually independent across all $i, j$.

### 3.2 Population Covariance Structure
Under this data-generating process:
$$\text{Cov}(D_{ij}, D_{lm}) = \begin{cases}
\sigma_D^2 = \sigma_c^2 + \sigma_j^2 + \sigma_e^2 & \text{if } i = l \text{ and } j = m \text{ (identical pair)} \\
\sigma_c^2 = \rho_c \sigma_D^2 & \text{if } i = l \text{ and } j \ne m \text{ (shares candidate only)} \\
\sigma_j^2 = \rho_j \sigma_D^2 & \text{if } i \ne l \text{ and } j = m \text{ (shares job only)} \\
0 & \text{if } i \ne l \text{ and } j \ne m \text{ (unshared candidate and job)}
\end{cases}$$
There is **zero** candidate-job interaction covariance ($\sigma_{cj}^2 = 0$) and **zero** unshared population covariance ($\text{Cov}_{\text{unshared}} = 0$).

### 3.3 Incidence Structure of the Main Benchmark
In the main evaluation benchmark ($N = 2,850$):
- Every candidate appears in exactly $m_{c, i} = 3$ pairs ($950 \times 3 = 2,850$).
  $$m_c^* = \frac{\sum_{i=1}^C m_{c, i}^2}{N} = \frac{950 \times 3^2}{2,850} = \mathbf{3.0000}$$
- Jobs are partitioned as $190$ jobs with $7$ pairs and $190$ jobs with $8$ pairs ($190 \times 7 + 190 \times 8 = 2,850$).
  $$m_j^* = \frac{\sum_{j=1}^J m_{j, j}^2}{N} = \frac{190 \times 7^2 + 190 \times 8^2}{2,850} = \frac{9,310 + 12,160}{2,850} = \frac{21,470}{2,850} = \mathbf{7.533333...}$$

### 3.4 Variance of the Sample Mean $\bar{D}$
The sample sum is $S = \sum_{k=1}^N D_k = N\mu + \sum_{i=1}^C m_{c, i} u_i + \sum_{j=1}^J m_{j, j} v_j + \sum_{k=1}^N \epsilon_k$.
Because $u_i, v_j, \epsilon_k$ are mutually independent:
$$\text{Var}(S) = \sum_{i=1}^C m_{c, i}^2 \sigma_c^2 + \sum_{j=1}^J m_{j, j}^2 \sigma_j^2 + N \sigma_e^2$$
Dividing by $N^2$ to find $\text{Var}(\bar{D}) = \text{Var}(S) / N^2$:
$$\text{Var}(\bar{D}) = \frac{\sigma_c^2}{N^2}\sum_{i=1}^C m_{c, i}^2 + \frac{\sigma_j^2}{N^2}\sum_{j=1}^J m_{j, j}^2 + \frac{\sigma_e^2}{N} = \frac{1}{N}\left[ m_c^* \sigma_c^2 + m_j^* \sigma_j^2 + \sigma_e^2 \right]$$
Substituting $\sigma_e^2 = \sigma_D^2 - \sigma_c^2 - \sigma_j^2$:
$$\text{Var}(\bar{D}) = \frac{\sigma_D^2}{N} \left[ 1 + (m_c^* - 1)\frac{\sigma_c^2}{\sigma_D^2} + (m_j^* - 1)\frac{\sigma_j^2}{\sigma_D^2} \right] = \frac{\sigma_D^2}{N} \left[ 1 + (m_c^* - 1)\rho_c + (m_j^* - 1)\rho_j \right]$$
Therefore, the exact theoretical Design Effect is:
$$\text{DEFF}_{\text{theoretical}} = 1 + (3.0 - 1)(0.142610) + (7.533333 - 1)(0.075726)$$
$$= 1 + 2(0.142610) + 6.533333(0.075726) = 1 + 0.285220 + 0.494747 = \mathbf{1.779967} \approx \mathbf{1.7800}$$

---

## 4. Monte Carlo Uncertainty & Empirical Reconciliation

### 4.1 Sampling Distribution of the Empirical Variance Ratio
In a simulation of $B$ independent dataset draws $\bar{D}_1, \dots, \bar{D}_B$, the sample variance of the mean is:
$$s^2 = \frac{1}{B - 1}\sum_{b=1}^B (\bar{D}_b - \bar{\bar{D}})^2$$
The empirical variance ratio is $\widehat{\text{DEFF}} = \frac{s^2}{\sigma_D^2 / N}$.
Under asymptotic normality of $\bar{D}$, $\frac{(B - 1)s^2}{\text{Var}(\bar{D})} \sim \chi_{B - 1}^2$, with variance $\text{Var}(s^2) = \frac{2 (\text{Var}(\bar{D}))^2}{B - 1}$.
Therefore, the Monte Carlo standard error of $\widehat{\text{DEFF}}$ is:
$$\text{SE}(\widehat{\text{DEFF}}) = \text{DEFF}_{\text{theoretical}} \cdot \sqrt{\frac{2}{B - 1}}$$

### 4.2 Statistical Test of the Phase 12I.4 Reported Value (1.7367 at $B = 5,000$)
- Theoretical DEFF: $1.779963$
- Monte Carlo SE at $B = 5,000$:
  $$\text{SE}(\widehat{\text{DEFF}}) = 1.779963 \cdot \sqrt{\frac{2}{4999}} = 1.779963 \times 0.020002 = \mathbf{0.03560}$$
- Observed Discrepancy: $1.7367 - 1.779963 = \mathbf{-0.04326}$
- Studentized $z$-Score:
  $$z = \frac{-0.04326}{0.03560} = \mathbf{-1.2152}$$
- Two-Sided $p$-Value:
  $$p = 2 \times (1 - \Phi(1.2152)) = 2 \times (1 - 0.8879) = \mathbf{0.2243} \quad (22.43\%)$$

**Statistical Conclusion:** A $p$-value of $0.2243$ indicates that the empirical realization of $1.7367$ is well within normal Monte Carlo sampling variation. It does not provide statistical evidence of an error in the DGP or a non-zero off-cluster covariance.

### 4.3 High-Precision Re-Simulation ($B = 10,000$)
We re-ran the crossed simulation with $B = 10,000$ iterations using the exact integer incidence structure (`reconcile_deff_monte_carlo.py`):
- **Monte Carlo Standard Error ($B = 10,000$):** $\text{SE} = 1.779963 \times \sqrt{2/9999} = \mathbf{0.025174}$
- **Empirical Variance Ratio:** $\widehat{\text{DEFF}} = \mathbf{1.785894}$
- **$95\%$ Confidence Interval:** $[\mathbf{1.7366}, \ \mathbf{1.8352}]$
- **$99\%$ Confidence Interval:** $[\mathbf{1.7210}, \ \mathbf{1.8507}]$
- **Target Coverage:** The theoretical value of $1.779963$ lies within the $95\%$ confidence interval. The bias is negligible ($+0.0059$, $z = +0.235, p = 0.814$).

*Data artifacts:*
- `experiments/phase12i/results/phase12i6_deff_reconciliation.json`
- `experiments/phase12i/results/phase12i6_monte_carlo_uncertainty.json`

---

## 5. Preservation of Three Separate ICCs in Study Governance

To prevent any conflation of psychometric and machine-learning clustering, the benchmark protocol maintains strict segregation of the three ICC concepts:

1. **Recruiter-Rating ICC ($\text{ICC}_{\text{rating}}$):**
   - *Status:* To be estimated from the 200-pair pilot once human ratings arrive.
   - *Meaning:* Measures recruiter subjectivity and resume presentation clustering.
2. **Adjudicated-Label ICC ($\text{ICC}_{\text{adjudicated}}$):**
   - *Status:* To be estimated from consensus ground truth.
   - *Meaning:* Measures underlying domain talent clustering across job descriptions.
3. **Paired Correctness-Difference ICC ($\text{ICC}_{D}$):**
   - *Status:* **UNAVAILABLE until both models are evaluated on benchmark ground truth.**
   - *Meaning:* Directly determines the true Design Effect ($\text{DEFF}$) and statistical power for testing $H_1: \Delta = 0.04$.

> [!IMPORTANT]
> Recruiter-rating ICC must **never** be used as a proxy for paired correctness-difference ICC. Benchmark power ($80.69\%$) remains a **conditional sensitivity benchmark** based on declared assumptions, not an unconditional guarantee.

---

## 6. Official Final Verdict

# **`STATISTICAL RECONCILIATION PASSED — PILOT HANDOFF READY`**
*The crossed-cluster variance derivation is mathematically verified ($\text{DEFF} = 1.7800$), the previous simulation result ($1.7367$) is proven consistent with Monte Carlo error ($p = 0.2243$), the high-precision re-simulation ($B=10,000$) converges to $1.7859$, and the recruiter pilot handoff package is ready for human execution.*
