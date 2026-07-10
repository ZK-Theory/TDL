import json
from pathlib import Path
from types import SimpleNamespace

import research_system.cli as cli
from research_system.command.models import Receipt
from tests.research_system.factories import PROJECT_ID


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"


def test_command_submit_derives_retention_policy_path_from_binding(
    monkeypatch,
    tmp_path,
    capsys,
):
    binding = SimpleNamespace(
        control_root=tmp_path / "control",
        project_id=PROJECT_ID,
        schema_root=SCHEMAS,
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

    assert cli.main(
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
    ) == 0

    assert captured["registry"] is registry
    assert captured["kwargs"] == {
        "retention_policy_path": SCHEMAS.parent / "evals" / "retention-policy.yaml"
    }
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"
