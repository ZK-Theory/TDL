"""Independent admission controls for the inert W11 expected catalogue."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import SchemaError
import tools.verify_w11_materialization as w11_verifier


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOGUE_PATH = REPO_ROOT / ".research-system" / "evals" / "expected" / "w11-portfolio-discovery-v1.json"
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas" / "contracts" / "w11"
OWNER_ROW_IDS = tuple([f"OR-{index:03d}" for index in range(1, 42)] + [f"OR-{index:03d}" for index in range(101, 141)])


def _catalogue() -> dict[str, object]:
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def _owner_row(catalogue: dict[str, object], owner_row_id: str) -> dict[str, object]:
    rows = catalogue["owner_contract_rows"]
    assert isinstance(rows, list)
    return next(row for row in rows if row["owner_row_id"] == owner_row_id)


def test_w11_expected_catalogue_admits_the_exact_static_subject() -> None:
    catalogue = _catalogue()
    w11_verifier.verify_expected_catalogue(REPO_ROOT, catalogue)


def test_w11_expected_catalogue_has_closed_counts_and_non_circular_hashes() -> None:
    catalogue = _catalogue()
    schema_rows = catalogue["schema_source_rows"]
    owner_rows = catalogue["owner_contract_rows"]

    assert len(schema_rows) == 62
    assert len(owner_rows) == 81
    assert tuple(row["owner_row_id"] for row in owner_rows) == OWNER_ROW_IDS
    assert tuple(row["repository_path"] for row in schema_rows) == tuple(
        sorted(row["repository_path"] for row in schema_rows)
    )
    assert len({row["repository_path"] for row in schema_rows}) == 62
    assert len({row["schema_id"] for row in schema_rows}) == 62
    assert "catalogue_content_hash" not in catalogue
    assert catalogue["content_hash"] == sha256_hex(
        canonical_bytes({key: value for key, value in catalogue.items() if key != "content_hash"})
    )
    assert catalogue["owner_row_range_hash"] == sha256_hex(canonical_bytes(list(OWNER_ROW_IDS)))


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_row",
        "duplicate_row",
        "swapped_subject",
        "removed_ordered_effect",
        "blank_reducer",
        "blank_projection",
        "aliased_test_identity",
        "alternate_producer",
        "self_edge",
        "back_edge",
    ),
)
def test_w11_expected_catalogue_rejects_decisive_catalogue_mutations(mutation: str) -> None:
    catalogue = _catalogue()
    rows = catalogue["owner_contract_rows"]
    assert isinstance(rows, list)

    if mutation == "missing_row":
        del rows[0]
    elif mutation == "duplicate_row":
        rows.append(copy.deepcopy(rows[0]))
    elif mutation == "swapped_subject":
        first = _owner_row(catalogue, "OR-001")
        second = _owner_row(catalogue, "OR-002")
        first["authority_subject"], second["authority_subject"] = (
            second["authority_subject"],
            first["authority_subject"],
        )
    elif mutation == "removed_ordered_effect":
        effects = _owner_row(catalogue, "OR-003")["ordered_events"]
        assert isinstance(effects, list) and len(effects) >= 2
        effects.pop()
    elif mutation == "blank_reducer":
        _owner_row(catalogue, "OR-001")["reducer"] = ""
    elif mutation == "blank_projection":
        _owner_row(catalogue, "OR-001")["projection_targets"] = []
    elif mutation == "aliased_test_identity":
        row = _owner_row(catalogue, "OR-001")
        row["negative_mutation_test_identity"] = row["positive_test_identity"]
    elif mutation == "alternate_producer":
        _owner_row(catalogue, "OR-001")["eligible_profile"] = "independent verifier"
    elif mutation == "self_edge":
        catalogue["source_refs"][0]["locator"] = ".research-system/evals/expected/w11-portfolio-discovery-v1.json"
    elif mutation == "back_edge":
        _owner_row(catalogue, "OR-001")["file_observation_ref"]["id"] = w11_verifier.W11_CATALOGUE_RECORD_ID
    else:
        raise AssertionError(f"unhandled mutation: {mutation}")

    with pytest.raises(SchemaError):
        w11_verifier.verify_expected_catalogue(REPO_ROOT, catalogue)


def test_w11_expected_catalogue_rejects_a_late_schema(tmp_path: Path) -> None:
    schema_root = tmp_path / "w11"
    shutil.copytree(SCHEMA_ROOT, schema_root)
    late_schema_path = schema_root / "late-schema.schema.json"
    late_schema_path.write_text(
        json.dumps(
            {
                "$id": "ars://portfolio/late-schema",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "additionalProperties": False,
                "properties": {"schema_id": {"const": "ars://portfolio/late-schema"}},
                "required": ["schema_id"],
                "title": "Late schema",
                "type": "object",
                "version": "1.0.0",
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(SchemaError):
        w11_verifier.verify_expected_catalogue(REPO_ROOT, _catalogue(), schema_root=schema_root)


def test_coordinated_catalogue_runtime_mutation_cannot_rescue_expected_source() -> None:
    catalogue = _catalogue()
    runtime_shadow = copy.deepcopy(catalogue)
    _owner_row(catalogue, "OR-001")["authority_subject"] = "coordinated catalogue mutation"
    _owner_row(runtime_shadow, "OR-001")["authority_subject"] = "coordinated runtime mutation"

    with pytest.raises(SchemaError):
        w11_verifier.verify_expected_catalogue(REPO_ROOT, catalogue)


def test_runtime_bindings_and_projection_sources_are_byte_unchanged_from_foundation() -> None:
    paths = subprocess.run(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            w11_verifier.W11_FOUNDATION_COMMIT,
            "--",
            "research_system",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert paths

    for relative_path in paths:
        expected = subprocess.run(
            ["git", "show", f"{w11_verifier.W11_FOUNDATION_COMMIT}:{relative_path}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        ).stdout
        current = (REPO_ROOT / relative_path).read_bytes().replace(b"\r\n", b"\n")
        assert current == expected, relative_path
