import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

import research_system.cli as cli
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Receipt
from research_system.errors import ConfigurationError
from research_system.operations.resources import TrustedRuntimeAuthority
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import initialize_control_store
from research_system.store.ledger import EventLedger
from tests.research_system.factories import PROJECT_ID


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
TASK_ID = "tsk_01978abc-3002-7000-8000-000000003002"
HOST_IDENTITY = "host:sha256:" + "a" * 64
BOOT_IDENTITY = "boot:sha256:" + "b" * 64


def _command_submit_binding(tmp_path):
    return SimpleNamespace(
        control_root=tmp_path / "control",
        project_id=PROJECT_ID,
        schema_root=SCHEMAS,
        store_identity="a" * 64,
        origin_witness=object(),
        origin_witness_path=tmp_path / "origin-witness.json",
    )


def _command_submit_inputs(tmp_path):
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
    return config, command


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


def test_restore_bind_runtime_inputs_require_exact_canonical_json(tmp_path):
    path = tmp_path / "operator-input.json"
    value = {"target_root": str(tmp_path), "status": "verified"}

    path.write_text(json.dumps(value, indent=2), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not canonical"):
        cli._read_canonical_json(path)

    path.write_bytes(canonical_bytes(value))
    assert cli._read_canonical_json(path) == value


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
    binding = _command_submit_binding(tmp_path)
    registry = SimpleNamespace(policy_revision="p0-retention-v1")
    authorizer = object()
    captured = {}

    class FakeCommandService:
        def __init__(self, *args, **kwargs):
            captured["service_kwargs"] = kwargs
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

    config, command = _command_submit_inputs(tmp_path)
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
    assert captured["service_kwargs"]["trusted_runtime_authority_provider"] is None
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"


@pytest.mark.parametrize(
    ("options", "message"),
    (
        (["--host-identity", HOST_IDENTITY], "host-identity and --boot-identity together"),
        (["--boot-identity", BOOT_IDENTITY], "host-identity and --boot-identity together"),
        (
            ["--host-identity", "host:sha256:" + "A" * 64, "--boot-identity", BOOT_IDENTITY],
            "runtime authority identities are invalid",
        ),
        (
            ["--host-identity", HOST_IDENTITY, "--boot-identity", "boot:sha256:" + "B" * 64],
            "runtime authority identities are invalid",
        ),
    ),
)
def test_command_submit_rejects_partial_or_malformed_runtime_authority_before_service(
    monkeypatch,
    tmp_path,
    options,
    message,
):
    binding = _command_submit_binding(tmp_path)
    constructed = []

    def forbidden_service(*args, **kwargs):
        constructed.append((args, kwargs))
        raise AssertionError("CommandService must not be constructed")

    monkeypatch.setattr(cli.ControlBinding, "load", lambda path: binding)
    monkeypatch.setattr(cli, "CommandService", forbidden_service)
    config, command = _command_submit_inputs(tmp_path)

    with pytest.raises(ConfigurationError, match=message):
        cli.main(
            [
                "command",
                "submit",
                "--config",
                str(config),
                "--command",
                str(command),
                *options,
            ]
        )

    assert constructed == []


def test_command_submit_runtime_authority_provider_reloads_manifest_and_rejects_drift(
    monkeypatch,
    tmp_path,
):
    binding = _command_submit_binding(tmp_path)
    first_manifest = {
        "project_id": PROJECT_ID,
        "store_identity": binding.store_identity,
        "generation": 1,
    }
    second_manifest = {
        "project_id": PROJECT_ID,
        "store_identity": binding.store_identity,
        "generation": 2,
    }
    drifted_manifest = {
        "project_id": PROJECT_ID,
        "store_identity": "c" * 64,
        "generation": 3,
    }
    manifests = [first_manifest, second_manifest, drifted_manifest]
    calls = []
    captured = {}

    class FakeCommandService:
        def __init__(self, *args, **kwargs):
            captured["provider"] = kwargs["trusted_runtime_authority_provider"]
            self.deletion_manifest_authorizer = None

        def submit(self, command):
            return Receipt(
                status="accepted",
                command_id=command["command_id"],
                payload_hash="b" * 64,
                event_batch_id=None,
                observed_stream_version=0,
            )

    def fake_load_store_manifest(control_root, *, approved_witness, approved_witness_path):
        calls.append((control_root, approved_witness, approved_witness_path))
        return manifests[len(calls) - 1]

    monkeypatch.setattr(cli.ControlBinding, "load", lambda path: binding)
    monkeypatch.setattr(cli, "CommandService", FakeCommandService)
    monkeypatch.setattr(cli, "load_store_manifest", fake_load_store_manifest)
    config, command = _command_submit_inputs(tmp_path)

    assert (
        cli.main(
            [
                "command",
                "submit",
                "--config",
                str(config),
                "--command",
                str(command),
                "--host-identity",
                HOST_IDENTITY,
                "--boot-identity",
                BOOT_IDENTITY,
            ]
        )
        == 0
    )

    provider = captured["provider"]
    first = provider()
    second = provider()
    assert first == TrustedRuntimeAuthority(
        HOST_IDENTITY,
        BOOT_IDENTITY,
        binding.store_identity,
        sha256_hex(canonical_bytes(first_manifest)),
    )
    assert second == TrustedRuntimeAuthority(
        HOST_IDENTITY,
        BOOT_IDENTITY,
        binding.store_identity,
        sha256_hex(canonical_bytes(second_manifest)),
    )
    with pytest.raises(ConfigurationError, match="store identity differs from the selected control binding"):
        provider()
    assert calls == [
        (binding.control_root, binding.origin_witness, binding.origin_witness_path),
        (binding.control_root, binding.origin_witness, binding.origin_witness_path),
        (binding.control_root, binding.origin_witness, binding.origin_witness_path),
    ]
