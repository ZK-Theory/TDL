# ARS P0 Work Package 4: Evaluation and Fixture Materialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement W6 evaluation contracts and materialize/calibrate the exact 37-case P0 dependency closure against the narrow foundation.

**Architecture:** Immutable fixture definitions drive a deterministic runner over fake/reference and candidate systems. Normalized traces collect W2/W4/W7/W8 evidence; independent graders emit non-compensable results; coverage and release decisions fail closed on any required failure, missing evidence, unavailable independence, or fixture defect.

**Tech Stack:** Python 3.13.5, dataclasses, pathlib, JSON/YAML, jsonschema, pytest, deterministic fake clocks/transports, SHA-256.

---

## File map

**Create:**

```text
research_system/evals/__init__.py
research_system/evals/models.py
research_system/evals/errors.py
research_system/evals/trace.py
research_system/evals/graders.py
research_system/evals/runner.py
research_system/evals/coverage.py
research_system/evals/release.py
research_system/evals/retention.py
research_system/evals/calibration.py
research_system/evals/scenarios.py
.research-system/schemas/evals/fixture-definition.schema.json
.research-system/schemas/evals/trace-envelope.schema.json
.research-system/schemas/evals/grader-result.schema.json
.research-system/schemas/evals/evaluation-run.schema.json
.research-system/schemas/evals/coverage-manifest.schema.json
.research-system/schemas/evals/release-gate-decision.schema.json
.research-system/schemas/evals/evidence-store-registry.schema.json
.research-system/schemas/evals/deletion-verification-manifest.schema.json
.research-system/evals/catalogue.yaml
.research-system/evals/p0-coverage.yaml
.research-system/evals/threshold-policies.yaml
.research-system/evals/p0-calibration-policy.yaml
.research-system/evals/p0-variant-matrix.yaml
.research-system/evals/retention-policy.yaml
.research-system/evals/fixtures/{case_id}/fixture.yaml for every ID in P0_CASES
.research-system/evals/fixtures/{case_id}/README.md for every ID in P0_CASES
.research-system/evals/fixtures/{case_id}/input/ for every ID in P0_CASES
.research-system/evals/fixtures/{case_id}/expected/ for every ID in P0_CASES
.research-system/evals/fixtures/{case_id}/graders/ for every ID in P0_CASES
tools/ars/materialize_p0_fixtures.py
tests/research_system/unit/test_eval_models.py
tests/research_system/unit/test_trace.py
tests/research_system/unit/test_graders.py
tests/research_system/unit/test_coverage.py
tests/research_system/unit/test_release_gate.py
tests/research_system/unit/test_retention.py
tests/research_system/integration/test_p0_control_fixtures.py
tests/research_system/integration/test_p0_context_routing_fixtures.py
tests/research_system/integration/test_p0_adapter_operations_fixtures.py
tests/research_system/integration/test_p0_scientific_fixtures.py
tests/research_system/integration/test_gate3_scenarios.py
```

**Modify:** `research_system/cli.py`, `research_system/command/reducers.py`.

The exact case IDs are:

```text
F-001 F-002 F-003 F-004 F-005
F-007 F-008 F-009 F-010 F-011 F-012 F-013 F-014
F-020 F-021 F-022 F-025 F-026 F-027 F-028
F-031 F-032 F-033 F-034 F-035 F-036
S-001 S-002 S-003 S-004 S-006 S-008 S-009 S-010 S-011 S-012 S-013
```

## Task 1: Implement W6 evaluation models and schemas

- [ ] **Step 1: Write failing model/schema tests**

