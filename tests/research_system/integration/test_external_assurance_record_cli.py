"""Exercise the bounded external assurance-record CLI seam end to end."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from research_system.assurance.resolver import ControlStoreAuthorityResolver
from research_system.assurance.external_records import ExternalAssuranceRecordStore
from research_system.authority import authority_bootstrap_sha256, initialize_authority_control_store
from research_system.canonical import canonical_bytes, jsonable, sha256_hex
from research_system.cli import main
from research_system.config import ApprovedProjectBinding, ControlBinding
from research_system.errors import ArsError, ConfigurationError
from research_system.store.identity import (
    load_restore_binding_evidence,
    load_store_manifest_unbound,
    rebind_restored_store,
)
from tests.research_system.factories import authority_bootstrap


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
PROJECT_ID = "prj_01978abc-1000-7000-8000-000000001000"
RECORD_ID = "act_01978abc-2000-7000-8000-000000002000"


@pytest.fixture(autouse=True)
def _restore_tests_have_durable_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import research_system.cli as cli_module
    import research_system.store.identity as identity_module

    monkeypatch.setattr(identity_module, "_fsync_directory", lambda _path: True)
    monkeypatch.setattr(cli_module, "_fsync_directory", lambda _path: True)
    monkeypatch.setattr(
        cli_module,
        "_CANONICAL_FOUNDATION_CONFIG",
        tmp_path / "foundation.yaml",
        raising=False,
    )


def _record() -> dict[str, str]:
    return {
        "record_type": "canonical_actor",
        "actor_id": RECORD_ID,
        "actor_kind": "agent",
        "canonical_name": "Ada",
        "status": "active",
    }


def _config(tmp_path: Path) -> tuple[Path, Path, str]:
    code_root = tmp_path / "code"
    code_root.mkdir()
    shutil.copytree(SCHEMA_ROOT, code_root / ".research-system" / "schemas")
    shutil.copytree(REPO_ROOT / ".research-system" / "contracts", code_root / ".research-system" / "contracts")
    control_root = tmp_path / "control"
    bootstrap = authority_bootstrap(publication_expires_at="2099-07-13T00:00:00Z")
    identity = initialize_authority_control_store(
        [code_root],
        control_root,
        PROJECT_ID,
        bootstrap,
        authority_bootstrap_sha256(bootstrap),
        canonical_schema_root=code_root / ".research-system" / "schemas",
    )
    schema_root = code_root / ".research-system" / "schemas"
    config = tmp_path / "binding.json"
    config.write_text(
        json.dumps(
            {
                "code_roots": [str(code_root.resolve())],
                "control_root": str(control_root.resolve()),
                "project_id": PROJECT_ID,
                "schema_root": str(schema_root.resolve()),
                "store_identity": identity,
            }
        ),
        encoding="utf-8",
    )
    return config, control_root, identity


def _foundation_value(
    case: dict[str, object],
    *,
    code_root: Path | None = None,
    schema_root: Path | None = None,
    control_root: Path | None = None,
) -> dict[str, object]:
    receipt = case["receipt"]
    assert hasattr(receipt, "project_id")
    resolved_code_root = (code_root or case["code_root"]).resolve()
    resolved_schema_root = (schema_root or (resolved_code_root / ".research-system" / "schemas")).resolve()
    value: dict[str, object] = {
        "schema_version": "1.0.0",
        "project_template_alias": "ars-foundation-p0",
        "project_id": receipt.project_id,
        "store_identity": receipt.store_identity,
        "control_root": str((control_root or case["source"]).resolve()),
        "control_root_required": True,
        "endpoint_scheme": receipt.source_endpoint_scheme,
        "canonical_uri": f"{receipt.source_endpoint_scheme}://{(control_root or case['source']).resolve().as_posix()}",
        "canonical_tail_position": receipt.canonical_tail_position,
        "canonical_tail_hash": receipt.canonical_tail_hash,
        "code_roots": [str(resolved_code_root)],
        "schema_root": str(resolved_schema_root),
        "canonical_hash": "sha256",
    }
    value["foundation_sha256"] = sha256_hex(
        canonical_bytes({key: item for key, item in value.items() if key != "foundation_sha256"})
    )
    return value


def _write_foundation(
    path: Path,
    case: dict[str, object],
    *,
    code_root: Path | None = None,
    schema_root: Path | None = None,
    control_root: Path | None = None,
) -> None:
    path.write_bytes(
        canonical_bytes(
            _foundation_value(
                case,
                code_root=code_root,
                schema_root=schema_root,
                control_root=control_root,
            )
        )
    )


def _target_files(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted((path.relative_to(root).as_posix(), path.read_bytes()) for path in root.rglob("*") if path.is_file())
    )


def _path_inventory(root: Path) -> tuple[tuple[str, str, bytes], ...]:
    if not root.exists():
        return ()
    entries: list[tuple[str, str, bytes]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append((relative, "symlink", os.readlink(path).encode("utf-8", errors="surrogateescape")))
        elif path.is_dir():
            entries.append((relative, "directory", b""))
        elif path.is_file():
            entries.append((relative, "file", path.read_bytes()))
        else:
            entries.append((relative, "other", b""))
    return tuple(sorted(entries))


def _foreign_binding_bytes(tmp_path: Path, case: dict[str, object]) -> bytes:
    foreign_code = tmp_path / "foreign-code"
    shutil.copytree(case["code_root"], foreign_code)
    foreign_control = tmp_path / "foreign-control"
    foreign_project = case["receipt"].project_id
    foreign_bootstrap = authority_bootstrap(publication_expires_at="2099-07-13T00:00:00Z")
    foreign_identity = initialize_authority_control_store(
        [foreign_code],
        foreign_control,
        foreign_project,
        foreign_bootstrap,
        authority_bootstrap_sha256(foreign_bootstrap),
        canonical_schema_root=foreign_code / ".research-system" / "schemas",
    )
    return canonical_bytes(
        {
            "code_roots": [str(foreign_code.resolve())],
            "control_root": str(foreign_control.resolve()),
            "project_id": foreign_project,
            "schema_root": str((foreign_code / ".research-system" / "schemas").resolve()),
            "store_identity": foreign_identity,
        }
    )


def _run_restore_crash(args: list[str], foundation: Path, crash_point: str) -> subprocess.CompletedProcess[str]:
    script = """
