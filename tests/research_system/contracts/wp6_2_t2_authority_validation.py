"""Independent semantic and content-address validation for the P-037 T2 candidate."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from jsonschema import Draft202012Validator

from research_system.schema_registry import SchemaRegistry
from tests.research_system.contracts.wp6_2_t2_expectations import (
    CATALOGUE_PATH,
    CATALOGUE_SCHEMA_PATH,
    CROSSWALK_AUTHORITIES,
    CROSSWALK_PATH,
    CROSSWALK_SCHEMA_PATH,
    EXPECTED_CROSSWALK,
    EXPECTED_ROWS,
    IDEMPOTENCY_TUPLE,
    IDENTITY_MANIFEST_PATH,
    IDENTITY_MANIFEST_SCHEMA_PATH,
    MATERIALIZED_LEAF_PATHS,
    NEGATIVE_CASES,
    PRE_ISSUE_SENTINEL_SEAMS,
    PROTECTED_PROVIDER_BLOBS,
    PROTECTED_TREE_IDENTITIES,
    SCHEMA_IDENTITIES,
    START_REVISION,
    WRITER,
)

UUID7_RE = re.compile(
    r"^(?P<prefix>[a-z][a-z0-9]*)_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class T2ContractError(ValueError):
    """Raised when a T2 candidate violates its independent authority contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise T2ContractError(message)


def _raw_utf8_lf(repo_root: Path, relative_path: str) -> bytes:
    raw = (repo_root / relative_path).read_bytes()
    _require(not raw.startswith(b"\xef\xbb\xbf"), f"UTF-8 BOM is prohibited: {relative_path}")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise T2ContractError(f"invalid UTF-8: {relative_path}") from exc
    _require(b"\r" not in raw, f"non-LF line ending: {relative_path}")
    _require(raw.endswith(b"\n"), f"missing final LF: {relative_path}")
    return raw


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _git_blob(repo_root: Path, relative_path: str) -> str:
    return _git(repo_root, "hash-object", "--no-filters", "--", relative_path)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_json_bytes(raw: bytes, relative_path: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise T2ContractError(f"invalid JSON: {relative_path}") from exc
    _require(isinstance(value, dict), f"JSON root is not an object: {relative_path}")
    return value


def _load_yaml_bytes(raw: bytes, relative_path: str) -> dict[str, Any]:
    value = yaml.safe_load(raw)
    _require(isinstance(value, dict), f"YAML root is not an object: {relative_path}")
    return value


def _validate_json_schema(schema: Mapping[str, Any], value: object, label: str) -> None:
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).iter_errors(value),
        key=lambda error: [str(item) for item in error.absolute_path],
    )
    if errors:
        rendered = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}" for error in errors
        )
        raise T2ContractError(f"{label} schema violation: {rendered}")


def _walk_schema(value: object) -> list[Mapping[str, Any]]:
    if isinstance(value, dict):
        return [value, *(item for child in value.values() for item in _walk_schema(child))]
    if isinstance(value, list):
        return [item for child in value for item in _walk_schema(child)]
    return []


def _validate_leaf_schemas(repo_root: Path) -> None:
    registry = SchemaRegistry(repo_root / ".research-system" / "schemas")
    for name, identity in SCHEMA_IDENTITIES.items():
        raw = _raw_utf8_lf(repo_root, identity["path"])
        schema = _load_json_bytes(raw, identity["path"])
        Draft202012Validator.check_schema(schema)
        _require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"draft mismatch: {name}")
        _require(schema.get("$id") == identity["schema_id"], f"schema identity mismatch: {name}")
        properties = schema.get("properties")
        _require(isinstance(properties, Mapping), f"schema properties missing: {name}")
        _require(
            properties.get("schema_version") == {"const": identity["schema_version"]},
            f"schema version mismatch: {name}",
        )
        for node in _walk_schema(schema):
            if node.get("type") == "object" and "properties" in node:
                _require(node.get("additionalProperties") is False, f"open object in schema: {name}")
        _require(registry.contains(identity["schema_id"]), f"schema registry omission: {name}")

    command_v2 = _load_json_bytes(
        _raw_utf8_lf(repo_root, SCHEMA_IDENTITIES["provider_command_v2"]["path"]),
        SCHEMA_IDENTITIES["provider_command_v2"]["path"],
    )
    receipt_v2 = _load_json_bytes(
        _raw_utf8_lf(repo_root, SCHEMA_IDENTITIES["provider_receipt_v2"]["path"]),
        SCHEMA_IDENTITIES["provider_receipt_v2"]["path"],
    )
    _require(
        command_v2.get("x-successor-of") == {"schema_id": "ars://adapters/provider-command", "schema_version": "1.0.0"},
        "ProviderCommand successor binding mismatch",
    )
    _require(
        receipt_v2.get("x-successor-of") == {"schema_id": "ars://adapters/provider-receipt", "schema_version": "1.0.0"},
        "ProviderReceipt successor binding mismatch",
    )