```python
import pytest

from research_system.evals.models import EvaluationRun, FixtureDefinition, GraderResult, TraceEnvelope


def _fixture(**changes):
    values = {
        'fixture_id': 'F-001', 'fixture_revision': 'r1', 'priority': 'P0',
        'gate_stage': 'p0_materialization', 'required_graders': ('state',),
        'threshold_policy_ids': ('tp-1',), 'source_manifest_hash': 'a' * 64,
        'required_evidence_classes': ('provider_receipt',),
    }
    values.update(changes)
    return FixtureDefinition(**values)


def test_fixture_requires_priority_and_gate_stage_separately():
    fixture = _fixture(priority='P1', gate_stage='p0_materialization')
    assert (fixture.priority, fixture.gate_stage) == ('P1', 'p0_materialization')


def test_gate_stage_accepts_only_w6_closed_enum():
    with pytest.raises(ValueError, match='invalid gate_stage'):
        _fixture(gate_stage='implementation_convenience')


def test_trace_requires_terminal_receipt_or_missing_evidence_record():
    trace = TraceEnvelope('trc_' + '1' * 32, (), ({'command_id': 'cmd-1'},))
    with pytest.raises(ValueError, match='terminal_or_missing_evidence_required'):
        trace.validate_terminal_evidence()


def test_grader_verdict_is_closed_enum():
    with pytest.raises(ValueError, match='invalid verdict'):
        GraderResult('grr_' + '2' * 32, 'run-1', 'F-001', 'r1', 'state', 'D', 'v1', 'maybe', True, True, 'b' * 64, 'c' * 64, ())


def test_evaluation_retry_gets_new_run_identity():
    run = EvaluationRun('run_' + '3' * 32, 'F-001', 1)
    retry = run.retry('run_' + '4' * 32)
    assert retry.evaluation_run_id != run.evaluation_run_id
    assert retry.attempt_number == 2
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_eval_models.py tests/research_system/unit/test_trace.py -q --no-cov`

Expected: eval models absent.

- [ ] **Step 3: Implement immutable contracts**

```python
# research_system/evals/models.py
from dataclasses import dataclass

GATE_STAGES = frozenset({
    'interface_review', 'p0_materialization',
    'foundation_release', 'pilot_promotion',
})
VERDICTS = frozenset({'pass', 'fail', 'unable_to_grade', 'fixture_error'})


@dataclass(frozen=True)
class FixtureDefinition:
    fixture_id: str
    fixture_revision: str
    priority: str
    gate_stage: str
    required_graders: tuple[str, ...]
    threshold_policy_ids: tuple[str, ...]
    source_manifest_hash: str
    required_evidence_classes: tuple[str, ...]

    def __post_init__(self):
        if self.priority not in {'P0', 'P1'}:
            raise ValueError('invalid priority')
        if self.gate_stage not in GATE_STAGES:
            raise ValueError('invalid gate_stage')


@dataclass(frozen=True)
class TraceEnvelope:
    trace_id: str
    items: tuple[dict, ...]
    issued_commands: tuple[dict, ...]

    def validate_terminal_evidence(self):
        incomplete = [
            item['command_id'] for item in self.issued_commands
            if not item.get('terminal_ref') and not item.get('missing_evidence_ref')
        ]
        if incomplete:
            raise ValueError('terminal_or_missing_evidence_required')


@dataclass(frozen=True)
class EvaluationRun:
    evaluation_run_id: str
    fixture_id: str
    attempt_number: int

    def retry(self, new_evaluation_run_id):
        if new_evaluation_run_id == self.evaluation_run_id:
            raise ValueError('retry requires new evaluation_run_id')
        return EvaluationRun(new_evaluation_run_id, self.fixture_id, self.attempt_number + 1)


@dataclass(frozen=True)
class GraderResult:
    grader_result_id: str
    evaluation_run_id: str
    fixture_id: str
    fixture_revision: str
    grader_id: str
    grader_class: str
    grader_version: str
    verdict: str
    critical: bool
    required: bool
    subject_hash: str
    trace_hash: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self):
        if self.verdict not in VERDICTS:
            raise ValueError('invalid verdict')
```

Implement `TraceEnvelope`, `EvaluationRun`, `CoverageManifest`, and `ReleaseGateDecision` with the exact W6 section 19–25 fields. Schemas use singular owner-defined IDs (`trace_id`, `grader_result_id`) and reject the retired Gate 3 aliases.

- [ ] **Step 4: Run model/schema tests**

Run: `uv run pytest tests/research_system/unit/test_eval_models.py tests/research_system/unit/test_trace.py -q --no-cov`

Expected: closed enums and identity rules pass.

- [ ] **Step 5: Commit eval contracts**

Commit subject: `[PIPELINE] P00: add ARS evaluation contracts`.

## Task 2: Implement trace completeness and exact required-grader closure

- [ ] **Step 1: Write failing grader and pass-on-omission tests**

