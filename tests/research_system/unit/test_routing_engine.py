from dataclasses import dataclass

from research_system.routing.engine import (
    PreparedDispatch,
    RouteCandidate,
    select_route,
)


@dataclass(frozen=True)
class _Request:
    request_id: str


class _Snapshot:
    def __init__(self, failures):
        self.routing_evidence_snapshot_id = "res_" + "1" * 32
        self._failures = {
            profile_id: tuple(reasons)
            for profile_id, reasons in failures.items()
        }

    def hard_gate_failures(self, request, candidate):
        del request
        return self._failures.get(candidate.profile_id, ())


def _candidate(profile_id, capability=1, independence=1, limitations=0):
    return RouteCandidate(
        profile_id,
        capability,
        independence,
        limitations,
        100,
        25,
        10,
    )


def test_candidate_permutation_produces_identical_selection_data():
    request = _Request("rrq_" + "2" * 32)
    candidates = [_candidate("b"), _candidate("a", capability=2)]
    snapshot = _Snapshot({})
    forward = select_route(request, candidates, snapshot)
    reverse = select_route(request, list(reversed(candidates)), snapshot)
    assert forward == reverse
    assert forward["winner"].profile_id == "a"


def test_live_telemetry_cannot_change_bound_snapshot():
    live = {"a": ("provider_unavailable",)}
    snapshot = _Snapshot(live)
    live["a"] = ()
    result = select_route(_Request("rrq_" + "3" * 32), [_candidate("a")], snapshot)
    assert result["kind"] == "failure"
    assert result["evaluated"][0][1] == ("provider_unavailable",)


def test_capability_suspension_and_missing_verifier_block_before_ranking():
    snapshot = _Snapshot(
        {
            "producer-a": ("capability_insufficient",),
            "producer-b": ("independence_unavailable",),
        }
    )
    result = select_route(
        _Request("rrq_" + "4" * 32),
        [_candidate("producer-b", capability=99), _candidate("producer-a")],
        snapshot,
    )
    assert result["kind"] == "failure"
    assert tuple(item.profile_id for item, _ in result["evaluated"]) == (
        "producer-a",
        "producer-b",
    )


def test_prepared_dispatch_freezes_unissued_wp3_contract():
    prepared = PreparedDispatch(
        attempt_id="att_" + "1" * 32,
        assurance_requirement_id="asr_" + "2" * 32,
        assurance_requirement_hash="a" * 64,
        context={"context_candidate_id": "ctx_" + "3" * 32},
        route={"kind": "selected", "winner": "codex"},
        provider_evidence_id="art_" + "4" * 32,
        provider_evidence_hash="b" * 64,
        operational_evidence_id="art_" + "5" * 32,
        operational_evidence_hash="c" * 64,
        expires_at="2026-07-03T00:00:00Z",
    )
    assert prepared.state == "unissued"
    assert prepared.provider_evidence_hash == "b" * 64
    assert prepared.operational_evidence_hash == "c" * 64
