from copy import copy, deepcopy
from dataclasses import FrozenInstanceError, asdict, fields
from datetime import UTC, datetime
from functools import lru_cache
import inspect
from pathlib import Path
import shutil
import threading
from types import SimpleNamespace

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.command.service import CommandService
from research_system.cli import _schemas_for_store_manifest
from research_system.errors import (
    ArsError,
    ConfigurationError,
    ConflictError,
    IntegrityError,
    SchemaError,
)
from research_system.evals.release_publication import (
    BoundReleasePublicationEvidence,
    PublicationEvidenceError,
    ReleasePublicationRequest,
    StoredReleasePublicationEvidence,
    content_artefact_id,
    verify_release_publication,
    verify_replayed_release,
)
from research_system.evals.harness import (
    build_release_decision,
    decision_document,
    run_all_scenarios,
    run_p0_coverage,
)
from research_system.evals.release_snapshot import (
    _result,
    build_release_snapshot_documents,
    rederive_release_from_snapshot,
)
from research_system.projection.replay import replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import (
    EventDraft,
    EventLedger,
    _take_release_submit_guard,
)
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore
from tests.research_system.factories import authority_bootstrap, control_plane


ROOT = Path(__file__).resolve().parents[3]
PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
DECISION_ID = "rgd_01978abc-1003-7000-8000-000000001003"
MANIFEST_REF = "art_01978abc-2001-7000-8000-000000002001"
CONTROL_REF = "art_01978abc-2002-7000-8000-000000002002"
GRANT_ID = "agr_01978abc-1001-7000-8000-000000001001"
EVENT_ID = "evt_01978abc-2003-7000-8000-000000002003"
COMMAND_ID = "cmd_01978abc-2004-7000-8000-000000002004"
BATCH_ID = "txb_01978abc-2005-7000-8000-000000002005"


@lru_cache(maxsize=1)
def producer_inputs():
    """Build one exact cached set of typed fake W6/W7/W8 producer inputs."""
    coverage_path = ROOT / ".research-system" / "evals" / "p0-coverage.yaml"
    evidence = run_p0_coverage(
        coverage_path,
        fixture_root=coverage_path.parent / "fixtures",
        schema_root=ROOT / ".research-system" / "schemas",
    )
    scenarios = run_all_scenarios()
    return evidence, scenarios


@lru_cache(maxsize=1)
def producer_snapshot() -> tuple[dict, dict, dict]:
    """Build one exact cached fake W6/W7/W8 publication snapshot."""
    evidence, scenarios = producer_inputs()
    record, _ = build_release_decision(
        evidence,
        scenarios,
        decided_at="2026-07-13T12:00:00Z",
        release_gate_decision_id=DECISION_ID,
    )
    source = decision_document(record)
    manifest, control = build_release_snapshot_documents(
        evidence,
        scenarios,
        source,
        project_id=PROJECT_ID,
        store_identity="4" * 64,
    )
    return source, manifest, control


def publication_request() -> dict:
    return {
        "schema": "ars://evals/release-publication-request",
        "project_id": PROJECT_ID,
        "release_decision_id": DECISION_ID,
        "evaluation_runs_manifest_ref": MANIFEST_REF,
        "control_binding_ref": CONTROL_REF,
        "publication_authority_grant_id": GRANT_ID,
        "publication_authority_sha256": "a" * 64,
        "idempotency_key": "release-publication:synthetic-p0",
    }


def publication_command(command_id: str = COMMAND_ID) -> dict:
    return {
        "command_id": command_id,
        "command_type": "PublishReleaseGateDecision",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-13T12:00:00Z",
        "actor_id": "act_01978abc-1002-7000-8000-000000001002",
        "on_behalf_of_actor_id": None,
        "authority_grant_id": GRANT_ID,
        "target_stream_id": DECISION_ID,
        "expected_stream_version": 0,
        "idempotency_key": "release-publication:synthetic-p0",
        "correlation_id": "synthetic-publication",
        "causation_id": None,
        "reason": "record the blocked synthetic P0 decision",
        "evidence_refs": [MANIFEST_REF, CONTROL_REF],
        "payload": publication_request(),
    }


def published_decision() -> dict:
    source = deepcopy(producer_snapshot()[0])
    source["canonical_event_ref"] = EVENT_ID
    return source


def published_event() -> dict:
    return {
        "event_id": EVENT_ID,
        "event_type": "ReleaseGateDecisionPublished",
        "schema_id": "ars://core/event/ReleaseGateDecisionPublished",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "stream_id": DECISION_ID,
        "stream_version": 1,
        "global_position": 3,
        "transaction_id": BATCH_ID,
        "transaction_index": 1,
        "transaction_count": 1,
        "command_id": COMMAND_ID,
        "command_type": "PublishReleaseGateDecision",
        "idempotency_key": "release-publication:synthetic-p0",
        "command_payload_hash": "e" * 64,
        "correlation_id": "synthetic-publication",
        "causation_id": None,
        "actor_id": "act_01978abc-1002-7000-8000-000000001002",
        "authority_grant_id": GRANT_ID,
        "occurred_at": None,
        "recorded_at": "2026-07-13T12:00:01Z",
        "payload": {
            "release_decision": published_decision(),
            "source_decision_sha256": "f" * 64,
            "evaluation_runs_manifest_ref": MANIFEST_REF,
            "evaluation_runs_manifest_sha256": "1" * 64,
            "control_binding_ref": CONTROL_REF,
            "control_binding_sha256": "2" * 64,
            "publication_authority_grant_id": GRANT_ID,
            "publication_authority_sha256": "a" * 64,
            "gate5_authorized": False,
            "candidate_status": "blocked",
        },
        "previous_event_hash": "0" * 64,
        "event_hash": "3" * 64,
    }


def source_decision() -> dict:
    return {**published_decision(), "canonical_event_ref": "unpublished:p0"}


