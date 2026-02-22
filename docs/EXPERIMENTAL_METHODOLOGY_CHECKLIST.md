# Experimental Methodology Checklist

**Purpose:** Prevent methodological errors before they propagate into results, analysis, and papers. Every experiment in this project MUST pass through this checklist before results are considered valid.

**Why this exists:** We have repeatedly spent weeks producing results that later turned out to rest on methodological errors — wrong evaluation metrics (financial TDA: classification vs trend detection), resolution mismatches (poverty TDA: LAD outcomes vs LSOA predictions), unfair baseline comparisons (poverty TDA: k=14 vs k=206). These errors were obvious in hindsight but not caught before analysis because there was no systematic pre-flight check.

> [!CAUTION]
> If you skip this checklist because you're "pretty sure" the methodology is fine, you are the target audience for this checklist.

---

## Pre-Experiment Checks (BEFORE running any code)

### 1. Resolution Alignment

**Question:** Are all variables measured at the same spatial/temporal resolution?

| Check | What to verify |
|-------|---------------|
| Predictors and outcomes at same resolution? | If predicting life expectancy (LAD level) from LSOA features, you have N_lsoas observations but only N_lads distinct outcome values. Your effective sample size is N_lads, not N_lsoas. |
| Aggregation direction explicit? | Are you aggregating up (LSOA → LAD) or disaggregating down (LAD → LSOA)? Disaggregating creates artificial precision. |
| Resolution mismatch documented? | If mismatch is unavoidable, it must be explicitly stated and the effective sample size used in all statistical tests. |

**The test:** Before running analysis, print `len(df[outcome_col].unique())`. If this is << `len(df)`, you have a resolution mismatch. Stop and fix it.

```python
# PUT THIS AT THE TOP OF EVERY ANALYSIS SCRIPT
def check_resolution(df, outcome_col, group_col):
    n_obs = len(df)
    n_unique_outcomes = df[outcome_col].nunique()
    ratio = n_unique_outcomes / n_obs
    if ratio < 0.1:
        raise ValueError(
            f"RESOLUTION MISMATCH: {n_unique_outcomes} unique outcome values "
            f"for {n_obs} observations (ratio={ratio:.3f}). "
            f"Effective sample size is {n_unique_outcomes}, not {n_obs}. "
            f"Find data at {group_col}-level resolution or adjust analysis."
        )
    print(f"Resolution check passed: {n_unique_outcomes}/{n_obs} unique outcomes ({ratio:.1%})")
```

**Prior failure:** Poverty TDA reported η²=83% for MS basins predicting life expectancy, but LE was at LAD level (7 unique values for 1638 LSOAs). The high η² likely reflects basin–LAD boundary alignment, not genuine outcome prediction.

---

### 2. Fair Comparison (Matched Complexity)

**Question:** Do all methods being compared have the same number of free parameters / partitions / degrees of freedom?

| Check | What to verify |
|-------|---------------|
| Same k across methods? | If Method A produces 200 groups and Method B produces 10, Method A will mechanically have higher η². Compare at matched k. |
| Parameter count explicit? | In regression, report both raw R² AND adjusted R² (or, better, cross-validated R²). |
| Random baseline included? | Always include a random partition at the same k as your method. If your method can't beat random, something is wrong. |

**The test:** For every η² or R² comparison, also compute the metric for a random partition with the same number of groups.

```python
def random_partition_baseline(n_observations, k, outcome_values, n_trials=100):
    """Compute expected η² from random k-way partition (null hypothesis)."""
    import numpy as np
    etas = []
    for _ in range(n_trials):
        labels = np.random.randint(0, k, size=n_observations)
        grand_mean = outcome_values.mean()
        ss_total = np.sum((outcome_values - grand_mean) ** 2)
        ss_between = sum(
            np.sum(labels == c) * (outcome_values[labels == c].mean() - grand_mean) ** 2
            for c in range(k) if np.sum(labels == c) > 0
        )
        etas.append(ss_between / ss_total if ss_total > 0 else 0)
    return np.mean(etas), np.std(etas)
```

**Prior failure:** Poverty TDA compared MS (k=206) vs K-means (k≤14). The 2× advantage was at least partly driven by the 15× difference in group count.

---

### 3. In-Sample vs Out-of-Sample

**Question:** Is the headline metric computed on the same data used to fit the model?

| Check | What to verify |
|-------|---------------|
| Is R²/η² in-sample or cross-validated? | In-sample R² with p features on n observations is biased upward by ~p/n. With 200 features on 1600 observations, this bias is ~12.5%. |
| Is cross-validation spatial? | For spatially autocorrelated data, random CV leaks information. Use spatial block CV or leave-one-region-out. |
| Is there a held-out test set? | Best practice: train on Region A, test on Region B. |

**The test:** The headline metric MUST be out-of-sample. In-sample R² should be reported only as a secondary diagnostic.

