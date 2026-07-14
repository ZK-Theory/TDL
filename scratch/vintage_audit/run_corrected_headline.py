# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: WT-1c — CORRECTED headline sequence-vintage materiality battery.
#   Re-derives the USoc H0/H1 headline W2 statistics on BOTH the orphan (May-2)
#   and canonical (Apr-8) observed diagrams under EXACT Wasserstein-2, against the
#   frozen 2026-05-28 null bank, and pins WHY the committed frozen headline differs.
#
#   Root-cause (verified, see memo): the committed frozen headline H1 W2 values
#   (obs-null 233.68, null-null 175.40) are GREEDY-FALLBACK artifacts of
#   trajectory_tda.topology.vectorisation.wasserstein_distance computed with POT
#   absent on 2026-05-28 (persistence-rank greedy matching, not optimal transport).
#   Exact W2 (POT/EMD present) gives H1 obs-null ~12.4, null-null ~3.6. For H0 the
#   greedy match is optimal (all births 0) so greedy == exact, which is why H0
#   reproduced and H1 did not.
#
#   Pipeline: STAGE A convention gate (greedy reproduces committed -> pins the
#   committed convention, recorded BEFORE any Apr-8 value) -> STAGE B full exact
#   battery (obs-null both vintages + null-null, checkpointed, process-parallel) ->
#   STAGE C exact stat derivation (aggregate_combined-faithful) -> STAGE D triangle-
#   inequality assertion -> result JSON. No pipeline module is edited; no cache or
#   prior result is modified/overwritten.
"""WT-1c corrected exact-W2 headline battery (both vintages) + convention gate."""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent.parent  # .../headline-vintage-materiality
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import _auditlib as al  # noqa: E402

# --- worker-count set from bench_w2.py; overridable via argv[1] ---------------
N_WORKERS = 8
CHECKPOINT_INTERVAL = 10
SEED = al.REF_SEED  # 42
B = 1000
N_NULL_PAIRS_EFFECT = 500  # committed DEFAULT_N_NULL_PAIRS (effect); pvalue uses all B

CKPT_DIR = HERE / "corrected_ckpt"
ORPHAN_SEQ_STATUS = "unknown"

# Committed frozen headline (the comparison target and greedy-gate reference).
COMMITTED = {
    "h0": {
        "mean_obs_null": 64.28028516956785,
        "mean_null_null": 4.312135967816683,
        "d_perm": 51.073746407735484,
        "t_ratio": 14.906831706912568,
    },
    "h1": {
        "mean_obs_null": 233.6845854219639,
        "mean_null_null": 175.39900129744694,
        "d_perm": 22.090334088910506,
        "t_ratio": 1.3323028278004532,
    },
}


# ---------------------------------------------------------------------------
# Solvers
# ---------------------------------------------------------------------------
def _w2_exact_pair(args: tuple) -> tuple[int, float]:
    """Exact W2 (gudhi.wasserstein, POT/EMD, order=2, internal_p=2). Picklable."""
    from gudhi.wasserstein import wasserstein_distance

    idx, a, b = args
    a = np.asarray(a, dtype=np.float64).reshape(-1, 2)
    b = np.asarray(b, dtype=np.float64).reshape(-1, 2)
    if a.shape[0]:
        a = a[np.isfinite(a).all(axis=1)]
    if b.shape[0]:
        b = b[np.isfinite(b).all(axis=1)]
    return idx, float(wasserstein_distance(a, b, order=2, internal_p=2))


def greedy_fallback(f1: np.ndarray, f2: np.ndarray, p: int = 2) -> float:
    """Exact replica of vectorisation.wasserstein_distance fallback (POT-absent path).

    Verified per-pair identical to the real committed helper with POT hidden
    (diag3_verify.py). Greedy match by persistence rank; unmatched -> diagonal.
    """
    f1 = al.finite_pairs(f1)
    f2 = al.finite_pairs(f2)
    if f1.shape[0] == 0 and f2.shape[0] == 0:
        return 0.0
    pers1 = f1[:, 1] - f1[:, 0]
    pers2 = f2[:, 1] - f2[:, 0]
    if f1.shape[0] == 0:
        return float(np.sum((pers2 / 2) ** p) ** (1 / p))
    if f2.shape[0] == 0:
        return float(np.sum((pers1 / 2) ** p) ** (1 / p))
    idx1 = np.argsort(-pers1)
    idx2 = np.argsort(-pers2)
    total = 0.0
    n = min(len(idx1), len(idx2))
    for i in range(n):
        diff = np.abs(f1[idx1[i]] - f2[idx2[i]])
        total += float(np.sum(diff**p))
    for i in range(n, len(idx1)):
        total += (pers1[idx1[i]] / 2) ** p * 2
    for i in range(n, len(idx2)):
        total += (pers2[idx2[i]] / 2) ** p * 2
    return float(total ** (1 / p))


