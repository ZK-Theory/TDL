# Research context: TDA-Research/03-Papers/P01-A/_project.md
# Purpose: Compute Table 1 effect-size column d_perm and Wasserstein-ratio
# rho_hat with a delta-method 95% confidence interval, for every
# (dataset x homology dim x null type) cell present in the canonical
# post-audit Wasserstein JSONs. Output a JSON consumed by the Table 1
# specification in the P01-A v2 draft. No randomness; deterministic.

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

PROJ_ROOT = Path(__file__).resolve().parents[4]

POST_AUDIT_JSONS: list[tuple[str, str, Path]] = [
    (
        "USoc",
        "L5000_postaudit_2026-05-02",
        PROJ_ROOT
        / "results/trajectory_tda_integration/post_audit/"
        "04_nulls_wasserstein_w2_L5000_20260502.json",
    ),
    (
        "USoc",
        "L5000_markov2_postaudit_2026-05-02",
        PROJ_ROOT
        / "results/trajectory_tda_integration/post_audit/"
        "04_nulls_wasserstein_w2_L5000_markov2_20260502.json",
    ),
    (
        "USoc",
        "L2000_legacy_2026-04-07",
        PROJ_ROOT
        / "results/trajectory_tda_integration/post_audit/"
        "04_nulls_wasserstein_w2_20260407.json",
    ),
    (
        "USoc",
        "stratified_markov1_L5000_2026-05-02",
        PROJ_ROOT
        / "results/trajectory_tda_integration/stratified_markov/"
        "stratified_markov1_W2_L5000_20260502.json",
    ),
    (
        "BHPS",
        "L5000_postaudit_2026-05-02",
        PROJ_ROOT
        / "results/trajectory_tda_bhps/post_audit/"
        "04_nulls_wasserstein_w2_L5000_20260502.json",
    ),
    (
        "BHPS",
        "L2000_legacy_2026-04-07",
        PROJ_ROOT
        / "results/trajectory_tda_bhps/post_audit/"
        "04_nulls_wasserstein_w2_20260407.json",
    ),
    (
        "BHPS",
        "stratified_markov1_L5000_2026-05-02",
        PROJ_ROOT
        / "results/trajectory_tda_bhps/stratified_markov/"
        "stratified_markov1_W2_L5000_20260502.json",
    ),
]


def _d_perm(
    mean_obs_null: float,
    mean_null_null: float,
    std_null_null: float,
) -> float | None:
    """Permutation effect size: (mean_obs_null - mean_null_null) / std_null_null.

    Returns None when std_null_null is zero or non-finite — the cell is
    flagged in the output rather than dropped.
    """
    if std_null_null is None or not math.isfinite(std_null_null) or std_null_null == 0.0:
        return None
    return float((mean_obs_null - mean_null_null) / std_null_null)


def _rho_hat_delta_ci(
    mean_obs_null: float,
    std_obs_null: float,
    n_obs: int,
    mean_null_null: float,
    std_null_null: float,
    n_null_pairs: int,
    z: float = 1.959963984540054,  # qnorm(0.975)
) -> tuple[float, float, float] | None:
    """Delta-method 95% CI for rho_hat = mean(W_obs_null) / mean(W_null_null).

    Var(rho_hat) ~= (1 / mean_null_null^2) * Var(mean_obs_null)
                   + (mean_obs_null^2 / mean_null_null^4) * Var(mean_null_null)
    Var(mean_obs_null)   = std_obs_null^2 / n_obs
    Var(mean_null_null)  = std_null_null^2 / n_null_pairs

    Returns (rho_hat, ci_lo, ci_hi) on success, None if the denominator
    distribution is degenerate (mean_null_null <= 0 or std missing).
    """
    if mean_null_null is None or mean_null_null <= 0.0:
        return None
    if std_obs_null is None or std_null_null is None:
        return None
    rho = mean_obs_null / mean_null_null
    var_on = (std_obs_null ** 2) / max(n_obs, 1)
    var_nn = (std_null_null ** 2) / max(n_null_pairs, 1)
    var_rho = var_on / (mean_null_null ** 2) + (mean_obs_null ** 2) * var_nn / (mean_null_null ** 4)
    se_rho = math.sqrt(var_rho)
    return float(rho), float(rho - z * se_rho), float(rho + z * se_rho)


