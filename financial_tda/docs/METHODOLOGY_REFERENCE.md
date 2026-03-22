# Canonical TDA Methodology Reference

> [!CAUTION]
> **DO NOT INVENT YOUR OWN METHODOLOGY.** This document defines the exact pipeline validated in our paper and based on Gidea & Katz (2018). All experiments MUST follow this specification to ensure reproducibility and comparability.

## Why This Matters

Deviating from the canonical methodology:
- **Invalidates comparisons** to baseline results (τ values become incomparable)
- **Creates p-hacking risk** (trying variations until something "works")
- **Undermines scientific credibility** of findings

If you want to test a methodological variation, **explicitly declare it as an experiment** with a control arm using the canonical method.

---

## 1. The Canonical Pipeline (Gidea & Katz 2018 + Our Extensions)

```
Raw Prices → Log Returns → Standardization → Point Cloud (Takens Embedding) 
    → Persistent Homology (H₁) → Persistence Landscape → L^p Norms 
    → Rolling Variance → Kendall-Tau Trend
```

---

## 2. Step-by-Step Specification

### 2.1 Data Preprocessing

**Input:** Daily adjusted close prices for N assets.

**Step A: Log Returns**
```python
log_returns = np.log(prices / prices.shift(1)).dropna()
```

**Step B: Standardization (Z-Score)**
```python
standardized = (log_returns - log_returns.mean()) / log_returns.std()
```

> [!WARNING]
> Use **full-sample** mean/std for standardization, NOT rolling. Rolling standardization is a valid variation but must be declared as such.

### 2.2 Point Cloud Construction (Takens Delay Embedding)

**Purpose:** Transform 1D time series into a geometric object (attractor reconstruction).

**Formula:** For each asset and time t, construct vector:
```
x(t) = [r_1(t), r_1(t-1), r_2(t), r_2(t-1), ..., r_N(t), r_N(t-1)]
```

Where:
- `r_i(t)` = standardized log return of asset i at time t
- Embedding dimension = 2 per asset (current + 1 lag)
- Total dimensions = 2N (e.g., 4 assets → 8D)

**Window:** Take the most recent `W_pc` days (default: 50) to form the point cloud.

```python
# Canonical implementation
point_cloud = []
for j in range(1, window_size):  # j from 1 to W_pc-1
    point = []
    for asset in range(n_assets):
        point.append(data[j, asset])      # r(t)
        point.append(data[j-1, asset])    # r(t-1)
    point_cloud.append(point)
```

### 2.3 Persistent Homology

**Tool:** GUDHI library (version 3.8.0 validated)

**Complex:** Vietoris-Rips complex

**Homology Dimension:** H₁ (1-dimensional holes / loops)

```python
import gudhi as gd

rips = gd.RipsComplex(points=point_cloud)
simplex_tree = rips.create_simplex_tree(max_dimension=2)
simplex_tree.compute_persistence()
persistence = simplex_tree.persistence_intervals_in_dimension(1)
```

### 2.4 Persistence Landscape → L^p Norms

**Definition:** For H₁ persistence pairs (birth, death), compute lifetimes:
```
lifetime_i = death_i - birth_i
```

**L¹ Norm (Total Persistence):**
```python
L1 = np.sum(lifetimes)
```

**L² Norm (Euclidean Persistence):**
```python
L2 = np.sqrt(np.sum(lifetimes ** 2))
```

> [!IMPORTANT]
> Filter out **infinite** intervals before computing norms:
> ```python
> finite = persistence[np.isfinite(persistence[:, 1])]
> ```

### 2.5 Rolling Statistics

**Rolling Window (W):** Number of days to compute variance over.
- Standard: W = 500 days
- Fast (COVID-optimized): W = 450 days

**Variance Computation:**
```python
L2_variance = L2_series.rolling(window=W).var()
```

### 2.6 Kendall-Tau Trend Detection

**Pre-Crisis Window (P):** Number of days before event to analyze.
- Standard: P = 250 days
- Fast: P = 200 days

**Kendall-Tau Computation:**
```python
from scipy.stats import kendalltau

segment = L2_variance[event_loc - P : event_loc]
tau, p_value = kendalltau(np.arange(len(segment)), segment.values)
```

