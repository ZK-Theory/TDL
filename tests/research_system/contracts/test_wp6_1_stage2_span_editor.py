"""Focused Stage-2 accepted-annex and localized-edit checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

import tests.research_system.contracts.wp6_1_stage2_span_editor as span_editor
from tests.research_system.contracts.wp6_1_stage2_span_editor import build_stage2_overlays
from tests.research_system.contracts.wp6_1_schema_source import approved_fact_annex_bytes


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas" / "core"


def _schema(targets: dict[str, bytes], relative: str) -> dict:
    return json.loads(targets[relative])


def test_wp6_1_stage2_exact_87_plus_86_and_valid_json() -> None:
    targets = build_stage2_overlays(REPO_ROOT)
    command_paths = {path for path in targets if "/commands/" in path}
    event_paths = {path for path in targets if "/events/" in path}
    assert len(command_paths) == 87
    assert len(event_paths) == 86
    assert len(targets) == 173
    for data in targets.values():
        json.loads(data)
        assert b"\r" not in data


def test_wp6_1_stage2_pilot_keeps_identity_and_reference_subtrees() -> None:
    targets = build_stage2_overlays(REPO_ROOT)
    for relative in (
        ".research-system/schemas/core/commands/accept_task.schema.json",
        ".research-system/schemas/core/events/task_accepted.schema.json",
    ):
        baseline = json.loads((REPO_ROOT / relative).read_bytes())
        target = _schema(targets, relative)
        assert target["$id"] == baseline["$id"]
        assert target["$schema"] == baseline["$schema"]
        assert target["description"] == baseline["description"]
        for field in ("command_type", "event_type", "schema_id", "schema_version", "payload"):
            if field in baseline["properties"]:
                assert target["properties"][field] == baseline["properties"][field]


def test_wp6_1_stage2_exceptional_cardinality_and_discriminators() -> None:
    targets = build_stage2_overlays(REPO_ROOT)
    expected = {
        "reopen_task": (3, "prior_terminal_status", {"partial", "rejected", "cancelled"}),
        "expire_dispatch": (3, "observed_prior_state", {"issued", "delivered", "acknowledged"}),
        "withdraw_dispatch": (2, "observed_prior_state", {"issued", "claimed"}),
        "satisfy_review": (2, "prior_review_state", {"verdict_recorded", "changes_requested"}),
    }
    for name, (count, field, constants) in expected.items():
        relative = f".research-system/schemas/core/commands/{name}.schema.json"
        variants = _schema(targets, relative)["$defs"]["payload"]["oneOf"]
        assert len(variants) == count
        assert {variant["properties"][field]["const"] for variant in variants} == constants

    event_expected = {
        "task_reopened": (3, "prior_terminal_status", {"partial", "rejected", "cancelled"}),
        "dispatch_expired": (3, "observed_prior_state", {"issued", "delivered", "acknowledged"}),
        "dispatch_withdrawn": (2, "observed_prior_state", {"issued", "claimed"}),
        "review_satisfied": (2, "prior_review_state", {"verdict_recorded", "changes_requested"}),
    }
    for name, (count, field, constants) in event_expected.items():
        relative = f".research-system/schemas/core/events/{name}.schema.json"
        variants = _schema(targets, relative)["$defs"]["payload"]["oneOf"]
        assert len(variants) == count
        assert {variant["properties"][field]["const"] for variant in variants} == constants
    lease = _schema(targets, ".research-system/schemas/core/events/lease_granted.schema.json")
    assert len(lease["$defs"]["payload"]["oneOf"]) == 1


def test_wp6_1_stage2_shared_claim_and_non_compensation_surfaces() -> None:
    targets = build_stage2_overlays(REPO_ROOT)
    claim = _schema(targets, ".research-system/schemas/core/commands/claim_dispatch.schema.json")
    required = set(claim["$defs"]["payload"]["oneOf"][0]["required"])
    assert {"dispatch_id", "task_id", "task_revision", "lease_id", "declared_write_set"} <= required
    decision = yaml.safe_load((REPO_ROOT / ".research-system/contracts/wp6-1-owner-source-catalogue.yaml").read_bytes())
    assert decision["decision_rule_evaluation_non_compensation"]["decision_subject_kind"] == "decision"
    assert decision["decision_rule_evaluation_non_compensation"]["rule_evaluation_subject_kind"] == "rule_evaluation"
    binding = next(row["atomic_binding"] for row in decision["rows"] if row["command_type"] == "ClaimDispatch")
    assert binding["cardinality"] == 2
    assert binding["facets"] == ["task.claim_start", "dispatch.claim"]


def test_wp6_1_stage2_manifests_bind_accepted_annex_and_exact_schema_hashes() -> None:
    identities = yaml.safe_load((REPO_ROOT / ".research-system/contracts/wp6-1-schema-identities.yaml").read_bytes())
    catalogue = yaml.safe_load(
        (REPO_ROOT / ".research-system/contracts/wp6-1-owner-source-catalogue.yaml").read_bytes()
    )
    for manifest in (identities, catalogue):
        assert manifest["source_annex"] == {
            "repository_path": ".research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml",
            "reviewed_revision": "da94bd62fbf19021f3046c19fae5117c19219c95",
            "git_blob_id": "2f55b82f1a84cc0de081d38f8500c73a2083bac4",
            "canonical_utf8_lf_sha256": "d52c9b4e923d7f31f7201213335a147ff48293f96c0aab7c9eb59f8e7ff96441",
            "normalized_row_count": 104,
            "expanded_edge_count": 182,
        }
        assert manifest["owner_source_annex"]["repository_path"].endswith("06d-wp6-1-owner-source-catalogue.md")
        assert manifest["owner_source_annex"]["lineage_role"] == "historical_lineage"
    assert identities["stage1_owner_acceptance"] == catalogue["stage1_owner_acceptance"]
    acceptance = yaml.safe_load(
        (REPO_ROOT / ".research-system/contracts/wp6-1-stage1-owner-acceptance-record.yaml").read_bytes()
    )
    assert (
        identities["stage1_owner_acceptance"]["accepted_stage1_tuple"]["reviewed_revision"]
        == "da94bd62fbf19021f3046c19fae5117c19219c95"
    )
    assert (
        identities["stage1_owner_acceptance"]["record"]["canonical_utf8_lf_sha256"]
        == hashlib.sha256(
            (REPO_ROOT / ".research-system/contracts/wp6-1-stage1-owner-acceptance-record.yaml").read_bytes()
        ).hexdigest()
    )
    assert (
        acceptance["accepted_stage1_tuple"]["proposal_yaml"]["canonical_utf8_lf_sha256"]
        == hashlib.sha256(approved_fact_annex_bytes(REPO_ROOT)).hexdigest()
    )
    assert len(identities["rows"]) == len(catalogue["rows"]) == 104
    for row in identities["rows"]:
        command = row["command_schema_identity"]
        data = (REPO_ROOT / command["command_schema_path"]).read_bytes()
        assert command["command_schema_sha256"] == hashlib.sha256(data).hexdigest()
        for event in row["event_schema_bindings"]:
            event_data = (REPO_ROOT / event["event_schema_path"]).read_bytes()
            assert event["event_schema_sha256"] == hashlib.sha256(event_data).hexdigest()


def test_wp6_1_coordinated_checkout_substitution_cannot_change_immutable_expectations(
    tmp_path: Path, monkeypatch
) -> None:
    candidate = tmp_path / "mutable-proposal.yaml"
    candidate.write_bytes(
        approved_fact_annex_bytes(REPO_ROOT).replace(b"CreateScopeDefinition", b"CreateScopeAlias", 1)
    )
    relative = ".research-system/schemas/core/commands/create_scope_definition.schema.json"
    baseline_bytes = {
        path.relative_to(REPO_ROOT).as_posix(): path.read_bytes() for path in SCHEMA_ROOT.rglob("*.schema.json")
    }
    baseline_bytes[relative] = (
        (REPO_ROOT / relative)
        .read_bytes()
        .replace(b'"const": "CreateScopeDefinition"', b'"const": "CreateScopeAlias"', 1)
    )
    monkeypatch.setattr(span_editor, "approved_fact_annex_bytes", lambda _repo_root: candidate.read_bytes())
    with pytest.raises(ValueError, match="fact-annex helper bytes diverge from immutable accepted source"):
        build_stage2_overlays(REPO_ROOT, baseline_bytes=baseline_bytes)
