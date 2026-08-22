from __future__ import annotations

import os
import stat
import subprocess
import sys
import threading
import time
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


def test_exact_file_publication_never_leaves_a_partial_final_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed private-file flush must leave the immutable name retryable."""

    import research_system.store.lock as lock_module

    store = CandidateDocumentStore(tmp_path)
    expected = b"complete immutable content"
    original_fsync = lock_module.os.fsync
    failed = False

    def fail_first_regular_file_flush(descriptor: int) -> None:
        nonlocal failed
        if not failed and stat.S_ISREG(os.fstat(descriptor).st_mode):
            failed = True
            raise OSError("simulated interrupted content flush")
        original_fsync(descriptor)

    monkeypatch.setattr(lock_module.os, "fsync", fail_first_regular_file_flush)
    with pytest.raises(ConflictError, match="cannot be published"):
        store.write(ARTEFACT_ID, expected)

    final_path = tmp_path / "methods" / "documents" / f"{ARTEFACT_ID}.json"
    assert not final_path.exists()
    assert list(final_path.parent.iterdir()) == []

    monkeypatch.setattr(lock_module.os, "fsync", original_fsync)
    store.write(ARTEFACT_ID, expected)
    assert final_path.read_bytes() == expected


def test_publication_preserves_primary_failure_when_owned_temp_cleanup_also_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.lock as lock_module

    store = CandidateDocumentStore(tmp_path)
    original_fsync = lock_module.os.fsync
    original_unlink = lock_module.os.unlink

    def fail_regular_file_flush(descriptor: int) -> None:
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise OSError("primary fsync failure")
        original_fsync(descriptor)

    def fail_private_cleanup(path, *args, **kwargs) -> None:
        if str(path).endswith(".remove"):
            raise PermissionError("cleanup unlink failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(lock_module.os, "fsync", fail_regular_file_flush)
    monkeypatch.setattr(lock_module.os, "unlink", fail_private_cleanup)

    with pytest.raises(ConflictError, match="cannot be published") as error:
        store.write(ARTEFACT_ID, b"complete content")

    assert isinstance(error.value.__cause__, PermissionError)
    directory = tmp_path / "methods" / "documents"
    assert not (directory / f"{ARTEFACT_ID}.json").exists()
    assert len(tuple(directory.glob("*.remove"))) == 1


def test_anchored_member_validation_rejects_nul_as_a_domain_conflict(tmp_path: Path) -> None:
    store = CandidateDocumentStore(tmp_path)

    with store._open_directory(Path("methods/documents"), create=True) as directory:
        with pytest.raises(ConflictError, match="member name"):
            directory.write_exact_file("invalid\x00.json", b"never written")


def test_private_publication_name_collision_never_deletes_unowned_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.lock as lock_module

    store = CandidateDocumentStore(tmp_path)
    directory = tmp_path / "methods" / "documents"
    directory.mkdir(parents=True)
    final_name = f"{ARTEFACT_ID}.json"
    private = directory / f".{final_name}.fixed.tmp"
    private.write_bytes(b"unowned sentinel")
    monkeypatch.setattr(lock_module.secrets, "token_hex", lambda _length: "fixed")

    with pytest.raises(ConflictError, match="private publication name"):
        store.write(ARTEFACT_ID, b"new content")

    assert private.read_bytes() == b"unowned sentinel"
    assert not (directory / final_name).exists()


def test_private_publication_cleanup_never_deletes_a_substituted_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.lock as lock_module

    store = CandidateDocumentStore(tmp_path)
    original_link = lock_module.os.link
    substituted = False

    def substitute_before_claim(source, destination, *args, **kwargs) -> None:
        nonlocal substituted
        if not substituted and str(source).endswith(".tmp") and str(destination).endswith(".remove"):
            substituted = True
            if "src_dir_fd" in kwargs:
                directory_fd = kwargs["src_dir_fd"]
                os.unlink(source, dir_fd=directory_fd)
                descriptor = os.open(source, os.O_CREAT | os.O_EXCL | os.O_WRONLY, dir_fd=directory_fd)
                try:
                    os.write(descriptor, b"foreign-sentinel")
                finally:
                    os.close(descriptor)
            else:
                Path(source).unlink()
                Path(source).write_bytes(b"foreign-sentinel")
        original_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(lock_module.os, "link", substitute_before_claim)

    with pytest.raises(ConflictError, match="changed"):
        store.write(ARTEFACT_ID, b"complete content")

    directory = tmp_path / "methods" / "documents"
    assert (directory / f"{ARTEFACT_ID}.json").read_bytes() == b"complete content"
    preserved = [path.read_bytes() for path in directory.iterdir() if path.name.endswith((".tmp", ".remove"))]
    assert preserved and all(raw == b"foreign-sentinel" for raw in preserved)


def test_private_cleanup_never_overwrites_a_post_link_destination_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.lock as lock_module

    store = CandidateDocumentStore(tmp_path)
    original_link = lock_module.os.link
    substituted = False

    def substitute_claim_after_link(source, destination, *args, **kwargs) -> None:
        nonlocal substituted
        original_link(source, destination, *args, **kwargs)
        if not substituted and str(source).endswith(".tmp") and str(destination).endswith(".remove"):
            substituted = True
            if "dst_dir_fd" in kwargs:
                directory_fd = kwargs["dst_dir_fd"]
                os.unlink(destination, dir_fd=directory_fd)
                descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, dir_fd=directory_fd)
                try:
                    os.write(descriptor, b"foreign-destination")
                finally:
                    os.close(descriptor)
            else:
                Path(destination).unlink()
                Path(destination).write_bytes(b"foreign-destination")

    monkeypatch.setattr(lock_module.os, "link", substitute_claim_after_link)

    with pytest.raises(ConflictError, match="changed while creating removal claim"):
        store.write(ARTEFACT_ID, b"complete content")

    directory = tmp_path / "methods" / "documents"
    assert (directory / f"{ARTEFACT_ID}.json").read_bytes() == b"complete content"
    preserved = [path.read_bytes() for path in directory.iterdir() if path.name.endswith(".remove")]
    assert b"foreign-destination" in preserved


def test_private_cleanup_claim_collision_preserves_unowned_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.lock as lock_module

    store = CandidateDocumentStore(tmp_path)
    directory = tmp_path / "methods" / "documents"
    directory.mkdir(parents=True)
    final_name = f"{ARTEFACT_ID}.json"
    collision = directory / f".{final_name}.private.tmp.collision.remove"
    collision.write_bytes(b"unowned cleanup claim")
    tokens = iter(("private", "collision", "fresh"))
    monkeypatch.setattr(lock_module.secrets, "token_hex", lambda _length: next(tokens))

    store.write(ARTEFACT_ID, b"complete content")

    assert (directory / final_name).read_bytes() == b"complete content"
    assert collision.read_bytes() == b"unowned cleanup claim"
    assert sorted(path.name for path in directory.iterdir()) == [collision.name, final_name]


def test_exact_removal_claim_collision_preserves_unowned_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.lock as lock_module

    store = CandidateDocumentStore(tmp_path)
    directory_path = tmp_path / "methods" / "documents"
    directory_path.mkdir(parents=True)
    source = directory_path / "marker.json"
    source.write_bytes(b"owned marker")
    collision = directory_path / ".marker.json.collision.remove"
    collision.write_bytes(b"unowned removal claim")
    tokens = iter(("collision", "fresh"))
    monkeypatch.setattr(lock_module.secrets, "token_hex", lambda _length: next(tokens))

    with store._open_directory(Path("methods/documents"), create=False) as directory:
        directory.remove_exact_file("marker.json", b"owned marker")

    assert not source.exists()
    assert collision.read_bytes() == b"unowned removal claim"
    assert sorted(path.name for path in directory_path.iterdir()) == [collision.name]


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
        "transaction_id": "tx-registration",
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
        ledger = FakeLedger()

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


def test_accepted_receipt_must_name_the_exact_committed_registration_batch(tmp_path) -> None:
    class WrongBatchService(CommittingService):
        def submit(self, envelope):
            receipt = super().submit(envelope)
            return SimpleNamespace(
                **{
                    **vars(receipt),
                    "event_batch_id": "tx-unrelated",
                }
            )

    with pytest.raises(IntegrityError, match="committed event batch"):
        register_candidate_document(
            value={"document": "returned evidence"},
            registration=registration(),
            document_store=CandidateDocumentStore(tmp_path),
            command_service=WrongBatchService(),
        )

    assert not (tmp_path / "methods" / "documents" / f"{ARTEFACT_ID}.json").exists()


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


def test_concurrent_exact_registration_retries_cannot_invalidate_each_others_completion(tmp_path) -> None:
    first_check_entered = threading.Event()
    release_first_check = threading.Event()

    class CoordinatedStore(CandidateDocumentStore):
        checks = 0
        guard = threading.Lock()

        def marker_exists(self, marker):
            with self.guard:
                self.checks += 1
                check = self.checks
            if check == 1:
                first_check_entered.set()
                assert release_first_check.wait(timeout=5)
            return super().marker_exists(marker)

    store = CoordinatedStore(tmp_path)
    service = CommittingService()
    results = []
    failures: list[BaseException] = []

    def register() -> None:
        try:
            results.append(
                register_candidate_document(
                    value={"document": "returned evidence"},
                    registration=registration(),
                    document_store=store,
                    command_service=service,
                )
            )
        except BaseException as exc:
            failures.append(exc)

    first = threading.Thread(target=register)
    first.start()
    assert first_check_entered.wait(timeout=5)
    second = threading.Thread(target=register)
    second.start()
    second.join(timeout=5)
    assert not second.is_alive()
    release_first_check.set()
    first.join(timeout=5)

    assert not first.is_alive()
    assert failures == []
    assert len(results) == 2
    assert results[0].content_sha256 == results[1].content_sha256
    assert store.read_relative(results[0].relative_path) == results[0].raw_bytes


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
    assert len(replacement_succeeded) == 1
    assert list(recovery.iterdir()) == []
    if moved.exists():
        assert list(moved.iterdir()) == []


def test_concurrent_recovery_passes_are_serial_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.registered_content as registered_content_module

    class FailOnceStore(CandidateDocumentStore):
        attempts = 0

        def publish_registered(self, relative_path, raw_bytes, *, root_anchor=None):
            self.attempts += 1
            if self.attempts == 1:
                raise OSError("leave one committed marker for concurrent recovery")
            return super().publish_registered(relative_path, raw_bytes, root_anchor=root_anchor)

    store = FailOnceStore(tmp_path)
    service = CommittingService()
    with pytest.raises(OSError, match="committed marker"):
        register_candidate_document(
            value={"document": "returned evidence"},
            registration=registration(),
            document_store=store,
            command_service=service,
        )

    first_entered = threading.Event()
    release_first = threading.Event()
    hook_calls = 0
    hook_guard = threading.Lock()

    def hold_first_pass(_directory) -> None:
        nonlocal hook_calls
        with hook_guard:
            hook_calls += 1
            call = hook_calls
        if call == 1:
            first_entered.set()
            assert release_first.wait(timeout=5)

    monkeypatch.setattr(registered_content_module, "_after_recovery_directory_anchored", hold_first_pass)
    results: list[tuple[str, ...]] = []
    failures: list[BaseException] = []

    def recover() -> None:
        try:
            results.append(recover_registered_content(store, tuple(service.ledger.events)))
        except BaseException as exc:
            failures.append(exc)

    first = threading.Thread(target=recover)
    second = threading.Thread(target=recover)
    first.start()
    assert first_entered.wait(timeout=5)
    second.start()
    time.sleep(0.05)
    assert hook_calls == 1
    assert second.is_alive()
    release_first.set()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive() and not second.is_alive()
    assert failures == []
    assert sorted(results, key=len) == [(), (f"methods/documents/{ARTEFACT_ID}.json",)]
