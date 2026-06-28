# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: T1.28 FDR assembly — collect per-subgroup W2 checkpoints into the
#   committed recompute JSON, then apply per-family Benjamini-Hochberg FDR
#   (gender 2, NS-SEC 3, cohort 7 USoc / 6 BHPS) and write the FDR JSON.
"""T1.28 output assembly + per-family BH FDR.

Usage::

    # Step 1 — assemble recompute JSON from per-subgroup checkpoints:
    uv run --env-file .env python trajectory_tda/scripts/run_t128_bh_fdr.py assemble

    # Step 2 — apply BH FDR and write per-family JSON:
    uv run --env-file .env python trajectory_tda/scripts/run_t128_bh_fdr.py fdr \\
        --recompute results/panel_methodology/fdr/stratified_w2_recompute_<date>.json

    # Both steps in one call:
    uv run --env-file .env python trajectory_tda/scripts/run_t128_bh_fdr.py all

Outputs (committed on the Task branch)::

    results/panel_methodology/fdr/stratified_w2_recompute_<YYYY-MM-DD>.json
    results/panel_methodology/fdr/stratified_w2_bh_per_family_<YYYY-MM-DD>.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

# ── Two-path output roots ─────────────────────────────────────────────────────

PROJ_ROOT = Path("C:/Users/steph/TDL")
WORKTREE = Path(__file__).resolve().parent.parent.parent

SUBGROUP_CKPT_DIR = PROJ_ROOT / "results/panel_methodology/fdr/subgroup_checkpoints"
OUTPUT_DIR = WORKTREE / "results/panel_methodology/fdr"

# ── Pre-registration references ───────────────────────────────────────────────

PRE_REG_REF = (
    "results/panel_methodology/fdr/pre_registrations_2026-06-13.json"
    " + 2026-06-27 amendment (per-subgroup model, BH per family)"
    " + 2026-06-28 amendment (bhps cohort n_tests 7->6)"
)

# ── Expected subgroup counts (post-amendments) ────────────────────────────────

EXPECTED_SUBGROUPS: dict[str, list[tuple[str, str]]] = {
    "usoc": [
        ("gender", "Female"),
        ("gender", "Male"),
        ("nssec", "Intermediate"),
        ("nssec", "Professional/Managerial"),
        ("nssec", "Routine/Manual"),
        ("cohort", "1930s"),
        ("cohort", "1940s"),
        ("cohort", "1950s"),
        ("cohort", "1960s"),
        ("cohort", "1970s"),
        ("cohort", "1980s"),
        ("cohort", "1990s"),
    ],
    "bhps": [
        ("gender", "Female"),
        ("gender", "Male"),
        ("nssec", "Intermediate"),
        ("nssec", "Professional/Managerial"),
        ("nssec", "Routine/Manual"),
        ("cohort", "1930s"),
        ("cohort", "1940s"),
        ("cohort", "1950s"),
        ("cohort", "1960s"),
        ("cohort", "1970s"),
        ("cohort", "1980s"),
    ],
}

ALPHA = 0.05
B_DEFAULT = 1000
SEED = 42


# ── Checkpoint loading ────────────────────────────────────────────────────────


def _ckpt_path(dataset: str, stratifier: str, label: str, B: int) -> Path:
    safe_label = label.replace("/", "-").replace(" ", "_")
    return SUBGROUP_CKPT_DIR / f"{dataset}_{stratifier}_{safe_label}_B{B}_seed{SEED}.json"


def _load_all_checkpoints(B: int = B_DEFAULT) -> dict[str, list[dict[str, Any]]]:
    """Load all per-subgroup checkpoints. Raises if any expected subgroup is missing."""
    results: dict[str, list[dict[str, Any]]] = {}
    missing: list[str] = []

    for ds, subgroups in EXPECTED_SUBGROUPS.items():
        results[ds] = []
        for strat, lbl in subgroups:
            p = _ckpt_path(ds, strat, lbl, B)
            if not p.exists():
                missing.append(f"{ds}/{strat}/{lbl}")
                continue
            with open(p) as f:
                results[ds].append(json.load(f))

    if missing:
        raise FileNotFoundError(
            "Missing checkpoints — run run_t128_stratified_w2.py first:\n" + "\n".join(f"  {m}" for m in missing)
        )
    return results


# ── Recompute JSON assembly ───────────────────────────────────────────────────


def _get_git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKTREE, text=True).strip()
    except Exception:
        return "unknown"


def assemble_recompute_json(B: int = B_DEFAULT) -> Path:
    """Collect per-subgroup checkpoints into the primary recompute JSON.

    Returns the output path.
    """
    checkpoints = _load_all_checkpoints(B)
    today = date.today().isoformat()
    out_path = OUTPUT_DIR / f"stratified_w2_recompute_{today}.json"

    if out_path.exists():
        raise FileExistsError(
            f"Output already exists (no-overwrite rule): {out_path}\nUse a different date or delete the file manually."
        )

    git_head = _get_git_head()

    # Build per-dataset subgroup lists and count families
    datasets_out: dict[str, Any] = {}
    for ds, ckpts in checkpoints.items():
        subgroups_out: list[dict[str, Any]] = []
        gender_n = nssec_n = cohort_n = 0
        for ck in ckpts:
            strat = ck["stratifier"]
            if strat == "gender":
                gender_n += 1
            elif strat == "nssec":
                nssec_n += 1
            elif strat == "cohort":
                cohort_n += 1
            subgroups_out.append(
                {
                    "stratifier": strat,
                    "subgroup_id": ck["subgroup_id"],
                    "n": ck["n"],
                    "actual_landmarks": ck["actual_landmarks"],
                    "t_ratio": ck["t_ratio"],
                    "bca_ci": ck["bca_ci"],
                    "w2_p": ck["w2_p"],
                    "w2_rejects": ck["w2_rejects"],
                    "landscape_l2_p": ck["landscape_l2_p"],
                }
            )
        datasets_out[ds] = {
            "subgroups": subgroups_out,
            "gender_n": gender_n,
            "nssec_n": nssec_n,
            "cohort_n": cohort_n,
        }

    payload: dict[str, Any] = {
        "schema_version": "stratified-w2-recompute-v1",
        "generated_at": today,
        "task": "T1.28 — per-subgroup stratified W2 recompute + per-family BH FDR",
        "pre_registration": PRE_REG_REF,
        "inputs": {
            "git_head": git_head,
            "frozen_loadings_provenance": {
                "usoc": str(PROJ_ROOT / "results/trajectory_tda_integration/embeddings.npy"),
                "bhps": str(PROJ_ROOT / "results/trajectory_tda_bhps/embeddings.npy"),
            },
        },
        "params": {
            "null_model": "markov-1",
            "frozen_loadings": True,
            "B": B,
            "seed": SEED,
            "p_value_formula": "(r+1)/(B+1)",
            "alpha": ALPHA,
            "L": 5000,
            "actual_landmarks": "min(5000, subgroup_n) — see per-subgroup actual_landmarks field",
        },
        "datasets": datasets_out,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Recompute JSON written: {out_path}")
    return out_path


# ── Per-family BH FDR ─────────────────────────────────────────────────────────


def _bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg correction. Returns adjusted p-values in original order."""
    from statsmodels.stats.multitest import multipletests

    if not p_values:
        return []
    _, adj, _, _ = multipletests(p_values, method="fdr_bh")
    return list(adj)


