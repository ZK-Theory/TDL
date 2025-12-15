# Ad-Hoc Task: Real-Time Crisis Detection - 2023-2025 Market Analysis

## Context

You have access to a validated TDA-based crisis detection methodology (Gidea & Katz, 2018) that has successfully detected pre-crisis buildups in:

- **2008 GFC**: τ = 0.9165 (PASS)
- **2000 Dotcom**: τ = 0.7504 (PASS)
- **2020 COVID**: τ = 0.7123 (PASS with optimized parameters)

**Key Finding**: The methodology works across different crisis types when parameters are tuned to event dynamics. Recent market conditions (2023-2025) warrant investigation for potential regime changes.

---

## Your Mission

**Analyze the most recent 2-3 years of market data (2023-present) to detect potential pre-crisis warning signals using the validated G&K TDA methodology.**

### Primary Questions

1. **Are there warning signs?** Do L^p norms show upward trends (τ > 0.70) in recent windows?
2. **What's the optimal detection window?** Given we don't know the "crisis type" in advance, what parameter range works?
3. **Which metrics are elevated?** Variance? Spectral density? ACF? L¹ vs L²?
4. **How does it compare to historical?** Are current trends stronger/weaker than pre-2008/2000/2020?

---

## Detailed Instructions

### Step 1: Data Acquisition & L^p Norm Computation

**Fetch recent data** (2022-01-01 to present):

```python
from financial_tda.validation.gidea_katz_replication import (
    fetch_historical_data,
    compute_persistence_landscape_norms
)

# Get recent data (extended window for context)
prices = fetch_historical_data("2022-01-01", "2025-12-31")

# Compute L^p norms (50-day windows, daily stride)
norms_df = compute_persistence_landscape_norms(
    prices,
    window_size=50,
    stride=1,
    n_layers=5
)
```

**Save data**:

- `outputs/2023_2025_realtime_lp_norms.csv`

### Step 2: Rolling Window Analysis with Parameter Grid

**Unlike historical validation** (where we know the crisis date), we need to:

- Apply rolling windows across the entire period
- Test multiple parameter combinations
- Look for elevated τ values in recent months

**Parameter Grid** (guided by historical findings):

- `rolling_windows`: [350, 400, 450, 500, 550] days
- `analysis_windows`: [150, 175, 200, 225, 250] days
- Focus on **most recent** analysis_window days of data

**Implementation approach**:

```python
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics
from scipy.stats import kendalltau
import pandas as pd
import numpy as np

results = []

for rolling_win in [350, 400, 450, 500, 550]:
    # Compute rolling statistics
    stats_df = compute_gk_rolling_statistics(norms_df, window_size=rolling_win)

    for analysis_win in [150, 175, 200, 225, 250]:
        # Take most recent analysis_win days
        recent_window = stats_df.tail(analysis_win)

        # Compute tau for each metric
        for metric in ['L1_norm_variance', 'L2_norm_variance',
                       'L1_norm_spectral_density_low', 'L2_norm_spectral_density_low']:
            series = recent_window[metric].dropna()
            if len(series) >= 50:  # Need sufficient data
                tau, p_value = kendalltau(np.arange(len(series)), series.values)

                results.append({
                    'rolling_window': rolling_win,
                    'analysis_window': analysis_win,
                    'metric': metric,
                    'tau': tau,
                    'p_value': p_value,
                    'n_samples': len(series),
                    'window_end': recent_window.index[-1]
                })

results_df = pd.DataFrame(results)
```

**What to look for**:

- **High τ values** (> 0.60-0.70) indicate upward trends
- **Statistical significance** (p < 0.001)
- **Consistent across parameters** (not just one combo)
- **Recent emergence** (trend started in last 6-12 months)

### Step 3: Comparative Analysis

**Compare current trends to historical pre-crisis periods**:

Load historical data:

```python
gfc_norms = load_lp_norms_from_csv("outputs/2008_gfc_lp_norms.csv")
dotcom_norms = load_lp_norms_from_csv("outputs/2000_dotcom_lp_norms.csv")
covid_norms = load_lp_norms_from_csv("outputs/2020_covid_lp_norms.csv")
```

For each historical crisis, extract the **comparable window** (same parameters as current best):