def evidence_resolver(*, derived: dict | None = None, gate: object = False):
    source, stored_manifest, stored_control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    control = deepcopy(stored_control)

    def rederive(resolved_manifest, resolved_control):
        resolved_source = resolved_manifest["release_decision"]
        if (
            resolved_manifest["project_id"] != PROJECT_ID
            or resolved_control["project_id"] != PROJECT_ID
            or resolved_control["store_identity"] != "4" * 64
            or resolved_control["coverage_manifest_id"] != resolved_source["coverage_manifest_id"]
        ):
            raise ValueError("unit publication evidence binding mismatch")
        if derived is not None:
            return derived, gate
        rebuilt, _ = rederive_release_from_snapshot(
            resolved_manifest,
            resolved_control,
        )
        return rebuilt, gate

    return BoundReleasePublicationEvidence(
        evaluation_runs_manifest_ref=MANIFEST_REF,
        evaluation_runs_manifest=manifest,
        control_binding_ref=CONTROL_REF,
        control_binding=control,
        expected_store_identity="4" * 64,
        rederive=rederive,
    )


def canonical_publication_plane(tmp_path):
    """Return a unit harness with replayable canonical authority genesis."""
    control_root = tmp_path / "control"
    bootstrap = authority_bootstrap()
    identity = initialize_authority_control_store(
        [ROOT],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
    )
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    ledger = EventLedger(control_root, PROJECT_ID, schemas)
    objects = ObjectStore(control_root)
    receipts = ReceiptStore(control_root)
    service = CommandService(control_root, ledger, objects, receipts, schemas)
    return SimpleNamespace(
        service=service,
        ledger=ledger,
        objects=objects,
        receipts=receipts,
        identity=identity,
        authority_hash=bootstrap["publication_grant_sha256"],
    )


def canonical_publication_command(harness, command_id: str = COMMAND_ID) -> dict:
    """Bind a unit publication command to canonical bootstrap authority."""
    command = publication_command(command_id)
    command["payload"] = {
        **command["payload"],
        "publication_authority_sha256": harness.authority_hash,
    }
    return command


def revoke_publication_command(harness) -> dict:
    """Return a root-authorized revocation of the publication grant."""
    bootstrap = authority_bootstrap()
    return {
        "command_id": "cmd_01978abc-2090-7000-8000-000000002090",
        "command_type": "RevokeAuthorityGrant",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": bootstrap["root_grant"]["actor_id"],
        "on_behalf_of_actor_id": None,
        "authority_grant_id": bootstrap["root_grant"]["authority_grant_id"],
        "target_stream_id": GRANT_ID,
        "expected_stream_version": 1,
        "idempotency_key": "revoke-publication-after-release",
        "correlation_id": "synthetic-publication-revocation",
        "causation_id": None,
        "reason": "prove historical publication survives revocation",
        "evidence_refs": [],
        "payload": {
            "project_id": PROJECT_ID,
            "target_grant_id": GRANT_ID,
            "target_grant_sha256": harness.authority_hash,
            "authority_grant_sha256": bootstrap["root_grant_sha256"],
            "reason": "prove historical publication survives revocation",
        },
    }


def test_release_publication_request_has_a_strict_registered_contract() -> None:
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    registry.validate(
        "ars://evals/release-publication-request",
        publication_request(),
    )
    _source, manifest, control = producer_snapshot()
    registry.validate("ars://evals/release-publication-evidence", manifest)
    registry.validate("ars://evals/release-control-binding", control)


def test_store_manifest_schema_root_ambiguity_fails_closed(tmp_path) -> None:
    roots = [tmp_path / "a", tmp_path / "b"]
    for root in roots:
        shutil.copytree(
            ROOT / ".research-system" / "schemas",
            root / ".research-system" / "schemas",
        )
    with pytest.raises(ConfigurationError, match="ambiguous schema roots"):
        _schemas_for_store_manifest({"code_roots": [str(root) for root in roots]})


def test_authority_resolver_rejects_missing_registry(tmp_path) -> None:
    with pytest.raises(TypeError):
        inspect.signature(LedgerAuthorityGrantResolver).bind(
            tmp_path,
            PROJECT_ID,
            "0" * 64,
        )
    with pytest.raises(TypeError, match="trusted SchemaRegistry"):
        constructor = LedgerAuthorityGrantResolver
        invalid_args = (
            tmp_path,
            PROJECT_ID,
            "0" * 64,
            None,
        )
        constructor(*invalid_args)


def test_release_publication_request_model_is_frozen_and_exact() -> None:
    request = ReleasePublicationRequest.from_dict(publication_request())
    assert request.release_decision_id == DECISION_ID
    assert request.to_dict() == publication_request()
    with pytest.raises(FrozenInstanceError):
        request.project_id = "prj_01978abc-9999-7000-8000-000000009999"


def test_release_event_has_a_strict_full_registered_contract() -> None:
    SchemaRegistry(ROOT / ".research-system" / "schemas").validate(
        "ars://core/event/ReleaseGateDecisionPublished",
        published_event(),
    )


def test_full_canonical_evidence_is_rederived_and_bound() -> None:
    verified = verify_release_publication(
        ReleasePublicationRequest.from_dict(publication_request()),
        evidence_resolver(),
        SchemaRegistry(ROOT / ".research-system" / "schemas"),
    )
    payload = verified.payload_for(EVENT_ID)
    assert payload["release_decision"]["canonical_event_ref"] == EVENT_ID
    assert payload["release_decision"]["decision"] == "blocked"
    assert payload["gate5_authorized"] is False
    assert payload["candidate_status"] == "blocked"


def test_snapshot_round_trips_every_grader_result_field_exactly() -> None:
    evidence, _scenarios = producer_inputs()
    _source, manifest, _control = producer_snapshot()
    restored = tuple(_result(item) for item in manifest["release_results"])
    assert tuple(asdict(item) for item in restored) == tuple(asdict(item) for item in evidence.results)
    assert set(manifest["release_results"][0]) == {item.name for item in fields(type(evidence.results[0]))}


def test_retained_policy_hash_cannot_attest_changed_policy_semantics() -> None:
    _source, stored_manifest, stored_control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    manifest["canonical_policy_bundle"]["controls"][0]["failure_mode"] = "allow"
    resolver = BoundReleasePublicationEvidence(
        MANIFEST_REF,
        manifest,
        CONTROL_REF,
        deepcopy(stored_control),
        "4" * 64,
        rederive_release_from_snapshot,
    )
    with pytest.raises(PublicationEvidenceError):
        verify_release_publication(
            ReleasePublicationRequest.from_dict(publication_request()),
            resolver,
            SchemaRegistry(ROOT / ".research-system" / "schemas"),
        )