import json
import os
from pathlib import Path

import research_system.cli as cli
import research_system.store.identity as identity

identity._fsync_directory = lambda _path: True
cli._fsync_directory = lambda _path: True
cli._CANONICAL_FOUNDATION_CONFIG = Path(os.environ["ARS_FOUNDATION"])
crash_point = os.environ["ARS_CRASH_POINT"]

def crash_after_state(path, _state, _generation):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record["last_completed_durability_step"] == crash_point:
        os._exit(77)

identity._after_restore_transaction_state_written = crash_after_state
cli.main(json.loads(os.environ["ARS_ARGS"]))
"""
    environment = os.environ.copy()
    environment["ARS_FOUNDATION"] = str(foundation)
    environment["ARS_ARGS"] = json.dumps(args)
    environment["ARS_CRASH_POINT"] = crash_point
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )


def _restore_cli_case(tmp_path: Path) -> tuple[dict[str, object], list[str]]:
    from tests.research_system.integration.test_gate5_release_tranche import _build_restore_case

    case = _build_restore_case(tmp_path)
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(jsonable(asdict(case["receipt"]))))
    registry = case["registry"]
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://evals/evidence-store-registry",
                "schema_version": "1.0.0",
                "store_id": registry.store_id,
                "registry_hash": registry.registry_hash,
                "policy_revision": registry.policy_revision,
                "primary_root": str(registry.primary_root),
                "runtime_root": str(registry.runtime_root),
                "staging_root": str(registry.staging_root),
                "temp_root": str(registry.temp_root),
                "replicas": [str(path) for path in registry.replicas],
                "backup_roots": [str(path) for path in registry.backup_roots],
                "restore_roots": [str(path) for path in registry.restore_roots],
                "permitted_consumers": list(registry.permitted_consumers),
                "retention_policy_ids": list(registry.retention_policy_ids),
                "verifier_authority_bindings": [list(pair) for pair in registry.verifier_authority_bindings],
                "unregistered_replicas_prohibited": registry.unregistered_replicas_prohibited,
            }
        )
    )
    config_output = tmp_path / "restored-binding.json"
    foundation_config = tmp_path / "foundation.yaml"
    _write_foundation(foundation_config, case)
    args = [
        "store",
        "restore-bind",
        "--control-root",
        str(case["target"]),
        "--source-root",
        str(case["source"]),
        "--receipt",
        str(receipt_path),
        "--snapshot",
        str(case["snapshot_path"]),
        "--endpoint-ownership",
        str(case["endpoint_path"]),
        "--artefact-manifest",
        str(case["artefact_manifest_path"]),
        "--registry",
        str(registry_path),
        "--actor-id",
        case["actor_id"],
        "--authority-grant-id",
        case["authority_grant_id"],
        "--foundation-config",
        str(foundation_config),
        "--schema-root",
        str(case["code_root"] / ".research-system" / "schemas"),
        "--config-output",
        str(config_output),
    ]
    return case, args


def test_restore_bind_cli_rejects_the_tracked_null_foundation(tmp_path: Path) -> None:
    case, args = _restore_cli_case(tmp_path)
    foundation = Path(args[args.index("--foundation-config") + 1])
    foundation.write_text(
        "\n".join(
            (
                "schema_version: '1.0.0'",
                "project_template_alias: ars-foundation-p0",
                "project_id: null",
                "control_root: null",
                "control_root_required: true",
                "endpoint_scheme: local-cli",
                "canonical_hash: sha256",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    before_target = _target_files(case["target"])

    with pytest.raises(ConfigurationError, match="missing|materialized"):
        main(args)

    assert _target_files(case["target"]) == before_target
    assert not (tmp_path / "restored-binding.json").exists()


def test_approved_project_binding_load_rejects_absent_store_without_creating(tmp_path: Path) -> None:
    case, _ = _restore_cli_case(tmp_path)
    foundation = tmp_path / "absent-foundation.yaml"
    absent_root = tmp_path / "absent-control"
    _write_foundation(foundation, case, control_root=absent_root)
    before_parent = _path_inventory(tmp_path)

    with pytest.raises(ConfigurationError, match="materialized|matching|unavailable"):
        ApprovedProjectBinding.load(foundation)

    assert not absent_root.exists()
    assert _path_inventory(tmp_path) == before_parent


def test_approved_project_binding_load_rejects_partial_store_without_repairing(tmp_path: Path) -> None:
    case, _ = _restore_cli_case(tmp_path)
    foundation = tmp_path / "partial-foundation.yaml"
    partial_root = tmp_path / "partial-control"
    (partial_root / "objects").mkdir(parents=True)
    (partial_root / "objects" / "sentinel.bin").write_bytes(b"preserve")
    _write_foundation(foundation, case, control_root=partial_root)
    before_root = _path_inventory(partial_root)

    with pytest.raises(ConfigurationError, match="materialized|matching|invalid"):
        ApprovedProjectBinding.load(foundation)

    assert _path_inventory(partial_root) == before_root
    assert not (partial_root / "manifests").exists()
    assert not (partial_root / "events").exists()
    assert not (partial_root / "receipts").exists()
    assert not (partial_root / "snapshots").exists()
    assert not (partial_root / "runtime").exists()


@pytest.mark.parametrize("missing_directory", ("objects", "events", "manifests", "receipts", "snapshots", "runtime"))
def test_approved_project_binding_load_rejects_valid_manifest_with_missing_required_directory(
    tmp_path: Path,
    missing_directory: str,
) -> None:
    case, _ = _restore_cli_case(tmp_path)
    foundation = tmp_path / "missing-directory-foundation.yaml"
    partial_root = case["source"]
    shutil.rmtree(partial_root / missing_directory)
    _write_foundation(foundation, case, control_root=partial_root)
    before_root = _path_inventory(partial_root)

    with pytest.raises(ConfigurationError, match="materialized|matching|missing|invalid"):
        ApprovedProjectBinding.load(foundation)

    assert _path_inventory(partial_root) == before_root
    assert not (partial_root / missing_directory).exists()


def _make_directory_reparse(path: Path, target: Path) -> str:
    try:
        os.symlink(target, path, target_is_directory=True)
        return "symlink"
    except OSError:
        if os.name == "nt":
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(path), str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return "junction"
        pytest.skip("directory reparse-point creation is unavailable")


@pytest.mark.parametrize("replacement", ("file", "reparse"))
@pytest.mark.parametrize("child_name", ("objects", "events", "manifests", "receipts", "snapshots", "runtime"))
def test_approved_project_binding_load_rejects_nonphysical_required_child_without_mutation(
    tmp_path: Path,
    replacement: str,
    child_name: str,
) -> None:
    case, _ = _restore_cli_case(tmp_path)
    foundation = tmp_path / f"{child_name}-{replacement}-foundation.yaml"
    child = case["source"] / child_name
    foreign = tmp_path / f"foreign-{child_name}"
    shutil.rmtree(child)
    if replacement == "file":
        child.write_bytes(b"not a directory")
    else:
        foreign.mkdir()
        (foreign / "foreign.bin").write_bytes(b"foreign")
        _make_directory_reparse(child, foreign)
    _write_foundation(foundation, case, control_root=case["source"])
    before_root = _path_inventory(case["source"])

    with pytest.raises(ConfigurationError, match="materialized|matching|missing|physical|reparse|invalid"):
        ApprovedProjectBinding.load(foundation)

    assert _path_inventory(case["source"]) == before_root
    if replacement == "reparse":
        assert child.is_symlink() or child.resolve(strict=True) == foreign.resolve()
        assert child.resolve(strict=True) == foreign.resolve()


def test_approved_project_binding_load_accepts_parent_alias_with_physical_children(tmp_path: Path) -> None:
    case, _ = _restore_cli_case(tmp_path)
    alias_parent = tmp_path / "control-parent-alias"
    try:
        os.symlink(tmp_path, alias_parent, target_is_directory=True)
    except OSError:
        pytest.skip("directory alias creation is unavailable")
    foundation = tmp_path / "parent-alias-foundation.yaml"
    _write_foundation(foundation, case, control_root=alias_parent / case["source"].name)

    loaded = ApprovedProjectBinding.load(foundation)

    assert loaded.control_root == case["source"].resolve()
    assert all(
        (loaded.control_root / name).is_dir()
        for name in ("objects", "events", "manifests", "receipts", "snapshots", "runtime")
    )


def test_assurance_record_write_cli_persists_and_resolves(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config, control_root, authority_root = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(_record()), encoding="utf-8")

    assert (
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                "--record",
                str(record_path),
            ]
        )
        == 0
    )
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["record_class"] == "canonical_actor"
    assert receipt["record_id"] == RECORD_ID
    assert receipt["revision"] == 1

    resolved = ControlStoreAuthorityResolver(ControlBinding.load(config)).resolve(
        record_id=RECORD_ID,
        record_class="canonical_actor",
        authority_root=authority_root,
        phase="load",
    )
    assert resolved == _record()


def test_assurance_record_write_cli_requires_json_object(tmp_path: Path) -> None:
    config, _, _ = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must contain an object"):
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                "--record",
                str(record_path),
            ]
        )


def test_assurance_record_copy_cannot_use_journal_less_rebind(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config, source_root, store_identity = _config(tmp_path)
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(_record()), encoding="utf-8")
    assert (
        main(
            [
                "assurance-record",
                "write",
                "--config",
                str(config),
                "--record-class",
                "canonical_actor",
                "--record-id",
                RECORD_ID,
                "--revision",
                "1",
                "--expected-previous-revision",
                "0",
                "--record",
                str(record_path),
            ]
        )
        == 0
    )
    capsys.readouterr()

    target_root = tmp_path / "restored"
    shutil.copytree(source_root, target_root)
    manifest_path = target_root / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    with pytest.raises(ArsError, match="complete approved restore transaction inputs"):
        rebind_restored_store(
            target_root,
            source_root,
            expected_project_id=PROJECT_ID,
            expected_store_identity=store_identity,
            expected_code_roots=[tmp_path / "code"],
        )
    assert manifest_path.read_bytes() == before_manifest
    assert not (target_root / "manifests" / ".restore-binding-transaction.json").exists()


def test_restore_bind_cli_rebinds_only_after_verified_preflight(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from tests.research_system.integration.test_gate5_release_tranche import _build_restore_case

    case = _build_restore_case(tmp_path)
    source_config = tmp_path / "source-binding.json"
    source_config.write_bytes(
        canonical_bytes(
            {
                "code_roots": [str(case["code_root"].resolve())],
                "control_root": str(case["source"].resolve()),
                "project_id": case["receipt"].project_id,
                "schema_root": str((case["code_root"] / ".research-system" / "schemas").resolve()),
                "store_identity": case["receipt"].store_identity,
            }
        )
    )
    ExternalAssuranceRecordStore(ControlBinding.load(source_config)).write(
        record_class="canonical_actor",
        record_id=RECORD_ID,
        revision=1,
        expected_previous_revision=0,
        record=_record(),
    )
    shutil.copytree(
        case["source"] / "objects" / "assurance_record",
        case["target"] / "objects" / "assurance_record",
        dirs_exist_ok=True,
    )
    before_events = sorted(
        (path.relative_to(case["target"]).as_posix(), path.read_bytes())
        for path in (case["target"] / "events").rglob("*.jsonl")
    )
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_bytes(canonical_bytes(jsonable(asdict(case["receipt"]))))
    registry = case["registry"]
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://evals/evidence-store-registry",
                "schema_version": "1.0.0",
                "store_id": registry.store_id,
                "registry_hash": registry.registry_hash,
                "policy_revision": registry.policy_revision,
                "primary_root": str(registry.primary_root),
                "runtime_root": str(registry.runtime_root),
                "staging_root": str(registry.staging_root),
                "temp_root": str(registry.temp_root),
                "replicas": [str(path) for path in registry.replicas],
                "backup_roots": [str(path) for path in registry.backup_roots],
                "restore_roots": [str(path) for path in registry.restore_roots],
                "permitted_consumers": list(registry.permitted_consumers),
                "retention_policy_ids": list(registry.retention_policy_ids),
                "verifier_authority_bindings": [list(pair) for pair in registry.verifier_authority_bindings],
                "unregistered_replicas_prohibited": registry.unregistered_replicas_prohibited,
            }
        )
    )
    config_output = tmp_path / "restored-binding.json"
    foundation_config = tmp_path / "foundation.yaml"
    _write_foundation(foundation_config, case)
    assert (
        main(
            [
                "store",
                "restore-bind",
                "--control-root",
                str(case["target"]),
                "--source-root",
                str(case["source"]),
                "--receipt",
                str(receipt_path),
                "--snapshot",
                str(case["snapshot_path"]),
                "--endpoint-ownership",
                str(case["endpoint_path"]),
                "--artefact-manifest",
                str(case["artefact_manifest_path"]),
                "--registry",
                str(registry_path),
                "--actor-id",
                case["actor_id"],
                "--authority-grant-id",
                case["authority_grant_id"],
                "--foundation-config",
                str(foundation_config),
                "--schema-root",
                str(case["code_root"] / ".research-system" / "schemas"),
                "--config-output",
                str(config_output),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    evidence = load_restore_binding_evidence(case["target"])
    assert evidence is not None
    assert output["status"] == (
        "bound"
        if evidence["operation_status"] == "bound-and-config-published" and evidence["durability_status"] == "durable"
        else "pending"
    )
    assert evidence["operation_status"] == "bound-and-config-published"
    fresh = ControlBinding.load(config_output)
    assert fresh.control_root == case["target"].resolve()
    resolved = ControlStoreAuthorityResolver(fresh).resolve(
        record_id=RECORD_ID,
        record_class="canonical_actor",
        authority_root=case["receipt"].store_identity,
        phase="load",
    )
    assert resolved == _record()
    assert (
        sorted(
            (path.relative_to(case["target"]).as_posix(), path.read_bytes())
            for path in (case["target"] / "events").rglob("*.jsonl")
        )
        == before_events
    )


def test_restore_bind_cli_preflights_fresh_binding_failure_before_rebind(tmp_path: Path, monkeypatch) -> None:
    import research_system.cli as cli_module
    from research_system.store.identity import load_restore_binding_evidence

    case, args = _restore_cli_case(tmp_path)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    before_events = sorted(path.read_bytes() for path in (case["target"] / "events").rglob("*.jsonl"))
    original_load = cli_module.ControlBinding.load

    def fail_shadow_load(path):
        if ".restore-binding-" in str(path):
            raise ConfigurationError("simulated fresh binding failure")
        return original_load(path)

    monkeypatch.setattr(cli_module.ControlBinding, "load", staticmethod(fail_shadow_load))
    with pytest.raises(ConfigurationError, match="simulated fresh binding failure"):
        main(args)
    assert manifest_path.read_bytes() == before_manifest
    assert sorted(path.read_bytes() for path in (case["target"] / "events").rglob("*.jsonl")) == before_events
    assert load_restore_binding_evidence(case["target"]) is None
    assert not (tmp_path / "restored-binding.json").exists()


def test_restore_bind_cli_preserves_preexisting_projection_collision(tmp_path: Path) -> None:
    case, args = _restore_cli_case(tmp_path)
    output_path = tmp_path / "restored-binding.json"
    foreign_output = b"foreign output\n"
    output_path.write_bytes(foreign_output)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    assert main(args) == 0

    assert json.loads(manifest_path.read_text(encoding="utf-8"))["control_root"] == str(case["target"].resolve())
    assert load_restore_binding_evidence(case["target"]) is not None
    assert output_path.read_bytes() == foreign_output


def test_restore_bind_cli_rejects_joint_manifest_substitution_against_approved_binding(tmp_path: Path) -> None:
    case, args = _restore_cli_case(tmp_path)
    foreign_code_root = tmp_path / "foreign-code"
    shutil.copytree(case["code_root"], foreign_code_root)
    foreign_schema_root = foreign_code_root / ".research-system" / "schemas"
    for root in (case["source"], case["target"]):
        manifest_path = root / "manifests" / "store-identity.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["code_roots"] = [str(foreign_code_root.resolve())]
        manifest["schema_root"] = str(foreign_schema_root.resolve())
        manifest["manifest_hash"] = sha256_hex(
            canonical_bytes({key: value for key, value in manifest.items() if key != "manifest_hash"})
        )
        manifest_path.write_bytes(canonical_bytes(manifest))
    foreign_foundation = tmp_path / "foreign-foundation.yaml"
    _write_foundation(
        foreign_foundation,
        case,
        code_root=foreign_code_root,
        schema_root=foreign_schema_root,
    )
    foundation_arg = args.index("--foundation-config") + 1
    args[foundation_arg] = str(foreign_foundation)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    before_target = _target_files(case["target"])

    with pytest.raises(ArsError, match="binding|approved"):
        main(args)

    assert manifest_path.read_bytes() == before_manifest
    assert _target_files(case["target"]) == before_target
    assert load_restore_binding_evidence(case["target"]) is None
    assert not (tmp_path / "restored-binding.json").exists()


def _canonical_restore_output(case: dict[str, object]) -> tuple[bytes, Path]:
    from research_system.store.identity import (
        canonical_restore_binding_output,
        restore_binding_output_object_path,
    )

    output = canonical_restore_binding_output(
        case["target"],
        case["receipt"].project_id,
        case["receipt"].store_identity,
        [case["code_root"]],
        case["code_root"] / ".research-system" / "schemas",
    )
    return output, restore_binding_output_object_path(case["target"], sha256_hex(output))


def test_restore_bind_cli_reuses_exact_content_addressed_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case, args = _restore_cli_case(tmp_path)
    expected_output, canonical_output = _canonical_restore_output(case)
    canonical_output.parent.mkdir(parents=True)
    canonical_output.write_bytes(expected_output)

    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    transaction = json.loads(
        (case["target"] / "manifests" / ".restore-binding-transaction.json").read_text(encoding="utf-8")
    )
    assert transaction["state"] == "cleared"
    assert canonical_output.read_bytes() == expected_output
    assert result["config"] == str(canonical_output.resolve())


def test_restore_bind_cli_preserves_wrong_content_addressed_collision(
    tmp_path: Path,
) -> None:
    case, args = _restore_cli_case(tmp_path)
    _, canonical_output = _canonical_restore_output(case)
    canonical_output.parent.mkdir(parents=True)
    foreign = b"foreign bytes under the approved digest name\n"
    canonical_output.write_bytes(foreign)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()

    with pytest.raises(ArsError, match="content-addressed output conflicts"):
        main(args)

    assert canonical_output.read_bytes() == foreign
    assert manifest_path.read_bytes() == before_manifest
    transaction = json.loads(
        (case["target"] / "manifests" / ".restore-binding-transaction.json").read_text(encoding="utf-8")
    )
    assert transaction["state"] == "prepared"
    assert not (case["target"] / "manifests" / "restore-binding-evidence.json").exists()


def test_restore_bind_cli_retry_is_independent_of_mutable_projection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case, args = _restore_cli_case(tmp_path)
    projection = Path(args[args.index("--config-output") + 1])
    assert main(args) == 0
    capsys.readouterr()
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    before_transaction = transaction_path.read_bytes()
    foreign = _foreign_binding_bytes(tmp_path, case)
    projection.write_bytes(foreign)

    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["projection_status"] == "foreign-conflict"
    assert projection.read_bytes() == foreign
    assert transaction_path.read_bytes() == before_transaction


@pytest.mark.parametrize(
    ("durability_step", "retained_state"),
    [
        ("published-record-durable", "published"),
        ("final-validation-durable", "final_validated"),
        ("commit-durable", "committed"),
        ("clear-durable", "cleared"),
    ],
)
def test_restore_bind_cli_retains_record_and_foreign_output_after_validation_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    durability_step: str,
    retained_state: str,
) -> None:
    import research_system.store.identity as identity_module

    case, args = _restore_cli_case(tmp_path)
    foreign = b"foreign canonical output after durable state\n"
    changed: list[Path] = []

    def change_output(path: Path, _state: str, _generation: int) -> None:
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["last_completed_durability_step"] == durability_step and not changed:
            output = case["target"] / record["output_object_path"]
            output.write_bytes(foreign)
            changed.append(output)

    monkeypatch.setattr(identity_module, "_after_restore_transaction_state_written", change_output)
    with pytest.raises(ArsError, match="output does not match"):
        main(args)

    assert len(changed) == 1
    assert changed[0].read_bytes() == foreign
    record = json.loads(
        (case["target"] / "manifests" / ".restore-binding-transaction.json").read_text(encoding="utf-8")
    )
    assert record["state"] == retained_state
    assert not (case["target"] / "manifests" / ".restore-binding-recovery.json").exists()


def test_restore_bind_cli_seals_success_to_store_owned_output_after_last_validation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A foreign caller projection cannot determine canonical restore success."""
    case, args = _restore_cli_case(tmp_path)
    projection_path = Path(args[args.index("--config-output") + 1])
    foreign_output = _foreign_binding_bytes(tmp_path, case)
    projection_path.write_bytes(foreign_output)

    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert projection_path.read_bytes() == foreign_output
    assert result["projection_status"] == "foreign-conflict"

    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    assert transaction_path.is_file()
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert transaction["state"] == "cleared"
    canonical_output = case["target"] / transaction["output_object_path"]
    assert canonical_output.is_file()
    assert sha256_hex(canonical_output.read_bytes()) == transaction["output_object_sha256"]
    assert result["config"] == str(canonical_output.resolve())


