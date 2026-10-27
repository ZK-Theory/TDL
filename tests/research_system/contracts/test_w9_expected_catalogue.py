# Research context: docs/plans/agentic-research-system/transition/w9/wp9-1-stage-b-design-note.md (WP9.1 B1; P-072, P-074)
# Purpose: controls for tools/verify_w9_materialization.py: the pinned annex, per-row W9-C01/W9-C03, and refusals.
"""Controls for the W9 catalogue verifier (WP9.1 stage B1).

The verifier's expected side is the owner annex, pinned by blob, together with Git and the bootstrap contract. These
controls cover the following (B1 review B-1, B-2, M-1, M-2, m-1 to m-3 and m-8):
- the pinned annex is the committed one;
- each row's W9-C01 positive control and W9-C03 mutation control, under W11's test-ID scheme;
- a golden literal row;
- every refusal the verifier owes.

From B2 the committed catalogue exists. Most controls here use the catalogue the verifier expects for this checkout,
built at ``HEAD``, with ``HEAD`` as the main ref. The B2 controls read the committed catalogue, with ``origin/main`` as
the main ref. After Stephen's O-8 acceptance (P-075), the committed catalogue and annex are also pinned to the
accepted bytes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
# Revision 3's annex before the confirmation's residuals were folded (B1 review probe P2), as literals. Its commit,
# 8a0d68fc, is a branch commit that a squash merge leaves off main, so the control must not read it (re-review R-M2).
PRE_FOLD_ANNEX_IDENTITY = {
    "repository_path": "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml",
    "git_commit": "8a0d68fc6038bd815dea0686eeb9f38543035da3",  # commit-literal: data
    "git_blob": "4e648b7f28f8925643ccf3559e943b1e59510491",
    "file_length": 85510,
    "file_sha256": "cd4838767c24ed070709f9c53a94abcc59a66cd8fb6d0b00229f8e5b80d39377",
}
STAGE_A_MAIN = "5d325c5b"  # main before stage B: it holds no annex, and an older W9 family
PRE_W9_MAIN = "d660f091"  # main before stage A: it holds no W9 family at all


@lru_cache(maxsize=None)
def _verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_w9_verify", REPO_ROOT / "tools" / "verify_w9_materialization.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V = _verifier()
ROW_IDS = V.W9_OWNER_ROW_IDS


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()


@lru_cache(maxsize=None)
def _expected() -> dict[str, Any]:
    return V.expected_catalogue(_head(), _head())


def _catalogue() -> dict[str, Any]:
    return deepcopy(_expected())


def _resign(catalogue: dict[str, Any]) -> dict[str, Any]:
    unsigned = {key: value for key, value in catalogue.items() if key != "content_hash"}
    catalogue["content_hash"] = V.sha256_hex(V.canonical_bytes(unsigned))
    return catalogue


def _problems(catalogue: Any, main_ref: str | None = None) -> list[str]:
    return V.verify_catalogue(catalogue, main_ref or _head())


def _independent_annex_rows() -> dict[str, dict[str, Any]]:
    """The pinned annex, read by blob through a plain YAML parse, independently of the verifier's loader."""
    data = subprocess.run(
        ["git", "cat-file", "blob", V.W9_ANNEX_BLOB], cwd=REPO_ROOT, capture_output=True, check=True
    ).stdout
    assert hashlib.sha256(data).hexdigest() == V.W9_ANNEX_SHA256
    return {row["owner_row_id"]: row for row in yaml.safe_load(data.decode("utf-8"))["rows"]}


# --- The pinned annex ------------------------------------------------------------------------------------------------