```python
from types import SimpleNamespace

import pytest

from research_system.evals.errors import UnableToGrade
from research_system.evals.models import GraderResult, TraceEnvelope
from research_system.evals.release import decide_release
from research_system.evals.trace import assert_trace_complete


STATE_KEY = ('F-001', 'r1', 'state', 'D', 'v1')
RESEARCH_KEY = ('F-001', 'r1', 'research', 'R', 'v1')


def _coverage(*keys):
    return SimpleNamespace(required_result_keys=keys)


def _result(key, verdict='pass'):
    fixture_id, fixture_revision, grader_id, grader_class, grader_version = key
    return GraderResult(
        'grr_' + '5' * 32, 'run-1', fixture_id, fixture_revision,
        grader_id, grader_class, grader_version, verdict,
        True, True, 'a' * 64, 'b' * 64, (),
    )


def test_missing_provider_receipt_is_unable_to_grade_and_blocking():
    fixture = SimpleNamespace(required_evidence_classes=('provider_receipt',))
    with pytest.raises(UnableToGrade):
        assert_trace_complete(TraceEnvelope('trc-1', (), ()), fixture)


def test_missing_required_grader_blocks_instead_of_passing_present_result():
    decision = decide_release(
        _coverage(STATE_KEY, RESEARCH_KEY), [_result(STATE_KEY)]
    )
    assert decision['decision'] == 'blocked'
    assert decision['missing'] == [RESEARCH_KEY]


def test_stale_revision_duplicate_or_unexpected_result_blocks():
    stale = ('F-001', 'r0', 'state', 'D', 'v1')
    assert decide_release(_coverage(STATE_KEY), [_result(stale)])['decision'] == 'blocked'
    duplicate = _result(STATE_KEY)
    assert decide_release(_coverage(STATE_KEY), [duplicate, duplicate])['decision'] == 'blocked'
    assert decide_release(
        _coverage(STATE_KEY), [_result(STATE_KEY), _result(RESEARCH_KEY)]
    )['decision'] == 'blocked'


def test_fixture_defect_and_critical_fail_remain_noncompensable():
    assert decide_release(_coverage(STATE_KEY), [_result(STATE_KEY, 'fixture_error')])['decision'] == 'blocked'
    assert decide_release(_coverage(STATE_KEY), [_result(STATE_KEY, 'fail')])['decision'] == 'fail'
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_graders.py tests/research_system/unit/test_release_gate.py -q --no-cov`

Expected: grader/release functions absent or the pass-on-omission test exposes a false pass.

- [ ] **Step 3: Implement trace and release rules**

```python
# research_system/evals/release.py
from collections import Counter

BLOCKING = {'fail', 'unable_to_grade', 'fixture_error'}


def _result_key(result):
    return (
        result.fixture_id, result.fixture_revision, result.grader_id,
        result.grader_class, result.grader_version,
    )


def decide_release(coverage, results):
    required = set(coverage.required_result_keys)
    observed_keys = [_result_key(result) for result in results]
    counts = Counter(observed_keys)
    observed = set(observed_keys)
    missing = sorted(required - observed)
    unexpected = sorted(observed - required)
    duplicates = sorted(key for key, count in counts.items() if count != 1)
    incompatible = [
        result for result in results
        if not result.subject_hash or not result.trace_hash
    ]
    blocking = [
        result for result in results
        if result.required and result.verdict in BLOCKING
    ]
    if missing or unexpected or duplicates or incompatible:
        return {
            'decision': 'blocked', 'missing': missing,
            'unexpected': unexpected, 'duplicates': duplicates,
            'blocking': blocking + incompatible,
        }
    if blocking:
        decision = (
            'blocked' if any(
                result.verdict in {'unable_to_grade', 'fixture_error'}
                for result in blocking
            ) else 'fail'
        )
        return {
            'decision': decision, 'missing': [], 'unexpected': [],
            'duplicates': [], 'blocking': blocking,
        }
    return {
        'decision': 'pass', 'missing': [], 'unexpected': [],
        'duplicates': [], 'blocking': [],
    }
```

`CoverageManifest.required_result_keys` is derived from the exact selected fixture revisions and their required grader IDs/classes/versions. The evaluated producer cannot supply or narrow this set. The production implementation also verifies oracle, policy, threshold-policy, independence, subject, and trace hashes before a result joins `observed`.

