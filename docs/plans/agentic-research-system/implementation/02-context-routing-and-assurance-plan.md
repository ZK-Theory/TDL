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

## Task 1: Freeze exact W3 context and W5 assurance models

- [ ] **Step 1: Write failing model/schema tests**

```python
import pytest

from research_system.assurance.models import (
    CORE_LANES, AssuranceRequirement, LaneRequirement,
)
from research_system.assurance.requirements import (
    GrantBackedAuthorityPolicy, validate_requirement,
)
from research_system.context.models import ContextCandidate
from research_system.errors import ArsError


def _requirement(
    assurance_requirement_id, prospective_producer_actor_id,
    author_actor_id, scope_reviewer_actor_id, accepting_actor_id,
    requested_risk='R2', action_semantic_risk='R2',
):
    lanes = tuple(
        LaneRequirement(
            lane, 'required', 'P0 test', ('governing-hash',),
            ('proof-1',), ('scientific_review',), 'blocked',
        )
        for lane in sorted(CORE_LANES)
    )
    return AssuranceRequirement(
        assurance_requirement_id, 1, 'a' * 64, 'tsk_' + '1' * 32, 1,
        'implementation', 0, 'act-owner', author_actor_id,
        scope_reviewer_actor_id, accepting_actor_id,
        prospective_producer_actor_id, 'arp-producer', requested_risk,
        requested_risk, action_semantic_risk, 'I1', lanes, (), 'b' * 64,
    )


def test_context_candidate_is_compiled_but_unissued():
    candidate = ContextCandidate('ctx_' + '1' * 32, 'ctx_' + '2' * 32, 'a' * 64, 10, 3, 'ref-v1')
    assert candidate.state == 'compiled'
    assert candidate.state not in {'validated', 'issued'}


def test_mandatory_source_cannot_be_excused_by_omission_reason():
    candidate = ContextCandidate('ctx_' + '3' * 32, 'ctx_' + '4' * 32, 'b' * 64, 20, 4, 'ref-v1')
    with pytest.raises(ArsError, match='mandatory source omitted'):
        candidate.validate_manifest(
            required={'src-a', 'src-b'},
            included={'src-a'},
            optional_candidates={'src-c'},
            omissions={'src-b': 'access_denied'},
        )


def test_assurance_requirement_uses_exact_six_w5_lanes_and_identity():
    assert CORE_LANES == frozenset({
        'topology', 'stochastic_null', 'statistical_panel',
        'representation', 'output_provenance', 'paper_claim',
    })
    requirement = _requirement(
        assurance_requirement_id='asr_' + '5' * 32,
        prospective_producer_actor_id='act-producer',
        author_actor_id='act-author',
        scope_reviewer_actor_id='act-reviewer',
        accepting_actor_id='act-manager',
    )
    assert {item.lane for item in requirement.lanes} == CORE_LANES


def test_producer_cannot_self_confirm_r2_scope_or_r3_action():
    requirement = _requirement(
        assurance_requirement_id='asr_' + '6' * 32,
        prospective_producer_actor_id='act-producer',
        author_actor_id='act-producer',
        scope_reviewer_actor_id='act-producer',
        accepting_actor_id='act-producer',
        requested_risk='R2',
        action_semantic_risk='R3',
    )
    with pytest.raises(ArsError, match='assurance_requirement_scope_unconfirmed'):
        validate_requirement(
            requirement,
            GrantBackedAuthorityPolicy({
                'act-producer': frozenset({
                    'accept_r3_assurance_requirement',
                }),
            }),
        )
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_context_compiler.py tests/research_system/unit/test_assurance_requirements.py -q --no-cov`

Expected: missing context/assurance modules.

- [ ] **Step 3: Implement immutable owner-defined models**

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

    def validate_manifest(self, required, included, optional_candidates, omissions):
        missing = set(required) - set(included)
        if missing:
            raise ArsError(f'mandatory source omitted: {sorted(missing)}')
        invalid_omissions = set(omissions) - set(optional_candidates)
        if invalid_omissions:
            raise ArsError(f'non-optional omission: {sorted(invalid_omissions)}')