def test_pinned_annex_is_the_committed_annex_and_passes_its_rules() -> None:
    blob = subprocess.run(
        ["git", "rev-parse", f"HEAD:{V.ANNEX_PATH}"], cwd=REPO_ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    assert blob == V.W9_ANNEX_BLOB
    assert V.check_annex(V.pinned_annex()) == []
    assert tuple(_independent_annex_rows()) == ROW_IDS


def test_expected_catalogue_verifies_clean() -> None:
    assert _problems(_catalogue()) == []


# --- W9-C01 and W9-C03, per row (W11's scheme: test_w11_expected_catalogue.py:47-96) -------------------------------


@pytest.mark.parametrize("row_id", ROW_IDS, ids=[f"W9-C01-{row_id}" for row_id in ROW_IDS])
def test_w9_c01_row_matches_the_annex(row_id: str) -> None:
    annex_row = _independent_annex_rows()[row_id]
    row = next(r for r in _expected()["owner_contract_rows"] if r["owner_row_id"] == row_id)
    for field in V.COPIED_FIELDS:
        assert row[field] == annex_row[field], field
    # The derived fields, against the independent parse rather than derive_row (B1 re-review r-3).
    assert row["logical_key"] == annex_row["logical_key"]
    assert row["receipt_identity"] == annex_row["receipt_identity"]
    assert (
        row["complete_write_set"] == [e["event"] for e in annex_row["ordered_events"]] + annex_row["affected_streams"]
    )
    assert row["owner_annex_ref"]["repository_path"] == (
        "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml"
    )
    assert row["owner_annex_ref"]["git_blob"] == "d8fbda416b016f5e19c03689f336caff3166d0d9"
    assert row["owner_annex_ref"]["file_sha256"] == "36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc"
    assert row["owner_annex_ref"]["row_sha256"] == V.sha256_hex(V.canonical_bytes(annex_row))
    assert row["positive_test_identity"] == f"W9-C01-{row_id}"
    assert row["negative_mutation_test_identity"] == f"W9-C03-{row_id}-owner-row-mutation"
    assert row["retry_test_identity"] == f"W9-C11-{row_id}"


@pytest.mark.parametrize("row_id", ROW_IDS, ids=[f"W9-C03-{row_id}-owner-row-mutation" for row_id in ROW_IDS])
def test_w9_c03_any_field_mutation_is_detected(row_id: str) -> None:
    expected = _expected()["owner_contract_rows"]
    index = ROW_IDS.index(row_id)
    for field in (*V.COPIED_FIELDS, *V.DERIVED_FIELDS):
        rows = deepcopy(expected)
        value = rows[index][field]
        rows[index][field] = {"mutated": True} if isinstance(value, dict) else "mutated"
        problems = V.compare_rows(rows, expected)
        assert problems == [f"{row_id}: field {field} differs from the annex-derived value"], (field, problems)


def test_a_row_mutation_fails_the_whole_catalogue() -> None:
    # The full path: a mutated row in a re-signed catalogue is refused by verify_catalogue itself.
    catalogue = _catalogue()
    catalogue["owner_contract_rows"][19]["authority_subject"] = "exact decision-proposal subject, loosened"
    problems = _problems(_resign(catalogue))
    assert "LR-020: field authority_subject differs from the annex-derived value" in problems


def test_golden_row_lr_020() -> None:
    # A literal check, so the derivation is not proved only against itself (B1 review M-2).
    row = _expected()["owner_contract_rows"][19]
    assert row["owner_row_id"] == "LR-020"
    assert row["complete_write_set"] == [
        "W2:DecisionResolved",
        "E:legacy-closed-reference-acceptance-recorded",
        "E:legacy-ownership-transitioned-recorded",
        "record stream of the pre-assigned legacy_closed_reference_acceptance ID",
        "legacy_closed_reference_acceptance index",
    ]
    assert row["receipt_identity"] == "R:resolve-w9-authority-decision/legacy_closed_reference_acceptance"
    assert row["reducer"] == "U:legacy-closed-reference-acceptance, U:legacy-ownership-transitioned"
    assert row["owner_annex_ref"]["repository_path"] == (
        "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml"
    )
    assert row["owner_annex_ref"]["git_blob"] == "d8fbda416b016f5e19c03689f336caff3166d0d9"
    assert row["owner_annex_ref"]["file_sha256"] == "36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc"
    assert (
        _expected()["owner_row_range_hash"]
        == hashlib.sha256(json.dumps(sorted(ROW_IDS), separators=(",", ":")).encode("utf-8")).hexdigest()
    )


# --- Refusals: the catalogue's non-row fields (B1 review B-1) ------------------------------------------------------


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (lambda c: c.update(unexpected_key=1), "schema:"),
        (lambda c: c.update(record_id="obj_00000000-0000-7000-8000-000000000001"), "record_id"),
        (lambda c: c.update(project_id="prj_00000000-0000-7000-8000-000000000002"), "project_id"),
        (lambda c: c["owner_spec_identity"].update(raw_bytes=1), "owner_spec_identity"),
        (lambda c: c["schema_source_rows"][0].update(git_blob="0" * 40), "schema_source_rows do not match"),
        (lambda c: c["schema_source_rows"].pop(), "schema_source_rows do not match"),
        (lambda c: c.update(owner_row_count=1), "owner_row_count"),
        (lambda c: c.update(owner_row_range_hash="0" * 64), "owner_row_range_hash"),
        (lambda c: c.update(global_preconditions=["G1"]), "global_preconditions"),
        (lambda c: c["owner_contract_rows"].pop(), "rows in the catalogue"),
    ],
)
def test_non_row_field_errors_are_refused(change: Any, expected: str) -> None:
    catalogue = _catalogue()
    change(catalogue)
    problems = _problems(_resign(catalogue))
    assert any(expected in problem for problem in problems), problems


