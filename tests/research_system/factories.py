from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
import uuid
from typing import Any, Callable

from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.command.reducers import ControlPlaneState, replay_control_plane
from research_system.command.service import CommandService
from research_system.evals.release_publication import BoundReleasePublicationEvidence
from research_system.evals.harness import (
    build_release_decision,
    decision_document,
    run_all_scenarios,
    run_p0_coverage,
)
from research_system.evals.release_snapshot import (
    build_release_snapshot_documents,
    rederive_release_from_snapshot,
)
from research_system.errors import ArsError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore

PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
AUTHORITY_GRANT_ID = "agr_01978abc-1001-7000-8000-000000001001"
REPO_ROOT = Path(__file__).resolve().parents[2]
ACTORS = {
    "actor-a": "act_01978abc-1002-7000-8000-000000001002",
    "actor-b": "act_01978abc-1003-7000-8000-000000001003",
}
ROOT_AUTHORITY_GRANT_ID = "agr_01978abc-1004-7000-8000-000000001004"
RELEASE_DECISION_ID = "rgd_01978abc-1003-7000-8000-000000001003"


def authority_bootstrap(
    publication_target_id: str = RELEASE_DECISION_ID,
    publication_expires_at: str | None = "2026-07-13T00:00:00Z",
) -> dict[str, Any]:
    """Return the canonical synthetic two-grant authority bootstrap fixture.

    Args:
        publication_target_id: Exact governed release-decision identity.
        publication_expires_at: Optional UTC expiry for the publication grant.

    Returns:
        A non-secret bootstrap manifest with root and publication grants.
    """

    def grant(
        grant_id: str,
        command: str,
        kind: str,
        subject_id: str,
        expires_at: str | None,
    ) -> dict[str, Any]:
        return {
            "schema_id": "ars://core/authority-grant",
            "schema_version": "1.1.0",
            "authority_grant_id": grant_id,
            "actor_id": ACTORS["actor-a"],
            "allowed_command_types": [command],
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": kind, "id": subject_id},
            },
            "risk_ceiling": "R2",
            "effective_at": "2026-07-12T00:00:00Z",
            "expires_at": expires_at,
            "delegable": False,
            "revoked": False,
        }

    root = grant(
        ROOT_AUTHORITY_GRANT_ID,
        "RevokeAuthorityGrant",
        "authority_grant",
        AUTHORITY_GRANT_ID,
        None,
    )
    publication = grant(
        AUTHORITY_GRANT_ID,
        "PublishReleaseGateDecision",
        "release_gate_decision",
        publication_target_id,
        publication_expires_at,
    )
    return {
        "schema_id": "ars://core/authority-bootstrap-manifest",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "owner_actor_id": ACTORS["actor-a"],
        "root_grant": root,
        "root_grant_sha256": sha256_hex(canonical_bytes(root)),
        "publication_grant": publication,
        "publication_grant_sha256": sha256_hex(canonical_bytes(publication)),
        "publication_target_id": publication_target_id,
    }


def write_authority_bootstrap_input(path: Path) -> Path:
    """Write the approved synthetic authority bootstrap input fixture.

    Args:
        path: Destination JSON path.

    Returns:
        The destination path.
    """
    manifest = authority_bootstrap()
    path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-input",
                "schema_version": "1.0.0",
                "approved_bootstrap_sha256": authority_bootstrap_sha256(manifest),
                "manifest": manifest,
            }
        )
    )
    return path


@dataclass(frozen=True)
class ControlPlaneHarness:
    service: CommandService
    ledger: EventLedger
    objects: ObjectStore
    receipts: ReceiptStore
    schemas: SchemaRegistry
    authority_root: Path
    authority_ledger: EventLedger
    authority_objects: ObjectStore
    authority_receipts: ReceiptStore
    authority_resolver: LedgerAuthorityGrantResolver
    authority_service: CommandService

    def replay(self) -> ControlPlaneState:
        return replay_control_plane(self.ledger.iter_events())


