#!/usr/bin/env python3
# Research context: docs/plans/strategy/system-review-2026-09-23-decision-report.md (Campaign F)
# Purpose: Prove formatter or codemod collateral is semantics-preserving by comparing each file's
# AST at a base ref against the working tree, instead of assuming formatters are safe.
"""Report whether each Python file's AST is unchanged since a base ref.

Obs 2026-09-08-formatter-collateral-needs-a-semantics-proof: a one-line edit triggered a 15-file
reformat. "Formatters preserve semantics" was assumed, and for one file it was false: docstring
whitespace changed, which changes the AST (docstrings are string constants). Attach this tool's
output as evidence whenever a formatter or codemod touches more than the intended edit.

Output, one line per file: EQUIVALENT, CHANGED, NEW (absent at the base) or UNPARSEABLE.
Exit status is 0 only when every file is EQUIVALENT.

Usage: python tools/ast_equivalence.py [--base HEAD] FILE...
"""

from __future__ import annotations

import argparse
import ast
import subprocess
from pathlib import Path


def _dump(source: str) -> str:
    return ast.dump(ast.parse(source), include_attributes=False)


def classify(path: str, base: str) -> str:
    """Return the equivalence verdict for ``path`` against ``base``."""
    old = subprocess.run(["git", "show", f"{base}:{path}"], capture_output=True, check=False)
    if old.returncode != 0:
        return "NEW"
    try:
        before = _dump(old.stdout.decode("utf-8"))
        after = _dump(Path(path).read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return "UNPARSEABLE"
    return "EQUIVALENT" if before == after else "CHANGED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare each file's AST at --base with the working tree.")
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args(argv)

    verdicts = [(path, classify(path, args.base)) for path in args.files]
    for path, verdict in verdicts:
        print(f"{verdict:<11} {path}")
    return 0 if all(verdict == "EQUIVALENT" for _, verdict in verdicts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
