"""The SPEC route replays an identical event list once per coordinator operation (P-058, 2026-10-01).

Measured at `bd5c971e`: 75% of the route's replay time repeated an event list the same invocation
had already replayed. These tests pin the cache's contract: it is keyed by the exact events and the
replay options, every caller gets its own copy, nothing is cached outside an operation or after a
failure, and no route module reaches the uncached replays directly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from research_system.discovery import spec_replay
from research_system.discovery.spec import SpecCoordinator

ROUTE_MODULES = ("spec.py", "spec_assay.py", "spec_result.py", "spec_source.py", "spec_task.py")
UNCACHED = {
    "research_system.projection.replay": {"replay"},
    "research_system.discovery.replay.driver": {"replay_discovery"},
}
REGISTRY = object()


class _Resolver:
    def validate(self, projection: dict) -> None:
        return None


def _events(*hashes: str) -> list[dict]:
    return [{"global_position": index + 1, "event_hash": value, "payload": {"n": index}} for index, value in
            enumerate(hashes)]  # fmt: skip


@pytest.fixture
def calls(monkeypatch) -> list[tuple]:
    """Replace both underlying replays with recorders that return a fresh nested state."""
    recorded: list[tuple] = []

    def control(events, *, schema_registry, authority_state_validator):
        recorded.append(("control", tuple(event["event_hash"] for event in events)))
        return {"streams": {"s": {"seen": [event["event_hash"] for event in events]}}}

    def discovery(events, *, schemas, authority_state_validator):
        recorded.append(("discovery", tuple(event["event_hash"] for event in events)))
        return {"candidates": {"c": {"seen": [event["event_hash"] for event in events]}}}

    monkeypatch.setattr(spec_replay, "_replay_control", control)
    monkeypatch.setattr(spec_replay, "_replay_discovery", discovery)
    return recorded


def _control(events, validator=None) -> dict:
    return spec_replay.replay(events, schema_registry=REGISTRY, authority_state_validator=validator)


def test_outside_an_operation_every_call_replays(calls):
    assert _control(_events("a", "b")) == _control(_events("a", "b"))
    assert len(calls) == 2


def test_an_identical_event_list_replays_once_per_operation(calls):
    with spec_replay.one_operation():
        first = _control(_events("a", "b"))
        second = _control(_events("a", "b"))
    assert first == second == {"streams": {"s": {"seen": ["a", "b"]}}}
    assert calls == [("control", ("a", "b"))]


def test_each_caller_gets_its_own_copy(calls):
    with spec_replay.one_operation():
        first = _control(_events("a"))
        first["streams"]["s"]["seen"].append("mutated")
        second = _control(_events("a"))
    assert second == {"streams": {"s": {"seen": ["a"]}}}


def test_a_different_event_list_replays_again(calls):
    changed = _events("a", "b")
    changed[1]["payload"]["n"] = 99  # Same length and event hashes, different content.
    with spec_replay.one_operation():
        _control(_events("a", "b"))
        _control(_events("a", "b", "c"))
        _control(_events("a"))
        _control(changed)
    assert len(calls) == 4


def test_different_replay_options_replay_again(calls):
    resolver, other = _Resolver(), _Resolver()
    with spec_replay.one_operation():
        _control(_events("a"), resolver.validate)
        _control(_events("a"), resolver.validate)
        _control(_events("a"), other.validate)
        _control(_events("a"))
        spec_replay.replay(_events("a"), schema_registry=object(), authority_state_validator=None)
    assert len(calls) == 4


def test_control_and_discovery_replays_are_cached_apart(calls):
    with spec_replay.one_operation():
        _control(_events("a"))
        projection = spec_replay.replay_discovery(_events("a"), schemas=REGISTRY, authority_state_validator=None)
        spec_replay.replay_discovery(_events("a"), schemas=REGISTRY, authority_state_validator=None)
    assert projection == {"candidates": {"c": {"seen": ["a"]}}}
    assert calls == [("control", ("a",)), ("discovery", ("a",))]


def test_nested_operations_share_one_cache_that_ends_with_the_outer_one(calls):
    with spec_replay.one_operation():
        _control(_events("a"))
        with spec_replay.one_operation():
            _control(_events("a"))
        _control(_events("a"))
    with spec_replay.one_operation():
        _control(_events("a"))
    assert len(calls) == 2


def test_a_failed_replay_is_not_cached(monkeypatch):
    attempts: list[int] = []

    def failing(events, *, schema_registry, authority_state_validator):
        attempts.append(len(events))
        raise ValueError("replay refused")

    monkeypatch.setattr(spec_replay, "_replay_control", failing)
    with spec_replay.one_operation():
        for _ in range(2):
            with pytest.raises(ValueError, match="replay refused"):
                _control(_events("a"))
    assert attempts == [1, 1]


@pytest.mark.parametrize("operation", ["status", "advance", "result"])
def test_each_coordinator_operation_is_one_replay_operation(operation, calls):
    method = getattr(SpecCoordinator, operation)
    assert getattr(method, "replays_once_per_operation", False) is True

    @spec_replay.per_operation
    def twice() -> None:
        _control(_events("a"))
        _control(_events("a"))

    twice()
    assert calls == [("control", ("a",))]


@pytest.mark.parametrize("module", ROUTE_MODULES)
def test_route_modules_reach_replay_only_through_the_cache(module):
    path = Path(spec_replay.__file__).with_name(module)
    imported = [
        (node.module, alias.name)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name in UNCACHED.get(node.module or "", set())
    ]
    assert imported == [], f"{module} imports an uncached replay: {imported}"
