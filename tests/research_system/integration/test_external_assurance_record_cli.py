"""Exercise the bounded external assurance-record CLI seam end to end."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from research_system.cli import main
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConfigurationError
from research_system.authority import initialize_authority_control_store
from tests.research_system.factories import (
    ROOT_AUTHORITY_GRANT_ID,
    authority_bootstrap,
    authority_bootstrap_sha256,
)


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


def _publication_args(store_identity: str, record_path: Path) -> list[str]:
    return [
        "--caller-actor-id",
        RECORD_ID,
        "--caller-actor-class",
        "agent",
        "--authority-grant-id",
        "agr_01978abc-2000-7000-8000-000000002030",
        "--record-action",
        "create",
        "--project-id",
        PROJECT_ID,
        "--store-identity",
        store_identity,
        "--authority-root",
        ROOT_AUTHORITY_GRANT_ID,
        "--canonical-sha256",
        sha256_hex(canonical_bytes(_record())),
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