```

```python
# research_system/assurance/models.py
from dataclasses import dataclass

CORE_LANES = frozenset({
    'topology', 'stochastic_null', 'statistical_panel',
    'representation', 'output_provenance', 'paper_claim',
})


@dataclass(frozen=True)
class LaneRequirement:
    lane: str
    disposition: str
    rationale: str
    governing_ref_hashes: tuple[str, ...]
    proof_obligation_ids: tuple[str, ...]
    reviewer_capabilities: tuple[str, ...]
    failure_consequence: str


@dataclass(frozen=True)
class AssuranceRequirement:
    assurance_requirement_id: str
    revision: int
    content_hash: str
    task_id: str
    task_revision: int
    purpose: str
    source_position: int
    owner_actor_id: str
    author_actor_id: str
    scope_reviewer_actor_id: str
    accepting_actor_id: str
    prospective_producer_actor_id: str
    prospective_producer_profile_id: str
    requested_risk: str
    w5_epistemic_risk_floor: str
    action_semantic_risk: str
    requirement_relationship_grade: str
    lanes: tuple[LaneRequirement, ...]
    human_gate_ids: tuple[str, ...]
    currency_hash: str
```

`requirements.py` validates the exact lane-set equality, non-empty rationale and authority for every `not_applicable`, R2 producer-distinct scope confirmation at I1 or stronger, action-semantic risk escalation, and R3 I2 plus attributed authority resolved from canonical grant policy. Software, mathematical, operations, and privacy remain assertion/evidence classes or reviewed pack extensions; they are not silently added to W5's six core lanes.

- [ ] **Step 4: Run targeted tests**

Run: `uv run pytest tests/research_system/unit/test_context_compiler.py tests/research_system/unit/test_assurance_requirements.py -q --no-cov`

Expected: exact owner identity/lane, mandatory-closure, and producer-independent requirement tests pass.

- [ ] **Step 5: Commit model freeze**

Commit subject: `[PIPELINE] P00: add ARS context and assurance models`.

## Task 2: Implement deterministic mandatory closure and two unit-safe token gates

- [ ] **Step 1: Write failing F-021/F-022/F-025–F-028 tests**

```python
import pytest

from research_system.canonical import sha256_hex
from research_system.context.compiler import compile_candidate, validate_provider_gate
from research_system.context.errors import ContextBudgetExceeded
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.tokenizers import (
    ProviderCountEvidence, ReferenceRegexV1, Utf8ByteEvidenceV1,
)
from research_system.errors import ArsError


def _fragment(source_id, authority, content, mandatory=True):
    return SourceFragment(
        source_id, 'r1', authority, mandatory, content,
        sha256_hex(content.encode('utf-8')),
    )


def test_f021_missing_amendment_blocks_instead_of_becoming_omission():
    baseline = [_fragment('design-r1', 90, 'original design')]
    with pytest.raises(ArsError, match='mandatory source omitted'):
        compile_candidate(
            baseline, ContextProfile('r2', 100), ReferenceRegexV1(),
            required_source_ids={'design-r1', 'amendment-r2'},
        )


def test_f022_f025_f026_complete_mandatory_closure_is_measured():
    required_ids = {
        'scope-22', 'amendment-r2', 'frozen-transform',
        'null-preflight', 'vintage', 'seed', 'stop-rule',
    }
    fragments = [_fragment(name, 100, name) for name in sorted(required_ids)]
    candidate = compile_candidate(
        fragments, ContextProfile('r2', 100), ReferenceRegexV1(),
        required_source_ids=required_ids,
    )
    provider = ProviderCountEvidence(
        counter_id='fake-codex-upper-v1', units='provider_tokens', count=12,
        exact=False, provider='codex', model='p0-fake',
        rendering_revision='render-v1', evidence_revision='eval-v1',
    )
    assert candidate.reference_count > 0
    assert validate_provider_gate(candidate, provider, usable_capacity_tokens=16) == provider
    assert Utf8ByteEvidenceV1().count(candidate.rendered_content).units == 'utf8_bytes'


