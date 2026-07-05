"""Shared deterministic fixture-shard materialization helpers."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar


CaseT = TypeVar("CaseT")
PackageBuilder = Callable[[str, CaseT], dict[str, bytes]]


def materialize_cases(
    root: Path,
    *,
    cases: Mapping[str, CaseT],
    package_builder: PackageBuilder[CaseT],
    shard_name: str,
    check: bool = False,
) -> None:
    """Generate a fixture shard or check its existing files exactly."""
    expected = {
        root / case_id / relative: data
        for case_id, case in cases.items()
        for relative, data in package_builder(case_id, case).items()
    }
    if check:
        observed = {path for case_id in cases for path in (root / case_id).rglob("*") if path.is_file()}
        if observed != set(expected):
            raise SystemExit(f"{shard_name} fixture file closure differs from generator")
        mismatches = [str(path) for path, data in expected.items() if path.read_bytes() != data]
        if mismatches:
            raise SystemExit(f"{shard_name} fixtures differ from generator: {mismatches}")
        return

    for path, data in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def run_cli(
    materialize: Callable[..., None],
    *,
    default_root: Path,
) -> None:
    """Run a fixture materializer in generation or check-only mode."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    materialize(args.root, check=args.check)
