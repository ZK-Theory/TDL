#!/usr/bin/env python3
# Research context: docs/superpowers/plans/2026-05-28-tdl-research-skillset-design.md
# Purpose: Keep the Codex skill tree (.agents/skills/) and the Claude Code skill
#   tree (.claude/skills/) in step. Runtime-agnostic skills are byte-mirrored
#   from .agents/ (authoring source of truth) into .claude/; runtime-specific and
#   plugin-owned skills are deliberately excluded. Also presence-checks that the
#   Research-Assurance sections are present in the Claude APM guides.
"""Dual-tree skill sync for the research-assurance skillset.

`.agents/skills/` is the authoring source of truth. This tool mirrors the
runtime-agnostic skills into `.claude/skills/` so Claude Code can load them,
while leaving runtime-specific skills (which legitimately differ by terminology,
e.g. "start Codex CLI" vs "start Claude Code") and plugin-owned skills alone.

Classification is exhaustive and fail-safe: every directory under
`.agents/skills/` must be either in SYNC_SKILLS or matched by EXCLUDE; an
unclassified skill is an error, so a newly authored skill cannot silently fall
through the net (it must be deliberately added to SYNC_SKILLS).

Modes:
    sync_agent_skills.py              # mirror SYNC_SKILLS .agents/ -> .claude/
    sync_agent_skills.py --check      # verify in step; exit 1 on any divergence
    sync_agent_skills.py --check-guides  # verify RA markers in .claude APM guides

Exit codes:
    0 — in step (or sync completed cleanly).
    1 — divergence found (--check) or unclassified skill, or missing RA markers.
    2 — framework error (missing trees, bad invocation).
"""

from __future__ import annotations

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path

# --- Manifest -------------------------------------------------------------

# Runtime-agnostic skills mirrored .agents/skills/ -> .claude/skills/.
# Add every new research-assurance skill here as it is authored.
SYNC_SKILLS: set[str] = {
    # Domain + coordination skills (already present in both trees)
    "bhps-wave-crosswalk",
    "commit-log",
    "humanizer",
    "markov-null-design",
    "new-analysis",
    "notation-check",
    "paper-draft",
    "paper-repo-extract",
    "phase0-status",
    "tda-experiment",
    "tda-figure-spec",
    "validate-topology",
    "vault-sync",
    "wasserstein-audit",
    # Research-assurance routing skill (Layer 0)
    "research-assurance-triage",
    # Layer-1 lane skills
    "result-provenance-review",
    "statistical-design-audit",
    "pre-reg-to-dispatch",
    "representation-freeze-audit",
    "paper-claim-trace",
    # Layer-2 lane skills
    "null-operation-invariance-audit",
    "panel-estimand-audit",
    "schema-contract-design",
    "topology-benchmark-review",
    "sensitivity-comparison-review",
    "reproducibility-package-review",
}

# Skills deliberately NOT byte-mirrored. Patterns match the .agents/ skill dir name.
#   - apm-communication: runtime-specific terminology (Codex CLI vs Claude Code).
#   - apm-N-*: numbered APM workflow skills supplied to Claude Code by a plugin.
#   - source-command-*: Codex slash-command shims with no Claude equivalent.
EXCLUDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^apm-communication$"),
    re.compile(r"^apm-\d"),
    re.compile(r"^source-command-"),
)

