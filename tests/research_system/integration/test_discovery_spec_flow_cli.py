from __future__ import annotations

import json
import hashlib
import shutil
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import research_system.cli as cli
import research_system.discovery.authority as discovery_authority_module
import research_system.discovery.operator as discovery_operator_module
import research_system.discovery.spec_flow as spec_flow_module
import research_system.methods.registration as registration_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import replay_control_plane
from research_system.command.service import CommandService
from research_system.errors import ConfigurationError, ConflictError, IntegrityError
from research_system.artefacts.authority import ArtefactAuthorityContractLoader
from research_system.artefacts.runtime import ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT
from research_system.artefacts.use_resolver import predicate_reference
from research_system.discovery.operator import load_discovery_operator
from research_system.discovery.assay_authority import assay_reconstruction_sha256
from research_system.discovery.authority import subject_sha256, validate_portable_path_subject
from research_system.discovery.commands import discovery_resolve_transaction_ids
from research_system.discovery.dossier import canonical_dossier_hash
from research_system.discovery.replay.driver import replay_discovery
from research_system.discovery.spec_flow import SpecFlow, _rows, build_spec_authority_subject
from research_system.discovery.routes import shared_event_partition
from research_system.context.spec_bridge import _stable_id as _stable_context_id
from research_system.context.spec_bridge import derive_spec_owner_context_id
from research_system.ids import new_id
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    RawContentPublication,
    publish_registered_raw_content,
    register_candidate_document,
)
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import (
    ACTORS,
    PROJECT_ID,
    GovernedTestCommandService,
    activate_lifecycle_grant,
)
from tests.research_system.integration.test_artefact_authority_commands import artefact_manifest
from tests.research_system.integration.test_discovery_operator_cli import (
    REPOSITORY_ROOT,
    _run_git,
    _tree_snapshot,
    operator_inputs as _operator_inputs_fixture,
)
from tests.research_system.integration.test_wp6_6_discovery_runtime import (
    ACTOR_ID as ASSAY_PRODUCER_ACTOR,
    ASSAY_AUTHORITY_ACTORS,
    C1_ATTEMPT_ID,
    C1_LEASE_ID,
    C1_RESOURCE_GRANT_ID,
    C1_TRUSTED_RUNTIME_AUTHORITY,
    _promotion_relation,
    _ref,
    _scorecard,
    _seed_running_attempt,
)


ROUTE_DIRECTORY = Path(".research-system/contracts/wp6-6/spec-gate6-run-v1")
ASSAY_RUBRIC_PATH = Path(".research-system/contracts/wp6-6/assay-rubric-content-v1.json")
ASSAY_SCOPE_PATH = Path(".research-system/contracts/wp6-6/assay-evidence-scope-content-v1.json")
REVIEWER_ACTOR = "act_019ffe2b-fd4b-7000-8000-000000000901"


def test_brief_authority_targets_exclude_already_reviewed_and_accepted_history():
    projection = {
        "artefact_streams": {
            "art_reviewed": {
                "manifest": {"artefact_type": "methods_asset"},
                "scientific_reviews": [{"review_id": "rev_existing"}],
                "use_authority": "accepted_for_scope",
            },
            "art_pending_review": {
                "manifest": {"artefact_type": "spec_operator_source"},
                "scientific_reviews": [],
                "use_authority": "candidate",
            },
            "art_pending_use": {
                "manifest": {"artefact_type": "spec_operator_source"},
                "scientific_reviews": [{"review_id": "rev_new"}],
                "use_authority": "candidate",
            },
        }
    }

    assert set(SpecFlow._pending_brief_input_authority_states(projection, "RecordScientificReview")) == {
        "art_pending_review"
    }
    assert set(SpecFlow._pending_brief_input_authority_states(projection, "SetArtefactUseAuthority")) == {
        "art_pending_review",
        "art_pending_use",
    }


