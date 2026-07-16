# Research context: TDA-Research/00-Meta/Discovery/mcbif-weighted-nerve-employment-dispatch-prereg-2026-07-10.md
# Purpose: Confirmatory tau-locked (tau=2) weighted-nerve MCbiF battery on the
#   USoc integration (19,912x13) and BHPS replication (5,363x13) employment
#   substrates, per the LOCKED 2026-07-10 pre-registration: B=1000 uniform
#   wave-order permutations (default_rng(42+b).permutation(13)), primary
#   statistic h1_total_area, TWO-SIDED p, BH-FDR across the 2 substrates,
#   redundancy gates |Spearman rho| < 0.95 vs mean adjacent ARI / conditional
#   entropy. Consumes trajectory_tda.topology.mcbif_nerve + f2_betti (merged,
#   cellwise-validated) — this script adds no new topology. Gate 0 per arm is
#   computed and persisted BEFORE any null compute; the USoc observed primary
#   must reproduce the spike value (1644.0) or the battery refuses to launch
#   nulls (fail-closed canary). Seeds: SEED=42, per-draw default_rng(42+b).
"""Confirmatory weighted-nerve employment MCbiF battery (tau=2, two-sided).

Stages (run in this order; each persists to the PROJ_ROOT checkpoint dir):

1. ``--stage gate0 --arm both``: substrate verification (sha256, alphabet,
   eligibility), global nerve build with a tau=1 cross-check against
   ``nerve_cell_skeleton``, Gate 0 (complete adjacent fraction < 0.9 AND
   observed h1_total_area > 0), and — integration arm only — the fail-closed
   spike-reproduction canary.
2. ``--stage nulls --arm <arm>``: invariance audit on one draw, >=8-unit
   benchmark with a wall-time projection gate, then the full tau=2 subset
   cache (checkpointed) and the B=1000 null statistic vectors.
3. ``--stage assemble``: assembles the committed result JSON (date-suffixed,
   never overwriting) from the per-arm checkpoints, computes BH-FDR across
   the two substrates, the redundancy gates, and the locked verdict.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import statistics as pystats
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from ctypes import wintypes
from datetime import date, datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

from trajectory_tda.topology.f2_betti import _rank_f2_int_rows
from trajectory_tda.topology.mcbif_nerve import hf_statistics, masks_from_partitions, nerve_cell_skeleton

WORKTREE = Path(__file__).resolve().parents[2]
PROJ_ROOT = Path(r"C:\Users\steph\TDL")
CHECKPOINT_DIR = PROJ_ROOT / "results" / "trajectory_tda_mcbif" / "checkpoints"
RESULT_DIR = WORKTREE / "results" / "trajectory_tda_mcbif"

SCHEMA_VERSION = "mcbif-weighted-nerve-employment/v1"
PREREG = "mcbif-weighted-nerve-employment-dispatch-prereg-2026-07-10"
TAU = 2  # LOCKED by the spike's smallest-tau priority rule; any other value violates the contract.
B = 1000
SEED = 42
W = 13
ALPHA = 0.05
REDUNDANCY_GATE = 0.95
TEST_KIND = "two-sided"
STATE_ORDER = ["EH", "EL", "EM", "IH", "IL", "IM", "UH", "UL", "UM"]
VALID_WAVES = list(range(W))

# Spike reference (scratch/discovery_spikes/mcbif-weighted-nerve-employment/
# weighted_spike_output.json, per_tau["2"].observed_statistics, run 2026-07-10,
# spike commit 4e2dd98): the integration observed primary at tau=2. The battery
# must reproduce this exactly before nulls launch (Gate: input/code drift).
SPIKE_H1_TOTAL_AREA_INTEGRATION = 1644.0

SUBSTRATES: dict[str, dict[str, str | int]] = {
    "integration": {
        "path": "results/trajectory_tda_integration/01_trajectories_sequences.json",
        "sha256": "7a4869170bb8c0f096c407a636ec09ee1926946372b27c18762734d96059e3b8",
        "n_eligible": 19912,
    },
    "bhps": {
        "path": "results/trajectory_tda_bhps/01_trajectories_sequences.json",
        "sha256": "b5328c83edfb82bfd8e5e5b14e8df18fbc3d595f1e7dec4bd4f602f581d40490",
        "n_eligible": 5363,
    },
}

STAT_NAMES = [
    "h1_total_area",
    "h1_lag1_area",
    "h1_lag2_area",
    "h1_lag3_area",
    "h1_lag_weighted_area",
    "h1_endpoint",
    "h1_max",
    "h0_total_area",
    "h0_lag1_area",
]
PRIMARY = "h1_total_area"
DESCRIPTIVE = ["h1_lag2_area", "h1_lag3_area", "h1_lag_weighted_area"]

# ── worker globals (set by _init_worker; ProcessPoolExecutor initializer) ────
_G: dict[str, Any] = {}


def _init_worker(
    edge_buckets: dict[tuple[int, int], list[tuple[int, int]]],
    tri_buckets: dict[tuple[int, int, int], list[tuple[int, int, int]]],
    wave_start: dict[int, int],
    n_labels: dict[int, int],
) -> None:
    """Install the per-arm nerve buckets as worker-process globals."""
    _G["edge_buckets"] = edge_buckets
    _G["tri_buckets"] = tri_buckets
    _G["wave_start"] = wave_start
    _G["n_labels"] = n_labels


def eval_subset(subset: tuple[int, ...]) -> tuple[tuple[int, ...], int, int]:
    """(beta0, beta1) of the tau-thresholded nerve on a set of original waves.

    Identical computation to the registered spike driver (reference
    implementation; scratch/discovery_spikes/mcbif-weighted-nerve-employment/
    run_weighted_spike.py): union-find beta0 over the cell's edges, then F2
    boundary rank over the cell's triangles via the shared row-reduction.

    Args:
        subset: Sorted tuple of original wave indices forming the cell.

    Returns:
        ``(subset, beta0, beta1)``.
    """
    edge_buckets = _G["edge_buckets"]
    tri_buckets = _G["tri_buckets"]
    wave_start = _G["wave_start"]
    n_labels = _G["n_labels"]

    base: dict[int, int] = {}
    n_verts = 0
    for w in subset:
        base[w] = n_verts
        n_verts += n_labels[w]

    parent = list(range(n_verts))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    n_comp = n_verts
    n_edges = 0
    for a, b in combinations(subset, 2):
        for i, j in edge_buckets.get((a, b), ()):
            n_edges += 1
            ri, rj = find(base[a] + i - wave_start[a]), find(base[b] + j - wave_start[b])
            if ri != rj:
                parent[ri] = rj
                n_comp -= 1
    rank_b1 = n_verts - n_comp

    local: dict[int, int] = {}
    _idx = local.setdefault
    rows = [
        (1 << _idx(e1, len(local))) | (1 << _idx(e2, len(local))) | (1 << _idx(e3, len(local)))
        for a, b, c in combinations(subset, 3)
        for e1, e2, e3 in tri_buckets.get((a, b, c), ())
    ]
    rank_b2 = _rank_f2_int_rows(rows)
    return subset, n_comp, n_edges - rank_b1 - rank_b2


def load_partitions(arm: str) -> tuple[list[NDArray[np.int64]], str, int]:
    """Load, sha-verify, and partition an arm's sequences file.

    Enforces the pre-registered eligibility (len >= 13, first 13 waves) and the
    crosswalk mandate: the observed state alphabet must equal the integration
    9-code set exactly.

    Args:
        arm: ``"integration"`` or ``"bhps"``.

    Returns:
        ``(partitions, sha256, n_eligible)`` with one int64 label array per wave.

    Raises:
        SystemExit: On sha mismatch, alphabet mismatch, or eligibility-count
            mismatch against the locked pre-registration.
    """
    spec = SUBSTRATES[arm]
    # Gitignored intermediate: lives at PROJ_ROOT, not in worktrees (two-path
    # rule, .claude/rules/apm-outputs.md); the sha256 pin below is the
    # provenance guarantee.
    path = PROJ_ROOT / str(spec["path"])
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if sha != spec["sha256"]:
        sys.exit(f"FATAL {arm}: sequences sha256 {sha} != locked {spec['sha256']} ({path})")
    sequences = json.loads(raw)
    eligible = [i for i, seq in enumerate(sequences) if len(seq) > max(VALID_WAVES)]
    if len(eligible) != spec["n_eligible"]:
        sys.exit(f"FATAL {arm}: n_eligible {len(eligible)} != locked {spec['n_eligible']}")
    observed_states = sorted({sequences[i][w] for i in eligible for w in VALID_WAVES})
    if observed_states != sorted(STATE_ORDER):
        sys.exit(f"FATAL {arm}: state alphabet {observed_states} != locked 9-code set {sorted(STATE_ORDER)}")
    state_map = {s: i for i, s in enumerate(STATE_ORDER)}
    partitions = [np.asarray([state_map[sequences[i][w]] for i in eligible], dtype=np.int64) for w in VALID_WAVES]
    return partitions, sha, len(eligible)


def build_global_nerve(partitions: list[NDArray[np.int64]]) -> dict[str, Any]:
    """Enumerate the full-range weighted nerve and cross-check at tau=1.

    Records pairwise/triple intersection cardinalities so tau-thresholded
    buckets can be derived, and pins the tau=1 enumeration against the merged
    ``nerve_cell_skeleton`` module (pre-reg: "enumeration cross-checked vs
    nerve_cell_skeleton at tau=1 per arm").

    Args:
        partitions: One int64 label array per wave.

    Returns:
        Dict with vertices, scales, wave_start, n_labels, edge_rec, tri_rec,
        and edge_index.

    Raises:
        SystemExit: If the tau=1 enumeration disagrees with the module.
    """
    masks = masks_from_partitions(partitions)
    vertices = sorted(masks)
    vmasks = [masks[v] for v in vertices]
    scales = [m for m, _ in vertices]
    n = len(vertices)
    offset = np.searchsorted(scales, np.arange(W + 1), side="left")
    wave_start = {w: int(offset[w]) for w in VALID_WAVES}
    n_labels = {w: int(offset[w + 1] - offset[w]) for w in VALID_WAVES}

    edge_rec: list[tuple[int, int, int]] = []
    edge_inter: list[int] = []
    for i in range(n):
        mi = vmasks[i]
        for j in range(i + 1, n):
            inter = mi & vmasks[j]
            if inter:
                edge_rec.append((i, j, inter.bit_count()))
                edge_inter.append(inter)
    tri_rec: list[tuple[int, int, int, int]] = []
    for (i, j, _), mij in zip(edge_rec, edge_inter, strict=True):
        for k in range(j + 1, n):
            t = mij & vmasks[k]
            if t:
                tri_rec.append((i, j, k, t.bit_count()))

    ref_v, ref_e, ref_t = nerve_cell_skeleton(masks, 0, W - 1)
    if ref_v != vertices or {(i, j) for i, j, _ in edge_rec} != set(ref_e):
        sys.exit("FATAL: tau=1 vertex/edge enumeration != nerve_cell_skeleton — do not proceed")
    if {(i, j, k) for i, j, k, _ in tri_rec} != set(ref_t):
        sys.exit("FATAL: tau=1 triangle enumeration != nerve_cell_skeleton — do not proceed")

    return {
        "vertices": vertices,
        "scales": scales,
        "wave_start": wave_start,
        "n_labels": n_labels,
        "edge_rec": edge_rec,
        "tri_rec": tri_rec,
        "edge_index": {(i, j): k for k, (i, j, _) in enumerate(edge_rec)},
    }


def buckets_for_tau(nerve: dict[str, Any], tau: int) -> tuple[dict, dict]:
    """tau-thresholded edge and triangle buckets keyed by wave tuples."""
    scales = nerve["scales"]
    edge_index = nerve["edge_index"]
    eb: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for i, j, c in nerve["edge_rec"]:
        if c >= tau:
            eb.setdefault((scales[i], scales[j]), []).append((i, j))
    tb: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for i, j, k, c in nerve["tri_rec"]:
        if c >= tau:
            key = (scales[i], scales[j], scales[k])
            triple = (edge_index[(i, j)], edge_index[(i, k)], edge_index[(j, k)])
            tb.setdefault(key, []).append(triple)
    return eb, tb


def complete_adjacent_fraction(nerve: dict[str, Any], tau: int) -> tuple[float, list[dict[str, Any]]]:
    """Gate-0 saturation check: fraction of adjacent wave pairs fully bipartite at tau."""
    scales = nerve["scales"]
    n_labels = nerve["n_labels"]
    adj_counts: dict[tuple[int, int], list[int]] = {}
    for i, j, c in nerve["edge_rec"]:
        wa, wb = scales[i], scales[j]
        if wb == wa + 1:
            adj_counts.setdefault((wa, wb), []).append(c)
    detail: list[dict[str, Any]] = []
    n_complete = 0
    for w in range(W - 1):
        possible = n_labels[w] * n_labels[w + 1]
        have = sum(1 for c in adj_counts.get((w, w + 1), ()) if c >= tau)
        complete = have == possible
        n_complete += complete
        detail.append({"pair": [w, w + 1], "n_edges": have, "n_possible": possible, "complete": complete})
    return n_complete / float(W - 1), detail


def null_orderings() -> list[tuple[int, ...]]:
    """The B pre-registered uniform wave-order permutations (per-draw seeds 42+b)."""
    return [tuple(int(x) for x in np.random.default_rng(SEED + b).permutation(W)) for b in range(B)]


def needed_subsets(orderings: list[tuple[int, ...]]) -> list[tuple[int, ...]]:
    """Distinct wave subsets required to grid every ordering (frozenset cache keys)."""
    needed: set[frozenset[int]] = set()
    for seq in orderings:
        for s in range(W):
            for t in range(s, W):
                needed.add(frozenset(seq[s : t + 1]))
    return sorted((tuple(sorted(sub)) for sub in needed), key=len)


def grid_from_cache(
    seq: tuple[int, ...], cache: dict[frozenset[int], tuple[int, int]]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """HF0/HF1 grids for one ordering from the subset cache."""
    m = len(seq)
    hf0 = np.full((m, m), np.nan)
    hf1 = np.full((m, m), np.nan)
    for s in range(m):
        for t in range(s, m):
            b0, b1 = cache[frozenset(seq[s : t + 1])]
            hf0[s, t] = b0
            hf1[s, t] = b1
    return hf0, hf1


def baseline_matrices(partitions: list[NDArray[np.int64]]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Pairwise adjusted-Rand and conditional-entropy matrices between waves."""
    n_states = len(STATE_ORDER)
    n_units = len(partitions[0])
    ari = np.zeros((W, W))
    ce = np.zeros((W, W))
    ent = np.zeros(W)
    for a in range(W):
        counts = np.bincount(partitions[a], minlength=n_states) / n_units
        nz = counts[counts > 0]
        ent[a] = float(-(nz * np.log(nz)).sum())
    for a in range(W):
        for b in range(W):
            if a == b:
                continue
            if b > a:
                ari[a, b] = ari[b, a] = adjusted_rand_score(partitions[a], partitions[b])
            joint = np.bincount(partitions[a] * n_states + partitions[b], minlength=n_states**2) / n_units
            nz = joint[joint > 0]
            ce[a, b] = float(-(nz * np.log(nz)).sum()) - ent[a]
    return ari, ce


def sequence_baselines(seq: tuple[int, ...], ari: NDArray[np.float64], ce: NDArray[np.float64]) -> dict[str, float]:
    """Mean adjacent ARI / conditional entropy of one wave ordering."""
    adj = list(zip(seq[:-1], seq[1:], strict=False))
    return {
        "mean_adjacent_ari": float(np.mean([ari[a, b] for a, b in adj])),
        "mean_adjacent_conditional_entropy": float(np.mean([ce[a, b] for a, b in adj])),
    }


def two_sided_p(null_values: NDArray[np.float64], observed: float) -> dict[str, float]:
    """Pre-registered two-sided permutation p: min(1, 2*min(p_lower, p_upper)).

    ``p_lower = (1 + #{null <= obs}) / (B + 1)`` and symmetrically for the upper
    tail; both tails are reported per the locked pre-registration.
    """
    n = len(null_values)
    p_lower = float((1 + np.sum(null_values <= observed)) / (n + 1))
    p_upper = float((1 + np.sum(null_values >= observed)) / (n + 1))
    return {"p_lower": p_lower, "p_upper": p_upper, "p_two": min(1.0, 2.0 * min(p_lower, p_upper))}


def bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg step-up adjusted p-values (monotonised, capped at 1)."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        running = min(running, min(1.0, p_values[idx] * m / (rank + 1)))
        adjusted[idx] = running
    return adjusted


def decide_verdict(arms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Locked decision rule over the two substrates.

    An arm's rejection is ``p_fdr <= alpha`` on the primary; its gates pass when
    both |rho| < 0.95. "Effective" rejection = rejection AND gates passing there.
    ADDITIVE: effective on both. NEGATIVE: no rejection anywhere. REDUNDANT:
    rejections exist but none survive its arm's gates ("a redundancy gate fails
    wherever rejection occurs"). PARTIAL-SIGNAL: exactly one effective rejection.

    Args:
        arms: Per-arm dict with ``p_fdr``, ``rho_ari``, ``rho_ce``.

    Returns:
        ``{"verdict": ..., "per_arm": {...}, "rationale": ...}``.
    """
    per_arm: dict[str, dict[str, Any]] = {}
    for arm, rec in arms.items():
        rejected = float(rec["p_fdr"]) <= ALPHA
        gates_pass = abs(float(rec["rho_ari"])) < REDUNDANCY_GATE and abs(float(rec["rho_ce"])) < REDUNDANCY_GATE
        per_arm[arm] = {"rejected": rejected, "gates_pass": gates_pass, "effective": rejected and gates_pass}
    rejections = [a for a, r in per_arm.items() if r["rejected"]]
    effective = [a for a, r in per_arm.items() if r["effective"]]
    if len(effective) == len(arms) and len(arms) == 2:
        verdict = "additive"
        rationale = "primary p_fdr <= 0.05 on both substrates with both redundancy gates passing on both"
    elif not rejections:
        verdict = "negative"
        rationale = "no rejection after BH-FDR on either substrate"
    elif not effective:
        verdict = "redundant"
        rationale = f"rejection on {rejections} but a redundancy gate fails wherever rejection occurs"
    else:
        verdict = "partial-signal"
        rationale = f"rejection surviving gates on exactly one substrate ({effective[0]})"
    return {"verdict": verdict, "per_arm": per_arm, "rationale": rationale}


def _peak_rss_gib() -> float | None:
    """Parent-process peak working set in GiB (workers not instrumented)."""
    try:

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        k32 = ctypes.windll.kernel32
        fn = k32.K32GetProcessMemoryInfo
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        fn.restype = wintypes.BOOL
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        if not fn(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return None
        return pmc.PeakWorkingSetSize / (1024**3)
    except Exception:
        return None


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=WORKTREE, capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _ckpt_path(arm: str, kind: str) -> Path:
    return CHECKPOINT_DIR / f"{arm}_tau{TAU}_{kind}.json"


def _load_ckpt(arm: str, kind: str) -> dict[str, Any] | None:
    path = _ckpt_path(arm, kind)
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_ckpt(arm: str, kind: str, payload: dict[str, Any]) -> None:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    _ckpt_path(arm, kind).write_text(json.dumps(payload))


def run_gate0(arm: str) -> dict[str, Any]:
    """Stage 1 for one arm: verification, tau=1 cross-check, Gate 0, canary.

    Persists the Gate-0 record (and the observed-window subset cache) to the
    checkpoint dir BEFORE any null compute exists for the arm.
    """
    t0 = time.perf_counter()
    partitions, sha, n_eligible = load_partitions(arm)
    print(f"[{arm}] partitions {n_eligible} x {W}; sha256 verified", flush=True)
    nerve = build_global_nerve(partitions)
    print(
        f"[{arm}] global nerve cross-checked vs nerve_cell_skeleton at tau=1: "
        f"{len(nerve['vertices'])} vertices, {len(nerve['edge_rec'])} edges, {len(nerve['tri_rec'])} triangles",
        flush=True,
    )
    frac, detail = complete_adjacent_fraction(nerve, TAU)
    eb, tb = buckets_for_tau(nerve, TAU)
    _init_worker(eb, tb, nerve["wave_start"], nerve["n_labels"])

    observed = tuple(VALID_WAVES)
    obs_windows = sorted(
        {tuple(sorted(frozenset(observed[s : t + 1]))) for s in range(W) for t in range(s, W)}, key=len
    )
    obs_cache: dict[str, list[int]] = {}
    for sub in obs_windows:
        _, b0, b1 = eval_subset(sub)
        obs_cache[",".join(map(str, sub))] = [b0, b1]
    cache = {frozenset(map(int, k.split(","))): (v[0], v[1]) for k, v in obs_cache.items()}
    hf0, hf1 = grid_from_cache(observed, cache)
    obs_stats = hf_statistics(hf0, hf1)

    gate_pass = frac < 0.9 and obs_stats[PRIMARY] > 0
    record = {
        "arm": arm,
        "sha256": sha,
        "n_eligible": n_eligible,
        "tau": TAU,
        "complete_adjacent_fraction": frac,
        "adjacent_detail": detail,
        "observed_statistics": obs_stats,
        "gate0_passed": bool(gate_pass),
        "infeasible": not gate_pass,
        "n_edges_tau": sum(1 for _, _, c in nerve["edge_rec"] if c >= TAU),
        "n_triangles_tau": sum(1 for _, _, _, c in nerve["tri_rec"] if c >= TAU),
        "observed_window_cache": obs_cache,
        "elapsed_seconds": time.perf_counter() - t0,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

    if arm == "integration":
        reproduced = obs_stats[PRIMARY] == SPIKE_H1_TOTAL_AREA_INTEGRATION
        record["spike_reproduction"] = {
            "expected_h1_total_area": SPIKE_H1_TOTAL_AREA_INTEGRATION,
            "observed_h1_total_area": obs_stats[PRIMARY],
            "reproduced": bool(reproduced),
        }
        if not reproduced:
            _save_ckpt(arm, "gate0", record)
            sys.exit(
                f"FATAL {arm}: observed {PRIMARY}={obs_stats[PRIMARY]} != spike "
                f"{SPIKE_H1_TOTAL_AREA_INTEGRATION} — input or code drift; nulls NOT launched. Escalate."
            )

    _save_ckpt(arm, "gate0", record)
    status = "PASS" if gate_pass else "FAIL -> arm INFEASIBLE (escalate)"
    print(
        f"[{arm}] Gate 0 {status}: complete adjacent fraction {frac:.3f}, "
        f"{PRIMARY}={obs_stats[PRIMARY]:.0f} ({record['elapsed_seconds']:.0f}s)",
        flush=True,
    )
    return record


def run_nulls(arm: str, workers: int, wall_hours: float, checkpoint_every: int) -> dict[str, Any]:
    """Stage 2 for one arm: invariance audit, benchmark, subset cache, null vectors.

    Refuses to run unless the arm's Gate-0 checkpoint exists and passed
    (acceptance criterion: Gate 0 recorded per arm before that arm's null
    compute exists).
    """
    gate = _load_ckpt(arm, "gate0")
    if gate is None:
        sys.exit(f"FATAL {arm}: no gate0 checkpoint — run --stage gate0 first")
    if not gate["gate0_passed"]:
        sys.exit(f"FATAL {arm}: Gate 0 failed — arm is INFEASIBLE per the pre-reg; nulls must not run")
    if arm == "integration" and not gate.get("spike_reproduction", {}).get("reproduced", False):
        sys.exit(f"FATAL {arm}: spike reproduction record missing/failed — nulls must not run")

    t_start = time.perf_counter()

    def wall_left() -> float:
        return wall_hours * 3600 - (time.perf_counter() - t_start)

    partitions, _, _ = load_partitions(arm)
    nerve = build_global_nerve(partitions)
    eb, tb = buckets_for_tau(nerve, TAU)
    _init_worker(eb, tb, nerve["wave_start"], nerve["n_labels"])

    observed = tuple(VALID_WAVES)
    orderings = [observed, *null_orderings()]
    subsets = needed_subsets(orderings)
    print(f"[{arm}] distinct subsets needed for B={B}: {len(subsets)}", flush=True)

    cache: dict[frozenset[int], tuple[int, int]] = {
        frozenset(map(int, k.split(","))): (v[0], v[1]) for k, v in gate["observed_window_cache"].items()
    }

    # ── invariance audit on one draw (perturbation + shape + centering) ──────
    draw0 = orderings[1]
    audit_windows = sorted({tuple(sorted(frozenset(draw0[s : t + 1]))) for s in range(W) for t in range(s, W)}, key=len)
    for sub in audit_windows:
        if frozenset(sub) not in cache:
            _, b0, b1 = eval_subset(sub)
            cache[frozenset(sub)] = (b0, b1)
    hf0_d, hf1_d = grid_from_cache(draw0, cache)
    draw0_stats = hf_statistics(hf0_d, hf1_d)
    displaced = draw0_stats[PRIMARY] != gate["observed_statistics"][PRIMARY]
    invariance_audit = {
        "draw_seed": SEED + 0,
        "draw_order": list(draw0),
        "draw_primary": draw0_stats[PRIMARY],
        "observed_primary": gate["observed_statistics"][PRIMARY],
        "statistic_displaced_on_draw0": bool(displaced),
        "grid_shape_checked": list(hf1_d.shape) == [W, W],
        "centering_statement": (
            "wave-order permutation null; not a parametric fit through the statistic's substrate, "
            "so the null is NOT centred at the observed value by construction — displacement on a "
            "permuted draw is the audit signal (pre-reg invariance_audit clause)"
        ),
    }
    if not displaced:
        print(f"[{arm}] WARNING: draw 0 primary equals observed — checking further draws", flush=True)

    # ── benchmark: >=8 stratified units from the REAL inputs; project from p75 ─
    rng = np.random.default_rng(SEED)
    sample: list[tuple[int, ...]] = []
    for size in range(3, W + 1):
        pool = [s for s in subsets if len(s) == size and frozenset(s) not in cache]
        if pool:
            take = min(2, len(pool))
            sample.extend(pool[i] for i in rng.choice(len(pool), size=take, replace=False))
    per_unit: list[float] = []
    for sub in sample:
        t0 = time.perf_counter()
        _, b0, b1 = eval_subset(sub)
        per_unit.append(time.perf_counter() - t0)
        cache[frozenset(sub)] = (b0, b1)
    p75 = float(np.percentile(per_unit, 75))
    todo = [s for s in subsets if frozenset(s) not in cache]
    projected_h = p75 * len(todo) / max(workers, 1) / 3600
    benchmark = {
        "n_units": len(sample),
        "seconds_median": pystats.median(per_unit),
        "seconds_min": min(per_unit),
        "seconds_max": max(per_unit),
        "seconds_p75": p75,
        "projected_hours_at_workers": projected_h,
        "workers": workers,
    }
    print(
        f"[{arm}] benchmark {len(sample)} units: median {benchmark['seconds_median']:.3f}s "
        f"(min {benchmark['seconds_min']:.3f} / max {benchmark['seconds_max']:.3f}); "
        f"projected {projected_h:.2f} h at {workers} workers for {len(todo)} subsets",
        flush=True,
    )
    if projected_h > 12:
        sys.exit(f"FATAL {arm}: projection {projected_h:.1f} h exceeds the 12 h stop threshold — escalate")
    if projected_h * 3600 > wall_left():
        sys.exit(f"FATAL {arm}: projection exceeds the {wall_hours} h wall-time flag — escalate")

    # ── full subset cache, parallel, checkpointed; progress line < 60 s ──────
    partial = _load_ckpt(arm, "cache")
    if partial:
        for k, v in partial["cache"].items():
            cache[frozenset(map(int, k.split(",")))] = (v[0], v[1])
        todo = [s for s in subsets if frozenset(s) not in cache]
        print(f"[{arm}] resumed cache checkpoint: {len(todo)} subsets remain", flush=True)

    progress_every = max(1, min(checkpoint_every, int(np.ceil(60.0 / max(p75 / max(workers, 1), 1e-6)))))
    order = sorted(todo, key=len, reverse=True)
    t0 = time.perf_counter()
    done = 0
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker, initargs=(eb, tb, nerve["wave_start"], nerve["n_labels"])
    ) as ex:
        for sub, b0, b1 in ex.map(eval_subset, order, chunksize=8):
            cache[frozenset(sub)] = (b0, b1)
            done += 1
            if done == 1 or done % progress_every == 0 or done == len(order):
                rate = done / max(time.perf_counter() - t0, 1e-9)
                eta_min = (len(order) - done) / max(rate, 1e-9) / 60
                print(
                    f"[{arm}] {done}/{len(order)} subsets ({time.perf_counter() - t0:.0f}s, "
                    f"{rate:.2f}/s, ETA {eta_min:.1f} min)",
                    flush=True,
                )
            if done % checkpoint_every == 0 or done == len(order):
                _save_ckpt(
                    arm,
                    "cache",
                    {"cache": {",".join(map(str, sorted(k))): list(v) for k, v in cache.items()}},
                )
            if wall_left() <= 0:
                _save_ckpt(
                    arm,
                    "cache",
                    {"cache": {",".join(map(str, sorted(k))): list(v) for k, v in cache.items()}},
                )
                sys.exit(f"FATAL {arm}: wall-time flag ({wall_hours} h) hit at {done}/{len(order)} — resumable")
    cache_seconds = time.perf_counter() - t0
    print(f"[{arm}] cache complete: {len(cache)} entries in {cache_seconds:.0f}s", flush=True)

    # ── statistics for every ordering from the cache ─────────────────────────
    ari_m, ce_m = baseline_matrices(partitions)
    rows: list[dict[str, Any]] = []
    for seq in orderings:
        hf0, hf1 = grid_from_cache(seq, cache)
        row: dict[str, Any] = {"sequence": list(seq)}
        row.update(hf_statistics(hf0, hf1))
        row.update(sequence_baselines(seq, ari_m, ce_m))
        rows.append(row)

    result = {
        "arm": arm,
        "invariance_audit": invariance_audit,
        "benchmark": benchmark,
        "cache_seconds": cache_seconds,
        "n_distinct_subsets": len(cache),
        "rows": rows,
        "wall_seconds": time.perf_counter() - t_start,
        "peak_rss_gib_parent": _peak_rss_gib(),
        "workers": workers,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    _save_ckpt(arm, "nulls", result)
    print(f"[{arm}] nulls stage complete in {result['wall_seconds']:.0f}s", flush=True)
    return result


def assemble(out_path: Path | None = None) -> Path:
    """Stage 3: assemble the committed result JSON from per-arm checkpoints."""
    arms = list(SUBSTRATES)
    gate0: dict[str, Any] = {}
    observed: dict[str, Any] = {}
    null_distribution: dict[str, Any] = {}
    redundancy: dict[str, Any] = {}
    decision_inputs: dict[str, dict[str, Any]] = {}
    meta: dict[str, Any] = {}

    for arm in arms:
        g = _load_ckpt(arm, "gate0")
        if g is None:
            sys.exit(f"FATAL: no gate0 checkpoint for {arm}")
        gate0[arm] = {
            "complete_adjacent_fraction": g["complete_adjacent_fraction"],
            "observed_h1_total_area": g["observed_statistics"][PRIMARY],
            "passed": g["gate0_passed"],
            "infeasible": g["infeasible"],
        }
        if "spike_reproduction" in g:
            gate0[arm]["spike_reproduction"] = g["spike_reproduction"]
        observed[arm] = {k: g["observed_statistics"][k] for k in STAT_NAMES}

        n = _load_ckpt(arm, "nulls")
        if n is None:
            sys.exit(f"FATAL: no nulls checkpoint for {arm} (a BLOCKED arm needs a User decision, not assembly)")
        obs_row, null_rows = n["rows"][0], n["rows"][1:]
        if len(null_rows) != B:
            sys.exit(f"FATAL {arm}: {len(null_rows)} null rows != B={B}")
        stats_block: dict[str, Any] = {}
        for name in STAT_NAMES:
            vals = np.asarray([r[name] for r in null_rows], dtype=float)
            entry: dict[str, Any] = two_sided_p(vals, float(obs_row[name]))
            entry.update(
                {
                    "observed": float(obs_row[name]),
                    "null_mean": float(np.mean(vals)),
                    "null_std": float(np.std(vals)),
                    "n_unique": int(len(np.unique(vals))),
                    "null_values": [float(v) for v in vals],
                }
            )
            stats_block[name] = entry
        null_distribution[arm] = stats_block

        primary_vals = np.asarray([r[PRIMARY] for r in null_rows], dtype=float)
        b_ari = np.asarray([r["mean_adjacent_ari"] for r in null_rows], dtype=float)
        b_ce = np.asarray([r["mean_adjacent_conditional_entropy"] for r in null_rows], dtype=float)
        redundancy[arm] = {
            "rho_ari": float(spearmanr(primary_vals, b_ari).statistic),
            "rho_ce": float(spearmanr(primary_vals, b_ce).statistic),
            "gate_threshold_abs": REDUNDANCY_GATE,
        }
        meta[arm] = {
            "invariance_audit": n["invariance_audit"],
            "benchmark": n["benchmark"],
            "n_distinct_subsets": n["n_distinct_subsets"],
            "cache_seconds": n["cache_seconds"],
            "wall_seconds": n["wall_seconds"],
            "peak_rss_gib_parent": n["peak_rss_gib_parent"],
            "workers": n["workers"],
        }

    fdr = bh_adjust([null_distribution[arm][PRIMARY]["p_two"] for arm in arms])
    for arm, p_fdr in zip(arms, fdr, strict=True):
        null_distribution[arm][PRIMARY]["p_fdr"] = p_fdr
        decision_inputs[arm] = {
            "p_fdr": p_fdr,
            "rho_ari": redundancy[arm]["rho_ari"],
            "rho_ce": redundancy[arm]["rho_ce"],
        }
    decision = decide_verdict(decision_inputs)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "pre_registration": PREREG,
        "substrate_sha256": {arm: SUBSTRATES[arm]["sha256"] for arm in arms},
        "params": {
            "tau": TAU,
            "B": B,
            "seed": SEED,
            "per_draw_seeds": "42+b for b in 0..999",
            "W": W,
            "test": TEST_KIND,
            "alpha": ALPHA,
            "primary_statistic": PRIMARY,
            "descriptive_statistics": DESCRIPTIVE,
            "eligibility": "len >= 13, first 13 waves",
            "state_order": STATE_ORDER,
        },
        "gate0": gate0,
        "observed": observed,
        "null_distribution": null_distribution,
        "redundancy": redundancy,
        "decision": decision,
        "metadata": {
            "per_arm": meta,
            "git_commit": _git_commit(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "script": "trajectory_tda/scripts/run_mcbif_weighted_nerve_battery.py",
        },
    }

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    if out_path is None:
        out_path = RESULT_DIR / f"mcbif_weighted_nerve_employment_{date.today().isoformat()}.json"
    if out_path.exists():
        sys.exit(f"FATAL: {out_path} already exists — results are never overwritten")
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"verdict: {decision['verdict']} — wrote {out_path}", flush=True)
    return out_path


def main() -> None:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["gate0", "nulls", "assemble"], required=True)
    ap.add_argument("--arm", choices=["integration", "bhps", "both"], default="both")
    ap.add_argument("--workers", type=int, default=10, help="pre-reg minimum 5")
    ap.add_argument("--wall-hours", type=float, default=4.0, help="pre-reg wall-time flag")
    ap.add_argument("--checkpoint-every", type=int, default=500, help="pre-reg: per 500 subsets")
    args = ap.parse_args()
    if args.stage != "assemble" and args.workers < 5:
        sys.exit("FATAL: pre-reg requires >= 5 workers")

    arms = ["integration", "bhps"] if args.arm == "both" else [args.arm]
    if args.stage == "gate0":
        for arm in arms:
            run_gate0(arm)
    elif args.stage == "nulls":
        for arm in arms:
            run_nulls(arm, args.workers, args.wall_hours, args.checkpoint_every)
    else:
        assemble()


if __name__ == "__main__":
    main()
