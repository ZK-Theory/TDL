#!/usr/bin/env python3
"""Reject CRLF on the repository's declared canonical byte surface.

Research context: docs/plans/agentic-research-system/handoffs/34-observation-backlog-handoff-2026-08-25.md
Purpose: commit-time enforcement of `canonical_byte_surface: git_blob_utf8_lf`, the surface
`.gitattributes` declares and the WP6.x contract validators hash against.

Why this exists as a *separate* check from `.gitattributes`
-----------------------------------------------------------
`* text=auto eol=lf` makes git normalise CRLF away when it writes the index blob. That fixes
the committed bytes but reports nothing: the authoring tool that emitted CRLF keeps emitting
it, and the working tree the contract validators hash stays wrong. On 2026-08-13 twelve
production modules were committed as CRLF after a `pathlib.Path.write_text` extraction on
Windows; `ruff check`, `ruff format`, the pre-commit framework and all 103 contract
validators passed, twice, across two commits. The only signal was `git diff --check`, which
was wired into no gate. Normalisation alone would have hidden that incident rather than
surfaced it.

So both sides are checked:

* **working tree** — the surface the validators read and the surface the author actually
  produced. A CRLF here fails even when git would normalise it on the way in.
* **index blob** — the committed bytes. Normally already LF, but a path carrying `-text`,
  or an add performed with `--no-renormalize`, can carry CRLF straight through.

Detection counts ``b"\\r\\n"`` byte pairs. It does not use `grep`: during the original
diagnosis ``grep -c $'\\r$'`` under Git Bash gave the wrong answer in *both* directions, and
the question was only settled by counting bytes.

Files declared `binary` in `.gitattributes` are skipped. The repository declares its binary
types explicitly rather than relying on git's NUL-byte heuristic, because that heuristic
misclassifies 99 of the 160 committed PDFs as text.
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path


CRLF = b"\r\n"


def count_crlf(data: bytes) -> int:
    """Return the number of CRLF byte pairs in `data`."""
    return data.count(CRLF)


def _git(args: list[str], *, repo_root: Path) -> bytes:
    """Run a git command in `repo_root` and return raw stdout, raising on failure."""
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    return completed.stdout


def staged_paths(repo_root: Path) -> list[str]:
    """Return staged added/copied/modified/renamed paths, NUL-separated so spaces survive."""
    out = _git(
        ["diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"],
        repo_root=repo_root,
    )
    return [chunk.decode("utf-8") for chunk in out.split(b"\x00") if chunk]


def binary_declared(paths: list[str], repo_root: Path, *, cached: bool = True) -> set[str]:
    """Return the subset of `paths` that `.gitattributes` declares `binary`.

    `cached` resolves attributes from the index rather than the working tree, which is the
    correct surface when validating a commit: if a staged `.gitattributes` change removes a
    `binary` declaration that the unstaged working copy still carries, the commit being built
    treats that path as text and so must this check.
    """
    if not paths:
        return set()
    stdin = "\x00".join(paths).encode("utf-8")
    command = ["git", "check-attr", "--stdin", "-z"] + (["--cached"] if cached else []) + ["binary"]
    completed = subprocess.run(
        command,
        cwd=repo_root,
        input=stdin,
        capture_output=True,
        check=True,
    )
    fields = [chunk.decode("utf-8") for chunk in completed.stdout.split(b"\x00")]
    declared: set[str] = set()
    # `-z` output is a flat NUL-separated stream of (path, attribute, value) triples.
    for index in range(0, len(fields) - 2, 3):
        path, attribute, value = fields[index], fields[index + 1], fields[index + 2]
        if attribute == "binary" and value == "set":
            declared.add(path)
    return declared


def index_bytes(path: str, repo_root: Path) -> bytes | None:
    """Return the staged blob's bytes, or None when the path has no index entry."""
    completed = subprocess.run(
        ["git", "show", f":{path}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def looks_binary(data: bytes) -> bool:
    """Return True when git's own text heuristic would classify `data` as binary.

    `text=auto` calls a blob binary when a NUL byte appears in its first 8000 bytes, and this
    check must agree with it or it rejects content git never treats as text.

    Necessary because the repository tracks binary formats that `.gitattributes` leaves as
    `binary: unspecified` — a `.gif`, an `.rds`, and two `.npy` embeddings, carrying 13, 12, 31
    and 14 incidental CRLF byte pairs respectively. Skipping only *declared* binary would reject
    any legitimate update to those files, and project rules forbid `--no-verify`, so the gate
    would have to be bypassed illegally or the file could never be updated.

    Declared `binary` remains a separate, independent skip: the inverse error also exists, and
    `.gitattributes` documents it — 99 of the 160 committed PDFs have no NUL in their first 8000
    bytes and this heuristic would call them text.
    """
    return b"\x00" in data[:8000]


def scan_paths(paths: list[str], repo_root: Path, *, check_index: bool) -> list[str]:
    """Return one violation line per CRLF-bearing surface, empty when the surface is clean."""
    skip = binary_declared(paths, repo_root) if check_index else set()
    violations: list[str] = []
    for path in paths:
        if path in skip:
            continue
        absolute = repo_root / path
        # `is_symlink` is checked first and short-circuits: `is_file()` and `read_bytes()` both
        # follow links, so a symlink whose target happens to contain CRLF would be reported as
        # though the link itself did. Git stores only the target pathname for a symlink, and the
        # staged-blob branch below already inspects exactly those bytes.
        if absolute.is_symlink():
            pass
        elif absolute.is_file():
            data = absolute.read_bytes()
            count = count_crlf(data)
            if count and not looks_binary(data):
                violations.append(f"{path}: {count} CRLF pair(s) in the working tree")
        if check_index:
            blob = index_bytes(path, repo_root)
            if blob is not None:
                count = count_crlf(blob)
                if count and not looks_binary(blob):
                    violations.append(f"{path}: {count} CRLF pair(s) in the staged blob")
    return violations


def tracked_paths(pathspecs: list[str], repo_root: Path) -> list[str]:
    """Return tracked paths matching `pathspecs`, whatever their staged or status state."""
    out = _git(["ls-files", "-z", "--", *pathspecs], repo_root=repo_root)
    return [chunk.decode("utf-8") for chunk in out.split(b"\x00") if chunk]


def worktree_violations(pathspecs: list[str], repo_root: Path) -> list[str]:
    """Scan the working-tree bytes of every tracked file under `pathspecs`.

    Why the staged scan is not enough (obs 2026-09-08-shell-rewrite-crlf-on-tracked-hook): a
    shell redirect rewrote a tracked hook with CRLF. Once any `git add` touches such a file,
    the index records its stat against the unchanged normalised LF blob, so nothing is staged
    and `git status` reports nothing, yet the CRLF shebang still executes from disk. For
    executable surfaces (hook directories) the working tree itself must be checked.
    """
    paths = tracked_paths(pathspecs, repo_root)
    # Attributes come from the index, the policy the commit being validated carries. An unstaged
    # working-tree `.gitattributes` edit declaring a hook `binary` must not exempt it.
    skip = binary_declared(paths, repo_root, cached=True)
    return scan_paths([path for path in paths if path not in skip], repo_root, check_index=False)


VIOLATION = re.compile(r"(?P<path>.*): \d+ CRLF pair\(s\) in the (?P<surface>working tree|staged blob)")


def fix_worktree(paths: list[str], repo_root: Path) -> list[str]:
    """Rewrite CRLF to LF in the working-tree bytes of `paths`, in place; return the paths changed.

    Only the working tree is written. The index, and with it any partial staging, is untouched,
    and content other than line endings is preserved byte for byte.
    """
    changed: list[str] = []
    for path in paths:
        absolute = repo_root / path
        if absolute.is_symlink() or not absolute.is_file():
            continue
        data = absolute.read_bytes()
        if looks_binary(data) or CRLF not in data:
            continue
        absolute.write_bytes(data.replace(CRLF, b"\n"))
        changed.append(path)
    return changed


def _same_apart_from_line_endings(path: str, repo_root: Path) -> bool:
    """Whether the staged blob and the working-tree file differ only in CRLF versus LF."""
    blob = index_bytes(path, repo_root)
    absolute = repo_root / path
    if blob is None or not absolute.is_file():
        return False
    return blob.replace(CRLF, b"\n") == absolute.read_bytes().replace(CRLF, b"\n")


def remediation(violations: list[str], repo_root: Path) -> list[str]:
    """Return fix-up commands that act on the surfaces this gate reads, one runnable command per line.

    `git add --renormalize` alone rewrites only the index blob, so the working-tree bytes this gate
    reads stay CRLF and the gate fails again. `--fix` rewrites the working tree in place instead,
    leaving the index alone, so a partially staged file keeps exactly its staged selection. A
    CRLF staged blob is re-staged only when the working copy holds nothing but the same content;
    otherwise re-staging would sweep unstaged edits into the commit, so the hunks are left to the
    author.
    """
    parsed = [match.groupdict() for match in map(VIOLATION.fullmatch, violations) if match]
    worktree = sorted({v["path"] for v in parsed if v["surface"] == "working tree"})
    staged = sorted({v["path"] for v in parsed if v["surface"] == "staged blob"})
    lines = [
        "Fix the producer, not just the file: on Windows `pathlib.Path.write_text` and "
        "`open(..., 'w')` translate \\n to \\r\\n unless you pass newline=''.",
        "Then run (the index and any partial staging are left as they are):",
    ]
    fixable = sorted(set(worktree) | set(staged))
    lines.append(
        "  "
        + shlex.join(
            [sys.executable, str(Path(__file__).resolve()), "--repo-root", str(repo_root), "--fix", "--", *fixable]
        )
    )
    manual: list[str] = []
    for path in staged:
        if _same_apart_from_line_endings(path, repo_root):
            lines.append("  " + shlex.join(["git", "-C", str(repo_root), "add", "--", path]))
        else:
            manual.append(path)
    if manual:
        lines.append(
            "These staged blobs carry CRLF and their working copies hold other unstaged edits; after the "
            "fix above, re-stage only the intended hunks with `git add -p`:"
        )
        lines += [f"  {shlex.quote(path)}" for path in manual]
    return lines


def main(argv: list[str] | None = None) -> int:
    """Scan the staged set, or an explicit path list, plus any tracked worktree pathspecs, for CRLF."""
    parser = argparse.ArgumentParser(description="Reject CRLF on the canonical LF byte surface.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--worktree",
        action="append",
        default=[],
        metavar="PATHSPEC",
        help="Also scan the working-tree bytes of every tracked file under PATHSPEC, staged or not. Repeatable.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Rewrite CRLF to LF in the working-tree bytes of the given paths, in place, and exit.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Explicit paths to scan (or, with --fix, to rewrite). Default: the staged set.",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    if args.fix:
        for path in fix_worktree(args.paths, repo_root):
            print(f"rewrote {path} with LF line endings", file=sys.stderr)
        return 0

    try:
        if args.paths:
            violations = scan_paths(args.paths, repo_root, check_index=False)
        else:
            violations = scan_paths(staged_paths(repo_root), repo_root, check_index=True)
        if args.worktree:
            seen = set(violations)
            violations += [v for v in worktree_violations(args.worktree, repo_root) if v not in seen]
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: could not enumerate paths to scan: {exc}", file=sys.stderr)
        return 2

    if violations:
        print("CRLF found on a surface the repository declares LF-canonical:", file=sys.stderr)
        for line in violations:
            print(f"  {line}", file=sys.stderr)
        print("", file=sys.stderr)
        for line in remediation(violations, repo_root):
            print(line, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
