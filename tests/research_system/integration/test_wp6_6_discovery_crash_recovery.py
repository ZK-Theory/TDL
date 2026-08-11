from __future__ import annotations

from pathlib import Path

import pytest

from research_system.discovery import replay_discovery
from research_system.store.ledger import EventLedger
from tests.research_system.integration.test_wp6_6_discovery_runtime import (
    _accept_assay_bar,
    _command,
    _genesis,
    _ingest_candidate,
    _runtime,
)


def _registered_runtime(tmp_path: Path):
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff68"
    runtime.submit(_genesis())
    candidate_sha256 = _ingest_candidate(
        runtime,
        candidate_id,
        observation_id="obj_019fed25-b33e-7740-b280-6f661aaeff67",
        title="Crash-safe TDA-scale Candidate",
    )
    acceptance_sha256, producer_relation_sha256 = _accept_assay_bar(runtime)
    return runtime, candidate_id, candidate_sha256, acceptance_sha256, producer_relation_sha256


def test_multi_stream_batch_crash_before_publish_is_zero_mutation_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime, candidate_id, candidate_sha256, acceptance_sha256, producer_relation_sha256 = _registered_runtime(tmp_path)
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff69"
    command = _command(
        "RequestAssay",
        assay_id,
        0,
        {
            "row_id": "OR-003",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "candidate_revision": 1,
            "candidate_sha256": candidate_sha256,
            "assay_bar_acceptance_sha256": acceptance_sha256,
            "producer_relation_sha256": producer_relation_sha256,
        },
    )
    before = tuple(runtime.ledger.iter_events())
    discovery_control_root = runtime.ledger.control_root

    def interrupt_before_publish(ledger: EventLedger, _temporary: Path) -> None:
        if ledger.control_root == discovery_control_root:
            raise OSError("injected pre-publication interruption")

    with monkeypatch.context() as patch:
        patch.setattr(EventLedger, "_after_batch_fsync", interrupt_before_publish)
        with pytest.raises(OSError, match="pre-publication interruption"):
            runtime.submit(command)

    restarted = _runtime(tmp_path)
    assert tuple(restarted.ledger.iter_events()) == before
    assert assay_id not in replay_discovery(restarted.ledger.iter_events())["assays"]

    receipt = restarted.submit(command)
    assert receipt.status == "accepted"
    batch = tuple(restarted.ledger.iter_batches())[-1]
    assert tuple(event["event_type"] for event in batch) == (
        "AssayRequested",
        "AssayEvidenceCollectionOpened",
        "CandidateAssayRequested",
    )
    assert all(event["transaction_count"] == 3 for event in batch)
    assert replay_discovery(restarted.ledger.iter_events())["assays"][assay_id]["status"] == "evidence_collecting"


def test_multi_stream_batch_crash_after_publish_recovers_exact_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime, candidate_id, candidate_sha256, acceptance_sha256, producer_relation_sha256 = _registered_runtime(tmp_path)
    assay_id = "asy_019fed25-b33e-7740-b280-6f661aaeff6a"
    command = _command(
        "RequestAssay",
        assay_id,
        0,
        {
            "row_id": "OR-003",
            "candidate_id": candidate_id,
            "assay_id": assay_id,
            "candidate_revision": 1,
            "candidate_sha256": candidate_sha256,
            "assay_bar_acceptance_sha256": acceptance_sha256,
            "producer_relation_sha256": producer_relation_sha256,
        },
    )
    discovery_control_root = runtime.ledger.control_root

    def interrupt_after_publish(ledger: EventLedger, _target: Path) -> None:
        if ledger.control_root == discovery_control_root:
            raise OSError("injected post-publication interruption")

    with monkeypatch.context() as patch:
        patch.setattr(EventLedger, "_after_publish", interrupt_after_publish)
        with pytest.raises(OSError, match="post-publication interruption"):
            runtime.submit(command)

    restarted = _runtime(tmp_path)
    batches_before_retry = tuple(restarted.ledger.iter_batches())
    committed = next(batch for batch in batches_before_retry if batch[0]["command_id"] == command["command_id"])
    assert tuple(event["event_type"] for event in committed) == (
        "AssayRequested",
        "AssayEvidenceCollectionOpened",
        "CandidateAssayRequested",
    )

    repaired = restarted.submit(command)
    assert repaired.status == "accepted"
    assert repaired.event_batch_id == committed[0]["transaction_id"]
    assert repaired.observed_stream_version == 2
    assert tuple(_runtime(tmp_path).ledger.iter_batches()) == batches_before_retry
