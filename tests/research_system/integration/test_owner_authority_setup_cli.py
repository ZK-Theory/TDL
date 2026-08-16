from __future__ import annotations

import json
import os
import shutil
import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import research_system.cli as cli
from research_system import owner_authority as owner_module
from research_system.authority import GrantedCommandIdentity, SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES
from research_system.canonical import canonical_bytes
from research_system.errors import (
    ArsError,
    ConfigurationError,
    ConflictError,
    IdempotencyConflictError,
    IntegrityError,
    SchemaError,
)
from tests.research_system.factories import ACTORS, PROJECT_ID, activate_lifecycle_grant, control_plane
from research_system.authority_actor import RegisterAuthorityActor, _deterministic_id


REPO = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO / ".research-system/schemas"
NOW = datetime(2026, 8, 14, 12, tzinfo=UTC)
ROUTE_FILES = (
    Path(".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json"),
    Path(".research-system/schemas/contracts/wp6-6/spec-gate6-route.schema.json"),
    Path(".research-system/evals/expected/w11-portfolio-discovery-v1.json"),
)


def _json(path: Path, value: dict[str, Any]) -> Path:
    path.write_bytes(canonical_bytes(value))
    return path


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()


def _tree(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        (path.relative_to(root).as_posix(), path.read_bytes()) for path in sorted(root.rglob("*")) if path.is_file()
    )


def _route_repo(tmp_path: Path) -> Path:
    root = tmp_path / "route"
    for relative in ROUTE_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, target)
    _git(root.parent, "init", "--quiet", root.name)
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "route")
    return root


@pytest.fixture
def inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    harness = control_plane(tmp_path, auto_authority=False, clock=lambda: NOW)
    route_root = _route_repo(tmp_path)
    for relative in (Path("objects/assurance_record"), Path("objects/authority_grant")):
        (harness.authority_root / relative).mkdir(parents=True, exist_ok=True)
    activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id="obj_01978abc-3999-7000-8000-000000003999",
        actor_id=ACTORS["actor-b"],
        allowed_actor_classes=("agent",),
        command_types=("RequestAssay",),
    )
    binding_path = _json(tmp_path / "binding.json", {})
    binding = SimpleNamespace(
        code_roots=(route_root,),
        control_root=harness.authority_root,
        project_id=PROJECT_ID,
        schema_root=SCHEMA_ROOT,
        store_identity=harness.authority_resolver.expected_store_identity,
        origin_witness=harness.authority_resolver.approved_witness,
        origin_witness_path=harness.authority_resolver.approved_witness_path,
    )
    monkeypatch.setattr(owner_module.ControlBinding, "load", lambda _path: binding)
    monkeypatch.setattr(
        owner_module, "datetime", SimpleNamespace(now=lambda _tz: NOW, fromisoformat=datetime.fromisoformat)
    )
    config = _json(
        tmp_path / "setup.json",
        {"authority_binding": str(binding_path), "repository_root": str(route_root)},
    )
    intent_value = {
        "retry_key": "owner-intent-1",
        "target_actor_id": ACTORS["actor-b"],
        "target_actor_class": "agent",
        "authority_lane": "portfolio_steward/spec_01_assay",
        "actor_role": "Portfolio Steward",
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "scope_definition", "id": "obj_01978abc-3011-7000-8000-000000003011"},
        },
        "evidence_refs": ["spec-route:test"],
        "effective_at": "2026-08-14T10:00:00Z",
        "expires_at": "2026-08-15T10:00:00Z",
        "reason": "authorize the exact SPEC assay requester lane",
        "owner_action": "activate_authority_grant",
    }
    intent = _json(tmp_path / "intent.json", intent_value)
    return SimpleNamespace(
        harness=harness,
        route_root=route_root,
        config=config,
        intent=intent,
        intent_value=intent_value,
        tmp_path=tmp_path,
        initial_event_count=len(tuple(harness.authority_ledger.iter_events())),
    )