@pytest.mark.parametrize(
    "producer_boundary",
    [
        "coverage_selection",
        "variant_row",
        "variant_execution",
        "variant_binding",
        "observed_assertion",
        "canonical_bundle",
        "applicability_requirement",
        "applicability_decision",
        "applicability_operation",
        "parity_evidence",
        "parity_report_row",
    ],
)
def test_release_evidence_schema_rejects_unknown_nested_fields(
    producer_boundary,
) -> None:
    _source, stored_manifest, _stored_control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    if producer_boundary == "coverage_selection":
        manifest["coverage"]["selected_fixture_revisions"][0].append("extra")
    elif producer_boundary == "variant_row":
        manifest["variant_rows"][0]["unexpected"] = True
    elif producer_boundary == "variant_execution":
        manifest["variant_executions"][0]["matrix_row"]["unexpected"] = True
    elif producer_boundary == "variant_binding":
        manifest["variant_executions"][0]["grader_result_bindings"][0].append(
            "unexpected"
        )
    elif producer_boundary == "observed_assertion":
        manifest["variant_executions"][0]["observed_assertions"][0][
            "unexpected"
        ] = True
    elif producer_boundary == "canonical_bundle":
        manifest["canonical_policy_bundle"]["unexpected"] = True
    elif producer_boundary == "applicability_requirement":
        manifest["policy_applicability"]["controls"][0]["provider_requirements"][0]["unexpected"] = True
    elif producer_boundary == "applicability_decision":
        manifest["policy_applicability"]["source"]["decision_payload"][
            "unexpected"
        ] = True
    elif producer_boundary == "applicability_operation":
        operations = manifest["policy_applicability"]["source"]["controls"][0][
            "provider_requirements"
        ][0]["canonical_observed_value"]["operations"]
        next(iter(operations.values()))["unexpected"] = True
    elif producer_boundary == "parity_evidence":
        manifest["parity_evidence"][0]["unexpected"] = True
    else:
        manifest["parity_report"]["rows"][0]["unexpected"] = True
    with pytest.raises(SchemaError):
        SchemaRegistry(ROOT / ".research-system" / "schemas").validate(
            "ars://evals/release-publication-evidence",
            manifest,
        )


def test_stored_evidence_resolves_after_restart_and_rejects_byte_tamper(
    tmp_path,
) -> None:
    _source, stored_manifest, stored_control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    control = deepcopy(stored_control)
    manifest_ref = content_artefact_id(manifest)
    control_ref = content_artefact_id(control)
    objects = ObjectStore(tmp_path)
    manifest_path = objects.write("artefact", manifest_ref, 1, manifest)
    objects.write("artefact", control_ref, 1, control)
    restarted = StoredReleasePublicationEvidence(
        ObjectStore(tmp_path),
        "4" * 64,
        rederive_release_from_snapshot,
    )
    assert restarted.resolve_evaluation_runs(manifest_ref) == manifest
    verify_release_publication(
        ReleasePublicationRequest.from_dict(
            {
                **publication_request(),
                "evaluation_runs_manifest_ref": manifest_ref,
                "control_binding_ref": control_ref,
            }
        ),
        restarted,
        SchemaRegistry(ROOT / ".research-system" / "schemas"),
    )
    manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
    with pytest.raises(IntegrityError, match="canonical"):
        restarted.resolve_evaluation_runs(manifest_ref)


def test_rederivation_callback_mutation_cannot_change_attested_snapshots() -> None:
    resolver = evidence_resolver()
    original_manifest = resolver.resolve_evaluation_runs(MANIFEST_REF)
    original_control = resolver.resolve_control_binding(CONTROL_REF)
    source = source_decision()

    def mutating_rederive(manifest, control):
        manifest["release_decision"]["required_verdicts"].append(["x", "pass"])
        control["coverage_manifest_id"] = "tampered"
        return source, False

    mutating = BoundReleasePublicationEvidence(
        MANIFEST_REF,
        original_manifest,
        CONTROL_REF,
        original_control,
        "4" * 64,
        mutating_rederive,
    )
    verified = verify_release_publication(
        ReleasePublicationRequest.from_dict(publication_request()),
        mutating,
        SchemaRegistry(ROOT / ".research-system" / "schemas"),
    )
    assert verified.evaluation_runs_manifest_sha256 == sha256_hex(canonical_bytes(original_manifest))
    assert verified.control_binding_sha256 == sha256_hex(canonical_bytes(original_control))


def test_semantic_rederivation_mismatch_fails_closed() -> None:
    changed = source_decision()
    changed["evidence_snapshot_hash"] = "9" * 64
    with pytest.raises(PublicationEvidenceError, match="re-derived decision mismatch"):
        verify_release_publication(
            ReleasePublicationRequest.from_dict(publication_request()),
            evidence_resolver(derived=changed),
            SchemaRegistry(ROOT / ".research-system" / "schemas"),
        )


@pytest.mark.parametrize(
    "producer_seam",
    [
        "binding_trace",
        "result_trace",
        "variant_execution",
        "parity_evidence",
        "parity_report",
        "applicability",
        "scenario",
        "control_version",
    ],
)
def test_stored_snapshot_rejects_one_at_a_time_document_tamper(
    producer_seam,
) -> None:
    _source, stored_manifest, stored_control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    control = deepcopy(stored_control)
    if producer_seam == "binding_trace":
        manifest["release_bindings"][0]["trace_hash"] = "0" * 64
    elif producer_seam == "result_trace":
        manifest["release_results"][0]["trace_hash"] = "0" * 64
    elif producer_seam == "variant_execution":
        manifest["variant_executions"][0]["observed_assertions"][0]["canonical_observed_value"] = {"tampered": True}
    elif producer_seam == "parity_evidence":
        manifest["parity_evidence"][0]["evidence_hash"] = "0" * 64
    elif producer_seam == "parity_report":
        manifest["parity_report"]["report_hash"] = "0" * 64
    elif producer_seam == "applicability":
        manifest["policy_applicability"]["applicability_hash"] = "0" * 64
    elif producer_seam == "scenario":
        manifest["operations_scenarios"][0]["event_types"][0] = "Tampered"
    else:
        control["derivation_contract_version"] = "changed"
    resolver = BoundReleasePublicationEvidence(
        MANIFEST_REF,
        manifest,
        CONTROL_REF,
        control,
        "4" * 64,
        rederive_release_from_snapshot,
    )
    with pytest.raises(PublicationEvidenceError):
        verify_release_publication(
            ReleasePublicationRequest.from_dict(publication_request()),
            resolver,
            SchemaRegistry(ROOT / ".research-system" / "schemas"),
        )


