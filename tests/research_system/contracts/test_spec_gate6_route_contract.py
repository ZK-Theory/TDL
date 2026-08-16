from __future__ import annotations

import hashlib
import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from research_system.discovery.spec_flow import validate_spec_route_contract
from research_system.errors import ConfigurationError, SchemaError
from research_system.schema_registry import cached_schema_registry


REPO = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO / ".research-system/schemas/contracts/wp6-6/spec-gate6-route.schema.json"
CONTRACT_PATH = REPO / ".research-system/contracts/wp6-6/spec-gate6-run-v1/route-package.json"
CATALOGUE_PATH = REPO / ".research-system/evals/expected/w11-portfolio-discovery-v1.json"

GOVERNING_SOURCES = [
    "decision:P-042",
    "repo:docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md",
    "repo:docs/plans/agentic-research-system/implementation/06g-wp6-owner-operated-session-amendment.md",
    "repo:.research-system/contracts/wp6-6/spec-gate6-run-v1/registered-path-read-policy.json",
    "owner-decision:SPEC-route-for-Gate-6",
]

EXPECTED_SOURCES = {
    "SPEC-01": (
        ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-01-assay-brief-v1.1.0.md",
        4745,
        "d3b1eac020b5c94707461c0a475cc911e36ab78e2bc1243c0b28747748106972",
    ),
    "SPEC-02": (
        ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-02-micro-spike-contract-v1.1.0.md",
        5937,
        "f005f4c961f91c4abcfdb6fc8a89d3b609b371ac5e613e82e68aaf5c3cf4dd32",
    ),
}

EXPECTED_LINEAGE = {
    "SPEC-01-lineage": (
        "vault/00-Meta/Discovery/ars-spec-01-spectral-distance-ph-assay-brief-v1.0.0-2026-07-16.md",
        14660,
        "39ee3e5a44ec9dbe25766e7ecf89b98fbae8eedcace2ae40f9d5a0fb32f43b84",
    ),
    "SPEC-02-lineage": (
        "vault/00-Meta/Discovery/ars-spec-02-spectral-distance-ph-micro-spike-template-v1.0.0-2026-07-16.md",
        12535,
        "f9316c33844d77c9bde9506decb942354a28441e372a06c7abc2d9ed03d5bec5",
    ),
}

EXPECTED_STAGE_ORDER = [
    "genesis",
    "authority",
    "admission",
    "source_observation",
    "spec_01_assay",
    "spec_01_outcome_review",
    "promotion_stop",
    "spec_02_spike",
    "spec_02_outcome_review",
    "result_stop",
]


