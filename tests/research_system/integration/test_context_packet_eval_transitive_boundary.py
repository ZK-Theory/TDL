import ast
from pathlib import Path


def test_context_service_has_no_provider_or_eval_execution_imports() -> None:
    source = Path("research_system/context/service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(name.startswith(("research_system.adapters", "research_system.evals")) for name in imports)
