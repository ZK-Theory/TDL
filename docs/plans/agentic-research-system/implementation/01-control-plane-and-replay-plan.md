# ARS P0 Work Package 1: Control Plane and Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the local single-writer command, event, receipt, replay, projection, and CLI foundation required by W1/W2.

**Architecture:** A Python package validates tracked JSON Schemas, writes immutable objects before one atomic JSONL event batch, and treats the batch rename as the commit point. Every invocation receives an explicit external control root; pure reducers rebuild disposable projections from the global position/hash chain.

**Tech Stack:** Python 3.13.5, dataclasses, pathlib, hashlib, json, tempfile/os.replace, PyYAML, jsonschema Draft 2020-12, argparse, pytest, ruff.

---

## File map

**Create:**

```text
research_system/__init__.py
research_system/errors.py
research_system/canonical.py
research_system/ids.py
research_system/config.py
research_system/schema_registry.py
research_system/store/__init__.py
research_system/store/layout.py
research_system/store/lock.py
research_system/store/objects.py
research_system/store/ledger.py
research_system/store/receipts.py
research_system/command/__init__.py
research_system/command/models.py
research_system/command/reducers.py
research_system/command/service.py
research_system/projection/__init__.py
research_system/projection/replay.py
research_system/cli.py
.research-system/config/foundation.yaml
.research-system/schemas/core/command.schema.json
.research-system/schemas/core/event.schema.json
.research-system/schemas/core/receipt.schema.json
.research-system/schemas/core/task.schema.json
.research-system/schemas/core/authority-grant.schema.json
tests/__init__.py
tests/research_system/__init__.py
tests/research_system/factories.py
tests/research_system/unit/test_canonical_ids.py
tests/research_system/unit/test_schema_registry.py
tests/research_system/unit/test_store.py
tests/research_system/unit/test_command_service.py
tests/research_system/unit/test_replay.py
tests/research_system/integration/test_control_plane_fixtures.py
```

**Modify:** `pyproject.toml`, `.gitignore`.

## Task 1: Bootstrap package, canonical serialization, and IDs

- [ ] **Step 1: Write failing canonical/ID tests**

```python
# tests/__init__.py
tests/research_system/__init__.py
tests/research_system/factories.py
tests/research_system/unit/test_canonical_ids.py
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id, validate_id


def test_canonical_bytes_are_order_independent():
    left = canonical_bytes({'b': 2, 'a': 1})
    right = canonical_bytes({'a': 1, 'b': 2})
    assert left == b'{"a":1,"b":2}'
    assert left == right
    assert sha256_hex(left) == sha256_hex(right)


def test_ids_are_prefixed_opaque_and_validated():
    value = new_id('cmd')
    assert value.startswith('cmd_')
    assert validate_id(value, 'cmd') == value
```

- [ ] **Step 2: Run the tests and confirm the package is absent**

Run: `uv run pytest tests/research_system/unit/test_canonical_ids.py -q --no-cov`

Expected: collection fails with `ModuleNotFoundError: No module named 'research_system'`.

- [ ] **Step 3: Add package metadata and minimal implementation**

Add to `pyproject.toml`:

```toml
[project.scripts]
ars = "research_system.cli:main"

[tool.setuptools.packages.find]
include = ["financial_tda*", "poverty_tda*", "shared*", "trajectory_tda*", "research_system*"]
```

Create:

```python
# research_system/canonical.py
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False
    ).encode('utf-8')


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

```python
# research_system/ids.py
from __future__ import annotations

import re
import uuid

_ID = re.compile(r'^(?P<prefix>[a-z][a-z0-9]*)_(?P<body>[0-9a-f]{32})$')


def new_id(prefix: str) -> str:
    if not re.fullmatch(r'[a-z][a-z0-9]*', prefix):
        raise ValueError(f'invalid ID prefix: {prefix!r}')
    return f'{prefix}_{uuid.uuid4().hex}'


def validate_id(value: str, prefix: str) -> str:
    match = _ID.fullmatch(value)
    if match is None or match.group('prefix') != prefix:
        raise ValueError(f'expected {prefix}_ ID, got {value!r}')
    return value