# ---------------------------------------------------------------------------
# Parallel block runner with checkpointing
# ---------------------------------------------------------------------------
def compute_block(name: str, arg_iter: list[tuple], n_workers: int) -> np.ndarray:
    """Compute a block of exact-W2 distances SERIALLY with checkpointing/resume.

    Exact W2 (EMD) on ~5000-6000-pt diagrams is memory-bandwidth bound: loky
    parallelism gives negative scaling here (measured), and repeatedly stalled.
    A single serial process at the diag-measured ~5-10s/pair is the reliable
    path; OS-level parallelism (concurrent instances on disjoint blocks) is the
    scaling lever if needed. ``n_workers`` is retained for signature stability
    but the loop is serial.
    """
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt = CKPT_DIR / f"{name}.npz"
    n = len(arg_iter)
    result = np.full(n, np.nan, dtype=np.float64)
    if ckpt.exists():
        with np.load(ckpt) as data:
            prev = data["w2"]
            result[: len(prev)] = prev[: len(result)]
        done0 = int(np.sum(~np.isnan(result)))
        print(f"  [{name}] resumed: {done0}/{n} done", flush=True)
    todo = [i for i in range(n) if np.isnan(result[i])]
    if not todo:
        print(f"  [{name}] all {n} done", flush=True)
        return result
    print(f"  [{name}] computing {len(todo)}/{n} serially", flush=True)
    t0 = time.time()
    for c, i in enumerate(todo, 1):
        _, result[i] = _w2_exact_pair(arg_iter[i])
        if c % CHECKPOINT_INTERVAL == 0 or c == len(todo):
            np.savez_compressed(ckpt, w2=result)
            done = int(np.sum(~np.isnan(result)))
            dt = time.time() - t0
            eta = (n - done) * (dt / c) / 60.0
            print(f"    [{name}] {done}/{n}  ({dt / c:.2f}s/pair, ETA {eta:.1f} min)", flush=True)
    return result


# ---------------------------------------------------------------------------
# Stat derivation — faithful to _battery_core.aggregate_combined (W2 cell)
# ---------------------------------------------------------------------------
def derive_cell(obs_null_w2: np.ndarray, null_null_w2_all: np.ndarray, dim: int) -> dict:
    from trajectory_tda.topology.vectorisation import compute_w2_ratio_bca_ci

    mean_on = float(obs_null_w2.mean())
    null_null_effect = null_null_w2_all[:N_NULL_PAIRS_EFFECT]
    pvalue_null_null = null_null_w2_all[:B]
    mean_nn = float(null_null_effect.mean())
    std_nn = float(null_null_effect.std())
    d_perm = (mean_on - mean_nn) / std_nn if std_nn > 0 else float("nan")
    t_ratio = mean_on / mean_nn if mean_nn > 0 else float("nan")
    r = int(np.sum(pvalue_null_null >= mean_on))
    w2_pvalue = (r + 1) / (len(pvalue_null_null) + 1)
    r_lower = int(np.sum(pvalue_null_null <= mean_on))
    lower_tail_pvalue = (r_lower + 1) / (len(pvalue_null_null) + 1)
    bca_lo = bca_hi = None
    try:
        _, bca_lo, bca_hi = compute_w2_ratio_bca_ci(obs_null_w2, null_null_effect, seed=SEED)
    except Exception as exc:  # noqa: BLE001
        print(f"    BCa failed dim {dim}: {exc}", flush=True)
    cell = {
        "w2_pvalue": w2_pvalue,
        "pvalue_null_draws": len(pvalue_null_null),
        "effect_null_pairs": len(null_null_effect),
        "t_ratio": t_ratio,
        "bca_ci_lower": bca_lo,
        "bca_ci_upper": bca_hi,
        "d_perm": d_perm,
        "mean_obs_null": mean_on,
        "mean_null_null": mean_nn,
        "obs_null_w2_std": float(obs_null_w2.std()),
        "rank_count": r,
    }
    if dim == 0:
        cell["lower_tail_pvalue"] = lower_tail_pvalue
    return cell


