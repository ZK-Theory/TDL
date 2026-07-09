# Task Prompt — T-C1-1: C1 persistent-Laplacian Fiedler-curve Markov-1 null battery

**Branch:** `run/c1-pl-fiedler-null`
**Pre-registration JSON:** `results/trajectory_tda_bhps/pre_registrations_2026-07-07.json`
**Vault pre-reg:** `vault/00-Meta/Discovery/c1-persistent-laplacian-dispatch-prereg-draft-2026-07-03.md` (LOCKED 2026-07-07)
**Paper target:** none — Discovery Harness candidate (Track-C flagship candidate, no paper number assigned). A POSITIVE outcome licenses only a further analysis pre-registration, not manuscript text.

**STOP condition:** this Task Prompt is dispatch preparation. Do not launch the B=1000
battery except from an explicitly approved Worker session with the timing pre-flight
(below) completed and reported to the Manager first.

---

## Objective

Test whether the persistent-Laplacian non-harmonic spectrum (Fiedler curve λ₁(t)) of
the observed BHPS 9-state employment-state transition graph (n=8509 trajectories)
differs significantly from a Markov-1 null distribution (B=1000). Primary statistic:
Integrated Fiedler Area (IFA), one-sided permutation p-value. Secondary: pointwise
comparison at each of the 35 filtration thresholds with Benjamini-Hochberg FDR
(α=0.05). Emit a date-suffixed result JSON and update the Discovery backlog per the
decision rule (positive/marginal/negative — see pre-registration JSON).

---

## Environment

Standard `uv run --env-file .env` — no WSL step for this task (unlike MCbiF). PETLS
is a real dependency (`pyproject.toml`, `uv.lock`) as of commit on `pipe/c1-pl-module`
(merge that branch, or cherry-pick `trajectory_tda/topology/persistent_laplacian.py`
+ `pyproject.toml`/`uv.lock` changes, before starting this task).

**Mandatory PATH prepend before running any script that imports petls (PowerShell):**

```powershell
$env:PATH = "C:\msys64\ucrt64\bin;" + $env:PATH
```

The module itself calls `os.add_dll_directory(r"C:\msys64\ucrt64\bin")` at import
time (no-op on non-Windows), so this PATH prepend is a belt-and-braces measure for
any subprocess that imports petls outside the module's own guard.

**Backend verification (mandatory first step):** import
`trajectory_tda.topology.persistent_laplacian` and check `PETLS_AVAILABLE`. Record
whichever backend actually ran (`petls`, `petls-pytorch`, or `numpy-schur-scratch`)
in the result JSON's `backend_used` field — do not assume PETLS is available; verify.

---

## Data (frozen — committed input)

| File | Path | Role |
|------|------|------|
| BHPS trajectory sequences | `results/trajectory_tda_bhps/01_trajectories_sequences.json` | n=8509 state-sequence lists; committed (worktree), SHA-256 `b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490` |

**Provenance gate (pre-flight step 1):** compute SHA-256 of the sequences file and
confirm it matches the value above before any analysis. If it differs, STOP and
escalate — do not proceed on a different data vintage than this pre-registration.

---

## Pre-flight (before launching the battery)

1. Verify `trajectory_tda/topology/persistent_laplacian.py` is present (merged from
   `pipe/c1-pl-module`) and `compute_fiedler_curve` importable.
2. Confirm `PETLS_AVAILABLE` and record the live backend.
3. Compute SHA-256 of `01_trajectories_sequences.json`; confirm match.
4. **Null-model-invariance audit (mandatory before B=1000):** run ONE null draw,
   confirm its rebuilt distance matrix differs from the observed `D`, and that this
   is a rebuild-from-synthetic-trajectories operation (not a shuffle of a cached
   scalar or of `D` itself) — see `null_model.invariance_requirement` in the
   pre-registration JSON.
5. **Cost estimate (mandatory):** time one full null draw (Markov-1 shuffle of 8509
   trajectories → transition graph → 35-step Fiedler curve). At 1.4s for the
   observed-only gate check on this 9-node substrate, B=1000 draws at ≥4 workers
   should be well under the 2h wall-time budget — but confirm empirically before
   committing to the full battery; surface to Manager if the estimate exceeds 30
   minutes projected total.

---

## Method

