#!/usr/bin/env python3
# Research context: docs/superpowers/plans/2026-05-28-manager-research-assurance-workflow.md
# Purpose: Pre-dispatch validator for APM Task Prompts. Checks a bus task.md is
#   self-contained and, when it touches research-assurance lanes, carries a
#   Research Assurance Requirements block with explicit parameters, paths, and
#   validation commands. Manager-run (and skill-invoked); NOT a blocking hook.
"""APM Task Prompt pre-dispatch validator (Manager Step 6).

Scans a Task Prompt bus file for the self-containedness and research-assurance
requirements the Manager workflow expects before dispatch. This is a judgment
aid, not a hard gate — FAIL flags self-containedness breaks and a missing
assurance block when lanes are clearly touched; WARN flags softer gaps.

Usage:
    apm_task_prompt_check.py .apm/bus/<agent>/task.md   # one prompt
    apm_task_prompt_check.py                            # all .apm/bus/*/task.md
    apm_task_prompt_check.py --strict <path>            # WARN also fails

Exit codes:
    0 — no FAILs (and, under --strict, no WARNs).
    1 — at least one FAIL (or WARN under --strict).
    2 — framework error (no repo root, no task files).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Phrases that break Worker self-containedness (Workers do not read Spec/Plan).
FORBIDDEN_REFERENCES = (
    re.compile(r"\bsee\s+(?:the\s+)?(?:spec|plan)\b", re.IGNORECASE),
    re.compile(r"\b(?:check|refer to)\s+(?:the\s+)?(?:spec|plan)\b", re.IGNORECASE),
)

# Lane trigger keywords — if present, the prompt likely touches that assurance
# lane and should carry a Research Assurance Requirements block.
LANE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Topology": ("persistence", "persistent homology", "filtration", "wasserstein",
                 "landscape", "mapper", "zigzag", "homology", " ph "),
    "Stochastic / Null Model": ("permutation", "markov", "null model", "bootstrap",
                                "p-value", "p value", "shuffle", "seed"),
    "Statistical / Panel": ("estimand", "ipw", "mice", "fdr", "glmm", "svyglm",
                            "manski", "denominator", "eligibility"),
    "Representation": ("pca", "umap", "scaler", "frozen loadings", "embedding",
                       "gmm", "recoding"),
    "Paper Claim": ("manuscript", "paper claim", "decision rule", "disclosure",
                    "table entry", "figure caption"),
}

STOCHASTIC_KEYWORDS = LANE_KEYWORDS["Stochastic / Null Model"]


def find_repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"No .git directory found above {here}")


def touched_lanes(text_lower: str) -> list[str]:
    return [lane for lane, kws in LANE_KEYWORDS.items()
            if any(k in text_lower for k in kws)]


def check_prompt(path: Path) -> tuple[list[str], list[str]]:
    """Return (fails, warns) for one Task Prompt file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    low = text.lower()
    fails: list[str] = []
    warns: list[str] = []

    # FAIL: self-containedness — no bare Spec/Plan references.
    for pat in FORBIDDEN_REFERENCES:
        m = pat.search(text)
        if m:
            fails.append(f"self-containedness: references '{m.group(0)}' "
                         "(Workers do not read Spec/Plan - embed the content)")

    lanes = touched_lanes(low)
    has_ra_block = "research assurance requirements" in low

    # FAIL: lanes clearly touched but no Research Assurance Requirements block.
    if lanes and not has_ra_block:
        fails.append("research assurance: prompt touches lane(s) "
                     f"[{', '.join(lanes)}] but has no "
                     "'Research Assurance Requirements' block")

    # WARN: stochastic work without an explicit seed mention.
    if any(k in low for k in STOCHASTIC_KEYWORDS) and "seed" not in low:
        warns.append("no explicit 'seed' mentioned despite stochastic content")

    # WARN: an Expected Output section but no results/ path.
    if "expected output" in low and "results/" not in low:
        warns.append("Expected Output present but no explicit results/ path")

    # WARN: no validation command.
    if "uv run" not in low and "pytest" not in low:
        warns.append("no validation command (uv run / pytest) found")

    # WARN: no vault obligation stated.
    if "vault" not in low and "computational-log" not in low:
        warns.append("no vault obligation (vault / Computational-Log) stated")

    # WARN: worktree dispatch without project-root path guidance.
    if "worktree" in low and "proj_root" not in low and "project root" not in low:
        warns.append("worktree dispatch but no PROJ_ROOT / project-root guidance "
                     "for .apm paths")

    return fails, warns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Task Prompt bus file to check")
    parser.add_argument("--strict", action="store_true",
                        help="treat WARN as failure")
    args = parser.parse_args(argv)

    if args.path:
        p = Path(args.path)
        if not p.is_file():
            print(f"ERROR: {p} is not a file.", file=sys.stderr)
            return 2
        targets = [p]
    else:
        try:
            repo_root = find_repo_root()
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        targets = sorted((repo_root / ".apm" / "bus").glob("*/task.md"))

    targets = [t for t in targets if t.is_file()]
    if not targets:
        print("ERROR: no Task Prompt files found to check.", file=sys.stderr)
        return 2

    any_fail = False
    any_warn = False
    for path in targets:
        fails, warns = check_prompt(path)
        if not fails and not warns:
            print(f"  OK    {path}")
            continue
        print(f"  ----  {path}")
        for f in fails:
            print(f"  FAIL  {f}")
            any_fail = True
        for w in warns:
            print(f"  WARN  {w}")
            any_warn = True

    if any_fail or (args.strict and any_warn):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