def test_stale_content_hash_is_refused() -> None:
    catalogue = _catalogue()
    catalogue["owner_row_count"] = 61  # unchanged value, unsigned edit below
    catalogue["created_at"] = "2026-10-25T00:00:00Z"
    assert any("content_hash" in problem for problem in _problems(catalogue))


def test_schema_source_commit_off_main_is_refused() -> None:
    assert any("schema source commit is not on" in p for p in _problems(_catalogue(), main_ref=STAGE_A_MAIN))


def _catalogue_with_schema_commit(revision: str) -> dict[str, Any]:
    catalogue = _catalogue()
    catalogue["schema_source_rows"] = V.expected_schema_source_rows(V.resolve_commit(revision))
    return _resign(catalogue)


def test_schema_changed_after_its_source_commit_is_refused() -> None:
    # Stage A's main commit is on main and its rows match its own files, but the catalogue-content schema changed
    # afterwards, so only the HEAD-drift check can refuse it (B1 re-review r-2).
    problems = _problems(_catalogue_with_schema_commit(STAGE_A_MAIN))
    drift = f"{V.SCHEMA_DIR}/w9-schema-catalogue-content.schema.json changed after the schema source commit"
    assert drift in problems, problems


def test_contract_family_at_the_schema_commit_must_be_heads() -> None:
    # Stage A's contract lists 17 schemas; HEAD's lists 19 (B1 re-review r-4).
    problems = _problems(_catalogue_with_schema_commit(STAGE_A_MAIN))
    assert "the bootstrap contract's family at the schema source commit differs from HEAD's" in problems, problems


def test_head_contract_must_list_the_pinned_family(monkeypatch: pytest.MonkeyPatch) -> None:
    real = V.family_parts
    monkeypatch.setattr(V, "family_parts", lambda commit: (real(commit)[0][:-1], real(commit)[1]))
    problems = _problems(_catalogue())
    assert "the bootstrap contract at HEAD does not list the pinned W9 record and bootstrap family" in problems


def test_contract_owner_identities_at_the_schema_commit_must_be_heads(monkeypatch: pytest.MonkeyPatch) -> None:
    real = V.expected_owner_identities

    def drifted(commit: str) -> dict[str, Any]:
        owners = deepcopy(real(commit))
        if commit != "HEAD":
            owners["owner_spec_identity"]["git_blob"] = "0" * 40
        return owners

    monkeypatch.setattr(V, "expected_owner_identities", drifted)
    problems = _problems(_catalogue())
    assert "the bootstrap contract's owner identities at the schema source commit differ from HEAD's" in problems


def test_schema_commit_without_the_w9_family_is_a_problem_not_a_traceback() -> None:
    catalogue = _catalogue()
    for row in catalogue["schema_source_rows"]:
        row["git_commit"] = V.resolve_commit(PRE_W9_MAIN)
    problems = _problems(_resign(catalogue))
    assert "the W9 family or its bootstrap contract is not complete at the schema source commit" in problems


