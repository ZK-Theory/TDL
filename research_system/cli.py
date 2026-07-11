from __future__ import annotations

import argparse
import json
import subprocess  # nosec B404 - fixed git discovery command
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from research_system.canonical import canonical_bytes
from research_system.command.service import CommandService
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConfigurationError
from research_system.evals.calibration import calibrate_fixture
from research_system.evals.coverage import FOUNDATION_CASES, load_p0_coverage
from research_system.evals.harness import (
    build_release_decision,
    decide_p0_release,
    decision_document,
    run_all_scenarios,
    run_p0_coverage,
    stable_projection,
)
from research_system.evals.retention import validate_retention_policy
from research_system.evals.retention_authorizer import (
    build_deletion_manifest_authorizer,
    load_evidence_store_registry,
)
from research_system.projection.replay import rebuild_projection, replay
from research_system.schema_registry import SchemaRegistry
from research_system.store.identity import initialize_control_store, load_store_manifest
from research_system.store.ledger import EventLedger
from research_system.store.objects import ObjectStore
from research_system.store.receipts import ReceiptStore


def _print_json(value: Any) -> None:
    print(canonical_bytes(value).decode('utf-8'))


def _registered_code_roots(roots: list[Path]) -> list[Path]:
    registered: set[Path] = set()
    for root in roots:
        resolved = root.resolve(strict=True)
        try:
            result = subprocess.run(  # nosec B603 B607 - fixed git argv
                ['git', '-C', str(resolved), 'worktree', 'list', '--porcelain'],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConfigurationError(
                f'git worktree enumeration timed out for {resolved}'
            ) from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or 'unknown git error'
            raise ConfigurationError(
                f'cannot enumerate git worktrees for {resolved}: {detail}'
            )
        for line in result.stdout.splitlines():
            if line.startswith('worktree '):
                registered.add(Path(line.removeprefix('worktree ')).resolve(strict=True))
    if not registered:
        raise ConfigurationError('at least one resolvable code root is required')
    return sorted(registered, key=str)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f'invalid JSON file: {path}') from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f'JSON file must contain an object: {path}')
    return value


def _store_init(args: argparse.Namespace) -> int:
    roots = _registered_code_roots(args.code_root)
    identity = initialize_control_store(roots, args.control_root, args.project_id)
    _print_json({'project_id': args.project_id, 'store_identity': identity})
    return 0


