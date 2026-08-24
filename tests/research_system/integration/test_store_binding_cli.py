from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import research_system.cli as cli


@pytest.mark.parametrize(
    ("command", "reader_name", "service_method"),
    (
        ("advance-binding", "read_advance_intent", "advance"),
        ("repair-binding", "read_repair_intent", "repair"),
    ),
)
def test_store_binding_cli_routes_typed_intent_to_one_public_service_method(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: str,
    reader_name: str,
    service_method: str,
) -> None:
    """Remediation-red: binding commands never construct a generic command service."""

    intent_path = tmp_path / "intent.json"
    intent = SimpleNamespace(
        control_root=tmp_path / "control",
        expected_project_id="prj_01978abc-0001-7000-8000-000000000001",
        expected_store_identity="a" * 64,
    )
    calls: list[object] = []

    def read_typed(supplied: Path) -> object:
        calls.append(("read", supplied))
        return intent

    class FakeStoreBindingService:
        def __init__(self, control_root: Path, project_id: str, store_identity: str) -> None:
            calls.append(("init", control_root, project_id, store_identity))

        def advance(self, supplied: object) -> dict[str, str]:
            calls.append(("advance", supplied))
            return {"status": "advanced"}

        def repair(self, supplied: object) -> dict[str, str]:
            calls.append(("repair", supplied))
            return {"status": "repaired"}

    monkeypatch.setattr(cli, reader_name, read_typed)
    monkeypatch.setattr(cli, "StoreBindingService", FakeStoreBindingService)

    assert cli.main(["store", command, "--intent", str(intent_path)]) == 0
    assert calls == [
        ("read", intent_path),
        ("init", intent.control_root, intent.expected_project_id, intent.expected_store_identity),
        (service_method, intent),
    ]
    assert json.loads(capsys.readouterr().out) == {"status": "advanced" if service_method == "advance" else "repaired"}


@pytest.mark.parametrize(
    ("argv", "legacy_option"),
    (
        (
            [
                "store",
                "backup",
                "--operator-config",
                "operator.json",
                "--request",
                "request.json",
                "--registry",
                "registry.yaml",
                "--destination-root",
                "destination",
            ],
            "--config",
        ),
        (
            [
                "store",
                "verify-restore",
                "--operator-config",
                "operator.json",
                "--command",
                "command.json",
                "--target-root",
                "target",
                "--receipt",
                "receipt.json",
                "--snapshot",
                "snapshot.json",
                "--endpoint-ownership",
                "endpoint.json",
                "--artefact-manifest",
                "artefacts.json",
                "--registry",
                "registry.yaml",
            ],
            "--config",
        ),
        (["replay", "verify", "--operator-config", "operator.json"], "--control-root"),
        (
            [
                "projection",
                "rebuild",
                "--operator-config",
                "operator.json",
                "--output",
                "projection.json",
            ],
            "--control-root",
        ),
    ),
)
def test_gate6_operator_routes_are_exclusive_from_local_administration(
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    legacy_option: str,
) -> None:
    """Remediation-red: exactly four consumers expose the admitted Gate 6 route."""

    parser = cli._parser()
    parsed = parser.parse_args(argv)
    assert parsed.operator_config == Path("operator.json")

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([*argv, legacy_option, "legacy"])
    assert exc_info.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err
