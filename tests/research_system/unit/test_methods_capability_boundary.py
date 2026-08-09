from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).parents[3]


def test_brief_capability_graph_has_no_execution_provider_or_network_primitive() -> None:
    paths = [
        ROOT / "research_system" / "methods" / name
        for name in ("brief.py", "importer.py", "registration.py", "verification_records.py")
    ]
    forbidden_imports = {"requests", "httpx", "socket", "subprocess", "importlib"}
    forbidden_calls = {"eval", "exec", "compile", "__import__"}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert not {alias.name.partition(".")[0] for alias in node.names} & forbidden_imports
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "").partition(".")[0] not in forbidden_imports
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls


def test_cli_names_exact_brief_handlers_and_only_fixed_git_subprocess() -> None:
    path = ROOT / "research_system" / "cli.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert {"brief_export", "brief_import"} <= names
    subprocess_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "subprocess"
    ]
    assert len(subprocess_calls) == 1
