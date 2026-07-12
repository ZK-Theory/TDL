from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

from research_system.canonical import jsonable
from research_system.cli import main
from research_system.errors import ArsError, ConfigurationError, SchemaError
from research_system.evals.retention import (
    RULES,
    CanonicalPayloadScan,
    EvidenceStoreRegistry,
    LocationInspection,
    require_retention_rule,
    validate_deletion_manifest_for_event,
    validate_fixture_retention,
    verify_deletion,
)
from research_system.evals.retention_authorizer import (
    build_deletion_manifest_authorizer,
    load_evidence_store_registry,
)
from research_system.projection.replay import apply_event
from research_system.schema_registry import SchemaRegistry
from research_system.projection.replay import replay as replay_projection
from tests.research_system.factories import (
    ACTORS,
    AUTHORITY_GRANT_ID,
    control_plane,
)


def test_validate_fixture_retention_accepts_r0_synthetic_package():
    validate_fixture_retention("R0", "R0:synthetic_fixture_package")


def test_validate_fixture_retention_rejects_unknown_r0_rule():
    with pytest.raises(ValueError, match="unknown_r0_retention_rule"):
        validate_fixture_retention("R0", "R0:minimized_sensitive_excerpt")


def test_validate_fixture_retention_validates_r1_r2_rules():
    validate_fixture_retention("R2", "R2:minimized_sensitive_excerpt")
    with pytest.raises(ValueError, match="retention_rule_missing"):
        validate_fixture_retention("R1", "R1:no_such_rule")


def test_validate_fixture_retention_rejects_class_mismatch_and_r3():
    with pytest.raises(ValueError, match="retention_rule_id_class_mismatch"):
        validate_fixture_retention("R2", "R1:operational_measurement")
    with pytest.raises(ValueError, match="R3_prohibited"):
        validate_fixture_retention("R3", "R3:anything")


POLICY = Path(".research-system/evals/retention-policy.yaml")


def _registry(tmp_path):
    return EvidenceStoreRegistry(
        store_id="evidence-store-1",
        registry_hash="a" * 64,
        policy_revision="p0-retention-v1",
        primary_root=tmp_path / "primary",
        runtime_root=tmp_path / "runtime",
        staging_root=tmp_path / "staging",
        temp_root=tmp_path / "temp",
        replicas=(tmp_path / "replica",),
        permitted_consumers=("eval",),
        retention_policy_ids=("R2:minimized_sensitive_excerpt",),
        verifier_authority_bindings=(("actor-1", "grant-1"),),
        unregistered_replicas_prohibited=True,
    )


def _inspection(path, evidence_hash, *, absent=True, inaccessible=False):
    return LocationInspection(
        resolved_path=str(path.resolve()),
        absent=absent,
        evidence_hash=evidence_hash,
        inspection_hash="b" * 64,
        inaccessible=inaccessible,
        reparse_target=None,
    )


def _verify(tmp_path, **changes):
    registry = _registry(tmp_path)
    values = {
        "evidence_id": "evidence-1",
        "evidence_hash": "c" * 64,
        "retention_rule_id": "R2:minimized_sensitive_excerpt",
        "registry": registry,
        "inspect_location": lambda path, digest: _inspection(path, digest),
        "discover_replicas": lambda _: set(registry.replicas),
        "canonical_payload_scan": lambda digest: CanonicalPayloadScan(
            payload_present=False,
            scan_hash="d" * 64,
        ),
        "actor_id": "actor-1",
        "authority_grant_id": "grant-1",
        "verified_at": "2026-07-03T12:00:00Z",
    }
    values.update(changes)
    return verify_deletion(**values)


