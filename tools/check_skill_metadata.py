#!/usr/bin/env python3
# Research context: docs/plans/skills/2026-07-02-skill-suite-ars-readiness-plan.md
# Purpose: Validate that every SYNC_SKILLS skill carries the required machine-readable
#   metadata frontmatter block (version, tier, lanes, roles, runtime); warns on
#   SKILL.md files exceeding 200 lines or 1600 words.
"""Skill metadata validator for the dual-tree skill suite.

Validates that every skill in SYNC_SKILLS carries a well-formed ``metadata:``
frontmatter block.  Prints WARN (not error) when a SKILL.md exceeds 200 lines
or 1600 words (W3 §13.2 R2/R3 context-ceiling guard).

Exit codes:
    0 — all metadata blocks valid (warnings may be present).
    1 — one or more metadata violations found.
    2 — framework error (missing trees, bad invocation).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Vocabulary tables (schema source: SKL-1 brief)
# ---------------------------------------------------------------------------

VALID_TIERS: frozenset[str] = frozenset({"core", "specialist", "optional", "domain"})
VALID_LANES: frozenset[str] = frozenset(
    {
        "topology",
        "stochastic-null",
        "statistical-panel",
        "representation",
        "output-provenance",
        "paper-claim",
    }
)
VALID_ROLES: frozenset[str] = frozenset(
    {
        "orchestrator",
        "manager",
        "implementer",
        "verifier",
        "claim-reviewer",
        "operator",
    }
)

SEMVER_RE: re.Pattern[str] = re.compile(r"^\d+\.\d+\.\d+$")

OVERSIZE_LINES: int = 200
OVERSIZE_WORDS: int = 1600
MAX_DESC_CHARS: int = 1024


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Extract and parse the YAML frontmatter block from a Markdown file.

    Args:
        text: Full file content, expected to start with ``---``.

    Returns:
        Tuple of (parsed frontmatter dict, body text after the closing ``---``).

    Raises:
        ValueError: If opening or closing ``---`` delimiters are absent, or the
            YAML inside them is invalid.
    """
    if not text.startswith("---"):
        raise ValueError("No opening frontmatter delimiter '---'")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("No closing frontmatter delimiter '---'")
    yaml_block = text[3:end].strip()
    body = text[end + 4 :]
    try:
        fm = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc
    return fm, body


# ---------------------------------------------------------------------------
# Per-skill validation
# ---------------------------------------------------------------------------


