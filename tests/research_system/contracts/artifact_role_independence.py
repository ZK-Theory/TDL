"""Role-driven producer/oracle independence checking, shared across materialization lanes.

The WP6.2 T2 lane already had this property machine-checked, but by a hand-written test naming
its two modules literally (``test_wp6_2_t2_authority_mutations.py::
test_protected_membership_expected_side_has_no_materializer_dependency``). Its sibling WP6.1 lane
pinned the same five files' bytes, declared no ``artifact_role``, and had no equivalent guard — so
the property held there by convention only, and an edit adding a derivation import to the expected
side would have passed (observation 2026-08-12-wp61-lane-lacks-t2-independence-guard).

This module derives the forbidden edges from the *declared roles* instead. A lane is covered by
declaring its roles in a contract under ``.research-system/contracts/``: manifests are discovered,
not listed, so adding a lane is a contract edit and nothing else. That matters because the failure
mode being guarded is exactly "the second lane nobody remembered to wire up".

Three properties keep the guard from passing vacuously:

* **Imports are resolved fully.** ``from pkg import submodule`` records only ``pkg`` in
  ``ImportFrom.module``; comparing that alone missed the package-import idiom this very package
  uses (``wp6_1_schema_materializer.py`` line 17). Aliased names and relative levels are resolved.
* **It fails closed.** An edge whose role has no Python declaration, or a declaration whose explicit
  ``module`` disagrees with its path, is a contract error — not a silently skipped edge.
* **Known breaches are pinned, not waived.** Where a lane genuinely carries a forbidden edge that
  cannot yet be removed, the contract enumerates the exact attributes shared across it. Using any
  attribute beyond the pin fails, and so does a pinned attribute that is no longer used — so the
  pin cannot outlive the fix.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]

CONTRACTS_DIR = ".research-system/contracts"
WP6_1_ROLES_PATH = f"{CONTRACTS_DIR}/wp6-1-artifact-roles.yaml"
WP6_2_T2_IDENTITIES_PATH = f"{CONTRACTS_DIR}/wp6-2-t2-schema-identities.yaml"

#: Edges applied to any lane that declares roles but no explicit ``independence_edges`` list.
#: These are the WP6.2 T2 lane's own edges, stated once so the T2 lane needs no contract change
#: to be covered by the generic rule.
DEFAULT_INDEPENDENCE_EDGES: tuple[tuple[str, str], ...] = (
    ("independent_oracle", "schema_materializer"),
    ("schema_materializer", "independent_oracle"),
)


class RoleContractError(ValueError):
    """A role manifest is malformed in a way that would otherwise disable enforcement silently."""


@dataclass(frozen=True)
class RoleDeclaration:
    """One declared artifact and the role it plays in its lane."""

    role: str
    repository_path: str
    module: str


@dataclass(frozen=True)
class Edge:
    """A forbidden (importer_role → imported_role) edge, optionally with a pinned known breach."""

    importer_role: str
    imported_role: str
    pinned_attributes: frozenset[str] | None = None


def _load_yaml(path: Path) -> Any:
    """Read a contract manifest."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def module_name(repository_path: str) -> str:
    """Derive the dotted module name a repository path is imported as."""
    return repository_path.removesuffix(".py").replace("/", ".")


def declarations(manifest: Mapping[str, Any]) -> list[RoleDeclaration]:
    """Return every Python artifact in `manifest` that declares a role.

    Non-Python artifacts (schemas, catalogues, `.gitattributes`) carry roles too but have no import
    graph, so they are skipped rather than treated as an empty one — an empty import set would make
    the assertion pass vacuously for them.

    Raises:
        RoleContractError: an explicit ``module`` disagrees with the one derived from its path. A
            stale module value would make the real module's imports unmatchable, so the guard
            would report independence for a file it is no longer looking at.
    """
    found: list[RoleDeclaration] = []
    for row in manifest.get("artifacts") or []:
        path = row.get("repository_path", "")
        if not path.endswith(".py") or "artifact_role" not in row:
            continue
        derived = module_name(path)
        declared = row.get("module")
        if declared is not None and declared != derived:
            raise RoleContractError(f"{path}: declared module {declared!r} does not match its path ({derived!r})")
        found.append(RoleDeclaration(role=row["artifact_role"], repository_path=path, module=derived))
    return found


def independence_edges(manifest: Mapping[str, Any]) -> tuple[Edge, ...]:
    """Return the edges this lane forbids, each with its pinned known breach if one is declared."""
    declared = manifest.get("independence_edges")
    if not declared:
        return tuple(Edge(importer, imported) for importer, imported in DEFAULT_INDEPENDENCE_EDGES)
    edges: list[Edge] = []
    for row in declared:
        breach = row.get("known_breach")
        pinned = frozenset(breach["attributes"]) if breach else None
        edges.append(Edge(row["forbidden_importer_role"], row["forbidden_imported_role"], pinned))
    return tuple(edges)


def _resolve_base(node: ast.ImportFrom, importer_module: str) -> str:
    """Resolve an ``ImportFrom``'s base module, applying its relative ``level``."""
    if not node.level:
        return node.module or ""
    package_parts = importer_module.split(".")[:-1]
    anchor = package_parts[: len(package_parts) - (node.level - 1)] if node.level > 1 else package_parts
    return ".".join(anchor + ([node.module] if node.module else []))


