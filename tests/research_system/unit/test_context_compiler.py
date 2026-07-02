import pytest

from research_system.canonical import sha256_hex
from research_system.context.compiler import compile_candidate
from research_system.context.models import (
    ContextCandidate,
    ContextProfile,
    SourceFragment,
)
from research_system.context.tokenizers import ReferenceRegexV1
from research_system.errors import ArsError


def test_context_candidate_is_compiled_but_unissued():
    candidate = ContextCandidate(
        "ctx_" + "1" * 32,
        "ctx_" + "2" * 32,
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
        "ctx_" + "4" * 32,
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

def test_compile_pipeline_rejects_mandatory_source_omission_evidence():
    content = "governing source"
    fragment = SourceFragment(
        "src-a",
        "r1",
        100,
        True,
        content,
        sha256_hex(content.encode("utf-8")),
    )
    with pytest.raises(ArsError, match="non-optional omission"):
        compile_candidate(
            [fragment],
            ContextProfile("r2", 100),
            ReferenceRegexV1(),
            required_source_ids={"src-a"},
            omissions={"src-a": "access_denied"},
        )

def test_compile_pipeline_records_declared_optional_omission():
    content = "governing source"
    fragment = SourceFragment(
        "src-a",
        "r1",
        100,
        True,
        content,
        sha256_hex(content.encode("utf-8")),
    )
    candidate = compile_candidate(
        [fragment],
        ContextProfile("r2", 100),
        ReferenceRegexV1(),
        required_source_ids={"src-a"},
        optional_source_ids={"src-optional"},
        omissions={"src-optional": "access_denied"},
    )
    assert candidate.omissions == {"src-optional": "access_denied"}