@pytest.mark.integration
def test_semantic_publish_then_guarded_activation(inputs, capsys):
    assert (
        cli.main(
            [
                "authority",
                "publish-owner-decision",
                "--setup-config",
                str(inputs.config),
                "--intent",
                str(inputs.intent),
            ]
        )
        == 0
    )
    publication = json.loads(capsys.readouterr().out)
    assert publication["status"] == "accepted"
    assert len(tuple(inputs.harness.authority_ledger.iter_events())) == inputs.initial_event_count + 1
    decision = inputs.harness.authority_objects.read("assurance_record", publication["administration_decision_id"], 1)
    assert decision["target_grant_id"] == publication["authority_grant_id"]
    projection = inputs.harness.authority_resolver._projection()
    assert projection["owner_authority_decision_publications"][decision["record_id"]]["consumed"] is False

    activation = _json(
        inputs.tmp_path / "activation.json",
        {
            "retry_key": "owner-activation-1",
            "publication_command_id": publication["command_id"],
            "reason": "activate the published exact grant",
            "evidence_refs": ["spec-route:test"],
        },
    )
    assert (
        cli.main(
            ["authority", "activate-scoped-grant", "--setup-config", str(inputs.config), "--input", str(activation)]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "accepted"
    grant = inputs.harness.authority_objects.read("authority_grant", publication["authority_grant_id"], 1)
    resolved = inputs.harness.authority_resolver.resolve_command(
        grant["authority_grant_id"],
        grant["actor_id"],
        "agent",
        GrantedCommandIdentity.from_dict(grant["allowed_commands"][0]),
        "R2",
        PROJECT_ID,
        grant["subject_scope"]["subject"]["kind"],
        grant["subject_scope"]["subject"]["id"],
        NOW,
    )
    assert resolved.authority_grant_id == grant["authority_grant_id"]
    assert (
        inputs.harness.authority_resolver._projection()["owner_authority_decision_publications"][decision["record_id"]][
            "consumed"
        ]
        is True
    )


@pytest.mark.integration
def test_exact_retry_and_changed_intent_conflict_without_mutation(inputs):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    first = setup.publish(inputs.intent_value)
    before = tuple(inputs.harness.authority_ledger.iter_events())
    assert setup.publish(inputs.intent_value) == first
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before
    changed = deepcopy(inputs.intent_value)
    changed["reason"] = "different semantic intent"
    with pytest.raises(IdempotencyConflictError):
        setup.publish(changed)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before


@pytest.mark.integration
def test_accepted_publication_retry_requires_exact_materialized_decision(inputs):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    published = setup.publish(inputs.intent_value)
    decision_root = (
        inputs.harness.authority_root / "objects" / "assurance_record" / published["administration_decision_id"]
    )
    decision_path = next(decision_root.glob("*.json"))
    decision_path.unlink()
    before = tuple(inputs.harness.authority_ledger.iter_events())

    with pytest.raises(IntegrityError, match="owner publication"):
        setup.publish(inputs.intent_value)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before


@pytest.mark.integration
@pytest.mark.parametrize(
    ("subject_kind", "subject_id", "expected_commands"),
    [
        ("scope_definition", "obj_01978abc-3011-7000-8000-000000003011", ("ObserveW11AuthorityFile",)),
        ("review", "rev_01978abc-3012-7000-8000-000000003012", ("RecordW11AuthorityReview",)),
    ],
)
def test_reviewer_lane_derives_exact_commands_for_subject_kind(inputs, subject_kind, subject_id, expected_commands):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    intent = deepcopy(inputs.intent_value)
    intent.update(
        {
            "retry_key": f"reviewer-{subject_kind}",
            "authority_lane": "independent_reviewer/authority_observation",
            "actor_role": "independent verifier",
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": subject_kind, "id": subject_id},
            },
        }
    )

    material = setup._derive_publication_material(intent)
    assert tuple(item["command_type"] for item in material["grant_value"]["allowed_commands"]) == expected_commands


@pytest.mark.integration
@pytest.mark.parametrize(
    ("lane", "role", "subject_kind", "expected_commands"),
    [
        ("producer/spec_brief_registration", "SPEC brief producer", "artefact", ("RegisterArtefact",)),
        (
            "independent_reviewer/spec_brief_review",
            "independent verifier",
            "artefact",
            ("RecordScientificReview",),
        ),
    ],
)
def test_spec_brief_lanes_derive_only_the_exact_subject_command(inputs, lane, role, subject_kind, expected_commands):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    intent = deepcopy(inputs.intent_value)
    intent.update(
        {
            "retry_key": f"brief-{lane}",
            "authority_lane": lane,
            "actor_role": role,
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": subject_kind, "id": "art_01978abc-3014-7000-8000-000000003014"},
            },
        }
    )

    material = setup._derive_publication_material(intent)
    assert tuple(item["command_type"] for item in material["grant_value"]["allowed_commands"]) == expected_commands
    assert material["grant_value"]["risk_ceiling"] == "R3"


