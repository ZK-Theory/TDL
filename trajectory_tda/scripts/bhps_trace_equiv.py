"""Trace the BHPS income equivalisation step by step."""

from pathlib import Path

import pandas as pd

data_dir = Path("trajectory_tda/data/UKDA-5151-tab")
wave_letter = "a"

# Step 1: Load indresp
candidates = list(data_dir.rglob(f"{wave_letter}indresp.tab"))
print(f"indresp file: {candidates[0]}")
df_ind = pd.read_csv(candidates[0], sep="\t", low_memory=False)
cols_ind = {c.lower(): c for c in df_ind.columns}

# Step 2: Find income col
for candidate in [
    f"b{wave_letter}_fihhmn",
    f"{wave_letter}_fihhmn",
    f"{wave_letter}fihhmni",
    f"{wave_letter}fihhmn",
    "fihhmn",
]:
    if candidate in cols_ind:
        income_col = cols_ind[candidate]
        print(f"Income column matched: '{candidate}' -> '{income_col}'")
        break

income_values = pd.to_numeric(df_ind[income_col], errors="coerce")
print(
    f"Raw income: n={len(income_values)}, mean={income_values.mean():.2f}, NaN={income_values.isna().sum()}"
)

# Step 3: HID
hid_col_ind = cols_ind.get(f"{wave_letter}hid")
print(f"Ind HID col: {hid_col_ind}")
print(f"Sample HIDs from indresp: {df_ind[hid_col_ind].head(5).tolist()}")

# Step 4: HHresp
hh_candidates = list(data_dir.rglob(f"{wave_letter}hhresp.tab"))
print(f"\nhhresp file: {hh_candidates[0]}")
df_hh = pd.read_csv(hh_candidates[0], sep="\t", low_memory=False)
cols_hh = {c.lower(): c for c in df_hh.columns}

eq_col = cols_hh.get(f"{wave_letter}eq_moecd")
hid_col_hh = cols_hh.get(f"{wave_letter}hid")
print(f"HH eq_moecd col: {eq_col}, HH HID col: {hid_col_hh}")
print(f"Sample HIDs from hhresp: {df_hh[hid_col_hh].head(5).tolist()}")

# Step 5: Build hh_lookup
eq_scale = pd.to_numeric(df_hh[eq_col], errors="coerce")
hh_lookup = pd.DataFrame(
    {
        "hid": df_hh[hid_col_hh],
        "eq_moecd": eq_scale,
    }
).dropna(subset=["eq_moecd"])
hh_lookup = hh_lookup[hh_lookup["eq_moecd"] > 0]
print(f"\nhh_lookup: {len(hh_lookup)} rows (after filtering >0)")
print(
    f"eq_moecd stats: mean={hh_lookup['eq_moecd'].mean():.4f}, median={hh_lookup['eq_moecd'].median():.4f}"
)

# Step 6: Merge
ind_hid = df_ind[hid_col_ind]
merged = pd.DataFrame(
    {
        "idx": range(len(df_ind)),
        "hid": ind_hid,
    }
).merge(hh_lookup, on="hid", how="left")
print(f"\nMerged: {len(merged)} rows (expect {len(df_ind)})")
print(f"Matched (non-NaN eq_moecd): {merged['eq_moecd'].notna().sum()}")
print(f"Unmatched: {merged['eq_moecd'].isna().sum()}")

# Check for duplicate-idx issues
if merged["idx"].duplicated().any():
    print(f"WARNING: {merged['idx'].duplicated().sum()} duplicate idx values!")

# Step 7: Equivalise
eq_values = merged.set_index("idx")["eq_moecd"]
valid_eq = eq_values.reindex(range(len(df_ind)))
equivalised = income_values / valid_eq
print(
    f"\nEquivalised income: mean={equivalised.mean():.2f}, median={equivalised.median():.2f}"
)
print(f"NaN after equiv: {equivalised.isna().sum()}")
print(f"Non-NaN after equiv: {equivalised.notna().sum()}")
print(f"Sample values (first 5): {equivalised.head(5).tolist()}")

# Final result
result = pd.DataFrame(
    {
        "pidp": df_ind[cols_ind.get("pidp") or cols_ind.get("pid")],
        "income_raw": equivalised,
        "year": 1991,
        "source": "bhps",
    }
).dropna(subset=["income_raw"])
print(
    f"\nFinal: {len(result)} obs, mean={result['income_raw'].mean():.2f}, median={result['income_raw'].median():.2f}"
)
