from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.cli import main
from research_system.errors import ArsError, IntegrityError
from research_system.projection.replay import apply_event, rebuild_projection, replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import (
    initialize_control_store,
    verify_store_identity,
)
from tests.research_system.factories import (
    PROJECT_ID,
    control_plane,
    create_task_command,
)

COMMAND_ID = 'cmd_01978abc-4001-7000-8000-000000004001'
TASK_ID = 'tsk_01978abc-4002-7000-8000-000000004002'


def _events(tmp_path):
    harness = control_plane(tmp_path)
    harness.service.submit(
        create_task_command(COMMAND_ID, 'replay', TASK_ID, {'title': 'Replay'})
    )
    return list(harness.ledger.iter_events()), harness


def _rehash(event):
    changed = dict(event)
    changed.pop('event_hash', None)
    changed['event_hash'] = sha256_hex(canonical_bytes(changed))
    return changed



def test_emitted_event_matches_frozen_schema(tmp_path):
    events, _ = _events(tmp_path)
    SchemaRegistry(Path('.research-system/schemas')).validate(
        'ars://core/event', events[0]
    )
def test_s008_incomplete_scope_completion_is_rejected():
    initial = {'streams': {}, 'last_position': 0, 'last_hash': '0' * 64}
    event = {
        'event_type': 'ScopeCompleted',
        'stream_id': 'prj_01978abc-4003-7000-8000-000000004003',
        'stream_version': 1,
        'payload': {
            'scope_definition_ref': {'object_id': 'scope-1', 'revision': 1},
            'required_member_ids': ['T2.1', 'T2.2'],
            'member_dispositions': {'T2.1': 'accepted'},
        },
    }
    with pytest.raises(IntegrityError, match='missing dispositions: T2.2'):
        apply_event(initial, event)
    assert initial == {'streams': {}, 'last_position': 0, 'last_hash': '0' * 64}


def test_s009_projection_rebuild_is_deterministic_and_disposable(tmp_path):
    events, harness = _events(tmp_path)
    output = tmp_path / 'projection.json'
    canonical_before = tuple(
        path.read_bytes() for path in sorted(harness.ledger.events_root.rglob('*.jsonl'))
    )
    first = rebuild_projection(events, output)
    first_bytes = output.read_bytes()
    output.unlink()
    second = rebuild_projection(events, output)
    assert first == second
    assert output.read_bytes() == first_bytes
    assert tuple(
        path.read_bytes() for path in sorted(harness.ledger.events_root.rglob('*.jsonl'))
    ) == canonical_before


def test_s010_unknown_major_fails_before_projection_publication(tmp_path):
    events, _ = _events(tmp_path)
    unknown = deepcopy(events)
    unknown[0]['schema_version'] = '2.0.0'
    unknown[0] = _rehash(unknown[0])
    output = tmp_path / 'projection.json'
    output.write_bytes(b'previous-projection\n')
    with pytest.raises(IntegrityError, match='unsupported major at 1'):
        rebuild_projection(unknown, output)
    assert output.read_bytes() == b'previous-projection\n'


def test_broken_event_hash_fails_closed(tmp_path):
    events, _ = _events(tmp_path)
    events[0]['payload']['title'] = 'tampered'
    with pytest.raises(IntegrityError, match='event hash mismatch at 1'):
        replay(events)


def test_s012_store_identity_mismatch_and_worktree_local_store_are_rejected(
    tmp_path,
):
    code_root = tmp_path / 'repo'
    code_root.mkdir()
    control_root = tmp_path / 'control'
    identity = initialize_control_store([code_root], control_root, PROJECT_ID)
    assert verify_store_identity(control_root, PROJECT_ID, identity) == identity
    with pytest.raises(ArsError, match='store identity mismatch'):
        verify_store_identity(control_root, PROJECT_ID, '0' * 64)
    rogue_root = tmp_path / 'rogue-repo'
    rogue_root.mkdir()
    with pytest.raises(ArsError, match='code root binding mismatch'):
        verify_store_identity(
            control_root, PROJECT_ID, identity, [rogue_root]
        )
    with pytest.raises(ArsError, match='disjoint from every code root'):
        initialize_control_store(
            [code_root], code_root / 'worktree-local-control', PROJECT_ID
        )


def test_cli_requires_explicit_control_and_code_paths():
    with pytest.raises(SystemExit) as exc_info:
        main(['store', 'init', '--project-id', PROJECT_ID])
    assert exc_info.value.code == 2
    with pytest.raises(SystemExit) as exc_info:
        main(['replay', 'verify'])
    assert exc_info.value.code == 2

def test_s006_cli_uses_namespaced_projection_and_explicit_binding(tmp_path, capsys):
    code_root = tmp_path / 'repo'
    code_root.mkdir()
    control_root = tmp_path / 'control'
    assert main(
        [
            'store',
            'init',
            '--code-root',
            str(code_root),
            '--control-root',
            str(control_root),
            '--project-id',
            PROJECT_ID,
        ]
    ) == 0
    identity = json.loads(capsys.readouterr().out)['store_identity']
    config_path = tmp_path / 'binding.json'
    config_path.write_bytes(
        canonical_bytes(
            {
                'code_roots': [str(code_root.resolve())],
                'control_root': str(control_root.resolve()),
                'project_id': PROJECT_ID,
                'schema_root': str(Path('.research-system/schemas').resolve()),
                'store_identity': identity,
            }
        )
    )
    command_path = tmp_path / 'command.json'
    command_path.write_bytes(
        canonical_bytes(
            create_task_command(
                COMMAND_ID, 'cli-submit', TASK_ID, {'title': 'CLI'}
            )
        )
    )
    assert main(
        [
            'command',
            'submit',
            '--config',
            str(config_path),
            '--command',
            str(command_path),
        ]
    ) == 0
    capsys.readouterr()
    assert main(['replay', 'verify', '--control-root', str(control_root)]) == 0
    capsys.readouterr()
    output = code_root / '.research-system' / 'projections' / 'state.json'
    assert main(
        [
            'projection',
            'rebuild',
            '--control-root',
            str(control_root),
            '--output',
            str(output),
        ]
    ) == 0
    assert json.loads(output.read_text(encoding='utf-8'))['last_position'] == 1
    with pytest.raises(ArsError, match='namespaced projection root'):
        main(
            [
                'projection',
                'rebuild',
                '--control-root',
                str(control_root),
                '--output',
                str(code_root / 'task.md'),
            ]
        )
    with pytest.raises(ArsError, match='projection output must be external'):
        main(
            [
                'projection',
                'rebuild',
                '--control-root',
                str(control_root),
                '--output',
                str(control_root / 'events' / 'projection.json'),
            ]
        )