def test_restore_recovery_preserves_foreign_output_at_cleanup_mutation_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cleanup preserves a temporary whose ownership changes at the mutation seam."""
    import research_system.store.identity as identity_module

    case, args = _restore_cli_case(tmp_path)
    foreign_output = b"foreign output introduced at cleanup mutation seam\n"
    substituted: list[Path] = []

    def substitute_before_cleanup(path: Path) -> None:
        if path.parent.name == "restore-bindings" and not substituted:
            path.write_bytes(foreign_output)
            substituted.append(path)

    monkeypatch.setattr(identity_module, "_before_restore_owned_temporary_cleanup", substitute_before_cleanup)

    with pytest.raises(ArsError, match="temporary ownership"):
        main(args)

    assert len(substituted) == 1
    assert substituted[0].read_bytes() == foreign_output
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    canonical_output = case["target"] / transaction["output_object_path"]
    assert canonical_output.read_bytes() == foreign_output
    assert transaction["state"] == "prepared"
    assert not (case["target"] / "manifests" / ".restore-binding-recovery.json").exists()


def test_restore_record_transition_failure_never_creates_sibling_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed same-path generation replace never creates a sibling authority."""
    import research_system.store.identity as identity_module

    case, args = _restore_cli_case(tmp_path)
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    original_replace = identity_module.os.replace

    def fail_transaction_transition(source: object, destination: object) -> None:
        if Path(destination).resolve(strict=False) == transaction_path.resolve(strict=False):
            raise OSError("simulated transaction generation replace failure")
        original_replace(source, destination)

    monkeypatch.setattr(identity_module.os, "replace", fail_transaction_transition)

    with pytest.raises(OSError, match="generation replace"):
        main(args)

    assert transaction_path.is_file()
    assert json.loads(transaction_path.read_text(encoding="utf-8"))["state"] == "prepared"
    assert not (case["target"] / "manifests" / ".restore-binding-journal.json").exists()
    assert not (case["target"] / "manifests" / ".restore-binding-recovery.json").exists()


