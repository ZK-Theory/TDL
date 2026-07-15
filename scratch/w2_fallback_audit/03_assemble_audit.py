# Research context: TDA-Research/00-Meta/Discovery/w2-fallback-audit-memo (WT-6)
# Purpose: Assemble the WT-6 deliverables from the classification pass and the
#   exact-W2 re-derivation blocks:
#     1. results/trajectory_tda_integration/stage1/w2_fallback_audit_<date>.json
#        — era boundary, full audit table (file x dim x convention x screen),
#          corrected-or-deferred status.
#     2. results/trajectory_tda_bhps/stage1/bhps_headline_frozen_corrected_<date>.json
#        — the corrected exact BHPS frozen headline with per-pair arrays.
#   Never overwrites a committed result file; corrected values get a new
#   date-suffixed filename.

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
BHPS_FROZEN_CACHE = al.CACHE_DIR / "null_diagrams_bhps_frozen_B1000_L5000_seed42_2026-05-28.npz"
BHPS_FROZEN_HEADLINE = BHPS_STAGE1 / "bhps_headline_frozen_2026-05-28.json"

ERA_BOUNDARY = {
    "question": "When did POT (`ot`) actually enter the venv, making gudhi.wasserstein (exact EMD) "
    "importable and the greedy fallback unreachable?",
    "headline": "The venv boundary is 2026-05-29/2026-05-30 — NOT the 2026-06-16 pyproject core-pin. "
    "Established empirically from the stored diagrams, not from git.",
    "git_evidence_only_bounds_the_question": {
        "pot_declared_optional": {
            "commit": "e08917c",
            "date": "2026-03-23",
            "subject": "chore: relax python constraint to <3.14, add mapper and wasserstein optional deps",
            "evidence": 'pyproject.toml gained `wasserstein = ["pot>=0.9.0"]` under '
            "[project.optional-dependencies]. Optional extras are NOT installed by a default "
            "`uv sync`/`uv run` — but they CAN be installed by hand or via --extra at any time, "
            "which is exactly what appears to have happened.",
        },
        "pot_promoted_to_core": {
            "commit": "ec291c0",
            "date": "2026-06-16",
            "subject": "[PIPELINE] P01-A: harden auxiliary diagnostics W2 runner",
            "evidence": "pyproject.toml `dependencies` gained `pot==0.9.6.post1` (+ uv.lock). This is when "
            "POT became GUARANTEED and REPRODUCIBLE for any `uv run` — not when it first "
            "appeared in the venv.",
        },
        "why_git_is_not_the_answer": "The venv is not git-tracked. A pyproject pin proves when POT became "
        "guaranteed; it cannot prove POT was absent before then. Dating the "
        "era from the pin alone would have MISCLASSIFIED four exact-era files "
        "(2026-05-30/31) as artifacts.",
    },
    "empirical_boundary_natural_experiment": {
        "finding": "The dedup amendment re-ran the SAME analysis on consecutive days, and the two runs used "
        "DIFFERENT solvers — pinning the venv boundary to a single day.",
        "greedy_side": {
            "file": "results/trajectory_tda_bhps/stage1/bhps_length_matched_truncate_frozen_2026-05-29.json",
            "committed_h1_mean_obs_null": 202.8400026226595,
            "diagonal_bound_mean": 20.3715,
            "greedy_gate_absdiff": 0.0,
            "verdict": "GREEDY — the greedy replica reproduces the committed value bit-for-bit, and the "
            "committed value is ~10x above the maximum any exact W2 could take.",
        },
        "exact_side": {
            "file": "results/trajectory_tda_bhps/stage1/bhps_length_matched_truncate_frozen_2026-05-30.json",
            "committed_h1_mean_obs_null": 6.6314,
            "diagonal_bound_mean": 20.3798,
            "exact_subsample_12_pairs": 6.6695,
            "greedy_subsample_12_pairs": 203.2209,
            "verdict": "EXACT — the committed value matches the exact solver on the same cached diagrams "
            "and is nowhere near the greedy value; it also sits below the diagonal bound.",
        },
        "conclusion": "POT entered the venv between 2026-05-29 and 2026-05-30 — most plausibly a manual "
        "`uv pip install pot` / `uv sync --extra wasserstein` during the dedup-amendment work. "
        "The 2026-06-16 core-pin later made that state reproducible.",
    },
    "verdict": {
        "greedy_era": "on or before 2026-05-29 — H1 W2 values computed via "
        "vectorisation.wasserstein_distance are greedy artifacts",
        "exact_era": "on or after 2026-05-30 — verified exact",
        "fragile_window": "2026-05-30 to 2026-06-16: the environment was exact but NOT reproducibly so "
        "(POT present by hand, undeclared). Results in this window are correct but their "
        "provenance was not guaranteed by the lockfile — a latent reproducibility hole "
        "that the core-pin closed.",
        "method_note": "Era is used ONLY as a prior. Every cell with stored diagrams was decided by the "
        "convention gate (bit-for-bit) plus the diagonal-bound screen, which is precisely why "
        "the true boundary surfaced instead of the assumed one.",
    },
}


