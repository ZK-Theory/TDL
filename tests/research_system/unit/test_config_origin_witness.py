from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

import research_system.config as config_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ApprovedProjectBinding, ControlBinding, _canonical_local_cli_uri
from research_system.errors import ConfigurationError
from research_system.store.identity import (
    build_store_origin_witness,
    persist_store_origin_witness,
)
from research_system.store.layout import require_external_control_root


PROJECT_ID = "prj_01978abc-0001-7000-8000-000000000001"


def _materialized_foundation(
    tmp_path: Path,
    *,
    include_retired_code_root: bool = False,
) -> tuple[Path, dict[str, object]]:
    code_root = tmp_path / "code"
    schema_root = code_root / ".research-system" / "schemas"
    schema_root.mkdir(parents=True)
    origin_root = tmp_path / "origin-authority"
    origin_root.mkdir()
    control_root = tmp_path / "control"
    require_external_control_root([code_root], control_root)
    code_roots = [str(code_root.resolve())]
    retired_code_root = tmp_path / "retired-code-root"
    if include_retired_code_root:
        retired_code_root.mkdir()
        code_roots.append(str(retired_code_root.resolve()))
    code_roots.sort()
    manifest = {
        "schema_id": "ars://core/store-identity",
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "store_identity": "a" * 64,
        "control_root": str(control_root.resolve()),
        "code_roots": code_roots,
        "schema_root": str(schema_root.resolve()),
        "schema_binding_version": "1.0.0",
        "endpoint_scheme": "local-cli",
    }
    manifest["manifest_hash"] = sha256_hex(canonical_bytes(manifest))
    (control_root / "manifests" / "store-identity.json").write_bytes(canonical_bytes(manifest))
    witness = build_store_origin_witness(manifest, initial_control_root=control_root)
    witness_path = persist_store_origin_witness(witness, origin_root)
    if include_retired_code_root:
        retired_code_root.rmdir()
    foundation = {
        "schema_version": "1.0.0",
        "project_id": PROJECT_ID,
        "control_root": str(control_root.resolve()),
        "control_root_required": True,
        "store_identity": manifest["store_identity"],
        "endpoint_scheme": "local-cli",
        "canonical_hash": "sha256",
        "canonical_uri": _canonical_local_cli_uri(control_root.resolve()),
        "canonical_tail_position": 0,
        "canonical_tail_hash": "0" * 64,
        "code_roots": code_roots,
        "schema_root": str(schema_root.resolve()),
        "origin_authority_root": str(origin_root.resolve()),
        "origin_witness_path": str(witness_path.resolve()),
        "origin_witness_sha256": witness.raw_sha256,
    }
    foundation["foundation_sha256"] = sha256_hex(canonical_bytes(foundation))
    foundation_path = tmp_path / "foundation.yaml"
    foundation_path.write_text(yaml.safe_dump(foundation, sort_keys=False), encoding="utf-8")
    return foundation_path, foundation


def test_approved_binding_loads_foundation_pinned_witness_before_store(tmp_path: Path):
    foundation_path, foundation = _materialized_foundation(tmp_path)

    binding = ApprovedProjectBinding.load(foundation_path)
    assert binding.origin_witness_sha256 == foundation["origin_witness_sha256"]
    assert binding.origin_witness.initial_control_root == str(binding.control_root)


@pytest.mark.parametrize("missing_child", ["objects", "events", "manifests", "receipts", "snapshots", "runtime"])
def test_approved_binding_rejects_partial_store_without_repair(
    tmp_path: Path,
    missing_child: str,
) -> None:
    foundation_path, foundation = _materialized_foundation(tmp_path)
    control_root = Path(str(foundation["control_root"]))
    shutil.rmtree(control_root / missing_child)
    before = {
        str(path.relative_to(control_root)): ("dir" if path.is_dir() else path.read_bytes())
        for path in control_root.rglob("*")
    }

    with pytest.raises(ConfigurationError, match="matching materialized store"):
        ApprovedProjectBinding.load(foundation_path)

    after = {
        str(path.relative_to(control_root)): ("dir" if path.is_dir() else path.read_bytes())
        for path in control_root.rglob("*")
    }
    assert after == before
    assert not (control_root / missing_child).exists()


