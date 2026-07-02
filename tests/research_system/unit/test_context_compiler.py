import pytest

from research_system.context.models import ContextCandidate
from research_system.errors import ArsError


def test_context_candidate_is_compiled_but_unissued():
    candidate = ContextCandidate(
        "ctx_" + "1" * 32,
        "mft_" + "2" * 32,
        "a" * 64,
        10,
        3,
        "ref-v1",
    )
    assert candidate.state == "compiled"
    assert candidate.state not in {"validated", "issued"}


def test_mandatory_source_cannot_be_excused_by_omission_reason():
    candidate = ContextCandidate(
        "ctx_" + "3" * 32,
        "mft_" + "4" * 32,
        "b" * 64,
        20,
        4,
        "ref-v1",
    )
    with pytest.raises(ArsError, match="mandatory source omitted"):
        candidate.validate_manifest(
            required={"src-a", "src-b"},
            included={"src-a"},
            optional_candidates={"src-c"},
            omissions={"src-b": "access_denied"},
        )
