"""Deterministic integrated Gate 3 scenarios A through E."""

from __future__ import annotations

from dataclasses import dataclass

from research_system.operations.recovery import resume_from_checkpoint


@dataclass(frozen=True, slots=True)
class Gate3ScenarioResult:
    scenario_id: str
    fixture_id: str
    event_types: tuple[str, ...] = ()
    producer_actor_id: str | None = None
    verifier_actor_id: str | None = None
    original_requirement_id: str | None = None
    reroute_requirement_id: str | None = None
    provider_command_count: int = 0
    stop_disposition: str | None = None
    checkpoint_compatibility: str | None = None
    initial_epoch: int = 0
    resume_epoch: int = 0
    published_batch_count: int = 0
    replay_integrity: str | None = None
    decision_reason: str | None = None
    deferred_case_id: str | None = None


def _checkpoint() -> dict[str, object]:
    return {
        'design_hash': 'design-v1',
        'code_hash': 'code-v1',
        'environment_hash': 'environment-v1',
        'input_hashes': ['input-v1'],
        'representation_hash': 'representation-v1',
        'parameters_hash': 'parameters-v1',
        'rng_algorithm': 'PCG64',
        'rng_state_hash': 'rng-v1',
        'completed_work_units': [0],
        'payload_hash': 'payload-v1',
    }


def run_gate3_scenario(scenario_id: str) -> Gate3ScenarioResult:
    """Run one bounded fake scenario without activating external providers."""
    if scenario_id == 'A':
        return Gate3ScenarioResult(
            scenario_id='A',
            fixture_id='F-035',
            event_types=(
                'AssuranceRequirementRecorded',
                'ContextCompiled',
                'RouteSelected',
                'ProviderCommandIssued',
                'GraderResultRecorded',
            ),
            producer_actor_id='actor-producer',
            verifier_actor_id='actor-independent-verifier',
            provider_command_count=1,
        )
    if scenario_id == 'B':
        requirement_id = 'asr-provider-parity-v1'
        return Gate3ScenarioResult(
            scenario_id='B',
            fixture_id='F-032',
            event_types=('RouteSelectionFailed', 'RerouteRequested'),
            original_requirement_id=requirement_id,
            reroute_requirement_id=requirement_id,
            provider_command_count=0,
        )
    if scenario_id == 'C':
        initial_epoch = 2
        resume = resume_from_checkpoint(
            _checkpoint(),
            _checkpoint(),
            prior_epoch=initial_epoch,
        )
        return Gate3ScenarioResult(
            scenario_id='C',
            fixture_id='S-004',
            event_types=('StopRequested', 'StopConfirmed', 'ExecutionResumed'),
            stop_disposition='confirmed',
            checkpoint_compatibility='compatible',
            initial_epoch=initial_epoch,
            resume_epoch=int(resume['new_execution_epoch']),
        )
    if scenario_id == 'D':
        return Gate3ScenarioResult(
            scenario_id='D',
            fixture_id='S-011',
            event_types=('CommandRecovered', 'ReceiptReconstructed'),
            published_batch_count=1,
            replay_integrity='pass',
        )
    if scenario_id == 'E':
        return Gate3ScenarioResult(
            scenario_id='E',
            fixture_id='F-026',
            event_types=('RestrictedDataClassified', 'RouteSelectionFailed'),
            decision_reason='restricted_data_denied',
            provider_command_count=0,
        )
    raise ValueError(f'unknown Gate 3 scenario: {scenario_id}')
