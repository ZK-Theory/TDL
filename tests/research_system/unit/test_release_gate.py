from types import SimpleNamespace

import pytest

from research_system.evals.models import GraderResult
from research_system.evals.release import decide_release


UUID7 = "01978abc-0001-7000-8000-000000000001"
STATE_KEY = ("F-001", "r1", "state", "D", "v1")
RESEARCH_KEY = ("F-001", "r1", "research", "R", "v1")


def _coverage(*keys, **changes):
    values = {
        "required_result_keys": keys,
        "expected_subject_hashes": {key: "a" * 64 for key in keys},
        "expected_trace_hashes": {key: "b" * 64 for key in keys},
        "expected_oracle_hashes": {key: "c" * 64 for key in keys},
        "expected_policy_hashes": {key: "d" * 64 for key in keys},
        "expected_threshold_policy_hashes": {key: "e" * 64 for key in keys},
        "required_independence": {
            key: ("cross_family_context_independent" if key[3] in {"R", "M", "H"} else "deterministic_independent")
            for key in keys
        },
        "required_criticality": {key: True for key in keys},
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _result(key, verdict="pass", **changes):
    fixture_id, fixture_revision, grader_id, grader_class, grader_version = key
    values = {
        "grader_result_id": f"grr_{UUID7}",
        "evaluation_run_id": f"run_{UUID7}",
        "fixture_id": fixture_id,
        "fixture_revision": fixture_revision,
        "grader_id": grader_id,
        "grader_class": grader_class,
        "grader_version": grader_version,
        "verdict": verdict,
        "severity": "critical",
        "critical": True,
        "required": True,
        "subject_hash": "a" * 64,
        "trace_hash": "b" * 64,
        "oracle_hash": "c" * 64,
        "policy_hash": "d" * 64,
        "threshold_policy_hash": "e" * 64,
        "evidence_refs": ("evidence-1",),
        "independently_recomputed": True,
        "producer_family": "candidate-family",
        "grader_family": "independent-family",
        "context_relationship": (
            "cross_family_context_independent" if grader_class in {"R", "M", "H"} else "deterministic_independent"
        ),
        "limitations": (),
        "redactions": (),
        "duration_ms": 1,
        "cost_microunits": 0,
        "executed_by_actor_id": f"act_{UUID7}",
    }
    values.update(changes)
    return GraderResult(**values)


def test_empty_or_partial_result_set_blocks_on_exact_missing_keys():
    coverage = _coverage(STATE_KEY, RESEARCH_KEY)
    empty = decide_release(coverage, [])
    assert empty["decision"] == "blocked"
    assert empty["missing"] == [STATE_KEY, RESEARCH_KEY]
    partial = decide_release(coverage, [_result(STATE_KEY)])
    assert partial["decision"] == "blocked"
    assert partial["missing"] == [RESEARCH_KEY]


def test_stale_revision_duplicate_or_extra_result_blocks():
    coverage = _coverage(STATE_KEY)
    stale = ("F-001", "r0", "state", "D", "v1")
    stale_decision = decide_release(coverage, [_result(stale)])
    assert stale_decision["decision"] == "blocked"
    assert stale_decision["missing"] == [STATE_KEY]
    assert stale_decision["unexpected"] == [stale]

    duplicate = _result(STATE_KEY)
    duplicate_decision = decide_release(coverage, [duplicate, duplicate])
    assert duplicate_decision["decision"] == "blocked"
    assert duplicate_decision["duplicates"] == [STATE_KEY]

    extra_decision = decide_release(
        coverage,
        [_result(STATE_KEY), _result(RESEARCH_KEY)],
    )
    assert extra_decision["decision"] == "blocked"
    assert extra_decision["unexpected"] == [RESEARCH_KEY]


@pytest.mark.parametrize(
    "change",
    [
        {"subject_hash": "f" * 64},
        {"trace_hash": "f" * 64},
        {"oracle_hash": "f" * 64},
        {"policy_hash": "f" * 64},
        {"threshold_policy_hash": ""},
        {"context_relationship": "producer_correlated"},
        {"critical": False},
        {"required": False},
    ],
)
def test_incompatible_result_binding_blocks(change):
    decision = decide_release(_coverage(STATE_KEY), [_result(STATE_KEY, **change)])
    assert decision["decision"] == "blocked"
    assert decision["incompatible"]


@pytest.mark.parametrize("grader_class", ["D", "T", "P", "R", "M", "H"])
def test_critical_and_required_grader_failures_are_noncompensable(grader_class):
    key = ("F-001", "r1", f"{grader_class.lower()}-grader", grader_class, "v1")
    decision = decide_release(_coverage(key), [_result(key, "fail")])
    assert decision["decision"] == "fail"
    assert decision["blocking"]


@pytest.mark.parametrize("verdict", ["unable_to_grade", "fixture_error"])
def test_ungradeable_or_fixture_defect_blocks_instead_of_failing_or_passing(
    verdict,
):
    decision = decide_release(_coverage(STATE_KEY), [_result(STATE_KEY, verdict)])
    assert decision["decision"] == "blocked"
    assert decision["blocking"]


def test_coverage_cannot_omit_immutable_result_bindings():
    incomplete_coverage = SimpleNamespace(required_result_keys=(STATE_KEY,))
    decision = decide_release(incomplete_coverage, [_result(STATE_KEY)])
    assert decision["decision"] == "blocked"
    assert decision["incompatible"]


def test_only_exact_compatible_required_set_can_pass():
    decision = decide_release(
        _coverage(STATE_KEY, RESEARCH_KEY),
        [_result(STATE_KEY), _result(RESEARCH_KEY)],
    )
    assert decision == {
        "decision": "pass",
        "missing": [],
        "unexpected": [],
        "duplicates": [],
        "incompatible": [],
        "blocking": [],
    }


def test_each_required_result_uses_its_own_subject_trace_and_policy_hashes():
    coverage = _coverage(
        STATE_KEY,
        RESEARCH_KEY,
        expected_subject_hashes={
            STATE_KEY: "a" * 64,
            RESEARCH_KEY: "1" * 64,
        },
        expected_trace_hashes={
            STATE_KEY: "b" * 64,
            RESEARCH_KEY: "2" * 64,
        },
        expected_policy_hashes={
            STATE_KEY: "d" * 64,
            RESEARCH_KEY: "3" * 64,
        },
    )
    decision = decide_release(
        coverage,
        [
            _result(STATE_KEY),
            _result(
                RESEARCH_KEY,
                subject_hash="1" * 64,
                trace_hash="2" * 64,
                policy_hash="3" * 64,
            ),
        ],
    )
    assert decision["decision"] == "pass"
