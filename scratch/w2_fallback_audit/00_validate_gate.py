# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6)
# Purpose: Validation gate. Confirm audit_lib reproduces the WT-1c-established
#   reference (frozen USoc headline) before trusting it on other files:
#   greedy must reproduce committed H0 & H1 bit-for-bit (convention gate);
#   exact H1 obs-null must match WT-1c's 12.68; the diagonal-bound screen must
#   flag the committed 233.68 as impossible. Benchmarks exact EMD cost first so
#   the recompute budget is measured, not assumed.

from __future__ import annotations

import argparse
import sys
import time

import audit_lib as al
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

CACHE = al.CACHE_DIR / "null_diagrams_usoc_frozen_B1000_L5000_seed42_2026-05-28.npz"
HEADLINE = al.STAGE1_DIR / "usoc_headline_frozen_2026-05-28.json"
SEED = 42


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exact-bench", type=int, default=2, help="pairs to time per dim")
    ap.add_argument("--exact-sub", type=int, default=8, help="exact obs-null subsample per dim")
    args = ap.parse_args()

    print(f"cache sha256:    {al.sha256_file(CACHE)}", flush=True)
    print(f"headline sha256: {al.sha256_file(HEADLINE)}", flush=True)
    cache = al.load_cache(CACHE)
    committed = al.load_result_json(HEADLINE)["result"]

    b = len(cache["h1_diagrams"])
    print(f"B={b}; obs H0 card={len(cache['obs_h0_diagram'])}; obs H1 card={len(cache['obs_h1_diagram'])}", flush=True)
    pair_indices = al.reproduce_pair_indices(b, max(al.DEFAULT_N_NULL_PAIRS, b), SEED)
    print(f"n_pair_draws={len(pair_indices)}; first 3 pairs={pair_indices[:3]}", flush=True)

    dims = [(0, "obs_h0_diagram", "h0_diagrams"), (1, "obs_h1_diagram", "h1_diagrams")]

    # --- Phase 1: measure exact EMD cost per dim (budget, not assumption) -----
    for dim, obs_key, null_key in dims:
        obs, nulls = cache[obs_key], cache[null_key]
        t0 = time.time()
        for i in range(args.exact_bench):
            al.exact_w2(obs, nulls[i])
        per = (time.time() - t0) / args.exact_bench
        print(f"[bench] H{dim} exact EMD: {per:.2f}s/pair -> 2000 pairs = {2000 * per / 3600:.2f}h serial", flush=True)

    # --- Phase 2: greedy convention gate + diagonal screen --------------------
    for dim, obs_key, null_key in dims:
        c = committed[f"h{dim}"]
        obs, nulls = cache[obs_key], cache[null_key]

        t0 = time.time()
        g_obs = al.obs_null_distances(obs, nulls, "greedy")
        g_nn = al.null_null_distances(nulls, pair_indices, "greedy")
        g = al.headline_stats_from_distances(g_obs, g_nn)
        print(f"\n=== H{dim} greedy convention gate ({time.time() - t0:.0f}s) ===", flush=True)
        for field in ("mean_obs_null", "mean_null_null", "d_perm", "t_ratio", "w2_pvalue"):
            cv, gv = c[field], g[field]
            print(f"  {field:16s} committed={cv:.10f} greedy={gv:.10f} absdiff={abs(cv - gv):.3e}", flush=True)

        bounds = np.array([al.diagonal_bound(obs, nd) for nd in nulls])
        impossible = c["mean_obs_null"] > bounds.mean()
        print(
            f"  diagonal_bound   mean={bounds.mean():.4f} max={bounds.max():.4f} "
            f"committed_obs_null={c['mean_obs_null']:.4f} IMPOSSIBLE_AS_EXACT={impossible}",
            flush=True,
        )

        n_sub = args.exact_sub
        t1 = time.time()
        e_sub = al.obs_null_distances(obs, nulls[:n_sub], "exact")
        g_sub = g_obs[:n_sub]
        print(
            f"  exact obs-null (first {n_sub}): mean={e_sub.mean():.4f} "
            f"vs greedy {g_sub.mean():.4f} ({(time.time() - t1) / n_sub:.2f}s/pair)",
            flush=True,
        )
        print(
            f"  max|exact-greedy| over subsample = {np.abs(e_sub - g_sub).max():.3e} "
            f"(H0 expected ~0 => greedy==exact; H1 expected large)",
            flush=True,
        )


if __name__ == "__main__":
    main()