@pytest.mark.integration
def test_spec_brief_owner_and_context_lanes_are_closed_server_policy():
    assert owner_module._LANE_COMMAND_POLICY["owner_decider/spec_brief_use"] == {"SetArtefactUseAuthority"}
    assert owner_module._LANE_ALLOWED_ACTOR_CLASSES["owner_decider/spec_brief_use"] == {"human"}
    assert owner_module._LANE_COMMAND_POLICY["operator/spec_01_context"] == {
        "RequestContextPacket",
        "BeginContextCompilation",
        "CompleteContextCompilation",
        "PrepareOwnerOperatedContextHandoff",
        "ValidateOwnerOperatedContextHandoff",
        "IssueOwnerOperatedContextHandoff",
        "RecordOwnerOperatedContextDelivery",
    }
    assert owner_module._LANE_ALLOWED_ACTOR_CLASSES["operator/spec_01_context"] == {"human", "service"}


@pytest.mark.integration
def test_spec_02_execution_lane_includes_terminal_operational_cleanup():
    assert {
        "CompleteAttempt",
        "ReleaseExecutionLease",
        "ReleaseResources",
    }.issubset(owner_module._LANE_COMMAND_POLICY["operator/spec_02_execution"])
    assert owner_module._SCOPED_COMMAND_SUBJECT_KINDS["CompleteAttempt"] == "attempt"
    assert owner_module._SCOPED_COMMAND_SUBJECT_KINDS["ReleaseExecutionLease"] == "lease"
    assert owner_module._SCOPED_COMMAND_SUBJECT_KINDS["ReleaseResources"] == "resource"
    assert {
        "CompleteAttempt",
        "ReleaseExecutionLease",
        "ReleaseResources",
    }.issubset(SCOPED_GRANT_ACTOR_CLASS_COMMAND_TYPES)


def test_legacy_generic_artefact_grant_is_not_reclassified_as_a_spec_role(inputs):
    owner_actor_id = inputs.harness.authority_resolver.administration_context().owner_actor_id
    legacy = activate_lifecycle_grant(
        inputs.harness,
        subject_kind="artefact",
        subject_id="art_01978abc-3011-7000-8000-000000003099",
        actor_id=owner_actor_id,
        allowed_actor_classes=("human",),
        command_types=("RegisterArtefact", "RecordScientificReview", "SetArtefactUseAuthority"),
    )
    assert legacy not in inputs.harness.authority_resolver.owner_published_grant_ids()
    request = {
        **inputs.intent_value,
        "retry_key": "owner-use-after-legacy-grant",
        "target_actor_id": owner_actor_id,
        "target_actor_class": "human",
        "authority_lane": "owner_decider/spec_brief_use",
        "actor_role": "Stephen",
        "subject_scope": {
            "project_id": PROJECT_ID,
            "subject": {"kind": "artefact", "id": "art_01978abc-3011-7000-8000-000000003100"},
        },
    }

    material = owner_module.load_owner_authority_setup(inputs.config)._derive_publication_material(request)

    assert material["grant"].allowed_commands[0].command_type == "SetArtefactUseAuthority"
    assert all(owner_module._LANE_RISK_POLICY[lane] == "R3" for lane in owner_module._SPEC_FLOW_SUPPORT_LANES)


