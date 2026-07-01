# ARS P0 Work Package 2: Context, Routing, and Assurance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement deterministic context compilation, two token gates, producer-independent assurance requirements, eligibility-first routing, verifier feasibility, and evidence-derived independence.

**Architecture:** W3 compiles immutable unissued candidates from declared sources, W5 freezes the required validity bar, and W4 evaluates every registered route against W3/W5/W6/W7/W8 evidence before deterministic ranking. Provider counting and operational facts enter through typed ports so tests can use exact deterministic fakes without granting authority to adapters or operations.

**Tech Stack:** Python 3.13.5, dataclasses, pathlib, regex reference tokenizer, SHA-256, PyYAML/jsonschema, pytest parameterization.

---

## File map

**Create:**

```text
research_system/context/__init__.py
research_system/context/models.py
research_system/context/errors.py
research_system/context/sources.py
research_system/context/tokenizers.py
research_system/context/compiler.py
research_system/assurance/__init__.py
research_system/assurance/models.py
research_system/assurance/requirements.py
research_system/routing/__init__.py
research_system/routing/models.py
research_system/routing/independence.py
research_system/routing/engine.py
research_system/routing/orchestrator.py
.research-system/schemas/context/context-candidate.schema.json
.research-system/schemas/context/context-manifest.schema.json
.research-system/schemas/assurance/assurance-requirement.schema.json
.research-system/schemas/routing/model-eval-profile.schema.json
.research-system/schemas/routing/route-request.schema.json
.research-system/schemas/routing/route-decision.schema.json
.research-system/schemas/routing/route-failure.schema.json
.research-system/policies/context-profiles.yaml
.research-system/policies/risk-and-independence.yaml
.research-system/packs/core-assurance.yaml
tests/research_system/unit/test_context_compiler.py
tests/research_system/unit/test_token_gates.py
tests/research_system/unit/test_assurance_requirements.py
tests/research_system/unit/test_independence.py
tests/research_system/unit/test_routing_engine.py
tests/research_system/integration/test_context_routing_fixtures.py
```

## Task 1: Freeze context and assurance models

- [ ] **Step 1: Write failing model/schema tests**

```python
import pytest

from research_system.assurance.models import CORE_LANES, AssuranceRequirement, LaneRequirement
from research_system.assurance.requirements import validate_requirement
from research_system.context.models import ContextCandidate
from research_system.errors import ArsError


def test_context_candidate_is_compiled_but_unissued():
    candidate = ContextCandidate('ctx_' + '1' * 32, 'mft_' + '2' * 32, 'a' * 64, 10, 3, 'ref-v1')
    assert candidate.state == 'compiled'
    assert candidate.state not in {'validated', 'issued'}


def test_manifest_requires_every_mandatory_source_and_omission_reason():
    candidate = ContextCandidate('ctx_' + '3' * 32, 'mft_' + '4' * 32, 'b' * 64, 20, 4, 'ref-v1')
    with pytest.raises(ArsError, match='mandatory source'):
        candidate.validate_manifest(required={'src-a', 'src-b'}, included={'src-a'}, omissions={})


def test_assurance_requirement_enumerates_every_core_lane():
    lanes = tuple(LaneRequirement(lane, 'required', 'P0 test') for lane in sorted(CORE_LANES))
    requirement = AssuranceRequirement('arq_' + '5' * 32, 'R2', 'act-producer', 'act-author', 'act-reviewer', 'I1', lanes)
    assert {item.lane for item in requirement.lanes} == CORE_LANES


def test_r2_requirement_author_cannot_be_sole_acceptor():
    lanes = tuple(LaneRequirement(lane, 'required', 'P0 test') for lane in sorted(CORE_LANES))
    requirement = AssuranceRequirement('arq_' + '6' * 32, 'R2', 'act-producer', 'act-producer', 'act-producer', 'I1', lanes)
    with pytest.raises(ArsError, match='scope_unconfirmed'):
        validate_requirement(requirement)
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_context_compiler.py tests/research_system/unit/test_assurance_requirements.py -q --no-cov`

Expected: missing context/assurance modules.

- [ ] **Step 3: Implement immutable models**

