#!/usr/bin/env python3
# Research context: 2026-10-02 research_system suite triage (obs 2026-10-03-shared-seam-change-merged-without-its-dependents)
# Purpose: duration-balanced shards for the nightly and pull-request research_system lanes.
"""Split the research_system test files into duration-balanced CI shards.

The unfiltered suite takes about 7.5 hours serially, and its largest file about an hour,
so the nightly lane runs it as N parallel shards. Assignment is deterministic: files are
weighted by ``tools/research_system_durations.json`` (unknown files get ``DEFAULT_SECONDS``)
and placed heaviest-first on the lightest shard, with ties broken by path. Every test file
lands in exactly one shard. A file missing from every shard would leave a test outside
every lane, which is the 2026-10-02 failure this lane exists to prevent.

With ``--files`` the shards split that selection (the pull-request lane's affected files)
instead of the whole suite. A shard of a small selection may then be empty, which is not
an error; an unknown path in the selection is.

Usage:
    research_system_shards.py --shard K --of N   # print shard K's files (1-based), one per line
    research_system_shards.py --of N --summary   # print each shard's file count and weight
    research_system_shards.py --shard K --of N --files selection.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = REPO_ROOT / "tests" / "research_system"
DURATIONS = REPO_ROOT / "tools" / "research_system_durations.json"
DEFAULT_SECONDS = 120


def discover(test_root: Path = TEST_ROOT) -> list[str]:
    """Return every research_system test file as a repo-relative POSIX path, sorted."""
    files = sorted(path.relative_to(REPO_ROOT).as_posix() for path in test_root.rglob("test_*.py"))
    if not files:
        raise SystemExit(f"no test files under {test_root}; refusing to emit empty shards")
    return files


def load_weights(path: Path = DURATIONS) -> dict[str, int]:
    """Return recorded per-file seconds."""
    return {str(key): int(value) for key, value in json.loads(path.read_text(encoding="utf-8"))["seconds"].items()}


def assign(files: list[str], weights: dict[str, int], shards: int) -> list[list[str]]:
    """Place files heaviest-first on the currently lightest shard (deterministic LPT)."""
    if shards < 1:
        raise ValueError("shard count must be at least 1")
    buckets: list[list[str]] = [[] for _ in range(shards)]
    loads = [0] * shards
    ordered = sorted(files, key=lambda name: (-weights.get(name, DEFAULT_SECONDS), name))
    for name in ordered:
        index = min(range(shards), key=lambda i: (loads[i], i))
        buckets[index].append(name)
        loads[index] += weights.get(name, DEFAULT_SECONDS)
    return [sorted(bucket) for bucket in buckets]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--of", type=int, required=True, help="number of shards")
    parser.add_argument("--shard", type=int, help="1-based shard to print")
    parser.add_argument("--summary", action="store_true", help="print per-shard counts and weights")
    parser.add_argument("--files", type=Path, help="shard only the test files listed here, one per line")
    args = parser.parse_args(argv)
    known = discover()
    files = known if args.files is None else read_selection(args.files, set(known))
    weights = load_weights()
    buckets = assign(files, weights, args.of)
    if args.summary:
        for number, bucket in enumerate(buckets, start=1):
            weight = sum(weights.get(name, DEFAULT_SECONDS) for name in bucket)
            print(f"shard {number}: {len(bucket)} files, {weight} s")
        return 0
    if args.shard is None or not 1 <= args.shard <= args.of:
        parser.error("--shard must be between 1 and --of")
    bucket = buckets[args.shard - 1]
    if not bucket and args.files is None:
        print(f"shard {args.shard} of {args.of} is empty", file=sys.stderr)
        return 1
    if bucket:
        print("\n".join(bucket))
    return 0


def read_selection(path: Path, known: set[str]) -> list[str]:
    """Return the selected test files, refusing any path that is not a known test file."""
    selected = sorted({line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()})
    unknown = [name for name in selected if name not in known]
    if unknown:
        raise SystemExit(f"selection names files that are not research_system tests: {unknown}")
    return selected


if __name__ == "__main__":
    raise SystemExit(main())