def validate_skill(skill_dir: Path, name: str) -> list[str]:
    """Validate the metadata frontmatter of a single skill directory.

    Prints WARN lines to stdout for oversize SKILL.md files (>200 lines or
    >1600 words).  These warnings are NOT included in the returned violations
    list and do not cause a non-zero exit.

    Args:
        skill_dir: Path to the skill directory containing SKILL.md.
        name: Canonical skill name (from SYNC_SKILLS manifest).

    Returns:
        List of violation description strings.  Empty list means the skill
        passed all checks.
    """
    skill_md = skill_dir / "SKILL.md"
    violations: list[str] = []

    if not skill_md.exists():
        return [f"{name}: SKILL.md not found at {skill_md}"]

    text = skill_md.read_text(encoding="utf-8", errors="replace")

    # Oversize checks — WARN only, never a violation.
    lines = text.splitlines()
    words = len(text.split())
    if len(lines) > OVERSIZE_LINES:
        print(f"  WARN  {name}: SKILL.md has {len(lines)} lines (>{OVERSIZE_LINES})")
    if words > OVERSIZE_WORDS:
        print(f"  WARN  {name}: SKILL.md has {words} words (>{OVERSIZE_WORDS})")

    # Parse frontmatter.
    try:
        fm, _ = parse_frontmatter(text)
    except ValueError as exc:
        return [f"{name}: frontmatter parse error: {exc}"]

    if not isinstance(fm, dict):
        return [f"{name}: frontmatter is not a YAML mapping"]

    # Required top-level fields: name and description.
    if not fm.get("name"):
        violations.append(f"{name}: frontmatter missing required 'name' field")
    desc = fm.get("description", "")
    if not desc:
        violations.append(f"{name}: frontmatter missing required 'description' field")
    elif len(desc) > MAX_DESC_CHARS:
        violations.append(f"{name}: description exceeds {MAX_DESC_CHARS} chars ({len(desc)} chars)")

    # metadata block presence.
    meta = fm.get("metadata")
    if meta is None:
        violations.append(f"{name}: missing required 'metadata:' block")
        return violations

    if not isinstance(meta, dict):
        violations.append(f"{name}: 'metadata' must be a YAML mapping, got {type(meta).__name__}")
        return violations

    # version — required semver string.
    version = meta.get("version", "")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        violations.append(f"{name}: metadata.version {version!r} is not a valid semver string (expected x.y.z)")

    # tier — required, from VALID_TIERS.
    tier = meta.get("tier", "")
    if tier not in VALID_TIERS:
        violations.append(f"{name}: metadata.tier {tier!r} not in allowed set {sorted(VALID_TIERS)}")

    # lanes — required list, each element from VALID_LANES.
    lanes = meta.get("lanes")
    if lanes is None:
        violations.append(f"{name}: metadata.lanes is required (use [] for empty)")
    elif not isinstance(lanes, list):
        violations.append(f"{name}: metadata.lanes must be a list, got {type(lanes).__name__}")
    else:
        for lane in lanes:
            if lane not in VALID_LANES:
                violations.append(
                    f"{name}: metadata.lanes contains unknown value {lane!r} (valid: {sorted(VALID_LANES)})"
                )

    # roles — required list, each element from VALID_ROLES.
    roles = meta.get("roles")
    if roles is None:
        violations.append(f"{name}: metadata.roles is required (use [] for empty)")
    elif not isinstance(roles, list):
        violations.append(f"{name}: metadata.roles must be a list, got {type(roles).__name__}")
    else:
        for role in roles:
            if role not in VALID_ROLES:
                violations.append(
                    f"{name}: metadata.roles contains unknown value {role!r} (valid: {sorted(VALID_ROLES)})"
                )

    # runtime — must be exactly "agnostic" for all SYNC_SKILLS.
    runtime = meta.get("runtime", "")
    if runtime != "agnostic":
        violations.append(f"{name}: metadata.runtime must be 'agnostic' for SYNC_SKILLS skills (got {runtime!r})")

    return violations


# ---------------------------------------------------------------------------
# Repo root resolution and SYNC_SKILLS import
# ---------------------------------------------------------------------------


def _find_repo_root() -> Path:
    """Walk up from this file until a .git entry is found."""
    here = Path(__file__).resolve().parent
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"No .git directory found above {here}")


# Ensure the repo root is in sys.path so SYNC_SKILLS can be imported from the
# sync tool without modifying that file.  We add it here (module level) so the
# import below works both when running the checker directly and when imported by
# tests (pytest adds the repo root itself, making this a no-op in that context).
_REPO_ROOT: Path = _find_repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.sync_agent_skills import SYNC_SKILLS  # noqa: E402


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the metadata check over the full SYNC_SKILLS roster.

    Args:
        argv: Command-line arguments (unused; reserved for future flags).

    Returns:
        0 if all skills pass, 1 on violations, 2 on framework error.
    """
    agents_skills = _REPO_ROOT / ".agents" / "skills"
    if not agents_skills.is_dir():
        print(f"ERROR: {agents_skills} not found", file=sys.stderr)
        return 2

    all_violations: list[str] = []
    for name in sorted(SYNC_SKILLS):
        skill_dir = agents_skills / name
        if not skill_dir.is_dir():
            print(f"  PLANNED  {name} (in manifest, not yet authored in .agents/)")
            continue
        violations = validate_skill(skill_dir, name)
        if violations:
            for v in violations:
                print(f"  FAIL  {v}")
            all_violations.extend(violations)
        else:
            print(f"  OK    {name}")

    if all_violations:
        print(f"\n{len(all_violations)} violation(s) found.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