# Files classified WITHOUT compute, each on stated evidence rather than era alone.
# (The compute-classified files are in audit_table, produced by 02_classify_all.py.)
NON_COMPUTE_CLASSIFIED: list[dict[str, Any]] = [
    {
        "label": "T1.28 stratified W2 (stratified_w2_recompute_2026-07-09.json, "
        "stratified_w2_bh_per_family_2026-07-09.json, fdr/subgroup_checkpoints/*.json)",
        "path_glob": "results/panel_methodology/fdr/",
        "dims": "h0+h1",
        "classification": "IMMUNE (exact era)",
        "basis": "Routes through the defective path (run_t128_stratified_w2.py -> "
        "_battery_core.run_headline_from_embeddings -> _null_null_w2_worker -> "
        "vectorisation.wasserstein_distance), so immunity rests on the era. Verified NOT by date "
        "but by git ancestry: the run records git_head=8e175cd2f8d629be235317c4cfbceb848678bdf5 "
        "(2026-07-01), and `git merge-base --is-ancestor ec291c0 8e175cd` is TRUE — that checkout "
        "contained pot==0.9.6.post1 as a core dependency, so `uv run` synced POT and the exact "
        "solver was used. Subgroup checkpoints record completed_at 2026-06-29, also post-boundary.",
        "residual_risk": "The venv is not git-tracked; a hand-built environment that skipped `uv sync` could "
        "in principle still have lacked POT. Checkpoints store only t_ratio/w2_p (no "
        "mean_obs_null), so no magnitude screen is possible. Confidence: high, not proven.",
    },
    {
        "label": "landscape_sensitivity_usoc_2026-05-25.json, landscape_sensitivity_bhps_2026-05-25.json",
        "path_glob": "results/trajectory_tda_integration/stage1/",
        "dims": "h0+h1 (landscape-L2 only)",
        "classification": "IMMUNE (different code path)",
        "basis": "Two independent grounds. (1) Code: landscape L2 is computed by "
        "_battery_core.landscape_l2_distance — pure numpy sqrt(sum((L1-L2)^2)*dx) on landscape "
        "grids; it never calls a Wasserstein solver. (2) Content: these files contain only "
        "*_landscape_l2_pvalue fields; no W2 quantity is stored. This answers the brief's "
        "'verify whether the landscape path shares the fallback' — it does NOT.",
    },
    {
        "label": "lm_sensitivity_L2500_2026-05-24, lm_sensitivity_L8000_2026-05-25, "
        "lm_sensitivity_L2500_frozen_2026-05-28, lm_sensitivity_L8000_frozen_2026-05-28",
        "path_glob": "results/trajectory_tda_integration/stage1/",
        "dims": "h0 IMMUNE / h1 SUSPECT-UNVERIFIABLE",
        "classification": "h0: IMMUNE; h1: SUSPECT-UNVERIFIABLE",
        "basis": "Greedy era (all pre-2026-06-16) and they route through the defective path, but they ran "
        "at L=2500/L=8000 and NO null-diagram cache exists at those landmark counts (the cache "
        "directory holds only L5000 and the L500 smoke). With no stored diagrams there is nothing "
        "to run the convention gate or the diagonal screen against, and the brief forbids "
        "re-running batteries to regenerate nulls.",
        "magnitude_note": "The frozen L2500 H1 reports mean_obs_null=164.18 / mean_null_null=102.69. For "
        "scale, the L5000 frozen USoc H1 diagonal bound is ~35.9 and the exact value "
        "~12.7; an L2500 diagram has ~half the points, so its bound is smaller still. "
        "164.18 is therefore almost certainly a greedy artifact — but this is an "
        "inference from magnitude, NOT a verified screen, which is exactly why the cell "
        "is SUSPECT-UNVERIFIABLE rather than ARTIFACT-CONFIRMED.",
    },
    {
        "label": "stratified_markov1_battery_2026-05-13.json",
        "path_glob": "results/trajectory_tda_integration/stage1/",
        "dims": "h0 IMMUNE / h1 SUSPECT-UNVERIFIABLE",
        "classification": "h0: IMMUNE; h1: SUSPECT-UNVERIFIABLE",
        "basis": "Greedy era (2026-05-13, B=100, per-regime markov-1). Stores only per-test raw_pvalue and "
        "reject flags — no W2 means — and predates every null-diagram cache (earliest is "
        "2026-05-24). Nothing to gate or screen against.",
        "note": "Superseded for paper use by the T1.28 stratified recompute (2026-07-09), which is "
        "exact-era IMMUNE — so this cell's exposure is largely historical.",
    },
    {
        "label": "pvalue_denominator_cleanup_2026-05-28.json",
        "path_glob": "results/trajectory_tda_integration/stage1/",
        "dims": "per-cell",
        "classification": "INHERITS (W2 H1 cells ARTIFACT; W2 H0 and landscape cells IMMUNE)",
        "basis": "A denominator-cleanup recompute that re-derives p-values from the same greedy-era caches "
        "and carries the same W2 means (e.g. 247.51 usoc H1, 201.92 bhps H1, alongside H0 27.99 / "
        "34.31 and landscape means). It introduces no new W2 computation convention, so each cell "
        "inherits the status of its source headline cell.",
    },
    {
        "label": "frozen_vs_provisional_comparison_2026-05-29.json, "
        "dedup_amendment_comparison_2026-05-30/31/2026-06-01.json",
        "path_glob": "results/trajectory_tda_integration/stage1/",
        "dims": "per-cell (derived)",
        "classification": "DERIVED — INHERITS from sources",
        "basis": "These files store no W2 of their own; they copy p-values / reject flags out of the "
        "underlying headline and length-matched files and compare them. Every W2 H1 cell they "
        "quote inherits ARTIFACT status from its source; H0 and landscape cells are IMMUNE.",
        "conclusion_note": "Both comparisons report rejection_direction_changes = 0 / "
        "rejection_direction_preserved = true. Because BOTH sides of each comparison "
        "were computed under the SAME greedy convention, the comparison is internally "
        "consistent — but it compares two greedy statistics, so it does not license any "
        "claim about exact-W2 agreement between the arms.",
    },
    {
        "label": "headline_vintage_materiality_2026-07-12.json",
        "path_glob": "results/trajectory_tda_integration/stage1/",
        "dims": "h1",
        "classification": "SUPERSEDED",
        "basis": "The WT-1 (2026-07-12) result whose H1 conclusion was inverted because it compared a fresh "
        "exact value (12.71) against the committed greedy artifact (233.68) and labelled the exact "
        "value a degradation. Superseded by headline_vintage_materiality_corrected_2026-07-14.json "
        "(WT-1c). Retained as historical record; must not be cited.",
    },
    {
        "label": "usoc_headline_frozen_smoke_2026-05-28.json",
        "path_glob": "results/trajectory_tda_integration/stage1/",
        "dims": "h0+h1",
        "classification": "OUT-OF-SCOPE (smoke)",
        "basis": "B=10 / L=500 smoke artifact for pipeline wiring, not a research result. Greedy era, so "
        "its H1 W2 is an artifact on the same reasoning, but nothing cites it.",
    },
    {
        "label": "bhps_nonoverlap_reanalysis_2026-06-09.json",
        "path_glob": "results/panel_methodology/bhps_nonoverlap/",
        "dims": "h0 IMMUNE / h1 ARTIFACT-SUSPECTED",
        "classification": "h0: IMMUNE; h1: SUSPECT (cache present, gate deferred)",
        "basis": "Dated 2026-06-09, i.e. one week BEFORE the 2026-06-16 POT core-pin, so greedy era. Its "
        "null cache (null_diagrams_bhps_nonoverlap_frozen_B1000_L5000_seed42_2026-06-09.npz) IS "
        "present, so this cell is fully gate-able and re-derivable — it was budget-deferred, not "
        "unverifiable. Listed in deferred_work.",
    },
]


