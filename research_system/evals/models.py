"""Immutable W6 evaluation records and closed vocabularies."""

from __future__ import annotations

from dataclasses import dataclass, replace

from research_system.ids import validate_id

GATE_STAGES = frozenset(
    {
        'interface_review',
        'p0_materialization',
        'foundation_release',
        'pilot_promotion',
    }
)
FIXTURE_STATUSES = frozenset(
    {
        'candidate',
        'source_verified',
        'authored',
        'calibrated',
        'active',
        'rejected',
        'quarantined',
        'superseded',
    }
)
GRADER_CLASSES = frozenset({'D', 'T', 'R', 'M', 'H', 'O', 'P'})
VERDICTS = frozenset({'pass', 'fail', 'unable_to_grade', 'fixture_error'})
RUN_STATES = frozenset(
    {
        'declared',
        'executing',
        'evidence_complete',
        'grading',
        'decided',
        'stopped',
        'failed',
    }
)
RELEASE_DECISIONS = frozenset({'pass', 'fail', 'blocked', 'exception_limited'})
RETENTION_CLASSES = frozenset({'R0', 'R1', 'R2'})

ResultKey = tuple[str, str, str, str, str]


def _require_choice(value: str, choices: frozenset[str], label: str) -> None:
    if value not in choices:
        raise ValueError(f'invalid {label}: {value}')


def _require_nonempty(value: str, label: str) -> None:
    if not value:
        raise ValueError(f'{label} is required')


@dataclass(frozen=True, slots=True)
class GraderRequirement:
    """One exact grader obligation declared by a fixture revision."""

    grader_id: str
    grader_class: str
    grader_version: str
    critical: bool
    required: bool
    independence_requirement: str

    def __post_init__(self) -> None:
        _require_choice(self.grader_class, GRADER_CLASSES, 'grader_class')
        _require_nonempty(self.grader_id, 'grader_id')
        _require_nonempty(self.grader_version, 'grader_version')
        _require_nonempty(
            self.independence_requirement,
            'independence_requirement',
        )


@dataclass(frozen=True, slots=True)
class FixtureDefinition:
    """Immutable executable description of one W6 fixture revision."""

    fixture_id: str
    fixture_revision: str
    title: str
    owner: str
    status: str
    incident_basis: str
    input_fidelity: str
    risk_tier: str
    assurance_lanes: tuple[str, ...]
    failure_class: str
    priority: str
    gate_stage: str
    source_manifest_hash: str
    decision_refs: tuple[str, ...]
    policy_versions: tuple[str, ...]
    schema_versions: tuple[str, ...]
    confidentiality: str
    permitted_consumers: tuple[str, ...]
    setup_hash: str
    stimulus_hash: str
    pre_control_oracle_hash: str
    post_control_oracle_hash: str
    required_trajectory: tuple[str, ...]
    forbidden_trajectory: tuple[str, ...]
    allowed_terminal_states: tuple[str, ...]
    expected_stop_semantics: str
    required_graders: tuple[GraderRequirement, ...]
    threshold_policy_ids: tuple[str, ...]
    required_evidence_classes: tuple[str, ...]
    known_bad_reference_hash: str
    known_good_reference_hash: str
    mutation_ids: tuple[str, ...]
    safe_variation_ids: tuple[str, ...]
    calibration_record_id: str | None
    retention_class: str
    retention_rule_id: str
    redaction_policy_id: str

    def __post_init__(self) -> None:
        _require_choice(self.priority, frozenset({'P0', 'P1'}), 'priority')
        _require_choice(self.gate_stage, GATE_STAGES, 'gate_stage')
        _require_choice(self.status, FIXTURE_STATUSES, 'fixture status')
        if self.retention_class == 'R3':
            raise ValueError('prohibited retention_class: R3')
        _require_choice(
            self.retention_class,
            RETENTION_CLASSES,
            'retention_class',
        )
        if not self.required_graders:
            raise ValueError('required_graders must not be empty')
        if not self.permitted_consumers:
            raise ValueError('permitted_consumers must not be empty')


