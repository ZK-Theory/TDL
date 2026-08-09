from __future__ import annotations

from types import SimpleNamespace

import pytest

from research_system.errors import ArsError
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    register_candidate_document,
)


ARTEFACT_ID = "art_019fe47a-3001-7000-8000-000000003001"


def registration() -> CandidateRegistration:
    return CandidateRegistration(
        artefact_id=ARTEFACT_ID,
        project_id="prj_01978abc-1000-7000-8000-000000001000",
        actor_id="act_01978abc-1001-7000-8000-000000001001",
        authority_grant_id="agr_019fe47a-3001-7000-8000-000000003001",
        submitted_at="2026-08-09T01:00:00Z",
        correlation_id="candidate-registration-test",
        reason="register one exact candidate",
        manifest={"artefact_id": ARTEFACT_ID, "authority": {"use_authority": "candidate"}},
    )


def test_rejected_candidate_registration_leaves_no_document_bytes(tmp_path) -> None:
    class RejectingService:
        def submit(self, envelope):
            del envelope
            return SimpleNamespace(status="rejected", reason_code="unauthorized")

    with pytest.raises(ArsError, match="was not accepted"):
        register_candidate_document(
            value={"document": "returned evidence"},
            registration=registration(),
            document_store=CandidateDocumentStore(tmp_path),
            command_service=RejectingService(),
        )

    assert not (tmp_path / "methods" / "documents" / f"{ARTEFACT_ID}.json").exists()


def test_accepted_candidate_registration_publishes_exact_document_bytes(tmp_path) -> None:
    receipt = SimpleNamespace(status="accepted")

    class AcceptingService:
        def submit(self, envelope):
            assert envelope["payload"]["manifest"]["authority"]["use_authority"] == "candidate"
            return receipt

    registered = register_candidate_document(
        value={"document": "returned evidence"},
        registration=registration(),
        document_store=CandidateDocumentStore(tmp_path),
        command_service=AcceptingService(),
    )

    assert registered.receipt is receipt
    assert (tmp_path / registered.relative_path).read_bytes() == registered.raw_bytes


def test_accepted_registration_recovers_document_publish_on_exact_retry(tmp_path) -> None:
    class FailOnceStore(CandidateDocumentStore):
        attempts = 0

        def write(self, artefact_id, raw_bytes):
            self.attempts += 1
            if self.attempts == 1:
                raise OSError("simulated post-authority publication interruption")
            return super().write(artefact_id, raw_bytes)

    class ReplayingService:
        attempts = 0
        command_ids = []

        def submit(self, envelope):
            self.command_ids.append(envelope["command_id"])
            self.attempts += 1
            return SimpleNamespace(status="accepted" if self.attempts == 1 else "replayed")

    store = FailOnceStore(tmp_path)
    service = ReplayingService()
    with pytest.raises(OSError, match="interruption"):
        register_candidate_document(
            value={"document": "returned evidence"},
            registration=registration(),
            document_store=store,
            command_service=service,
        )

    recovered = register_candidate_document(
        value={"document": "returned evidence"},
        registration=registration(),
        document_store=store,
        command_service=service,
    )
    assert (tmp_path / recovered.relative_path).read_bytes() == recovered.raw_bytes
    assert service.command_ids[0] == service.command_ids[1]
