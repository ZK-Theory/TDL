import ast
import importlib
from pathlib import Path


def test_context_service_has_no_provider_or_eval_execution_imports() -> None:
    source = Path("research_system/context/service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(name.startswith(("research_system.adapters", "research_system.evals")) for name in imports)


def test_legacy_public_routing_and_dispatch_constructors_are_absent() -> None:
    engine = importlib.import_module("research_system.routing.engine")
    orchestrator = importlib.import_module("research_system.routing.orchestrator")
    coordinator = importlib.import_module("research_system.operations.coordinator")
    assert not hasattr(engine, "PreparedDispatch")
    assert not hasattr(engine, "select_route")
    assert not hasattr(orchestrator, "plan_dispatch")
    assert not hasattr(coordinator, "issue_prepared_dispatch")


def test_private_capability_and_dispatch_mints_have_one_first_party_owner() -> None:
    roots = tuple(Path("research_system").rglob("*.py"))
    capability_owners = [path for path in roots if "_CAPABILITY_MINT_KEY" in path.read_text(encoding="utf-8")]
    dispatch_constructors = [path for path in roots if "LifecycleBoundDispatch(" in path.read_text(encoding="utf-8")]
    assert capability_owners == [Path("research_system/context/service.py")]
    assert dispatch_constructors == [Path("research_system/context/service.py")]


def test_provider_command_construction_is_closed_to_typed_runners() -> None:
    constructors = {
        path.as_posix()
        for path in Path("research_system").rglob("*.py")
        if "ProviderCommand(" in path.read_text(encoding="utf-8")
    }
    assert constructors == {
        "research_system/evals/adapter_scientific_runner.py",
        "research_system/evals/executors/adapter_scientific.py",
        "research_system/evals/lifecycle.py",
        "research_system/evals/scenarios.py",
    }
    assert "ProviderCommand" not in Path("research_system/evals/variants.py").read_text(encoding="utf-8")