def test_approved_binding_preserves_unavailable_historical_code_root(tmp_path: Path):
    foundation_path, foundation = _materialized_foundation(tmp_path, include_retired_code_root=True)

    binding = ApprovedProjectBinding.load(foundation_path)
    control_binding = ControlBinding.from_raw(
        yaml.safe_dump(
            {
                "code_roots": foundation["code_roots"],
                "control_root": foundation["control_root"],
                "project_id": foundation["project_id"],
                "schema_root": foundation["schema_root"],
                "store_identity": foundation["store_identity"],
            },
            sort_keys=False,
        ).encode("utf-8"),
        approved=binding,
    )

    assert [str(root) for root in binding.code_roots] == foundation["code_roots"]
    assert control_binding.code_roots == binding.code_roots


def test_approved_binding_rejects_substituted_unavailable_historical_code_root(tmp_path: Path):
    foundation_path, foundation = _materialized_foundation(tmp_path, include_retired_code_root=True)
    value = dict(foundation)
    value["code_roots"] = [
        str((tmp_path / "foreign-retired-code-root").resolve(strict=False))
        if root.endswith("retired-code-root")
        else root
        for root in foundation["code_roots"]
    ]
    value["code_roots"].sort()
    value.pop("foundation_sha256")
    value["foundation_sha256"] = sha256_hex(canonical_bytes(value))
    foundation_path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="materialized store code roots"):
        ApprovedProjectBinding.load(foundation_path)


def test_approved_binding_rejects_unbound_local_cli_alias(tmp_path: Path):
    foundation_path, foundation = _materialized_foundation(tmp_path)
    value = dict(foundation)
    value["canonical_uri"] = "local-cli://control"
    value.pop("foundation_sha256")
    value["foundation_sha256"] = sha256_hex(canonical_bytes(value))
    foundation_path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="materialized control root"):
        ApprovedProjectBinding.load(foundation_path)


@pytest.mark.parametrize("mutation", ["path", "digest", "foundation"])
def test_config_cannot_substitute_an_alternate_witness_or_unapproved_bytes(tmp_path: Path, mutation: str):
    foundation_path, foundation = _materialized_foundation(tmp_path)
    value = dict(foundation)
    if mutation == "path":
        value["origin_witness_path"] = str((tmp_path / "wrong.json").resolve())
    elif mutation == "digest":
        value["origin_witness_sha256"] = "b" * 64
    else:
        value["canonical_uri"] = "local-cli://changed"
    if mutation != "foundation":
        value["foundation_sha256"] = sha256_hex(canonical_bytes(value))
    foundation_path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")

    with pytest.raises(ConfigurationError):
        ApprovedProjectBinding.load(foundation_path)


def test_control_binding_from_raw_uses_supplied_approved_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    foundation_path, foundation = _materialized_foundation(tmp_path)
    approved = ApprovedProjectBinding.from_raw(foundation_path.read_bytes())
    binding_raw = yaml.safe_dump(
        {
            "code_roots": foundation["code_roots"],
            "control_root": foundation["control_root"],
            "project_id": foundation["project_id"],
            "schema_root": foundation["schema_root"],
            "store_identity": foundation["store_identity"],
        },
        sort_keys=False,
    ).encode("utf-8")

    def unexpected_reload(cls, path: Path):
        raise AssertionError(f"foundation was reloaded from {path}")

    monkeypatch.setattr(ApprovedProjectBinding, "load", classmethod(unexpected_reload))
    binding = ControlBinding.from_raw(binding_raw, approved=approved)

    assert binding.project_id == approved.project_id
    assert binding.control_root == approved.control_root
    assert binding.store_identity == approved.store_identity


def test_control_binding_load_rejects_foundation_root_omitted_from_approved_code_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    foundation_path, foundation = _materialized_foundation(tmp_path)
    unapproved_root = tmp_path / "unapproved-executing-root"
    canonical_path = unapproved_root / ".research-system" / "config" / "foundation.yaml"
    canonical_path.parent.mkdir(parents=True)
    canonical_path.write_bytes(foundation_path.read_bytes())
    binding_path = tmp_path / "binding.yaml"
    binding_path.write_text(
        yaml.safe_dump(
            {
                "code_roots": foundation["code_roots"],
                "control_root": foundation["control_root"],
                "project_id": foundation["project_id"],
                "schema_root": foundation["schema_root"],
                "store_identity": foundation["store_identity"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(config_module, "canonical_foundation_path", lambda: canonical_path)

    with pytest.raises(ConfigurationError, match="canonical foundation root"):
        ControlBinding.load(binding_path)