@pytest.mark.integration
def test_reviewer_lane_rejects_unmatched_subject_and_role_without_mutation(inputs):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    before = tuple(inputs.harness.authority_ledger.iter_events())
    unmatched = deepcopy(inputs.intent_value)
    unmatched.update(
        {
            "authority_lane": "independent_reviewer/authority_observation",
            "actor_role": "independent verifier",
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": "decision", "id": "dec_01978abc-3013-7000-8000-000000003013"},
            },
        }
    )
    with pytest.raises(ArsError, match="no command for the subject kind"):
        setup._derive_publication_material(unmatched)

    wrong_role = deepcopy(unmatched)
    wrong_role["authority_lane"] = "independent_reviewer/authority_observation"
    wrong_role["actor_role"] = "Portfolio Steward"
    wrong_role["subject_scope"] = {
        "project_id": PROJECT_ID,
        "subject": {"kind": "scope_definition", "id": "obj_01978abc-3011-7000-8000-000000003011"},
    }
    with pytest.raises(ArsError, match="lane and actor role"):
        setup._derive_publication_material(wrong_role)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before


@pytest.mark.integration
def test_reviewer_lane_retry_is_idempotent(inputs):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    intent = deepcopy(inputs.intent_value)
    intent.update(
        {
            "retry_key": "reviewer-retry",
            "authority_lane": "independent_reviewer/authority_observation",
            "actor_role": "independent verifier",
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": "review", "id": "rev_01978abc-3012-7000-8000-000000003012"},
            },
        }
    )
    first = setup.publish(intent)
    before = tuple(inputs.harness.authority_ledger.iter_events())
    assert setup.publish(intent) == first
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before


@pytest.mark.integration
def test_owner_publication_requires_governed_actor_registration(inputs):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    registration = RegisterAuthorityActor(
        "Codex producer",
        "agent",
        "codex_desktop",
        "1.0",
        "owner-join-session",
        "SPEC-01 producer",
        "producer",
        "producer/spec_01_assay",
        "2026-08-14T10:00:00Z",
        "2026-08-15T10:00:00Z",
        ("spec-route:test",),
        "Register the observed live Codex producer session.",
        "register-codex-desktop-actor",
        "actor-join-retry",
    )
    target_actor_id = _deterministic_id(
        "authority-actor",
        "act",
        {"project_id": PROJECT_ID, "app_family": "codex_desktop", "session_identity": registration.session_identity},
    )
    intent = deepcopy(inputs.intent_value)
    intent["target_actor_id"] = target_actor_id
    with pytest.raises(ArsError, match="real configured authority actor"):
        setup.publish(intent)
    accepted = setup.register_actor(registration)
    assert accepted["actor_id"] == target_actor_id
    assert (
        inputs.harness.authority_resolver._projection()["authority_actors"][target_actor_id]["actor_sha256"]
        == accepted["actor_sha256"]
    )
    published = setup.publish(intent)
    assert published["status"] == "accepted"


@pytest.mark.integration
def test_owner_publication_evaluates_registered_actor_window_with_setup_clock(inputs, monkeypatch):
    class OutsideWindowDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 8, 16, 12, tzinfo=UTC)
            return value if tz is None else value.astimezone(tz)

    monkeypatch.setattr(
        owner_module,
        "datetime",
        OutsideWindowDateTime,
    )
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    registration = RegisterAuthorityActor(
        "Codex producer",
        "agent",
        "codex_desktop",
        "1.0",
        "clock-bound-owner-join-session",
        "SPEC-01 producer",
        "producer",
        "producer/spec_01_assay",
        "2026-08-14T10:00:00Z",
        "2026-08-15T10:00:00Z",
        ("spec-route:test",),
        "Register the observed live Codex producer session.",
        "register-codex-desktop-actor",
        "actor-clock-join-retry",
    )
    accepted = setup.register_actor(registration)
    intent = deepcopy(inputs.intent_value)
    intent["target_actor_id"] = accepted["actor_id"]

    assert setup.publish(intent)["status"] == "accepted"


