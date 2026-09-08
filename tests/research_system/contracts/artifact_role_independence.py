"""Role-driven producer/oracle independence checking, shared across materialization lanes.

The WP6.2 T2 lane already had this property machine-checked, but by a hand-written test naming
its two modules literally (``test_wp6_2_t2_authority_mutations.py::
test_protected_membership_expected_side_has_no_materializer_dependency``). Its sibling WP6.1 lane
pinned the same five files' bytes, declared no ``artifact_role``, and had no equivalent guard — so
the property held there by convention only, and an edit adding a derivation import to the expected
side would have passed (observation 2026-08-12-wp61-lane-lacks-t2-independence-guard).

This module derives the forbidden edges from the *declared roles* instead. A lane is covered by
declaring its roles in a contract; nothing has to be restated per lane in a test. Adding a lane is
a contract edit, not a new hand-written assertion — which is the point, because the failure mode
being guarded is exactly "the second lane nobody remembered to write the assertion for".
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]

WP6_1_ROLES_PATH = ".research-system/contracts/wp6-1-artifact-roles.yaml"
WP6_2_T2_IDENTITIES_PATH = ".research-system/contracts/wp6-2-t2-schema-identities.yaml"

#: Edges applied to any lane that declares roles but no explicit ``independence_edges`` list.
#: These are the WP6.2 T2 lane's own edges, stated once so the T2 lane needs no contract change
#: to be covered by the generic rule.
DEFAULT_INDEPENDENCE_EDGES: tuple[tuple[str, str], ...] = (
    ("independent_oracle", "schema_materializer"),
    ("schema_materializer", "independent_oracle"),
)


@dataclass(frozen=True)
class RoleDeclaration:
    """One declared artifact and the role it plays in its lane."""

    role: str
    repository_path: str
    module: str


def _load_yaml(relative_path: str, repo_root: Path) -> Mapping[str, Any]:
    """Read a contract manifest."""
    return yaml.safe_load((repo_root / relative_path).read_text(encoding="utf-8"))


def _module_name(repository_path: str) -> str:
    """Derive a dotted module name from a repository path."""
    return repository_path.removesuffix(".py").replace("/", ".")


def declarations(manifest: Mapping[str, Any]) -> list[RoleDeclaration]:
    """Return every Python artifact in `manifest` that declares a role.

    Non-Python artifacts (schemas, catalogues, `.gitattributes`) carry roles too but have no import
    graph, so they are skipped rather than treated as an empty one — an empty import set would make
    the assertion pass vacuously for them.
    """
    rows = manifest.get("artifacts") or []
    found: list[RoleDeclaration] = []
    for row in rows:
        path = row.get("repository_path", "")
        if not path.endswith(".py"):
            continue
        found.append(
            RoleDeclaration(
                role=row["artifact_role"],
                repository_path=path,
                module=row.get("module") or _module_name(path),
            )
        )
    return found


def independence_edges(manifest: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """Return the (importer_role, imported_role) pairs this lane forbids."""
    declared = manifest.get("independence_edges")
    if not declared:
        return DEFAULT_INDEPENDENCE_EDGES
    return tuple((edge["forbidden_importer_role"], edge["forbidden_imported_role"]) for edge in declared)


def imported_modules(source_path: Path) -> set[str]:
    """Return every module name imported by `source_path`, from both import forms.

    ``ImportFrom`` alone is not sufficient: a plain ``import a.b.c`` reaches the same module and
    would slip past a check that only walked ``ImportFrom`` nodes.
    """
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def violations(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    source_override: Mapping[str, Path] | None = None,
) -> list[str]:
    """Return one message per forbidden import edge found, empty when the lane is independent.

    `source_override` maps a repository path to an alternative file to parse. The negative control
    uses it to point one role at a mutated copy without writing into the real tree.
    """
    rows = declarations(manifest)
    by_role: dict[str, list[RoleDeclaration]] = {}
    for row in rows:
        by_role.setdefault(row.role, []).append(row)

    found: list[str] = []
    for importer_role, imported_role in independence_edges(manifest):
        importers = by_role.get(importer_role, [])
        imported = by_role.get(imported_role, [])
        if not importers or not imported:
            continue
        forbidden_modules = {row.module for row in imported}
        for row in importers:
            source = (source_override or {}).get(row.repository_path) or (repo_root / row.repository_path)
            for module in imported_modules(source):
                if module in forbidden_modules:
                    found.append(
                        f"{row.repository_path} ({importer_role}) imports {module} ({imported_role}) — "
                        f"the {importer_role} → {imported_role} edge is forbidden by contract"
                    )
    return found


def covered_manifests(repo_root: Path = REPO_ROOT) -> dict[str, Mapping[str, Any]]:
    """Return every role-declaring manifest this guard covers, keyed by path."""
    return {path: _load_yaml(path, repo_root) for path in (WP6_1_ROLES_PATH, WP6_2_T2_IDENTITIES_PATH)}


def assert_independent(manifests: Iterable[str] | None = None, *, repo_root: Path = REPO_ROOT) -> None:
    """Raise AssertionError naming every forbidden edge across the covered lanes."""
    loaded = covered_manifests(repo_root)
    selected = list(manifests) if manifests is not None else list(loaded)
    found = [line for path in selected for line in violations(loaded[path], repo_root=repo_root)]
    if found:
        raise AssertionError("producer/oracle independence breached:\n  " + "\n  ".join(found))