@pytest.mark.parametrize(
    "rows",
    [["x"], [{"git_commit": ["not", "a", "string"]}], [], "not a list"],
    ids=["string-row", "list-commit", "empty", "not-a-list"],
)
def test_malformed_schema_source_rows_are_a_problem_not_a_traceback(rows: Any) -> None:
    catalogue = _catalogue()
    catalogue["schema_source_rows"] = rows
    problems = _problems(_resign(catalogue))
    assert "schema_source_rows do not all name one full commit SHA in this repository" in problems


# --- Refusals: the expected side (B1 review B-2) -------------------------------------------------------------------


def test_annex_at_a_commit_off_main_is_refused() -> None:
    # Match the annex's own ancestry message: the schema source check also fails on this ref (B1 re-review r-1).
    problems = _problems(_catalogue(), main_ref=STAGE_A_MAIN)
    assert f"owner_annex_identity.git_commit is not on {STAGE_A_MAIN}" in problems, problems


def test_catalogue_cannot_choose_the_pre_fold_annex() -> None:
    catalogue = _catalogue()
    catalogue["owner_annex_identity"] = dict(PRE_FOLD_ANNEX_IDENTITY)
    problems = _problems(_resign(catalogue))
    assert "owner_annex_identity does not name the pinned annex blob, SHA-256 and size" in problems, problems


def test_annex_commit_without_the_annex_is_refused() -> None:
    catalogue = _catalogue()
    catalogue["owner_annex_identity"]["git_commit"] = V.resolve_commit(STAGE_A_MAIN)
    problems = _problems(_resign(catalogue))
    assert any("does not hold the pinned annex blob" in p for p in problems), problems


def test_non_object_catalogue_is_a_problem_not_a_traceback() -> None:
    assert _problems([]) == ["the catalogue is not a JSON object"]


# --- Refusals: annex rules (P-073 item 1; B1 review m-2) -----------------------------------------------------------


def _first(annex: dict[str, Any], reason: str | None) -> dict[str, Any]:
    return next(row for row in annex["rows"] if row["w9c_only_reason"] == reason)


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda a: _first(a, "authority_flow_step").update(binding_tests=[]), "must bind a W9-C2x test"),
        (lambda a: _first(a, "authority_flow_step").update(w9c_only_reason=None), "needs a w9c_only_reason"),
        (lambda a: _first(a, None).update(w9c_only_reason="authority_flow_step"), "carries a w9c_only_reason"),
        (lambda a: _first(a, "authority_flow_step").update(binding_tests=["W9-C29"]), "not a declared W9-C2x"),
        (lambda a: _first(a, None).update(binding_tests=["W9-T24"]), "outside W9 §17"),
        (lambda a: a["catalogue_tests"].pop("W9-C24"), "catalogue_tests"),
        (lambda a: a["rows"][0].update(owner_row_id="LR-099"), "LR-001 to LR-061"),
        (lambda a: a["rows"][1].update(payload_discriminant=a["rows"][0]["payload_discriminant"]), "unique"),
        (lambda a: a["rows"][0].update(command_type="NewCommand"), "command-type set"),
        (lambda a: a["rows"][0].update(eligible_actor="manager"), "closed set"),
        (lambda a: a["rows"][0].update(resolver="anyone"), "resolver"),
        (lambda a: a["rows"][4].update(eligible_actor="migration_analyst"), "submitted by Stephen"),
        (lambda a: a["rows"][0].update(projection_targets=["not a P token"]), "P: tokens"),
        (lambda a: a["rows"][0].update(reducer="nope"), "U: token"),
        (
            lambda a: a["rows"][0].update(record_schema_id="ars://legacy/w9-materialization-bootstrap-contract"),
            "not a W9 record or import schema",
        ),
        (lambda a: a["rows"][0].update(record_schema_version="2.0.0"), "record_schema_version"),
        (lambda a: _first(a, None).update(pilot_promotion_fixtures=[{"fixture_id": "F-039", "when": None}]), "F-001"),
        (lambda a: a["rows"][0]["ordered_events"][0].update(multiplicity="many"), "multiplicity"),
        (lambda a: a["rows"][0]["ordered_events"][0].update(event="E:bad token"), "malformed"),
        (lambda a: a["rows"][0].update(receipt_identity="R:other"), "receipt_identity"),
        (lambda a: a["rows"][0].pop("source_refs"), "annex row fields"),
    ],
)
def test_annex_rule_violations_are_refused(mutate: Any, expected: str) -> None:
    annex = deepcopy(V.pinned_annex())
    mutate(annex)
    problems = V.check_annex(annex)
    assert any(expected in problem for problem in problems), problems


