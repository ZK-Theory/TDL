"""Controls for collision-resistant system record identifiers."""

from tools.system_record_id import is_ulid, mint_ulid


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
