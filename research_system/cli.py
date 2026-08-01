from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404 - fixed git discovery command
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from research_system.authority import (
    LedgerAuthorityGrantResolver,
    authority_bootstrap_sha256,
    initialize_authority_control_store,
)
from research_system.canonical import canonical_bytes, jsonable
from research_system.command.service import CommandService
from research_system.config import ControlBinding
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
from research_system.projection.replay import rebuild_projection, replay
from research_system.schema_registry import (
    SchemaRegistry,
    require_authority_schemas,
    runtime_schema_registry,
)
from research_system.store.identity import load_store_manifest, manifest_schema_root
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
    identity = initialize_authority_control_store(
        roots,
        args.control_root,
        args.project_id,
        manifest,
        approved,
        canonical_schema_root=explicit_root / ".research-system" / "schemas",
    )
    _print_json(
        {
            "project_id": args.project_id,
            "store_identity": identity,
            "bootstrap_manifest_sha256": authority_bootstrap_sha256(manifest),
        }
    )
    return 0


def _command_submit(args: argparse.Namespace) -> int:
    binding = ControlBinding.load(args.config)
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
        ),
        clock=_authority_clock,
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


def _verified_ledger(
    control_root: Path,
) -> tuple[
    EventLedger,
    SchemaRegistry,
    LedgerAuthorityGrantResolver,
]:
    manifest = load_store_manifest(control_root)
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
    manifest = load_store_manifest(control_root)
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

    command = groups.add_parser("command")
    command_actions = command.add_subparsers(dest="command_action", required=True)
    submit = command_actions.add_parser("submit")
    submit.add_argument("--config", type=Path, required=True)
    submit.add_argument("--command", type=Path, required=True)
    submit.add_argument("--evidence-store-registry", type=Path, default=None)
    submit.set_defaults(handler=_command_submit)

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
    if args.group != "eval":
        return int(args.handler(args))
    try:
        return int(args.handler(args))
    except ArsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