def _identity_from_file(repo_root: Path, identity: Mapping[str, str]) -> dict[str, str]:
    raw = _raw_utf8_lf(repo_root, identity["path"])
    return {
        "repository_path": identity["path"],
        "schema_id": identity["schema_id"],
        "schema_version": identity["schema_version"],
        "git_blob_id": _git_blob(repo_root, identity["path"]),
        "raw_utf8_lf_sha256": _sha256(raw),
    }


def _event_identity_from_file(repo_root: Path, event_type: str) -> dict[str, str]:
    identity = _identity_from_file(repo_root, SCHEMA_IDENTITIES[event_type])
    return {"event_type": event_type, **identity}


def validate_catalogue_semantics(catalogue: Mapping[str, Any], repo_root: Path) -> None:
    """Validate catalogue meaning against literals independent of the candidate."""

    _require(catalogue.get("writer") == WRITER, "writer mismatch")
    _require(catalogue.get("transition_family_closed") is True, "transition family is not closed")
    _require(catalogue.get("idempotency_tuple") == IDEMPOTENCY_TUPLE, "idempotency tuple mismatch")
    _require(catalogue.get("pre_issue_sentinel_seams") == PRE_ISSUE_SENTINEL_SEAMS, "sentinel seam mismatch")
    expected_codes = {name: details["rejection_code"] for name, details in NEGATIVE_CASES.items()}
    _require(catalogue.get("negative_controls") == expected_codes, "negative-control set mismatch")
    _require(
        set(catalogue.get("stable_rejection_codes", [])) == {code for code in expected_codes.values() if code},
        "stable rejection-code set mismatch",
    )
    _require(
        catalogue.get("universal_rejection_effects")
        == {"canonical_event_count": 0, "provider_invocation_count": 0, "automatic_retry": False},
        "universal rejection effects mismatch",
    )
    rows = catalogue.get("rows")
    _require(isinstance(rows, list) and len(rows) == 3, "authority catalogue must contain exactly three rows")
    referenced_negatives: set[str] = set()
    for row, expected in zip(rows, EXPECTED_ROWS, strict=True):
        _require(isinstance(row, Mapping), "authority row is not an object")
        for key, value in expected.items():
            _require(row.get(key) == value, f"authority row mismatch: {expected['key']}/{key}")
        command_identity = _identity_from_file(repo_root, SCHEMA_IDENTITIES[expected["command_type"]])
        _require(
            row.get("command_schema_identity") == command_identity, f"command identity mismatch: {expected['key']}"
        )
        event_identities = [_event_identity_from_file(repo_root, event) for event in expected["ordered_events"]]
        _require(row.get("event_schema_bindings") == event_identities, f"event identity mismatch: {expected['key']}")
        atomic = row.get("atomic_batch")
        _require(isinstance(atomic, Mapping), f"atomic binding missing: {expected['key']}")
        _require(atomic.get("required") is True, f"atomic publication not required: {expected['key']}")
        _require(
            atomic.get("transaction_count") == len(expected["ordered_events"]),
            f"batch count mismatch: {expected['key']}",
        )
        _require(
            atomic.get("ordered_event_types") == expected["ordered_events"], f"batch order mismatch: {expected['key']}"
        )
        _require(
            [item["stream_role"] for item in row.get("write_set_contract", [])] == expected["write_set"],
            f"write-set contract mismatch: {expected['key']}",
        )
        _require(row.get("receipt_binding", {}).get("schema_id") == "ars://core/receipt/v2", "receipt schema mismatch")
        _require(row.get("receipt_binding", {}).get("schema_version") == "2.0.0", "receipt version mismatch")
        referenced_negatives.update(row.get("negative_tests", []))
    _require(referenced_negatives == set(NEGATIVE_CASES), "row negative-test coverage mismatch")


