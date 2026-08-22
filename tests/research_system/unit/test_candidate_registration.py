from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.command.models import Command
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    recover_registered_content,
    register_candidate_document,
)


ARTEFACT_ID = "art_019fe47a-3001-7000-8000-000000003001"


def test_command_service_cold_import_is_independent_of_methods_registration() -> None:
    """The lower-level registered-content dependency must not reintroduce this cycle."""

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from research_system.command.service import CommandService; print(CommandService.__name__)",
        ],
        cwd=Path(__file__).resolve().parents[3],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "CommandService"


def test_registration_reexports_the_lower_level_content_store() -> None:
    from research_system.store.registered_content import CandidateDocumentStore as LowerLevelStore

    assert CandidateDocumentStore is LowerLevelStore


def test_registered_content_preserves_primary_error_when_anchor_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.registered_content as registered_content_module

    class BrokenAnchor:
        def close(self) -> None:
            raise OSError("cleanup failure")

    monkeypatch.setattr(
        registered_content_module,
        "open_registered_root_anchor",
        lambda *_args, **_kwargs: BrokenAnchor(),
    )
    store = CandidateDocumentStore(tmp_path)

    with pytest.raises(ValueError, match="primary failure") as error:
        with store._open_directory(Path(), create=False):
            raise ValueError("primary failure")

    assert isinstance(error.value.__cause__, OSError)


def test_recovery_session_preserves_primary_error_when_root_cleanup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.registered_content as registered_content_module

    class Directory:
        def open_member_directory(self, *_args, **_kwargs):
            return self

        def close(self) -> None:
            return None

    class BrokenRoot:
        def open_member_directory(self, *_args, **_kwargs):
            return Directory()

        def close(self) -> None:
            raise OSError("root cleanup failure")

    monkeypatch.setattr(
        registered_content_module,
        "open_registered_root_anchor",
        lambda *_args, **_kwargs: BrokenRoot(),
    )
    store = CandidateDocumentStore(tmp_path)

    with pytest.raises(ValueError, match="primary recovery failure") as error:
        with store.recovery_session():
            raise ValueError("primary recovery failure")

    assert isinstance(error.value.__cause__, OSError)


