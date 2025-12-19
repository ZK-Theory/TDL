"""
Sector Data Fetcher for Sector-Specific TDA Analysis

Downloads and preprocesses data for 9 Select Sector SPDRs:
- XLF (Financials), XLK (Technology), XLE (Energy)
- XLY (Consumer Discretionary), XLP (Consumer Staples), XLV (Healthcare)
- XLI (Industrials), XLB (Materials), XLU (Utilities)

All ETFs have inception Dec 1998, providing coverage from 1999+.
"""

import os
import numpy as np
import pandas as pd
import yfinance as yf

# Output directory
OUTPUT_DIR = "outputs/sector"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sector SPDR ETFs (all 9 original Select Sector SPDRs)
SECTOR_ETFS = {
    "XLF": "Financials",
    "XLK": "Technology",
    "XLE": "Energy",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLV": "Healthcare",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLU": "Utilities",
}

# Date range covering all major crises
START_DATE = "1999-01-01"  # ETF inception is Dec 1998
END_DATE = "2024-12-31"


def fetch_sector_data(start_date=START_DATE, end_date=END_DATE, save=True):
    """
    Fetch adjusted close prices for all 9 sector ETFs.

    Returns:
        DataFrame with DatetimeIndex and columns for each sector ticker.
    """
    tickers = list(SECTOR_ETFS.keys())
    print(f"Fetching {len(tickers)} sector ETFs: {tickers}")

    df = yf.download(tickers, start=start_date, end=end_date, progress=True)

    # Handle MultiIndex columns from yfinance
    if isinstance(df.columns, pd.MultiIndex):
        try:
            prices = df["Adj Close"]
        except KeyError:
            prices = df["Close"]
    else:
        prices = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]

    # Ensure column order matches SECTOR_ETFS
    prices = prices[tickers]

    # Forward-fill and drop any remaining NaN rows
    prices = prices.ffill().dropna()

    print(f"Data shape: {prices.shape}")
    print(f"Date range: {prices.index[0]} to {prices.index[-1]}")

    if save:
        filepath = os.path.join(OUTPUT_DIR, "sector_prices.csv")
        prices.to_csv(filepath)
        print(f"Saved to {filepath}")

    return prices


def compute_log_returns(prices, standardize=True, save=True):
    """
    Compute log returns from prices.

    Args:
        prices: DataFrame of prices
        standardize: If True, standardize returns to zero mean and unit variance
        save: If True, save to CSV

    Returns:
        DataFrame of log returns
    """
    log_returns = np.log(prices / prices.shift(1)).dropna()

    if standardize:
        log_returns = (log_returns - log_returns.mean()) / log_returns.std()

    if save:
        filepath = os.path.join(OUTPUT_DIR, "sector_returns.csv")
        log_returns.to_csv(filepath)
        print(f"Saved returns to {filepath}")

    return log_returns


def validate_data_availability():
    """
    Quick check to confirm data availability for all sectors.
    """
    print("\n--- Data Availability Check ---")
    for ticker, name in SECTOR_ETFS.items():
        data = yf.Ticker(ticker).history(start="1998-01-01", end="2000-01-01")
        print(f"{ticker} ({name}): {len(data)} days available pre-2000")
    print()


if __name__ == "__main__":
    # Validate availability first
    validate_data_availability()

    # Fetch and process
    prices = fetch_sector_data()
    returns = compute_log_returns(prices)

    print("\n--- Summary ---")
    print(f"Sectors: {list(SECTOR_ETFS.keys())}")
    print(f"Trading days: {len(returns)}")
    print(f"Dimensions: {returns.shape[1]} (one per sector)")