@pytest.mark.integration
def test_owner_publication_rejects_registered_actor_role_lane_crossing_without_mutation(inputs):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    accepted = setup.register_actor(
        RegisterAuthorityActor(
            "Codex producer",
            "agent",
            "codex_desktop",
            "1.0",
            "producer-role-bound-session",
            "SPEC-01 producer",
            "producer",
            "producer/spec_01_assay",
            "2026-08-14T10:00:00Z",
            "2026-08-15T10:00:00Z",
            ("spec-route:test",),
            "Register the observed live Codex producer session.",
            "register-codex-desktop-actor",
            "actor-role-bound-retry",
        )
    )
    intent = deepcopy(inputs.intent_value)
    intent.update(
        {
            "target_actor_id": accepted["actor_id"],
            "authority_lane": "independent_reviewer/authority_observation",
            "actor_role": "independent verifier",
            "subject_scope": {
                "project_id": PROJECT_ID,
                "subject": {"kind": "review", "id": "rev_01978abc-3012-7000-8000-000000003012"},
            },
        }
    )
    before = tuple(inputs.harness.authority_ledger.iter_events())

    with pytest.raises(ArsError, match="governed session role"):
        setup.publish(intent)

    assert tuple(inputs.harness.authority_ledger.iter_events()) == before