@pytest.mark.parametrize(
    "producer_seam",
    [
        "grader_results",
        "variant_execution",
        "parity_evidence",
        "parity_report",
        "applicability",
        "operations_scenarios",
    ],
)
def test_public_verifier_rejects_pre_serialization_producer_perturbation(
    producer_seam,
) -> None:
    evidence, scenarios = producer_inputs()
    evidence = copy(evidence)
    if producer_seam == "grader_results":
        object.__setattr__(evidence, "results", evidence.results[:-1])
    elif producer_seam == "variant_execution":
        object.__setattr__(
            evidence,
            "variant_executions",
            evidence.variant_executions[:-1],
        )
    elif producer_seam == "parity_evidence":
        object.__setattr__(
            evidence,
            "parity_evidence",
            evidence.parity_evidence[:-1],
        )
    elif producer_seam == "parity_report":
        report = copy(evidence.parity_report)
        object.__setattr__(report, "report_hash", "0" * 64)
        object.__setattr__(evidence, "parity_report", report)
    elif producer_seam == "applicability":
        applicability = copy(evidence.policy_applicability)
        object.__setattr__(
            applicability,
            "applicability_hash",
            "0" * 64,
        )
        object.__setattr__(evidence, "policy_applicability", applicability)
    else:
        scenarios = scenarios[:-1]
    source = deepcopy(producer_snapshot()[0])
    manifest, control = build_release_snapshot_documents(
        evidence,
        scenarios,
        source,
        project_id=PROJECT_ID,
        store_identity="4" * 64,
    )
    resolver = BoundReleasePublicationEvidence(
        MANIFEST_REF,
        manifest,
        CONTROL_REF,
        control,
        "4" * 64,
        rederive_release_from_snapshot,
    )
    with pytest.raises(PublicationEvidenceError):
        verify_release_publication(
            ReleasePublicationRequest.from_dict(publication_request()),
            resolver,
            SchemaRegistry(ROOT / ".research-system" / "schemas"),
        )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("grader_result_id", "grr_invalid"),
        ("evaluation_run_id", "run_invalid"),
        ("executed_by_actor_id", "act_invalid"),
        ("evidence_refs", ["trc_invalid"]),
    ],
)
def test_release_result_identity_tamper_fails_closed(field, invalid) -> None:
    _source, stored_manifest, _control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    manifest["release_results"][0][field] = invalid
    with pytest.raises(SchemaError):
        SchemaRegistry(ROOT / ".research-system" / "schemas").validate(
            "ars://evals/release-publication-evidence",
            manifest,
        )


def test_stored_snapshot_rederivation_uses_resolved_documents(tmp_path) -> None:
    _source, stored_manifest, stored_control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    control = deepcopy(stored_control)
    objects = ObjectStore(tmp_path)
    manifest_ref = content_artefact_id(manifest)
    control_ref = content_artefact_id(control)
    objects.write("artefact", manifest_ref, 1, manifest)
    objects.write("artefact", control_ref, 1, control)
    verified = verify_release_publication(
        ReleasePublicationRequest.from_dict(
            {
                **publication_request(),
                "evaluation_runs_manifest_ref": manifest_ref,
                "control_binding_ref": control_ref,
            }
        ),
        StoredReleasePublicationEvidence(
            objects,
            "4" * 64,
            rederive_release_from_snapshot,
        ),
        SchemaRegistry(ROOT / ".research-system" / "schemas"),
    )
    assert verified.source_decision_sha256 == sha256_hex(canonical_bytes(source_decision()))


def test_concurrent_identical_producer_snapshot_writes_are_idempotent(
    tmp_path,
    monkeypatch,
) -> None:
    import research_system.store.objects as object_module

    _source, stored_manifest, _control = producer_snapshot()
    manifest = deepcopy(stored_manifest)
    reference = content_artefact_id(manifest)
    entered = threading.Barrier(3)
    release = threading.Event()

    def pause(_temporary):
        entered.wait(timeout=2)
        assert release.wait(2)

    monkeypatch.setattr(object_module, "_after_object_temp_fsync", pause)
    paths = []
    errors = []

    def publish():
        try:
            paths.append(ObjectStore(tmp_path).write("artefact", reference, 1, manifest))
        except Exception as exc:  # pragma: no branch - asserted below
            errors.append(exc)

    writers = [threading.Thread(target=publish) for _ in range(2)]
    for writer in writers:
        writer.start()
    entered.wait(timeout=2)
    release.set()
    for writer in writers:
        writer.join(timeout=2)
        assert not writer.is_alive()
    assert errors == []
    assert len(set(paths)) == 1
    assert ObjectStore(tmp_path).read("artefact", reference, 1) == manifest


def test_foreign_but_well_formed_store_identity_fails_closed() -> None:
    original = evidence_resolver()
    foreign = BoundReleasePublicationEvidence(
        MANIFEST_REF,
        original.resolve_evaluation_runs(MANIFEST_REF),
        CONTROL_REF,
        original.resolve_control_binding(CONTROL_REF),
        "5" * 64,
        original.rederive_release_decision,
    )
    with pytest.raises(PublicationEvidenceError, match="store identity mismatch"):
        verify_release_publication(
            ReleasePublicationRequest.from_dict(publication_request()),
            foreign,
            SchemaRegistry(ROOT / ".research-system" / "schemas"),
        )


