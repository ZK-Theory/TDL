"""End-to-end P0 scenarios, coverage closure, and release blocking."""

from copy import deepcopy

from research_system.evals.catalogue import P0_CASES
from research_system.evals.coverage import load_p0_coverage
from research_system.evals.harness import decide_p0_release, run_p0_coverage
from research_system.evals.scenarios import run_gate3_scenario


def test_scenario_a_r2_two_stage_production_and_verification():
    result = run_gate3_scenario('A')
    assert result.event_types.index('RouteSelected') < result.event_types.index(
        'ProviderCommandIssued'
    )
    assert result.producer_actor_id != result.verifier_actor_id


def test_scenario_b_provider_outage_preserves_requirements():
    result = run_gate3_scenario('B')
    assert result.fixture_id == 'F-032'
    assert result.original_requirement_id == result.reroute_requirement_id
    assert result.provider_command_count == 0
    assert result.deferred_case_id is None


def test_scenario_c_long_run_stop_checkpoint_resume():
    result = run_gate3_scenario('C')
    assert result.stop_disposition == 'confirmed'
    assert result.checkpoint_compatibility == 'compatible'
    assert result.resume_epoch == result.initial_epoch + 1


def test_scenario_d_writer_crash_restore_has_zero_or_one_batch():
    result = run_gate3_scenario('D')
    assert result.fixture_id == 'S-011'
    assert result.published_batch_count in {0, 1}
    assert result.replay_integrity == 'pass'
    assert result.deferred_case_id is None


def test_scenario_e_restricted_data_denied_before_provider_issue():
    result = run_gate3_scenario('E')
    assert result.decision_reason == 'restricted_data_denied'
    assert 'ProviderCommandIssued' not in result.event_types


def test_p0_coverage_is_exact_and_gate5_deferrals_are_restrictive():
    coverage = load_p0_coverage()
    assert dict(coverage.selected_fixture_revisions) == {
        fixture_id: 'r1' for fixture_id in sorted(P0_CASES)
    }
    assert {item.fixture_id for item in coverage.omitted_gate5} == {
        'S-014', 'S-015', 'S-016'
    }
    assert all(item.status == 'capability_disabled' for item in coverage.omitted_gate5)
    assert all(item.required_before == 'gate5' for item in coverage.omitted_gate5)
    assert coverage.transport == 'fake'
    assert coverage.accepted_grader_classes == ('D', 'O', 'P', 'R', 'T')
    assert coverage.unavailable_grader_classes == ('H', 'M')


def test_candidate_run_has_exact_required_result_key_closure_and_blocks():
    document = run_p0_coverage()
    result_keys = [tuple(item['result_key']) for item in document['results']]
    assert document['fixture_count'] == 37
    assert len(result_keys) == len(set(result_keys))
    assert set(result_keys) == set(map(tuple, document['required_result_keys']))
    assert document['candidate_status'] == 'blocked'
    assert not {'S-014', 'S-015', 'S-016'}.intersection(
        item['fixture_id'] for item in document['results']
    )


def test_release_is_blocked_by_unavailable_mh_and_does_not_accept_gate5():
    assessment = decide_p0_release(run_p0_coverage())
    assert assessment.decision.decision == 'blocked'
    assert assessment.missing == ()
    assert assessment.unexpected == ()
    assert assessment.duplicates == ()
    assert assessment.decision.human_authority_id is None
    assert assessment.decision.disabled_or_constrained_capability == (
        'foundation_release_and_pilot_promotion'
    )


def test_release_blocks_missing_required_result_without_inferred_pass():
    document = deepcopy(run_p0_coverage())
    document['results'].pop()
    assessment = decide_p0_release(document)
    assert assessment.decision.decision == 'blocked'
    assert len(assessment.missing) == 1
    assert assessment.unexpected == ()
