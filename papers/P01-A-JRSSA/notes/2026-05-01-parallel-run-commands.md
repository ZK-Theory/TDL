# P01-A Parallel Run Commands

**Created:** 2026-05-01  
**Purpose:** All computation commands for the reviewer response (§11 of the plan).
Run each block in a separate terminal. Wall-clock estimates are from the plan's §11.3.

All commands are run from the repo root (`c:\Users\steph\TDL`).

---

## TERMINAL 1 — ISSUE H1: Matched-L W₂ battery, USoc, 4 nulls (5–8 h)

Addresses: landmark-count inconsistency. Runs label, cohort, order, Markov-1 at L=5000.

```powershell
python -m trajectory_tda.scripts.run_wasserstein_battery `
    --checkpoint-dir results/trajectory_tda_integration `
    --null-types label_shuffle cohort_shuffle order_shuffle markov `
    --markov-order 1 `
    --n-perms 100 --landmarks 5000 `
    --output-name post_audit/04_nulls_wasserstein_w2_L5000_20260501.json `
    --seed 42
```

Output: `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_20260501.json`

---

## TERMINAL 2 — ISSUE H1: Matched-L W₂ battery, USoc, Markov-2 (12–20 h)

Run separately because Markov-2 is the longest job and benefits from a dedicated terminal.

```powershell
python -m trajectory_tda.scripts.run_wasserstein_battery `
    --checkpoint-dir results/trajectory_tda_integration `
    --null-types markov `
    --markov-order 2 `
    --n-perms 100 --landmarks 5000 `
    --output-name post_audit/04_nulls_wasserstein_w2_L5000_markov2_20260501.json `
    --seed 42
```

Output: `results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_markov2_20260501.json`

---

## TERMINAL 3 — ISSUE H2: Stratified Markov-1 W₂, USoc (5–8 h)

Addresses: regime-stratified null misspecification. Uses the fixed regime labels from
`05_analysis.json` (not the broken GMM reload). Seed 43 avoids overlap with Terminal 1.

```powershell
python -m trajectory_tda.scripts.run_wasserstein_battery `
    --checkpoint-dir results/trajectory_tda_integration `
    --null-types stratified_markov1 `
    --n-perms 100 --landmarks 5000 `
    --regime-labels-path results/trajectory_tda_integration/05_analysis.json `
    --output-name stratified_markov/stratified_markov1_W2_L5000_20260501.json `
    --seed 43
```

Output: `results/trajectory_tda_integration/stratified_markov/stratified_markov1_W2_L5000_20260501.json`  
Verify: `regime_distribution` in output must show all 7 regimes with correct counts.

---

## TERMINAL 4 — §10.2: Positive control simulation, USoc (5–8 h)

Generates one Markov-1 synthetic cloud, then tests whether Markov-1 null reproduces its
topology. Expected: p ≈ 0.5 for H₀ and H₁. Seed 44 avoids overlap.

```powershell
python -m trajectory_tda.scripts.run_positive_control `
    --checkpoint-dir results/trajectory_tda_integration `
    --n-perms 100 --landmarks 5000 `
    --seed 44 `
    --output results/trajectory_tda_integration/positive_control/positive_control_markov1_L5000_20260501.json
```

Output: `results/trajectory_tda_integration/positive_control/positive_control_markov1_L5000_20260501.json`

---

## TERMINAL 5 — ISSUE H1: Matched-L W₂ battery, BHPS (2–3 h)

BHPS counterpart for the matched-L comparison. Runs all 4 nulls + Markov-1 at L=5000.

```powershell
python -m trajectory_tda.scripts.run_wasserstein_battery `
    --checkpoint-dir results/trajectory_tda_bhps `
    --null-types label_shuffle cohort_shuffle order_shuffle markov `
    --markov-order 1 `
    --n-perms 100 --landmarks 5000 `
    --output-name post_audit/04_nulls_wasserstein_w2_L5000_20260501.json `
    --seed 42
```

Output: `results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_L5000_20260501.json`

