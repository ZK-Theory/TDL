import pytest

from research_system.context.compiler import validate_provider_gate
from research_system.context.errors import ContextBudgetExceeded
from research_system.context.models import ContextCandidate
from research_system.context.tokenizers import (
    ProviderCountEvidence,
    ReferenceRegexV1,
    Utf8ByteEvidenceV1,
)
from research_system.errors import ArsError


def _candidate() -> ContextCandidate:
    return ContextCandidate(
        "ctx_" + "1" * 32,
        "ctx_" + "2" * 32,
        "a" * 64,
        10,
        3,
        "ars-reference-regex-v1",
    )


def test_reference_and_utf8_counters_keep_distinct_units():
    text = "café + topology"
    reference = ReferenceRegexV1().count(text)
    byte_count = Utf8ByteEvidenceV1().count(text)
    assert reference.units == "ars_reference_tokens"
    assert byte_count.units == "utf8_bytes"
    assert byte_count.count == len(text.encode("utf-8"))


def test_provider_gate_rejects_non_token_units():
    evidence = ProviderCountEvidence(
        "bytes-v1",
        "utf8_bytes",
        2,
        True,
        "codex",
        "p0-fake",
        "render-v1",
        "eval-v1",
    )
    with pytest.raises(ArsError, match="provider_tokens"):
        validate_provider_gate(_candidate(), evidence, usable_capacity_tokens=16)


def test_provider_gate_reserves_twenty_percent_capacity():
    evidence = ProviderCountEvidence(
        "fake-codex-upper-v1",
        "provider_tokens",
        13,
        False,
        "codex",
        "p0-fake",
        "render-v1",
        "eval-v1",
    )
    with pytest.raises(ContextBudgetExceeded, match="bound_provider_capacity_gate"):
        validate_provider_gate(_candidate(), evidence, usable_capacity_tokens=16)
