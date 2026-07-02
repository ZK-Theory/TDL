import json
import pytest

from research_system.canonical import canonical_bytes
from research_system.command.reducers import reduce_task
from research_system.command.service import CommandService
from research_system.errors import ConflictError, IntegrityError, SchemaError
from tests.research_system.factories import (
    claim_dispatch_command,
    control_plane,
    create_task_command,
)

CMD_CREATE = 'cmd_01978abc-2001-7000-8000-000000002001'
CMD_CLAIM_A = 'cmd_01978abc-2002-7000-8000-000000002002'
CMD_CLAIM_B = 'cmd_01978abc-2003-7000-8000-000000002003'
TASK_ID = 'tsk_01978abc-2004-7000-8000-000000002004'
DISPATCH_ID = 'dsp_01978abc-2005-7000-8000-000000002005'
ARTEFACT_ID = 'art_01978abc-2006-7000-8000-000000002006'


def test_identical_retry_returns_original_receipt_and_one_batch(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, 'same', TASK_ID, {'title': 'A'})
    assert harness.service.submit(command) == harness.service.submit(command)
    assert len(tuple(harness.ledger.iter_batches())) == 1


def test_same_idempotency_key_with_changed_payload_conflicts(tmp_path):
    harness = control_plane(tmp_path)
    first = create_task_command(CMD_CREATE, 'same', TASK_ID, {'title': 'A'})
    changed = {**first, 'payload': {'title': 'B'}}
    harness.service.submit(first)
    with pytest.raises(ConflictError, match='idempotency'):
        harness.service.submit(changed)


def test_same_key_is_independent_across_command_types(tmp_path):
    harness = control_plane(tmp_path)
    create = create_task_command(CMD_CREATE, 'shared', TASK_ID, {'title': 'A'})
    claim = claim_dispatch_command(
        CMD_CLAIM_A, 'actor-a', DISPATCH_ID, expected_version=0
    )
    claim['idempotency_key'] = 'shared'
    assert harness.service.submit(create).status == 'accepted'
    assert harness.service.submit(claim).status == 'accepted'
    assert len(tuple(harness.ledger.iter_batches())) == 2


def test_reused_command_id_conflicts_before_second_batch(tmp_path):
    harness = control_plane(tmp_path)
    first = create_task_command(CMD_CREATE, 'first-command', TASK_ID, {'title': 'A'})
    reused = claim_dispatch_command(
        CMD_CREATE, 'actor-b', DISPATCH_ID, expected_version=0
    )
    original = harness.service.submit(first)
    with pytest.raises(ConflictError, match='command ID conflicts'):
        harness.service.submit(reused)
    assert len(tuple(harness.ledger.iter_batches())) == 1
    assert harness.receipts.load(CMD_CREATE) == original


def test_competing_claims_create_only_one_active_attempt(tmp_path):
    harness = control_plane(tmp_path)
    first = claim_dispatch_command(
        CMD_CLAIM_A, 'actor-a', DISPATCH_ID, expected_version=0
    )
    second = claim_dispatch_command(
        CMD_CLAIM_B, 'actor-b', DISPATCH_ID, expected_version=0
    )
    winner = harness.service.submit(first)
    loser = harness.service.submit(second)
    assert {winner.status, loser.status} == {'accepted', 'conflict'}
    assert len(harness.replay().active_attempt_ids) == 1


def test_conflict_receipt_is_persisted_and_reused_after_stream_changes(tmp_path):
    harness = control_plane(tmp_path)
    blocked = claim_dispatch_command(
        CMD_CLAIM_A, 'actor-a', DISPATCH_ID, expected_version=1
    )
    original = harness.service.submit(blocked)
    assert original.status == 'conflict'
    assert original.observed_stream_version == 0
    assert harness.receipts.load(CMD_CLAIM_A) == original

    advancing = claim_dispatch_command(
        CMD_CLAIM_B, 'actor-a', DISPATCH_ID, expected_version=0
    )
    assert harness.service.submit(advancing).status == 'accepted'
    restarted = CommandService(
        harness.service.control_root,
        harness.ledger,
        harness.objects,
        harness.receipts,
        harness.service.schemas,
    )
    assert restarted.submit(blocked) == original


def test_conflict_receipt_rejects_command_id_reuse_with_changed_payload(tmp_path):
    harness = control_plane(tmp_path)
    blocked = claim_dispatch_command(
        CMD_CLAIM_A, 'actor-a', DISPATCH_ID, expected_version=1
    )
    harness.service.submit(blocked)
    changed = {**blocked, 'payload': {'changed': True}}
    with pytest.raises(ConflictError, match='stored receipt'):
        harness.service.submit(changed)


