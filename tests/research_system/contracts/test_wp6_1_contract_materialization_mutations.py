from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import pytest
import yaml

from research_system.errors import SchemaError
from tests.research_system.contracts import wp6_1_materialization_validation as validation
from tests.research_system.contracts.wp6_1_materialization_validation import (
    validate_wp6_1_contract_materialization,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPO_ROOT / ".research-system" / "schemas"
CONTRACT_ROOT = REPO_ROOT / ".research-system" / "contracts"
CATALOGUE_PATH = CONTRACT_ROOT / "wp6-1-owner-source-catalogue.yaml"
IDENTITIES_PATH = CONTRACT_ROOT / "wp6-1-schema-identities.yaml"

Document = dict[str, Any]
PairMutation = Callable[[Document, Document], None]


def _load_documents() -> tuple[Document, Document]:
    return (
        yaml.safe_load(CATALOGUE_PATH.read_bytes()),
        yaml.safe_load(IDENTITIES_PATH.read_bytes()),
    )


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _git_blob_id(data: bytes) -> str:
    return (
        subprocess.run(
            ["git", "hash-object", "--no-filters", "--stdin"],
            cwd=REPO_ROOT,
            input=data,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        .stdout.decode("ascii")
        .strip()
    )


def _yaml_bytes(document: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(
        document,
        allow_unicode=True,
        sort_keys=False,
        width=4096,
    ).encode("utf-8")


def _repair_hashes(document: Document, row_hash_field: str, multiset_field: str) -> None:
    for row in document["rows"]:
        row_without_hash = {key: value for key, value in row.items() if key != row_hash_field}
        row[row_hash_field] = _canonical_hash(row_without_hash)
    document[multiset_field] = _canonical_hash(sorted(document["rows"], key=lambda row: row["key"]))


def _write_candidate_pair(
    tmp_path: Path,
    catalogue: Document,
    identities: Document,
) -> tuple[Path, Path]:
    identity_bytes = _yaml_bytes(identities)
    catalogue["schema_identity_manifest"]["git_blob_id"] = _git_blob_id(identity_bytes)
    catalogue["schema_identity_manifest"]["canonical_utf8_lf_sha256"] = hashlib.sha256(identity_bytes).hexdigest()
    catalogue_bytes = _yaml_bytes(catalogue)

    catalogue_path = tmp_path / CATALOGUE_PATH.name
    identities_path = tmp_path / IDENTITIES_PATH.name
    catalogue_path.write_bytes(catalogue_bytes)
    identities_path.write_bytes(identity_bytes)
    return catalogue_path, identities_path


def _validate_candidate(
    tmp_path: Path,
    catalogue: Document,
    identities: Document,
    *,
    observed_runtime_rows: list[Mapping[str, Any]] | None = None,
) -> None:
    catalogue_path, identities_path = _write_candidate_pair(tmp_path, catalogue, identities)
    validate_wp6_1_contract_materialization(
        catalogue_path=catalogue_path,
        identities_path=identities_path,
        schema_root=SCHEMA_ROOT,
        observed_runtime_rows=observed_runtime_rows,
    )


def _row(document: Document, key: str) -> Document:
    return next(row for row in document["rows"] if row["key"] == key)


def _missing_row(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"].pop()


def _extra_row(catalogue: Document, _identities: Document) -> None:
    extra = copy.deepcopy(catalogue["rows"][-1])
    extra["key"] = "backup.extra"
    catalogue["rows"].append(extra)


def _duplicate_row(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][1] = copy.deepcopy(catalogue["rows"][0])


def _command_alias(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][1]["command_type"] = catalogue["rows"][0]["command_type"]


def _positive_test_alias(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][1]["positive_test"] = catalogue["rows"][0]["positive_test"]


def _expanded_negative_alias(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][1]["expanded_negative_tests"][0] = catalogue["rows"][0]["expanded_negative_tests"][0]


def _swap_rows(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][0], catalogue["rows"][1] = catalogue["rows"][1], catalogue["rows"][0]


def _incomplete_state_class(catalogue: Document, _identities: Document) -> None:
    catalogue["state_classes"]["task_nonterminal"].pop()


def _incomplete_actor_class(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][0]["authority"]["allowed_actor_classes"].pop()


def _effect_loss(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][0]["projections"].remove("governance")


def _row_hash_mutation(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][0]["complete_record_sha256"] = "0" * 64


def _identity_hash_mutation(_catalogue: Document, identities: Document) -> None:
    identities["rows"][0]["row_identity_contract_sha256"] = "0" * 64


def _unexpected_top_level(catalogue: Document, _identities: Document) -> None:
    catalogue["unexpected"] = True


def _unexpected_nested_field(catalogue: Document, _identities: Document) -> None:
    catalogue["rows"][0]["authority"]["unexpected"] = True


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(_missing_row, id="missing-record"),
        pytest.param(_extra_row, id="extra-record"),
        pytest.param(_duplicate_row, id="duplicate-record"),
        pytest.param(_command_alias, id="command-alias"),
        pytest.param(_positive_test_alias, id="positive-test-alias"),
        pytest.param(_expanded_negative_alias, id="expanded-negative-alias"),
        pytest.param(_swap_rows, id="row-swap"),
        pytest.param(_incomplete_state_class, id="state-class-incomplete"),
        pytest.param(_incomplete_actor_class, id="actor-class-incomplete"),
        pytest.param(_effect_loss, id="effect-loss"),
        pytest.param(_row_hash_mutation, id="complete-record-hash"),
        pytest.param(_identity_hash_mutation, id="identity-row-hash"),
        pytest.param(_unexpected_top_level, id="top-additional-property"),
        pytest.param(_unexpected_nested_field, id="nested-additional-property"),
    ],
)
def test_wp6_1_materialization_rejects_complete_record_mutations(
    tmp_path: Path,
    mutation: PairMutation,
) -> None:
    catalogue, identities = _load_documents()
    mutation(catalogue, identities)

    with pytest.raises(SchemaError):
        _validate_candidate(tmp_path, catalogue, identities)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        pytest.param(
            ("stored_relation", "dispatch_task_id_source"),
            "payload.task_id",
            id="foreign-current-task",
        ),
        pytest.param(
            ("stored_relation", "dispatch_task_revision_source"),
            "payload.task_revision",
            id="stale-dispatch-task-relation",
        ),
        pytest.param(
            ("lease_relation", "lease_task_id_source"),
            "payload.task_id",
            id="wrong-lease-task-subject",
        ),
        pytest.param(
            ("declared_write_set", "1", "expected_version_source"),
            "payload.expected_dispatch_stream_version",
            id="wrong-write-set-version",
        ),
    ],
)
def test_wp6_1_claim_dispatch_rejects_relational_mutations(
    tmp_path: Path,
    path: tuple[str, ...],
    value: str,
) -> None:
    catalogue, identities = _load_documents()
    for key in ("task.claim_start", "dispatch.claim"):
        atomic_binding = _row(catalogue, key)["atomic_binding"]
        current: Any = atomic_binding
        for token in path[:-1]:
            current = current[int(token)] if token.isdigit() else current[token]
        current[path[-1]] = value
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    with pytest.raises(SchemaError):
        _validate_candidate(tmp_path, catalogue, identities)


