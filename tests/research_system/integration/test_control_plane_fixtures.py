import json

import pytest

from research_system.canonical import canonical_bytes
from research_system.command.models import Receipt
from research_system.errors import IntegrityError
from tests.research_system.factories import (
    claim_dispatch_command,
    control_plane,
    create_task_command,
)

FAULT_COMMAND_ID = 'cmd_01978abc-3010-7000-8000-000000003010'
FAULT_TASK_ID = 'tsk_01978abc-3011-7000-8000-000000003011'


def _fault_command():
    return create_task_command(
        FAULT_COMMAND_ID,
        'fault-recovery',
        FAULT_TASK_ID,
        {'title': 'Fault recovery'},
    )


def _raise(message):
    raise OSError(message)


def _assert_recovered(harness, command):
    recovered = harness.service.submit(command)
    assert recovered.status == 'accepted'
    assert len(tuple(harness.ledger.iter_batches())) == 1
    event = next(harness.ledger.iter_events())
    expected = Receipt(
        status='accepted',
        command_id=event['command_id'],
        payload_hash=event['command_payload_hash'],
        event_batch_id=event['transaction_id'],
        observed_stream_version=event['stream_version'],
    )
    receipt_path = harness.receipts.receipts_root / f'{event["command_id"]}.json'
    assert recovered == expected
    assert receipt_path.read_bytes() == canonical_bytes(
        {
            'schema_id': 'ars://core/receipt',
            'schema_version': '1.0.0',
            'command_id': expected.command_id,
            'status': expected.status,
            'payload_hash': expected.payload_hash,
            'outcome': {
                'event_batch_id': expected.event_batch_id,
                'observed_stream_version': expected.observed_stream_version,
                'reason_code': expected.reason_code,
            },
        }
    )


def test_s001_s002_f001_f002_control_plane_flow(tmp_path):
    harness = control_plane(tmp_path)
    task_id = 'tsk_01978abc-3001-7000-8000-000000003001'
    dispatch_id = 'dsp_01978abc-3002-7000-8000-000000003002'
    create = create_task_command(
        'cmd_01978abc-3003-7000-8000-000000003003',
        'integration-create',
        task_id,
        {'title': 'Integrated'},
    )
    assert harness.service.submit(create) == harness.service.submit(create)
    first = claim_dispatch_command(
        'cmd_01978abc-3004-7000-8000-000000003004',
        'actor-a',
        dispatch_id,
        expected_version=0,
    )
    second = claim_dispatch_command(
        'cmd_01978abc-3005-7000-8000-000000003005',
        'actor-b',
        dispatch_id,
        expected_version=0,
    )
    assert harness.service.submit(first).status == 'accepted'
    assert harness.service.submit(second).status == 'conflict'
    assert len(tuple(harness.ledger.iter_batches())) == 2
    assert len(harness.replay().active_attempt_ids) == 1


def test_s011_crash_after_object_write_retries_to_one_batch(tmp_path, monkeypatch):
    harness = control_plane(tmp_path)
    command = _fault_command()
    original = harness.objects.write

    def write_then_crash(*args, **kwargs):
        original(*args, **kwargs)
        _raise('after object write')

    with monkeypatch.context() as patch:
        patch.setattr(harness.objects, 'write', write_then_crash)
        with pytest.raises(OSError, match='after object write'):
            harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()
    _assert_recovered(harness, command)


def test_s011_crash_after_batch_temp_fsync_retries_to_one_batch(
    tmp_path, monkeypatch
):
    harness = control_plane(tmp_path)
    command = _fault_command()
    with monkeypatch.context() as patch:
        patch.setattr(
            harness.ledger,
            '_after_batch_fsync',
            lambda path: _raise('after batch temp fsync'),
            raising=False,
        )
        with pytest.raises(OSError, match='after batch temp fsync'):
            harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()
    _assert_recovered(harness, command)


def test_s011_crash_after_event_rename_reconstructs_receipt(
    tmp_path, monkeypatch
):
    harness = control_plane(tmp_path)
    command = _fault_command()
    original = harness.ledger._publish

    def publish_then_crash(source, target):
        original(source, target)
        _raise('after event rename')

    with monkeypatch.context() as patch:
        patch.setattr(harness.ledger, '_publish', publish_then_crash)
        with pytest.raises(OSError, match='after event rename'):
            harness.service.submit(command)
    _assert_recovered(harness, command)


def test_s011_crash_before_ledger_tail_refresh_reconstructs_receipt(
    tmp_path, monkeypatch
):
    harness = control_plane(tmp_path)
    command = _fault_command()
    with monkeypatch.context() as patch:
        patch.setattr(
            harness.ledger,
            '_after_publish',
            lambda path: _raise('before ledger tail refresh'),
            raising=False,
        )
        with pytest.raises(OSError, match='before ledger tail refresh'):
            harness.service.submit(command)
    _assert_recovered(harness, command)


def test_s011_crash_after_receipt_temp_fsync_reconstructs_receipt(
    tmp_path, monkeypatch
):
    harness = control_plane(tmp_path)
    command = _fault_command()
    with monkeypatch.context() as patch:
        patch.setattr(
            harness.receipts,
            '_after_temp_fsync',
            lambda path: _raise('after receipt temp fsync'),
            raising=False,
        )
        with pytest.raises(OSError, match='after receipt temp fsync'):
            harness.service.submit(command)
    _assert_recovered(harness, command)


def test_s011_crash_after_receipt_rename_returns_byte_identical_receipt(
    tmp_path, monkeypatch
):
    harness = control_plane(tmp_path)
    command = _fault_command()

    def publish_then_crash(source, target):
        source.replace(target)
        _raise('after receipt rename')

    with monkeypatch.context() as patch:
        patch.setattr(
            harness.receipts,
            '_publish',
            publish_then_crash,
            raising=False,
        )
        with pytest.raises(OSError, match='after receipt rename'):
            harness.service.submit(command)
    _assert_recovered(harness, command)

def test_broken_canonical_tail_blocks_later_command(tmp_path):
    harness = control_plane(tmp_path)
    first = _fault_command()
    harness.service.submit(first)
    batch_path = next(harness.ledger.events_root.rglob('*.jsonl'))
    event = json.loads(batch_path.read_text(encoding='utf-8'))
    event['payload']['title'] = 'tampered without rehash'
    batch_path.write_bytes(canonical_bytes(event) + b'\n')
    second = create_task_command(
        'cmd_01978abc-3012-7000-8000-000000003012',
        'blocked-by-corrupt-tail',
        'tsk_01978abc-3013-7000-8000-000000003013',
        {'title': 'Must not commit'},
    )
    with pytest.raises(IntegrityError, match='event hash mismatch at 1'):
        harness.service.submit(second)
    assert len(tuple(harness.ledger.iter_batches())) == 1
