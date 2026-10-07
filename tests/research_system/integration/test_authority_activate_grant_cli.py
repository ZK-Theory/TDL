"""The owner activates a scoped grant through the public CLI (P-058, 2026-10-07, census finding B-3).

``ActivateAuthorityGrant`` admission verifies an owner administration decision it loads from the control
store, and until ``ars authority activate-grant`` only internal code placed one. The census showed every
other step of the live sequence has a public path; this closes the last one. Admission is unchanged.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import research_system.cli as cli
from research_system.authority import LedgerAuthorityGrantResolver
from research_system.canonical import canonical_bytes
from research_system.config import ControlBinding
from research_system.errors import ConfigurationError
from research_system.ids import new_id
from research_system.schema_registry import runtime_schema_registry
from research_system.store.ledger import EventLedger
from tests.research_system.factories import ACTORS, PROJECT_ID, authority_bootstrap, create_task_command
from tests.research_system.integration.test_command_cli import _external_store

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
TASK_ID = "tsk_01978abc-9300-7000-8000-000000009300"


def _binding_config(tmp_path: Path, code_root: Path, control_root: Path) -> Path:
    manifest = json.loads((control_root / "manifests" / "store-identity.json").read_bytes())
    path = tmp_path / "control-binding.json"
    path.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(code_root.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str((code_root / ".research-system" / "schemas").resolve()),
                "store_identity": manifest["store_identity"],
            }
        )
    )
    return path


def _request(tmp_path: Path, **overrides) -> tuple[Path, dict]:
    value = {
        "owner_actor_id": authority_bootstrap()["owner_actor_id"],
        "authority_grant_id": new_id("authority_grant"),
        "actor_id": ACTORS["actor-a"],
        "allowed_actor_classes": ["human"],
        "command_types": ["CreateTask"],
        "subject_scope": {"project_id": PROJECT_ID, "subject": {"kind": "task", "id": TASK_ID}},
        "risk_ceiling": "R3",
        "effective_at": "2026-01-01T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
        "decided_at": "2026-10-07T11:55:00Z",
        "reason": "activate the Task creation grant for the fresh run",
        **overrides,
    }
    path = tmp_path / f"grant-request-{value['authority_grant_id']}.json"
    path.write_bytes(canonical_bytes(value))
    return path, value


def _events(control_root: Path, code_root: Path) -> int:
    schemas = runtime_schema_registry(code_root / ".research-system" / "schemas")
    return EventLedger(control_root, PROJECT_ID, schemas).snapshot().global_position


def _decisions(control_root: Path) -> list[Path]:
    return sorted((control_root / "objects" / "assurance_record").glob("*")) if (
        control_root / "objects" / "assurance_record"
    ).exists() else []  # fmt: skip


def test_the_owner_activates_a_grant_that_then_authorizes_its_command(tmp_path, monkeypatch, capsys):
    code_root, control_root, _projection = _external_store(tmp_path, monkeypatch, schema_bound=True)
    monkeypatch.setattr(cli, "_authority_clock", lambda: NOW)  # Fixture commands carry fixed timestamps.
    config = _binding_config(tmp_path, code_root, control_root)
    request_path, request = _request(tmp_path)

    assert cli.main(["authority", "activate-grant", "--config", str(config), "--request", str(request_path)]) == 0
    activated = json.loads(capsys.readouterr().out)
    assert activated["status"] == "accepted"
    binding = ControlBinding.load(config)
    resolver = LedgerAuthorityGrantResolver(
        binding.control_root,
        PROJECT_ID,
        binding.store_identity,
        runtime_schema_registry(binding.schema_root),
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    assert resolver.scoped_grant_identity(request["authority_grant_id"]).actor_id == ACTORS["actor-a"]
    position = _events(control_root, code_root)

    # The exact retry writes the same decision bytes and reads the committed receipt; nothing is appended.
    assert cli.main(["authority", "activate-grant", "--config", str(config), "--request", str(request_path)]) == 0
    assert json.loads(capsys.readouterr().out)["command_receipt"] == activated["command_receipt"]
    assert _events(control_root, code_root) == position

    # The activated grant authorizes its command through the public command path.
    command = create_task_command(new_id("command"), "activate-grant:create-task", TASK_ID, {"title": "Fresh run"})
    command["authority_grant_id"] = request["authority_grant_id"]
    command["submitted_at"] = "2026-10-07T11:58:00Z"
    command_path = tmp_path / "create-task.json"
    command_path.write_bytes(canonical_bytes(command))
    assert cli.main(["command", "submit", "--config", str(config), "--command", str(command_path)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"


@pytest.mark.parametrize(
    ("override", "message"),
    (
        ({"owner_actor_id": ACTORS["actor-b"]}, "only the authority owner"),
        (
            {"subject_scope": {"project_id": "prj_01978abc-1000-7000-8000-000000009999", "subject": {}}},
            "must name the bound project",
        ),
    ),
)
def test_a_grant_request_that_is_not_the_owners_writes_nothing(tmp_path, monkeypatch, override, message):
    code_root, control_root, _projection = _external_store(tmp_path, monkeypatch, schema_bound=True)
    monkeypatch.setattr(cli, "_authority_clock", lambda: NOW)
    config = _binding_config(tmp_path, code_root, control_root)
    request_path, _request_value = _request(tmp_path, **override)
    before = (_events(control_root, code_root), _decisions(control_root))
    with pytest.raises(ConfigurationError, match=message):
        cli.main(["authority", "activate-grant", "--config", str(config), "--request", str(request_path)])
    assert (_events(control_root, code_root), _decisions(control_root)) == before
