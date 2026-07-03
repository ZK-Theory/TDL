from research_system.operations.recovery import (
    benchmark_disposition,
    resume_from_checkpoint,
)


def _checkpoint():
    return {
        "design_hash": "a",
        "code_hash": "b",
        "environment_hash": "c",
        "input_hashes": ["d"],
        "representation_hash": "e",
        "parameters_hash": "f",
        "rng_algorithm": "PCG64",
        "rng_state_hash": "g",
        "completed_work_units": [0, 1],
        "payload_hash": "h",
    }


def test_hidden_prerequisite_blocks_benchmark_projection():
    result = benchmark_disposition(
        independent_work_units=10,
        workers=2,
        required_prerequisites={"frozen_loadings", "null_cache"},
        measured_prerequisites={"null_cache"},
        projected_runtime_s=100,
        hard_limit_s=200,
    )
    assert result == {
        "status": "blocked",
        "reason": "hidden_prerequisite",
        "missing": ["frozen_loadings"],
    }


def test_more_workers_than_independent_units_invalidates_projection():
    result = benchmark_disposition(
        independent_work_units=2,
        workers=3,
        required_prerequisites=set(),
        measured_prerequisites=set(),
        projected_runtime_s=100,
        hard_limit_s=200,
    )
    assert result["reason"] == "invalid_worker_projection"


def test_compatible_resume_creates_new_epoch_and_revalidates_w3_to_w8():
    result = resume_from_checkpoint(_checkpoint(), _checkpoint(), prior_epoch=4)
    assert result == {
        "verdict": "compatible",
        "new_execution_epoch": 5,
        "revalidate": ("W3", "W4", "W5", "W6", "W7", "W8"),
    }


def test_incompatible_checkpoint_blocks_resume_and_preserves_evidence():
    result = resume_from_checkpoint(
        _checkpoint(), {**_checkpoint(), "input_hashes": ["changed"]}, prior_epoch=4
    )
    assert result["verdict"] == "incompatible"
    assert result["preserve_checkpoint"] is True
