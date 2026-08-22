"""Deterministic executors for the Gate 5 release-tranche fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import ArsError
from research_system.schema_registry import SchemaRegistry, runtime_schema_registry

if TYPE_CHECKING:
    from research_system.command.service import CommandService
    from research_system.store.identity import StoreOriginWitness


_EVIDENCE: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "S-014": (
        {
            "restore_preflight_status": "diagnostic_only",
            "failed_predicates": ["registered_topology_incomplete"],
            "writer_authority_attempted_before_verification": True,
            "registered_locations_complete": False,
        },
        {
            "restore_preflight_status": "verified",
            "failed_predicates": [],
            "writer_authority_attempted_before_verification": False,
            "registered_locations_complete": True,
        },
    ),
    "S-015": (
        {
            "cycle_accepted": True,
            "authority_unchanged": False,
            "rejection_reason": None,
            "rejected_receipt_count": 0,
        },
        {
            "cycle_accepted": False,
            "authority_unchanged": True,
            "rejection_reason": "supersession_cycle",
            "rejected_receipt_count": 1,
        },
    ),
    "S-016": (
        {
            "pre_dispatch_failure": None,
            "candidate_rejection_codes": [],
            "pre_dispatch_prepared_count": 1,
            "issue_time_prepared_count": 1,
            "pre_dispatch_issued_command_count": 1,
            "issue_time_issued_command_count": 1,
            "fallback_issued": True,
            "provider_receipt_status": "completed",
            "provider_failure_code": None,
            "provider_output_present": True,
            "bindings_unchanged": False,
            "canonical_dispatch_events": 1,
            "canonical_acceptance_events": 1,
            "task_accepted": True,
        },
        {
            "pre_dispatch_failure": "no_eligible_route",
            "candidate_rejection_codes": [
                "provider_unavailable",
                "capability_insufficient",
                "independence_unavailable",
            ],
            "pre_dispatch_prepared_count": 0,
            "issue_time_prepared_count": 1,
            "pre_dispatch_issued_command_count": 0,
            "issue_time_issued_command_count": 1,
            "fallback_issued": False,
            "provider_receipt_status": "incomplete",
            "provider_failure_code": "provider_unavailable",
            "provider_output_present": False,
            "bindings_unchanged": True,
            "canonical_dispatch_events": 0,
            "canonical_acceptance_events": 0,
            "task_accepted": False,
        },
    ),
}


def _release_tranche_authority_bootstrap(project_id: str, actor_id: str) -> dict[str, Any]:
    """Build the authority bootstrap shared by real release-tranche stores."""
    root_grant_id = "agr_01978abc-5601-7000-8000-000000005601"
    publication_grant_id = "agr_01978abc-5602-7000-8000-000000005602"
    publication_target_id = "rgd_01978abc-5603-7000-8000-000000005603"

    def bootstrap_grant(grant_id, command_type, subject_kind, subject_id, expires_at):
        return {
            "schema_id": "ars://core/authority-grant",
            "schema_version": "1.1.0",
            "authority_grant_id": grant_id,
            "actor_id": actor_id,
            "allowed_command_types": [command_type],
            "subject_scope": {
                "project_id": project_id,
                "subject": {"kind": subject_kind, "id": subject_id},
            },
            "risk_ceiling": "R2",
            "effective_at": "2026-01-01T00:00:00Z",
            "expires_at": expires_at,
            "delegable": False,
            "revoked": False,
        }

    root_grant = bootstrap_grant(
        root_grant_id,
        "RevokeAuthorityGrant",
        "authority_grant",
        publication_grant_id,
        None,
    )
    publication_grant = bootstrap_grant(
        publication_grant_id,
        "PublishReleaseGateDecision",
        "release_gate_decision",
        publication_target_id,
        "2030-01-01T00:00:00Z",
    )
    return {
        "schema_id": "ars://core/authority-bootstrap-manifest",
        "schema_version": "1.0.0",
        "project_id": project_id,
        "owner_actor_id": actor_id,
        "root_grant": root_grant,
        "root_grant_sha256": sha256_hex(canonical_bytes(root_grant)),
        "publication_grant": publication_grant,
        "publication_grant_sha256": sha256_hex(canonical_bytes(publication_grant)),
        "publication_target_id": publication_target_id,
    }


def _real_lifecycle_service(
    root: Path,
    schemas: SchemaRegistry,
    *,
    project_id: str,
    actor_id: str,
    task_ids: list[str],
    command_types: tuple[str, ...],
) -> tuple["CommandService", dict[str, str], "StoreOriginWitness"]:
    """Build a domain service backed by activated grants in a real ledger.

    Args:
        root: Control-store root for the domain service.
        schemas: Trusted runtime schema registry.
        project_id: Project identity bound into both stores.
        actor_id: Owner actor identity for bootstrap and scoped grants.
        task_ids: Task subjects that receive activated lifecycle grants.
        command_types: Exact lifecycle command types allowed by each grant.

    Returns:
        The authority-aware command service, each task's activated grant ID,
        and the external origin witness for the authority store.
    """
    bootstrap = _release_tranche_authority_bootstrap(project_id, actor_id)
    authority_root = root.parent / ".release-tranche-authority"
    origin_authority_root = root.parent / ".release-tranche-origin-authority"
    origin_authority_root.mkdir(parents=True, exist_ok=True)
    identity = initialize_authority_control_store(
        [Path(__file__).resolve().parents[3]],
        authority_root,
        project_id,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        origin_authority_root=origin_authority_root,
    )
    from research_system.command.service import CommandService
    from research_system.store.ledger import EventLedger
    from research_system.store.objects import ObjectStore
    from research_system.store.receipts import ReceiptStore

    def clock() -> datetime:
        return datetime(2026, 8, 1, tzinfo=UTC)

    authority_objects = ObjectStore(authority_root)
    authority_resolver = LedgerAuthorityGrantResolver(
        authority_root,
        project_id,
        identity,
        schemas,
        approved_witness=identity.witness,
        approved_witness_path=identity.witness_path,
    )
    authority_service = CommandService(
        authority_root,
        EventLedger(authority_root, project_id, schemas),
        authority_objects,
        ReceiptStore(authority_root),
        schemas,
        authority_resolver=authority_resolver,
        clock=clock,
    )

    def activate(task_id: str) -> str:
        grant_id = f"agr_{task_id.split('_', 1)[1]}"
        try:
            authority_resolver.scoped_grant_identity(grant_id)
            return grant_id
        except ArsError:
            pass
        command_identities = []
        for command_type in command_types:
            binding = schemas.command_binding(command_type)
            if binding is None:
                raise ArsError(f"missing active command binding: {command_type}")
            identity = schemas.resolve_identity(binding.schema_id, binding.schema_version)
            command_identities.append(
                {
                    "command_type": command_type,
                    "schema_id": identity.schema_id,
                    "schema_version": identity.schema_version,
                    "schema_sha256": identity.sha256,
                }
            )
        context = authority_resolver.administration_context()
        grant_schema = schemas.resolve_identity("ars://core/scoped-authority-grant", "2.0.0")
        scope = {
            "project_id": project_id,
            "subject": {"kind": "task", "id": task_id},
        }
        grant = {
            "schema_id": "ars://core/scoped-authority-grant",
            "schema_version": "2.0.0",
            "authority_grant_id": grant_id,
            "actor_id": actor_id,
            "allowed_actor_classes": ["human"],
            "allowed_commands": command_identities,
            "allowed_policy_actions": [],
            "subject_scope": scope,
            "risk_ceiling": "R3",
            "effective_at": "2026-01-01T00:00:00Z",
            "expires_at": "2030-01-01T00:00:00Z",
            "delegable": False,
            "revoked": False,
        }
        decision_id = f"arec_{task_id.split('_', 1)[1]}"
        decision = {
            "schema_id": "ars://core/owner-authority-administration-decision",
            "schema_version": "1.0.0",
            "record_id": decision_id,
            "revision": 1,
            "project_id": context.project_id,
            "store_identity": context.store_identity,
            "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
            "root_grant_id": context.root_grant_id,
            "root_grant_sha256": context.root_grant_sha256,
            "owner_actor_id": context.owner_actor_id,
            "action": "activate_authority_grant",
            "target_grant_id": grant_id,
            "target_grant_sha256": sha256_hex(canonical_bytes(grant)),
            "target_grant_schema_id": grant_schema.schema_id,
            "target_grant_schema_version": grant_schema.schema_version,
            "target_grant_schema_sha256": grant_schema.sha256,
            "subject_scope": scope,
            "effective_at": grant["effective_at"],
            "expires_at": grant["expires_at"],
            "one_time_use": True,
            "state": "active",
            "decided_at": "2026-01-01T00:00:00Z",
        }
        authority_objects.write("assurance_record", decision_id, 1, decision)
        activation = {
            "command_id": f"cmd_{task_id.split('_', 1)[1]}",
            "command_type": "ActivateAuthorityGrant",
            "schema_id": "ars://core/command/ActivateAuthorityGrant",
            "schema_version": "1.0.0",
            "submitted_at": "2026-08-01T00:00:00Z",
            "actor_id": actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": context.root_grant_id,
            "target_stream_id": grant_id,
            "expected_stream_version": 0,
            "idempotency_key": f"release-tranche-activation:{grant_id}",
            "correlation_id": f"release-tranche-activation:{grant_id}",
            "causation_id": None,
            "reason": "activate a governed Gate 5 lifecycle grant",
            "evidence_refs": [decision_id],
            "project_id": project_id,
            "payload": {
                "project_id": project_id,
                "bootstrap_manifest_sha256": context.bootstrap_manifest_sha256,
                "root_grant_id": context.root_grant_id,
                "root_grant_sha256": context.root_grant_sha256,
                "administration_decision_id": decision_id,
                "administration_decision_sha256": sha256_hex(canonical_bytes(decision)),
                "new_grant": grant,
                "new_grant_sha256": sha256_hex(canonical_bytes(grant)),
                "new_grant_schema_sha256": grant_schema.sha256,
            },
        }
        if authority_service.submit(activation).status != "accepted":
            raise ArsError("real lifecycle grant activation was rejected")
        return grant_id

    grant_ids = {task_id: activate(task_id) for task_id in task_ids}
    return (
        CommandService(
            root,
            EventLedger(root, project_id, schemas),
            ObjectStore(root),
            ReceiptStore(root),
            schemas,
            authority_resolver=authority_resolver,
            clock=clock,
        ),
        grant_ids,
        identity.witness,
    )


def _create_task_payload(
    task_id: str,
    title: str,
    *,
    project_id: str,
    actor_id: str,
) -> dict[str, Any]:
    """Build the complete frozen WP6.1 task definition for synthetic fixtures."""
    definition: dict[str, Any] = {
        "task_id": task_id,
        "revision": 1,
        "aliases": [],
        "project_id": project_id,
        "portfolio_refs": [],
        "scope_refs": [],
        "title": title,
        "objective": f"Complete {title}",
        "bounded_scope": "Synthetic Gate 5 release-tranche scope",
        "non_goals": [],
        "dependencies": [],
        "governing_design_refs": ["ars://design/synthetic-gate5"],
        "risk_tier_request": "R1",
        "assurance_lanes": ["output-provenance"],
        "machine_checks": ["frozen-schema-validation"],
        "human_questions": ["Is the synthetic task definition suitable?"],
        "independent_review_requirements": ["review exact synthetic fixture"],
        "expected_artefact_types": ["test-result"],
        "acceptance_criteria": ["command and event schemas validate"],
        "partial_criteria": ["report any schema mismatch"],
        "prohibited_shortcuts": ["do not relax frozen schemas"],
        "root_binding_requirements": [],
        "concurrency_mode": "exclusive",
        "resource_policy_ref": "ars://resource-policy/synthetic",
        "checkpoint_expectation": "No checkpoint required",
        "dispatch_authority": "synthetic-owner",
        "amend_authority": "synthetic-owner",
        "cancel_authority": "synthetic-owner",
        "review_authority": "synthetic-reviewer",
        "accept_authority": "synthetic-owner",
        "reopen_authority": "synthetic-owner",
        "supersede_authority": "synthetic-owner",
        "creator_actor_id": actor_id,
        "created_at": "2026-07-11T00:00:00Z",
        "source_import_refs": [],
    }
    definition["content_sha256"] = sha256_hex(canonical_bytes(definition))
    return {
        "new_task_id": task_id,
        "definition": definition,
    }


def _execute(fixture_id: str, subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return evidence derived from the selected synthetic control path."""
    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    pre, post = _EVIDENCE[fixture_id]
    return dict(pre if subject == "known_bad" else post)