def scoped_lifecycle_grant_id(subject_id: str) -> str:
    """Derive one deterministic valid authority-grant identity for a subject.

    Args:
        subject_id: UUID-like subject identity whose suffix is reused.

    Returns:
        The deterministic scoped authority-grant identity for ``subject_id``.
    """
    return f"agr_{subject_id.split('_', 1)[1]}"


def _prefixed_identity(prefix: str, source_id: str) -> str:
    return f"{prefix}_{source_id.split('_', 1)[1]}"


def _revocation_decision_id(grant_id: str) -> str:
    """Derive a deterministic, registered assurance-record ID for revocation."""
    raw = bytearray.fromhex(sha256_hex(f"revoke:{grant_id}".encode("utf-8"))[:32])
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    return f"arec_{uuid.UUID(bytes=bytes(raw))}"


def activate_lifecycle_grant(
    harness: ControlPlaneHarness,
    *,
    subject_kind: str,
    subject_id: str,
    actor_id: str = ACTORS["actor-a"],
) -> str:
    """Activate a real scoped command grant through the authority ledger.

    Args:
        harness: Test control-plane and sibling authority stores.
        subject_kind: Governed subject kind for the grant scope.
        subject_id: Governed subject identity for the grant scope.
        actor_id: Actor recorded on the issued grant.

    Returns:
        The deterministic authority-grant identity.

    Raises:
        AssertionError: If an expected active command binding is missing or
            the authority service rejects activation.
    """
    grant_id = scoped_lifecycle_grant_id(subject_id)
    try:
        existing = harness.authority_resolver.scoped_grant_identity(grant_id)
    except ArsError:
        existing = None
    if existing is not None:
        return grant_id
    command_types = (
        ("CreateScopeDefinition", "AmendScopeDefinition", "SupersedeScopeDefinition")
        if subject_kind == "scope_definition"
        else ("CreateTask", "AmendTask", "SupersedeTask")
    )
    command_identities = []
    for command_type in command_types:
        binding = harness.schemas.command_binding(command_type)
        if binding is None:
            raise AssertionError(f"missing active binding for {command_type}")
        identity = harness.schemas.resolve_identity(binding.schema_id, binding.schema_version)
        command_identities.append(
            {
                "command_type": command_type,
                "schema_id": identity.schema_id,
                "schema_version": identity.schema_version,
                "schema_sha256": identity.sha256,
            }
        )
    context = harness.authority_resolver.administration_context()
    grant_schema = harness.schemas.resolve_identity(
        "ars://core/scoped-authority-grant",
        "2.0.0",
    )
    subject_scope = {
        "project_id": PROJECT_ID,
        "subject": {"kind": subject_kind, "id": subject_id},
    }
    grant = {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.0.0",
        "authority_grant_id": grant_id,
        "actor_id": actor_id,
        "allowed_actor_classes": ["human"],
        "allowed_commands": command_identities,
        "allowed_policy_actions": [],
        "subject_scope": subject_scope,
        "risk_ceiling": "R3",
        "effective_at": "2026-01-01T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    decision_id = _prefixed_identity("arec", grant_id)
    decision = {
        "schema_id": "ars://core/owner-authority-administration-decision",
        "schema_version": "1.0.0",
        "record_id": decision_id,
        "revision": 1,
        "project_id": context.project_id,
        "store_identity": context.store_identity,
        "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
        "root_grant_id": context.root_grant_id,
        "root_grant_sha256": context.root_grant_sha256,
        "owner_actor_id": context.owner_actor_id,
        "action": "activate_authority_grant",
        "target_grant_id": grant_id,
        "target_grant_sha256": sha256_hex(canonical_bytes(grant)),
        "target_grant_schema_id": grant_schema.schema_id,
        "target_grant_schema_version": grant_schema.schema_version,
        "target_grant_schema_sha256": grant_schema.sha256,
        "subject_scope": subject_scope,
        "effective_at": grant["effective_at"],
        "expires_at": grant["expires_at"],
        "one_time_use": True,
        "state": "active",
        "decided_at": "2026-01-01T00:00:00Z",
    }
    harness.authority_objects.write("assurance_record", decision_id, 1, decision)
    activation = {
        "command_id": _prefixed_identity("cmd", grant_id),
        "command_type": "ActivateAuthorityGrant",
        "schema_id": "ars://core/command/ActivateAuthorityGrant",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-01T00:00:00Z",
        "actor_id": context.owner_actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": context.root_grant_id,
        "target_stream_id": grant_id,
        "expected_stream_version": 0,
        "idempotency_key": f"activate-lifecycle-grant:{grant_id}",
        "correlation_id": f"activate-lifecycle-grant:{grant_id}",
        "causation_id": None,
        "reason": "activate a governed lifecycle command grant for a test subject",
        "evidence_refs": [decision_id],
        "project_id": context.project_id,
        "payload": {
            "project_id": context.project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "administration_decision_id": decision_id,
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "new_grant": grant,
            "new_grant_sha256": sha256_hex(canonical_bytes(grant)),
            "new_grant_schema_sha256": grant_schema.sha256,
        },
    }
    receipt = harness.authority_service.submit(activation)
    if receipt.status != "accepted":
        raise AssertionError(f"real lifecycle grant activation failed: {receipt}")
    return grant_id


def revoke_lifecycle_grant(
    harness: ControlPlaneHarness,
    *,
    subject_id: str,
    decision_id: str | None = None,
) -> str:
    """Revoke one issued lifecycle grant through the governed authority ledger.

    Args:
        harness: Test control-plane and sibling authority stores.
        subject_id: Subject whose deterministic lifecycle grant is revoked.
        decision_id: Optional assurance-record identity for the revocation.

    Returns:
        The deterministic authority-grant identity that was revoked.

    Raises:
        ArsError: If the subject grant cannot be resolved from authority
            history.
        AssertionError: If the authority service rejects revocation.
    """
    grant_id = scoped_lifecycle_grant_id(subject_id)
    if decision_id is None:
        decision_id = _revocation_decision_id(grant_id)
    resolution = harness.authority_resolver.scoped_grant_identity(grant_id)
    context = harness.authority_resolver.administration_context()
    decision = {
        "schema_id": "ars://core/owner-authority-administration-decision",
        "schema_version": "1.0.0",
        "record_id": decision_id,
        "revision": 1,
        "project_id": context.project_id,
        "store_identity": context.store_identity,
        "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
        "root_grant_id": context.root_grant_id,
        "root_grant_sha256": context.root_grant_sha256,
        "owner_actor_id": context.owner_actor_id,
        "action": "revoke_issued_authority_grant",
        "target_grant_id": resolution.authority_grant_id,
        "target_grant_sha256": resolution.authority_grant_sha256,
        "target_grant_schema_id": resolution.schema_id,
        "target_grant_schema_version": resolution.schema_version,
        "target_grant_schema_sha256": resolution.schema_sha256,
        "subject_scope": resolution.subject_scope.to_dict(),
        "effective_at": resolution.effective_at.isoformat().replace("+00:00", "Z"),
        "expires_at": resolution.expires_at.isoformat().replace("+00:00", "Z"),
        "one_time_use": True,
        "state": "active",
        "decided_at": "2026-08-01T00:00:00Z",
    }
    harness.authority_objects.write("assurance_record", decision_id, 1, decision)
    command = {
        "command_id": _prefixed_identity("cmd", decision_id),
        "command_type": "RevokeIssuedAuthorityGrant",
        "schema_id": "ars://core/command/RevokeIssuedAuthorityGrant",
        "schema_version": "1.0.0",
        "submitted_at": "2026-08-01T00:00:00Z",
        "actor_id": context.owner_actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": context.root_grant_id,
        "target_stream_id": grant_id,
        "expected_stream_version": 1,
        "idempotency_key": f"revoke-lifecycle-grant:{grant_id}",
        "correlation_id": f"revoke-lifecycle-grant:{grant_id}",
        "causation_id": None,
        "reason": "revoke a governed lifecycle command grant for a retry test",
        "evidence_refs": [decision_id],
        "project_id": context.project_id,
        "payload": {
            "project_id": context.project_id,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "target_grant_id": resolution.authority_grant_id,
            "target_grant_sha256": resolution.authority_grant_sha256,
            "target_grant_schema_sha256": resolution.schema_sha256,
            "administration_decision_id": decision_id,
            "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
            "reason": "revoke a governed lifecycle command grant for a retry test",
        },
    }
    receipt = harness.authority_service.submit(command)
    if receipt.status != "accepted":
        raise AssertionError(f"real lifecycle grant revocation failed: {receipt}")
    return grant_id


class GovernedTestCommandService(CommandService):
    """Test adapter that provisions real grants in a sibling authority ledger.

    Actor-a lifecycle submissions have their authority-grant field overwritten
    with a real grant activated in the sibling authority store.  With
    ``control_plane(auto_authority=False)``, the plain ``CommandService`` is
    returned instead, so actor-a submissions are not rewritten and must supply
    an independently activated grant when a positive case is intended.
    """

    def __init__(self, *args: Any, authority_harness: ControlPlaneHarness, **kwargs: Any) -> None:
        self._authority_harness = authority_harness
        self._prepared_authority_grants: dict[str, str] = {}
        super().__init__(*args, **kwargs)

    def _before_submission_lock(self, command: Command) -> None:
        if (
            command.envelope.get("command_type")
            in {
                "CreateScopeDefinition",
                "AmendScopeDefinition",
                "SupersedeScopeDefinition",
                "CreateTask",
                "AmendTask",
                "SupersedeTask",
            }
            and command.actor_id == ACTORS["actor-a"]
        ):
            _, subject_kind, subject_id, _ = self._lifecycle_authority_inputs(
                command,
                self.ledger.snapshot(),
            )
            grant_id = scoped_lifecycle_grant_id(subject_id)
            if getattr(self, "_restore_preflight_result", None) is None:
                # Restore reuses the deterministic scoped grant already activated
                # in the sibling authority store; it must not be activated again.
                grant_id = activate_lifecycle_grant(
                    self._authority_harness,
                    subject_kind=subject_kind,
                    subject_id=subject_id,
                )
            self._prepared_authority_grants[command.command_id] = grant_id

    def _before_authority_resolution(self, command: Command) -> None:
        grant_id = self._prepared_authority_grants.pop(command.command_id, None)
        if grant_id is not None:
            command.envelope["authority_grant_id"] = grant_id


def control_plane(
    tmp_path: Path,
    *,
    auto_authority: bool = True,
    clock: Callable[[], datetime] | None = None,
) -> ControlPlaneHarness:
    root = tmp_path / "control"
    root.mkdir()
    clock = clock or (lambda: datetime(2026, 8, 1, tzinfo=UTC))
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    authority_root = root.parent / f".{root.name}.authority"
    origin_authority_root = root.parent / f".{root.name}.origin-authority"
    origin_authority_root.mkdir()
    bootstrap = authority_bootstrap()
    authority_identity = initialize_authority_control_store(
        [REPO_ROOT],
        authority_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        origin_authority_root=origin_authority_root,
    )
    authority_ledger = EventLedger(authority_root, PROJECT_ID, schemas)
    authority_objects = ObjectStore(authority_root)
    authority_receipts = ReceiptStore(authority_root)
    authority_resolver = LedgerAuthorityGrantResolver(
        authority_root,
        PROJECT_ID,
        authority_identity,
        schemas,
        approved_witness=authority_identity.witness,
    )
    authority_service = CommandService(
        authority_root,
        authority_ledger,
        authority_objects,
        authority_receipts,
        schemas,
        authority_resolver=authority_resolver,
        clock=clock,
    )
    ledger = EventLedger(root, project_id=PROJECT_ID, schemas=schemas)
    objects = ObjectStore(root)
    receipts = ReceiptStore(root)
    service = CommandService(
        root,
        ledger,
        objects,
        receipts,
        schemas,
        authority_resolver=authority_resolver,
        clock=clock,
    )
    harness = ControlPlaneHarness(
        service=service,
        ledger=ledger,
        objects=objects,
        receipts=receipts,
        schemas=schemas,
        authority_root=authority_root,
        authority_ledger=authority_ledger,
        authority_objects=authority_objects,
        authority_receipts=authority_receipts,
        authority_resolver=authority_resolver,
        authority_service=authority_service,
    )
    if auto_authority:
        harness = replace(
            harness,
            service=GovernedTestCommandService(
                root,
                ledger,
                objects,
                receipts,
                schemas,
                authority_resolver=authority_resolver,
                clock=clock,
                authority_harness=harness,
            ),
        )
    return harness


def _command(
    command_id: str,
    idempotency_key: str,
    target_stream_id: str,
    payload: dict[str, Any],
    *,
    command_type: str,
    actor_id: str,
    expected_version: int,
) -> dict[str, Any]:
    return {
        "command_id": command_id,
        "command_type": command_type,
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-01T12:00:00Z",
        "actor_id": actor_id,
        "on_behalf_of_actor_id": None,
        "authority_grant_id": AUTHORITY_GRANT_ID,
        "target_stream_id": target_stream_id,
        "expected_stream_version": expected_version,
        "idempotency_key": idempotency_key,
        "correlation_id": "synthetic-control-plane",
        "causation_id": None,
        "reason": "synthetic P0 command test",
        "evidence_refs": [],
        "payload": payload,
    }


def create_task_command(
    command_id: str,
    idempotency_key: str,
    task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    title = str(payload.get("title", "Synthetic task"))
    definition = {
        "task_id": task_id,
        "revision": 1,
        "aliases": [],
        "project_id": PROJECT_ID,
        "portfolio_refs": [],
        "scope_refs": [],
        "title": title,
        "objective": f"Complete {title}",
        "bounded_scope": "Synthetic command-service test scope",
        "non_goals": [],
        "dependencies": [],
        "governing_design_refs": ["ars://design/synthetic"],
        "risk_tier_request": "R1",
        "assurance_lanes": ["output-provenance"],
        "machine_checks": ["frozen-schema-validation"],
        "human_questions": ["Is the bounded task definition suitable?"],
        "independent_review_requirements": ["review exact candidate"],
        "expected_artefact_types": ["test-result"],
        "acceptance_criteria": ["command and event schemas validate"],
        "partial_criteria": ["report any schema mismatch"],
        "prohibited_shortcuts": ["do not relax frozen schemas"],
        "root_binding_requirements": [],
        "concurrency_mode": "exclusive",
        "resource_policy_ref": "ars://resource-policy/synthetic",
        "checkpoint_expectation": "No checkpoint required",
        "dispatch_authority": "synthetic-owner",
        "amend_authority": "synthetic-owner",
        "cancel_authority": "synthetic-owner",
        "review_authority": "synthetic-reviewer",
        "accept_authority": "synthetic-owner",
        "reopen_authority": "synthetic-owner",
        "supersede_authority": "synthetic-owner",
        "creator_actor_id": ACTORS["actor-a"],
        "created_at": "2026-07-01T12:00:00Z",
        "source_import_refs": [],
    }
    definition["content_sha256"] = sha256_hex(canonical_bytes(definition))
    command = _command(
        command_id,
        idempotency_key,
        task_id,
        {"new_task_id": task_id, "definition": definition},
        command_type="CreateTask",
        actor_id=ACTORS["actor-a"],
        expected_version=0,
    )
    command["schema_id"] = "ars://core/command/CreateTask"
    command["project_id"] = PROJECT_ID
    return command


def claim_dispatch_command(
    command_id: str,
    actor: str,
    dispatch_id: str,
    *,
    expected_version: int,
) -> dict[str, Any]:
    return _command(
        command_id,
        f"claim-{actor}",
        dispatch_id,
        {},
        command_type="ClaimDispatch",
        actor_id=ACTORS[actor],
        expected_version=expected_version,
    )


@lru_cache(maxsize=1)
def _release_producer():
    coverage_path = REPO_ROOT / ".research-system" / "evals" / "p0-coverage.yaml"
    evidence = run_p0_coverage(
        coverage_path,
        fixture_root=coverage_path.parent / "fixtures",
        schema_root=REPO_ROOT / ".research-system" / "schemas",
    )
    scenarios = run_all_scenarios()
    record, _ = build_release_decision(
        evidence,
        scenarios,
        decided_at="2026-07-12T12:00:00Z",
        release_gate_decision_id=RELEASE_DECISION_ID,
    )
    return evidence, scenarios, decision_document(record)


def synthetic_release_decision(
    canonical_event_ref: str = "unpublished:p0",
) -> dict[str, Any]:
    """Return one complete blocked typed decision for publication tests.

    Args:
        canonical_event_ref: The canonical event reference inserted into the
            synthetic decision.

    Returns:
        The complete blocked typed decision fixture.
    """
    source = deepcopy(_release_producer()[2])
    source["canonical_event_ref"] = canonical_event_ref
    return source


def synthetic_publication_evidence(
    store_identity: str,
) -> BoundReleasePublicationEvidence:
    """Return narrow stored-reference evidence with independent re-derivation.

    Args:
        store_identity: Exact canonical control-store identity.

    Returns:
        Immutable synthetic evidence resolver bound to the supplied store.
    """
    evidence, scenarios, stored_source = _release_producer()
    source = deepcopy(stored_source)
    manifest_ref = "art_01978abc-2001-7000-8000-000000002001"
    control_ref = "art_01978abc-2002-7000-8000-000000002002"
    manifest, control = build_release_snapshot_documents(
        evidence,
        scenarios,
        source,
        project_id=PROJECT_ID,
        store_identity=store_identity,
    )

    def rederive(
        resolved_manifest: dict[str, Any],
        resolved_control: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        return rederive_release_from_snapshot(
            resolved_manifest,
            resolved_control,
        )

    return BoundReleasePublicationEvidence(
        manifest_ref,
        manifest,
        control_ref,
        control,
        store_identity,
        rederive,
    )


def publish_release_command(
    command_id: str,
    authority_grant_sha256: str,
) -> dict[str, Any]:
    """Return the exact W2 publication command for the synthetic decision.

    Args:
        command_id: Fresh command identity for this submission attempt.
        authority_grant_sha256: Canonical hash of the publication grant.

    Returns:
        Exact synthetic ``PublishReleaseGateDecision`` command envelope.
    """
    manifest_ref = "art_01978abc-2001-7000-8000-000000002001"
    control_ref = "art_01978abc-2002-7000-8000-000000002002"
    idempotency_key = "release-publication:synthetic-p0"
    request = {
        "schema": "ars://evals/release-publication-request",
        "project_id": PROJECT_ID,
        "release_decision_id": RELEASE_DECISION_ID,
        "evaluation_runs_manifest_ref": manifest_ref,
        "control_binding_ref": control_ref,
        "publication_authority_grant_id": AUTHORITY_GRANT_ID,
        "publication_authority_sha256": authority_grant_sha256,
        "idempotency_key": idempotency_key,
    }
    return {
        "command_id": command_id,
        "command_type": "PublishReleaseGateDecision",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-12T12:00:00Z",
        "actor_id": ACTORS["actor-a"],
        "on_behalf_of_actor_id": None,
        "authority_grant_id": AUTHORITY_GRANT_ID,
        "target_stream_id": RELEASE_DECISION_ID,
        "expected_stream_version": 0,
        "idempotency_key": idempotency_key,
        "correlation_id": "synthetic-publication",
        "causation_id": None,
        "reason": "record the blocked synthetic P0 decision",
        "evidence_refs": [manifest_ref, control_ref],
        "payload": request,
    }
