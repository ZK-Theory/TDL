import json
from copy import deepcopy
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


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("extra",), "forbidden"),
        (("project_id",), "prj_not-a-uuid7"),
        (("target_grant_id",), "agr_not-a-uuid7"),
        (("target_grant_sha256",), "0" * 63),
        (("authority_grant_sha256",), "not-a-hash"),
        (("reason",), ""),
    ],
)
def test_revoke_authority_grant_payload_schema_is_strict(path, value):
    payload = {
        "project_id": "prj_01978abc-1000-7000-8000-000000001000",
        "target_grant_id": "agr_01978abc-1001-7000-8000-000000001001",
        "target_grant_sha256": "1" * 64,
        "authority_grant_sha256": "2" * 64,
        "reason": "synthetic revocation",
    }
    invalid = deepcopy(payload)
    invalid[path[0]] = value
    registry = SchemaRegistry(SCHEMAS)
    registry.validate("ars://core/command/RevokeAuthorityGrant/payload", payload)
    with pytest.raises(SchemaError):
        registry.validate(
            "ars://core/command/RevokeAuthorityGrant/payload", invalid
        )


def test_every_core_schema_declares_closed_object_contract():
    paths = sorted((SCHEMAS / 'core').glob('*.schema.json'))
    assert {path.name for path in paths} == {
        'authority-bootstrap-input.schema.json',
        'authority-bootstrap-manifest.schema.json',
        'authority-grant-activated.schema.json',
        'authority-grant-revoked.schema.json',
        'authority-grant.schema.json',
        'authority-root-initialized.schema.json',
        'command.schema.json',
        'event.schema.json',
        'receipt.schema.json',
        'revoke-authority-grant.schema.json',
        'store-identity-1.1.schema.json',
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


def test_authority_event_and_store_schemas_require_complete_registered_ids():
    registry = SchemaRegistry(SCHEMAS)
    root_payload = {
        'bootstrap_manifest_sha256': '0' * 64,
        'authorizing_grant_id': 'agr_not-a-uuid7',
        'authorizing_grant_sha256': '1' * 64,
        'activated_grant_id': 'agr_not-a-uuid7',
        'activated_grant_sha256': '1' * 64,
    }
    with pytest.raises(SchemaError, match='authorizing_grant_id'):
        registry.validate(
            'ars://core/event/AuthorityRootInitialized/payload', root_payload
        )

    store_identity = {
        'schema_id': 'ars://core/store-identity',
        'schema_version': '1.1.0',
        'store_nonce': '0' * 32,
        'project_id': 'prj_not-a-uuid7',
        'bootstrap_manifest_sha256': '1' * 64,
        'store_identity': '2' * 64,
        'control_root': 'C:/synthetic-control',
        'code_roots': ['C:/synthetic-code'],
        'endpoint_scheme': 'local-cli',
        'manifest_hash': '3' * 64,
    }
    with pytest.raises(SchemaError, match='project_id'):
        registry.validate('ars://core/store-identity/1.1', store_identity)
