from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404 - fixed git discovery command
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.assurance.external_records import (
    ExternalAssuranceRecordStore,
    ExternalRecordPublicationContext,
)
from research_system.assurance.relationship_facts import (
    ProtectedRelationshipReference,
    RelationshipEvidenceFactsStore,
    RelationshipEvidenceParticipant,
)
from research_system.assurance.runner import (
    AssurancePackRunnerConfig,
    SemanticRecordLocator,
    accept_assurance_pack,
    prepare_assurance_pack,
)
from research_system.canonical import canonical_bytes, jsonable, sha256_hex
from research_system.command.service import CommandService
from research_system.config import (
    ApprovedProjectBinding,
    ControlBinding,
    canonical_foundation_path,
    load_foundation_origin_pins,
)
from research_system.errors import ArsError, ConfigurationError, IntegrityError
from research_system.evals.calibration import calibrate_fixture
from research_system.evals.coverage import FOUNDATION_CASES, load_p0_coverage
from research_system.evals.harness import (
    build_release_decision,
    decide_p0_release,
    decision_document,
    run_all_scenarios,
    run_p0_coverage,
)
from research_system.evals.release_publication import (
    ReleasePublicationRequest,
    StoredReleasePublicationEvidence,
    content_artefact_id,
    verify_replayed_release,
)
from research_system.evals.release_snapshot import (
    build_release_snapshot_documents,
    rederive_release_from_snapshot,
)
from research_system.ids import new_id
from research_system.evals.retention import validate_retention_policy
from research_system.evals.retention_authorizer import (
    build_deletion_manifest_authorizer,
    load_evidence_store_registry,
)
from research_system.operations.backups import (
    ArtefactBinding,
    BackupArtefactInput,
    BackupMaterializer,
    BackupReceipt,
    verify_restore_before_writer_lease,
)
from research_system.operations.resources import TrustedRuntimeAuthority
from research_system.projection.replay import rebuild_projection, replay
from research_system.schema_registry import (
    SchemaRegistry,
    require_authority_schemas,
    runtime_schema_registry,
)
from research_system.store.identity import (
    canonical_restore_binding_output,
    load_store_manifest,
    manifest_schema_root,
    rebind_restored_store,
)
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


def _print_json(value: Any) -> None:
    print(canonical_bytes(jsonable(value)).decode("utf-8"))


def _authority_clock() -> datetime:
    return datetime.now(UTC)


def _registered_code_roots(roots: list[Path]) -> list[Path]:
    registered: set[Path] = set()
    for root in roots:
        resolved = root.resolve(strict=True)
        try:
            result = subprocess.run(  # nosec B603 B607 - fixed git argv
                ["git", "-C", str(resolved), "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConfigurationError(f"git worktree enumeration timed out for {resolved}") from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or "unknown git error"
            raise ConfigurationError(f"cannot enumerate git worktrees for {resolved}: {detail}")
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                registered.add(Path(line.removeprefix("worktree ")).resolve(strict=True))
    if not registered:
        raise ConfigurationError("at least one resolvable code root is required")
    return sorted(registered, key=str)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"JSON file must contain an object: {path}")
    return value


def _read_canonical_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"invalid canonical JSON file: {path}") from exc
    if not isinstance(value, dict) or raw != canonical_bytes(value):
        raise ConfigurationError(f"JSON file is not canonical: {path}")
    return value