def test_registry_schema_requires_exact_actor_grant_bindings(tmp_path):
    registry = SchemaRegistry(Path(".research-system/schemas"))
    payload = {
        "schema_id": "ars://evals/evidence-store-registry",
        "schema_version": "1.0.0",
        "store_id": "evidence-store-1",
        "registry_hash": "a" * 64,
        "policy_revision": "p0-retention-v1",
        "primary_root": str(tmp_path / "primary"),
        "runtime_root": str(tmp_path / "runtime"),
        "staging_root": str(tmp_path / "staging"),
        "temp_root": str(tmp_path / "temp"),
        "replicas": [str(tmp_path / "replica")],
        "backup_roots": [str(tmp_path / "backup")],
        "restore_roots": [str(tmp_path / "restore")],
        "permitted_consumers": ["eval"],
        "retention_policy_ids": ["R2:minimized_sensitive_excerpt"],
        "verifier_authority_bindings": [["actor-1", "grant-1"]],
        "unregistered_replicas_prohibited": True,
    }
    registry.validate("ars://evals/evidence-store-registry", payload)

    payload["verifier_authority_bindings"] = [["actor-1", "grant-1", "extra"]]
    with pytest.raises(SchemaError, match="verifier_authority_bindings"):
        registry.validate("ars://evals/evidence-store-registry", payload)

    payload.pop("verifier_authority_bindings")
    payload["verifier_actor_ids"] = ["actor-1"]
    payload["verifier_authority_grant_ids"] = ["grant-1"]
    with pytest.raises(SchemaError, match="verifier_authority_bindings"):
        registry.validate("ars://evals/evidence-store-registry", payload)


def test_r1_r2_windows_are_exact_and_r2_uses_earlier_expiry():
    assert RULES[("R1", "redacted_command_summary")].max_days == 180
    assert RULES[("R1", "operational_measurement")].max_days == 365
    assert RULES[("R1", "grader_explanation")].max_days == 365
    assert RULES[("R2", "restricted_local_reference")].max_days == 90
    assert RULES[("R2", "minimized_sensitive_excerpt")].max_days == 30
    assert all(
        rule.use_earlier_source_expiry
        for key, rule in RULES.items()
        if key[0] == "R2"
    )


def test_verifier_derives_every_location_from_authorized_registry(tmp_path):
    registry = _registry(tmp_path)
    inspected = []

    def inspect(path, evidence_hash):
        inspected.append(path)
        return _inspection(path, evidence_hash)

    result = _verify(tmp_path, registry=registry, inspect_location=inspect)
    assert set(inspected) == set(registry.checked_locations())
    assert result.status == "verified"


def test_failed_inaccessible_or_reparse_location_stays_pending(tmp_path):
    registry = _registry(tmp_path)

    def inspect(path, evidence_hash):
        if path.name == "replica":
            return _inspection(path, evidence_hash, absent=False)
        if path.name == "staging":
            return _inspection(path, evidence_hash, inaccessible=True)
        result = _inspection(path, evidence_hash)
        if path.name == "runtime":
            return LocationInspection(
                **(
                    asdict(result)
                    | {"reparse_target": str(tmp_path / "escape")}
                )
            )
        return result

    result = _verify(tmp_path, registry=registry, inspect_location=inspect)
    assert result.status == "deletion_pending"
    assert str((tmp_path / "staging").resolve()) in result.inaccessible_locations
    assert result.reparse_locations


def test_unregistered_replica_or_canonical_payload_blocks(tmp_path):
    registry = _registry(tmp_path)
    extra = tmp_path / "unregistered-replica"
    unregistered = _verify(
        tmp_path,
        registry=registry,
        discover_replicas=lambda _: {*registry.replicas, extra},
    )
    assert unregistered.status == "deletion_pending"
    assert str(extra.resolve()) in unregistered.unregistered_replicas

    contaminated = _verify(
        tmp_path,
        registry=registry,
        canonical_payload_scan=lambda digest: CanonicalPayloadScan(
            payload_present=True,
            scan_hash="e" * 64,
        ),
    )
    assert contaminated.status == "deletion_pending"
    assert contaminated.canonical_payload_present is True


def test_boolean_absence_assertions_are_not_verification_evidence(tmp_path):
    with pytest.raises(TypeError, match="LocationInspection"):
        _verify(tmp_path, inspect_location=lambda path, digest: True)


def test_missing_or_wrong_authority_stays_pending(tmp_path):
    result = _verify(tmp_path, actor_id="producer-actor")
    assert result.status == "deletion_pending"
    assert result.authority_current is False


