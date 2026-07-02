from research_system.operations.checkpoints import checkpoint_compatibility


def _state(**changes):
    state = {
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
    state.update(changes)
    return state


def test_compatible_checkpoint_allows_different_completed_work_units():
    assert checkpoint_compatibility(
        _state(completed_work_units=[0]), _state(completed_work_units=[0, 1])
    ) == {"verdict": "compatible", "mismatches": []}


def test_changed_design_and_rng_reject_checkpoint():
    result = checkpoint_compatibility(
        _state(), _state(design_hash="changed", rng_state_hash="changed")
    )
    assert result == {
        "verdict": "incompatible",
        "mismatches": ["design_hash", "rng_state_hash"],
    }


def test_missing_payload_hash_is_unable_to_determine():
    result = checkpoint_compatibility(_state(payload_hash=""), _state(payload_hash=""))
    assert result == {
        "verdict": "unable_to_determine",
        "mismatches": ["payload_hash"],
    }
