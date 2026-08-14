from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.authority_actor import (
    AuthorityActorRegistrationService,
    RegisterAuthorityActor,
    read_actor_registration_intent,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, ConfigurationError, IntegrityError
from research_system.owner_authority import _known_authority_actor_classes
from research_system.schema_registry import bundled_runtime_schema_registry
from research_system.store.objects import ObjectStore


PROJECT = "prj_01978abc-1000-7000-8000-000000001000"
STORE = "a" * 64
OWNER = "act_01978abc-1002-7000-8000-000000001002"
ROOT_GRANT = "agr_01978abc-1000-7000-8000-000000001000"
NOW = datetime(2026, 8, 14, tzinfo=UTC)


def _intent(**changes: object) -> RegisterAuthorityActor:
    value = RegisterAuthorityActor(
        "Codex producer",
        "agent",
        "codex_desktop",
        "1.0",
        "desktop-session-1",
        "SPEC-01 assay producer",
        "producer",
        "producer/spec_01_assay",
        "2026-08-14T00:00:00Z",
        "2026-08-15T00:00:00Z",
        ("brief-ref", "session-ref"),
        "Register the observed live Codex producer session.",
        "register-codex-desktop-actor",
        "actor-retry-1",
    )
    return replace(value, **changes)


def _service(tmp_path: Path) -> AuthorityActorRegistrationService:
    context = SimpleNamespace(
        project_id=PROJECT,
        store_identity=STORE,
        owner_actor_id=OWNER,
        root_grant_id=ROOT_GRANT,
    )
    resolver = SimpleNamespace(administration_context=lambda: context)
    commands = frozenset(
        {
            "RequestAssay",
            "RecordAssayScore",
            "RecordAssayPartial",
            "ReviewDiscoveryOutcome",
        }
    )
    return AuthorityActorRegistrationService(
        tmp_path,
        PROJECT,
        STORE,
        bundled_runtime_schema_registry(),
        resolver,
        ObjectStore(tmp_path),
        commands,
        clock=lambda: NOW,
    )


def test_intent_requires_canonical_route_and_codex_app(tmp_path: Path) -> None:
    source = tmp_path / "intent.json"
    source.write_bytes(b'{"command_type":"RegisterAuthorityActor"}')
    with pytest.raises(ConfigurationError):
        read_actor_registration_intent(source)
    with pytest.raises(ArsError):
        _service(tmp_path).register(_intent(app_family="other_app"))
    with pytest.raises(ConfigurationError):
        _service(tmp_path).register(_intent(expires_at="2026-08-14T00:00:00Z"))


def test_registration_is_durable_and_retry_is_duplicate(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.register(_intent())
    second = service.register(_intent())
    assert first["status"] == "accepted"
    assert second["status"] == "duplicate"
    assert first["actor_id"] == second["actor_id"]
    assert (tmp_path / "receipts" / "authority_actor" / f"{first['registration_id']}.json").exists()
    assert not list((tmp_path / "runtime").glob(".authority-actor-registration-*.json"))


def test_retry_preserves_acceptance_bytes_when_clock_advances(tmp_path: Path) -> None:
    current = [NOW]
    service = _service(tmp_path)
    service.clock = lambda: current[0]
    first = service.register(_intent())
    current[0] += timedelta(seconds=1)
    second = service.register(_intent())
    assert second["status"] == "duplicate"
    assert second["registration_sha256"] == first["registration_sha256"]


def test_changed_retry_and_second_role_cannot_mutate_registration(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.register(_intent())
    with pytest.raises(ConflictError):
        service.register(_intent(reason="Changed meaning for the same retry key."))
    with pytest.raises(ConflictError):
        service.register(
            _intent(
                actor_role="independent_reviewer",
                authority_lane="independent_reviewer/outcome_review",
                session_purpose="SPEC-01 independent review",
                retry_key="actor-retry-2",
            )
        )


@pytest.mark.parametrize("boundary", ["actor", "registration", "event", "receipt"])
def test_registration_recovers_after_each_publication_boundary(tmp_path: Path, boundary: str) -> None:
    service = _service(tmp_path)

    def crash(stage: str) -> None:
        if stage == boundary:
            raise RuntimeError(f"crash at {stage}")

    with pytest.raises(RuntimeError):
        service.register(_intent(), phase_hook=crash)
    recovered = service.register(_intent())
    assert recovered["actor_id"]
    assert recovered["status"] in {"accepted", "duplicate"}
    assert len(list((tmp_path / "events" / PROJECT).rglob("*.jsonl"))) == 1
    assert not list((tmp_path / "runtime").glob(".authority-actor-registration-*.json"))


@pytest.mark.parametrize("first_role", ["producer", "independent_reviewer"])
def test_same_session_cannot_hold_producer_and_reviewer_in_either_order(tmp_path: Path, first_role: str) -> None:
    service = _service(tmp_path)
    if first_role == "producer":
        first = _intent()
        second = _intent(
            actor_role="independent_reviewer",
            authority_lane="independent_reviewer/outcome_review",
            session_purpose="SPEC-01 independent review",
            retry_key="actor-retry-2",
        )
    else:
        first = _intent(
            actor_role="independent_reviewer",
            authority_lane="independent_reviewer/outcome_review",
            session_purpose="SPEC-01 independent review",
        )
        second = _intent(
            actor_role="producer",
            authority_lane="producer/spec_01_assay",
            session_purpose="SPEC-01 assay producer",
            retry_key="actor-retry-2",
        )
    service.register(first)
    with pytest.raises(ConflictError):
        service.register(second)


def test_unknown_app_version_and_session_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ArsError):
        _service(tmp_path).register(_intent(observed_app_version="unknown"))
    with pytest.raises(ArsError):
        _service(tmp_path).register(_intent(session_identity="synthetic"))
    with pytest.raises(ArsError):
        _service(tmp_path).register(_intent(authority_lane="operator/not-a-route", actor_role="operator"))
    with pytest.raises(ArsError):
        _service(tmp_path).register(_intent(session_identity=OWNER))
    with pytest.raises(ConfigurationError):
        _service(tmp_path).register(_intent(expires_at="2026-08-14T00:00:00Z"))
    with pytest.raises(ConfigurationError):
        _service(tmp_path).register(_intent(effective_at="2026-08-13T00:00:00Z", expires_at="2026-08-13T23:00:00Z"))
    with pytest.raises(ConfigurationError):
        _service(tmp_path).register(_intent(expires_at="not-a-time"))
    assert not list((tmp_path / "events").rglob("*.jsonl"))
    assert not list((tmp_path / "objects" / "canonical_actor").rglob("*.json"))


@pytest.mark.parametrize(
    ("actor_role", "authority_lane"),
    (("producer", "producer/spec_01_assay"), ("independent_reviewer", "independent_reviewer/outcome_review")),
)
def test_owner_actor_cannot_register_non_owner_role_zero_publication(
    tmp_path: Path, actor_role: str, authority_lane: str
) -> None:
    with pytest.raises(ArsError):
        _service(tmp_path).register(
            _intent(session_identity=OWNER, actor_role=actor_role, authority_lane=authority_lane)
        )
    assert not list((tmp_path / "events").rglob("*.jsonl"))
    assert not list((tmp_path / "objects").rglob("*.json"))
    assert not list((tmp_path / "receipts").rglob("*.json"))


def test_generic_assurance_record_does_not_prove_actor(tmp_path: Path) -> None:
    service = _service(tmp_path)
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True)
    objects = ObjectStore(tmp_path)
    generic_id = "arec_01978abc-1000-7000-8000-000000001003"
    objects.write(
        "assurance_record",
        generic_id,
        1,
        {
            "schema_id": "ars://core/assurance-record",
            "schema_version": "1.0.0",
            "actor_id": "act_01978abc-1000-7000-8000-000000001004",
        },
    )
    assert _known_authority_actor_classes(tmp_path, objects) == {}
    result = service.register(_intent())
    assert _known_authority_actor_classes(tmp_path, objects)[result["actor_id"]] == frozenset({"agent"})


def test_foreign_registration_context_is_not_known_to_current_owner(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent())
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True)
    objects = ObjectStore(tmp_path)
    actor = objects.read("canonical_actor", result["actor_id"], 1)
    registration = objects.read("assurance_record", result["registration_id"], 1)
    foreign_actor = {
        **actor,
        "project_id": "prj_01978abc-1000-7000-8000-000000009999",
        "store_identity": "b" * 64,
        "owner_actor_id": "act_01978abc-1002-7000-8000-000000009999",
    }
    foreign_actor_sha = sha256_hex(canonical_bytes(foreign_actor))
    foreign_registration = {
        **registration,
        "project_id": foreign_actor["project_id"],
        "store_identity": foreign_actor["store_identity"],
        "owner_actor_id": foreign_actor["owner_actor_id"],
        "actor_sha256": foreign_actor_sha,
    }
    objects.write("canonical_actor", result["actor_id"], 2, foreign_actor)
    objects.write("assurance_record", result["registration_id"], 2, foreign_registration)
    assert (
        _known_authority_actor_classes(
            tmp_path,
            objects,
            project_id=PROJECT,
            store_identity=STORE,
            owner_actor_id=OWNER,
        )
        == {}
    )


