from __future__ import annotations

import os
from collections.abc import Iterable
from copy import deepcopy
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.reducers import reduce_task
from research_system.errors import IntegrityError, SchemaError
from research_system.schema_registry import SchemaRegistry

_ALLOWED_DISPOSITIONS = frozenset(
    {
        'accepted',
        'partial_accepted',
        'deferred',
        'superseded',
        'removed_by_amendment',
        'cancelled',
        'rejected',
    }
)


def _validate_scope_completion(payload: dict[str, Any]) -> None:
    reference = payload.get('scope_definition_ref')
    if (
        not isinstance(reference, dict)
        or not reference.get('object_id')
        or not isinstance(reference.get('revision'), int)
        or reference['revision'] < 1
    ):
        raise IntegrityError('scope completion requires an exact definition revision')
    required = payload.get('required_member_ids')
    dispositions = payload.get('member_dispositions')
    if not isinstance(required, list) or len(required) != len(set(required)):
        raise IntegrityError('scope completion has invalid required members')
    if not isinstance(dispositions, dict):
        raise IntegrityError('scope completion requires member dispositions')
    missing = sorted(set(required).difference(dispositions))
    if missing:
        raise IntegrityError(f'missing dispositions: {", ".join(missing)}')
    extra = sorted(set(dispositions).difference(required))
    if extra:
        raise IntegrityError(f'unexpected dispositions: {", ".join(extra)}')
    invalid = sorted(
        member
        for member, disposition in dispositions.items()
        if disposition not in _ALLOWED_DISPOSITIONS
    )
    if invalid:
        raise IntegrityError(f'invalid dispositions: {", ".join(invalid)}')


