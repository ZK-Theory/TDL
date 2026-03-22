"""
Multi-Asset TDA: Data Infrastructure Module
Handles fetching, aligning, and preprocessing multi-asset data from various sources.

Usage:
    from fetch_multiasset_data import MultiAssetDataFetcher
    fetcher = MultiAssetDataFetcher(config='extended')
    data = fetcher.fetch_and_align()
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional

# =============================================================================
# CONFIGURATION: Asset Universes
# =============================================================================

ASSET_CONFIGS = {
    "minimal": {
        "description": "Core 4-asset macro portfolio (Equities/Bonds/Gold/Dollar)",
        "tickers": ["SPY", "TLT", "GLD", "UUP"],
        "start_date": "2007-02-20",  # UUP inception
        "asset_classes": {"SPY": "Equity", "TLT": "Bond", "GLD": "Commodity", "UUP": "Currency"},
    },
    "extended": {
        "description": "8-asset extended portfolio (adds Credit/Energy/Tech/FX)",
        "tickers": ["SPY", "QQQ", "TLT", "HYG", "GLD", "USO", "UUP", "FXE"],
        "start_date": "2007-04-11",  # HYG inception
        "asset_classes": {
            "SPY": "Equity",
            "QQQ": "Equity_Tech",
            "TLT": "Bond_Duration",
            "HYG": "Bond_Credit",
            "GLD": "Commodity_Gold",
            "USO": "Commodity_Energy",
            "UUP": "Currency_USD",
            "FXE": "Currency_EUR",
        },
    },
    "full_crypto": {
        "description": "10-asset with Crypto (post-2017 only)",
        "tickers": ["SPY", "QQQ", "TLT", "HYG", "GLD", "USO", "UUP", "FXE", "BTC-USD", "ETH-USD"],
        "start_date": "2017-11-09",  # ETH reliable data
        "asset_classes": {
            "SPY": "Equity",
            "QQQ": "Equity_Tech",
            "TLT": "Bond_Duration",
            "HYG": "Bond_Credit",
            "GLD": "Commodity_Gold",
            "USO": "Commodity_Energy",
            "UUP": "Currency_USD",
            "FXE": "Currency_EUR",
            "BTC-USD": "Crypto",
            "ETH-USD": "Crypto",
        },
    },
}

# =============================================================================
# KNOWN STRESS EVENTS (for labeling and validation)
# =============================================================================

STRESS_EVENTS = [
    {"name": "2008 GFC Peak", "date": "2008-09-15", "type": "risk_off", "severity": "major"},
    {"name": "2010 Flash Crash", "date": "2010-05-06", "type": "flash", "severity": "minor"},
    {"name": "2011 Debt Ceiling", "date": "2011-08-05", "type": "risk_off", "severity": "moderate"},
    {"name": "2015 China Crash", "date": "2015-08-24", "type": "risk_off", "severity": "minor"},
    {"name": "2018 Volmageddon", "date": "2018-02-05", "type": "equity_only", "severity": "minor"},
    {"name": "2020 COVID Liquidity", "date": "2020-03-16", "type": "liquidity", "severity": "major"},
    {"name": "2022 Rate Shock", "date": "2022-10-01", "type": "duration", "severity": "moderate"},
    {"name": "2022 FTX Collapse", "date": "2022-11-08", "type": "crypto", "severity": "crypto_only"},
]

# =============================================================================
# DATA FETCHER CLASS
# =============================================================================


class MultiAssetDataFetcher:
    """
    Fetches and aligns multi-asset data for TDA analysis.

    Handles:
    - Different trading calendars (crypto 24/7, equities weekdays only)
    - Missing data imputation (forward fill within limits)
    - Log returns and standardization
    """

    def __init__(self, config: str = "extended", end_date: Optional[str] = None):
        """
        Args:
            config: One of 'minimal', 'extended', 'full_crypto'
            end_date: End date for data (default: today)
        """
        if config not in ASSET_CONFIGS:
            raise ValueError(f"Config must be one of {list(ASSET_CONFIGS.keys())}")

        self.config_name = config
        self.config = ASSET_CONFIGS[config]
        self.end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        self.raw_prices = None
        self.aligned_prices = None
        self.log_returns = None
        self.standardized_returns = None

    def fetch_raw(self) -> pd.DataFrame:
        """Download raw price data from Yahoo Finance."""
        print(f"Fetching {self.config_name} data ({len(self.config['tickers'])} assets)...")

        df = yf.download(self.config["tickers"], start=self.config["start_date"], end=self.end_date, progress=False)

        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            try:
                prices = df["Adj Close"]
            except KeyError:
                prices = df["Close"]
        else:
            prices = df

        self.raw_prices = prices
        print(f"  Raw shape: {prices.shape}")
        return prices

    def align_and_clean(self, max_ffill_days: int = 5) -> pd.DataFrame:
        """
        Align all assets to common trading days.

        Strategy:
        1. Forward-fill gaps up to max_ffill_days (weekends, holidays)
        2. Drop any remaining NaN rows (hard intersection)
        """
        if self.raw_prices is None:
            self.fetch_raw()

        prices = self.raw_prices.copy()

        # Forward fill (handles weekends, minor holidays)
        prices = prices.ffill(limit=max_ffill_days)

        # Drop remaining NaNs (strict intersection)
        aligned = prices.dropna()

        self.aligned_prices = aligned
        print(f"  Aligned shape: {aligned.shape}")
        print(f"  Date range: {aligned.index[0].date()} to {aligned.index[-1].date()}")
        return aligned

    def compute_returns(self, standardize: bool = True) -> pd.DataFrame:
        """Compute log returns and optionally standardize."""
        if self.aligned_prices is None:
            self.align_and_clean()

        # Log returns
        log_ret = np.log(self.aligned_prices / self.aligned_prices.shift(1)).dropna()
        self.log_returns = log_ret

        if standardize:
            # Rolling standardization (252-day = 1 year)
            # For now, use full-sample standardization for simplicity
            standardized = (log_ret - log_ret.mean()) / log_ret.std()
            self.standardized_returns = standardized
            return standardized

        return log_ret

    def fetch_and_align(self, standardize: bool = True) -> pd.DataFrame:
        """Full pipeline: fetch -> align -> returns."""
        self.fetch_raw()
        self.align_and_clean()
        return self.compute_returns(standardize=standardize)

    def get_asset_classes(self) -> Dict[str, str]:
        """Return mapping of ticker -> asset class."""
        return self.config["asset_classes"]

    def get_stress_events_in_range(self) -> List[Dict]:
        """Return stress events that fall within our data range."""
        if self.aligned_prices is None:
            return STRESS_EVENTS

        start = self.aligned_prices.index[0]
        end = self.aligned_prices.index[-1]

        in_range = []
        for event in STRESS_EVENTS:
            event_date = pd.to_datetime(event["date"])
            if start <= event_date <= end:
                in_range.append(event)
        return in_range

    def save(self, output_dir: str = "outputs/multiasset"):
        """Save processed data to CSV."""
        os.makedirs(output_dir, exist_ok=True)

        if self.aligned_prices is not None:
            self.aligned_prices.to_csv(os.path.join(output_dir, f"{self.config_name}_prices.csv"))
        if self.standardized_returns is not None:
            self.standardized_returns.to_csv(os.path.join(output_dir, f"{self.config_name}_returns.csv"))
        print(f"  Saved to {output_dir}/")


# =============================================================================
# MAIN: Quick validation
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Multi-Asset Data Infrastructure Validation")
    print("=" * 60)

    for config_name in ["minimal", "extended", "full_crypto"]:
        print(f"\n--- Config: {config_name} ---")
        fetcher = MultiAssetDataFetcher(config=config_name)
        data = fetcher.fetch_and_align()

        events = fetcher.get_stress_events_in_range()
        print(f"  Stress events in range: {len(events)}")
        for e in events[:3]:
            print(f"    - {e['name']} ({e['date']})")