```

Create empty `__init__.py` files and define typed exceptions in `research_system/errors.py`:

```python
class ArsError(Exception):
    pass


class SchemaError(ArsError):
    pass


class ConflictError(ArsError):
    pass


class IntegrityError(ArsError):
    pass
```

- [ ] **Step 4: Run targeted tests and lint**

Run:

```powershell
uv run pytest tests/research_system/unit/test_canonical_ids.py -q --no-cov
uv run ruff check research_system tests/__init__.py
tests/research_system/__init__.py
tests/research_system/factories.py
tests/research_system/unit/test_canonical_ids.py
```

Expected: 2 tests pass; ruff exits 0.

- [ ] **Step 5: Commit the bootstrap**

```powershell
git add pyproject.toml research_system tests/__init__.py
tests/research_system/__init__.py
tests/research_system/factories.py
tests/research_system/unit/test_canonical_ids.py
[IO.File]::WriteAllLines('C:\tmp\ars-p0-wp1-bootstrap.txt', @('[PIPELINE] P00: scaffold ARS foundation package', '', 'Adds canonical serialization, opaque IDs, and the ars entry point.'))
git commit -F C:\tmp\ars-p0-wp1-bootstrap.txt
```

## Task 2: Add tracked schema registry and project configuration

- [ ] **Step 1: Write failing schema-registry tests**

```python
# tests/research_system/unit/test_schema_registry.py
from pathlib import Path

import pytest

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


SCHEMAS = Path('.research-system/schemas')


def test_registry_validates_command_envelope():
    registry = SchemaRegistry(SCHEMAS)
    payload = {
        'command_id': 'cmd_' + '1' * 32,
        'command_type': 'CreateTask',
        'schema_id': 'ars://core/command',
        'schema_version': '1.0.0',
        'actor_id': 'act_' + '2' * 32,
        'authority_grant_id': 'agr_' + '3' * 32,
        'target_stream_id': 'tsk_' + '4' * 32,
        'expected_stream_version': 0,
        'idempotency_key': 'create-task-1',
        'correlation_id': 'cor_' + '5' * 32,
        'causation_id': None,
        'reason': 'synthetic P0 test',
        'evidence_refs': [],
        'payload': {},
    }
    registry.validate('ars://core/command', payload)


def test_registry_rejects_unknown_schema():
    with pytest.raises(SchemaError, match='unknown schema'):
        SchemaRegistry(SCHEMAS).validate('ars://missing', {})
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_schema_registry.py -q --no-cov`

Expected: import or missing-schema failure.

- [ ] **Step 3: Create Draft 2020-12 schemas and loader**

Every schema file must declare `$schema`, `$id`, `type: object`, `required`, `properties`, and `additionalProperties: false`. Implement:

```python
# research_system/schema_registry.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from research_system.errors import SchemaError


class SchemaRegistry:
    def __init__(self, root: Path):
        self._schemas: dict[str, dict[str, Any]] = {}
        for path in sorted(root.rglob('*.schema.json')):
            schema = json.loads(path.read_text(encoding='utf-8'))
            Draft202012Validator.check_schema(schema)
            schema_id = schema['$id']
            if schema_id in self._schemas:
                raise SchemaError(f'duplicate schema: {schema_id}')
            self._schemas[schema_id] = schema

    def validate(self, schema_id: str, value: Any) -> None:
        schema = self._schemas.get(schema_id)
        if schema is None:
            raise SchemaError(f'unknown schema: {schema_id}')
        errors = sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            message = '; '.join(error.message for error in errors)
            raise SchemaError(f'{schema_id}: {message}')
