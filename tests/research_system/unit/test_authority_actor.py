from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from research_system.authority_actor import (
    AuthorityActorRegistrationService,
    COMMAND_SCHEMA_ID,
    INTENT_SCHEMA_ID,
    REGISTRATION_SCHEMA_ID,
    RegisterAuthorityActor,
    authority_actor_command_id,
    authority_actor_idempotency_key,
    read_actor_registration_intent,
)
from research_system.authority import (
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
    EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError, ConflictError, ConfigurationError, IntegrityError, SchemaError
from research_system.owner_authority import _known_authority_actor_classes
from research_system.schema_registry import bundled_runtime_schema_registry
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore


PROJECT = "prj_01978abc-1000-7000-8000-000000001000"
STORE = "a" * 64
OWNER = "act_01978abc-1002-7000-8000-000000001002"
ROOT_GRANT = "agr_01978abc-1000-7000-8000-000000001000"
NOW = datetime(2026, 8, 14, tzinfo=UTC)


def _redirect_directory(link: Path, target: Path) -> None:
    """Create the platform's ordinary directory redirection primitive."""
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"Windows junction creation is unavailable: {result.stderr or result.stdout}")
    else:
        os.symlink(target, link, target_is_directory=True)


def _remove_directory_redirect(path: Path) -> None:
    if os.name == "nt":
        os.rmdir(path)
    else:
        path.unlink()


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
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True, exist_ok=True)
    (tmp_path / "objects" / "assurance_record").mkdir(parents=True, exist_ok=True)
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


def _authority_projection(
    tmp_path: Path,
    *grants: dict[str, object],
) -> dict[str, object]:
    """Stand in for the resolver's already-verified replay result."""

    actors: dict[str, dict[str, object]] = {}
    ledger = EventLedger(tmp_path, PROJECT, bundled_runtime_schema_registry())
    for event in ledger.iter_events():
        if event.get("event_type") != "AuthorityActorRegistered":
            continue
        payload = event["payload"]
        actors[str(payload["actor_id"])] = dict(payload)
    return {
        "authority_grants": {
            str(grant["authority_grant_id"]): {
                "authority_grant_id": grant["authority_grant_id"],
                "authority_grant_sha256": sha256_hex(canonical_bytes(grant)),
            }
            for grant in grants
        },
        "authority_actors": actors,
    }


