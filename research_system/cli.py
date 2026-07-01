from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from research_system.canonical import canonical_bytes
from research_system.command.service import CommandService
from research_system.config import ControlBinding
from research_system.errors import ArsError, ConfigurationError
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
        result = subprocess.run(
            ['git', '-C', str(resolved), 'worktree', 'list', '--porcelain'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            registered.add(resolved)
            continue
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
    service = CommandService(
        binding.control_root,
        ledger,
        ObjectStore(binding.control_root),
        ReceiptStore(binding.control_root),
        SchemaRegistry(binding.schema_root),
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return int(args.handler(args))
