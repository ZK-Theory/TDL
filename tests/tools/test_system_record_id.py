"""Controls for collision-resistant system record identifiers."""

import sys

import pytest

from tools.system_record_id import is_ulid, main, mint_ulid


def test_ulid_canonical_shape_and_timestamp_order() -> None:
    earlier = mint_ulid(timestamp_ms=1_000, randomness=0)
    later = mint_ulid(timestamp_ms=1_001, randomness=0)
    assert is_ulid(earlier)
    assert is_ulid(later)
    assert earlier < later


def test_same_millisecond_random_component_avoids_collision() -> None:
    first = mint_ulid(timestamp_ms=1_000, randomness=1)
    second = mint_ulid(timestamp_ms=1_000, randomness=2)
    assert first != second


def test_rejects_ambiguous_or_out_of_range_identifiers() -> None:
    assert not is_ulid("01J8Z9K3QX7M2AB4CD5EF6GHIJ")
    assert not is_ulid("Z1J8Z9K3QX7M2AB4CD5EF6GH7J")


def test_handoff_slug_accepts_documented_format(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["system_record_id.py", "--handoff-slug", "system-review-d1-d4"])
    assert main() == 0
    assert capsys.readouterr().out.strip().endswith("-system-review-d1-d4.md")


def test_handoff_slug_rejects_path_or_uppercase_syntax(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["system_record_id.py", "--handoff-slug", "../Bad"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
