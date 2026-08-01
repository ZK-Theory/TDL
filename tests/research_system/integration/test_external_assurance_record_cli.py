"""Exercise the bounded external assurance-record CLI seam end to end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from research_system.assurance.resolver import ControlStoreAuthorityResolver
from research_system.cli import main
from research_system.config import ControlBinding
from research_system.errors import ConfigurationError
from research_system.store.identity import initialize_control_store


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


def test_assurance_record_write_cli_persists_and_resolves(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config, control_root, authority_root = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(_record()), encoding="utf-8")

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
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                "--record",
                str(record_path),
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["record_class"] == "canonical_actor"
    assert receipt["record_id"] == RECORD_ID
    assert receipt["revision"] == 1

    resolved = ControlStoreAuthorityResolver(ControlBinding.load(config)).resolve(
        record_id=RECORD_ID,
        record_class="canonical_actor",
        authority_root=authority_root,
        phase="load",
    )
    assert resolved == _record()


def test_assurance_record_write_cli_requires_json_object(tmp_path: Path) -> None:
    config, _, _ = _config(tmp_path)
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
                "--record",
                str(record_path),
            ]
        )