def test_f027_index_deletion_preserves_mandatory_hash():
    profile = ContextProfile('r2', reference_limit=100)
    mandatory = _fragment('direct-source', 100, 'governing evidence')
    optional = _fragment('optional-index', 1, 'supplement', mandatory=False)
    with_index = compile_candidate([mandatory, optional], profile, ReferenceRegexV1(), {'direct-source'})
    direct = compile_candidate([mandatory], profile, ReferenceRegexV1(), {'direct-source'})
    assert with_index.mandatory_hash == direct.mandatory_hash


def test_f028_either_token_gate_blocks_without_truncation():
    fragment = _fragment('mandatory', 100, 'one two three')
    with pytest.raises(ContextBudgetExceeded, match='reference_token_gate'):
        compile_candidate(
            [fragment], ContextProfile('r2', 2), ReferenceRegexV1(),
            required_source_ids={'mandatory'},
        )
    candidate = compile_candidate(
        [fragment], ContextProfile('r2', 100), ReferenceRegexV1(),
        required_source_ids={'mandatory'},
    )
    overflow = ProviderCountEvidence(
        counter_id='fake-codex-upper-v1', units='provider_tokens', count=13,
        exact=False, provider='codex', model='p0-fake',
        rendering_revision='render-v1', evidence_revision='eval-v1',
    )
    with pytest.raises(ContextBudgetExceeded, match='bound_provider_capacity_gate'):
        validate_provider_gate(candidate, overflow, usable_capacity_tokens=16)
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_token_gates.py tests/research_system/integration/test_context_routing_fixtures.py -q --no-cov`

Expected: compiler/counter functions absent.

- [ ] **Step 3: Implement versioned reference, byte-diagnostic, and provider-token evidence**

```python
# research_system/context/tokenizers.py
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CountEvidence:
    counter_id: str
    units: str
    count: int
    exact: bool


@dataclass(frozen=True)
class ProviderCountEvidence:
    counter_id: str
    units: str
    count: int
    exact: bool
    provider: str
    model: str
    rendering_revision: str
    evidence_revision: str


class ReferenceRegexV1:
    counter_id = 'ars-reference-regex-v1'

    def count(self, text: str) -> CountEvidence:
        count = len(re.findall(r'\w+|[^\w\s]', text, flags=re.UNICODE))
        return CountEvidence(self.counter_id, 'ars_reference_tokens', count, True)


class Utf8ByteEvidenceV1:
    counter_id = 'utf8-byte-evidence-v1'

    def count(self, text: str) -> CountEvidence:
        return CountEvidence(self.counter_id, 'utf8_bytes', len(text.encode('utf-8')), True)
```

`ProviderCountEvidence` is supplied through the W7 port. An exact provider tokenizer or evaluated conservative upper bound must already express its count in `provider_tokens` for the named provider/model/rendering/evidence revision. UTF-8 bytes remain diagnostic and are never compared with token capacity.

```python
# research_system/context/compiler.py
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id
from research_system.context.models import ContextCandidate


def build_candidate(rendered, ordered, mandatory, evidence, omissions=None):
    source_manifest = tuple(
        {
            'source_id': item.source_id, 'revision': item.revision,
            'content_hash': item.content_hash, 'mandatory': item.mandatory,
        }
        for item in ordered
    )
    mandatory_manifest = tuple(
        item for item in source_manifest if item['source_id'] in {
            source.source_id for source in mandatory
        }
    )
    return ContextCandidate(
        context_candidate_id=new_id('context'),
        manifest_id=new_id('context'),
        content_hash=sha256_hex(rendered.encode('utf-8')),
        utf8_bytes=len(rendered.encode('utf-8')),
        reference_count=evidence.count,
        reference_counter_id=evidence.counter_id,
        rendered_content=rendered,
        source_ids=tuple(item['source_id'] for item in source_manifest),
        mandatory_source_ids=tuple(item['source_id'] for item in mandatory_manifest),
        mandatory_hash=sha256_hex(canonical_bytes(list(mandatory_manifest))),
        source_manifest=source_manifest,
        conflicts=(),
        omissions=dict(omissions or {}),
    )