def _committed_blob(relative_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", f"HEAD:{relative_path}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


SCHEMA_BINDINGS = {
    "ars://portfolio/candidate": "candidate.schema.json",
    "ars://portfolio/scout-observation-batch": "scout-observation-batch.schema.json",
    "ars://portfolio/assay-scorecard": "assay-scorecard.schema.json",
    "ars://portfolio/spike-plan": "spike-plan.schema.json",
    "ars://portfolio/spike-verdict": "spike-verdict.schema.json",
    "ars://portfolio/relation/assay-request": "relation-assay-request.schema.json",
    "ars://portfolio/relation/assay-producer": "relation-assay-producer.schema.json",
    "ars://portfolio/relation/discovery-promotion": "relation-discovery-promotion.schema.json",
    "ars://portfolio/relation/spike-plan": "relation-spike-plan.schema.json",
    "ars://portfolio/relation/spike-attempt": "relation-spike-attempt.schema.json",
    "ars://portfolio/research-dossier-manifest": "research-dossier-manifest.schema.json",
}

EXPECTED_RELATIONS = {
    "candidate_to_assay": ("candidate", "assay", "ars://portfolio/relation/assay-request"),
    "assay_to_producer": ("assay", "producer_runtime_record", "ars://portfolio/relation/assay-producer"),
    "assay_to_spike": ("assay", "spike", "ars://portfolio/relation/discovery-promotion"),
    "spike_to_plan": ("spike", "spike_plan_runtime_record", "ars://portfolio/relation/spike-plan"),
    "spike_to_attempt": ("spike", "attempt_lease_runtime_record", "ars://portfolio/relation/spike-attempt"),
}

OWNER_ROW_DOMAIN = {f"OR-{number:03d}" for number in range(1, 42)} | {f"OR-{number:03d}" for number in range(101, 141)}


def _load() -> tuple[dict[str, object], dict[str, object]]:
    return json.loads(SCHEMA_PATH.read_bytes()), json.loads(CONTRACT_PATH.read_bytes())


def _catalogue_rows() -> dict[str, dict[str, object]]:
    catalogue = json.loads(CATALOGUE_PATH.read_bytes())
    return {row["owner_row_id"]: row for row in catalogue["owner_contract_rows"]}


def _validate_contract(contract: dict[str, object], *, lineage_root: Path | None = None) -> None:
    schema = json.loads(SCHEMA_PATH.read_bytes())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(contract)
    validate_spec_route_contract(
        REPO,
        CATALOGUE_PATH,
        cached_schema_registry(REPO / ".research-system/schemas"),
        contract,
    )
    _validate_semantics(contract, lineage_root=lineage_root)


def _validate_semantics(contract: dict[str, object], *, lineage_root: Path | None) -> None:
    route_schema = json.loads(SCHEMA_PATH.read_bytes())
    authoritative_steps = route_schema["properties"]["route_steps"]["const"]
    authoritative_exclusions = route_schema["properties"]["intentional_exclusions"]["const"]
    if contract["route_steps"] != authoritative_steps:
        raise ValueError("closed_route_step_mapping_mismatch")
    if contract["intentional_exclusions"] != authoritative_exclusions:
        raise ValueError("closed_route_exclusion_mapping_mismatch")
    if contract["governing_sources"] != GOVERNING_SOURCES:
        raise ValueError("governing_source_set_mismatch")

    current_sources = {row["alias"]: row for row in contract["sources"]}
    if set(current_sources) != set(EXPECTED_SOURCES):
        raise ValueError("current_source_set_mismatch")
    for alias, (locator, size, digest) in EXPECTED_SOURCES.items():
        row = current_sources[alias]
        if (row["locator"], row["size_bytes"], row["sha256"], row["admitted_member"]) != (
            locator,
            size,
            digest,
            True,
        ):
            raise ValueError("current_source_identity_mismatch")
        raw = (REPO / locator).read_bytes()
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError("governed_source_identity_mismatch")
        if re.search(rb"\b(?:scale(?:-01)?|dir)\b", raw.lower()):
            raise ValueError("foreign_predecessor_in_governed_source")

    lineage = {row["alias"]: row for row in contract["lineage_sources"]}
    if set(lineage) != set(EXPECTED_LINEAGE):
        raise ValueError("lineage_source_set_mismatch")
    for alias, (locator, size, digest) in EXPECTED_LINEAGE.items():
        row = lineage[alias]
        if (row["locator"], row["size_bytes"], row["sha256"]) != (locator, size, digest):
            raise ValueError("lineage_identity_mismatch")
        if row["required"] or row["current_authority"] or row["admitted_member"] or row["live_root_token"]:
            raise ValueError("lineage_must_be_optional_metadata")
        if lineage_root is not None:
            path = lineage_root / locator
            if path.is_file():
                raw = path.read_bytes()
                if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
                    raise ValueError("observed_lineage_identity_mismatch")

    if contract["admission"]["current_expected_set_source_aliases"] != list(EXPECTED_SOURCES):
        raise ValueError("admission_current_source_mismatch")
    if contract["admission"]["live_root_tokens"] != ["repository"] or not contract["admission"]["lineage_excluded"]:
        raise ValueError("lineage_admission_leak")

    slots = {row["slot"]: row for row in contract["identity_slots"]}
    expected_slot_kinds = {
        "dossier": "object",
        "scope": "object",
        "candidate": "object",
        "assay": "assay",
        "spike": "spike",
    }
    if {slot: row["id_kind"] for slot, row in slots.items()} != expected_slot_kinds:
        raise ValueError("identity_slot_set_mismatch")
    for row in slots.values():
        if row["value_in_contract"] is not None:
            raise ValueError("concrete_identity_in_inert_contract")
        if row["registry_check"] != "absent_from_all_replayed_accepted_registries":
            raise ValueError("accepted_registry_exclusion_missing")
        if row["uniqueness"] != "pairwise_distinct_across_route_slots":
            raise ValueError("identity_slot_distinctness_missing")
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    if re.search(r'"(?:act|agr|ses|obj|asy|spk)_[0-9a-f-]+"', canonical):
        raise ValueError("concrete_runtime_identity_present")

    relations = {row["relation_kind"]: row for row in contract["relations"]}
    if set(relations) != set(EXPECTED_RELATIONS):
        raise ValueError("relation_set_mismatch")
    for kind, expected in EXPECTED_RELATIONS.items():
        row = relations[kind]
        if (row["from_slot"], row["to_slot"], row["schema_id"]) != expected:
            raise ValueError("relation_binding_mismatch")

    if contract["stage_order"] != EXPECTED_STAGE_ORDER:
        raise ValueError("stage_order_mismatch")
    stage_positions = {stage: index for index, stage in enumerate(EXPECTED_STAGE_ORDER)}
    steps = contract["route_steps"]
    if [stage_positions[row["stage"]] for row in steps] != sorted(stage_positions[row["stage"]] for row in steps):
        raise ValueError("route_step_order_mismatch")

    route_rows = [owner_row for step in steps for owner_row in step["owner_rows"]]
    if len(route_rows) != len(set(route_rows)):
        raise ValueError("duplicate_route_owner_row")
    exclusions = [owner_row for group in contract["intentional_exclusions"] for owner_row in group["owner_rows"]]
    if len(exclusions) != len(set(exclusions)):
        raise ValueError("duplicate_exclusion_owner_row")
    if set(route_rows) & set(exclusions) or set(route_rows) | set(exclusions) != OWNER_ROW_DOMAIN:
        raise ValueError("route_exclusion_partition_mismatch")

    catalogue = _catalogue_rows()
    derived_commands: list[str] = []
    for owner_row in route_rows:
        command_type = catalogue[owner_row]["command_type"]
        if command_type not in derived_commands:
            derived_commands.append(command_type)
    if contract["governed_command_types"] != derived_commands:
        raise ValueError("governed_command_derivation_mismatch")
    if catalogue["OR-029"]["command_type"] != "IngestScoutObservationBatch" or "OR-001" in route_rows:
        raise ValueError("real_source_observation_route_missing")
    if catalogue["OR-005"]["command_type"] != "RecordAssayPartial" or "OR-005" not in route_rows:
        raise ValueError("assay_partial_route_missing")

    row_stage = {owner_row: step["stage"] for step in steps for owner_row in step["owner_rows"]}
    required_row_stages = {
        "OR-029": "source_observation",
        "OR-003": "spec_01_assay",
        "OR-005": "spec_01_assay",
        "OR-014": "spec_02_spike",
        "OR-017": "spec_02_spike",
        "OR-018": "spec_02_spike",
        "OR-019": "spec_02_spike",
        "OR-036": "spec_02_outcome_review",
        "OR-037": "spec_02_outcome_review",
        "OR-020": "spec_02_outcome_review",
        "OR-021": "spec_02_outcome_review",
        "OR-026": "result_stop",
        "OR-027": "result_stop",
    }
    if any(row_stage.get(owner_row) != stage for owner_row, stage in required_row_stages.items()):
        raise ValueError("route_row_stage_mismatch")
    row_position = {owner_row: index for index, owner_row in enumerate(route_rows)}
    strict_precedence = [
        ("OR-029", "OR-003"),
        ("OR-003", "OR-005"),
        ("OR-014", "OR-015"),
        ("OR-015", "OR-016"),
        ("OR-016", "OR-017"),
        ("OR-017", "OR-018"),
        ("OR-017", "OR-019"),
        ("OR-018", "OR-036"),
        ("OR-036", "OR-020"),
        ("OR-019", "OR-037"),
        ("OR-037", "OR-021"),
        ("OR-020", "OR-026"),
        ("OR-021", "OR-026"),
        ("OR-026", "OR-027"),
    ]
    if any(row_position[before] >= row_position[after] for before, after in strict_precedence):
        raise ValueError("route_row_precedence_mismatch")

    if contract["atomicity"] != {
        "invalid_input_classes": ["missing", "extra", "duplicate", "tampered", "invalid_order", "authority_mismatched"],
        "failure_outcome": "zero_publication",
        "zero_publication_surfaces": ["events", "objects", "projections", "receipts", "indexes", "results", "claims"],
        "duplicate_publication_count": 0,
        "corrupt_publication_count": 0,
    }:
        raise ValueError("atomicity_contract_mismatch")
    if contract["restart"] != {
        "idempotency_tuple": ["actor_id", "authority_scope", "command_type", "idempotency_key"],
        "committed_command_binding": "exact_canonical_command_digest",
        "same_input_same_receipt_and_event_batch": True,
        "replay_from_durable_ledger": True,
        "changed_command_outcome": "conflict_without_publication",
        "repair_allowed": False,
        "resume_requires_exact_relations": True,
    }:
        raise ValueError("restart_contract_mismatch")

    bindings = contract["schema_bindings"]
    if bindings != [{"schema_id": schema_id, "schema_version": "1.0.0"} for schema_id in SCHEMA_BINDINGS]:
        raise ValueError("schema_binding_set_mismatch")
    schema_root = REPO / ".research-system/schemas/contracts/w11"
    for schema_id, filename in SCHEMA_BINDINGS.items():
        schema = json.loads((schema_root / filename).read_bytes())
        Draft202012Validator.check_schema(schema)
        if schema["$id"] != schema_id:
            raise ValueError("schema_identity_mismatch")

    if not all(contract["producer_authority_binding"].values()):
        raise ValueError("producer_authority_binding_missing")
    if contract["stage_gates"]["spec_02_entry"]["automatic_advance"]:
        raise ValueError("automatic_spec_02_advance")
    if contract["stage_gates"]["result_stop"]["import_is_result_or_claim_acceptance"]:
        raise ValueError("import_result_acceptance_forbidden")
    if not all(contract["prohibitions"].values()):
        raise ValueError("prohibition_missing")


def test_spec_gate6_route_contract_binds_exact_proposed_package() -> None:
    schema, contract = _load()
    object_nodes: list[dict[str, object]] = []
    pending: list[object] = [schema]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            if node.get("type") == "object":
                object_nodes.append(node)
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    assert object_nodes and all(node.get("additionalProperties") is False for node in object_nodes)
    _validate_contract(contract)


def test_optional_lineage_observation_never_controls_current_validity(tmp_path: Path) -> None:
    _, contract = _load()
    _validate_contract(contract)
    _validate_contract(contract, lineage_root=tmp_path)
    actual_external_root = Path("C:/Users/steph/TDL")
    if actual_external_root.is_dir():
        _validate_contract(contract, lineage_root=actual_external_root)


def _drop_first_route_row(value: dict[str, object]) -> None:
    value["route_steps"][0]["owner_rows"].pop()


def _add_extra_route_row(value: dict[str, object]) -> None:
    value["route_steps"][0]["owner_rows"].append("OR-001")


def _duplicate_route_row(value: dict[str, object]) -> None:
    value["route_steps"][1]["owner_rows"].append("OR-140")


def _invalidate_route_order(value: dict[str, object]) -> None:
    value["route_steps"][0], value["route_steps"][-1] = value["route_steps"][-1], value["route_steps"][0]


def _authority_mismatch(value: dict[str, object]) -> None:
    value["route_steps"][6]["owner_rows"] = ["OR-001"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value["governing_sources"].__setitem__(0, "unrelated:source"),
        lambda value: value["governing_sources"].pop(),
        lambda value: value["governing_sources"].append("extra:source"),
        lambda value: value["identity_slots"][0].__setitem__(
            "value_in_contract", "obj_01978abc-1000-7000-8000-000000001000"
        ),
        lambda value: value["identity_slots"][0].__setitem__("registry_check", "unchecked"),
        lambda value: value["operator_exchange"].__setitem__(
            "session_defaults", {"actor_id": "act_fixture", "session_id": "ses_fixture"}
        ),
        lambda value: value["lineage_sources"][0].__setitem__("required", True),
        lambda value: value["lineage_sources"][0].__setitem__("admitted_member", True),
        _drop_first_route_row,
        _add_extra_route_row,
        _duplicate_route_row,
        _invalidate_route_order,
        _authority_mismatch,
        lambda value: value["governed_command_types"].pop(),
        lambda value: value["governed_command_types"].append("ExtraCommand"),
        lambda value: value["atomicity"]["invalid_input_classes"].remove("tampered"),
        lambda value: value["atomicity"]["zero_publication_surfaces"].remove("receipts"),
        lambda value: value["restart"].__setitem__("same_input_same_receipt_and_event_batch", False),
        lambda value: value["restart"].__setitem__("repair_allowed", True),
        lambda value: value["schema_bindings"].pop(1),
        lambda value: value["producer_authority_binding"].__setitem__("caller_built_substitute_rejected", False),
        lambda value: value["stage_gates"]["spec_02_entry"].__setitem__("automatic_advance", True),
        lambda value: value["stage_gates"]["result_stop"].__setitem__("import_is_result_or_claim_acceptance", True),
        lambda value: value["prohibitions"].__setitem__("provider_process_or_cli_launch", False),
        lambda value: value["prohibitions"].__setitem__("provider_api_call", False),
        lambda value: value["prohibitions"].__setitem__("oauth_read_store_resolve_or_pass", False),
    ],
)
def test_spec_gate6_route_mutations_reject_through_public_validator(mutation) -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    mutation(invalid)
    with pytest.raises(ValidationError):
        _validate_contract(invalid)


