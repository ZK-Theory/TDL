from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from research_system.authority import (
    AuthorityAdministrationContext,
    AuthorityScope,
    ScopedAuthorityGrantResolution,
    authority_bootstrap_sha256,
)
from research_system.canonical import canonical_bytes, sha256_hex
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
from research_system.schema_registry import runtime_schema_registry
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

    def replay(self) -> ControlPlaneState:
        return replay_control_plane(self.ledger.iter_events())


class _SyntheticLifecycleAuthorityResolver:
    """Fixture-only authority consumer for legacy unbound lifecycle tests."""

    def __init__(self) -> None:
        self._last_resolution: ScopedAuthorityGrantResolution | None = None

    def administration_context(self) -> AuthorityAdministrationContext:
        return AuthorityAdministrationContext(
            project_id=PROJECT_ID,
            store_identity="a" * 64,
            bootstrap_manifest_sha256="b" * 64,
            root_grant_id=ROOT_AUTHORITY_GRANT_ID,
            root_grant_sha256="c" * 64,
            owner_actor_id=ACTORS["actor-a"],
        )

    def resolve_command(
        self,
        *,
        grant_id: str,
        actor_id: str,
        actor_class: str,
        command,
        required_risk: str,
        project_id: str,
        subject_kind: str,
        subject_id: str,
        now: datetime,
    ) -> ScopedAuthorityGrantResolution:
        if actor_class != "human":
            raise ArsError("synthetic fixture actor class mismatch")
        resolution = ScopedAuthorityGrantResolution(
            authority_grant_id=grant_id,
            authority_grant_sha256="d" * 64,
            schema_id="ars://core/scoped-authority-grant",
            schema_version="2.0.0",
            schema_sha256="e" * 64,
            actor_id=actor_id,
            subject_scope=AuthorityScope(project_id, subject_kind, subject_id),
            effective_at=datetime(2026, 1, 1, tzinfo=UTC),
            expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            activation_event_id="evt_01978abc-1005-7000-8000-000000001005",
            activation_position=1,
            administration_decision_id="arec_01978abc-1006-7000-8000-000000001006",
            administration_decision_sha256="f" * 64,
            status="active",
            revocation_event_id=None,
        )
        self._last_resolution = resolution
        return resolution

    def scoped_grant_identity(self, _grant_id: str) -> ScopedAuthorityGrantResolution | None:
        return self._last_resolution


def control_plane(tmp_path: Path) -> ControlPlaneHarness:
    root = tmp_path / "control"
    root.mkdir()
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system" / "schemas")
    ledger = EventLedger(root, project_id=PROJECT_ID, schemas=schemas)
    objects = ObjectStore(root)
    receipts = ReceiptStore(root)
    service = CommandService(
        root,
        ledger,
        objects,
        receipts,
        schemas,
        authority_resolver=_SyntheticLifecycleAuthorityResolver(),
    )
    return ControlPlaneHarness(service, ledger, objects, receipts)


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