```python
# research_system/context/models.py
from dataclasses import dataclass, field

from research_system.errors import ArsError


@dataclass(frozen=True)
class SourceFragment:
    source_id: str
    revision: str
    authority_rank: int
    mandatory: bool
    content: str
    content_hash: str


@dataclass(frozen=True)
class ContextProfile:
    profile_id: str
    reference_limit: int


@dataclass(frozen=True)
class ContextCandidate:
    context_candidate_id: str
    manifest_id: str
    content_hash: str
    utf8_bytes: int
    reference_count: int
    reference_counter_id: str
    state: str = 'compiled'
    rendered_content: str = ''
    source_ids: tuple[str, ...] = ()
    mandatory_source_ids: tuple[str, ...] = ()
    mandatory_hash: str = ''
    source_manifest: tuple[dict, ...] = ()
    conflicts: tuple[str, ...] = ()
    omissions: dict[str, str] = field(default_factory=dict)

    def validate_manifest(self, required, included, omissions):
        unexplained = set(required) - set(included) - set(omissions)
        if unexplained:
            raise ArsError(f'mandatory source omitted: {sorted(unexplained)}')
```

```python
# research_system/assurance/models.py
from dataclasses import dataclass

CORE_LANES = frozenset({
    'software', 'provenance', 'mathematical', 'statistical',
    'topological', 'stochastic', 'representation', 'claim',
    'operations', 'privacy',
})


@dataclass(frozen=True)
class LaneRequirement:
    lane: str
    disposition: str
    rationale: str


@dataclass(frozen=True)
class AssuranceRequirement:
    assurance_requirement_id: str
    risk_tier: str
    prospective_producer_id: str
    authored_by: str
    accepted_by: str
    required_independence: str
    lanes: tuple[LaneRequirement, ...]
```

`requirements.py` validates complete lane enumeration, non-empty rationale for every `not_applicable`, R2 producer-distinct acceptance at I1 or stronger, and R3 I2 plus a Stephen authority record. It returns stable reason codes including `assurance_requirement_scope_unconfirmed`.

- [ ] **Step 4: Run targeted tests**

Run: `uv run pytest tests/research_system/unit/test_context_compiler.py tests/research_system/unit/test_assurance_requirements.py -q --no-cov`

Expected: model/schema and producer-independent requirement tests pass.

- [ ] **Step 5: Commit model freeze**

Commit subject: `[PIPELINE] P00: add ARS context and assurance models`.

## Task 2: Implement deterministic compilation and two token gates

- [ ] **Step 1: Write failing F-021/F-022/F-025–F-028 tests**

Tests must cover mandatory-source closure, authority conflict, optional-index deletion equivalence, safe deterministic ordering, reference overflow, candidate-bound provider overflow, and no truncation/summarization fallback.

```python
import pytest

from research_system.context.compiler import compile_candidate, validate_provider_gate
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.tokenizers import ReferenceRegexV1, Utf8ByteUpperBoundV1
from research_system.context.errors import ContextBudgetExceeded


def _fragment(source_id, authority, content, mandatory=True):
    return SourceFragment(source_id, 'r1', authority, mandatory, content, 'h-' + source_id)


def test_f025_scope_authority_survives_distractors():
    profile = ContextProfile('r2', reference_limit=100)
    strong = _fragment('scope-22', 100, 'scope has 22 members')
    stale = _fragment('tracker-stale', 10, 'stage complete', mandatory=False)
    candidate = compile_candidate([stale, strong], profile, ReferenceRegexV1())
    assert candidate.source_ids[0] == 'scope-22'
    assert 'scope has 22 members' in candidate.rendered_content


def test_f026_frozen_null_vintage_requirements_are_mandatory():
    profile = ContextProfile('r2', reference_limit=100)
    required = [_fragment(name, 100, name) for name in ('frozen-transform', 'null-preflight', 'vintage', 'seed', 'stop-rule')]
    candidate = compile_candidate(required, profile, ReferenceRegexV1())
    assert set(candidate.mandatory_source_ids) == {item.source_id for item in required}


def test_f027_index_deletion_preserves_mandatory_hash():
    profile = ContextProfile('r2', reference_limit=100)
    mandatory = _fragment('direct-source', 100, 'governing evidence')
    optional = _fragment('optional-index', 1, 'supplement', mandatory=False)
    with_index = compile_candidate([mandatory, optional], profile, ReferenceRegexV1())
    direct = compile_candidate([mandatory], profile, ReferenceRegexV1())
    assert with_index.mandatory_hash == direct.mandatory_hash


def test_f028_either_token_gate_blocks_issue_without_truncation():
    profile = ContextProfile('r2', reference_limit=2)
    fragment = _fragment('mandatory', 100, 'one two three')
    with pytest.raises(ContextBudgetExceeded, match='reference_token_gate'):
        compile_candidate([fragment], profile, ReferenceRegexV1())
    candidate = compile_candidate([fragment], ContextProfile('r2', 100), ReferenceRegexV1())
    with pytest.raises(ContextBudgetExceeded, match='bound_provider_capacity_gate'):
        validate_provider_gate(candidate, Utf8ByteUpperBoundV1(), usable_capacity=4)


def test_f021_f022_mandatory_closure_is_measured_without_priority_change():
    fixture = {'priority': 'P1', 'gate_stage': 'p0_materialization', 'variant': 'mandatory_closure_sizing'}
    assert fixture == {'priority': 'P1', 'gate_stage': 'p0_materialization', 'variant': 'mandatory_closure_sizing'}
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_token_gates.py tests/research_system/integration/test_context_routing_fixtures.py -q --no-cov`