def load_blocks(pattern_prefix: str, expected_total: int) -> tuple[np.ndarray, bool]:
    """Concatenate disjoint checkpoint blocks in start order. Returns (values, complete)."""
    ckpt = Path("ckpt")
    files = sorted(ckpt.glob(f"{pattern_prefix}_*.npz"), key=lambda p: int(p.stem.split("_")[-1]))
    chunks: list[np.ndarray] = []
    for f in files:
        with np.load(f) as d:
            vals = np.asarray(d["values"], dtype=np.float64)
            start, end = int(d["start"]), int(d["end"])
            if len(vals) != end - start:
                print(f"  [partial] {f.name}: {len(vals)}/{end - start}", flush=True)
                return np.array([]), False
            chunks.append(vals)
    if not chunks:
        return np.array([]), False
    out = np.concatenate(chunks)
    return out, len(out) == expected_total


def build_corrected_bhps(today: str) -> dict[str, Any] | None:
    """Re-derive the BHPS frozen H1 headline under exact W2 from the cached diagrams."""
    obs_null, ok1 = load_blocks("bhps_frozen_h1_obsnull", 1000)
    null_null, ok2 = load_blocks("bhps_frozen_h1_nullnull", 1000)
    if not (ok1 and ok2):
        print(f"  BHPS frozen H1 blocks incomplete (obs_null={len(obs_null)}, null_null={len(null_null)})", flush=True)
        return None

    committed = al.load_result_json(BHPS_FROZEN_HEADLINE)
    c_h1 = committed["result"]["h1"]
    corrected = al.headline_stats_from_distances(obs_null, null_null)

    cache = al.load_cache(BHPS_FROZEN_CACHE)
    obs = cache["obs_h1_diagram"]
    bounds = np.array([al.diagonal_bound(obs, nd) for nd in cache["h1_diagrams"]])

    # H0 immunity spot check (greedy == exact) doubles as a pipeline sanity gate.
    g_obs_h0 = al.obs_null_distances(cache["obs_h0_diagram"], cache["h0_diagrams"], "greedy")
    pair_idx = al.reproduce_pair_indices(len(cache["h0_diagrams"]), 1000, 42)
    g_nn_h0 = al.null_null_distances(cache["h0_diagrams"], pair_idx, "greedy")
    g_h0 = al.headline_stats_from_distances(g_obs_h0, g_nn_h0)
    c_h0 = committed["result"]["h0"]
    h0_gate = {
        "committed_mean_obs_null": c_h0["mean_obs_null"],
        "greedy_regate_mean_obs_null": g_h0["mean_obs_null"],
        "absdiff": abs(c_h0["mean_obs_null"] - g_h0["mean_obs_null"]),
        "reproduces_bit_for_bit": abs(c_h0["mean_obs_null"] - g_h0["mean_obs_null"]) < 1e-9,
        "note": "H0 births are all 0 => greedy rank-matching is optimal 1-D transport, so the committed "
        "H0 is already exact. Reproducing it bit-for-bit confirms the pipeline replica is faithful.",
    }

    rejection_flips = (c_h1["w2_pvalue"] < 0.05) != (corrected["w2_pvalue"] < 0.05)
    return {
        "schema_version": "w2-exact-corrected-headline/v1",
        "generated_at": today,
        "task": "WT-6 — exact-W2 re-derivation of the frozen BHPS H1 headline",
        "supersedes_for_h1": str(BHPS_FROZEN_HEADLINE),
        "supersedes_note": "H1 W2 values only. H0 is unaffected (greedy == exact) and the committed H0 "
        "stands. Landscape-L2 values are unaffected (separate code path) and stand.",
        "inputs": {
            "cache": str(BHPS_FROZEN_CACHE),
            "cache_sha256": al.sha256_file(BHPS_FROZEN_CACHE),
            "committed_headline": str(BHPS_FROZEN_HEADLINE),
            "committed_headline_sha256": al.sha256_file(BHPS_FROZEN_HEADLINE),
        },
        "solver": {
            "exact": "gudhi.wasserstein.wasserstein_distance(order=2, internal_p=2) — POT/EMD optimal transport",
            "gudhi": _ver("gudhi"),
            "pot": _ver("ot"),
            "numpy": _ver("numpy"),
            "platform": platform.platform(),
        },
        "method": {
            "obs_null": "exact W2(obs, null_i) for all B=1000 cached null draws (same draws the battery used)",
            "null_null": "exact W2(null_i, null_j) over the IDENTICAL pair sample the battery drew "
            "(np.random.RandomState(42).choice(1000, size=2, replace=False) x 1000); "
            "effect statistic uses the first 500 pairs, p-value uses all 1000 — "
            "mirrors _battery_core.aggregate_combined exactly.",
            "isolation": "Only the solver changes (greedy -> exact). Diagrams, draws, pairs, seed and "
            "aggregation are identical to the committed run, so the delta is attributable "
            "solely to the convention.",
        },
        "h0_immunity_gate": h0_gate,
        "h1": {
            "committed_greedy": {
                k: c_h1.get(k) for k in ("mean_obs_null", "mean_null_null", "d_perm", "t_ratio", "w2_pvalue")
            },
            "corrected_exact": corrected,
            "diagonal_bound_mean": float(bounds.mean()),
            "diagonal_bound_max": float(bounds.max()),
            "committed_exceeds_diagonal_bound": bool(c_h1["mean_obs_null"] > float(bounds.mean())),
            "rejection_at_alpha_0.05": {
                "committed": bool(c_h1["w2_pvalue"] < 0.05),
                "corrected": bool(corrected["w2_pvalue"] < 0.05),
                "flips": bool(rejection_flips),
            },
            "per_pair": {
                "obs_null_exact": obs_null.tolist(),
                "null_null_exact": null_null.tolist(),
                "null_null_pair_indices": al.reproduce_pair_indices(1000, 1000, 42),
            },
        },
    }


