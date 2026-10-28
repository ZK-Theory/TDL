"""Shared W9 legacy command-family identity.

The control-plane, Discovery and legacy projections share one atomic event ledger. This closed set lets each of them
route a W9 event to the legacy reducer without importing the legacy runtime (design note §2.1, U-7). It is a leaf: the
replay path reads no file, and a test requires the set to equal the accepted W9 catalogue's command set.

Membership grants nothing. It only routes replay; a command still needs its runtime-binding row and scoped authority
before it can append.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

LEGACY_COMMAND_TYPES = frozenset(
    {
        "ImportAcceptedW9CatalogueGenesis",
        "ImportAcceptedW9CatalogueRevision",
        "ProposeLegacyRecord",
        "RequestW9AuthorityReview",
        "RecordW9AuthorityReview",
        "ProposeW9AuthorityDecision",
        "ResolveW9AuthorityDecision",
        "RecordLegacyLightInventory",
        "ObserveLegacyRecord",
        "CreateLegacyPaperRoot",
        "RecordPaperCitationStatus",
        "RecordAdoptionUseMismatch",
    }
)


def is_legacy_projection_event(event: Mapping[str, Any]) -> bool:
    """Return whether the event belongs to the W9 legacy reducer.

    Args:
        event: One persisted shared-ledger event.

    Returns:
        True when the event's command type is a W9 command type.
    """

    return event.get("command_type") in LEGACY_COMMAND_TYPES
