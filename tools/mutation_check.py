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
* **The restore never overwrites another edit.** The original is written back only if the file still
  holds the mutant bytes this tool wrote; otherwise the tool exits 2 and leaves the file alone.
* **Every selection is bounded.** ``--timeout`` (default 900 s) stops a run that outlasts it. A mutant
  that hangs counts as CAUGHT and says so; a baseline that times out exits 2.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clear_bytecode(target: Path) -> None:
    """Delete every cached bytecode file for ``target``, whatever interpreter tag wrote it."""
    # Beside the source, and wherever the interpreter puts bytecode when PYTHONPYCACHEPREFIX is set:
    # then it is read from <prefix>/<source dir>, and clearing only __pycache__ left it trusted.
    directories = {target.parent / "__pycache__"}
    if os.environ.get("PYTHONPYCACHEPREFIX") or sys.pycache_prefix:
        directories.add(Path(importlib.util.cache_from_source(str(target))).parent)
    for cache_dir in directories:
        if cache_dir.is_dir():
            for cached in cache_dir.glob(f"{target.stem}.*.pyc"):
                cached.unlink()


def restore(target: Path, mutant: bytes, original: bytes) -> bool:
    """Put ``original`` back only if ``target`` still holds the ``mutant`` bytes this tool wrote.

    The target is a live source file. If its bytes are no longer the mutant, another session edited
    it during the run, and an unconditional restore would silently destroy that edit (Codex review
    of PR #303). Returns whether the file held the mutant, and so was restored.
    """
    if target.read_bytes() != mutant:
        return False
    target.write_bytes(original)
    return True


def run_selection(target: Path, cwd: Path, pytest_args: list[str], timeout: float | None = None) -> int | None:
    """Run the pytest selection with bytecode fully disabled; return pytest's exit code.

    Returns None when the selection outran ``timeout`` seconds: a mutant can loop forever, and an
    unbounded run let one hang stall the whole check (Codex review of PR #303).
    """
    clear_bytecode(target)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", *pytest_args]
    try:
        return subprocess.run(
            command, cwd=cwd, env=env, capture_output=True, text=True, check=False, timeout=timeout
        ).returncode
    except subprocess.TimeoutExpired:
        return None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pytest_args: list[str] = []
    if "--" in argv:
        split = argv.index("--")
        argv, pytest_args = argv[:split], argv[split + 1 :]
    parser = argparse.ArgumentParser(description="Prove each named mutant is caught by a pytest selection.")
    parser.add_argument("--target", type=Path, required=True, help="Source file to mutate (relative to --cwd).")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="Directory to run pytest from.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=900.0,
        help="Seconds allowed for each pytest selection (default 900). A mutant that outruns it counts as caught.",
    )
    parser.add_argument("--mutant", nargs=3, action="append", default=[], metavar=("NAME", "OLD", "NEW"), required=True)
    args = parser.parse_args(argv)
    if not pytest_args:
        parser.error("give the pytest selection after `--`")

    cwd = args.cwd.resolve()
    target = (cwd / args.target).resolve()
    original = target.read_bytes()
    original_sha = _sha256(original)
    text = original.decode("utf-8")

    baseline = run_selection(target, cwd, pytest_args, args.timeout)
    if baseline is None:
        print(f"ERROR: the baseline timed out after {args.timeout:g}s; raise --timeout.", file=sys.stderr)
        return 2
    if baseline != 0:
        print("ERROR: the baseline is not green; no mutant can be judged against it.", file=sys.stderr)
        return 2

    results: list[tuple[str, str]] = []
    held: bytes | None = None
    try:
        for name, old, new in args.mutant:
            count = text.count(old)
            if count != 1:
                reason = "anchor not found" if count == 0 else f"anchor occurs {count} times"
                results.append((name, f"ANCHOR    {name}: {reason} (must occur exactly once)"))
                continue
            mutant = text.replace(old, new, 1).encode("utf-8")
            target.write_bytes(mutant)
            held = mutant
            try:
                code = run_selection(target, cwd, pytest_args, args.timeout)
            finally:
                if not restore(target, mutant, original):
                    held = None
            if held is None:
                print(
                    f"ERROR: {target} changed during the run of {name} and no longer holds the mutant bytes; "
                    "it was NOT restored, because that would overwrite another edit. Reconcile it by hand.",
                    file=sys.stderr,
                )
                return 2
            held = None
            if _sha256(target.read_bytes()) != original_sha:
                print(f"ERROR: restore after {name} did not reproduce the original bytes.", file=sys.stderr)
                return 2
            if code is None:
                results.append((name, f"CAUGHT    {name}: timed out after {args.timeout:g}s (the mutant hangs)"))
            elif code == 1:
                results.append((name, f"CAUGHT    {name}"))
            elif code == 0:
                results.append((name, f"SURVIVED  {name}: the selection passed with the mutant in place"))
            else:
                results.append(
                    (name, f"ERROR     {name}: pytest exit {code} (collection or usage error, not a caught mutant)")
                )
    finally:
        if held is not None:
            restore(target, held, original)
        clear_bytecode(target)

    for _, line in results:
        print(line)

    if run_selection(target, cwd, pytest_args, args.timeout) != 0 or _sha256(target.read_bytes()) != original_sha:
        print("ERROR: the restored baseline is not green; results above are not trustworthy.", file=sys.stderr)
        return 2
    print("restored baseline green")

    return 0 if all(line.startswith("CAUGHT") for _, line in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