def test_wp6_1_claim_dispatch_rejects_missing_race_mutation(
    tmp_path: Path,
) -> None:
    catalogue, identities = _load_documents()
    for key in ("task.claim_start", "dispatch.claim"):
        _row(catalogue, key)["atomic_binding"]["required_mutations"].remove("concurrent_task_stream_race")
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    with pytest.raises(SchemaError):
        _validate_candidate(tmp_path, catalogue, identities)


def test_wp6_1_claim_dispatch_materializes_two_identical_relational_facets() -> None:
    catalogue, _ = _load_documents()
    task_facet = _row(catalogue, "task.claim_start")["atomic_binding"]
    dispatch_facet = _row(catalogue, "dispatch.claim")["atomic_binding"]

    assert task_facet == dispatch_facet
    assert task_facet["cardinality"] == 2
    assert task_facet["facets"] == ["task.claim_start", "dispatch.claim"]
    assert {member["stream_kind"] for member in task_facet["declared_write_set"]} == {
        "dispatch",
        "task",
    }


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(
            lambda catalogue: catalogue["decision_rule_evaluation_non_compensation"].__setitem__(
                "rule_evaluation_subject_kind", "decision"
            ),
            id="rule-evaluation-compensated-by-decision",
        ),
        pytest.param(
            lambda catalogue: next(
                mapping
                for mapping in catalogue["correction_selector"]["mappings"]
                if mapping["corrected_record_kind"] == "decision"
            ).__setitem__("owner_projection", "rule_evaluation"),
            id="decision-correction-selector-collapsed",
        ),
        pytest.param(
            lambda catalogue: _row(catalogue, "rule.evaluate")["authority"].__setitem__(
                "authority_subject_kind", "decision"
            ),
            id="rule-evaluation-owner-collapsed",
        ),
        pytest.param(
            lambda catalogue: _row(catalogue, "decision.propose")["authority"].__setitem__(
                "authority_subject_kind", "rule_evaluation"
            ),
            id="decision-owner-collapsed",
        ),
    ],
)
def test_wp6_1_decision_and_rule_evaluation_reject_non_compensation_mutations(
    tmp_path: Path,
    mutation: Callable[[Document], None],
) -> None:
    catalogue, identities = _load_documents()
    mutation(catalogue)
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    with pytest.raises(SchemaError):
        _validate_candidate(tmp_path, catalogue, identities)


