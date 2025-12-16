import pandas as pd

# Load 2008 stats to check baselines
try:
    s08 = pd.read_csv("outputs/six_markets/2008_gfc_stats.csv", index_col=0)
    print("--- 2008 GFC Stats (Baselines) ---")
    print(s08.max())

    b_max = s08.max()

    # Load 2023 stats to check values
    s23 = pd.read_csv("outputs/six_markets/2023_2025_stats.csv", index_col=0)
    print("\n--- 2023 Stats Max Values ---")
    print(s23.max())

    print("\n--- Ratios (2023 Max / 2008 Max) ---")
    for col in s08.columns:
        if col in s23.columns:
            ratio = s23[col].max() / s08[col].max()
            print(f"{col}: {ratio:.4f}")

    # Load 2020 stats
    s20 = pd.read_csv("outputs/six_markets/2020_covid_stats.csv", index_col=0)
    print("\n--- 2020 Stats Max Values ---")
    print(s20.max())

    print("\n--- Ratios (2020 Max / 2008 Max) ---")
    for col in s08.columns:
        if col in s20.columns:
            ratio = s20[col].max() / s08[col].max()
            print(f"{col}: {ratio:.4f}")

except Exception as e:
    print(f"Error: {e}")
