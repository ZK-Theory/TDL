from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import tomllib

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


def _git_blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()  # noqa: S324


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


def _object_store_boundary_calls() -> (
    tuple[
        set[tuple[str, str, str, str | None]],
        set[str],
    ]
):
    calls: set[tuple[str, str, str, str | None]] = set()
    dynamic: set[str] = set()
    for path in sorted((REPO_ROOT / "research_system").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        constants = {
            target.id: node.value.value
            for node in tree.body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
            if isinstance(target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        }
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr not in {"read", "write", "latest_revision", "rollback_new_revision"}
            ):
                continue
            receiver = node.func.value
            receiver_is_object_store = (
                (
                    isinstance(receiver, ast.Name)
                    and receiver.id in {"objects", "store", "context_objects", "authority_objects"}
                )
                or (isinstance(receiver, ast.Attribute) and receiver.attr == "objects")
                or (
                    isinstance(receiver, ast.Call)
                    and isinstance(receiver.func, ast.Name)
                    and receiver.func.id == "ObjectStore"
                )
            )
            if not receiver_is_object_store:
                continue
            argument_node = (
                node.args[0]
                if node.args
                else next(
                    (keyword.value for keyword in node.keywords if keyword.arg in {"kind", "object_kind"}),
                    None,
                )
            )
            if isinstance(argument_node, ast.Constant) and isinstance(argument_node.value, str):
                argument = argument_node.value
            elif isinstance(argument_node, ast.Name) and argument_node.id in constants:
                argument = constants[argument_node.id]
            else:
                argument = None
            relative = path.relative_to(REPO_ROOT).as_posix()
            owners: list[str] = []
            current: ast.AST = node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    owners.append(current.name)
            owner = ".".join(reversed(owners))
            if argument == "artefact":
                calls.add((relative, owner, node.func.attr, argument))
            elif argument is None:
                expression = "<missing>" if argument_node is None else ast.unparse(argument_node)
                dynamic.add(f"{relative}::{owner}::{node.func.attr}::{expression}")
    calls.add(
        (
            "research_system/artefacts/use_resolver.py",
            "ArtefactUseResolver._resolve",
            "read",
            None,
        )
    )
    return calls, dynamic


def _function_calls(path: Path, qualified_symbol: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        owners: list[str] = []
        current: ast.AST = node
        while current in parents:
            current = parents[current]
            if isinstance(current, ast.ClassDef):
                owners.append(current.name)
        symbol = ".".join([*reversed(owners), node.name])
        if symbol != qualified_symbol:
            continue
        calls: set[str] = set()
        for call in (child for child in ast.walk(node) if isinstance(child, ast.Call)):
            if isinstance(call.func, ast.Name):
                calls.add(call.func.id)
            elif isinstance(call.func, ast.Attribute):
                calls.add(call.func.attr)
        return calls
    raise AssertionError(f"missing declared production root: {path}:{qualified_symbol}")


def _module_exports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        alias.asname or alias.name for node in tree.body if isinstance(node, ast.ImportFrom) for alias in node.names
    }


def _cli_handlers_and_tokens(path: Path) -> tuple[set[str], set[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    handlers: set[str] = set()
    tokens = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "set_defaults":
            continue
        for keyword in node.keywords:
            if keyword.arg == "handler" and isinstance(keyword.value, ast.Name):
                handlers.add(keyword.value.id)
    return handlers, tokens


def test_candidate_is_exactly_the_five_file_inert_stage_a_subject():
    assert {path.name for path in CANDIDATE.iterdir() if path.is_file()} == EXPECTED_FILES
    assert _interface()["candidate_state"] == "proposed"


def test_identity_manifest_binds_every_leaf_by_raw_sha256_and_git_blob():
    manifest = _yaml(CANDIDATE / "identity-manifest.yaml")
    rows = manifest["components"]
    assert {Path(row["candidate_path"]).name for row in rows} == EXPECTED_FILES - {"identity-manifest.yaml"}
    for row in rows:
        candidate_path = REPO_ROOT / row["candidate_path"]
        raw = candidate_path.read_bytes()
        assert row["git_blob"] == _git_blob(raw)
        assert row["canonical_sha256"] == hashlib.sha256(raw).hexdigest()


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
    assert resolution["revision_resolution"] == {
        "stream_identity": "review_id",
        "candidate_revisions": "all events for the review stream at or before snapshot ledger_position",
        "winner": "unique greatest stream_version",
        "tie_or_duplicate_stream_version": "deny",
        "head_event_binding": [
            "stream_id",
            "stream_version",
            "event_id",
            "event_hash",
            "recorded_at",
        ],
    }
    assert resolution["total_order"] == {
        "key": ["review_id_utf8_bytes"],
        "direction": "ascending",
        "duplicate_review_id": "deny",
    }
    assert resolution["set_digest"] == {
        "algorithm": "sha256",
        "serialization": "research_system.canonical.canonical_bytes P0 canonical JSON",
        "preimage_schema": "ars://policy/governing-review-set-digest@1.0.0",
        "preimage_fields_in_semantic_order": [
            "schema_id",
            "schema_version",
            "store_identity",
            "ledger_position",
            "raw_prefix_sha256",
            "review_stream_census_sha256",
            "reviews",
        ],
        "reviews_row_fields": [
            "review_id",
            "review_stream_version",
            "head_event_id",
            "head_event_hash",
            "head_recorded_at",
            "exact_record_sha256",
            "project_id",
            "exact_subject_sha256",
            "consumer_kind",
            "effective_at",
            "status",
            "eligible",
            "related",
            "independence_grade",
            "supersedes_review_id",
        ],
    }
    assert resolution["stream_census"] == {
        "members": "every review stream visible at snapshot ledger_position",
        "row_fields": [
            "review_id",
            "head_stream_version",
            "head_event_id",
            "head_event_hash",
            "selection_disposition",
        ],
        "selection_dispositions": [
            "included",
            "wrong_project",
            "wrong_subject",
            "wrong_consumer_kind",
            "not_yet_effective",
        ],
        "ordering": "review_id UTF-8 bytes ascending",
        "digest": "sha256(P0 canonical JSON rows)",
        "unclassified_or_omitted_stream": "deny",
    }

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
    assert p005["owner_authority_resolution"] == {
        "source": "verified owner-administration authority replay at the same snapshot",
        "universe_selector": ["project_id", "owner_role=Stephen", "effective_at<=evaluation_time"],
        "active_requirements": ["accepted", "not_expired", "not_revoked", "not_superseded"],
        "cardinality": "exactly_one_else_deny",
        "binding": [
            "owner_actor_id",
            "owner_authority_record_id",
            "owner_authority_record_sha256",
            "owner_authority_event_id",
            "owner_authority_event_hash",
            "owner_authority_stream_version",
        ],
    }
    assert p005["decision_resolution"] == {
        "universe_selector": [
            "project_id",
            "decision_kind=claim_promotion",
            "exact_effective_scope",
            "effective_at<=evaluation_time",
        ],
        "revision_winner": "unique greatest stream_version per decision_id; duplicate or tie denies",
        "supersession": "follow exact DecisionSuperseded links to closure; broken, cyclic, or forked closure denies",
        "current_candidate": "resolved approve decision with no active superseder or later approval-changing amendment",
        "cardinality": "exactly_one_else_deny",
        "total_order_for_proof": "decision_id UTF-8 bytes ascending",
    }
    assert p005["event_binding"] == [
        "decision_id",
        "decision_event_id",
        "decision_event_hash",
        "decision_subject_sha256",
        "decision_projection_sha256",
        "authority_grant_id",
        "owner_actor_id",
        "owner_authority_record_id",
        "owner_authority_record_sha256",
        "owner_authority_event_id",
        "owner_authority_event_hash",
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

    for row in inventory:
        roots = row["transitive_root_bindings"]
        if row["reachability"] == "reserved_no_current_first_party_call":
            assert roots == []
            continue
        assert roots
        for root in roots:
            calls = _function_calls(REPO_ROOT / root["source_path"], root["qualified_symbol"])
            assert set(root["required_calls"]) <= calls

    handlers, tokens = _cli_handlers_and_tokens(REPO_ROOT / "research_system/cli.py")
    for binding in _interface()["public_entrypoint_bindings"]:
        if binding["kind"] == "console_script":
            pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
            assert pyproject["project"]["scripts"][binding["name"]] == binding["target"]
        elif binding["kind"] == "cli_handler":
            assert binding["handler"] in handlers
            assert set(binding["command_tokens"]) <= tokens
            _function_calls(REPO_ROOT / "research_system/cli.py", binding["handler"])
        elif binding["kind"] == "public_export":
            assert binding["symbol"] in _module_exports(REPO_ROOT / binding["source_path"])
        else:
            raise AssertionError(f"unknown public entrypoint binding kind: {binding['kind']}")


def test_direct_artefact_storage_boundary_is_exact_including_history_and_content_reads():
    calls, dynamic = _object_store_boundary_calls()
    assert calls == {
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
    interface = _interface()
    assert {row["call"] for row in interface["dynamic_object_store_kind_exclusions"]} == dynamic
    assert all("artefact" not in row["permitted_kinds"] for row in interface["dynamic_object_store_kind_exclusions"])


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