```

`.research-system/config/foundation.yaml` contains only tracked definitions and no live path:

```yaml
schema_version: '1.0.0'
project_template_id: prj_ars_foundation_p0
control_root: null
control_root_required: true
endpoint_scheme: local-cli
canonical_hash: sha256
```

- [ ] **Step 4: Verify schemas**

Run:

```powershell
uv run pytest tests/research_system/unit/test_schema_registry.py -q --no-cov
uv run python -c "from pathlib import Path; from research_system.schema_registry import SchemaRegistry; SchemaRegistry(Path('.research-system/schemas')); print('schemas-ok')"
```

Expected: tests pass and command prints `schemas-ok`.

- [ ] **Step 5: Commit schema freeze**

Commit subject: `[PIPELINE] P00: add ARS core schema registry` using a message file and `git commit -F`.

## Task 3: Implement explicit external control-root storage

- [ ] **Step 1: Write failing layout, lock, object, and atomic-batch tests**

Tests must prove:

```python
import pytest

from research_system.errors import ArsError, ConflictError
from research_system.store.layout import require_external_control_root
from research_system.store.ledger import EventLedger
from research_system.store.lock import WriterLock
from research_system.store.objects import write_object


def test_control_root_inside_code_root_is_rejected(tmp_path):
    code_root = tmp_path / 'repo'
    code_root.mkdir()
    with pytest.raises(ArsError, match='outside the code repository'):
        require_external_control_root(code_root, code_root / 'control')


def test_second_writer_lock_is_rejected(tmp_path):
    path = tmp_path / 'writer.lock'
    with WriterLock(path, {'writer_id': 'w1'}):
        with pytest.raises(ConflictError, match='writer lock exists'):
            with WriterLock(path, {'writer_id': 'w2'}):
                raise AssertionError('second writer entered lock')


def test_object_write_is_content_addressed_and_non_overwriting(tmp_path):
    first = write_object(tmp_path, 'task', 'tsk_' + '1' * 32, 1, {'x': 1})
    second = write_object(tmp_path, 'task', 'tsk_' + '1' * 32, 1, {'x': 1})
    assert first == second
    with pytest.raises(ConflictError, match='object revision already exists'):
        write_object(tmp_path, 'task', 'tsk_' + '1' * 32, 1, {'x': 2})


def test_batch_is_invisible_until_atomic_replace(tmp_path, monkeypatch):
    ledger = EventLedger(tmp_path, project_id='prj_' + '2' * 32)
    monkeypatch.setattr(ledger, '_publish', lambda source, target: (_ for _ in ()).throw(OSError('crash')))
    with pytest.raises(OSError, match='crash'):
        ledger.append([{'event_type': 'TaskCreated', 'stream_id': 'tsk_' + '3' * 32}])
    assert list((tmp_path / 'events').rglob('*.jsonl')) == []


def test_batch_positions_and_hash_chain_are_contiguous(tmp_path):
    ledger = EventLedger(tmp_path, project_id='prj_' + '4' * 32)
    receipt = ledger.append([{'event_type': 'TaskCreated', 'stream_id': 'tsk_' + '5' * 32}])
    events = list(ledger.iter_events())
    assert [item['global_position'] for item in events] == [1]
    assert events[0]['previous_event_hash'] == '0' * 64
    assert receipt['event_batch_id'] == events[0]['event_batch_id']
```

Use a synthetic `code_root = tmp_path / 'repo'` and separate `control_root = tmp_path / 'control'`; never point tests at the real repository.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_store.py -q --no-cov`

Expected: missing `research_system.store` modules.

- [ ] **Step 3: Implement the storage boundary**

Core layout check:

```python
# research_system/store/layout.py
from pathlib import Path

from research_system.errors import ArsError


def require_external_control_root(code_root: Path, control_root: Path) -> Path:
    code = code_root.resolve(strict=True)
    control = control_root.resolve(strict=False)
    if control == code or code in control.parents:
        raise ArsError('control root must be outside the code repository')
    for name in ('objects', 'events', 'manifests', 'receipts', 'snapshots', 'runtime'):
        (control / name).mkdir(parents=True, exist_ok=True)
    return control
```

Writer lock uses exclusive creation and never auto-breaks a stale lock:

```python
# research_system/store/lock.py
import json
import os
from pathlib import Path

from research_system.errors import ConflictError


class WriterLock:
    def __init__(self, path: Path, identity: dict[str, str]):
        self.path = path
        self.identity = identity

    def __enter__(self):
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ConflictError(f'writer lock exists: {self.path}') from exc
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(self.identity, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        return self

    def __exit__(self, exc_type, exc, traceback):
        recorded = json.loads(self.path.read_text(encoding='utf-8'))
        if recorded != self.identity:
            raise ConflictError('writer lock ownership changed while held')
        self.path.unlink()
        return False
```

`objects.py` refuses overwrite unless bytes are identical. `ledger.py` writes the complete batch to `runtime/`, fsyncs, and uses `os.replace` exactly once into the date/position path. Batch and event hashes use `canonical_bytes` plus SHA-256; global position, previous-event hash, batch ID, and complete write set are mandatory.

- [ ] **Step 4: Run storage tests**

Run: `uv run pytest tests/research_system/unit/test_store.py -q --no-cov`

Expected: every root/lock/object/atomicity/hash-chain test passes.

- [ ] **Step 5: Commit storage foundation**

Commit subject: `[PIPELINE] P00: add ARS external single-writer store`.

## Task 4: Implement command validation, receipts, and reducers

- [ ] **Step 1: Write failing S-001/S-002/F-001/F-002 tests**

```python
import pytest

from research_system.errors import ConflictError
from tests.research_system.factories import (
    claim_dispatch_command, control_plane, create_task_command,
)


def test_identical_retry_returns_original_receipt_and_one_batch(tmp_path):
    harness = control_plane(tmp_path)
    command = create_task_command('cmd_' + '4' * 32, 'same', 'tsk_' + '5' * 32, {'title': 'A'})
    assert harness.service.submit(command) == harness.service.submit(command)
    assert len(tuple(harness.ledger.iter_batches())) == 1


def test_same_idempotency_key_with_changed_payload_conflicts(tmp_path):
    harness = control_plane(tmp_path)
    first = create_task_command('cmd_' + '6' * 32, 'same', 'tsk_' + '7' * 32, {'title': 'A'})
    changed = {**first, 'payload': {'title': 'B'}}
    harness.service.submit(first)
    with pytest.raises(ConflictError, match='idempotency'):
        harness.service.submit(changed)


def test_competing_claims_create_only_one_active_attempt(tmp_path):
    harness = control_plane(tmp_path)
    first = claim_dispatch_command('cmd_' + '8' * 32, 'actor-a', 'dsp_' + '9' * 32, expected_version=0)
    second = claim_dispatch_command('cmd_' + 'a' * 32, 'actor-b', 'dsp_' + '9' * 32, expected_version=0)
    winner = harness.service.submit(first)
    loser = harness.service.submit(second)
    assert {winner.status, loser.status} == {'accepted', 'conflict'}
    assert len(harness.replay().active_attempt_ids) == 1


def test_distinct_task_and_report_objects_cannot_overwrite(tmp_path):
    harness = control_plane(tmp_path)
    task = harness.objects.write('task', 'tsk_' + 'b' * 32, 1, {'kind': 'task'})
    report = harness.objects.write('report', 'rpt_' + 'c' * 32, 1, {'kind': 'report'})
    assert task != report
    assert task.read_bytes() != report.read_bytes()
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_command_service.py -q --no-cov`

Expected: missing command-service implementation.

- [ ] **Step 3: Implement immutable command/receipt models and service order**

```python
# research_system/command/models.py
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Command:
    envelope: dict[str, Any]

    @property
    def command_id(self) -> str:
        return str(self.envelope['command_id'])

    @property
    def idempotency_key(self) -> str:
        return str(self.envelope['idempotency_key'])


@dataclass(frozen=True)
class Receipt:
    status: str
    command_id: str
    payload_hash: str
    event_batch_id: str | None
    observed_stream_version: int
    reason_code: str | None = None
```

`CommandService.submit()` performs W2 section 8.2 checks in order, reads the original receipt before allocating a position, acquires the writer lock, rechecks the tail/stream version, writes objects, builds one complete event batch, atomically publishes it, then writes the immutable receipt. Rejected/conflict receipts never enter lifecycle events. `tests/research_system/factories.py` constructs the real ledger/object/receipt/service components under `tmp_path` and builds schema-valid commands; it must not add test-only branches to production classes.

