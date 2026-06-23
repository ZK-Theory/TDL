# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Recover the Apr-8-vintage integration trajectory state sequences
#          (01_trajectories_sequences.json) by re-running the deterministic
#          steps 1-2 build, then canary-gate against the committed OM baseline
#          (comparison_at_gmm_k.ari = 0.2611807) so the B9 OM-vs-GMM ARI is
#          computed on the genuine Apr-8 object, not the 2026-05-02 orphan.
"""Recover and canary-check the Apr-8 integration trajectory sequences.

The on-disk ``results/trajectory_tda_integration/01_trajectories_sequences.json``
was rewritten 2026-05-02 (an orphan no canonical result consumes), three weeks
after the Apr-8 GMM labels and OM baseline. The sequence-construction code path
(``build_trajectories_from_raw`` and its state-assignment dependencies) is
byte-identical between the Apr-8 commit and HEAD and is fully deterministic
(no RNG; ``groupby('pidp', sort=True)`` row order), so re-running it reproduces
the Apr-8 sequences IFF the raw UKDA inputs are unchanged. The OM-vs-GMM k=7 ARI
canary (must reproduce 0.2611807 within 1e-4 against the committed Apr-8 GMM
labels) is the arbiter: pass => recovered; fail => the Apr-8 build is not
reproducible from current code+data and the caller must report Partial.

Writes the regenerated sequences to a scratch path (does NOT touch the live
integration checkpoint). Promotion of the recovered file to the canonical path
is a separate, canary-gated step performed by the caller.

Run from the task worktree root::

    uv run --env-file .env python -m trajectory_tda.scripts.recover_apr8_integration_sequences --canary
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.metrics import adjusted_rand_score

from trajectory_tda.data.trajectory_builder import build_trajectories
from trajectory_tda.scripts.run_om_baseline import compute_pairwise_dhd

PROJ_ROOT = Path("C:/Users/steph/TDL")
DEFAULT_DATA_DIR = Path("trajectory_tda/data")
# The raw UKDA tab files are gitignored and live only at PROJ_ROOT. The loader
# rglobs b{w}_indresp.tab (BHPS) and {w}_indresp.tab (USoc); both subtrees are
# nested under UKDA-6614-tab, so both subdir overrides point there.
DEFAULT_BHPS_SUBDIR = "UKDA-6614-tab"
DEFAULT_USOC_SUBDIR = "UKDA-6614-tab"
DEFAULT_OUT = PROJ_ROOT / "results/trajectory_tda_integration_apr8_recovery/01_trajectories_sequences.json"
LIVE_ANALYSIS_JSON = PROJ_ROOT / "results/trajectory_tda_integration/05_analysis.json"

# Apr-8 integration build parameters (from results_full.json["args"]).
MIN_YEARS = 10
MAX_GAP = 2
INCOME_THRESHOLD = 0.6

EXPECTED_N = 27_280
OM_K = 7
CANARY_ARI = 0.2611807
CANARY_TOL = 1e-4


def sha256_of(path: Path) -> str:
    """Return the hex sha256 of a file's bytes."""

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def regenerate_sequences(
    data_dir: Path,
    out_path: Path,
    bhps_subdir: str = DEFAULT_BHPS_SUBDIR,
    usoc_subdir: str = DEFAULT_USOC_SUBDIR,
) -> list[list[str]]:
    """Rebuild the integration state sequences and write them to out_path."""

    trajectories, _metadata = build_trajectories(
        data_dir=data_dir,
        min_years=MIN_YEARS,
        max_gap=MAX_GAP,
        income_threshold=INCOME_THRESHOLD,
        bhps_subdir=bhps_subdir,
        usoc_subdir=usoc_subdir,
    )
    trajectories = [list(t) for t in trajectories]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(trajectories, handle)
    return trajectories


def om_k7_ari_vs_gmm(trajectories: list[list[str]], analysis_json: Path = LIVE_ANALYSIS_JSON) -> float:
    """Compute OM (DHD ward-linkage) k=7 vs canonical GMM k=7 ARI (the canary)."""

    with analysis_json.open("r", encoding="utf-8") as handle:
        gmm_labels = np.asarray(json.load(handle)["gmm_labels"], dtype=np.int64)
    condensed = compute_pairwise_dhd(trajectories)
    linkage_matrix = linkage(condensed, method="ward")
    labels_k7 = fcluster(linkage_matrix, t=OM_K, criterion="maxclust") - 1
    return float(adjusted_rand_score(gmm_labels, labels_k7))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--bhps-subdir", default=DEFAULT_BHPS_SUBDIR)
    parser.add_argument("--usoc-subdir", default=DEFAULT_USOC_SUBDIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--canary",
        action="store_true",
        help="Also compute the OM-vs-GMM k=7 ARI and check it reproduces 0.2611807.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    print("=== Recover Apr-8 integration trajectory sequences ===")
    print(f"data_dir={args.data_dir}  out={args.out}")
    print(f"bhps_subdir={args.bhps_subdir}  usoc_subdir={args.usoc_subdir}")
    print(f"params: min_years={MIN_YEARS} max_gap={MAX_GAP} income_threshold={INCOME_THRESHOLD}")

    trajectories = regenerate_sequences(args.data_dir, args.out, args.bhps_subdir, args.usoc_subdir)
    n = len(trajectories)
    digest = sha256_of(args.out)
    print(f"regenerated n={n} (expected {EXPECTED_N}); sha256={digest}")
    if n != EXPECTED_N:
        print(f"WARNING: n={n} != expected {EXPECTED_N} — cohort mismatch, canary not meaningful")

    if args.canary:
        if n != EXPECTED_N:
            print("CANARY SKIPPED — n != 27,280, so ARI vs the 27,280 GMM labels is undefined")
        else:
            ari = om_k7_ari_vs_gmm(trajectories)
            ok = abs(ari - CANARY_ARI) <= CANARY_TOL
            print(f"CANARY OM-vs-GMM k=7 ARI = {ari:.10f} (target {CANARY_ARI}, tol {CANARY_TOL})")
            print(f"CANARY {'PASS' if ok else 'FAIL'}")
    print(f"elapsed={time.perf_counter() - started:.1f}s")
    print("=== complete ===")


if __name__ == "__main__":
    main()