def test_cross_paired_actor_and_grant_stays_pending(tmp_path):
    registry = EvidenceStoreRegistry(
        **(
            asdict(_registry(tmp_path))
            | {
                "verifier_authority_bindings": (
                    ("actor-1", "grant-1"),
                    ("actor-2", "grant-2"),
                ),
            }
        )
    )
    result = _verify(
        tmp_path,
        registry=registry,
        actor_id="actor-1",
        authority_grant_id="grant-2",
    )
    assert result.status == "deletion_pending"
    assert result.authority_current is False


def test_missing_rule_and_r3_are_prohibited():
    with pytest.raises(ValueError, match="retention_rule_missing"):
        require_retention_rule("R2", "full_transcript")
    with pytest.raises(ValueError, match="R3_prohibited"):
        require_retention_rule("R3", "secret")


def test_only_complete_current_verified_manifest_authorizes_event(tmp_path):
    verified = _verify(tmp_path)
    payload = validate_deletion_manifest_for_event(
        verified,
        registry=_registry(tmp_path),
        current_policy_revision="p0-retention-v1",
        actor_id="actor-1",
        authority_grant_id="grant-1",
    )
    assert payload["status"] == "verified"

    pending = _verify(tmp_path, actor_id="producer-actor")
    with pytest.raises(ValueError, match="deletion_pending"):
        validate_deletion_manifest_for_event(
            pending,
            registry=_registry(tmp_path),
            current_policy_revision="p0-retention-v1",
            actor_id="producer-actor",
            authority_grant_id="grant-1",
        )


def test_event_authorization_rechecks_actor_grant_binding(tmp_path):
    verified = _verify(tmp_path)
    rebound_registry = EvidenceStoreRegistry(
        **(
            asdict(_registry(tmp_path))
            | {
                "verifier_authority_bindings": (("actor-2", "grant-2"),),
            }
        )
    )
    with pytest.raises(ValueError, match="authority mismatch"):
        validate_deletion_manifest_for_event(
            verified,
            registry=rebound_registry,
            current_policy_revision="p0-retention-v1",
            actor_id="actor-1",
            authority_grant_id="grant-1",
        )


def test_replay_marks_verified_evidence_expired_deleted(tmp_path):
    manifest = _verify(tmp_path)
    event = {
        "event_type": "EvidenceDeletionVerified",
        "stream_id": "evidence-store-1",
        "stream_version": 1,
        "payload": validate_deletion_manifest_for_event(
            manifest,
            registry=_registry(tmp_path),
            current_policy_revision="p0-retention-v1",
            actor_id="actor-1",
            authority_grant_id="grant-1",
        ),
    }
    initial = {"streams": {}, "last_position": 0, "last_hash": "0" * 64}
    updated = apply_event(initial, event)
    assert updated["streams"]["evidence-store-1"]["status"] == "expired_deleted"
    assert initial["streams"] == {}


def _deletion_command(manifest_hash):
    return {
        "command_id": "cmd_01978abc-9001-7000-8000-000000009001",
        "command_type": "VerifyEvidenceDeletion",
        "schema_id": "ars://core/command",
        "schema_version": "1.0.0",
        "submitted_at": "2026-07-03T12:00:00Z",
        "actor_id": ACTORS["actor-a"],
        "on_behalf_of_actor_id": None,
        "authority_grant_id": AUTHORITY_GRANT_ID,
        "target_stream_id": "dec_01978abc-9002-7000-8000-000000009002",
        "expected_stream_version": 0,
        "idempotency_key": "verify-deletion-1",
        "correlation_id": "retention-test",
        "causation_id": None,
        "reason": "record evidence-derived deletion verification",
        "evidence_refs": [manifest_hash],
        "payload": {"manifest_hash": manifest_hash},
    }


