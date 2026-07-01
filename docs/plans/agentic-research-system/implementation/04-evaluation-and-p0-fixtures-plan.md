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
.research-system/evals/catalogue.yaml
.research-system/evals/p0-coverage.yaml
.research-system/evals/threshold-policies.yaml
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
        GraderResult('grr_' + '2' * 32, 'run-1', 'F-001', 'state', 'D', 'maybe', True, True, 'b' * 64, 'c' * 64, ())


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
    grader_id: str
    grader_class: str
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

## Task 2: Implement trace completeness and deterministic graders

- [ ] **Step 1: Write failing grader tests**

```python
from types import SimpleNamespace

import pytest

from research_system.evals.errors import UnableToGrade
from research_system.evals.models import GraderResult, TraceEnvelope
from research_system.evals.release import decide_release
from research_system.evals.trace import assert_trace_complete


def _coverage():
    return SimpleNamespace(required_fixture_ids=('F-001',))


def _result(verdict):
    return GraderResult(
        'grr_' + '5' * 32, 'run-1', 'F-001', 'state', 'D', verdict,
        True, True, 'a' * 64, 'b' * 64, (),
    )


def test_missing_provider_receipt_is_unable_to_grade_and_blocking():
    fixture = SimpleNamespace(required_evidence_classes=('provider_receipt',))
    with pytest.raises(UnableToGrade):
        assert_trace_complete(TraceEnvelope('trc-1', (), ()), fixture)


def test_missing_operational_terminal_record_is_unable_to_grade():
    fixture = SimpleNamespace(required_evidence_classes=('operational_terminal',))
    trace = TraceEnvelope('trc-1', ({'evidence_class': 'provider_receipt'},), ())
    with pytest.raises(UnableToGrade):
        assert_trace_complete(trace, fixture)


def test_fixture_defect_is_quarantined_not_system_pass():
    assert decide_release(_coverage(), [_result('fixture_error')])['decision'] == 'blocked'


def test_critical_fail_cannot_be_overridden_by_weighted_score():
    assert decide_release(_coverage(), [_result('fail')])['decision'] == 'fail'


def test_producer_pass_flag_is_not_independent_property_evidence():
    fixture = SimpleNamespace(required_evidence_classes=('independent_property_evidence',))
    trace = TraceEnvelope('trc-1', ({'evidence_class': 'producer_pass_flag'},), ())
    with pytest.raises(UnableToGrade):
        assert_trace_complete(trace, fixture)
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_graders.py tests/research_system/unit/test_release_gate.py -q --no-cov`

Expected: grader/release functions absent.

- [ ] **Step 3: Implement trace and release rules**

```python
# research_system/evals/release.py
BLOCKING = {'fail', 'unable_to_grade', 'fixture_error'}


def decide_release(coverage, results):
    by_fixture = {}
    for result in results:
        by_fixture.setdefault(result.fixture_id, []).append(result)
    missing = sorted(set(coverage.required_fixture_ids) - set(by_fixture))
    blocking = [
        result for result in results
        if result.required and result.verdict in BLOCKING
    ]
    if missing or blocking:
        decision = 'blocked' if missing or any(
            result.verdict in {'unable_to_grade', 'fixture_error'}
            for result in blocking
        ) else 'fail'
        return {'decision': decision, 'missing': missing, 'blocking': blocking}
    return {'decision': 'pass', 'missing': [], 'blocking': []}
```

```python
# research_system/evals/trace.py
def assert_trace_complete(trace, fixture):
    required = set(fixture.required_evidence_classes)
    present = {item['evidence_class'] for item in trace.items}
    missing = sorted(required - present)
    unterminated = [item['command_id'] for item in trace.issued_commands if not item.get('terminal_ref')]
    if missing or unterminated:
        raise UnableToGrade({'missing': missing, 'unterminated': unterminated})
```

Deterministic graders recompute hashes, ordering, state, token bounds, null-input identity, representation call logs, root bindings, and authority relationships. Model/human graders are represented as required external results; the runner cannot synthesize them.

- [ ] **Step 4: Run grader/release tests**

