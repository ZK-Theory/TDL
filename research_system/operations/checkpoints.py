"""Deterministic checkpoint compatibility predicates."""

CHECKPOINT_KEYS = (
    "design_hash",
    "code_hash",
    "environment_hash",
    "input_hashes",
    "representation_hash",
    "parameters_hash",
    "rng_algorithm",
    "rng_state_hash",
    "completed_work_units",
    "payload_hash",
)


def checkpoint_compatibility(checkpoint, request):
    mismatches = [
        key
        for key in CHECKPOINT_KEYS
        if checkpoint.get(key) != request.get(key) and key != "completed_work_units"
    ]
    if mismatches:
        return {"verdict": "incompatible", "mismatches": sorted(mismatches)}
    if not checkpoint.get("payload_hash"):
        return {"verdict": "unable_to_determine", "mismatches": ["payload_hash"]}
    return {"verdict": "compatible", "mismatches": []}
