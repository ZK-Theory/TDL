# ARS P0 Work Package 3: Adapters and Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement provider-neutral policy projection, Claude/Codex adapter evidence, normalized commands/receipts, and proportional resource/lease/checkpoint/recovery controls.

**Architecture:** W7 compiles accepted canonical policy into provider-specific projections and delegates execution to an injected transport. W8 evaluates preliminary operational risk before routing, then issues a selected-route grant/lease; deterministic fake transports and fake clocks exercise all P0 paths without credentials, live providers, or long-running processes.

**Tech Stack:** Python 3.13.5, dataclasses, subprocess argument arrays, pathlib, hashlib, PyYAML/jsonschema, pytest fake transports/clocks.

---

## File map

**Create:**

```text
research_system/policy/__init__.py
research_system/policy/models.py
research_system/policy/compiler.py
research_system/adapters/__init__.py
research_system/adapters/base.py
research_system/adapters/fake.py
research_system/adapters/subprocess_transport.py
research_system/adapters/claude.py
research_system/adapters/codex.py
research_system/adapters/parity.py
research_system/operations/__init__.py
research_system/operations/models.py
research_system/operations/profiles.py
research_system/operations/resources.py
research_system/operations/leases.py
research_system/operations/checkpoints.py
research_system/operations/recovery.py
research_system/operations/coordinator.py
.research-system/schemas/adapters/canonical-policy-bundle.schema.json
.research-system/schemas/adapters/capability-manifest.schema.json
.research-system/schemas/adapters/provider-command.schema.json
.research-system/schemas/adapters/provider-receipt.schema.json
.research-system/schemas/adapters/parity-report.schema.json
.research-system/schemas/operations/resource-request.schema.json
.research-system/schemas/operations/resource-grant.schema.json
.research-system/schemas/operations/execution-lease.schema.json
.research-system/schemas/operations/checkpoint-manifest.schema.json
.research-system/schemas/operations/stop-record.schema.json
.research-system/schemas/operations/recovery-evidence.schema.json
.research-system/policies/canonical-policy.yaml
.research-system/policies/operational-profiles.yaml
.research-system/adapters/claude.yaml
.research-system/adapters/codex.yaml
tests/research_system/unit/test_policy_projection.py
tests/research_system/unit/test_adapter_parity.py
tests/research_system/unit/test_provider_receipts.py
tests/research_system/unit/test_resource_profiles.py
tests/research_system/unit/test_leases.py
tests/research_system/unit/test_checkpoints.py
tests/research_system/unit/test_recovery.py
tests/research_system/integration/test_adapter_operations_fixtures.py
```

## Task 1: Compile canonical policy and semantic parity

- [ ] **Step 1: Write failing F-020 parity tests**

```python
from dataclasses import dataclass

from research_system.adapters.parity import build_parity_report
from research_system.policy.compiler import compile_projection, projection_disposition
from research_system.policy.models import CanonicalPolicyBundle, Control


@dataclass(frozen=True)
class _Manifest:
    provider: str
    dispositions: dict[str, str]

    def disposition(self, control_id):
        return self.dispositions.get(control_id, 'unsupported')


def _bundle():
    control = Control('no-shell', 'execution_boundary', True, 'block')
    return CanonicalPolicyBundle('cpb_' + '1' * 32, 'r1', 'a' * 64, (control,))


def test_critical_control_missing_from_codex_blocks_parity():
    report = build_parity_report(_bundle(), [_Manifest('codex', {})])
    assert report == {
        'rows': [{'control_id': 'no-shell', 'providers': {'codex': 'unsupported'}}],
        'blocking_controls': ['no-shell'], 'passed': False,
    }


def test_missing_required_provider_cannot_pass_parity():
    report = build_parity_report(
        _bundle(), [_Manifest('claude', {'no-shell': 'supported'})]
    )
    assert report['passed'] is False
    assert report['rows'][0]['providers']['codex'] == 'unsupported'


def test_richer_destination_is_not_overwritten_by_poorer_projection():
    existing = {'owner': 'human', 'semantic_controls': ['no-shell', 'extra-review']}
    assert projection_disposition(existing, _bundle()) == 'divergent'


def test_byte_difference_with_equivalent_semantics_can_pass():
    manifests = [_Manifest('codex', {'no-shell': 'supported'}), _Manifest('claude', {'no-shell': 'supported'})]
    assert build_parity_report(_bundle(), manifests)['passed'] is True


def test_generated_projection_binds_source_bundle_hash():
    projection = compile_projection(_bundle(), _Manifest('codex', {'no-shell': 'supported'}))
    assert projection['metadata']['canonical_policy_bundle_hash'] == 'a' * 64
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_policy_projection.py tests/research_system/unit/test_adapter_parity.py -q --no-cov`

