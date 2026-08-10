"""Per-fixture executor registry: observed evidence from stimulus only."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from research_system.evals.errors import FixtureDefinitionError
from research_system.errors import ArsError
from research_system.evals.executors.adapter_scientific import (
    ADAPTER_SCIENTIFIC_EXECUTORS,
)
from research_system.evals.executors.context_routing import (
    CONTEXT_ROUTING_EXECUTORS,
)
from research_system.evals.executors.control_store import CONTROL_STORE_EXECUTORS
from research_system.evals.executors.release_tranche import RELEASE_TRANCHE_EXECUTORS

FixtureExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]

_RAW_EXECUTORS: dict[str, FixtureExecutor] = {
    **CONTROL_STORE_EXECUTORS,
    **ADAPTER_SCIENTIFIC_EXECUTORS,
    **CONTEXT_ROUTING_EXECUTORS,
    **RELEASE_TRANCHE_EXECUTORS,
}

LIFECYCLE_REQUIRED_IDS = frozenset(
    {"F-021", "F-022", "F-025", "F-026", "F-027", "F-028", "F-031", "F-033", "F-035", "S-016"}
)
ADAPTER_SCIENTIFIC_IDS = frozenset(ADAPTER_SCIENTIFIC_EXECUTORS)
PURE_OBSERVATION_IDS = frozenset({*CONTROL_STORE_EXECUTORS, "S-014", "S-015"})


@dataclass(frozen=True, slots=True)
class RegisteredExecutor:
    fixture_id: str
    execution_class: str
    execute_raw: FixtureExecutor

    def __call__(self, subject: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.execution_class == "lifecycle_required":
            raise ArsError(f"lifecycle execution authority required: {self.fixture_id}")
        return self.execute_raw(subject, payload)


def _execution_class(fixture_id: str) -> str:
    memberships = [
        name
        for name, fixture_ids in (
            ("lifecycle_required", LIFECYCLE_REQUIRED_IDS),
            ("adapter_scientific", ADAPTER_SCIENTIFIC_IDS),
            ("pure_observation", PURE_OBSERVATION_IDS),
        )
        if fixture_id in fixture_ids
    ]
    if len(memberships) != 1:
        raise FixtureDefinitionError(f"executor_classification_invalid: {fixture_id}: {memberships}")
    return memberships[0]


EXECUTORS: dict[str, RegisteredExecutor] = {
    fixture_id: RegisteredExecutor(
        fixture_id,
        _execution_class(fixture_id),
        execute,
    )
    for fixture_id, execute in _RAW_EXECUTORS.items()
}


def require_executor(fixture_id: str) -> RegisteredExecutor:
    """Return the registered executor or fail closed.

    Args:
        fixture_id: P0 case identifier.

    Returns:
        The registered executor callable.

    Raises:
        FixtureDefinitionError: If no executor is registered for the case.
    """
    try:
        return EXECUTORS[fixture_id]
    except KeyError as exc:
        raise FixtureDefinitionError(f"executor_missing: {fixture_id}") from exc
