import pytest

from research_system.errors import ArsError, ConflictError
from research_system.store.layout import require_external_control_root
from research_system.store.ledger import EventLedger
from research_system.store.lock import WriterLock
from research_system.store.objects import write_object


PROJECT_ID = 'prj_01978abc-0001-7000-8000-000000000001'
TASK_ID = 'tsk_01978abc-0002-7000-8000-000000000002'


def test_control_root_requires_registered_code_roots(tmp_path):
    with pytest.raises(ArsError, match='registered code roots required'):
        require_external_control_root([], tmp_path / 'control')


def test_control_root_overlapping_any_registered_worktree_is_rejected(tmp_path):
    main = tmp_path / 'main'
    worktree = tmp_path / 'worktree'
    main.mkdir()
    worktree.mkdir()
    with pytest.raises(ArsError, match='disjoint from every code root'):
        require_external_control_root([main, worktree], worktree / 'control')
    with pytest.raises(ArsError, match='disjoint from every code root'):
        require_external_control_root([main, worktree], tmp_path)


def test_sibling_external_control_root_is_accepted(tmp_path):
    code_root = tmp_path / 'repo'
    control_root = tmp_path / 'control'
    code_root.mkdir()
    assert require_external_control_root([code_root], control_root) == control_root.resolve()


def test_resolved_reparse_parent_overlapping_code_root_is_rejected(tmp_path):
    code_root = tmp_path / 'repo'
    linked_parent = tmp_path / 'linked-parent'
    code_root.mkdir()
    try:
        linked_parent.symlink_to(code_root, target_is_directory=True)
    except OSError:
        pytest.skip('directory symlink/reparse creation unavailable on this host')
    with pytest.raises(ArsError, match='disjoint from every code root'):
        require_external_control_root([code_root], linked_parent / 'control')


def test_second_writer_lock_is_rejected(tmp_path):
    path = tmp_path / 'writer.lock'
    with WriterLock(path, {'writer_id': 'w1'}):
        with pytest.raises(ConflictError, match='writer lock exists'):
            with WriterLock(path, {'writer_id': 'w2'}):
                raise AssertionError('second writer entered lock')


def test_object_write_is_content_addressed_and_non_overwriting(tmp_path):
    first = write_object(tmp_path, 'task', TASK_ID, 1, {'x': 1})
    second = write_object(tmp_path, 'task', TASK_ID, 1, {'x': 1})
    assert first == second
    with pytest.raises(ConflictError, match='object revision already exists'):
        write_object(tmp_path, 'task', TASK_ID, 1, {'x': 2})


def test_batch_is_invisible_until_atomic_replace(tmp_path, monkeypatch):
    ledger = EventLedger(tmp_path, project_id=PROJECT_ID)
    monkeypatch.setattr(
        ledger,
        '_publish',
        lambda source, target: (_ for _ in ()).throw(OSError('crash')),
    )
    with pytest.raises(OSError, match='crash'):
        ledger.append([{'event_type': 'TaskCreated', 'stream_id': TASK_ID}])
    assert list((tmp_path / 'events').rglob('*.jsonl')) == []


def test_batch_positions_and_hash_chain_are_contiguous(tmp_path):
    ledger = EventLedger(tmp_path, project_id=PROJECT_ID)
    receipt = ledger.append(
        [{'event_type': 'TaskCreated', 'stream_id': TASK_ID}]
    )
    events = list(ledger.iter_events())
    assert [item['global_position'] for item in events] == [1]
    assert events[0]['previous_event_hash'] == '0' * 64
    assert receipt['event_batch_id'] == events[0]['transaction_id']

def test_caller_cannot_override_recorded_at(tmp_path):
    ledger = EventLedger(tmp_path, project_id=PROJECT_ID)
    with pytest.raises(ArsError, match='protected event fields'):
        ledger.append(
            [
                {
                    'event_type': 'TaskCreated',
                    'stream_id': TASK_ID,
                    'recorded_at': '2000-01-01T00:00:00Z',
                }
            ]
        )