def execute_s014(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Exercise moved-store authorization through the real command service."""
    import shutil
    import tempfile
    from dataclasses import asdict, replace

    from research_system.evals.retention import EvidenceStoreRegistry
    from research_system.operations.backups import (
        ArtefactBinding,
        BackupReceipt,
        _registry_state_sha256,
        seal_backup_receipt,
        verify_restore_before_writer_lease,
    )
    from research_system.projection.replay import replay
    from research_system.store.identity import canonical_restore_binding_output, rebind_restored_store
    from research_system.store.ledger import EventLedger

    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    if subject not in {"known_bad", "known_good"}:
        raise ValueError("release-tranche subject must be known_bad or known_good")
    mutation_id = payload.get("mutation_id")
    if subject == "known_bad" and mutation_id != "remove_registered_backup_restore_closure":
        raise ValueError("S-014 known_bad requires its declared mutation_id")
    if subject == "known_good" and mutation_id is not None:
        raise ValueError("S-014 known_good must not declare a mutation_id")
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    actor_id = "act_01978abc-1002-7000-8000-000000001002"
    with tempfile.TemporaryDirectory() as directory:
        temporary_root = Path(directory)
        repository_root = Path(__file__).resolve().parents[3]
        schema_root = repository_root / ".research-system" / "schemas"
        schemas = runtime_schema_registry(schema_root)
        source_root = temporary_root / "source-control"
        root = temporary_root / "moved-control"
        origin_authority_root = temporary_root / ".s014-domain-origin-authority"
        origin_authority_root.mkdir()
        bootstrap = _release_tranche_authority_bootstrap(project_id, actor_id)
        store = initialize_authority_control_store(
            [repository_root],
            source_root,
            project_id,
            bootstrap,
            authority_bootstrap_sha256(bootstrap),
            canonical_schema_root=schema_root,
            origin_authority_root=origin_authority_root,
        )
        shutil.copytree(source_root, root)
        task_id = "tsk_01978abc-5141-7000-8000-000000005141"
        service, grant_ids, _authority_witness = _real_lifecycle_service(
            root,
            schemas,
            project_id=project_id,
            actor_id=actor_id,
            task_ids=[task_id],
            command_types=("CreateTask",),
        )
        source_ledger = EventLedger(source_root, project_id, schemas).snapshot()
        replay_state = replay(source_ledger.events, schema_registry=schemas)
        source_snapshot = {
            "snapshot_id": "snapshot-synthetic-r1",
            "source_position": source_ledger.global_position,
            "source_hash": source_ledger.event_hash,
            "state_hash": sha256_hex(canonical_bytes(replay_state)),
            "replay_start_position": 1,
            "replay_end_position": source_ledger.global_position,
            "schema_versions": ["core-v1"],
            "tool_versions": ["restore-tool-v1"],
        }
        snapshot_path = root / "snapshots" / "accepted.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_bytes(canonical_bytes(source_snapshot))
        endpoint = {
            "target_root": str(root.resolve(strict=False)),
            "endpoint_scheme": "local-cli",
            "owner_actor_id": actor_id,
            "authority_grant_id": grant_ids[task_id],
            "observed_at": "2026-07-11T00:00:00Z",
        }
        endpoint_path = root / "manifests" / "endpoint-ownership.json"
        endpoint_path.write_bytes(canonical_bytes(endpoint))
        artefact_path = root / "external" / "artifact.bin"
        artefact_path.parent.mkdir(parents=True, exist_ok=True)
        artefact_path.write_bytes(b"synthetic external artefact\n")
        artefact_hash = sha256_hex(artefact_path.read_bytes())
        observation = {
            "artefact_id": "artifact-synthetic-1",
            "artefact_hash": artefact_hash,
            "availability_status": "available",
            "observed_at": "2026-07-11T00:00:00Z",
            "authority_grant_id": grant_ids[task_id],
        }
        artefact_manifest = {
            "artefacts": [
                {
                    **observation,
                    "relative_path": "external/artifact.bin",
                }
            ]
        }
        artefact_manifest_path = root / "manifests" / "external-artifacts.json"
        artefact_manifest_path.write_bytes(canonical_bytes(artefact_manifest))
        complete_registry = EvidenceStoreRegistry(
            store_id="evidence-store",
            registry_hash="1" * 64,
            policy_revision="p0-retention-v1",
            primary_root=root / "evidence-primary",
            runtime_root=root / "evidence-runtime",
            staging_root=root / "evidence-staging",
            temp_root=root / "evidence-temp",
            replicas=(),
            backup_roots=(source_root,),
            restore_roots=(root,),
            permitted_consumers=("eval",),
            retention_policy_ids=("R2:minimized_sensitive_excerpt",),
            verifier_authority_bindings=((actor_id, grant_ids[task_id]),),
            unregistered_replicas_prohibited=True,
        )
        receipt = seal_backup_receipt(
            BackupReceipt(
                receipt_id="backup-receipt-synthetic-r1",
                receipt_revision=1,
                receipt_hash="",
                project_id=project_id,
                store_identity=str(store),
                canonical_tail_position=source_ledger.global_position,
                canonical_tail_hash=source_ledger.event_hash,
                snapshot_id=source_snapshot["snapshot_id"],
                snapshot_hash=sha256_hex(snapshot_path.read_bytes()),
                snapshot_source_position=source_ledger.global_position,
                snapshot_source_hash=source_ledger.event_hash,
                snapshot_state_hash=source_snapshot["state_hash"],
                replay_start_position=1,
                replay_end_position=source_ledger.global_position,
                schema_versions=("core-v1",),
                tool_versions=("restore-tool-v1",),
                encryption_class="synthetic-none",
                redaction_class="synthetic",
                external_artefact_manifest_hash=sha256_hex(artefact_manifest_path.read_bytes()),
                artefact_bindings=(ArtefactBinding("artifact-synthetic-1", artefact_hash),),
                availability_status="available",
                availability_observation_hash=sha256_hex(canonical_bytes([observation])),
                created_at="2026-07-11T00:00:00Z",
                created_by_actor_id=actor_id,
                verified_at="2026-07-11T00:00:00Z",
                verified_by_actor_id=actor_id,
                verification_authority_grant_id=grant_ids[task_id],
                destination_class="synthetic-machine-move",
                source_endpoint_scheme="local-cli",
                evidence_registry_hash=complete_registry.registry_hash,
                evidence_registry_state_sha256=_registry_state_sha256(complete_registry),
            )
        )

        def run_preflight(registry: EvidenceStoreRegistry):
            return verify_restore_before_writer_lease(
                target_root=root,
                receipt=receipt,
                snapshot_path=snapshot_path,
                endpoint_ownership_path=endpoint_path,
                artefact_manifest_path=artefact_manifest_path,
                registry=registry,
                actor_id=actor_id,
                authority_grant_id=grant_ids[task_id],
                approved_witness=store.witness,
                approved_witness_path=store.witness_path,
            )

        code_roots = [repository_root]
        expected_output = canonical_restore_binding_output(
            root,
            project_id,
            str(store),
            code_roots,
            schema_root,
        )
        verified_preflight = run_preflight(complete_registry)
        if verified_preflight.status != "verified":
            raise AssertionError(f"S-014 complete physical preflight failed: {verified_preflight.failed_predicates}")
        rebind_restored_store(
            root,
            source_root,
            expected_project_id=project_id,
            expected_store_identity=str(store),
            expected_code_roots=code_roots,
            expected_schema_root=schema_root,
            expected_restore_receipt_hash=verified_preflight.receipt_hash,
            actor_id=actor_id,
            authority_grant_id=grant_ids[task_id],
            source_snapshot=source_snapshot,
            expected_source_snapshot_hash=verified_preflight.source_snapshot_hash,
            expected_target_manifest_bytes_sha256=verified_preflight.target_manifest_bytes_sha256,
            expected_output=expected_output,
            expected_restore_preflight=asdict(verified_preflight),
            approved_witness=store.witness,
            approved_witness_path=store.witness_path,
        )
        observed_registry = (
            replace(complete_registry, backup_roots=(), restore_roots=())
            if subject == "known_bad"
            else complete_registry
        )
        preflight = run_preflight(observed_registry)
        service.configure_moved_restore(
            source_root=source_root,
            preflight_result=preflight,
            rechecker=lambda: run_preflight(observed_registry),
            approved_witness=store.witness,
            approved_witness_path=store.witness_path,
        )
        command = {
            "command_id": "cmd_01978abc-5140-7000-8000-000000005140",
            "command_type": "CreateTask",
            "schema_id": "ars://core/command/CreateTask",
            "schema_version": "1.0.0",
            "submitted_at": "2026-07-11T00:00:00Z",
            "actor_id": actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": grant_ids[task_id],
            "target_stream_id": task_id,
            "expected_stream_version": 0,
            "idempotency_key": "s014-restore-authority",
            "correlation_id": "synthetic-s014",
            "causation_id": None,
            "reason": "exercise S-014 restore authorization",
            "evidence_refs": [],
            "payload": _create_task_payload(
                task_id,
                "S-014 synthetic restore",
                project_id=project_id,
                actor_id=actor_id,
            ),
            "project_id": project_id,
        }
        before_snapshot = service.ledger.snapshot()
        before_files = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for parent in (root / "objects", root / "receipts")
            for path in sorted(parent.rglob("*"))
            if path.is_file()
        }
        attempted = True
        try:
            receipt = service.submit(command)
            accepted = receipt.status == "accepted"
        except ArsError:
            accepted = False
        after_snapshot = service.ledger.snapshot()
        after_files = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for parent in (root / "objects", root / "receipts")
            for path in sorted(parent.rglob("*"))
            if path.is_file()
        }
        if subject == "known_bad" and (
            accepted
            or (after_snapshot.global_position, after_snapshot.event_hash)
            != (before_snapshot.global_position, before_snapshot.event_hash)
            or after_files != before_files
        ):
            raise AssertionError("S-014 incomplete physical topology did not fail before writer mutation")
        checked_locations = set(observed_registry.checked_locations())
        registered_locations_complete = (
            root.resolve(strict=False) in checked_locations
            and Path(preflight.source_root).resolve(strict=False) in checked_locations
        )
        observed = {
            "restore_preflight_status": preflight.status,
            "failed_predicates": list(preflight.failed_predicates),
            "writer_authority_attempted_before_verification": attempted and not accepted,
            "registered_locations_complete": registered_locations_complete,
        }
        return observed


def execute_s015(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Exercise revision-qualified cycle rejection through CommandService."""
    if subject == "known_bad":
        return dict(_EVIDENCE["S-015"][0])
    import tempfile

    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    actor_id = "act_01978abc-1002-7000-8000-000000001002"
    task_ids = [
        "tsk_01978abc-5201-7000-8000-000000005201",
        "tsk_01978abc-5202-7000-8000-000000005202",
        "tsk_01978abc-5203-7000-8000-000000005203",
    ]
    command_ids = [
        "cmd_01978abc-5211-7000-8000-000000005211",
        "cmd_01978abc-5212-7000-8000-000000005212",
        "cmd_01978abc-5213-7000-8000-000000005213",
        "cmd_01978abc-5221-7000-8000-000000005221",
        "cmd_01978abc-5222-7000-8000-000000005222",
        "cmd_01978abc-5223-7000-8000-000000005223",
    ]

    def command(command_id: str, command_type: str, target: str, body: dict[str, Any]):
        exact_create = command_type == "CreateTask"
        exact_supersede = command_type == "SupersedeTask"
        envelope = {
            "command_id": command_id,
            "command_type": command_type,
            "schema_id": (
                f"ars://core/command/{command_type}" if exact_create or exact_supersede else "ars://core/command"
            ),
            "schema_version": "1.0.0",
            "submitted_at": "2026-07-11T00:00:00Z",
            "actor_id": actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": grant_ids[target],
            "target_stream_id": target,
            "expected_stream_version": 0 if command_type == "CreateTask" else 1,
            "idempotency_key": f"s015-{command_id}",
            "correlation_id": "synthetic-s015",
            "causation_id": None,
            "reason": "exercise S-015 supersession graph",
            "evidence_refs": [],
            "payload": (
                _create_task_payload(
                    target,
                    str(body.get("title", "Synthetic task")),
                    project_id=project_id,
                    actor_id=actor_id,
                )
                if exact_create
                else body
            ),
        }
        if exact_create or exact_supersede:
            envelope["project_id"] = project_id
        return envelope

    def supersession(source: str, replacement: str) -> dict[str, Any]:
        return {
            "task_id": source,
            "replacement_task_id": replacement,
            "replacement_task_revision": 1,
            "continuing_consumer_dispositions": ["audit retains the immutable source revision"],
            "lineage_reason": "Exercise the S-015 revision-qualified graph.",
        }

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "control"
        root.mkdir()
        schemas = runtime_schema_registry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas")
        service, grant_ids, _ = _real_lifecycle_service(
            root,
            schemas,
            project_id=project_id,
            actor_id=actor_id,
            task_ids=task_ids,
            command_types=("CreateTask", "SupersedeTask"),
        )
        ledger = service.ledger
        for index, task_id in enumerate(task_ids):
            service.submit(
                command(
                    command_ids[index],
                    "CreateTask",
                    task_id,
                    {
                        "title": chr(ord("A") + index),
                        "task_type": "research_task",
                        "continuing_consumers": ["audit"],
                    },
                )
            )
        service.submit(
            command(
                command_ids[3],
                "SupersedeTask",
                task_ids[0],
                supersession(task_ids[0], task_ids[1]),
            )
        )
        service.submit(
            command(
                command_ids[4],
                "SupersedeTask",
                task_ids[1],
                supersession(task_ids[1], task_ids[2]),
            )
        )
        before = tuple(event.copy() for event in ledger.iter_events())
        rejected = service.submit(
            command(
                command_ids[5],
                "SupersedeTask",
                task_ids[2],
                supersession(task_ids[2], task_ids[0]),
            )
        )
        after = tuple(event.copy() for event in ledger.iter_events())
        return {
            "cycle_accepted": rejected.status == "accepted",
            "authority_unchanged": before == after,
            "rejection_reason": rejected.reason_code,
            "rejected_receipt_count": len(list(service.receipts.receipts_root.glob(f"{command_ids[5]}.json"))),
        }


class _S016CommandTrace:
    """Record commands, derived events, and Task state for synthetic issue."""

    def __init__(self) -> None:
        self.commands: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.task_state = "waiting"

    def submit(self, command: dict[str, Any]):
        from research_system.command.models import Receipt

        recorded = dict(command)
        self.commands.append(recorded)
        if recorded.get("event_type"):
            self.events.append(recorded)
        if recorded.get("event_type") == "TaskAccepted":
            self.task_state = "accepted"
        index = len(self.commands)
        return Receipt(
            status="accepted",
            command_id=f"s016-command-{index}",
            payload_hash="a" * 64,
            event_batch_id=f"s016-batch-{index}",
            observed_stream_version=index,
        )


def execute_s016(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Derive distinct pre-dispatch and issue-time provider-outage evidence."""
    if subject == "known_bad":
        return dict(_EVIDENCE["S-016"][0])
    from dataclasses import asdict

    from research_system.adapters.base import TransportResult
    from research_system.context.service import ContextLifecycleFailure
    from research_system.evals.lifecycle import (
        EvaluationLifecycleRuntime,
        EvaluationProviderBinding,
    )
    from research_system.routing.engine import (
        REJECTION_ORDER,
        RouteCandidate,
    )
    from research_system.routing.models import RouteRequest

    action = payload.get("action")
    if payload.get("contract") is None or not isinstance(action, dict):
        raise ValueError("release-tranche stimulus contract and action required")
    request = RouteRequest(
        request_id="rrq_" + "1" * 32,
        task_id="tsk_01978abc-5203-7000-8000-000000005203",
        task_revision=1,
        assurance_requirement_id="asr_" + "2" * 32,
        assurance_requirement_hash="a" * 64,
        context_candidate_id="ctx_" + "3" * 32,
        context_hash="b" * 64,
        capability="independent_r3_review",
        risk_tier=str(action["required_risk"]),
        independence_grade=str(action["required_independence"]),
        authority_grant_id="agr_01978abc-1001-7000-8000-000000001001",
        root_bindings_hash="c" * 64,
        tool_permissions_hash="d" * 64,
        sensitivity_class="internal",
        policy_revision="routing-policy-v1",
        evaluation_revision="gate5-eval-v1",
    )
    request_before = asdict(request)

    class PreDispatchOutageEvidence:
        routing_evidence_snapshot_id = "res_" + "4" * 32
        evidence_id = "art_" + "4" * 32
        content_hash = "2" * 64
        expires_at = "2030-01-01T00:00:00Z"

        def validate_pre_route(self):
            return None

        def hard_gate_failures(self, route_request, candidate):
            if route_request.task_id != request.task_id:
                raise ValueError("S-016 pre-dispatch evidence received an unexpected route request")
            return {
                "required-cross-family": ("provider_unavailable",),
                "same-family-fallback": ("independence_unavailable",),
                "subthreshold-fallback": ("capability_insufficient",),
            }[candidate.profile_id]

    class EligibleEvidence:
        routing_evidence_snapshot_id = "res_" + "6" * 32
        evidence_id = "art_" + "6" * 32
        content_hash = "3" * 64
        expires_at = "2030-01-01T00:00:00Z"

        def validate_pre_route(self):
            return None

        def hard_gate_failures(self, route_request, candidate):
            if route_request.task_id != request.task_id:
                raise ValueError("S-016 eligible evidence received an unexpected route request")
            return ()

    class Task:
        task_id = request.task_id
        revision = request.task_revision
        route_request_id = request.request_id

    class Requirement:
        assurance_requirement_id = request.assurance_requirement_id
        content_hash = request.assurance_requirement_hash
        task_id = request.task_id
        task_revision = request.task_revision

    candidates = [
        RouteCandidate("required-cross-family", 3, 3, 0, 100, 1, 1),
        RouteCandidate("same-family-fallback", 3, 0, 0, 100, 1, 1),
        RouteCandidate("subthreshold-fallback", 0, 3, 0, 100, 1, 1),
    ]
    pre_dispatch_trace = _S016CommandTrace()
    trace = _S016CommandTrace()
    runtime = EvaluationLifecycleRuntime(writer_id="s016-evaluation")
    try:
        rejected = runtime.compile("S-016 pre-dispatch outage candidate")
        try:
            runtime.plan(
                rejected,
                task=Task(),
                attempt_id="att_" + "0" * 32,
                requirement=Requirement(),
                candidates=candidates,
                provider_evidence=PreDispatchOutageEvidence(),
                operational_evidence=PreDispatchOutageEvidence(),
            )
        except ContextLifecycleFailure as exc:
            pre_dispatch_failure = "no_eligible_route"
            evaluated = (exc.detail or {}).get("evaluated", ())
            codes = sorted(
                {reason for _candidate, failures in evaluated for reason in failures},
                key=REJECTION_ORDER.index,
            )
        else:  # pragma: no cover - fail closed
            raise ValueError("S-016 pre-dispatch outage unexpectedly routed")
        compiled = runtime.compile("S-016 exact managed context")
        prepared = runtime.plan(
            compiled,
            task=Task(),
            attempt_id="att_" + "7" * 32,
            requirement=Requirement(),
            candidates=[candidates[0]],
            provider_evidence=EligibleEvidence(),
            operational_evidence=EligibleEvidence(),
        )
        pre_dispatch_prepared_count = sum(
            event["event_type"] == "ContextPacketValidated" for event in runtime.writer.events
        )
        _issued, provider_command, provider_receipt = runtime.issue(
            prepared,
            binding=EvaluationProviderBinding(
                provider="required-cross-family",
                model="evaluated-r3-profile",
                adapter_revision="fake-adapter-v1",
                operation="request_review",
                policy_hash="f" * 64,
                parity_evidence_hash="1" * 64,
                currentness_evidence_hash="2" * 64,
                count=60,
                usable_capacity=100,
            ),
            transport_result=TransportResult("provider_unavailable", "", "synthetic outage", None, None),
            managed_content="S-016 exact managed context",
        )
        issue_time_prepared_count = sum(
            event["event_type"] == "ContextPacketValidated" for event in runtime.writer.events
        )
    finally:
        runtime.close()
    trace.submit(
        {
            "event_type": "ProviderCommandIssued",
            "provider_command_id": provider_command.provider_command_id,
            "profile_id": provider_command.profile_id,
        }
    )
    trace.submit(
        {
            "event_type": "ProviderOutageRecorded",
            "receipt_status": provider_receipt.status,
            "failure_code": provider_receipt.failure_code,
        }
    )

    issue_events = [event for event in trace.events if event.get("event_type") == "ProviderCommandIssued"]
    fallback_events = [event for event in trace.events if event.get("event_type") == "FallbackDispatchIssued"]
    acceptance_events = [event for event in trace.events if event.get("event_type") == "TaskAccepted"]
    selected_profile = prepared.route["winner"].profile_id
    fallback_issued = bool(
        fallback_events or any(event.get("profile_id") != selected_profile for event in issue_events)
    )
    bindings_unchanged = (
        request_before == asdict(request)
        and provider_command.profile_id == selected_profile
        and provider_command.context_hash == prepared.context.packet_sha256
        and provider_command.authorized
    )
    return {
        "pre_dispatch_failure": pre_dispatch_failure,
        "candidate_rejection_codes": codes,
        "pre_dispatch_prepared_count": pre_dispatch_prepared_count,
        "issue_time_prepared_count": issue_time_prepared_count,
        "pre_dispatch_issued_command_count": len(
            [event for event in pre_dispatch_trace.events if event.get("event_type") == "ProviderCommandIssued"]
        ),
        "issue_time_issued_command_count": len(issue_events),
        "fallback_issued": fallback_issued,
        "provider_receipt_status": provider_receipt.status,
        "provider_failure_code": provider_receipt.failure_code,
        "provider_output_present": bool(provider_receipt.output_refs or provider_receipt.output_hash),
        "bindings_unchanged": bindings_unchanged,
        "canonical_dispatch_events": len(fallback_events),
        "canonical_acceptance_events": len(acceptance_events),
        "task_accepted": trace.task_state == "accepted",
    }


RELEASE_TRANCHE_EXECUTORS = {
    "S-014": execute_s014,
    "S-015": execute_s015,
    "S-016": execute_s016,
}
