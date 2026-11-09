# Research context: observation 2026-10-28-byte-identity-controls-bypass-their-guard-despite-checklist
# Purpose: prove that the shared byte-identity helper fails for a weakened or deleted guard, not only for a sound one.
"""Controls for ``assert_byte_identity``: a sound guard passes, and each weakened guard fails."""

from __future__ import annotations

import json

import pytest

from tests.research_system.contracts.byte_identity import assert_byte_identity, object_equal_refusals

COMMITTED = b'{"a":1,"b":[2,3]}'
TAMPER = b'{"a":1,"b":[2,4]}'


def _bytes_guard(data: bytes) -> bool:
    return data == COMMITTED


def _object_guard(data: bytes) -> bool:
    # The weakening the WP9.2-1 review found: a parsed comparison admits every re-encoding.
    return json.loads(data) == json.loads(COMMITTED)


def test_a_byte_comparison_guard_passes() -> None:
    assert_byte_identity(_bytes_guard, COMMITTED, tampers=[TAMPER])


def test_a_guard_weakened_to_an_object_comparison_fails() -> None:
    with pytest.raises(AssertionError, match="object-equal re-encoding"):
        assert_byte_identity(_object_guard, COMMITTED, tampers=[TAMPER])


def test_a_deleted_guard_fails() -> None:
    with pytest.raises(AssertionError, match="object-equal re-encoding"):
        assert_byte_identity(lambda data: True, COMMITTED)


def test_a_guard_that_refuses_the_committed_bytes_fails() -> None:
    with pytest.raises(AssertionError, match="refuses the committed bytes"):
        assert_byte_identity(lambda data: False, COMMITTED)


def test_a_guard_that_admits_a_tamper_fails() -> None:
    with pytest.raises(AssertionError, match="admits a tamper"):
        assert_byte_identity(lambda data: data in (COMMITTED, TAMPER), COMMITTED, tampers=[TAMPER])


def test_a_re_encoding_passed_as_a_tamper_is_refused_as_misuse() -> None:
    with pytest.raises(AssertionError, match="must change the parsed value"):
        assert_byte_identity(_bytes_guard, COMMITTED, tampers=[COMMITTED + b"\n"])


def test_the_built_refusals_differ_in_bytes_and_agree_in_value() -> None:
    refusals = object_equal_refusals(COMMITTED)
    assert len(set(refusals)) == 3 and COMMITTED not in refusals
    assert all(json.loads(data) == json.loads(COMMITTED) for data in refusals)
