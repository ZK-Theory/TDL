from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from research_system.canonical import canonical_bytes
from research_system.errors import ArsError, ConflictError, IntegrityError
from research_system.methods import registration as registration_module
from research_system.methods.registration import (
    CandidateDocumentStore,
    CandidateRegistration,
    prepare_candidate_document,
    recover_registered_content,
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


def _prepared(tmp_path):
    store = CandidateDocumentStore(tmp_path)
    prepared = prepare_candidate_document(
        value={"document": "returned evidence"},
        registration=registration(),
        document_store=store,
    )
    return prepared, store


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


def test_recovery_marker_crash_before_atomic_publish_leaves_final_name_absent(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared, _store = _prepared(tmp_path)

    class SimulatedHardStop(BaseException):
        pass

    observed = []

    def stop_after_fsync(temporary, target):
        observed.append((temporary, target))
        assert temporary.read_bytes()
        assert not target.exists()
        raise SimulatedHardStop

    monkeypatch.setattr(registration_module, "_after_contained_file_fsync", stop_after_fsync)
    with pytest.raises(SimulatedHardStop):
        registration_module._publish_recovery_marker(
            tmp_path,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )

    assert observed
    assert observed[0][0].exists()
    marker_directory = tmp_path / "runtime" / "registered-content-recovery"
    assert not tuple(marker_directory.glob("*.json"))


def test_partial_abandoned_marker_stage_does_not_wedge_recovery_or_exact_retry(tmp_path) -> None:
    prepared, _store = _prepared(tmp_path)
    marker_directory = tmp_path / "runtime" / "registered-content-recovery"
    marker_directory.mkdir(parents=True)
    abandoned = marker_directory / f".{prepared.command['command_id']}.json.{'a' * 32}.tmp"
    abandoned.write_bytes(b'{"schema_id":')

    marker_relative = registration_module._publish_recovery_marker(
        tmp_path,
        prepared.command,
        prepared.relative_path,
        prepared.raw_bytes,
    )
    first_bytes = (tmp_path / marker_relative).read_bytes()
    recover_registered_content(tmp_path, ())
    retried_relative = registration_module._publish_recovery_marker(
        tmp_path,
        prepared.command,
        prepared.relative_path,
        prepared.raw_bytes,
    )

    assert retried_relative == marker_relative
    assert (tmp_path / marker_relative).read_bytes() == first_bytes
    assert abandoned.read_bytes() == b'{"schema_id":'


def test_live_conflicting_recovery_marker_is_never_replaced(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    prepared, _store = _prepared(tmp_path)
    competing = canonical_bytes({"live": "other registration"})

    def publish_competing_final(_temporary, target):
        target.write_bytes(competing)

    monkeypatch.setattr(
        registration_module,
        "_after_contained_file_fsync",
        publish_competing_final,
    )

    with pytest.raises(ConflictError, match="already binds different bytes"):
        registration_module._publish_recovery_marker(
            tmp_path,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )

    marker_directory = tmp_path / "runtime" / "registered-content-recovery"
    marker = marker_directory / f"{prepared.command['command_id']}.json"
    assert marker.read_bytes() == competing
    assert not tuple(marker_directory.glob(".*.tmp"))


def test_staging_leaf_remains_bound_until_final_publication(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    prepared, _store = _prepared(tmp_path)
    replacement_attempted = False
    replacement_blocked = False

    def replace_staging(temporary, _target):
        nonlocal replacement_attempted, replacement_blocked
        replacement_attempted = True
        try:
            temporary.unlink()
            temporary.write_bytes(b"attacker replacement")
        except PermissionError:
            replacement_blocked = True

    monkeypatch.setattr(registration_module, "_after_contained_file_fsync", replace_staging)
    marker = tmp_path / "runtime" / "registered-content-recovery" / f"{prepared.command['command_id']}.json"
    if os.name == "nt":
        registration_module._publish_recovery_marker(
            tmp_path,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )
        assert replacement_attempted and replacement_blocked
        assert json.loads(marker.read_bytes())["command"]["command_id"] == prepared.command["command_id"]
    else:
        with pytest.raises(IntegrityError, match="staging identity changed"):
            registration_module._publish_recovery_marker(
                tmp_path,
                prepared.command,
                prepared.relative_path,
                prepared.raw_bytes,
            )
        assert replacement_attempted
        assert not marker.exists()


def test_foreign_destination_replacement_survives_failed_publish_and_exact_retry(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared, _store = _prepared(tmp_path)
    foreign = canonical_bytes({"live": "foreign replacement"})
    replacement_attempted = False
    replacement_blocked = False
    replacement_completed = False

    def replace_published_destination(_temporary, target):
        nonlocal replacement_attempted, replacement_blocked, replacement_completed
        replacement_attempted = True
        try:
            target.unlink()
            target.write_bytes(foreign)
        except PermissionError:
            replacement_blocked = True
        else:
            replacement_completed = True

    monkeypatch.setattr(
        registration_module,
        "_after_contained_file_linked",
        replace_published_destination,
    )
    marker = tmp_path / "runtime" / "registered-content-recovery" / f"{prepared.command['command_id']}.json"

    publication_error = None
    try:
        registration_module._publish_recovery_marker(
            tmp_path,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )
    except IntegrityError as exc:
        publication_error = exc
    monkeypatch.setattr(registration_module, "_after_contained_file_linked", lambda _temporary, _target: None)

    if replacement_completed:
        assert isinstance(publication_error, IntegrityError)
        assert "published file identity differs" in str(publication_error)
        assert replacement_attempted
        assert marker.read_bytes() == foreign
        with pytest.raises(ConflictError, match="already binds different bytes"):
            registration_module._publish_recovery_marker(
                tmp_path,
                prepared.command,
                prepared.relative_path,
                prepared.raw_bytes,
            )
        assert marker.read_bytes() == foreign
    else:
        assert publication_error is None
        assert replacement_attempted and replacement_blocked
        expected = canonical_bytes(
            registration_module._recovery_marker(prepared.command, prepared.relative_path, prepared.raw_bytes)
        )
        assert marker.read_bytes() == expected
        registration_module._publish_recovery_marker(
            tmp_path,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )
        assert marker.read_bytes() == expected


def test_parent_redirect_preserves_foreign_destination_and_exact_retry_is_safe(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepared, _store = _prepared(tmp_path)
    foreign = canonical_bytes({"live": "redirected destination"})
    redirect_attempted = False
    redirect_blocked = False
    redirect_completed = False

    def redirect_published_parent(_temporary, target):
        nonlocal redirect_attempted, redirect_blocked, redirect_completed
        redirect_attempted = True
        detached = target.parent.with_name(f"{target.parent.name}-detached")
        try:
            target.parent.rename(detached)
            target.parent.mkdir()
            target.write_bytes(foreign)
        except PermissionError:
            redirect_blocked = True
        else:
            redirect_completed = True

    monkeypatch.setattr(
        registration_module,
        "_after_contained_file_linked",
        redirect_published_parent,
    )
    marker = tmp_path / "runtime" / "registered-content-recovery" / f"{prepared.command['command_id']}.json"
    detached_parent = marker.parent.with_name(f"{marker.parent.name}-detached")

    publication_error = None
    try:
        registration_module._publish_recovery_marker(
            tmp_path,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )
    except IntegrityError as exc:
        publication_error = exc
    monkeypatch.setattr(registration_module, "_after_contained_file_linked", lambda _temporary, _target: None)

    if redirect_completed:
        assert isinstance(publication_error, IntegrityError)
        assert redirect_attempted
        assert marker.read_bytes() == foreign
        assert not tuple(detached_parent.glob(f".{marker.name}.*.tmp"))
        assert not (detached_parent / marker.name).exists()
        with pytest.raises(ConflictError, match="already binds different bytes"):
            registration_module._publish_recovery_marker(
                tmp_path,
                prepared.command,
                prepared.relative_path,
                prepared.raw_bytes,
            )
        assert marker.read_bytes() == foreign
    else:
        assert publication_error is None
        assert redirect_attempted and redirect_blocked
        expected = canonical_bytes(
            registration_module._recovery_marker(prepared.command, prepared.relative_path, prepared.raw_bytes)
        )
        assert marker.read_bytes() == expected
        registration_module._publish_recovery_marker(
            tmp_path,
            prepared.command,
            prepared.relative_path,
            prepared.raw_bytes,
        )
        assert marker.read_bytes() == expected


def test_exact_recovery_marker_publication_is_idempotent(tmp_path) -> None:
    prepared, _store = _prepared(tmp_path)

    first = registration_module._publish_recovery_marker(
        tmp_path,
        prepared.command,
        prepared.relative_path,
        prepared.raw_bytes,
    )
    first_bytes = (tmp_path / first).read_bytes()
    second = registration_module._publish_recovery_marker(
        tmp_path,
        prepared.command,
        prepared.relative_path,
        prepared.raw_bytes,
    )

    assert second == first
    assert (tmp_path / first).read_bytes() == first_bytes
    assert json.loads(first_bytes)["command"]["command_id"] == prepared.command["command_id"]
    assert not tuple((tmp_path / "runtime/registered-content-recovery").glob(".*.tmp"))