**Interpretation:**
- τ > 0: Variance is **increasing** (crisis building)
- τ < 0: Variance is **decreasing** (no warning)
- **Threshold:** τ ≥ 0.70 = "Crisis Warning" (Gidea & Katz criterion)

---

## 3. Validated Parameter Sets

| Parameter Set | W (Rolling) | P (Pre-Crisis) | Use Case |
|---------------|-------------|----------------|----------|
| **Standard** | 500 | 250 | Gradual crises (2008 GFC) |
| **COVID-Optimized** | 450 | 200 | Rapid shocks (2020 COVID) |
| **Extended** | 550 | 225 | Sector bubbles (2000 Dotcom) |
| **Crypto-Fast** | 300 | 150 | Cryptocurrency (experimental) |

---

## 4. What You MUST NOT Do

> [!CAUTION]
> The following deviations are **PROHIBITED** unless explicitly declared as experimental with a control arm:

| ❌ Don't | ✅ Instead |
|----------|-----------|
| Invent new embedding schemes | Use Takens [t, t-1] as defined |
| Try random parameter combinations | Use validated parameter sets |
| Change homology dimension (H₀, H₂) | Use H₁ (loops) |
| Use different persistence metrics | Use L¹/L² as defined |
| Change the tau computation | Use scipy.stats.kendalltau on variance |
| Optimize parameters to "improve" a failing result | Report the failure honestly |

---

## 5. Reporting Requirements

For **every** experiment, you MUST report:

1. **Parameters Used:** (W, P, point cloud window)
2. **Data Source:** (Yahoo Finance tickers, date range)
3. **Preprocessing:** (Confirm log returns + z-score standardization)
4. **τ Value and p-value:** For each event analyzed
5. **Comparison to Baseline:** How does this compare to our paper's validated results?

---

## 6. Reference Implementation

The canonical implementation is in:
```
financial_tda/validation/validate_all_params_realtime.py
```

Any new experiment should import from or mirror this implementation.

---

## 7. Baseline Results (What "Good" Looks Like)

These are the validated τ values from our paper. New experiments MUST be compared against these baselines.

### 7.1 US Equity Indices (4 assets: ^GSPC, ^DJI, ^IXIC, ^RUT)

| Event | Parameters | L² Variance τ | p-value | Status |
|-------|------------|---------------|---------|--------|
| **2008 GFC** | Standard (500/250) | **0.81** | <10⁻⁵⁰ | ✅ Detected |
| **2000 Dotcom** | Extended (550/225) | **0.76** | <10⁻⁵⁰ | ✅ Detected |
| **2020 COVID** | Fast (450/200) | **0.55** | <10⁻³⁰ | ✅ Detected (Orange Zone) |

### 7.2 International (6 assets: +^FTSE, ^GDAXI)

| Event | Parameters | L² Variance τ | Status |
|-------|------------|---------------|--------|
| **2008 GFC** | Standard | **0.79** | ✅ Detected |
| **2020 COVID** | Fast | **0.35-0.55** | ✅ Detected (varies by config) |

### 7.3 Known Failures (Your Results Should Match)

| Event | Reason for Failure | Expected τ |
|-------|-------------------|------------|
| **2010 Flash Crash** | Cold-start (post-GFC) | Negative or near-zero |
| **2011 Debt Crisis** | Refractory period | Negative or low |
| **2015 China Crash** | Distal shock (no US correlation change) | Near-zero |

### 7.4 How to Use This Table

When reporting results:
1. **Compare to baseline:** Is your τ similar to the paper's?
2. **If lower:** Explain the methodological difference (different assets? different window?)
3. **If higher:** Be skeptical — did you accidentally p-hack?
4. **If negative where expected positive:** Report honestly, analyze why

---

## 8. Handling Failures

If the method **fails** to detect an event (τ < 0.50):

1. **REPORT THE FAILURE HONESTLY** — Do not try to "fix" it by changing methodology
2. **Analyze why:** Was this a rapid shock? Exogenous event? Cold-start problem?
3. **Document in results:** Add to the "Limitations" or "Stress Test Failures" section
4. **Only then** consider if a documented methodological extension (e.g., faster parameters) is justified

---

**Remember:** A negative result (failure to detect) is still a valid scientific finding. Manipulating methodology to get positive results is p-hacking.