```python
import hashlib
import json
from pathlib import Path

import numpy as np
from joblib import Parallel, delayed

from trajectory_tda.topology.persistent_laplacian import (
    PETLS_AVAILABLE,
    PETLS_BACKEND_NAME,
    build_undirected_graph,
    compute_fiedler_curve,
)

STATES = ["EL", "EM", "EH", "UL", "UM", "UH", "IL", "IM", "IH"]
STATE_TO_IDX = {s: i for i, s in enumerate(STATES)}
N_STATES = len(STATES)
SEQ_PATH = Path("results/trajectory_tda_bhps/01_trajectories_sequences.json")
EXPECTED_SHA256 = "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490"

raw = SEQ_PATH.read_bytes()
substrate_sha256 = hashlib.sha256(raw).hexdigest()
assert substrate_sha256 == EXPECTED_SHA256, "substrate vintage mismatch — STOP, do not proceed"
sequences = json.loads(raw)


def build_counts(seqs: list[list[str]]) -> np.ndarray:
    C = np.zeros((N_STATES, N_STATES), dtype=np.int64)
    for seq in seqs:
        for a, b in zip(seq[:-1], seq[1:]):
            if a in STATE_TO_IDX and b in STATE_TO_IDX:
                C[STATE_TO_IDX[a], STATE_TO_IDX[b]] += 1
    return C


def markov1_shuffle(seqs: list[list[str]], rng: np.random.RandomState) -> list[list[str]]:
    """Same estimation approach as permutation_nulls.py _markov_shuffle(order=1),
    stopping before re-embedding — only the raw synthetic sequences are needed to
    rebuild the transition graph."""
    tm = np.zeros((N_STATES, N_STATES), dtype=np.float64)
    init_counts = np.zeros(N_STATES, dtype=np.float64)
    for seq in seqs:
        if len(seq) == 0:
            continue
        s0 = STATE_TO_IDX.get(seq[0])
        if s0 is not None:
            init_counts[s0] += 1
        for t in range(len(seq) - 1):
            i, j = STATE_TO_IDX.get(seq[t]), STATE_TO_IDX.get(seq[t + 1])
            if i is not None and j is not None:
                tm[i, j] += 1
    row_sums = tm.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    tm /= row_sums
    init_probs = init_counts / init_counts.sum() if init_counts.sum() > 0 else np.ones(N_STATES) / N_STATES

    synthetic = []
    for seq in seqs:
        length = len(seq)
        if length == 0:
            synthetic.append([])
            continue
        s = [STATES[rng.choice(N_STATES, p=init_probs)]]
        current = STATE_TO_IDX[s[0]]
        for _ in range(length - 1):
            current = rng.choice(N_STATES, p=tm[current])
            s.append(STATES[current])
        synthetic.append(s)
    return synthetic


# Observed
observed_D = build_undirected_graph(build_counts(sequences))
observed_curve = compute_fiedler_curve(observed_D, backend="auto")
thresholds = observed_curve["thresholds"]
dt = np.diff(thresholds, prepend=thresholds[0])
observed_ifa = float(np.trapz(observed_curve["lambda1"], thresholds))


# One null draw (for the invariance audit AND the battery)
def one_null_draw(seed: int) -> dict:
    rng = np.random.RandomState(seed)
    synth = markov1_shuffle(sequences, rng)
    D_null = build_undirected_graph(build_counts(synth))
    curve = compute_fiedler_curve(D_null, thresholds=thresholds, backend="auto")
    ifa = float(np.trapz(curve["lambda1"], thresholds)) if curve["lambda1"] else 0.0
    return {"ifa": ifa, "lambda1_curve": curve["lambda1"], "distance_matrix_differs": not np.array_equal(D_null, observed_D)}


# Parallel: joblib.Parallel(n_jobs=-1, backend='loky') — NOT threading (gudhi/petls GIL)
# Checkpoint every 50 draws to a gitignored .npz scratch file; wall-time flag at 2h
```

---

## Baselines / secondary statistic

Pointwise comparison at each of the 35 thresholds: fraction of null draws with
`λ₁_null(t) ≥ λ₁_obs(t)`. Apply BH-FDR at α=0.05 across the 35 thresholds. Report
which thresholds survive.

---

## Decision rule (locked — do not alter without a pre-reg amendment)

```python
r = sum(1 for draw in null_draws if draw["ifa"] >= observed_ifa)
ifa_p_value = (r + 1) / (B + 1)  # one-sided

pointwise_survivors = bh_fdr_survivor_count(pointwise_p_values, alpha=0.05)  # of 35

if ifa_p_value < 0.05 and pointwise_survivors >= 1:
    verdict = "positive"
elif (ifa_p_value < 0.05 and pointwise_survivors == 0) or (ifa_p_value >= 0.05 and pointwise_survivors >= 5):
    verdict = "marginal"
else:
    verdict = "negative"
```

---

## Output schema (contract `c1-pl-fiedler-null-result`, materialised from
`planned_contracts` in the pre-registration JSON at dispatch time)

Result JSON at `results/trajectory_tda_bhps/c1_pl_fiedler_null_<YYYY-MM-DD>.json`:

