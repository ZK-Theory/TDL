#!/usr/bin/env python3
# Research context: docs/superpowers/plans/2026-05-28-tdl-research-skillset-design.md
# Purpose: Keep the Codex skill tree (.agents/skills/) and the Claude Code skill
#   tree (.claude/skills/) in step. Runtime-agnostic skills are byte-mirrored
#   from .agents/ (authoring source of truth) into .claude/; runtime-specific and
#   plugin-owned skills are deliberately excluded. Also presence-checks that the
#   Research-Assurance sections are present in the Claude APM guides.
#   SKL-3 (2026-07-21): three-way mirror state in tools/skill_sync_state.json;
#   MIRROR_EDITED detection refuses to silently overwrite mirror-side edits.
"""Dual-tree skill sync for the research-assurance skillset.

`.agents/skills/` is the authoring source of truth. This tool mirrors the
runtime-agnostic skills into `.claude/skills/` so Claude Code can load them,
while leaving runtime-specific skills (which legitimately differ by terminology,
e.g. "start Codex CLI" vs "start Claude Code") and plugin-owned skills alone.

Classification is exhaustive and fail-safe: every directory under
`.agents/skills/` must be either in SYNC_SKILLS or matched by EXCLUDE; an
unclassified skill is an error, so a newly authored skill cannot silently fall
through the net (it must be deliberately added to SYNC_SKILLS).

Three-way mirror state (`tools/skill_sync_state.json`) records the per-file
SHA-256 of the mirror tree after each successful sync. On subsequent runs,
each differing file is classified:

  * dst hash == recorded hash  →  mirror untouched since last sync → safe overwrite
  * dst hash != recorded hash AND dst hash != src hash  →  **MIRROR_EDITED**:
    error with the skill/file names and two remedies; skill is skipped; exit 1.
  * dst missing  →  CREATED (unchanged behaviour).

Bootstrap: absent state file + identical trees → write state. Absent state
file + divergent trees → every divergent skill is MIRROR_EDITED (fail safe).

Modes:
    sync_agent_skills.py              # mirror SYNC_SKILLS .agents/ -> .claude/
    sync_agent_skills.py --check      # verify in step; exit 1 on any divergence
    sync_agent_skills.py --check-guides  # verify RA markers in .claude APM guides
    sync_agent_skills.py --force-mirror  # overwrite MIRROR_EDITED skills

Exit codes:
    0 — in step (or sync completed cleanly).
    1 — divergence found (--check) or unclassified skill, or missing RA markers,
        or any MIRROR_EDITED skill detected (without --force-mirror).
    2 — framework error (missing trees, bad invocation).
"""

from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

# --- Manifest -------------------------------------------------------------

# Runtime-agnostic skills mirrored .agents/skills/ -> .claude/skills/.
# Add every new research-assurance skill here as it is authored.
SYNC_SKILLS: set[str] = {
    # Domain + coordination skills (already present in both trees)
    "assay",
    "bhps-wave-crosswalk",
    "commit-log",
    "humanizer",
    "markov-null-design",
    "new-analysis",
    "notation-check",
    "paper-draft",
    "paper-repo-extract",
    "phase0-status",
    "scout-review",
    "spike",
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
    # Adversarial review (2026-06-29)
    "adversarial-design-review",
    # TDL-adapted engineering + workflow skills (2026-07-02 skill plan)
    "tda-diagnosing-computational-defects",
    "contract-first-tdd",
    "tda-resource-preflight",
    "tda-domain-modeling",
    "tda-codebase-design",
    "tda-statistical-analysis-review",
    "tda-peer-review-panel",
    "tda-literature-verification",
    "tda-task-brief-from-plan",
    "tda-handoff",
    # Tier-2 specialist skills (2026-07-02 skill plan, tier 2)
    "tda-statistical-modeling-toolkit",
    "tda-trajectory-baselines",
    "tda-representation-diagnostics",
    "tda-graph-network-analysis",
    "tda-acceleration-benchmarking",
    "tda-external-data-lookup",
    "tda-visualisation-and-diagramming",
    "tda-document-ingestion",
    # Tier-3 optional skills (2026-07-02 skill plan, tier 3)
    "tda-prototype-sandbox",
    "tda-research-ideation-lab",
    "tda-scenario-stress-test",
    "tda-skill-authoring-workbench",
    "tda-agent-safety-guardrails",
    "tda-learning-scaffold",
    "tda-paper-dissemination-pack",
    "tda-light-task-triage",
    "tda-large-workflow-supervision",
    # Runtime-agnostic complements to plugin-owned (read-only) skills — the
    # guidance applies equally in Claude Code, which has the same plugin
    # skills available (2026-07-06 weekly review, Obs 27 / Obs 35).
    "executing-plans-extras",
    "gh-address-comments-extras",
    "using-git-worktrees-extras",
    "writing-plans-extras",
    "subagent-driven-development-extras",
}

