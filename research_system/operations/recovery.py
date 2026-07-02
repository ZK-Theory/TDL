"""Benchmark feasibility and compatible-resume decisions."""

from collections.abc import Mapping, Sequence
from typing import Any

from research_system.operations.checkpoints import checkpoint_compatibility


def benchmark_disposition(
    *,
    independent_work_units: int,
    workers: int,
    required_prerequisites: Sequence[str],
    measured_prerequisites: Sequence[str],
    projected_runtime_s: float,
    hard_limit_s: float,
) -> dict[str, Any]:
    """Classify whether a benchmark projection is decision-grade and feasible."""
    missing = set(required_prerequisites) - set(measured_prerequisites)
    if missing:
        return {
            "status": "blocked",
            "reason": "hidden_prerequisite",
            "missing": sorted(missing),
        }
    if workers > independent_work_units:
        return {"status": "blocked", "reason": "invalid_worker_projection"}
    if projected_runtime_s > hard_limit_s:
        return {"status": "stop_required", "reason": "hard_runtime_limit"}
    return {"status": "feasible", "reason": None}


def resume_from_checkpoint(
    checkpoint: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    prior_epoch: int,
) -> dict[str, Any]:
    """Return a compatible new epoch or preserve an incompatible checkpoint."""
    compatibility = checkpoint_compatibility(checkpoint, request)
    if compatibility["verdict"] != "compatible":
        return {
            **compatibility,
            "preserve_checkpoint": True,
        }
    return {
        "verdict": "compatible",
        "new_execution_epoch": prior_epoch + 1,
        "revalidate": ("W3", "W4", "W5", "W6", "W7", "W8"),
    }
