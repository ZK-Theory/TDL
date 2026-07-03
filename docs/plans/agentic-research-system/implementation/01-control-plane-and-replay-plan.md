# ARS P0 Work Package 1: Control Plane and Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the local single-writer command, event, receipt, replay, projection, and CLI foundation required by W1/W2.

**Architecture:** A Python package validates tracked JSON Schemas, writes immutable objects before one atomic JSONL event batch, and treats the batch rename as the commit point. Every invocation receives an explicit external control root; pure reducers rebuild disposable projections from the global position/hash chain.

**Tech Stack:** Python 3.13.5, dataclasses, pathlib, hashlib, json, secrets/time/uuid, tempfile/os.replace, PyYAML, jsonschema Draft 2020-12, argparse, pytest, ruff.

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
.research-system/config/id-kind-registry.yaml
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

## Task 1: Bootstrap package, canonical serialization, and owner-registered UUIDv7 IDs

- [ ] **Step 1: Write failing canonical/ID tests**

Create empty `tests/__init__.py`, `tests/research_system/__init__.py`, and `tests/research_system/factories.py`, then create:

```python
# tests/research_system/unit/test_canonical_ids.py
import uuid

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id, validate_id


def test_canonical_bytes_are_order_independent():
    left = canonical_bytes({'b': 2, 'a': 1})
    right = canonical_bytes({'a': 1, 'b': 2})
    assert left == b'{"a":1,"b":2}'
    assert left == right
    assert sha256_hex(left) == sha256_hex(right)


def test_ids_use_registered_owner_prefix_and_uuid7_body():
    command_id = new_id('command')
    assert command_id.startswith('cmd_')
    assert uuid.UUID(command_id.removeprefix('cmd_')).version == 7
    assert validate_id(command_id, 'command') == command_id


def test_wrong_or_unknown_kind_is_rejected():
    assurance_id = new_id('assurance_requirement')
    assert assurance_id.startswith('asr_')
    with pytest.raises(ValueError, match='expected command ID'):
        validate_id(assurance_id, 'command')
    with pytest.raises(ValueError, match='unknown ID kind'):
        new_id('arbitrary_prefix')
```

- [ ] **Step 2: Run the tests and confirm the package is absent**

Run: `uv run pytest tests/research_system/unit/test_canonical_ids.py -q --no-cov`

Expected: collection fails with `ModuleNotFoundError: No module named 'research_system'`.

- [ ] **Step 3: Add package metadata, the exact owner-kind registry, and minimal implementation**

Add to the existing `[tool.setuptools.packages.find]` table in `pyproject.toml` rather than creating a second table:

```toml
[project.scripts]
ars = "research_system.cli:main"

[tool.setuptools.packages.find]
include = ["financial_tda*", "poverty_tda*", "shared*", "trajectory_tda*", "research_system*"]
```

`.research-system/config/id-kind-registry.yaml` is the tracked authority. It contains every P0 field kind and exact owner prefix. Prefixes are field-scoped: the accepted W4 and W8 catalogues both use `rrq`, so callers must validate against the expected kind and schema rather than infer kind from prefix alone. No arbitrary-prefix constructor is exposed.

```yaml
schema_version: '1.0.0'
kinds:
  project: prj
  task: tsk
  command: cmd
  event_batch: txb
  event: evt
  dispatch: dsp
  attempt: att
  authority_grant: agr
  actor: act
  context: ctx
  assurance_requirement: asr
  route_request: rrq
  route_decision: rte
  routing_evidence_snapshot: res
  resource_request: rsq
  resource_grant: rgr
  execution_lease: els
  provider_command: pcmd
  provider_receipt: prcp
  trace: trc
  grader_result: grr
  evaluation_run: run
```

```python
# research_system/canonical.py
from __future__ import annotations

import hashlib
import json
from typing import Any


_MAX_SAFE_INTEGER = (1 << 53) - 1


def _validate_p0_canonical_value(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key.isascii():
                raise ValueError('P0 canonical JSON requires ASCII object keys')
            _validate_p0_canonical_value(item)
        return
    if isinstance(value, list):
        for item in value:
            _validate_p0_canonical_value(item)
        return
    if isinstance(value, float):
        raise ValueError('P0 canonical JSON rejects floating-point values')
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        if not -_MAX_SAFE_INTEGER <= value <= _MAX_SAFE_INTEGER:
            raise ValueError('P0 canonical JSON requires the safe integer range')
        return
    raise TypeError(f'unsupported P0 canonical JSON value: {type(value).__name__}')


def canonical_bytes(value: Any) -> bytes:
    _validate_p0_canonical_value(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    ).encode('utf-8')


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
```

`_validate_p0_canonical_value()` enforces the W2 P0 canonical subset before serialization: ASCII object keys, no floating-point values, and integers limited to the interoperable safe range. Gate 5 must adopt or verify full RFC 8785 behavior before cross-implementation or external-store interchange broadens that domain.