Expected: policy/adapter modules absent.

- [ ] **Step 3: Implement policy and parity models**

```python
# research_system/policy/models.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Control:
    control_id: str
    semantic_class: str
    critical: bool
    failure_mode: str


@dataclass(frozen=True)
class CanonicalPolicyBundle:
    canonical_policy_bundle_id: str
    revision: str
    content_hash: str
    controls: tuple[Control, ...]
```

```python
# research_system/adapters/parity.py
def build_parity_report(bundle, manifests, required_providers=('claude', 'codex')):
    by_provider = {}
    for manifest in manifests:
        if manifest.provider in by_provider:
            raise ValueError(f'duplicate provider manifest: {manifest.provider}')
        by_provider[manifest.provider] = manifest
    rows = []
    blocking = []
    for control in bundle.controls:
        dispositions = {
            provider: (
                by_provider[provider].disposition(control.control_id)
                if provider in by_provider else 'unsupported'
            )
            for provider in sorted(required_providers)
        }
        rows.append({'control_id': control.control_id, 'providers': dispositions})
        if control.critical and any(
            value in {'unsupported', 'divergent', 'diagnostic_only'}
            for value in dispositions.values()
        ):
            blocking.append(control.control_id)
    return {'rows': rows, 'blocking_controls': sorted(blocking), 'passed': not blocking}
```

`compiler.py` implements `compile_projection(bundle, manifest) -> dict` with generated-ownership metadata, the canonical bundle hash, generator version, and sorted semantic controls. `projection_disposition(existing, bundle)` returns `replaceable` only when the generated marker and bundle lineage match and replacement preserves a semantic superset. Hand-edited or richer projections return `divergent`; the writer refuses to overwrite them.

- [ ] **Step 4: Run parity tests**

Run: `uv run pytest tests/research_system/unit/test_policy_projection.py tests/research_system/unit/test_adapter_parity.py -q --no-cov`

Expected: critical semantic gaps block; byte identity is neither necessary nor sufficient.

- [ ] **Step 5: Commit policy/parity slice**

Commit subject: `[PIPELINE] P00: add ARS canonical policy parity`.

## Task 2: Implement normalized provider commands and fake transport

- [ ] **Step 1: Write failing receipt/idempotency tests**

Tests cover exact command revision binding, incomplete receipt, timeout/uncertain completion, duplicate response, cancellation, wrapper-token accounting, S-013 unauthorized adapter command, and proof that raw stdout/stderr/full transcripts never enter normalized commands, receipts, events, or traces.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_provider_receipts.py tests/research_system/integration/test_adapter_operations_fixtures.py -k adapter -q --no-cov`

Expected: command/transport classes absent.

- [ ] **Step 3: Implement transport protocol and normalized receipts**

```python
# research_system/adapters/base.py
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TransportResult:
    status: str
    stdout: str
    stderr: str
    provider_request_id: str | None
    exit_code: int | None


class Transport(Protocol):
    def invoke(self, argv: list[str], stdin: str, timeout_s: float) -> TransportResult: ...
```

```python
# research_system/adapters/subprocess_transport.py
import subprocess

from research_system.adapters.base import TransportResult