# Skills deliberately NOT byte-mirrored. Patterns match the .agents/ skill dir name.
#   - apm-communication: runtime-specific terminology (Codex CLI vs Claude Code).
#   - apm-N-*: numbered APM workflow skills supplied to Claude Code by a plugin.
#   - source-command-*: Codex slash-command shims with no Claude equivalent.
#   - writing-skills-extras: Codex-side complement (agents/openai.yaml) to the
#     superpowers writing-skills plugin skill, which Claude Code loads from the
#     plugin, not this tree.
EXCLUDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^apm-communication$"),
    re.compile(r"^apm-\d"),
    re.compile(r"^source-command-"),
    re.compile(r"^writing-skills-extras$"),
)

# Stable heading substrings that must appear in each Claude APM guide once the
# Research-Assurance workflow has been ported (Workstream B).
GUIDE_RA_MARKERS: dict[str, str] = {
    "task-assignment.md": "Research Assurance Requirements",
    "task-execution.md": "Research Assurance Requirements",
    "task-logging.md": "Research Assurance Evidence",
    "task-review.md": "Research assurance review",
}

# State-file name — resolved relative to the tools/ directory at repo root.
_STATE_FILE = "skill_sync_state.json"


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


def mirror_skill(src: Path, dst: Path) -> None:
    """Mirror src into dst non-destructively, one file at a time.

    Copies each src file over its dst counterpart (creating parent directories
    as needed, skipping byte-identical files), then removes only dst files
    absent from src plus any stale directories left empty. The dst directory
    itself is never removed: the previous rmtree+copytree update could half-
    delete a skill when a transient Windows handle (agent harness, indexer)
    blocked the directory removal after its files were already gone
    (2026-07-02 incident).

    Raises:
        OSError: If a copy or stale-file removal fails. Files already
            mirrored stay in place, so re-running after the lock is released
            completes the mirror.
    """
    for src_file in sorted(src.rglob("*")):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(src)
        target = dst / rel
        if target.exists() and filecmp.cmp(src_file, target, shallow=False):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, target)
    stale_dirs: list[Path] = []
    if dst.exists():
        for dst_path in sorted(dst.rglob("*")):
            rel = dst_path.relative_to(dst)
            if (src / rel).exists():
                continue
            if dst_path.is_dir():
                stale_dirs.append(dst_path)
            else:
                dst_path.unlink()
    for stale_dir in sorted(stale_dirs, reverse=True):
        stale_dir.rmdir()


# --- Three-way state helpers -----------------------------------------------