def _match(a: float, b: float, rtol: float) -> bool:
    return abs(a - b) <= rtol * max(1.0, abs(b))


def main() -> None:
    global N_WORKERS
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        N_WORKERS = int(sys.argv[1])
    # OS-level parallelism: `--only=orphan_h1[,apr8_h1,nullnull_h1]` computes just
    # those exact blocks serially and exits (checkpoints reused by the later full/
    # combine run). Run 3 concurrent instances on disjoint blocks; exact W2 does not
    # parallelise inside one process (memory-bandwidth bound), so independent serial
    # processes are the scaling lever.
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = {s for s in a.split("=", 1)[1].split(",") if s}
    t_start = time.time()
    print("=" * 78)
    print("WT-1c CORRECTED headline vintage-materiality battery (exact W2)")
    print("=" * 78)

    # --- Solver identity + POT proof (no silent fallback) ---
    import gudhi

    try:
        import ot

        pot_ver = getattr(ot, "__version__", "unknown")
    except ImportError:
        print(
            "FATAL: POT (ot) not importable — exact gudhi.wasserstein would silently fall back to greedy. ABORT.",
            flush=True,
        )
        sys.exit(3)
    solver = {
        "obs_null_and_null_null": "gudhi.wasserstein.wasserstein_distance(order=2, internal_p=2)",
        "exactness": "POT/EMD optimal transport (exact)",
        "pot_version": pot_ver,
        "gudhi_version": gudhi.__version__,
        "pot_available": True,
        "hera_exact_note": "gudhi.hera(delta=0) is exact but infeasible here (does not "
        "terminate on ~5000-6000-pt diagrams); EMD via POT is the "
        "exact, feasible path and is the same solver the committed "
        "battery used WHEN POT is present.",
        "greedy_convention_ref": "trajectory_tda.topology.vectorisation.wasserstein_distance "
        "POT-absent fallback (persistence-rank greedy)",
    }
    print(f"Solver: gudhi {gudhi.__version__}, POT {pot_ver} (exact EMD). Workers={N_WORKERS}", flush=True)

    # --- Inputs (verify sha256) ---
    global ORPHAN_SEQ_STATUS
    canonical_sha = al.verify_input(al.CANONICAL_SEQUENCES, al.CANONICAL_SHA256)
    if al.ORPHAN_SEQUENCES.exists():
        orphan_sha = al.verify_input(al.ORPHAN_SEQUENCES, al.ORPHAN_SHA256)
        ORPHAN_SEQ_STATUS = "present_and_verified"
    else:
        # File removed from disk after WT-1 (2026-07-12). Not needed here: the
        # orphan-vintage observed diagram is taken directly from the frozen cache,
        # which WT-1 verified reproduces bit-for-bit from the orphan sequences
        # (sha 31bbbce, bottleneck ~1e-308). Record the expected hash.
        orphan_sha = al.ORPHAN_SHA256
        ORPHAN_SEQ_STATUS = (
            "absent_on_disk_2026-07-13; orphan obs taken from frozen cache "
            "(WT-1 verified bit-for-bit reproduction from orphan sha 31bbbce)"
        )
    cache_sha = al.sha256_file(al.USOC_FROZEN_CACHE)
    headline_sha = al.sha256_file(al.USOC_FROZEN_HEADLINE)
    print(f"canonical sha {canonical_sha[:12]}  orphan seq: {ORPHAN_SEQ_STATUS[:40]}", flush=True)

    # --- Diagrams: orphan obs = frozen cache obs (bit-for-bit, verified WT-1) ---
    cache = al.load_cache(al.USOC_FROZEN_CACHE)
    orphan_h = {0: al.finite_pairs(cache["obs_h0_diagram"]), 1: al.finite_pairs(cache["obs_h1_diagram"])}
    null = {0: cache["h0_diagrams"], 1: cache["h1_diagrams"]}
    print(f"null bank B={len(null[0])}; orphan obs H0={orphan_h[0].shape[0]} H1={orphan_h[1].shape[0]}", flush=True)

    # --- apr8 obs diagram: reconstruct from canonical sequences (frozen-loadings) ---
    # Only needed for the apr8_h1 block, the triangle bound, and the full write.
    need_apr8 = only is None or "apr8_h1" in only
    if need_apr8:
        print("Reconstructing Apr-8 canonical obs diagram...", flush=True)
        apr8_recon = al.reconstruct_obs_diagram(al.CANONICAL_SEQUENCES, al.USOC_CHECKPOINT)
        apr8_h = {0: al.finite_pairs(apr8_recon.h0_finite), 1: al.finite_pairs(apr8_recon.h1_finite)}
        apr8_comp = al.compare_diagrams(apr8_recon, cache["obs_h0_diagram"], cache["obs_h1_diagram"])
        print(
            f"apr8 obs H0={apr8_h[0].shape[0]} H1={apr8_h[1].shape[0]}; "
            f"bottleneck vs cache H0={apr8_comp['bottleneck_h0']:.3e} H1={apr8_comp['bottleneck_h1']:.3e}",
            flush=True,
        )
    else:
        apr8_recon = apr8_comp = None
        apr8_h = None

    # --- Null-null pair sampling (aggregate_combined-faithful; same pairs both dims) ---
    rng = np.random.RandomState(SEED)
    rng.seed(SEED)
    nn_pairs = [tuple(int(x) for x in rng.choice(B, size=2, replace=False)) for _ in range(B)]

    # --- OS-parallel worker mode: compute only the requested exact H1 block(s), exit ---
    if only is not None:
        print(f"[--only={sorted(only)}] serial exact-block worker", flush=True)
        if "orphan_h1" in only:
            compute_block("orphan_h1", [(i, orphan_h[1], null[1][i]) for i in range(B)], N_WORKERS)
        if "apr8_h1" in only:
            compute_block("apr8_h1", [(i, apr8_h[1], null[1][i]) for i in range(B)], N_WORKERS)
        if "nullnull_h1" in only:
            compute_block("nullnull_h1", [(k, null[1][i], null[1][j]) for k, (i, j) in enumerate(nn_pairs)], N_WORKERS)
        print("[--only] done; exiting.", flush=True)
        return

    # ===================================================================
    # STAGE A — CONVENTION GATE (greedy reproduces committed frozen headline)
    #   Recorded BEFORE any Apr-8 exact value is computed. Stores the greedy
    #   obs-null / null-null arrays for reuse (H0: greedy == exact, verified).
    # ===================================================================
    print("\n--- STAGE A: convention gate (greedy reproduces committed) ---", flush=True)
    gate = {
        "recorded_before_apr8": True,
        "convention": "greedy-fallback (POT absent)",
        "tolerance_rtol": 0.02,
        "cells": {},
        "passed": True,
    }
    greedy_orphan = {}
    for dim in (0, 1):
        g_on = np.array([greedy_fallback(orphan_h[dim], null[dim][i]) for i in range(B)])
        g_nn = np.array([greedy_fallback(null[dim][i], null[dim][j]) for (i, j) in nn_pairs])
        greedy_orphan[dim] = {"obs_null": g_on, "null_null": g_nn}
        gcell = derive_cell(g_on, g_nn, dim)
        c = COMMITTED[f"h{dim}"]
        checks = {
            "mean_obs_null": (
                gcell["mean_obs_null"],
                c["mean_obs_null"],
                _match(gcell["mean_obs_null"], c["mean_obs_null"], 0.01),
            ),
            "mean_null_null": (
                gcell["mean_null_null"],
                c["mean_null_null"],
                _match(gcell["mean_null_null"], c["mean_null_null"], 0.01),
            ),
            "d_perm": (gcell["d_perm"], c["d_perm"], _match(gcell["d_perm"], c["d_perm"], 0.02)),
            "t_ratio": (gcell["t_ratio"], c["t_ratio"], _match(gcell["t_ratio"], c["t_ratio"], 0.02)),
        }
        ok = all(v[2] for v in checks.values())
        gate["passed"] = gate["passed"] and ok
        gate["cells"][f"h{dim}"] = {
            "greedy": gcell,
            "committed": c,
            "checks": {k: {"greedy": v[0], "committed": v[1], "match": v[2]} for k, v in checks.items()},
            "cell_passed": ok,
        }
        print(
            f"  H{dim} greedy: obs-null={gcell['mean_obs_null']:.4f} (committed {c['mean_obs_null']:.4f}) "
            f"null-null={gcell['mean_null_null']:.4f} (committed {c['mean_null_null']:.4f}) "
            f"d_perm={gcell['d_perm']:.3f} (committed {c['d_perm']:.3f}) -> {'PASS' if ok else 'FAIL'}",
            flush=True,
        )
    print(f"  GATE {'PASSED' if gate['passed'] else 'FAILED'}: committed convention = greedy-fallback", flush=True)
    if not gate["passed"]:
        print("STOP: greedy did not reproduce committed; committed convention unpinned. Escalate.", flush=True)
        _write(
            None,
            gate,
            solver,
            apr8_comp,
            None,
            None,
            canonical_sha,
            orphan_sha,
            cache_sha,
            headline_sha,
            apr8_recon,
            round(time.time() - t_start, 1),
            stopped="gate_failed",
        )
        return

    # Greedy apr8 obs-null (H0 fast; H0 greedy == exact -> used for the H0 headline).
    greedy_apr8 = {dim: np.array([greedy_fallback(apr8_h[dim], null[dim][i]) for i in range(B)]) for dim in (0, 1)}

    # ===================================================================
    # STAGE B0 — H0 exact==greedy VERIFICATION (fail-fast, before the long H1)
    #   Provable: H0 births are all 0 -> monotone rank matching is optimal 1D
    #   transport. Verified per-pair here so the H0 headline can use the (free)
    #   greedy values instead of 2000 EMD pairs.
    # ===================================================================
    print("\n--- STAGE B0: H0 exact==greedy verification sample ---", flush=True)
    n_ver = 60
    ver_on = compute_block("verify_h0_obs_null", [(i, orphan_h[0], null[0][i]) for i in range(n_ver)], N_WORKERS)
    ver_nn = compute_block(
        "verify_h0_null_null", [(k, null[0][nn_pairs[k][0]], null[0][nn_pairs[k][1]]) for k in range(n_ver)], N_WORKERS
    )
    h0_ver = {
        "n_pairs": n_ver,
        "obs_null_max_abs_diff": float(np.max(np.abs(ver_on - greedy_orphan[0]["obs_null"][:n_ver]))),
        "null_null_max_abs_diff": float(np.max(np.abs(ver_nn - greedy_orphan[0]["null_null"][:n_ver]))),
    }
    h0_ver["exact_equals_greedy"] = bool(
        h0_ver["obs_null_max_abs_diff"] < 1e-6 and h0_ver["null_null_max_abs_diff"] < 1e-6
    )
    print(
        f"  H0 max|exact-greedy| obs-null={h0_ver['obs_null_max_abs_diff']:.2e} "
        f"null-null={h0_ver['null_null_max_abs_diff']:.2e} -> "
        f"{'exact==greedy CONFIRMED' if h0_ver['exact_equals_greedy'] else 'MISMATCH'}",
        flush=True,
    )
    if not h0_ver["exact_equals_greedy"]:
        print("STOP: H0 exact != greedy; cannot substitute. Escalate.", flush=True)
        _write(
            None,
            gate,
            solver,
            apr8_comp,
            None,
            None,
            canonical_sha,
            orphan_sha,
            cache_sha,
            headline_sha,
            apr8_recon,
            round(time.time() - t_start, 1),
            stopped="h0_verify_failed",
            h0_ver=h0_ver,
        )
        return

    # ===================================================================
    # STAGE B — EXACT EMD battery: H1 only (H0 == verified greedy)
    # ===================================================================
    print("\n--- STAGE B: exact-W2 EMD battery (H1; ~3000 pairs) ---", flush=True)
    ex_orphan_h1 = compute_block("orphan_h1", [(i, orphan_h[1], null[1][i]) for i in range(B)], N_WORKERS)
    ex_apr8_h1 = compute_block("apr8_h1", [(i, apr8_h[1], null[1][i]) for i in range(B)], N_WORKERS)
    ex_nn_h1 = compute_block(
        "nullnull_h1", [(k, null[1][i], null[1][j]) for k, (i, j) in enumerate(nn_pairs)], N_WORKERS
    )

    # ===================================================================
    # STAGE C — stat derivation: H1 exact EMD; H0 greedy (== exact, verified)
    # ===================================================================
    print("\n--- STAGE C: stat derivation ---", flush=True)
    exact_cells = {
        "orphan": {
            "h0": derive_cell(greedy_orphan[0]["obs_null"], greedy_orphan[0]["null_null"], 0),
            "h1": derive_cell(ex_orphan_h1, ex_nn_h1, 1),
        },
        "apr8": {
            "h0": derive_cell(greedy_apr8[0], greedy_orphan[0]["null_null"], 0),
            "h1": derive_cell(ex_apr8_h1, ex_nn_h1, 1),
        },
    }
    for vint in ("orphan", "apr8"):
        for dim in ("h0", "h1"):
            cell = exact_cells[vint][dim]
            src = "EMD" if dim == "h1" else "greedy==exact"
            print(
                f"  {vint} {dim.upper()} ({src}): obs-null={cell['mean_obs_null']:.4f} "
                f"null-null={cell['mean_null_null']:.4f} d_perm={cell['d_perm']:.3f} "
                f"t_ratio={cell['t_ratio']:.3f} p={cell['w2_pvalue']:.6f}",
                flush=True,
            )

    # ===================================================================
    # STAGE D — triangle-inequality assertion (exact obs-obs anchors)
    # ===================================================================
    print("\n--- STAGE D: triangle-inequality assertion ---", flush=True)
    obs_obs = {}
    for dim in (0, 1):
        _, obs_obs[dim] = _w2_exact_pair((0, orphan_h[dim], apr8_h[dim]))
    triangle = {"obs_obs_w2": {f"h{dim}": obs_obs[dim] for dim in (0, 1)}, "checks": {}, "passed": True}
    for dim in (0, 1):
        delta = abs(exact_cells["apr8"][f"h{dim}"]["mean_obs_null"] - exact_cells["orphan"][f"h{dim}"]["mean_obs_null"])
        bound = obs_obs[dim]
        ok = delta <= bound + 1e-9
        triangle["passed"] = triangle["passed"] and ok
        triangle["checks"][f"h{dim}"] = {"delta_mean_obs_null": delta, "w2_obs_obs_bound": bound, "within_bound": ok}
        print(
            f"  H{dim}: |mean_apr8 - mean_orphan| = {delta:.4f}  <=  W2(obs_orphan,obs_apr8) = {bound:.4f}  "
            f"-> {'OK' if ok else 'VIOLATION'}",
            flush=True,
        )

    per_pair = {
        "orphan": {0: greedy_orphan[0]["obs_null"], 1: ex_orphan_h1},
        "apr8": {0: greedy_apr8[0], 1: ex_apr8_h1},
        "null_null": {0: greedy_orphan[0]["null_null"], 1: ex_nn_h1},
    }
    if not triangle["passed"]:
        print("STOP: triangle-inequality VIOLATION on final numbers. Not publishing.", flush=True)
        _write(
            exact_cells,
            gate,
            solver,
            apr8_comp,
            triangle,
            per_pair,
            canonical_sha,
            orphan_sha,
            cache_sha,
            headline_sha,
            apr8_recon,
            round(time.time() - t_start, 1),
            stopped="triangle_violation",
            h0_ver=h0_ver,
        )
        return

    _write(
        exact_cells,
        gate,
        solver,
        apr8_comp,
        triangle,
        per_pair,
        canonical_sha,
        orphan_sha,
        cache_sha,
        headline_sha,
        apr8_recon,
        round(time.time() - t_start, 1),
        h0_ver=h0_ver,
    )
    print(f"\nDONE in {(time.time() - t_start) / 60:.1f} min", flush=True)