- [ ] **Step 4: Run grader/release tests**

Run: `uv run pytest tests/research_system/unit/test_graders.py tests/research_system/unit/test_release_gate.py -q --no-cov`

Expected: empty, partial, stale, duplicate, unexpected, incompatible, failed, unable-to-grade, and fixture-error evidence sets all block or fail exactly; only exact required-set closure can pass.

- [ ] **Step 5: Commit runner primitives**

Commit subject: `[PIPELINE] P00: enforce ARS non-compensable grading`.

## Task 3: Implement retention policy and evidence-derived deletion verification

- [ ] **Step 1: Write failing retention and verifier tests**

```python
from pathlib import Path

import pytest

from research_system.evals.retention import (
    RULES, EvidenceStoreRegistry, require_retention_rule, verify_deletion,
)


def _registry(tmp_path):
    return EvidenceStoreRegistry(
        store_id='evs_' + '1' * 32, registry_hash='a' * 64,
        primary=tmp_path / 'primary', runtime=tmp_path / 'runtime',
        staging=tmp_path / 'staging', temp=tmp_path / 'temp',
        replicas=(tmp_path / 'replica',), permitted_consumers=('eval',),
    )


def test_r1_r2_windows_are_explicit_and_r2_uses_earlier_expiry():
    assert RULES[('R1', 'redacted_command_summary')].max_days == 180
    assert RULES[('R1', 'operational_measurement')].max_days == 365
    assert RULES[('R1', 'grader_explanation')].max_days == 365
    assert RULES[('R2', 'restricted_local_reference')].max_days == 90
    assert RULES[('R2', 'minimized_sensitive_excerpt')].max_days == 30
    assert all(rule.use_earlier_source_expiry for key, rule in RULES.items() if key[0] == 'R2')


def test_verifier_derives_locations_and_blocks_failed_replica(tmp_path):
    registry = EvidenceStoreRegistry(
        store_id='evs_' + '1' * 32, registry_hash='a' * 64,
        primary=tmp_path / 'primary', runtime=tmp_path / 'runtime',
        staging=tmp_path / 'staging', temp=tmp_path / 'temp',
        replicas=(tmp_path / 'replica',), permitted_consumers=('eval',),
    )
    inspected = []

    def inspect(path, evidence_hash):
        inspected.append(path)
        return path.name != 'replica'

    result = verify_deletion(
        evidence_id='evi_' + '2' * 32, evidence_hash='b' * 64,
        registry=registry, inspect_location=inspect,
        discover_replicas=lambda _: set(registry.replicas),
        canonical_payload_scan=lambda _: False,
        actor_id='act_' + '3' * 32, authority_grant_id='agr_' + '4' * 32,
    )
    assert set(inspected) == set(registry.checked_locations())
    assert result.status == 'deletion_pending'


def test_unregistered_replica_or_canonical_payload_blocks(tmp_path):
    registry = _registry(tmp_path)
    extra = tmp_path / 'unregistered-replica'
    assert verify_deletion(
        'evi-1', 'c' * 64, registry,
        inspect_location=lambda path, digest: True,
        discover_replicas=lambda _: {*registry.replicas, extra},
        canonical_payload_scan=lambda digest: False,
        actor_id='act-1', authority_grant_id='agr-1',
    ).status == 'deletion_pending'
    assert verify_deletion(
        'evi-1', 'c' * 64, registry,
        inspect_location=lambda path, digest: True,
        discover_replicas=lambda _: set(registry.replicas),
        canonical_payload_scan=lambda digest: True,
        actor_id='act-1', authority_grant_id='agr-1',
    ).status == 'deletion_pending'


def test_missing_retention_rule_blocks_fixture_activation():
    with pytest.raises(ValueError, match='retention_rule_missing'):
        require_retention_rule('R2', 'full_transcript')
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_retention.py -q --no-cov`

Expected: retention module, registry schema, and verifier absent.

- [ ] **Step 3: Implement the policy, registry, and verifier**