def _sha256(path: Path) -> str:
    """SHA-256 hex digest of a file's raw bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _skill_state(skill_dir: Path) -> dict[str, str]:
    """SHA-256 of every file in skill_dir, keyed by POSIX relative path."""
    return {f.relative_to(skill_dir).as_posix(): _sha256(f) for f in sorted(skill_dir.rglob("*")) if f.is_file()}


def _load_state(state_path: Path) -> dict[str, dict[str, str]] | None:
    """Load the sync state file, or return None if absent.

    Raises:
        SystemExit: If the file exists but contains malformed JSON (exit code 2).
    """
    if not state_path.exists():
        return None
    text = state_path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"ERROR: malformed state file {state_path}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _save_state(state_path: Path, state: dict[str, dict[str, str]]) -> None:
    """Write the sync state JSON, sorted keys, newline-terminated."""
    state_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _classify_diff(
    src: Path,
    dst: Path,
    recorded: dict[str, str] | None,
) -> tuple[list[str], list[str]]:
    """Three-way classify per-file differences between src (authoring) and dst (mirror).

    For each file that differs (src ≠ dst), determine whether dst was edited
    since the last sync (MIRROR_EDITED) or is safe to overwrite (dst unchanged
    since last sync, or dst file is newly absent).

    Args:
        src: Authoring-tree skill directory.
        dst: Mirror-tree skill directory.
        recorded: Per-file sha256 map from the last sync state, or None
            (bootstrap — no prior recorded state exists).

    Returns:
        (mirror_edited, safe): POSIX-relative path strings of differing files
        in each category. Files absent in dst (CREATED) are always safe.
    """
    mirror_edited: list[str] = []
    safe: list[str] = []

    for src_file in sorted(src.rglob("*")):
        if src_file.is_dir():
            continue
        rel = src_file.relative_to(src).as_posix()
        dst_file = dst / rel

        if not dst_file.exists():
            safe.append(rel)  # CREATED — no mirror edit possible
            continue

        if filecmp.cmp(src_file, dst_file, shallow=False):
            continue  # identical — not differing

        # File differs between src and dst. Three-way classify.
        if recorded is None:
            # Bootstrap: no prior state → cannot distinguish safe from mirror-edited
            mirror_edited.append(rel)
            continue

        recorded_hash = recorded.get(rel)
        if recorded_hash is None:
            # File was added to src after last sync → safe to push to dst
            safe.append(rel)
            continue

        if _sha256(dst_file) == recorded_hash:
            # dst hasn't changed since last sync; src has → safe to overwrite
            safe.append(rel)
        else:
            # dst changed since last sync independently of src → MIRROR_EDITED
            mirror_edited.append(rel)

    # Stale dst files (present in dst but absent in src).
    if dst.exists():
        for dst_file in sorted(dst.rglob("*")):
            if dst_file.is_dir():
                continue
            rel = dst_file.relative_to(dst).as_posix()
            if (src / rel).exists():
                continue
            label = f"{rel} (stale in mirror, absent in authoring tree)"
            if recorded is None:
                mirror_edited.append(label)
            else:
                recorded_hash = recorded.get(rel)
                if recorded_hash is None:
                    # Never present in src at last sync → manually added to mirror
                    mirror_edited.append(label)
                elif _sha256(dst_file) == recorded_hash:
                    # dst unchanged since last sync; src removed it → safe to remove
                    safe.append(label)
                else:
                    # dst was edited since last sync AND src removed it → mirror-edited
                    mirror_edited.append(label)

    return mirror_edited, safe


# --- Core sync logic -------------------------------------------------------


def run_sync(
    agents_skills: Path,
    claude_skills: Path,
    check_only: bool,
    state_path: Path | None = None,
    force_mirror: bool = False,
) -> int:
    """Sync or check runtime-agnostic skills from .agents/ to .claude/.

    When state_path is provided, applies three-way mirror-state classification:
    a mirror-side edit is detected (MIRROR_EDITED) and refused instead of being
    silently overwritten. Without state_path the legacy two-way behaviour is used
    (backward-compatible with callers that don't supply a state file).

    Args:
        agents_skills: Path to .agents/skills/ directory (source of truth).
        claude_skills: Path to .claude/skills/ directory (sync destination).
        check_only: If True, verify sync without writing; if False, mirror divergent skills.
        state_path: Path to the skill_sync_state.json file, or None to skip
            three-way classification.
        force_mirror: If True, overwrite MIRROR_EDITED skills and record fresh state.

    Returns:
        0 if in sync (or sync completed), 1 if unclassified skills or
        divergence found, or if any skill failed to mirror cleanly, or if any
        MIRROR_EDITED skill was detected (without --force-mirror).
    """
    to_sync, errors, planned = classify(agents_skills)
    if errors:
        print(
            "ERROR: unclassified skills in .agents/skills/ (add to SYNC_SKILLS or EXCLUDE_PATTERNS):", file=sys.stderr
        )
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    for name in planned:
        print(f"  PLANNED    {name} (in manifest, not yet authored in .agents/)")

    state: dict[str, dict[str, str]] | None = None
    if state_path is not None:
        state = _load_state(state_path)

    # pending_state accumulates updated state across the run; saved at end.
    pending_state: dict[str, dict[str, str]] = dict(state) if state is not None else {}

    any_divergence = False
    any_failure = False
    any_mirror_edited = False

    for name in to_sync:
        src = agents_skills / name
        dst = claude_skills / name
        warnings = lint_path_literals(src)
        for w in warnings:
            print(f"  WARN  {name}: {w}", file=sys.stderr)

        if state_path is None:
            # --- Legacy path: no three-way classification ---
            differing = diff_skill(src, dst)
            if not differing:
                print(f"  IDENTICAL  {name}")
                continue

            any_divergence = True
            if check_only:
                print(f"  DIVERGED   {name}: {', '.join(differing)}")
                continue

            action = "CREATED" if not dst.exists() else "UPDATED"
            try:
                mirror_skill(src, dst)
            except OSError as exc:
                any_failure = True
                print(
                    f"  ERROR      {name}: mirror failed ({exc}); destination left "
                    "file-consistent — re-run after releasing the lock",
                    file=sys.stderr,
                )
                continue
            print(f"  {action}    {name}: {', '.join(differing)}")

        else:
            # --- Three-way path ---
            recorded = state.get(name) if state is not None else None
            mirror_edited, safe = _classify_diff(src, dst, recorded)

            if not mirror_edited and not safe:
                print(f"  IDENTICAL  {name}")
                pending_state[name] = _skill_state(dst) if dst.exists() else {}
                continue

            any_divergence = True

            if mirror_edited:
                if check_only:
                    print(f"  MIRROR_EDITED  {name}: {', '.join(mirror_edited)}")
                elif not force_mirror:
                    any_mirror_edited = True
                    print(
                        f"  MIRROR_EDITED  {name}: {', '.join(mirror_edited)}\n"
                        "    Remedy: port the change to the authoring tree and re-run,\n"
                        "    or re-run with --force-mirror to discard the mirror edit.",
                        file=sys.stderr,
                    )
                    continue  # skip this skill; others still sync
                # force_mirror=True → fall through to sync without flagging exit 1

            if safe and check_only and not mirror_edited:
                print(f"  DIVERGED   {name}: {', '.join(safe)}")
                continue

            if check_only:
                # MIRROR_EDITED row already printed; also report safe divergence
                if safe:
                    print(f"  DIVERGED   {name}: {', '.join(safe)}")
                continue

            # Sync path (normal UPDATED/CREATED, or force_mirror overriding MIRROR_EDITED)
            action = "CREATED" if not dst.exists() else "UPDATED"
            try:
                mirror_skill(src, dst)
            except OSError as exc:
                any_failure = True
                print(
                    f"  ERROR      {name}: mirror failed ({exc}); destination left "
                    "file-consistent — re-run after releasing the lock",
                    file=sys.stderr,
                )
                continue

            pending_state[name] = _skill_state(dst)
            all_differing = mirror_edited + safe
            print(f"  {action}    {name}: {', '.join(all_differing)}")

    if state_path is not None and not check_only:
        _save_state(state_path, pending_state)

    if check_only and any_divergence:
        print(
            "\nTrees diverged. Run `uv run python tools/sync_agent_skills.py` "
            "to mirror .agents/skills/ -> .claude/skills/.",
            file=sys.stderr,
        )
        return 1
    return 1 if (any_failure or any_mirror_edited) else 0


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
        print("\nERROR: Research-Assurance markers missing from .claude/apm-guides/:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point — parse args and dispatch to run_sync or run_check_guides."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify trees are in step; exit 1 on divergence")
    parser.add_argument("--check-guides", action="store_true", help="verify RA markers present in Claude APM guides")
    parser.add_argument(
        "--force-mirror",
        action="store_true",
        help="overwrite MIRROR_EDITED mirror skills with authoring-tree content; records fresh state",
    )
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
    state_path = repo_root / "tools" / _STATE_FILE

    if not agents_skills.is_dir():
        print(f"ERROR: {agents_skills} not found", file=sys.stderr)
        return 2
    claude_skills.mkdir(parents=True, exist_ok=True)

    return run_sync(
        agents_skills,
        claude_skills,
        check_only=args.check,
        state_path=state_path,
        force_mirror=args.force_mirror,
    )


if __name__ == "__main__":
    raise SystemExit(main())
