# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 6, §10.2, point O)
# Purpose: R6 review probe. Does revision 6's prefix-collision check (normalized_path, component boundary, no
# case-folding) catch every path that reaches a file under a legacy_manuscript_root? Scratch files only, under a
# temporary directory; no ARS store, no ledger, no real repository path is touched.
"""Probe for the review of WP9.4 design note revision 6 (R6-M1, R6-m1).

Run from the worktree root:
    uv run --env-file .env python docs/plans/agentic-research-system/reviews/wp9-4-note-r6-review-artifacts/r6_prefix_probe.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.legacy.preparers import _same_physical_identity
from research_system.legacy.reader import LegacyReader, ReadRefused, canonical_target, handle_bound_read
from research_system.legacy.replay.reducers import _registration_conflicts

ROOT_PATH = "papers/P01-A-JRSSA/"
EXACT = "papers/P01-A-JRSSA/_project.md"
VARIANT = "papers/p01-a-jrssa/_project.md"


def note_prefix_rule(state: dict[str, Any], record: dict[str, Any]) -> bool:
    """Revision 6, section 10.2, as written: strict prefix on normalized_path at a component boundary, no folding."""
    mine = record["normalized_path"]
    for other in state["records"]["legacy_path_registration"].values():
        theirs = other["normalized_path"]
        if other["role"] == "legacy_manuscript_root" and mine != theirs and mine.startswith(theirs):
            return True
        if record["role"] == "legacy_manuscript_root" and theirs != mine and theirs.startswith(mine):
            return True
    return False


def target_prefix_rule(state: dict[str, Any], record: dict[str, Any]) -> bool:
    """The alternative: strict prefix on os.path.normcase(canonical_target) at a component boundary."""

    def norm(physical: dict[str, Any]) -> str:
        return os.path.normcase(physical["canonical_target"]).replace("\\", "/").rstrip("/") + "/"

    mine = norm(record["physical_identity"])
    for other in state["records"]["legacy_path_registration"].values():
        theirs = norm(other["physical_identity"])
        if other["role"] == "legacy_manuscript_root" and mine != theirs and mine.startswith(theirs):
            return True
        if record["role"] == "legacy_manuscript_root" and theirs != mine and theirs.startswith(mine):
            return True
    return False


def registration(path: str, role: str, physical: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "root_kind": "repository_root",
        "root_id": "tdl",
        "normalized_path": path,
        "role": role,
        "source_identity_kind": kind,
        "physical_identity": physical,
    }


def main() -> int:
    print(f"platform={sys.platform} python={sys.version.split()[0]}")
    at = datetime.now(UTC)
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp).resolve()
        root_dir = repo / "papers" / "P01-A-JRSSA"
        root_dir.mkdir(parents=True)
        (root_dir / "_project.md").write_bytes(b"# P01-A\n")
        git = ["git", "-C", str(repo)]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "."], check=True)
        subprocess.run(
            [*git, "-c", "user.name=p", "-c", "user.email=p@example.invalid", "commit", "-qm", "x"], check=True
        )
        head = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

        st = os.stat(root_dir)
        root_physical = {
            "canonical_target": canonical_target(root_dir.resolve()),
            "reparse_chain": [],
            "volume_serial_number": str(st.st_dev),
            "stable_file_id": str(st.st_ino),
            "link_count": int(st.st_nlink),
            "case_aliases": [],
            "unicode_aliases": [],
            "short_name_aliases": [],
        }
        root_reg = registration(ROOT_PATH, "legacy_manuscript_root", root_physical, "git_tracked")
        state = {"records": {"legacy_path_registration": {"root": root_reg}}, "proposals": {}}

        print("\n[1] Handle-bound read (LR-003's preparer read) of case variants of a member path")
        reads: dict[str, dict[str, Any]] = {}
        for path in (EXACT, VARIANT, "PAPERS/P01-A-JRSSA/_project.md"):
            try:
                _, physical, key = handle_bound_read(repo, path)
                reads[path] = physical
                print(f"  {path!r}: READ, canonical_target ends {physical['canonical_target'][-32:]!r}, id={key}")
            except ReadRefused as exc:
                print(f"  {path!r}: REFUSED ({exc})")

        print("\n[2] LegacyReader.read of the case variant, by source kind")
        reader = LegacyReader(repository_root=repo, git_head=head)
        for kind in ("git_tracked", "untracked_file"):
            try:
                reader.read({"role": "legacy_coordination", "source_identity_kind": kind, "normalized_path": VARIANT})
                print(f"  kind={kind}: READ")
            except ReadRefused as exc:
                print(f"  kind={kind}: REFUSED ({exc})")

        if VARIANT not in reads:
            print("\nCase variant refused by the read; the gap does not exist on this platform.")
            return 0

        member = registration(VARIANT, "legacy_coordination", reads[VARIANT], "untracked_file")
        print("\n[3] A registration of the case variant, with the root recorded")
        print(f"  _registration_conflicts (today's equality): {_registration_conflicts(state, member, at)}")
        print(f"  revision 6's normalized_path prefix rule:  {note_prefix_rule(state, member)}")
        print(f"  canonical_target prefix rule (normcase):   {target_prefix_rule(state, member)}")
        exact = registration(EXACT, "legacy_coordination", reads[EXACT], "git_tracked")
        print("  control, exact-case member path:")
        print(
            f"    revision 6's rule: {note_prefix_rule(state, exact)}; target rule: {target_prefix_rule(state, exact)}"
        )
        sibling = repo / "papers" / "P01-A-JRSSA-old"
        sibling.mkdir()
        (sibling / "x.md").write_bytes(b"x\n")
        _, sib_phys, _ = handle_bound_read(repo, "papers/P01-A-JRSSA-old/x.md")
        sib = registration("papers/P01-A-JRSSA-old/x.md", "legacy_coordination", sib_phys, "untracked_file")
        print("  control, component boundary (papers/P01-A-JRSSA-old/x.md):")
        print(f"    revision 6's rule: {note_prefix_rule(state, sib)}; target rule: {target_prefix_rule(state, sib)}")
        reverse_state = {"records": {"legacy_path_registration": {"m": member}}, "proposals": {}}
        print("  reverse direction (member recorded first, then the root):")
        print(
            f"    revision 6's rule: {note_prefix_rule(reverse_state, root_reg)}; "
            f"target rule: {target_prefix_rule(reverse_state, root_reg)}"
        )

        print("\n[4] The physical-identity half: a declared canonical_target in another case")
        declared = dict(reads[VARIANT])
        declared["canonical_target"] = declared["canonical_target"].upper()
        print(
            f"  preparer _same_physical_identity(observed, declared upper-cased): "
            f"{_same_physical_identity(reads[VARIANT], declared)}"
        )
        first = registration(EXACT, "legacy_coordination", reads[EXACT], "git_tracked")
        s2 = {"records": {"legacy_path_registration": {"first": first}}, "proposals": {}}
        second = registration(VARIANT, "legacy_task_log", declared, "untracked_file")
        print(
            f"  one file registered twice (path case differs, declared target case differs): "
            f"_registration_conflicts={_registration_conflicts(s2, second, at)}"
        )
        third = registration(VARIANT, "legacy_task_log", reads[VARIANT], "untracked_file")
        print(
            f"  control, declared target as observed: _registration_conflicts={_registration_conflicts(s2, third, at)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
