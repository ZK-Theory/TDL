"""Typed direct-source resolver boundary for deterministic W3 compilation."""

import json
from pathlib import Path
from typing import Protocol

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.context.models import SourceFragment
from research_system.errors import ArsError


class SourceResolver(Protocol):
    def resolve(self, source_ids: set[str]) -> tuple[SourceFragment, ...]: ...


class FileSourceResolver:
    """Read current direct-source records from an operator-provisioned authority root."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def record_path(self, source_id: str) -> Path:
        return self.root / f"{sha256_hex(source_id.encode('utf-8'))}.json"

    def resolve(self, source_ids: set[str]) -> tuple[SourceFragment, ...]:
        resolved: list[SourceFragment] = []
        for source_id in sorted(source_ids):
            path = self.record_path(source_id)
            try:
                raw = path.read_bytes()
                value = json.loads(raw)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ArsError(f"direct source authority is unavailable: {source_id}") from exc
            if not isinstance(value, dict):
                raise ArsError(f"direct source authority is not canonical: {source_id}")
            try:
                canonical = canonical_bytes(value)
            except (TypeError, ValueError) as exc:
                raise ArsError(f"direct source authority is not canonical: {source_id}") from exc
            if canonical != raw:
                raise ArsError(f"direct source authority is not canonical: {source_id}")
            required = {
                "source_id",
                "revision",
                "authority_rank",
                "mandatory",
                "content",
                "content_hash",
                "direct",
                "current",
                "superseded",
                "sensitivity_class",
            }
            if set(value) != required or value["source_id"] != source_id:
                raise ArsError(f"direct source authority identity mismatch: {source_id}")
            resolved.append(SourceFragment(**value))
        return tuple(resolved)


def resolve_sources(
    resolver: SourceResolver,
    required_source_ids: set[str],
    optional_source_ids: set[str] | None = None,
) -> tuple[SourceFragment, ...]:
    """Resolve an exact, hash-verified mandatory source closure."""
    candidate_source_ids = set(required_source_ids) | set(optional_source_ids or ())
    fragments = tuple(resolver.resolve(candidate_source_ids))
    resolved_ids = [fragment.source_id for fragment in fragments]
    missing = set(required_source_ids) - set(resolved_ids)
    if missing:
        raise ArsError(f"mandatory source omitted: {sorted(missing)}")
    if len(resolved_ids) != len(set(resolved_ids)):
        raise ArsError("duplicate source identity")
    unexpected = set(resolved_ids) - candidate_source_ids
    if unexpected:
        raise ArsError(f"unexpected source returned: {sorted(unexpected)}")
    for fragment in fragments:
        if not fragment.direct:
            raise ArsError(f"source is not direct: {fragment.source_id}")
        if not fragment.current or fragment.superseded:
            raise ArsError(f"source is stale or superseded: {fragment.source_id}")
        if fragment.sensitivity_class in {
            "restricted",
            "secret",
            "credential",
            "transcript",
            "hidden_reasoning",
        }:
            raise ArsError(f"unsafe or restricted source: {fragment.source_id}")
        observed_hash = sha256_hex(fragment.content.encode("utf-8"))
        if observed_hash != fragment.content_hash:
            raise ArsError(f"source hash mismatch: {fragment.source_id}")
    return tuple(sorted(fragments, key=lambda item: (item.source_id, item.revision)))