```python
# research_system/evals/retention.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RetentionRule:
    max_days: int
    review_lead_days: int
    owner: str
    extension_authority: str
    anchor: str
    use_earlier_source_expiry: bool = False


@dataclass(frozen=True)
class EvidenceStoreRegistry:
    store_id: str
    registry_hash: str
    primary: Path
    runtime: Path
    staging: Path
    temp: Path
    replicas: tuple[Path, ...]
    permitted_consumers: tuple[str, ...]

    def checked_locations(self):
        return (self.primary, self.runtime, self.staging, self.temp, *self.replicas)


@dataclass(frozen=True)
class DeletionVerificationManifest:
    evidence_id: str
    evidence_hash: str
    registry_hash: str
    actor_id: str
    authority_grant_id: str
    checked_locations: tuple[tuple[str, bool], ...]
    unregistered_replicas: tuple[str, ...]
    canonical_payload_present: bool
    status: str


RULES = {
    ('R1', 'redacted_command_summary'): RetentionRule(180, 30, 'system_maintainer', 'manager', 'run_terminal'),
    ('R1', 'operational_measurement'): RetentionRule(365, 30, 'system_maintainer', 'manager', 'release_decision'),
    ('R1', 'grader_explanation'): RetentionRule(365, 30, 'evaluation_owner', 'manager', 'release_decision'),
    ('R2', 'restricted_local_reference'): RetentionRule(90, 14, 'data_controller', 'data_authority', 'run_terminal', True),
    ('R2', 'minimized_sensitive_excerpt'): RetentionRule(30, 7, 'data_controller', 'data_authority', 'run_terminal', True),
}


def verify_deletion(
    evidence_id, evidence_hash, registry, inspect_location, discover_replicas,
    canonical_payload_scan, actor_id, authority_grant_id,
):
    checks = tuple(
        (str(path.resolve()), inspect_location(path.resolve(), evidence_hash))
        for path in registry.checked_locations()
    )
    discovered = {path.resolve() for path in discover_replicas(registry)}
    registered = {path.resolve() for path in registry.replicas}
    unregistered = tuple(sorted(str(path) for path in discovered - registered))
    canonical_present = canonical_payload_scan(evidence_hash)
    verified = all(passed for _, passed in checks) and not unregistered and not canonical_present
    return DeletionVerificationManifest(
        evidence_id, evidence_hash, registry.registry_hash, actor_id,
        authority_grant_id, checks, unregistered, canonical_present,
        'verified' if verified else 'deletion_pending',
    )
```

Production `inspect_location` performs evidence-hash/path-class checks itself and records inaccessible locations, reparse/junction targets, and per-location evidence hashes. The verifier never accepts caller-supplied absence booleans. `.research-system/evals/retention-policy.yaml` and the evidence-store registry schema encode policy revision, effective date, owners, extension authorities, consumers, and the prohibition on unregistered replicas.

The WP1 command service owns `DeleteEvidenceObject` and `VerifyEvidenceDeletion`. It accepts `EvidenceDeletionVerified` only from a complete verified manifest whose registry/policy hashes and actor authority are current; otherwise it records `deletion_pending`, blocks a clean release, and blocks new R2 intake for that store.

- [ ] **Step 4: Run retention and replay tests**

```powershell
uv run pytest tests/research_system/unit/test_retention.py tests/research_system/unit/test_replay.py -q --no-cov
uv run python -m research_system.cli eval retention validate --policy .research-system/evals/retention-policy.yaml
```

Expected: every evidence type has an explicit rule; stale temp/staging content, inaccessible or unregistered replicas, junction escapes, and canonical payload contamination block verification; authorized deletion preserves replay.

- [ ] **Step 5: Commit retention controls**

Commit subject: `[PIPELINE] P00: add ARS evidence retention controls` using a task-specific message file and `git commit -F`.

## Task 4: Materialize the exact fixture package registry

- [ ] **Step 1: Write failing catalogue-closure tests**