@dataclass(frozen=True, slots=True)
class TraceEnvelope:
    """Minimized, ordered evidence carrier for one evaluation run."""

    trace_id: str
    evaluation_run_id: str
    fixture_id: str
    fixture_revision: str
    subject_id: str
    subject_hash: str
    items: tuple[dict[str, object], ...]
    issued_commands: tuple[dict[str, object], ...]
    route_decision_id: str | None
    routing_evidence_snapshot_id: str | None
    canonical_policy_bundle_id: str | None
    adapter_manifest_version: str | None
    resource_record_ids: tuple[str, ...]
    tool_records: tuple[dict[str, object], ...]
    artefact_refs: tuple[str, ...]
    review_refs: tuple[str, ...]
    decision_refs: tuple[str, ...]
    claim_refs: tuple[str, ...]
    present_evidence_classes: tuple[str, ...]
    missing_segments: tuple[str, ...]
    clock_source: str
    ordering_method: str
    redaction_record_hash: str
    content_hash: str
    trace_complete: bool = False

    def __post_init__(self) -> None:
        validate_id(self.trace_id, 'trace')
        validate_id(self.evaluation_run_id, 'evaluation_run')
        if self.trace_complete and self.missing_segments:
            raise ValueError('complete_trace_has_missing_segments')

    def validate_terminal_evidence(self) -> None:
        """Reject issued commands without a receipt or explicit missing record."""
        incomplete = [
            str(item.get('command_id', '<unknown>'))
            for item in self.issued_commands
            if not item.get('terminal_ref') and not item.get('missing_evidence_ref')
        ]
        if incomplete:
            raise ValueError(
                'terminal_or_missing_evidence_required: ' + ','.join(incomplete)
            )

    def missing_evidence_classes(
        self,
        required_evidence_classes: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return declared evidence classes absent from this trace."""
        present = set(self.present_evidence_classes)
        return tuple(
            evidence
            for evidence in required_evidence_classes
            if evidence not in present
        )


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """One immutable evaluation transaction and its lifecycle bindings."""

    evaluation_run_id: str
    fixture_id: str
    fixture_revision: str
    subject_type: str
    subject_version: str
    subject_hash: str
    run_role: str
    attempt_number: int
    coverage_manifest_id: str
    policy_bundle_hash: str
    provider_variant: str
    runtime_variant: str
    state: str
    route_decision_id: str | None = None
    resource_request_id: str | None = None
    start_sequence_position: int | None = None
    end_sequence_position: int | None = None
    trace_ids: tuple[str, ...] = ()
    provider_receipt_ids: tuple[str, ...] = ()
    operational_record_ids: tuple[str, ...] = ()
    grader_result_ids: tuple[str, ...] = ()
    exception_refs: tuple[str, ...] = ()
    quarantine_refs: tuple[str, ...] = ()
    terminal_summary: str | None = None
    retry_of: str | None = None
    supersedes: str | None = None

    def __post_init__(self) -> None:
        validate_id(self.evaluation_run_id, 'evaluation_run')
        _require_choice(self.state, RUN_STATES, 'evaluation run state')
        if self.run_role not in {'baseline', 'candidate'}:
            raise ValueError(f'invalid run_role: {self.run_role}')
        if self.attempt_number < 1:
            raise ValueError('attempt_number must be positive')

    def retry(self, new_evaluation_run_id: str) -> EvaluationRun:
        """Create a new declared run linked to this terminal attempt."""
        if new_evaluation_run_id == self.evaluation_run_id:
            raise ValueError('retry requires new evaluation_run_id')
        validate_id(new_evaluation_run_id, 'evaluation_run')
        return replace(
            self,
            evaluation_run_id=new_evaluation_run_id,
            attempt_number=self.attempt_number + 1,
            state='declared',
            start_sequence_position=None,
            end_sequence_position=None,
            trace_ids=(),
            provider_receipt_ids=(),
            operational_record_ids=(),
            grader_result_ids=(),
            exception_refs=(),
            quarantine_refs=(),
            terminal_summary=None,
            retry_of=self.evaluation_run_id,
            supersedes=None,
        )


@dataclass(frozen=True, slots=True)
class GraderResult:
    """One exact grader judgment over immutable subject and trace hashes."""

    grader_result_id: str
    evaluation_run_id: str
    fixture_id: str
    fixture_revision: str
    grader_id: str
    grader_class: str
    grader_version: str
    verdict: str
    severity: str
    critical: bool
    required: bool
    subject_hash: str
    trace_hash: str
    oracle_hash: str
    policy_hash: str
    threshold_policy_hash: str
    evidence_refs: tuple[str, ...]
    independently_recomputed: bool
    producer_family: str
    grader_family: str
    context_relationship: str
    limitations: tuple[str, ...]
    redactions: tuple[str, ...]
    duration_ms: int
    cost_microunits: int
    executed_by_actor_id: str
    supersedes: str | None = None

    def __post_init__(self) -> None:
        validate_id(self.grader_result_id, 'grader_result')
        validate_id(self.evaluation_run_id, 'evaluation_run')
        validate_id(self.executed_by_actor_id, 'actor')
        _require_choice(self.grader_class, GRADER_CLASSES, 'grader_class')
        _require_choice(self.verdict, VERDICTS, 'verdict')

    @property
    def result_key(self) -> ResultKey:
        """Return the immutable key used for exact closure."""
        return (
            self.fixture_id,
            self.fixture_revision,
            self.grader_id,
            self.grader_class,
            self.grader_version,
        )


@dataclass(frozen=True, slots=True)
class CoverageManifest:
    """Pre-run declaration of the exact evidence a change must prove."""

    coverage_manifest_id: str
    changed_component: str
    baseline_version: str
    candidate_version: str
    affected_capabilities: tuple[str, ...]
    risk_tiers: tuple[str, ...]
    assurance_lanes: tuple[str, ...]
    provider_variants: tuple[str, ...]
    runtime_variants: tuple[str, ...]
    gate_stage: str
    selected_fixture_revisions: tuple[tuple[str, str], ...]
    omitted_fixtures: tuple[tuple[str, str, str], ...]
    required_result_keys: tuple[ResultKey, ...]
    required_parity_controls: tuple[str, ...]
    required_operations_scenarios: tuple[str, ...]
    expected_evidence_classes: tuple[str, ...]
    release_gate_policy_version: str

    def __post_init__(self) -> None:
        _require_nonempty(self.coverage_manifest_id, 'coverage_manifest_id')
        _require_choice(self.gate_stage, GATE_STAGES, 'gate_stage')


@dataclass(frozen=True, slots=True)
class ReleaseGateDecision:
    """Attributed non-aggregated decision over one complete evidence set."""

    release_gate_decision_id: str
    coverage_manifest_id: str
    baseline_identity: str
    candidate_identity: str
    evidence_snapshot_hash: str
    required_verdicts: tuple[tuple[ResultKey, str], ...]
    critical_failures: tuple[ResultKey, ...]
    parity_status: str
    operations_status: str
    decision: str
    decided_at: str
    canonical_event_ref: str
    exception_scope: str | None = None
    exception_expiry: str | None = None
    disabled_or_constrained_capability: str | None = None
    rationale: str | None = None
    human_authority_id: str | None = None
    supersedes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty(
            self.release_gate_decision_id,
            'release_gate_decision_id',
        )
        _require_choice(self.decision, RELEASE_DECISIONS, 'decision')
        if self.decision == 'exception_limited' and not all(
            (
                self.exception_scope,
                self.exception_expiry,
                self.disabled_or_constrained_capability,
                self.human_authority_id,
            )
        ):
            raise ValueError('exception_limited requires bounded authority')
