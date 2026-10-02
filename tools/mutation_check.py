#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign D)
# Purpose: Run named source mutants against a pytest selection and prove each is caught,
# without the stale-bytecode and unverified-restore failures of per-session scratch scripts.
"""Mutation check: prove a test selection fails when a named piece of source is broken.

Usage::

    python tools/mutation_check.py --target tools/check_merge_admission.py \\
        --mutant ge-to-gt ">= threshold" "> threshold" \\
        --mutant drop-guard "if not ok:" "if False:" \\
        -- tests/tools/test_merge_admission.py

For each ``--mutant NAME OLD NEW`` the tool replaces the single occurrence of OLD with NEW,
runs the selection, and restores the original bytes. A mutant is CAUGHT when pytest reports
failing tests (exit 1). Exit status: 0 when every mutant is caught, 1 when any survives, errors,
or has an anchor that is missing or ambiguous, and 2 when the harness itself cannot be trusted
(red baseline, failed restore).

Guarantees learned the hard way (obs 2026-09-11-mutation-harness-stale-bytecode):

* **No stale bytecode.** CPython reuses a cached ``.pyc`` whenever the source's size and
  whole-second mtime match, so a same-size mutant (``>`` to ``<``) written and restored within
  one second can run the previous mutant's code. ``-B`` stops writing bytecode but not
  *reading* a stale file, so the target's cached bytecode is deleted before every run, and
  every run uses ``-B`` with ``PYTHONDONTWRITEBYTECODE=1``.
* **Anchors are exact.** OLD must occur exactly once; a missing or repeated anchor fails
  rather than skips, so a refactor cannot silently turn a mutant into a no-op.
* **The restore is verified.** Original bytes are restored after every mutant (also on
  error), checked by SHA-256, and the baseline is re-run at the end: a harness that never
  checks its own restore cannot tell a caught mutant from a stale one.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clear_bytecode(target: Path) -> None:
    """Delete every cached bytecode file for ``target``, whatever interpreter tag wrote it."""
    cache_dir = target.parent / "__pycache__"
    if cache_dir.is_dir():
        for cached in cache_dir.glob(f"{target.stem}.*.pyc"):
            cached.unlink()


def run_selection(target: Path, cwd: Path, pytest_args: list[str]) -> int:
    """Run the pytest selection with bytecode fully disabled; return pytest's exit code."""
    clear_bytecode(target)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", *pytest_args]
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pytest_args: list[str] = []
    if "--" in argv:
        split = argv.index("--")
        argv, pytest_args = argv[:split], argv[split + 1 :]
    parser = argparse.ArgumentParser(description="Prove each named mutant is caught by a pytest selection.")
    parser.add_argument("--target", type=Path, required=True, help="Source file to mutate (relative to --cwd).")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Directory to run pytest from.")
    parser.add_argument("--mutant", nargs=3, action="append", default=[], metavar=("NAME", "OLD", "NEW"), required=True)
    args = parser.parse_args(argv)
    if not pytest_args:
        parser.error("give the pytest selection after `--`")

    cwd = args.cwd.resolve()
    target = (cwd / args.target).resolve()
    original = target.read_bytes()
    original_sha = _sha256(original)
    text = original.decode("utf-8")

    if run_selection(target, cwd, pytest_args) != 0:
        print("ERROR: the baseline is not green; no mutant can be judged against it.", file=sys.stderr)
        return 2

    results: list[tuple[str, str]] = []
    try:
        for name, old, new in args.mutant:
            count = text.count(old)
            if count != 1:
                reason = "anchor not found" if count == 0 else f"anchor occurs {count} times"
                results.append((name, f"ANCHOR    {name}: {reason} (must occur exactly once)"))
                continue
            target.write_bytes(text.replace(old, new, 1).encode("utf-8"))
            try:
                code = run_selection(target, cwd, pytest_args)
            finally:
                target.write_bytes(original)
            if _sha256(target.read_bytes()) != original_sha:
                print(f"ERROR: restore after {name} did not reproduce the original bytes.", file=sys.stderr)
                return 2
            if code == 1:
                results.append((name, f"CAUGHT    {name}"))
            elif code == 0:
                results.append((name, f"SURVIVED  {name}: the selection passed with the mutant in place"))
            else:
                results.append(
                    (name, f"ERROR     {name}: pytest exit {code} (collection or usage error, not a caught mutant)")
                )
    finally:
        target.write_bytes(original)
        clear_bytecode(target)

    for _, line in results:
        print(line)

    if run_selection(target, cwd, pytest_args) != 0 or _sha256(target.read_bytes()) != original_sha:
        print("ERROR: the restored baseline is not green; results above are not trustworthy.", file=sys.stderr)
        return 2
    print("restored baseline green")

    return 0 if all(line.startswith("CAUGHT") for _, line in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