@pytest.mark.parametrize("missing_directory", ("objects", "events", "manifests", "receipts", "snapshots", "runtime"))
def test_restore_bind_cli_retry_rejects_missing_target_directory_without_repairing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    missing_directory: str,
) -> None:
    case, args = _restore_cli_case(tmp_path)
    assert main(args) == 0
    capsys.readouterr()

    missing_path = case["target"] / missing_directory
    shutil.rmtree(missing_path)
    before_target = _path_inventory(case["target"])
    output_path = Path(args[args.index("--config-output") + 1])
    before_output = output_path.read_bytes()

    with pytest.raises(ArsError, match="restore|control|missing|required|preflight"):
        main(args)

    assert _path_inventory(case["target"]) == before_target
    assert not missing_path.exists()
    assert output_path.read_bytes() == before_output


@pytest.mark.parametrize(
    ("crash_point", "retained_state", "loader_allowed"),
    [
        ("prepared-record-durable", "prepared", False),
        ("output-object-durable", "prepared", False),
        ("manifest-durable", "prepared", False),
        ("evidence-durable", "prepared", False),
        ("published-record-durable", "published", False),
        ("final-validation-durable", "final_validated", False),
        ("commit-durable", "committed", False),
        ("clear-durable", "cleared", True),
    ],
)
def test_restore_bind_cli_recovers_after_every_durable_state_crash(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    crash_point: str,
    retained_state: str,
    loader_allowed: bool,
) -> None:
    case, args = _restore_cli_case(tmp_path)
    foundation = Path(args[args.index("--foundation-config") + 1])
    result = _run_restore_crash(args, foundation, crash_point)
    assert result.returncode == 77, result.stderr

    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert transaction["state"] == retained_state
    assert transaction["last_completed_durability_step"] == crash_point
    canonical_output = case["target"] / transaction["output_object_path"]
    if loader_allowed:
        assert ControlBinding.load(canonical_output).control_root == case["target"].resolve()
    else:
        binding_path = tmp_path / "noncleared-binding.json"
        binding_path.write_bytes(
            canonical_bytes(
                {
                    "code_roots": [str(case["code_root"].resolve())],
                    "control_root": str(case["target"].resolve()),
                    "project_id": case["receipt"].project_id,
                    "schema_root": str((case["code_root"] / ".research-system" / "schemas").resolve()),
                    "store_identity": case["receipt"].store_identity,
                }
            )
        )
        with pytest.raises(ArsError, match="restore|control-root|transaction"):
            ControlBinding.load(binding_path)

    assert main(args) == 0
    capsys.readouterr()
    cleared = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert cleared["state"] == "cleared"
    assert ControlBinding.load(case["target"] / cleared["output_object_path"]).control_root == case["target"].resolve()
    assert not (case["target"] / "manifests" / ".restore-binding-journal.json").exists()
    assert not (case["target"] / "manifests" / ".restore-binding-recovery.json").exists()