def apply_event(state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(state)
    streams = updated.setdefault('streams', {})
    stream_id = event['stream_id']
    event_type = event['event_type']
    if event_type == 'AuthorityRootInitialized':
        payload = event['payload']
        if set(payload) != {
            'bootstrap_manifest_sha256', 'authorizing_grant_id',
            'authorizing_grant_sha256', 'activated_grant_id',
            'activated_grant_sha256',
        }:
            raise IntegrityError('authority root payload fields must be exact')
        if event.get('global_position') != 1 or event.get('transaction_index') != 1 or event.get('transaction_count') != 2:
            raise IntegrityError('authority root must be genesis index 1/2')
        bootstrap_hash = payload.get('bootstrap_manifest_sha256')
        bootstrap_key = f'authority-bootstrap:{bootstrap_hash}'
        if (
            event.get('schema_id')
            != 'ars://core/event/AuthorityRootInitialized'
            or event.get('command_type') != 'InitializeAuthorityRoot'
            or event.get('authority_grant_id') != stream_id
            or not isinstance(event.get('command_id'), str)
            or not isinstance(event.get('actor_id'), str)
            or event.get('command_payload_hash') != bootstrap_hash
            or event.get('idempotency_key') != bootstrap_key
            or event.get('correlation_id') != bootstrap_key
            or event.get('causation_id') is not None
        ):
            raise IntegrityError('authority genesis envelope binding mismatch')
        if payload.get('activated_grant_id') != stream_id or payload.get('authorizing_grant_id') != stream_id:
            raise IntegrityError('authority root stream binding mismatch')
        if payload.get('activated_grant_sha256') != payload.get('authorizing_grant_sha256'):
            raise IntegrityError('authority root hash binding mismatch')
        grants = updated.setdefault('authority_grants', {})
        if grants:
            raise IntegrityError('authority root already initialized')
        grants[stream_id] = {
            'authority_grant_id': stream_id,
            'authority_grant_sha256': payload['activated_grant_sha256'],
            'status': 'active',
            'activation_event_id': event['event_id'],
            'activation_position': event['global_position'],
            'revocation_event_id': None,
            'revocation_position': None,
        }
        updated['authority_root_id'] = stream_id
        updated['bootstrap_manifest_sha256'] = payload['bootstrap_manifest_sha256']
        updated['_authority_genesis_envelope'] = {
            field: event.get(field)
            for field in (
                'command_id',
                'command_type',
                'actor_id',
                'authority_grant_id',
                'idempotency_key',
                'command_payload_hash',
                'correlation_id',
                'causation_id',
            )
        }
    elif event_type == 'AuthorityGrantActivated':
        payload = event['payload']
        if set(payload) != {
            'authorizing_grant_id', 'authorizing_grant_sha256',
            'activated_grant_id', 'activated_grant_sha256',
        }:
            raise IntegrityError('authority activation payload fields must be exact')
        grants = updated.setdefault('authority_grants', {})
        root_id = updated.get('authority_root_id')
        if event.get('global_position') != 2 or event.get('transaction_index') != 2 or event.get('transaction_count') != 2:
            raise IntegrityError('publication grant must be genesis index 2/2')
        genesis_envelope = updated.pop('_authority_genesis_envelope', None)
        if (
            event.get('schema_id')
            != 'ars://core/event/AuthorityGrantActivated'
            or not isinstance(genesis_envelope, dict)
            or any(
                event.get(field) != expected
                for field, expected in genesis_envelope.items()
            )
        ):
            raise IntegrityError('authority genesis envelope binding mismatch')
        if payload.get('authorizing_grant_id') != root_id or payload.get('authorizing_grant_sha256') != grants.get(root_id, {}).get('authority_grant_sha256'):
            raise IntegrityError('publication activation authority mismatch')
        if payload.get('activated_grant_id') != stream_id or stream_id in grants:
            raise IntegrityError('publication activation stream mismatch or duplicate')
        grants[stream_id] = {
            'authority_grant_id': stream_id,
            'authority_grant_sha256': payload['activated_grant_sha256'],
            'status': 'active',
            'activation_event_id': event['event_id'],
            'activation_position': event['global_position'],
            'revocation_event_id': None,
            'revocation_position': None,
        }
    elif event_type == 'AuthorityGrantRevoked':
        payload = event['payload']
        if set(payload) != {
            'project_id', 'target_grant_id', 'target_grant_sha256',
            'authorizing_grant_id', 'authorizing_grant_sha256', 'reason',
        }:
            raise IntegrityError('authority revocation payload fields must be exact')
        grants = updated.setdefault('authority_grants', {})
        current = grants.get(stream_id)
        root_id = updated.get('authority_root_id')
        if payload.get('project_id') != updated.get('project_id'):
            raise IntegrityError('authority revocation project mismatch')
        if current is None or current['status'] != 'active':
            raise IntegrityError('authority revocation requires active grant')
        if payload.get('target_grant_id') != stream_id or payload.get('target_grant_sha256') != current['authority_grant_sha256']:
            raise IntegrityError('authority revocation target mismatch')
        if payload.get('authorizing_grant_id') != root_id or payload.get('authorizing_grant_sha256') != grants.get(root_id, {}).get('authority_grant_sha256'):
            raise IntegrityError('authority revocation root mismatch')
        grants[stream_id] = {
            **current,
            'status': 'revoked',
            'revocation_event_id': event['event_id'],
            'revocation_position': event['global_position'],
        }
    elif event_type in {'TaskCreated', 'TaskSuperseded'}:
        streams[stream_id] = reduce_task(streams.get(stream_id, {}), event)
    elif event_type == 'DispatchClaimed':
        current = streams.get(
            stream_id,
            {
                'dispatch_id': stream_id,
                'status': 'unclaimed',
                'active_attempt_ids': [],
                'version': 0,
            },
        )
        if current['status'] != 'unclaimed':
            raise IntegrityError('dispatch already has an active attempt')
        streams[stream_id] = {
            **current,
            'status': 'claimed',
            'active_attempt_ids': [event['payload']['attempt_id']],
            'version': current['version'] + 1,
        }
    elif event_type == 'ScopeCompleted':
        _validate_scope_completion(event['payload'])
        streams[stream_id] = {
            'scope_id': stream_id,
            'status': 'completed',
            'scope_definition_ref': event['payload']['scope_definition_ref'],
            'member_dispositions': dict(event['payload']['member_dispositions']),
            'version': event['stream_version'],
        }
    elif event_type in {'EvidenceDeletionVerified', 'EvidenceDeletionPending'}:
        payload = event['payload']
        expected_status = (
            'verified'
            if event_type == 'EvidenceDeletionVerified'
            else 'deletion_pending'
        )
        if payload.get('status') != expected_status:
            raise IntegrityError('deletion event status mismatch')
        required = {
            'evidence_store_id',
            'evidence_id',
            'evidence_hash',
            'retention_rule_id',
            'policy_revision',
            'registry_hash',
            'manifest_hash',
        }
        missing = sorted(required.difference(payload))
        if missing:
            raise IntegrityError(
                'deletion event missing fields: ' + ', '.join(missing)
            )
        evidence_store_id = payload['evidence_store_id']
        streams[evidence_store_id] = {
            'evidence_store_id': evidence_store_id,
            'status': (
                'expired_deleted' if expected_status == 'verified'
                else 'deletion_pending'
            ),
            'evidence_id': payload['evidence_id'],
            'evidence_hash': payload['evidence_hash'],
            'retention_rule_id': payload['retention_rule_id'],
            'policy_revision': payload['policy_revision'],
            'registry_hash': payload['registry_hash'],
            'deletion_manifest_hash': payload['manifest_hash'],
            'r2_intake_blocked': expected_status != 'verified',
            'version': event['stream_version'],
        }
    elif event_type == 'ReleaseGateDecisionPublished':
        payload = event['payload']
        expected_fields = {
            'release_decision',
            'source_decision_sha256',
            'evaluation_runs_manifest_ref',
            'evaluation_runs_manifest_sha256',
            'control_binding_ref',
            'control_binding_sha256',
            'publication_authority_grant_id',
            'publication_authority_sha256',
            'gate5_authorized',
            'candidate_status',
        }
        if set(payload) != expected_fields:
            raise IntegrityError('release publication payload fields must be exact')
        decision = payload.get('release_decision')
        stream_id = event.get('stream_id')
        publication_grant_id = payload.get('publication_authority_grant_id')
        publication_grant = updated.get('authority_grants', {}).get(
            publication_grant_id
        )
        if (
            not isinstance(decision, dict)
            or not isinstance(stream_id, str)
            or not stream_id.startswith('rgd_')
            or decision.get('release_gate_decision_id') != stream_id
            or decision.get('canonical_event_ref') != event.get('event_id')
            or decision.get('decision') != 'blocked'
            or payload.get('gate5_authorized') is not False
            or payload.get('candidate_status') != 'blocked'
            or event.get('authority_grant_id') != publication_grant_id
            or not isinstance(publication_grant, dict)
            or publication_grant.get('status') != 'active'
            or publication_grant.get('authority_grant_sha256')
            != payload.get('publication_authority_sha256')
        ):
            raise IntegrityError('release publication identity or disposition mismatch')
        source = deepcopy(decision)
        source['canonical_event_ref'] = 'unpublished:p0'
        if payload.get('source_decision_sha256') != sha256_hex(
            canonical_bytes(source)
        ):
            raise IntegrityError('release publication source hash mismatch')
        releases = updated.setdefault('release_decisions', {})
        if stream_id in releases:
            raise IntegrityError('release decision is already projected')
        projection = {
            'release_decision_id': stream_id,
            'event_id': event['event_id'],
            'event_hash': event['event_hash'],
            'event_position': event['global_position'],
            'project_id': event['project_id'],
            'release_decision': decision,
            'source_decision_sha256': payload['source_decision_sha256'],
            'evaluation_runs_manifest_ref': payload[
                'evaluation_runs_manifest_ref'
            ],
            'evaluation_runs_manifest_sha256': payload[
                'evaluation_runs_manifest_sha256'
            ],
            'control_binding_ref': payload['control_binding_ref'],
            'control_binding_sha256': payload['control_binding_sha256'],
            'publication_authority_grant_id': payload[
                'publication_authority_grant_id'
            ],
            'publication_authority_sha256': payload[
                'publication_authority_sha256'
            ],
            'publication_authority_activation_position': publication_grant[
                'activation_position'
            ],
            'gate5_authorized': False,
            'candidate_status': 'blocked',
            'version': event['stream_version'],
        }
        releases[stream_id] = projection
        streams[stream_id] = projection
    else:
        raise IntegrityError(f'unsupported event type: {event_type}')
    return updated


def _major(event: dict[str, Any]) -> int:
    try:
        return int(str(event['schema_version']).split('.', maxsplit=1)[0])
    except (KeyError, TypeError, ValueError) as exc:
        raise IntegrityError('invalid event schema version') from exc


def _verify_event_hash(event: dict[str, Any]) -> bool:
    unsigned = dict(event)
    recorded = unsigned.pop('event_hash', None)
    return recorded == sha256_hex(canonical_bytes(unsigned))


def replay(
    events: Iterable[dict[str, Any]],
    supported_major: int = 1,
    schema_registry: SchemaRegistry | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        'streams': {},
        'last_position': 0,
        'last_hash': '0' * 64,
        'project_id': None,
    }
    stream_versions: dict[str, int] = {}
    transaction_id: str | None = None
    transaction_count = 0
    transaction_index = 0
    for source in events:
        event = deepcopy(source)
        position = event.get('global_position')
        release_event = event.get('event_type') == 'ReleaseGateDecisionPublished'
        if release_event and schema_registry is None:
            raise IntegrityError('release event schema validator unavailable')
        if schema_registry is not None:
            try:
                schema_registry.validate('ars://core/event', event)
                if release_event:
                    schema_registry.validate(
                        'ars://core/event/ReleaseGateDecisionPublished',
                        event,
                    )
                else:
                    payload_schema = f"{event.get('schema_id')}/payload"
                    if schema_registry.contains(payload_schema):
                        schema_registry.validate(payload_schema, event.get('payload'))
            except SchemaError as exc:
                raise IntegrityError(
                    f'event schema validation failed at {position}'
                ) from exc
        if _major(event) != supported_major:
            raise IntegrityError(f'unsupported major at {position}')
        schema_id = event.get('schema_id')
        if not isinstance(schema_id, str) or not schema_id.startswith(
            'ars://core/event/'
        ):
            raise IntegrityError(f'unknown event schema at {position}')
        if position != state['last_position'] + 1:
            raise IntegrityError('event position gap or overlap')
        if event.get('previous_event_hash') != state['last_hash']:
            raise IntegrityError('event hash-chain mismatch')
        if not _verify_event_hash(event):
            raise IntegrityError(f'event hash mismatch at {position}')
        project_id = event.get('project_id')
        if state['project_id'] is None:
            state['project_id'] = project_id
        elif project_id != state['project_id']:
            raise IntegrityError('event project identity mismatch')
        stream_id = event.get('stream_id')
        expected_stream_version = stream_versions.get(stream_id, 0) + 1
        if event.get('stream_version') != expected_stream_version:
            raise IntegrityError('stream version gap or overlap')
        stream_versions[stream_id] = expected_stream_version
        current_transaction = event.get('transaction_id')
        if current_transaction != transaction_id:
            if transaction_id is not None and transaction_index != transaction_count:
                raise IntegrityError('incomplete event transaction')
            transaction_id = current_transaction
            transaction_count = event.get('transaction_count')
            transaction_index = 0
        if event.get('transaction_count') != transaction_count:
            raise IntegrityError('event transaction count mismatch')
        transaction_index += 1
        if event.get('transaction_index') != transaction_index:
            raise IntegrityError('event transaction index gap or overlap')
        state = apply_event(state, event)
        state['last_position'] = position
        state['last_hash'] = event['event_hash']
    if transaction_id is not None and transaction_index != transaction_count:
        raise IntegrityError('incomplete event transaction')
    return state


def rebuild_projection(
    events: Iterable[dict[str, Any]],
    output: Path,
    schema_registry: SchemaRegistry | None = None,
) -> dict[str, Any]:
    state = replay(events, schema_registry=schema_registry)
    data = canonical_bytes(state) + b'\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f'.{output.name}.tmp')
    with temporary.open('wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output)
    return state
