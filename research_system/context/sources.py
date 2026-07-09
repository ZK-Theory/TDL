"""Typed direct-source resolver boundary for deterministic W3 compilation."""

from typing import Protocol

from research_system.canonical import sha256_hex
from research_system.context.models import SourceFragment
from research_system.errors import ArsError


class SourceResolver(Protocol):
    def resolve(self, source_ids: set[str]) -> tuple[SourceFragment, ...]: ...


def resolve_sources(
    resolver: SourceResolver, required_source_ids: set[str]
) -> tuple[SourceFragment, ...]:
    """Resolve an exact, hash-verified mandatory source closure."""
    fragments = tuple(resolver.resolve(set(required_source_ids)))
    resolved_ids = [fragment.source_id for fragment in fragments]
    missing = set(required_source_ids) - set(resolved_ids)
    if missing:
        raise ArsError(f"mandatory source omitted: {sorted(missing)}")
    if len(resolved_ids) != len(set(resolved_ids)):
        raise ArsError("duplicate source identity")
    unexpected = set(resolved_ids) - set(required_source_ids)
    if unexpected:
        raise ArsError(f"unexpected source returned: {sorted(unexpected)}")
    for fragment in fragments:
        observed_hash = sha256_hex(fragment.content.encode("utf-8"))
        if observed_hash != fragment.content_hash:
            raise ArsError(f"source hash mismatch: {fragment.source_id}")
    return tuple(
        sorted(fragments, key=lambda item: (item.source_id, item.revision))
    )
