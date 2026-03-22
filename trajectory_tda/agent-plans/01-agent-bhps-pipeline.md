# Agent 1: BHPS Data Pipeline

**Core plan reference:** `trajectory_tda/plan-fourthDraftMajorRevision.md` — Phase 1, steps 0–6
**Orchestration:** `trajectory_tda/agent-plans/00-orchestration.md`

## Scope

Fix the broken BHPS–USoc person linkage so that BHPS-era (1991–2008) trajectories can be built, then run the full TDA pipeline on them as a cross-era replication.

## Files You Own (EXCLUSIVE WRITE)

- `trajectory_tda/data/employment_status.py`
- `trajectory_tda/data/income_band.py`
- `trajectory_tda/data/trajectory_builder.py`

**DO NOT edit any other existing files.** You may create temporary scripts in `trajectory_tda/scripts/` prefixed with `bhps_` if needed for pipeline runs.

## Steps

### Step 0 — BLOCKING: Verify BHPS `fihhmn` variable

Before writing ANY income harmonisation code, determine whether BHPS `fihhmn` is:
- (a) Raw monthly household net income, OR
- (b) Already equivalised (adjusted for household composition)

**How to verify:**
1. Check BHPS documentation files in `trajectory_tda/data/UKDA-5151-tab/` for variable descriptions (look for `mrdoc/` or `*.rtf`/`*.txt` documentation files)
2. If no documentation, inspect the variable values: equivalised income for a 1-person household should equal raw income; if values differ by household size, it's raw
3. If `fihhmn` is raw: income harmonisation needs equivalence scale (modified OECD) + CPI deflation
4. If `fihhmn` is already equivalised: only CPI deflation needed
5. **Record your finding explicitly** — this determines the approach for step 3

### Step 1 — Load xwaveid mapping

Load `trajectory_tda/data/UKDA-6614-tab/tab/ukhls/xwavedat.tab` (or `xwaveid.tab`) to build a mapping from BHPS `{wave}pid` → unified `pidp`.

**Key questions to resolve:**
- Which column in xwavedat contains the BHPS pid? (likely `pid` or `bapid`)
- Which column contains the USoc `pidp`? (likely `pidp`)
- Build a helper function or module-level lookup dict that other modules can import

### Step 2 — Fix employment_status.py

In the BHPS wave extraction loop (which iterates over waves a–r):
- After loading each BHPS wave's `{wave}pid`, map it to `pidp` using the xwaveid lookup from step 1
- The rest of the employment extraction logic (jbstat → E/U/I mapping) should work unchanged
- Verify that BHPS `jbstat` codes use the same mapping as USoc (they should — both use the harmonised LFS classification)

### Step 3 — Fix income_band.py

Using the approach determined in step 0:
- For BHPS waves, load `fihhmn` (or the correct income variable for each wave)
- Apply equivalisation if needed (modified OECD scale: 1.0 for first adult, 0.5 for subsequent adults age 14+, 0.3 for children under 14 — requires household composition from `hhresp`)
- Apply CPI deflation to bring BHPS-era incomes to a common price base (or compute year-specific medians, which avoids the deflation issue)
- Compute per-year medians from the full BHPS sample
- Classify L/M/H using 60%/120% of contemporary median thresholds (same approach as USoc)

**Preferred approach:** Compute year-specific medians (avoids CPI deflation entirely — same approach already used for USoc).

### Step 4 — Add survey_era to trajectory_builder.py

- After the trajectory merge, add a `survey_era` column to metadata:
  - `"bhps_only"` if all years ≤ 2008
  - `"usoc_only"` if all years ≥ 2009
  - `"spanning"` if trajectory contains years from both surveys
- This enables downstream filtering for Tier 1 (BHPS-only) and Tier 2 (spanning) analyses
- Existing `min_years=10` and gap-filling logic should work unchanged

### Step 5 — Run BHPS-era pipeline

Run the full pipeline on BHPS-era trajectories only (`survey_era == "bhps_only"`):
1. N-gram embedding (unigrams + bigrams) → PCA-20D
2. VR PH at L=5000 landmarks
3. Order-shuffle null (n=500)
4. Markov-1 null (n=500)
5. GMM regime discovery (BIC-optimal k)

Record: total H₀ persistence, total H₁ persistence, order-shuffle p-values, Markov-1 p-values, number of regimes, sample size.

### Step 6 — Run spanning-trajectory pipeline (conditional)

Count respondents with `survey_era == "spanning"`. If n ≥ 500, run the same pipeline. If n < 500, record the sample size and skip.

## Handoff Summary (produce when complete)

Report to Agent 5 (Paper):
1. BHPS `fihhmn` determination (raw vs equivalised) and harmonisation approach used
2. BHPS-era sample size (n trajectories, mean length, year range)
3. Spanning sample size (n, or "insufficient — n = X")
4. BHPS-era PH results: H₀ total persistence, H₁ total persistence
5. BHPS-era null results: order-shuffle p-values (H₀, H₁), Markov-1 p-values (H₀, H₁)
6. BHPS-era regime count and whether regime structure is comparable to USoc-era
7. State distribution comparison: BHPS-era vs USoc-era E/U/I × L/M/H frequencies
8. Any unexpected findings

## Verification

- `python -m pytest tests/trajectory/ -v` — ensure existing tests still pass after code changes
- Compare BHPS-era employment rates against known benchmarks (e.g., ONS Labour Force Survey 1991–2008 employment rates: ~70–75% for working-age population)
- Verify that USoc-era trajectories (n=27,280) are unchanged after the code modifications
