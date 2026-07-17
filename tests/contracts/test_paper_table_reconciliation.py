# Research context: TDA-Research/03-Papers/P01-B/_project.md
# Purpose: Binding test for the paper-table-source-reconciliation contract.
#          Enforces that every numeric cell PRESENTED as an inferential result in
#          the P01-B §4.2 Markov-ladder table reconciles to its certified source
#          value, and that any Wasserstein-2 cell presented as inferential is
#          backed by a source JSON carrying a certified-exact solver stamp. A
#          'greedy_rank' or absent stamp is refused (uncitable), because an
#          unstamped W2 may be the H0-only-valid greedy rank-matching artifact.
#
# Runnable from a bare checkout: the certified landscape L2 values are pinned as
# literals (derivation below); the summary JSON it reads for the solver stamp is
# a committed deliverable. No gitignored intermediate is required.
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TABLE = REPO_ROOT / "papers" / "P01-B-JRSSB" / "drafts" / "sections" / "results-4-2-tables.md"
SUMMARY = (
    REPO_ROOT / "results" / "trajectory_tda_integration" / "post_audit" / "markov2_alpha_sweep_summary_2026-06-16.json"
)

# Keys that, when present with an exact value, certify the source used the exact
# optimal-transport solver rather than the greedy rank-matching fallback.
EXACT_STAMP_KEYS = ("backend_versions", "convention", "solver", "wasserstein_backend")

# Certified landscape L2 p-values for the Markov-2 alpha=1 cells. Landscape L2 is
# computed on a solver-independent path (no optimal transport), so these values
# are unaffected by the POT-absence risk that makes the W2 numbers uncitable.
# Derivation: results/trajectory_tda_integration/post_audit/
#   markov2_alpha_sweep_cell_{usoc,bhps}_alpha1_B1000_L5000_seed42_*.json
#   [result][{h0,h1}][landscape_l2_pvalue]; summary git_head 6b71cb2.
PINNED_LANDSCAPE: dict[tuple[str, str], str] = {
    ("USoc", "H0"): "0.258",  # 0.25774225774225773  -> non-reject
    ("USoc", "H1"): "0.003",  # 0.002997002997002997 -> reject
    ("BHPS", "H0"): "<0.001",  # 0.000999000999000999 -> reject
    ("BHPS", "H1"): "<0.001",  # 0.000999000999000999 -> reject
}

# Column indices in Table 2 (after splitting a row on '|' and trimming edges).
_COL_NULL, _COL_L, _COL_B, _COL_DIM, _COL_T, _COL_DPERM, _COL_W2, _COL_LAND = range(8)

_NUMERIC = re.compile(r"\d")


def _has_exact_solver_stamp(summary: dict) -> bool:
    """True iff the summary records the solver actually used as exact.

    An explicit greedy stamp — any string stamp value naming ``greedy`` — is
    disqualifying, so a source declaring ``greedy_rank`` is never accepted even
    if another stamp field is truthy.
    """
    scopes = [summary, summary.get("params", {}), summary.get("inputs", {})]
    exact = False
    for scope in scopes:
        if not isinstance(scope, dict):
            continue
        for key in EXACT_STAMP_KEYS:
            val = scope.get(key)
            if isinstance(val, str) and "greedy" in val.lower():
                return False  # explicit greedy stamp disqualifies the source
            if key == "convention":
                if val == "exact":
                    exact = True
            elif val:  # backend_versions/solver/wasserstein_backend present and truthy
                exact = True
    return exact


def _markov2_alpha1_rows(table_text: str) -> dict[tuple[str, str], list[str]]:
    """Extract the Markov-2 alpha=1 rows keyed by (dataset, dim) -> column list."""
    rows: dict[tuple[str, str], list[str]] = {}
    section: str | None = None
    for line in table_text.splitlines():
        if "**USoc**" in line:
            section = "USoc"
        elif "**BHPS**" in line:
            section = "BHPS"
        if section is None or "Markov-2" not in line:
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 8:
            continue
        dim = cols[_COL_DIM]
        rows[(section, dim)] = cols
    return rows


def _is_presented_number(cell: str) -> bool:
    """A cell presents a numeric result if it contains a digit (a held/withheld
    cell is a dash marker with no digit)."""
    return bool(_NUMERIC.search(cell))


def reconcile(table_text: str, summary: dict, pinned_landscape: dict[tuple[str, str], str]) -> list[str]:
    """Reconcile the Markov-2 alpha=1 table rows against their certified sources.

    Args:
        table_text: Markdown of the §4.2 Markov-ladder table.
        summary: The committed Markov-2 alpha-sweep summary JSON.
        pinned_landscape: Certified landscape L2 values keyed by (dataset, dim).

    Returns:
        Reconciliation violations: (a) a landscape cell whose printed value
        disagrees with the certified value; (b) any W2-derived cell (T, d_perm,
        W2 p) presented as a number while the source carries no exact-solver
        stamp.
    """
    violations: list[str] = []
    stamped = _has_exact_solver_stamp(summary)
    rows = _markov2_alpha1_rows(table_text)
    for key, expected in pinned_landscape.items():
        cols = rows.get(key)
        if cols is None:
            violations.append(f"[MISSING ROW] Markov-2 alpha=1 {key[0]} {key[1]} not found in table")
            continue
        # (a) landscape reconciliation
        land = cols[_COL_LAND]
        if expected not in land:
            violations.append(
                f"[LANDSCAPE MISMATCH] {key[0]} {key[1]}: table prints {land!r}, certified value {expected!r}"
            )
        # (b) W2 presented-as-inferential without an exact-solver stamp
        if not stamped:
            for idx, name in ((_COL_T, "T"), (_COL_DPERM, "d_perm"), (_COL_W2, "W2 p")):
                if _is_presented_number(cols[idx]):
                    violations.append(
                        f"[W2 UNCITABLE] {key[0]} {key[1]}: {name}={cols[idx]!r} presented as inferential "
                        f"but source carries no exact-solver stamp {EXACT_STAMP_KEYS}"
                    )
    return violations


