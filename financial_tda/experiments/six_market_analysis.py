"""
Six Market Experiment
=====================
Runs TDA pipeline on an expanded 6-asset Global Basket to test scalability and signal robustness.
Basket: ^GSPC (US), ^FTSE (UK), ^GDAXI (DE), ^FCHI (FR), ^N225 (JP), ^HSI (HK).

Periods:
1. 2000 Dotcom
2. 2008 GFC
3. 2020 COVID
4. 2023-2025 (Validation)

Metrics:
- Execution Time (Pipeline Latency)
- Topological Signal Strength (Lp Norms)
"""

import time
import logging
import pandas as pd
import yfinance as yf
from pathlib import Path
from financial_tda.validation.gidea_katz_replication import (
    compute_persistence_landscape_norms,
    compute_rolling_statistics,
)

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SixMarket")
DATA_DIR = Path("outputs/six_markets")
DATA_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = {"S&P500": "^GSPC", "FTSE": "^FTSE", "DAX": "^GDAXI", "CAC": "^FCHI", "Nikkei": "^N225", "HangSeng": "^HSI"}

PERIODS = {
    "2000_dotcom": ("1996-01-01", "2002-12-31"),  # Extended for 500d window
    "2008_gfc": ("2004-01-01", "2010-12-31"),  # Extended
    "2020_covid": ("2016-01-01", "2021-12-31"),  # Extended
    "2023_2025": ("2019-01-01", "2025-11-30"),  # Extended
}


def fetch_data(start, end):
    data = {}
    logger.info(f"Fetching data {start} to {end}...")
    for name, ticker in TICKERS.items():
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            if not df.empty:
                # Handle MultiIndex
                if isinstance(df.columns, pd.MultiIndex):
                    data[name] = df["Close"][ticker]
                else:
                    data[name] = df["Close"]
        except Exception as e:
            logger.error(f"Failed {name}: {e}")

    # Align Data (ffill for holidays)
    df_aligned = pd.DataFrame(data).ffill().dropna()
    return df_aligned


def run_pipeline(period_name, start, end):
    logger.info(f"--- Running {period_name} ---")

    t0 = time.time()

    # 1. Fetch
    prices = fetch_data(start, end)

    # Convert back to dict for TDA function (it expects dict or df, let's pass dict to be safe/consistent)
    prices_dict = {col: prices[col] for col in prices.columns}

    t_fetch = time.time()

    # 2. Compute Norms
    # Window=50, Stride=1, Layers=5
    logger.info(f"Computing Norms (N={len(prices)} rows)...")
    norms = compute_persistence_landscape_norms(prices_dict, window_size=50, stride=1, n_layers=5)

    t_norms = time.time()

    # 3. Compute Stats
    # Window=500
    if len(norms) > 500:
        logger.info("Computing Rolling Stats...")
        stats = compute_rolling_statistics(norms, window_size=500)
    else:
        logger.warning("Not enough data for rolling stats")
        stats = pd.DataFrame()

    t_end = time.time()

    # Save
    norms.to_csv(DATA_DIR / f"{period_name}_norms.csv")
    if not stats.empty:
        stats.to_csv(DATA_DIR / f"{period_name}_stats.csv")

    execution_time = t_end - t_fetch
    logger.info(f"Pipeline Time (Compute Only): {execution_time:.4f}s")

    return execution_time, len(prices)


def main():
    timings = {}

    for name, (start, end) in PERIODS.items():
        try:
            duration, rows = run_pipeline(name, start, end)
            timings[name] = {"duration": duration, "rows": rows}
        except Exception as e:
            logger.error(f"Failed {name}: {e}")

    # Report
    print("\n" + "=" * 50)
    print("SIX MARKET EXPERIMENT TIMING")
    print("=" * 50)
    print(f"{'Period':<15} | {'Rows':<6} | {'Time (s)':<10} | {'Sec/Row':<10}")
    print("-" * 50)

    for name, data in timings.items():
        rows = data["rows"]
        dur = data["duration"]
        rate = dur / rows if rows > 0 else 0
        print(f"{name:<15} | {rows:<6} | {dur:.4f}     | {rate:.4f}")


if __name__ == "__main__":
    main()