def _ver(mod: str) -> str:
    try:
        m = __import__(mod)
        return str(getattr(m, "__version__", "unknown"))
    except ImportError:
        return "absent"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classification", default="classification_raw.json")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--worktree", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()

    wt = Path(args.worktree)
    classification = json.loads(Path(args.classification).read_text(encoding="utf-8"))

    corrected = build_corrected_bhps(args.date)
    if corrected is not None:
        out_corr = wt / "results/trajectory_tda_bhps/stage1" / f"bhps_headline_frozen_corrected_{args.date}.json"
        out_corr.parent.mkdir(parents=True, exist_ok=True)
        if out_corr.exists():
            raise SystemExit(f"refusing to overwrite {out_corr}")
        out_corr.write_text(json.dumps(al.convert_numpy(corrected), indent=2), encoding="utf-8")
        print(f"wrote {out_corr}", flush=True)

    audit = {
        "schema_version": "w2-fallback-audit/v1",
        "generated_at": args.date,
        "task": "WT-6 — systemic greedy-fallback W2 audit + fail-loud solver fix",
        "defect": {
            "summary": "trajectory_tda.topology.vectorisation.wasserstein_distance wrapped the gudhi "
            "(POT/EMD) import in try/except (ImportError, AttributeError) and silently fell "
            "through to greedy persistence-rank matching, which is NOT optimal transport.",
            "fix": "The except is narrowed to ImportError and the exact solver is asserted: the function "
            "now RAISES RuntimeError when POT is unavailable. The greedy path is reachable only "
            "via the explicit allow_greedy_fallback=True argument and logs a loud warning marking "
            "its output convention as 'greedy_rank'.",
            "h0_immunity": {
                "claim": "H0 is immune for every decision in this audit, but the equality is NOT absolute — "
                "a correction to the WT-1c generalisation.",
                "mechanism": "With all births = 0 the points lie on a line, so rank-matching is optimal "
                "transport FOR THE MATCHED PART. Greedy then dumps the surplus |n-m| points "
                "onto the diagonal, where optimal transport may redistribute. The discrepancy "
                "therefore scales with the cardinality mismatch between the two diagrams.",
                "measured_per_cache_6_pairs": {
                    "usoc_frozen_2026-05-28": {
                        "obs_card": 4999,
                        "null_cards": "~4999 (matched)",
                        "max_abs_exact_minus_greedy": 0.0,
                        "relative": 0.0,
                    },
                    "bhps_frozen_2026-05-28": {
                        "obs_card": 4970,
                        "null_cards": "~4988 (delta~18)",
                        "max_abs_exact_minus_greedy": 4.214e-3,
                        "relative": 9.80e-5,
                    },
                    "bhps_2026-05-24": {
                        "obs_card": 4970,
                        "null_cards": "~4978 (delta~8)",
                        "max_abs_exact_minus_greedy": 1.481e-2,
                        "relative": 4.30e-4,
                    },
                    "bhps_length_matched_truncate_frozen_2026-05-29": {
                        "obs_card": 4829,
                        "null_cards": "~4991 (delta~162)",
                        "max_abs_exact_minus_greedy": 4.086e-1,
                        "relative": 1.12e-2,
                    },
                },
                "decision_impact": "None. The largest shift is ~1.1% on a cell whose W2 p-value is already "
                "at the floor (0.000999) with d_perm ~26-51. No threshold is approached.",
                "wt1c_reconciliation": "WT-1c measured 7.1e-15 on USoc, where obs and null cardinalities "
                "coincide (4999 vs 4999) — the exactly-immune case. The 'H0 is "
                "immune because births are 0' generalisation carries an unstated "
                "equal-cardinality precondition.",
            },
            "screen": "Exact W2(A,B) <= sqrt(diag(A)^2 + diag(B)^2) (project every point to the diagonal). "
            "A committed value above that bound is mathematically impossible as an exact W2.",
        },
        "era_boundary": ERA_BOUNDARY,
        "solver_now": {
            "gudhi": _ver("gudhi"),
            "pot": _ver("ot"),
            "numpy": _ver("numpy"),
            "scipy": _ver("scipy"),
        },
        "classification_taxonomy": {
            "IMMUNE": "Not affected: H0 (greedy == exact), or exact-era, or not computed via the fallback path.",
            "ARTIFACT-CONFIRMED": "Greedy era, H1, AND the greedy replica reproduces the committed value "
            "bit-for-bit, AND (where checkable) the committed value exceeds the "
            "diagonal bound so it is impossible as an exact W2.",
            "SUSPECT-UNVERIFIABLE": "Greedy era, H1, but no cached diagrams exist to gate or screen against.",
            "DERIVED/INHERITS": "Stores no W2 of its own; each cell inherits its source cell's status.",
            "SUPERSEDED": "Retained as historical record; must not be cited.",
        },
        "enforcement_artifacts": {
            "convention_gate": "A cell is ARTIFACT-CONFIRMED only if the greedy replica reproduces the "
            "committed value bit-for-bit. Era is a prior, never a verdict, whenever "
            "diagrams exist. Validated against WT-1c: the replica reproduced the frozen "
            "USoc H0 and H1 headline statistics with absdiff = 0.0e+00 on all five "
            "fields (mean_obs_null, mean_null_null, d_perm, t_ratio, w2_pvalue).",
            "diagonal_bound_screen": "exact W2(A,B) <= sqrt(diag(A)^2 + diag(B)^2); needs no solver and is "
            "O(n). Frozen USoc H1: bound 35.90 vs committed 233.68 => impossible.",
            "h0_immunity_spot_check": "H0 must reproduce committed bit-for-bit and greedy must equal exact "
            "(measured 0.0 over an 8-pair subsample), doubling as a pipeline "
            "sanity gate on the replica itself.",
            "pot_hidden_raise_test": "tests/trajectory/test_wasserstein_fallback_guard.py — with POT hidden "
            "the default call RAISES; with POT present exact values are unchanged; "
            "greedy requires explicit opt-in and is ignored when POT is present.",
        },
        "audit_table": classification,
        "non_compute_classified": NON_COMPUTE_CLASSIFIED,
        "compute_budget": {
            "measured_exact_emd_cost": {
                "usoc_frozen_h1_6004pts": "12.46 s/pair (8-pair sample); 14.51 s/pair (2-pair sample)",
                "usoc_frozen_h0_4999pts": "10.67 s/pair (2-pair sample); 50.90 s/pair (8-pair sample)",
                "bhps_frozen_h1_3458x4831pts": "6.24 s/pair obs-null, 6.68 s/pair null-null (3-pair sample)",
                "note": "The WT-1c memo's '~5 s/pair on ~5000-pt diagrams' materially UNDERSTATES the cost: "
                "measured 6-15 s/pair, and EMD solve time varies ~5x across diagram pairs "
                "(H0 10.7 -> 50.9 s/pair between samples). Budget from a measurement on the actual "
                "cache, never from the memo figure.",
            },
            "parallelism": "Independent OS processes on disjoint checkpointed blocks (loky/threads scale "
            "negatively — exact EMD is memory-bandwidth-bound and each worker holds ~1.2 GB). "
            "Over-parallelising is actively harmful: 8 blocks + the classifier drove free RAM "
            "from 33 GB to 2.9 GB and stalled all workers. 4 blocks ran at 8.2-10.0 s/pair.",
        },
        "deferred_work": [
            {
                "item": "Exact re-derivation of bhps_headline_2026-05-24 H1 (provisional-loadings BHPS headline)",
                "cache": "null_diagrams_bhps_B1000_L5000_seed42_2026-05-24.npz (present)",
                "why_deferred": "Budget. ~2000 exact EMD pairs at ~6.5 s/pair = ~3.6 h serial. The frozen "
                "BHPS headline was prioritised because it is the citable counterpart of the "
                "frozen USoc headline and its H1 rejection is borderline (p=0.019).",
                "status": "re-derivable on demand; classification already ARTIFACT-CONFIRMED via the gate",
            },
            {
                "item": "Exact re-derivation of the BHPS length-matched / probe family H1 cells "
                "(truncate 2026-05-25/29/30, first13 2026-05-30, probe-pinned-thresh 2026-05-31, "
                "probe-symmetric-dedup 2026-05-30)",
                "cache": "all present under stage1/cache/",
                "why_deferred": "Budget (~3.6 h serial each). These feed the dedup-amendment comparisons, "
                "whose reported conclusion is 'rejection direction preserved' across arms — "
                "a within-greedy comparison that is internally consistent, so correcting it "
                "is lower priority than the citable headlines.",
                "status": "re-derivable on demand; classification established by the gate",
            },
            {
                "item": "Exact re-derivation of usoc_headline_2026-05-24 H1 (provisional USoc headline)",
                "cache": "null_diagrams_usoc_B1000_L5000_seed42_2026-05-24.npz (present)",
                "why_deferred": "Budget (~7 h serial at USoc diagram sizes). Superseded for paper use by the "
                "frozen 2026-05-28 headline, whose H1 WT-1c already corrected.",
                "status": "re-derivable on demand",
            },
            {
                "item": "Exact re-derivation of bhps_nonoverlap_reanalysis_2026-06-09 H1",
                "cache": "null_diagrams_bhps_nonoverlap_frozen_B1000_L5000_seed42_2026-06-09.npz (present)",
                "why_deferred": "Budget; identified late in the audit. Greedy era by 7 days.",
                "status": "re-derivable on demand",
            },
            {
                "item": "lm_sensitivity (L2500/L8000) and stratified_markov1_battery_2026-05-13 H1 cells",
                "cache": "NONE at those L / dates",
                "why_deferred": "Not deferrable-by-budget but UNVERIFIABLE: no cached diagrams exist and the "
                "brief forbids regenerating nulls. Would require a full battery re-run "
                "(a production decision for the User, not an audit action).",
                "status": "SUSPECT-UNVERIFIABLE",
            },
        ],
        "corrected_files": (
            [str(Path("results/trajectory_tda_bhps/stage1") / f"bhps_headline_frozen_corrected_{args.date}.json")]
            if corrected is not None
            else []
        ),
    }
    out_audit = wt / "results/trajectory_tda_integration/stage1" / f"w2_fallback_audit_{args.date}.json"
    out_audit.parent.mkdir(parents=True, exist_ok=True)
    if out_audit.exists():
        raise SystemExit(f"refusing to overwrite {out_audit}")
    out_audit.write_text(json.dumps(al.convert_numpy(audit), indent=2), encoding="utf-8")
    print(f"wrote {out_audit}", flush=True)


if __name__ == "__main__":
    main()
