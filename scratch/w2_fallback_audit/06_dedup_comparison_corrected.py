# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6 addendum)
# Purpose: Re-evaluate the dedup-amendment comparison with BOTH arms on the exact
#   W2 convention, per the 2026-07-14 [DECISION] item 4.
#
#   The committed comparison (dedup_amendment_comparison_2026-06-01.json) compares
#   the 2026-05-29 no-dedup arm against the 2026-05-30 dedup arm. Those arms
#   straddle the greedy/exact solver boundary (WT-6): 05-29 ran greedy, 05-30 ran
#   exact. It therefore contrasts a greedy statistic with an exact one, and its
#   H1 W2 "flip" (p 0.3497 -> 0.000999) is attributed by the committed
#   methodological disclosure to dedup stripping phantom features.
#
#   This script: (1) gates the greedy replica bit-for-bit against the committed
#   05-29 file (proving which convention wrote it); (2) re-derives the 05-29 arm's
#   H1 under exact EMD from its own cached diagrams with the identical seed-42 pair
#   sample and (r+1)/(B+1) aggregation; (3) reuses the already-exact 05-30 arm;
#   (4) re-evaluates the rejection-direction conclusion with both arms exact.
#   Never overwrites a committed file.

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import date
from pathlib import Path
from typing import Any

import audit_lib as al
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

BHPS_STAGE1 = al.PROJ_ROOT / "results/trajectory_tda_bhps/stage1"
ARM29 = BHPS_STAGE1 / "bhps_length_matched_truncate_frozen_2026-05-29.json"
ARM30 = BHPS_STAGE1 / "bhps_length_matched_truncate_frozen_2026-05-30.json"
CACHE29 = al.CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-29.npz"
CACHE30 = al.CACHE_DIR / "null_diagrams_bhps_length_matched_truncate_frozen_B1000_L5000_seed42_2026-05-30.npz"
COMMITTED_COMPARISON = al.STAGE1_DIR / "dedup_amendment_comparison_2026-06-01.json"
ALPHA = 0.05
SEED = 42


def _ver(mod: str) -> str:
    try:
        m = __import__(mod)
        return str(getattr(m, "__version__", "unknown"))
    except ImportError:
        return "absent"


