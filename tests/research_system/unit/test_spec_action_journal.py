from __future__ import annotations

import json

import pytest

from research_system.discovery.spec_action_journal import read_preparation
from research_system.errors import IntegrityError


def test_spec_action_journal_maps_noncanonical_json_values_to_integrity_error(tmp_path) -> None:
    journal = tmp_path / "runtime" / "spec-flow-preparations" / "bootstrap_genesis.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        json.dumps(
            {
                "schema_id": "ars://internal/spec-flow-action-preparation",
                "schema_version": "1.0.0",
                "route_id": "SPEC-GATE6-RUN-V1",
                "action": "bootstrap_genesis",
                "packet": {
                    "schema_id": "ars://portfolio/spec-flow-action",
                    "schema_version": "1.0.0",
                    "route_id": "SPEC-GATE6-RUN-V1",
                    "action": "bootstrap_genesis",
                    "retry_id": "spec-flow:bootstrap_genesis:invalid",
                    "commands": [1.5],
                    "document": None,
                    "registration": None,
                },
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    with pytest.raises(IntegrityError, match="journal is invalid"):
        read_preparation(tmp_path, "bootstrap_genesis")