def validate_protected_snapshot(observed_trees: Mapping[str, str], observed_provider_blobs: Mapping[str, str]) -> None:
    _require(dict(observed_trees) == PROTECTED_TREE_IDENTITIES, "protected WP6.1 tree identity mismatch")
    _require(dict(observed_provider_blobs) == PROTECTED_PROVIDER_BLOBS, "protected provider 1.0.0 blob mismatch")


def _validate_protected_bytes(repo_root: Path) -> None:
    observed_trees = {path: _git(repo_root, "rev-parse", f"HEAD:{path}") for path in PROTECTED_TREE_IDENTITIES}
    observed_provider_blobs = {path: _git(repo_root, "rev-parse", f"HEAD:{path}") for path in PROTECTED_PROVIDER_BLOBS}
    validate_protected_snapshot(observed_trees, observed_provider_blobs)
    protected_pathspecs = [
        ".research-system/contracts/wp6-1-*",
        ".research-system/schemas/contracts/wp6-1-*",
        ".research-system/schemas/core/commands",
        ".research-system/schemas/core/events",
        "docs/plans/agentic-research-system/implementation/06d-wp6-1-owner-source-catalogue.md",
        "docs/plans/agentic-research-system/implementation/06e-wp6-1-schema-fact-annex-proposal.md",
        "tests/research_system/contracts/*wp6_1*",
        ".research-system/contracts/wp6-2-live-grader-calibration-*",
        ".research-system/contracts/wp6_2_live_grader_calibration_future_result_semantics.py",
        ".research-system/schemas/contracts/wp6-2-live-grader-calibration-*",
        "tests/research_system/unit/*wp6_2_live_grader_calibration*",
        *PROTECTED_PROVIDER_BLOBS,
    ]
    changed = _git(repo_root, "diff", "--name-only", START_REVISION, "--", *protected_pathspecs)
    _require(not changed, f"protected WP6.1/T1a/provider bytes changed: {changed}")


def _expected_manifest_schema_identity(repo_root: Path, relative_path: str) -> tuple[str | None, str | None]:
    if relative_path.endswith(".schema.json"):
        schema = _load_json_bytes(_raw_utf8_lf(repo_root, relative_path), relative_path)
        version = schema.get("properties", {}).get("schema_version", {}).get("const")
        return schema.get("$id"), version
    if relative_path == CATALOGUE_PATH:
        return "ars://contracts/wp6-2-t2-cost-grant-authority-catalogue", "1.0.0"
    if relative_path == CROSSWALK_PATH:
        return "ars://contracts/wp6-2-t2-normative-crosswalk", "1.0.0"
    return None, None


