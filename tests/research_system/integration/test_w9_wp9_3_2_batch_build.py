# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-2 §12.1, §10.5; O9)
# Purpose: the builder's batch mode (the WP9.3-2 plan's Q1, Stephen 2026-11-11): the LR-016 content and the ownership
# list's fixed parts from record files, then the full list printed by `ars legacy show` after a real LR-016 submit.
"""Batch build mode (WP9.3 note §12.1, §10.5; P-083 item 6, O9). Scratch stores and repositories under tmp_path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from research_system import cli
from research_system.errors import IntegrityError
from research_system.legacy.inventory import ASSIGNED_AT_LR_016, build_acceptance_batch
from research_system.legacy.records import ownership_record_id
from research_system.legacy.replay.driver import replay_legacy
from tests.research_system.integration import w9_flows as flows
from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes
from tests.research_system.integration.w9_runtime_harness import W9Store, w9_store


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> W9Store:
    return w9_store(tmp_path, monkeypatch)


def _batch_input(store: W9Store) -> tuple[dict[str, Any], str, str]:
    registration = store.register("results/x.json")
    receipt, observation_id = store.observe(store.observation_payload(registration))
    assert receipt.status == "accepted"
    template = store.acceptance_payload([observation_id])
    observation = store.recorded("legacy_observation", observation_id)
    batch = {
        "project_id": template["project_id"],
        "items": [
            {
                "observation": observation,
                "registration": registration,
                "membership": None,
                "pilot_promotion": flows.pilot_promotion(),
            }
        ],
        **{
            key: template[key]
            for key in (
                "threshold_preregistration_sha256",
                "governing_record_set_sha256",
                "anchors",
                "enforcement_change_list",
            )
        },
    }
    return batch, observation_id, registration["record_id"]


def test_batch_mode_prints_the_fixed_parts_and_show_prints_the_stored_list_after_lr016(
    store: W9Store, tmp_path: Path, monkeypatch, capsys
) -> None:
    batch, observation_id, registration_id = _batch_input(store)
    batch_file = tmp_path / "batch.json"
    batch_file.write_text(json.dumps(batch), encoding="utf-8")
    vault = tmp_path / "vault"
    vault.mkdir()
    output = tmp_path / "out" / "acceptance.json"
    output.parent.mkdir()
    argv = ["legacy", "inventory", "batch", "--batch", str(batch_file), "--vault-root", str(vault)]
    assert cli.main([*argv, "--output", str(output)]) == 0
    printed = json.loads(capsys.readouterr().out)
    proposal = json.loads(output.read_text(encoding="utf-8"))
    [row] = printed["ownership_list"]
    assert row["observation_id"] == observation_id and row["transitions"] is True
    assert {row[key] for key in ("record_id", "created_at", "content_hash")} == {ASSIGNED_AT_LR_016}
    assert not {"created_at", "created_by_actor_id", "content_hash"} & set(proposal)

    # The proposal the tool built is admitted at LR-016, and replay's stored list agrees with the printed parts.
    assert store.accept(proposal, stop_after="LR-016").status == "accepted"
    state = replay_legacy(store.events(), schemas=store.harness.schemas, pinned_signatures=(store.pin,))
    [stored] = state["proposals"][proposal["record_id"]]["ownership"]
    for key in ("subject_registration_ref", "from_mode", "to_mode", "reviewer_ref", "decision_ref"):
        assert stored[key] == row[key]
    created_at = state["proposals"][proposal["record_id"]]["record"]["created_at"]
    assert stored["record_id"] == ownership_record_id(proposal["record_id"], registration_id, created_at)

    # `ars legacy show` prints the stored list in full, read-only.
    def bind(root: Path, **kwargs: Any) -> Any:
        assert kwargs == {"read_only": True}
        return store.harness.ledger, store.harness.schemas, store.harness.authority_resolver

    monkeypatch.setattr(cli, "_verified_ledger", bind)
    control_root = store.harness.ledger.control_root
    before = _tree_bytes(control_root)
    assert cli.main(["legacy", "show", proposal["record_id"], "--control-root", str(control_root)]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["proposal"]["ownership"] == [stored]
    assert _tree_bytes(control_root) == before


def test_batch_mode_marks_an_item_that_does_not_cover_the_whole_file_as_transitioning_nothing(store: W9Store) -> None:
    batch, _, _ = _batch_input(store)
    tracker = store.register("tracker.md", role="legacy_coordination")
    inventory = store.inventory(tracker)
    row = inventory["rows"][0]
    payload = store.observation_payload(
        tracker,
        selector={
            "selector_kind": "inventory_item",
            "inventory_ref": flows.record_ref(inventory),
            "row_ordinal": row["row_ordinal"],
            "anchor_text": row["anchor_text"],
            "raw_row_sha256": row["raw_row_sha256"],
        },
        family="item",
    )
    receipt, item_id = store.observe(payload)
    assert receipt.status == "accepted"
    batch["items"].append(
        {
            "observation": store.recorded("legacy_observation", item_id),
            "registration": tracker,
            "membership": None,
            "pilot_promotion": flows.pilot_promotion(),
        }
    )
    _, preview = build_acceptance_batch(batch)
    assert [entry["transitions"] for entry in preview] == [True, False]
    assert set(preview[1]) == {"observation_id", "transitions"}


def test_batch_mode_refuses_a_record_not_at_its_recomputed_hash(store: W9Store) -> None:
    batch, _, _ = _batch_input(store)
    batch["items"][0]["observation"] = {**batch["items"][0]["observation"], "observer_actor_id": "someone"}
    with pytest.raises(IntegrityError, match="W9 batch build legacy_observation record is not at its recomputed"):
        build_acceptance_batch(batch)


def test_batch_mode_refuses_an_observation_of_another_registration(store: W9Store) -> None:
    batch, _, _ = _batch_input(store)
    batch["items"][0]["registration"] = store.register("tracker.md", role="legacy_coordination")
    with pytest.raises(IntegrityError, match="W9 batch build observation names another registration"):
        build_acceptance_batch(batch)


def test_batch_mode_refuses_a_malformed_input() -> None:
    with pytest.raises(IntegrityError, match="W9 batch build input does not have the fixed format"):
        build_acceptance_batch({"items": []})


@pytest.mark.parametrize(
    ("where", "message"),
    [
        ("apm", "W9 tool output is under .apm/"),
        ("vault", "W9 tool output is under the vault"),
        ("store", "W9 tool output is inside a store"),
        ("existing", "W9 tool output already exists"),
    ],
)
def test_batch_mode_refuses_a_forbidden_output_before_reading(tmp_path: Path, capsys, where: str, message: str) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    store = tmp_path / "store"
    (store / "manifests").mkdir(parents=True)
    (store / "manifests" / "store-identity.json").write_text("{}", encoding="utf-8")
    existing = tmp_path / "existing.json"
    existing.write_text("{}", encoding="utf-8")
    outputs = {"apm": tmp_path / ".apm" / "a.json", "vault": vault / "a.json", "store": store / "a.json"}
    outputs["existing"] = existing
    batch = tmp_path / "missing-batch.json"  # never read: the guard runs first
    before = _tree_bytes(tmp_path)
    argv = ["legacy", "inventory", "batch", "--batch", str(batch), "--vault-root", str(vault)]
    assert cli.main([*argv, "--output", str(outputs[where])]) == 1
    assert message in capsys.readouterr().err
    assert _tree_bytes(tmp_path) == before