@pytest.mark.integration
def test_publication_failure_before_event_rolls_back_and_retries(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    original_write = setup.objects.write

    def fail_before_object(*_args, **_kwargs):
        raise OSError("injected before publication")

    monkeypatch.setattr(setup.objects, "write", fail_before_object)
    before = tuple(inputs.harness.authority_ledger.iter_events())
    with pytest.raises(OSError, match="injected"):
        setup.publish(inputs.intent_value)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before
    assert not any((inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json"))
    monkeypatch.setattr(setup.objects, "write", original_write)
    assert setup.publish(inputs.intent_value)["status"] == "accepted"


@pytest.mark.integration
@pytest.mark.parametrize("boundary", ["marker", "event"])
def test_ordinary_failure_before_publication_commit_leaves_zero_durable_state(inputs, monkeypatch, boundary):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)

    def fail(*_args, **_kwargs):
        raise OSError(f"injected {boundary} failure")

    if boundary == "marker":
        monkeypatch.setattr(setup.service, "_write_owner_publication_marker", fail)
    else:
        monkeypatch.setattr(setup.service.ledger, "_append_scoped_authority_from_validated_submit", fail)
    before_events = tuple(inputs.harness.authority_ledger.iter_events())
    before_receipts = tuple(sorted((inputs.harness.authority_root / "receipts").rglob("*.json")))
    before_objects = tuple(sorted((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json")))
    with pytest.raises(OSError, match=f"injected {boundary} failure"):
        setup.publish(inputs.intent_value)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before_events
    assert tuple(sorted((inputs.harness.authority_root / "receipts").rglob("*.json"))) == before_receipts
    assert tuple(sorted((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json"))) == before_objects


@pytest.mark.integration
def test_value_error_before_publication_commit_rolls_back_new_decision_object(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)

    def fail(*_args, **_kwargs):
        raise ValueError("injected semantic append failure")

    monkeypatch.setattr(setup.service.ledger, "_append_scoped_authority_from_validated_submit", fail)
    before_events = tuple(inputs.harness.authority_ledger.iter_events())
    before_objects = tuple(sorted((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json")))

    with pytest.raises(ValueError, match="semantic append failure"):
        setup.publish(inputs.intent_value)

    assert tuple(inputs.harness.authority_ledger.iter_events()) == before_events
    assert tuple(sorted((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json"))) == before_objects
    assert not tuple((inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json"))


@pytest.mark.integration
def test_ordinary_receipt_failure_recovers_committed_publication(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    before_objects = tuple(sorted((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json")))

    def fail_receipt(*_args, **_kwargs):
        raise OSError("injected receipt failure")

    monkeypatch.setattr(setup.service.receipts, "write_scoped", fail_receipt)
    with pytest.raises(OSError, match="injected receipt failure"):
        setup.publish(inputs.intent_value)
    publications = [
        event
        for event in inputs.harness.authority_ledger.iter_events()
        if event["event_type"] == "OwnerAuthorityAdministrationDecisionPublished"
    ]
    assert len(publications) == 1
    assert (
        len(tuple((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json")))
        == len(before_objects) + 1
    )
    assert (
        len(tuple((inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json"))) == 1
    )

    recovered = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW).publish(inputs.intent_value)
    assert recovered["status"] == "accepted"
    assert recovered["event_batch_id"] == publications[0]["transaction_id"]
    assert not tuple((inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json"))


@pytest.mark.integration
def test_event_committed_before_receipt_recovers_exact_result(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    original_write_scoped = setup.service.receipts.write_scoped
    calls = 0

    def fail_after_event(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise KeyboardInterrupt("injected hard stop after event")
        return original_write_scoped(*args, **kwargs)

    monkeypatch.setattr(setup.service.receipts, "write_scoped", fail_after_event)
    with pytest.raises(KeyboardInterrupt, match="injected hard stop after event"):
        setup.publish(inputs.intent_value)
    publications = [
        event
        for event in inputs.harness.authority_ledger.iter_events()
        if event["event_type"] == "OwnerAuthorityAdministrationDecisionPublished"
    ]
    assert len(publications) == 1
    recovered = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW).publish(inputs.intent_value)
    assert recovered["status"] == "accepted"
    assert recovered["event_batch_id"] == publications[0]["transaction_id"]
    assert (
        len(
            [
                event
                for event in inputs.harness.authority_ledger.iter_events()
                if event["event_type"] == "OwnerAuthorityAdministrationDecisionPublished"
            ]
        )
        == 1
    )


@pytest.mark.integration
def test_object_only_hard_stop_reconciles_on_fresh_setup_and_retry(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)

    def stop_after_object(*_args, **_kwargs):
        raise KeyboardInterrupt("injected hard stop before event")

    monkeypatch.setattr(setup.service.ledger, "_append_scoped_authority_from_validated_submit", stop_after_object)
    before_events = tuple(inputs.harness.authority_ledger.iter_events())
    with pytest.raises(KeyboardInterrupt, match="injected hard stop before event"):
        setup.publish(inputs.intent_value)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before_events
    marker_paths = tuple(
        (inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json")
    )
    assert len(marker_paths) == 1
    marker = json.loads(marker_paths[0].read_bytes())
    assert (
        inputs.harness.authority_objects.read("assurance_record", marker["target_stream_id"], 1) == marker["decision"]
    )

    before_alternate_retry = _tree(inputs.harness.authority_root)
    alternate_retry = {**inputs.intent_value, "retry_key": "owner-intent-2"}
    with pytest.raises(ConflictError, match="different recovery command"):
        owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW).publish(alternate_retry)
    assert _tree(inputs.harness.authority_root) == before_alternate_retry

    recovered = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW).publish(inputs.intent_value)
    assert recovered["status"] == "accepted"
    publications = [
        event
        for event in inputs.harness.authority_ledger.iter_events()
        if event["event_type"] == "OwnerAuthorityAdministrationDecisionPublished"
    ]
    assert len(publications) == 1
    assert recovered["event_batch_id"] == publications[0]["transaction_id"]
    assert not tuple((inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json"))

    changed_retry = {**inputs.intent_value, "retry_key": "owner-intent-2"}
    second = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW).publish(changed_retry)
    assert second["status"] == "conflict"
    assert (
        len(
            [
                event
                for event in inputs.harness.authority_ledger.iter_events()
                if event["event_type"] == "OwnerAuthorityAdministrationDecisionPublished"
            ]
        )
        == 1
    )


@pytest.mark.integration
@pytest.mark.parametrize("tamper", ["marker", "object"])
def test_object_only_restart_tampering_fails_closed(inputs, monkeypatch, tamper):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)

    def stop_after_object(*_args, **_kwargs):
        raise KeyboardInterrupt("injected hard stop before event")

    monkeypatch.setattr(setup.service.ledger, "_append_scoped_authority_from_validated_submit", stop_after_object)
    with pytest.raises(KeyboardInterrupt):
        setup.publish(inputs.intent_value)
    marker_path = next((inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json"))
    marker = json.loads(marker_path.read_bytes())
    if tamper == "marker":
        marker["command_payload_hash"] = "0" * 64
        marker_path.write_bytes(canonical_bytes(marker))
    else:
        object_path = next(
            (inputs.harness.authority_root / "objects/assurance_record" / marker["target_stream_id"]).glob(
                "00000001-*.json"
            )
        )
        changed = deepcopy(marker["decision"])
        changed["state"] = "tampered"
        object_path.write_bytes(canonical_bytes(changed))
    fresh = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    before = _tree(inputs.harness.authority_root)
    with pytest.raises((ArsError, ConfigurationError), match="owner publication recovery"):
        fresh.publish(inputs.intent_value)
    assert _tree(inputs.harness.authority_root) == before


@pytest.mark.integration
def test_redirected_recovery_marker_fails_closed_without_mutation(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)

    def stop_after_object(*_args, **_kwargs):
        raise KeyboardInterrupt("injected hard stop before event")

    monkeypatch.setattr(setup.service.ledger, "_append_scoped_authority_from_validated_submit", stop_after_object)
    with pytest.raises(KeyboardInterrupt):
        setup.publish(inputs.intent_value)
    marker_path = next((inputs.harness.authority_root / "runtime/owner-authority-publication-recovery").glob("*.json"))
    marker_bytes = marker_path.read_bytes()
    external = inputs.tmp_path / "external-marker.json"
    external.write_bytes(marker_bytes)
    marker_path.unlink()
    try:
        os.symlink(external, marker_path)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")

    before_events = tuple(inputs.harness.authority_ledger.iter_events())
    before_object = tuple(sorted((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json")))
    with pytest.raises(IntegrityError, match="reparse component"):
        owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW).publish(inputs.intent_value)
    assert marker_path.is_symlink()
    assert external.read_bytes() == marker_bytes
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before_events
    assert tuple(sorted((inputs.harness.authority_root / "objects/assurance_record").rglob("*.json"))) == before_object


@pytest.mark.integration
def test_actor_census_rejects_redirected_grant_child_without_publication(inputs):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    grant_root = inputs.harness.authority_root / "objects" / "authority_grant"
    candidate = next(path for path in grant_root.iterdir() if path.is_dir())
    external = inputs.tmp_path / "external-grant"
    shutil.copytree(candidate, external)
    shutil.rmtree(candidate)
    try:
        candidate.symlink_to(external, target_is_directory=True)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("symlink creation is not permitted on this Windows runner")
        raise
    before = len(tuple(inputs.harness.authority_ledger.iter_events()))
    external_before = _tree(external)

    with pytest.raises(ConfigurationError, match="configured authority grant object"):
        setup.publish(inputs.intent_value)

    assert len(tuple(inputs.harness.authority_ledger.iter_events())) == before
    assert _tree(external) == external_before


@pytest.mark.integration
@pytest.mark.parametrize(
    "field,value",
    [
        ("target_actor_id", ACTORS["actor-a"]),
        ("authority_lane", "producer/spec_01_assay"),
        ("actor_role", "Assay producer"),
        ("target_actor_class", "service"),
        ("owner_action", "revoke_issued_authority_grant"),
        ("expires_at", "2026-08-14T11:00:00Z"),
    ],
)
def test_semantic_attacks_reject_zero_mutation(inputs, field, value):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    attack = deepcopy(inputs.intent_value)
    attack[field] = value
    before = tuple(inputs.harness.authority_ledger.iter_events())
    decision_root = inputs.harness.authority_root / "objects/assurance_record"
    before_objects = tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*")))
    with pytest.raises((ArsError, ConfigurationError, ValueError)):
        setup.publish(attack)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before
    assert tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*"))) == before_objects


@pytest.mark.integration
def test_direct_command_service_accepts_only_semantic_intent_and_generic_service_rejects(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    captured: dict[str, Any] = {}

    class Captured(BaseException):
        pass

    original_submit = setup.service.submit

    def capture(envelope):
        captured.update(deepcopy(envelope))
        raise Captured

    monkeypatch.setattr(setup.service, "submit", capture)
    with pytest.raises(Captured):
        setup.publish(inputs.intent_value)
    monkeypatch.setattr(setup.service, "submit", original_submit)

    assert set(captured["payload"]) == {"intent"}
    assert set(captured["payload"]["intent"]) == set(inputs.intent_value) - {"retry_key"}
    assert not ({"decision", "proposed_grant", "root_grant_sha256"} & set(captured["payload"]))

    before_events = tuple(inputs.harness.authority_ledger.iter_events())
    decision_root = inputs.harness.authority_root / "objects/assurance_record"
    before_objects = tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*")))
    with pytest.raises(ArsError, match="semantic authority setup"):
        inputs.harness.authority_service.submit(captured)
    assert tuple(inputs.harness.authority_ledger.iter_events()) == before_events
    assert tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*"))) == before_objects

    receipt = setup.service.submit(captured)
    assert receipt.status == "accepted"
    event = next(
        event
        for event in inputs.harness.authority_ledger.iter_events()
        if event["event_type"] == "OwnerAuthorityAdministrationDecisionPublished"
    )
    assert event["payload"]["decision"]["record_id"] == captured["target_stream_id"]


@pytest.mark.integration
def test_direct_command_service_rederives_material_and_rejects_caller_forgery(inputs, monkeypatch):
    setup = owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    captured: dict[str, Any] = {}

    class Captured(BaseException):
        pass

    original_submit = setup.service.submit

    def capture(envelope):
        captured.update(deepcopy(envelope))
        raise Captured

    monkeypatch.setattr(setup.service, "submit", capture)
    with pytest.raises(Captured):
        setup.publish(inputs.intent_value)
    monkeypatch.setattr(setup.service, "submit", original_submit)

    before_events = tuple(inputs.harness.authority_ledger.iter_events())
    decision_root = inputs.harness.authority_root / "objects/assurance_record"
    before_objects = tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*")))

    injected = deepcopy(captured)
    injected["payload"]["proposed_grant"] = {"actor_id": ACTORS["actor-a"]}
    with pytest.raises(SchemaError):
        setup.service.submit(injected)

    forged = deepcopy(captured)
    forged_intent = forged["payload"]["intent"]
    forged_intent["target_actor_id"] = ACTORS["actor-a"]
    forged_intent["target_actor_class"] = "human"
    forged["target_stream_id"] = owner_module._deterministic_id(
        "owner-authority-decision",
        "arec",
        forged_intent,
    )
    with pytest.raises(ArsError, match="non-owner SPEC route lanes"):
        setup.service.submit(forged)

    assert tuple(inputs.harness.authority_ledger.iter_events()) == before_events
    assert tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*"))) == before_objects


@pytest.mark.integration
def test_raw_submit_is_sealed(monkeypatch, tmp_path):
    command = _json(tmp_path / "raw.json", {"command_type": "PublishOwnerAuthorityAdministrationDecision"})
    config = _json(tmp_path / "config.json", {})
    monkeypatch.setattr(cli.ControlBinding, "load", lambda _path: SimpleNamespace())
    with pytest.raises(ConfigurationError, match="sealed"):
        cli.main(["command", "submit", "--config", str(config), "--command", str(command)])


@pytest.mark.integration
def test_dirty_route_rejects_before_mutation(inputs):
    decision_root = inputs.harness.authority_root / "objects/assurance_record"
    before_objects = tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*")))
    (inputs.route_root / "dirty.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not clean"):
        owner_module.load_owner_authority_setup(inputs.config, clock=lambda: NOW)
    assert tuple(sorted(path.relative_to(decision_root) for path in decision_root.rglob("*"))) == before_objects