```python
# research_system/ids.py
from __future__ import annotations

import secrets
import time
import uuid
from collections.abc import Mapping


def _uuid7(now_ms: int | None = None) -> uuid.UUID:
    timestamp_ms = time.time_ns() // 1_000_000 if now_ms is None else now_ms
    if not 0 <= timestamp_ms < 1 << 48:
        raise ValueError('UUIDv7 timestamp is outside 48-bit range')
    value = (
        (timestamp_ms << 80)
        | (0x7 << 76)
        | (secrets.randbits(12) << 64)
        | (0b10 << 62)
        | secrets.randbits(62)
    )
    return uuid.UUID(int=value)


class IdRegistry:
    def __init__(self, kind_prefixes: Mapping[str, str]):
        self._kind_prefixes = dict(kind_prefixes)

    def new(self, kind: str) -> str:
        try:
            prefix = self._kind_prefixes[kind]
        except KeyError as exc:
            raise ValueError(f'unknown ID kind: {kind}') from exc
        return f'{prefix}_{_uuid7()}'

    def validate(self, value: str, kind: str) -> str:
        try:
            prefix = self._kind_prefixes[kind]
        except KeyError as exc:
            raise ValueError(f'unknown ID kind: {kind}') from exc
        marker = f'{prefix}_'
        if not value.startswith(marker):
            raise ValueError(f'expected {kind} ID with {marker} prefix')
        try:
            body = uuid.UUID(value.removeprefix(marker))
        except ValueError as exc:
            raise ValueError(f'expected {kind} ID with UUID body') from exc
        if body.version != 7 or body.variant != uuid.RFC_4122:
            raise ValueError(f'expected {kind} ID with UUIDv7 body')
        return value
```

`new_id()` and `validate_id()` are thin module-level delegates to one registry loaded from `id-kind-registry.yaml`. Loading fails on an unknown owner field, malformed prefix, duplicate kind, or a plan/schema kind missing from the registry. A prefix shared by two accepted field kinds is allowed only because validation always receives the expected field kind.

Create empty package `__init__.py` files and typed exceptions in `research_system/errors.py`.

- [ ] **Step 4: Run targeted tests and lint**

Run:

```powershell
uv run pytest tests/research_system/unit/test_canonical_ids.py -q --no-cov
uv run ruff check research_system tests/__init__.py tests/research_system/__init__.py tests/research_system/factories.py tests/research_system/unit/test_canonical_ids.py
```

Expected: 3 tests pass; ruff exits 0.

- [ ] **Step 5: Commit the bootstrap**

Stage only `pyproject.toml`, `research_system`, `.research-system/config/id-kind-registry.yaml`, and the named tests. Use subject `[PIPELINE] P00: scaffold ARS foundation package` in a task-specific message file and commit with `git commit -F`.
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

Every schema file must declare `$schema`, `$id`, `type: object`, `required`, `properties`, and `additionalProperties: false`. In WP1, command/event/receipt schemas are enforced or emission-tested. `task.schema.json` freezes the W2 status vocabulary, while full Task and authority-grant object validation is deferred to the package that first persists those complete records. Implement:

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
project_template_alias: ars-foundation-p0
project_id: null
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


def require_external_control_root(code_roots: list[Path], control_root: Path) -> Path:
    if not code_roots:
        raise ArsError('registered code roots required')
    controls_parent = control_root.parent.resolve(strict=True)
    control = (controls_parent / control_root.name).resolve(strict=False)
    codes = [root.resolve(strict=True) for root in code_roots]
    for code in codes:
        if control == code or code in control.parents or control in code.parents:
            raise ArsError('control root must be disjoint from every code root')
    for name in ('objects', 'events', 'manifests', 'receipts', 'snapshots', 'runtime'):
        (control / name).mkdir(parents=True, exist_ok=True)
    return control
```

The CLI boundary obtains the complete code-root set from `git worktree list --porcelain`, adds the live main root, rejects malformed or missing registrations, resolves every path through Windows symlink/junction/reparse targets, and passes that immutable set to `require_external_control_root()`. The unit test above attacks a resolved reparse-parent escape; an integration test creates two registered worktrees and verifies both ancestor and descendant overlap rejection.

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

`CommandService.submit()` implements the WP1 subset of W2 section 8.2: envelope schema, canonical-history integrity, global command-ID and idempotency checks, expected stream version, supported reducer preconditions, and batch integrity. It is not an authorization boundary. Referenced-object/hash validation, canonical owner/compatibility mode, actor/authority evaluation, and assurance/review/human gates (W2 steps 2, 3, 4, and 8) remain mandatory WP2/WP3 obligations before those command classes are enabled. The service rebuilds the accepted-command/idempotency index from committed events before allocating a position, returns or reconstructs the original accepted receipt when the committed command already exists, acquires the writer lock, rechecks the tail/stream version and accepted-command index, writes objects, builds one complete event batch, atomically publishes it, then writes the immutable receipt. A crash after batch rename and before receipt rename is recovered from committed event fields before any later mutation. Rejected/conflict receipts never enter lifecycle events. The first event in a command batch identifies the command target stream; acceptance uses the ledger's authoritative resulting version for that stream, and reconstruction derives the maximum version only among events for that same target stream. `tests/research_system/factories.py` constructs the real ledger/object/receipt/service components under `tmp_path` and builds schema-valid commands; it must not add test-only branches to production classes.

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

Tests cover incomplete scope rejection, deterministic projection rebuild, unknown major schema fail-closed, rejection of a mismatched store identity or worktree-local ledger, and fault injection after object write, batch temp fsync, event rename, ledger-tail visibility, receipt temp fsync, and receipt rename. The event-rename/receipt-rename case must reconstruct the byte-identical original receipt from committed events and leave exactly one batch.

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
- [ ] A crash after event rename and before receipt publication reconstructs the original accepted receipt from event-derived idempotency evidence.
- [ ] Unknown schemas, broken hashes, stale versions, and second writers fail closed.
- [ ] Deleting projections changes no canonical state.
- [ ] The control root is explicit and external in every CLI/test path.
- [ ] An independent provenance/software reviewer accepts the staged diff before WP2/WP3 consume these APIs.
