import pytest

from research_system.canonical import sha256_hex
from research_system.context.models import SourceFragment
from research_system.context.sources import resolve_sources
from research_system.errors import ArsError


class _Resolver:
    def __init__(self, fragments):
        self.fragments = fragments

    def resolve(self, source_ids):
        return tuple(
            fragment
            for fragment in self.fragments
            if fragment.source_id in source_ids
        )


def _fragment(source_id, content):
    return SourceFragment(
        source_id,
        "r1",
        100,
        True,
        content,
        sha256_hex(content.encode("utf-8")),
    )


def test_source_resolver_returns_verified_stable_required_closure():
    fragments = [_fragment("b", "second"), _fragment("a", "first")]
    resolved = resolve_sources(_Resolver(fragments), {"a", "b"})
    assert tuple(item.source_id for item in resolved) == ("a", "b")


def test_source_resolver_rejects_missing_or_hash_divergent_source():
    with pytest.raises(ArsError, match="mandatory source omitted"):
        resolve_sources(_Resolver([_fragment("a", "first")]), {"a", "b"})
    invalid = SourceFragment("a", "r1", 100, True, "changed", "0" * 64)
    with pytest.raises(ArsError, match="source hash mismatch"):
        resolve_sources(_Resolver([invalid]), {"a"})
