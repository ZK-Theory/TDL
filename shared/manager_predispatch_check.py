#!/usr/bin/env python3
# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Manager-side (R-B) pre-dispatch gate. Before issuing a Task Prompt,
#   the Manager runs this over the Task's input-provenance manifest to confirm
#   every consumed input exists, matches its recorded signature, and that
#   co-consumed inputs share a coherent vintage. Exits non-zero on any
#   violation so a Task cannot be dispatched against missing/incoherent data.
"""Pre-dispatch input-provenance check (R-B).

Reads one or more input-provenance manifests (see ``shared/input_provenance.py``),
checks each declared input against the files on disk, and prints a per-input
table plus a coherence verdict. The output is copied into the Task Prompt's
Input Provenance Ledger (R-A).

Usage::

    uv run python -m shared.manager_predispatch_check                    # all manifests
    uv run python -m shared.manager_predispatch_check <manifest.yaml> ...  # specific
    uv run python -m shared.manager_predispatch_check --report-only       # never exit 1

Exit codes:
    0 — every checked manifest is present, signed, and coherent.
    1 — at least one manifest has a missing/mismatched/incoherent input
        (suppressed by --report-only).
    2 — usage error (a named manifest does not exist).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shared.input_provenance import (
    ManifestResult,
    check_manifest,
    discover_manifests,
    load_manifest,
)


def _find_repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"No .git directory found above {here}")


def _format_result(result: ManifestResult) -> str:
    lines: list[str] = []
    flag = "enforced" if result.enforced else "advisory (enforced: false)"
    verdict = "OK" if result.ok else "VIOLATION"
    lines.append(f"manifest: {result.manifest_id}  task: {result.task or '-'}  [{flag}]  ->  {verdict}")
    for s in result.inputs:
        mark = "ok " if (s.exists and s.signature_ok) else "BAD"
        vintage = s.disk_vintage or "ABSENT"
        lines.append(f"  [{mark}] {vintage}  ({s.root})  {s.role or s.path}")
        lines.append(f"        {s.path}")
        for v in s.violations:
            lines.append(f"        ! {v}")
    if result.vintage_spread_days is not None:
        bound = result.max_vintage_spread_days
        verdict_c = "ok" if result.coherent else "EXCEEDED"
        lines.append(f"  vintage spread: {result.vintage_spread_days}d (bound {bound}d) -> {verdict_c}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-dispatch input-provenance check.")
    parser.add_argument(
        "manifests",
        nargs="*",
        help="Manifest YAML paths. Default: every manifest under the dir.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print the report but always exit 0 (no dispatch block).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        repo_root = _find_repo_root()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.manifests:
        paths = [Path(m) for m in args.manifests]
        missing = [p for p in paths if not p.is_file()]
        if missing:
            for p in missing:
                print(f"ERROR: manifest not found: {p}", file=sys.stderr)
            return 2
    else:
        paths = discover_manifests(repo_root)
        if not paths:
            print("No input-provenance manifests found; nothing to check.")
            return 0

    any_violation = False
    blocks: list[str] = []
    for p in paths:
        result = check_manifest(load_manifest(p), repo_root)
        blocks.append(_format_result(result))
        if not result.ok:
            any_violation = True

    print("\n\n".join(blocks))
    if any_violation:
        print(
            "\nPre-dispatch gate: at least one manifest has missing or "
            "incoherent inputs. Resolve before issuing the Task.",
            file=sys.stderr,
        )
        return 0 if args.report_only else 1

    print("\nPre-dispatch gate: all checked inputs present and coherent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