def _validate_manifest(manifest: Mapping[str, Any], repo_root: Path, catalogue: Mapping[str, Any]) -> None:
    _require(
        manifest.get("status") == "proposed_pending_fresh_independent_review_and_stephen_exact_hash_acceptance",
        "manifest lifecycle mismatch",
    )
    _require(
        manifest.get("self_identity")
        == {
            "repository_path": IDENTITY_MANIFEST_PATH,
            "schema_id": "ars://contracts/wp6-2-t2-schema-identities",
            "schema_version": "1.0.0",
            "hash_binding": "external_exact_state_review_and_owner_acceptance_only",
        },
        "manifest self-identity rule mismatch",
    )
    artifacts = manifest.get("artifacts")
    _require(isinstance(artifacts, list), "manifest artifacts missing")
    by_path = {item.get("repository_path"): item for item in artifacts if isinstance(item, Mapping)}
    _require(set(by_path) == MATERIALIZED_LEAF_PATHS, "manifest leaf path set mismatch")
    for relative_path in sorted(MATERIALIZED_LEAF_PATHS):
        raw = _raw_utf8_lf(repo_root, relative_path)
        schema_id, schema_version = _expected_manifest_schema_identity(repo_root, relative_path)
        expected = {
            "repository_path": relative_path,
            "canonical_schema_id": schema_id,
            "schema_version": schema_version,
            "git_blob_id": _git_blob(repo_root, relative_path),
            "raw_utf8_lf_sha256": _sha256(raw),
        }
        for key, value in expected.items():
            _require(by_path[relative_path].get(key) == value, f"manifest artifact mismatch: {relative_path}/{key}")
        _require(
            isinstance(by_path[relative_path].get("artifact_role"), str), f"artifact role missing: {relative_path}"
        )

    authority_rows = manifest.get("authority_rows")
    _require(isinstance(authority_rows, list) and len(authority_rows) == 3, "manifest authority rows mismatch")
    for identity_row, catalogue_row in zip(authority_rows, catalogue["rows"], strict=True):
        expected = {
            "key": catalogue_row["key"],
            "ordered_event_set": catalogue_row["ordered_events"],
            "reducers": catalogue_row["reducers"],
            "projections": catalogue_row["projections"],
            "stream_write_set": catalogue_row["write_set"],
            "authority": {
                "scope": catalogue_row["authority_scope"],
                "subject": catalogue_row["authority_subject"],
                "subject_fields": catalogue_row["authority_subject_fields"],
            },
            "receipt": catalogue_row["receipt_binding"],
            "test_identity": {
                "positive": catalogue_row["positive_test"],
                "negative": catalogue_row["negative_tests"],
            },
        }
        _require(identity_row == expected, f"manifest authority binding mismatch: {catalogue_row['key']}")

    tests = manifest.get("test_identities")
    _require(isinstance(tests, Mapping), "manifest test identities missing")
    _require(
        tests.get("positive_tests") == [row["positive_test"] for row in EXPECTED_ROWS],
        "positive test identity mismatch",
    )
    _require(set(tests.get("negative_tests", [])) == set(NEGATIVE_CASES), "negative test identity mismatch")
    graph = manifest.get("hash_dependency_graph")
    _require(
        graph
        == [
            "leaf_exact_bytes_to_identity_manifest",
            "identity_manifest_to_external_independent_review",
            "external_independent_review_to_stephen_exact_hash_acceptance",
        ],
        "hash dependency graph mismatch",
    )
    lifecycle = manifest.get("candidate_lifecycle")
    _require(
        lifecycle
        == {
            "review_status": "pending_fresh_independent_review",
            "acceptance_status": "pending_stephen_exact_hash_acceptance",
            "runtime_implementation_authorized": False,
        },
        "candidate lifecycle self-attestation mismatch",
    )


def validate_t2_authority_contract(repo_root: Path) -> None:
    """Validate the complete materialized T2 candidate at ``repo_root``."""

    repo_root = repo_root.resolve()
    catalogue_raw = _raw_utf8_lf(repo_root, CATALOGUE_PATH)
    catalogue = _load_yaml_bytes(catalogue_raw, CATALOGUE_PATH)
    catalogue_schema = _load_json_bytes(_raw_utf8_lf(repo_root, CATALOGUE_SCHEMA_PATH), CATALOGUE_SCHEMA_PATH)
    _validate_json_schema(catalogue_schema, catalogue, "catalogue")
    validate_catalogue_semantics(catalogue, repo_root)
    _validate_leaf_schemas(repo_root)
    _validate_protected_bytes(repo_root)

    crosswalk_raw = _raw_utf8_lf(repo_root, CROSSWALK_PATH)
    crosswalk = _load_yaml_bytes(crosswalk_raw, CROSSWALK_PATH)
    crosswalk_schema = _load_json_bytes(
        _raw_utf8_lf(repo_root, CROSSWALK_SCHEMA_PATH),
        CROSSWALK_SCHEMA_PATH,
    )
    _validate_json_schema(crosswalk_schema, crosswalk, "normative crosswalk")
    validate_crosswalk(crosswalk)

    manifest_raw = _raw_utf8_lf(repo_root, IDENTITY_MANIFEST_PATH)
    manifest = _load_yaml_bytes(manifest_raw, IDENTITY_MANIFEST_PATH)
    manifest_schema = _load_json_bytes(
        _raw_utf8_lf(repo_root, IDENTITY_MANIFEST_SCHEMA_PATH),
        IDENTITY_MANIFEST_SCHEMA_PATH,
    )
    _validate_json_schema(manifest_schema, manifest, "identity manifest")
    _validate_manifest(manifest, repo_root, catalogue)

    registry = SchemaRegistry(repo_root / ".research-system" / "schemas")
    _require(registry.contains(catalogue_schema["$id"]), "catalogue schema registry omission")
    _require(registry.contains(manifest_schema["$id"]), "manifest schema registry omission")