class SubprocessTransport:
    def invoke(self, argv, stdin, timeout_s):
        try:
            completed = subprocess.run(
                argv, input=stdin, text=True, capture_output=True,
                timeout=timeout_s, check=False, shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return TransportResult(
                status='timed_out', stdout=exc.stdout or '', stderr=str(exc),
                provider_request_id=None, exit_code=124,
            )
        return TransportResult(
            status='terminal', stdout=completed.stdout, stderr=completed.stderr,
            provider_request_id=None, exit_code=completed.returncode,
        )
```

`FakeTransport` returns scripted acknowledgements, terminal outputs, timeouts, duplicates, and cancellation results. Unit/integration tests use only `FakeTransport`.

Provider manifests define argument arrays, not shell strings:

```yaml
# .research-system/adapters/codex.yaml
provider: codex
operation: request_model_work
argv: [codex, exec, --ephemeral, --ignore-user-config, --json, -]
terminal_receipt: jsonl
live_enabled: false
```

```yaml
# .research-system/adapters/claude.yaml
provider: claude
operation: request_model_work
argv: [claude, --print, --output-format, json]
terminal_receipt: json
live_enabled: false
windows_requires_git_bash: true
```

Live enablement is a reviewed local override, never committed. A transport timeout yields `timed_out` and normalizes to an `uncertain` completion requiring reconciliation; it must not be collapsed into a definite blocked non-completion. A missing executable, unsupported flag, unclassified wrapper, unknown delivered hash, or incomplete provider identity yields a blocked/incomplete receipt.

TransportResult.stdout and .stderr are ephemeral boundary values. The receipt normalizer extracts only registered semantic fields, hashes and redacted summaries, then discards raw content. Any policy-authorized retained excerpt is written through the external evidence-store contract with a retention class; full transcripts remain prohibited.

- [ ] **Step 4: Verify receipt and wrapper accounting**

Run:

```powershell
uv run pytest tests/research_system/unit/test_provider_receipts.py -q --no-cov
uv run pytest tests/research_system/integration/test_adapter_operations_fixtures.py -k 'f020 or s013 or wrapper' -q --no-cov
```

Expected: fake receipts are complete and deterministic; incomplete/unauthorized paths cannot satisfy dispatch.

- [ ] **Step 5: Commit adapter boundary**

Commit subject: `[PIPELINE] P00: implement ARS provider command boundary`.

## Task 3: Implement preliminary risk and proportional resource profiles

- [ ] **Step 1: Write failing profile/resource tests**

```python
from types import SimpleNamespace

import pytest

from research_system.operations.profiles import (
    OperationalProfile, ResourceClaim, has_resource_conflict, operational_risk_floor,
    profile_evidence_dispositions, validate_profile_request,
)


def _trivial():
    return OperationalProfile('trivial-v1', 120, False, False, False, False, False)


def test_trivial_profile_requires_typed_grant_and_terminal_closure():
    grant = validate_profile_request(_trivial(), expected_runtime_s=60, child_process=False, durable_writer=False)
    assert grant == {'profile_id': 'trivial-v1', 'closure': 'terminal_receipt'}


def test_trivial_profile_marks_benchmark_checkpoint_heartbeat_not_applicable():
    assert profile_evidence_dispositions(_trivial()) == {
        'benchmark': 'not_applicable', 'checkpoint': 'not_applicable', 'heartbeat': 'not_applicable',
    }


def test_trivial_profile_cannot_spawn_process_or_open_durable_writer():
    with pytest.raises(ValueError, match='profile_envelope_exceeded'):
        validate_profile_request(_trivial(), expected_runtime_s=60, child_process=True, durable_writer=True)


def test_operational_floor_raises_route_risk_before_selection():
    request = SimpleNamespace(
        restricted_data=True, external_write=False, expected_runtime_s=60,
        exclusive_resources=(), checkpoint_uncertain=False, stop_confirmation_uncertain=False,
    )
    assert operational_risk_floor(request) == 'R3'


@pytest.mark.parametrize(
    ('requested', 'held', 'capacity', 'expected'),
    [
        (ResourceClaim('exclusive', 1), ResourceClaim('exclusive', 1), 1, True),
        (ResourceClaim('exclusive', 1), ResourceClaim('read_shared', 1), 1, True),
        (ResourceClaim('read_shared', 1), ResourceClaim('exclusive', 1), 1, True),
        (ResourceClaim('read_shared', 1), ResourceClaim('read_shared', 1), 1, False),
        (ResourceClaim('capacity_shared', 4), ResourceClaim('capacity_shared', 5), 10, False),
        (ResourceClaim('capacity_shared', 6), ResourceClaim('capacity_shared', 5), 10, True),
        (ResourceClaim('read_shared', 1), ResourceClaim('capacity_shared', 1), 10, True),
        (ResourceClaim('capacity_shared', 1), ResourceClaim('read_shared', 1), 10, True),
    ],
)
def test_resource_conflict_matrix_is_symmetric(requested, held, capacity, expected):
    assert has_resource_conflict(
        {'gpu:0': requested}, {'gpu:0': held}, {'gpu:0': capacity}
    ) is expected
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_resource_profiles.py -q --no-cov`

Expected: operations policy absent.

- [ ] **Step 3: Implement profiles and risk floor**

```python
# research_system/operations/profiles.py
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceClaim:
    mode: str
    units: int

    def __post_init__(self):
        if self.mode not in {'exclusive', 'capacity_shared', 'read_shared'}:
            raise ValueError('unknown_resource_mode')
        if self.units <= 0:
            raise ValueError('resource_units_must_be_positive')


@dataclass(frozen=True)
class OperationalProfile:
    profile_id: str
    max_runtime_s: int
    allow_child_process: bool
    allow_durable_writer: bool
    require_benchmark: bool
    require_periodic_heartbeat: bool
    require_checkpoint: bool


PROFILES = {
    'trivial': OperationalProfile('trivial-v1', 120, False, False, False, False, False),
    'bounded': OperationalProfile('bounded-v1', 3600, True, True, False, True, False),
    'long_running': OperationalProfile('long-running-v1', 172800, True, True, True, True, True),
}
```

Values are policy inputs for the P0 synthetic foundation, not universal constants. `.research-system/policies/operational-profiles.yaml` is authoritative and versioned; tests load it and assert the dataclass values.

```python
RISK_ORDER = {'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3}


def max_risk(risks):
    return max(risks, key=RISK_ORDER.__getitem__)


def validate_profile_request(profile, *, expected_runtime_s, child_process, durable_writer):
    if (
        expected_runtime_s > profile.max_runtime_s
        or child_process and not profile.allow_child_process
        or durable_writer and not profile.allow_durable_writer
    ):
        raise ValueError('profile_envelope_exceeded')
    return {'profile_id': profile.profile_id, 'closure': 'terminal_receipt'}


def profile_evidence_dispositions(profile):
    return {
        'benchmark': 'required' if profile.require_benchmark else 'not_applicable',
        'checkpoint': 'required' if profile.require_checkpoint else 'not_applicable',
        'heartbeat': 'required' if profile.require_periodic_heartbeat else 'not_applicable',
    }


def operational_risk_floor(request):
    raises = []
    if request.restricted_data or request.external_write:
        raises.append('R3')
    if request.expected_runtime_s > 3600 or request.exclusive_resources:
        raises.append('R2')
    if request.checkpoint_uncertain or request.stop_confirmation_uncertain:
        raises.append('R3')
    return max_risk(['R0', *raises])


def has_resource_conflict(requested, held, capacities):
    for key, requested_claim in requested.items():
        held_claim = held.get(key)
        if held_claim is None:
            continue
        modes = {requested_claim.mode, held_claim.mode}
        if 'exclusive' in modes:
            return True
        if modes == {'read_shared'}:
            continue
        if modes == {'capacity_shared'}:
            capacity = capacities.get(key)
            if capacity is None:
                return True
            if requested_claim.units + held_claim.units > capacity:
                return True
            continue
        return True
    return False
```

Resource conflict evaluation operates on typed keys and all three W8 modes. `capacity_shared` claims are compatible only when their summed units fit the registered capacity; mixed `read_shared`/`capacity_shared` claims fail closed unless a later accepted compatibility rule says otherwise. The predicate returns `resource_conflict`; it never silently reduces requested resources or widens a grant.

- [ ] **Step 4: Run profile tests**

Run: `uv run pytest tests/research_system/unit/test_resource_profiles.py -q --no-cov`

Expected: trivial work remains lightweight but explicit; exceeding its envelope requires a new request.

- [ ] **Step 5: Commit proportional profiles**

Commit subject: `[PIPELINE] P00: add proportional ARS resource profiles`.

## Task 4: Implement leases, checkpoints, stop, and recovery

- [ ] **Step 1: Write failing F-007–F-010/S-003/S-004 tests**

Tests cover hidden prerequisites, invalid worker projection, hard runtime stop, unauthorized operational expansion, lease expiry/late artefact, compatible resume epoch, and incompatible checkpoint rejection.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_leases.py tests/research_system/unit/test_checkpoints.py tests/research_system/unit/test_recovery.py -q --no-cov`

Expected: operational state functions absent.

- [ ] **Step 3: Implement deterministic predicates**

```python
# research_system/operations/checkpoints.py
CHECKPOINT_KEYS = (
    'design_hash', 'code_hash', 'environment_hash', 'input_hashes',
    'representation_hash', 'parameters_hash', 'rng_algorithm',
    'rng_state_hash', 'completed_work_units', 'payload_hash',
)


def checkpoint_compatibility(checkpoint, request):
    mismatches = [
        key for key in CHECKPOINT_KEYS
        if checkpoint.get(key) != request.get(key)
        and key != 'completed_work_units'
    ]
    if mismatches:
        return {'verdict': 'incompatible', 'mismatches': sorted(mismatches)}
    if not checkpoint.get('payload_hash'):
        return {'verdict': 'unable_to_determine', 'mismatches': ['payload_hash']}
    return {'verdict': 'compatible', 'mismatches': []}
```

```python
# research_system/operations/leases.py
def heartbeat_disposition(profile, heartbeat_policy):
    if profile == 'trivial':
        if heartbeat_policy != {'status': 'not_applicable', 'reason': 'terminal_receipt_closes_lease'}:
            raise ValueError('invalid trivial heartbeat disposition')
        return heartbeat_policy
    if not heartbeat_policy.get('cadence_s') or not heartbeat_policy.get('grace_s'):
        raise ValueError('periodic heartbeat policy required')
    return heartbeat_policy
```

Stop confirmation requires provider, process/children, output-writer, and checkpoint dispositions. Any unknown remains `stop_uncertain`. Resume creates a new execution epoch and revalidates W3–W8 currency.

- [ ] **Step 4: Run operational fixture tests**

Run:

```powershell
uv run pytest tests/research_system/unit/test_leases.py tests/research_system/unit/test_checkpoints.py tests/research_system/unit/test_recovery.py -q --no-cov
uv run pytest tests/research_system/integration/test_adapter_operations_fixtures.py -k 'f007 or f008 or f009 or f010 or s003 or s004' -q --no-cov
```

Expected: guardrails stop/Partial correctly; no final science is emitted by W8.

- [ ] **Step 5: Commit operations**

Commit subject: `[PIPELINE] P00: implement ARS lease checkpoint recovery`.

## Task 5: Integrate selected-route revalidation and issue

- [ ] **Step 1: Write a failing Gate 3 ordering test**

The test proves preliminary W7/W8 evidence precedes W4, selected-route W7 revalidation precedes W8 grant/lease, grant/lease precedes provider issue, and terminal receipt/operational evidence precede W6 trace completion.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/integration/test_adapter_operations_fixtures.py -k two_stage -q --no-cov`

Expected: integrated issue coordinator absent.

- [ ] **Step 3: Implement issue coordinator**

```python
# research_system/operations/coordinator.py
from typing import Protocol


class AdapterIssuePort(Protocol):
    def load_evidence(self, evidence_id: str, content_hash: str): ...
    def revalidate(self, route, context, provider_evidence): ...
    def build_command(self, prepared, grant, lease, revalidated): ...
    def record_issue_command(self, provider_command): ...
    def issue(self, provider_command, issued_receipt): ...


class OperationsIssuePort(Protocol):
    def build_request(self, prepared, revalidated): ...
    def request_grant_command(self, request): ...
    def load_grant(self, grant_receipt): ...
    def claim_lease_command(self, grant, attempt_id: str): ...
    def load_lease(self, lease_receipt): ...
    def record_provider_receipt_command(self, lease, provider_receipt): ...


class CommandServicePort(Protocol):
    def submit(self, command): ...


def issue_prepared_dispatch(
    prepared, adapter: AdapterIssuePort,
    operations: OperationsIssuePort, command_service: CommandServicePort,
):
    provider_evidence = adapter.load_evidence(
        prepared.provider_evidence_id, prepared.provider_evidence_hash
    )
    revalidated = adapter.revalidate(
        prepared.route, prepared.context, provider_evidence
    )
    request = operations.build_request(prepared, revalidated)
    grant_receipt = command_service.submit(operations.request_grant_command(request))
    grant = operations.load_grant(grant_receipt)
    lease_receipt = command_service.submit(
        operations.claim_lease_command(grant, prepared.attempt_id)
    )
    lease = operations.load_lease(lease_receipt)
    provider_command = adapter.build_command(prepared, grant, lease, revalidated)
    issued_receipt = command_service.submit(adapter.record_issue_command(provider_command))
    provider_receipt = adapter.issue(provider_command, issued_receipt)
    terminal_receipt = command_service.submit(
        operations.record_provider_receipt_command(lease, provider_receipt)
    )
    return provider_command, provider_receipt, terminal_receipt
```

The three protocols above are the owned cross-package signatures; contract tests instantiate strict fakes that fail on any extra method or mismatched argument. Every grant, lease, issue, and terminal transition is a typed WP1 command. Adapter/operations helpers construct commands or read committed objects; they never write events directly. Revalidation, evidence hashes, expiry, and attempt identity must match the frozen `PreparedDispatch`. Any failure returns a typed block/Partial path with no provider issue.

- [ ] **Step 4: Run complete WP3 verification**

Run:

```powershell
uv run ruff check research_system/policy research_system/adapters research_system/operations tests/research_system
uv run pytest tests/research_system/unit/test_policy_projection.py tests/research_system/unit/test_adapter_parity.py tests/research_system/unit/test_provider_receipts.py tests/research_system/unit/test_resource_profiles.py tests/research_system/unit/test_leases.py tests/research_system/unit/test_checkpoints.py tests/research_system/unit/test_recovery.py tests/research_system/integration/test_adapter_operations_fixtures.py -q --no-cov
```

Expected: all WP3 tests pass with fake transport; no live provider or long-running process is invoked.

- [ ] **Step 5: Commit WP3**

Commit subject: `[PIPELINE] P00: complete ARS adapter operations slice`.

## Work-package acceptance

- [ ] F-020 parity is semantic and non-compensable.
- [ ] F-007–F-009 guardrails count hidden work and stop without scientific claims.
- [ ] F-010 W8 coverage is limited to unauthorized operational expansion.
- [ ] F-032 reroutes through W4 under original requirements.
- [ ] F-034 denies missing permission/root/sensitivity and unsafe decomposition.
- [ ] S-003/S-004 preserve late artefact and resume lineage.
- [ ] S-013 adapter rejection occurs before canonical event publication.
- [ ] Live Claude/Codex smoke remains disabled until a separate bounded approval.
- [ ] Independent security/operations/parity review accepts WP3 before provider enablement.