def test_caller_built_release_draft_cannot_bypass_command_service(
    tmp_path,
) -> None:
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    verified = verify_release_publication(
        ReleasePublicationRequest.from_dict(publication_request()),
        evidence_resolver(),
        schemas,
    )
    base = {
        key: value
        for key, value in published_event().items()
        if key
        not in {
            "event_id",
            "project_id",
            "stream_version",
            "global_position",
            "transaction_id",
            "transaction_index",
            "transaction_count",
            "recorded_at",
            "payload",
            "previous_event_hash",
            "event_hash",
        }
    }
    ledger = EventLedger(tmp_path / "control", PROJECT_ID)
    service = CommandService(
        ledger.control_root,
        ledger,
        ObjectStore(ledger.control_root),
        ReceiptStore(ledger.control_root),
        schemas,
    )
    assert not hasattr(ledger, "_release_draft_capability")
    assert not hasattr(ledger, "_issued_release_drafts")
    assert not hasattr(service, "_release_draft_factory")
    constructor = EventDraft
    with pytest.raises(ArsError, match="CommandService"):
        caller_draft = constructor(
            base,
            lambda allocated: verified.payload_for(allocated.event_id),
        )
        ledger.append([caller_draft])
    with pytest.raises(ArsError, match="validated CommandService.submit"):
        forged_internal = object.__new__(EventDraft)
        object.__setattr__(forged_internal, "envelope", base)
        object.__setattr__(
            forged_internal,
            "finalize_payload",
            lambda allocated: verified.payload_for(allocated.event_id),
        )
        ledger.append([forged_internal])
    ledger._issued_release_drafts = {id(forged_internal): forged_internal}
    try:
        with pytest.raises(ArsError, match="validated CommandService.submit"):
            ledger.append([forged_internal])
    finally:
        del ledger._issued_release_drafts
    assert tuple(ledger.iter_events()) == ()


def test_bound_service_cannot_directly_invoke_release_append(tmp_path) -> None:
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    verified = verify_release_publication(
        ReleasePublicationRequest.from_dict(publication_request()),
        evidence_resolver(),
        schemas,
    )
    base = {
        key: value
        for key, value in published_event().items()
        if key
        not in {
            "event_id",
            "project_id",
            "stream_version",
            "global_position",
            "transaction_id",
            "transaction_index",
            "transaction_count",
            "recorded_at",
            "payload",
            "previous_event_hash",
            "event_hash",
        }
    }
    harness = control_plane(tmp_path)
    assert not hasattr(harness.ledger, "_append_release_from_command_service")
    with pytest.raises(ArsError, match="validated CommandService.submit"):
        harness.ledger._append_release_from_validated_submit(
            harness.service,
            base,
            lambda allocated: verified.payload_for(allocated.event_id),
        )
    assert tuple(harness.ledger.iter_events()) == ()


def test_release_submit_guard_cannot_be_claimed_by_an_alternate_factory() -> None:
    with pytest.raises(ArsError, match="already bound"):
        _take_release_submit_guard()


def test_command_service_submit_preserves_public_signature_and_guard_metadata(
    tmp_path,
) -> None:
    public = CommandService.submit
    signature = inspect.signature(public)
    assert list(signature.parameters) == ["self", "envelope"]
    assert signature.parameters["envelope"].annotation == "dict[str, Any]"
    assert signature.return_annotation == "Receipt"
    assert public.__module__ == "research_system.command.service"
    assert public.__annotations__ == {
        "envelope": "dict[str, Any]",
        "return": "Receipt",
    }
    assert not hasattr(public, "__wrapped__")

    implementation = next(
        cell.cell_contents
        for cell in public.__closure__ or ()
        if inspect.isfunction(cell.cell_contents)
        and cell.cell_contents.__name__ == "submit"
    )
    assert inspect.signature(implementation).parameters["release_append"].default is None
    harness = control_plane(tmp_path)
    with pytest.raises(ArsError, match="guarded release continuation"):
        implementation(harness.service, publication_command())
    assert tuple(harness.ledger.iter_events()) == ()


def test_captured_release_draft_rejects_cross_ledger_and_reuse(
    tmp_path,
    monkeypatch,
) -> None:
    import research_system.store.ledger as ledger_module

    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first = control_plane(first_root)
    second = control_plane(second_root)
    first.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256="a" * 64)
    )
    first.service.release_publication_evidence = evidence_resolver()
    captured = []
    consume = ledger_module._consume_release_draft

    def capture(ledger, draft):
        captured.append(draft)
        consume(ledger, draft)

    monkeypatch.setattr(ledger_module, "_consume_release_draft", capture)
    assert first.service.submit(publication_command()).status == "accepted"
    assert len(captured) == 1
    draft = captured[0]
    with pytest.raises(ArsError, match="validated CommandService.submit"):
        second.ledger.append([draft])
    with pytest.raises(ArsError, match="validated CommandService.submit"):
        first.ledger.append([draft])
    assert tuple(second.ledger.iter_events()) == ()
    assert len(tuple(first.ledger.iter_events())) == 1


def test_stale_release_append_leaves_no_issuance_state_and_retry_succeeds(
    tmp_path,
    monkeypatch,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256="a" * 64)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    persisted_tail = harness.ledger._persisted_tail
    stale_once = [True]

    def persisted_tail_with_one_conflict():
        if stale_once:
            stale_once.pop()
            return 1, "f" * 64
        return persisted_tail()

    monkeypatch.setattr(
        harness.ledger,
        "_persisted_tail",
        persisted_tail_with_one_conflict,
    )
    append = harness.ledger.append
    captured = []

    def capture(proposed_events, *, snapshot=None):
        proposed = list(proposed_events)
        captured.extend(item for item in proposed if isinstance(item, EventDraft))
        return append(proposed, snapshot=snapshot)

    monkeypatch.setattr(harness.ledger, "append", capture)

    with pytest.raises(ConflictError, match="persisted ledger tail"):
        harness.service.submit(publication_command())

    assert not hasattr(harness.ledger, "_issued_release_drafts")
    assert len(captured) == 1
    with pytest.raises(ArsError, match="validated CommandService.submit"):
        harness.ledger.append([captured[0]])
    assert tuple(harness.ledger.iter_events()) == ()
    receipt = harness.service.submit(publication_command())
    assert receipt.status == "accepted"
    assert len(tuple(harness.ledger.iter_events())) == 1