```python
from research_system.evals.catalogue import load_catalogue, load_fixture


P0_CASES = {
    'F-001', 'F-002', 'F-003', 'F-004', 'F-005',
    'F-007', 'F-008', 'F-009', 'F-010', 'F-011', 'F-012', 'F-013', 'F-014',
    'F-020', 'F-021', 'F-022', 'F-025', 'F-026', 'F-027', 'F-028',
    'F-031', 'F-032', 'F-033', 'F-034', 'F-035', 'F-036',
    'S-001', 'S-002', 'S-003', 'S-004', 'S-006', 'S-008',
    'S-009', 'S-010', 'S-011', 'S-012', 'S-013',
}


def test_p0_catalogue_contains_exactly_37_cases():
    catalogue = load_catalogue('.research-system/evals/catalogue.yaml')
    assert set(catalogue.p0_materialization_ids) == P0_CASES
    assert len(P0_CASES) == 37


def test_f021_remains_p1_but_materializes_for_sizing():
    fixture = load_fixture('F-021')
    assert fixture.priority == 'P1'
    assert fixture.gate_stage == 'p0_materialization'
    assert fixture.variant == 'mandatory_closure_sizing'
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_coverage.py -q --no-cov`

Expected: catalogue and fixture packages absent.

- [ ] **Step 3: Implement deterministic materializer and package schema**

`.research-system/evals/p0-calibration-policy.yaml` is an immutable P0 proposal with these exact rules:

```yaml
schema_version: '1.0.0'
policy_revision: p0-calibration-v1
deterministic_repetitions: 2
identical_input_requirement: byte_identical_normalized_decision
known_bad_requirement: intended_failure_in_every_repetition
known_good_requirement: intended_pass_in_every_repetition
declared_mutation_requirement: detected_in_every_repetition
stochastic_policy_missing: fixture_error
model_or_human_threshold_policy_missing: unable_to_grade
live_provider_calibration_enabled: false
```

`.research-system/evals/p0-variant-matrix.yaml` contains explicit rows, never wildcards. Control/store cases bind provider `none`, `in_process_fake`, Windows, and their declared operational profile. Context/routing cases bind the exact reference counter plus each required fake Claude/Codex provider-count/rendering revision. Adapter cases bind `claude`/`codex`, adapter profile/revision, `fake` transport, Windows, and the applicable `trivial`/`bounded`/`long_running` profile. Scientific cases bind the exact synthetic oracle, grader versions, seeds/repeats where stochastic, and required independence class. Every row names one fixture revision and one complete variant tuple.

`tools/ars/materialize_p0_fixtures.py` reads `.research-system/evals/catalogue.yaml`, refuses any ID set other than `P0_CASES`, validates that every required variant has one explicit matrix row, and creates each exact package with:

```text
fixture.yaml
README.md
input/source-manifest.json
input/stimulus.json
expected/pre-control.json
expected/post-control.json
expected/trajectory.json
graders/required.json
```

The materializer refuses overwrite unless every generated byte is identical. Every `fixture.yaml` records incident basis, input fidelity, priority, gate stage, risk tier, lanes, source/reconstruction/redaction hashes, policy/schema versions, required variants, required grader IDs/classes, threshold-policy IDs, retention class, and allowed consumers.

Run:

```powershell
uv run python tools/ars/materialize_p0_fixtures.py --catalogue .research-system/evals/catalogue.yaml --root .research-system/evals/fixtures
uv run python tools/ars/materialize_p0_fixtures.py --catalogue .research-system/evals/catalogue.yaml --root .research-system/evals/fixtures --check
```

Expected: first command creates 37 packages; second reports `37 packages byte-identical`.

- [ ] **Step 4: Validate package closure**

Run: `uv run pytest tests/research_system/unit/test_coverage.py -q --no-cov`

Expected: exact ID/count, provenance axes, F-021 staging, no-overwrite, calibration-policy, and explicit no-wildcard variant-matrix tests pass.

- [ ] **Step 5: Commit fixture definitions**

Commit subject: `[PIPELINE] P00: materialize ARS P0 fixture definitions`.

## Task 5: Implement known-bad and known-good reference systems

- [ ] **Step 1: Write failing paired-calibration tests**

Split integration tests by responsibility:

- control/store: F-001–F-005 and S-001/S-002/S-006/S-008–S-012;
- context/routing: F-021/F-022/F-025–F-028/F-031/F-033/F-035/F-036;
- adapters/operations: F-007–F-010/F-020/F-032/F-034 and S-003/S-004/S-013;
- scientific controls: F-011–F-014/F-036.

Each deterministic test runs a deliberately defective reference implementation and the controlled candidate implementation twice against the same immutable fixture input. Identical-input normalized decisions must be byte-identical; known-bad behavior must fail twice and known-good behavior must pass twice. A stochastic fixture uses only its own accepted seed/repeat/uncertainty policy. Required M/H evidence remains blocking `unable_to_grade` until a separate accepted live-grader threshold policy and bounded authority exist.

