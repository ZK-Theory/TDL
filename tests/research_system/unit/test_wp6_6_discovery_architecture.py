"""Architectural controls for the Discovery module boundaries.

These tests do not exercise lifecycle behaviour -- the WP6.6 gate does that.
They exist so the structural properties that made the previous single-file
runtime hard to review cannot silently return: one owning reducer per event,
no unreachable reducer, an acyclic leaf-first dependency direction, and a
facade that owns orchestration rather than lifecycle policy.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from research_system.discovery.replay.registry import REDUCERS

DISCOVERY = Path(__file__).resolve().parents[3] / "research_system" / "discovery"
LIFECYCLE_MODULES = (
    "genesis",
    "scout_candidate",
    "assay",
    "spike",
    "review_decision",
    "promotion",
    "dossier",
)
# Leaves may not import anything that owns state or orchestration.
FORBIDDEN_IMPORTS = {
    "accepted_w11": ("routes", "rules", "ledger_integrity", "replay", "runtime", "dossier"),
    "routes": ("rules", "ledger_integrity", "replay", "runtime"),
    "rules": ("replay", "runtime"),
    "ledger_integrity": ("replay", "runtime"),
    "replay": ("runtime",),
}


def _module_imports(path: Path, *, full: bool = False) -> set[str]:
    """Return the research_system.discovery submodules this file imports.

    ``full`` keeps the dotted submodule path (``replay.scope``); otherwise only
    the owning top-level component (``replay``) is returned.
    """

    imported: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("research_system.discovery"):
                tail = node.module[len("research_system.discovery") :].lstrip(".")
                if tail:
                    imported.add(tail if full else tail.split(".")[0])
    return imported


def _reducer_functions(module: str) -> set[str]:
    tree = ast.parse((DISCOVERY / "replay" / f"{module}.py").read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_every_registered_event_type_has_exactly_one_owning_reducer() -> None:
    """No accepted event may be reduced by two functions or by none."""

    assert REDUCERS, "the reducer registry is empty"
    for event_type, reducer in REDUCERS.items():
        assert callable(reducer), event_type
        assert reducer.__module__.startswith("research_system.discovery.replay."), event_type


def test_no_reducer_is_unreachable_from_the_registry() -> None:
    """Every reducer defined in a lifecycle module is dispatchable."""

    registered = {reducer.__name__ for reducer in REDUCERS.values()}
    for module in LIFECYCLE_MODULES:
        defined = _reducer_functions(module)
        orphans = defined - registered
        assert not orphans, f"{module}.py defines unreachable reducers: {sorted(orphans)}"


def test_each_reducer_is_owned_by_exactly_one_lifecycle_module() -> None:
    """A reducer name may not be defined in two lifecycle modules."""

    seen: dict[str, str] = {}
    for module in LIFECYCLE_MODULES:
        for name in _reducer_functions(module):
            assert name not in seen, f"{name} defined in both {seen.get(name)} and {module}"
            seen[name] = module


@pytest.mark.parametrize("module,forbidden", sorted(FORBIDDEN_IMPORTS.items()))
def test_leaf_modules_do_not_import_towards_the_facade(module: str, forbidden: tuple[str, ...]) -> None:
    """Dependency direction runs leaf -> replay -> facade and never back."""

    paths = sorted((DISCOVERY / module).glob("*.py")) if (DISCOVERY / module).is_dir() else [DISCOVERY / f"{module}.py"]
    for path in paths:
        offending = _module_imports(path) & set(forbidden)
        assert not offending, f"{path.name} must not import {sorted(offending)}"


def test_discovery_package_has_no_import_cycle() -> None:
    """The discovery package import graph is acyclic."""

    edges = {
        path.relative_to(DISCOVERY).with_suffix("").as_posix().replace("/", "."): {
            name for name in _module_imports(path, full=True)
        }
        for path in DISCOVERY.rglob("*.py")
    }
    # A package's __init__ stands in for the package name itself.
    for name in list(edges):
        if name.endswith(".__init__"):
            edges[name.removesuffix(".__init__")] = edges.pop(name)
    known = set(edges)
    edges = {name: imports & known for name, imports in edges.items()}

    visiting: set[str] = set()
    done: set[str] = set()

    def walk(node: str, trail: tuple[str, ...]) -> None:
        if node in done:
            return
        assert node not in visiting, f"import cycle: {' -> '.join((*trail, node))}"
        visiting.add(node)
        for peer in sorted(edges.get(node, ())):
            walk(peer, (*trail, node))
        visiting.discard(node)
        done.add(node)

    for node in sorted(edges):
        walk(node, ())


def test_runtime_facade_owns_no_replay_reducer() -> None:
    """runtime.py orchestrates submission; it does not reduce events."""

    tree = ast.parse((DISCOVERY / "runtime.py").read_text(encoding="utf-8"))
    defined = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    reducers = sorted(name for name in defined if name.startswith("reduce_"))
    assert reducers == [], "lifecycle reducers must live in research_system.discovery.replay"
    assert "replay_discovery" not in defined, "replay_discovery must be owned by replay.driver"