def validate_crosswalk(crosswalk: Mapping[str, Any]) -> None:
    _require(set(crosswalk.get("authorities", [])) == CROSSWALK_AUTHORITIES, "crosswalk authority set mismatch")
    rows = crosswalk.get("rows")
    _require(isinstance(rows, list), "crosswalk rows missing")
    actual = {row.get("finding_id"): {key: value for key, value in row.items() if key != "finding_id"} for row in rows}
    _require(actual == EXPECTED_CROSSWALK, "crosswalk independent-oracle mismatch")


def validate_event_observation(command_type: str, event_types: Sequence[str]) -> None:
    expected_by_command = {row["command_type"]: row["ordered_events"] for row in EXPECTED_ROWS}
    _require(command_type in expected_by_command, "unknown T2 command")
    expected = expected_by_command[command_type]
    _require(len(event_types) == len(expected), "event_batch_incomplete")
    _require(list(event_types) == expected, "event_batch_order_invalid")


def validate_canonical_id(value: object, prefix: str) -> None:
    _require(isinstance(value, str), "canonical_id_invalid")
    match = UUID7_RE.fullmatch(value)
    _require(match is not None and match.group("prefix") == prefix, "canonical_id_invalid")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def rebuild_idempotency_index(canonical_event_bytes: Sequence[bytes]) -> dict[str, tuple[str, str]]:
    """Rebuild the T2 idempotency index from canonical serialized event bytes."""

    index: dict[str, tuple[str, str]] = {}
    effects: set[tuple[str, str]] = set()
    effect_fields = {
        "CostGrantIssued": "cost_grant_id",
        "CostGrantReserved": "reservation_id",
        "ProviderCommandIssued": "provider_command_id",
        "ProviderReceiptRecorded": "provider_receipt_id",
        "CostGrantReconciled": "reservation_id",
    }
    for raw in canonical_event_bytes:
        _require(isinstance(raw, bytes), "event_bytes_required")
        try:
            event = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise T2ContractError("invalid canonical event bytes") from exc
        _require(_canonical_json_bytes(event) == raw, "noncanonical event bytes")
        _require(isinstance(event, Mapping), "event must be an object")
        command_id = event.get("command_id")
        idempotency_hash = event.get("idempotency_key_hash")
        payload_hash = event.get("payload_hash")
        _require(
            all(isinstance(item, str) for item in (command_id, idempotency_hash, payload_hash)),
            "event index binding missing",
        )
        binding = (idempotency_hash, payload_hash)
        previous = index.setdefault(command_id, binding)
        _require(previous == binding, "idempotency_conflict")
        event_type = event.get("event_type")
        payload = event.get("payload")
        _require(event_type in effect_fields and isinstance(payload, Mapping), "unknown T2 event effect")
        effect_id = payload.get(effect_fields[event_type])
        _require(isinstance(effect_id, str), "event effect identity missing")
        effect = (event_type, effect_id)
        _require(effect not in effects, "duplicate replay effect")
        effects.add(effect)
    return index


