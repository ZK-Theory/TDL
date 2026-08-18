"""Stable semantic identity for replayed decisions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex


# These fields bind the terminal ledger event, not the decision's meaning. The
# event identity remains mandatory evidence alongside this semantic hash.
_REPLAY_PROVENANCE_FIELDS = frozenset({"terminal_event_id", "terminal_event_hash"})


def decision_semantic_sha256(decision: Mapping[str, Any]) -> str:
    """Hash decision semantics without replay-only terminal provenance fields.

    The returned identity is stable when replay attaches the terminal event
    coordinates. Status, selected option, authority, scope, review bindings,
    and every other semantic field remain hash-bearing.
    """

    semantic_projection = {key: value for key, value in decision.items() if key not in _REPLAY_PROVENANCE_FIELDS}
    return sha256_hex(canonical_bytes(semantic_projection))
