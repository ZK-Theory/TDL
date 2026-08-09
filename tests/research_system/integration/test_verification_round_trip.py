from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from research_system.methods.registration import CandidateDocumentStore, CandidateRegistration
from research_system.methods.verification_records import (
    build_operator_verification_run,
    build_verification_request,
    register_verification_record,
)
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).parents[3]


@dataclass
class Receipt:
    status: str = "accepted"


class Commands:
    def __init__(self) -> None:
        self.commands = []

    def submit(self, command):
        self.commands.append(command)
        return Receipt()


def test_request_and_operator_run_register_as_distinct_candidates(tmp_path) -> None:
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    request_id = "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b"
    run_id = "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6c"
    request = build_verification_request(
        brief_sha256="1" * 64,
        request_artefact_id=request_id,
        candidate_artefact_id="art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6d",
        script_source="assert exact_bytes",
        recorded_at="2026-08-08T12:00:00Z",
        schema_registry=schemas,
    )
    run = build_operator_verification_run(
        request=request,
        run_artefact_id=run_id,
        outcome="failed",
        exit_code=1,
        stdout_excerpt="",
        stderr_excerpt="failed",
        traceback="trace exact",
        environment_description="operator workstation",
        executed_by_actor_id="act_01978abc-1002-7000-8000-000000001002",
        executed_on="2026-08-08T12:05:00Z",
        schema_registry=schemas,
    )
    commands = Commands()
    for record, artefact_id in ((request, request_id), (run, run_id)):
        register_verification_record(
            record=record,
            schema_registry=schemas,
            registration=CandidateRegistration(
                artefact_id,
                "prj_01978abc-1001-7000-8000-000000001001",
                "act_01978abc-1002-7000-8000-000000001002",
                "agr_01978abc-1003-7000-8000-000000001003",
                "2026-08-08T12:05:00Z",
                "rm04",
                "register operator record",
                {"artefact_id": artefact_id, "authority": {"use_authority": "accepted_for_scope"}},
            ),
            document_store=CandidateDocumentStore(tmp_path),
            command_service=commands,
        )
    assert [command["payload"]["manifest"]["authority"]["use_authority"] for command in commands.commands] == [
        "candidate",
        "candidate",
    ]
    assert run["traceback"] == "trace exact"
