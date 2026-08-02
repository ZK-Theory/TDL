"""Exercise the bounded external assurance-record CLI seam end to end."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from research_system.cli import main
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.assurance.external_records import ExternalAssuranceRecordStore
from research_system.errors import ArsError, ConfigurationError
from research_system.authority import initialize_authority_control_store
from research_system.store.identity import load_store_manifest
from research_system.store.objects import ObjectStore
from tests.research_system.factories import (
    ROOT_AUTHORITY_GRANT_ID,
    authority_bootstrap,
    authority_bootstrap_sha256,
)
from tests.research_system.integration.test_external_assurance_record_publication import _activation_case


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
RECORD_ID = "act_01978abc-2000-7000-8000-000000002000"


def _record() -> dict[str, str]:
    return {
        "record_type": "canonical_actor",
        "actor_id": RECORD_ID,
        "actor_kind": "agent",
        "canonical_name": "Ada",
        "status": "active",
    }


def _config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, str]:
    code_root = tmp_path / "code"
    schema_root = code_root / ".research-system" / "schemas"
    schema_root.mkdir(parents=True)
    for source in (REPO_ROOT / ".research-system" / "schemas").iterdir():
        target = schema_root / source.name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            target.write_bytes(source.read_bytes())
    shutil.copytree(
        REPO_ROOT / ".research-system" / "contracts",
        code_root / ".research-system" / "contracts",
    )
    control_root = tmp_path / "control"
    origin_authority_root = tmp_path / "origin-authority"
    origin_authority_root.mkdir()
    bootstrap = authority_bootstrap()
    identity = initialize_authority_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        canonical_schema_root=schema_root,
        origin_authority_root=origin_authority_root,
    )
    foundation_path = code_root / ".research-system" / "config" / "foundation.yaml"
    foundation_path.parent.mkdir()
    foundation = {
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "control_root": str(control_root.resolve()),
        "control_root_required": True,
        "store_identity": str(identity),
        "endpoint_scheme": "local-cli",
        "canonical_hash": "sha256",
        "canonical_uri": "local-cli://control",
        "canonical_tail_position": 0,
        "canonical_tail_hash": "0" * 64,
        "code_roots": [str(code_root.resolve())],
        "schema_root": str(schema_root.resolve()),
        "origin_authority_root": str(origin_authority_root.resolve()),
        "origin_witness_path": str(identity.witness_path.resolve()),
        "origin_witness_sha256": identity.witness.raw_sha256,
    }
    foundation["foundation_sha256"] = sha256_hex(canonical_bytes(foundation))
    foundation_path.write_text(yaml.safe_dump(foundation, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr("research_system.config.canonical_foundation_path", lambda: foundation_path)
    config = tmp_path / "binding.json"
    config.write_text(
        json.dumps(
            {
                "code_roots": [str(code_root.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str(schema_root.resolve()),
                "store_identity": identity,
            }
        ),
        encoding="utf-8",
    )
    return config, control_root, identity


def _publication_args(
    store_identity: str,
    record_path: Path,
    *,
    record: dict[str, str] | None = None,
    caller_actor_class: str = "agent",
    caller_actor_id: str = RECORD_ID,
    authority_grant_id: str = "agr_01978abc-2000-7000-8000-000000002030",
    authority_root: str = ROOT_AUTHORITY_GRANT_ID,
) -> list[str]:
    record = _record() if record is None else record
    return [
        "--caller-actor-id",
        caller_actor_id,
        "--caller-actor-class",
        caller_actor_class,
        "--authority-grant-id",
        authority_grant_id,
        "--record-action",
        "create",
        "--project-id",
        PROJECT_ID,
        "--store-identity",
        store_identity,
        "--authority-root",
        authority_root,
        "--canonical-sha256",
        sha256_hex(canonical_bytes(record)),
        "--task-id",
        "tsk_01978abc-2000-7000-8000-000000002031",
        "--session-id",
        "ctx_01978abc-2000-7000-8000-000000002032",
        "--required-risk",
        "R1",
        "--occurred-at",
        "2026-07-18T08:20:00Z",
        "--record",
        str(record_path),
    ]


@pytest.mark.integration
def test_assurance_record_write_cli_requires_current_publication_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, control_root, authority_root = _config(tmp_path, monkeypatch)
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(_record()), encoding="utf-8")

    with pytest.raises(ArsError, match="scoped authority grant is not activated"):
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                *_publication_args(authority_root, record_path),
            ]
        )
    assert not (control_root / "objects" / "canonical_actor" / RECORD_ID).exists()


@pytest.mark.integration
def test_assurance_record_write_cli_requires_json_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config, _, authority_root = _config(tmp_path, monkeypatch)
    record_path = tmp_path / "record.json"
    record_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must contain an object"):
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                *_publication_args(authority_root, record_path),
            ]
        )


def test_assurance_record_write_cli_rejects_unknown_caller_actor_class(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["assurance-record", "write", "--caller-actor-class", "robot"])

    assert exc_info.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


@pytest.mark.integration
def test_assurance_record_write_cli_persists_activated_grant_receipt(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_root, _, resolver, _, service, command = _activation_case(tmp_path, "external")
    assert service.submit(command).status == "accepted"
    grant = command["payload"]["new_grant"]
    assert isinstance(grant, dict)
    caller_actor_id = str(grant["actor_id"])
    record_id = str(grant["subject_scope"]["subject"]["id"])
    manifest = load_store_manifest(control_root)
    shutil.copytree(
        REPO_ROOT / ".research-system" / "contracts",
        Path(manifest["schema_root"]).parent / "contracts",
    )
    config = tmp_path / "binding.json"
    config.write_text(
        json.dumps(
            {
                "code_roots": manifest["code_roots"],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": manifest["schema_root"],
                "store_identity": manifest["store_identity"],
            }
        ),
        encoding="utf-8",
    )
    record = {**_record(), "actor_id": record_id, "actor_kind": "human"}
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")

    class FixedClockExternalAssuranceRecordStore(ExternalAssuranceRecordStore):
        def __init__(self, binding) -> None:
            super().__init__(binding, clock=lambda: datetime(2026, 7, 12, 12, tzinfo=timezone.utc))

    monkeypatch.setattr("research_system.cli.ExternalAssuranceRecordStore", FixedClockExternalAssuranceRecordStore)

    assert (
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                record_id,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                *_publication_args(
                    manifest["store_identity"],
                    record_path,
                    record=record,
                    caller_actor_class="human",
                    caller_actor_id=caller_actor_id,
                    authority_grant_id=command["target_stream_id"],
                    authority_root=resolver.administration_context().root_grant_id,
                ),
            ]
        )
        == 0
    )

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["record_class"] == "canonical_actor"
    assert receipt["record_id"] == record_id
    assert receipt["revision"] == 1
    assert receipt["canonical_sha256"] == sha256_hex(canonical_bytes(record))
    assert receipt["caller_actor_id"] == caller_actor_id
    assert receipt["record_action"] == "create"
    assert ObjectStore(control_root).read("canonical_actor", record_id, 1) == record
