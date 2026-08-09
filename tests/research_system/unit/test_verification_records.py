from __future__ import annotations

from pathlib import Path

import pytest

from research_system.errors import ArsError
from research_system.methods.verification_records import (
    build_operator_verification_run,
    build_verification_request,
)
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
REQUEST = "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b"
CANDIDATE = "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6c"
RUN = "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6d"


def test_verification_records_are_non_executing_and_script_bound() -> None:
    registry = SchemaRegistry(SCHEMAS)
    request = build_verification_request(
        brief_sha256="1" * 64,
        request_artefact_id=REQUEST,
        candidate_artefact_id=CANDIDATE,
        script_source="assert candidate_hash",
        recorded_at="2026-08-08T12:00:00Z",
        schema_registry=registry,
    )
    run = build_operator_verification_run(
        request=request,
        run_artefact_id=RUN,
        outcome="passed",
        exit_code=0,
        stdout_excerpt="ok",
        stderr_excerpt="",
        traceback="",
        environment_description="operator workstation",
        executed_by_actor_id="act_01978abc-1002-7000-8000-000000001002",
        executed_on="2026-08-08T12:05:00Z",
        schema_registry=registry,
    )

    assert request["script_sha256"] == run["script_sha256"]
    assert run["attestation"] == "operator_self_attested"
    assert "interpreter" not in request


def test_operator_run_rejects_changed_script_and_execution_fields() -> None:
    registry = SchemaRegistry(SCHEMAS)
    request = build_verification_request(
        brief_sha256="1" * 64,
        request_artefact_id=REQUEST,
        candidate_artefact_id=CANDIDATE,
        script_source="assert candidate_hash",
        recorded_at="2026-08-08T12:00:00Z",
        schema_registry=registry,
    )
    with pytest.raises(ArsError, match="script hash"):
        build_operator_verification_run(
            request={**request, "script_sha256": "0" * 64},
            run_artefact_id=RUN,
            outcome="passed",
            exit_code=0,
            stdout_excerpt="ok",
            stderr_excerpt="",
            traceback="",
            environment_description="operator workstation",
            executed_by_actor_id="act_01978abc-1002-7000-8000-000000001002",
            executed_on="2026-08-08T12:05:00Z",
            schema_registry=registry,
        )