def _read_yaml_or_json(path: Path, label: str) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigurationError(f"invalid {label} file: {path}") from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml

            value = yaml.safe_load(text)
        except (yaml.YAMLError, TypeError) as exc:
            raise ConfigurationError(f"invalid YAML or JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"{label} file must contain an object: {path}")
    return value


def _store_init(args: argparse.Namespace) -> int:
    if len(args.code_root) != 1:
        raise ConfigurationError("store init requires exactly one explicit code root for schema authority")
    explicit_root = args.code_root[0].resolve(strict=True)
    roots = _registered_code_roots(args.code_root)
    bootstrap_input = _read_json(args.authority_bootstrap)
    if (
        set(bootstrap_input)
        != {
            "schema_id",
            "schema_version",
            "approved_bootstrap_sha256",
            "manifest",
        }
        or bootstrap_input.get("schema_id") != "ars://core/authority-bootstrap-input"
        or bootstrap_input.get("schema_version") != "1.0.0"
    ):
        raise ConfigurationError("invalid authority bootstrap input")
    manifest = bootstrap_input["manifest"]
    approved = bootstrap_input["approved_bootstrap_sha256"]
    if not isinstance(manifest, dict) or not isinstance(approved, str):
        raise ConfigurationError("invalid authority bootstrap input")
    origin_root, _witness_path, origin_witness_sha256 = load_foundation_origin_pins(
        canonical_foundation_path(),
        project_id=args.project_id,
        initial_control_root=args.control_root,
    )
    identity = initialize_authority_control_store(
        roots,
        args.control_root,
        args.project_id,
        manifest,
        approved,
        canonical_schema_root=explicit_root / ".research-system" / "schemas",
        origin_authority_root=origin_root,
        approved_origin_witness_sha256=origin_witness_sha256,
    )
    _print_json(
        {
            "project_id": args.project_id,
            "store_identity": identity,
            "bootstrap_manifest_sha256": authority_bootstrap_sha256(manifest),
            "origin_witness_sha256": identity.witness.raw_sha256,
            "origin_witness_path": str(identity.witness_path),
        }
    )
    return 0


def _backup_receipt_from_json(value: dict[str, Any]) -> BackupReceipt:
    try:
        payload = dict(value)
        payload["schema_versions"] = tuple(payload["schema_versions"])
        payload["tool_versions"] = tuple(payload["tool_versions"])
        payload["artefact_bindings"] = tuple(ArtefactBinding(**item) for item in payload["artefact_bindings"])
        return BackupReceipt(**payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError("invalid backup receipt") from exc


_BACKUP_REQUEST_FIELDS = frozenset(
    {
        "command_id",
        "receipt_id",
        "receipt_revision",
        "submitted_at",
        "actor_id",
        "on_behalf_of_actor_id",
        "authority_grant_id",
        "idempotency_key",
        "correlation_id",
        "causation_id",
        "reason",
        "evidence_refs",
        "snapshot_id",
        "schema_versions",
        "tool_versions",
        "encryption_class",
        "redaction_class",
        "destination_class",
        "verified_at",
        "verified_by_actor_id",
        "verification_authority_grant_id",
        "external_artefacts",
    }
)
_BACKUP_ARTEFACT_FIELDS = frozenset(
    {
        "artefact_id",
        "source_path",
        "content_sha256",
        "availability",
        "availability_evidence_refs",
        "observed_at",
    }
)


def _store_backup(args: argparse.Namespace) -> int:
    """Create one governed event-first backup through the public CLI."""
    binding = ControlBinding.load(args.config)
    request = _read_json(args.request)
    if set(request) != _BACKUP_REQUEST_FIELDS:
        missing = sorted(_BACKUP_REQUEST_FIELDS - set(request))
        unexpected = sorted(set(request) - _BACKUP_REQUEST_FIELDS)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected: {', '.join(unexpected)}")
        raise ConfigurationError(f"invalid backup request fields ({'; '.join(details)})")
    raw_artefacts = request["external_artefacts"]
    if not isinstance(raw_artefacts, list) or not raw_artefacts:
        raise ConfigurationError("backup request external_artefacts must be a non-empty list")
    for field in ("evidence_refs", "schema_versions", "tool_versions"):
        if not isinstance(request[field], list):
            raise ConfigurationError(f"backup request {field} must be a list")
    for index, item in enumerate(raw_artefacts):
        if not isinstance(item, dict):
            raise ConfigurationError(f"backup request external_artefacts[{index}] must be an object")
        if set(item) != _BACKUP_ARTEFACT_FIELDS:
            missing = sorted(_BACKUP_ARTEFACT_FIELDS - set(item))
            unexpected = sorted(set(item) - _BACKUP_ARTEFACT_FIELDS)
            details = []
            if missing:
                details.append(f"missing: {', '.join(missing)}")
            if unexpected:
                details.append(f"unexpected: {', '.join(unexpected)}")
            raise ConfigurationError(
                f"invalid backup request external_artefacts[{index}] fields ({'; '.join(details)})"
            )
        if not isinstance(item["availability_evidence_refs"], list):
            raise ConfigurationError(
                f"backup request external_artefacts[{index}].availability_evidence_refs must be a list"
            )
    try:
        artefacts = tuple(
            BackupArtefactInput(
                artefact_id=item["artefact_id"],
                source_path=Path(item["source_path"]),
                content_sha256=item["content_sha256"],
                availability=item["availability"],
                availability_evidence_refs=tuple(item["availability_evidence_refs"]),
                observed_at=item["observed_at"],
            )
            for item in raw_artefacts
        )
        schema_versions = tuple(request["schema_versions"])
        tool_versions = tuple(request["tool_versions"])
        evidence_refs = list(request["evidence_refs"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError("invalid backup request") from exc

    source_root = binding.control_root.resolve(strict=True)
    destination_root = args.destination_root
    if not destination_root.is_absolute():
        raise ConfigurationError("backup destination root must be absolute")
    destination_root = destination_root.resolve(strict=False)
    stage_root = destination_root.parent / f".{destination_root.name}.{request['command_id']}.stage"
    schemas = runtime_schema_registry(binding.schema_root)
    registry = load_evidence_store_registry(args.registry, schemas)
    materializer = BackupMaterializer(
        command_id=request["command_id"],
        source_root=source_root,
        destination_root=destination_root,
        stage_root=stage_root,
        receipt_id=request["receipt_id"],
        receipt_revision=request["receipt_revision"],
        registry=registry,
        artefacts=artefacts,
        verified_at=request["verified_at"],
        verified_by_actor_id=request["verified_by_actor_id"],
        verification_authority_grant_id=request["verification_authority_grant_id"],
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    ledger = EventLedger(source_root, binding.project_id, schemas)
    snapshot = ledger.snapshot()
    payload = materializer.derive_event_payload(
        snapshot_id=request["snapshot_id"],
        destination_class=request["destination_class"],
        schema_versions=schema_versions,
        tool_versions=tool_versions,
        encryption_class=request["encryption_class"],
        redaction_class=request["redaction_class"],
        ledger_snapshot=snapshot,
    )
    committed = [
        event
        for event in snapshot.events
        if event.get("command_id") == request["command_id"] and event.get("command_type") == "CreateBackup"
    ]
    if len(committed) > 1:
        raise IntegrityError("backup command has multiple committed events")
    expected_stream_version = (
        int(committed[0]["stream_version"]) - 1 if committed else snapshot.stream_versions.get(binding.project_id, 0)
    )
    command = {
        "command_id": request["command_id"],
        "command_type": "CreateBackup",
        "schema_id": "ars://core/command/CreateBackup",
        "schema_version": "1.0.0",
        "submitted_at": request["submitted_at"],
        "actor_id": request["actor_id"],
        "on_behalf_of_actor_id": request["on_behalf_of_actor_id"],
        "authority_grant_id": request["authority_grant_id"],
        "target_stream_id": binding.project_id,
        "expected_stream_version": expected_stream_version,
        "idempotency_key": request["idempotency_key"],
        "correlation_id": request["correlation_id"],
        "causation_id": request["causation_id"],
        "reason": request["reason"],
        "evidence_refs": evidence_refs,
        "payload": payload,
        "project_id": binding.project_id,
    }
    receipt = CommandService(
        source_root,
        ledger,
        ObjectStore(source_root),
        ReceiptStore(source_root),
        schemas,
        authority_resolver=LedgerAuthorityGrantResolver(
            source_root,
            binding.project_id,
            binding.store_identity,
            schemas,
            approved_witness=binding.origin_witness,
            approved_witness_path=binding.origin_witness_path,
        ),
        clock=_authority_clock,
        backup_materializer=materializer,
    ).submit(command)
    if receipt.status != "accepted":
        _print_json(
            {
                "status": receipt.status,
                "command_receipt": asdict(receipt),
                "destination_root": str(destination_root),
            }
        )
        return 0
    backup_receipt_path = destination_root / "manifests" / "backup-receipt.json"
    backup_receipt = _backup_receipt_from_json(_read_json(backup_receipt_path))
    _print_json(
        {
            "status": receipt.status,
            "command_receipt": asdict(receipt),
            "backup_receipt": asdict(backup_receipt),
            "destination_root": str(destination_root),
            "backup_receipt_path": str(backup_receipt_path),
            "snapshot_path": str(destination_root / "snapshots" / f"{backup_receipt.snapshot_id}.json"),
        }
    )
    return 0


def _load_canonical_approved_binding(path: Path) -> ApprovedProjectBinding:
    canonical = canonical_foundation_path().resolve(strict=False)
    supplied = path.resolve(strict=False)
    if supplied != canonical:
        raise ConfigurationError("restore binding requires the canonical foundation config")
    return ApprovedProjectBinding.load(canonical)


def _publish_exact_file(path: Path, data: bytes) -> None:
    if path.exists():
        if not path.is_file() or path.read_bytes() != data:
            raise ArsError(f"output path exists with foreign content: {path}")
        return
    if not path.parent.is_dir():
        raise ArsError(f"output directory is unavailable: {path.parent}")
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as exc:
        raise ArsError(f"output path is unavailable: {path}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _store_restore_bind(args: argparse.Namespace) -> int:
    target_root = args.control_root.resolve(strict=True)
    requested_source = args.source_root.resolve(strict=True)
    approved = _load_canonical_approved_binding(args.foundation_config)
    if requested_source != approved.control_root:
        raise ConfigurationError("restore source root differs from canonical approved control root")
    schema_root = args.schema_root.resolve(strict=True)
    if schema_root != approved.schema_root:
        raise ConfigurationError("caller schema root differs from approved project binding")
    schemas = require_authority_schemas(runtime_schema_registry(approved.schema_root))
    receipt = _backup_receipt_from_json(_read_canonical_json(args.receipt))
    if receipt.project_id != approved.project_id:
        raise ConfigurationError("backup receipt project differs from approved project binding")
    if receipt.store_identity != approved.store_identity:
        raise ArsError("restored store identity differs from backup receipt")
    if receipt.source_endpoint_scheme != approved.endpoint_scheme:
        raise ConfigurationError("backup receipt endpoint differs from approved project binding")
    snapshot = _read_canonical_json(args.snapshot)
    _read_canonical_json(args.endpoint_ownership)
    _read_canonical_json(args.artefact_manifest)
    _read_canonical_json(args.registry)
    expected_output = canonical_restore_binding_output(
        target_root,
        approved.project_id,
        approved.store_identity,
        approved.code_roots,
        approved.schema_root,
    )
    registry = load_evidence_store_registry(args.registry, schemas)
    preflight = verify_restore_before_writer_lease(
        target_root=target_root,
        receipt=receipt,
        snapshot_path=args.snapshot,
        endpoint_ownership_path=args.endpoint_ownership,
        artefact_manifest_path=args.artefact_manifest,
        registry=registry,
        actor_id=args.actor_id,
        authority_grant_id=args.authority_grant_id,
        approved_witness=approved.origin_witness,
        approved_witness_path=approved.origin_witness_path,
    )
    if preflight.status != "verified":
        raise ArsError(f"restore preflight is not verified: {', '.join(preflight.failed_predicates)}")
    preflight_value = asdict(preflight)
    result = rebind_restored_store(
        target_root,
        requested_source,
        expected_project_id=approved.project_id,
        expected_store_identity=approved.store_identity,
        expected_code_roots=list(approved.code_roots),
        expected_schema_root=approved.schema_root,
        expected_restore_receipt_hash=receipt.receipt_hash,
        actor_id=args.actor_id,
        authority_grant_id=args.authority_grant_id,
        source_snapshot=snapshot,
        expected_source_snapshot_hash=preflight.source_snapshot_hash,
        expected_target_manifest_bytes_sha256=preflight.target_manifest_bytes_sha256,
        expected_output=expected_output,
        expected_restore_preflight=preflight_value,
        approved_witness=approved.origin_witness,
        approved_witness_path=approved.origin_witness_path,
    )
    _publish_exact_file(args.config_output, expected_output)
    _print_json(
        {
            "status": "bound",
            "transaction_state": "cleared",
            "control_root": str(target_root),
            "project_id": approved.project_id,
            "store_identity": approved.store_identity,
            "origin_witness_sha256": approved.origin_witness_sha256,
            "config": str(args.config_output.resolve(strict=False)),
            "config_sha256": sha256_hex(expected_output),
            "manifest_hash": result["manifest_hash"],
            "preflight_result_hash": preflight.result_hash,
        }
    )
    return 0


def _command_submit_runtime_authority_provider(
    binding: ControlBinding,
    host_identity: str | None,
    boot_identity: str | None,
) -> Callable[[], TrustedRuntimeAuthority] | None:
    if host_identity is None and boot_identity is None:
        return None
    if host_identity is None or boot_identity is None:
        raise ConfigurationError("command submit requires --host-identity and --boot-identity together")
    try:
        TrustedRuntimeAuthority(
            host_identity=host_identity,
            boot_identity=boot_identity,
            control_store_identity=binding.store_identity,
            store_manifest_sha256="0" * 64,
        )
    except ValueError as exc:
        raise ConfigurationError("command submit runtime authority identities are invalid") from exc

    def provider() -> TrustedRuntimeAuthority:
        manifest = load_store_manifest(
            binding.control_root,
            approved_witness=binding.origin_witness,
            approved_witness_path=binding.origin_witness_path,
        )
        if manifest.get("project_id") != binding.project_id:
            raise ConfigurationError("current store manifest project differs from the selected control binding")
        if manifest.get("store_identity") != binding.store_identity:
            raise ConfigurationError("current store manifest store identity differs from the selected control binding")
        return TrustedRuntimeAuthority(
            host_identity=host_identity,
            boot_identity=boot_identity,
            control_store_identity=binding.store_identity,
            store_manifest_sha256=sha256_hex(canonical_bytes(manifest)),
        )

    return provider


def _command_submit(args: argparse.Namespace) -> int:
    binding = ControlBinding.load(args.config)
    trusted_runtime_authority_provider = _command_submit_runtime_authority_provider(
        binding,
        args.host_identity,
        args.boot_identity,
    )
    command = _read_json(args.command)
    schemas = runtime_schema_registry(binding.schema_root)
    ledger = EventLedger(binding.control_root, binding.project_id, schemas)
    service = CommandService(
        binding.control_root,
        ledger,
        ObjectStore(binding.control_root),
        ReceiptStore(binding.control_root),
        schemas,
        authority_resolver=LedgerAuthorityGrantResolver(
            binding.control_root,
            binding.project_id,
            binding.store_identity,
            schemas,
            approved_witness=binding.origin_witness,
            approved_witness_path=binding.origin_witness_path,
        ),
        clock=_authority_clock,
        trusted_runtime_authority_provider=trusted_runtime_authority_provider,
    )
    if args.evidence_store_registry is not None:
        registry = load_evidence_store_registry(args.evidence_store_registry, schemas)
        retention_policy_path = binding.schema_root.parent / "evals" / "retention-policy.yaml"
        service.deletion_manifest_authorizer = build_deletion_manifest_authorizer(
            registry,
            retention_policy_path=retention_policy_path,
        )
    _print_json(asdict(service.submit(command)))
    return 0


def _assurance_record_write(args: argparse.Namespace) -> int:
    binding = ControlBinding.load(args.config)
    record = _read_json(args.record)
    receipt = ExternalAssuranceRecordStore(binding).write(
        record_class=args.record_class,
        record_id=args.record_id,
        revision=args.revision,
        expected_previous_revision=args.expected_previous_revision,
        record=record,
        publication_context=ExternalRecordPublicationContext(
            caller_actor_id=args.caller_actor_id,
            caller_actor_class=args.caller_actor_class,
            authority_grant_id=args.authority_grant_id,
            record_action=args.record_action,
            record_class=args.record_class,
            record_id=args.record_id,
            revision=args.revision,
            expected_previous_revision=args.expected_previous_revision,
            project_id=args.project_id,
            store_identity=args.store_identity,
            authority_root=args.authority_root,
            canonical_sha256=args.canonical_sha256,
            task_id=args.task_id,
            session_id=args.session_id,
            relationship_record_id=args.relationship_record_id,
            required_risk=args.required_risk,
            occurred_at=args.occurred_at,
        ),
    )
    _print_json(asdict(receipt))
    return 0


def _assurance_relationship_facts_publish(args: argparse.Namespace) -> int:
    binding = ControlBinding.load(args.config)
    source = _read_yaml_or_json(args.facts, "relationship-facts input")
    try:
        protected = source["protected_relationship"]
        publication = source["publication_context"]
        publish_kwargs = {
            "relationship_evidence_facts_id": source["relationship_evidence_facts_id"],
            "revision": source["revision"],
            "expected_previous_revision": source["expected_previous_revision"],
            "relationship_scope": source["relationship_scope"],
            "protected_relationship": ProtectedRelationshipReference(
                relationship_record_id=protected["relationship_record_id"],
                revision=protected["revision"],
                canonical_sha256=protected["canonical_sha256"],
                relationship_context=protected["relationship_context"],
                grade=protected["grade"],
                effective_at=protected["effective_at"],
                expires_at=protected["expires_at"],
            ),
            "reviewed_subject": source["reviewed_subject"],
            "producer": RelationshipEvidenceParticipant(**source["producer"]),
            "reviewer": RelationshipEvidenceParticipant(**source["reviewer"]),
            "evidence_author_actor_id": source["evidence_author_actor_id"],
            "producer_conclusions_visibility": source["producer_conclusions_visibility"],
            "reviewed_at": source["reviewed_at"],
            "publication_context": ExternalRecordPublicationContext(**publication),
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError("malformed relationship-facts input") from exc
    receipt = RelationshipEvidenceFactsStore(binding).publish(**publish_kwargs)
    _print_json(asdict(receipt))
    return 0


def _assurance_pack_locator(value: str) -> tuple[str, SemanticRecordLocator]:
    """Parse one required semantic-to-opaque-record locator argument."""

    semantic, separator, address = value.partition("=")
    record_class, class_separator, record_id = address.rpartition(":")
    if not separator or not semantic or not class_separator or not record_class or not record_id:
        raise ConfigurationError("--record-locator must be SEMANTIC=RECORD_CLASS:RECORD_ID")
    return semantic, SemanticRecordLocator(record_class, record_id)


def _assurance_pack_run(args: argparse.Namespace) -> int:
    locators: dict[str, SemanticRecordLocator] = {}
    for raw_locator in args.record_locator:
        semantic, locator = _assurance_pack_locator(raw_locator)
        if semantic in locators:
            raise ConfigurationError(f"duplicate assurance-pack semantic locator: {semantic}")
        locators[semantic] = locator
    try:
        evaluation_time = datetime.fromisoformat(args.evaluation_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigurationError("--evaluation-time must be an RFC 3339 timestamp") from exc
    config = AssurancePackRunnerConfig.load(args.config, repository_root=Path.cwd())
    runner = prepare_assurance_pack if args.phase == "prepare" else accept_assurance_pack
    result = runner(
        config=config,
        candidate_path=args.candidate,
        evaluation_time=evaluation_time,
        run_id=args.run_id,
        record_locators=locators,
    )
    output = asdict(result)
    output["evidence_path"] = str(result.evidence_path)
    _print_json(output)
    return 0


def _verified_ledger(
    control_root: Path,
) -> tuple[
    EventLedger,
    SchemaRegistry,
    LedgerAuthorityGrantResolver,
]:
    approved = ApprovedProjectBinding.load(canonical_foundation_path())
    manifest = load_store_manifest(
        control_root,
        approved_witness=approved.origin_witness,
        approved_witness_path=approved.origin_witness_path,
    )
    schemas = _schemas_for_store_manifest(manifest)
    resolved_root = control_root.resolve(strict=True)
    return (
        EventLedger(resolved_root, manifest["project_id"], schemas),
        schemas,
        LedgerAuthorityGrantResolver(
            resolved_root,
            manifest["project_id"],
            manifest["store_identity"],
            schemas,
            approved_witness=approved.origin_witness,
            approved_witness_path=approved.origin_witness_path,
        ),
    )


def _replay_verify(args: argparse.Namespace) -> int:
    ledger, schemas, resolver = _verified_ledger(args.control_root)
    _print_json(
        replay(
            ledger.iter_events(),
            schema_registry=schemas,
            authority_state_validator=resolver.validate_replayed_administration_state,
        )
    )
    return 0


def _projection_rebuild(args: argparse.Namespace) -> int:
    control_root = args.control_root.resolve(strict=True)
    output = args.output.resolve(strict=False)
    if output == control_root or control_root in output.parents:
        raise ArsError("projection output must be external to canonical control root")
    approved = ApprovedProjectBinding.load(canonical_foundation_path())
    manifest = load_store_manifest(
        control_root,
        approved_witness=approved.origin_witness,
        approved_witness_path=approved.origin_witness_path,
    )
    projection_roots = [Path(root) / ".research-system" / "projections" for root in manifest["code_roots"]]
    if not any(output == root or root in output.parents for root in projection_roots):
        raise ArsError("projection output must use an ARS namespaced projection root")
    schemas = _schemas_for_store_manifest(manifest)
    ledger = EventLedger(control_root, manifest["project_id"], schemas)
    resolver = LedgerAuthorityGrantResolver(
        control_root,
        manifest["project_id"],
        manifest["store_identity"],
        schemas,
        approved_witness=approved.origin_witness,
        approved_witness_path=approved.origin_witness_path,
    )
    state = rebuild_projection(
        ledger.iter_events(),
        output,
        schemas,
        resolver.validate_replayed_administration_state,
    )
    _print_json(state)
    return 0


def _eval_retention_validate(args: argparse.Namespace) -> int:
    policy = validate_retention_policy(args.policy)
    _print_json({"policy_revision": policy["policy_revision"], "rules": len(policy["rules"])})
    return 0


def _eval_roots(coverage: Path) -> tuple[Path, Path]:
    try:
        eval_root = coverage.resolve(strict=True).parent
    except OSError as exc:
        raise ConfigurationError(f"invalid coverage file: {coverage}") from exc
    return eval_root / "fixtures", eval_root.parent / "schemas"


def _eval_validate(args: argparse.Namespace) -> int:
    import yaml

    try:
        catalogue = yaml.safe_load(args.catalogue.read_text(encoding="utf-8"))
        coverage_manifest = catalogue["coverage_manifest"]
        if not isinstance(coverage_manifest, str):
            raise TypeError
    except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
        raise ConfigurationError(f"invalid evaluation catalogue: {args.catalogue}") from exc
    coverage_path = args.catalogue.parent / coverage_manifest
    fixtures, schemas = _eval_roots(coverage_path)
    coverage = load_p0_coverage(coverage_path, fixture_root=fixtures, schema_root=schemas)
    _print_json({"status": "valid", "fixture_count": len(coverage.selected_fixture_revisions)})
    return 0


def _eval_calibrate(args: argparse.Namespace) -> int:
    if args.transport != "fake":
        raise ArsError("P0 calibration requires fake transport")
    fixtures, schemas = _eval_roots(args.coverage)
    load_p0_coverage(args.coverage, fixture_root=fixtures, schema_root=schemas)
    records = [calibrate_fixture(item, fixture_root=fixtures) for item in sorted(FOUNDATION_CASES)]
    blocked = sum(record.blocking_verdict is not None for record in records)
    mutations_uncalibrated = sum(
        record.mutation_calibration_status != "calibrated" and bool(record.declared_mutation_ids) for record in records
    )
    _print_json(
        {
            "fixture_count": len(records),
            "blocked_fixture_count": blocked,
            "mutation_calibration": ("calibrated" if mutations_uncalibrated == 0 else "incomplete"),
            "fixtures_with_uncalibrated_mutations": mutations_uncalibrated,
        }
    )
    return 0


def _eval_run(args: argparse.Namespace) -> int:
    if args.transport != "fake":
        raise ArsError("P0 execution requires fake transport")
    fixtures, schemas = _eval_roots(args.coverage)
    evidence = run_p0_coverage(args.coverage, fixture_root=fixtures, schema_root=schemas)
    assessment = decide_p0_release(evidence)
    output: Path | None = args.output
    if output is None:
        _print_json({"candidate_status": assessment["decision"], "result_count": len(evidence.results)})
        return 0
    if output.exists():
        raise ArsError(f"output path exists: {output}")
    scenario_results = run_all_scenarios()
    record, _outcome = build_release_decision(evidence, scenario_results)
    document = decision_document(record)
    SchemaRegistry(schemas).validate("ars://evals/release-gate-decision", document)
    data = canonical_bytes(document)
    try:
        with output.open("xb") as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise ArsError(f"output path exists: {output}") from exc
    _print_json(
        {
            "candidate_status": assessment["decision"],
            "result_count": len(evidence.results),
            "output": str(output),
        }
    )
    return 0


def _schemas_for_store_manifest(
    manifest: dict[str, Any],
) -> SchemaRegistry:
    try:
        persisted = manifest_schema_root(manifest)
    except IntegrityError as exc:
        raise ConfigurationError(str(exc)) from exc
    if persisted is not None:
        if not persisted.is_dir():
            raise ConfigurationError("store manifest schema root is missing")
        try:
            registry = runtime_schema_registry(persisted)
            return require_authority_schemas(registry)
        except ArsError as exc:
            raise ConfigurationError("store manifest schema root is unusable") from exc
    candidates = [Path(root) / ".research-system" / "schemas" for root in manifest.get("code_roots", [])]
    existing = [
        path.resolve(strict=True)
        for path in candidates
        if (path.is_dir() and (path / "core" / "release-gate-decision-published.schema.json").is_file())
    ]
    if not existing:
        raise ConfigurationError("store manifest does not bind a usable runtime schema root")
    unique = sorted(set(existing), key=str)
    if len(unique) != 1:
        raise ConfigurationError("store manifest has ambiguous schema roots")
    registry = runtime_schema_registry(unique[0])
    return require_authority_schemas(registry)


def _rederive_bound_decision(
    binding: ControlBinding,
    source: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    coverage_path = binding.schema_root.parent / "evals" / "p0-coverage.yaml"
    fixtures, schemas = _eval_roots(coverage_path)
    evidence = run_p0_coverage(
        coverage_path,
        fixture_root=fixtures,
        schema_root=schemas,
    )
    record, _ = build_release_decision(
        evidence,
        run_all_scenarios(),
        decided_at=str(source["decided_at"]),
        release_gate_decision_id=str(source["release_gate_decision_id"]),
    )
    return decision_document(record), evidence.coverage.gate5_authorized


def _publication_evidence(
    binding: ControlBinding,
    source: dict[str, Any],
) -> tuple[StoredReleasePublicationEvidence, str, str]:
    schemas = runtime_schema_registry(binding.schema_root)
    resolver = LedgerAuthorityGrantResolver(
        binding.control_root,
        binding.project_id,
        binding.store_identity,
        schemas,
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    existing_projection = replay(
        EventLedger(binding.control_root, binding.project_id, schemas).iter_events(),
        schema_registry=schemas,
        authority_state_validator=resolver.validate_replayed_administration_state,
    )
    existing = existing_projection.get("release_decisions", {}).get(source["release_gate_decision_id"])
    if isinstance(existing, dict):
        resolver = StoredReleasePublicationEvidence(
            objects=ObjectStore(binding.control_root),
            expected_store_identity=binding.store_identity,
            rederive=rederive_release_from_snapshot,
        )
        manifest_ref = existing["evaluation_runs_manifest_ref"]
        control_ref = existing["control_binding_ref"]
        manifest = resolver.resolve_evaluation_runs(manifest_ref)
        control = resolver.resolve_control_binding(control_ref)
        schemas.validate("ars://evals/release-publication-evidence", manifest)
        schemas.validate("ars://evals/release-control-binding", control)
        derived, gate5_authorized = resolver.rederive_release_decision(
            manifest,
            control,
        )
        if gate5_authorized is not False:
            raise ArsError("stored publication evidence differs from source")
        if derived == source:
            return resolver, manifest_ref, control_ref
    coverage_path = binding.schema_root.parent / "evals" / "p0-coverage.yaml"
    fixtures, schemas_root = _eval_roots(coverage_path)
    producer_evidence = run_p0_coverage(
        coverage_path,
        fixture_root=fixtures,
        schema_root=schemas_root,
    )
    scenarios = run_all_scenarios()
    record, _ = build_release_decision(
        producer_evidence,
        scenarios,
        decided_at=str(source["decided_at"]),
        release_gate_decision_id=str(source["release_gate_decision_id"]),
    )
    if decision_document(record) != source:
        raise ArsError("publication source differs from producer evidence")
    manifest, control = build_release_snapshot_documents(
        producer_evidence,
        scenarios,
        source,
        project_id=binding.project_id,
        store_identity=binding.store_identity,
    )
    schemas.validate("ars://evals/release-publication-evidence", manifest)
    schemas.validate("ars://evals/release-control-binding", control)
    manifest_ref = content_artefact_id(manifest)
    control_ref = content_artefact_id(control)
    objects = ObjectStore(binding.control_root)
    objects.write("artefact", manifest_ref, 1, manifest)
    objects.write("artefact", control_ref, 1, control)

    resolver = StoredReleasePublicationEvidence(
        objects=objects,
        expected_store_identity=binding.store_identity,
        rederive=rederive_release_from_snapshot,
    )
    return resolver, manifest_ref, control_ref


def _reserve_output(output: Path) -> tuple[Path, int]:
    """Reserve a same-directory temporary without creating the final path."""
    if output.exists():
        raise ArsError(f"output path exists: {output}")
    parent = output.parent
    if not parent.is_dir():
        raise ArsError(f"output directory is unavailable: {parent}")
    temporary = parent / f".{output.name}.{new_id('command')}.tmp"
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except OSError as exc:
        raise ArsError(f"output path is unavailable: {output}") from exc
    return temporary, descriptor


def _after_receipt_output_fsync(_temporary: Path) -> None:
    """Test seam after durable temporary output and before publication."""


def _publish_reserved_output(
    output: Path,
    temporary: Path,
    descriptor: int,
    data: bytes,
) -> None:
    """Durably write then atomically link a receipt without clobbering."""
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    _after_receipt_output_fsync(temporary)
    try:
        os.link(temporary, output)
    except FileExistsError as exc:
        raise ArsError(f"output path exists: {output}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _eval_publish_release(args: argparse.Namespace) -> int:
    binding = ControlBinding.load(args.config)
    source = _read_json(args.evaluation_runs)
    schemas = runtime_schema_registry(binding.schema_root)
    schemas.validate("ars://evals/release-gate-decision", source)
    if source.get("canonical_event_ref") != "unpublished:p0":
        raise ArsError("publication requires unpublished:p0 source evidence")
    output = args.output
    temporary, descriptor = _reserve_output(output)
    try:
        evidence, manifest_ref, control_ref = _publication_evidence(binding, source)
        authority = LedgerAuthorityGrantResolver(
            binding.control_root,
            binding.project_id,
            binding.store_identity,
            schemas,
            approved_witness=binding.origin_witness,
            approved_witness_path=binding.origin_witness_path,
        )
        resolution = authority.grant_identity(args.authority_grant_id)
        idempotency_key = f"release-publication:{source['release_gate_decision_id']}"
        request = ReleasePublicationRequest.from_dict(
            {
                "schema": "ars://evals/release-publication-request",
                "project_id": binding.project_id,
                "release_decision_id": source["release_gate_decision_id"],
                "evaluation_runs_manifest_ref": manifest_ref,
                "control_binding_ref": control_ref,
                "publication_authority_grant_id": args.authority_grant_id,
                "publication_authority_sha256": (resolution.authority_grant_sha256),
                "idempotency_key": idempotency_key,
            }
        )
        command = {
            "command_id": new_id("command"),
            "command_type": "PublishReleaseGateDecision",
            "schema_id": "ars://core/command",
            "schema_version": "1.0.0",
            "submitted_at": _authority_clock().isoformat().replace("+00:00", "Z"),
            "actor_id": args.actor_id,
            "on_behalf_of_actor_id": None,
            "authority_grant_id": args.authority_grant_id,
            "target_stream_id": source["release_gate_decision_id"],
            "expected_stream_version": 0,
            "idempotency_key": idempotency_key,
            "correlation_id": idempotency_key,
            "causation_id": None,
            "reason": "record the verified blocked P0 release decision",
            "evidence_refs": [manifest_ref, control_ref],
            "payload": request.to_dict(),
        }
        ledger = EventLedger(binding.control_root, binding.project_id, schemas)
        receipt = CommandService(
            binding.control_root,
            ledger,
            ObjectStore(binding.control_root),
            ReceiptStore(binding.control_root),
            schemas,
            authority_resolver=authority,
            release_publication_evidence=evidence,
            clock=_authority_clock,
        ).submit(command)
        reserved_descriptor = descriptor
        descriptor = -1
        _publish_reserved_output(
            output,
            temporary,
            reserved_descriptor,
            canonical_bytes(jsonable(asdict(receipt))),
        )
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    _print_json(asdict(receipt))
    return 0


def _eval_release(args: argparse.Namespace) -> int:
    if args.config is None:
        raise ArsError("eval release requires canonical control binding")
    binding = ControlBinding.load(args.config)
    supplied = _read_json(args.evaluation_runs)
    supplied_document = supplied.get("decision_document", supplied)
    if not isinstance(supplied_document, dict):
        raise ConfigurationError("evaluation runs require a decision document")
    schema_registry = runtime_schema_registry(binding.schema_root)
    schema_registry.validate("ars://evals/release-gate-decision", supplied_document)
    if supplied_document.get("canonical_event_ref") == "unpublished:p0":
        raise ArsError("eval release requires a canonical published event reference")
    ledger = EventLedger(binding.control_root, binding.project_id, schema_registry)
    authority_resolver = LedgerAuthorityGrantResolver(
        binding.control_root,
        binding.project_id,
        binding.store_identity,
        schema_registry,
        approved_witness=binding.origin_witness,
        approved_witness_path=binding.origin_witness_path,
    )
    projection = replay(
        ledger.iter_events(),
        schema_registry=schema_registry,
        authority_state_validator=authority_resolver.validate_replayed_administration_state,
    )
    decision_id = supplied_document["release_gate_decision_id"]
    projected = projection.get("release_decisions", {}).get(decision_id)
    if not isinstance(projected, dict):
        raise ArsError("canonical release event is unavailable")
    resolver = StoredReleasePublicationEvidence(
        ObjectStore(binding.control_root),
        binding.store_identity,
        rederive_release_from_snapshot,
    )
    manifest = resolver.resolve_evaluation_runs(projected["evaluation_runs_manifest_ref"])
    control = resolver.resolve_control_binding(projected["control_binding_ref"])
    fresh_document, gate5_authorized = resolver.rederive_release_decision(
        manifest,
        control,
    )
    source_document = dict(supplied_document)
    source_document["canonical_event_ref"] = "unpublished:p0"
    if gate5_authorized is not False or fresh_document != source_document:
        raise ArsError("evaluation document divergence")
    record = verify_replayed_release(
        supplied_document,
        fresh_document,
        projection,
        binding.project_id,
        resolver,
        schema_registry,
    )
    _print_json(
        {
            "decision": "blocked",
            "gate5_authorized": False,
            "candidate_status": "blocked",
            "canonical_event_ref": record["event_id"],
        }
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ars")
    groups = parser.add_subparsers(dest="group", required=True)

    store = groups.add_parser("store")
    store_commands = store.add_subparsers(dest="store_command", required=True)
    init = store_commands.add_parser("init")
    init.add_argument("--code-root", type=Path, action="append", required=True)
    init.add_argument("--control-root", type=Path, required=True)
    init.add_argument("--project-id", required=True)
    init.add_argument("--authority-bootstrap", type=Path, required=True)
    init.set_defaults(handler=_store_init)

    backup = store_commands.add_parser("backup")
    backup.add_argument("--config", type=Path, required=True)
    backup.add_argument("--request", type=Path, required=True)
    backup.add_argument("--registry", type=Path, required=True)
    backup.add_argument("--destination-root", type=Path, required=True)
    backup.set_defaults(handler=_store_backup)

    restore_bind = store_commands.add_parser("restore-bind")
    restore_bind.add_argument("--control-root", type=Path, required=True)
    restore_bind.add_argument("--source-root", type=Path, required=True)
    restore_bind.add_argument("--receipt", type=Path, required=True)
    restore_bind.add_argument("--snapshot", type=Path, required=True)
    restore_bind.add_argument("--endpoint-ownership", type=Path, required=True)
    restore_bind.add_argument("--artefact-manifest", type=Path, required=True)
    restore_bind.add_argument("--registry", type=Path, required=True)
    restore_bind.add_argument("--actor-id", required=True)
    restore_bind.add_argument("--authority-grant-id", required=True)
    restore_bind.add_argument("--foundation-config", type=Path, required=True)
    restore_bind.add_argument("--schema-root", type=Path, required=True)
    restore_bind.add_argument("--config-output", type=Path, required=True)
    restore_bind.set_defaults(handler=_store_restore_bind)

    command = groups.add_parser("command")
    command_actions = command.add_subparsers(dest="command_action", required=True)
    submit = command_actions.add_parser("submit")
    submit.add_argument("--config", type=Path, required=True)
    submit.add_argument("--command", type=Path, required=True)
    submit.add_argument("--host-identity", default=None)
    submit.add_argument("--boot-identity", default=None)
    submit.add_argument("--evidence-store-registry", type=Path, default=None)
    submit.set_defaults(handler=_command_submit)

    assurance_record = groups.add_parser("assurance-record")
    assurance_record_actions = assurance_record.add_subparsers(dest="assurance_record_action", required=True)
    write_record = assurance_record_actions.add_parser("write")
    write_record.add_argument("--config", type=Path, required=True)
    write_record.add_argument("--record-class", required=True)
    write_record.add_argument("--record-id", required=True)
    write_record.add_argument("--revision", type=int, required=True)
    write_record.add_argument("--expected-previous-revision", type=int, required=True)
    write_record.add_argument("--record", type=Path, required=True)
    write_record.add_argument("--caller-actor-id", required=True)
    write_record.add_argument("--caller-actor-class", choices=("human", "agent", "service"), required=True)
    write_record.add_argument("--authority-grant-id", required=True)
    write_record.add_argument("--record-action", choices=("create", "revise"), required=True)
    write_record.add_argument("--project-id", required=True)
    write_record.add_argument("--store-identity", required=True)
    write_record.add_argument("--authority-root", required=True)
    write_record.add_argument("--canonical-sha256", required=True)
    write_record.add_argument("--task-id", required=True)
    write_record.add_argument("--session-id", required=True)
    write_record.add_argument("--relationship-record-id", default=None)
    write_record.add_argument("--required-risk", choices=("R0", "R1", "R2", "R3"), required=True)
    write_record.add_argument("--occurred-at", required=True)
    write_record.set_defaults(handler=_assurance_record_write)

    assurance_pack = groups.add_parser(
        "assurance-pack",
        help="prepare or authorize consumption of the TDL_private assurance pack",
    )
    assurance_pack_actions = assurance_pack.add_subparsers(dest="assurance_pack_action", required=True)
    assurance_pack_run = assurance_pack_actions.add_parser(
        "run",
        help="run the read-only two-phase assurance-pack coordinator",
    )
    assurance_pack_run.add_argument("--config", type=Path, required=True, help="verified ControlBinding JSON")
    assurance_pack_run.add_argument("--candidate", type=Path, required=True, help="candidate pack path")
    assurance_pack_run.add_argument(
        "--evaluation-time",
        required=True,
        help="UTC RFC 3339 evaluation time, for example 2026-08-03T12:00:00Z",
    )
    assurance_pack_run.add_argument("--run-id", required=True, help="immutable evaluation-run identity")
    assurance_pack_run.add_argument(
        "--phase",
        choices=("prepare", "acceptance"),
        required=True,
        help="phase to execute; acceptance reloads preparation and authorizes consumption",
    )
    assurance_pack_run.add_argument(
        "--record-locator",
        action="append",
        required=True,
        metavar="SEMANTIC=RECORD_CLASS:RECORD_ID",
        help="opaque semantic record locator; repeat for every required authority record",
    )
    assurance_pack_run.set_defaults(handler=_assurance_pack_run)
    relationship_facts = assurance_pack_actions.add_parser(
        "publish-relationship-facts",
        help="publish governed YAML or JSON relationship-evidence facts consumed by the assurance-pack runner",
    )
    relationship_facts.add_argument("--config", type=Path, required=True, help="verified ControlBinding JSON")
    relationship_facts.add_argument(
        "--facts",
        type=Path,
        required=True,
        help="YAML or JSON input containing protected relationship, concrete provenance, and publication context",
    )
    relationship_facts.set_defaults(handler=_assurance_relationship_facts_publish)

    replay_parser = groups.add_parser("replay")
    replay_actions = replay_parser.add_subparsers(dest="replay_action", required=True)
    verify = replay_actions.add_parser("verify")
    verify.add_argument("--control-root", type=Path, required=True)
    verify.set_defaults(handler=_replay_verify)

    projection = groups.add_parser("projection")
    projection_actions = projection.add_subparsers(dest="projection_action", required=True)
    rebuild = projection_actions.add_parser("rebuild")
    rebuild.add_argument("--control-root", type=Path, required=True)
    rebuild.add_argument("--output", type=Path, required=True)
    rebuild.set_defaults(handler=_projection_rebuild)

    evaluation = groups.add_parser("eval")
    evaluation_actions = evaluation.add_subparsers(dest="eval_action", required=True)
    validate_eval = evaluation_actions.add_parser("validate")
    validate_eval.add_argument("--catalogue", type=Path, required=True)
    validate_eval.set_defaults(handler=_eval_validate)

    calibrate = evaluation_actions.add_parser("calibrate")
    calibrate.add_argument("--coverage", type=Path, required=True)
    calibrate.add_argument("--transport", required=True)
    calibrate.set_defaults(handler=_eval_calibrate)

    run = evaluation_actions.add_parser("run")
    run.add_argument("--coverage", type=Path, required=True)
    run.add_argument("--transport", required=True)
    run.add_argument("--output", type=Path, default=None)
    run.set_defaults(handler=_eval_run)

    publish_release = evaluation_actions.add_parser("publish-release")
    publish_release.add_argument("--config", type=Path, required=True)
    publish_release.add_argument("--actor-id", required=True)
    publish_release.add_argument("--authority-grant-id", required=True)
    publish_release.add_argument("--evaluation-runs", type=Path, required=True)
    publish_release.add_argument("--output", type=Path, required=True)
    publish_release.set_defaults(handler=_eval_publish_release)

    release = evaluation_actions.add_parser("release")
    release.add_argument("--config", type=Path, required=True)
    release.add_argument("--evaluation-runs", type=Path, required=True)
    release.set_defaults(handler=_eval_release)

    retention = evaluation_actions.add_parser("retention")
    retention_actions = retention.add_subparsers(dest="retention_action", required=True)
    validate = retention_actions.add_parser("validate")
    validate.add_argument("--policy", type=Path, required=True)
    validate.set_defaults(handler=_eval_retention_validate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.group not in {"eval", "assurance-pack"}:
        return int(args.handler(args))
    try:
        return int(args.handler(args))
    except ArsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