def test_release_append_requires_exact_registered_release_schema(tmp_path) -> None:
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    schemas._schemas.pop("ars://core/event/ReleaseGateDecisionPublished")
    control_root = tmp_path / "control"
    ledger = EventLedger(control_root, PROJECT_ID, schemas)
    service = CommandService(
        control_root,
        ledger,
        ObjectStore(control_root),
        ReceiptStore(control_root),
        schemas,
    )
    service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256="a" * 64)
    )
    service.release_publication_evidence = evidence_resolver()
    with pytest.raises(SchemaError, match="ReleaseGateDecisionPublished"):
        service.submit(publication_command())
    assert tuple(ledger.iter_events()) == ()
    assert list(control_root.rglob("*.jsonl")) == []


def test_valid_publication_request_fails_closed_without_authorizer(tmp_path) -> None:
    harness = control_plane(tmp_path)
    receipt = harness.service.submit(publication_command())
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_publication_authorizer_unavailable"
    assert tuple(harness.ledger.iter_events()) == ()


def test_authorized_verified_command_publishes_one_self_referential_event(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256="a" * 64)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    receipt = harness.service.submit(publication_command())
    assert receipt.status == "accepted"
    events = tuple(harness.ledger.iter_events())
    assert len(events) == 1
    assert events[0]["event_type"] == "ReleaseGateDecisionPublished"
    assert events[0]["stream_id"] == DECISION_ID
    assert events[0]["payload"]["release_decision"]["canonical_event_ref"] == events[0]["event_id"]


def test_authority_store_init_is_idempotent_after_release_publication(
    tmp_path,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256=harness.authority_hash)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    assert harness.service.submit(canonical_publication_command(harness)).status == ("accepted")
    bootstrap = authority_bootstrap()
    assert (
        initialize_authority_control_store(
            [ROOT],
            harness.ledger.control_root,
            PROJECT_ID,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
        )
        == harness.identity
    )


def test_rejected_exact_retry_with_new_command_id_returns_original_outcome(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    original = harness.service.submit(publication_command())
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256="a" * 64)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    retry = publication_command("cmd_01978abc-2006-7000-8000-000000002006")
    assert harness.service.submit(retry) == original
    assert tuple(harness.ledger.iter_events()) == ()


def test_scoped_retry_with_changed_payload_returns_conflict_without_event(
    tmp_path,
) -> None:
    harness = control_plane(tmp_path)
    harness.service.submit(publication_command())
    changed = publication_command("cmd_01978abc-2007-7000-8000-000000002007")
    changed_ref = "art_01978abc-2008-7000-8000-000000002008"
    changed["payload"] = {
        **changed["payload"],
        "evaluation_runs_manifest_ref": changed_ref,
    }
    changed["evidence_refs"] = [changed_ref, CONTROL_REF]
    receipt = harness.service.submit(changed)
    assert receipt.status == "conflict"
    assert receipt.reason_code == "idempotency_conflict"
    assert tuple(harness.ledger.iter_events()) == ()


def test_accepted_exact_retry_with_new_command_id_returns_original_event(
    tmp_path,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256=harness.authority_hash)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    original = harness.service.submit(canonical_publication_command(harness))
    retry = canonical_publication_command(harness, "cmd_01978abc-2009-7000-8000-000000002009")
    assert harness.service.submit(retry) == original
    assert len(tuple(harness.ledger.iter_events())) == 3