# --- synthetic fixtures for the rejection cases (no file dependency) ----------

_GOOD_TABLE = """
| Null level | $L$ | $B$ | Dim | $T$ | $d$ | $W_2$ $p$ | Landscape $L^2$ $p$ |
| **USoc** | | | | | | | |
| Markov-2, $\\alpha=1$ (matched) | 5,000 | 1,000 | H0 | — | — | —$^{\\ddagger}$ | 0.258 |
| Markov-2, $\\alpha=1$ (matched) | 5,000 | 1,000 | H1 | — | — | —$^{\\ddagger}$ | **0.003** |
| **BHPS** | | | | | | | |
| Markov-2, $\\alpha=1$ (matched) | 5,000 | 1,000 | H0 | — | — | —$^{\\ddagger}$ | **<0.001** |
| Markov-2, $\\alpha=1$ (matched) | 5,000 | 1,000 | H1 | — | — | —$^{\\ddagger}$ | **<0.001** |
"""

_UNSTAMPED_SUMMARY: dict = {"params": {"wasserstein_order": 2}}  # no backend/convention stamp
_STAMPED_SUMMARY: dict = {"params": {"wasserstein_order": 2, "convention": "exact"}}
_GREEDY_SUMMARY: dict = {"params": {"wasserstein_order": 2, "solver": "greedy_rank"}}


def test_paper_table_source_reconciliation() -> None:
    """Bind the paper-table-source-reconciliation invariant.

    Asserts the reconciler REJECTS: (a) a landscape cell that disagrees with the
    certified value (the 'n/a not computed' falsehood); (b) a W2 cell presented
    as a number while the source carries no exact-solver stamp. Asserts it ACCEPTS
    the fixed committed table, and that a stamped source opens the W2 gate.
    """
    # Positive: the fixed synthetic table reconciles against an unstamped source
    # (W2 held, landscape correct).
    assert reconcile(_GOOD_TABLE, _UNSTAMPED_SUMMARY, PINNED_LANDSCAPE) == []

    # (a) landscape 'n/a' falsehood is rejected.
    bad_landscape = _GOOD_TABLE.replace("| 0.258 |", "| n/a |")
    v_a = reconcile(bad_landscape, _UNSTAMPED_SUMMARY, PINNED_LANDSCAPE)
    assert v_a != [], "n/a landscape falsehood must be rejected"
    assert any("LANDSCAPE MISMATCH" in v and "USoc H0" in v for v in v_a), v_a

    # (a') a wrong landscape number is rejected.
    wrong_landscape = _GOOD_TABLE.replace("| 0.258 |", "| 0.999 |")
    assert any("LANDSCAPE MISMATCH" in v for v in reconcile(wrong_landscape, _UNSTAMPED_SUMMARY, PINNED_LANDSCAPE))

    # (b) a numeric W2 presented while the source is unstamped is rejected.
    presented_w2 = _GOOD_TABLE.replace(
        "H0 | — | — | —$^{\\ddagger}$ | 0.258", "H0 | 20.33 | 69.24 | **<0.001** | 0.258"
    )
    v_b = reconcile(presented_w2, _UNSTAMPED_SUMMARY, PINNED_LANDSCAPE)
    assert v_b != [], "uncertified numeric W2 must be rejected"
    assert any("W2 UNCITABLE" in v for v in v_b), v_b

    # (b') the same numeric W2 is ACCEPTED once the source carries an exact stamp
    # (the gate opens for a certified recompute; only landscape must still match).
    v_bp = reconcile(presented_w2, _STAMPED_SUMMARY, PINNED_LANDSCAPE)
    assert not any("W2 UNCITABLE" in v for v in v_bp), v_bp

    # (b'') a source explicitly stamped greedy_rank is refused exactly like an
    # unstamped one — a greedy stamp is not evidence of the exact solver.
    v_greedy = reconcile(presented_w2, _GREEDY_SUMMARY, PINNED_LANDSCAPE)
    assert any("W2 UNCITABLE" in v for v in v_greedy), v_greedy

    # Enforce against the real committed artifacts when present.
    if TABLE.exists() and SUMMARY.exists():
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        real_violations = reconcile(TABLE.read_text(encoding="utf-8"), summary, PINNED_LANDSCAPE)
        assert real_violations == [], "P01-B Table 2 does not reconcile to its certified sources:\n  " + "\n  ".join(
            real_violations
        )
