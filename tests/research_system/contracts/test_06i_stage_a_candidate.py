from __future__ import annotations

import ast
from pathlib import Path

import yaml

from tests.research_system.factories import REPO_ROOT


CANDIDATE = REPO_ROOT / ".research-system/contracts/candidates/06i-artefact-authority-v1"
OWNER_CATALOGUE = REPO_ROOT / ".research-system/contracts/wp6-1-owner-source-catalogue.yaml"
EXPECTED_FILES = {
    "artefact-authority-interface.v1.yaml",
    "artefact-consumer-predicates.schema.json",
    "artefact-consumer-predicates.v1.yaml",
    "governing-review-set-rules.v1.yaml",
    "identity-manifest.yaml",
}
CATALOGUE_FIELDS = {
    "command_type",
    "ordered_events",
    "reducers",
    "projections",
    "projection_selector",
    "authority",
    "receipt",
    "positive_test",
    "negative_profile",
    "expanded_negative_tests",
    "complete_record_sha256",
}
CATALOGUE_KEYS = {
    "artefact.register",
    "artefact.scientific_review",
    "artefact.use_authority",
    "decision.resolve",
}


def _yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _owner_rows() -> dict[str, dict[str, object]]:
    source = _yaml(OWNER_CATALOGUE)
    rows = source["rows"]
    assert isinstance(rows, list)
    return {str(row["key"]): row for row in rows if isinstance(row, dict) and row.get("key") in CATALOGUE_KEYS}


def _interface() -> dict[str, object]:
    return _yaml(CANDIDATE / "artefact-authority-interface.v1.yaml")


def _policy_pairs() -> set[tuple[str, str]]:
    policy = _yaml(CANDIDATE / "artefact-consumer-predicates.v1.yaml")
    pairs: set[tuple[str, str]] = set()
    for row in policy["predicates"]:
        for consumer_id in row["allowed_consumer_ids"]:
            pairs.add((row["consumer_kind"], consumer_id))
    return pairs


def _production_dispatch_bindings() -> set[str]:
    bindings: set[str] = set()
    methods = {
        "resolve_for_result",
        "resolve_for_review",
        "resolve_for_manuscript",
        "resolve_for_claim",
        "resolve_sensitive_sidecar",
    }
    for path in sorted((REPO_ROOT / "research_system").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "_PURPOSE_CONSUMER" for target in node.targets
            ):
                mapping = ast.literal_eval(node.value)
                for purpose, (method, _consumer_id) in mapping.items():
                    bindings.add(f"{path.relative_to(REPO_ROOT).as_posix()}::_PURPOSE_CONSUMER[{purpose}]::{method}")
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in methods:
                continue
            consumer_id = next(
                (
                    keyword.value.value
                    for keyword in node.keywords
                    if keyword.arg == "consumer_id"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ),
                None,
            )
            if consumer_id is None:
                continue
            owners: list[str] = []
            current: ast.AST = node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    owners.append(current.name)
            bindings.add(f"{path.relative_to(REPO_ROOT).as_posix()}::{'.'.join(reversed(owners))}::{node.func.attr}")
    return bindings


def _artefact_storage_boundary_calls() -> set[tuple[str, str, str, str | None]]:
    calls: set[tuple[str, str, str, str | None]] = set()
    for path in sorted((REPO_ROOT / "research_system").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr not in {"read", "write", "latest_revision"}
            ):
                continue
            argument = (
                node.args[0].value
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
                else None
            )
            relative = path.relative_to(REPO_ROOT).as_posix()
            is_artefact_object_call = argument == "artefact"
            is_resolver_content_call = (
                relative == "research_system/artefacts/use_resolver.py"
                and node.func.attr == "read"
                and argument is None
            )
            if not is_artefact_object_call and not is_resolver_content_call:
                continue
            owners: list[str] = []
            current: ast.AST = node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    owners.append(current.name)
            calls.add((relative, ".".join(reversed(owners)), node.func.attr, argument))
    return calls


def test_candidate_is_exactly_the_five_file_inert_stage_a_subject():
    assert {path.name for path in CANDIDATE.iterdir() if path.is_file()} == EXPECTED_FILES
    assert _interface()["candidate_state"] == "proposed"