def _collect_cells(label: str, source: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for null_key, null_block in payload.items():
        if not isinstance(null_block, dict) or "n_permutations" not in null_block:
            continue
        n_perm = int(null_block.get("n_permutations", 0))
        for dim_key in ("H0", "H1"):
            dim_block = null_block.get(dim_key)
            if not isinstance(dim_block, dict):
                continue
            mean_on = dim_block.get("mean_wasserstein_obs_null")
            std_on = dim_block.get("std_wasserstein_obs_null")
            mean_nn = dim_block.get("mean_wasserstein_null_null")
            std_nn = dim_block.get("std_wasserstein_null_null")
            n_nn_pairs = int(dim_block.get("n_null_null_pairs", 0))
            p_value = dim_block.get("p_value")
            obs_null_arr = dim_block.get("obs_null_distribution")
            obs_null_len = len(obs_null_arr) if isinstance(obs_null_arr, list) else 0

            d_perm = (
                _d_perm(mean_on, mean_nn, std_nn)
                if mean_on is not None and mean_nn is not None
                else None
            )
            rho_ci = (
                _rho_hat_delta_ci(
                    mean_on,
                    std_on,
                    n_perm,
                    mean_nn,
                    std_nn,
                    n_nn_pairs,
                )
                if mean_on is not None
                and mean_nn is not None
                and std_on is not None
                and std_nn is not None
                else None
            )
            rho_hat, ci_lo, ci_hi = (rho_ci if rho_ci is not None else (None, None, None))

            rows.append(
                {
                    "dataset": label,
                    "source": source,
                    "null": null_key,
                    "dim": dim_key,
                    "n_permutations": n_perm,
                    "n_null_null_pairs": n_nn_pairs,
                    "obs_null_array_len": obs_null_len,
                    "mean_obs_null": mean_on,
                    "std_obs_null": std_on,
                    "mean_null_null": mean_nn,
                    "std_null_null": std_nn,
                    "p_value": p_value,
                    "d_perm": d_perm,
                    "rho_hat": rho_hat,
                    "rho_hat_ci_lo": ci_lo,
                    "rho_hat_ci_hi": ci_hi,
                    "rho_hat_ci_excludes_1": (
                        ci_lo is not None and ci_hi is not None and (ci_lo > 1.0 or ci_hi < 1.0)
                    ),
                }
            )
    return rows


def _format_md_table(rows: list[dict[str, Any]]) -> str:
    header = (
        "| Dataset | Source | Null | Dim | B | mean obs-null | mean null-null | "
        "std null-null | d_perm | rho_hat | 95% delta CI | p | array len |"
    )
    sep = "|---" * 13 + "|"
    lines = [header, sep]
    for r in rows:
        def fmt(x: Any, digits: int = 3) -> str:
            if x is None:
                return "n/a"
            if isinstance(x, bool):
                return str(x)
            try:
                return f"{x:.{digits}f}"
            except (TypeError, ValueError):
                return str(x)

        ci = (
            f"[{fmt(r['rho_hat_ci_lo'])}, {fmt(r['rho_hat_ci_hi'])}]"
            if r["rho_hat_ci_lo"] is not None
            else "n/a"
        )
        lines.append(
            f"| {r['dataset']} | {r['source']} | {r['null']} | {r['dim']} | "
            f"{r['n_permutations']} | {fmt(r['mean_obs_null'])} | "
            f"{fmt(r['mean_null_null'])} | {fmt(r['std_null_null'])} | "
            f"{fmt(r['d_perm'], 2)} | {fmt(r['rho_hat'])} | {ci} | "
            f"{fmt(r['p_value'], 4)} | {r['obs_null_array_len']} |"
        )
    return "\n".join(lines)


def main() -> None:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for label, source, path in POST_AUDIT_JSONS:
        if not path.exists():
            missing.append(str(path))
            continue
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        rows.extend(_collect_cells(label, source, payload))

    output_dir = Path(__file__).resolve().parent
    date_suffix = "2026-05-22"
    json_path = output_dir / f"table1_effects_{date_suffix}.json"
    md_path = output_dir / f"table1_effects_{date_suffix}.md"

    payload_out: dict[str, Any] = {
        "rows": rows,
        "missing_inputs": missing,
        "n_rows": len(rows),
        "delta_method_z_95": 1.959963984540054,
        "sources": [
            {"dataset": d, "source": s, "path": str(p)} for d, s, p in POST_AUDIT_JSONS
        ],
        "notes": (
            "d_perm = (mean_obs_null - mean_null_null) / std_null_null. "
            "rho_hat = mean_obs_null / mean_null_null. "
            "Delta-method 95% CI uses Var(mean_obs_null) = std_obs_null^2 / n_perm "
            "and Var(mean_null_null) = std_null_null^2 / n_null_pairs. "
            "B = n_permutations stored in input JSON (post-audit canonical = 100; "
            "headline relaunch pre-registered at 1000)."
        ),
    }

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(payload_out, fh, indent=2)

    with md_path.open("w", encoding="utf-8") as fh:
        fh.write("# Table 1 candidate rows — d_perm and rho_hat with delta-method CI\n\n")
        fh.write(f"Generated {date_suffix} from canonical post-audit Wasserstein JSONs.\n\n")
        fh.write(_format_md_table(rows))
        fh.write("\n")

    print(f"Wrote {json_path.relative_to(PROJ_ROOT)}")
    print(f"Wrote {md_path.relative_to(PROJ_ROOT)}")
    if missing:
        print("MISSING:")
        for m in missing:
            print(f"  {m}")


if __name__ == "__main__":
    main()