def test_restore_bind_rejects_a_second_recovery_authority_before_mutation(tmp_path: Path) -> None:
    case, args = _restore_cli_case(tmp_path)
    sibling = case["target"] / "manifests" / ".restore-binding-recovery.json"
    sibling.write_bytes(canonical_bytes({"foreign": "authority"}))
    before = _target_files(case["target"])

    with pytest.raises(ArsError, match="second restore recovery authority"):
        main(args)

    assert _target_files(case["target"]) == before
    assert not (case["target"] / "manifests" / ".restore-binding-transaction.json").exists()


def test_restore_bind_cli_output_publication_failure_retains_prepared_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import research_system.store.identity as identity_module

    case, args = _restore_cli_case(tmp_path)
    expected_output, canonical_output = _canonical_restore_output(case)
    original_link = identity_module.os.link

    def fail_output_link(source: object, destination: object) -> None:
        if Path(destination).resolve(strict=False) == canonical_output.resolve(strict=False):
            raise OSError("simulated output publication failure")
        original_link(source, destination)

    monkeypatch.setattr(identity_module.os, "link", fail_output_link)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    with pytest.raises(OSError, match="simulated output publication failure"):
        main(args)

    assert manifest_path.read_bytes() == before_manifest
    assert not canonical_output.exists()
    transaction = json.loads(
        (case["target"] / "manifests" / ".restore-binding-transaction.json").read_text(encoding="utf-8")
    )
    assert transaction["state"] == "prepared"
    assert transaction["output_object_sha256"] == sha256_hex(expected_output)


