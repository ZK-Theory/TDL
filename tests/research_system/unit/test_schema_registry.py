import json
from pathlib import Path

import pytest

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


SCHEMAS = Path('.research-system/schemas')
UUID7 = '01978abc-0001-7000-8000-000000000001'


def _command_payload():
    return {
        'command_id': f'cmd_{UUID7}',
        'command_type': 'CreateTask',
        'schema_id': 'ars://core/command',
        'schema_version': '1.0.0',
        'submitted_at': '2026-07-01T12:00:00Z',
        'actor_id': 'act_01978abc-0002-7000-8000-000000000002',
        'on_behalf_of_actor_id': None,
        'authority_grant_id': 'agr_01978abc-0003-7000-8000-000000000003',
        'target_stream_id': 'tsk_01978abc-0004-7000-8000-000000000004',
        'expected_stream_version': 0,
        'idempotency_key': 'create-task-1',
        'correlation_id': 'synthetic-workflow-1',
        'causation_id': None,
        'reason': 'synthetic P0 test',
        'evidence_refs': [],
        'payload': {},
    }


def test_registry_validates_command_envelope():
    SchemaRegistry(SCHEMAS).validate('ars://core/command', _command_payload())


def test_registry_rejects_non_uuid7_command_identity():
    payload = _command_payload()
    payload['command_id'] = 'cmd_' + '1' * 32
    with pytest.raises(SchemaError, match='command_id'):
        SchemaRegistry(SCHEMAS).validate('ars://core/command', payload)


def test_registry_rejects_unknown_schema():
    with pytest.raises(SchemaError, match='unknown schema'):
        SchemaRegistry(SCHEMAS).validate('ars://missing', {})


def test_every_core_schema_declares_closed_object_contract():
    paths = sorted((SCHEMAS / 'core').glob('*.schema.json'))
    assert {path.name for path in paths} == {
        'authority-grant.schema.json',
        'command.schema.json',
        'event.schema.json',
        'receipt.schema.json',
        'task.schema.json',
    }
    for path in paths:
        schema = json.loads(path.read_text(encoding='utf-8'))
        assert schema['$schema'] == 'https://json-schema.org/draft/2020-12/schema'
        assert schema['$id'].startswith('ars://core/')
        assert schema['type'] == 'object'
        assert schema['required']
        assert schema['properties']
        assert schema['additionalProperties'] is False

def test_task_schema_uses_w2_status_vocabulary():
    task = {
        'schema_id': 'ars://core/task',
        'schema_version': '1.0.0',
        'task_id': 'tsk_01978abc-0004-7000-8000-000000000004',
        'record_revision': 1,
        'status': 'draft',
        'content_hash': '0' * 64,
    }
    registry = SchemaRegistry(SCHEMAS)
    registry.validate('ars://core/task', task)
    task['status'] = 'proposed'
    with pytest.raises(SchemaError, match='status'):
        registry.validate('ars://core/task', task)
