from research_system.context.models import ContextCandidate
from research_system.routing.engine import PreparedDispatch, RouteCandidate
from research_system.routing.orchestrator import plan_dispatch


class _Task:
    task_id = "tsk_" + "1" * 32
    revision = 1
    route_request_id = "rrq_" + "2" * 32


class _Requirement:
    assurance_requirement_id = "asr_" + "3" * 32
    content_hash = "a" * 64
    task_id = _Task.task_id
    task_revision = _Task.revision


class _Evidence:
    routing_evidence_snapshot_id = "res_" + "4" * 32
    expires_at = "2026-07-03T00:00:00Z"

    def __init__(self, evidence_id, content_hash):
        self.evidence_id = evidence_id
        self.content_hash = content_hash

    def validate_pre_route(self):
        return None

    def hard_gate_failures(self, request, candidate):
        del request, candidate
        return ()


def test_real_compiled_candidate_can_be_planned_without_issue():
    compiled = ContextCandidate(
        "ctx_" + "5" * 32,
        "ctx_" + "6" * 32,
        "b" * 64,
        10,
        2,
        "ars-reference-regex-v1",
    )
    prepared = plan_dispatch(
        _Task(),
        "att_" + "7" * 32,
        _Requirement(),
        compiled,
        [RouteCandidate("codex", 1, 1, 0, 100, 1, 1)],
        _Evidence("art_" + "8" * 32, "c" * 64),
        _Evidence("art_" + "9" * 32, "d" * 64),
    )
    assert isinstance(prepared, PreparedDispatch)
    assert prepared.state == "unissued"