Run: `uv run pytest tests/research_system/unit/test_graders.py tests/research_system/unit/test_release_gate.py -q --no-cov`

Expected: non-compensable and missing-evidence tests pass.

- [ ] **Step 5: Commit runner primitives**

Commit subject: `[PIPELINE] P00: enforce ARS non-compensable grading`.

## Task 3: Implement retention policy and deletion verification

- [ ] **Step 1: Write failing retention tests**

```python
import pytest

from research_system.evals.retention import RULES, deletion_verdict, require_retention_rule


def test_r1_windows_are_explicit_by_evidence_type():
    assert RULES[('R1', 'redacted_command_summary')].max_days == 180
    assert RULES[('R1', 'operational_measurement')].max_days == 365
    assert RULES[('R1', 'grader_explanation')].max_days == 365


def test_r2_windows_use_earlier_source_expiry():
    assert RULES[('R2', 'restricted_local_reference')].max_days == 90
    assert RULES[('R2', 'minimized_sensitive_excerpt')].max_days == 30
    assert all(rule.use_earlier_source_expiry for key, rule in RULES.items() if key[0] == 'R2')


def test_deletion_requires_absence_from_every_registered_location():
    checks = {
        'primary_absent': True, 'runtime_absent': True, 'temp_absent': True,
        'registered_replicas_absent': False, 'canonical_payload_absent': True,
    }
    assert deletion_verdict(checks) == 'deletion_pending'
    checks['registered_replicas_absent'] = True
    assert deletion_verdict(checks) == 'verified'


def test_missing_retention_rule_blocks_fixture_activation():
    with pytest.raises(ValueError, match='retention_rule_missing'):
        require_retention_rule('R2', 'full_transcript')
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_retention.py -q --no-cov`

Expected: retention module and versioned policy file absent.

- [ ] **Step 3: Implement the policy and verifier**

```python
# research_system/evals/retention.py
from dataclasses import dataclass


@dataclass(frozen=True)
class RetentionRule:
    max_days: int
    review_lead_days: int
    owner: str
    extension_authority: str
    anchor: str
    use_earlier_source_expiry: bool = False


RULES = {
    ('R1', 'redacted_command_summary'): RetentionRule(180, 30, 'system_maintainer', 'manager', 'run_terminal'),
    ('R1', 'operational_measurement'): RetentionRule(365, 30, 'system_maintainer', 'manager', 'release_decision'),
    ('R1', 'grader_explanation'): RetentionRule(365, 30, 'evaluation_owner', 'manager', 'release_decision'),
    ('R2', 'restricted_local_reference'): RetentionRule(90, 14, 'data_controller', 'data_authority', 'run_terminal', True),
    ('R2', 'minimized_sensitive_excerpt'): RetentionRule(30, 7, 'data_controller', 'data_authority', 'run_terminal', True),
}


def require_retention_rule(retention_class, evidence_type):
    try:
        return RULES[(retention_class, evidence_type)]
    except KeyError as exc:
        raise ValueError('retention_rule_missing') from exc


def deletion_verdict(checks):
    required = {
        'primary_absent', 'runtime_absent', 'temp_absent',
        'registered_replicas_absent', 'canonical_payload_absent',
    }
    return 'verified' if required <= checks.keys() and all(checks[key] for key in required) else 'deletion_pending'
```

`.research-system/evals/retention-policy.yaml` is the versioned authority and must encode the same rows, policy revision, effective date, owning roles, extension authorities, permitted consumers, and the prohibition on unregistered R1/R2 replicas. `retention.py` loads that file in production; the literal table above is the unit-test oracle, not a second mutable policy source.

The command service owns `DeleteEvidenceObject` and `VerifyEvidenceDeletion`. The former removes only an authorized expiring payload from the external evidence root; the latter checks primary/runtime/temp/registered-replica absence, confirms that canonical records contain only R0 metadata, rebuilds the availability projection as `expired_deleted`, and emits an `EvidenceDeletionVerified` event plus immutable command receipt. An incomplete check remains `deletion_pending`, blocks clean release, and blocks new R2 intake for that store.

- [ ] **Step 4: Run retention and replay tests**