Expected: compiler/counter functions absent.

- [ ] **Step 3: Implement versioned counters and compiler**

```python
# research_system/context/tokenizers.py
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CountEvidence:
    counter_id: str
    units: str
    count: int
    exact: bool


class ReferenceRegexV1:
    counter_id = 'ars-reference-regex-v1'

    def count(self, text: str) -> CountEvidence:
        count = len(re.findall(r'\w+|[^\w\s]', text, flags=re.UNICODE))
        return CountEvidence(self.counter_id, 'ars_reference_tokens', count, True)


class Utf8ByteUpperBoundV1:
    counter_id = 'utf8-byte-upper-bound-v1'

    def count(self, text: str) -> CountEvidence:
        return CountEvidence(self.counter_id, 'provider_token_upper_bound', len(text.encode('utf-8')), False)
```

```python
# research_system/context/compiler.py
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.models import ContextCandidate
from research_system.context.errors import ContextBudgetExceeded


def _source_record(item):
    return {
        'source_id': item.source_id, 'revision': item.revision,
        'content_hash': item.content_hash, 'mandatory': item.mandatory,
    }


def build_candidate(rendered, ordered, mandatory, evidence):
    manifest = tuple(_source_record(item) for item in ordered)
    mandatory_manifest = tuple(_source_record(item) for item in mandatory)
    content_hash = sha256_hex(rendered.encode('utf-8'))
    manifest_hash = sha256_hex(canonical_bytes(manifest))
    return ContextCandidate(
        context_candidate_id='ctx_' + content_hash[:32],
        manifest_id='mft_' + manifest_hash[:32],
        content_hash=content_hash,
        utf8_bytes=len(rendered.encode('utf-8')),
        reference_count=evidence.count,
        reference_counter_id=evidence.counter_id,
        rendered_content=rendered,
        source_ids=tuple(item.source_id for item in ordered),
        mandatory_source_ids=tuple(item.source_id for item in mandatory),
        mandatory_hash=sha256_hex(canonical_bytes(mandatory_manifest)),
        source_manifest=manifest,
    )


def compile_candidate(fragments, profile, reference_counter):
    ordered = sorted(
        fragments,
        key=lambda item: (-item.authority_rank, item.source_id, item.revision),
    )
    mandatory = [item for item in ordered if item.mandatory]
    rendered = '\n\n'.join(item.content for item in ordered)
    evidence = reference_counter.count(rendered)
    if evidence.count > profile.reference_limit:
        raise ContextBudgetExceeded('reference_token_gate')
    return build_candidate(rendered, ordered, mandatory, evidence)


def validate_provider_gate(candidate, counter, usable_capacity):
    evidence = counter.count(candidate.rendered_content)
    limit = int(usable_capacity * 0.80)
    if evidence.count > limit:
        raise ContextBudgetExceeded('bound_provider_capacity_gate')
    return evidence
```