def _identity_contract_hash(identity: Document) -> str:
    return _canonical_hash({key: value for key, value in identity.items() if key != "command_identity_contract_sha256"})


def _runtime_observations(catalogue: Document) -> list[Mapping[str, Any]]:
    return [
        {
            "key": row["key"],
            "command_type": row["command_type"],
            "command_schema_id": row["command_schema_identity"]["command_schema_id"],
            "ordered_events": row["ordered_events"],
            "event_schema_ids": [binding["event_schema_id"] for binding in row["event_schema_bindings"]],
        }
        for row in catalogue["rows"]
    ]


def test_wp6_1_rejects_coordinated_expected_runtime_substitution(
    tmp_path: Path,
) -> None:
    catalogue, identities = _load_documents()
    catalogue_row = _row(catalogue, "scope.create")
    identity_row = _row(identities, "scope.create")
    for row in (catalogue_row, identity_row):
        row["command_type"] = "CreateScopeAlias"
        row["command_schema_identity"]["command_schema_id"] = "ars://core/command/CreateScopeAlias"
        row["command_schema_identity"]["command_identity_contract_sha256"] = _identity_contract_hash(
            row["command_schema_identity"]
        )
    _repair_hashes(identities, "row_identity_contract_sha256", "row_identity_multiset_sha256")
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")
    observed_runtime_rows = _runtime_observations(catalogue)

    with pytest.raises(SchemaError):
        _validate_candidate(
            tmp_path,
            catalogue,
            identities,
            observed_runtime_rows=observed_runtime_rows,
        )


def _walk_schema_objects(node: Any) -> list[Document]:
    objects: list[Document] = []
    if isinstance(node, dict):
        if node.get("type") == "object":
            objects.append(node)
        for value in node.values():
            objects.extend(_walk_schema_objects(value))
    elif isinstance(node, list):
        for value in node:
            objects.extend(_walk_schema_objects(value))
    return objects


@pytest.mark.parametrize(
    "schema_name",
    [
        "wp6-1-owner-source-catalogue.schema.json",
        "wp6-1-schema-identities.schema.json",
    ],
)
def test_wp6_1_materialization_schema_is_strict_at_every_object(
    schema_name: str,
) -> None:
    schema = json.loads((SCHEMA_ROOT / "contracts" / schema_name).read_text(encoding="utf-8"))
    objects = _walk_schema_objects(schema)

    assert objects
    assert all(node.get("additionalProperties") is False for node in objects)


