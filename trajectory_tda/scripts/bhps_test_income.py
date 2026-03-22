"""Test BHPS income extraction after fix."""

import logging

logging.basicConfig(level=logging.INFO)
from pathlib import Path

from trajectory_tda.data.income_band import _load_bhps_income_wave, extract_income_bands

# Test single wave
df = _load_bhps_income_wave(Path("trajectory_tda/data/UKDA-5151-tab"), "a")
if df is not None:
    print(f"Wave a: {len(df)} obs")
    print(
        f"  Income mean={df['income_raw'].mean():.2f}, median={df['income_raw'].median():.2f}"
    )
    print(f"  Min={df['income_raw'].min():.2f}, Max={df['income_raw'].max():.2f}")
else:
    print("Wave a: FAILED (returned None)")

# Test extract with BHPS only
print("\n--- Full BHPS extraction (waves a-c only, no USoc) ---")
df_bhps = extract_income_bands(
    "trajectory_tda/data", bhps_waves=["a", "b", "c"], usoc_waves=[]
)
print(f"Shape: {df_bhps.shape}")
print(f"Income bands:\n{df_bhps['income_band'].value_counts()}")
print(
    f"By year:\n{df_bhps.groupby('year')['income_band'].value_counts().unstack(fill_value=0)}"
)
