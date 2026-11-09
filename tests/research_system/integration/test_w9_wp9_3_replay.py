# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1; P-080, P-081)
# Purpose: WP9.3-1's replay half on forged scratch ledgers: LR-003 to LR-015, N-2, identities, W2 encodings, lapse.
"""WP9.3-1 replay controls (WP9.3 note §4 to §9, §14, §17).

The base ledger is a scratch store holding W11 genesis and a real W9 genesis. Every flow is forged onto a copy and
re-hashed; nothing is written back. Each negative control changes one field of an otherwise valid flow and asserts the
refusing check's own message, so it reaches the guard itself (note §17).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import research_system.legacy.accepted_w9 as accepted_w9
from research_system.discovery.runtime import replay_discovery
from research_system.legacy.replay.driver import replay_legacy
from research_system.projection.replay import rebuild_projection
from research_system.projection.replay import replay as replay_projection
from tests.research_system.contracts.test_w9_contract_materialization import _load_tool
from tests.research_system.factories import ACTORS
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_legacy_runtime import _genesis_command, _store
from tests.research_system.integration.w9_flows import Actors, Forger, at

OWNER = ACTORS["actor-a"]
PIN = flows.signature()
SEGMENTER = _load_tool("w9_segmentation")
TRACKER = b"## Task Tracking\n| Task | S |\n|---|---|\n| 1.1 | a |\n| 1.2 | b |\n"
SOURCE_SHA = "a" * 64


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> tuple[Forger, Any]:
    tmp_path = tmp_path_factory.mktemp("w9-wp9-3-replay")
    runtime, harness = _store(tmp_path)
    runtime.submit(_genesis_command(harness))
    return Forger(tuple(harness.ledger.iter_events())), harness.schemas


@pytest.fixture
def actors() -> Actors:
    return Actors(owner=OWNER)


def _replay(forger: Forger, schemas: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("pinned_signatures", (PIN,))
    return replay_legacy(forger.events, schemas=schemas, **kwargs)


def _segmented() -> dict[str, Any]:
    return SEGMENTER.segment(TRACKER, "tracker_task_row")


def _full_flow(base_forger: Forger, actors: Actors) -> tuple[Forger, dict[str, dict[str, Any]]]:
    """A registration, a membership table, a tracker registration and inventory, and one observation of each kind."""
    forger, registration = flows.registered(base_forger, actors)
    forger, table = flows.membership_recorded(forger, actors, sha256=SOURCE_SHA, size=1)
    forger, tracker = flows.registered(
        forger, actors, start=30, path="tracker.md", role="legacy_coordination", file_id="2"
    )
    forger, inventory = flows.inventory_recorded(forger, actors, tracker, _segmented(), start=40)
    whole = flows.observation(forger.project_id, actors.observer, at(50), registration, PIN)
    forger = forger.row("LR-015", whole["record_id"], whole, actor=actors.observer, when=at(50))
    family_set = flows.observation(
        forger.project_id,
        actors.observer,
        at(51),
        registration,
        PIN,
        count=1,
        selector={
            "selector_kind": "json_family_set",
            "membership_ref": flows.record_ref(table),
            "family_names": ["headline"],
        },
        families=[flows.signed_family("headline", PIN)],
    )
    forger = forger.row("LR-015", family_set["record_id"], family_set, actor=actors.observer, when=at(51))
    row = inventory["rows"][0]
    item = flows.observation(
        forger.project_id,
        actors.observer,
        at(52),
        tracker,
        PIN,
        selector={
            "selector_kind": "inventory_item",
            "inventory_ref": flows.record_ref(inventory),
            "row_ordinal": 1,
            "anchor_text": row["anchor_text"],
            "raw_row_sha256": row["raw_row_sha256"],
        },
        families=[flows.signed_family("item", PIN)],
    )
    forger = forger.row("LR-015", item["record_id"], item, actor=actors.observer, when=at(52))
    return forger, {
        "registration": registration,
        "table": table,
        "tracker": tracker,
        "inventory": inventory,
        "whole": whole,
        "family_set": family_set,
        "item": item,
    }


# --- The whole flow (note §17, first row) ----------------------------------------------------------------------------


def test_whole_flow_replays_through_every_public_replay(base, actors, monkeypatch, tmp_path: Path) -> None:
    forger, records = _full_flow(*base[:1], actors)
    schemas = base[1]
    # The public replay calls replay_legacy with the code's pins, so the test pin is injected there.
    monkeypatch.setattr(accepted_w9, "ACCEPTED_W0_SIGNATURES", (PIN,))
    replay_projection(forger.events, schema_registry=schemas)
    rebuild_projection(forger.events, tmp_path / "projection.json", schemas)
    replay_discovery(forger.events, schemas=schemas)
    state = replay_legacy(forger.events, schemas=schemas)
    assert set(state["records"]["legacy_path_registration"]) == {
        records["registration"]["record_id"],
        records["tracker"]["record_id"],
    }
    assert set(state["records"]["legacy_observation"]) == {
        records[key]["record_id"] for key in ("whole", "family_set", "item")
    }
    assert state["row_counts"] == {
        "LR-001": 1,
        **{row: 2 for row in ("LR-003", "LR-004", "LR-005")},
        **{f"LR-{n:03d}": 1 for n in range(6, 15)},
        "LR-015": 3,
    }
    # Every pre-assigned ID was reserved and then used.
    assert all(reservation["used"] for reservation in state["reservations"].values())
    assert state["stale_observations"] == []