def test_cli_accepts_semantic_intent_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from research_system import cli

    source = tmp_path / "intent.json"
    source.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://wp6-6/gate6/authority/command/RegisterAuthorityActor",
                "schema_version": "1.0.0",
                "command_type": "RegisterAuthorityActor",
                "retry_key": "cli-retry",
                "canonical_display_name": "Codex producer",
                "actor_class": "agent",
                "app_family": "codex_desktop",
                "observed_app_version": "1.0",
                "session_identity": "cli-session",
                "session_purpose": "SPEC-01 producer",
                "actor_role": "producer",
                "authority_lane": "producer/spec_01_assay",
                "effective_at": "2026-08-14T00:00:00Z",
                "expires_at": "2026-08-15T00:00:00Z",
                "evidence_refs": ["brief"],
                "reason": "Register the observed live Codex producer session.",
                "owner_action": "register-codex-desktop-actor",
            }
        )
    )

    class FakeSetup:
        def register_actor(self, intent: object) -> dict[str, str]:
            assert isinstance(intent, RegisterAuthorityActor)
            return {"status": "accepted"}

    monkeypatch.setattr(cli, "load_owner_authority_setup", lambda _path: FakeSetup())
    assert (
        cli.main(
            ["authority", "register-actor", "--setup-config", str(tmp_path / "setup.json"), "--intent", str(source)]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {"status": "accepted"}


def test_registration_evidence_is_tamper_detected_before_owner_publication(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent())
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True)
    actor_path = next((tmp_path / "objects" / "canonical_actor" / result["actor_id"]).glob("*.json"))
    actor_path.write_bytes(actor_path.read_bytes().replace(b"Codex producer", b"Tampered producer"))
    with pytest.raises(IntegrityError):
        _known_authority_actor_classes(tmp_path, ObjectStore(tmp_path))


@pytest.mark.parametrize("field", ["actor_id", "actor_sha256"])
def test_registration_event_tamper_is_detected_on_retry(tmp_path: Path, field: str) -> None:
    service = _service(tmp_path)
    service.register(_intent())
    event_path = next((tmp_path / "events" / PROJECT).rglob("*.jsonl"))
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["payload"][field] = "act_01978abc-1000-7000-8000-000000001009" if field == "actor_id" else "0" * 64
    unsigned = dict(event)
    unsigned.pop("event_hash", None)
    event["event_hash"] = sha256_hex(canonical_bytes(unsigned))
    event_path.write_bytes(canonical_bytes(event) + b"\n")
    with pytest.raises(IntegrityError, match="event relation is invalid"):
        service.register(_intent())
