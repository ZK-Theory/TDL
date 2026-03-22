"""
Phase 10.2: Information Content Assessment
==========================================

Purpose:
    Determine if Topological Complexity (Tau) adds incremental predictive power
    beyond standard financial metrics (VIX).

    Models:
    1. Future Returns (30d) ~ VIX + Tau
    2. Future Volatility (30d) ~ VIX + Tau

    Hypothesis:
    If Tau is useful, the coefficient beta_tau should be significant and adjusted R^2 should increase.

Input:
    - outputs/phase_10/continuous_signal_2000_2025.csv (generated in Task 10.1)
    - SPY/GSPC returns data (fetched via yfinance)

Output:
    - outputs/phase_10/information_content_results.txt
"""

import pandas as pd
import numpy as np
import yfinance as yf
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

SIGNAL_FILE = "outputs/phase_10/continuous_signal_2000_2025.csv"
REPORT_FILE = "outputs/phase_10/information_content_results.txt"


def run_regression_analysis():
    print("=" * 80)
    print("PHASE 10.2: INFORMATION CONTENT ASSESSMENT")
    print("=" * 80)

    # 1. Load Signal Data
    print(f"Loading signal data from {SIGNAL_FILE}...")
    df = pd.read_csv(SIGNAL_FILE, index_col=0, parse_dates=True)

    # 2. Fetch Market Data (S&P 500) for Targets
    print("Fetching S&P 500 data for target generation...")
    sp500 = yf.download("^GSPC", start="2000-01-01", end="2025-12-31", progress=False)

    print(f"DEBUG: Raw SP500 Shape: {sp500.shape}")
    print(f"DEBUG: Raw SP500 Columns: {sp500.columns}")

    if sp500.empty:
        raise ValueError("CRITICAL: S&P 500 data download failed (empty).")

    # Handle yfinance multi-index columns (Price, Ticker)
    try:
        if isinstance(sp500.columns, pd.MultiIndex):
            # Try to find 'Close' in level 0
            if "Close" in sp500.columns.get_level_values(0):
                sp500 = sp500["Close"]
            # If still DataFrame (multiple tickers?), take first column
            if isinstance(sp500, pd.DataFrame):
                sp500 = sp500.iloc[:, 0]
        elif "Close" in sp500.columns:
            sp500 = sp500["Close"]
        else:
            sp500 = sp500.iloc[:, 0]

        # Ensure it is a Series
        if isinstance(sp500, pd.DataFrame):
            sp500 = sp500.iloc[:, 0]

        print(f"DEBUG: Extracted SP500 Series Shape: {sp500.shape}")

    except Exception as e:
        print(f"ERROR extracting Close price: {e}")
        # Fallback
        sp500 = sp500.iloc[:, 0]

    # Ensure timezone naive
    if sp500.index.tz is not None:
        sp500.index = sp500.index.tz_localize(None)

    # Normalize to midnight
    sp500.index = sp500.index.normalize()

    # 3. Create Targets
    # Forward 30-day returns
    # r_{t+30} = (Price_{t+30} / Price_t) - 1
    # We shift -30 to align future value to current row
    print("Constructing target variables (Future 30d Returns, Future 30d Vol)...")

    sp500_forward = sp500.shift(-30)
    sp500_future_returns = (sp500_forward / sp500) - 1

    # Future 30-day realized volatility
    # Std dev of next 30 daily returns * sqrt(252/30)? No, just std of next 30 days
    daily_returns = sp500.pct_change()
    future_vol = daily_returns.rolling(window=30).std().shift(-30) * np.sqrt(252)

    # 4. Merge
    analysis_df = df.join(sp500_future_returns.rename("Future_Ret_30d"), how="inner")
    analysis_df = analysis_df.join(future_vol.rename("Future_Vol_30d"), how="inner")

    # Drop NaNs (end of series)
    analysis_df.dropna(inplace=True)

    print(f"Analysis Dataset: {len(analysis_df)} observations")

    # 5. Regressions
    results_txt = []
    results_txt.append("REGRESSION ANALYSIS RESULTS")
    results_txt.append("===========================")

    targets = ["Future_Ret_30d", "Future_Vol_30d"]

    for target in targets:
        results_txt.append(f"\nTARGET: {target}")
        results_txt.append("-" * 40)

        y = analysis_df[target]
        X_base = analysis_df[["VIX"]]
        X_aug = analysis_df[["VIX", "Tau"]]

        # Standardize for coefficient comparison
        scaler = StandardScaler()
        X_base_scaled = sm.add_constant(scaler.fit_transform(X_base))
        X_aug_scaled = sm.add_constant(scaler.fit_transform(X_aug))

        # Baseline Model (VIX only)
        model_base = sm.OLS(y, X_base_scaled).fit()

        # Augmented Model (VIX + Tau)
        model_aug = sm.OLS(y, X_aug_scaled).fit()

        results_txt.append(f"Baseline R^2 (VIX only): {model_base.rsquared:.4f}")
        results_txt.append(f"Augmented R^2 (VIX+Tau): {model_aug.rsquared:.4f}")
        results_txt.append(f"Delta R^2:               {model_aug.rsquared - model_base.rsquared:.4f}")
        results_txt.append(f"Tau p-value:             {model_aug.pvalues[2]:.4e}")
        results_txt.append(f"Tau Coefficient:         {model_aug.params[2]:.4f}")

        if model_aug.pvalues[2] < 0.05:
            results_txt.append(">> RESULT: Tau is SIGNIFICANT.")
        else:
            results_txt.append(">> RESULT: Tau is NOT significant.")

    # 6. Save Report
    with open(REPORT_FILE, "w") as f:
        f.write("\n".join(results_txt))

    print("\n".join(results_txt))
    print(f"\nReport saved to {REPORT_FILE}")


if __name__ == "__main__":
    run_regression_analysis()