def test_command_service_requires_trusted_manifest_authorizer(tmp_path):
    manifest = _verify(
        tmp_path,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=AUTHORITY_GRANT_ID,
        registry=EvidenceStoreRegistry(
            **(
                asdict(_registry(tmp_path))
                | {
                    "verifier_authority_bindings": (
                        (ACTORS["actor-a"], AUTHORITY_GRANT_ID),
                    ),
                }
            )
        ),
    )
    registry = EvidenceStoreRegistry(
        **(
            asdict(_registry(tmp_path))
            | {
                "verifier_authority_bindings": (
                    (ACTORS["actor-a"], AUTHORITY_GRANT_ID),
                ),
            }
        )
    )
    command_root = tmp_path / "command"
    command_root.mkdir()
    harness = control_plane(command_root)
    command = _deletion_command(manifest.manifest_hash)
    with pytest.raises(ArsError, match="trusted deletion manifest authorizer"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()

    def authorize(reference, actor_id, authority_grant_id):
        assert reference == {"manifest_hash": manifest.manifest_hash}
        return validate_deletion_manifest_for_event(
            manifest,
            registry=registry,
            current_policy_revision="p0-retention-v1",
            actor_id=actor_id,
            authority_grant_id=authority_grant_id,
        )

    harness.service.deletion_manifest_authorizer = authorize
    assert harness.service.submit(command).status == "accepted"
    state = replay_projection(harness.ledger.iter_events())
    assert state["streams"]["evidence-store-1"]["status"] == "expired_deleted"


def _bound_registry(tmp_path):
    """Registry accepting ACTORS['actor-a']/AUTHORITY_GRANT_ID as the verifier."""
    return EvidenceStoreRegistry(
        **(
            asdict(_registry(tmp_path))
            | {
                "verifier_authority_bindings": (
                    (ACTORS["actor-a"], AUTHORITY_GRANT_ID),
                ),
            }
        )
    )


def test_authorizer_refuses_mismatched_registry_hash_or_policy_revision(tmp_path):
    manifest = _verify(tmp_path)
    payload = jsonable(asdict(manifest))

    wrong_hash_registry = EvidenceStoreRegistry(
        **(asdict(_registry(tmp_path)) | {"registry_hash": "f" * 64})
    )
    authorize_wrong_hash = build_deletion_manifest_authorizer(
        wrong_hash_registry, retention_policy_path=POLICY
    )
    with pytest.raises(ValueError, match="stale deletion registry"):
        authorize_wrong_hash(payload, "actor-1", "grant-1")

    stale_registry = EvidenceStoreRegistry(
        **(asdict(_registry(tmp_path)) | {"policy_revision": "p0-retention-v0"})
    )
    stale_manifest = _verify(tmp_path, registry=stale_registry)
    authorize_stale_policy = build_deletion_manifest_authorizer(
        stale_registry, retention_policy_path=POLICY
    )
    with pytest.raises(ValueError, match="stale deletion registry"):
        authorize_stale_policy(jsonable(asdict(stale_manifest)), "actor-1", "grant-1")


def test_authorizer_requires_valid_canonical_retention_policy(tmp_path):
    missing = tmp_path / "missing-retention-policy.yaml"
    with pytest.raises(ConfigurationError, match="invalid retention policy"):
        build_deletion_manifest_authorizer(_registry(tmp_path), retention_policy_path=missing)

    malformed = tmp_path / "retention-policy.yaml"
    malformed.write_text("policy_revision: p0-retention-v0\nrules: []\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid retention policy revision"):
        build_deletion_manifest_authorizer(_registry(tmp_path), retention_policy_path=malformed)


def test_production_authorizer_rejects_stale_self_validating_manifest(tmp_path):
    stale_registry = EvidenceStoreRegistry(
        **(asdict(_bound_registry(tmp_path)) | {"policy_revision": "p0-retention-v0"})
    )
    manifest = _verify(
        tmp_path,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=AUTHORITY_GRANT_ID,
        registry=stale_registry,
    )
    assert manifest.policy_revision == "p0-retention-v0"

    command_root = tmp_path / "command"
    command_root.mkdir()
    harness = control_plane(command_root)
    harness.service.deletion_manifest_authorizer = build_deletion_manifest_authorizer(
        stale_registry, retention_policy_path=POLICY
    )
    command = {
        **_deletion_command(manifest.manifest_hash),
        "payload": jsonable(asdict(manifest)),
    }

    with pytest.raises(ValueError, match="stale deletion registry or policy"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()
    assert harness.receipts.load(command["command_id"]) is None

def test_production_authorizer_accepts_complete_current_manifest(tmp_path):
    registry = _bound_registry(tmp_path)
    manifest = _verify(
        tmp_path,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=AUTHORITY_GRANT_ID,
        registry=registry,
    )
    assert manifest.status == "verified"

    command_root = tmp_path / "command"
    command_root.mkdir()
    harness = control_plane(command_root)
    harness.service.deletion_manifest_authorizer = build_deletion_manifest_authorizer(
        registry, retention_policy_path=POLICY
    )
    command = {
        **_deletion_command(manifest.manifest_hash),
        "payload": jsonable(asdict(manifest)),
    }
    expected_payload = validate_deletion_manifest_for_event(
        manifest,
        registry=registry,
        current_policy_revision="p0-retention-v1",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=AUTHORITY_GRANT_ID,
    )

    receipt = harness.service.submit(command)
    assert receipt.status == "accepted"
    events = list(harness.ledger.iter_events())
    verified_events = [
        event for event in events if event["event_type"] == "EvidenceDeletionVerified"
    ]
    assert len(verified_events) == 1
    assert verified_events[0]["payload"] == expected_payload
    state = replay_projection(harness.ledger.iter_events())
    assert state["streams"]["evidence-store-1"]["status"] == "expired_deleted"


def test_production_authorizer_rejects_tampered_manifest_payload(tmp_path):
    registry = _bound_registry(tmp_path)
    manifest = _verify(
        tmp_path,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=AUTHORITY_GRANT_ID,
        registry=registry,
    )
    tampered_payload = jsonable(asdict(manifest))
    tampered_payload["evidence_id"] = "evidence-tampered"

    command_root = tmp_path / "command"
    command_root.mkdir()
    harness = control_plane(command_root)
    harness.service.deletion_manifest_authorizer = build_deletion_manifest_authorizer(
        registry, retention_policy_path=POLICY
    )
    command = {
        **_deletion_command(manifest.manifest_hash),
        "payload": tampered_payload,
    }
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()


def test_production_authorizer_rejects_malformed_payload_missing_field(tmp_path):
    registry = _bound_registry(tmp_path)
    manifest = _verify(
        tmp_path,
        actor_id=ACTORS["actor-a"],
        authority_grant_id=AUTHORITY_GRANT_ID,
        registry=registry,
    )
    malformed_payload = jsonable(asdict(manifest))
    del malformed_payload["canonical_scan_hash"]

    command_root = tmp_path / "command"
    command_root.mkdir()
    harness = control_plane(command_root)
    harness.service.deletion_manifest_authorizer = build_deletion_manifest_authorizer(
        registry, retention_policy_path=POLICY
    )
    command = {
        **_deletion_command(manifest.manifest_hash),
        "payload": malformed_payload,
    }
    with pytest.raises(ValueError, match="missing fields: canonical_scan_hash"):
        harness.service.submit(command)
    assert tuple(harness.ledger.iter_batches()) == ()


def _registry_config_payload(tmp_path):
    return {
        "schema_id": "ars://evals/evidence-store-registry",
        "schema_version": "1.0.0",
        "store_id": "evidence-store-1",
        "registry_hash": "a" * 64,
        "policy_revision": "p0-retention-v1",
        "primary_root": str(tmp_path / "primary"),
        "runtime_root": str(tmp_path / "runtime"),
        "staging_root": str(tmp_path / "staging"),
        "temp_root": str(tmp_path / "temp"),
        "replicas": [str(tmp_path / "replica")],
        "backup_roots": [str(tmp_path / "backup")],
        "restore_roots": [str(tmp_path / "restore")],
        "permitted_consumers": ["eval"],
        "retention_policy_ids": ["R2:minimized_sensitive_excerpt"],
        "verifier_authority_bindings": [["actor-1", "grant-1"]],
        "unregistered_replicas_prohibited": True,
    }


def test_load_evidence_store_registry_builds_from_schema_valid_config(tmp_path):
    schemas = SchemaRegistry(Path(".research-system/schemas"))
    config = _registry_config_payload(tmp_path)
    config_path = tmp_path / "registry.yaml"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    registry = load_evidence_store_registry(config_path, schemas)
    assert registry.store_id == "evidence-store-1"
    assert registry.primary_root == tmp_path / "primary"
    assert registry.replicas == (tmp_path / "replica",)
    assert registry.backup_roots == (tmp_path / "backup",)
    assert registry.restore_roots == (tmp_path / "restore",)
    assert registry.verifier_authority_bindings == (("actor-1", "grant-1"),)


def test_load_evidence_store_registry_rejects_schema_invalid_config(tmp_path):
    schemas = SchemaRegistry(Path(".research-system/schemas"))
    bad_config = _registry_config_payload(tmp_path)
    del bad_config["registry_hash"]
    bad_path = tmp_path / "bad_registry.yaml"
    bad_path.write_text(json.dumps(bad_config), encoding="utf-8")

    with pytest.raises(SchemaError):
        load_evidence_store_registry(bad_path, schemas)


def test_retention_policy_cli_validates_accepted_file(capsys):
    assert main(["eval", "retention", "validate", "--policy", str(POLICY)]) == 0
    assert "p0-retention-v1" in capsys.readouterr().out


def test_retention_policy_cli_runs_through_python_module_entrypoint():
    result = subprocess.run(  # nosemgrep  # nosec B603 - fixed local argv
        [
            sys.executable,
            "-m",
            "research_system.cli",
            "eval",
            "retention",
            "validate",
            "--policy",
            str(POLICY),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["policy_revision"] == "p0-retention-v1"


def test_deletion_verification_checks_registered_backup_restore_topology(tmp_path):
    registry = EvidenceStoreRegistry(
        store_id="evidence-store-1",
        registry_hash="a" * 64,
        policy_revision="p0-retention-v1",
        primary_root=tmp_path / "primary",
        runtime_root=tmp_path / "runtime",
        staging_root=tmp_path / "staging",
        temp_root=tmp_path / "temp",
        replicas=(tmp_path / "replica",),
        backup_roots=(tmp_path / "backup",),
        restore_roots=(tmp_path / "restore",),
        permitted_consumers=("eval",),
        retention_policy_ids=("R2:minimized_sensitive_excerpt",),
        verifier_authority_bindings=(("actor-1", "grant-1"),),
        unregistered_replicas_prohibited=True,
    )
    seen = []

    def inspect(path, digest):
        seen.append(path)
        return _inspection(path, digest)

    manifest = verify_deletion(
        evidence_id="evidence-1",
        evidence_hash="c" * 64,
        retention_rule_id="R2:minimized_sensitive_excerpt",
        registry=registry,
        inspect_location=inspect,
        discover_replicas=lambda _: {
            *registry.replicas,
            *registry.backup_roots,
            *registry.restore_roots,
        },
        canonical_payload_scan=lambda digest: CanonicalPayloadScan(
            payload_present=False,
            scan_hash="d" * 64,
        ),
        actor_id="actor-1",
        authority_grant_id="grant-1",
        verified_at="2026-07-11T00:00:00Z",
    )
    assert manifest.status == "verified"
    assert tuple(seen) == registry.checked_locations()


def test_deletion_verification_blocks_unregistered_backup_or_restore_copy(tmp_path):
    registry = _registry(tmp_path)
    manifest = verify_deletion(
        evidence_id="evidence-1",
        evidence_hash="c" * 64,
        retention_rule_id="R2:minimized_sensitive_excerpt",
        registry=registry,
        inspect_location=lambda path, digest: _inspection(path, digest),
        discover_replicas=lambda _: {
            *registry.replicas,
            tmp_path / "unregistered-backup",
        },
        canonical_payload_scan=lambda digest: CanonicalPayloadScan(
            payload_present=False,
            scan_hash="d" * 64,
        ),
        actor_id="actor-1",
        authority_grant_id="grant-1",
        verified_at="2026-07-11T00:00:00Z",
    )
    assert manifest.status == "deletion_pending"
    assert manifest.unregistered_replicas == (
        str((tmp_path / "unregistered-backup").resolve(strict=False)),
    )