def validate_pre_issue_evidence(
    manifest: Mapping[str, Any],
    seam_payloads: Mapping[str, object],
    *,
    safe_sentinel: str,
    prohibited_material: Sequence[str],
) -> None:
    """Scan the actual recursive serialized eight-seam payload surface."""

    _require(list(seam_payloads) == PRE_ISSUE_SENTINEL_SEAMS, "pre_issue_seam_order_invalid")
    seam_records = manifest.get("seams")
    _require(isinstance(seam_records, list) and len(seam_records) == 8, "pre_issue_manifest_incomplete")
    _require(
        manifest.get("safe_synthetic_sentinel_hash") == _sha256(safe_sentinel.encode("utf-8")),
        "pre_issue_sentinel_identity_mismatch",
    )
    expected_hashes: list[str] = []
    needles = [safe_sentinel.encode("utf-8"), *(item.encode("utf-8") for item in prohibited_material)]
    for expected_seam, record in zip(PRE_ISSUE_SENTINEL_SEAMS, seam_records, strict=True):
        _require(isinstance(record, Mapping) and record.get("seam_id") == expected_seam, "pre_issue_seam_order_invalid")
        raw = _canonical_json_bytes(seam_payloads[expected_seam])
        _require(not any(needle and needle in raw for needle in needles), "secret_material_detected")
        payload_hash = _sha256(raw)
        _require(record.get("serialized_payload_hash") == payload_hash, "pre_issue_payload_hash_mismatch")
        _require(record.get("outcome") == "no_prohibited_material_or_sentinel", "pre_issue_scan_failed")
        expected_hashes.append(payload_hash)
    aggregate = _sha256("\n".join(expected_hashes).encode("ascii"))
    _require(manifest.get("aggregate_content_hash") == aggregate, "pre_issue_aggregate_hash_mismatch")


def validate_receipt_v2(receipt: Mapping[str, Any], original: Mapping[str, Any] | None = None) -> None:
    outcome = receipt.get("outcome")
    events = receipt.get("events")
    _require(isinstance(events, list), "receipt_events_invalid")
    if outcome == "accepted":
        _require(bool(events) and receipt.get("event_batch_id") is not None, "accepted_receipt_missing_events")
        _require(
            receipt.get("stable_reason") is None and receipt.get("unmet_preconditions") == [],
            "accepted_receipt_rejection_fields",
        )
    elif outcome == "duplicate":
        _require(original is not None and original.get("outcome") == "accepted", "duplicate_original_missing")
        for field in (
            "command_id",
            "idempotency_key_hash",
            "payload_hash",
            "event_batch_id",
            "events",
            "outcome_binding_hash",
        ):
            _require(receipt.get(field) == original.get(field), f"duplicate_receipt_mismatch:{field}")
        _require(
            receipt.get("original_accepted_receipt_hash") == _sha256(_canonical_json_bytes(original)),
            "duplicate_original_hash_mismatch",
        )
        _require(
            receipt.get("new_event_count") == 0 and receipt.get("new_invocation_count") == 0, "duplicate_side_effect"
        )
    elif outcome in {"rejected", "conflict"}:
        _require(events == [] and receipt.get("event_batch_id") is None, "rejected_receipt_has_events")
        _require(
            isinstance(receipt.get("stable_reason"), str) and bool(receipt.get("unmet_preconditions")),
            "rejected_receipt_reason_missing",
        )
    else:
        raise T2ContractError("receipt_outcome_invalid")


