"""Discovery genesis replay reducers.

One function per accepted event type.  Each is reached only through
:mod:`research_system.discovery.replay.registry`, which proves exactly one
reducer owns each executable event.
"""

from __future__ import annotations

from copy import deepcopy
from research_system.discovery.accepted_w11 import CATALOGUE_STREAM_ID as _CATALOGUE_STREAM_ID
from research_system.discovery.accepted_w11 import accepted_genesis_payload as _accepted_genesis_payload
from research_system.discovery.replay.scope import EventScope
from research_system.errors import IntegrityError


def reduce_w11_catalogue_genesis_imported(scope: EventScope) -> None:
    """Reduce W11CatalogueGenesisImported."""

    state = scope.state
    payload = scope.payload
    event = scope.event

    if (
        state["catalogue"] is not None
        or event.get("command_type") != "ImportAcceptedW11CatalogueGenesis"
        or event.get("stream_id") != _CATALOGUE_STREAM_ID
        or payload != _accepted_genesis_payload()
    ):
        raise IntegrityError("W11 genesis identity mismatch")
    state["catalogue"] = deepcopy(payload)