def test_a_conditional_event_needs_its_condition() -> None:
    annex = deepcopy(V.pinned_annex())
    row = next(r for r in annex["rows"] if any(e["multiplicity"] == "0..n" for e in r["ordered_events"]))
    next(e for e in row["ordered_events"] if e["multiplicity"] == "0..n")["condition"] = None
    assert any("needs its condition" in p for p in V.check_annex(annex))


def test_duplicate_yaml_keys_are_refused() -> None:
    with pytest.raises(yaml.YAMLError):
        V.strict_yaml(b"rows:\n- resolver: stephen\n  resolver: none\n")


# --- The command line (B1 review M-1, m-8) -------------------------------------------------------------------------


def test_missing_named_catalogue_fails() -> None:
    assert V.main(["--catalogue", "does/not/exist.json"]) == 1


def test_required_catalogue_passes() -> None:
    # Stage B2 replaces B1's absence check (design note §6; B1 re-review r-6).
    assert (REPO_ROOT / V.CATALOGUE_PATH).exists()
    assert V.main(["--require-catalogue"]) == 0


def test_required_absent_catalogue_still_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # B1 review M-1's control stays: with no catalogue at the default path, --require-catalogue fails, and it fails on
    # that guard rather than on some other problem (B2 review i-2).
    monkeypatch.setattr(V, "CATALOGUE_PATH", ".research-system/evals/expected/does-not-exist.json")
    assert V.main(["--require-catalogue"]) == 1
    assert "no catalogue at" in capsys.readouterr().err


def test_annex_only_run_passes() -> None:
    assert V.main([]) == 0


# --- The committed catalogue (B2 review m-2, m-4) ------------------------------------------------------------------

B1_MAIN = "fc5f356ba3488d8250180e15bc9b7df8a9a2e12a"  # B1's squash commit on main; the catalogue's pin (note §6)
LEGACY_INSTANCE_IDS = frozenset(
    {"ars://legacy/w9-schema-catalogue-content", "ars://legacy/w9-catalogue-acceptance-envelope"}
)


def _is_b1_main_output(data: bytes) -> bool:
    return data == V.canonical_bytes(V.expected_catalogue(B1_MAIN, B1_MAIN))


def test_committed_catalogue_is_the_verifier_output_at_b1_main() -> None:
    # The verifier compares objects, so it passes a re-encoding or a re-signed created_at. O-8 accepts one byte string.
    assert _is_b1_main_output((REPO_ROOT / V.CATALOGUE_PATH).read_bytes())


def test_byte_identity_refuses_a_re_encoding_or_a_new_created_at() -> None:
    data = (REPO_ROOT / V.CATALOGUE_PATH).read_bytes()
    catalogue = json.loads(data)
    re_encoded = json.dumps(catalogue, indent=2, sort_keys=True).encode()
    assert not _is_b1_main_output(re_encoded)
    assert not _is_o8_accepted(re_encoded, "catalogue")
    assert not _is_o8_accepted(data + b"\n", "catalogue")
    assert not _is_o8_accepted(data + b"\r\n", "catalogue")
    catalogue["created_at"] = "2030-01-01T00:00:00Z"
    catalogue["content_hash"] = V.sha256_hex(
        V.canonical_bytes({key: value for key, value in catalogue.items() if key != "content_hash"})
    )
    assert V.verify_catalogue(catalogue) == []  # the verifier alone passes it
    assert not _is_b1_main_output(V.canonical_bytes(catalogue))
    assert not _is_o8_accepted(V.canonical_bytes(catalogue), "catalogue")


