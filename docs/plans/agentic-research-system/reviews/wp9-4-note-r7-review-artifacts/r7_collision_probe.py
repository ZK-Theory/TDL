# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 7, §10.2, point O)
# Purpose: R7 review probe. Revision 7's three LR-003 collision checks (case-folded path prefix, case-folded
# physical-target prefix, (volume_serial_number, stable_file_id) equality), written from the note's text, run on
# scratch directories under a temporary directory with in-memory replay state. No ARS store, no ledger, no real
# repository path is read or written except the code under test, imported read-only.
"""Probe for the review of WP9.4 design note revision 7 (R6-M1 and R6-M2's fixes).

Run from the worktree root:
    uv run --env-file .env python docs/plans/agentic-research-system/reviews/wp9-4-note-r7-review-artifacts/r7_collision_probe.py
"""

from __future__ import annotations

import ntpath
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from research_system.legacy.preparers import _same_physical_identity
from research_system.legacy.reader import ReadRefused, canonical_target, handle_bound_read
from research_system.errors import IntegrityError
from research_system.legacy.replay.reducers import _check_registration, _registration_conflicts, proposal_open
from research_system.store.anchor import open_registered_root_anchor

ROOT = "papers/P01-A-JRSSA/"
ROOT_ROLE = "legacy_manuscript_root"


# ---------------------------------------------------------------------------------------------------------------
# Revision 7's rules, as §10.2 writes them.
# ---------------------------------------------------------------------------------------------------------------


def _fold_target(target: str, boundary: bool) -> str:
    folded = target.replace("\\", "/").casefold().rstrip("/")
    return folded + "/" if boundary else folded


def _records(state: dict[str, Any], at: datetime) -> list[dict[str, Any]]:
    recorded = list(state["records"].get("legacy_path_registration", {}).values())
    proposed = [
        p["record"]
        for p in state["proposals"].values()
        if p["kind"] == "legacy_path_registration" and proposal_open(p, at)
    ]
    return recorded + proposed


def path_half(state: dict[str, Any], record: dict[str, Any], at: datetime) -> bool:
    """Folded normalized_path, component boundary, within one (root_kind, root_id), root-scoped, both directions."""
    mine = record["normalized_path"].casefold()
    for other in _records(state, at):
        if (other["root_kind"], other["root_id"]) != (record["root_kind"], record["root_id"]):
            continue
        theirs = other["normalized_path"].casefold()
        if other["role"] == ROOT_ROLE and mine != theirs and mine.startswith(theirs):
            return True
        if record["role"] == ROOT_ROLE and theirs != mine and theirs.startswith(mine):
            return True
    return False


def target_half(state: dict[str, Any], record: dict[str, Any], at: datetime, *, boundary: bool = True) -> bool:
    """Folded canonical_target with '/' separators; strictly under, both directions, root-scoped.

    The note does not say "component boundary" for this half; ``boundary=False`` is the plain string reading.
    """
    mine = _fold_target(record["physical_identity"]["canonical_target"], boundary)
    for other in _records(state, at):
        theirs = _fold_target(other["physical_identity"]["canonical_target"], boundary)
        if other["role"] == ROOT_ROLE and mine != theirs and mine.startswith(theirs):
            return True
        if record["role"] == ROOT_ROLE and theirs != mine and theirs.startswith(mine):
            return True
    return False


def equality_half(state: dict[str, Any], record: dict[str, Any], at: datetime, *, path_part: bool = True) -> bool:
    """Every role: (volume_serial_number, stable_file_id) equal, or the folded normalized_path equal in one root."""
    mine = record["physical_identity"]
    for other in _records(state, at):
        theirs = other["physical_identity"]
        if (mine["volume_serial_number"], mine["stable_file_id"]) == (
            theirs["volume_serial_number"],
            theirs["stable_file_id"],
        ):
            return True
        if path_part and (other["root_kind"], other["root_id"], other["normalized_path"].casefold()) == (
            record["root_kind"],
            record["root_id"],
            record["normalized_path"].casefold(),
        ):
            return True
    return False


def wrong_equality_folded_target(state: dict[str, Any], record: dict[str, Any], at: datetime) -> bool:
    """A plausible WRONG implementation: today's check with the target case-folded; no volume, target still trusted."""
    mine = record["physical_identity"]
    for other in _records(state, at):
        theirs = other["physical_identity"]
        if (mine["canonical_target"].casefold(), mine["stable_file_id"]) == (
            theirs["canonical_target"].casefold(),
            theirs["stable_file_id"],
        ):
            return True
    return False


