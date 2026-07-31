import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import research_system.cli as cli
from research_system.command.models import Receipt
from research_system.errors import ConfigurationError
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import initialize_control_store
from research_system.store.ledger import EventLedger
from tests.research_system.factories import PROJECT_ID


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
TASK_ID = "tsk_01978abc-3002-7000-8000-000000003002"


def _external_v1_store(tmp_path, *, schema_bound):
    code_root = tmp_path / "code"
    code_root.mkdir()
    projection_root = code_root / ".research-system" / "projections"
    projection_root.mkdir(parents=True)
    if schema_bound:
        shutil.copytree(SCHEMAS, code_root / ".research-system" / "schemas")
    control_root = tmp_path / "control"
    initialize_control_store([code_root], control_root, PROJECT_ID)
    return code_root, control_root, projection_root


@pytest.mark.parametrize("command", ["replay", "projection"])
def test_history_commands_reject_v1_store_without_runtime_schema_authority(
    tmp_path,
    command,
    capsys,
):
    _code_root, control_root, projection_root = _external_v1_store(
        tmp_path,
        schema_bound=False,
    )
    EventLedger(
        control_root,
        PROJECT_ID,
        SchemaRegistry(SCHEMAS),
    ).append([{"event_type": "TaskCreated", "stream_id": TASK_ID}])

    argv = [command, "verify", "--control-root", str(control_root)]
    if command == "projection":
        output = projection_root / "rebuilt.json"
        argv = [command, "rebuild", "--control-root", str(control_root), "--output", str(output)]

    with pytest.raises(
        ConfigurationError,
        match="store manifest does not bind a usable runtime schema root",
    ):
        cli.main(argv)
    assert capsys.readouterr().out == ""
    if command == "projection":
        assert not output.exists()


@pytest.mark.parametrize("command", ["replay", "projection"])
def test_history_commands_accept_schema_bound_current_store(tmp_path, command):
    _code_root, control_root, projection_root = _external_v1_store(
        tmp_path,
        schema_bound=True,
    )
    argv = [command, "verify", "--control-root", str(control_root)]
    if command == "projection":
        output = projection_root / "rebuilt.json"
        argv = [command, "rebuild", "--control-root", str(control_root), "--output", str(output)]

    assert cli.main(argv) == 0
    if command == "projection":
        assert output.is_file()


def test_command_submit_derives_retention_policy_path_from_binding(
    monkeypatch,
    tmp_path,
    capsys,
):
    binding = SimpleNamespace(
        control_root=tmp_path / "control",
        project_id=PROJECT_ID,
        schema_root=SCHEMAS,
        store_identity="a" * 64,
    )
    registry = SimpleNamespace(policy_revision="p0-retention-v1")
    authorizer = object()
    captured = {}

    class FakeCommandService:
        def __init__(self, *args, **kwargs):
            self.deletion_manifest_authorizer = None

        def submit(self, command):
            assert command["payload"] == {"manifest_hash": "a" * 64}
            assert self.deletion_manifest_authorizer is authorizer
            return Receipt(
                status="accepted",
                command_id=command["command_id"],
                payload_hash="b" * 64,
                event_batch_id=None,
                observed_stream_version=0,
            )

    def fake_build_deletion_manifest_authorizer(loaded_registry, **kwargs):
        captured["registry"] = loaded_registry
        captured["kwargs"] = kwargs
        return authorizer

    monkeypatch.setattr(cli.ControlBinding, "load", lambda path: binding)
    monkeypatch.setattr(cli, "load_evidence_store_registry", lambda path, schemas: registry)
    monkeypatch.setattr(
        cli,
        "build_deletion_manifest_authorizer",
        fake_build_deletion_manifest_authorizer,
    )
    monkeypatch.setattr(cli, "CommandService", FakeCommandService)

    config = tmp_path / "binding.yaml"
    config.write_text("{}", encoding="utf-8")
    command = tmp_path / "command.json"
    command.write_text(
        json.dumps(
            {
                "command_id": "cmd_01978abc-3001-7000-8000-000000003001",
                "payload": {"manifest_hash": "a" * 64},
            }
        ),
        encoding="utf-8",
    )
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text("{}", encoding="utf-8")

    assert (
        cli.main(
            [
                "command",
                "submit",
                "--config",
                str(config),
                "--command",
                str(command),
                "--evidence-store-registry",
                str(registry_path),
            ]
        )
        == 0
    )

    assert captured["registry"] is registry
    assert captured["kwargs"] == {"retention_policy_path": SCHEMAS.parent / "evals" / "retention-policy.yaml"}
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"