```powershell
uv run pytest tests/research_system/unit/test_retention.py tests/research_system/unit/test_replay.py -q --no-cov
uv run python -m research_system.cli eval retention validate --policy .research-system/evals/retention-policy.yaml
```

Expected: all evidence types have explicit windows; deletion verification cannot pass with any unchecked location; replay remains valid after an authorized payload deletion.

- [ ] **Step 5: Commit retention controls**

Commit subject: `[PIPELINE] P00: add ARS evidence retention controls` using a task-specific message file and `git commit -F`.

## Task 4: Materialize the exact fixture package registry

- [ ] **Step 1: Write failing catalogue-closure tests**

```python
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

`tools/ars/materialize_p0_fixtures.py` reads `.research-system/evals/catalogue.yaml`, refuses any ID set other than `P0_CASES`, and creates each exact package with:

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

Expected: exact ID/count, provenance axes, F-021 staging, and no-overwrite tests pass.

- [ ] **Step 5: Commit fixture definitions**

Commit subject: `[PIPELINE] P00: materialize ARS P0 fixture definitions`.

## Task 5: Implement known-bad and known-good reference systems

- [ ] **Step 1: Write failing paired-calibration tests**

Split integration tests by responsibility:

- control/store: F-001–F-005 and S-001/S-002/S-006/S-008–S-012;
- context/routing: F-021/F-022/F-025–F-028/F-031/F-033/F-035/F-036;
- adapters/operations: F-007–F-010/F-020/F-032/F-034 and S-003/S-004/S-013;
- scientific controls: F-011–F-014/F-036.

Each test runs a deliberately defective reference implementation and the controlled candidate implementation against the same immutable fixture input.

- [ ] **Step 2: Run and confirm calibration is absent**

Run: `uv run pytest tests/research_system/integration/test_p0_*_fixtures.py -q --no-cov`

Expected: calibration records or reference fakes missing.

- [ ] **Step 3: Implement minimized reference fakes and property graders**

Scientific fixtures use synthetic property evidence only:

```python
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

Expected: each known-bad case fails for its intended reason and each known-good case passes; any fixture mismatch is `fixture_error`.

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
from research_system.evals.errors import FixtureDefinitionError, MissingEvidence, UnableToGrade


def run_fixture(fixture, subject, trace_collector, graders):
    run = start_run(fixture, subject)
    try:
        subject_result = subject.execute(fixture.stimulus)
        trace = trace_collector.complete(run, subject_result)
        results = tuple(grader.grade(fixture, trace, subject_result) for grader in graders)
        return finish_run(run, trace, results)
    except FixtureDefinitionError as exc:
        return fixture_error_run(run, exc)
    except (MissingEvidence, UnableToGrade) as exc:
        return unable_to_grade_run(run, exc)
```

CLI commands:

```text
ars eval validate --catalogue PATH
ars eval calibrate --coverage PATH --transport fake
ars eval run --coverage PATH --transport fake
ars eval release --evaluation-runs PATH
```

All output paths are explicit, date-suffixed, and non-overwriting. `release` validates complete coverage and emits one `ReleaseGateDecision`; it never activates providers, migrates a project, or accepts a research claim.

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
- [ ] Every critical D/T/P and required R/M/H result is non-compensable.
- [ ] F-021 remains P1 while its sizing variant runs at P0 materialization.
- [ ] No raw UKDA data, secrets, hidden reasoning, or full transcripts enter fixture/trace storage.
- [ ] Model/human grader requirements are satisfied by independent evidence or remain blocking `unable_to_grade`.
- [ ] A fresh reviewer checks F-011/F-012/F-022/F-026/F-035/F-036, including F-036 mutations derived from the deferred F-015/F-016 incident classes, for oracle validity and anchoring.
- [ ] `ReleaseGateDecision` records `pass`, `fail`, or `blocked`; `exception_limited` is unavailable unless an accepted policy explicitly constrains the affected capability.
- [ ] Gate 5 remains closed until S-014/S-015/S-016 release cases and the accepted P0 decision are reviewed.
- [ ] Stephen accepts the P0 evidence before any live provider, greenfield pilot, or research task is initialized.