def test_command_families_bind_exact_owner_catalogue_authority_and_controls():
    interface = _interface()
    rows = {row["catalogue_key"]: row for row in interface["command_families"]}
    owner = _owner_rows()

    assert set(rows) == CATALOGUE_KEYS == set(owner)
    for key in sorted(CATALOGUE_KEYS):
        assert rows[key]["owner_catalogue_binding"] == {field: owner[key].get(field) for field in CATALOGUE_FIELDS}
        assert rows[key]["atomic_failure_contract"] == {
            "validation_order": [
                "schema_and_exact_subject_identity",
                "authority_grant_actor_scope_and_effectivity",
                "current_state_expected_version_and_idempotency",
                "bound_evidence_and_domain_preconditions",
                "writer_lock_recheck",
                "durable_mutation",
            ],
            "failure_exception": "typed_command_rejection",
            "rejected_receipt": "permitted_if_typed_and_not_accepted",
            "accepted_receipt": "none",
            "event_append": "none",
            "object_revision": "none",
            "projection_mutation": "none",
        }


def test_review_universe_and_p005_are_deterministic_and_no_omission():
    rules = _yaml(CANDIDATE / "governing-review-set-rules.v1.yaml")
    resolution = rules["governing_review_resolution"]
    assert resolution["authoritative_source"] == "verified_replay_at_evaluation_snapshot"
    assert resolution["universe_selector"] == [
        "project_id",
        "exact_subject_sha256",
        "consumer_kind",
        "effective_at_or_before_evaluation_time",
    ]
    assert resolution["no_omission_proof"] == [
        "store_identity",
        "ledger_position",
        "raw_prefix_sha256",
        "ordered_governing_review_ids",
        "ordered_governing_review_record_sha256s",
        "governing_review_set_sha256",
    ]
    assert resolution["satisfaction_gate"]["evaluate_every_governing_review"] is True
    assert resolution["satisfaction_gate"]["blocking_states"] == [
        "changes_requested",
        "rejected",
        "unsatisfied",
        "ineligible",
        "related",
        "insufficient_independence",
    ]

    p005 = rules["decision_rules"]["claim_promotion"]
    assert p005["authoritative_source"] == "verified_decision_replay_at_evaluation_snapshot"
    assert p005["required_status"] == "resolved"
    assert p005["selected_option"] == "approve"
    assert p005["deciding_actor_binding"] == {
        "required_owner_role": "Stephen",
        "actor_id_source": "current_accepted_owner_authority.actor_id",
        "prohibit_caller_supplied_actor": True,
    }
    assert p005["currentness"] == {
        "effective_at_or_before_evaluation_time": True,
        "not_expired": True,
        "not_rejected": True,
        "not_superseded": True,
        "no_later_effective_amendment_changes_approval": True,
    }
    assert p005["event_binding"] == [
        "decision_id",
        "decision_event_id",
        "decision_event_hash",
        "decision_subject_sha256",
        "decision_projection_sha256",
        "authority_grant_id",
    ]


def test_consumer_inventory_is_exactly_closed_over_policy_and_production_dispatch():
    inventory = _interface()["consumer_inventory"]
    assert {(row["consumer_kind"], row["consumer_id"]) for row in inventory} == _policy_pairs()

    declared = {
        binding
        for row in inventory
        for binding in row["dispatch_bindings"]
        if row["reachability"] == "current_first_party"
    }
    assert declared == _production_dispatch_bindings()

    sidecar = next(row for row in inventory if row["consumer_id"] == "rm03_sensitive_sidecar")
    assert sidecar["reachability"] == "reserved_no_current_first_party_call"
    assert sidecar["dispatch_bindings"] == []
    assert sidecar["activation_rule"] == (
        "deny until a changed exact candidate inventories and independently reviews the first-party call path"
    )


def test_direct_artefact_storage_boundary_is_exact_including_history_and_content_reads():
    assert _artefact_storage_boundary_calls() == {
        (
            "research_system/artefacts/use_resolver.py",
            "ArtefactUseResolver._resolve",
            "read",
            "artefact",
        ),
        (
            "research_system/artefacts/use_resolver.py",
            "ArtefactUseResolver._resolve",
            "read",
            None,
        ),
        (
            "research_system/command/service.py",
            "CommandService._ensure_artefact_materialized",
            "read",
            "artefact",
        ),
        (
            "research_system/command/service.py",
            "CommandService._ensure_artefact_materialized",
            "write",
            "artefact",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "prepare_session_brief",
            "write",
            "artefact",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "_evidence_revision_history",
            "latest_revision",
            "artefact",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "_evidence_revision_history",
            "read",
            "artefact",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "record_session_evidence",
            "write",
            "artefact",
        ),
    }


def test_resolver_and_command_failures_distinguish_rejection_from_acceptance():
    interface = _interface()
    assert interface["public_resolver"]["failure_contract"] == {
        "exception": "ArtefactUseDenied",
        "side_effects": "none",
        "receipt": "none",
        "event": "none",
        "object_revision": "none",
        "projection_mutation": "none",
    }
    assert "no accepted receipt" in interface["invariants"][-1]
    assert "no receipt" not in interface["invariants"][-1]
