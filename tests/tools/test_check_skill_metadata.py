# Research context: docs/plans/skills/2026-07-02-skill-suite-ars-readiness-plan.md
# Purpose: TDD tests for tools/check_skill_metadata.py — cover missing metadata block,
#   bad enum values, bad semver, oversize-warning (not error), and clean pass.
"""Tests for the skill metadata checker tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import check_skill_metadata as csm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(tmp_path: Path, content: str) -> Path:
    """Create a SKILL.md in a fresh skill directory inside tmp_path."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


_VALID = """\
---
name: test-skill
description: A test skill for unit testing purposes only.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---

# Test Skill

Some body text.
"""


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


def test_parse_frontmatter_valid() -> None:
    fm, body = csm.parse_frontmatter(_VALID)
    assert fm["name"] == "test-skill"
    assert isinstance(fm["metadata"], dict)
    assert "# Test Skill" in body


def test_parse_frontmatter_no_delimiter() -> None:
    with pytest.raises(ValueError, match="opening"):
        csm.parse_frontmatter("# No frontmatter here\n")


def test_parse_frontmatter_no_closing_delimiter() -> None:
    with pytest.raises(ValueError, match="closing"):
        csm.parse_frontmatter("---\nname: x\n")


# ---------------------------------------------------------------------------
# validate_skill — clean pass
# ---------------------------------------------------------------------------


def test_clean_pass(tmp_path: Path) -> None:
    skill_dir = _write_skill(tmp_path, _VALID)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert violations == []


def test_clean_pass_with_lanes_and_roles(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: A test skill.
metadata:
  version: "2.3.1"
  tier: core
  lanes:
    - topology
    - stochastic-null
  roles:
    - implementer
    - verifier
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    assert csm.validate_skill(skill_dir, "test-skill") == []


# ---------------------------------------------------------------------------
# validate_skill — missing metadata block
# ---------------------------------------------------------------------------


def test_missing_metadata_block(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: A test skill without a metadata block.
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("metadata" in v for v in violations)


# ---------------------------------------------------------------------------
# validate_skill — bad enum values
# ---------------------------------------------------------------------------


def test_bad_tier(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: Bad tier.
metadata:
  version: "1.0.0"
  tier: invalid-tier
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("tier" in v for v in violations)


def test_bad_lane(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: Bad lane.
metadata:
  version: "1.0.0"
  tier: domain
  lanes:
    - not-a-real-lane
  roles:
    - orchestrator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("lanes" in v for v in violations)


def test_bad_role(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: Bad role.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - not-a-real-role
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("roles" in v for v in violations)


def test_bad_runtime(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: Bad runtime.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: claude-only
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("runtime" in v for v in violations)


# ---------------------------------------------------------------------------
# validate_skill — bad semver
# ---------------------------------------------------------------------------


def test_bad_semver_string(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: Bad semver.
metadata:
  version: "not-a-version"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("version" in v for v in violations)


def test_bad_semver_two_parts(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: Two-part version.
metadata:
  version: "1.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("version" in v for v in violations)


def test_valid_semver_with_patch(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
description: Valid semver 0.9.3.
metadata:
  version: "0.9.3"
  tier: optional
  lanes: []
  roles:
    - operator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    assert csm.validate_skill(skill_dir, "test-skill") == []


# ---------------------------------------------------------------------------
# validate_skill — oversize warning (not error)
# ---------------------------------------------------------------------------


def test_oversize_lines_warns_not_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    long_body = "\n".join(f"line {i}" for i in range(210))
    content = f"""\
---
name: test-skill
description: Oversize by lines.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---

# Body

{long_body}
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert violations == [], "oversize lines must warn, not fail"
    captured = capsys.readouterr()
    assert "WARN" in captured.out


def test_oversize_words_warns_not_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    many_words = " ".join(f"word{i}" for i in range(1700))
    content = f"""\
---
name: test-skill
description: Oversize by words.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---

{many_words}
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert violations == [], "oversize words must warn, not fail"
    captured = capsys.readouterr()
    assert "WARN" in captured.out


# ---------------------------------------------------------------------------
# validate_skill — description length
# ---------------------------------------------------------------------------


def test_description_too_long(tmp_path: Path) -> None:
    long_desc = "A" * 1025
    content = f"""\
---
name: test-skill
description: "{long_desc}"
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("description" in v for v in violations)


# ---------------------------------------------------------------------------
# validate_skill — missing required frontmatter keys
# ---------------------------------------------------------------------------


def test_missing_name(tmp_path: Path) -> None:
    content = """\
---
description: A test skill.
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("name" in v for v in violations)


def test_missing_description(tmp_path: Path) -> None:
    content = """\
---
name: test-skill
metadata:
  version: "1.0.0"
  tier: domain
  lanes: []
  roles:
    - orchestrator
  runtime: agnostic
---
body
"""
    skill_dir = _write_skill(tmp_path, content)
    violations = csm.validate_skill(skill_dir, "test-skill")
    assert any("description" in v for v in violations)


# ---------------------------------------------------------------------------
# validate_skill — missing SKILL.md
# ---------------------------------------------------------------------------


def test_missing_skill_md(tmp_path: Path) -> None:
    skill_dir = tmp_path / "empty-skill"
    skill_dir.mkdir()
    violations = csm.validate_skill(skill_dir, "empty-skill")
    assert any("SKILL.md" in v for v in violations)