def rev7(state: dict[str, Any], record: dict[str, Any], at: datetime) -> dict[str, bool]:
    return {
        "path": path_half(state, record, at),
        "target": target_half(state, record, at),
        "target_plain_string": target_half(state, record, at, boundary=False),
        "equality": equality_half(state, record, at),
        "today": _registration_conflicts(state, record, at),
    }


# ---------------------------------------------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------------------------------------------


def reg(
    path: str,
    role: str,
    physical: dict[str, Any],
    kind: str,
    *,
    root_kind: str = "repository_root",
    root_id: str = "tdl",
) -> dict[str, Any]:
    return {
        "root_kind": root_kind,
        "root_id": root_id,
        "normalized_path": path,
        "role": role,
        "source_identity_kind": kind,
        "physical_identity": physical,
    }


def state_of(*records: dict[str, Any], proposed: tuple[dict[str, Any], ...] = ()) -> dict[str, Any]:
    return {
        "records": {"legacy_path_registration": {f"r{i}": r for i, r in enumerate(records)}},
        "proposals": {
            f"p{i}": {
                "kind": "legacy_path_registration",
                "record": r,
                "recorded": False,
                "lapse_at": datetime(2099, 1, 1, tzinfo=UTC),
            }
            for i, r in enumerate(proposed)
        },
    }


def dir_identity(path: Path) -> dict[str, Any]:
    """The note's directory identity: from the bound anchor, in the reader's decimal-string encoding."""
    anchor = open_registered_root_anchor(path, delete_protect=False)
    try:
        identity = anchor.identity
        final = anchor.final_path
    finally:
        anchor.close()
    return {
        "canonical_target": canonical_target(final),
        "reparse_chain": [],
        "volume_serial_number": str(identity.volume_or_device),
        "stable_file_id": str(int.from_bytes(identity.file_id, "little")),
        "link_count": int(os.stat(path).st_nlink),
        "case_aliases": [],
        "unicode_aliases": [],
        "short_name_aliases": [],
        "_scheme": identity.scheme,
    }


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def make_repo(base: Path) -> Path:
    repo = base
    for rel, data in {
        "papers/P01-A-JRSSA/_project.md": b"# P01-A\n",
        "papers/P01-A-JRSSA/drafts/a.tex": b"x\n",
        "papers/P01-A-JRSSA-old/x.md": b"old\n",
        "papers/P01-B-JRSSB/_project.md": b"# P01-B\n",
    }.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_bytes(data)
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=p", "-c", "user.email=p@example.invalid", "commit", "-qm", "x")
    return repo


def show(label: str, result: dict[str, bool]) -> None:
    print(f"  {label}: " + ", ".join(f"{k}={v}" for k, v in result.items()))


