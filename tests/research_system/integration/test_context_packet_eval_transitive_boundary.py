import ast
import importlib
from pathlib import Path

import pytest

from research_system.errors import ArsError


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


def test_parser_derived_eval_roots_have_exact_fail_closed_classification() -> None:
    cli = importlib.import_module("research_system.cli")
    parser = cli._parser()
    commands = {
        "validate": ["eval", "validate", "--catalogue", "catalogue.yaml"],
        "calibrate": ["eval", "calibrate", "--coverage", "coverage.yaml", "--transport", "fake"],
        "run": ["eval", "run", "--coverage", "coverage.yaml", "--transport", "fake"],
        "publish-release": [
            "eval",
            "publish-release",
            "--config",
            "config.json",
            "--actor-id",
            "actor-1",
            "--authority-grant-id",
            "grant-1",
            "--evaluation-runs",
            "runs.json",
            "--output",
            "output.json",
        ],
        "release": ["eval", "release", "--config", "config.json", "--evaluation-runs", "runs.json"],
        "retention.validate": ["eval", "retention", "validate", "--policy", "policy.yaml"],
    }
    observed = {
        name: cli.require_eval_root_execution_class(parser.parse_args(argv).handler) for name, argv in commands.items()
    }
    assert observed == {
        "validate": "pure_observation",
        "calibrate": "classified_dispatch",
        "run": "classified_dispatch",
        "publish-release": "classified_dispatch",
        "release": "pure_observation",
        "retention.validate": "pure_observation",
    }
    with pytest.raises(ArsError, match="unclassified eval CLI root"):
        cli.require_eval_root_execution_class(lambda _args: 0)


def test_eval_validate_parser_root_cannot_reach_execution_or_provider_seams(monkeypatch) -> None:
    cli = importlib.import_module("research_system.cli")
    executors = importlib.import_module("research_system.evals.executors")
    service = importlib.import_module("research_system.context.service")
    routing = importlib.import_module("research_system.routing.engine")
    coordinator = importlib.import_module("research_system.operations.coordinator")
    provider = importlib.import_module("research_system.adapters.provider")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("eval validate reached an execution seam")

    monkeypatch.setattr(executors, "require_executor", forbidden)
    monkeypatch.setattr(service.ContextLifecycleService, "plan_dispatch", forbidden)
    monkeypatch.setattr(service.ContextLifecycleService, "prevalidate_dispatch", forbidden)
    monkeypatch.setattr(routing, "_select_route", forbidden)
    monkeypatch.setattr(coordinator, "issue_lifecycle_dispatch", forbidden)
    monkeypatch.setattr(provider.ProviderAdapter, "issue", forbidden)
    catalogue = Path(".research-system/evals/catalogue.yaml").resolve()
    assert cli.main(["eval", "validate", "--catalogue", str(catalogue)]) == 0


def test_eval_parser_root_removed_from_classification_fails_before_handler(monkeypatch, capsys) -> None:
    cli = importlib.import_module("research_system.cli")
    monkeypatch.delitem(cli._EVAL_ROOT_EXECUTION_CLASSES, cli._eval_validate)
    assert cli.main(["eval", "validate", "--catalogue", "missing.yaml"]) == 1
    assert "unclassified eval CLI root" in capsys.readouterr().err
