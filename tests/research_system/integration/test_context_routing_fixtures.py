import pytest

from research_system.canonical import sha256_hex
from research_system.context.compiler import compile_candidate, validate_provider_gate
from research_system.context.errors import ContextBudgetExceeded
from research_system.context.models import ContextProfile, SourceFragment
from research_system.context.tokenizers import (
    ProviderCountEvidence,
    ReferenceRegexV1,
    Utf8ByteEvidenceV1,
)
from research_system.errors import ArsError
from research_system.routing.engine import PreparedDispatch, RouteCandidate, select_route


def _fragment(source_id, authority, content, mandatory=True):
    return SourceFragment(
        source_id,
        "r1",
        authority,
        mandatory,
        content,
        sha256_hex(content.encode("utf-8")),
    )


def test_f021_missing_amendment_blocks_instead_of_becoming_omission():
    baseline = [_fragment("design-r1", 90, "original design")]
    with pytest.raises(ArsError, match="mandatory source omitted"):
        compile_candidate(
            baseline,
            ContextProfile("r2", 100),
            ReferenceRegexV1(),
            required_source_ids={"design-r1", "amendment-r2"},
        )


def test_f022_f025_f026_complete_mandatory_closure_is_measured():
    required_ids = {
        "scope-22",
        "amendment-r2",
        "frozen-transform",
        "null-preflight",
        "vintage",
        "seed",
        "stop-rule",
    }
    fragments = [_fragment(name, 100, name) for name in sorted(required_ids)]
    candidate = compile_candidate(
        fragments,
        ContextProfile("r2", 100),
        ReferenceRegexV1(),
        required_source_ids=required_ids,
    )
    provider = ProviderCountEvidence(
        counter_id="fake-codex-upper-v1",
        units="provider_tokens",
        count=12,
        exact=False,
        provider="codex",
        model="p0-fake",
        rendering_revision="render-v1",
        evidence_revision="eval-v1",
    )
    assert candidate.reference_count > 0
    assert (
        validate_provider_gate(candidate, provider, usable_capacity_tokens=16)
        == provider
    )
    assert Utf8ByteEvidenceV1().count(candidate.rendered_content).units == "utf8_bytes"


def test_f027_index_deletion_preserves_mandatory_hash():
    profile = ContextProfile("r2", reference_limit=100)
    mandatory = _fragment("direct-source", 100, "governing evidence")
    optional = _fragment("optional-index", 1, "supplement", mandatory=False)
    with_index = compile_candidate(
        [mandatory, optional], profile, ReferenceRegexV1(), {"direct-source"}
    )
    direct = compile_candidate(
        [mandatory], profile, ReferenceRegexV1(), {"direct-source"}
    )
    assert with_index.mandatory_hash == direct.mandatory_hash


def test_f028_either_token_gate_blocks_without_truncation():
    fragment = _fragment("mandatory", 100, "one two three")
    with pytest.raises(ContextBudgetExceeded, match="reference_token_gate"):
        compile_candidate(
            [fragment],
            ContextProfile("r2", 2),
            ReferenceRegexV1(),
            required_source_ids={"mandatory"},
        )
    candidate = compile_candidate(
        [fragment],
        ContextProfile("r2", 100),
        ReferenceRegexV1(),
        required_source_ids={"mandatory"},
    )
    overflow = ProviderCountEvidence(
        counter_id="fake-codex-upper-v1",
        units="provider_tokens",
        count=13,
        exact=False,
        provider="codex",
        model="p0-fake",
        rendering_revision="render-v1",
        evidence_revision="eval-v1",
    )
    with pytest.raises(ContextBudgetExceeded, match="bound_provider_capacity_gate"):
        validate_provider_gate(candidate, overflow, usable_capacity_tokens=16)


class _RoutingRequest:
    request_id = "rrq_" + "7" * 32


class _RoutingSnapshot:
    routing_evidence_snapshot_id = "res_" + "8" * 32

    def __init__(self, failures=None):
        self.failures = failures or {}

    def hard_gate_failures(self, request, candidate):
        del request
        return self.failures.get(candidate.profile_id, ())


def _route_candidate(profile_id, capability):
    return RouteCandidate(profile_id, capability, 2, 0, 100, 1, 1)


def test_f031_routing_is_permutation_invariant():
    candidates = [_route_candidate("weak", 1), _route_candidate("strong", 2)]
    forward = select_route(_RoutingRequest(), candidates, _RoutingSnapshot())
    reverse = select_route(
        _RoutingRequest(), list(reversed(candidates)), _RoutingSnapshot()
    )
    assert forward == reverse
    assert forward["winner"].profile_id == "strong"


def test_f033_missing_verifier_witness_blocks_prepared_dispatch():
    result = select_route(
        _RoutingRequest(),
        [_route_candidate("producer", 10)],
        _RoutingSnapshot({"producer": ("independence_unavailable",)}),
    )
    assert result["kind"] == "failure"
    assert result["evaluated"][0][1] == ("independence_unavailable",)


def test_prepared_dispatch_remains_unissued():
    prepared = PreparedDispatch(
        "att_" + "1" * 32,
        "asr_" + "2" * 32,
        "a" * 64,
        {"context": "compiled"},
        {"kind": "selected"},
        "art_" + "3" * 32,
        "b" * 64,
        "art_" + "4" * 32,
        "c" * 64,
        "2026-07-03T00:00:00Z",
    )
    assert prepared.state == "unissued"