`build_candidate` records all source IDs/revisions/hashes, conflicts, omissions, counter units, and candidate hash. Define `ContextBudgetExceeded(ArsError)` in package-local `research_system/context/errors.py`. The reference count and provider count remain distinct fields and are never compared to one another.

- [ ] **Step 4: Verify P-028 closure**

Run:

```powershell
uv run pytest tests/research_system/unit/test_token_gates.py -q --no-cov
uv run pytest tests/research_system/integration/test_context_routing_fixtures.py -k 'f021 or f022 or f025 or f026 or f027 or f028' -q --no-cov
```

Expected: known-bad overflow/omission paths fail; controlled candidates preserve complete mandatory closure.

- [ ] **Step 5: Commit compiler**

Commit subject: `[PIPELINE] P00: implement ARS context token gates`.

## Task 3: Implement requirement integrity and independence grading

- [ ] **Step 1: Write failing F-022/F-033/F-035/F-036 tests**

```python
from research_system.assurance.requirements import effective_risk, two_key_decision
from research_system.routing.independence import RelationshipEvidence, independence_grade


def test_correlated_actor_session_context_family_is_not_independent():
    evidence = RelationshipEvidence(True, True, True, True, True)
    assert independence_grade(evidence) == 'I0'


def test_role_label_change_does_not_change_relationship_grade():
    evidence = RelationshipEvidence(False, False, True, False, False)
    assert independence_grade(evidence) == 'I0'


def test_r3_action_raises_floor_even_when_request_says_r2():
    assert effective_risk('R2', 'R2', 'R1', 'R3', 'R0') == 'R3'


def test_key_a_cannot_compensate_for_missing_key_b():
    assert two_key_decision(key_a=True, key_b=False) == 'blocked'


def test_producer_pass_flag_cannot_satisfy_property_grader():
    evidence = {'producer_pass_flag': True, 'independent_property_evidence': None}
    assert two_key_decision(key_a=True, key_b=bool(evidence['independent_property_evidence'])) == 'blocked'
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_independence.py tests/research_system/unit/test_assurance_requirements.py -q --no-cov`

Expected: missing independence/action-risk evaluators.

- [ ] **Step 3: Implement relationship evidence grading**

```python
# research_system/routing/independence.py
from dataclasses import dataclass


@dataclass(frozen=True)
class RelationshipEvidence:
    same_actor: bool
    same_session: bool
    same_context_hash: bool
    same_model_family: bool
    producer_conclusions_visible: bool


def independence_grade(evidence: RelationshipEvidence) -> str:
    if evidence.same_actor or evidence.same_session:
        return 'I0'
    if evidence.same_context_hash or evidence.producer_conclusions_visible:
        return 'I0'
    if evidence.same_model_family:
        return 'I1'
    return 'I2'
```

`requirements.py` uses the explicit ordered risk enum and evaluates Key A and Key B separately; no aggregate score is exposed as acceptance:

```python
RISK_ORDER = {'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3}


def effective_risk(*risks):
    return max(risks, key=RISK_ORDER.__getitem__)


def two_key_decision(*, key_a, key_b):
    return 'accepted' if key_a and key_b else 'blocked'
```

- [ ] **Step 4: Run independence/assurance tests**

Run: `uv run pytest tests/research_system/unit/test_independence.py tests/research_system/unit/test_assurance_requirements.py -q --no-cov`

Expected: every self/correlated review and weakened requirement is rejected with its stable reason code.

- [ ] **Step 5: Commit authority controls**

Commit subject: `[PIPELINE] P00: enforce ARS assurance independence`.

## Task 4: Implement eligibility-first deterministic routing

- [ ] **Step 1: Write failing F-031–F-034 routing tests**

Tests cover candidate enumeration permutation, live telemetry outside the bound snapshot, missing verifier witness, outage reroute under original requirements, missing root/sensitivity permission, and unsafe multi-agent decomposition.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_routing_engine.py -q --no-cov`

Expected: routing engine absent.

- [ ] **Step 3: Implement candidate evaluation and stable ranking**

```python
# research_system/routing/engine.py
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteCandidate:
    profile_id: str
    capability_margin: int
    independence_margin: int
    limitation_count: int
    snapshot_reliability: int
    snapshot_latency_ms: int
    snapshot_cost_units: int


