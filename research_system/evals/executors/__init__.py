"""Per-fixture executor registry: observed evidence from stimulus only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from research_system.evals.errors import FixtureDefinitionError
from research_system.evals.executors.adapter_scientific import (
    ADAPTER_SCIENTIFIC_EXECUTORS,
)
from research_system.evals.executors.context_routing import (
    CONTEXT_ROUTING_EXECUTORS,
)
from research_system.evals.executors.control_store import CONTROL_STORE_EXECUTORS

FixtureExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]

EXECUTORS: dict[str, FixtureExecutor] = {
    **CONTROL_STORE_EXECUTORS,
    **ADAPTER_SCIENTIFIC_EXECUTORS,
    **CONTEXT_ROUTING_EXECUTORS,
}


def require_executor(fixture_id: str) -> FixtureExecutor:
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
