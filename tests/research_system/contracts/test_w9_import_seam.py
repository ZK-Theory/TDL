# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §9, §15, review m-2)
# Purpose: enforce that modules outside research_system/legacy/ import only projection_read plus the allowlisted legacy imports.
"""Contract test for the WP9.4-1 legacy import seam (06v §2.7, WP9.4 note §9, §15)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG_ROOT = REPO_ROOT / "research_system"
LEGACY_PREFIX = "research_system.legacy"
READ_INTERFACE = "research_system.legacy.projection_read"

# Existing non-legacy imports of research_system.legacy allowlisted by module and imported submodule (§9).
LEGACY_IMPORT_ALLOWLIST: dict[str, frozenset[str]] = {
    "research_system/cli.py": frozenset(
        {
            "research_system.legacy",
            "research_system.legacy.accepted_w9",
            "research_system.legacy.apm_inventory",
            "research_system.legacy.commands",
            "research_system.legacy.evidence",
            "research_system.legacy.export_recheck",
            "research_system.legacy.inventory",
            "research_system.legacy.preparers",
            "research_system.legacy.projection_read",
            "research_system.legacy.reader",
            "research_system.legacy.replay.driver",
            "research_system.legacy.replay.reducers",
            "research_system.legacy.runtime",
        }
    ),
    "research_system/projection/replay.py": frozenset(
        {
            "research_system.legacy.commands",
            "research_system.legacy.replay.driver",
        }
    ),
    "research_system/command/service.py": frozenset({"research_system.legacy.identities"}),
    "research_system/command/t2.py": frozenset({"research_system.legacy.identities"}),
    "research_system/discovery/routes.py": frozenset(
        {
            "research_system.legacy.identities",
            "research_system.legacy.commands",
        }
    ),
}


def _resolve_relative_base(rel_path: str, level: int) -> list[str]:
    parts = rel_path.split("/")[:-1]
    if level > 1:
        parts = parts[: len(parts) - (level - 1)]
    return parts


def _is_legacy_submodule(module_name: str) -> bool:
    if not module_name.startswith(f"{LEGACY_PREFIX}."):
        return False
    base = REPO_ROOT.joinpath(*module_name.split("."))
    return base.with_suffix(".py").is_file() or (base / "__init__.py").is_file()


def _imported_legacy_modules(source: str, rel_path: str) -> set[str]:
    """Return every ``research_system.legacy*`` module imported in ``source``."""
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == LEGACY_PREFIX or alias.name.startswith(f"{LEGACY_PREFIX}."):
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mod = node.module
            elif node.level > 0:
                base = _resolve_relative_base(rel_path, node.level)
                mod = ".".join([*base, *(node.module.split(".") if node.module else [])])
            else:
                continue
            if mod == LEGACY_PREFIX:
                for alias in node.names:
                    found.add(LEGACY_PREFIX if alias.name == "*" else f"{LEGACY_PREFIX}.{alias.name}")
            elif mod == "research_system":
                for alias in node.names:
                    if alias.name == "*":
                        found.add(LEGACY_PREFIX)
                    else:
                        candidate = f"research_system.{alias.name}"
                        if candidate == LEGACY_PREFIX or candidate.startswith(f"{LEGACY_PREFIX}."):
                            found.add(candidate)
            elif mod.startswith(f"{LEGACY_PREFIX}."):
                for alias in node.names:
                    if alias.name != "*" and _is_legacy_submodule(f"{mod}.{alias.name}"):
                        found.add(f"{mod}.{alias.name}")
                    else:
                        found.add(mod)
    return found


def _check_non_legacy_source(rel_path: str, source: str) -> list[str]:
    allowed = LEGACY_IMPORT_ALLOWLIST.get(rel_path, frozenset()) | {READ_INTERFACE}
    disallowed = sorted(_imported_legacy_modules(source, rel_path) - allowed)
    return [f"{rel_path} imports non-allowlisted legacy module {mod}" for mod in disallowed]


def test_non_legacy_modules_import_only_projection_read_or_allowlisted_modules() -> None:
    violations: list[str] = []
    for path in sorted(PKG_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith("research_system/legacy/"):
            continue
        violations.extend(_check_non_legacy_source(rel, path.read_text(encoding="utf-8")))
    assert violations == []


@pytest.mark.parametrize(
    ("rel_path", "source"),
    [
        ("research_system/command/service.py", "from research_system.legacy.replay import reducers\n"),
        ("research_system/command/service.py", "from research_system.legacy import preparers\n"),
        ("research_system/artefacts/use_resolver.py", "import research_system.legacy.identities\n"),
        ("research_system/artefacts/use_resolver.py", "from ..legacy import preparers\n"),
        ("research_system/artefacts/use_resolver.py", "from research_system import legacy\n"),
        ("research_system/authority.py", "from . import legacy\n"),
        ("research_system/authority.py", "from research_system import *\n"),
    ],
    ids=[
        "direct-replay-import",
        "from-package-preparers",
        "unlisted-importer-identities",
        "relative-import-preparers",
        "from-root-import-legacy",
        "relative-root-import-legacy",
        "wildcard-root-import",
    ],
)
def test_import_seam_check_refuses_disallowed_legacy_imports(rel_path: str, source: str) -> None:
    violations = _check_non_legacy_source(rel_path, source)
    assert len(violations) == 1
    assert rel_path in violations[0]


def test_import_seam_check_admits_projection_read_anywhere() -> None:
    violations = _check_non_legacy_source(
        "research_system/artefacts/use_resolver.py",
        "from research_system.legacy import projection_read\nimport research_system.legacy.projection_read\n",
    )
    assert violations == []


def test_import_seam_check_admits_allowlisted_submodule_and_symbol_imports() -> None:
    sub_src = "from research_system.legacy.replay import reducers\n"
    assert _imported_legacy_modules(sub_src, "research_system/cli.py") == {"research_system.legacy.replay.reducers"}
    assert _check_non_legacy_source("research_system/cli.py", sub_src) == []

    sym_src = "from research_system.legacy.replay.driver import replay_legacy\n"
    assert _imported_legacy_modules(sym_src, "research_system/projection/replay.py") == {
        "research_system.legacy.replay.driver"
    }
    assert _check_non_legacy_source("research_system/projection/replay.py", sym_src) == []
