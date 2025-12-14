"""
Financial returns and volatility calculations.

This module provides functions for computing returns and volatility measures
from financial time series data. All functions preserve pandas DataFrame/Series
structure and index information.
"""

import numpy as np
import pandas as pd


def compute_log_returns(
    prices: pd.Series | pd.DataFrame,
) -> pd.Series | pd.DataFrame:
    """
    Compute logarithmic returns from price series.

    Log returns are calculated as: log(P_t / P_{t-1})

    Args:
        prices: Price series or DataFrame with price columns

    Returns:
        Log returns with same structure as input. First value will be NaN.

    Examples:
        >>> prices = pd.Series([100, 105, 103, 108])
        >>> returns = compute_log_returns(prices)
        >>> # Returns: [NaN, 0.04879, -0.01942, 0.04741]
    """
    if prices.empty:
        return prices.copy()

    log_returns = np.log(prices / prices.shift(1))
    return log_returns


def compute_simple_returns(
    prices: pd.Series | pd.DataFrame,
) -> pd.Series | pd.DataFrame:
    """
    Compute simple (arithmetic) returns from price series.

    Simple returns are calculated as: (P_t - P_{t-1}) / P_{t-1}

    Args:
        prices: Price series or DataFrame with price columns

    Returns:
        Simple returns with same structure as input. First value will be NaN.

    Examples:
        >>> prices = pd.Series([100, 105, 103, 108])
        >>> returns = compute_simple_returns(prices)
        >>> # Returns: [NaN, 0.05, -0.01905, 0.04854]
    """
    if prices.empty:
        return prices.copy()

    # Use pct_change which handles edge cases like zero prices
    simple_returns = prices.pct_change()
    return simple_returns


def compute_cumulative_returns(
    returns: pd.Series | pd.DataFrame,
    log_returns: bool = False,
) -> pd.Series | pd.DataFrame:
    """
    Compute cumulative returns from return series.

    Args:
        returns: Return series or DataFrame
        log_returns: If True, treats input as log returns (uses cumsum + exp).
                     If False, treats as simple returns (uses cumprod of 1+r).

    Returns:
        Cumulative returns starting from 0

    Examples:
        >>> returns = pd.Series([0.05, -0.02, 0.03])
        >>> cum_returns = compute_cumulative_returns(returns)
        >>> # Returns cumulative product: [0.05, 0.029, 0.0587]
    """
    if returns.empty:
        return returns.copy()

    if log_returns:
        # For log returns: cumulative sum then exponentiate, subtract 1
        cum_returns = np.exp(returns.fillna(0).cumsum()) - 1
    else:
        # For simple returns: cumulative product of (1 + r) - 1
        cum_returns = (1 + returns.fillna(0)).cumprod() - 1

    return cum_returns


def compute_rolling_volatility(
    returns: pd.Series,
    window: int = 20,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> pd.Series:
    """
    Compute rolling volatility (standard deviation of returns).

    Args:
        returns: Return series
        window: Rolling window size
        annualize: If True, annualize the volatility
        periods_per_year: Number of periods in a year (252 for daily data)

    Returns:
        Rolling volatility series

    Examples:
        >>> returns = pd.Series(np.random.randn(100) * 0.01)
        >>> vol = compute_rolling_volatility(returns, window=20)
    """
    if returns.empty:
        return returns.copy()

    # Compute rolling standard deviation
    rolling_vol = returns.rolling(window=window, min_periods=window).std()

    if annualize:
        rolling_vol = rolling_vol * np.sqrt(periods_per_year)

    return rolling_vol


def compute_ewma_volatility(
    returns: pd.Series,
    span: int = 20,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> pd.Series:
    """
    Compute exponentially weighted moving average (EWMA) volatility.

    EWMA volatility is more responsive to recent data than simple rolling volatility.

    Args:
        returns: Return series
        span: Span for exponential weighting (higher = more smoothing)
        annualize: If True, annualize the volatility
        periods_per_year: Number of periods in a year (252 for daily data)

    Returns:
        EWMA volatility series

    Examples:
        >>> returns = pd.Series(np.random.randn(100) * 0.01)
        >>> vol = compute_ewma_volatility(returns, span=20)
    """
    if returns.empty:
        return returns.copy()

    # Compute EWMA of squared returns, then take square root
    ewma_vol = returns.ewm(span=span, min_periods=span).std()

    if annualize:
        ewma_vol = ewma_vol * np.sqrt(periods_per_year)

    return ewma_vol


def compute_realized_volatility(
    prices: pd.DataFrame,
    window: int = 20,
    method: str = "parkinson",
    annualize: bool = True,
    periods_per_year: int = 252,
) -> pd.Series:
    """
    Compute realized volatility using high-low price information.

    This provides a more efficient estimate than close-to-close volatility
    when OHLC data is available.

    Args:
        prices: DataFrame with 'High', 'Low', 'Open', 'Close' columns
        window: Rolling window size
        method: Estimator method ('parkinson' or 'garman_klass')
        annualize: If True, annualize the volatility
        periods_per_year: Number of periods in a year

    Returns:
        Realized volatility series

    Examples:
        >>> ohlc = pd.DataFrame({
        ...     'High': [105, 107, 106],
        ...     'Low': [100, 102, 101],
        ...     'Open': [102, 105, 104],
        ...     'Close': [103, 104, 105]
        ... })
        >>> vol = compute_realized_volatility(ohlc, window=2)

    References:
        Parkinson, M. (1980). The Extreme Value Method for Estimating the Variance
        of the Rate of Return. Journal of Business, 53(1), 61-65.

        Garman, M. B., & Klass, M. J. (1980). On the Estimation of Security Price
        Volatilities from Historical Data. Journal of Business, 53(1), 67-78.
    """
    if prices.empty:
        return pd.Series(dtype=float)

    required_cols = {"High", "Low", "Open", "Close"}
    if not required_cols.issubset(prices.columns):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    if method == "parkinson":
        # Parkinson volatility: sqrt((1/(4*ln(2))) * (ln(H/L))^2)
        hl_ratio = np.log(prices["High"] / prices["Low"])
        variance = (1 / (4 * np.log(2))) * (hl_ratio**2)

    elif method == "garman_klass":
        # Garman-Klass volatility (more efficient than Parkinson)
        hl_ratio = np.log(prices["High"] / prices["Low"])
        co_ratio = np.log(prices["Close"] / prices["Open"])

        variance = 0.5 * (hl_ratio**2) - (2 * np.log(2) - 1) * (co_ratio**2)

    else:
        raise ValueError(f"Unknown method: {method}. Use 'parkinson' or 'garman_klass'")

    # Take rolling mean of variance, then square root
    rolling_variance = variance.rolling(window=window, min_periods=window).mean()
    realized_vol = np.sqrt(rolling_variance)

    if annualize:
        realized_vol = realized_vol * np.sqrt(periods_per_year)

    return realized_vol