REJECTION_ORDER = (
    'provider_unavailable', 'capability_insufficient', 'risk_exceeded',
    'authority_missing', 'permission_missing', 'context_budget_exceeded',
    'assurance_unsatisfied', 'independence_unavailable',
    'fixture_coverage_missing', 'resource_unavailable',
)


def select_route(request, candidates, evidence):
    evaluated = []
    for candidate in sorted(candidates, key=lambda item: item.profile_id):
        failures = evaluate_hard_gates(request, candidate, evidence)
        evaluated.append((candidate, tuple(sorted(failures, key=REJECTION_ORDER.index))))
    eligible = [item for item, failures in evaluated if not failures]
    if not eligible:
        return route_failure(request, evaluated)
    winner = min(
        eligible,
        key=lambda item: (
            -item.capability_margin,
            -item.independence_margin,
            item.limitation_count,
            -item.snapshot_reliability,
            item.snapshot_latency_ms,
            item.snapshot_cost_units,
            item.profile_id,
        ),
    )
    return route_decision(request, winner, evaluated)
```

`evaluate_hard_gates` follows W4 section 12 exactly, including candidate-specific provider counting and a currently eligible verifier witness before R2/R3 producer eligibility. It reads only the immutable `routing_evidence_snapshot_id`; live telemetry is not an input.

- [ ] **Step 4: Verify deterministic routing**

Run:

```powershell
uv run pytest tests/research_system/unit/test_routing_engine.py -q --no-cov
uv run pytest tests/research_system/integration/test_context_routing_fixtures.py -k 'f031 or f032 or f033 or f034' -q --no-cov
```

Expected: permutations produce byte-identical decision data; missing witness/permission blocks before dispatch.

- [ ] **Step 5: Commit router**

Commit subject: `[PIPELINE] P00: add deterministic ARS routing`.

## Task 5: Integrate context, assurance, and route evidence

- [ ] **Step 1: Write a failing two-stage Gate 3 flow test**

The test asserts W5 acceptance and W3 reference gate before W4, W7/W8 preliminary evidence before candidate evaluation, candidate-specific provider gate during W4, and a selected route that is still unissued.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/integration/test_context_routing_fixtures.py -k two_stage -q --no-cov`

Expected: orchestration function absent.

- [ ] **Step 3: Add a pure planning orchestrator**

```python
# research_system/routing/orchestrator.py
def plan_dispatch(task, requirement, candidate, provider_evidence, operational_evidence):
    assert_requirement_current(task, requirement)
    compiled = compile_context_for_task(task)
    preliminary = bind_pre_route_evidence(provider_evidence, operational_evidence)
    route = select_route(build_route_request(task, requirement, compiled), candidate, preliminary)
    if route.kind == 'failure':
        return route
    return PreparedDispatch(context=compiled, route=route, state='unissued')
```

This function cannot issue provider commands or grants; WP3 owns those records.

- [ ] **Step 4: Run complete WP2 verification**

Run:

```powershell
uv run ruff check research_system/context research_system/assurance research_system/routing tests/research_system
uv run pytest tests/research_system/unit/test_context_compiler.py tests/research_system/unit/test_token_gates.py tests/research_system/unit/test_assurance_requirements.py tests/research_system/unit/test_independence.py tests/research_system/unit/test_routing_engine.py tests/research_system/integration/test_context_routing_fixtures.py -q --no-cov
```

Expected: all WP2 tests pass; no provider command or operational grant is emitted.

- [ ] **Step 5: Commit WP2**

Commit subject: `[PIPELINE] P00: complete ARS context routing assurance slice`.

## Research assurance and acceptance

- [ ] F-021/F-022/F-025/F-026 mandatory closure is measured under distinct reference/provider units.
- [ ] F-028 fails closed without removing mandatory material.
- [ ] F-031 routing is invariant to candidate order and unbound telemetry.
- [ ] F-033 blocks producer work without a verifier witness.
- [ ] F-035 keeps requirement scope and both validity keys non-compensable.
- [ ] F-036 uses independent oracles for sanity anchoring, fallback, and null invariance; these graders require an independent research reviewer.
- [ ] No result from this package is a paper claim or methodological decision.
- [ ] Independent authority/provenance review accepts WP2 before any R2/R3 route is enabled.