def test_historical_publication_retry_and_eval_survive_later_revocation(
    tmp_path,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    authority = LedgerAuthorityGrantResolver(
        harness.ledger.control_root,
        PROJECT_ID,
        harness.identity,
        schemas,
    )
    harness.service.authority_resolver = authority
    harness.service.release_publication_evidence = evidence_resolver()
    harness.service.clock = lambda: datetime(2026, 7, 12, 12, tzinfo=UTC)
    original = harness.service.submit(canonical_publication_command(harness))
    assert original.status == "accepted"
    assert harness.service.submit(revoke_publication_command(harness)).status == ("accepted")

    retry = canonical_publication_command(
        harness,
        "cmd_01978abc-2091-7000-8000-000000002091",
    )
    assert harness.service.submit(retry) == original
    changed = canonical_publication_command(
        harness,
        "cmd_01978abc-2092-7000-8000-000000002092",
    )
    changed["idempotency_key"] = "release-publication:new-after-revocation"
    changed["payload"] = {
        **changed["payload"],
        "idempotency_key": "release-publication:new-after-revocation",
    }
    rejected = harness.service.submit(changed)
    assert rejected.status == "rejected"
    assert rejected.reason_code == "release_publication_unauthorized"

    projection = replay(harness.ledger.iter_events(), schema_registry=schemas)
    assert projection["authority_grants"][GRANT_ID]["status"] == "revoked"
    record = projection["release_decisions"][DECISION_ID]
    assert (
        verify_replayed_release(
            record["release_decision"],
            source_decision(),
            projection,
            PROJECT_ID,
            evidence_resolver(),
            schemas,
        )
        == record
    )


def test_authority_identity_lookup_survives_expiry_without_authorizing_use(
    tmp_path,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    authority = LedgerAuthorityGrantResolver(
        harness.ledger.control_root,
        PROJECT_ID,
        harness.identity,
        schemas,
    )
    identity = authority.grant_identity(GRANT_ID)
    assert identity.authority_grant_sha256 == harness.authority_hash
    with pytest.raises(ArsError, match="expired"):
        authority.resolve(
            GRANT_ID,
            publication_command()["actor_id"],
            "PublishReleaseGateDecision",
            PROJECT_ID,
            "release_gate_decision",
            DECISION_ID,
            datetime(2026, 7, 14, tzinfo=UTC),
        )


def test_authority_resolution_replays_one_verified_projection(
    tmp_path,
    monkeypatch,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    authority = LedgerAuthorityGrantResolver(
        harness.ledger.control_root,
        PROJECT_ID,
        harness.identity,
        schemas,
    )
    calls = 0
    project = authority._projection

    def counted_projection():
        nonlocal calls
        calls += 1
        return project()

    monkeypatch.setattr(authority, "_projection", counted_projection)
    command = canonical_publication_command(harness)
    authority.resolve(
        GRANT_ID,
        command["actor_id"],
        "PublishReleaseGateDecision",
        PROJECT_ID,
        "release_gate_decision",
        DECISION_ID,
        datetime(2026, 7, 12, 12, tzinfo=UTC),
    )
    assert calls == 1


@pytest.mark.parametrize(
    ("target", "value"),
    [
        ("request_extra", True),
        ("request_hash", "A" * 64),
        ("request_ref", "C:/tmp/decision.json"),
        ("request_float", 1.5),
        ("event_payload_schema", "forbidden"),
        ("event_secret", "forbidden"),
        ("event_authorized", True),
        ("event_sentinel", "unpublished:p0"),
    ],
)
def test_publication_schemas_reject_forbidden_surfaces(target, value) -> None:
    registry = SchemaRegistry(ROOT / ".research-system" / "schemas")
    if target.startswith("request_"):
        document = publication_request()
        if target == "request_extra":
            document["authorized"] = value
        elif target == "request_hash":
            document["publication_authority_sha256"] = value
        elif target == "request_ref":
            document["evaluation_runs_manifest_ref"] = value
        else:
            document["idempotency_key"] = value
        schema_id = "ars://evals/release-publication-request"
    else:
        document = published_event()
        if target == "event_payload_schema":
            document["payload_schema"] = value
        elif target == "event_secret":
            document["payload"]["secret"] = value
        elif target == "event_authorized":
            document["payload"]["gate5_authorized"] = value
        else:
            document["payload"]["release_decision"]["canonical_event_ref"] = value
        schema_id = "ars://core/event/ReleaseGateDecisionPublished"
    with pytest.raises(SchemaError):
        registry.validate(schema_id, document)


def test_direct_raw_release_event_cannot_bypass_ledger_finalizer(tmp_path) -> None:
    event = published_event()
    raw = {
        key: value
        for key, value in event.items()
        if key
        not in {
            "event_id",
            "project_id",
            "stream_version",
            "global_position",
            "transaction_id",
            "transaction_index",
            "transaction_count",
            "recorded_at",
            "previous_event_hash",
            "event_hash",
        }
    }
    with pytest.raises(ArsError, match="requires a ledger event finalizer"):
        EventLedger(tmp_path / "control", PROJECT_ID).append([raw])


def test_release_draft_cannot_supply_noop_validation_or_append_invalid_payload(
    tmp_path,
) -> None:
    event = published_event()
    envelope = {
        key: value
        for key, value in event.items()
        if key
        not in {
            "event_id",
            "project_id",
            "stream_version",
            "global_position",
            "transaction_id",
            "transaction_index",
            "transaction_count",
            "recorded_at",
            "payload",
            "previous_event_hash",
            "event_hash",
        }
    }
    assert {item.name for item in fields(EventDraft)} == {
        "envelope",
        "finalize_payload",
    }
    ledger = EventLedger(tmp_path / "trusted", PROJECT_ID)

    def invalid_payload(allocated):
        payload = deepcopy(event["payload"])
        payload["release_decision"]["canonical_event_ref"] = allocated.event_id
        payload["caller_extra"] = True
        return payload

    with pytest.raises(ArsError, match="CommandService"):
        invalid = EventDraft(envelope, invalid_payload)
        ledger.append([invalid])
    assert tuple(ledger.iter_events()) == ()


def test_replay_requires_schema_validation_and_rejects_self_reference_tamper(
    tmp_path,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256=harness.authority_hash)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    harness.service.submit(canonical_publication_command(harness))
    events = list(harness.ledger.iter_events())
    event = events[-1]
    with pytest.raises(IntegrityError, match="schema validator unavailable"):
        replay(events)
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    assert replay(events, schema_registry=schemas)["release_decisions"][DECISION_ID]["candidate_status"] == "blocked"
    tampered = deepcopy(event)
    tampered["payload"]["release_decision"]["canonical_event_ref"] = "evt_01978abc-2010-7000-8000-000000002010"
    unsigned = dict(tampered)
    unsigned.pop("event_hash")
    tampered["event_hash"] = sha256_hex(canonical_bytes(unsigned))
    with pytest.raises(IntegrityError, match="identity or disposition"):
        replay([*events[:-1], tampered], schema_registry=schemas)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("source_hash", "source hash mismatch"),
        ("previous_hash", "hash-chain mismatch"),
        ("authority_id", "identity or disposition"),
        ("authority_hash", "identity or disposition"),
    ],
)
def test_replay_rejects_release_source_and_chain_tamper(
    tmp_path,
    tamper,
    message,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256=harness.authority_hash)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    harness.service.submit(canonical_publication_command(harness))
    events = [deepcopy(item) for item in harness.ledger.iter_events()]
    event = events[-1]
    if tamper == "source_hash":
        event["payload"]["source_decision_sha256"] = "0" * 64
    elif tamper == "previous_hash":
        event["previous_event_hash"] = "1" * 64
    elif tamper == "authority_id":
        event["payload"]["publication_authority_grant_id"] = "agr_01978abc-9997-7000-8000-000000009997"
    else:
        event["payload"]["publication_authority_sha256"] = "0" * 64
    unsigned = dict(event)
    unsigned.pop("event_hash")
    event["event_hash"] = sha256_hex(canonical_bytes(unsigned))
    schemas = SchemaRegistry(ROOT / ".research-system" / "schemas")
    with pytest.raises(IntegrityError, match=message):
        replay([*events[:-1], event], schema_registry=schemas)


@pytest.mark.parametrize(
    "tamper",
    [
        "sentinel",
        "unknown_event",
        "foreign_project",
        "projection_source",
        "event_ref",
        "manifest_hash",
        "control_hash",
        "authority_hash",
        "authority_id",
        "authorized",
        "released",
    ],
)
def test_release_resolution_rejects_sentinel_unknown_foreign_and_projection_tamper(
    tamper,
) -> None:
    source = source_decision()
    published = published_decision()
    resolver = evidence_resolver()
    manifest = resolver.resolve_evaluation_runs(MANIFEST_REF)
    control = resolver.resolve_control_binding(CONTROL_REF)
    record = {
        "project_id": PROJECT_ID,
        "release_decision_id": DECISION_ID,
        "release_decision": published_decision(),
        "source_decision_sha256": sha256_hex(canonical_bytes(source)),
        "gate5_authorized": False,
        "candidate_status": "blocked",
        "event_id": EVENT_ID,
        "evaluation_runs_manifest_ref": MANIFEST_REF,
        "evaluation_runs_manifest_sha256": sha256_hex(canonical_bytes(manifest)),
        "control_binding_ref": CONTROL_REF,
        "control_binding_sha256": sha256_hex(canonical_bytes(control)),
        "publication_authority_grant_id": GRANT_ID,
        "publication_authority_sha256": "a" * 64,
    }
    projection = {
        "release_decisions": {DECISION_ID: record},
        "authority_grants": {
            GRANT_ID: {
                "status": "active",
                "authority_grant_sha256": "a" * 64,
            }
        },
    }
    if tamper == "sentinel":
        published["canonical_event_ref"] = "unpublished:p0"
    elif tamper == "unknown_event":
        projection["release_decisions"] = {}
    elif tamper == "foreign_project":
        record["project_id"] = "prj_01978abc-9999-7000-8000-000000009999"
    elif tamper == "projection_source":
        record["source_decision_sha256"] = "0" * 64
    elif tamper == "event_ref":
        published["canonical_event_ref"] = "evt_01978abc-9998-7000-8000-000000009998"
    elif tamper == "manifest_hash":
        record["evaluation_runs_manifest_sha256"] = "0" * 64
    elif tamper == "control_hash":
        record["control_binding_sha256"] = "0" * 64
    elif tamper == "authority_hash":
        record["publication_authority_sha256"] = "0" * 64
    elif tamper == "authority_id":
        record["publication_authority_grant_id"] = "agr_01978abc-9997-7000-8000-000000009997"
    elif tamper == "authorized":
        record["gate5_authorized"] = True
    else:
        record["candidate_status"] = "released"
    with pytest.raises(PublicationEvidenceError):
        verify_replayed_release(
            published,
            source,
            projection,
            PROJECT_ID,
            resolver,
            SchemaRegistry(ROOT / ".research-system" / "schemas"),
        )


@pytest.mark.parametrize(
    "failure",
    [
        "authority actor mismatch",
        "authority command mismatch",
        "authority grant expired",
        "authority grant revoked",
        "authority subject scope mismatch",
    ],
)
def test_authority_failures_return_stable_unauthorized_receipts(
    tmp_path,
    failure,
) -> None:
    harness = control_plane(tmp_path)

    def reject(*_args):
        raise ArsError(failure)

    harness.service.authority_resolver = SimpleNamespace(resolve=reject)
    harness.service.release_publication_evidence = evidence_resolver()
    receipt = harness.service.submit(publication_command())
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_publication_unauthorized"
    assert tuple(harness.ledger.iter_events()) == ()


def test_foreign_project_binding_is_a_stable_rejection(tmp_path) -> None:
    harness = control_plane(tmp_path)
    command = publication_command()
    command["payload"] = {
        **command["payload"],
        "project_id": "prj_01978abc-2011-7000-8000-000000002011",
    }
    receipt = harness.service.submit(command)
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_publication_evidence_mismatch"
    assert tuple(harness.ledger.iter_events()) == ()


def test_stale_expected_version_conflicts_without_append(tmp_path) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256="a" * 64)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    command = publication_command()
    command["expected_stream_version"] = 1
    receipt = harness.service.submit(command)
    assert receipt.status == "conflict"
    assert receipt.reason_code == "stream_version_conflict"
    assert receipt.observed_stream_version == 0
    assert tuple(harness.ledger.iter_events()) == ()