def _command_submit(args: argparse.Namespace) -> int:
    binding = ControlBinding.load(args.config)
    command = _read_json(args.command)
    ledger = EventLedger(binding.control_root, binding.project_id)
    schemas = SchemaRegistry(binding.schema_root)
    service = CommandService(
        binding.control_root,
        ledger,
        ObjectStore(binding.control_root),
        ReceiptStore(binding.control_root),
        schemas,
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


def _verified_ledger(control_root: Path) -> EventLedger:
    manifest = load_store_manifest(control_root)
    return EventLedger(control_root.resolve(strict=True), manifest['project_id'])


def _replay_verify(args: argparse.Namespace) -> int:
    ledger = _verified_ledger(args.control_root)
    _print_json(replay(ledger.iter_events()))
    return 0


def _projection_rebuild(args: argparse.Namespace) -> int:
    control_root = args.control_root.resolve(strict=True)
    output = args.output.resolve(strict=False)
    if output == control_root or control_root in output.parents:
        raise ArsError('projection output must be external to canonical control root')
    manifest = load_store_manifest(control_root)
    projection_roots = [
        Path(root) / '.research-system' / 'projections'
        for root in manifest['code_roots']
    ]
    if not any(output == root or root in output.parents for root in projection_roots):
        raise ArsError('projection output must use an ARS namespaced projection root')
    ledger = EventLedger(control_root, manifest['project_id'])
    state = rebuild_projection(ledger.iter_events(), output)
    _print_json(state)
    return 0


def _eval_retention_validate(args: argparse.Namespace) -> int:
    policy = validate_retention_policy(args.policy)
    _print_json(
        {'policy_revision': policy['policy_revision'], 'rules': len(policy['rules'])}
    )
    return 0


def _eval_roots(coverage: Path) -> tuple[Path, Path]:
    try:
        eval_root = coverage.resolve(strict=True).parent
    except OSError as exc:
        raise ConfigurationError(f'invalid coverage file: {coverage}') from exc
    return eval_root / "fixtures", eval_root.parent / "schemas"


def _eval_validate(args: argparse.Namespace) -> int:
    import yaml

    try:
        catalogue = yaml.safe_load(args.catalogue.read_text(encoding="utf-8"))
        coverage_manifest = catalogue["coverage_manifest"]
        if not isinstance(coverage_manifest, str):
            raise TypeError
    except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
        raise ConfigurationError(
            f"invalid evaluation catalogue: {args.catalogue}"
        ) from exc
    coverage_path = args.catalogue.parent / coverage_manifest
    fixtures, schemas = _eval_roots(coverage_path)
    coverage = load_p0_coverage(
        coverage_path, fixture_root=fixtures, schema_root=schemas
    )
    _print_json({"status": "valid", "fixture_count": len(coverage.selected_fixture_revisions)})
    return 0


def _eval_calibrate(args: argparse.Namespace) -> int:
    if args.transport != "fake":
        raise ArsError("P0 calibration requires fake transport")
    fixtures, schemas = _eval_roots(args.coverage)
    load_p0_coverage(args.coverage, fixture_root=fixtures, schema_root=schemas)
    records = [
        calibrate_fixture(item, fixture_root=fixtures) for item in sorted(FOUNDATION_CASES)
    ]
    blocked = sum(record.blocking_verdict is not None for record in records)
    mutations_uncalibrated = sum(
        record.mutation_calibration_status != "calibrated"
        and bool(record.declared_mutation_ids)
        for record in records
    )
    _print_json(
        {
            "fixture_count": len(records),
            "blocked_fixture_count": blocked,
            "mutation_calibration": (
                "calibrated" if mutations_uncalibrated == 0 else "incomplete"
            ),
            "fixtures_with_uncalibrated_mutations": mutations_uncalibrated,
        }
    )
    return 0


def _eval_run(args: argparse.Namespace) -> int:
    if args.transport != "fake":
        raise ArsError("P0 execution requires fake transport")
    fixtures, schemas = _eval_roots(args.coverage)
    evidence = run_p0_coverage(
        args.coverage, fixture_root=fixtures, schema_root=schemas
    )
    assessment = decide_p0_release(evidence)
    output: Path | None = args.output
    if output is None:
        _print_json(
            {"candidate_status": assessment["decision"], "result_count": len(evidence.results)}
        )
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


def _eval_release(args: argparse.Namespace) -> int:
    manifest = _read_json(args.evaluation_runs)
    coverage_value = manifest.get("coverage")
    if not isinstance(coverage_value, str):
        raise ConfigurationError("evaluation runs manifest requires coverage")
    supplied_document = manifest.get("decision_document")
    if not isinstance(supplied_document, dict):
        raise ConfigurationError("evaluation runs manifest requires decision_document")
    coverage_path = Path(coverage_value)
    fixtures, schemas = _eval_roots(coverage_path)
    schema_registry = SchemaRegistry(schemas)
    schema_registry.validate(
        "ars://evals/release-gate-decision", supplied_document
    )
    evidence = run_p0_coverage(
        coverage_path, fixture_root=fixtures, schema_root=schemas
    )
    scenario_results = run_all_scenarios()
    record, outcome = build_release_decision(evidence, scenario_results)
    fresh_document = decision_document(record)
    schema_registry.validate("ars://evals/release-gate-decision", fresh_document)
    if stable_projection(fresh_document) != stable_projection(supplied_document):
        _print_json({"decision": "blocked", "reason": "evaluation_document_divergence"})
        return 0
    _print_json(
        {"decision": fresh_document["decision"], "missing": len(outcome["missing"])}
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='ars')
    groups = parser.add_subparsers(dest='group', required=True)

    store = groups.add_parser('store')
    store_commands = store.add_subparsers(dest='store_command', required=True)
    init = store_commands.add_parser('init')
    init.add_argument('--code-root', type=Path, action='append', required=True)
    init.add_argument('--control-root', type=Path, required=True)
    init.add_argument('--project-id', required=True)
    init.set_defaults(handler=_store_init)

    command = groups.add_parser('command')
    command_actions = command.add_subparsers(dest='command_action', required=True)
    submit = command_actions.add_parser('submit')
    submit.add_argument('--config', type=Path, required=True)
    submit.add_argument('--command', type=Path, required=True)
    submit.add_argument('--evidence-store-registry', type=Path, default=None)
    submit.set_defaults(handler=_command_submit)

    replay_parser = groups.add_parser('replay')
    replay_actions = replay_parser.add_subparsers(
        dest='replay_action', required=True
    )
    verify = replay_actions.add_parser('verify')
    verify.add_argument('--control-root', type=Path, required=True)
    verify.set_defaults(handler=_replay_verify)

    projection = groups.add_parser('projection')
    projection_actions = projection.add_subparsers(
        dest='projection_action', required=True
    )
    rebuild = projection_actions.add_parser('rebuild')
    rebuild.add_argument('--control-root', type=Path, required=True)
    rebuild.add_argument('--output', type=Path, required=True)
    rebuild.set_defaults(handler=_projection_rebuild)

    evaluation = groups.add_parser('eval')
    evaluation_actions = evaluation.add_subparsers(
        dest='eval_action', required=True
    )
    validate_eval = evaluation_actions.add_parser('validate')
    validate_eval.add_argument('--catalogue', type=Path, required=True)
    validate_eval.set_defaults(handler=_eval_validate)

    calibrate = evaluation_actions.add_parser('calibrate')
    calibrate.add_argument('--coverage', type=Path, required=True)
    calibrate.add_argument('--transport', required=True)
    calibrate.set_defaults(handler=_eval_calibrate)

    run = evaluation_actions.add_parser('run')
    run.add_argument('--coverage', type=Path, required=True)
    run.add_argument('--transport', required=True)
    run.add_argument('--output', type=Path, default=None)
    run.set_defaults(handler=_eval_run)

    release = evaluation_actions.add_parser('release')
    release.add_argument('--evaluation-runs', type=Path, required=True)
    release.set_defaults(handler=_eval_release)

    retention = evaluation_actions.add_parser('retention')
    retention_actions = retention.add_subparsers(
        dest='retention_action', required=True
    )
    validate = retention_actions.add_parser('validate')
    validate.add_argument('--policy', type=Path, required=True)
    validate.set_defaults(handler=_eval_retention_validate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.group != 'eval':
        return int(args.handler(args))
    try:
        return int(args.handler(args))
    except ArsError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