def validate_command_relations(
    command: Mapping[str, Any],
    canonical_subjects: Mapping[str, Mapping[str, Any]],
    receipt_events: Sequence[Mapping[str, Any]],
) -> None:
    """Enforce cross-object identities independently of JSON Schema shape."""

    command_type = command.get("command_type")
    expected_row = next((row for row in EXPECTED_ROWS if row["command_type"] == command_type), None)
    _require(expected_row is not None, "unknown T2 command")
    payload = command.get("payload")
    write_set = command.get("write_set")
    _require(isinstance(payload, Mapping) and isinstance(write_set, list), "command relation surface missing")
    _require(len(write_set) == len(expected_row["write_set"]), "write_set relation mismatch")
    role_id_fields = {"cost_grant": "cost_grant_id", "provider_command": "provider_command_id"}
    for item, role in zip(write_set, expected_row["write_set"], strict=True):
        _require(item.get("stream_role") == role, "write_set role mismatch")
        _require(
            item.get("stream_id") == payload.get(role_id_fields[role]), "target/write_set/payload identity mismatch"
        )
    target_field = role_id_fields[expected_row["target_stream_role"]]
    _require(command.get("target_stream_id") == payload.get(target_field), "target/write_set/payload identity mismatch")
    if command_type == "IssueCostGrant":
        _require(write_set[0].get("expected_stream_version") == 0, "issue expected version must be zero")
    elif command_type == "AuthorizeProviderIssue":
        _require(
            write_set[0].get("expected_stream_version") == payload.get("cost_grant_revision"),
            "cost grant expected version mismatch",
        )
        _require(write_set[1].get("expected_stream_version") == 0, "provider command expected version must be zero")
        command_id = command.get("command_id")
        _require(isinstance(command_id, str) and "_" in command_id, "command identity invalid")
        _require(payload.get("reservation_id") == f"crs_{command_id.split('_', 1)[1]}", "reservation identity mismatch")
    elif command_type == "RecordProviderReceipt":
        _require(
            write_set[0].get("expected_stream_version") == payload.get("provider_command_revision"),
            "provider command expected version mismatch",
        )
        _require(
            write_set[1].get("expected_stream_version") == payload.get("cost_grant_revision"),
            "cost grant expected version mismatch",
        )
    for field in expected_row["authority_subject_fields"]:
        if not field.endswith("_id"):
            continue
        stem = field[:-3]
        revision_field = f"{stem}_revision"
        hash_field = f"{stem}_hash"
        subject = canonical_subjects.get(stem)
        _require(isinstance(subject, Mapping), f"authority subject missing:{stem}")
        _require(payload[field] == subject.get("id"), f"authority subject id mismatch:{stem}")
        if revision_field in payload or hash_field in payload:
            _require(
                revision_field in payload and hash_field in payload,
                f"authority subject identity incomplete:{stem}",
            )
            _require(
                payload[revision_field] == subject.get("revision"),
                f"authority subject revision mismatch:{stem}",
            )
            _require(payload[hash_field] == subject.get("content_hash"), f"authority subject hash mismatch:{stem}")
    _require(
        [event.get("event_type") for event in receipt_events] == expected_row["ordered_events"],
        "receipt event order mismatch",
    )
    for event, item in zip(receipt_events, write_set, strict=True):
        _require(event.get("stream_id") == item.get("stream_id"), "receipt event stream mismatch")
        _require(
            event.get("resulting_stream_version") == item.get("expected_stream_version") + 1,
            "receipt resulting version mismatch",
        )


def validate_reconciliation(payload: Mapping[str, Any]) -> None:
    input_tokens = payload.get("actual_input_tokens")
    output_tokens = payload.get("actual_output_tokens")
    total_tokens = payload.get("actual_total_tokens")
    reserved_input = payload.get("reserved_input_tokens")
    reserved_output = payload.get("reserved_output_tokens")
    reserved_total = payload.get("reserved_total_tokens")
    reserved = payload.get("reserved_cost_microunits")
    consumed = payload.get("consumed_cost_microunits")
    refund = payload.get("refund_cost_microunits")
    disposition = payload.get("refund_disposition")
    input_rate = payload.get("input_microunits_per_million_tokens")
    output_rate = payload.get("output_microunits_per_million_tokens")
    values = [
        input_tokens,
        output_tokens,
        total_tokens,
        reserved_input,
        reserved_output,
        reserved_total,
        reserved,
        consumed,
        refund,
        input_rate,
        output_rate,
    ]
    _require(
        all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in values),
        "reconciliation_actuals_invalid",
    )
    _require(total_tokens == input_tokens + output_tokens, "reconciliation_actuals_invalid")
    _require(input_tokens <= reserved_input and output_tokens <= reserved_output, "reconciliation_actuals_invalid")
    _require(total_tokens <= reserved_total, "reconciliation_actuals_invalid")
    mode = payload.get("rate_mode")
    zero_authority = payload.get("zero_cost_authority")
    if mode == "metered":
        _require(input_rate > 0 and output_rate > 0 and zero_authority is None, "reconciliation_actuals_invalid")
    elif mode == "zero_cost_authorized":
        _require(
            input_rate == 0 and output_rate == 0 and isinstance(zero_authority, Mapping),
            "reconciliation_actuals_invalid",
        )
        _require(
            set(zero_authority) == {"subject_id", "subject_revision", "subject_hash"}, "reconciliation_actuals_invalid"
        )
    else:
        raise T2ContractError("reconciliation_actuals_invalid")
    expected_consumed = (input_tokens * input_rate + 999_999) // 1_000_000 + (
        output_tokens * output_rate + 999_999
    ) // 1_000_000
    _require(consumed == expected_consumed and consumed <= reserved, "reconciliation_actuals_invalid")
    _require(refund == reserved - consumed, "reconciliation_actuals_invalid")
    expected_disposition = "fully_consumed" if refund == 0 else "refunded"
    _require(disposition == expected_disposition, "reconciliation_actuals_invalid")