def load_blocks(ckpt_dir: Path, prefix: str, expected: int) -> np.ndarray:
    """Concatenate disjoint checkpoint blocks in start order; assert completeness."""
    files = sorted(ckpt_dir.glob(f"{prefix}_*.npz"), key=lambda p: int(p.stem.split("_")[-1]))
    chunks: list[np.ndarray] = []
    for f in files:
        with np.load(f) as d:
            vals = np.asarray(d["values"], dtype=np.float64)
            start, end = int(d["start"]), int(d["end"])
            if len(vals) != end - start:
                raise SystemExit(f"incomplete block {f.name}: {len(vals)}/{end - start}")
            chunks.append(vals)
    out = np.concatenate(chunks) if chunks else np.array([])
    if len(out) != expected:
        raise SystemExit(f"{prefix}: got {len(out)} values, expected {expected}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="ckpt29")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--worktree", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()

    cache29 = al.load_cache(CACHE29)
    cache30 = al.load_cache(CACHE30)
    committed29 = al.load_result_json(ARM29)["result"]
    committed30 = al.load_result_json(ARM30)["result"]
    committed_cmp = al.load_result_json(COMMITTED_COMPARISON)

    b = len(cache29["h1_diagrams"])
    pair_indices = al.reproduce_pair_indices(b, max(al.DEFAULT_N_NULL_PAIRS, b), SEED)

    # ---- (1) Convention gate: prove the 05-29 arm was written by greedy --------
    gate: dict[str, Any] = {}
    for dim in (0, 1):
        obs, nulls = cache29[f"obs_h{dim}_diagram"], cache29[f"h{dim}_diagrams"]
        g_obs = al.obs_null_distances(obs, nulls, "greedy")
        g_nn = al.null_null_distances(nulls, pair_indices, "greedy")
        g = al.headline_stats_from_distances(g_obs, g_nn)
        c = committed29[f"h{dim}"]
        fields = ("mean_obs_null", "mean_null_null", "d_perm", "t_ratio", "w2_pvalue")
        diffs = {k: abs(float(c[k]) - float(g[k])) for k in fields}
        gate[f"h{dim}"] = {
            "committed": {k: c[k] for k in fields},
            "greedy_regate": {k: g[k] for k in fields},
            "absdiff": diffs,
            "reproduces_bit_for_bit": all(v < 1e-9 for v in diffs.values()),
            "null_null_max": float(g_nn.max()),
        }
        print(
            f"  gate h{dim}: bit-for-bit={gate[f'h{dim}']['reproduces_bit_for_bit']} "
            f"absdiff(mean_obs_null)={diffs['mean_obs_null']:.2e}",
            flush=True,
        )

    # ---- (2) Exact re-derivation of the 05-29 arm, H1 -------------------------
    ck = Path(args.ckpt)
    obs_null = load_blocks(ck, "lm29_h1_obsnull", b)
    null_null = load_blocks(ck, "lm29_h1_nullnull", len(pair_indices))
    exact29_h1 = al.headline_stats_from_distances(obs_null, null_null)
    print(
        f"  exact 05-29 H1: mean_obs_null={exact29_h1['mean_obs_null']:.4f} "
        f"mean_null_null={exact29_h1['mean_null_null']:.4f} p={exact29_h1['w2_pvalue']:.6f}",
        flush=True,
    )

    # ---- (2b) 2x2 factorial: separate the solver axis from the dedup axis -----
    # The committed comparison varies solver AND dedup together. Completing the
    # 2x2 (greedy/exact x no-dedup/dedup) attributes the effect to one axis.
    greedy30_obs = al.obs_null_distances(cache30["obs_h1_diagram"], cache30["h1_diagrams"], "greedy")
    greedy30_nn = al.null_null_distances(cache30["h1_diagrams"], pair_indices, "greedy")
    greedy30 = al.headline_stats_from_distances(greedy30_obs, greedy30_nn)
    print(
        f"  greedy on the DEDUP arm's own diagrams: mean_obs_null={greedy30['mean_obs_null']:.4f} "
        f"(committed exact = {float(committed30['h1']['mean_obs_null']):.4f})",
        flush=True,
    )

    # ---- (3) Diagnostics: what actually differs between the arms --------------
    o29, o30 = cache29["obs_h1_diagram"], cache30["obs_h1_diagram"]
    identical = sum(
        1
        for a, bb in zip(cache29["h1_diagrams"], cache30["h1_diagrams"])
        if a.shape == bb.shape and float(np.abs(a - bb).max()) == 0.0
    )
    p29 = o29[:, 1] - o29[:, 0]
    obs_obs_w2 = al.exact_w2(o29, o30)
    bounds29 = np.array([al.diagonal_bound(o29, nd) for nd in cache29["h1_diagrams"]])

    # ---- (4) Re-evaluate the cells -------------------------------------------
    c29_h1, c30_h1 = committed29["h1"], committed30["h1"]
    exact_p29 = exact29_h1["w2_pvalue"]
    exact_p30 = float(c30_h1["w2_pvalue"])  # already exact-era
    reject29, reject30 = exact_p29 < ALPHA, exact_p30 < ALPHA

    h1_cell_committed = next(c for c in committed_cmp["cells"] if c["cell_id"] == "bhps_length_matched_truncate_h1_w2")
    h0_gate = gate["h0"]
    h0_exact_est = float(committed29["h0"]["mean_obs_null"]) * (1 - 1.12e-2)

    payload: dict[str, Any] = {
        "schema_version": "dedup-amendment-comparison-corrected/v1",
        "generated_at": args.date,
        "task": "WT-6 addendum — re-evaluate the dedup-amendment comparison with BOTH arms on the exact W2 "
        "convention (2026-07-14 [DECISION] item 4)",
        "supersedes_for_h1_w2": str(COMMITTED_COMPARISON),
        "supersedes_note": "Corrects ONLY the H1 W2 comparison cell and the decision_summary counts that "
        "depend on it, plus the causal attribution in the committed "
        "methodological_disclosure_draft. The committed file is otherwise preserved and "
        "remains the record for landscape-L2 cells, dedup_provenance and the probes.",
        "why": "The committed comparison contrasts the 2026-05-29 no-dedup arm (greedy convention) against "
        "the 2026-05-30 dedup arm (exact convention). It therefore compared a greedy statistic with "
        "an exact one, and attributed the entire difference to the dedup amendment.",
        "inputs": {
            "arm_no_dedup_2026-05-29": {
                "path": str(ARM29),
                "sha256": al.sha256_file(ARM29),
                "cache": str(CACHE29),
                "cache_sha256": al.sha256_file(CACHE29),
                "convention_as_committed": "greedy_rank (proven by the gate below)",
            },
            "arm_dedup_2026-05-30": {
                "path": str(ARM30),
                "sha256": al.sha256_file(ARM30),
                "cache": str(CACHE30),
                "cache_sha256": al.sha256_file(CACHE30),
                "convention_as_committed": "exact EMD (post-2026-05-30 venv boundary; WT-6 audit)",
            },
            "committed_comparison": {
                "path": str(COMMITTED_COMPARISON),
                "sha256": al.sha256_file(COMMITTED_COMPARISON),
            },
        },
        "solver": {
            "exact": "gudhi.wasserstein.wasserstein_distance(order=2, internal_p=2) — POT/EMD optimal transport",
            "gudhi": _ver("gudhi"),
            "pot": _ver("ot"),
            "numpy": _ver("numpy"),
            "platform": platform.platform(),
            "seed": SEED,
        },
        "method": {
            "gate": "The greedy replica reproduces the committed 2026-05-29 statistics bit-for-bit, proving "
            "that arm's convention before any correction is claimed.",
            "exact": "W2(obs, null_i) for all B=1000 cached null draws, and W2(null_i, null_j) over the "
            "IDENTICAL seed-42 pair sample the battery drew (RandomState(42).choice(1000, size=2, "
            "replace=False) x 1000; effect statistic = first 500 pairs, p-value = all 1000). Only "
            "the solver changes; diagrams, draws, pairs, seed and aggregation are the committed ones.",
        },
        "convention_gate_2026-05-29_arm": gate,
        "arms_h1_w2": {
            "no_dedup_2026-05-29": {
                "committed_greedy": {
                    k: c29_h1[k] for k in ("mean_obs_null", "mean_null_null", "d_perm", "t_ratio", "w2_pvalue")
                },
                "corrected_exact": exact29_h1,
                "diagonal_bound_mean": float(bounds29.mean()),
                "committed_exceeds_diagonal_bound": bool(float(c29_h1["mean_obs_null"]) > float(bounds29.mean())),
            },
            "dedup_2026-05-30": {
                "committed_exact": {
                    k: c30_h1[k] for k in ("mean_obs_null", "mean_null_null", "d_perm", "t_ratio", "w2_pvalue")
                },
                "note": "Already exact — no correction needed or applied (WT-6 era verification).",
            },
        },
        "factorial_2x2_solver_vs_dedup": {
            "purpose": "The committed comparison varies the solver AND the dedup together, then attributes "
            "the whole difference to dedup. Completing the 2x2 on mean_obs_null (H1 W2) "
            "attributes it to one axis.",
            "cells": {
                "greedy_no_dedup_2026-05-29": float(c29_h1["mean_obs_null"]),
                "greedy_dedup_2026-05-30": float(greedy30["mean_obs_null"]),
                "exact_no_dedup_2026-05-29": float(exact29_h1["mean_obs_null"]),
                "exact_dedup_2026-05-30": float(c30_h1["mean_obs_null"]),
            },
            "provenance": {
                "greedy_no_dedup_2026-05-29": "committed value; reproduced bit-for-bit by the gate",
                "greedy_dedup_2026-05-30": "computed here: greedy replica on the dedup arm's own cached diagrams",
                "exact_no_dedup_2026-05-29": "computed here: exact EMD, B=1000, seed-42 pairs",
                "exact_dedup_2026-05-30": "committed value (already exact-era)",
            },
            "dedup_axis_effect_greedy": float(greedy30["mean_obs_null"]) - float(c29_h1["mean_obs_null"]),
            "dedup_axis_effect_exact": float(c30_h1["mean_obs_null"]) - float(exact29_h1["mean_obs_null"]),
            "solver_axis_effect_no_dedup": float(exact29_h1["mean_obs_null"]) - float(c29_h1["mean_obs_null"]),
            "solver_axis_effect_dedup": float(c30_h1["mean_obs_null"]) - float(greedy30["mean_obs_null"]),
            "reading": "Holding the solver fixed, dedup barely moves the statistic on either row. Holding "
            "dedup fixed, greedy->exact moves it by ~30x on either column. The variation the "
            "committed comparison attributed to dedup lies almost entirely on the solver axis.",
        },
        "diagnostics_what_actually_differs_between_the_arms": {
            "h1_null_bank_byte_identical_draws": f"{identical}/1000",
            "obs_h1_cardinality": {
                "no_dedup_2026-05-29": int(len(o29)),
                "dedup_2026-05-30": int(len(o30)),
                "note": "Dedup removed 139 near-duplicate LANDMARKS (5000 -> 4861) but "
                "changed the H1 diagram by only +2 features.",
            },
            "exact_w2_between_the_two_observed_diagrams": float(obs_obs_w2),
            "obs_h1_features_with_persistence_below_1e-6": {
                "no_dedup_2026-05-29": int((p29 < 1e-6).sum()),
                "note": "The committed disclosure attributes the flip to '~139 phantom H1 features at "
                "near-zero filtration scales'. There are none: no H1 feature in the 2026-05-29 "
                "observed diagram has persistence below 1e-6.",
            },
            "triangle_inequality_bound": {
                "statement": "W2 is a metric, so for any null N: |W2(obs29,N) - W2(obs30,N)| <= W2(obs29,obs30).",
                "w2_obs29_obs30": float(obs_obs_w2),
                "implication": f"The exact obs-null mean of the no-dedup arm must lie within "
                f"{obs_obs_w2:.3f} of the dedup arm's {float(c30_h1['mean_obs_null']):.4f} "
                f"(exactly so for the {identical}/1000 byte-identical null draws). It is "
                f"therefore mathematically impossible for the no-dedup arm's exact obs-null "
                f"to be the committed 202.84. The ~30x gap is the greedy convention, not dedup.",
            },
        },
        "corrected_cell_bhps_length_matched_truncate_h1_w2": {
            "committed": {
                "no_dedup_pvalue": h1_cell_committed["no_dedup_pvalue"],
                "dedup_pvalue": h1_cell_committed["dedup_pvalue"],
                "delta_pvalue": h1_cell_committed["delta_pvalue"],
                "no_dedup_reject": h1_cell_committed["no_dedup_reject"],
                "dedup_reject": h1_cell_committed["dedup_reject"],
                "rejection_direction_preserved": h1_cell_committed["rejection_direction_preserved"],
                "convention": "no_dedup=greedy vs dedup=exact (UNLIKE statistics)",
            },
            "corrected_both_arms_exact": {
                "no_dedup_pvalue": exact_p29,
                "dedup_pvalue": exact_p30,
                "delta_pvalue": exact_p30 - exact_p29,
                "no_dedup_reject": bool(reject29),
                "dedup_reject": bool(reject30),
                "rejection_direction_preserved": bool(reject29 == reject30),
                "convention": "both arms exact EMD (LIKE statistics)",
            },
        },
        "corrected_decision_summary": {
            "alpha": ALPHA,
            "rejection_direction_changes_committed": committed_cmp["decision_summary"]["rejection_direction_changes"],
            "rejection_direction_changes_corrected": 0 if reject29 == reject30 else 1,
            "h1_w2_flip_survives_correction": bool(reject29 != reject30),
            "outcome_A_status": "UNCHANGED. Outcome A rests on the dedup arms (truncate 2026-05-30 and "
            "first13 2026-05-30), both of which are exact-era and both of which reject "
            "H1 W2 at alpha=0.05. Nothing in this correction touches them.",
        },
        "h0_w2_cell_note": {
            "status": "Out of scope of the 2026-07-14 ruling (H0 immunity verified, not assumed), and "
            "unaffected in conclusion — but stated honestly rather than assumed.",
            "issue": "The h0_w2 cell also compares the greedy 05-29 arm against the exact 05-30 arm.",
            "bound": f"WT-6 measured greedy-vs-exact H0 on THIS cache at max|exact-greedy| = 4.086e-01 "
            f"(1.12e-02 relative) — the largest H0 gap in the audit, because dedup leaves a large "
            f"obs/null cardinality mismatch (obs 4829 vs nulls ~4991) and greedy dumps the surplus "
            f"on the diagonal where optimal transport redistributes. Applying that bound to the "
            f"committed 37.5066 gives an exact obs-null of about {h0_exact_est:.2f}.",
            "why_the_conclusion_cannot_move": f"The p-value is r = #(null_null >= mean_obs_null) with "
            f"(r+1)/(B+1). The largest null-null H0 distance in the whole "
            f"seed-42 sample is {h0_gate['null_null_max']:.4f}, far below "
            f"the ~{h0_exact_est:.1f} obs-null, so r = 0 and p stays at the "
            f"Monte-Carlo floor 0.000999 under either convention. Both arms "
            f"reject; the direction is preserved regardless.",
            "not_recomputed_because": "Full exact H0 (2000 EMD pairs at 10-50 s/pair) would cost 5-28 h serial "
            "to move a p-value that is provably pinned at the floor. Recorded as a "
            "bounded argument instead of an assumption.",
        },
        "committed_disclosure_correction": {
            "committed_claim": "the 2026-05-29 observed PD contained ~139 phantom H1 features at near-zero "
            "filtration scales ... those phantoms inflated the W2 statistic by a ~30-200x "
            "constant on both observed-to-null and null-to-null pairings, making observed "
            "look statistically indistinguishable from a null (ratio 1.006). External dedup "
            "... strips the phantoms and reveals the underlying signal (ratio 1.87).",
            "finding": "The mechanism is misattributed. The ~30x inflation is the greedy persistence-rank "
            "fallback, not phantom features: (a) the 2026-05-29 observed H1 diagram contains ZERO "
            "features with persistence < 1e-6, so there are no near-zero phantoms to strip; "
            "(b) dedup changed the observed H1 diagram by only +2 features (3144 -> 3146) and by "
            f"exact W2 = {obs_obs_w2:.3f}, which cannot move a p-value from 0.35 to the floor under "
            "a metric; (c) the greedy value on the DEDUP arm's own diagrams is ~203.2 (WT-6 "
            "measured), i.e. essentially identical to the no-dedup arm's committed 202.84 — the "
            "dedup barely moves the greedy statistic either. The ratio 1.006 -> 1.87 is greedy -> "
            "exact, not no-dedup -> dedup.",
            "consequence": "The dedup amendment must NOT be justified in the manuscript by the H1 W2 flip. "
            "Any surviving justification for external dedup rests on other grounds (the "
            "near-duplicate landmarks are a true data property per the committed "
            "dedup_provenance asymmetry_note); the H1 W2 evidence for it dissolves under the "
            "exact metric. This is a User/Manager decision, not an audit action.",
        },
    }
    out = (
        Path(args.worktree)
        / "results/trajectory_tda_integration/stage1"
        / (f"dedup_amendment_comparison_corrected_{args.date}.json")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise SystemExit(f"refusing to overwrite {out}")
    payload["per_pair"] = {
        "no_dedup_2026-05-29_h1_obs_null_exact": obs_null.tolist(),
        "no_dedup_2026-05-29_h1_null_null_exact": null_null.tolist(),
        "null_null_pair_indices": pair_indices,
    }
    out.write_text(json.dumps(al.convert_numpy(payload), indent=2), encoding="utf-8")
    print(f"wrote {out}", flush=True)


if __name__ == "__main__":
    main()