def test_wp6_1_schema_identities_are_materialized_proposals_with_exact_raw_bytes() -> None:
    catalogue, identities = _load_documents()

    assert len(catalogue["rows"]) == len(identities["rows"]) == 104
    for row in identities["rows"]:
        schema_identities = [row["command_schema_identity"], *row["event_schema_bindings"]]
        for identity in schema_identities:
            prefix = "command" if "command_schema_id" in identity else "event"
            schema_path = REPO_ROOT / identity[f"{prefix}_schema_path"]
            schema_bytes = schema_path.read_bytes()
            schema = json.loads(schema_bytes.decode("utf-8"))

            assert identity[f"{prefix}_schema_version"] == "1.0.0"
            assert re.fullmatch(r"[0-9a-f]{64}", identity[f"{prefix}_schema_sha256"])
            assert identity[f"{prefix}_schema_sha256"] == hashlib.sha256(schema_bytes).hexdigest()
            assert identity["materialization_status"] == "proposed_materialized"
            assert identity["review_status"] == "pending_independent_review"
            assert identity["acceptance_status"] == "pending_d_g6_3_owner_acceptance"
            assert not {"accepted", "owner_accepted", "owner_decision", "acceptance_record"} & set(identity)
            assert schema_path.exists()
            assert not schema_bytes.startswith(b"\xef\xbb\xbf")
            assert b"\r" not in schema_bytes
            assert schema["$id"] == identity[f"{prefix}_schema_id"]
            assert schema["properties"]["schema_version"]["const"] == identity[f"{prefix}_schema_version"]
            expected_type = row["command_type"] if prefix == "command" else identity["event_type"]
            assert schema["properties"][f"{prefix}_type"]["const"] == expected_type
            hash_field = f"{prefix}_identity_contract_sha256"
            assert identity[hash_field] == _canonical_hash(
                {name: value for name, value in identity.items() if name != hash_field}
            )


@pytest.mark.parametrize("key", [row["key"] for row in _load_documents()[0]["rows"]])
def test_wp6_1_rejects_every_authority_subject_row_mutation(tmp_path: Path, key: str) -> None:
    """Each approved row retains its own authority subject; no family-level shortcut."""
    catalogue, identities = _load_documents()
    authority = _row(catalogue, key)["authority"]
    authority["authority_subject_kind"] = (
        "project_store" if authority["authority_subject_kind"] != "project_store" else "task"
    )
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    with pytest.raises(SchemaError, match=rf"authority mismatch: {key}"):
        _validate_candidate(tmp_path, catalogue, identities)


@pytest.mark.parametrize(
    ("target", "field", "replacement"),
    [
        pytest.param(
            "command_schema_identity", "command_schema_id", "ars://core/command/RetainedTypeAlias", id="command-id"
        ),
        pytest.param("command_schema_identity", "command_schema_version", "9.9.9", id="command-version"),
        pytest.param("command_schema_identity", "command_schema_sha256", "a" * 64, id="command-content-hash"),
        pytest.param("event_schema_bindings", "event_schema_id", "ars://core/event/RetainedEventAlias", id="event-id"),
        pytest.param("event_schema_bindings", "event_schema_version", "9.9.9", id="event-version"),
        pytest.param("event_schema_bindings", "event_schema_sha256", "b" * 64, id="event-content-hash"),
    ],
)
def test_wp6_1_rejects_retained_type_identity_component_mutations(
    tmp_path: Path, target: str, field: str, replacement: str
) -> None:
    catalogue, identities = _load_documents()
    for document in (catalogue, identities):
        row = _row(document, "scope.create")
        identity = row[target][0] if target == "event_schema_bindings" else row[target]
        identity[field] = replacement
        hash_field = (
            "event_identity_contract_sha256"
            if target == "event_schema_bindings"
            else "command_identity_contract_sha256"
        )
        identity[hash_field] = _canonical_hash({name: value for name, value in identity.items() if name != hash_field})
    _repair_hashes(identities, "row_identity_contract_sha256", "row_identity_multiset_sha256")
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    with pytest.raises(
        SchemaError,
        match=(
            r"schema identity mismatch|event identity mismatch: scope\.create|"
            r"command_schema_version: '1\.0\.0' was expected|"
            r"event_schema_version: '1\.0\.0' was expected"
        ),
    ):
        _validate_candidate(tmp_path, catalogue, identities)