def _scoped_grant(
    grant_id: str,
    actor_id: str,
    *,
    project_id: str = PROJECT,
    actor_class: str = "service",
) -> dict[str, object]:
    return {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.1.0",
        "authority_grant_id": grant_id,
        "actor_id": actor_id,
        "allowed_actor_classes": [actor_class],
        "allowed_commands": [
            {
                "command_type": "RequestAssay",
                "schema_id": "ars://core/command/RequestAssay",
                "schema_version": "1.0.0",
                "schema_sha256": "1" * 64,
            }
        ],
        "allowed_policy_actions": [],
        "subject_scope": {
            "project_id": project_id,
            "subject": {"kind": "task", "id": "tsk_01978abc-1000-7000-8000-000000001010"},
        },
        "risk_ceiling": "R1",
        "effective_at": "2026-08-14T00:00:00Z",
        "expires_at": "2026-08-15T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }


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

    registration = ObjectStore(tmp_path).read("assurance_record", first["registration_id"], 1)
    registration["semantic_intent"] = {}
    with pytest.raises(SchemaError):
        service.schemas.validate(REGISTRATION_SCHEMA_ID, registration)


def test_semantic_intent_has_its_own_schema_and_deterministic_command_identity(tmp_path: Path) -> None:
    intent = _intent()
    service = _service(tmp_path)

    intent_identity = service.schemas.validate(INTENT_SCHEMA_ID, intent.input_mapping(), schema_version="1.0.0")
    command_identity = service.schemas.resolve_identity(COMMAND_SCHEMA_ID, "1.0.0")
    result = service.register(intent)
    event = next(EventLedger(tmp_path, PROJECT, service.schemas).iter_events())

    assert intent_identity.schema_id == INTENT_SCHEMA_ID
    assert command_identity.schema_id == COMMAND_SCHEMA_ID
    assert intent_identity.sha256 != command_identity.sha256
    assert authority_actor_idempotency_key(intent.retry_key) == intent.retry_key
    assert result["receipt"]["command_id"] == authority_actor_command_id(OWNER, intent.retry_key)
    assert event["command_id"] == authority_actor_command_id(OWNER, intent.retry_key)
    assert event["idempotency_key"] == intent.retry_key
    assert authority_actor_command_id(OWNER, "other-retry") != event["command_id"]


def test_semantic_intent_schema_is_inert_but_format_checked(tmp_path: Path) -> None:
    schemas = _service(tmp_path).schemas
    identity = schemas.resolve_identity(INTENT_SCHEMA_ID, "1.0.0")
    assert not schemas.is_active(INTENT_SCHEMA_ID, "1.0.0")
    assert identity.parsed["$defs"]["utc"]["format"] == "date-time"

    invalid = _intent().input_mapping()
    invalid["effective_at"] = "2026-02-30T00:00:00Z"
    with pytest.raises(SchemaError, match="is not a 'date-time'"):
        schemas.validate(INTENT_SCHEMA_ID, invalid, schema_version="1.0.0")


def test_invalid_receipt_contract_fails_before_any_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    validate = service.schemas.validate

    def reject_receipt(schema_id: str, value: object, **kwargs: object) -> object:
        if schema_id == "ars://wp6-6/gate6/authority/receipt/AuthorityActorRegistration":
            raise SchemaError("injected invalid receipt contract")
        return validate(schema_id, value, **kwargs)

    monkeypatch.setattr(service.schemas, "validate", reject_receipt)
    with pytest.raises(SchemaError, match="invalid receipt contract"):
        service.register(_intent())

    assert not list((tmp_path / "runtime").glob(".authority-actor-registration-*.json"))
    assert not list((tmp_path / "objects" / "canonical_actor").rglob("*.json"))
    assert not list((tmp_path / "objects" / "assurance_record").rglob("*.json"))
    assert not list((tmp_path / "events").rglob("*.jsonl"))
    assert not list((tmp_path / "receipts").rglob("*.json"))


@pytest.mark.parametrize(
    "relative",
    (
        Path("objects/canonical_actor"),
        Path("objects/assurance_record"),
        Path("receipts/authority_actor"),
    ),
    ids=("actor-object", "registration-object", "receipt"),
)
def test_redirected_publication_surface_is_rejected_before_transaction(
    tmp_path: Path,
    relative: Path,
) -> None:
    service = _service(tmp_path)
    link = tmp_path / relative
    external = tmp_path / "external" / relative.name
    external.parent.mkdir(parents=True, exist_ok=True)
    if link.exists():
        link.rename(external)
    else:
        external.mkdir()
        link.parent.mkdir(parents=True, exist_ok=True)
    _redirect_directory(link, external)

    with pytest.raises(IntegrityError, match="redirected component"):
        service.register(_intent())

    assert not list((tmp_path / "runtime").glob(".authority-actor-registration-*.json"))
    assert not list((tmp_path / "events").rglob("*.jsonl"))
    assert not list((tmp_path / "receipts").rglob("*.json"))
    assert not list(external.rglob("*.json"))


def test_legacy_flat_command_identity_is_limited_to_exact_committed_retry(tmp_path: Path) -> None:
    service = _service(tmp_path)
    legacy_path = tmp_path / "legacy-intent.json"
    legacy_path.write_bytes(canonical_bytes({**_intent().input_mapping(), "schema_id": COMMAND_SCHEMA_ID}))
    legacy = read_actor_registration_intent(legacy_path)
    assert legacy.input_schema_id == COMMAND_SCHEMA_ID

    with pytest.raises(ConflictError, match="only for an exact committed retry"):
        service.register(legacy)
    assert not list((tmp_path / "events" / PROJECT).rglob("*.jsonl"))
    assert not list((tmp_path / "objects" / "canonical_actor").rglob("*.json"))

    first = service.register(_intent())
    duplicate = service.register(legacy)
    assert duplicate["status"] == "duplicate"
    assert duplicate["actor_id"] == first["actor_id"]
    assert duplicate["registration_sha256"] == first["registration_sha256"]

    service.clock = lambda: datetime(2028, 8, 14, tzinfo=UTC)
    expired_duplicate = service.register(legacy)
    assert expired_duplicate["status"] == "duplicate"
    assert expired_duplicate["registration_sha256"] == first["registration_sha256"]


def test_legacy_flat_command_identity_cannot_change_a_committed_retry(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.register(_intent())

    with pytest.raises(ConflictError, match="retry key conflicts"):
        service.register(replace(_intent(reason="changed"), input_schema_id=COMMAND_SCHEMA_ID))


def test_direct_actor_registration_ledger_continuation_is_rejected(tmp_path: Path) -> None:
    ledger = EventLedger(tmp_path, PROJECT, bundled_runtime_schema_registry())

    with pytest.raises(ArsError, match="validated registration continuation"):
        ledger._append_authority_actor_from_validated_service(
            {"payload": {}},
            snapshot=ledger.snapshot(),
        )


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


def test_started_registration_recovers_after_owner_window_expires(tmp_path: Path) -> None:
    service = _service(tmp_path)

    def crash(stage: str) -> None:
        if stage == "actor":
            raise RuntimeError("crash after actor")

    with pytest.raises(RuntimeError, match="crash after actor"):
        service.register(_intent(), phase_hook=crash)
    service.clock = lambda: datetime(2028, 8, 14, tzinfo=UTC)
    recovered = service.register(_intent())
    assert recovered["status"] == "accepted"
    assert not list((tmp_path / "runtime").glob(".authority-actor-registration-*.json"))


def test_redirected_recovery_marker_cannot_authorize_future_window_and_retry_recovers(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)

    def crash_after_actor(stage: str) -> None:
        if stage == "actor":
            raise RuntimeError("crash after actor")

    with pytest.raises(RuntimeError, match="crash after actor"):
        service.register(_intent(), phase_hook=crash_after_actor)
    assert not list((tmp_path / "events").rglob("*.jsonl"))
    assert not list((tmp_path / "objects" / "assurance_record").rglob("*.json"))

    runtime = tmp_path / "runtime"
    external_runtime = tmp_path / "external-runtime"
    runtime.rename(external_runtime)
    _redirect_directory(runtime, external_runtime)
    service.clock = lambda: datetime(2028, 8, 14, tzinfo=UTC)

    with pytest.raises(IntegrityError, match="redirected component"):
        service.register(_intent())
    assert not list((tmp_path / "events").rglob("*.jsonl"))
    assert not list((tmp_path / "objects" / "assurance_record").rglob("*.json"))
    assert not list((tmp_path / "receipts").rglob("*.json"))

    _remove_directory_redirect(runtime)
    external_runtime.rename(runtime)
    recovered = service.register(_intent())
    assert recovered["status"] == "accepted"
    assert not list(runtime.glob(".authority-actor-registration-*.json"))


@pytest.mark.parametrize(
    ("phase", "surface", "expected_events"),
    (
        ("registration", "receipt", 0),
        ("event", "actor", 1),
        ("receipt", "receipt", 1),
    ),
)
def test_redirect_introduced_at_publication_phase_is_detected_and_exact_retry_recovers(
    tmp_path: Path,
    phase: str,
    surface: str,
    expected_events: int,
) -> None:
    service = _service(tmp_path)
    redirected: dict[str, Path] = {}

    def redirect(stage: str) -> None:
        if stage != phase:
            return
        if surface == "actor":
            link = next((tmp_path / "objects" / "canonical_actor").iterdir())
        else:
            link = tmp_path / "receipts" / "authority_actor"
        target = tmp_path / f"external-{phase}-{surface}"
        target.parent.mkdir(parents=True, exist_ok=True)
        if link.exists():
            link.rename(target)
        else:
            target.mkdir()
            link.parent.mkdir(parents=True, exist_ok=True)
        _redirect_directory(link, target)
        redirected.update(link=link, target=target)

    with pytest.raises(IntegrityError, match="redirected component"):
        service.register(_intent(), phase_hook=redirect)
    assert len(list((tmp_path / "events").rglob("*.jsonl"))) == expected_events
    assert list((tmp_path / "runtime").glob(".authority-actor-registration-*.json"))

    _remove_directory_redirect(redirected["link"])
    redirected["target"].rename(redirected["link"])
    recovered = service.register(_intent())
    assert recovered["status"] in {"accepted", "duplicate"}
    assert len(list((tmp_path / "events").rglob("*.jsonl"))) == 1
    assert not list((tmp_path / "runtime").glob(".authority-actor-registration-*.json"))


def test_registered_actor_class_must_be_usable_by_its_selected_lane(tmp_path: Path) -> None:
    with pytest.raises(ArsError, match="class is not permitted"):
        _service(tmp_path).register(
            _intent(
                actor_class="service",
                actor_role="independent_reviewer",
                authority_lane="independent_reviewer/outcome_review",
            )
        )
    operator_service = _service(tmp_path)
    operator_service.route_commands |= {"ImportAcceptedW11CatalogueGenesis"}
    with pytest.raises(ArsError, match="class is not permitted"):
        operator_service.register(
            _intent(
                actor_class="agent",
                actor_role="operator",
                authority_lane="operator/genesis",
            )
        )
    assert not list((tmp_path / "events").rglob("*.jsonl"))


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
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True, exist_ok=True)
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
    assert _known_authority_actor_classes(tmp_path, objects, now=NOW) == {}
    result = service.register(_intent())
    assert _known_authority_actor_classes(
        tmp_path,
        objects,
        now=NOW,
        authority_projection=_authority_projection(tmp_path),
    )[result["actor_id"]] == frozenset({"agent"})


def test_empty_recovery_identity_directory_is_not_actor_evidence(tmp_path: Path) -> None:
    service = _service(tmp_path)
    empty_id = "arec_01978abc-1000-7000-8000-000000001005"
    (tmp_path / "objects" / "assurance_record" / empty_id).mkdir()

    assert (
        _known_authority_actor_classes(
            tmp_path,
            service.objects,
            now=NOW,
            authority_projection={"authority_grants": {}, "authority_actors": {}},
        )
        == {}
    )


def test_registration_objects_without_committed_event_do_not_prove_actor(tmp_path: Path) -> None:
    service = _service(tmp_path)

    def crash(stage: str) -> None:
        if stage == "registration":
            raise RuntimeError("crash before event")

    with pytest.raises(RuntimeError, match="before event"):
        service.register(_intent(), phase_hook=crash)
    objects = ObjectStore(tmp_path)

    assert (
        _known_authority_actor_classes(
            tmp_path,
            objects,
            now=NOW,
            authority_projection={"authority_grants": {}, "authority_actors": {}},
        )
        == {}
    )


def test_forged_actor_registration_pair_without_replay_event_does_not_prove_actor(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent())
    for path in (tmp_path / "events" / PROJECT).rglob("*.jsonl"):
        path.unlink()

    known = _known_authority_actor_classes(
        tmp_path,
        ObjectStore(tmp_path),
        now=NOW,
        authority_projection={"authority_grants": {}, "authority_actors": {}},
    )

    assert result["actor_id"] not in known


def test_actor_census_rejects_later_actor_revision_class_drift(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent())
    objects = ObjectStore(tmp_path)
    actor = objects.read("canonical_actor", result["actor_id"], 1)
    objects.write("canonical_actor", result["actor_id"], 2, {**actor, "actor_class": "service"})

    with pytest.raises(IntegrityError, match="revision is not exact"):
        _known_authority_actor_classes(
            tmp_path,
            objects,
            now=NOW,
            authority_projection=_authority_projection(tmp_path),
        )


def test_actor_census_rejects_redirected_later_actor_revision(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent())
    actor = ObjectStore(tmp_path).read("canonical_actor", result["actor_id"], 1)
    external = tmp_path / "redirected-actor.json"
    external.write_bytes(canonical_bytes({**actor, "actor_class": "service"}))
    revision_path = (
        tmp_path
        / "objects"
        / "canonical_actor"
        / result["actor_id"]
        / f"00000002-{sha256_hex(external.read_bytes())}.json"
    )
    try:
        os.symlink(external, revision_path)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("symlink creation is not permitted on this Windows runner")
        raise

    with pytest.raises(IntegrityError, match="revision is not exact"):
        _known_authority_actor_classes(
            tmp_path,
            ObjectStore(tmp_path),
            now=NOW,
            authority_projection=_authority_projection(tmp_path),
        )


def test_mixed_scoped_grant_families_and_registration_prove_actor_classes(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent(expires_at="2099-01-01T00:00:00Z"))
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True, exist_ok=True)
    objects = ObjectStore(tmp_path)
    normal_grant = _scoped_grant(
        "agr_01978abc-1000-7000-8000-000000001010",
        "act_01978abc-1000-7000-8000-000000001010",
    )
    external_grant = {
        **normal_grant,
        "schema_id": EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_ID,
        "schema_version": EXTERNAL_RECORD_SCOPED_GRANT_SCHEMA_VERSION,
        "authority_grant_id": "agr_01978abc-1000-7000-8000-000000001011",
        "actor_id": result["actor_id"],
        "allowed_actor_classes": ["human"],
        "allowed_commands": [],
        "allowed_policy_actions": [
            {
                "policy_action_type": "publish_external_assurance_record",
                "schema_id": "ars://core/policy-action/PublishExternalAssuranceRecord",
                "schema_version": "1.0.0",
                "schema_sha256": "2" * 64,
            }
        ],
        "subject_scope": {
            "project_id": PROJECT,
            "subject": {"kind": "external_assurance_record", "id": "agr_01978abc-1000-7000-8000-000000001011"},
        },
    }
    objects.write("authority_grant", normal_grant["authority_grant_id"], 1, normal_grant)
    objects.write("authority_grant", external_grant["authority_grant_id"], 1, external_grant)

    known = _known_authority_actor_classes(
        tmp_path,
        objects,
        now=NOW,
        authority_projection=_authority_projection(tmp_path, normal_grant, external_grant),
    )
    assert known[normal_grant["actor_id"]] == frozenset({"service"})
    assert known[result["actor_id"]] == frozenset({"agent"})


