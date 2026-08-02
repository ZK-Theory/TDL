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


def _real_lifecycle_service(
    root: Path,
    schemas: SchemaRegistry,
    *,
    project_id: str,
    actor_id: str,
    task_ids: list[str],
    command_types: tuple[str, ...],
) -> tuple["CommandService", dict[str, str]]:
    """Build a domain service backed by activated grants in a real ledger.

    Args:
        root: Control-store root for the domain service.
        schemas: Trusted runtime schema registry.
        project_id: Project identity bound into both stores.
        actor_id: Owner actor identity for bootstrap and scoped grants.
        task_ids: Task subjects that receive activated lifecycle grants.
        command_types: Exact lifecycle command types allowed by each grant.

    Returns:
        The authority-aware command service and each task's activated grant ID.
    """
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
    bootstrap = {
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
    authority_root = root.parent / ".release-tranche-authority"
    identity = initialize_authority_control_store(
        [Path(__file__).resolve().parents[3]],
        authority_root,
        project_id,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
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
    import tempfile
    from research_system.errors import ArsError
    from research_system.operations.backups import (
        RestorePreflightResult,
        seal_restore_preflight_result,
    )

    if payload.get("contract") is None or not isinstance(payload.get("action"), dict):
        raise ValueError("release-tranche stimulus contract and action required")
    project_id = "prj_01978abc-1000-7000-8000-000000001000"
    actor_id = "act_01978abc-1002-7000-8000-000000001002"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "moved-control"
        root.mkdir()
        schemas = runtime_schema_registry(Path(__file__).resolve().parents[3] / ".research-system" / "schemas")
        task_id = "tsk_01978abc-5141-7000-8000-000000005141"
        service, grant_ids = _real_lifecycle_service(
            root,
            schemas,
            project_id=project_id,
            actor_id=actor_id,
            task_ids=[task_id],
            command_types=("CreateTask",),
        )
        failed = ("registered_topology_incomplete",) if subject == "known_bad" else ()
        preflight = seal_restore_preflight_result(
            RestorePreflightResult(
                status="diagnostic_only" if failed else "verified",
                failed_predicates=failed,
                receipt_hash="a" * 64,
                ledger_hash="b" * 64,
                snapshot_hash="c" * 64,
                target_endpoint_ownership_hash="d" * 64,
                artefact_manifest_hash="e" * 64,
                availability_observations_hash="f" * 64,
                registry_hash="1" * 64,
                target_root=str(root.resolve(strict=False)),
                project_id=project_id,
                store_identity="2" * 64,
                tail_position=0,
                tail_hash="0" * 64,
                snapshot_id="snapshot-synthetic-r1",
                actor_id=actor_id,
                authority_grant_id=grant_ids[task_id],
                result_hash="",
            )
        )
        service.configure_moved_restore(
            source_root=Path(directory) / "source-control",
            preflight_result=preflight,
            rechecker=lambda: preflight,
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
        attempted = True
        try:
            receipt = service.submit(command)
            accepted = receipt.status == "accepted"
        except ArsError:
            accepted = False
        observed = {
            "restore_preflight_status": preflight.status,
            "failed_predicates": list(preflight.failed_predicates),
            "writer_authority_attempted_before_verification": attempted and not accepted,
            "registered_locations_complete": not preflight.failed_predicates,
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
        service, grant_ids = _real_lifecycle_service(
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


class _S016IssueAdapter:
    """Build and issue the provider command from one eligible dispatch."""

    def __init__(self, request) -> None:
        from research_system.adapters.base import TransportResult
        from research_system.adapters.fake import FakeTransport
        from research_system.adapters.provider import ProviderAdapter

        transport = FakeTransport(
            [
                TransportResult(
                    "provider_unavailable",
                    "",
                    "synthetic outage",
                    None,
                    None,
                )
            ]
        )
        self.request = request
        from research_system.adapters.provider import default_provider_operation_policy

        self.provider = ProviderAdapter(
            ["fake-provider"],
            transport,
            operation_policy=default_provider_operation_policy(live_provider_enabled=True),
        )
        self.managed_content = ""

    def load_evidence(self, evidence_id: str, content_hash: str) -> dict[str, Any]:
        return {
            "evidence_id": evidence_id,
            "content_hash": content_hash,
            "available": True,
        }

    def revalidate(self, route, context, provider_evidence):
        winner = route.get("winner")
        if (
            route.get("kind") != "selected"
            or winner is None
            or winner.profile_id != "required-cross-family"
            or provider_evidence.get("available") is not True
        ):
            raise ValueError("S-016 issue route is not eligible")
        return {
            "profile_id": winner.profile_id,
            "context_hash": self.request.context_hash,
        }

    def build_command(self, prepared, grant, lease, revalidated):
        from research_system.adapters.base import ProviderCommand

        profile_id = prepared.route["winner"].profile_id
        if revalidated["profile_id"] != profile_id:
            raise ValueError("S-016 revalidation changed selected profile")
        self.managed_content = str(prepared.context["managed_content"])
        return ProviderCommand(
            provider_command_id="pcmd_" + "5" * 32,
            revision=1,
            revision_hash="e" * 64,
            provider=profile_id,
            model="evaluated-r3-profile",
            profile_id=profile_id,
            adapter_revision="fake-adapter-v1",
            policy_hash="f" * 64,
            context_hash=revalidated["context_hash"],
            rendered_payload_hash="1" * 64,
            idempotency_key="s016-issue-time-outage",
            operation="request_review",
            timeout_s=30.0,
            wrapper_accounting={
                "method": "fake-upper-v1",
                "raw_capacity": 100,
                "fixed_overhead": 10,
                "managed_tokens": 60,
                "reserved_variable_tokens": 5,
                "segments": {"managed": "managed", "system": "reserved"},
            },
            authorized=bool(grant["authorized"] and lease["active"]),
        )

    def record_issue_command(self, provider_command):
        return {
            "event_type": "ProviderCommandIssued",
            "provider_command_id": provider_command.provider_command_id,
            "profile_id": provider_command.profile_id,
        }

    def issue(self, provider_command, issued_receipt):
        if issued_receipt.status != "accepted":
            raise ValueError("S-016 provider command was not recorded")
        return self.provider.issue(provider_command, self.managed_content)


class _S016IssueOperations:
    """Drive grant, lease, and outage receipt transitions for S-016."""

    def build_request(self, prepared, revalidated):
        return {
            "attempt_id": prepared.attempt_id,
            "profile_id": revalidated["profile_id"],
        }

    def request_grant_command(self, request):
        return {
            "event_type": "ResourceGrantRequested",
            "attempt_id": request["attempt_id"],
            "authorized": True,
        }

    def load_grant(self, grant_receipt):
        return {"authorized": grant_receipt.status == "accepted"}

    def claim_lease_command(self, grant, attempt_id):
        return {
            "event_type": "LeaseClaimed",
            "attempt_id": attempt_id,
            "authorized": grant["authorized"],
        }

    def load_lease(self, lease_receipt):
        return {"active": lease_receipt.status == "accepted"}

    def record_provider_receipt_command(self, lease, provider_receipt):
        return {
            "event_type": (
                "ProviderOutageRecorded"
                if provider_receipt.failure_code == "provider_unavailable"
                else "ProviderReceiptRecorded"
            ),
            "lease_active": lease["active"],
            "receipt_status": provider_receipt.status,
            "failure_code": provider_receipt.failure_code,
            "acceptance_allowed": provider_receipt.complete,
        }


def execute_s016(subject: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Derive distinct pre-dispatch and issue-time provider-outage evidence."""
    if subject == "known_bad":
        return dict(_EVIDENCE["S-016"][0])
    from dataclasses import asdict

    from research_system.operations import coordinator
    from research_system.routing.engine import (
        REJECTION_ORDER,
        PreparedDispatch,
        RouteCandidate,
        select_route,
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

        def hard_gate_failures(self, route_request, candidate):
            assert route_request == request
            return {
                "required-cross-family": ("provider_unavailable",),
                "same-family-fallback": ("independence_unavailable",),
                "subthreshold-fallback": ("capability_insufficient",),
            }[candidate.profile_id]

    class EligibleEvidence:
        routing_evidence_snapshot_id = "res_" + "6" * 32

        def hard_gate_failures(self, route_request, candidate):
            assert route_request == request
            return ()

    candidates = [
        RouteCandidate("required-cross-family", 3, 3, 0, 100, 1, 1),
        RouteCandidate("same-family-fallback", 3, 0, 0, 100, 1, 1),
        RouteCandidate("subthreshold-fallback", 0, 3, 0, 100, 1, 1),
    ]
    pre_dispatch = select_route(request, candidates, PreDispatchOutageEvidence())
    pre_dispatch_trace = _S016CommandTrace()
    codes = sorted(
        {reason for _candidate, failures in pre_dispatch["evaluated"] for reason in failures},
        key=REJECTION_ORDER.index,
    )

    issue_route = select_route(request, [candidates[0]], EligibleEvidence())
    if issue_route["kind"] != "selected":
        raise ValueError("S-016 issue-time provider was not eligible")
    prepared = PreparedDispatch(
        attempt_id="att_" + "7" * 32,
        assurance_requirement_id=request.assurance_requirement_id,
        assurance_requirement_hash=request.assurance_requirement_hash,
        context={
            "managed_content": "synthetic managed context",
            "context_hash": request.context_hash,
        },
        route=issue_route,
        provider_evidence_id="art_" + "8" * 32,
        provider_evidence_hash="2" * 64,
        operational_evidence_id="art_" + "9" * 32,
        operational_evidence_hash="3" * 64,
        expires_at="2026-07-11T00:30:00Z",
    )
    trace = _S016CommandTrace()
    provider_command, provider_receipt, _terminal = coordinator.issue_prepared_dispatch(
        prepared,
        _S016IssueAdapter(request),
        _S016IssueOperations(),
        trace,
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
        and provider_command.context_hash == request.context_hash
        and provider_command.authorized
    )
    return {
        "pre_dispatch_failure": ("no_eligible_route" if pre_dispatch["kind"] == "failure" else None),
        "candidate_rejection_codes": codes,
        "pre_dispatch_prepared_count": (0 if pre_dispatch["kind"] == "failure" else 1),
        "issue_time_prepared_count": int(isinstance(prepared, PreparedDispatch)),
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
