"""Replay each event list once per SPEC route operation (P-058, 2026-10-01).

Every route read re-derives from the ledger, so one coordinator operation replays the same event
lists many times: measured at `bd5c971e`, 75% of the route's replay time repeated a list the same
invocation had already replayed. Within one operation (`status`, `advance` or `result`), this
module replays an identical list once.

The cache is keyed by the list's exact canonical bytes, the replay kind and the replay options,
so a list that differs in any field, even under the same event hashes, replays again. Every caller
receives its own deep copy, so no caller can change what another reads. A failed replay is not
cached, and nothing is cached outside an operation. The cache ends with the operation, so a later
operation, and every separate CLI process, replays from the ledger again.

Only the route's own reads use it. Admission, the command service and the authority resolver keep
their own replays, so no check moves out from under the writer lock. Route modules must not import
the uncached replays (`tests/research_system/unit/test_spec_replay.py`).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import functools
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.replay.driver import replay_discovery as _replay_discovery
from research_system.projection.replay import replay as _replay_control
from research_system.schema_registry import SchemaRegistry

_Validator = Callable[[dict[str, Any]], None] | None

# One operation's replays: key -> (registry, validator owner, state). The entry holds the registry
# and the validator's owner, so the object ids in its key cannot be reused while the cache lives.
_ACTIVE: ContextVar[dict[tuple, tuple[Any, Any, dict[str, Any]]] | None] = ContextVar(
    "spec_route_replays", default=None
)


@contextmanager
def one_operation() -> Iterator[None]:
    """Hold one replay cache for the enclosed route operation; a nested operation shares it."""
    if _ACTIVE.get() is not None:
        yield
        return
    token = _ACTIVE.set({})
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def per_operation(method: Callable[..., Any]) -> Callable[..., Any]:
    """Run a coordinator operation inside one replay cache."""

    @functools.wraps(method)
    def operation(*args: Any, **kwargs: Any) -> Any:
        with one_operation():
            return method(*args, **kwargs)

    operation.replays_once_per_operation = True  # type: ignore[attr-defined]
    return operation


def replay(
    events: Iterable[dict[str, Any]], *, schema_registry: SchemaRegistry, authority_state_validator: _Validator
) -> dict[str, Any]:
    """Return the control-plane projection of ``events``, replayed once per operation."""
    return _cached(
        "control",
        tuple(events),
        schema_registry,
        authority_state_validator,
        lambda ordered: _replay_control(
            ordered, schema_registry=schema_registry, authority_state_validator=authority_state_validator
        ),
    )


def replay_discovery(
    events: Iterable[dict[str, Any]], *, schemas: SchemaRegistry, authority_state_validator: _Validator
) -> dict[str, Any]:
    """Return the Discovery projection of ``events``, replayed once per operation."""
    return _cached(
        "discovery",
        tuple(events),
        schemas,
        authority_state_validator,
        lambda ordered: _replay_discovery(
            ordered, schemas=schemas, authority_state_validator=authority_state_validator
        ),
    )


def _cached(
    kind: str,
    ordered: tuple[dict[str, Any], ...],
    registry: SchemaRegistry,
    validator: _Validator,
    compute: Callable[[tuple[dict[str, Any], ...]], dict[str, Any]],
) -> dict[str, Any]:
    cache = _ACTIVE.get()
    if cache is None:
        return compute(ordered)
    owner = getattr(validator, "__self__", validator)
    key = (
        kind,
        sha256_hex(canonical_bytes(list(ordered))),
        id(registry),
        id(owner),
        getattr(validator, "__func__", validator),
    )
    entry = cache.get(key)
    if entry is None:
        entry = cache[key] = (registry, owner, compute(ordered))
    return deepcopy(entry[2])