```json
{
  "schema_version": "c1-pl-fiedler-null/v1",
  "generated_at": "<ISO timestamp>",
  "task": "T-C1-1",
  "pre_registration": "results/trajectory_tda_bhps/pre_registrations_2026-07-07.json",
  "substrate_sha256": "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490",
  "backend_used": "<petls|petls-pytorch|numpy-schur-scratch>",
  "null_model_construction_verified": true,
  "params": {
    "B": 1000,
    "seed": 42,
    "null_model": "markov-1",
    "n_filtration_thresholds": 35,
    "parallel_workers": "<int>",
    "wall_time_hours_budget": 2
  },
  "observed": {
    "ifa": "<float>",
    "lambda1_curve": ["<float> x35"]
  },
  "null_distribution": {
    "draws": 1000,
    "ifa_values": ["<float> x1000"],
    "percentile_95": "<float>"
  },
  "pointwise": {
    "p_values": ["<float> x35"],
    "bh_fdr_survivors": "<int>"
  },
  "decision": {
    "ifa_p_value": "<float>",
    "pointwise_bh_survivors": "<int>",
    "verdict": "<positive|marginal|negative>"
  }
}
```

---

## Research Assurance Requirements

**Lanes touched:** Topology · Stochastic / Null Model · Statistical (BH-FDR) ·
Paper Claim (deferred — no prose licensed by this task regardless of outcome)

**Governing pre-registration:**
- Vault: `vault/00-Meta/Discovery/c1-persistent-laplacian-dispatch-prereg-draft-2026-07-03.md` (LOCKED 2026-07-07)
- JSON: `results/trajectory_tda_bhps/pre_registrations_2026-07-07.json`
- Registered: 2026-07-07 (dispatch preparation). No amendments. First-dispatch clean design — extends the gate-check pre-reg (2026-07-03) per its own `outcome_to_prose.success` clause.

**Locked parameters (do not change without a pre-reg amendment):**
- null_model = "markov-1" (rebuild transition graph from synthetic trajectories — NOT a shuffle of the cached distance matrix or scalar summaries)
- B = 1000, seed = 42, per-draw seed = 42 + draw_index
- statistic = IFA (trapezoidal integral of λ₁(t) over the 35 thresholds), one-sided p-value
- fdr_method = benjamini-hochberg, alpha = 0.05
- parallel_workers ≥ 4, backend = loky (NOT threading — gudhi/petls hold the GIL, see `reference_gudhi_w2_threading_gil` project convention)
- substrate: 9-state transition graph only — no L=5000 embedding infrastructure
- float32 distance-matrix convention throughout both backends; no epsilon tolerance

**Machine-checkable claims:**
1. Result JSON validates against `contracts/discovery-harness/c1-pl-fiedler-null-result.yaml` (Manager materialises at dispatch from `planned_contracts` in the pre-reg JSON).
2. `null_model_construction_verified = true` (Worker asserts; binding test in `tests/discovery/test_c1_pl_fiedler_null_contract.py`); `std(null_distribution.ifa_values) > 0` (non-degenerate null).
3. `substrate_sha256` matches the on-disk SHA-256 of `01_trajectories_sequences.json` (binding test).
4. `verdict` in `{positive, marginal, negative}` (binding test).
5. `params.B == 1000`, `params.seed == 42`, `params.null_model == "markov-1"`, `backend_used` in `{petls, petls-pytorch, numpy-schur-scratch}`, `len(observed.lambda1_curve) == 35` (binding test).

**Human-review-only claims:**
- Interpretation of the pointwise BH-FDR survivor pattern (which thresholds, why).
- MARGINAL-outcome follow-up scoping (Manager/User call, not Worker).
- Any subgroup-extension interpretation (conditional on POSITIVE primary only).

**Partial criteria:** if the pre-flight cost estimate (one null draw) projects total
B=1000 wall time beyond the 2h budget at ≥4 workers, surface to Manager with the
timing data before launching the full battery — do not silently down-scope B or
skip workers.

**Vault obligation:** write a `[RESULT]` entry (POSITIVE/MARGINAL) or `[NEGATIVE]`
entry (NEGATIVE verdict) to `04-Methods/Computational-Log.md` (top-of-page,
reverse-chronological) after the battery completes, and update the Discovery
backlog C1 entry per the decision rule.

**Validation commands:**
```bash
uv run --env-file .env python -m pytest tests/trajectory_tda/test_persistent_laplacian.py -v
uv run --env-file .env python -m pytest tests/discovery/test_c1_pl_fiedler_null_contract.py -v
uv run --env-file .env python tools/apm_task_prompt_check.py .apm/bus/<agent>/task.md
```

---

## Commit message prefix

`[RESULT] T-C1-1: C1 persistent-Laplacian Fiedler null — <verdict> (IFA_p=<x>, BH_survivors=<n>/35)`
