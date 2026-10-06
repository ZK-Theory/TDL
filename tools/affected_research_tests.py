#!/usr/bin/env python3
# Research context: 2026-10-02 research_system suite triage (obs 2026-10-03-shared-seam-change-merged-without-its-dependents)
# Purpose: select the research_system tests a pull request's diff can affect.
"""Select the research_system tests a change can affect, for the pull-request lane.

On 2026-10-02 most of 195 failures on main traced to PRs that changed a shared seam and ran
only the tests beside it (obs 2026-10-03-shared-seam-change-merged-without-its-dependents).
For a diff against a base ref this selects:

* every changed test file under ``tests/research_system``;
* every test file that imports a changed module, or any module that transitively imports
  one. Changed modules are ``research_system`` sources and the test tree's own helpers
  (``factories.py``, the ``contracts/wp6_*`` validators and expectations). The closure runs
  over both trees' imports, so a change re-exported through a facade such as ``store.lock``,
  or reached through a helper, still selects its tests;
* every research_system test, when a ``conftest.py`` that governs the tree changes;
* when a changed non-Python path is pinned by a ``.research-system`` file (a skill, a doc,
  ``.gitattributes``, a schema), or anything under ``.research-system/`` changes: every
  contract test, every test that names the path, and every test that loads packs.

Output: one test file per line, sorted. No output means nothing is affected.

Usage:
    affected_research_tests.py --base origin/main
"""

from __future__ import annotations

import argparse
import ast
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "research_system"
TEST_ROOT = "tests/research_system"
PINNING_ROOT = ".research-system"


def changed_files(base: str) -> list[str]:
    """Return repo-relative paths changed between ``base``'s merge-base and HEAD."""
    output = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [line.strip() for line in output.splitlines() if line.strip()]


def module_name(path: str) -> str | None:
    """Return the dotted module for a ``research_system`` or research test-tree path, or None."""
    if not (path.startswith((f"{PACKAGE}/", f"{TEST_ROOT}/")) and path.endswith(".py")):
        return None
    return path[: -len(".py")].replace("/", ".").removesuffix(".__init__")


def imported_modules(source: str, current: str, *, is_package: bool = False) -> set[str]:
    """Return absolute module names a source imports (``from x import y`` yields x and x.y).

    Relative imports resolve against the containing package, which for a package's own
    ``__init__.py`` is the package itself.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    if is_package:
        package = current
    else:
        package = current.rsplit(".", 1)[0] if "." in current else current
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                base_parts = parts[: len(parts) - (node.level - 1)] if node.level > 1 else parts
                base = ".".join(base_parts + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            if base:
                found.add(base)
                found.update(f"{base}.{alias.name}" for alias in node.names)
    return found


def dependents(changed_modules: set[str], sources: dict[str, str]) -> set[str]:
    """Return every module that transitively imports one of ``changed_modules``.

    Args:
        changed_modules: Dotted names of the changed modules.
        sources: ``{repo-relative path: source}``; module names and package status come
            from the paths.
    """
    imports = {
        module_name(path) or "": imported_modules(source, module_name(path) or "", is_package=_is_package(path))
        for path, source in sources.items()
    }
    affected = set(changed_modules)
    grew = True
    while grew:
        grew = False
        for module, names in imports.items():
            if module not in affected and any(_hits(name, affected) for name in names):
                affected.add(module)
                grew = True
    return affected


def _is_package(path: str) -> bool:
    return path.endswith("/__init__.py")


def _hits(name: str, modules: set[str]) -> bool:
    """True if an imported name is, or is inside, an affected module, or a parent re-exporting it."""
    return any(name == module or name.startswith(f"{module}.") for module in modules)


def select(changed: list[str], tests: dict[str, str], package_sources: dict[str, str], pinned_text: str) -> list[str]:
    """Return the affected test files.

    Args:
        changed: Changed repo-relative paths.
        tests: ``{test path: source}`` for every ``.py`` under the test root.
        package_sources: ``{repo-relative path: source}`` for the research_system package.
        pinned_text: Concatenated text of every ``.research-system`` file, for pin lookups.
    """
    selected = {path for path in changed if path in tests}
    if any(_governs(path) for path in changed):
        selected |= set(tests)
    changed_modules = {module for module in (module_name(path) for path in changed) if module}
    if changed_modules:
        affected = dependents(changed_modules, {**package_sources, **tests})
        selected |= {path for path in tests if module_name(path) in affected}
    other = [path for path in changed if not path.endswith(".py") or not path.startswith((PACKAGE + "/", TEST_ROOT))]
    pinned = [path for path in other if path.startswith(PINNING_ROOT + "/") or path in pinned_text]
    if pinned:
        selected |= {path for path in tests if path.startswith(f"{TEST_ROOT}/contracts/")}
        selected |= {
            path
            for path, source in tests.items()
            if any(name in source for name in pinned) or ".research-system/packs" in source or '"packs"' in source
        }
    return sorted(path for path in selected if Path(path).name.startswith("test_"))


def _governs(path: str) -> bool:
    """True for a ``conftest.py`` whose directory contains the research test tree, or lies inside it."""
    if Path(path).name != "conftest.py":
        return False
    directory = path.rsplit("/", 1)[0] if "/" in path else ""
    if not directory:
        return True
    return TEST_ROOT == directory or TEST_ROOT.startswith(f"{directory}/") or directory.startswith(f"{TEST_ROOT}/")


def _package_sources(root: Path = REPO_ROOT) -> dict[str, str]:
    """Return ``{repo-relative path: source}`` for every research_system module."""
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8") for path in (root / PACKAGE).rglob("*.py")
    }


def _pinned_text(root: Path = REPO_ROOT) -> str:
    chunks = []
    for path in (root / PINNING_ROOT).rglob("*"):
        if path.is_file() and path.suffix in {".yaml", ".yml", ".json", ".md"}:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args(argv)
    tests = {
        path.relative_to(REPO_ROOT).as_posix(): path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / TEST_ROOT).rglob("*.py")
    }
    for path in select(changed_files(args.base), tests, _package_sources(), _pinned_text()):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