def test_distinct_task_and_artefact_objects_cannot_overwrite(tmp_path):
    harness = control_plane(tmp_path)
    task = harness.objects.write('task', TASK_ID, 1, {'kind': 'task'})
    artefact = harness.objects.write(
        'artefact', ARTEFACT_ID, 1, {'kind': 'artefact'}
    )
    assert task != artefact
    assert task.read_bytes() != artefact.read_bytes()


def test_committed_batch_reconstructs_missing_receipt_on_retry(
    tmp_path, monkeypatch
):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, 'recover', TASK_ID, {'title': 'A'})
    original_write = harness.receipts.write
    monkeypatch.setattr(
        harness.receipts,
        'write',
        lambda receipt: (_ for _ in ()).throw(OSError('receipt crash')),
    )
    with pytest.raises(OSError, match='receipt crash'):
        harness.service.submit(command)
    assert len(tuple(harness.ledger.iter_batches())) == 1
    monkeypatch.setattr(harness.receipts, 'write', original_write)
    recovered = harness.service.submit(command)
    assert recovered.status == 'accepted'
    assert len(tuple(harness.ledger.iter_batches())) == 1
    assert harness.receipts.load(CMD_CREATE) == recovered


def test_reconstructed_receipt_uses_target_stream_version_not_batch_max(tmp_path):
    harness = control_plane(tmp_path)
    transaction_id = 'txb_01978abc-2011-7000-8000-000000002011'
    shared = {
        'command_id': CMD_CREATE,
        'command_payload_hash': 'a' * 64,
        'transaction_id': transaction_id,
    }
    reconstructed = harness.service._return_or_reconstruct(
        [
            {**shared, 'stream_id': TASK_ID, 'stream_version': 1},
            {**shared, 'stream_id': DISPATCH_ID, 'stream_version': 4},
        ]
    )
    assert reconstructed.observed_stream_version == 1


def test_retry_rejects_receipt_that_does_not_match_committed_batch(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, 'receipt-match', TASK_ID, {'title': 'A'})
    harness.service.submit(command)
    path = harness.receipts.receipts_root / f'{CMD_CREATE}.json'
    record = json.loads(path.read_text(encoding='utf-8'))
    record['outcome']['event_batch_id'] = (
        'txb_01978abc-2010-7000-8000-000000002010'
    )
    path.write_bytes(canonical_bytes(record))
    with pytest.raises(IntegrityError, match='receipt does not match'):
        harness.service.submit(command)


def test_invalid_command_is_rejected_before_lifecycle_event(tmp_path):
    harness = control_plane(tmp_path)
    invalid = create_task_command(CMD_CREATE, 'invalid', TASK_ID, {'title': 'A'})
    invalid.pop('reason')
    with pytest.raises(SchemaError, match='reason'):
        harness.service.submit(invalid)
    assert tuple(harness.ledger.iter_batches()) == ()


def test_task_reducer_is_pure_and_fails_closed():
    created = reduce_task(
        {},
        {'event_type': 'TaskCreated', 'stream_id': TASK_ID},
    )
    assert created == {'task_id': TASK_ID, 'status': 'draft', 'version': 1}
    with pytest.raises(ValueError, match='TaskCreated requires empty stream'):
        reduce_task(created, {'event_type': 'TaskCreated', 'stream_id': TASK_ID})

def test_unknown_task_stream_readiness_fails_as_illegal_transition():
    with pytest.raises(ValueError, match='illegal task transition: None'):
        reduce_task(
            {},
            {'event_type': 'ReadinessRequested', 'stream_id': TASK_ID},
        )


def test_submission_materializes_ledger_once(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, 'one-scan', TASK_ID, {'title': 'A'})
    original = harness.ledger.iter_events
    calls = 0

    def counted_events():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(harness.ledger, 'iter_events', counted_events)
    assert harness.service.submit(command).status == 'accepted'
    assert calls == 1

def test_persisted_receipt_matches_frozen_schema(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command(CMD_CREATE, 'receipt-schema', TASK_ID, {'title': 'A'})
    harness.service.submit(command)
    record = json.loads(
        (harness.receipts.receipts_root / f'{CMD_CREATE}.json').read_text(
            encoding='utf-8'
        )
    )
    harness.service.schemas.validate('ars://core/receipt', record)