def test_distinct_command_cannot_republish_existing_decision(tmp_path) -> None:
    harness = control_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256="a" * 64)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    harness.service.submit(publication_command())
    second = publication_command("cmd_01978abc-2012-7000-8000-000000002012")
    second["idempotency_key"] = "release-publication:distinct"
    second["payload"] = {
        **second["payload"],
        "idempotency_key": "release-publication:distinct",
    }
    receipt = harness.service.submit(second)
    assert receipt.status == "rejected"
    assert receipt.reason_code == "release_decision_already_published"
    assert len(tuple(harness.ledger.iter_events())) == 1


def test_index_first_receipt_crash_recovers_exactly_one_publication(
    tmp_path,
    monkeypatch,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256=harness.authority_hash)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    original_write = harness.receipts.write
    monkeypatch.setattr(
        harness.receipts,
        "write",
        lambda _receipt: (_ for _ in ()).throw(OSError("receipt crash")),
    )
    with pytest.raises(OSError, match="receipt crash"):
        harness.service.submit(canonical_publication_command(harness))
    assert len(tuple(harness.ledger.iter_events())) == 3
    monkeypatch.setattr(harness.receipts, "write", original_write)
    recovered = harness.service.submit(
        canonical_publication_command(harness, "cmd_01978abc-2013-7000-8000-000000002013")
    )
    assert recovered.status == "accepted"
    assert len(tuple(harness.ledger.iter_events())) == 3


def test_concurrent_exact_publications_serialize_to_one_original_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    harness = canonical_publication_plane(tmp_path)
    harness.service.authority_resolver = SimpleNamespace(
        resolve=lambda *_args: SimpleNamespace(authority_grant_sha256=harness.authority_hash)
    )
    harness.service.release_publication_evidence = evidence_resolver()
    entered = threading.Event()
    release = threading.Event()
    crossed_former_cutoff = threading.Event()
    logical_time = [0.0]

    harness.service._monotonic = lambda: logical_time[0]

    def advance_without_wall_sleep(_interval):
        logical_time[0] += 1.1
        if logical_time[0] > 5.0:
            crossed_former_cutoff.set()
            release.set()
        threading.Event().wait(0.001)

    harness.service._lock_wait = advance_without_wall_sleep

    def pause(_temporary):
        entered.set()
        assert release.wait(2)

    monkeypatch.setattr(harness.ledger, "_after_batch_fsync", pause)
    results = []
    errors = []

    def submit(command):
        try:
            results.append(harness.service.submit(command))
        except Exception as exc:  # pragma: no branch - asserted below
            errors.append(exc)

    first = threading.Thread(target=submit, args=(canonical_publication_command(harness),))
    second = threading.Thread(
        target=submit,
        args=(canonical_publication_command(harness, "cmd_01978abc-2014-7000-8000-000000002014"),),
    )
    first.start()
    assert entered.wait(2)
    second.start()
    first.join(4)
    second.join(4)
    assert crossed_former_cutoff.is_set()
    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert len(results) == 2
    assert results[0] == results[1]
    assert len(tuple(harness.ledger.iter_events())) == 3