def _write(
    exact_cells,
    gate,
    solver,
    apr8_comp,
    triangle,
    per_pair,
    canonical_sha,
    orphan_sha,
    cache_sha,
    headline_sha,
    apr8_recon,
    wall_s,
    stopped=None,
    h0_ver=None,
):
    out = {
        "schema": "headline_vintage_materiality_corrected/v1",
        "generated": date.today().isoformat(),
        "audit_task": "WT-1c",
        "seed": SEED,
        "wall_s": wall_s,
        "stopped": stopped,
        "solver": solver,
        "exact_headline_method": {
            "h1": "exact EMD (gudhi.wasserstein, POT), full 1000 obs-null per vintage + 1000 null-null",
            "h0": "greedy == exact (H0 births all 0 -> monotone rank matching is optimal 1D "
            "transport); verified per-pair against EMD on a 60-pair sample (see "
            "h0_exact_equals_greedy_verification); greedy H0 also reproduces committed 64.28 "
            "bit-for-bit in the convention gate, so the greedy H0 values ARE the exact H0.",
        },
        "h0_exact_equals_greedy_verification": h0_ver,
        "defect_diagnosis": {
            "summary": "The committed frozen USoc H1 headline W2 (obs-null 233.68, null-null "
            "175.40, d_perm +22.09) is a GREEDY-FALLBACK artifact of "
            "vectorisation.wasserstein_distance run with POT absent (2026-05-28), "
            "NOT exact Wasserstein-2. Exact EMD gives H1 obs-null ~12.4, null-null "
            "~3.6. For H0 the greedy match is optimal (births all 0) so greedy==exact, "
            "which is why H0 reproduced across the fresh vs committed seam and H1 did not.",
            "mechanism": "vectorisation.wasserstein_distance tries `from gudhi.wasserstein import "
            "wasserstein_distance`; on ImportError (POT not installed) it falls to a "
            "greedy persistence-rank matching (lines 236-254) that ignores birth "
            "location -> for H1 (births scattered 2.7-15) badly suboptimal, ~18x "
            "inflated. _single_permutation obs-null uses this wrapper (compute_wasserstein).",
            "why_2026_07_12_crosscheck_missed_it": "The 2026-07-12 sanity check compared "
            "committed_orphan_stats (values COPIED from the committed JSON) against the "
            "committed JSON — trivially true — instead of re-deriving orphan obs-null "
            "through the fresh code path. It also assumed the committed 233.68 was exact "
            "and flagged the fresh exact 12.71 as the defect; the reverse is true.",
            "max_possible_exact_w2_h1": "~35.8 (sqrt(diag(obs)^2+diag(null)^2)); 233.68 is "
            "mathematically impossible as an exact W2 on these diagrams.",
        },
        "inputs": {
            "canonical_sequences": {"path": str(al.CANONICAL_SEQUENCES), "sha256": canonical_sha},
            "orphan_sequences": {"path": str(al.ORPHAN_SEQUENCES), "sha256": orphan_sha, "status": ORPHAN_SEQ_STATUS},
            "usoc_frozen_cache": {"path": str(al.USOC_FROZEN_CACHE), "sha256": cache_sha},
            "committed_headline": {"path": str(al.USOC_FROZEN_HEADLINE), "sha256": headline_sha},
        },
        "apr8_obs_reconstruction": {
            "seq_sha256": apr8_recon.seq_sha256,
            "n_trajectories": apr8_recon.n_trajectories,
            "h0_card": apr8_recon.h0_card,
            "h1_card": apr8_recon.h1_card,
            **al.convert_numpy(apr8_comp),
        },
        "convention_gate_greedy_reproduces_committed": gate,
        "committed_frozen_headline": COMMITTED,
    }
    if exact_cells is not None:
        out["corrected_exact_headline"] = al.convert_numpy(exact_cells)
        # materiality comparison (exact, orphan vs apr8)
        comp = {}
        for dim in ("h0", "h1"):
            o = exact_cells["orphan"][dim]
            a = exact_cells["apr8"][dim]
            comp[dim] = {
                "mean_obs_null_orphan": o["mean_obs_null"],
                "mean_obs_null_apr8": a["mean_obs_null"],
                "d_perm_orphan": o["d_perm"],
                "d_perm_apr8": a["d_perm"],
                "d_perm_delta": a["d_perm"] - o["d_perm"],
                "p_orphan": o["w2_pvalue"],
                "p_apr8": a["w2_pvalue"],
                "decision_threshold_crossed": (o["w2_pvalue"] < 0.05) != (a["w2_pvalue"] < 0.05),
            }
        out["exact_vintage_materiality"] = comp
    if triangle is not None:
        out["triangle_inequality"] = al.convert_numpy(triangle)
    if per_pair is not None:
        out["per_pair_w2"] = {
            "orphan": {f"h{d}": per_pair["orphan"][d].tolist() for d in (0, 1)},
            "apr8": {f"h{d}": per_pair["apr8"][d].tolist() for d in (0, 1)},
            "null_null": {f"h{d}": per_pair["null_null"][d].tolist() for d in (0, 1)},
            "null_null_pair_indices_note": "pairs drawn via RandomState(42).choice(1000,2) x1000, "
            "same indices both dims (aggregate_combined-faithful)",
        }
    out_dir = WORKTREE / "results/trajectory_tda_integration/stage1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"headline_vintage_materiality_corrected_{date.today().isoformat()}.json"
    out_path.write_text(json.dumps(al.convert_numpy(out), indent=2), encoding="utf-8")
    print(f"Wrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