def test_actor_census_rejects_later_grant_revision_drift(tmp_path: Path) -> None:
    objects = ObjectStore(tmp_path)
    grant = _scoped_grant(
        "agr_01978abc-1000-7000-8000-000000001013",
        "act_01978abc-1000-7000-8000-000000001013",
    )
    objects.write("authority_grant", str(grant["authority_grant_id"]), 1, grant)
    objects.write(
        "authority_grant",
        str(grant["authority_grant_id"]),
        2,
        {**grant, "allowed_actor_classes": ["agent"]},
    )

    with pytest.raises(IntegrityError, match="revision is not exact"):
        _known_authority_actor_classes(
            tmp_path,
            objects,
            now=NOW,
            project_id=PROJECT,
            authority_projection=_authority_projection(tmp_path, grant),
        )


def test_foreign_project_grant_is_not_actor_evidence_even_when_projected(tmp_path: Path) -> None:
    objects = ObjectStore(tmp_path)
    (tmp_path / "objects" / "assurance_record").mkdir(parents=True)
    foreign = _scoped_grant(
        "agr_01978abc-1000-7000-8000-000000001014",
        "act_01978abc-1000-7000-8000-000000001014",
        project_id="prj_01978abc-1000-7000-8000-000000009999",
    )
    objects.write("authority_grant", str(foreign["authority_grant_id"]), 1, foreign)

    assert (
        _known_authority_actor_classes(
            tmp_path,
            objects,
            now=NOW,
            project_id=PROJECT,
            authority_projection=_authority_projection(tmp_path, foreign),
        )
        == {}
    )