# Stable heading substrings that must appear in each Claude APM guide once the
# Research-Assurance workflow has been ported (Workstream B).
GUIDE_RA_MARKERS: dict[str, str] = {
    "task-assignment.md": "Research Assurance Requirements",
    "task-execution.md": "Research Assurance Requirements",
    "task-logging.md": "Research Assurance Evidence",
    "task-review.md": "Research assurance review",
}


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) until a .git directory is found."""
    here = (start or Path.cwd()).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"No .git directory found above {here}")


def is_excluded(name: str) -> bool:
    """True if the skill dir name matches any EXCLUDE pattern."""
    return any(p.search(name) for p in EXCLUDE_PATTERNS)


def classify(agents_skills: Path) -> tuple[list[str], list[str], list[str]]:
    """Partition .agents/skills/ dirs into (to_sync, errors, planned).

    Every directory present in .agents/ must be in SYNC_SKILLS or match EXCLUDE;
    anything else is a fatal error so a new skill cannot silently fall through.
    SYNC_SKILLS entries not yet authored in .agents/ are returned as `planned`
    (benign — the manifest names the full target set up front).
    """
    to_sync: list[str] = []
    errors: list[str] = []
    for child in sorted(p for p in agents_skills.iterdir() if p.is_dir()):
        name = child.name
        if is_excluded(name):
            continue
        if name in SYNC_SKILLS:
            to_sync.append(name)
        else:
            errors.append(name)
    present = {p.name for p in agents_skills.iterdir() if p.is_dir()}
    planned = sorted(SYNC_SKILLS - present)
    return to_sync, errors, planned


def diff_skill(src: Path, dst: Path) -> list[str]:
    """Return a list of relative paths that differ (or are missing) dst vs src."""
    differing: list[str] = []
    for src_file in sorted(src.rglob("*")):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(src)
        dst_file = dst / rel
        if not dst_file.exists() or not filecmp.cmp(src_file, dst_file, shallow=False):
            differing.append(str(rel))
    # Files present in dst but absent in src (stale).
    if dst.exists():
        for dst_file in sorted(dst.rglob("*")):
            if dst_file.is_dir():
                continue
            rel = dst_file.relative_to(dst)
            if not (src / rel).exists():
                differing.append(f"{rel} (stale in .claude/, absent in .agents/)")
    return differing


def lint_path_literals(skill_dir: Path) -> list[str]:
    """Warn on tree-specific path literals that would break under sync."""
    warnings: list[str] = []
    for md in skill_dir.rglob("*.md"):
        text = md.read_text(encoding="utf-8", errors="replace")
        for literal in (".agents/skills", ".claude/skills"):
            if literal in text:
                warnings.append(f"{md.name}: contains tree-specific path '{literal}'")
    return warnings


def run_sync(agents_skills: Path, claude_skills: Path, check_only: bool) -> int:
    """Sync or check runtime-agnostic skills from .agents/ to .claude/.

    Args:
        agents_skills: Path to .agents/skills/ directory (source of truth).
        claude_skills: Path to .claude/skills/ directory (sync destination).
        check_only: If True, verify sync without writing; if False, mirror divergent skills.

    Returns:
        0 if in sync (or sync completed), 1 if unclassified skills or divergence found.
    """
    to_sync, errors, planned = classify(agents_skills)
    if errors:
        print("ERROR: unclassified skills in .agents/skills/ "
              "(add to SYNC_SKILLS or EXCLUDE_PATTERNS):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    for name in planned:
        print(f"  PLANNED    {name} (in manifest, not yet authored in .agents/)")

    any_divergence = False
    for name in to_sync:
        src = agents_skills / name
        dst = claude_skills / name
        differing = diff_skill(src, dst)
        warnings = lint_path_literals(src)
        for w in warnings:
            print(f"  WARN  {name}: {w}", file=sys.stderr)

        if not differing:
            print(f"  IDENTICAL  {name}")
            continue

        any_divergence = True
        if check_only:
            print(f"  DIVERGED   {name}: {', '.join(differing)}")
            continue

        action = "CREATED" if not dst.exists() else "UPDATED"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print(f"  {action}    {name}: {', '.join(differing)}")

    if check_only and any_divergence:
        print("\nTrees diverged. Run `uv run python tools/sync_agent_skills.py` "
              "to mirror .agents/skills/ -> .claude/skills/.", file=sys.stderr)
        return 1
    return 0


def run_check_guides(repo_root: Path) -> int:
    """Presence-check RA markers in the Claude APM guides (not byte identity)."""
    guides_dir = repo_root / ".claude" / "apm-guides"
    missing: list[str] = []
    for fname, marker in GUIDE_RA_MARKERS.items():
        path = guides_dir / fname
        if not path.exists():
            missing.append(f"{fname} (file missing)")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker not in text:
            missing.append(f"{fname} (missing marker '{marker}')")
        else:
            print(f"  OK  {fname}: '{marker}' present")
    if missing:
        print("\nERROR: Research-Assurance markers missing from .claude/apm-guides/:",
              file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify trees are in step; exit 1 on divergence")
    parser.add_argument("--check-guides", action="store_true",
                        help="verify RA markers present in Claude APM guides")
    args = parser.parse_args(argv)

    try:
        repo_root = find_repo_root()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.check_guides:
        return run_check_guides(repo_root)

    agents_skills = repo_root / ".agents" / "skills"
    claude_skills = repo_root / ".claude" / "skills"
    if not agents_skills.is_dir():
        print(f"ERROR: {agents_skills} not found", file=sys.stderr)
        return 2
    claude_skills.mkdir(parents=True, exist_ok=True)

    return run_sync(agents_skills, claude_skills, check_only=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