- [ ] **Step 2: Run and confirm calibration is absent**

Run: `uv run pytest tests/research_system/integration/test_p0_*_fixtures.py -q --no-cov`

Expected: calibration records or reference fakes missing.

- [ ] **Step 3: Implement minimized reference fakes and property graders**

Scientific fixtures use synthetic property evidence only:

```python
def pass_or_fail(condition):
    return 'pass' if condition else 'fail'


def grade_f011(call_log, expected_fingerprint):
    forbidden = [call for call in call_log if call['operation'] in {'fit', 'fit_transform'}]
    fingerprint_ok = all(
        call.get('transform_fingerprint') == expected_fingerprint
        for call in call_log if call['operation'] == 'transform'
    )
    return pass_or_fail(not forbidden and fingerprint_ok)


def grade_f012(before_hash, after_hash, producer_pass_flag):
    del producer_pass_flag
    return pass_or_fail(before_hash != after_hash)


def grade_f013(input_manifests):
    vintages = {item['vintage_id'] for item in input_manifests}
    return pass_or_fail(len(vintages) == 1)


def grade_f014(author_actor, approver_actor, relationship_grade):
    return pass_or_fail(author_actor != approver_actor and relationship_grade in {'I1', 'I2'})
```

F-036 has three independent mutation cases: expected-value anchoring, degenerate fallback, and null invariance. No expected number is accepted merely because output is close; the grader recomputes or challenges the property from fixture inputs.

- [ ] **Step 4: Run paired calibration**

Run:

```powershell
uv run pytest tests/research_system/integration/test_p0_control_fixtures.py -q --no-cov
uv run pytest tests/research_system/integration/test_p0_context_routing_fixtures.py -q --no-cov
uv run pytest tests/research_system/integration/test_p0_adapter_operations_fixtures.py -q --no-cov
uv run pytest tests/research_system/integration/test_p0_scientific_fixtures.py -q --no-cov
```

Expected: each known-bad case fails for its intended reason in both repetitions, each known-good case passes in both repetitions, identical normalized decisions are byte-stable, and any fixture/policy mismatch is `fixture_error`; unavailable required M/H evidence is blocking `unable_to_grade`.

- [ ] **Step 5: Commit calibration evidence**

Commit subject: `[PIPELINE] P00: calibrate ARS P0 paired fixtures`.

## Task 6: Implement scenarios A–E and release decision

- [ ] **Step 1: Write failing end-to-end scenario tests**

```python
from research_system.evals.scenarios import run_gate3_scenario


def test_scenario_a_r2_two_stage_production_and_verification():
    result = run_gate3_scenario('A')
    assert result.event_types.index('RouteSelected') < result.event_types.index('ProviderCommandIssued')
    assert result.producer_actor_id != result.verifier_actor_id


def test_scenario_b_provider_outage_preserves_requirements():
    result = run_gate3_scenario('B')
    assert result.original_requirement_id == result.reroute_requirement_id
    assert result.provider_command_count == 0


def test_scenario_c_long_run_stop_checkpoint_resume():
    result = run_gate3_scenario('C')
    assert result.stop_disposition == 'confirmed'
    assert result.checkpoint_compatibility == 'compatible'
    assert result.resume_epoch == result.initial_epoch + 1


def test_scenario_d_writer_crash_restore_has_zero_or_one_batch():
    result = run_gate3_scenario('D')
    assert result.published_batch_count in {0, 1}
    assert result.replay_integrity == 'pass'


def test_scenario_e_restricted_data_denied_before_provider_issue():
    result = run_gate3_scenario('E')
    assert result.decision_reason == 'restricted_data_denied'
    assert 'ProviderCommandIssued' not in result.event_types
```

Scenario B uses the F-032 P0 path; it does not claim S-016 activation. Scenario D uses S-011 recovery; cross-machine S-014 remains a later foundation-release case.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/integration/test_gate3_scenarios.py -q --no-cov`

Expected: integrated evaluation coordinator absent.

- [ ] **Step 3: Implement runner, coverage, calibration, and release CLI**

```python
# research_system/evals/runner.py
from typing import Protocol