def test_restore_bind_cli_rejects_retry_after_governed_grant_revocation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tests.research_system.integration.test_gate5_release_tranche import _revoke_restore_grant

    case, args = _restore_cli_case(tmp_path)
    assert main(args) == 0
    capsys.readouterr()
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    output_path = tmp_path / "restored-binding.json"
    before_output = output_path.read_bytes()
    before_events = sorted(
        (path.relative_to(case["target"]).as_posix(), path.read_bytes())
        for path in (case["target"] / "events").rglob("*.jsonl")
    )

    _revoke_restore_grant(case)

    with pytest.raises(ArsError, match="restore_binding_evidence_mismatch"):
        main(args)
    assert manifest_path.read_bytes() == before_manifest
    assert (
        sorted(
            (path.relative_to(case["target"]).as_posix(), path.read_bytes())
            for path in (case["target"] / "events").rglob("*.jsonl")
        )
        == before_events
    )
    assert output_path.read_bytes() == before_output


def test_restore_bind_retries_require_independent_original_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    case, args = _restore_cli_case(tmp_path)
    assert main(args) == 0
    capsys.readouterr()

    foreign_source = tmp_path / "foreign-source"
    shutil.copytree(case["source"], foreign_source)
    foreign_manifest_path = foreign_source / "manifests" / "store-identity.json"
    foreign_manifest = json.loads(foreign_manifest_path.read_text(encoding="utf-8"))
    foreign_manifest["control_root"] = str(foreign_source.resolve())
    foreign_manifest["manifest_hash"] = sha256_hex(
        canonical_bytes({key: value for key, value in foreign_manifest.items() if key != "manifest_hash"})
    )
    foreign_manifest_path.write_bytes(canonical_bytes(foreign_manifest))
    evidence_path = case["target"] / "manifests" / "restore-binding-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["source_root"] = str(foreign_source.resolve())
    evidence_path.write_bytes(canonical_bytes(evidence))

    with pytest.raises(ArsError, match="source"):
        main(args)
    assert load_store_manifest_unbound(case["target"])["control_root"] == str(case["target"].resolve())


def test_restore_bind_rejects_unsupported_directory_durability(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import research_system.store.identity as identity_module

    case, args = _restore_cli_case(tmp_path)
    manifest_path = case["target"] / "manifests" / "store-identity.json"
    before_manifest = manifest_path.read_bytes()
    monkeypatch.setattr(identity_module, "_fsync_directory", lambda _path: False)

    with pytest.raises(ArsError, match="durab"):
        main(args)

    assert manifest_path.read_bytes() == before_manifest
    assert load_restore_binding_evidence(case["target"]) is None
    assert not (tmp_path / "restored-binding.json").exists()
    transaction_path = case["target"] / "manifests" / ".restore-binding-transaction.json"
    assert json.loads(transaction_path.read_text(encoding="utf-8"))["state"] == "prepared"
    assert not (case["target"] / "manifests" / ".restore-binding-recovery.json").exists()
