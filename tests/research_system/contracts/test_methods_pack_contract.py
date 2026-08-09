from __future__ import annotations

import dataclasses
import json
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from research_system.methods import (
    MethodsPackError,
    load_methods_pack,
    verify_methods_pack_lineage,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
METHODS_ROOT = Path(".research-system/methods")
SCHEMA_ROOT = Path(".research-system/schemas/methods")
SOURCE_SHA256 = "43f65f8dfae9e0cb0a8493e517a3a19cc48432b5329b22345a64dfc731cccf24"
REQUIRED_OUTPUTS = {
    "mth_adversarial_review_protocol": "ReviewFindingSet",
    "mth_counterexample_search_brief": "CounterexampleCandidate",
    "mth_context_deidentification_transform": "DeidentifiedContextSidecar",
    "mth_theorem_retrieval_brief": "TheoremCitation",
    "mth_decomposition_scaffolding_template": "ExploratoryMemo",
}


def _copy_pack(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / METHODS_ROOT, root / METHODS_ROOT)
    shutil.copytree(REPO_ROOT / SCHEMA_ROOT, root / SCHEMA_ROOT)
    return root


def _yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_yaml(path: Path, value: object) -> None:
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
        newline="\n",
    )


def test_methods_pack_public_seam_loads_five_frozen_candidate_assets() -> None:
    pack = load_methods_pack(REPO_ROOT)

    assert pack.pack_id == "research-methods-pack"
    assert pack.pack_version == "1.0.0"
    assert pack.declared_review_state == "candidate"
    assert len(pack.assets) == 5
    assert {asset.asset_id: asset.required_output for asset in pack.assets} == REQUIRED_OUTPUTS
    assert all(asset.compatibility == "any" for asset in pack.assets)
    assert all(asset.declared_review_state == "candidate" for asset in pack.assets)
    assert all(asset.lineage.source_sha256 == SOURCE_SHA256 for asset in pack.assets)
    assert all(asset.permissions for asset in pack.assets)
    assert not any("accepted" in asset.content.lower() for asset in pack.assets)

    with pytest.raises(dataclasses.FrozenInstanceError):
        pack.assets[0].version = "2.0.0"  # type: ignore[misc]


def test_methods_pack_schemas_are_closed_and_validate_current_documents() -> None:
    pairs = (
        ("methods-pack-manifest.schema.json", "methods-pack.yaml"),
        ("methods-pack-revisions.schema.json", "methods-pack-revisions.yaml"),
    )
    for schema_name, document_name in pairs:
        schema = json.loads((REPO_ROOT / SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
        document = _yaml(REPO_ROOT / METHODS_ROOT / document_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(document)
        assert schema["additionalProperties"] is False


def test_methods_pack_rejects_tampered_asset_bytes(tmp_path: Path) -> None:
    root = _copy_pack(tmp_path)
    asset = root / METHODS_ROOT / "assets/adversarial-review-protocol.md"
    asset.write_text(asset.read_text(encoding="utf-8") + "\nUnrecorded mutation.\n", encoding="utf-8")

    with pytest.raises(MethodsPackError, match="identity mismatch"):
        load_methods_pack(root)


@pytest.mark.parametrize("mutation", ["duplicate", "unknown"])
def test_methods_pack_rejects_duplicate_or_unknown_assets(tmp_path: Path, mutation: str) -> None:
    root = _copy_pack(tmp_path)
    manifest_path = root / METHODS_ROOT / "methods-pack.yaml"
    manifest = _yaml(manifest_path)
    assets = manifest["assets"]
    assert isinstance(assets, list)
    if mutation == "duplicate":
        assets.append(dict(assets[0]))
    else:
        assets[0] = dict(assets[0]) | {"asset_id": "mth_unregistered_asset"}
    _write_yaml(manifest_path, manifest)

    with pytest.raises(MethodsPackError, match="duplicate|unknown|manifest asset paths"):
        load_methods_pack(root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("declared_review_state", "accepted", "schema validation failed"),
        ("owner_acceptance", {"actor": "self"}, "schema validation failed"),
        ("base_ref", "candidate-selected", "schema validation failed"),
    ],
)
def test_methods_pack_rejects_local_authority_and_candidate_selected_base(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    root = _copy_pack(tmp_path)
    manifest_path = root / METHODS_ROOT / "methods-pack.yaml"
    manifest = _yaml(manifest_path)
    manifest[field] = value
    _write_yaml(manifest_path, manifest)

    with pytest.raises(MethodsPackError, match=message):
        load_methods_pack(root)


def test_methods_pack_rejects_frontmatter_self_hash(tmp_path: Path) -> None:
    root = _copy_pack(tmp_path)
    asset = root / METHODS_ROOT / "assets/counterexample-search-brief.md"
    text = asset.read_text(encoding="utf-8")
    asset.write_text(text.replace("---\n", "---\ncontent_sha256: deadbeef\n", 1), encoding="utf-8")

    with pytest.raises(MethodsPackError, match="self-hash"):
        load_methods_pack(root)


def test_methods_pack_rejects_sidecar_self_declared_access(tmp_path: Path) -> None:
    root = _copy_pack(tmp_path)
    asset = root / METHODS_ROOT / "assets/context-deidentification-transform.md"
    text = asset.read_text(encoding="utf-8")
    asset.write_text(text + "\nauthorized_consumers: [operator]\n", encoding="utf-8")

    with pytest.raises(MethodsPackError, match="authorized_consumers"):
        load_methods_pack(root)


def test_methods_pack_identity_is_crlf_lf_checkout_stable(tmp_path: Path) -> None:
    root = _copy_pack(tmp_path)
    asset = root / METHODS_ROOT / "assets/theorem-retrieval-brief.md"
    raw = asset.read_bytes()
    assert b"\r\n" not in raw
    asset.write_bytes(raw.replace(b"\n", b"\r\n"))

    pack = load_methods_pack(root)
    assert next(item for item in pack.assets if item.asset_id == "mth_theorem_retrieval_brief")


def test_methods_pack_lineage_citations_exist_in_pinned_source() -> None:
    source = Path("C:/Users/steph/Documents/TDA-Research/01-Literature/Research Papers/Gemini For Research.md")
    if not source.exists():
        pytest.skip("pinned lineage source is external to the repository checkout")
    raw = source.read_bytes()
    pack = load_methods_pack(REPO_ROOT)
    verify_methods_pack_lineage(pack, {SOURCE_SHA256: raw})

    first = pack.assets[0]
    bad_lineage = dataclasses.replace(
        first.lineage,
        sections=("### **2.5 Nonexistent Retrieval Section**",),
    )
    bad_pack = dataclasses.replace(
        pack,
        assets=(dataclasses.replace(first, lineage=bad_lineage), *pack.assets[1:]),
    )
    with pytest.raises(MethodsPackError, match="nonexistent lineage section"):
        verify_methods_pack_lineage(bad_pack, {SOURCE_SHA256: raw})


def test_methods_pack_assets_have_required_operator_sections_and_neutral_bodies() -> None:
    pack = load_methods_pack(REPO_ROOT)
    headings = (
        "## Purpose",
        "## Applicability",
        "## Operator protocol",
        "## Required RM-03 output",
        "## Failure modes",
        "## Worked example",
        "## Verified lineage",
    )
    for asset in pack.assets:
        assert all(heading in asset.content for heading in headings)
        body_before_lineage = asset.content.split("## Verified lineage", 1)[0].lower()
        assert "gemini" not in body_before_lineage
        assert "openai" not in body_before_lineage