Reducers are pure functions:

```python
from collections.abc import Callable

Reducer = Callable[[dict, dict], dict]


def reduce_task(state: dict, event: dict) -> dict:
    event_type = event['event_type']
    if event_type == 'TaskCreated':
        if state:
            raise ValueError('TaskCreated requires empty stream')
        return {'task_id': event['stream_id'], 'status': 'draft', 'version': 1}
    if event_type == 'ReadinessRequested' and state['status'] == 'draft':
        return {**state, 'status': 'readiness_pending', 'version': state['version'] + 1}
    raise ValueError(f'illegal task transition: {state.get("status")} -> {event_type}')
```

Extend the reducer table only for the command/event types required by the 37 P0 cases; unsupported types fail closed.

- [ ] **Step 4: Run unit and integration tests**

Run:

```powershell
uv run pytest tests/research_system/unit/test_command_service.py -q --no-cov
uv run pytest tests/research_system/integration/test_control_plane_fixtures.py -q --no-cov
```

Expected: S-001/S-002/F-001/F-002 tests pass with one global writer and no duplicate batch.

- [ ] **Step 5: Commit command service**

Commit subject: `[PIPELINE] P00: implement ARS command and receipt boundary`.

## Task 5: Implement replay, projections, and CLI

- [ ] **Step 1: Write failing S-008–S-012 tests**

Tests cover incomplete scope rejection, deterministic projection rebuild, unknown major schema fail-closed, writer crash before/after replace, and rejection of a mismatched store identity or worktree-local ledger.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_replay.py tests/research_system/integration/test_control_plane_fixtures.py -q --no-cov`

Expected: replay/CLI functions absent.

- [ ] **Step 3: Implement verified replay and CLI commands**

```python
# research_system/projection/replay.py
def replay(events: list[dict], supported_major: int = 1) -> dict:
    state = {'streams': {}, 'last_position': 0, 'last_hash': '0' * 64}
    for event in events:
        if int(event['schema_version'].split('.')[0]) != supported_major:
            raise IntegrityError(f'unsupported major at {event["global_position"]}')
        if event['global_position'] != state['last_position'] + 1:
            raise IntegrityError('event position gap or overlap')
        if event['previous_event_hash'] != state['last_hash']:
            raise IntegrityError('event hash-chain mismatch')
        state = apply_event(state, event)
    return state
```

`research_system.cli` exposes only explicit commands:

```text
ars store init --code-root PATH --control-root PATH --project-id ID
ars command submit --config PATH --command PATH
ars replay verify --control-root PATH
ars projection rebuild --control-root PATH --output PATH
```

`argparse` requires every path argument; no command derives the control root from cwd. `projection rebuild` writes to a temporary output and publishes only after full replay succeeds.

- [ ] **Step 4: Run complete work-package verification**

Run:

```powershell
uv run ruff check research_system tests/research_system
uv run pytest tests/research_system/unit/test_canonical_ids.py tests/research_system/unit/test_schema_registry.py tests/research_system/unit/test_store.py tests/research_system/unit/test_command_service.py tests/research_system/unit/test_replay.py tests/research_system/integration/test_control_plane_fixtures.py -q --no-cov
```

Expected: all WP1 tests pass; replay output is byte-stable; no repository control root exists.

- [ ] **Step 5: Commit WP1**

Commit subject: `[PIPELINE] P00: complete ARS control-plane replay slice`.

## Work-package acceptance

- [ ] S-001/S-002/S-006/S-008/S-009/S-010/S-011/S-012 are represented by named tests.
- [ ] F-001–F-005 known-bad and controlled paths are gradeable without active APM state.
- [ ] Atomic recovery yields zero or one committed batch.
- [ ] Unknown schemas, broken hashes, stale versions, and second writers fail closed.
- [ ] Deleting projections changes no canonical state.
- [ ] The control root is explicit and external in every CLI/test path.
- [ ] An independent provenance/software reviewer accepts the staged diff before WP2/WP3 consume these APIs.
