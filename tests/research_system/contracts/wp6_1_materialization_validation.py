"""Fail-closed validation for independently reviewable ARS contract artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry
from tests.research_system.contracts import wp6_1_schema_source as schema_source
from tests.research_system.contracts.wp6_1_stage2_span_editor import build_stage2_overlays


WP6_1_CATALOGUE_SCHEMA_ID = "ars://contracts/wp6-1-owner-source-catalogue"
WP6_1_IDENTITIES_SCHEMA_ID = "ars://contracts/wp6-1-schema-identities"
APPROVED_WP6_1_ANNEX_PATH = "docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md"
APPROVED_WP6_1_REVISION = "fe5f1d40bc8f05f061317c677b5891cea0711249"
APPROVED_WP6_1_ANNEX_BLOB = "5e2eb60ca4419d1529506de6859fb027cff518af"
APPROVED_WP6_1_ANNEX_SHA256 = "96932fd752362eddb6da2da77bc0b56ccb8e83ced58e93c3b139e3248acb08f7"
APPROVED_WP6_1_FACT_ANNEX_PATH = ".research-system/contracts/wp6-1-schema-fact-annex-proposal.yaml"
APPROVED_WP6_1_FACT_REVISION = "da94bd62fbf19021f3046c19fae5117c19219c95"
APPROVED_WP6_1_FACT_BLOB = "2f55b82f1a84cc0de081d38f8500c73a2083bac4"
APPROVED_WP6_1_FACT_SHA256 = "d52c9b4e923d7f31f7201213335a147ff48293f96c0aab7c9eb59f8e7ff96441"
APPROVED_WP6_1_ANNEX_ROW_BINDING_SHA256 = "ddb22f7f8b0347367082e3cd6458bf9dc2ed07ca52e3fdc4a8844325a6271e01"
_TICK = chr(96)
_ARROW = chr(0x2192)

_SOURCE_ANNEX = {
    "repository_path": APPROVED_WP6_1_FACT_ANNEX_PATH,
    "reviewed_revision": APPROVED_WP6_1_FACT_REVISION,
    "git_blob_id": APPROVED_WP6_1_FACT_BLOB,
    "canonical_utf8_lf_sha256": APPROVED_WP6_1_FACT_SHA256,
    "normalized_row_count": 104,
    "expanded_edge_count": 182,
}
_OWNER_SOURCE_ANNEX = {
    "repository_path": APPROVED_WP6_1_ANNEX_PATH,
    "reviewed_revision": APPROVED_WP6_1_REVISION,
    "git_blob_id": APPROVED_WP6_1_ANNEX_BLOB,
    "canonical_utf8_lf_sha256": APPROVED_WP6_1_ANNEX_SHA256,
    "normalized_row_count": 104,
    "expanded_edge_count": 182,
    "lineage_role": "historical_lineage",
}
_STAGE1_ACCEPTANCE_PATH = ".research-system/contracts/wp6-1-stage1-owner-acceptance-record.yaml"
_STAGE1_ACCEPTANCE_SCHEMA_ID = "ars://contracts/wp6-1-stage1-owner-acceptance-record"
_STAGE1_ACCEPTANCE_BLOB = "42d7ef3a2fb7f082a39634e4d81f47ebd8a81e83"
_STAGE1_ACCEPTANCE_SHA256 = "70a37499528b7d5fdb2fb4627723ae726156c33229aeba5400fd382c752aa648"
_GOVERNANCE = {
    "producer": "pipe/ars-wp6-1-task-lifecycle owning Worker",
    "intended_independent_reviewer": "independent reviewer who did not implement the schemas",
    "intended_acceptor": "Stephen under D-G6-3",
    "review_status": "pending_independent_review",
    "acceptance_status": "pending_d_g6_3_owner_acceptance",
}
_STATE_CLASSES = {
    "task_nonterminal": [
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "blocked",
        "input_required",
        "paused",
    ],
    "task_suspended": ["blocked", "input_required", "paused"],
    "task_prior_active": ["draft", "readiness_pending", "ready", "in_progress", "review_pending"],
    "task_blockable": [
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "input_required",
        "paused",
    ],
    "task_input_requestable": [
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "blocked",
        "paused",
    ],
    "task_pausable": [
        "draft",
        "readiness_pending",
        "ready",
        "in_progress",
        "review_pending",
        "blocked",
        "input_required",
    ],
    "attempt_nonterminal": ["created", "claimed", "running", "paused", "stopping"],
    "attempt_retryable": ["completed", "failed", "partial", "abandoned"],
    "review_nonterminal": ["requested", "assigned", "in_review", "verdict_recorded", "changes_requested"],
    "decision_unresolved": ["proposed", "under_review"],
}
_N0 = [
    "missing_field",
    "wrong_type",
    "missing_authority",
    "wrong_authority",
    "expired_grant",
    "not_yet_effective_grant",
    "prohibited_actor",
    "wrong_authority_scope",
    "wrong_authority_subject_kind",
    "wrong_authority_subject_id",
    "stale_expected_version",
    "conflicting_payload",
    "idempotency_conflict",
    "atomic_no_event",
    "atomic_no_receipt_acceptance",
    "atomic_no_projection_side_effect",
]
_NE = _N0 + ["illegal_from_state", "illegal_to_state", "invalid_command_subject_identity"]
_NA = _NE + ["authority_rule_mutation", "accepted_subject_binding_mutation", "allowed_actor_class_mutation"]
_NI = _NA + [
    "stale_subject_hash",
    "ineligible_reviewer",
    "self_related_reviewer",
    "insufficient_independence_grade",
    "incomplete_governing_review_set",
]
_NC = _NA + [
    "competing_claim",
    "competing_reservation",
    "incompatible_lease",
    "incompatible_checkpoint",
    "preserved_predecessor_evidence",
]
_NS = _NA + [
    "supersession_cycle",
    "absent_replacement",
    "type_incompatible_replacement",
    "missing_continuing_consumer_disposition",
    "attempted_history_mutation",
]
_NEGATIVE_PROFILES = {"N0": _N0, "NE": _NE, "NA": _NA, "NI": _NI, "NC": _NC, "NS": _NS}
_CORRECTION_MAPPINGS = [
    {"corrected_record_kind": "scope_definition", "owner_projection": "scope"},
    {"corrected_record_kind": "task", "owner_projection": "task"},
    {"corrected_record_kind": "dispatch", "owner_projection": "dispatch"},
    {"corrected_record_kind": "lease", "owner_projection": "lease"},
    {"corrected_record_kind": "attempt", "owner_projection": "attempt"},
    {"corrected_record_kind": "checkpoint", "owner_projection": "checkpoint"},
    {"corrected_record_kind": "message", "owner_projection": "message"},
    {"corrected_record_kind": "blocker", "owner_projection": "blocker"},
    {"corrected_record_kind": "artefact", "owner_projection": "artefact"},
    {"corrected_record_kind": "review", "owner_projection": "review"},
    {"corrected_record_kind": "decision", "owner_projection": "decision"},
    {"corrected_record_kind": "rule_evaluation", "owner_projection": "rule_evaluation"},
    {"corrected_record_kind": "resource", "owner_projection": "resource"},
    {"corrected_record_kind": "operation", "owner_projection": "operations"},
    {"corrected_record_kind": "backup", "owner_projection": "backup"},
]
_NON_COMPENSATION = {
    "decision_subject_kind": "decision",
    "decision_id_source": "payload.new_decision_id",
    "decision_owner_projection": "decision",
    "rule_evaluation_subject_kind": "rule_evaluation",
    "rule_evaluation_id_source": "payload.new_rule_evaluation_id",
    "rule_evaluation_owner_projection": "rule_evaluation",
    "coordinated_candidate_runtime_substitution_rejects": True,
    "unchanged_surfaces": [
        "event_tail",
        "receipt_acceptance_state",
        "decision_projection",
        "rule_evaluation_projection",
        "governance_correction_index",
    ],
}


@dataclass(frozen=True)
class Wp61MaterializationSummary:
    """Validated cardinalities and content identities for the WP6.1 pair."""

    normalized_row_count: int
    expanded_edge_count: int
    catalogue_multiset_sha256: str
    row_identity_multiset_sha256: str


@dataclass(frozen=True)
class _AnnexRow:
    source_table: str
    key: str
    cells: tuple[str, str, str, str, str, str]


def _fail(message: str) -> None:
    raise SchemaError(f"WP6.1 contract materialization: {message}")


def _require(condition: bool, message: str) -> None:
    if not condition:
        _fail(message)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_value(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _git_blob_id(data: bytes, repo_root: Path) -> str:
    """Obtain the raw Git blob identity without reimplementing SHA-1."""
    result = subprocess.run(
        ["git", "hash-object", "--no-filters", "--stdin"],
        cwd=repo_root,
        input=data,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _require(result.returncode == 0, "Git cannot calculate a raw blob identity")
    return result.stdout.decode("ascii").strip()


def _plain(value: str) -> str:
    return value.replace(_TICK, "")


def _read_yaml(path: Path) -> tuple[bytes, dict[str, Any]]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SchemaError(f"WP6.1 contract materialization: unreadable artifact: {path}") from exc
    _require(not data.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM is prohibited: {path}")
    _require(b"\r" not in data, f"artifact must use canonical LF bytes: {path}")
    try:
        value = yaml.safe_load(data.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise SchemaError(f"WP6.1 contract materialization: invalid UTF-8 YAML: {path}") from exc
    _require(isinstance(value, dict), f"artifact root must be an object: {path}")
    return data, value


@lru_cache(maxsize=1)
def _verify_approved_annex_provenance(repo_root: Path) -> bytes:
    result = subprocess.run(
        [
            "git",
            "show",
            f"{APPROVED_WP6_1_REVISION}:{APPROVED_WP6_1_ANNEX_PATH}",
        ],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _require(result.returncode == 0, "approved annex revision is unavailable")
    _require(_git_blob_id(result.stdout, repo_root) == APPROVED_WP6_1_ANNEX_BLOB, "approved annex Git blob mismatch")
    _require(
        hashlib.sha256(result.stdout).hexdigest() == APPROVED_WP6_1_ANNEX_SHA256,
        "approved annex canonical SHA-256 mismatch",
    )
    return result.stdout


@lru_cache(maxsize=1)
def _verify_fact_annex_provenance(repo_root: Path) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{APPROVED_WP6_1_FACT_REVISION}:{APPROVED_WP6_1_FACT_ANNEX_PATH}"],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    _require(result.returncode == 0, "accepted fact annex revision is unavailable")
    _require(
        _git_blob_id(result.stdout, repo_root) == APPROVED_WP6_1_FACT_BLOB, "accepted fact annex Git blob mismatch"
    )
    _require(
        hashlib.sha256(result.stdout).hexdigest() == APPROVED_WP6_1_FACT_SHA256,
        "accepted fact annex canonical SHA-256 mismatch",
    )
    return result.stdout


@lru_cache(maxsize=1)
def _verify_stage2_overlay_bytes(repo_root: Path) -> None:
    expected = build_stage2_overlays(repo_root)
    _require(len(expected) == 173, "accepted Stage-2 overlay count mismatch")
    for relative, data in expected.items():
        _require((repo_root / relative).read_bytes() == data, f"localized Stage-2 schema mismatch: {relative}")


def _parse_annex_bytes(data: bytes) -> list[_AnnexRow]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SchemaError("WP6.1 contract materialization: approved annex is not UTF-8") from exc
    section: str | None = None
    rows: list[_AnnexRow] = []
    for line in lines:
        if line.startswith("## 2. "):
            section = "w2_lifecycle"
        elif line.startswith("## 3. "):
            section = "w2_messages_governance"
        elif line.startswith("## 4. "):
            section = "w8_operator"
        elif line.startswith("## 5. "):
            section = None
        if section is None or not line.startswith(f"| {_TICK}"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if len(cells) != 6:
            continue
        rows.append(_AnnexRow(section, _plain(cells[0]), cells))  # type: ignore[arg-type]
    return rows


def _parse_annex(path: Path) -> list[_AnnexRow]:
    """Legacy checkout parser retained only for external compatibility tests."""
    try:
        return _parse_annex_bytes(path.read_bytes())
    except OSError as exc:
        raise SchemaError(f"WP6.1 contract materialization: unreadable approved annex: {path}") from exc


def _command_event_parts(cell: str) -> tuple[str, str, list[str], list[str]]:
    parts = [_plain(part.strip()) for part in cell.split(";")]
    _require(len(parts) == 3, "approved command/event cell is malformed")
    schema_token, command_type = (part.strip() for part in parts[0].split(" / ", 1))
    events = [item.strip() for item in parts[1].strip("[]").split(",")]
    event_tokens = [item.strip() for item in parts[2].strip("[]").split(",")]
    _require(len(events) == len(event_tokens), "approved event/schema binding cardinality differs")
    return schema_token, command_type, events, event_tokens


def _transition(cell: str, source_table: str) -> dict[str, Any]:
    tokens = re.findall(f"{_TICK}([^{_TICK}]+){_TICK}", cell)
    edge = next((token for token in tokens if _ARROW in token), None)
    if edge is not None:
        from_state, to_state = (part.strip() for part in edge.split(_ARROW, 1))
        kind = "edge"
    elif "state-neutral" in cell:
        from_state, to_state, kind = None, None, "state_neutral"
    elif "dimension update" in cell:
        from_state, to_state, kind = None, None, "dimension_update"
    elif source_table == "w8_operator":
        from_state, to_state, kind = None, None, "operator_command"
    else:
        _fail(f"unparseable owner transition: {cell}")
    type_match = re.search(f"type {_TICK}([^{_TICK}]+){_TICK}", cell)
    discriminator_match = re.search(f"discriminator {_TICK}([^{_TICK}]+){_TICK}", cell)
    if type_match:
        discriminator = {"field": "message_type", "value": type_match.group(1)}
    elif discriminator_match:
        discriminator = {"field": discriminator_match.group(1), "value": None}
    elif source_table == "w8_operator":
        discriminator = {"field": "owner_command", "value": tokens[0]}
    else:
        discriminator = None
    return {"kind": kind, "from_state": from_state, "to_state": to_state, "discriminator": discriminator}


def _reducer_projection_parts(cell: str) -> tuple[list[str], list[str], str | None]:
    reducer_text, effect_text = cell.split(";", 1)
    reducers = [_plain(item.strip()) for item in reducer_text.split("+")]
    selector_match = re.search(f"{_TICK}(projection_selector/[^{_TICK}]+){_TICK}", cell)
    if selector_match:
        return reducers, ["governance_correction_index"], selector_match.group(1)
    return reducers, [_plain(item.strip()) for item in effect_text.split(",")], None


def _authority_binding(key: str, command_type: str) -> tuple[str, str]:
    family = key.split(".", 1)[0]
    if command_type == "ClaimDispatch":
        return "dispatch", "payload.dispatch_id"
    if key in {"operator.request_resource_grant", "operator.release_resources"}:
        return "resource", "payload.resource_id"
    if key in {"operator.create_backup", "operator.verify_restore"}:
        return "project_store", "payload.project_id"
    if key == "operator.adopt_late_artefact":
        return "artefact", "envelope.target_stream_id"
    if key in {
        "operator.request_pause",
        "operator.confirm_pause",
        "operator.request_stop",
        "operator.confirm_stop",
        "operator.request_resume",
        "operator.quarantine_orphan",
    }:
        return "attempt", "envelope.target_stream_id"
    if key in {"operator.claim_execution_lease", "operator.record_heartbeat"}:
        source = "payload.new_lease_id" if key == "operator.claim_execution_lease" else "envelope.target_stream_id"
        return "lease", source
    if family == "scope":
        source = "payload.new_scope_definition_id" if key == "scope.create" else "envelope.target_stream_id"
        return "scope_definition", source
    if family == "task":
        return "task", "payload.new_task_id" if key == "task.create" else "envelope.target_stream_id"
    if family == "dispatch":
        return "dispatch", "payload.dispatch_id"
    if family == "lease":
        return "lease", "payload.new_lease_id" if key == "lease.activate" else "envelope.target_stream_id"
    if family == "attempt":
        source = "payload.new_attempt_id" if key in {"attempt.create", "attempt.retry"} else "envelope.target_stream_id"
        return "attempt", source
    if family == "checkpoint":
        return "attempt", "payload.attempt_id"
    if family == "message":
        source = "payload.new_message_id" if key.startswith("message.publish_") else "envelope.target_stream_id"
        return "message", source
    if family == "blocker":
        return "blocker", "payload.new_blocker_id" if key == "blocker.record" else "envelope.target_stream_id"
    if family == "artefact":
        return "artefact", "payload.new_artefact_id" if key == "artefact.register" else "envelope.target_stream_id"
    if family == "review":
        return "review", "payload.new_review_id" if key == "review.request" else "envelope.target_stream_id"
    if family == "decision":
        return "decision", "payload.new_decision_id" if key == "decision.propose" else "envelope.target_stream_id"
    if family == "rule":
        return "rule_evaluation", "payload.new_rule_evaluation_id"
    if family == "correction":
        return "corrected_record", "payload.erroneous_record_id"
    _fail(f"unmapped authority family: {key}")


def _canonical_schema_sha256(path: Path) -> str:
    """Hash current bytes; same-path mutation must never reuse a stale digest."""
    _require(path.is_file(), f"materialized schema is missing: {path}")
    schema_bytes = path.read_bytes()
    _require(
        not schema_bytes.startswith(b"\xef\xbb\xbf") and b"\r" not in schema_bytes,
        f"schema bytes are not canonical: {path}",
    )
    return hashlib.sha256(schema_bytes).hexdigest()


def _identity_object(schema_token: str, semantic_type: str, kind: str, repo_root: Path) -> dict[str, Any]:
    token = schema_token.split("/", 1)[1]
    if kind == "command":
        base = {
            "schema_token": schema_token,
            "command_schema_path": f".research-system/schemas/core/commands/{token}.schema.json",
            "command_schema_id": f"ars://core/command/{semantic_type}",
            "command_schema_version": "1.0.0",
            "command_schema_sha256": "",
            "materialization_status": "proposed_materialized",
            "review_status": "pending_independent_review",
            "acceptance_status": "pending_d_g6_3_owner_acceptance",
        }
    else:
        base = {
            "event_type": semantic_type,
            "schema_token": schema_token,
            "event_schema_path": f".research-system/schemas/core/events/{token}.schema.json",
            "event_schema_id": f"ars://core/event/{semantic_type}",
            "event_schema_version": "1.0.0",
            "event_schema_sha256": "",
            "materialization_status": "proposed_materialized",
            "review_status": "pending_independent_review",
            "acceptance_status": "pending_d_g6_3_owner_acceptance",
        }
    path_field = "command_schema_path" if kind == "command" else "event_schema_path"
    path = repo_root / base[path_field]
    base["command_schema_sha256" if kind == "command" else "event_schema_sha256"] = _canonical_schema_sha256(path)
    result: dict[str, Any] = {}
    digest = _sha256_value(base)
    for field, value in base.items():
        result[field] = value
        if field == "command_schema_sha256":
            result["command_identity_contract_sha256"] = digest
        elif field == "event_schema_sha256":
            result["event_identity_contract_sha256"] = digest
    return result


def _authority(cell: str, key: str, command_type: str) -> dict[str, Any]:
    subject_kind, subject_id_source = _authority_binding(key, command_type)
    return {
        "rule_and_precondition": _plain(cell),
        "authority_subject_kind": subject_kind,
        "authority_subject_id_source": subject_id_source,
        "authority_scope_source": ["envelope.project_id", "authority_subject_kind", "authority_subject_id_source"],
        "authority_grant_id_source": "envelope.authority_grant_id",
        "authority_effective_at_source": "authority_grant.effective_at",
        "authority_expires_at_source": "authority_grant.expires_at",
        "allowed_actor_classes": ["human", "agent", "service"],
        "prohibited_actor_classes": ["importer"],
    }


def _atomic_claim_binding() -> dict[str, Any]:
    return {
        "group": "claim_dispatch_task_dispatch_v1",
        "cardinality": 2,
        "facets": ["task.claim_start", "dispatch.claim"],
        "dispatch_authority_subject_source": "payload.dispatch_id",
        "stored_relation": {
            "dispatch_task_id_source": "accepted_dispatch.task_id",
            "dispatch_task_revision_source": "accepted_dispatch.task_revision",
            "payload_task_id_source": "payload.task_id",
            "payload_task_revision_source": "payload.task_revision",
        },
        "lease_relation": {
            "lease_task_id_source": "active_lease.task_id",
            "lease_task_revision_source": "active_lease.task_revision",
            "lease_dispatch_id_source": "active_lease.dispatch_id",
        },
        "declared_write_set": [
            {
                "stream_kind": "dispatch",
                "stream_id_source": "payload.dispatch_id",
                "expected_version_source": "payload.expected_dispatch_stream_version",
            },
            {
                "stream_kind": "task",
                "stream_id_source": "payload.task_id",
                "expected_version_source": "payload.expected_task_stream_version",
            },
        ],
        "ordered_events": ["DispatchClaimed", "TaskClaimStarted"],
        "acceptance_order": [
            "validate_dispatch_scoped_authority",
            "load_accepted_dispatch_revision",
            "verify_dispatch_stored_task_relation",
            "verify_active_lease_relation",
            "idempotency_lookup",
            "version_and_tail_validation",
            "position_allocation",
            "atomic_event_publication",
            "receipt_acceptance",
        ],
        "required_mutations": [
            "missing_task_facet",
            "missing_dispatch_facet",
            "missing_task_binding",
            "stale_task_stream_version",
            "foreign_current_task",
            "stale_dispatch_task_relation",
            "wrong_lease_task_subject",
            "wrong_lease_dispatch_subject",
            "concurrent_task_stream_race",
            "missing_write_set_member",
            "extra_write_set_member",
            "dispatch_only_batch",
            "dispatch_only_receipt",
        ],
        "unchanged_surfaces": [
            "task_stream",
            "dispatch_stream",
            "event_tail",
            "receipt_acceptance_state",
            "task_projection",
            "dispatch_projection",
        ],
    }


def _expanded_edge_count(rows: list[Mapping[str, Any]]) -> int:
    count = 0
    for row in rows:
        transition = row["transition"]
        if transition["kind"] != "edge":
            count += 1
            continue
        from_token = transition["from_state"]
        to_token = transition["to_state"]
        from_states = _STATE_CLASSES.get(from_token, [from_token])
        if to_token == "same status(new revision)":
            count += len(from_states)
        else:
            to_states = _STATE_CLASSES.get(to_token, [to_token])
            count += len(from_states) * len(to_states)
    return count


def _verify_content_hashes(document: Mapping[str, Any], row_hash_field: str, multiset_field: str) -> None:
    rows = document["rows"]
    for row in rows:
        candidate = {key: value for key, value in row.items() if key != row_hash_field}
        _require(row[row_hash_field] == _sha256_value(candidate), f"row hash mismatch: {row['key']}")
    expected = _sha256_value(sorted(rows, key=lambda item: item["key"]))
    _require(document[multiset_field] == expected, f"{multiset_field} mismatch")


def _verify_schema_identity(identity: Mapping[str, Any], expected: Mapping[str, Any], repo_root: Path) -> None:
    path_field = "command_schema_path" if "command_schema_path" in expected else "event_schema_path"
    _require(identity == expected, f"schema identity mismatch: {expected[path_field]}")
    path = repo_root / str(identity[path_field])
    hash_field = "command_schema_sha256" if "command_schema_path" in expected else "event_schema_sha256"
    _require(identity[hash_field] == _canonical_schema_sha256(path), f"schema SHA-256 mismatch: {path}")


@lru_cache(maxsize=1)
def _schema_registry(schema_root: Path) -> SchemaRegistry:
    return SchemaRegistry(schema_root)


def _field_spec_shape(field: schema_source.FieldSpec) -> tuple[Any, ...]:
    nested = _object_spec_shape(field.object_spec) if field.object_spec else None
    return (
        field.name,
        field.json_type,
        field.const,
        field.nullable,
        field.item_type,
        field.minimum,
        field.format,
        field.pattern,
        field.item_pattern,
        nested,
        field.enum,
    )


def _object_spec_shape(spec: schema_source.ObjectSpec | None) -> tuple[Any, ...] | None:
    if spec is None:
        return None
    return (
        tuple(sorted((_field_spec_shape(field) for field in spec.fields), key=lambda item: item[0])),
        tuple(sorted(field.name for field in spec.fields if field.required)),
        spec.exclusive_required,
    )


def _local_ref(root: Mapping[str, Any], value: Mapping[str, Any]) -> Mapping[str, Any]:
    token = str(value["$ref"]).removeprefix("#/$defs/")
    resolved = root.get("$defs", {}).get(token)
    _require(isinstance(resolved, Mapping), f"unresolved local schema reference: {token}")
    return resolved


def _schema_field_shape(name: str, field: Mapping[str, Any], root: Mapping[str, Any]) -> tuple[Any, ...]:
    raw_type = field.get("type")
    nullable = isinstance(raw_type, list) and set(raw_type) == {"string", "null"}
    json_type = "string" if nullable else raw_type
    nested = None
    item_type = None
    item_pattern = None
    if "$ref" in field:
        json_type = "object"
        nested = _schema_object_shape(_local_ref(root, field), root)
    if json_type == "array":
        if name == "declared_write_set":
            members = field.get("prefixItems")
            _require(
                isinstance(members, list) and len(members) == 2, "ClaimDispatch write set is not exactly two members"
            )
            _require(
                field.get("minItems") == field.get("maxItems") == 2, "ClaimDispatch write set cardinality mismatch"
            )
            member_shapes = [_schema_object_shape(member, root) for member in members]
            _require(
                [member["properties"]["stream_kind"].get("const") for member in members] == ["dispatch", "task"],
                "ClaimDispatch write set order/kinds mismatch",
            )
            fields, required, exclusive = member_shapes[0]
            nested = (
                tuple((item[0], item[1], None if item[0] == "stream_kind" else item[2], *item[3:]) for item in fields),
                required,
                exclusive,
            )
        else:
            items = field.get("items")
            if isinstance(items, Mapping) and "$ref" in items:
                nested = _schema_object_shape(_local_ref(root, items), root)
            elif isinstance(items, Mapping) and items.get("type") == "object":
                nested = _schema_object_shape(items, root)
            elif isinstance(items, Mapping):
                item_type = items.get("type")
                item_pattern = items.get("pattern")
    _require("x-source-citation" in field, f"uncited generated field: {name}")
    return (
        name,
        json_type,
        field.get("const"),
        nullable,
        item_type,
        field.get("minimum"),
        field.get("format"),
        field.get("pattern"),
        item_pattern,
        nested,
        tuple(field.get("enum", [])),
    )


def _schema_object_shape(value: Mapping[str, Any], root: Mapping[str, Any]) -> tuple[Any, ...]:
    _require(value.get("type") == "object", "payload variant is not an object")
    _require(value.get("additionalProperties") is False, "generated payload object is not closed")
    required = value.get("required")
    properties = value.get("properties")
    _require(isinstance(required, list) and isinstance(properties, Mapping), "invalid generated payload object")
    _require(set(required) <= set(properties), "generated payload required/property mismatch")
    _require("x-source-citation" in value, "uncited generated payload object")
    exclusive = tuple(tuple(branch.get("required", [])) for branch in value.get("oneOf", []))
    return (
        tuple(
            sorted((_schema_field_shape(name, properties[name], root) for name in properties), key=lambda item: item[0])
        ),
        tuple(sorted(required)),
        exclusive,
    )


@lru_cache(maxsize=256)
def _parsed_schema(path: Path, sha256: str) -> Mapping[str, Any]:
    data = path.read_bytes()
    _require(hashlib.sha256(data).hexdigest() == sha256, f"schema changed while validating: {path}")
    value = json.loads(data)
    _require(isinstance(value, Mapping), f"generated schema is not an object: {path}")
    return value


def _semantic_schema(path: Path) -> Mapping[str, Any]:
    data = path.read_bytes()
    return _parsed_schema(path, hashlib.sha256(data).hexdigest())


_INDEPENDENT_COMMAND_ROOT = frozenset(
    {
        "command_id",
        "command_type",
        "schema_id",
        "schema_version",
        "submitted_at",
        "actor_id",
        "on_behalf_of_actor_id",
        "authority_grant_id",
        "target_stream_id",
        "expected_stream_version",
        "idempotency_key",
        "correlation_id",
        "causation_id",
        "reason",
        "evidence_refs",
        "payload",
    }
)
_INDEPENDENT_EVENT_ROOT = frozenset(
    {
        "event_id",
        "event_type",
        "schema_id",
        "schema_version",
        "project_id",
        "stream_id",
        "stream_version",
        "global_position",
        "transaction_id",
        "transaction_index",
        "transaction_count",
        "command_id",
        "command_type",
        "command_schema_id",
        "command_schema_version",
        "command_schema_sha256",
        "idempotency_key",
        "command_payload_hash",
        "correlation_id",
        "causation_id",
        "actor_id",
        "authority_grant_id",
        "occurred_at",
        "recorded_at",
        "payload",
        "previous_event_hash",
        "event_hash",
    }
)
_INDEPENDENT_BANNED_FIELDS = {
    "command_key",
    "event_key",
    "subject_reference",
    "evidence_reference",
    "source_model_citation",
}
_INDEPENDENT_DISPOSITIONS = {
    "accepted",
    "partial_accepted",
    "deferred",
    "superseded",
    "removed_by_amendment",
    "cancelled",
    "rejected",
}
_INDEPENDENT_MESSAGE_TYPES = {
    "assignment",
    "acknowledgement",
    "progress",
    "input_request",
    "escalation",
    "report",
    "review_request",
    "review_response",
    "decision_request",
    "handoff",
}
_INDEPENDENT_MESSAGE_COMMON_FACTS = {
    "message_type",
    "sender_actor_id",
    "recipient_actor_ids",
    "audience",
    "task_id",
    "dispatch_id",
    "attempt_id",
    "review_id",
    "decision_id",
    "reply_to_message_id",
    "thread_id",
    "typed_subject",
    "sensitivity_class",
    "retention_class",
}
_INDEPENDENT_ACTIONABLE_MESSAGES = {
    "assignment",
    "input_request",
    "escalation",
    "review_request",
    "decision_request",
    "handoff",
}


def _walk_schema_objects(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        result = [value] if value.get("type") == "object" else []
        return result + [item for child in value.values() for item in _walk_schema_objects(child)]
    if isinstance(value, list):
        return [item for child in value for item in _walk_schema_objects(child)]
    return []


def _verify_independent_scope_and_message_contracts(repo_root: Path) -> None:
    command_paths = sorted((repo_root / ".research-system/schemas/core/commands").glob("*.schema.json"))
    event_paths = sorted((repo_root / ".research-system/schemas/core/events").glob("*.schema.json"))
    _require(len(command_paths) == 87 and len(event_paths) == 86, "independent generated schema count mismatch")
    for kind, paths, expected_root in (
        ("command", command_paths, _INDEPENDENT_COMMAND_ROOT),
        ("event", event_paths, _INDEPENDENT_EVENT_ROOT),
    ):
        for path in paths:
            schema = _semantic_schema(path)
            _require(set(schema.get("required", [])) == expected_root, f"independent {kind} root mismatch: {path}")
            _require(set(schema.get("properties", {})) == expected_root, f"independent {kind} fields mismatch: {path}")
            text = json.dumps(schema)
            _require(
                not any(f'"{field}"' in text for field in _INDEPENDENT_BANNED_FIELDS),
                f"banned toy payload field returned: {path}",
            )
            _require(
                all(item.get("additionalProperties") is False for item in _walk_schema_objects(schema)),
                f"independent open-object check failed: {path}",
            )

    create = _semantic_schema(repo_root / ".research-system/schemas/core/commands/create_scope_definition.schema.json")
    member = create["$defs"]["scope_member"]
    _require(
        set(member["required"]) == {"member_id", "member_kind", "required_disposition"},
        "ScopeMember relational fields mismatch",
    )
    _require(
        set(member["properties"]["required_disposition"].get("enum", [])) == _INDEPENDENT_DISPOSITIONS,
        "ScopeMember disposition vocabulary mismatch",
    )
    create_required = set(create["$defs"]["payload"]["oneOf"][0]["required"])
    _require(
        {
            "new_scope_definition_id",
            "members",
            "dependencies",
            "ordering_rules",
            "completion_rule",
            "authority_rule",
            "effective_revision",
            "effective_at",
            "supersession_rule",
            "supersession_lineage",
        }
        <= create_required,
        "CreateScopeDefinition facts are incomplete",
    )
    _require(
        create["$defs"]["payload"]["oneOf"][0]["properties"]["effective_revision"].get("minimum") == 1,
        "Scope effective revision is not positive",
    )
    for name in ("amend_scope_definition", "complete_scope"):
        scope = _semantic_schema(repo_root / f".research-system/schemas/core/commands/{name}.schema.json")
        disposition = scope["$defs"]["member_disposition"]
        _require(
            set(disposition["required"]) == {"member_id", "member_kind", "disposition"},
            f"MemberDisposition relational fields mismatch: {name}",
        )
        _require(
            set(disposition["properties"]["disposition"].get("enum", [])) == _INDEPENDENT_DISPOSITIONS,
            f"MemberDisposition vocabulary mismatch: {name}",
        )

    for path in (
        repo_root / ".research-system/schemas/core/commands/publish_message.schema.json",
        repo_root / ".research-system/schemas/core/events/message_published.schema.json",
    ):
        message = _semantic_schema(path)
        is_command = path.parent.name == "commands"
        message_identity = "new_message_id" if is_command else "message_id"
        forbidden_identity = "message_id" if is_command else "new_message_id"
        expected_common = _INDEPENDENT_MESSAGE_COMMON_FACTS | {message_identity}
        variants = message["$defs"]["payload"]["oneOf"]
        _require(len(variants) == 10, f"message variant cardinality mismatch: {path}")
        _require(
            {variant["properties"]["message_type"]["const"] for variant in variants} == _INDEPENDENT_MESSAGE_TYPES,
            f"message type vocabulary mismatch: {path}",
        )
        body_ref = message["$defs"]["body_artefact_ref"]
        _require(
            set(body_ref["required"]) == {"artefact_id", "content_sha256"}
            and body_ref.get("additionalProperties") is False,
            f"message body artefact reference mismatch: {path}",
        )
        for variant in variants:
            message_type = variant["properties"]["message_type"]["const"]
            required = set(variant["required"])
            properties = variant["properties"]
            _require(expected_common <= required, f"message common facts missing: {path}")
            _require(
                forbidden_identity not in properties,
                f"command/event message identity leaked across the boundary: {path}",
            )
            _require(
                variant.get("oneOf") == [{"required": ["body"]}, {"required": ["body_artefact_ref"]}],
                f"message body XOR mismatch: {path}",
            )
            for field in ("task_id", "dispatch_id", "attempt_id", "review_id", "decision_id", "reply_to_message_id"):
                _require(
                    set(properties[field].get("type", [])) == {"string", "null"},
                    f"message nullable correlation mismatch: {path}/{field}",
                )
            applicable = message_type in _INDEPENDENT_ACTIONABLE_MESSAGES
            _require(
                ({"requested_action", "deadline"} <= required) == applicable,
                f"message action/deadline applicability mismatch: {path}/{message_type}",
            )


def _verify_generated_semantics(
    *,
    path: Path,
    kind: str,
    semantic_type: str,
    payload_specs: list[schema_source.ObjectSpec],
) -> None:
    schema = _semantic_schema(path)
    expected_root = set(schema_source.COMMAND_ROOT_NAMES if kind == "command" else schema_source.EVENT_ROOT_NAMES)
    _require(set(schema.get("required", [])) == expected_root, f"generated {kind} root mismatch: {path}")
    properties = schema.get("properties")
    _require(
        isinstance(properties, Mapping) and set(properties) == expected_root, f"generated root fields mismatch: {path}"
    )
    _require("envelope" not in properties, f"nested envelope returned: {path}")
    _require(schema.get("additionalProperties") is False, f"generated root is not closed: {path}")
    _require(schema.get("$id") == f"ars://core/{kind}/{semantic_type}", f"generated schema id mismatch: {path}")
    type_field = f"{kind}_type"
    _require(properties[type_field].get("const") == semantic_type, f"generated semantic type mismatch: {path}")
    _require(properties["payload"] == {"$ref": "#/$defs/payload"}, f"generated payload ref mismatch: {path}")
    variants = schema.get("$defs", {}).get("payload", {}).get("oneOf")
    _require(isinstance(variants, list) and variants, f"generated payload union is empty: {path}")
    actual_shapes = [_schema_object_shape(variant, schema) for variant in variants]
    expected_shapes = list(dict.fromkeys(_object_spec_shape(spec) for spec in payload_specs))
    _require(actual_shapes == expected_shapes, f"generated payload semantics mismatch: {path}")


def _verify_all_generated_semantics(repo_root: Path) -> None:
    _verify_independent_scope_and_message_contracts(repo_root)
    rows = schema_source.source_rows(repo_root)
    operations = schema_source.resolve_operation_specs(repo_root, rows)
    for kind in ("command", "event"):
        for relative_path, group in schema_source.grouped_rows(rows, kind=kind).items():
            semantic_type = group[0][2]
            payload_specs: list[schema_source.ObjectSpec] = []
            for row, _, _ in group:
                operation = operations[row.key]
                if kind == "command":
                    payload_specs.append(operation.command_payload)
                else:
                    payload_specs.extend(
                        payload for event_type, payload in operation.event_payloads if event_type == semantic_type
                    )
            _verify_generated_semantics(
                path=repo_root / relative_path,
                kind=kind,
                semantic_type=semantic_type,
                payload_specs=payload_specs,
            )


def validate_wp6_1_contract_materialization(
    *,
    catalogue_path: Path,
    identities_path: Path,
    schema_root: Path,
    observed_runtime_rows: list[Mapping[str, Any]] | None = None,
) -> Wp61MaterializationSummary:
    """Validate the WP6.1 candidate pair against the owner-approved annex.

    Runtime registrations are deliberately absent from this seam. They may become
    comparison inputs only after the independently reviewed artifacts receive the
    D-G6-3 owner acceptance required before runtime implementation.
    """

    schema_root = schema_root.resolve()
    repo_root = schema_root.parent.parent
    _verify_stage2_overlay_bytes(repo_root)
    identities_bytes, identities = _read_yaml(identities_path)
    _, catalogue = _read_yaml(catalogue_path)
    registry = _schema_registry(schema_root)
    registry.validate(WP6_1_IDENTITIES_SCHEMA_ID, identities)
    registry.validate(WP6_1_CATALOGUE_SCHEMA_ID, catalogue)
    acceptance_bytes, acceptance = _read_yaml(repo_root / _STAGE1_ACCEPTANCE_PATH)
    registry.validate(_STAGE1_ACCEPTANCE_SCHEMA_ID, acceptance)
    _require(
        hashlib.sha256(acceptance_bytes).hexdigest() == _STAGE1_ACCEPTANCE_SHA256, "Stage-1 acceptance SHA-256 mismatch"
    )
    _require(
        _git_blob_id(acceptance_bytes, repo_root) == _STAGE1_ACCEPTANCE_BLOB, "Stage-1 acceptance Git blob mismatch"
    )
    expected_record = {
        "repository_path": _STAGE1_ACCEPTANCE_PATH,
        "schema_id": _STAGE1_ACCEPTANCE_SCHEMA_ID,
        "schema_version": "1.0.0",
        "git_blob_id": _STAGE1_ACCEPTANCE_BLOB,
        "canonical_utf8_lf_sha256": _STAGE1_ACCEPTANCE_SHA256,
    }
    for manifest in (identities, catalogue):
        _require(
            manifest["stage1_owner_acceptance"]["record"] == expected_record,
            "Stage-1 acceptance record identity mismatch",
        )
        _require(
            manifest["stage1_owner_acceptance"]["accepted_stage1_tuple"] == acceptance["accepted_stage1_tuple"],
            "Stage-1 accepted tuple mismatch",
        )
        _require(
            manifest["stage1_owner_acceptance"]["acceptance_statement"] == acceptance["acceptance_statement"],
            "Stage-1 acceptance statement mismatch",
        )

    _require(identities["source_annex"] == _SOURCE_ANNEX, "identity source annex mismatch")
    _require(catalogue["source_annex"] == _SOURCE_ANNEX, "catalogue source annex mismatch")
    _require(identities["owner_source_annex"] == _OWNER_SOURCE_ANNEX, "identity owner source annex mismatch")
    _require(catalogue["owner_source_annex"] == _OWNER_SOURCE_ANNEX, "catalogue owner source annex mismatch")
    _require(identities["governance"] == _GOVERNANCE, "identity governance status mismatch")
    _require(catalogue["governance"] == _GOVERNANCE, "catalogue governance status mismatch")
    _require(catalogue["state_classes"] == _STATE_CLASSES, "closed state class mismatch")
    _require(catalogue["negative_profiles"] == _NEGATIVE_PROFILES, "closed negative profile mismatch")
    _require(
        catalogue["correction_selector"]
        == {
            "selector_id": "projection_selector/corrected_record_kind/v1",
            "governance_index": "governance_correction_index",
            "mappings": _CORRECTION_MAPPINGS,
        },
        "closed correction selector mismatch",
    )
    _require(
        catalogue["decision_rule_evaluation_non_compensation"] == _NON_COMPENSATION,
        "Decision/RuleEvaluation non-compensation mismatch",
    )

    manifest_ref = catalogue["schema_identity_manifest"]
    _require(
        manifest_ref["git_blob_id"] == _git_blob_id(identities_bytes, repo_root),
        "identity manifest Git blob mismatch",
    )
    _require(
        manifest_ref["canonical_utf8_lf_sha256"] == hashlib.sha256(identities_bytes).hexdigest(),
        "identity manifest SHA-256 mismatch",
    )

    _verify_fact_annex_provenance(repo_root)
    approved_annex_bytes = _verify_approved_annex_provenance(repo_root)
    annex_rows = _parse_annex_bytes(approved_annex_bytes)
    binding_surface = [[row.source_table, *row.cells] for row in annex_rows]
    _require(
        _sha256_value(binding_surface) == APPROVED_WP6_1_ANNEX_ROW_BINDING_SHA256,
        "approved annex row-binding digest mismatch",
    )
    section_counts = {
        section: sum(row.source_table == section for row in annex_rows)
        for section in ("w2_lifecycle", "w2_messages_governance", "w8_operator")
    }
    _require(
        section_counts == {"w2_lifecycle": 50, "w2_messages_governance": 41, "w8_operator": 13},
        "approved annex section cardinality mismatch",
    )
    expected_keys = [row.key for row in annex_rows]
    _require(len(expected_keys) == 104 and len(set(expected_keys)) == 104, "approved annex key cardinality mismatch")

    catalogue_rows = catalogue["rows"]
    identity_rows = identities["rows"]
    _require([row["key"] for row in catalogue_rows] == expected_keys, "catalogue key order/multiset mismatch")
    _require([row["key"] for row in identity_rows] == expected_keys, "identity key order/multiset mismatch")
    identity_by_key = {row["key"]: row for row in identity_rows}

    positive_tests: list[str] = []
    negative_tests: list[str] = []
    expected_runtime_observations: list[dict[str, Any]] = []
    for annex_row, row in zip(annex_rows, catalogue_rows, strict=True):
        cells = annex_row.cells
        schema_token, command_type, events, event_tokens = _command_event_parts(cells[2])
        command_identity = _identity_object(schema_token, command_type, "command", repo_root)
        event_identities = [
            _identity_object(event_token, event_type, "event", repo_root)
            for event_type, event_token in zip(events, event_tokens, strict=True)
        ]
        reducers, projections, selector = _reducer_projection_parts(cells[3])
        receipt_cell = _plain(cells[5])
        positive_match = re.search(r"(pos_[a-z0-9_]+)", receipt_cell)
        profile_match = re.search(r"(N0|NE|NA|NI|NC|NS)\s*$", receipt_cell)
        _require(positive_match is not None and profile_match is not None, f"invalid test binding: {annex_row.key}")
        positive_test = positive_match.group(1)
        negative_profile = profile_match.group(1)
        expanded_negatives = [
            f"neg_{annex_row.key.replace('.', '_')}_{case_name}" for case_name in _NEGATIVE_PROFILES[negative_profile]
        ]
        expected_annex_binding = {
            "owner_transition_discriminator": cells[1],
            "command_event_identity": cells[2],
            "reducer_projections_selector": cells[3],
            "authority_precondition": cells[4],
            "receipt_positive_negatives": cells[5],
        }
        _require(row["source_table"] == annex_row.source_table, f"source table mismatch: {annex_row.key}")
        _require(row["command_type"] == command_type, f"command type mismatch: {annex_row.key}")
        _require(
            row["owner_transition_discriminator"] == cells[1],
            f"owner transition/discriminator mismatch: {annex_row.key}",
        )
        _require(row["transition"] == _transition(cells[1], annex_row.source_table), f"edge mismatch: {annex_row.key}")
        _verify_schema_identity(row["command_schema_identity"], command_identity, repo_root)
        _require(row["ordered_events"] == events, f"ordered event mismatch: {annex_row.key}")
        _require(row["event_schema_bindings"] == event_identities, f"event identity mismatch: {annex_row.key}")
        for identity, expected in zip(row["event_schema_bindings"], event_identities, strict=True):
            _verify_schema_identity(identity, expected, repo_root)
        _require(row["reducers"] == reducers, f"reducer effect mismatch: {annex_row.key}")
        _require(row["projections"] == projections, f"projection effect mismatch: {annex_row.key}")
        _require(row["projection_selector"] == selector, f"projection selector mismatch: {annex_row.key}")
        _require(
            row["authority"] == _authority(cells[4], annex_row.key, command_type),
            f"authority mismatch: {annex_row.key}",
        )
        _require(row["receipt"] == "R", f"receipt mismatch: {annex_row.key}")
        _require(row["positive_test"] == positive_test, f"positive-test mismatch: {annex_row.key}")
        _require(row["negative_profile"] == negative_profile, f"negative profile mismatch: {annex_row.key}")
        _require(row["expanded_negative_tests"] == expanded_negatives, f"negative-test mismatch: {annex_row.key}")
        expected_atomic = _atomic_claim_binding() if command_type == "ClaimDispatch" else None
        _require(row["atomic_binding"] == expected_atomic, f"atomic claim binding mismatch: {annex_row.key}")
        _require(row["annex_binding"] == expected_annex_binding, f"annex binding mismatch: {annex_row.key}")

        identity_row = identity_by_key[annex_row.key]
        expected_identity_row = {
            "key": annex_row.key,
            "command_type": command_type,
            "command_schema_identity": command_identity,
            "event_schema_bindings": event_identities,
        }
        expected_identity_row["row_identity_contract_sha256"] = _sha256_value(expected_identity_row)
        _require(identity_row == expected_identity_row, f"identity row mismatch: {annex_row.key}")
        _require(
            identity_row["command_schema_identity"] == row["command_schema_identity"]
            and identity_row["event_schema_bindings"] == row["event_schema_bindings"],
            f"catalogue/identity pair mismatch: {annex_row.key}",
        )
        positive_tests.append(row["positive_test"])
        negative_tests.extend(row["expanded_negative_tests"])
        expected_runtime_observations.append(
            {
                "key": annex_row.key,
                "command_type": command_type,
                "command_schema_id": command_identity["command_schema_id"],
                "ordered_events": events,
                "event_schema_ids": [identity["event_schema_id"] for identity in event_identities],
            }
        )

    _require(len(set(positive_tests)) == 104, "positive test alias detected")
    _require(len(set(negative_tests)) == len(negative_tests), "expanded negative test alias detected")
    if observed_runtime_rows is not None:
        _require(
            observed_runtime_rows == expected_runtime_observations,
            "observed runtime rows differ from the independently fixed owner catalogue",
        )
    _verify_content_hashes(identities, "row_identity_contract_sha256", "row_identity_multiset_sha256")
    _verify_content_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")
    expanded_edges = _expanded_edge_count(catalogue_rows)
    _require(expanded_edges == 182, "expanded edge cardinality mismatch")

    return Wp61MaterializationSummary(
        normalized_row_count=len(catalogue_rows),
        expanded_edge_count=expanded_edges,
        catalogue_multiset_sha256=catalogue["catalogue_multiset_sha256"],
        row_identity_multiset_sha256=identities["row_identity_multiset_sha256"],
    )