from research_system.evals.errors import FixtureDefinitionError, MissingEvidence, UnableToGrade


class EvaluationLifecyclePort(Protocol):
    def start(self, fixture, subject): ...
    def finish(self, run, trace, results): ...
    def fixture_error(self, run, error: FixtureDefinitionError): ...
    def unable_to_grade(self, run, error: Exception): ...


def run_fixture(fixture, subject, trace_collector, graders, lifecycle: EvaluationLifecyclePort):
    run = lifecycle.start(fixture, subject)
    try:
        subject_result = subject.execute(fixture.stimulus)
        trace = trace_collector.complete(run, subject_result)
        results = tuple(grader.grade(fixture, trace, subject_result) for grader in graders)
        return lifecycle.finish(run, trace, results)
    except FixtureDefinitionError as exc:
        return lifecycle.fixture_error(run, exc)
    except (MissingEvidence, UnableToGrade) as exc:
        return lifecycle.unable_to_grade(run, exc)
```

`EvaluationLifecyclePort` is implemented in `research_system/evals/lifecycle.py`; its contract tests require immutable run identity, terminal trace/result hashes, and closed `fixture_error`/`unable_to_grade` outcomes. The runner has no unowned lifecycle helper. `load_catalogue()` and `load_fixture()` are owned by `research_system/evals/catalogue.py`, used by the materializer and the closure tests through the stable signatures shown in Task 4.

CLI commands:

```text
ars eval validate --catalogue PATH
ars eval calibrate --coverage PATH --transport fake
ars eval run --coverage PATH --transport fake
ars eval release --evaluation-runs PATH
```

All output paths are explicit, date-suffixed, and non-overwriting. `release` validates exact required-result tuple closure, accepted calibration/variant policy, and explicit capability restrictions before emitting one `ReleaseGateDecision`. Missing required M/H threshold/authority remains blocked. S-014/S-015/S-016 remain omitted with Gate 5 restrictions and cannot be converted into P0 pass. `release` never activates providers, migrates a project, initializes a pilot, or accepts a research claim.

- [ ] **Step 4: Run full P0 verification**

Run:

```powershell
uv run ruff check research_system tools/ars tests/research_system
uv run pytest tests/research_system -q --no-cov
uv run python -m research_system.cli eval validate --catalogue .research-system/evals/catalogue.yaml
uv run python -m research_system.cli eval calibrate --coverage .research-system/evals/p0-coverage.yaml --transport fake
uv run python -m research_system.cli eval run --coverage .research-system/evals/p0-coverage.yaml --transport fake
```

Expected: 37 fixture definitions validate; every paired calibration behaves as declared; the candidate P0 run has complete evidence or a blocking non-pass.

- [ ] **Step 5: Commit WP4**

Commit subject: `[PIPELINE] P00: complete ARS P0 evaluation harness`.

## P0 acceptance and independent review

- [ ] p0-coverage.yaml names exactly 37 cases and explains every catalogue omission.
- [ ] Every R1/R2 evidence type has an accepted duration, owner, review lead, external payload location, and deletion-verification path; R3 remains prohibited.
- [ ] Every critical D/T/P and required R/M/H result is non-compensable, and exact required-result set equality is enforced before verdict evaluation.
- [ ] Deterministic P0 calibration repeats every known-bad/known-good/mutation case twice; missing stochastic or M/H threshold policy blocks rather than defaults.
- [ ] F-021 remains P1 while its sizing variant runs at P0 materialization.
- [ ] No raw UKDA data, secrets, hidden reasoning, or full transcripts enter fixture/trace storage.
- [ ] Model/human grader requirements are satisfied by independent evidence or remain blocking `unable_to_grade`.
- [ ] A fresh reviewer checks F-011/F-012/F-022/F-026/F-035/F-036, including F-036 mutations derived from the deferred F-015/F-016 incident classes, for oracle validity and anchoring.
- [ ] `ReleaseGateDecision` records `pass`, `fail`, or `blocked`; `exception_limited` is unavailable unless an accepted policy explicitly constrains the affected capability.
- [ ] Gate 5 remains closed until S-014/S-015/S-016 release cases and the accepted P0 decision are reviewed.
- [ ] Stephen accepts the P0 evidence before any live provider, greenfield pilot, or research task is initialized.
