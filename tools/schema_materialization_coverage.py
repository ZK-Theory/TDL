#!/usr/bin/env python3
"""Report the ratio of accepted command/event schemas to runtime-wired commands.

Why (obs 145): `.research-system/schemas/core/{commands,events}/` holds an
accepted specification surface; `CommandService._build_event` implements a
subset of it. Nothing published that ratio, so a planning session reading the
runtime concluded a capability was absent and designed a parallel mechanism
duplicating one the schemas already specify and accept review already
covered. This is read-only introspection — it does not modify
`research_system/command/service.py` or the schema tree, so it stays safe to
run regardless of in-flight work on either.

Usage:
    uv run python tools/schema_materialization_coverage.py
    uv run python tools/schema_materialization_coverage.py --unwired-only
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMAND_SCHEMAS_DIR = REPO_ROOT / ".research-system" / "schemas" / "core" / "commands"
EVENT_SCHEMAS_DIR = REPO_ROOT / ".research-system" / "schemas" / "core" / "events"
COMMAND_SERVICE = REPO_ROOT / "research_system" / "command" / "service.py"


def _accepted_types(schema_dir: Path, kind: str) -> set[str]:
    """Return the accepted type names declared by every schema's `$id`.

    `$id` is authoritative (`ars://core/{kind}/{Type}`), unlike deriving the
    type from the snake_case filename, which is lossy to reconstruct exactly.
    """
    accepted: set[str] = set()
    prefix = f"ars://core/{kind}/"
    for schema_file in sorted(schema_dir.glob("*.schema.json")):
        try:
            data = json.loads(schema_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARNING: could not parse {schema_file}: {exc}", file=sys.stderr)
            continue
        schema_id = data.get("$id", "")
        if schema_id.startswith(prefix):
            accepted.add(schema_id[len(prefix) :])
        else:
            print(f"WARNING: {schema_file} has no {prefix}<Type> $id — skipped", file=sys.stderr)
    return accepted


def _wired_command_types() -> set[str]:
    """Return every command_type string `_build_event` branches on, via AST.

    Reads the live source rather than a hardcoded list, so this stays correct
    as the runtime is actively extended — the whole point of a report that
    should not itself rot (obs 145's suggested fix: "regenerated ... so it
    cannot rot").
    """
    tree = ast.parse(COMMAND_SERVICE.read_text(encoding="utf-8"))
    build_event = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_build_event":
            build_event = node
            break
    if build_event is None:
        raise AssertionError("_build_event not found in research_system/command/service.py")

    wired: set[str] = set()
    for node in ast.walk(build_event):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        for op, comparator in zip(node.ops, node.comparators):
            if not isinstance(op, ast.Eq):
                continue
            for side in (left, comparator):
                if isinstance(side, ast.Name) and side.id == "command_type":
                    other = comparator if side is left else left
                    if isinstance(other, ast.Constant) and isinstance(other.value, str):
                        wired.add(other.value)
    return wired


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unwired-only", action="store_true", help="print only the unwired command list")
    args = parser.parse_args()

    accepted_commands = _accepted_types(COMMAND_SCHEMAS_DIR, "command")
    accepted_events = _accepted_types(EVENT_SCHEMAS_DIR, "event")
    wired = _wired_command_types()

    unwired = sorted(accepted_commands - wired)
    wired_and_accepted = sorted(accepted_commands & wired)
    wired_but_unaccepted = sorted(wired - accepted_commands)

    if args.unwired_only:
        for name in unwired:
            print(name)
        return 0

    print(f"Accepted command schemas : {len(accepted_commands)}")
    print(f"Accepted event schemas   : {len(accepted_events)}")
    print(f"Wired in _build_event    : {len(wired_and_accepted)} / {len(accepted_commands)}")
    if wired_but_unaccepted:
        print(
            f"WARNING: {len(wired_but_unaccepted)} command(s) wired but not in the accepted "
            f"schema set: {wired_but_unaccepted}"
        )
    print()
    print(f"Unwired accepted commands ({len(unwired)}):")
    for name in unwired:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