@pytest.mark.parametrize(("field", "value"), [("sha256", "f" * 64), ("size_bytes", 1)])
def test_spec_gate6_source_identity_mutations_reject_through_public_validator(field, value) -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    invalid["sources"][0][field] = value

    with pytest.raises(ConfigurationError, match="SPEC-01 governed source binding differs"):
        _validate_contract(invalid)


def _recompute_governed_commands(value: dict[str, object]) -> None:
    catalogue = _catalogue_rows()
    commands: list[str] = []
    for step in value["route_steps"]:
        for owner_row in step["owner_rows"]:
            command_type = catalogue[owner_row]["command_type"]
            if command_type not in commands:
                commands.append(command_type)
    value["governed_command_types"] = commands


def test_rework_rejects_selected_row_stage_swap_even_after_command_recompute() -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    source_step = next(step for step in invalid["route_steps"] if step["step_id"] == "source_observation_and_candidate")
    assay_step = next(step for step in invalid["route_steps"] if step["step_id"] == "assay_request")
    source_step["owner_rows"], assay_step["owner_rows"] = assay_step["owner_rows"], source_step["owner_rows"]
    _recompute_governed_commands(invalid)
    with pytest.raises(ValidationError):
        _validate_contract(invalid)


def test_rework_rejects_selected_excluded_substitution_after_command_recompute() -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    assay_step = next(step for step in invalid["route_steps"] if step["step_id"] == "assay_request")
    exclusion = next(group for group in invalid["intentional_exclusions"] if "OR-030" in group["owner_rows"])
    assay_step["owner_rows"] = ["OR-030"]
    exclusion["owner_rows"][exclusion["owner_rows"].index("OR-030")] = "OR-003"
    _recompute_governed_commands(invalid)
    with pytest.raises(ValidationError):
        _validate_contract(invalid)