def apply_bh_fdr(recompute_path: Path) -> Path:
    """Apply per-family BH FDR and write the per-family FDR JSON.

    Returns the output path.
    """
    with open(recompute_path) as f:
        recompute: dict[str, Any] = json.load(f)

    today = date.today().isoformat()
    out_path = OUTPUT_DIR / f"stratified_w2_bh_per_family_{today}.json"

    if out_path.exists():
        raise FileExistsError(f"Output already exists (no-overwrite rule): {out_path}")

    datasets_out: dict[str, Any] = {}
    for ds_name, ds_data in recompute["datasets"].items():
        # Group subgroups by stratifier family
        families: dict[str, list[dict[str, Any]]] = {
            "gender": [],
            "nssec": [],
            "cohort": [],
        }
        for sg in ds_data["subgroups"]:
            fam = sg["stratifier"]
            if fam in families:
                families[fam].append(sg)

        # BH per family
        families_out: dict[str, Any] = {}
        for fam_name, members in families.items():
            raw_ps = [sg["w2_p"] for sg in members]
            adj_ps = _bh_adjust(raw_ps)

            tests_out: list[dict[str, Any]] = []
            for sg, raw_p, adj_p in zip(members, raw_ps, adj_ps):
                # adjusted_p >= raw_p invariant (BH is monotone)
                adj_p_clipped = max(float(adj_p), float(raw_p))
                tests_out.append(
                    {
                        "subgroup_id": sg["subgroup_id"],
                        "raw_p": float(raw_p),
                        "adjusted_p": adj_p_clipped,
                        "rejected": bool(adj_p_clipped < ALPHA),
                        "t_ratio": sg["t_ratio"],
                        "bca_ci": sg["bca_ci"],
                    }
                )

            families_out[fam_name] = {
                "method": "BH",
                "n_tests": len(members),
                "alpha": ALPHA,
                "tests": tests_out,
            }

        datasets_out[ds_name] = {"families": families_out}

    payload: dict[str, Any] = {
        "schema_version": "stratified-w2-fdr-families-v1",
        "generated_at": today,
        "pre_registration": PRE_REG_REF,
        "source_recompute": str(recompute_path),
        "datasets": datasets_out,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"FDR JSON written: {out_path}")
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T1.28 assembly + per-family BH FDR")
    sub = parser.add_subparsers(dest="command", required=True)

    # assemble
    p_assemble = sub.add_parser("assemble", help="Assemble recompute JSON from checkpoints")
    p_assemble.add_argument("--B", type=int, default=B_DEFAULT)

    # fdr
    p_fdr = sub.add_parser("fdr", help="Apply BH FDR to recompute JSON")
    p_fdr.add_argument(
        "--recompute",
        type=Path,
        required=True,
        help="Path to stratified_w2_recompute_<date>.json",
    )

    # all
    p_all = sub.add_parser("all", help="Assemble + FDR in one call")
    p_all.add_argument("--B", type=int, default=B_DEFAULT)

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.command == "assemble":
        assemble_recompute_json(B=args.B)

    elif args.command == "fdr":
        apply_bh_fdr(recompute_path=args.recompute)

    elif args.command == "all":
        recompute_path = assemble_recompute_json(B=args.B)
        apply_bh_fdr(recompute_path=recompute_path)


if __name__ == "__main__":
    main()