def _create_directory_redirection(path: Path, target: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(target, target_is_directory=True)
        return
    except OSError:
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(path), str(target)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            if completed.returncode == 0:
                return
    pytest.skip("the platform cannot create a directory redirection")


@pytest.mark.parametrize(
    "redirected_relative_directory",
    ["methods", "runtime/registered-content-recovery"],
)
def test_registered_content_refuses_redirected_destination_without_writing_outside(
    tmp_path: Path,
    redirected_relative_directory: str,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    _create_directory_redirection(tmp_path / redirected_relative_directory, outside)
    store = CandidateDocumentStore(tmp_path)

    with pytest.raises(ConflictError, match="physical member directory|reparse"):
        if redirected_relative_directory == "methods":
            store.write(ARTEFACT_ID, b"must remain in control root")
        else:
            store.stage_recovery_marker(
                {"command_id": "cmd_00000000-0000-7000-8000-000000000001"},
                f"methods/documents/{ARTEFACT_ID}.json",
                b"must remain in control root",
            )

    assert list(outside.iterdir()) == []


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


def registration_event(envelope):
    return {
        "command_id": envelope["command_id"],
        "command_type": envelope["command_type"],
        "event_type": "ArtefactRegistered",
        "stream_id": envelope["target_stream_id"],
        "project_id": envelope["project_id"],
        "command_schema_id": envelope["schema_id"],
        "command_schema_version": envelope["schema_version"],
        "idempotency_key": envelope["idempotency_key"],
        "correlation_id": envelope["correlation_id"],
        "causation_id": envelope["causation_id"],
        "actor_id": envelope["actor_id"],
        "authority_grant_id": envelope["authority_grant_id"],
        "command_payload_hash": sha256_hex(canonical_bytes(envelope["payload"])),
        "payload": envelope["payload"],
    }


class FakeLedger:
    def __init__(self):
        self.events = []

    def snapshot(self):
        return SimpleNamespace(events=tuple(self.events))


class CommittingService:
    def __init__(self):
        self.ledger = FakeLedger()
        self.envelopes = []

    def submit(self, envelope):
        self.envelopes.append(envelope)
        event = registration_event(envelope)
        if not self.ledger.events:
            self.ledger.events.append(event)
            status = "accepted"
        else:
            status = "replayed"
        return SimpleNamespace(
            status=status,
            command_id=envelope["command_id"],
            payload_hash=Command(envelope).payload_hash,
            event_batch_id="tx-registration",
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
    service = CommittingService()

    registered = register_candidate_document(
        value={"document": "returned evidence"},
        registration=registration(),
        document_store=CandidateDocumentStore(tmp_path),
        command_service=service,
    )

    assert registered.receipt.status == "accepted"
    assert service.envelopes[0]["payload"]["manifest"]["authority"]["use_authority"] == "candidate"
    assert (tmp_path / registered.relative_path).read_bytes() == registered.raw_bytes


def test_accepted_registration_recovers_document_publish_on_exact_retry(tmp_path) -> None:
    class FailOnceStore(CandidateDocumentStore):
        attempts = 0

        def publish_registered(self, relative_path, raw_bytes, *, root_anchor=None):
            self.attempts += 1
            if self.attempts == 1:
                raise OSError("simulated post-authority publication interruption")
            return super().publish_registered(relative_path, raw_bytes, root_anchor=root_anchor)

    store = FailOnceStore(tmp_path)
    service = CommittingService()
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
    assert service.envelopes[0]["command_id"] == service.envelopes[1]["command_id"]


def test_recovery_without_an_exact_registration_event_publishes_nothing(tmp_path) -> None:
    class InterruptBeforeSubmit:
        ledger = FakeLedger()

        def submit(self, envelope):
            del envelope
            raise OSError("transport failed before a receipt")

    store = CandidateDocumentStore(tmp_path)
    with pytest.raises(OSError, match="before a receipt"):
        register_candidate_document(
            value={"document": "returned evidence"},
            registration=registration(),
            document_store=store,
            command_service=InterruptBeforeSubmit(),
        )

    assert recover_registered_content(store, ()) == ()
    assert not (tmp_path / "methods" / "documents" / f"{ARTEFACT_ID}.json").exists()


def test_malformed_marker_blocks_all_recovery_publication(tmp_path) -> None:
    class InterruptBeforeSubmit:
        ledger = FakeLedger()

        def __init__(self):
            self.envelope = None

        def submit(self, envelope):
            self.envelope = envelope
            raise OSError("transport failed before a receipt")

    store = CandidateDocumentStore(tmp_path)
    service = InterruptBeforeSubmit()
    with pytest.raises(OSError):
        register_candidate_document(
            value={"document": "returned evidence"},
            registration=registration(),
            document_store=store,
            command_service=service,
        )
    assert service.envelope is not None
    recovery = tmp_path / "runtime" / "registered-content-recovery"
    (recovery / "cmd_00000000-0000-7000-8000-000000000000.json").write_bytes(b"{}")

    with pytest.raises(IntegrityError, match="recovery marker"):
        recover_registered_content(store, (registration_event(service.envelope),))

    assert not (tmp_path / "methods" / "documents" / f"{ARTEFACT_ID}.json").exists()


def test_recovery_keeps_the_physical_marker_directory_anchored_during_publication(
    tmp_path,
    monkeypatch,
) -> None:
    import research_system.store.registered_content as registered_content_module

    class FailOnceStore(CandidateDocumentStore):
        attempts = 0

        def publish_registered(self, relative_path, raw_bytes, *, root_anchor=None):
            self.attempts += 1
            if self.attempts == 1:
                raise OSError("interrupt after committed registration")
            return super().publish_registered(relative_path, raw_bytes, root_anchor=root_anchor)

    store = FailOnceStore(tmp_path)
    service = CommittingService()
    with pytest.raises(OSError, match="after committed"):
        register_candidate_document(
            value={"document": "returned evidence"},
            registration=registration(),
            document_store=store,
            command_service=service,
        )

    recovery = tmp_path / "runtime" / "registered-content-recovery"
    moved = tmp_path / "runtime" / "registered-content-recovery-moved"
    replacement_succeeded = []

    def attempt_replacement(_directory):
        try:
            recovery.rename(moved)
            recovery.mkdir()
        except OSError:
            replacement_succeeded.append(False)
        else:
            replacement_succeeded.append(True)

    monkeypatch.setattr(registered_content_module, "_after_recovery_directory_anchored", attempt_replacement)

    recovered = recover_registered_content(store, tuple(service.ledger.events))

    assert recovered == (f"methods/documents/{ARTEFACT_ID}.json",)
    assert (tmp_path / recovered[0]).read_bytes() == canonical_bytes({"document": "returned evidence"})
    assert replacement_succeeded == ([True] if moved.exists() else [False])
    if moved.exists():
        assert list(moved.iterdir()) == []