def test_rework_rejects_or029_stage_mutation() -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    source_step = next(step for step in invalid["route_steps"] if step["step_id"] == "source_observation_and_candidate")
    source_step["stage"] = "spec_01_assay"
    with pytest.raises(ValidationError):
        _validate_contract(invalid)


def test_rework_rejects_or029_step_swap_with_later_step() -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    source_index = next(
        index
        for index, step in enumerate(invalid["route_steps"])
        if step["step_id"] == "source_observation_and_candidate"
    )
    spike_index = next(
        index
        for index, step in enumerate(invalid["route_steps"])
        if step["step_id"] == "spike_plan_authority_and_start"
    )
    invalid["route_steps"][source_index], invalid["route_steps"][spike_index] = (
        invalid["route_steps"][spike_index],
        invalid["route_steps"][source_index],
    )
    _recompute_governed_commands(invalid)
    with pytest.raises(ValidationError):
        _validate_contract(invalid)


def test_rework_rejects_later_row_swap_after_command_recompute() -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    start_step = next(step for step in invalid["route_steps"] if step["step_id"] == "spike_plan_authority_and_start")
    verdict_step = next(step for step in invalid["route_steps"] if step["step_id"] == "spike_verdict_complete")
    start_step["owner_rows"][-1], verdict_step["owner_rows"][0] = (
        verdict_step["owner_rows"][0],
        start_step["owner_rows"][-1],
    )
    _recompute_governed_commands(invalid)
    with pytest.raises(ValidationError):
        _validate_contract(invalid)