```python
# Example: If current best is rolling=450, analysis=200
historical_comparison = []

for event_name, event_norms, crisis_date in [
    ('2008 GFC', gfc_norms, '2008-09-15'),
    ('2000 Dotcom', dotcom_norms, '2000-03-10'),
    ('2020 COVID', covid_norms, '2020-03-16')
]:
    stats = compute_gk_rolling_statistics(event_norms, window_size=450)
    pre_crisis = stats[stats.index < crisis_date].tail(200)

    for metric in ['L2_norm_variance', 'L1_norm_variance']:
        series = pre_crisis[metric].dropna()
        tau, p = kendalltau(np.arange(len(series)), series.values)
        historical_comparison.append({
            'event': event_name,
            'metric': metric,
            'tau': tau,
            'status': 'Pre-Crisis Buildup'
        })
```

**Key comparison**:
| Period | Best τ | Status | Interpretation |
|--------|--------|--------|----------------|
| 2023-2025 Current | ? | ? | Unknown |
| 2008 Pre-GFC | 0.92-0.96 | Crisis occurred | Strong warning |
| 2000 Pre-Dotcom | 0.75-0.84 | Crisis occurred | Strong warning |
| 2020 Pre-COVID | 0.56-0.71 | Crisis occurred | Moderate warning |

**Decision matrix**:

- **τ > 0.70**: High concern - matches pre-crisis levels
- **0.60 < τ < 0.70**: Moderate concern - elevated but below threshold
- **0.50 < τ < 0.60**: Weak concern - monitor
- **τ < 0.50**: No concern - normal market dynamics

### Step 4: Temporal Analysis - When Did Trends Emerge?

**Rolling trend detection** to identify when elevated τ began:

```python
# Sliding window approach - compute tau for overlapping periods
import matplotlib.pyplot as plt

lookback_periods = range(100, 301, 25)  # 100-300 days
tau_timeline = []

for lookback in lookback_periods:
    recent = stats_df.tail(lookback)
    series = recent['L2_norm_variance'].dropna()
    if len(series) >= 50:
        tau, p = kendalltau(np.arange(len(series)), series.values)
        tau_timeline.append({
            'lookback_days': lookback,
            'tau': tau,
            'p_value': p,
            'end_date': recent.index[-1]
        })

# Plot tau evolution
plt.figure(figsize=(12, 6))
df = pd.DataFrame(tau_timeline)
plt.plot(df['lookback_days'], df['tau'], marker='o')
plt.axhline(0.70, color='red', linestyle='--', label='Crisis threshold')
plt.xlabel('Lookback Period (days)')
plt.ylabel('Kendall-tau')
plt.title('Trend Strength vs. Analysis Window')
plt.legend()
plt.savefig('figures/2023_2025_tau_evolution.png')
```

**Interpretation**:

- If τ increases with longer lookbacks → **sustained buildup** (concerning)
- If τ peaks at short lookbacks → **recent surge** (very concerning)
- If τ is flat/low across all → **no clear trend** (normal)

### Step 5: Sector/Asset Breakdown

**Analyze individual indices** to identify localized stress:

```python
# Fetch individual index data
from financial_tda.data.fetchers.yahoo_fetcher import YahooFinanceFetcher

fetcher = YahooFinanceFetcher()
indices = {
    'SPY': 'S&P 500 Large Cap',
    'IWM': 'Russell 2000 Small Cap',
    'QQQ': 'NASDAQ Tech',
    'DIA': 'Dow Industrials'
}

sector_results = {}

for ticker, name in indices.items():
    data = fetcher.fetch(ticker, "2022-01-01", "2025-12-31")
    # Convert to G&K format (4 identical series for single-asset analysis)
    prices_df = pd.DataFrame({
        'index1': data['Close'],
        'index2': data['Close'],
        'index3': data['Close'],
        'index4': data['Close']
    })

    norms = compute_persistence_landscape_norms(prices_df, window_size=50)
    stats = compute_gk_rolling_statistics(norms, window_size=450)
    recent = stats.tail(200)

    tau, p = kendalltau(np.arange(len(recent)), recent['L2_norm_variance'].values)
    sector_results[ticker] = {'name': name, 'tau': tau, 'p_value': p}
```

**Look for**:

- **Sector-specific stress**: One index >> 0.70, others normal
- **Broad-based stress**: All indices elevated (more concerning)
- **Small-cap weakness**: IWM (Russell 2000) often leads

### Step 6: Visualization & Report

Create comprehensive visualization:

```python
fig, axes = plt.subplots(3, 2, figsize=(16, 14))

# Panel 1: Recent L^p norms
ax = axes[0, 0]
recent_norms = norms_df.tail(500)
ax.plot(recent_norms.index, recent_norms['L1_norm'], label='L¹', alpha=0.7)
ax.plot(recent_norms.index, recent_norms['L2_norm'], label='L²', alpha=0.7)
ax.set_title('Recent L^p Norms (Last 500 days)')
ax.legend()

# Panel 2: Rolling variance with trend
ax = axes[0, 1]
recent_stats = stats_df.tail(200)
ax.plot(recent_stats.index, recent_stats['L2_norm_variance'])
# Add trend line
from scipy.stats import theilslopes
slope, intercept, _, _ = theilslopes(
    recent_stats['L2_norm_variance'].values,
    np.arange(len(recent_stats))
)
ax.plot(recent_stats.index,
        slope * np.arange(len(recent_stats)) + intercept,
        'r--', label=f'τ={tau:.3f}')
ax.set_title('L² Variance Trend (Most Recent Window)')
ax.legend()

# Panel 3: Historical comparison
ax = axes[1, 0]
events = ['Current\n(2023-25)', '2008 GFC', '2000 Dotcom', '2020 COVID']
taus = [current_tau, 0.92, 0.75, 0.71]  # Fill with actual values
colors = ['blue', 'red', 'orange', 'purple']
ax.bar(events, taus, color=colors, alpha=0.7)
ax.axhline(0.70, color='black', linestyle='--', label='Threshold')
ax.set_ylabel('Kendall-tau')
ax.set_title('Current vs. Historical Pre-Crisis Trends')
ax.legend()

# Panel 4: Parameter sensitivity heatmap
ax = axes[1, 1]
# Create pivot table of tau values
pivot = results_df.pivot_table(
    values='tau',
    index='rolling_window',
    columns='analysis_window',
    aggfunc='max'  # Max tau across all metrics
)
im = ax.imshow(pivot.values, cmap='RdYlGn', vmin=0, vmax=1)
ax.set_xticks(range(len(pivot.columns)))
ax.set_yticks(range(len(pivot.index)))
ax.set_xticklabels(pivot.columns)
ax.set_yticklabels(pivot.index)
ax.set_xlabel('Analysis Window')
ax.set_ylabel('Rolling Window')
ax.set_title('Parameter Sensitivity (Max τ)')
plt.colorbar(im, ax=ax)

# Panel 5: Sector breakdown
ax = axes[2, 0]
sectors = list(sector_results.keys())
sector_taus = [sector_results[s]['tau'] for s in sectors]
ax.barh(sectors, sector_taus)
ax.axvline(0.70, color='red', linestyle='--', label='Threshold')
ax.set_xlabel('Kendall-tau')
ax.set_title('Sector/Index Breakdown')
ax.legend()

# Panel 6: Timeline of tau evolution
ax = axes[2, 1]
df = pd.DataFrame(tau_timeline)
ax.plot(df['lookback_days'], df['tau'], marker='o')
ax.axhline(0.70, color='red', linestyle='--', label='Threshold')
ax.set_xlabel('Lookback Period (days)')
ax.set_ylabel('Kendall-tau')
ax.set_title('Trend Strength vs. Window Size')
ax.legend()

plt.tight_layout()
plt.savefig('figures/2023_2025_comprehensive_analysis.png', dpi=300)
```

**Generate markdown report**: `financial_tda/validation/2023_2025_realtime_analysis.md`

Include:

- **Executive summary**: Warning level (None/Low/Moderate/High)
- **Best parameters found**: (rolling, analysis) yielding highest τ
- **Current τ values**: All metrics, sorted by strength
- **Historical context**: How does it compare to 2008/2000/2020?
- **Sector analysis**: Which areas show stress?
- **Temporal pattern**: When did trends emerge?
- **Recommendation**: Monitor/Alert/Concern levels

---

## Expected Deliverables

1. **Script**: `financial_tda/validation/realtime_detection_2023_2025.py`
2. **Data**: `outputs/2023_2025_realtime_lp_norms.csv`
3. **Results**: `outputs/2023_2025_parameter_grid_results.csv`
4. **Report**: `financial_tda/validation/2023_2025_realtime_analysis.md`
5. **Visualization**: `figures/2023_2025_comprehensive_analysis.png`

---

## Decision Framework

Based on your analysis, classify the situation:

### **HIGH CONCERN** (τ > 0.70, p < 0.001)

- Current trends match or exceed pre-2008/2000/2020 levels
- Multiple metrics elevated
- Broad-based (multiple sectors)
- **Action**: Detailed investigation warranted, consider risk management

### **MODERATE CONCERN** (0.60 < τ < 0.70)

