from __future__ import annotations

import json
from datetime import UTC, datetime

import research_system.store.binding_repair as repair_module
from research_system import cli
from research_system.canonical import canonical_bytes
from tests.research_system.store.test_binding_repair import _fixture


def test_cli_executes_typed_repair_and_returns_same_receipt_on_retry(tmp_path, monkeypatch, capsys):
    _initialized, _witness, _target, _candidate, _foundation, intent = _fixture(tmp_path, monkeypatch)
    intent_path = tmp_path / "repair-intent.json"
    intent_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": repair_module.COMMAND_SCHEMA_ID,
                "schema_version": "1.0.0",
                "command_type": "RepairStoreBinding",
                **intent.semantic_payload(),
            }
        )
    )
    monkeypatch.setattr(repair_module, "datetime", _FixedDateTime)
    assert cli.main(["store", "repair-binding", "--intent", str(intent_path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert cli.main(["store", "repair-binding", "--intent", str(intent_path)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second == first


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 8, 14, tzinfo=UTC)