def compile_candidate(fragments, profile, reference_counter, required_source_ids, optional_source_ids=None, omissions=None):
    included_ids = {item.source_id for item in fragments}
    missing = set(required_source_ids) - included_ids
    if missing:
        raise ArsError(f'mandatory source omitted: {sorted(missing)}')
    ordered = sorted(
        fragments, key=lambda item: (-item.authority_rank, item.source_id, item.revision)
    )
    mandatory = [item for item in ordered if item.source_id in required_source_ids]
    rendered = '\n\n'.join(item.content for item in ordered)
    evidence = reference_counter.count(rendered)
    if evidence.units != 'ars_reference_tokens':
        raise ArsError('invalid reference-token units')
    if evidence.count > profile.reference_limit:
        raise ContextBudgetExceeded('reference_token_gate')
    candidate = build_candidate(rendered, ordered, mandatory, evidence, omissions)
    candidate.validate_manifest(
        required_source_ids, included_ids,
        ({item.source_id for item in ordered if not item.mandatory}
         | set(optional_source_ids or ())) - required_source_ids,
        candidate.omissions,
    )
    return candidate


def validate_provider_gate(candidate, evidence, usable_capacity_tokens):
    if evidence.units != 'provider_tokens':
        raise ArsError('provider count must use provider_tokens')
    if not evidence.provider or not evidence.model or not evidence.rendering_revision:
        raise ArsError('provider count scope incomplete')
    limit = usable_capacity_tokens * 80 // 100
    if evidence.count > limit:
        raise ContextBudgetExceeded('bound_provider_capacity_gate')
    return evidence
```

The W2 owner catalogue assigns `ctx` to the context-packet identity family. Candidate, manifest, packet, and addendum identities therefore intentionally use the registered `context` kind and `ctx_` prefix; their schemas and content hashes distinguish object roles rather than inventing unowned ID kinds.

`build_candidate` records source IDs/revisions/hashes, conflicts, optional omissions, reference units, UTF-8 bytes, and candidate/mandatory hashes. Provider evidence remains a separately bound W7/W4 record and cannot be manufactured by W3.

- [ ] **Step 4: Verify P-028 closure and write the sizing record**

Run:

```powershell
uv run pytest tests/research_system/unit/test_token_gates.py -q --no-cov
uv run pytest tests/research_system/integration/test_context_routing_fixtures.py -k 'f021 or f022 or f025 or f026 or f027 or f028' -q --no-cov
```

Expected: known-bad omission/overflow paths fail; controlled candidates preserve complete mandatory closure; F-021/F-022/F-025/F-026 each emit reference-token, provider-token, UTF-8-byte, provider/model/rendering, capacity, reserve, and verdict fields for every variant in `p0-variant-matrix.yaml`.

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

## Task 4: Implement F-031/F-033 eligibility-first routing and freeze `PreparedDispatch`

- [ ] **Step 1: Write failing F-031/F-033 routing and prepared-dispatch tests**

Tests cover candidate enumeration permutation, live telemetry outside the bound snapshot, capability-family suspension, missing verifier witness, relationship-grade recomputation, and exact construction of the shared unissued `PreparedDispatch`. F-032 outage and F-034 permission/root/sensitivity/decomposition integration belong to WP3/WP4.

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest tests/research_system/unit/test_routing_engine.py -q --no-cov`

Expected: routing engine absent.

- [ ] **Step 3: Implement candidate evaluation and stable ranking**