def validate_cost_evidence_relations(*records: Mapping[str, Any]) -> None:
    _require(bool(records), "cost evidence missing")
    fields = ("currency", "rate_evidence_id", "rate_evidence_revision", "rate_evidence_hash")
    expected = tuple(records[0].get(field) for field in fields)
    _require(all(value is not None for value in expected), "cost evidence missing")
    for record in records[1:]:
        _require(tuple(record.get(field) for field in fields) == expected, "cost evidence identity mismatch")


def validate_provider_receipt_gates(receipt: Mapping[str, Any]) -> None:
    completeness = receipt.get("completeness")
    _require(isinstance(completeness, Mapping), "provider receipt completeness missing")
    gates = (
        "dispatch_gate_satisfied",
        "delivery_gate_satisfied",
        "reconciliation_gate_satisfied",
        "review_gate_satisfied",
    )
    if completeness.get("complete") is True:
        _require(all(completeness.get(gate) is True for gate in gates), "complete provider receipt gate mismatch")
        _require(completeness.get("diagnostic_only") is False, "complete provider receipt diagnostic mismatch")
        _require(receipt.get("delivery_proof", {}).get("disposition") == "proven", "complete delivery proof missing")
    else:
        _require(all(completeness.get(gate) is False for gate in gates), "incomplete provider receipt satisfied gate")
        _require(completeness.get("diagnostic_only") is True, "incomplete provider receipt not diagnostic-only")


def validate_concurrency_observation(observation: Mapping[str, Any]) -> None:
    _require(observation.get("command_count") == 2, "concurrency observation must contain two commands")
    _require(observation.get("accepted_count") == 1, "concurrency arbitration must have exactly one winner")
    _require(observation.get("rejected_count") == 1, "concurrency arbitration must have exactly one loser")
    _require(observation.get("reservation_count") == 1, "concurrency arbitration emitted duplicate reservations")
    _require(observation.get("invocation_count") == 1, "concurrency arbitration emitted duplicate invocations")
    _require(observation.get("loser_rejection_code") == "cost_grant_exhausted", "wrong concurrency rejection")
    reserved = observation.get("total_reserved_microunits")
    ceiling = observation.get("grant_ceiling_microunits")
    _require(isinstance(reserved, int) and isinstance(ceiling, int) and reserved <= ceiling, "cost grant over-reserved")


def validate_replay_observation(observation: Mapping[str, Any]) -> None:
    same_payload = observation.get("original_payload_hash") == observation.get("replay_payload_hash")
    if same_payload:
        _require(observation.get("status") == "duplicate", "accepted replay must return duplicate status")
        _require(observation.get("receipt_hash") == observation.get("original_receipt_hash"), "replay receipt mismatch")
        for field in (
            "new_grant_count",
            "new_reservation_count",
            "new_issue_count",
            "new_invocation_count",
            "new_provider_receipt_count",
            "new_reconciliation_count",
            "new_refund_count",
        ):
            _require(observation.get(field) == 0, f"replay side effect: {field}")
    else:
        _require(observation.get("status") == "conflict", "different replay payload must conflict")
        _require(observation.get("rejection_code") == "idempotency_conflict", "wrong idempotency conflict code")


def validate_pre_issue_rejection(observation: Mapping[str, Any]) -> None:
    seam = observation.get("seam")
    _require(seam in PRE_ISSUE_SENTINEL_SEAMS, "unknown pre-issue producer seam")
    _require(observation.get("rejection_code") == "secret_material_detected", "wrong sentinel rejection")
    _require(observation.get("reservation_count") == 0, "sentinel rejection reserved cost")
    _require(observation.get("invocation_count") == 0, "sentinel reached provider invocation")
    _require(observation.get("canonical_publication_count") == 0, "sentinel reached canonical publication")
