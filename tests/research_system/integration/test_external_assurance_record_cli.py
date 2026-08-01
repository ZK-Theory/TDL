"""Exercise the bounded external assurance-record CLI seam end to end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.cli import main
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConfigurationError
from research_system.store.identity import initialize_control_store


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
RECORD_ID = "act_01978abc-2000-7000-8000-000000002000"
ROOT_GRANT_ID = "agr_01978abc-2000-7000-8000-000000002033"


def _record() -> dict[str, str]:
    return {
        "record_type": "canonical_actor",
        "actor_id": RECORD_ID,
        "actor_kind": "agent",
        "canonical_name": "Ada",
        "status": "active",
    }


def _config(tmp_path: Path) -> tuple[Path, Path, str]:
    code_root = tmp_path / "code"
    code_root.mkdir()
    control_root = tmp_path / "control"
    identity = initialize_control_store([code_root], control_root, PROJECT_ID)
    config = tmp_path / "binding.json"
    config.write_text(
        json.dumps(
            {
                "code_roots": [str(code_root.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str(SCHEMA_ROOT.resolve()),
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
        ROOT_GRANT_ID,
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


def test_assurance_record_write_cli_requires_current_publication_authority(tmp_path: Path) -> None:
    config, control_root, authority_root = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(_record()), encoding="utf-8")

    with pytest.raises(ArsError, match="authority_bootstrap_required"):
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


def test_assurance_record_write_cli_requires_json_object(tmp_path: Path) -> None:
    config, _, authority_root = _config(tmp_path)
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