```python
# research_system/routing/engine.py
from dataclasses import dataclass
from typing import Protocol


class RoutingEvidenceSnapshot(Protocol):
    routing_evidence_snapshot_id: str

    def hard_gate_failures(self, request, candidate) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class RouteCandidate:
    profile_id: str
    capability_margin: int
    independence_margin: int
    limitation_count: int
    snapshot_reliability: int
    snapshot_latency_ms: int
    snapshot_cost_units: int


@dataclass(frozen=True)
class PreparedDispatch:
    attempt_id: str
    assurance_requirement_id: str
    assurance_requirement_hash: str
    context: object
    route: object
    provider_evidence_id: str
    provider_evidence_hash: str
    operational_evidence_id: str
    operational_evidence_hash: str
    expires_at: str
    state: str = 'unissued'


REJECTION_ORDER = (
    'provider_unavailable', 'capability_insufficient', 'risk_exceeded',
    'authority_missing', 'permission_missing', 'context_budget_exceeded',
    'assurance_unsatisfied', 'independence_unavailable',
    'fixture_coverage_missing', 'resource_unavailable',
)


def select_route(request, candidates, evidence: RoutingEvidenceSnapshot):
    evaluated = []
    for candidate in sorted(candidates, key=lambda item: item.profile_id):
        failures = evidence.hard_gate_failures(request, candidate)
        unknown = set(failures) - set(REJECTION_ORDER)
        if unknown:
            raise ValueError(f'unknown route rejection reason: {sorted(unknown)}')
        evaluated.append((candidate, tuple(sorted(failures, key=REJECTION_ORDER.index))))
    eligible = [item for item, failures in evaluated if not failures]
    if not eligible:
        return {
            'kind': 'failure', 'request_id': request.request_id,
            'routing_evidence_snapshot_id': evidence.routing_evidence_snapshot_id,
            'evaluated': tuple(evaluated),
        }
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
    return {
        'kind': 'selected', 'request_id': request.request_id,
        'routing_evidence_snapshot_id': evidence.routing_evidence_snapshot_id,
        'winner': winner, 'evaluated': tuple(evaluated),
    }
```

`RoutingEvidenceSnapshot.hard_gate_failures()` is the single owned gate port. Its concrete W4 implementation follows section 12 exactly, including candidate-specific provider counting and a currently eligible verifier witness before R2/R3 producer eligibility. The immutable `routing_evidence_snapshot_id` binds every returned reason; live telemetry is not an input. `select_route()` constructs the failure/selection records directly, so no unowned `evaluate_hard_gates`, `route_failure`, or `route_decision` helper remains.

- [ ] **Step 4: Verify deterministic routing**

Run:

```powershell
uv run pytest tests/research_system/unit/test_routing_engine.py -q --no-cov
uv run pytest tests/research_system/integration/test_context_routing_fixtures.py -k 'f031 or f033 or prepared_dispatch' -q --no-cov
```

Expected: permutations produce byte-identical decision data; missing witness blocks before dispatch; the prepared record contains every WP3-consumed field and remains `unissued`.

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
def plan_dispatch(
    task, attempt_id, requirement, compiled, candidates,
    provider_evidence, operational_evidence,
):
    assert_requirement_current(task, requirement)
    preliminary = bind_pre_route_evidence(provider_evidence, operational_evidence)
    route = select_route(
        build_route_request(task, requirement, compiled), candidates, preliminary
    )
    if route['kind'] == 'failure':
        return route
    return PreparedDispatch(
        attempt_id=attempt_id,
        assurance_requirement_id=requirement.assurance_requirement_id,
        assurance_requirement_hash=requirement.content_hash,
        context=compiled,
        route=route,
        provider_evidence_id=provider_evidence.evidence_id,
        provider_evidence_hash=provider_evidence.content_hash,
        operational_evidence_id=operational_evidence.evidence_id,
        operational_evidence_hash=operational_evidence.content_hash,
        expires_at=min(provider_evidence.expires_at, operational_evidence.expires_at),
        state='unissued',
    )
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

- [ ] F-021/F-022/F-025/F-026 mandatory closure is compiled and measured under distinct reference/provider units for every exact P0 variant.
- [ ] F-028 fails closed without removing mandatory material.
- [ ] F-031 routing is invariant to candidate order and unbound telemetry.
- [ ] F-033 blocks producer work without a verifier witness.
- [ ] F-035 keeps requirement scope and both validity keys non-compensable.
- [ ] F-036 uses independent oracles for sanity anchoring, fallback, and null invariance; these graders require an independent research reviewer.
- [ ] No result from this package is a paper claim or methodological decision.
- [ ] Independent authority/provenance review accepts WP2 before any R2/R3 route is enabled.
