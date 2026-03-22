"""
Compare 4-Market vs 6-Market Signal Strength (2023)
===================================================
"""

import pandas as pd
from pathlib import Path
from financial_tda.validation.trend_analysis_validator import compute_gk_rolling_statistics

# Windows
WS = 500


def get_stats(dirname, baseline_file, target_file):
    base_path = Path(dirname) / baseline_file
    targ_path = Path(dirname) / target_file

    if not base_path.exists() or not targ_path.exists():
        return None

    s_base = (
        pd.read_csv(base_path, index_col=0)
        if "stats" in baseline_file
        else compute_gk_rolling_statistics(pd.read_csv(base_path, index_col=0), WS)
    )
    s_targ = (
        pd.read_csv(targ_path, index_col=0)
        if "stats" in target_file
        else compute_gk_rolling_statistics(pd.read_csv(targ_path, index_col=0), WS)
    )

    # Strip tz
    if s_base.index.dtype == "object":
        s_base.index = pd.to_datetime(s_base.index, utc=True)
    if s_base.index.tz is not None:
        s_base.index = s_base.index.tz_localize(None)
    if s_targ.index.dtype == "object":
        s_targ.index = pd.to_datetime(s_targ.index, utc=True)
    if s_targ.index.tz is not None:
        s_targ.index = s_targ.index.tz_localize(None)

    # Normalize
    b_max = s_base.max()
    t_max = s_targ.iloc[WS:].max() if len(s_targ) > WS else s_targ.max()

    ratio = {}
    for c in b_max.index:
        if c in t_max.index and b_max[c] != 0:
            ratio[c] = t_max[c] / b_max[c]
    return ratio


def main():
    # 4-Market (Outputs)
    # Baseline: 2008_gfc_lp_norms.csv
    # Target: 2023_2025_realtime_lp_norms.csv
    r4 = get_stats("outputs", "2008_gfc_lp_norms.csv", "2023_2025_realtime_lp_norms.csv")

    # 6-Market (Outputs/Six_Markets)
    # Baseline: 2008_gfc_stats.csv
    # Target: 2023_2025_stats.csv
    r6 = get_stats("outputs/six_markets", "2008_gfc_stats.csv", "2023_2025_stats.csv")

    print(f"{'Metric':<30} | {'4-Market Ratio':<15} | {'6-Market Ratio':<15} | {'Delta':<10}")
    print("-" * 80)

    for c in r4:
        v4 = r4.get(c, 0)
        v6 = r6.get(c, 0) if r6 else 0
        delta = v6 - v4
        print(f"{c:<30} | {v4:.4f}          | {v6:.4f}          | {delta:+.4f}")


if __name__ == "__main__":
    main()
