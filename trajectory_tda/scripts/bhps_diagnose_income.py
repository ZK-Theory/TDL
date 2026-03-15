"""Diagnostic script to check BHPS income data format."""

import glob

import pandas as pd

# Load wave 1 indresp
df = pd.read_csv(
    "trajectory_tda/data/UKDA-5151-tab/tab/bhps_w1/aindresp.tab",
    sep="\t",
    low_memory=False,
)

# Find columns
cols = {c.lower(): c for c in df.columns}
inc_cols = [c for c in df.columns if "fihhmn" in c.lower()]
pid_cols = [c for c in df.columns if "pid" in c.lower()]
hid_cols = [c for c in df.columns if "hid" in c.lower()]

print(f"Income cols: {inc_cols}")
print(f"PID cols: {pid_cols}")
print(f"HID cols: {hid_cols}")

# Income values
inc_col = inc_cols[0]
vals = pd.to_numeric(df[inc_col], errors="coerce")
print(f"\nIncome column: {inc_col}")
print(f"  n={len(vals)}, mean={vals.mean():.2f}, median={vals.median():.2f}")
print(f"  min={vals.min():.2f}, max={vals.max():.2f}")
print(
    f"  positive: {(vals > 0).sum()}, negative: {(vals < 0).sum()}, zero: {(vals == 0).sum()}"
)
print("  Negative value counts:")
neg_counts = vals[vals < 0].value_counts().head(10)
for v, c in neg_counts.items():
    print(f"    {v}: {c}")

# Check hhresp
hh_files = glob.glob("trajectory_tda/data/UKDA-5151-tab/tab/bhps_w1/*hhresp*")
print(f"\nHH files: {hh_files}")
if hh_files:
    hh = pd.read_csv(hh_files[0], sep="\t", low_memory=False)
    eq_cols_list = [c for c in hh.columns if "eq_moecd" in c.lower()]
    hid_cols_hh = [c for c in hh.columns if "hid" in c.lower()]
    print(f"HH eq_moecd cols: {eq_cols_list}")
    print(f"HH hid cols: {hid_cols_hh}")
    if eq_cols_list:
        eq_col = eq_cols_list[0]
        eq_vals = pd.to_numeric(hh[eq_col], errors="coerce")
        print(f"\neq_moecd column: {eq_col}")
        print(
            f"  n={len(eq_vals)}, mean={eq_vals.mean():.4f}, median={eq_vals.median():.4f}"
        )
        print(f"  min={eq_vals.min():.4f}, max={eq_vals.max():.4f}")
        print(f"  Sample values: {eq_vals.head(10).tolist()}")
        print(f"  Positive: {(eq_vals > 0).sum()}, Negative: {(eq_vals < 0).sum()}")

    # Also check fihhmn in hhresp (might be there too)
    hh_inc_cols = [c for c in hh.columns if "fihhmn" in c.lower()]
    print(f"\nHH income cols: {hh_inc_cols}")
    if hh_inc_cols:
        hh_inc = pd.to_numeric(hh[hh_inc_cols[0]], errors="coerce")
        print(f"  HH-level income: mean={hh_inc.mean():.2f}, med={hh_inc.median():.2f}")