---

## TERMINAL 6 — ISSUE H2: Stratified Markov-1 W₂, BHPS (2–3 h)

BHPS counterpart. k=8 regimes; all above min_regime_n=30 (verified 2026-05-01).

```powershell
python -m trajectory_tda.scripts.run_wasserstein_battery `
    --checkpoint-dir results/trajectory_tda_bhps `
    --null-types stratified_markov1 `
    --n-perms 100 --landmarks 5000 `
    --regime-labels-path results/trajectory_tda_bhps/05_analysis.json `
    --output-name stratified_markov/stratified_markov1_W2_L5000_20260501.json `
    --seed 43
```

Output: `results/trajectory_tda_bhps/stratified_markov/stratified_markov1_W2_L5000_20260501.json`  
Verify: `regime_distribution` must show all 8 BHPS regimes.

---

## Sanity checks before launching

Run these before starting terminals 1–6 to confirm the environment is ready:

```powershell
# Confirm checkpoint sizes
python -c "import numpy as np; e=np.load('results/trajectory_tda_integration/embeddings.npy'); print('USoc:', e.shape)"
python -c "import numpy as np; e=np.load('results/trajectory_tda_bhps/embeddings.npy'); print('BHPS:', e.shape)"

# Confirm regime labels load correctly
python -c "
import sys; sys.path.insert(0, '.')
from trajectory_tda.scripts.run_wasserstein_battery import load_regime_labels
from collections import Counter
print('USoc regimes:', dict(sorted(Counter(load_regime_labels('results/trajectory_tda_integration/05_analysis.json').tolist()).items())))
print('BHPS regimes:', dict(sorted(Counter(load_regime_labels('results/trajectory_tda_bhps/05_analysis.json').tolist()).items())))
"
```

---

## Result verification (after runs complete)

For each output JSON, check:

1. **H1/H2 matched-L runs:** `regime_distribution` must list all 7 (USoc) or 8 (BHPS) regimes.
2. **Positive control:** Both `H0.p_value` and `H1.p_value` should be in [0.3, 0.7].
3. **All runs:** `elapsed_seconds` present; no `"error": "failed"` entries.

```powershell
# Quick p-value check across all outputs (run after completion)
python -c "
import json, pathlib
files = [
    'results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_L5000_20260501.json',
    'results/trajectory_tda_integration/stratified_markov/stratified_markov1_W2_L5000_20260501.json',
    'results/trajectory_tda_integration/positive_control/positive_control_markov1_L5000_20260501.json',
    'results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_L5000_20260501.json',
    'results/trajectory_tda_bhps/stratified_markov/stratified_markov1_W2_L5000_20260501.json',
]
for f in files:
    p = pathlib.Path(f)
    if not p.exists():
        print(f'MISSING: {f}')
        continue
    d = json.load(open(p))
    for null_key, val in d.items():
        if isinstance(val, dict) and 'H0' in val:
            h0, h1 = val['H0']['p_value'], val['H1']['p_value']
            print(f'{p.parent.name}/{p.stem}: {null_key}  H0 p={h0:.4f}  H1 p={h1:.4f}')
        elif null_key in ('H0', 'H1'):
            pass  # handled as part of top-level positive control dict
    if 'H0' in d and 'positive_control' in d:
        print(f'{p.stem}: H0 p={d[\"H0\"][\"p_value\"]:.4f}  H1 p={d[\"H1\"][\"p_value\"]:.4f}  [positive control]')
"
```

---

## Sequencing notes

- Terminals 1–4 are USoc; Terminals 5–6 are BHPS. All are independent — start all six.
- Terminal 2 (Markov-2 USoc) is the longest job (~12–20 h). Start it first.
- If RAM is constrained, prioritise Terminals 3, 4, 5, 6 (stratified + BHPS) — they finish
  fastest and unblock the §4.3 / §7.1 rewrite decision (Outcome A/B/C for ISSUE H2).
- The legacy files are preserved; no command above uses `--overwrite-output`.
