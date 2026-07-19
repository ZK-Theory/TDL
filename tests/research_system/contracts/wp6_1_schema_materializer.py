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
    SourceRow,
    canonical_yaml_bytes,
    git_blob_id,
    grouped_rows,
    schema_identity,
    sha256_value,
    source_citation,
    source_rows,
)


MATERIALIZATION_STATUS = "proposed_materialized"
REVIEW_STATUS = "pending_independent_review"
ACCEPTANCE_STATUS = "pending_d_g6_3_owner_acceptance"
SCHEMA_VERSION = "1.0.0"
CONTRACT_ROOT = ".research-system/contracts"


def _citation_property(schema: dict[str, Any], citation: str) -> dict[str, Any]:
    schema["x-source-citation"] = citation
    return schema


def _variant(row: SourceRow, *, kind: str, semantic_type: str) -> dict[str, Any]:
    citation = source_citation(row)
    key_name = "command_key" if kind == "command" else "event_key"
    fields: dict[str, Any] = {
        key_name: _citation_property({"const": row.key}, citation),
        "subject_reference": _citation_property({"type": "string", "minLength": 1}, citation),
        "evidence_reference": _citation_property({"type": "string", "minLength": 1}, citation),
        "source_model_citation": _citation_property({"const": citation}, citation),
    }
    if kind == "command":
        fields["command_type"] = _citation_property({"const": semantic_type}, citation)
    else:
        fields["source_command_type"] = _citation_property({"const": row.command_type}, citation)
        fields["event_type"] = _citation_property({"const": semantic_type}, citation)
    return {
        "type": "object",
        "required": list(fields),
        "properties": fields,
        "additionalProperties": False,
    }


def _generated_schema(
    rows: list[tuple[SourceRow, str, str]], *, kind: str, identity: Mapping[str, str]
) -> dict[str, Any]:
    semantic_type = identity[f"{kind}_schema_id"].rsplit("/", 1)[1]
    citation = "; ".join(source_citation(row) for row, _, _ in rows)
    envelope_fields = {
        "project_id": _citation_property({"type": "string", "minLength": 1}, citation),
        "stream_id": _citation_property({"type": "string", "minLength": 1}, citation),
        "authority_grant_id": _citation_property({"type": "string", "minLength": 1}, citation),
        "idempotency_key": _citation_property({"type": "string", "minLength": 1}, citation),
    }
    type_field = "command_type" if kind == "command" else "event_type"
    schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": identity[f"{kind}_schema_id"],
        "title": f"WP6.1 proposed {kind} schema: {semantic_type}",
        "description": "Closed, proposed-only materialization from the reviewed WP6.1 owner source.",
        "type": "object",
        "required": ["schema_id", "schema_version", type_field, "envelope", "payload"],
        "properties": {
            "schema_id": {"const": identity[f"{kind}_schema_id"]},
            "schema_version": {"const": SCHEMA_VERSION},
            type_field: {"const": semantic_type},
            "envelope": {"$ref": "#/$defs/envelope"},
            "payload": {"$ref": "#/$defs/payload"},
        },
        "additionalProperties": False,
        "$defs": {
            "envelope": {
                "type": "object",
                "required": list(envelope_fields),
                "properties": envelope_fields,
                "additionalProperties": False,
            },
            "payload": {"oneOf": [_variant(row, kind=kind, semantic_type=type_) for row, _, type_ in rows]},
        },
        "x-source-citation": citation,
        "x-lifecycle": MATERIALIZATION_STATUS,
    }
    return schema


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
                    _generated_schema(group, kind=kind, identity=schema_identity(token, semantic_type, kind)),
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
