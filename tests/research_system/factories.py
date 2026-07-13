from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research_system.authority import authority_bootstrap_sha256
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import ControlPlaneState, replay_control_plane
from research_system.command.service import CommandService
from research_system.evals.release_publication import BoundReleasePublicationEvidence
from research_system.schema_registry import SchemaRegistry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore

PROJECT_ID = 'prj_01978abc-1000-7000-8000-000000001000'
AUTHORITY_GRANT_ID = 'agr_01978abc-1001-7000-8000-000000001001'
REPO_ROOT = Path(__file__).resolve().parents[2]
ACTORS = {
    'actor-a': 'act_01978abc-1002-7000-8000-000000001002',
    'actor-b': 'act_01978abc-1003-7000-8000-000000001003',
}
ROOT_AUTHORITY_GRANT_ID = 'agr_01978abc-1004-7000-8000-000000001004'
RELEASE_DECISION_ID = 'rgd_01978abc-1003-7000-8000-000000001003'


def authority_bootstrap(
    publication_target_id: str = RELEASE_DECISION_ID,
    publication_expires_at: str | None = '2026-07-13T00:00:00Z',
) -> dict[str, Any]:
    """Return the canonical synthetic two-grant authority bootstrap fixture.

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
            'schema_id': 'ars://core/authority-grant',
            'schema_version': '1.1.0',
            'authority_grant_id': grant_id,
            'actor_id': ACTORS['actor-a'],
            'allowed_command_types': [command],
            'subject_scope': {
                'project_id': PROJECT_ID,
                'subject': {'kind': kind, 'id': subject_id},
            },
            'risk_ceiling': 'R2',
            'effective_at': '2026-07-12T00:00:00Z',
            'expires_at': expires_at,
            'delegable': False,
            'revoked': False,
        }

    root = grant(
        ROOT_AUTHORITY_GRANT_ID,
        'RevokeAuthorityGrant',
        'authority_grant',
        AUTHORITY_GRANT_ID,
        None,
    )
    publication = grant(
        AUTHORITY_GRANT_ID,
        'PublishReleaseGateDecision',
        'release_gate_decision',
        publication_target_id,
        publication_expires_at,
    )
    return {
        'schema_id': 'ars://core/authority-bootstrap-manifest',
        'schema_version': '1.0.0',
        'project_id': PROJECT_ID,
        'owner_actor_id': ACTORS['actor-a'],
        'root_grant': root,
        'root_grant_sha256': sha256_hex(canonical_bytes(root)),
        'publication_grant': publication,
        'publication_grant_sha256': sha256_hex(canonical_bytes(publication)),
        'publication_target_id': publication_target_id,
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
                'schema_id': 'ars://core/authority-bootstrap-input',
                'schema_version': '1.0.0',
                'approved_bootstrap_sha256': authority_bootstrap_sha256(manifest),
                'manifest': manifest,
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


def control_plane(tmp_path: Path) -> ControlPlaneHarness:
    root = tmp_path / 'control'
    root.mkdir()
    ledger = EventLedger(root, project_id=PROJECT_ID)
    objects = ObjectStore(root)
    receipts = ReceiptStore(root)
    schemas = SchemaRegistry(REPO_ROOT / '.research-system' / 'schemas')
    service = CommandService(root, ledger, objects, receipts, schemas)
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
        'command_id': command_id,
        'command_type': command_type,
        'schema_id': 'ars://core/command',
        'schema_version': '1.0.0',
        'submitted_at': '2026-07-01T12:00:00Z',
        'actor_id': actor_id,
        'on_behalf_of_actor_id': None,
        'authority_grant_id': AUTHORITY_GRANT_ID,
        'target_stream_id': target_stream_id,
        'expected_stream_version': expected_version,
        'idempotency_key': idempotency_key,
        'correlation_id': 'synthetic-control-plane',
        'causation_id': None,
        'reason': 'synthetic P0 command test',
        'evidence_refs': [],
        'payload': payload,
    }


def create_task_command(
    command_id: str,
    idempotency_key: str,
    task_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return _command(
        command_id,
        idempotency_key,
        task_id,
        payload,
        command_type='CreateTask',
        actor_id=ACTORS['actor-a'],
        expected_version=0,
    )


def claim_dispatch_command(
    command_id: str,
    actor: str,
    dispatch_id: str,
    *,
    expected_version: int,
) -> dict[str, Any]:
    return _command(
        command_id,
        f'claim-{actor}',
        dispatch_id,
        {},
        command_type='ClaimDispatch',
        actor_id=ACTORS[actor],
        expected_version=expected_version,
    )


def synthetic_release_decision(
    canonical_event_ref: str = 'unpublished:p0',
) -> dict[str, Any]:
    """Return one complete blocked typed decision for publication tests."""
    return {
        'schema_id': 'ars://evals/release-gate-decision',
        'schema_version': '1.0.0',
        'release_gate_decision_id': RELEASE_DECISION_ID,
        'coverage_manifest_id': 'foundation-coverage-v2',
        'baseline_identity': 'reference-pair-p0',
        'candidate_identity': 'foundation-p0',
        'evidence_snapshot_hash': 'b' * 64,
        'required_verdicts': [],
        'critical_failures': [],
        'parity_status': 'pass',
        'operations_status': 'pass',
        'decision': 'blocked',
        'decided_at': '2026-07-12T12:00:00Z',
        'canonical_event_ref': canonical_event_ref,
        'policy_parity_report_id': 'ppr_' + 'c' * 64,
        'policy_parity_report_hash': 'c' * 64,
        'policy_control_applicability_id': 'pca_' + 'd' * 64,
        'policy_control_applicability_hash': 'd' * 64,
        'exception_policy_id': None,
        'exception_policy_hash': None,
        'exception_scope': None,
        'exception_expiry': None,
        'disabled_or_constrained_capability': None,
        'rationale': None,
        'human_authority_id': None,
        'supersedes': None,
    }


def synthetic_publication_evidence(
    store_identity: str,
) -> BoundReleasePublicationEvidence:
    """Return narrow stored-reference evidence with independent re-derivation."""
    source = synthetic_release_decision()
    manifest_ref = 'art_01978abc-2001-7000-8000-000000002001'
    control_ref = 'art_01978abc-2002-7000-8000-000000002002'
    manifest = {
        'schema_id': 'ars://evals/release-publication-evidence',
        'schema_version': '1.0.0',
        'project_id': PROJECT_ID,
        'release_decision': source,
    }
    control = {
        'schema_id': 'ars://evals/release-control-binding',
        'schema_version': '1.0.0',
        'project_id': PROJECT_ID,
        'store_identity': store_identity,
        'coverage_manifest_id': source['coverage_manifest_id'],
    }
    return BoundReleasePublicationEvidence(
        manifest_ref,
        manifest,
        control_ref,
        control,
        lambda _manifest, _control: (source, False),
    )


def publish_release_command(
    command_id: str,
    authority_grant_sha256: str,
) -> dict[str, Any]:
    """Return the exact W2 publication command for the synthetic decision."""
    manifest_ref = 'art_01978abc-2001-7000-8000-000000002001'
    control_ref = 'art_01978abc-2002-7000-8000-000000002002'
    idempotency_key = 'release-publication:synthetic-p0'
    request = {
        'schema': 'ars://evals/release-publication-request',
        'project_id': PROJECT_ID,
        'release_decision_id': RELEASE_DECISION_ID,
        'evaluation_runs_manifest_ref': manifest_ref,
        'control_binding_ref': control_ref,
        'publication_authority_grant_id': AUTHORITY_GRANT_ID,
        'publication_authority_sha256': authority_grant_sha256,
        'idempotency_key': idempotency_key,
    }
    return {
        'command_id': command_id,
        'command_type': 'PublishReleaseGateDecision',
        'schema_id': 'ars://core/command',
        'schema_version': '1.0.0',
        'submitted_at': '2026-07-12T12:00:00Z',
        'actor_id': ACTORS['actor-a'],
        'on_behalf_of_actor_id': None,
        'authority_grant_id': AUTHORITY_GRANT_ID,
        'target_stream_id': RELEASE_DECISION_ID,
        'expected_stream_version': 0,
        'idempotency_key': idempotency_key,
        'correlation_id': 'synthetic-publication',
        'causation_id': None,
        'reason': 'record the blocked synthetic P0 decision',
        'evidence_refs': [manifest_ref, control_ref],
        'payload': request,
    }