- Elevated but below crisis threshold
- Some metrics elevated, others normal
- May be sector-specific
- **Action**: Continue monitoring, weekly updates

### **LOW CONCERN** (0.50 < τ < 0.60)

- Weak trends, not statistically robust
- Inconsistent across parameters/metrics
- **Action**: Normal monitoring cadence

### **NO CONCERN** (τ < 0.50)

- Normal market dynamics
- No sustained upward trends
- **Action**: Routine oversight

---

## Key Questions to Answer

1. **What's the current warning level?** (None/Low/Moderate/High)

2. **If elevated, what's the optimal detection window?**

   - Best (rolling, analysis) parameters
   - Which metric is strongest indicator?

3. **How does it compare historically?**

   - Current τ vs. 2008 (0.92), 2000 (0.75), 2020 (0.71)
   - Percentile ranking

4. **Is it localized or systemic?**

   - Single sector vs. broad market
   - Large cap vs. small cap

5. **When did it start?**

   - Recent (< 3 months) vs. sustained (> 6 months)
   - Accelerating vs. stable

6. **Statistical confidence?**
   - P-values all < 0.001?
   - Consistent across parameter variations?

---

## Technical Notes

### Handling "No Crisis Date" Problem

Unlike historical validation (where we know the crisis date), real-time analysis requires:

1. **Use most recent window** - Assume "today" is potential pre-crisis
2. **Sliding windows** - Check if τ is stable or increasing
3. **Multiple parameter sets** - Can't optimize to a specific event

### False Positive Considerations

TDA may show elevated trends without a crisis if:

- **High volatility** (but not crisis) → Check VIX levels
- **Regime shift** (new normal, not crisis) → Compare to post-2020 baseline
- **Technical artifacts** → Verify across multiple metrics

### Null Hypothesis

**H₀**: Current market dynamics are normal (τ < 0.50)  
**H₁**: Pre-crisis buildup is occurring (τ > 0.70)

Reject H₀ only with:

- τ > 0.70
- p < 0.001
- Consistent across multiple parameter sets
- At least 2 metrics elevated

---

## Success Criteria

Your analysis is successful if you provide:

1. ✅ **Clear answer**: Current warning level (None/Low/Moderate/High)
2. ✅ **Quantitative**: Actual τ values with confidence intervals
3. ✅ **Context**: Comparison to historical pre-crisis levels
4. ✅ **Actionable**: Specific recommendations based on findings
5. ✅ **Reproducible**: Code + data for verification

---

## Code Template

```python
"""
Real-Time Crisis Detection: 2023-2025 Market Analysis
Uses validated G&K TDA methodology for early warning signals.
"""
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import kendalltau
import matplotlib.pyplot as plt

from financial_tda.validation.gidea_katz_replication import (
    fetch_historical_data,
    compute_persistence_landscape_norms
)
from financial_tda.validation.trend_analysis_validator import (
    compute_gk_rolling_statistics
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).parent / "outputs"
FIGURES_DIR = Path(__file__).parent / "figures"

def analyze_realtime_crisis_signals():
    """Main analysis function"""

    logger.info("Step 1: Fetch and compute L^p norms...")
    # YOUR CODE HERE

    logger.info("Step 2: Parameter grid search...")
    # YOUR CODE HERE

    logger.info("Step 3: Historical comparison...")
    # YOUR CODE HERE

    logger.info("Step 4: Temporal analysis...")
    # YOUR CODE HERE

    logger.info("Step 5: Sector breakdown...")
    # YOUR CODE HERE

    logger.info("Step 6: Generate report and visualization...")
    # YOUR CODE HERE

    # Final recommendation
    logger.info(f"\n{'='*80}")
    logger.info("RECOMMENDATION:")
    logger.info(f"Warning Level: {warning_level}")
    logger.info(f"Best tau: {best_tau:.4f}")
    logger.info(f"Optimal parameters: rolling={best_rolling}, analysis={best_analysis}")
    logger.info(f"{'='*80}")

if __name__ == "__main__":
    analyze_realtime_crisis_signals()
```

---

## Final Notes

- **This is exploratory research** - findings may or may not indicate impending crisis
- **TDA detects buildups, not timing** - Even if τ > 0.70, crisis could be months away (or not occur)
- **Multiple factors matter** - TDA is one signal among many (macro, sentiment, valuations, etc.)
- **Document thoroughly** - Future researchers will want to know what you found in Dec 2025

**IMPORTANT**: Be objective. Report what the data shows, not what you expect/want to see.