@dataclass(frozen=True)
class ImportGraph:
    """What one source file imports, and which attributes of each imported module it touches."""

    modules: frozenset[str]
    attributes: Mapping[str, frozenset[str]]


def import_graph(source_path: Path, importer_module: str, targets: Iterable[str]) -> ImportGraph:
    """Resolve every module `source_path` imports, and the attributes it uses from each target.

    Every import form is resolved to candidate full module names:

    * ``import a.b.c`` / ``import a.b.c as x`` → ``a.b.c``
    * ``from a.b import c`` → ``a.b`` and ``a.b.c`` (``c`` may be a submodule, not just a name)
    * ``from . import c`` / ``from .d import e`` → resolved against `importer_module`'s package

    For each module in `targets`, the attributes used are collected from names bound to that module
    (``from pkg import mod as alias`` then ``alias.attr``; ``import pkg.mod`` then ``pkg.mod.attr``)
    and from names imported out of it directly (``from pkg.mod import attr``).
    """
    wanted = set(targets)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    bound: dict[str, str] = {}
    used: dict[str, set[str]] = {module: set() for module in wanted}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
                if alias.name in wanted:
                    bound[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_base(node, importer_module)
            if base:
                modules.add(base)
            for alias in node.names:
                candidate = f"{base}.{alias.name}" if base else alias.name
                modules.add(candidate)
                if candidate in wanted:
                    bound[alias.asname or alias.name] = candidate
                if base in wanted:
                    used[base].add(alias.name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            owner = ast.unparse(node.value)
            if owner in bound:
                used[bound[owner]].add(node.attr)

    return ImportGraph(frozenset(modules), {module: frozenset(names) for module, names in used.items()})


def violations(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    source_override: Mapping[str, Path] | None = None,
) -> list[str]:
    """Return one message per breach of a forbidden edge, empty when the lane is independent.

    `source_override` maps a repository path to an alternative file to parse. The negative controls
    use it to point one role at a mutated copy without writing into the real tree; the copy is still
    resolved as the declared module, so relative imports behave as they would in place.

    Raises:
        RoleContractError: an edge names a role with no Python declaration. Skipping that edge would
            report the lane as independent while enforcing nothing.
    """
    by_role: dict[str, list[RoleDeclaration]] = {}
    for row in declarations(manifest):
        by_role.setdefault(row.role, []).append(row)

    found: list[str] = []
    for edge in independence_edges(manifest):
        for role in (edge.importer_role, edge.imported_role):
            if not by_role.get(role):
                raise RoleContractError(
                    f"edge {edge.importer_role} → {edge.imported_role} names undeclared role {role!r}"
                )
        forbidden = {row.module for row in by_role[edge.imported_role]}

        for row in by_role[edge.importer_role]:
            source = (source_override or {}).get(row.repository_path) or (repo_root / row.repository_path)
            graph = import_graph(source, row.module, forbidden)
            for module in sorted(graph.modules & forbidden):
                if edge.pinned_attributes is None:
                    found.append(
                        f"{row.repository_path} ({edge.importer_role}) imports {module} ({edge.imported_role}) — "
                        f"the {edge.importer_role} → {edge.imported_role} edge is forbidden by contract"
                    )
                    continue
                used = graph.attributes[module]
                for extra in sorted(used - edge.pinned_attributes):
                    found.append(
                        f"{row.repository_path} uses {module}.{extra} beyond the pinned known breach — "
                        f"the shared surface across {edge.importer_role} → {edge.imported_role} has grown"
                    )
                for stale in sorted(edge.pinned_attributes - used):
                    found.append(
                        f"{row.repository_path} no longer uses {module}.{stale}, but the contract still pins it — "
                        f"remove it from known_breach so the pin cannot outlive the fix"
                    )
    return found


def covered_manifests(repo_root: Path = REPO_ROOT) -> dict[str, Mapping[str, Any]]:
    """Discover every contract under ``.research-system/contracts/`` that declares an artifact role.

    Discovered rather than listed: a hard-coded set would let a newly declared lane pass
    ``assert_independent`` while never being checked.
    """
    found: dict[str, Mapping[str, Any]] = {}
    for path in sorted((repo_root / CONTRACTS_DIR).glob("*.yaml")):
        manifest = _load_yaml(path)
        if not isinstance(manifest, Mapping):
            continue
        rows = manifest.get("artifacts")
        if isinstance(rows, list) and any(isinstance(row, Mapping) and "artifact_role" in row for row in rows):
            found[path.relative_to(repo_root).as_posix()] = manifest
    return found


def assert_independent(manifests: Iterable[str] | None = None, *, repo_root: Path = REPO_ROOT) -> None:
    """Raise AssertionError naming every forbidden edge across the covered lanes."""
    loaded = covered_manifests(repo_root)
    selected = list(manifests) if manifests is not None else list(loaded)
    found = [line for path in selected for line in violations(loaded[path], repo_root=repo_root)]
    if found:
        raise AssertionError("producer/oracle independence breached:\n  " + "\n  ".join(found))