def main() -> int:
    print(f"platform={sys.platform} python={sys.version.split()[0]}")
    at = datetime(2026, 11, 20, tzinfo=UTC)
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp).resolve()
        repo = make_repo(base / "checkout-a")
        vault = base / "vault"
        (vault / "papers" / "P01-A-JRSSA").mkdir(parents=True)
        (vault / "papers" / "P01-A-JRSSA" / "note.md").write_bytes(b"vault note\n")
        (vault / "04-Methods").mkdir()
        (vault / "04-Methods" / "Computational-Log.md").write_bytes(b"log\n")

        print("\n[0] The directory identity's source (R6-i1)")
        root_dir = repo / "papers" / "P01-A-JRSSA"
        try:
            fd = os.open(root_dir, os.O_RDONLY)
            os.close(fd)
            print("  os.open on the directory: OPENED")
        except OSError as exc:
            print(f"  os.open on the directory: REFUSED ({type(exc).__name__}: {exc.strerror})")
        ident = dir_identity(root_dir)
        st = os.stat(root_dir)
        print(f"  anchor scheme={ident['_scheme']}")
        print(
            f"  anchor vol == st_dev: {ident['volume_serial_number'] == str(st.st_dev)}; "
            f"int.from_bytes(file_id,'little') == st_ino: {ident['stable_file_id'] == str(st.st_ino)}"
        )
        nlink_before = os.stat(root_dir).st_nlink
        (root_dir / "newsub").mkdir()
        (root_dir / "newfile.md").write_bytes(b"n\n")
        nlink_after = os.stat(root_dir).st_nlink
        (root_dir / "newfile.md").unlink()
        (root_dir / "newsub").rmdir()
        print(f"  directory st_nlink before/after adding a subdirectory and a file: {nlink_before}/{nlink_after}")
        ident.pop("_scheme")
        root_reg = reg(ROOT, ROOT_ROLE, ident, "git_tracked")

        print("\n[1] Case variants of a member path: what LR-003's preparer read admits")
        reads: dict[str, dict[str, Any]] = {}
        for path in (
            "papers/P01-A-JRSSA/_project.md",
            "papers/p01-a-jrssa/_project.md",
            "PAPERS/P01-A-JRSSA/_PROJECT.MD",
            "papers/P01-a-JrSsA/drafts/A.TEX",
            "papers/P01-A-JRSSA-old/x.md",
        ):
            try:
                _, physical, key = handle_bound_read(repo, path)
                reads[path] = physical
                print(f"  {path!r}: READ; canonical_target tail {physical['canonical_target'][-34:]!r}")
            except ReadRefused as exc:
                print(f"  {path!r}: REFUSED ({exc})")

        print("\n[2] Root recorded first; each member proposed (rev 7 rules; 'today' = _registration_conflicts)")
        for path, physical in reads.items():
            show(path, rev7(state_of(root_reg), reg(path, "legacy_coordination", physical, "untracked_file"), at))
        print("  reverse direction: member recorded (or in an open proposal) first, then the root proposed")
        for path, physical in reads.items():
            member = reg(path, "legacy_coordination", physical, "untracked_file")
            show(f"{path} recorded", rev7(state_of(member), root_reg, at))
            show(f"{path} proposed", rev7(state_of(proposed=(member,)), root_reg, at))

        print("\n[3] The vault_root control: a vault path that begins papers/P01-A-JRSSA/")
        _, vphys, _ = handle_bound_read(vault, "papers/P01-A-JRSSA/note.md")
        vreg = reg(
            "papers/P01-A-JRSSA/note.md",
            "legacy_coordination",
            vphys,
            "vault_file",
            root_kind="vault_root",
            root_id="tda",
        )
        show("vault note, root recorded", rev7(state_of(root_reg), vreg, at))
        show("root proposed, vault note recorded", rev7(state_of(vreg), root_reg, at))
        _, lphys, _ = handle_bound_read(vault, "04-Methods/Computational-Log.md")
        lreg = reg(
            "04-Methods/Computational-Log.md",
            "legacy_decision_log_entry",
            lphys,
            "vault_file",
            root_kind="vault_root",
            root_id="tda",
        )
        show("legacy_decision_log_entry beside the root and the vault note", rev7(state_of(root_reg, vreg), lreg, at))

        print("\n[4] root_id is a free string: a variant under another root_id, same binding")
        variant = reads["papers/p01-a-jrssa/_project.md"]
        show(
            "root_id='tdl-2'",
            rev7(
                state_of(root_reg),
                reg(
                    "papers/p01-a-jrssa/_project.md", "legacy_coordination", variant, "untracked_file", root_id="tdl-2"
                ),
                at,
            ),
        )

        print("\n[5] The store's binding moves to another checkout (AdvanceStoreBinding / RepairStoreBinding)")
        repo_b = base / "checkout-b"
        shutil.copytree(repo, repo_b)
        _, bphys, _ = handle_bound_read(repo_b, "papers/P01-A-JRSSA/_project.md")
        for rid in ("tdl", "tdl-2"):
            show(
                f"root registered at checkout A; _project.md registered at checkout B, root_id={rid!r}",
                rev7(
                    state_of(root_reg),
                    reg("papers/P01-A-JRSSA/_project.md", "legacy_coordination", bphys, "git_tracked", root_id=rid),
                    at,
                ),
            )

        print("\n[6] One file registered twice (R6-M2): the equality half and the section 15 test")
        exact = reads["papers/P01-A-JRSSA/_project.md"]
        declared = dict(variant)
        declared["canonical_target"] = declared["canonical_target"].upper()
        print(f"  preparer admits the upper-cased declared target: {_same_physical_identity(variant, declared)}")
        first = reg("papers/P01-A-JRSSA/_project.md", "legacy_coordination", exact, "git_tracked")
        second = reg("papers/p01-a-jrssa/_project.md", "legacy_task_log", declared, "untracked_file")
        s = state_of(first)
        print(f"  today's _registration_conflicts: {_registration_conflicts(s, second, at)}")
        print(f"  rev 7 equality half, full: {equality_half(s, second, at)}")
        print(f"  rev 7 equality half, path part disabled: {equality_half(s, second, at, path_part=False)}")
        print(
            f"  WRONG impl (folded target + file id, no volume), path disabled: "
            f"{wrong_equality_folded_target(s, second, at)}  <- section 15's test cannot tell it from the decided one"
        )
        forged = dict(exact)
        forged["canonical_target"] = "C:/elsewhere/unrelated/name.md"
        other = reg("unrelated/name.md", "legacy_task_log", forged, "untracked_file")
        print("  discriminating fixture: same (volume, file id), unrelated path and target, no path half needed:")
        print(
            f"    decided impl: {equality_half(s, other, at)}; wrong impl: {wrong_equality_folded_target(s, other, at)}"
        )
        moved = dict(exact)
        moved["volume_serial_number"] = str(int(exact["volume_serial_number"]) + 1)
        same_id_other_vol = reg("unrelated/other.md", "legacy_task_log", moved, "untracked_file")
        print("  volume control: same file id, another volume (two distinct files):")
        print(
            f"    decided impl: {equality_half(s, same_id_other_vol, at)}; "
            f"today: {_registration_conflicts(s, reg('unrelated/other.md', 'legacy_task_log', dict(moved, canonical_target=exact['canonical_target']), 'untracked_file'), at)}"
        )
        control = reg(
            "papers/P01-B-JRSSB/_project.md",
            "legacy_coordination",
            handle_bound_read(repo, "papers/P01-B-JRSSB/_project.md")[1],
            "git_tracked",
        )
        print(f"  control, two distinct files: {equality_half(s, control, at)}")

        print("\n[7] File-ID reuse after delete (false refusal of a later registration?)")
        scratch = base / "reuse"
        scratch.mkdir()
        seen: set[int] = set()
        reused = 0
        for i in range(3000):
            f = scratch / f"f{i}.md"
            f.write_bytes(b"x")
            ino = os.stat(f).st_ino
            reused += ino in seen
            seen.add(ino)
            f.unlink()
        print(f"  3000 create/delete cycles: distinct st_ino={len(seen)}, reuses={reused}")
        g = scratch / "rewrite.md"
        g.write_bytes(b"a")
        before = os.stat(g).st_ino
        tmpf = scratch / "rewrite.md.tmp"
        tmpf.write_bytes(b"b")
        os.replace(tmpf, g)
        print(f"  atomic replace (as Obsidian and git checkout write) changes st_ino: {before != os.stat(g).st_ino}")

        print("\n[8] str.casefold against what NTFS and os.path.normcase treat as equal")
        names = {
            "sharp s": ("stra\u00dfe.md", "strasse.md"),
            "Kelvin sign": ("\u212a.md", "k.md"),
            "dotless i": ("\u0131.md", "i.md"),
            "long s": ("\u017f.md", "s.md"),
            "dotted capital I": ("\u0130.md", "i.md"),
            "Greek final sigma": ("\u03c2.md", "\u03c3.md"),
            "ASCII case": ("A.md", "a.md"),
            "NFC/NFD e-acute": ("\u00e9.md", "e\u0301.md"),
        }
        print("  pair: NTFS_same, casefold_equal, normcase_equal, lower_equal")
        for label, (a, b) in names.items():
            d = base / f"cmp-{abs(hash(label))}"
            d.mkdir()
            (d / a).write_bytes(b"1")
            try:
                with open(d / b, "xb") as h:
                    h.write(b"2")
                ntfs_same = False
            except FileExistsError:
                ntfs_same = True
            print(
                f"  {label}: {ntfs_same}, {a.casefold() == b.casefold()}, "
                f"{ntpath.normcase(a) == ntpath.normcase(b)}, {a.lower() == b.lower()}"
            )
        print("  can a parent spelled with an NTFS-equal, casefold-equal but normcase-unequal name pass the read?")
        try:
            handle_bound_read(repo, "paper\u017f/P01-A-JRSSA/_project.md")
            print("    'paperſ/...': READ")
        except ReadRefused as exc:
            print(f"    'paperſ/...': REFUSED ({exc})")
        bmp_fold_wider = sum(
            1 for cp in range(0x10000) if not (0xD800 <= cp <= 0xDFFF) and chr(cp).casefold() != chr(cp).lower()
        )
        print(f"  BMP code points where casefold != lower: {bmp_fold_wider}")
        print(f"  unicodedata version: {unicodedata.unidata_version}")

        print("\n[9] The other prefix test at LR-003: the legacy projection directory (_check_registration)")
        projection = repo / ".research-system" / "projections" / "legacy"
        projection.mkdir(parents=True)
        (projection / "p.json").write_bytes(b"{}")
        for path in (".research-system/projections/legacy/p.json", ".Research-System/Projections/Legacy/p.json"):
            try:
                _, pphys, _ = handle_bound_read(repo, path)
                read = "READ"
            except ReadRefused as exc:
                print(f"  {path}: read REFUSED ({exc})")
                continue
            record = reg(path, "legacy_coordination", pphys, "untracked_file")
            try:
                _check_registration(state_of(), record, at)
                verdict = "replay ADMITS a legacy role here"
            except IntegrityError as exc:
                verdict = f"replay refuses ({exc})"
            print(f"  {path}: {read}; {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
