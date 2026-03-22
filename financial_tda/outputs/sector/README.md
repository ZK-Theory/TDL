# SECTOR ANALYSIS: EXPERIMENTAL CONDITIONS

Generated: 2025-12-17

## Valid Experiments (G&K Standard Methodology)

The following results use CORRECT G&K (2018) parameters:
- Point cloud window: 50 days
- Rolling statistics window: **500 days** (CRITICAL)
- Pre-crisis window: 250 days

### Validated Experiments:

1. **experiment_systematic_baskets.py** → systematic_basket_results.csv
   - US_4 baseline: τ = 0.88 for 2008 GFC (matches main paper ~0.92)
   - Best combination: US_Tech+XLF τ = 0.97

2. **experiment_inter_sector.py** → inter_sector_results.csv
   - 9-sector 18D point cloud
   - 2008 GFC: τ = 0.49

3. **experiment_per_sector.py** → per_sector_results.csv, sector_tau_matrix.csv
   - Correlation-based sector stress
   - 2008 GFC leader: XLY (Consumer Discretionary) τ = 0.64

### Experiments Not Compatible with 500-day Rolling:

4. **experiment_sector_tda.py** - Produces "segment too short" errors
   because sector-centric point clouds don't accumulate enough data 
   before pre-crisis windows at 500-day rolling scale.

5. **experiment_dominance.py** - Uses different methodology (LOO analysis)
   without rolling variance. Results not directly comparable.

## Invalid/Deprecated Outputs

Any outputs generated BEFORE 2025-12-17T15:00 used incorrect parameters
(250-day or 120-day rolling windows) and are NOT comparable to the main
paper's results. These have been superseded by the corrected runs above.
