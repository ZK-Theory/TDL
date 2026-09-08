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


def binary_declared(paths: list[str], repo_root: Path) -> set[str]:
    """Return the subset of `paths` that `.gitattributes` declares `binary`."""
    if not paths:
        return set()
    stdin = "\x00".join(paths).encode("utf-8")
    completed = subprocess.run(
        ["git", "check-attr", "--stdin", "-z", "binary"],
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


def scan_paths(paths: list[str], repo_root: Path, *, check_index: bool) -> list[str]:
    """Return one violation line per CRLF-bearing surface, empty when the surface is clean."""
    skip = binary_declared(paths, repo_root) if check_index else set()
    violations: list[str] = []
    for path in paths:
        if path in skip:
            continue
        absolute = repo_root / path
        if absolute.is_file():
            count = count_crlf(absolute.read_bytes())
            if count:
                violations.append(f"{path}: {count} CRLF pair(s) in the working tree")
        if check_index:
            blob = index_bytes(path, repo_root)
            if blob is not None:
                count = count_crlf(blob)
                if count:
                    violations.append(f"{path}: {count} CRLF pair(s) in the staged blob")
    return violations


def main(argv: list[str] | None = None) -> int:
    """Scan the staged set, or an explicit path list, for CRLF."""
    parser = argparse.ArgumentParser(description="Reject CRLF on the canonical LF byte surface.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "paths",
        nargs="*",
        help="Explicit paths to scan. Default: the staged set. Used by the negative control.",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    if args.paths:
        violations = scan_paths(args.paths, repo_root, check_index=False)
    else:
        try:
            paths = staged_paths(repo_root)
        except subprocess.CalledProcessError as exc:
            print(f"ERROR: could not enumerate staged paths: {exc}", file=sys.stderr)
            return 2
        violations = scan_paths(paths, repo_root, check_index=True)

    if violations:
        print("CRLF found on a surface the repository declares LF-canonical:", file=sys.stderr)
        for line in violations:
            print(f"  {line}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Fix the producer, not just the file: on Windows `pathlib.Path.write_text` and "
            "`open(..., 'w')` translate \\n to \\r\\n unless you pass newline=''.",
            file=sys.stderr,
        )
        print("Then renormalise:  git add --renormalize <path>", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