@pytest.mark.parametrize(
    ("field_path", "replacement"),
    [
        pytest.param(("reducers",), [], id="reducer-omission"),
        pytest.param(("projections",), ["governance"], id="wrong-projection"),
        pytest.param(("projection_selector",), "projection_selector/foreign/v1", id="wrong-selector"),
        pytest.param(("transition", "discriminator", "value"), "handoff", id="message-discriminator"),
        pytest.param(("transition", "from_state"), "blocked", id="exact-edge"),
        pytest.param(("ordered_events",), ["TaskClaimStarted", "DispatchClaimed"], id="event-reorder"),
        pytest.param(("ordered_events",), [], id="event-omission"),
    ],
)
def test_wp6_1_rejects_row_effect_and_order_mutations(
    tmp_path: Path, field_path: tuple[str, ...], replacement: Any
) -> None:
    catalogue, identities = _load_documents()
    row = _row(catalogue, "message.publish_assignment" if field_path[0] == "transition" else "task.claim_start")
    current: Any = row
    for field in field_path[:-1]:
        current = current[field]
    current[field_path[-1]] = replacement
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    expected = (
        r"ordered event mismatch|rows\.11\.ordered_events: \[\] should be non-empty"
        if field_path[0] == "ordered_events"
        else (
            r"reducer effect mismatch|rows\.11\.reducers: \[\] should be non-empty"
            if field_path[0] == "reducers"
            else "projection"
            if field_path[0] == "projections"
            else "mismatch"
        )
    )
    with pytest.raises(SchemaError, match=expected):
        _validate_candidate(tmp_path, catalogue, identities)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        pytest.param(("group",), "wrong_group", id="group"),
        pytest.param(("cardinality",), 1, id="cardinality"),
        pytest.param(("facets",), ["task.claim_start"], id="missing-dispatch-facet"),
        pytest.param(("facets",), ["dispatch.claim"], id="missing-task-facet"),
        pytest.param(("dispatch_authority_subject_source",), "payload.task_id", id="authority-subject"),
        pytest.param(("stored_relation", "dispatch_task_id_source"), "payload.task_id", id="foreign-current-task"),
        pytest.param(
            ("stored_relation", "dispatch_task_revision_source"), "payload.task_revision", id="stale-dispatch-relation"
        ),
        pytest.param(
            ("stored_relation", "payload_task_id_source"), "accepted_dispatch.task_id", id="payload-task-source"
        ),
        pytest.param(
            ("stored_relation", "payload_task_revision_source"),
            "accepted_dispatch.task_revision",
            id="payload-revision-source",
        ),
        pytest.param(("lease_relation", "lease_task_id_source"), "payload.task_id", id="wrong-lease-task"),
        pytest.param(
            ("lease_relation", "lease_task_revision_source"), "payload.task_revision", id="wrong-lease-revision"
        ),
        pytest.param(("lease_relation", "lease_dispatch_id_source"), "payload.dispatch_id", id="wrong-lease-dispatch"),
        pytest.param(("declared_write_set", "0", "stream_kind"), "task", id="write-set-kind"),
        pytest.param(("declared_write_set", "0", "stream_id_source"), "payload.task_id", id="write-set-id"),
        pytest.param(
            ("declared_write_set", "0", "expected_version_source"),
            "payload.expected_task_stream_version",
            id="dispatch-version",
        ),
        pytest.param(
            ("declared_write_set", "1", "expected_version_source"),
            "payload.expected_dispatch_stream_version",
            id="task-version",
        ),
        pytest.param(("ordered_events",), ["TaskClaimStarted", "DispatchClaimed"], id="batch-order-race"),
        pytest.param(("required_mutations",), [], id="declared-race-catalogue"),
        pytest.param(("unchanged_surfaces",), ["event_tail"], id="unchanged-surface"),
    ],
)
def test_wp6_1_claim_dispatch_rejects_all_approved_relation_and_race_cases(
    tmp_path: Path, path: tuple[str, ...], replacement: Any
) -> None:
    catalogue, identities = _load_documents()
    for key in ("task.claim_start", "dispatch.claim"):
        current: Any = _row(catalogue, key)["atomic_binding"]
        for token in path[:-1]:
            current = current[int(token)] if token.isdigit() else current[token]
        current[path[-1]] = replacement
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    with pytest.raises(
        SchemaError,
        match=r"atomic claim binding mismatch|rows\.(11|25)\.atomic_binding:",
    ):
        _validate_candidate(tmp_path, catalogue, identities)


