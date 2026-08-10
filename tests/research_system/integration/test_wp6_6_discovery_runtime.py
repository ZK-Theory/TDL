from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from research_system.discovery.runtime import DiscoveryRuntime, replay_discovery
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.schema_registry import bundled_runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.receipts import ReceiptStore


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOGUE = REPO_ROOT / ".research-system" / "evals" / "expected" / "w11-portfolio-discovery-v1.json"
PROJECT_ID = "prj_019fed25-b33e-7740-b280-6f661aaeff58"
ACTOR_ID = "act_019fed25-b33e-7740-b280-6f661aaeff58"
GRANT_ID = "agr_019fed25-b33e-7740-b280-6f661aaeff58"


def _runtime(tmp_path: Path) -> DiscoveryRuntime:
    schemas = bundled_runtime_schema_registry()
    return DiscoveryRuntime(
        tmp_path,
        EventLedger(tmp_path, PROJECT_ID, schemas),
        schemas,
        catalogue_path=CATALOGUE,
    )


def _genesis() -> dict[str, object]:
    return {
        "command_id": new_id("command"),
        "command_type": "ImportAcceptedW11CatalogueGenesis",
        "actor_id": ACTOR_ID,
        "authority_grant_id": GRANT_ID,
        "idempotency_key": "wp6.6:w11:09be63a9",
        "target_stream_id": "w11_catalogue",
        "expected_stream_version": 0,
        "payload": {
            "accepted_commit": "09be63a9ba7e9525f5f69b8b8154b06d86a3c2b6",
            "accepted_tree": "151e0f8b24ad76913640aa0f1de66cd177a44f8f",
            "catalogue_blob": "8d58818540e04859f929d4b04c71e4cfa0512554",
            "catalogue_bytes": 136229,
            "catalogue_sha256": "7e36b39a3a0aa0a01e262e9f8a8c0d8a35f111c76efa0054f2c326ee15860b80",
            "bootstrap_blob": "aac7242072c3ce62370dd74d9a27a29e1a33070d",
            "bootstrap_sha256": "ebb7529a3bbf8faea9101b1556b3b71e6e0b3b9dbe0df163591466903d569d38",
            "review_commit": "bd61f00d05191de1fd330e997d33ba74ac1b506c",
            "review_blob": "2e0deee51e526cc712c6b04a79695abaa4fb6442",
            "review_sha256": "beb96faa0b58d3ba5faf326b94bb7bc7e1d6649b00c577f2239e1083fe09eaf9",
            "owner_decision": "I accept the KAN 84 envelope, proceed.",
        },
    }


def test_exact_w11_genesis_is_one_time_replay_safe_and_tamper_atomic(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    command = _genesis()

    accepted = runtime.submit(command)
    duplicate = runtime.submit(deepcopy(command))

    assert accepted.status == "accepted"
    assert duplicate == accepted
    events = tuple(runtime.ledger.iter_events())
    assert len(events) == 1
    projection = replay_discovery(events)
    assert projection["catalogue"]["row_count"] == 81
    assert projection["catalogue"]["row_ids"] == [
        *[f"OR-{number:03d}" for number in range(1, 42)],
        *[f"OR-{number:03d}" for number in range(101, 141)],
    ]

    tampered = _genesis()
    tampered["payload"]["catalogue_sha256"] = "0" * 64  # type: ignore[index]
    before = tuple(runtime.ledger.iter_events())
    with pytest.raises(IntegrityError, match="catalogue identity mismatch"):
        runtime.submit(tampered)
    assert tuple(runtime.ledger.iter_events()) == before


def test_candidate_registration_runs_through_durable_public_seam(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff58"
    candidate = {
        "command_id": new_id("command"),
        "command_type": "RegisterCandidate",
        "actor_id": ACTOR_ID,
        "authority_grant_id": GRANT_ID,
        "idempotency_key": f"wp6.6:candidate:{candidate_id}:1",
        "target_stream_id": candidate_id,
        "expected_stream_version": 0,
        "payload": {
            "candidate_id": candidate_id,
            "revision": 1,
            "content_sha256": "1" * 64,
            "source_observation_refs": ["obs:tda-scale:v1"],
            "title": "TDA-scale dossier candidate",
        },
    }

    with pytest.raises(IntegrityError, match="W11 genesis is required"):
        runtime.submit(candidate)
    assert tuple(runtime.ledger.iter_events()) == ()

    runtime.submit(_genesis())
    receipt = runtime.submit(candidate)
    duplicate = runtime.submit(deepcopy(candidate))

    assert receipt.status == "accepted"
    assert duplicate == receipt
    restarted = _runtime(tmp_path)
    projection = replay_discovery(restarted.ledger.iter_events())
    assert projection["candidates"][candidate_id] == {
        "candidate_id": candidate_id,
        "revision": 1,
        "content_sha256": "1" * 64,
        "status": "registered",
        "source_observation_refs": ["obs:tda-scale:v1"],
        "title": "TDA-scale dossier candidate",
        "version": 1,
    }


def test_genesis_retry_repairs_receipt_after_committed_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    command = _genesis()
    original_write = ReceiptStore.write
    calls = 0

    def interrupt_once(store: ReceiptStore, receipt: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected receipt interruption")
        return original_write(store, receipt)  # type: ignore[arg-type]

    monkeypatch.setattr(ReceiptStore, "write", interrupt_once)
    with pytest.raises(OSError, match="receipt interruption"):
        runtime.submit(command)
    assert len(tuple(runtime.ledger.iter_events())) == 1

    repaired = _runtime(tmp_path).submit(command)
    assert repaired.status == "accepted"
    assert len(tuple(runtime.ledger.iter_events())) == 1
