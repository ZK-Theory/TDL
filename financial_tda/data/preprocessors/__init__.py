"""
Financial data preprocessing utilities.

This subpackage provides tools for preprocessing financial time series data
for topological data analysis, including returns calculations, volatility
estimation, normalization, and windowing utilities.
"""

from financial_tda.data.preprocessors import normalization, returns, windowing

__all__ = [
    "returns",
    "normalization",
    "windowing",
]
