"""Deterministically materialize the WP6.1 proposed schema contract surface.

Usage is deliberately narrow: ``--check`` compares canonical in-memory bytes to
the checked-out candidate; ``--write`` writes only the 173 generated schemas and
the two proposal documents.  It never inspects runtime registrations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tests.research_system.contracts import wp6_1_materialization_validation as validation
from tests.research_system.contracts.wp6_1_schema_source import (
    ANNEX_BLOB,
    ANNEX_PATH,
    ANNEX_REVISION,
    ANNEX_SHA256,
    COMMAND_ROOT_NAMES,
    EVENT_ROOT_NAMES,
    FieldSpec,
    ObjectSpec,
    OperationSpec,
    SourceRow,
    canonical_yaml_bytes,
    command_root_spec,
    event_root_spec,
    git_blob_id,
    grouped_rows,
    schema_identity,
    sha256_value,
    resolve_operation_specs,
    source_citation,
    source_rows,
)


MATERIALIZATION_STATUS = "proposed_materialized"
REVIEW_STATUS = "pending_independent_review"
ACCEPTANCE_STATUS = "pending_d_g6_3_owner_acceptance"
SCHEMA_VERSION = "1.0.0"
CONTRACT_ROOT = ".research-system/contracts"


def _citation_text(spec: FieldSpec | ObjectSpec) -> str:
    return "; ".join(citation.text() for citation in spec.citations)


def _render_field(field: FieldSpec) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": [field.json_type, "null"] if field.nullable else field.json_type,
        "x-source-citation": _citation_text(field),
    }
    if field.const is not None:
        schema["const"] = field.const
    if field.enum:
        schema["enum"] = list(field.enum)
    if field.minimum is not None:
        schema["minimum"] = field.minimum
    if field.format is not None:
        schema["format"] = field.format
    if field.pattern is not None:
        schema["pattern"] = field.pattern
    if field.json_type == "string" and field.const is None:
        schema["minLength"] = 1
    if field.json_type == "array":
        if field.name == "declared_write_set":
            if field.object_spec is None:
                raise RuntimeError("ClaimDispatch write set lacks its closed member contract")
            members = []
            for stream_kind in ("dispatch", "task"):
                member = _render_object(field.object_spec)
                member["properties"]["stream_kind"]["const"] = stream_kind
                members.append(member)
            schema.update({"prefixItems": members, "minItems": 2, "maxItems": 2})
        elif field.object_spec is not None:
            schema["items"] = (
                {"$ref": f"#/$defs/{field.ref_name}"} if field.ref_name else _render_object(field.object_spec)
            )
        else:
            schema["items"] = {"type": field.item_type or "string", "minLength": 1}
            if field.item_pattern is not None:
                schema["items"]["pattern"] = field.item_pattern
            schema["uniqueItems"] = True
    elif field.json_type == "object" and field.object_spec is not None:
        if field.ref_name:
            schema.pop("type")
            schema["$ref"] = f"#/$defs/{field.ref_name}"
        else:
            schema.update(_render_object(field.object_spec))
    return schema


def _render_object(spec: ObjectSpec) -> dict[str, Any]:
    rendered = {
        "type": "object",
        "required": [field.name for field in spec.fields if field.required],
        "properties": {field.name: _render_field(field) for field in spec.fields},
        "additionalProperties": False,
        "x-source-citation": _citation_text(spec),
    }
    if spec.exclusive_required:
        rendered["oneOf"] = [{"required": list(names)} for names in spec.exclusive_required]
    return rendered


def _object_signature(spec: ObjectSpec) -> tuple[Any, ...]:
    return tuple(
        sorted(
            (
                field.name,
                field.json_type,
                field.const,
                field.nullable,
                field.item_type,
                field.ref_name,
                field.required,
                field.enum,
                field.minimum,
                field.format,
                field.pattern,
                field.item_pattern,
                _object_signature(field.object_spec) if field.object_spec else None,
            )
            for field in spec.fields
        )
    ) + (spec.exclusive_required,)


def _named_definitions(payloads: list[ObjectSpec]) -> dict[str, Any]:
    definitions: dict[str, Any] = {}
    signatures: dict[str, tuple[Any, ...]] = {}

    def visit(spec: ObjectSpec) -> None:
        for field in spec.fields:
            if field.object_spec is None:
                continue
            if field.ref_name:
                signature = _object_signature(field.object_spec)
                if field.ref_name in signatures and signatures[field.ref_name] != signature:
                    raise RuntimeError(f"conflicting local definition: {field.ref_name}")
                signatures[field.ref_name] = signature
                definitions.setdefault(field.ref_name, _render_object(field.object_spec))
            visit(field.object_spec)

    for payload in payloads:
        visit(payload)
    return definitions


def _payload_specs(
    rows: list[tuple[SourceRow, str, str]],
    *,
    kind: str,
    semantic_type: str,
    operations: Mapping[str, OperationSpec],
) -> list[ObjectSpec]:
    candidates: list[ObjectSpec] = []
    for row, _, _ in rows:
        operation = operations[row.key]
        if kind == "command":
            candidates.append(operation.command_payload)
            continue
        matches = [payload for event_type, payload in operation.event_payloads if event_type == semantic_type]
        if len(matches) != 1:
            raise RuntimeError(f"event payload binding mismatch for {row.key}/{semantic_type}")
        candidates.extend(matches)
    unique: dict[tuple[Any, ...], ObjectSpec] = {}
    for candidate in candidates:
        unique.setdefault(_object_signature(candidate), candidate)
    if not unique:
        raise RuntimeError(f"empty {kind} payload union for {semantic_type}")
    return list(unique.values())


def _generated_schema(
    rows: list[tuple[SourceRow, str, str]],
    *,
    kind: str,
    identity: Mapping[str, str],
    operations: Mapping[str, OperationSpec],
) -> dict[str, Any]:
    semantic_type = identity[f"{kind}_schema_id"].rsplit("/", 1)[1]
    citation = "; ".join(source_citation(row) for row, _, _ in rows)
    root = command_root_spec() if kind == "command" else event_root_spec()
    root_names = COMMAND_ROOT_NAMES if kind == "command" else EVENT_ROOT_NAMES
    type_field = "command_type" if kind == "command" else "event_type"
    properties = {field.name: _render_field(field) for field in root.fields}
    properties["schema_id"] = {"const": identity[f"{kind}_schema_id"], "x-source-citation": citation}
    properties["schema_version"] = {"const": SCHEMA_VERSION, "x-source-citation": citation}
    properties[type_field] = {"const": semantic_type, "x-source-citation": citation}
    properties["payload"] = {"$ref": "#/$defs/payload"}
    payloads = _payload_specs(rows, kind=kind, semantic_type=semantic_type, operations=operations)
    definitions = {"payload": {"oneOf": [_render_object(payload) for payload in payloads]}}
    definitions.update(_named_definitions(payloads))
    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": identity[f"{kind}_schema_id"],
        "title": f"WP6.1 proposed {kind} schema: {semantic_type}",
        "description": "Closed, proposed-only materialization from the reviewed WP6.1 owner source.",
        "type": "object",
        "required": list(root_names),
        "properties": properties,
        "additionalProperties": False,
        "$defs": definitions,
        "x-source-citation": citation,
        "x-lifecycle": MATERIALIZATION_STATUS,
    }
    return schema


def _preflight_model(rows: list[SourceRow], operations: Mapping[str, OperationSpec]) -> None:
    banned = {"command_key", "event_key", "subject_reference", "evidence_reference", "source_model_citation"}
    if len(operations) != 104 or set(operations) != {row.key for row in rows}:
        raise RuntimeError("WP6.1 semantic model is not exactly the approved 104 rows")
    for row in rows:
        operation = operations[row.key]
        if len(operation.event_payloads) != len(row.events):
            raise RuntimeError(f"WP6.1 event fact count mismatch for {row.key}")
        command_names = {field.name for field in operation.command_payload.fields}
        if command_names & banned or len(command_names) < 2:
            raise RuntimeError(f"WP6.1 invalid command payload for {row.key}")
        if any(not field.citations for field in operation.command_payload.fields):
            raise RuntimeError(f"WP6.1 uncited command field for {row.key}")
        _, authority_source = validation._authority_binding(row.key, row.command_type)
        if authority_source.startswith("payload.") and authority_source.split(".", 1)[1] not in command_names:
            raise RuntimeError(f"WP6.1 authority subject is absent from {row.key}")
        for event_type, payload in operation.event_payloads:
            names = {field.name for field in payload.fields}
            if names & banned or len(names) < 2 or any(not field.citations for field in payload.fields):
                raise RuntimeError(f"WP6.1 invalid immutable event facts for {row.key}/{event_type}")


def _identity(identity: Mapping[str, str], *, kind: str, schema_bytes: bytes) -> dict[str, str]:
    result = dict(identity)
    hash_field = f"{kind}_schema_sha256"
    contract_hash_field = f"{kind}_identity_contract_sha256"
    result[hash_field] = hashlib.sha256(schema_bytes).hexdigest()
    result["materialization_status"] = MATERIALIZATION_STATUS
    result["review_status"] = REVIEW_STATUS
    result["acceptance_status"] = ACCEPTANCE_STATUS
    result[contract_hash_field] = sha256_value(result)
    return result


def _source_annex() -> dict[str, Any]:
    return {
        "repository_path": ANNEX_PATH,
        "reviewed_revision": ANNEX_REVISION,
        "git_blob_id": ANNEX_BLOB,
        "canonical_utf8_lf_sha256": ANNEX_SHA256,
        "normalized_row_count": 104,
        "expanded_edge_count": 182,
    }


def _governance() -> dict[str, str]:
    return {
        "producer": "pipe/ars-wp6-1-task-lifecycle owning Worker",
        "intended_independent_reviewer": "independent reviewer who did not implement the schemas",
        "intended_acceptor": "Stephen under D-G6-3",
        "review_status": REVIEW_STATUS,
        "acceptance_status": ACCEPTANCE_STATUS,
    }


def _identity_rows(repo_root: Path, rows: list[SourceRow], schema_bytes: Mapping[str, bytes]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in rows:
        command_base = schema_identity(row.command_token, row.command_type, "command")
        command = _identity(
            command_base,
            kind="command",
            schema_bytes=schema_bytes[command_base["command_schema_path"]],
        )
        events: list[dict[str, str]] = []
        for event_type, event_token in row.events:
            event_base = schema_identity(event_token, event_type, "event")
            events.append(
                _identity(event_base, kind="event", schema_bytes=schema_bytes[event_base["event_schema_path"]])
            )
        record: dict[str, Any] = {
            "key": row.key,
            "command_type": row.command_type,
            "command_schema_identity": command,
            "event_schema_bindings": events,
        }
        record["row_identity_contract_sha256"] = sha256_value(record)
        result.append(record)
    return result


def _catalogue_rows(rows: list[SourceRow], identity_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identity_by_key = {row["key"]: row for row in identity_rows}
    result: list[dict[str, Any]] = []
    for source in rows:
        _, projections, selector = validation._reducer_projection_parts(source.reducer_projection)
        reducers, _, _ = validation._reducer_projection_parts(source.reducer_projection)
        positive_match = re.search(r"(pos_[a-z0-9_]+)", source.receipt_tests)
        profile_match = re.search(r"(N0|NE|NA|NI|NC|NS)(?:`)?\s*$", source.receipt_tests)
        if positive_match is None or profile_match is None:
            raise RuntimeError(f"missing test binding for {source.key}")
        identity = identity_by_key[source.key]
        record: dict[str, Any] = {
            "source_table": source.source_table,
            "key": source.key,
            "owner_transition_discriminator": source.owner_transition,
            "transition": validation._transition(source.owner_transition, source.source_table),
            "command_type": source.command_type,
            "command_schema_identity": identity["command_schema_identity"],
            "ordered_events": [event_type for event_type, _ in source.events],
            "event_schema_bindings": identity["event_schema_bindings"],
            "reducers": reducers,
            "projections": projections,
            "projection_selector": selector,
            "authority": validation._authority(source.authority, source.key, source.command_type),
            "receipt": "R",
            "positive_test": positive_match.group(1),
            "negative_profile": profile_match.group(1),
            "expanded_negative_tests": [
                f"neg_{source.key.replace('.', '_')}_{case}"
                for case in validation._NEGATIVE_PROFILES[profile_match.group(1)]
            ],
            "atomic_binding": validation._atomic_claim_binding() if source.command_type == "ClaimDispatch" else None,
            "annex_binding": {
                "owner_transition_discriminator": source.owner_transition,
                "command_event_identity": source.command_event_identity,
                "reducer_projections_selector": source.reducer_projection,
                "authority_precondition": source.authority,
                "receipt_positive_negatives": source.receipt_tests,
            },
        }
        record["complete_record_sha256"] = sha256_value(record)
        result.append(record)
    return result


def generate_artifacts(repo_root: Path) -> dict[str, bytes]:
    """Build the complete acyclic output graph without modifying the checkout."""
    rows = source_rows(repo_root)
    operations = resolve_operation_specs(repo_root, rows)
    _preflight_model(rows, operations)
    command_groups = grouped_rows(rows, kind="command")
    event_groups = grouped_rows(rows, kind="event")
    if len(command_groups) != 87 or len(event_groups) != 86:
        raise RuntimeError("WP6.1 exact 87-command/86-event materialization counts differ")
    artifacts: dict[str, bytes] = {}
    for kind, groups in (("command", command_groups), ("event", event_groups)):
        for path, group in sorted(groups.items()):
            _, token, semantic_type = group[0]
            artifacts[path] = (
                json_bytes := json.dumps(
                    _generated_schema(
                        group,
                        kind=kind,
                        identity=schema_identity(token, semantic_type, kind),
                        operations=operations,
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                ).encode("utf-8")
                + b"\n"
            )
            if b"\r" in json_bytes or json_bytes.startswith(b"\xef\xbb\xbf"):
                raise RuntimeError(f"non-canonical generated schema bytes: {path}")
    identity_rows = _identity_rows(repo_root, rows, artifacts)
    identities: dict[str, Any] = {
        "schema_id": "ars://contracts/wp6-1-schema-identities",
        "schema_version": SCHEMA_VERSION,
        "manifest_id": "wp6-1-schema-identities",
        "source_annex": _source_annex(),
        "governance": _governance(),
        "normalized_row_count": 104,
        "row_identity_multiset_sha256": sha256_value(sorted(identity_rows, key=lambda row: row["key"])),
        "rows": identity_rows,
    }
    identity_bytes = canonical_yaml_bytes(identities)
    identity_path = f"{CONTRACT_ROOT}/wp6-1-schema-identities.yaml"
    artifacts[identity_path] = identity_bytes
    catalogue_rows = _catalogue_rows(rows, identity_rows)
    catalogue: dict[str, Any] = {
        "schema_id": "ars://contracts/wp6-1-owner-source-catalogue",
        "schema_version": SCHEMA_VERSION,
        "catalogue_id": "wp6-1-owner-source-catalogue",
        "source_annex": _source_annex(),
        "schema_identity_manifest": {
            "repository_path": identity_path,
            "schema_id": identities["schema_id"],
            "schema_version": SCHEMA_VERSION,
            "git_blob_id": git_blob_id(repo_root, identity_bytes),
            "canonical_utf8_lf_sha256": hashlib.sha256(identity_bytes).hexdigest(),
            "review_status": REVIEW_STATUS,
            "acceptance_status": ACCEPTANCE_STATUS,
        },
        "governance": _governance(),
        "normalized_row_count": 104,
        "expanded_edge_count": 182,
        "state_classes": validation._STATE_CLASSES,
        "negative_profiles": validation._NEGATIVE_PROFILES,
        "correction_selector": {
            "selector_id": "projection_selector/corrected_record_kind/v1",
            "governance_index": "governance_correction_index",
            "mappings": validation._CORRECTION_MAPPINGS,
        },
        "decision_rule_evaluation_non_compensation": validation._NON_COMPENSATION,
        "catalogue_multiset_sha256": sha256_value(sorted(catalogue_rows, key=lambda row: row["key"])),
        "rows": catalogue_rows,
    }
    artifacts[f"{CONTRACT_ROOT}/wp6-1-owner-source-catalogue.yaml"] = canonical_yaml_bytes(catalogue)
    if len(artifacts) != 175:
        raise RuntimeError("WP6.1 materializer did not produce exactly 173 schemas plus two contracts")
    return artifacts


def materialize(repo_root: Path, *, write: bool) -> list[str]:
    artifacts = generate_artifacts(repo_root)
    mismatches: list[str] = []
    for relative_path, expected in artifacts.items():
        path = repo_root / relative_path
        actual = path.read_bytes() if path.exists() else None
        if actual != expected:
            mismatches.append(relative_path)
            if write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(expected)
    if mismatches and not write:
        raise RuntimeError("generated WP6.1 artifacts differ: " + ", ".join(mismatches))
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("provide exactly one of --write or --check")
    mismatches = materialize(args.repo_root.resolve(), write=args.write)
    print(
        f"wp6.1 materializer {'wrote' if args.write else 'verified'} {175 - len(mismatches) if not args.write else len(mismatches)} artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