def test_expired_registered_actor_is_not_revived_by_historical_grant(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent(expires_at="2026-08-15T00:00:00Z"))
    objects = ObjectStore(tmp_path)
    grant = {
        "schema_id": "ars://core/scoped-authority-grant",
        "schema_version": "2.1.0",
        "authority_grant_id": "agr_01978abc-1000-7000-8000-000000001012",
        "actor_id": result["actor_id"],
        "allowed_actor_classes": ["agent"],
        "allowed_commands": [
            {
                "command_type": "RequestAssay",
                "schema_id": "ars://core/command/RequestAssay",
                "schema_version": "1.0.0",
                "schema_sha256": "1" * 64,
            }
        ],
        "allowed_policy_actions": [],
        "subject_scope": {
            "project_id": PROJECT,
            "subject": {"kind": "task", "id": "tsk_01978abc-1000-7000-8000-000000001012"},
        },
        "risk_ceiling": "R1",
        "effective_at": "2026-08-14T00:00:00Z",
        "expires_at": "2099-01-01T00:00:00Z",
        "delegable": False,
        "revoked": False,
    }
    objects.write("authority_grant", grant["authority_grant_id"], 1, grant)

    assert result["actor_id"] not in _known_authority_actor_classes(
        tmp_path,
        objects,
        now=datetime(2026, 8, 16, tzinfo=UTC),
        authority_projection=_authority_projection(tmp_path, grant),
    )


def test_later_foreign_registration_revision_is_rejected_as_class_drift(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.register(_intent())
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True, exist_ok=True)
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
    with pytest.raises(IntegrityError, match="revision is not exact"):
        _known_authority_actor_classes(
            tmp_path,
            objects,
            project_id=PROJECT,
            store_identity=STORE,
            owner_actor_id=OWNER,
            now=NOW,
            authority_projection=_authority_projection(tmp_path),
        )


def test_cli_accepts_semantic_intent_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from research_system import cli

    source = tmp_path / "intent.json"
    source.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://wp6-6/gate6/authority/intent/RegisterAuthorityActor",
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
    (tmp_path / "objects" / "authority_grant").mkdir(parents=True, exist_ok=True)
    actor_path = next((tmp_path / "objects" / "canonical_actor" / result["actor_id"]).glob("*.json"))
    actor_path.write_bytes(actor_path.read_bytes().replace(b"Codex producer", b"Tampered producer"))
    with pytest.raises(IntegrityError):
        _known_authority_actor_classes(
            tmp_path,
            ObjectStore(tmp_path),
            now=NOW,
            authority_projection=_authority_projection(tmp_path),
        )


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
