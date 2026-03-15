# Agent 2: Null Model Compute

**Core plan reference:** `trajectory_tda/plan-fourthDraftMajorRevision.md` — Phase 2, steps 1–3
**Orchestration:** `trajectory_tda/agent-plans/00-orchestration.md`

## Scope

Re-run the three missing null models at L=5,000 landmarks: label-shuffle, cohort-shuffle, and Markov-2. This is pure compute — no source code edits.

## Files You Own (EXCLUSIVE WRITE)

Output files only:
- `results/trajectory_tda_integration/04_nulls.json` (will be overwritten with L=5000 results)
- `results/trajectory_tda_integration/04_nulls_markov2.json` (will be overwritten with L=5000 results)
- Any new result files in `results/trajectory_tda_robustness/landmark_sensitivity/` with L=5000 suffix

**DO NOT edit any source code files.**

## Context

The current state of null model results:

| Null Model | L=2,500 | L=5,000 | Needs Re-run? |
|------------|---------|---------|---------------|
| Order-shuffle | ✅ in 04_nulls.json | ✅ in landmark_sensitivity/ | No |
| Markov-1 | ✅ in 04_nulls.json | ✅ in landmark_sensitivity/ | No |
| Label-shuffle | ✅ in 04_nulls.json | ❌ MISSING | **Yes** |
| Cohort-shuffle | ✅ in 04_nulls.json | ❌ MISSING | **Yes** |
| Markov-2 | ✅ in 04_nulls_markov2.json | ❌ MISSING | **Yes** |

The observed PH at L=5,000 (from `results/trajectory_tda_integration/03_ph.json`):
- H₀ total persistence: **20,411.1**
- H₁ total persistence: **2,224.7**

## Steps

### Step 1 — Re-run label-shuffle at L=5000

```bash
cd c:\Projects\TDL
python -m trajectory_tda.scripts.rerun_nulls --landmarks 5000 --null label_shuffle --permutations 500
```

Adjust the command if `rerun_nulls.py` uses different flag names — check `--help` first. Save output with clear L=5000 labelling.

### Step 2 — Re-run cohort-shuffle at L=5000

```bash
python -m trajectory_tda.scripts.rerun_nulls --landmarks 5000 --null cohort_shuffle --permutations 500
```

### Step 3 — Re-run Markov-2 at L=5000

```bash
python -m trajectory_tda.scripts.rerun_nulls --landmarks 5000 --null markov2 --permutations 500
```

### Step 4 — Collect and verify results

After all three complete:
1. Verify that observed values in each output match: H₀ = 20,411.1, H₁ = 2,224.7
2. Collect existing L=5000 results for order-shuffle and Markov-1 from `results/trajectory_tda_robustness/landmark_sensitivity/`
3. Compile a complete Table 2 data summary (all 5 nulls at L=5000)

## Handoff Summary (produce when complete)

Report to Agent 5 (Paper) — the complete Table 2 replacement data:

For each null model (label-shuffle, cohort-shuffle, order-shuffle, Markov-1, Markov-2):
1. Observed H₀ total persistence (should be 20,411.1 for all)
2. Observed H₁ total persistence (should be 2,224.7 for all)
3. Null mean ± std for H₀
4. Null mean ± std for H₁
5. z-score for H₀ and H₁
6. p-value for H₀ and H₁
7. Significance at α=0.05

**CRITICAL: Report the order-shuffle H₁ p-value explicitly.** At L=2,500 this was p=0.20; at L=5,000 Appendix B shows p=0.02. The L=5,000 value needs to be confirmed from the actual output and reported prominently — it changes the interpretation (marginal significance for H₁ under order-shuffle).

## Verification

- All five null models should report the SAME observed values (20,411.1 / 2,224.7)
- Cross-check against `03_ph.json` observed totals
- Cross-check order-shuffle and Markov-1 results against existing `landmark_sensitivity/nulls_order_shuffle_L5000.json` and `nulls_markov1_L5000.json`
- If any observed values do not match, STOP and report the discrepancy

## Resource Notes

This is the most compute-intensive agent task. 500 permutations × 3 null models at L=5000 will take significant time. If the machine supports it, the three null models can run in parallel (assuming `rerun_nulls.py` supports separate null type flags). If not, run sequentially — label-shuffle → cohort-shuffle → Markov-2.