def test_rework_rejects_command_order_swap_for_authoritative_rows() -> None:
    _, contract = _load()
    invalid = deepcopy(contract)
    commands = invalid["governed_command_types"]
    observation_index = commands.index("IngestScoutObservationBatch")
    assay_index = commands.index("RequestAssay")
    commands[observation_index], commands[assay_index] = commands[assay_index], commands[observation_index]
    with pytest.raises(ConfigurationError, match="SPEC route command derivation differs"):
        _validate_contract(invalid)


def test_spec_operator_brief_binds_exact_stage_source_bytes_and_git_blob() -> None:
    registry = cached_schema_registry(REPO / ".research-system/schemas")
    brief = {
        "schema_id": "ars://portfolio/spec-operator-brief-package",
        "schema_version": "1.0.0",
        "document_type": "spec_01_operator_brief",
        "route_id": "SPEC-GATE6-RUN-V1",
        "stage": "SPEC-01",
        "route_expected_return_type": "AssayScorecard",
        "route_source": {
            "relative_path": EXPECTED_SOURCES["SPEC-01"][0],
            "raw_sha256": EXPECTED_SOURCES["SPEC-01"][2],
            "git_blob": _committed_blob(EXPECTED_SOURCES["SPEC-01"][0]),
        },
        "brief_manifest": {},
        "brief_manifest_sha256": "a" * 64,
        "operator_session": {
            "session_id": "session-1",
            "operator_actor_id": "actor-1",
            "application": "Codex desktop",
            "application_version": "1",
            "manually_operated": True,
        },
        "prohibitions": [
            "no provider or model launch",
            "no automatic promotion",
            "import is candidate evidence only",
        ],
    }
    registry.validate("ars://portfolio/spec-operator-brief-package", brief, schema_version="1.0.0")

    for field, changed in (("raw_sha256", "f" * 64), ("git_blob", "f" * 40)):
        invalid = deepcopy(brief)
        invalid["route_source"][field] = changed
        with pytest.raises(SchemaError):
            registry.validate("ars://portfolio/spec-operator-brief-package", invalid, schema_version="1.0.0")


def test_dossier_governing_decision_binds_exact_p042_section_bytes() -> None:
    decisions = (REPO / "docs/plans/agentic-research-system/03-decisions-and-open-questions.md").read_bytes()
    start = decisions.index(b"### P-042 - Owner-operated external model sessions")
    end = decisions.find(b"\n### P-", start + 1)
    section = decisions[start:] if end < 0 else decisions[start : end + 1]
    manifest = json.loads(
        (REPO / ".research-system/contracts/wp6-6/spec-gate6-run-v1/spec-research-dossier-manifest.json").read_bytes()
    )

    assert manifest["governing_decisions"] == [
        {
            "id": "decision:P-042",
            "record_revision": 1,
            "content_hash": hashlib.sha256(section).hexdigest(),
        }
    ]