# Stephen's O-8 acceptance (P-075): the catalogue and the owner annex at main commit 7979e85a, by blob and SHA-256.
# Literals until WP9.2 adds accepted_w9.py (P-066), as W11's catalogue is pinned from accepted_w11.py. After O-8 any row
# change is a new catalogue identity and needs a new acceptance (B2 confirmation c-i3).
O8_ACCEPTED = {
    "main_commit": "7979e85a075ab6a643a7b201ac4186b0b2090d74",
    "catalogue": {
        "path": V.CATALOGUE_PATH,
        "blob": "d1916ffd380050f193fb2c927bb4d724cd2f8a88",
        "sha256": "f7e2d9e2deac022790c296a4962ea3feb7feb1e646da125edf7819ff8719db8c",
        "bytes": 128583,
    },
    "annex": {
        "path": V.ANNEX_PATH,
        "blob": "d8fbda416b016f5e19c03689f336caff3166d0d9",
        "sha256": "36a3d1ac945930ae68a24059fc4be1a7f90050ff99a4038fd41853e01a3536fc",
        "bytes": 85664,
    },
}


def _is_o8_accepted(data: bytes, kind: str) -> bool:
    accepted = O8_ACCEPTED[kind]
    return len(data) == accepted["bytes"] and hashlib.sha256(data).hexdigest() == accepted["sha256"]


def _blob(revision: str, path: str) -> str:
    result = subprocess.run(["git", "rev-parse", f"{revision}:{path}"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.mark.parametrize("kind", ["catalogue", "annex"])
def test_committed_file_is_the_o8_accepted_byte_string(kind: str) -> None:
    accepted = O8_ACCEPTED[kind]
    assert _is_o8_accepted((REPO_ROOT / accepted["path"]).read_bytes(), kind)
    assert _blob("HEAD", accepted["path"]) == accepted["blob"]
    assert _blob(O8_ACCEPTED["main_commit"], accepted["path"]) == accepted["blob"]


def test_o8_pin_refuses_the_other_file() -> None:
    assert not _is_o8_accepted((REPO_ROOT / V.ANNEX_PATH).read_bytes(), "catalogue")
    assert not _is_o8_accepted((REPO_ROOT / V.CATALOGUE_PATH).read_bytes(), "annex")


def _legacy_instances(paths: list[Path]) -> set[str]:
    """Return the paths, outside the schema tree, whose top-level ``schema_id`` is a W9 catalogue or envelope."""
    found = set()
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else path.as_posix()
        if relative.startswith(".research-system/schemas/"):
            continue
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
        if isinstance(data, dict) and data.get("schema_id") in LEGACY_INSTANCE_IDS:
            found.add(relative)
    return found


def _legacy_candidates(root: Path = REPO_ROOT, *, tracked: bool = True) -> list[Path]:
    """Prefilter JSON and YAML files under ``root`` that name a W9 catalogue or envelope kind.

    The patterns are the kind names, which hold no ``/``, so an ID written with escaped slashes still matches
    (B2 confirmation c-i2; PR #396 review). Parsing every tracked file instead would read results files of tens of MB.
    """
    patterns = [arg for schema_id in sorted(LEGACY_INSTANCE_IDS) for arg in ("-e", schema_id.rsplit("/", 1)[1])]
    index = [] if tracked else ["--no-index"]
    result = subprocess.run(
        ["git", "grep", *index, "-l", "-F", *patterns, "--", "*.json", "*.yaml", "*.yml"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), result.stderr
    return [root / line for line in result.stdout.splitlines()]


def test_the_only_tracked_instance_is_the_w9_catalogue() -> None:
    # The bootstrap contract: one W9 expected catalogue, and no acceptance-envelope instance in the repository.
    assert _legacy_instances(_legacy_candidates()) == {V.CATALOGUE_PATH}


@pytest.mark.parametrize("schema_id", sorted(LEGACY_INSTANCE_IDS))
def test_a_second_instance_is_found(tmp_path: Path, schema_id: str) -> None:
    # Each kind, as plain JSON and as YAML and JSON with escaped slashes, passes through the prefilter and the parse
    # (B2 confirmation c-i1 and c-i2).
    escaped = schema_id.replace("/", "\\/")
    files = {
        tmp_path / "plain.json": json.dumps({"schema_id": schema_id}),
        tmp_path / "escaped.json": '{"schema_id": "' + escaped + '"}',
        tmp_path / "escaped.yaml": 'schema_id: "' + escaped + '"\n',
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    candidates = _legacy_candidates(tmp_path, tracked=False)
    assert sorted(candidates) == sorted(files)
    assert _legacy_instances(candidates) == {path.as_posix() for path in files}