@pytest.mark.parametrize(
    "mutation",
    [
        pytest.param(
            lambda selector: selector.__setitem__("selector_id", "projection_selector/foreign/v1"),
            id="unknown-selector",
        ),
        pytest.param(lambda selector: selector.__setitem__("governance_index", "task"), id="missing-governance-index"),
        pytest.param(
            lambda selector: selector["mappings"].__setitem__(
                0, {"corrected_record_kind": "task", "owner_projection": "scope"}
            ),
            id="swapped-owner",
        ),
        pytest.param(lambda selector: selector["mappings"].pop(), id="zero-owner"),
        pytest.param(
            lambda selector: selector["mappings"].append(copy.deepcopy(selector["mappings"][0])), id="multiple-owner"
        ),
    ],
)
def test_wp6_1_correction_selector_rejects_cardinality_and_owner_mutations(
    tmp_path: Path, mutation: Callable[[Document], None]
) -> None:
    catalogue, identities = _load_documents()
    mutation(catalogue["correction_selector"])
    _repair_hashes(catalogue, "complete_record_sha256", "catalogue_multiset_sha256")

    with pytest.raises(
        SchemaError,
        match=(
            r"closed correction selector mismatch|" r"correction_selector\.(selector_id|governance_index|mappings):"
        ),
    ):
        _validate_candidate(tmp_path, catalogue, identities)


def _fixed_expected_runtime_rows() -> list[Mapping[str, Any]]:
    """Expected values originate from a clean authority copy, never a candidate mutation."""
    authoritative_catalogue, _ = _load_documents()
    return _runtime_observations(authoritative_catalogue)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        pytest.param("key", "scope.create_alias", id="runtime-key"),
        pytest.param("command_type", "CreateScopeAlias", id="runtime-command-type"),
        pytest.param("command_schema_id", "ars://core/command/CreateScopeAlias", id="runtime-command-id"),
        pytest.param("ordered_events", ["ScopeCreatedAlias"], id="runtime-event-order"),
        pytest.param("event_schema_ids", ["ars://core/event/ScopeCreatedAlias"], id="runtime-event-id"),
    ],
)
def test_wp6_1_runtime_observations_are_compared_to_a_separate_expected_producer(
    tmp_path: Path, field: str, replacement: Any
) -> None:
    catalogue, identities = _load_documents()
    observed = [dict(item) for item in _fixed_expected_runtime_rows()]
    observed[0][field] = replacement

    with pytest.raises(SchemaError, match=r"observed runtime rows differ"):
        _validate_candidate(tmp_path, catalogue, identities, observed_runtime_rows=observed)


def test_wp6_1_canonical_schema_digest_changes_when_same_path_bytes_change(tmp_path: Path) -> None:
    schema_path = tmp_path / "candidate.schema.json"
    schema_path.write_bytes(b'{"$id":"ars://test/first"}\n')
    first = validation._canonical_schema_sha256(schema_path)

    schema_path.write_bytes(b'{"$id":"ars://test/second"}\n')
    second = validation._canonical_schema_sha256(schema_path)

    assert first != second
