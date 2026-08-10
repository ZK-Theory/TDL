from __future__ import annotations

from pathlib import Path

import pytest

from research_system.discovery import replay_discovery
from research_system.store.ledger import EventLedger
from tests.research_system.integration.test_wp6_6_discovery_runtime import (
    _command,
    _genesis,
    _runtime,
)


def _registered_runtime(tmp_path: Path):
    runtime = _runtime(tmp_path)
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaeff68"
    runtime.submit(_genesis())
    runtime.submit(
        _command(
            "RegisterCandidate",
            candidate_id,
            0,
            {
                "candidate_id": candidate_id,
                "revision": 1,
                "content_sha256": "a" * 64,
                "source_observation_refs": ["obs:tda-scale:crash-proof"],
                "title": "Crash-safe TDA-scale Candidate",
            },
        )
    )
    return runtime, candidate_id


def test_multi_stream_batch_crash_before_publish_is_zero_mutation_and_retryable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime, candidate_id = _registered_runtime(tmp_path)
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
            "candidate_sha256": "a" * 64,
            "assay_bar_acceptance_sha256": "b" * 64,
            "producer_relation_sha256": "c" * 64,
        },
    )
    before = tuple(runtime.ledger.iter_events())

    def interrupt_before_publish(_ledger: EventLedger, _temporary: Path) -> None:
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
    runtime, candidate_id = _registered_runtime(tmp_path)
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
            "candidate_sha256": "a" * 64,
            "assay_bar_acceptance_sha256": "b" * 64,
            "producer_relation_sha256": "c" * 64,
        },
    )

    def interrupt_after_publish(_ledger: EventLedger, _target: Path) -> None:
        raise OSError("injected post-publication interruption")

    with monkeypatch.context() as patch:
        patch.setattr(EventLedger, "_after_publish", interrupt_after_publish)
        with pytest.raises(OSError, match="post-publication interruption"):
            runtime.submit(command)

    restarted = _runtime(tmp_path)
    batches_before_retry = tuple(restarted.ledger.iter_batches())
    committed = batches_before_retry[-1]
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
