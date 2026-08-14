from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import research_system.cli as cli
from research_system.canonical import canonical_bytes
from research_system.discovery import operator as operator_module
from research_system.discovery.accepted_w11 import ACCEPTED, CATALOGUE_STREAM_ID
from research_system.errors import ConflictError, ConfigurationError, IntegrityError
from research_system.ids import new_id
from research_system.store.ledger import EventLedger
from tests.research_system.factories import ACTORS, PROJECT_ID, activate_lifecycle_grant, control_plane


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPOSITORY_ROOT / ".research-system" / "schemas"
CATALOGUE_PATH = SCHEMA_ROOT.parent / "evals" / "expected" / "w11-portfolio-discovery-v1.json"
ACTOR_ID = ACTORS["actor-a"]


def _tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes], ...]:
    if not root.exists():
        return ()
    entries: list[tuple[str, str, bytes]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        entries.append(
            ("directory" if path.is_dir() else "file", relative, b"" if path.is_dir() else path.read_bytes())
        )
    return tuple(entries)


def _write_canonical_json(path: Path, value: dict[str, Any]) -> Path:
    path.write_bytes(canonical_bytes(value))
    return path


def _run_git(repository_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        capture_output=True,
        check=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def _clean_w11_repository(tmp_path: Path, *, name: str = "clean-w11-repository") -> Path:
    repository_root = tmp_path / name
    for source, relative in (
        (CATALOGUE_PATH, Path(".research-system") / "evals" / "expected" / CATALOGUE_PATH.name),
        (
            SCHEMA_ROOT.parent / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml",
            Path(".research-system") / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml",
        ),
    ):
        target = repository_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    _run_git(repository_root.parent, "init", "--quiet", repository_root.name)
    _run_git(repository_root, "config", "user.email", "tests@example.invalid")
    _run_git(repository_root, "config", "user.name", "Discovery operator tests")
    _run_git(repository_root, "add", ".")
    _run_git(repository_root, "commit", "--quiet", "-m", "fixture")
    return repository_root


def _operator_config(
    tmp_path: Path,
    *,
    repository_root: Path,
    root_tokens: dict[str, str],
) -> Path:
    binding_path = _write_canonical_json(tmp_path / "control-binding.json", {})
    authority_binding_path = _write_canonical_json(tmp_path / "authority-binding.json", {})
    return _write_canonical_json(
        tmp_path / "operator-config.json",
        {
            "control_binding": str(binding_path),
            "authority_binding": str(authority_binding_path),
            "repository_root": str(repository_root),
            "catalogue_path": str(repository_root / CATALOGUE_PATH.relative_to(REPOSITORY_ROOT)),
            "root_tokens": root_tokens,
        },
    )


def _genesis_command(grant_id: str) -> dict[str, object]:
    return {
        "command_id": new_id("command"),
        "command_type": "ImportAcceptedW11CatalogueGenesis",
        "actor_id": ACTOR_ID,
        "authority_grant_id": grant_id,
        "idempotency_key": "operator-cli:w11-genesis",
        "target_stream_id": CATALOGUE_STREAM_ID,
        "expected_stream_version": 0,
        "payload": dict(ACCEPTED),
    }


@pytest.fixture
def operator_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Temporary implementation fixture; it is not Gate 6 research evidence."""

    harness = control_plane(tmp_path, auto_authority=False, clock=lambda: datetime(2026, 8, 1, tzinfo=UTC))
    repository_root = _clean_w11_repository(tmp_path)
    binding_path = _write_canonical_json(tmp_path / "control-binding.json", {})
    authority_binding_path = _write_canonical_json(tmp_path / "authority-binding.json", {})
    for name in ("objects", "manifests", "snapshots"):
        (harness.ledger.control_root / name).mkdir()
    binding = SimpleNamespace(
        code_roots=(repository_root,),
        control_root=harness.ledger.control_root,
        project_id=PROJECT_ID,
        schema_root=SCHEMA_ROOT,
        store_identity="e" * 64,
        origin_witness=None,
        origin_witness_path=None,
    )
    authority_binding = SimpleNamespace(
        code_roots=(repository_root,),
        control_root=harness.authority_root,
        project_id=PROJECT_ID,
        schema_root=SCHEMA_ROOT,
        store_identity=harness.authority_resolver.expected_store_identity,
        origin_witness=harness.authority_resolver.approved_witness,
        origin_witness_path=harness.authority_resolver.approved_witness_path,
    )

    def load_binding(path: Path) -> SimpleNamespace:
        if path == binding_path:
            return binding
        assert path == authority_binding_path
        return authority_binding

    monkeypatch.setattr(operator_module.ControlBinding, "load", load_binding)
    config = {
        "control_binding": str(binding_path),
        "authority_binding": str(authority_binding_path),
        "repository_root": str(repository_root),
        "catalogue_path": str(repository_root / CATALOGUE_PATH.relative_to(REPOSITORY_ROOT)),
        "root_tokens": {"repository": str(repository_root)},
    }
    config_path = _write_canonical_json(tmp_path / "operator-config.json", config)
    grant_id = activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=CATALOGUE_STREAM_ID,
        actor_id=ACTOR_ID,
        allowed_actor_classes=("human",),
        command_types=("ImportAcceptedW11CatalogueGenesis",),
    )
    command = _genesis_command(grant_id)
    command_path = _write_canonical_json(tmp_path / "command.json", command)
    return {
        "harness": harness,
        "binding": binding,
        "authority_binding": authority_binding,
        "config": config,
        "config_path": config_path,
        "command": command,
        "command_path": command_path,
    }


def _submit_argv(inputs: dict[str, Any]) -> list[str]:
    return [
        "discovery",
        "submit",
        "--operator-config",
        str(inputs["config_path"]),
        "--command",
        str(inputs["command_path"]),
    ]


def _status_argv(inputs: dict[str, Any]) -> list[str]:
    return ["discovery", "status", "--operator-config", str(inputs["config_path"])]


@pytest.mark.integration
def test_discovery_cli_rejects_dirty_repository_root_and_legacy_root_token_before_binding(
    tmp_path: Path,
) -> None:
    config_path = _operator_config(
        tmp_path,
        repository_root=REPOSITORY_ROOT,
        root_tokens={"$REPOSITORY_CONTRACT_ROOT": str(REPOSITORY_ROOT)},
    )

    with pytest.raises(ConfigurationError, match="repository_root is not clean"):
        cli.main(["discovery", "status", "--operator-config", str(config_path)])


@pytest.mark.integration
def test_discovery_cli_rejects_fake_git_marker_before_binding(tmp_path: Path) -> None:
    fake_root = tmp_path / "fake-git-root"
    fake_root.mkdir()
    (fake_root / ".git").write_text("not a Git repository", encoding="utf-8")
    for source, relative in (
        (CATALOGUE_PATH, CATALOGUE_PATH.relative_to(REPOSITORY_ROOT)),
        (
            SCHEMA_ROOT.parent / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml",
            Path(".research-system") / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml",
        ),
    ):
        target = fake_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    config_path = _operator_config(
        tmp_path,
        repository_root=fake_root,
        root_tokens={"$REPOSITORY_CONTRACT_ROOT": str(fake_root)},
    )

    with pytest.raises(ConfigurationError, match="actual Git worktree root"):
        cli.main(["discovery", "status", "--operator-config", str(config_path)])


@pytest.mark.integration
def test_discovery_cli_rejects_redirected_nested_event_store_before_constructor(
    operator_inputs: dict[str, Any],
    tmp_path: Path,
) -> None:
    control_root = operator_inputs["binding"].control_root
    event_root = control_root / "events" / PROJECT_ID
    event_root.rmdir()
    redirected_root = tmp_path / "redirected-events"
    redirected_root.mkdir()
    event_root.symlink_to(redirected_root, target_is_directory=True)
    before = _tree_snapshot(control_root)

    with pytest.raises(ConfigurationError, match="physical path"):
        cli.main(_status_argv(operator_inputs))

    assert _tree_snapshot(control_root) == before
    assert _tree_snapshot(redirected_root) == ()


@pytest.mark.integration
def test_discovery_cli_submit_status_and_fresh_runtime_restart_are_canonical(
    operator_inputs: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(_submit_argv(operator_inputs)) == 0
    accepted = json.loads(capsys.readouterr().out)
    assert accepted["status"] == "accepted"

    before_status = _tree_snapshot(operator_inputs["binding"].control_root)
    assert cli.main(_status_argv(operator_inputs)) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["event_count"] >= 1
    assert status["latest_global_position"] >= 1
    assert status["projection"]["catalogue"]["stream_id"] == CATALOGUE_STREAM_ID
    assert status["projection"]["catalogue"]["state"] == "imported"
    assert status["projection"]["catalogue"]["accepted_commit"] == ACCEPTED["accepted_commit"]
    assert _tree_snapshot(operator_inputs["binding"].control_root) == before_status

    # A second CLI invocation constructs a new operator/runtime from durable state.
    assert cli.main(_submit_argv(operator_inputs)) == 0
    assert json.loads(capsys.readouterr().out) == accepted


@pytest.mark.integration
def test_discovery_cli_reused_command_id_with_changed_command_conflicts_without_repair(
    operator_inputs: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(_submit_argv(operator_inputs)) == 0
    capsys.readouterr()
    before = _tree_snapshot(operator_inputs["binding"].control_root)
    changed = deepcopy(operator_inputs["command"])
    changed["idempotency_key"] = "operator-cli:w11-genesis:changed"
    _write_canonical_json(operator_inputs["command_path"], changed)

    with pytest.raises(ConflictError):
        cli.main(_submit_argv(operator_inputs))

    assert _tree_snapshot(operator_inputs["binding"].control_root) == before


@pytest.mark.integration
def test_discovery_cli_rejects_malformed_envelope_before_any_store_mutation(
    operator_inputs: dict[str, Any],
) -> None:
    before = _tree_snapshot(operator_inputs["binding"].control_root)
    malformed = dict(operator_inputs["command"])
    malformed.pop("payload")
    _write_canonical_json(operator_inputs["command_path"], malformed)

    with pytest.raises(IntegrityError, match="invalid Discovery command envelope"):
        cli.main(_submit_argv(operator_inputs))

    assert _tree_snapshot(operator_inputs["binding"].control_root) == before


@pytest.mark.integration
@pytest.mark.parametrize(
    "override",
    (
        {
            "catalogue_path": str(
                SCHEMA_ROOT.parent / "contracts" / "w11" / "w11-materialization-bootstrap-contract.yaml"
            )
        },
        {"repository_root": "REPLACED_BY_TMP_PATH"},
        {"root_tokens": {}},
    ),
)
def test_discovery_cli_rejects_wrong_catalogue_path_or_root_token_binding_without_mutation(
    operator_inputs: dict[str, Any],
    override: dict[str, object],
    tmp_path: Path,
) -> None:
    before = _tree_snapshot(operator_inputs["binding"].control_root)
    config = deepcopy(operator_inputs["config"])
    resolved_override = {
        key: (str(tmp_path) if value == "REPLACED_BY_TMP_PATH" else value) for key, value in override.items()
    }
    config.update(resolved_override)
    _write_canonical_json(operator_inputs["config_path"], config)

    with pytest.raises(ConfigurationError):
        cli.main(_submit_argv(operator_inputs))

    assert _tree_snapshot(operator_inputs["binding"].control_root) == before


@pytest.mark.integration
def test_discovery_cli_rejects_clean_repository_outside_control_binding_without_mutation(
    operator_inputs: dict[str, Any],
    tmp_path: Path,
) -> None:
    unbound_repository = _clean_w11_repository(tmp_path, name="unbound-w11-repository")
    before = _tree_snapshot(operator_inputs["binding"].control_root)
    config = deepcopy(operator_inputs["config"])
    config.update(
        {
            "repository_root": str(unbound_repository),
            "catalogue_path": str(unbound_repository / CATALOGUE_PATH.relative_to(REPOSITORY_ROOT)),
            "root_tokens": {"repository": str(unbound_repository)},
        }
    )
    _write_canonical_json(operator_inputs["config_path"], config)

    with pytest.raises(ConfigurationError, match="repository_root is not bound by control_binding"):
        cli.main(_submit_argv(operator_inputs))

    assert _tree_snapshot(operator_inputs["binding"].control_root) == before


@pytest.mark.integration
@pytest.mark.parametrize("layout", ("missing", "partial"))
def test_discovery_cli_rejects_missing_or_partial_store_before_constructing_runtime(
    operator_inputs: dict[str, Any],
    layout: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid_root = tmp_path / f"{layout}-control"
    if layout == "partial":
        invalid_root.mkdir()
        for name in ("objects", "events", "manifests", "receipts", "snapshots"):
            (invalid_root / name).mkdir()
    invalid_binding = SimpleNamespace(
        **{
            **operator_inputs["binding"].__dict__,
            "control_root": invalid_root,
        }
    )
    monkeypatch.setattr(operator_module.ControlBinding, "load", lambda _path: invalid_binding)
    before = _tree_snapshot(tmp_path)

    with pytest.raises(ConfigurationError):
        cli.main(_submit_argv(operator_inputs))

    assert _tree_snapshot(tmp_path) == before


@pytest.mark.integration
def test_discovery_cli_recovers_post_publication_interruption_with_canonical_receipt(
    operator_inputs: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    control_root = operator_inputs["binding"].control_root

    def interrupt_after_publish(ledger: EventLedger, _target: Path) -> None:
        if ledger.control_root == control_root:
            raise OSError("injected post-publication interruption")

    with monkeypatch.context() as patch:
        patch.setattr(EventLedger, "_after_publish", interrupt_after_publish)
        with pytest.raises(OSError, match="post-publication interruption"):
            cli.main(_submit_argv(operator_inputs))

    before_retry = _tree_snapshot(control_root)
    assert cli.main(_submit_argv(operator_inputs)) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "accepted"
    restarted = EventLedger(
        control_root,
        PROJECT_ID,
        operator_inputs["harness"].schemas,
        store_identity="e" * 64,
    )
    committed = [
        batch
        for batch in restarted.iter_batches()
        if batch[0]["command_id"] == operator_inputs["command"]["command_id"]
    ]
    assert len(committed) == 1
    assert receipt["event_batch_id"] == committed[0][0]["transaction_id"]
    assert cli.main(_submit_argv(operator_inputs)) == 0
    assert json.loads(capsys.readouterr().out) == receipt
    assert _tree_snapshot(control_root) != before_retry


@pytest.mark.integration
def test_discovery_cli_pre_publication_interruption_leaves_zero_published_state(
    operator_inputs: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control_root = operator_inputs["binding"].control_root

    def interrupt_before_publish(ledger: EventLedger, _temporary: Path) -> None:
        if ledger.control_root == control_root:
            raise OSError("injected pre-publication interruption")

    with monkeypatch.context() as patch:
        patch.setattr(EventLedger, "_after_batch_fsync", interrupt_before_publish)
        with pytest.raises(OSError, match="pre-publication interruption"):
            cli.main(_submit_argv(operator_inputs))

    restarted = EventLedger(
        control_root,
        PROJECT_ID,
        operator_inputs["harness"].schemas,
        store_identity="e" * 64,
    )
    assert tuple(restarted.iter_events()) == ()
    assert not list((control_root / "objects").rglob("*"))
    assert not list((control_root / "receipts").glob("*.json"))
    assert not list((control_root / "receipts" / "idempotency").rglob("*.json"))