```python
# NEVER report in-sample R² as the headline
# This is WRONG:
lr.fit(X, y)
r2 = lr.score(X, y)  # DO NOT REPORT THIS

# This is RIGHT:
from sklearn.model_selection import cross_val_score
cv_r2 = cross_val_score(lr, X, y, cv=spatial_cv, scoring='r2').mean()  # REPORT THIS
```

**Prior failure:** Poverty TDA reported +0.63–0.91 R² improvement using in-sample R² with 200+ one-hot basin features. CV R² was computed but not reported as the headline.

---

### 4. Interrogate Your Interpolation

**Question:** Does your data preprocessing create artefacts that your analysis then "discovers"?

| Check | What to verify |
|-------|---------------|
| Interpolation method appropriate? | Cubic splines can create oscillations (Runge's phenomenon) that produce spurious topological features. |
| Compare interpolation methods | Run analysis with both linear and cubic interpolation. If results differ substantially, the topology may be an interpolation artefact. |
| Grid resolution sensitivity | Run at multiple resolutions. If basin count scales linearly with grid size, you may be subdividing noise. |

**The test:** If your method detects topological features, verify that those features persist across interpolation methods and grid resolutions.

**Prior failure:** Poverty TDA found 206 basins with cubic interpolation on a 100×100 grid. Not yet tested whether these persist with linear interpolation. If many basins are interpolation-induced oscillations, η² is inflated.

---

### 5. Statistical Independence

**Question:** Are your predictor and outcome variables actually independent?

| Check | What to verify |
|-------|---------------|
| Predictor and outcome from different data sources? | If both come from IMD, you may be predicting IMD from IMD. |
| No circular logic? | If basins are defined by deprivation and outcomes correlate with deprivation, high η² is trivially expected. |
| Outcome truly external? | Best validation uses outcomes from a completely different domain (e.g., migration, voting, health) that are not inputs to the model. |

**The test:** Can you articulate, in one sentence, why the outcome variable is independent of the input variable? If not, you may have circular validation.

---

### 6. Bootstrap and Confidence Intervals

**Question:** Do your CIs account for the correlation structure in your data?

| Check | What to verify |
|-------|---------------|
| Spatial autocorrelation? | Standard i.i.d. bootstrap underestimates uncertainty for spatial data. Use block bootstrap or spatial bootstrap. |
| Temporal autocorrelation? | For time-series data, use block bootstrap or stationary bootstrap. |
| Multiple comparisons? | If testing multiple methods × multiple outcomes, apply Bonferroni or FDR correction. |

---

## Post-Experiment Checks (AFTER getting results)

### 7. Sanity Check the Magnitude

**Question:** Are the results plausible, or are they "too good to be true"?

| Result | Suspicion level | Action |
|--------|----------------|--------|
| R² > 0.90 with a simple model | **High** | Check for data leakage, resolution mismatch, or overfitting |
| η² > 0.80 with many groups | **High** | Compare with random partition at same k |
| p < 0.001 with large n | **Low** | Large samples make everything significant; report effect size |
| Method A is 2×+ better than Method B | **Medium** | Check that A and B have matched complexity |

**Rule of thumb:** If your method explains >80% of variance in a complex social outcome, something is probably wrong with your methodology, not right with your method.

---

### 8. Adversarial Review

Before sharing or writing up results, answer these questions as if you were a hostile reviewer:

1. *"Isn't this just overfitting?"* — What is your out-of-sample evidence?
2. *"What happens with a simpler baseline?"* — Have you tried random forest / GWR / matched-k K-means?
3. *"Your data is at the wrong resolution"* — Are predictors and outcomes at the same level?
4. *"Your CIs are too narrow"* — Have you accounted for spatial autocorrelation?
5. *"Cherry-picking"* — Did you try multiple specifications and report the best one?

---

## Known Pitfalls in This Project

| Pitfall | Where it happened | Root cause | How to prevent |
|---------|-------------------|------------|----------------|
| Wrong evaluation metric | Financial TDA: used F1 when literature uses τ | Didn't read literature carefully | Read 3+ benchmark papers before designing evaluation |
| Resolution mismatch | Poverty TDA: LAD outcomes on LSOA predictions | Outcome data only available at LAD level, but this wasn't flagged | Run `check_resolution()` before analysis |
| Unfair baseline | Poverty TDA: k=206 vs k=14 | K-means auto-selected k; nobody noticed the 15× gap | Always include matched-k and random baselines |
| In-sample as headline | Poverty TDA: reported in-sample R² | Code computed CV but reported in-sample | Enforce policy: headline metric is ALWAYS out-of-sample |
| Interpolation artefacts | Poverty TDA: cubic spline on sparse points | Cubic was default in scipy | Compare linear vs cubic before trusting topology |

---

## When to Update This Document

Add a new entry to "Known Pitfalls" every time:
- A methodological error is discovered after results were produced
- A reviewer (real or simulated) identifies an issue
- You catch yourself thinking "this is probably fine"

> [!IMPORTANT]
> **This document is a living record of our mistakes.** If we stop adding to it, we have either stopped making mistakes (unlikely) or stopped noticing them (dangerous).