@pytest.fixture
def spec_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Synthetic governed fixture; it is implementation proof, not Gate 6 proof."""

    operator_inputs = _operator_inputs_fixture.__wrapped__(tmp_path, monkeypatch)
    repository_root = Path(operator_inputs["config"]["repository_root"])
    for source in (REPOSITORY_ROOT / ROUTE_DIRECTORY).iterdir():
        target = repository_root / ROUTE_DIRECTORY / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for relative in (ASSAY_RUBRIC_PATH, ASSAY_SCOPE_PATH):
        target = repository_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative, target)
    shutil.copytree(
        REPOSITORY_ROOT / ".research-system" / "methods",
        repository_root / ".research-system" / "methods",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        REPOSITORY_ROOT / ".research-system" / "schemas" / "methods",
        repository_root / ".research-system" / "schemas" / "methods",
        dirs_exist_ok=True,
    )
    _run_git(
        repository_root,
        "add",
        ROUTE_DIRECTORY.as_posix(),
        ASSAY_RUBRIC_PATH.as_posix(),
        ASSAY_SCOPE_PATH.as_posix(),
        ".research-system/methods",
        ".research-system/schemas/methods",
    )
    _run_git(repository_root, "commit", "--quiet", "--amend", "--no-edit")
    packet_path = tmp_path / "spec-action.json"
    packet = {
        "schema_id": "ars://portfolio/spec-flow-action",
        "schema_version": "1.0.0",
        "route_id": "SPEC-GATE6-RUN-V1",
        "action": "bootstrap_genesis",
        "retry_id": "pending",
        "commands": [operator_inputs["command"]],
        "document": None,
        "registration": None,
    }
    retry_preimage = {key: value for key, value in packet.items() if key != "retry_id"}
    packet["retry_id"] = f"spec-flow:bootstrap_genesis:{sha256_hex(canonical_bytes(retry_preimage))}"
    packet_path.write_bytes(canonical_bytes(packet))
    return {**operator_inputs, "packet": packet, "packet_path": packet_path}


def _status_argv(inputs: dict[str, Any]) -> list[str]:
    return ["discovery", "spec", "status", "--operator-config", str(inputs["config_path"])]


def _advance_argv(inputs: dict[str, Any], action: str = "bootstrap_genesis") -> list[str]:
    return [
        "discovery",
        "spec",
        "advance",
        "--operator-config",
        str(inputs["config_path"]),
        "--action",
        action,
        "--input",
        str(inputs["packet_path"]),
    ]


def _refresh_retry_id(packet: dict[str, Any]) -> None:
    preimage = {key: value for key, value in packet.items() if key != "retry_id"}
    packet["retry_id"] = f"spec-flow:{packet['action']}:{sha256_hex(canonical_bytes(preimage))}"


def _write_action(
    inputs: dict[str, Any],
    action: str,
    *,
    commands: list[dict[str, Any]] | None = None,
    document: dict[str, Any] | None = None,
    registration: dict[str, Any] | None = None,
) -> None:
    packet = {
        "schema_id": "ars://portfolio/spec-flow-action",
        "schema_version": "1.0.0",
        "route_id": "SPEC-GATE6-RUN-V1",
        "action": action,
        "retry_id": "pending",
        "commands": commands or [],
        "document": document,
        "registration": registration,
    }
    _refresh_retry_id(packet)
    inputs["packet"] = packet
    inputs["packet_path"].write_bytes(canonical_bytes(packet))


def _artefact_command(
    *,
    command_type: str,
    artefact_id: str,
    actor_id: str,
    grant_id: str,
    version: int,
    payload: dict[str, Any],
    suffix: int,
) -> dict[str, Any]:
    return {
        "command_id": f"cmd_019ffe2b-fd4b-7000-8000-{suffix:012d}",
        "command_type": command_type,
        "schema_id": f"ars://core/command/{command_type}",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-14T12:00:00Z",
        "actor_id": actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": grant_id,
        "target_stream_id": artefact_id,
        "expected_stream_version": version,
        "idempotency_key": f"spec-input:{command_type}:{artefact_id}",
        "correlation_id": "spec-input-authority",
        "causation_id": None,
        "reason": "Govern exact SPEC brief input.",
        "evidence_refs": list(payload.get("evidence_refs", [])),
        "payload": payload,
        "project_id": PROJECT_ID,
    }


def _governed_submit(
    inputs: dict[str, Any], command: dict[str, Any], *, subject_kind: str, subject_id: str | None = None
) -> Any:
    grant_id = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind=subject_kind,
        subject_id=subject_id or command["target_stream_id"],
        actor_id=command["actor_id"],
        allowed_actor_classes=(("human",) if command["actor_id"] == ACTORS["actor-a"] else ("agent",)),
        command_types=(command["command_type"],),
        grant_id=new_id("authority_grant"),
    )
    command["authority_grant_id"] = grant_id
    return load_discovery_operator(inputs["config_path"]).submit(command)


def _route_command(
    command_type: str, target: str, version: int, row: str, payload: dict[str, Any], actor: str
) -> dict[str, Any]:
    return {
        "command_id": new_id("command"),
        "command_type": command_type,
        "actor_id": actor,
        "authority_grant_id": "agr_pending",
        "idempotency_key": f"spec-e2e:{row}:{target}:{version}",
        "target_stream_id": target,
        "expected_stream_version": version,
        "payload": {"row_id": row, **payload},
    }


def _accepted_route_authority(inputs: dict[str, Any], kind: str, offset: int) -> None:
    repository_root = Path(inputs["config"]["repository_root"])
    subject = build_spec_authority_subject(repository_root, kind)
    relative = ROUTE_DIRECTORY / (
        "spec-dossier-expected-set-authority.json"
        if kind == "dossier_expected_set"
        else "spec-path-registration-authority.json"
    )
    raw = (repository_root / relative).read_bytes()
    subject.update(
        authority_file_path=relative.as_posix(),
        authority_file_size=len(raw),
        authority_file_sha256=hashlib.sha256(raw).hexdigest(),
        authority_file_git_commit=_run_git(repository_root, "rev-parse", "HEAD"),
        authority_file_git_blob=_run_git(repository_root, "rev-parse", f"HEAD:{relative.as_posix()}"),
    )
    subject["subject_sha256"] = subject_sha256(subject)
    stream = f"obj_019ffe2b-fd4b-7000-8000-{offset:012d}"
    review = f"rev_019ffe2b-fd4b-7000-8000-{offset:012d}"
    decision = f"dec_019ffe2b-fd4b-7000-8000-{offset:012d}"
    base = 110 if kind == "dossier_expected_set" else 116
    actors = [f"act_019ffe2b-fd4b-7000-8000-{offset + index:012d}" for index in range(6)]
    actors[-1] = ACTORS["actor-a"]
    steps = (
        (
            "RegisterDossierExpectedSetContent"
            if kind == "dossier_expected_set"
            else "RegisterPathRegistrationContent",
            stream,
            0,
            {"subject": subject},
            "scope_definition",
        ),
        ("ObserveW11AuthorityFile", stream, 1, {"subject_sha256": subject["subject_sha256"]}, "scope_definition"),
        ("RequestW11AuthorityReview", review, 0, {"reviewer_actor_id": actors[3]}, "review"),
        (
            "RecordW11AuthorityReview",
            review,
            1,
            {
                "verdict": "approve",
                "unchanged_subject_sha256": subject["subject_sha256"],
                "unchanged_file_sha256": subject["authority_file_sha256"],
                "reconstruction_sha256": "5" * 64,
            },
            "review",
        ),
        (
            "ProposeW11AuthorityDecision",
            decision,
            0,
            {"decision_id": decision, "proposed_decision": "accept"},
            "decision",
        ),
        (
            "ResolveDecision",
            decision,
            1,
            {"decision_id": decision, "decision": "accept", "transaction_id": f"txn:{kind}"},
            "decision",
        ),
    )
    for index, (command_type, target, version, value, subject_kind) in enumerate(steps):
        result = _governed_submit(
            inputs,
            _route_command(
                command_type,
                target,
                version,
                f"OR-{base + index:03d}",
                {"authority_kind": kind, **value},
                actors[index],
            ),
            subject_kind=subject_kind,
        )
        assert result.status == "accepted"


def _accept_assay_authority(inputs: dict[str, Any], *, through_index: int | None = None) -> tuple[str, str] | None:
    repository_root = Path(inputs["config"]["repository_root"])
    rubric = json.loads((repository_root / ASSAY_RUBRIC_PATH).read_bytes())
    scope = json.loads((repository_root / ASSAY_SCOPE_PATH).read_bytes())
    review = "rev_019ffe2b-fd4b-7000-8000-000000000105"
    decision = "dec_019ffe2b-fd4b-7000-8000-000000000107"
    producer_ref = {"id": ACTORS["actor-a"], "record_revision": 1, "content_hash": "3" * 64}
    rubric_observer, scope_observer, requester, reviewer, author, decision_proposer = ASSAY_AUTHORITY_ACTORS
    actors = [
        author,
        author,
        rubric_observer,
        scope_observer,
        requester,
        reviewer,
        decision_proposer,
        ACTORS["actor-a"],
    ]
    steps = [
        (
            "RegisterAssayRubricContent",
            rubric["record_id"],
            0,
            {"content": rubric, "authority_file_path": ASSAY_RUBRIC_PATH.as_posix()},
            "scope_definition",
        ),
        (
            "RegisterAssayEvidenceScopeContent",
            scope["record_id"],
            0,
            {"content": scope, "authority_file_path": ASSAY_SCOPE_PATH.as_posix()},
            "scope_definition",
        ),
        ("ObserveW11AuthorityFile", rubric["record_id"], 1, {}, "scope_definition"),
        ("ObserveW11AuthorityFile", scope["record_id"], 1, {}, "scope_definition"),
        (
            "RequestW11AuthorityReview",
            review,
            0,
            {"reviewer_actor_id": reviewer, "prospective_producer_ref": producer_ref},
            "review",
        ),
        ("RecordW11AuthorityReview", review, 1, {}, "review"),
        ("ProposeW11AuthorityDecision", decision, 0, {"proposed_decision": "accept"}, "decision"),
        ("ResolveDecision", decision, 1, {"decision_id": decision, "decision": "accept"}, "decision"),
    ]
    for index, (command_type, target, version, value, subject_kind) in enumerate(steps):
        if through_index is not None and index > through_index:
            break
        if index == 5:
            bar = replay_discovery(load_discovery_operator(inputs["config_path"]).ledger.iter_events())[
                "assay_bar_authority"
            ]
            value = {
                "verdict": "approve",
                "unchanged_subject_sha256": bar["subject_sha256"],
                "reconstruction_sha256": assay_reconstruction_sha256(bar, "ctx_019fed25-b33e-7740-b280-000000000105"),
            }
        result = _governed_submit(
            inputs,
            _route_command(
                command_type,
                target,
                version,
                f"OR-{101 + index:03d}",
                {"authority_kind": "assay_bar", **value},
                actors[index],
            ),
            subject_kind=subject_kind,
        )
        assert result.status == "accepted"
    if through_index is not None:
        return None
    bar = replay_discovery(load_discovery_operator(inputs["config_path"]).ledger.iter_events())["assay_bar_authority"]
    return bar["acceptance_sha256"], bar["producer_relation_sha256"]


def _seed_requested_spec_01(inputs: dict[str, Any]) -> tuple[str, str, str]:
    assert cli.main(_advance_argv(inputs)) == 0
    bar_sha256, producer_sha256 = _accept_assay_authority(inputs)
    _accepted_route_authority(inputs, "dossier_expected_set", 210)
    _accepted_route_authority(inputs, "path_registration", 220)
    repository_root = Path(inputs["config"]["repository_root"])
    expected = build_spec_authority_subject(repository_root, "dossier_expected_set")["expected_set"]
    dossier = json.loads((repository_root / ROUTE_DIRECTORY / "spec-research-dossier-manifest.json").read_bytes())
    assert (
        _governed_submit(
            inputs,
            _route_command(
                "AdmitResearchDossier",
                expected["dossier_id"],
                0,
                "OR-028",
                {
                    "dossier_id": expected["dossier_id"],
                    "expected_set_id": expected["expected_set_id"],
                    "candidate_members": expected["members"],
                    "candidate_manifest": dossier,
                },
                ACTORS["actor-a"],
            ),
            subject_kind="scope_definition",
        ).status
        == "accepted"
    )
    candidate_id = "obj_019ffe2b-fd4b-7000-8000-000000000301"
    observation_id = "obj_019ffe2b-fd4b-7000-8000-000000000302"
    batch = {
        "schema_id": "ars://portfolio/scout-observation-batch",
        "schema_version": "1.0.0",
        "source_query": "exact:SPEC-GATE6-RUN-V1",
        "source_version": "1",
        "observed_at": "2026-08-14T00:00:00Z",
        "returned_identifiers": [observation_id],
        "normalized_dedup_keys": ["spec-gate6-run-v1"],
        "raw_source_refs": [{"ref_kind": "external", "locator": ROUTE_DIRECTORY.as_posix(), "content_hash": "9" * 64}],
        "matching_facts": ["Exact admitted SPEC route candidate"],
        "omissions_or_errors": [],
        "viability_judgment_absent": True,
    }
    batch_sha256 = sha256_hex(canonical_bytes(batch))
    candidate_sha256 = sha256_hex(canonical_bytes([{"observation_id": observation_id, "content_sha256": batch_sha256}]))
    assert (
        _governed_submit(
            inputs,
            _route_command(
                "IngestScoutObservationBatch",
                observation_id,
                0,
                "OR-029",
                {
                    "observation_id": observation_id,
                    "batch": batch,
                    "batch_sha256": batch_sha256,
                    "candidate_blueprints": [
                        {
                            "candidate_id": candidate_id,
                            "revision": 1,
                            "content_sha256": candidate_sha256,
                            "source_observation_refs": [observation_id],
                            "title": "SPEC Gate 6 candidate",
                        }
                    ],
                },
                ACTORS["actor-a"],
            ),
            subject_kind="scope_definition",
        ).status
        == "accepted"
    )
    assay_id = "asy_019ffe2b-fd4b-7000-8000-000000000303"
    assert (
        _governed_submit(
            inputs,
            _route_command(
                "RequestAssay",
                assay_id,
                0,
                "OR-003",
                {
                    "candidate_id": candidate_id,
                    "assay_id": assay_id,
                    "candidate_revision": 1,
                    "candidate_sha256": candidate_sha256,
                    "assay_bar_acceptance_sha256": bar_sha256,
                    "producer_relation_sha256": producer_sha256,
                },
                ACTORS["actor-a"],
            ),
            subject_kind="scope_definition",
            subject_id=candidate_id,
        ).status
        == "accepted"
    )
    return candidate_id, assay_id, candidate_sha256


def _accept_spec_01_brief_inputs(inputs: dict[str, Any]) -> list[str]:
    repository_root = Path(inputs["config"]["repository_root"])
    sources = [
        (ROUTE_DIRECTORY / "spec-01-assay-brief-v1.1.0.md", "spec_operator_source"),
        (ROUTE_DIRECTORY / "spec-02-micro-spike-contract-v1.1.0.md", "spec_operator_source"),
        (Path(".research-system/methods/assets/adversarial-review-protocol.md"), "methods_asset"),
    ]
    entries = []
    artefact_ids = []
    for index, (source_path, document_type) in enumerate(sources, start=1):
        artefact_id = f"art_019ffe2b-fd4b-7000-8000-{400 + index:012d}"
        artefact_ids.append(artefact_id)
        raw = (repository_root / source_path).read_bytes()
        grant_id = activate_lifecycle_grant(
            inputs["harness"],
            subject_kind="artefact",
            subject_id=artefact_id,
            actor_id=ACTORS["actor-a"],
            command_types=("RegisterArtefact",),
            grant_id=new_id("authority_grant"),
        )
        manifest = artefact_manifest()
        manifest.update(
            artefact_id=artefact_id,
            producer_actor_id=ACTORS["actor-a"],
            task_id=f"tsk_019ffe2b-fd4b-7000-8000-{400 + index:012d}",
        )
        manifest["authority"]["accepted_scope"] = "spec-gate6-run"
        entries.append(
            {
                "publication": {
                    "source_relative_path": source_path.as_posix(),
                    "source_git_blob": _run_git(repository_root, "rev-parse", f"HEAD:{source_path.as_posix()}"),
                    "content_sha256": sha256_hex(raw),
                    "size_bytes": len(raw),
                    "media_type": "text/markdown; charset=utf-8",
                    "document_type": document_type,
                    "destination_relative_path": f"methods/content/spec-flow/{artefact_id}.md",
                },
                "registration": {
                    "artefact_id": artefact_id,
                    "project_id": PROJECT_ID,
                    "actor_id": ACTORS["actor-a"],
                    "authority_grant_id": grant_id,
                    "submitted_at": "2026-08-14T12:00:00Z",
                    "correlation_id": "spec-input-registration",
                    "reason": "Register exact committed SPEC brief input.",
                    "manifest": manifest,
                },
            }
        )
    _write_action(inputs, "register_spec_01_brief_inputs", registration={"raw_publications": entries})
    assert cli.main(_advance_argv(inputs, "register_spec_01_brief_inputs")) == 0

    review_commands = []
    publications = []
    for index, (artefact_id, entry) in enumerate(zip(artefact_ids, entries, strict=True), start=1):
        digest = entry["publication"]["content_sha256"]
        review_id = f"rev_019ffe2b-fd4b-7000-8000-{500 + index:012d}"
        evidence_id = f"arec_019ffe2b-fd4b-7000-8000-{500 + index:012d}"
        grant_id = activate_lifecycle_grant(
            inputs["harness"],
            subject_kind="artefact",
            subject_id=artefact_id,
            actor_id=REVIEWER_ACTOR,
            allowed_actor_classes=("agent",),
            command_types=("RecordScientificReview",),
            grant_id=new_id("authority_grant"),
        )
        payload = {
            "artefact_id": artefact_id,
            "review_id": review_id,
            "subject_sha256": digest,
            "scientific_review": "approved",
            "evidence_refs": [evidence_id],
        }
        review_commands.append(
            _artefact_command(
                command_type="RecordScientificReview",
                artefact_id=artefact_id,
                actor_id=REVIEWER_ACTOR,
                grant_id=grant_id,
                version=1,
                payload=payload,
                suffix=500 + index,
            )
        )
        publications.append(
            {
                "reference_id": evidence_id,
                "record": {
                    "schema_id": "ars://evidence/governing-scientific-review",
                    "schema_version": "1.0.0",
                    "project_id": PROJECT_ID,
                    "review_id": review_id,
                    "subject_sha256": digest,
                    "reviewer_actor_id": REVIEWER_ACTOR,
                    "eligible": True,
                    "related": False,
                    "independence_grade": "I1",
                    "status": "active",
                },
            }
        )
    _write_action(
        inputs,
        "review_spec_01_brief_inputs",
        commands=review_commands,
        registration={"governing_reviews": publications},
    )
    assert cli.main(_advance_argv(inputs, "review_spec_01_brief_inputs")) == 0

    contract = ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT).load()
    predicate, predicate_sha256 = contract.predicate_for("result_evidence")
    use_commands = []
    for index, (artefact_id, entry, publication) in enumerate(
        zip(artefact_ids, entries, publications, strict=True), start=1
    ):
        grant_id = activate_lifecycle_grant(
            inputs["harness"],
            subject_kind="artefact",
            subject_id=artefact_id,
            actor_id=ACTORS["actor-a"],
            command_types=("SetArtefactUseAuthority",),
            grant_id=new_id("authority_grant"),
        )
        payload = {
            "artefact_id": artefact_id,
            "use_authority": "accepted_for_scope",
            "subject_sha256": entry["publication"]["content_sha256"],
            "consumer_predicate": predicate_reference(
                str(predicate["predicate_id"]), str(predicate["predicate_version"]), predicate_sha256
            ),
            "evidence_refs": [publication["record"]["review_id"], publication["reference_id"]],
        }
        use_commands.append(
            _artefact_command(
                command_type="SetArtefactUseAuthority",
                artefact_id=artefact_id,
                actor_id=ACTORS["actor-a"],
                grant_id=grant_id,
                version=2,
                payload=payload,
                suffix=600 + index,
            )
        )
    _write_action(inputs, "accept_spec_01_brief_inputs", commands=use_commands)
    assert cli.main(_advance_argv(inputs, "accept_spec_01_brief_inputs")) == 0
    return artefact_ids


def _prepare_spec_01(inputs: dict[str, Any]) -> dict[str, Any]:
    actor_id = ACTORS["actor-a"]
    context_grant_id = new_id("authority_grant")
    brief_id = "art_019ffe2b-fd4b-7000-8000-000000000701"
    package_id = "art_019ffe2b-fd4b-7000-8000-000000000702"
    brief_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=brief_id,
        actor_id=actor_id,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    package_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=package_id,
        actor_id=actor_id,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    semantic = {
        "operator_actor_id": actor_id,
        "operator_session_id": "codex-desktop-session-spec-01",
        "recipient_id": "codex-desktop-operator-exchange",
        "purpose": "result_analysis",
        "scope": "spec-gate6-run",
        "evaluation_time": "2026-08-14T12:00:00Z",
        "created_at": "2026-08-14T12:00:00Z",
        "application_version": "1",
        "handoff_expires_at": "2026-08-15T12:00:00Z",
    }

    def registration(artefact_id: str, grant_id: str, artefact_type: str) -> dict[str, Any]:
        manifest = artefact_manifest()
        manifest.update(
            artefact_id=artefact_id,
            artefact_type=artefact_type,
            producer_actor_id=actor_id,
            task_id="tsk_019ffe2b-fd4b-7000-8000-000000000703",
        )
        manifest["authority"]["accepted_scope"] = semantic["scope"]
        return {
            "artefact_id": artefact_id,
            "project_id": PROJECT_ID,
            "actor_id": actor_id,
            "authority_grant_id": grant_id,
            "submitted_at": semantic["created_at"],
            "correlation_id": "spec-01-prepare",
            "reason": "Export exact owner-operated SPEC-01 brief.",
            "manifest": manifest,
        }

    registrations = {
        "context_authority_grant_id": context_grant_id,
        "brief_registration": registration(brief_id, brief_grant, "operator_brief_manifest"),
        "package_registration": registration(package_id, package_grant, "spec_01_operator_brief"),
    }
    _write_action(inputs, "prepare_spec_01", document=semantic, registration=registrations)
    context_id = derive_spec_owner_context_id(
        actor_id=actor_id,
        operator_session_id=semantic["operator_session_id"],
        recipient_id=semantic["recipient_id"],
        purpose=semantic["purpose"],
        scope=semantic["scope"],
        application_version=semantic["application_version"],
        valid_from=semantic["evaluation_time"],
        expires_at=semantic["handoff_expires_at"],
    )
    activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="context",
        subject_id=context_id,
        actor_id=actor_id,
        command_types=(
            "RequestContextPacket",
            "BeginContextCompilation",
            "CompleteContextCompilation",
            "PrepareOwnerOperatedContextHandoff",
            "ValidateOwnerOperatedContextHandoff",
            "IssueOwnerOperatedContextHandoff",
            "RecordOwnerOperatedContextDelivery",
        ),
        grant_id=context_grant_id,
    )
    assert cli.main(_advance_argv(inputs, "prepare_spec_01")) == 0
    return {"context_id": context_id, "brief_id": brief_id, "package_id": package_id}


def _return_spec_01_complete(
    inputs: dict[str, Any],
    candidate_id: str,
    assay_id: str,
    candidate_sha256: str,
    *,
    execute: bool = True,
) -> dict[str, Any]:
    operator = load_discovery_operator(inputs["config_path"])
    projection = replay_discovery(operator.ledger.iter_events(), schemas=operator.schemas)
    relation_sha256 = projection["assays"][assay_id]["producer_relation_sha256"]
    scorecard = _scorecard(
        SimpleNamespace(ledger=operator.ledger), candidate_id, assay_id, candidate_sha256, relation_sha256
    )
    scorecard_sha256 = sha256_hex(canonical_bytes(scorecard))
    package = SpecFlow(operator)._snapshot()[2]["spec_01_operator_brief"][0]
    return_id = "art_019ffe2b-fd4b-7000-8000-000000000801"
    registration_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=return_id,
        actor_id=ASSAY_PRODUCER_ACTOR,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    manifest = artefact_manifest()
    manifest.update(
        artefact_id=return_id,
        artefact_type="spec_01_return",
        producer_actor_id=ASSAY_PRODUCER_ACTOR,
        task_id="tsk_019ffe2b-fd4b-7000-8000-000000000801",
    )
    manifest["authority"]["accepted_scope"] = "spec-gate6-run:spec-01"
    document = {
        "schema_id": "ars://portfolio/spec-operator-return",
        "schema_version": "1.0.0",
        "document_type": "spec_01_return",
        "route_id": "SPEC-GATE6-RUN-V1",
        "stage": "SPEC-01",
        "outcome": "COMPLETE",
        "responds_to": {
            "brief_artefact_id": package["brief_manifest"]["brief_artefact_id"],
            "brief_manifest_sha256": package["brief_manifest_sha256"],
            "operator_session_id": package["operator_session"]["session_id"],
        },
        "producer": {"actor_id": ASSAY_PRODUCER_ACTOR, "relation_sha256": relation_sha256},
        "sources": [{"name": "accepted-spec-source", "sha256": package["route_source"]["raw_sha256"]}],
        "decisions": [{"decision": "complete exact assay", "automatic_promotion": False}],
        "checks": [{"check": "deterministic fixture scorecard", "passed": True}],
        "artifact_hashes": [{"name": "embedded_artefact", "sha256": scorecard_sha256}],
        "resource_use": {"elapsed_seconds": 1, "cpu_seconds": 1, "peak_memory_bytes": 1, "external_cost_gbp": 0},
        "deterministic_rerun": {"performed": True, "evidence_sha256": "8" * 64, "same_output": True},
        "embedded_artefact": scorecard,
    }
    discovery_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=ASSAY_PRODUCER_ACTOR,
        command_types=("RecordAssayScore",),
        grant_id=new_id("authority_grant"),
    )
    command = _route_command(
        "RecordAssayScore",
        assay_id,
        2,
        "OR-004",
        {
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "scorecard_sha256": scorecard_sha256,
            "scorecard_artifact": scorecard,
            "producer_relation_sha256": relation_sha256,
        },
        ASSAY_PRODUCER_ACTOR,
    )
    command["authority_grant_id"] = discovery_grant
    registration = {
        "artefact_id": return_id,
        "project_id": PROJECT_ID,
        "actor_id": ASSAY_PRODUCER_ACTOR,
        "authority_grant_id": registration_grant,
        "submitted_at": "2026-08-14T13:00:00Z",
        "correlation_id": "spec-01-return",
        "reason": "Register exact manually returned SPEC-01 evidence.",
        "manifest": manifest,
    }
    _write_action(inputs, "return_spec_01_complete", commands=[command], document=document, registration=registration)
    if execute:
        assert cli.main(_advance_argv(inputs, "return_spec_01_complete")) == 0
    return {"return_id": return_id, "scorecard_sha256": scorecard_sha256}


def _return_spec_01_partial(
    inputs: dict[str, Any], candidate_id: str, assay_id: str, candidate_sha256: str
) -> dict[str, Any]:
    operator = load_discovery_operator(inputs["config_path"])
    projection = replay_discovery(operator.ledger.iter_events(), schemas=operator.schemas)
    assay = projection["assays"][assay_id]
    bar = projection["assay_bar_authority"]
    relation_sha256 = assay["producer_relation_sha256"]
    partial = {
        "schema_id": "ars://portfolio/assay-partial",
        "schema_version": "1.0.0",
        "assay_id": assay_id,
        "candidate_ref": _ref(candidate_id, 1, candidate_sha256),
        "rubric_ref": deepcopy(bar["acceptance"]["rubric_ref"]),
        "scope_ref": deepcopy(bar["acceptance"]["scope_ref"]),
        "assay_bar_acceptance_ref": {
            "id": bar["acceptance"]["decision_id"],
            "record_revision": 1,
            "content_hash": bar["acceptance_sha256"],
        },
        "assay_relation_hash": relation_sha256,
        "completed_axes": [],
        "completed_evidence": [],
        "unmet_axes": ["identity"],
        "unmet_evidence": [],
        "reason_codes": ["incomplete_axis_closure"],
        "limitations": ["incomplete axis closure"],
        "revisit_requirements": ["complete the remaining assay axes"],
        "mechanical_recommendation": "PARK",
    }
    partial_sha256 = sha256_hex(canonical_bytes(partial))
    package = SpecFlow(operator)._snapshot()[2]["spec_01_operator_brief"][0]
    return_id = "art_019ffe2b-fd4b-7000-8000-000000000802"
    registration_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=return_id,
        actor_id=ASSAY_PRODUCER_ACTOR,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    manifest = artefact_manifest()
    manifest.update(
        artefact_id=return_id,
        artefact_type="spec_01_return",
        producer_actor_id=ASSAY_PRODUCER_ACTOR,
        task_id="tsk_019ffe2b-fd4b-7000-8000-000000000802",
    )
    manifest["authority"]["accepted_scope"] = "spec-gate6-run"
    document = {
        "schema_id": "ars://portfolio/spec-operator-return",
        "schema_version": "1.0.0",
        "document_type": "spec_01_return",
        "route_id": "SPEC-GATE6-RUN-V1",
        "stage": "SPEC-01",
        "outcome": "PARTIAL",
        "responds_to": {
            "brief_artefact_id": package["brief_manifest"]["brief_artefact_id"],
            "brief_manifest_sha256": package["brief_manifest_sha256"],
            "operator_session_id": package["operator_session"]["session_id"],
        },
        "producer": {"actor_id": ASSAY_PRODUCER_ACTOR, "relation_sha256": relation_sha256},
        "sources": [{"name": "accepted-spec-source", "sha256": package["route_source"]["raw_sha256"]}],
        "decisions": [{"decision": "record partial only", "automatic_promotion": False}],
        "checks": [{"check": "partial closure", "passed": False}],
        "artifact_hashes": [{"name": "embedded_artefact", "sha256": partial_sha256}],
        "resource_use": {"elapsed_seconds": 1, "cpu_seconds": 1, "peak_memory_bytes": 1, "external_cost_gbp": 0},
        "deterministic_rerun": {"performed": True, "evidence_sha256": "8" * 64, "same_output": True},
        "embedded_artefact": partial,
    }
    command_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=ASSAY_PRODUCER_ACTOR,
        command_types=("RecordAssayPartial",),
        grant_id=new_id("authority_grant"),
    )
    command = _route_command(
        "RecordAssayPartial",
        assay_id,
        2,
        "OR-005",
        {
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "producer_relation_sha256": relation_sha256,
            "partial_sha256": partial_sha256,
            "partial_artifact": partial,
        },
        ASSAY_PRODUCER_ACTOR,
    )
    command["authority_grant_id"] = command_grant
    registration = {
        "artefact_id": return_id,
        "project_id": PROJECT_ID,
        "actor_id": ASSAY_PRODUCER_ACTOR,
        "authority_grant_id": registration_grant,
        "submitted_at": "2026-08-14T12:00:00Z",
        "correlation_id": "spec-01-partial",
        "reason": "Register exact partial SPEC-01 evidence.",
        "manifest": manifest,
    }
    _write_action(inputs, "return_spec_01_partial", commands=[command], document=document, registration=registration)
    assert cli.main(_advance_argv(inputs, "return_spec_01_partial")) == 0
    return {"return_id": return_id, "partial_sha256": partial_sha256}


def _review_spec_01_complete(
    inputs: dict[str, Any],
    candidate_id: str,
    assay_id: str,
    scorecard_sha256: str,
    *,
    partial: bool = False,
    reviewer_actor: str = REVIEWER_ACTOR,
    execute_verdict: bool = True,
) -> str:
    review_id = "rev_019ffe2b-fd4b-7000-8000-000000000901"
    request_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=ACTORS["actor-a"],
        command_types=("RequestDiscoveryOutcomeReview",),
        grant_id=new_id("authority_grant"),
    )
    request = _route_command(
        "RequestDiscoveryOutcomeReview",
        review_id,
        0,
        "OR-035" if partial else "OR-034",
        {
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": review_id,
            "subject_sha256": scorecard_sha256,
            "review_contract": {
                "review_type": "provenance",
                "new_review_id": review_id,
                "subject_ids": [assay_id],
                "subject_hashes": [scorecard_sha256],
                "governing_refs": ["W11:OR-035" if partial else "W11:OR-034"],
                "review_questions": ["Does exact SPEC-01 assay evidence satisfy the accepted bar?"],
                "required_evidence_refs": ["scorecard:exact"],
                "required_lanes": ["provenance"],
                "reviewer_capability": ["assay-independent-review"],
                "required_independence_grade": "independent",
                "visibility_policy": "owner-visible",
                "allowed_verdicts": [
                    "approve",
                    "approve_with_conditions",
                    "changes_requested",
                    "reject",
                    "unable_to_verify",
                    "withdrawn",
                ],
                "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
                "deadline": "2026-08-15T12:00:00Z",
                "escalation_rule": "owner-ruling",
            },
        },
        ACTORS["actor-a"],
    )
    request["authority_grant_id"] = request_grant
    action = "review_spec_01_partial" if partial else "review_spec_01_complete"
    _write_action(inputs, action, commands=[request])
    assert cli.main(_advance_argv(inputs, action)) == 0

    review_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="review",
        subject_id=review_id,
        actor_id=reviewer_actor,
        allowed_actor_classes=("agent",) if reviewer_actor == REVIEWER_ACTOR else ("human",),
        command_types=("ReviewDiscoveryOutcome",),
        grant_id=new_id("authority_grant"),
    )
    verdict = _route_command(
        "ReviewDiscoveryOutcome",
        review_id,
        1,
        "OR-007" if partial else "OR-006",
        {
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "review_id": review_id,
            "subject_sha256": scorecard_sha256,
            "verdict": "approve",
            "review_verdict": {
                "review_id": review_id,
                "verdict": "approve",
                "findings": [],
                "required_evidence_refs": ["scorecard:exact"],
                "limitations": [],
                "conditions": [],
                "reviewer_actor_id": reviewer_actor,
                "reviewer_profile": "independent-assay-reviewer",
                "reviewer_session": "codex-desktop-independent-review",
                "reviewer_model_metadata": "manual-independent-review",
                "context_manifest_id": "ctx_019ffe2b-fd4b-7000-8000-000000000902",
                "context_manifest_sha256": "5" * 64,
                "unchanged_subject_sha256": scorecard_sha256,
                "producing_attempt_id": "att_019ffe2b-fd4b-7000-8000-000000000903",
                "trace_visibility_evidence_refs": ["trace:spec-01-review"],
                "computed_independence_grade": "independent",
            },
        },
        reviewer_actor,
    )
    verdict["authority_grant_id"] = review_grant
    _write_action(inputs, action, commands=[verdict])
    if execute_verdict:
        assert cli.main(_advance_argv(inputs, action)) == 0
    return review_id


def _decide_spec_01(
    inputs: dict[str, Any],
    candidate_id: str,
    assay_id: str,
    review_id: str,
    recommendation: str = "PROMOTE",
) -> str:
    decision_id = "dec_019ffe2b-fd4b-7000-8000-000000000904"
    owner_id = ACTORS["actor-a"]
    proposal_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=owner_id,
        command_types=("ProposePromotionDecision",),
        grant_id=new_id("authority_grant"),
    )
    proposed = {
        "question": "assay_to_spike",
        "recommendation": recommendation,
        "new_decision_id": decision_id,
        "decision_revision": 1,
        "decision_kind": "design_lock",
        "options": ["PROMOTE", "PARK", "KILL"],
        "governing_evidence_refs": ["evidence:exact"],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "expires_at": "2026-08-15T18:00:00Z",
        "review_date": "2026-08-14T12:00:00Z",
        "consequences": ["authorize exact next Discovery transition"],
    }
    operator = load_discovery_operator(inputs["config_path"])
    proposal = _route_command(
        "ProposePromotionDecision",
        decision_id,
        0,
        "OR-012",
        {
            "candidate_id": candidate_id,
            "decision_id": decision_id,
            "review_id": review_id,
            "w2_payload": proposed,
            "promotion_relation": _promotion_relation(
                SimpleNamespace(ledger=operator.ledger),
                decision_id=decision_id,
                candidate_id=candidate_id,
                aggregate_id=assay_id,
                review_id=review_id,
                gate="assay_to_spike",
                recommendation=recommendation,
            ),
        },
        owner_id,
    )
    proposal["authority_grant_id"] = proposal_grant
    _write_action(inputs, "decide_spec_01", commands=[proposal])
    assert cli.main(_advance_argv(inputs, "decide_spec_01")) == 0

    resolution_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="decision",
        subject_id=decision_id,
        actor_id=owner_id,
        command_types=("ResolveDecision",),
        grant_id=new_id("authority_grant"),
    )
    resolved = {
        "decision_id": decision_id,
        "selected_option": recommendation,
        "effective_scope": f"assay_to_spike:{candidate_id}",
        "decision_revision": 1,
        "deciding_actor_id": owner_id,
        "decision_authority_grant_id": resolution_grant,
        "governing_evidence_refs": ["evidence:exact"],
        "considered_review_ids": [review_id],
        "effective_at": "2026-08-14T12:30:00Z",
        "permitted_commands": ["RegisterSpikePlan"] if recommendation == "PROMOTE" else [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    resolution = _route_command(
        "ResolveDecision",
        decision_id,
        1,
        "OR-013",
        {"candidate_id": candidate_id, "decision_id": decision_id, "w2_payload": resolved},
        owner_id,
    )
    resolution["authority_grant_id"] = resolution_grant
    _write_action(inputs, "decide_spec_01", commands=[resolution])
    assert cli.main(_advance_argv(inputs, "decide_spec_01")) == 0
    return decision_id


def _correct_spec_01_source(inputs: dict[str, Any], scorecard_sha256: str) -> str:
    operator = load_discovery_operator(inputs["config_path"])
    decision = next(
        event
        for event in operator.ledger.iter_events()
        if event["event_type"] == "CandidatePromotionApplied" and event.get("payload", {}).get("row_id") == "OR-013"
    )
    projection = replay_discovery(operator.ledger.iter_events())
    assay_ids = tuple(projection["assays"])
    assert len(assay_ids) == 1
    assay_id = assay_ids[0]
    correction_id = "correction:spec-01-neurips2024-tag-v1"
    artefact_id = "art_019ffe2b-fd4b-7000-8000-000000000904"
    actor_id = ACTORS["actor-b"]
    grant_id = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=artefact_id,
        actor_id=actor_id,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    document = {
        "schema_id": "ars://portfolio/spec-01-source-correction",
        "schema_version": "1.0.0",
        "document_type": "spec_01_source_correction",
        "route_id": "SPEC-GATE6-RUN-V1",
        "correction_id": correction_id,
        "recorded_at": "2026-08-14T12:40:00Z",
        "producer": {
            "actor_id": actor_id,
            "session_id": "independent-source-check",
            "role": "source-correction verifier",
        },
        "scorecard_ref": {"id": assay_id, "sha256": scorecard_sha256},
        "decision_ref": {"id": decision["event_id"], "sha256": decision["event_hash"]},
        "incorrect_assertions": [
            "paper-cited neurips2024 branch is absent from the live Git remote",
            "primary_paper_code_discrepancy",
            "paper-code provenance requires a replacement immutable commit",
        ],
        "corrected_git_reference": {
            "cited_locator": "https://github.com/berenslab/eff-ph/tree/neurips2024",
            "repository_url": "https://github.com/berenslab/eff-ph.git",
            "requested_ref": "neurips2024",
            "resolved_ref": "refs/tags/neurips2024",
            "ref_kind": "tag",
            "commit_oid": "145efcde673f1a1897eff250b77221d26c34c479",
            "retrieval_methods": ["direct_locator", "git_ls_remote_tags", "detached_clone"],
            "required_paths": [
                {"path": "environment.yml", "sha256": "a" * 64},
                {"path": "scripts/compute_ph.py", "sha256": "b" * 64},
            ],
        },
        "correction_effect": {
            "withdrawn_condition_codes": ["primary_paper_code_discrepancy"],
            "withdrawn_limitations": [
                "The paper-cited neurips2024 code branch is absent from the live Git remote; only main and scRNA heads were advertised."
            ],
            "withdrawn_revisit_triggers": [
                "paper-code provenance restored",
                "an immutable replacement for the absent paper-cited branch is supplied",
            ],
            "preserved_findings": [
                "future_estimand_unidentified",
                "representation_freeze_missing",
                "primary_claim_missing",
            ],
        },
        "scientific_disposition": "PARK",
    }
    manifest = artefact_manifest()
    manifest.update(
        artefact_id=artefact_id,
        artefact_type="spec_01_source_correction",
        producer_actor_id=actor_id,
        task_id="tsk_019ffe2b-fd4b-7000-8000-000000000904",
    )
    manifest["authority"]["accepted_scope"] = "spec-gate6-run:spec-01-correction"
    registration = {
        "artefact_id": artefact_id,
        "project_id": PROJECT_ID,
        "actor_id": actor_id,
        "authority_grant_id": grant_id,
        "submitted_at": "2026-08-14T12:40:00Z",
        "correlation_id": correction_id,
        "reason": "Correct the head-only false negative for the paper-cited Git tag.",
        "manifest": manifest,
    }
    _write_action(inputs, "correct_spec_01_source", document=document, registration=registration)
    assert cli.main(_advance_argv(inputs, "correct_spec_01_source")) == 0
    return correction_id


def _approve_spec_02(inputs: dict[str, Any], *, execute: bool = True, park_override: bool = False) -> str:
    operator = load_discovery_operator(inputs["config_path"])
    promotion = next(
        event
        for event in operator.ledger.iter_events()
        if event["event_type"] == "CandidatePromotionApplied" and event.get("payload", {}).get("row_id") == "OR-013"
    )
    source = next(item for item in SpecFlow(operator).route["sources"] if item["alias"] == "SPEC-02")
    owner_id = ACTORS["actor-a"]
    artefact_id = "art_019ffe2b-fd4b-7000-8000-000000000905"
    grant_id = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=artefact_id,
        actor_id=owner_id,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    document = {
        "schema_id": "ars://portfolio/spec-02-live-run-approval",
        "schema_version": "1.0.0",
        "document_type": "spec_02_live_run_approval",
        "route_id": "SPEC-GATE6-RUN-V1",
        "owner": {"actor_id": owner_id, "role": "Stephen"},
        "decision": "APPROVE_SPEC_02_LIVE_RUN",
        "approved_at": "2026-08-14T13:00:00Z",
        "valid_window": {
            "starts_at": "2026-08-14T12:45:00Z",
            "expires_at": "2026-08-15T13:00:00Z",
        },
        "spec_02_subject": {"id": "SPEC-02", "sha256": source["sha256"]},
        "spec_01_promotion": {"id": promotion["event_id"], "sha256": promotion["event_hash"]},
        "entry_mode": "owner_approved_park_test" if park_override else "standard_promotion",
        "source_correction": None,
        "scientific_promotion": not park_override,
        "brief_identity": {"id": source["locator"], "sha256": source["sha256"]},
        "limits": {
            "budget_gbp": 0,
            "wall_time_seconds": 60,
            "cpu_seconds": 60,
            "peak_memory_bytes": 1048576,
            "resource_ids": ["owner-operated-codex-desktop"],
        },
        "automatic_execution": False,
    }
    if park_override:
        correction = SpecFlow(operator)._snapshot()[2]["spec_01_source_correction"][0]
        document["source_correction"] = {
            "id": correction["correction_id"],
            "sha256": sha256_hex(canonical_bytes(correction)),
        }
    manifest = artefact_manifest()
    manifest.update(
        artefact_id=artefact_id,
        artefact_type="spec_02_live_run_approval",
        producer_actor_id=owner_id,
        task_id="tsk_019ffe2b-fd4b-7000-8000-000000000905",
    )
    manifest["authority"]["accepted_scope"] = "spec-gate6-run:spec-02"
    registration = {
        "artefact_id": artefact_id,
        "project_id": PROJECT_ID,
        "actor_id": owner_id,
        "authority_grant_id": grant_id,
        "submitted_at": "2026-08-14T13:00:00Z",
        "correlation_id": "spec-02-live-run-approval",
        "reason": "Record Stephen's explicit bounded SPEC-02 live-run approval.",
        "manifest": manifest,
    }
    _write_action(inputs, "approve_spec_02", document=document, registration=registration)
    if execute:
        assert cli.main(_advance_argv(inputs, "approve_spec_02")) == 0
    return artefact_id


def _prepare_spec_02(inputs: dict[str, Any]) -> dict[str, Any]:
    actor_id = ACTORS["actor-a"]
    context_grant_id = new_id("authority_grant")
    brief_id = "art_019ffe2b-fd4b-7000-8000-000000000906"
    package_id = "art_019ffe2b-fd4b-7000-8000-000000000907"
    brief_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=brief_id,
        actor_id=actor_id,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    package_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=package_id,
        actor_id=actor_id,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    semantic = {
        "operator_actor_id": actor_id,
        "operator_session_id": "codex-desktop-session-spec-02",
        "recipient_id": "codex-desktop-operator-exchange",
        "purpose": "result_analysis",
        "scope": "spec-gate6-run",
        "evaluation_time": "2026-08-14T13:15:00Z",
        "created_at": "2026-08-14T13:15:00Z",
        "application_version": "1",
        "handoff_expires_at": "2026-08-15T13:00:00Z",
    }

    def registration(artefact_id: str, grant_id: str, artefact_type: str) -> dict[str, Any]:
        manifest = artefact_manifest()
        manifest.update(
            artefact_id=artefact_id,
            artefact_type=artefact_type,
            producer_actor_id=actor_id,
            task_id="tsk_019ffe2b-fd4b-7000-8000-000000000908",
        )
        manifest["authority"]["accepted_scope"] = semantic["scope"]
        return {
            "artefact_id": artefact_id,
            "project_id": PROJECT_ID,
            "actor_id": actor_id,
            "authority_grant_id": grant_id,
            "submitted_at": semantic["created_at"],
            "correlation_id": "spec-02-prepare",
            "reason": "Export exact owner-operated SPEC-02 brief.",
            "manifest": manifest,
        }

    registrations = {
        "context_authority_grant_id": context_grant_id,
        "brief_registration": registration(brief_id, brief_grant, "operator_brief_manifest"),
        "package_registration": registration(package_id, package_grant, "spec_02_operator_brief"),
    }
    _write_action(inputs, "prepare_spec_02", document=semantic, registration=registrations)
    retry_id = inputs["packet"]["retry_id"]
    seed = sha256_hex(
        canonical_bytes(
            {
                "semantic": [
                    actor_id,
                    context_grant_id,
                    semantic["operator_session_id"],
                    semantic["recipient_id"],
                    semantic["purpose"],
                    semantic["scope"],
                    retry_id,
                    semantic["application_version"],
                    semantic["evaluation_time"],
                    semantic["handoff_expires_at"],
                ]
            }
        )
    )
    context_id = _stable_context_id("ctx", f"{seed}:context")
    activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="context",
        subject_id=context_id,
        actor_id=actor_id,
        command_types=(
            "RequestContextPacket",
            "BeginContextCompilation",
            "CompleteContextCompilation",
            "PrepareOwnerOperatedContextHandoff",
            "ValidateOwnerOperatedContextHandoff",
            "IssueOwnerOperatedContextHandoff",
            "RecordOwnerOperatedContextDelivery",
        ),
        grant_id=context_grant_id,
    )
    assert cli.main(_advance_argv(inputs, "prepare_spec_02")) == 0
    return {"context_id": context_id, "brief_id": brief_id, "package_id": package_id}


def _start_spec_02(
    inputs: dict[str, Any], candidate_id: str, assay_id: str, *, execute_start: bool = True
) -> dict[str, str]:
    all_events = tuple(inputs["harness"].ledger.iter_events())
    resolve_ids = discovery_resolve_transaction_ids(all_events)
    operational_events = tuple(
        event
        for event in all_events
        if shared_event_partition(event, resolve_transaction_ids=resolve_ids) == "operational"
    )
    operational = replay_control_plane(operational_events).stream_states
    if C1_ATTEMPT_ID not in operational:
        _seed_running_attempt(inputs["harness"])
        all_events = tuple(inputs["harness"].ledger.iter_events())
        resolve_ids = discovery_resolve_transaction_ids(all_events)
        operational_events = tuple(
            event
            for event in all_events
            if shared_event_partition(event, resolve_transaction_ids=resolve_ids) == "operational"
        )
        operational = replay_control_plane(operational_events).stream_states
    attempt_sha256 = sha256_hex(canonical_bytes(operational[C1_ATTEMPT_ID]))
    resource_sha256 = sha256_hex(canonical_bytes(operational[C1_RESOURCE_GRANT_ID]))
    operator = load_discovery_operator(inputs["config_path"])
    projection = replay_discovery(operator.ledger.iter_events(), schemas=operator.schemas)
    candidate = projection["candidates"][candidate_id]
    assay = projection["assays"][assay_id]
    promotion_id = candidate["decision_id"]
    promotion = projection["decisions"][promotion_id]
    spike_id = "spk_019ffe2b-fd4b-7000-8000-000000000909"
    execution_id = "dec_019ffe2b-fd4b-7000-8000-000000000910"
    owner_id = ACTORS["actor-a"]
    candidate_ref = _ref(candidate_id, candidate["revision"], candidate["content_sha256"])
    assay_ref = _ref(assay_id, 1, assay["scorecard_sha256"])
    plan = {
        "schema_id": "ars://portfolio/spike-plan",
        "schema_version": "1.0.0",
        "spike_id": spike_id,
        "candidate_ref": candidate_ref,
        "originating_assay_ref": assay_ref,
        "source_scorecard_refs": [assay_ref],
        "assay_promotion_decision_ref": _ref(
            promotion_id, promotion["proposal_version"], promotion["proposal_event_hash"]
        ),
        "required_approving_authority": "Stephen",
        "time_resource_box": {"time_limit_seconds": 60, "worker_limit": 1, "network_access": False},
        "question": "Does the bounded provider-free SPEC-02 predicate hold?",
        "scope": "Exact approved SPEC-02 owner-operated micro-spike.",
        "inputs": ["fixture:exact"],
        "method_or_object": "No-provider validation",
        "baselines": [],
        "null_or_comparator": None,
        "success_predicates": ["closure holds"],
        "failure_predicates": ["closure fails"],
        "kill_conditions": ["identity mismatch"],
        "partial_rules": ["unable to evaluate is partial"],
        "planned_contracts": ["W11:OR-018"],
        "outputs": ["spike verdict"],
        "prohibited_work": ["provider execution"],
        "outcome_to_next_step": {"PASS": "review"},
    }
    plan_sha256 = sha256_hex(canonical_bytes(plan))
    plan_ref = _ref(spike_id, 1, plan_sha256)
    execution_relation = {
        "schema_id": "ars://portfolio/relation/spike-execution-authority",
        "schema_version": "1.0.0",
        "relation_kind": "spike_execution_authority",
        "decision_id": execution_id,
        "spike_ref": plan_ref,
        "candidate_ref": candidate_ref,
        "plan_ref": plan_ref,
        "resource_ref": _ref(C1_RESOURCE_GRANT_ID, 1, resource_sha256),
        "route_ref": plan_ref,
        "assurance_ref": assay_ref,
        "selected_option": "AUTHORIZE",
        "actor_id": owner_id,
    }
    proposed = {
        "question": "spike_execution",
        "recommendation": "approve",
        "new_decision_id": execution_id,
        "decision_revision": 1,
        "decision_kind": "design_lock",
        "options": ["approve", "reject"],
        "governing_evidence_refs": ["evidence:exact"],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "expires_at": "2026-08-15T18:00:00Z",
        "review_date": "2026-08-14T13:30:00Z",
        "consequences": ["authorize bounded SPEC-02 attempt"],
    }
    plan_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=owner_id,
        command_types=("RegisterSpikePlan",),
        grant_id=new_id("authority_grant"),
    )
    plan_command = _route_command(
        "RegisterSpikePlan",
        spike_id,
        0,
        "OR-014",
        {"candidate_id": candidate_id, "spike_id": spike_id, "plan_sha256": plan_sha256, "plan_artifact": plan},
        owner_id,
    )
    plan_command["authority_grant_id"] = plan_grant
    _write_action(inputs, "start_spec_02", commands=[plan_command])
    assert cli.main(_advance_argv(inputs, "start_spec_02")) == 0

    proposal_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=owner_id,
        command_types=("ProposeSpikeExecutionDecision",),
        grant_id=new_id("authority_grant"),
    )
    proposal = _route_command(
        "ProposeSpikeExecutionDecision",
        execution_id,
        0,
        "OR-015",
        {
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "decision_id": execution_id,
            "w2_payload": proposed,
            "execution_authority_relation": execution_relation,
        },
        owner_id,
    )
    proposal["authority_grant_id"] = proposal_grant
    _write_action(inputs, "start_spec_02", commands=[proposal])
    assert cli.main(_advance_argv(inputs, "start_spec_02")) == 0

    decision_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="decision",
        subject_id=execution_id,
        actor_id=owner_id,
        command_types=("ResolveDecision",),
        grant_id=new_id("authority_grant"),
    )
    resolved = {
        "decision_id": execution_id,
        "selected_option": "approve",
        "effective_scope": f"spike_execution:{spike_id}",
        "decision_revision": 1,
        "deciding_actor_id": owner_id,
        "decision_authority_grant_id": decision_grant,
        "governing_evidence_refs": ["evidence:exact"],
        "considered_review_ids": [],
        "effective_at": "2026-08-14T13:35:00Z",
        "permitted_commands": ["StartSpike"],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    resolution = _route_command(
        "ResolveDecision",
        execution_id,
        1,
        "OR-016",
        {
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "decision_id": execution_id,
            "w2_payload": resolved,
            "execution_authority_relation": execution_relation,
        },
        owner_id,
    )
    resolution["authority_grant_id"] = decision_grant
    _write_action(inputs, "start_spec_02", commands=[resolution])
    assert cli.main(_advance_argv(inputs, "start_spec_02")) == 0

    start_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=owner_id,
        command_types=("StartSpike",),
        grant_id=new_id("authority_grant"),
    )
    start = _route_command(
        "StartSpike",
        spike_id,
        4,
        "OR-017",
        {
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "attempt_id": C1_ATTEMPT_ID,
            "attempt_sha256": attempt_sha256,
            "lease_id": C1_LEASE_ID,
            "resource_grant_id": C1_RESOURCE_GRANT_ID,
        },
        owner_id,
    )
    start["authority_grant_id"] = start_grant
    _write_action(inputs, "start_spec_02", commands=[start])
    if execute_start:
        assert cli.main(_advance_argv(inputs, "start_spec_02")) == 0
    return {"spike_id": spike_id, "attempt_sha256": attempt_sha256, "plan_sha256": plan_sha256}


def _register_spike_return_evidence(inputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    operator = load_discovery_operator(inputs["config_path"])
    service = CommandService(
        operator.control_root,
        operator.ledger,
        ObjectStore(operator.control_root),
        ReceiptStore(operator.control_root),
        operator.schemas,
        authority_resolver=operator.authority_resolver,
        clock=lambda: datetime(2026, 8, 1, 12, 31, tzinfo=UTC),
    )
    registered: dict[str, dict[str, Any]] = {}
    for index, (name, artefact_type) in enumerate(
        (
            ("raw_output", "evaluation_run"),
            ("source", "evaluation_run"),
            ("checks", "validation_report"),
            ("result", "evaluation_run"),
        ),
        start=1,
    ):
        artefact_id = f"art_019ffe2b-fd4b-7000-8000-{920 + index:012d}"
        actor_id = ACTORS["actor-a"]
        value = {
            "schema_id": "ars://portfolio/spec-route-evidence",
            "schema_version": "1.0.0",
            "route_id": "SPEC-GATE6-RUN-V1",
            "stage": "SPEC-02",
            "evidence_kind": name,
            "content": f"exact deterministic {name}",
        }
        grant_id = activate_lifecycle_grant(
            inputs["harness"],
            subject_kind="artefact",
            subject_id=artefact_id,
            actor_id=actor_id,
            command_types=("RegisterArtefact",),
            grant_id=new_id("authority_grant"),
        )
        manifest = artefact_manifest()
        manifest.update(
            artefact_id=artefact_id,
            artefact_type=artefact_type,
            producer_actor_id=actor_id,
            task_id=f"tsk_019ffe2b-fd4b-7000-8000-{920 + index:012d}",
        )
        manifest["authority"]["accepted_scope"] = "spec-gate6-run"
        result = register_candidate_document(
            value=value,
            registration=CandidateRegistration(
                artefact_id=artefact_id,
                project_id=PROJECT_ID,
                actor_id=actor_id,
                authority_grant_id=grant_id,
                submitted_at="2026-08-01T12:31:00Z",
                correlation_id="spec-02-return-evidence",
                reason=f"Register exact SPEC-02 {name} candidate evidence.",
                manifest=manifest,
            ),
            document_store=CandidateDocumentStore(
                operator.control_root, relative_directory=Path("methods/documents/spec-flow/evidence")
            ),
            command_service=service,
        )
        registered[name] = {
            "artefact_id": artefact_id,
            "content_sha256": result.content_sha256,
            "value": value,
            "artefact_type": artefact_type,
        }
    return registered


def _return_spec_02_complete(
    inputs: dict[str, Any],
    candidate_id: str,
    assay_id: str,
    started: dict[str, str],
    *,
    partial: bool = False,
) -> dict[str, str]:
    evidence = _register_spike_return_evidence(inputs)
    operator = load_discovery_operator(inputs["config_path"])
    projection = replay_discovery(operator.ledger.iter_events(), schemas=operator.schemas)
    candidate = projection["candidates"][candidate_id]
    assay = projection["assays"][assay_id]
    spike = projection["spikes"][started["spike_id"]]
    candidate_ref = _ref(candidate_id, candidate["revision"], candidate["content_sha256"])
    assay_ref = _ref(assay_id, 1, assay["scorecard_sha256"])
    result_ref = _ref(evidence["result"]["artefact_id"], 1, evidence["result"]["content_sha256"])
    validation_ref = _ref(evidence["checks"]["artefact_id"], 1, evidence["checks"]["content_sha256"])
    verdict = {
        "schema_id": "ars://portfolio/spike-verdict",
        "schema_version": "1.0.0",
        "spike_id": started["spike_id"],
        "candidate_ref": candidate_ref,
        "originating_assay_ref": assay_ref,
        "spike_plan_ref": _ref(started["spike_id"], 1, spike["plan_sha256"]),
        "attempt_ref": _ref(C1_ATTEMPT_ID, 1, spike["attempt_sha256"]),
        "verdict": "PARTIAL" if partial else "PASS",
        "success_predicates": [
            {
                "predicate": "closure holds",
                "status": "unable_to_evaluate" if partial else "passed",
                "evidence_refs": [result_ref],
            }
        ],
        "failure_predicates": [{"predicate": "closure fails", "status": "passed", "evidence_refs": [result_ref]}],
        "kill_conditions": [
            {
                "condition": "identity mismatch",
                "status": "triggered" if partial else "not_triggered",
                "evidence_refs": [result_ref],
                "consequence": "stop",
            }
        ],
        "artefact_refs": [result_ref],
        "validation_refs": [validation_ref],
        "completed_scope": "The evaluable declared scope completed.",
        "unmet_scope": "One predicate remains unevaluated." if partial else "None.",
        "limitations": ["One predicate could not be evaluated."] if partial else [],
        "mechanical_recommendation": "PARK" if partial else "NONE",
        "prohibited_inferences": ["This verdict does not authorize dispatch."],
    }
    verdict_sha256 = sha256_hex(canonical_bytes(verdict))
    package = SpecFlow(operator)._snapshot()[2]["spec_02_operator_brief"][0]
    return_id = "art_019ffe2b-fd4b-7000-8000-000000000925"
    actor_id = ACTORS["actor-a"]
    registration_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="artefact",
        subject_id=return_id,
        actor_id=actor_id,
        command_types=("RegisterArtefact",),
        grant_id=new_id("authority_grant"),
    )
    manifest = artefact_manifest()
    manifest.update(
        artefact_id=return_id,
        artefact_type="spec_02_return",
        producer_actor_id=actor_id,
        task_id="tsk_019ffe2b-fd4b-7000-8000-000000000925",
    )
    manifest["authority"]["accepted_scope"] = "spec-gate6-run"
    document = {
        "schema_id": "ars://portfolio/spec-operator-return",
        "schema_version": "1.0.0",
        "document_type": "spec_02_return",
        "route_id": "SPEC-GATE6-RUN-V1",
        "stage": "SPEC-02",
        "outcome": "PARTIAL" if partial else "COMPLETE",
        "responds_to": {
            "brief_artefact_id": package["brief_manifest"]["brief_artefact_id"],
            "brief_manifest_sha256": package["brief_manifest_sha256"],
            "operator_session_id": package["operator_session"]["session_id"],
        },
        "producer": {
            "actor_id": actor_id,
            "relation_sha256": sha256_hex(canonical_bytes(spike["execution_authority_relation"])),
        },
        "sources": [{"name": "accepted-spec-source", "sha256": package["route_source"]["raw_sha256"]}],
        "decisions": [{"decision": "record candidate verdict only", "automatic_promotion": False}],
        "checks": [{"check": "deterministic rerun", "passed": True}],
        "artifact_hashes": [
            *(
                {"name": name, "sha256": evidence[name]["content_sha256"]}
                for name in ("raw_output", "source", "checks", "result")
            ),
            {"name": "embedded_artefact", "sha256": verdict_sha256},
        ],
        "resource_use": {"elapsed_seconds": 1, "cpu_seconds": 1, "peak_memory_bytes": 1, "external_cost_gbp": 0},
        "deterministic_rerun": {"performed": True, "evidence_sha256": "8" * 64, "same_output": True},
        "embedded_artefact": verdict,
    }
    command_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=actor_id,
        command_types=("RecordSpikeVerdict",),
        grant_id=new_id("authority_grant"),
    )
    command = _route_command(
        "RecordSpikeVerdict",
        started["spike_id"],
        5,
        "OR-019" if partial else "OR-018",
        {
            "candidate_id": candidate_id,
            "spike_id": started["spike_id"],
            "verdict": "PARTIAL" if partial else "PASS",
            "verdict_sha256": verdict_sha256,
            "verdict_artifact": verdict,
            "evidence_refs": [f"artefact:{return_id}"],
        },
        actor_id,
    )
    command["authority_grant_id"] = command_grant
    registration = {
        "artefact_id": return_id,
        "project_id": PROJECT_ID,
        "actor_id": actor_id,
        "authority_grant_id": registration_grant,
        "submitted_at": "2026-08-01T12:32:00Z",
        "correlation_id": "spec-02-return",
        "reason": "Register exact SPEC-02 return wrapper.",
        "manifest": manifest,
    }
    action = "return_spec_02_partial" if partial else "return_spec_02_complete"
    _write_action(inputs, action, commands=[command], document=document, registration=registration)
    assert cli.main(_advance_argv(inputs, action)) == 0
    return {"return_id": return_id, "verdict_sha256": verdict_sha256}


def _review_spec_02_complete(
    inputs: dict[str, Any],
    candidate_id: str,
    spike_id: str,
    verdict_sha256: str,
    *,
    partial: bool = False,
) -> str:
    review_id = "rev_019ffe2b-fd4b-7000-8000-000000000926"
    request_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=ACTORS["actor-a"],
        command_types=("RequestDiscoveryOutcomeReview",),
        grant_id=new_id("authority_grant"),
    )
    request = _route_command(
        "RequestDiscoveryOutcomeReview",
        review_id,
        0,
        "OR-037" if partial else "OR-036",
        {
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "review_id": review_id,
            "subject_sha256": verdict_sha256,
            "review_contract": {
                "review_type": "provenance",
                "new_review_id": review_id,
                "subject_ids": [spike_id],
                "subject_hashes": [verdict_sha256],
                "governing_refs": ["W11:OR-037" if partial else "W11:OR-036"],
                "review_questions": ["Is the exact SPEC-02 Spike verdict supported?"],
                "required_evidence_refs": ["evidence:provider-free"],
                "required_lanes": ["provenance"],
                "reviewer_capability": ["spike-independent-review"],
                "required_independence_grade": "independent",
                "visibility_policy": "owner-visible",
                "allowed_verdicts": [
                    "approve",
                    "approve_with_conditions",
                    "changes_requested",
                    "reject",
                    "unable_to_verify",
                    "withdrawn",
                ],
                "satisfaction_authority": "ars://portfolio/policy/discovery-outcome-review@1.0.0",
                "deadline": "2026-08-02T12:00:00Z",
                "escalation_rule": "owner-ruling",
            },
        },
        ACTORS["actor-a"],
    )
    request["authority_grant_id"] = request_grant
    action = "review_spec_02_partial" if partial else "review_spec_02_complete"
    _write_action(inputs, action, commands=[request])
    assert cli.main(_advance_argv(inputs, action)) == 0

    review_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="review",
        subject_id=review_id,
        actor_id=REVIEWER_ACTOR,
        allowed_actor_classes=("agent",),
        command_types=("ReviewDiscoveryOutcome",),
        grant_id=new_id("authority_grant"),
    )
    verdict = _route_command(
        "ReviewDiscoveryOutcome",
        review_id,
        1,
        "OR-021" if partial else "OR-020",
        {
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "review_id": review_id,
            "subject_sha256": verdict_sha256,
            "review_verdict": {
                "review_id": review_id,
                "verdict": "approve",
                "findings": [],
                "required_evidence_refs": ["evidence:provider-free"],
                "limitations": [],
                "conditions": [],
                "reviewer_actor_id": REVIEWER_ACTOR,
                "reviewer_profile": "independent-spike-reviewer",
                "reviewer_session": "codex-desktop-independent-spec-02-review",
                "reviewer_model_metadata": "manual-independent-review",
                "context_manifest_id": "ctx_019ffe2b-fd4b-7000-8000-000000000927",
                "context_manifest_sha256": "7" * 64,
                "unchanged_subject_sha256": verdict_sha256,
                "producing_attempt_id": C1_ATTEMPT_ID,
                "trace_visibility_evidence_refs": ["trace:spec-02"],
                "computed_independence_grade": "independent",
            },
        },
        REVIEWER_ACTOR,
    )
    verdict["authority_grant_id"] = review_grant
    _write_action(inputs, action, commands=[verdict])
    assert cli.main(_advance_argv(inputs, action)) == 0
    return review_id


def _decide_spec_02(
    inputs: dict[str, Any],
    candidate_id: str,
    spike_id: str,
    review_id: str,
    recommendation: str = "PROMOTE",
) -> str:
    decision_id = "dec_019ffe2b-fd4b-7000-8000-000000000928"
    owner_id = ACTORS["actor-a"]
    proposal_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="scope_definition",
        subject_id=candidate_id,
        actor_id=owner_id,
        command_types=("ProposePromotionDecision",),
        grant_id=new_id("authority_grant"),
    )
    proposed = {
        "question": "spike_to_preregistration",
        "recommendation": recommendation,
        "new_decision_id": decision_id,
        "decision_revision": 1,
        "decision_kind": "design_lock",
        "options": ["PROMOTE", "PARK", "KILL"],
        "governing_evidence_refs": ["evidence:exact"],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "expires_at": "2026-08-02T18:00:00Z",
        "review_date": "2026-08-01T12:35:00Z",
        "consequences": ["record terminal SPEC-02 disposition without claim publication"],
    }
    operator = load_discovery_operator(inputs["config_path"])
    spike = replay_discovery(operator.ledger.iter_events())["spikes"][spike_id]
    proposal = _route_command(
        "ProposePromotionDecision",
        decision_id,
        0,
        "OR-026",
        {
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "decision_id": decision_id,
            "review_id": review_id,
            "verdict_sha256": spike["verdict_sha256"],
            "w2_payload": proposed,
            "promotion_relation": _promotion_relation(
                SimpleNamespace(ledger=operator.ledger),
                decision_id=decision_id,
                candidate_id=candidate_id,
                aggregate_id=spike_id,
                review_id=review_id,
                gate="spike_to_preregistration",
                recommendation=recommendation,
            ),
        },
        owner_id,
    )
    proposal["authority_grant_id"] = proposal_grant
    _write_action(inputs, "decide_spec_02", commands=[proposal])
    assert cli.main(_advance_argv(inputs, "decide_spec_02")) == 0
    resolution_grant = activate_lifecycle_grant(
        inputs["harness"],
        subject_kind="decision",
        subject_id=decision_id,
        actor_id=owner_id,
        command_types=("ResolveDecision",),
        grant_id=new_id("authority_grant"),
    )
    resolved = {
        "decision_id": decision_id,
        "selected_option": recommendation,
        "effective_scope": f"spike_to_preregistration:{candidate_id}",
        "decision_revision": 1,
        "deciding_actor_id": owner_id,
        "decision_authority_grant_id": resolution_grant,
        "governing_evidence_refs": ["evidence:exact"],
        "considered_review_ids": [review_id],
        "effective_at": "2026-08-01T12:36:00Z",
        "permitted_commands": [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    resolution = _route_command(
        "ResolveDecision",
        decision_id,
        1,
        "OR-027",
        {
            "candidate_id": candidate_id,
            "spike_id": spike_id,
            "decision_id": decision_id,
            "review_id": review_id,
            "verdict_sha256": spike["verdict_sha256"],
            "w2_payload": resolved,
        },
        owner_id,
    )
    resolution["authority_grant_id"] = resolution_grant
    _write_action(inputs, "decide_spec_02", commands=[resolution])
    assert cli.main(_advance_argv(inputs, "decide_spec_02")) == 0
    return decision_id


def _brief_document(inputs: dict[str, Any]) -> dict[str, Any]:
    repository_root = Path(inputs["config"]["repository_root"])
    source_path = ROUTE_DIRECTORY / "spec-01-assay-brief-v1.1.0.md"
    source = (repository_root / source_path).read_bytes()
    manifest = {"brief_artefact_id": "art_019ffe2b-fd4b-7000-8000-000000000001"}
    return {
        "schema_id": "ars://portfolio/spec-operator-brief-package",
        "schema_version": "1.0.0",
        "document_type": "spec_01_operator_brief",
        "route_id": "SPEC-GATE6-RUN-V1",
        "stage": "SPEC-01",
        "route_expected_return_type": "AssayScorecard",
        "route_source": {
            "relative_path": source_path.as_posix(),
            "raw_sha256": sha256_hex(source),
            "git_blob": _run_git(repository_root, "rev-parse", f"HEAD:{source_path.as_posix()}"),
        },
        "brief_manifest": manifest,
        "brief_manifest_sha256": sha256_hex(canonical_bytes(manifest)),
        "operator_session": {
            "session_id": "codex-desktop-session-1",
            "operator_actor_id": "act_019ffe2b-fd4b-7000-8000-000000000001",
            "application": "Codex desktop",
            "application_version": "1",
            "manually_operated": True,
        },
        "prohibitions": [
            "no provider or model launch",
            "no automatic promotion",
            "import is candidate evidence only",
        ],
    }


@pytest.mark.integration
def test_spec_status_is_read_only_and_names_exact_first_action(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    before = _tree_snapshot(spec_inputs["binding"].control_root)

    assert cli.main(_status_argv(spec_inputs)) == 0

    status = json.loads(capsys.readouterr().out)
    assert status == {
        "block_reason": "exact action identities, evidence, and active authority are required",
        "capability_state": "NOT_RUNNABLE",
        "completed_stage": "none",
        "next_action": "bootstrap_genesis",
        "route_id": "SPEC-GATE6-RUN-V1",
    }
    assert _tree_snapshot(spec_inputs["binding"].control_root) == before


@pytest.mark.integration
def test_spec_identity_producers_match_clean_post_format_fixture_commit(
    spec_inputs: dict[str, Any],
) -> None:
    repository_root = Path(spec_inputs["config"]["repository_root"])

    assert _run_git(repository_root, "status", "--porcelain=v1") == ""
    expected = build_spec_authority_subject(repository_root, "dossier_expected_set")
    paths = build_spec_authority_subject(repository_root, "path_registration")
    for member in paths["required_member_bindings"]:
        assert member["git_blob"] == _run_git(
            repository_root,
            "rev-parse",
            f"HEAD:{member['relative_path']}",
        )
    manifest = repository_root / ROUTE_DIRECTORY / "spec-research-dossier-manifest.json"
    assert expected["expected_set"]["manifest_sha256"] == canonical_dossier_hash(json.loads(manifest.read_bytes()))


@pytest.mark.integration
def test_spec_proposed_authorities_are_repository_only_and_portable_between_clean_checkouts(
    spec_inputs: dict[str, Any],
) -> None:
    repository_root = Path(spec_inputs["config"]["repository_root"])
    expected = build_spec_authority_subject(repository_root, "dossier_expected_set")
    paths = build_spec_authority_subject(repository_root, "path_registration")

    members = expected["expected_set"]["members"]
    assert [member["member_key"] for member in members] == ["route-package", "SPEC-01", "SPEC-02"]
    assert {member["root_id"] for member in members} == {"repository"}
    assert paths["registered_roots"] == [
        {
            "authorized": True,
            "path": "repository",
            "registration_revision": 1,
            "root_id": "repository",
        }
    ]
    assert paths == json.loads(
        (repository_root / ROUTE_DIRECTORY / "spec-path-registration-authority.json").read_bytes()
    )
    assert paths["portable_observation_binding"] == "git-subject-plus-physical-root-v1"
    second = repository_root.parent / "second-clean-spec-checkout"
    _run_git(
        repository_root.parent,
        "-c",
        "core.autocrlf=false",
        "clone",
        "--quiet",
        "--no-hardlinks",
        str(repository_root),
        str(second),
    )
    assert build_spec_authority_subject(second, "path_registration") == paths
    assert build_spec_authority_subject(second, "dossier_expected_set") == expected

    wrong_token = deepcopy(paths)
    wrong_token["registered_roots"][0]["root_id"] = "foreign"
    with pytest.raises(ValueError, match="invalid_portable_registered_root"):
        validate_portable_path_subject(wrong_token)
    dirty_member = second / ROUTE_DIRECTORY / "spec-01-assay-brief-v1.1.0.md"
    dirty_member.write_bytes(dirty_member.read_bytes() + b"\ntampered\n")
    with pytest.raises(ConfigurationError, match="member binding differs"):
        build_spec_authority_subject(second, "dossier_expected_set")


@pytest.mark.integration
def test_spec_portable_authority_producer_rejects_non_exact_member_set(
    spec_inputs: dict[str, Any],
) -> None:
    repository_root = Path(spec_inputs["config"]["repository_root"])
    authority_path = repository_root / ROUTE_DIRECTORY / "spec-path-registration-authority.json"
    original_raw = authority_path.read_bytes()
    original = json.loads(original_raw)
    variants = []

    missing = deepcopy(original)
    missing["required_member_bindings"].pop()
    variants.append(missing)

    extra = deepcopy(original)
    extra["required_member_bindings"].append(
        {
            **extra["required_member_bindings"][0],
            "alias": "unexpected-member",
        }
    )
    variants.append(extra)

    renamed = deepcopy(original)
    renamed["required_member_bindings"][0]["alias"] = "renamed-route-package"
    variants.append(renamed)

    changed = deepcopy(original)
    changed["required_member_bindings"][0]["sha256"] = "0" * 64
    variants.append(changed)

    try:
        for candidate in variants:
            candidate["content_sha256"] = sha256_hex(
                canonical_bytes(
                    {
                        key: value
                        for key, value in candidate.items()
                        if key not in {"content_sha256", "subject_sha256"} and not key.startswith("authority_file_")
                    }
                )
            )
            authority_path.write_bytes(canonical_bytes(candidate))
            with pytest.raises(
                ConfigurationError,
                match="portable repository-only|exact route bytes",
            ):
                build_spec_authority_subject(repository_root, "path_registration")
    finally:
        authority_path.write_bytes(original_raw)

    assert build_spec_authority_subject(repository_root, "path_registration") == original


@pytest.mark.integration
def test_public_portable_observation_rejects_missing_required_member_without_mutation(
    spec_inputs: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert cli.main(_advance_argv(spec_inputs)) == 0
    capsys.readouterr()
    _accepted_route_authority(spec_inputs, "dossier_expected_set", 1120)
    repository_root = Path(spec_inputs["config"]["repository_root"])
    relative = ROUTE_DIRECTORY / "spec-path-registration-authority.json"
    authority_path = repository_root / relative
    subject = json.loads(authority_path.read_bytes())
    subject["required_member_bindings"].pop()
    subject["content_sha256"] = sha256_hex(
        canonical_bytes(
            {
                key: value
                for key, value in subject.items()
                if key not in {"content_sha256", "subject_sha256"} and not key.startswith("authority_file_")
            }
        )
    )
    authority_path.write_bytes(canonical_bytes(subject))
    _run_git(repository_root, "add", relative.as_posix())
    _run_git(repository_root, "commit", "--quiet", "-m", "test missing portable member")
    raw = authority_path.read_bytes()
    subject.update(
        authority_file_path=relative.as_posix(),
        authority_file_size=len(raw),
        authority_file_sha256=sha256_hex(raw),
        authority_file_git_commit=_run_git(repository_root, "rev-parse", "HEAD"),
        authority_file_git_blob=_run_git(
            repository_root,
            "rev-parse",
            f"HEAD:{relative.as_posix()}",
        ),
    )
    subject["subject_sha256"] = subject_sha256(subject)
    stream_id = "obj_019ffe2b-fd4b-7000-8000-000000001226"

    # Simulate a durable registration produced by the pre-fix subset validator.
    # The runtime keeps its own exact-member validator reference, so OR-117 must
    # independently reject even while historical replay remains permissive.
    with monkeypatch.context() as patch:
        patch.setattr(
            discovery_authority_module,
            "validate_portable_path_subject",
            lambda _subject: None,
        )
        patch.setattr(
            discovery_authority_module,
            "validate_portable_members_against_expected_set",
            lambda _subject, _expected_set: None,
        )
        registered = _governed_submit(
            spec_inputs,
            _route_command(
                "RegisterPathRegistrationContent",
                stream_id,
                0,
                "OR-116",
                {"authority_kind": "path_registration", "subject": subject},
                "act_019ffe2b-fd4b-7000-8000-000000001226",
            ),
            subject_kind="scope_definition",
        )
        assert registered.status == "accepted"
        before = _tree_snapshot(spec_inputs["binding"].control_root)
        with pytest.raises(IntegrityError, match="invalid_portable_member_bindings"):
            _governed_submit(
                spec_inputs,
                _route_command(
                    "ObserveW11AuthorityFile",
                    stream_id,
                    1,
                    "OR-117",
                    {
                        "authority_kind": "path_registration",
                        "subject_sha256": subject["subject_sha256"],
                    },
                    "act_019ffe2b-fd4b-7000-8000-000000001227",
                ),
                subject_kind="scope_definition",
            )
        assert _tree_snapshot(spec_inputs["binding"].control_root) == before


@pytest.mark.integration
def test_portable_path_observation_rejects_clean_different_commit_without_mutation(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(_advance_argv(spec_inputs)) == 0
    capsys.readouterr()
    _accepted_route_authority(spec_inputs, "dossier_expected_set", 1110)
    repository_root = Path(spec_inputs["config"]["repository_root"])
    subject = build_spec_authority_subject(repository_root, "path_registration")
    relative = ROUTE_DIRECTORY / "spec-path-registration-authority.json"
    raw = (repository_root / relative).read_bytes()
    subject.update(
        authority_file_path=relative.as_posix(),
        authority_file_size=len(raw),
        authority_file_sha256=sha256_hex(raw),
        authority_file_git_commit=_run_git(repository_root, "rev-parse", "HEAD"),
        authority_file_git_blob=_run_git(repository_root, "rev-parse", f"HEAD:{relative.as_posix()}"),
    )
    subject["subject_sha256"] = subject_sha256(subject)
    stream_id = "obj_019ffe2b-fd4b-7000-8000-000000001216"
    registered = _governed_submit(
        spec_inputs,
        _route_command(
            "RegisterPathRegistrationContent",
            stream_id,
            0,
            "OR-116",
            {"authority_kind": "path_registration", "subject": subject},
            "act_019ffe2b-fd4b-7000-8000-000000001216",
        ),
        subject_kind="scope_definition",
    )
    assert registered.status == "accepted"

    unrelated = repository_root / "clean-different-commit.txt"
    unrelated.write_text("unrelated committed change\n", encoding="utf-8", newline="\n")
    _run_git(repository_root, "add", unrelated.name)
    _run_git(repository_root, "commit", "--quiet", "-m", "test unrelated clean commit")
    assert _run_git(repository_root, "status", "--porcelain=v1") == ""
    assert _run_git(repository_root, "rev-parse", "HEAD") != subject["authority_file_git_commit"]

    before = _tree_snapshot(spec_inputs["binding"].control_root)
    with pytest.raises(IntegrityError, match="authority file identity mismatch"):
        _governed_submit(
            spec_inputs,
            _route_command(
                "ObserveW11AuthorityFile",
                stream_id,
                1,
                "OR-117",
                {"authority_kind": "path_registration", "subject_sha256": subject["subject_sha256"]},
                "act_019ffe2b-fd4b-7000-8000-000000001217",
            ),
            subject_kind="scope_definition",
        )
    assert _tree_snapshot(spec_inputs["binding"].control_root) == before
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    authority = projection["authorities"]["path_registration"]
    assert authority["status"] == "registered"
    assert "portable_physical_binding" not in authority


@pytest.mark.integration
def test_spec_raw_brief_publication_registers_exact_committed_bytes_and_restarts(
    spec_inputs: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root = Path(spec_inputs["config"]["repository_root"])
    source_path = ROUTE_DIRECTORY / "spec-01-assay-brief-v1.1.0.md"
    raw = (repository_root / source_path).read_bytes()
    artefact_id = "art_019ffe2b-fd4b-7000-8000-000000000111"
    grant_id = activate_lifecycle_grant(
        spec_inputs["harness"],
        subject_kind="artefact",
        subject_id=artefact_id,
        command_types=("RegisterArtefact",),
    )
    manifest = artefact_manifest()
    manifest.update(
        {
            "artefact_id": artefact_id,
            "context_packet_id": "ctx_019ffe2b-fd4b-7000-8000-000000000112",
        }
    )
    registration = CandidateRegistration(
        artefact_id=artefact_id,
        project_id=PROJECT_ID,
        actor_id=spec_inputs["command"]["actor_id"],
        authority_grant_id=grant_id,
        submitted_at="2026-08-14T12:00:00Z",
        correlation_id="spec-flow:raw-source",
        reason="register exact committed SPEC brief source",
        manifest=manifest,
    )
    publication = RawContentPublication(
        source_relative_path=source_path.as_posix(),
        source_git_blob=_run_git(repository_root, "rev-parse", f"HEAD:{source_path.as_posix()}"),
        content_sha256=sha256_hex(raw),
        size_bytes=len(raw),
        media_type="text/markdown; charset=utf-8",
        document_type="spec_operator_source",
        destination_relative_path=f"methods/content/spec-flow/{artefact_id}.md",
    )

    target = spec_inputs["binding"].control_root / publication.destination_relative_path
    with monkeypatch.context() as patch:
        patch.setattr(
            spec_inputs["harness"].service,
            "submit",
            lambda *_args: (_ for _ in ()).throw(OSError("injected before registration")),
        )
        with pytest.raises(OSError, match="before registration"):
            publish_registered_raw_content(
                repository_root=repository_root,
                publication=publication,
                registration=registration,
                control_root=spec_inputs["binding"].control_root,
                command_service=spec_inputs["harness"].service,
            )
    assert not target.exists()
    assert not any(
        event.get("event_type") == "ArtefactRegistered" and event.get("stream_id") == artefact_id
        for event in spec_inputs["harness"].ledger.iter_events()
    )
    original_write = registration_module._write_immutable_raw
    with monkeypatch.context() as patch:
        patch.setattr(
            registration_module,
            "_write_immutable_raw",
            lambda *_args: (_ for _ in ()).throw(OSError("injected after registration")),
        )
        with pytest.raises(OSError, match="after registration"):
            publish_registered_raw_content(
                repository_root=repository_root,
                publication=publication,
                registration=registration,
                control_root=spec_inputs["binding"].control_root,
                command_service=spec_inputs["harness"].service,
            )
    assert not target.exists()
    event = next(
        event
        for event in spec_inputs["harness"].ledger.iter_events()
        if event.get("event_type") == "ArtefactRegistered" and event.get("stream_id") == artefact_id
    )
    assert event["payload"]["manifest"]["content_sha256"] == sha256_hex(raw)
    assert event["payload"]["manifest"]["relative_path"] == publication.destination_relative_path

    monkeypatch.setattr(registration_module, "_write_immutable_raw", original_write)
    result = publish_registered_raw_content(
        repository_root=repository_root,
        publication=publication,
        registration=registration,
        control_root=spec_inputs["binding"].control_root,
        command_service=spec_inputs["harness"].service,
    )
    assert result.content_sha256 == sha256_hex(raw)
    assert target.read_bytes() == raw
    assert (
        len([event for event in spec_inputs["harness"].ledger.iter_events() if event.get("stream_id") == artefact_id])
        == 1
    )

    before = _tree_snapshot(spec_inputs["binding"].control_root)
    with pytest.raises(ConfigurationError, match="byte binding differs"):
        publish_registered_raw_content(
            repository_root=repository_root,
            publication=RawContentPublication(**{**publication.__dict__, "content_sha256": "f" * 64}),
            registration=registration,
            control_root=spec_inputs["binding"].control_root,
            command_service=spec_inputs["harness"].service,
        )
    assert _tree_snapshot(spec_inputs["binding"].control_root) == before


@pytest.mark.integration
def test_spec_advance_genesis_restarts_with_same_receipt_and_next_action(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(_advance_argv(spec_inputs)) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["receipts"][0]["status"] == "accepted"
    assert first["status"]["next_action"] == "bootstrap_assay_authority"

    assert cli.main(_advance_argv(spec_inputs)) == 0
    second = json.loads(capsys.readouterr().out)
    assert second == first


@pytest.mark.integration
def test_public_spec_flow_advances_assay_review_rows_from_projected_state(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(_advance_argv(spec_inputs)) == 0
    capsys.readouterr()
    _accept_assay_authority(spec_inputs, through_index=3)

    review_id = "rev_019ffe2b-fd4b-7000-8000-000000000105"
    requester = ASSAY_AUTHORITY_ACTORS[2]
    reviewer = ASSAY_AUTHORITY_ACTORS[3]
    producer_ref = {"id": ACTORS["actor-a"], "record_revision": 1, "content_hash": "3" * 64}

    def command(
        command_type: str,
        target: str,
        version: int,
        row: str,
        actor: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        grant_id = activate_lifecycle_grant(
            spec_inputs["harness"],
            subject_kind="review",
            subject_id=target,
            actor_id=actor,
            allowed_actor_classes=("agent",),
            command_types=(command_type,),
            grant_id=new_id("authority_grant"),
        )
        value = _route_command(command_type, target, version, row, payload, actor)
        value["authority_grant_id"] = grant_id
        return value

    # Without a durable review request, OR-106 must not be inferred or
    # accepted as the next public row.
    invalid_review = _route_command(
        "RecordW11AuthorityReview",
        review_id,
        1,
        "OR-106",
        {
            "authority_kind": "assay_bar",
            "verdict": "approve",
            "unchanged_subject_sha256": "0" * 64,
            "reconstruction_sha256": "0" * 64,
        },
        reviewer,
    )
    _write_action(spec_inputs, "bootstrap_assay_authority", commands=[invalid_review])
    with pytest.raises(IntegrityError, match="exact next route row"):
        cli.main(_advance_argv(spec_inputs, "bootstrap_assay_authority"))
    capsys.readouterr()

    request = command(
        "RequestW11AuthorityReview",
        review_id,
        0,
        "OR-105",
        requester,
        {
            "authority_kind": "assay_bar",
            "reviewer_actor_id": reviewer,
            "prospective_producer_ref": producer_ref,
        },
    )
    _write_action(spec_inputs, "bootstrap_assay_authority", commands=[request])
    assert cli.main(_advance_argv(spec_inputs, "bootstrap_assay_authority")) == 0
    capsys.readouterr()
    bar = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())[
        "assay_bar_authority"
    ]
    assert bar["status"] == "review_requested"

    review = command(
        "RecordW11AuthorityReview",
        review_id,
        1,
        "OR-106",
        reviewer,
        {
            "authority_kind": "assay_bar",
            "verdict": "approve",
            "unchanged_subject_sha256": bar["subject_sha256"],
            "reconstruction_sha256": assay_reconstruction_sha256(bar, "ctx_019fed25-b33e-7740-b280-000000000105"),
        },
    )
    _write_action(spec_inputs, "bootstrap_assay_authority", commands=[review])
    assert cli.main(_advance_argv(spec_inputs, "bootstrap_assay_authority")) == 0
    capsys.readouterr()
    assert (
        replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())[
            "assay_bar_authority"
        ]["status"]
        == "reviewed"
    )


@pytest.mark.parametrize(
    ("kind", "status", "expected"),
    [
        ("dossier_expected_set", "registered", ("OR-110",)),
        ("dossier_expected_set", "review_requested", ("OR-110", "OR-111", "OR-112")),
        ("dossier_expected_set", "decision_proposed", tuple(f"OR-{row:03d}" for row in range(110, 115))),
        ("path_registration", "observed", ("OR-116", "OR-117")),
        ("path_registration", "reviewed", tuple(f"OR-{row:03d}" for row in range(116, 120))),
        ("path_registration", "accepted", tuple(f"OR-{row:03d}" for row in range(116, 122))),
    ],
)
def test_rows_infers_generic_authority_progress_from_projection(
    kind: str, status: str, expected: tuple[str, ...]
) -> None:
    assert _rows((), {"authorities": {kind: {"status": status}}}) == expected


@pytest.mark.integration
def test_public_spec_flow_reaches_brief_input_registration_from_exact_admitted_route(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()

    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["completed_stage"] == "request_spec_01"
    assert status["next_action"] == "register_spec_01_brief_inputs"
    assert status["capability_state"] == "NOT_RUNNABLE"
    assert cli.main(_status_argv(spec_inputs)) == 0
    assert json.loads(capsys.readouterr().out)["next_action"] == "register_spec_01_brief_inputs"


@pytest.mark.integration
def test_public_spec_flow_registers_reviews_and_accepts_exact_spec_01_brief_inputs(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    artefact_ids = _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()

    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["completed_stage"] == "request_spec_01"
    assert status["next_action"] == "prepare_spec_01"
    assert status["capability_state"] == "OWNER_BLOCKED"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    for artefact_id in artefact_ids:
        state = projection["artefact_streams"][artefact_id]
        assert state["scientific_reviews"]
        assert state["use_authority"] == "accepted_for_scope"


@pytest.mark.integration
def test_public_spec_flow_prepares_actual_owner_operated_spec_01_brief(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    identities = _prepare_spec_01(spec_inputs)
    output = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert output["context_id"] == identities["context_id"]
    assert output["registration"]["artefact_id"] == identities["package_id"]
    assert output["status"]["completed_stage"] == "prepare_spec_01"
    assert output["status"]["next_action"] == "return_spec_01"
    operator = load_discovery_operator(spec_inputs["config_path"])
    context_events = [
        event for event in operator.ledger.iter_events() if event["stream_id"] == identities["context_id"]
    ]
    assert [event["event_type"] for event in context_events][-4:] == [
        "OwnerOperatedContextHandoffPrepared",
        "OwnerOperatedContextHandoffValidated",
        "OwnerOperatedContextHandoffIssued",
        "OwnerOperatedContextDelivered",
    ]
    assert context_events[-4]["payload"]["owner_profile"]["provider_launch"] is False
    assert all("provider_template_sha256" not in event["payload"] for event in context_events[-4:])


@pytest.mark.integration
def test_public_spec_flow_records_complete_spec_01_return_without_auto_promotion(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    output = json.loads(capsys.readouterr().out)

    assert output["registration"]["artefact_id"] == returned["return_id"]
    assert output["status"]["completed_stage"] == "return_spec_01"
    assert output["status"]["next_action"] == "review_spec_01"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["assays"][assay_id]["status"] == "scored"
    assert projection["candidates"][candidate_id]["status"] == "assay_scored"
    assert not projection.get("claims")


@pytest.mark.integration
def test_public_spec_flow_rejects_malformed_and_wrongly_bound_spec_01_returns_without_publication(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256, execute=False)
    original = deepcopy(spec_inputs["packet"])
    before = _tree_snapshot(spec_inputs["binding"].control_root)
    mutations = []
    wrong_brief = deepcopy(original)
    wrong_brief["document"]["responds_to"]["brief_artefact_id"] = "art_wrong"
    mutations.append(wrong_brief)
    wrong_session = deepcopy(original)
    wrong_session["document"]["responds_to"]["operator_session_id"] = "wrong-session"
    mutations.append(wrong_session)
    wrong_producer = deepcopy(original)
    wrong_producer["document"]["producer"]["actor_id"] = REVIEWER_ACTOR
    mutations.append(wrong_producer)
    extra = deepcopy(original)
    extra["document"]["unexpected"] = True
    mutations.append(extra)
    missing = deepcopy(original)
    missing["document"].pop("artifact_hashes")
    mutations.append(missing)
    duplicate = deepcopy(original)
    duplicate["document"]["artifact_hashes"].append(deepcopy(duplicate["document"]["artifact_hashes"][0]))
    mutations.append(duplicate)
    tampered = deepcopy(original)
    tampered["document"]["embedded_artefact"]["recommendation"] = "PARK"
    mutations.append(tampered)
    for malformed in mutations:
        _refresh_retry_id(malformed)
        spec_inputs["packet_path"].write_bytes(canonical_bytes(malformed))
        with pytest.raises(IntegrityError):
            cli.main(_advance_argv(spec_inputs, "return_spec_01_complete"))
        assert _tree_snapshot(spec_inputs["binding"].control_root) == before
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["assays"][assay_id]["status"] == "evidence_collecting"
    assert "spec_01_return" not in SpecFlow(load_discovery_operator(spec_inputs["config_path"]))._snapshot()[2]


@pytest.mark.integration
def test_public_spec_flow_independently_reviews_complete_spec_01_return(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    output = json.loads(capsys.readouterr().out.splitlines()[-1])

    assert output["status"]["completed_stage"] == "review_spec_01"
    assert output["status"]["next_action"] == "decide_spec_01"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["reviews"][review_id]["status"] == "satisfied"
    assert projection["reviews"][review_id]["reviewer_actor_id"] == REVIEWER_ACTOR


@pytest.mark.integration
def test_public_spec_flow_rejects_producer_as_spec_01_reviewer_without_verdict(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(
        spec_inputs,
        candidate_id,
        assay_id,
        returned["scorecard_sha256"],
        reviewer_actor=ASSAY_PRODUCER_ACTOR,
        execute_verdict=False,
    )
    capsys.readouterr()
    before = _tree_snapshot(spec_inputs["binding"].control_root)
    with pytest.raises(IntegrityError, match="reviewer must be independent"):
        cli.main(_advance_argv(spec_inputs, "review_spec_01_complete"))
    assert _tree_snapshot(spec_inputs["binding"].control_root) == before
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["reviews"][review_id]["status"] == "pending"
    assert projection["assays"][assay_id]["status"] == "scored"


@pytest.mark.integration
def test_public_spec_flow_partial_spec_01_return_and_review_is_terminal(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_partial(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["partial_sha256"], partial=True)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["capability_state"] == "PROVEN"
    assert status["completed_stage"] == "spec_01_partial_reviewed"
    assert status["next_action"] is None
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["reviews"][review_id]["status"] == "satisfied"
    assert projection["assays"][assay_id]["status"] == "partial_reviewed"
    assert (
        "spec_02_live_run_approval" not in SpecFlow(load_discovery_operator(spec_inputs["config_path"]))._snapshot()[2]
    )


@pytest.mark.integration
def test_public_spec_flow_owner_promotes_reviewed_spec_01_without_auto_execution(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    output = json.loads(capsys.readouterr().out)
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert output["completed_stage"] == "spec_01_promoted", projection["candidates"][candidate_id]["status"]
    assert output["next_action"] == "approve_spec_02"
    assert projection["candidates"][candidate_id]["status"] == "spike_planning_authorized"
    assert not projection.get("spikes")
    assert not projection.get("claims")


@pytest.mark.integration
@pytest.mark.parametrize("recommendation", ("PARK", "KILL"))
def test_public_spec_flow_owner_park_or_kill_is_terminal_after_spec_01_review(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str], recommendation: str
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id, recommendation)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    if recommendation == "KILL":
        assert status["capability_state"] == "PROVEN"
        assert status["completed_stage"] == "spec_01_killed"
        assert status["next_action"] is None
    else:
        assert status["capability_state"] == "NOT_RUNNABLE"
        assert status["completed_stage"] == "spec_01_parked"
        assert status["next_action"] == "correct_spec_01_source"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["candidates"][candidate_id]["status"] == recommendation.casefold() + "ed"
    assert (
        "spec_02_live_run_approval" not in SpecFlow(load_discovery_operator(spec_inputs["config_path"]))._snapshot()[2]
    )


@pytest.mark.integration
def test_public_spec_flow_corrects_false_git_ref_finding_and_allows_owner_approved_park_test(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id, "PARK")
    capsys.readouterr()
    monkeypatch.setattr(
        spec_flow_module,
        "_resolve_remote_tag",
        lambda repository_url, resolved_ref: "145efcde673f1a1897eff250b77221d26c34c479",
    )
    _correct_spec_01_source(spec_inputs, returned["scorecard_sha256"])
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    corrected = json.loads(capsys.readouterr().out)
    assert corrected["next_action"] == "approve_spec_02"
    _approve_spec_02(spec_inputs, park_override=True)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["completed_stage"] == "approve_spec_02"
    assert status["next_action"] == "prepare_spec_02"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["candidates"][candidate_id]["status"] == "parked"
    assert not projection.get("spikes")
    assert not projection.get("claims")


@pytest.mark.integration
def test_public_spec_flow_requires_and_records_separate_spec_02_live_approval(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    before = json.loads(capsys.readouterr().out)
    assert before["capability_state"] == "OWNER_BLOCKED"
    assert before["next_action"] == "approve_spec_02"

    approval_id = _approve_spec_02(spec_inputs)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    after = json.loads(capsys.readouterr().out)
    assert after["completed_stage"] == "approve_spec_02"
    assert after["next_action"] == "prepare_spec_02"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["artefact_streams"][approval_id]["manifest"]["artefact_type"] == "spec_02_live_run_approval"
    assert not projection.get("spikes")
    assert not projection.get("claims")


@pytest.mark.integration
def test_public_spec_flow_rejects_wrong_spec_02_live_approval_without_registration(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    _approve_spec_02(spec_inputs, execute=False)
    original = deepcopy(spec_inputs["packet"])
    before = _tree_snapshot(spec_inputs["binding"].control_root)
    mutations = []
    wrong_owner = deepcopy(original)
    wrong_owner["document"]["owner"]["actor_id"] = REVIEWER_ACTOR
    mutations.append(wrong_owner)
    wrong_subject = deepcopy(original)
    wrong_subject["document"]["spec_02_subject"]["sha256"] = "f" * 64
    mutations.append(wrong_subject)
    wrong_promotion = deepcopy(original)
    wrong_promotion["document"]["spec_01_promotion"]["sha256"] = "f" * 64
    mutations.append(wrong_promotion)
    expired = deepcopy(original)
    expired["document"]["approved_at"] = "2026-08-16T13:00:00Z"
    mutations.append(expired)
    for malformed in mutations:
        _refresh_retry_id(malformed)
        spec_inputs["packet_path"].write_bytes(canonical_bytes(malformed))
        with pytest.raises(IntegrityError):
            cli.main(_advance_argv(spec_inputs, "approve_spec_02"))
        assert _tree_snapshot(spec_inputs["binding"].control_root) == before
    assert (
        "spec_02_live_run_approval" not in SpecFlow(load_discovery_operator(spec_inputs["config_path"]))._snapshot()[2]
    )


@pytest.mark.integration
def test_public_spec_flow_prepares_actual_owner_operated_spec_02_brief_after_approval(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    _approve_spec_02(spec_inputs)
    capsys.readouterr()
    prepared = _prepare_spec_02(spec_inputs)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["completed_stage"] == "prepare_spec_02"
    assert status["next_action"] == "start_spec_02"
    operator = load_discovery_operator(spec_inputs["config_path"])
    package = SpecFlow(operator)._snapshot()[2]["spec_02_operator_brief"][0]
    assert package["route_expected_return_type"] == "SpikeVerdict"
    assert package["operator_session"]["session_id"] == "codex-desktop-session-spec-02"
    assert package["prohibitions"] == [
        "no provider or model launch",
        "no automatic promotion",
        "import is candidate evidence only",
    ]
    delivered = next(
        event
        for event in operator.ledger.iter_events()
        if event["event_type"] == "OwnerOperatedContextDelivered" and event["stream_id"] == prepared["context_id"]
    )
    delivery_receipt = ObjectStore(operator.control_root).read(
        "context", delivered["payload"]["delivery_receipt_object_id"], 1
    )
    assert delivery_receipt["provider_launch"] is False
    assert not {"provider_template_sha256", "adapter_receipt", "transport_receipt"} & set(delivery_receipt)
    assert not replay_discovery(operator.ledger.iter_events()).get("claims")


def _seed_governed_operational_attempt(inputs: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    class OperationalClock(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return datetime(2026, 8, 1, 12, 30, tzinfo=UTC)

    monkeypatch.setattr(discovery_operator_module, "datetime", OperationalClock)
    harness = inputs["harness"]
    governed_operational_fixture = replace(
        harness,
        service=GovernedTestCommandService(
            harness.ledger.control_root,
            harness.ledger,
            harness.objects,
            harness.receipts,
            harness.schemas,
            authority_resolver=harness.authority_resolver,
            clock=lambda: datetime(2026, 8, 1, 12, 30, tzinfo=UTC),
            trusted_runtime_authority_provider=lambda: C1_TRUSTED_RUNTIME_AUTHORITY,
            authority_harness=harness,
        ),
    )
    _seed_running_attempt(governed_operational_fixture)


@pytest.mark.integration
def test_public_spec_flow_starts_spec_02_only_with_exact_lease_and_attempt(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_governed_operational_attempt(spec_inputs, monkeypatch)
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    _approve_spec_02(spec_inputs)
    capsys.readouterr()
    _prepare_spec_02(spec_inputs)
    capsys.readouterr()
    started = _start_spec_02(spec_inputs, candidate_id, assay_id)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["completed_stage"] == "start_spec_02"
    assert status["next_action"] == "return_spec_02"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    spike = projection["spikes"][started["spike_id"]]
    assert spike["status"] == "running"
    assert spike["attempt_id"] == C1_ATTEMPT_ID
    assert spike["lease_id"] == C1_LEASE_ID
    assert not projection.get("claims")


@pytest.mark.integration
def test_public_spec_flow_rejects_wrong_spec_02_lease_or_attempt_without_start(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_governed_operational_attempt(spec_inputs, monkeypatch)
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    _approve_spec_02(spec_inputs)
    capsys.readouterr()
    _prepare_spec_02(spec_inputs)
    capsys.readouterr()
    started = _start_spec_02(spec_inputs, candidate_id, assay_id, execute_start=False)
    capsys.readouterr()
    original = deepcopy(spec_inputs["packet"])
    before = _tree_snapshot(spec_inputs["binding"].control_root)
    for field, value in (
        ("lease_id", "els_019ffe2b-fd4b-7000-8000-ffffffffffff"),
        ("attempt_id", "att_019ffe2b-fd4b-7000-8000-ffffffffffff"),
        ("attempt_sha256", "f" * 64),
    ):
        malformed = deepcopy(original)
        malformed["commands"][0]["payload"][field] = value
        _refresh_retry_id(malformed)
        spec_inputs["packet_path"].write_bytes(canonical_bytes(malformed))
        with pytest.raises(IntegrityError, match="invalid Spike transition"):
            cli.main(_advance_argv(spec_inputs, "start_spec_02"))
        assert _tree_snapshot(spec_inputs["binding"].control_root) == before
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["spikes"][started["spike_id"]]["status"] == "authorized"
    assert projection["candidates"][candidate_id]["status"] == "spike_authorized"


@pytest.mark.integration
def test_public_spec_flow_registers_complete_spec_02_return_without_claim(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_governed_operational_attempt(spec_inputs, monkeypatch)
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    _approve_spec_02(spec_inputs)
    capsys.readouterr()
    _prepare_spec_02(spec_inputs)
    capsys.readouterr()
    started = _start_spec_02(spec_inputs, candidate_id, assay_id)
    capsys.readouterr()
    returned_spike = _return_spec_02_complete(spec_inputs, candidate_id, assay_id, started)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["completed_stage"] == "return_spec_02"
    assert status["next_action"] == "review_spec_02"
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["spikes"][started["spike_id"]]["status"] == "verdict_recorded"
    assert projection["spikes"][started["spike_id"]]["verdict_sha256"] == returned_spike["verdict_sha256"]
    assert not projection.get("claims")


@pytest.mark.integration
def test_public_spec_flow_partial_spec_02_return_and_review_is_terminal(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_governed_operational_attempt(spec_inputs, monkeypatch)
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    _approve_spec_02(spec_inputs)
    capsys.readouterr()
    _prepare_spec_02(spec_inputs)
    capsys.readouterr()
    started = _start_spec_02(spec_inputs, candidate_id, assay_id)
    capsys.readouterr()
    returned_spike = _return_spec_02_complete(spec_inputs, candidate_id, assay_id, started, partial=True)
    capsys.readouterr()
    review_id = _review_spec_02_complete(
        spec_inputs,
        candidate_id,
        started["spike_id"],
        returned_spike["verdict_sha256"],
        partial=True,
    )
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["capability_state"] == "PROVEN"
    assert status["completed_stage"] == "spec_02_partial_reviewed"
    assert status["next_action"] is None
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["reviews"][review_id]["status"] == "satisfied"
    assert projection["spikes"][started["spike_id"]]["status"] == "partial_reviewed"
    assert not projection.get("claims")


@pytest.mark.integration
def test_public_spec_flow_reviews_and_owner_decides_spec_02_without_scientific_claim(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_governed_operational_attempt(spec_inputs, monkeypatch)
    candidate_id, assay_id, candidate_sha256 = _seed_requested_spec_01(spec_inputs)
    capsys.readouterr()
    _accept_spec_01_brief_inputs(spec_inputs)
    capsys.readouterr()
    _prepare_spec_01(spec_inputs)
    capsys.readouterr()
    returned = _return_spec_01_complete(spec_inputs, candidate_id, assay_id, candidate_sha256)
    capsys.readouterr()
    review_id = _review_spec_01_complete(spec_inputs, candidate_id, assay_id, returned["scorecard_sha256"])
    capsys.readouterr()
    _decide_spec_01(spec_inputs, candidate_id, assay_id, review_id)
    capsys.readouterr()
    _approve_spec_02(spec_inputs)
    capsys.readouterr()
    _prepare_spec_02(spec_inputs)
    capsys.readouterr()
    started = _start_spec_02(spec_inputs, candidate_id, assay_id)
    capsys.readouterr()
    returned_spike = _return_spec_02_complete(spec_inputs, candidate_id, assay_id, started)
    capsys.readouterr()
    spike_review_id = _review_spec_02_complete(
        spec_inputs, candidate_id, started["spike_id"], returned_spike["verdict_sha256"]
    )
    capsys.readouterr()
    _decide_spec_02(spec_inputs, candidate_id, started["spike_id"], spike_review_id)
    capsys.readouterr()
    assert cli.main(_status_argv(spec_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["capability_state"] == "PROVEN"
    assert status["completed_stage"] == "spec_02_owner_decided"
    assert status["next_action"] is None
    projection = replay_discovery(load_discovery_operator(spec_inputs["config_path"]).ledger.iter_events())
    assert projection["reviews"][spike_review_id]["status"] == "satisfied"
    assert projection["candidates"][candidate_id]["status"] == "preregistration_authorized"
    assert not projection.get("claims")


@pytest.mark.integration
def test_spec_wrong_action_or_malformed_later_command_has_zero_mutation(spec_inputs: dict[str, Any]) -> None:
    before = _tree_snapshot(spec_inputs["binding"].control_root)
    with pytest.raises(IntegrityError, match="action argument and packet differ"):
        cli.main(_advance_argv(spec_inputs, action="bootstrap_assay_authority"))
    assert _tree_snapshot(spec_inputs["binding"].control_root) == before


@pytest.mark.integration
@pytest.mark.parametrize("mutation", ("extra", "tampered_manifest"))
def test_spec_brief_malformed_or_tampered_is_rejected_before_registration(
    spec_inputs: dict[str, Any], mutation: str
) -> None:
    flow = SpecFlow(load_discovery_operator(spec_inputs["config_path"]))
    document = _brief_document(spec_inputs)
    if mutation == "extra":
        document["unexpected"] = True
    else:
        document["brief_manifest"]["changed"] = True
    before = _tree_snapshot(spec_inputs["binding"].control_root)

    with pytest.raises(IntegrityError):
        flow._register_document("prepare_spec_01", document, None)

    assert _tree_snapshot(spec_inputs["binding"].control_root) == before

    malformed = deepcopy(spec_inputs["packet"])
    malformed["commands"].append({"not": "a command"})
    _refresh_retry_id(malformed)
    spec_inputs["packet_path"].write_bytes(canonical_bytes(malformed))
    with pytest.raises(IntegrityError, match="only the exact next route command"):
        cli.main(_advance_argv(spec_inputs))
    assert _tree_snapshot(spec_inputs["binding"].control_root) == before


@pytest.mark.integration
def test_spec_changed_command_same_retry_identity_conflicts_without_new_publication(
    spec_inputs: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(_advance_argv(spec_inputs)) == 0
    capsys.readouterr()
    before = _tree_snapshot(spec_inputs["binding"].control_root)
    changed = deepcopy(spec_inputs["packet"])
    changed["commands"][0]["idempotency_key"] = "changed-under-same-command-identity"
    spec_inputs["packet_path"].write_bytes(canonical_bytes(changed))

    with pytest.raises(ConflictError):
        cli.main(_advance_argv(spec_inputs))

    assert _tree_snapshot(spec_inputs["binding"].control_root) == before
