"""Binding tests for the ``TDL_private`` pack candidate and its acceptance loader.

Deliberately a separate module from
``test_wp6_3_tdl_private_assurance_pack_contract.py``: that module's declared test
surface is closed at its declared function set and ``_assert_test_surface_closure``
fails on any addition.

Every declared value is read from the governing artifact — the upstream contract, the
pack schema, or the W1 allocation file — rather than restated here, so drift fails
instead of passing on a stale literal.

Two enforcement layers exist. Where the pack schema or the external-record schema
already rejects a mutation, this module proves that with a schema-level negative
control instead of adding an unreachable runtime check beside it.
"""

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from research_system.assurance import (
    AUTHORITY_RESOLUTION_PHASES,
    PackUnconsumable,
    git_blob_id,
    validate_tdl_private_pack_for_acceptance,
)
from research_system.assurance.external_records import ExternalRecordResolution
from research_system.assurance.pack_loader import _RECORD_ENVELOPE, _require_key
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry
from tests.research_system.contracts.test_wp6_3_tdl_private_assurance_pack_contract import (
    _assert_test_surface_closure,
)

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
CONTRACT_PATH = ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
PACK_SCHEMA_PATH = SCHEMAS / "assurance" / "assurance-pack.schema.json"
EXTERNAL_RECORD_SCHEMA_PATH = SCHEMAS / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json"
ALLOCATIONS_PATH = ROOT / ".research-system" / "config" / "assurance-pack-object-allocations.yaml"
IDENTITY_ALLOCATIONS_PATH = ROOT / ".research-system" / "config" / "assurance-producer-and-requirement-allocations.yaml"
PACK_SCHEMA_ID = "ars://assurance/packs/tdl-private/1.0"

EVALUATION_TIME = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)

# Five of the six external identities the candidate must carry are now allocated under W1
# authority (Decision 2) and are read from the allocation file rather than restated here.
# The `scope_reviewer` actor is still a placeholder — it is one of the identities Decision 5
# routes through the external control store rather than through repository YAML.
#
# `acceptance_record_sha256` is the other exception and is deliberately still a placeholder:
# it hashes an owner acceptance record that has to genuinely exist, so it cannot be
# allocated ahead of the acceptance. `test_requirement_acceptance_is_still_pending` fails
# the moment it lands, which is the signal that the candidate can finally be authored.
PLACEHOLDER_SCOPE_REVIEWER_ACTOR_ID = "act_00000000-0000-7000-8000-000000000001"
PLACEHOLDER_REQUIREMENT_SHA256 = "0" * 64

AUTHORITY_ROOT = "authority-root-under-test"


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _schema_registry() -> SchemaRegistry:
    return SchemaRegistry(SCHEMAS)


def _repository_subject(path: Path) -> dict:
    """Return the content-addressed subject of a committed repository artifact."""
    data = path.read_bytes()
    assert b"\r" not in data, f"{path} must be LF in the working tree (canonical byte surface)"
    return {"git_blob": git_blob_id(data), "canonical_sha256": hashlib.sha256(data).hexdigest()}


def _accepted_contract_subject() -> dict:
    subject = _repository_subject(CONTRACT_PATH)
    return {
        "schema_id": "ars://contracts/wp6-3-tdl-private-assurance-pack",
        "schema_version": "1.0.0",
        "repository_path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
        **subject,
    }


def _accepted_schema_subject() -> dict:
    subject = _repository_subject(PACK_SCHEMA_PATH)
    return {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "repository_path": PACK_SCHEMA_PATH.relative_to(ROOT).as_posix(),
        **subject,
    }


def _expanded_obligation(row: dict, profile: dict) -> dict:
    return {
        "obligation_id": row["obligation_id"],
        "row_profile_id": profile["row_profile_id"],
        "source_authority_id": profile["source_authority_id"],
        "source_sections": deepcopy(row["source_sections"]),
        "assertion_classes": deepcopy(row["assertion_classes"]),
        "enforcing_reference_ids": deepcopy(row["enforcing_reference_ids"]),
        "review_question_id": row["review_question_id"],
        "evidence_output_id": row["evidence_output_id"],
    }


def build_candidate_pack(contract: dict | None = None) -> dict:
    """Build the ``TDL_private`` pack candidate from the governing contract.

    Nothing structural is authored here. Lanes, obligations, fixtures, references,
    consumers, and source authority are all projected from the upstream contract, so
    the candidate cannot silently diverge from what it claims to implement.

    Args:
        contract: Parsed upstream contract; read from the repository when omitted.

    Returns:
        The candidate pack object.
    """
    contract = deepcopy(contract or _load_yaml(CONTRACT_PATH))
    required = contract["required_pack_contract"]
    reference_rows = required["references"]["exact_reference_rows"]
    profile = required["obligation_row_profile"]
    allocation = _current_allocation()
    producer = _current_producer_allocation()
    requirement = _current_requirement_allocation()

    lanes = {
        lane_id: {
            "lane_id": lane_id,
            "governing_reference_ids": deepcopy(lane_contract["exact_governing_reference_ids"]),
            "obligation_rows": [_expanded_obligation(row, profile) for row in lane_contract["required_obligations"]],
            "fixture_ids": deepcopy(lane_contract["exact_fixture_ids"]),
            "prospective_schema_only": True,
            "scientific_review_status": "not_performed_by_pack_schema",
            "failure_consequence": "blocked_no_cross_lane_compensation",
            "cross_lane_compensation": "prohibited",
        }
        for lane_id, lane_contract in required["lanes"].items()
    }

    return {
        "schema_id": PACK_SCHEMA_ID,
        "schema_version": "1.0.0",
        "pack_id": "TDL_private",
        "assurance_pack_id": allocation["assurance_pack_id"],
        "assurance_pack_revision": allocation["assurance_pack_revision"],
        "canonical_repository_path": allocation["canonical_repository_path"],
        "distribution_scope": allocation["distribution_scope"],
        "candidate_state": "proposed",
        "producer_actor_id": producer["actor_id"],
        "upstream_contract_reference": _accepted_contract_subject(),
        "schema_reference": _accepted_schema_subject(),
        "assurance_requirement_reference": {
            "assurance_requirement_id": requirement["assurance_requirement_id"],
            "revision": requirement["revision"],
            "acceptance_record_id": requirement["acceptance_record_id"],
            "acceptance_record_sha256": requirement["acceptance_record_sha256"] or PLACEHOLDER_REQUIREMENT_SHA256,
            "prospective_producer_actor_id": requirement["prospective_producer_actor_id"],
        },
        "source_authority": {
            "accepted_plan_revision": contract["source_authority"]["accepted_plan_revision"],
            "governing_sources": deepcopy(contract["source_authority"]["governing_sources"]),
        },
        "references": {
            "contract_references": [deepcopy(r) for r in reference_rows if r["reference_kind"] == "contract"],
            "skill_references": [deepcopy(r) for r in reference_rows if r["reference_kind"] == "skill"],
        },
        "task_applicability_policy": {
            "pack_obligations": profile["applicability"].replace("required", "all_required"),
            "task_not_applicable_location": profile["task_not_applicable_location"],
            "producer_only_confirmation": profile["producer_only_not_applicable"],
            "minimum_independence_grade": required["external_acceptance_evidence"]["minimum_independence_grade"],
            "unable_to_grade_may_pass": False,
            "partial_may_pass": False,
            "failed_proof_may_pass": False,
        },
        "distribution_controls": {
            "permitted_consumers": deepcopy(required["distribution"]["exact_permitted_consumers"]),
            "public_template_export": required["distribution"]["public_template_export"],
            "publication_boundary": {
                "public_template_use": "prohibited",
                "manuscript_use": "requires_separately_accepted_result_and_claim_decision",
                "public_excerpt": "prohibited_without_template_safe_derivative_review",
                "claim_promotion": "requires_stephen_attributed_p005_decision",
            },
            "path_restrictions": {
                "repository_namespace": "tdl_private_only",
                "public_repository_paths": "prohibited",
                "public_template_paths": "prohibited",
                "private_path_disclosure": "opaque_content_addressed_references_only",
            },
            "data_restrictions": {
                "raw_restricted_data": "prohibited",
                "minimized_excerpts": "separately_authorized_only",
                "restricted_references": "opaque_content_addressed_only",
                "secrets_env_transcripts_hidden_reasoning": "prohibited",
            },
        },
        "currency": {
            "authored_at": "2026-07-28T09:00:00Z",
            "effective_at": "2026-07-28T09:00:00Z",
            "expires_at": "2027-07-28T09:00:00Z",
            "currency_triggers": [
                "upstream_contract_identity_changed",
                "schema_identity_changed",
                "reference_identity_or_activation_changed",
                "assurance_requirement_or_producer_relationship_changed",
                "distribution_or_consumer_policy_changed",
            ],
            "retention_class": "durable_governance_record",
            "stale_identity_behavior": "block_consumption_and_require_superseding_revision",
        },
        "lanes": lanes,
        "required_fixtures": deepcopy(required["fixtures"]["exact_fixture_rows"]),
        "limitations": [
            "prospective_pack_no_result_or_claim_review",
            "schema_shape_does_not_establish_scientific_validity",
            "candidate_cannot_assert_review_or_owner_acceptance",
            "pending_reference_blocks_owner_acceptance",
        ],
        "core_boundary": {
            "may_modify_w1_w2_lifecycle": False,
            "may_modify_canonical_authority": False,
            "may_override_p005_p022": False,
            "may_lower_w3_w4_controls": False,
            "may_assert_observed_results": False,
            "may_accept_results": False,
            "may_promote_claims": False,
            "may_authorize_migration": False,
        },
    }


def render_candidate_bytes(pack: dict) -> bytes:
    """Render a candidate to its canonical ``git_blob_utf8_lf`` byte surface."""
    raw = yaml.safe_dump(pack, sort_keys=False, allow_unicode=True, width=4096).encode("utf-8")
    assert b"\r" not in raw and raw.endswith(b"\n")
    return raw


def _current_allocation() -> dict:
    allocations = [row for row in _load_yaml(ALLOCATIONS_PATH)["allocations"] if row["id_kind"] == "assurance_pack"]
    current_revision = max(row["assurance_pack_revision"] for row in allocations)
    return next(row for row in allocations if row["assurance_pack_revision"] == current_revision)


def _current_producer_allocation() -> dict:
    """Return the current W1-allocated `future_pack_producer` actor row."""
    rows = [
        row
        for row in _load_yaml(IDENTITY_ALLOCATIONS_PATH)["actor_allocations"]
        if row["role"] == "future_pack_producer"
    ]
    return max(rows, key=lambda row: row["revision"])


def _current_requirement_allocation() -> dict:
    """Return the current W1-allocated assurance-requirement row."""
    rows = _load_yaml(IDENTITY_ALLOCATIONS_PATH)["assurance_requirement_allocations"]
    return max(rows, key=lambda row: row["revision"])


def _reference_snapshot(pack: dict) -> dict[str, dict]:
    rows = pack["references"]["contract_references"] + pack["references"]["skill_references"]
    return {
        row["reference_id"]: {
            "git_blob": row["git_blob"],
            "canonical_sha256": row["canonical_sha256"],
            "activation_state": row["activation_state"],
            "pack_acceptance_eligible": row["pack_acceptance_eligible"],
        }
        for row in rows
    }


def _subject_block(raw: bytes, pack: dict) -> dict:
    return {
        "pack_git_blob": git_blob_id(raw),
        "pack_raw_sha256": hashlib.sha256(raw).hexdigest(),
        "assurance_pack_id": pack["assurance_pack_id"],
        "assurance_pack_revision": pack["assurance_pack_revision"],
    }


def _record_ids(contract: dict, pack: dict) -> dict[str, str]:
    """Return the opaque id per required record class.

    Two classes are identified by an id the candidate already pins, because the record schemas identify
    them that way: the registered pack object by its ``assurance_pack_id``, and the accepted requirement by
    its ``acceptance_record_id``. Using an invented id for those would let the double pass a check the real
    records could not.
    """
    classes = contract["required_pack_contract"]["external_acceptance_evidence"]["required_record_types"]
    reference = pack["assurance_requirement_reference"]
    pinned = {
        "registered_pack_object": pack["assurance_pack_id"],
        "accepted_assurance_requirement": reference["acceptance_record_id"],
    }
    return {record_class: pinned.get(record_class, f"rec_{record_class}") for record_class in classes}


def _record_store(pack: dict, raw: bytes, contract: dict) -> dict[str, dict]:
    """Build a complete, internally consistent external record store for the loader.

    Each record carries the identity and lifecycle fields its own accepted schema defines, taken from
    :data:`_RECORD_ENVELOPE`. The record schemas set ``additionalProperties: false`` and define no common
    envelope, so a double using a generic ``record_id``/``lifecycle_state`` shape would be testing the
    loader against records that could never exist.
    """
    ids = _record_ids(contract, pack)
    subject = _subject_block(raw, pack)
    requirement_reference = pack["assurance_requirement_reference"]
    store = {}
    for record_class, record_id in ids.items():
        id_field, state_field, active_state = _RECORD_ENVELOPE[record_class]
        store[record_class] = {id_field: record_id, "record_type": record_class, state_field: active_state}
    store["registered_pack_object"] |= {
        "assurance_pack_id": pack["assurance_pack_id"],
        "revision": pack["assurance_pack_revision"],
        "canonical_repository_path": pack["canonical_repository_path"],
    }
    store["producer_relationship_evidence"] |= {
        "relationship_context": "pack_scientific_review",
        "subject_actor_id": PLACEHOLDER_SCOPE_REVIEWER_ACTOR_ID,
        "object_actor_id": pack["producer_actor_id"],
        "grade": "I2",
        "effective_at": "2026-07-01T00:00:00Z",
        "expires_at": "2026-12-31T00:00:00Z",
    }
    store["accepted_assurance_requirement"] |= {
        "assurance_requirement_id": requirement_reference["assurance_requirement_id"],
        "revision": requirement_reference["revision"],
        "prospective_producer_actor_id": pack["producer_actor_id"],
        "scope_relationship_record_id": ids["producer_relationship_evidence"],
        "minimum_independence_grade": "I2",
    }
    store["independent_pack_review"] |= {
        "subject": subject,
        "reviewer_actor_id": PLACEHOLDER_SCOPE_REVIEWER_ACTOR_ID,
        "producer_actor_id": pack["producer_actor_id"],
        "relationship_record_id": ids["producer_relationship_evidence"],
        "minimum_independence_grade": "I2",
        "reviewed_at": "2026-07-28T10:00:00Z",
    }
    store["stephen_owner_acceptance"] |= {
        "subject": subject,
        "decided_at": "2026-07-28T11:00:00Z",
        "review_record_id": ids["independent_pack_review"],
    }
    return store


class _Resolver:
    """Trusted resolver stub. Records every (record_class, phase) it was asked for."""

    def __init__(
        self,
        store: dict[str, dict],
        *,
        per_phase_override: dict | None = None,
        per_phase_resolution_override: dict | None = None,
        trusted_digests: dict[str, str] | None = None,
        trusted_revisions: dict[str, int] | None = None,
    ) -> None:
        self.store = store
        self.per_phase_override = per_phase_override or {}
        self.per_phase_resolution_override = per_phase_resolution_override or {}
        self.trusted_digests = trusted_digests or {
            "accepted_assurance_requirement": PLACEHOLDER_REQUIREMENT_SHA256,
        }
        self.trusted_revisions = trusted_revisions or {}
        self.calls: list[tuple[str, str]] = []

    def resolve(self, *, record_id: str, record_class: str, authority_root: str, phase: str) -> dict:
        self.calls.append((record_class, phase))
        if (record_class, phase) in self.per_phase_override:
            return dict(self.per_phase_override[(record_class, phase)])
        if record_class not in self.store:
            raise KeyError(record_class)
        return dict(self.store[record_class])

    def resolve_with_receipt(
        self,
        *,
        record_id: str,
        record_class: str,
        authority_root: str,
        phase: str,
    ) -> ExternalRecordResolution:
        if (record_class, phase) in self.per_phase_resolution_override:
            self.calls.append((record_class, phase))
            resolution = self.per_phase_resolution_override[(record_class, phase)]
            if not isinstance(resolution, ExternalRecordResolution):
                raise TypeError("resolution override must carry trusted metadata")
            return resolution
        body = self.resolve(
            record_id=record_id,
            record_class=record_class,
            authority_root=authority_root,
            phase=phase,
        )
        return ExternalRecordResolution(
            record_class=record_class,
            record_id=record_id,
            revision=self.trusted_revisions.get(record_class, 1),
            canonical_sha256=self.trusted_digests.get(record_class, sha256_hex(canonical_bytes(body))),
            record=body,
        )


def _loader_kwargs(pack: dict, raw: bytes, contract: dict, **overrides) -> dict:
    kwargs = {
        "accepted_upstream_contract_subject": _accepted_contract_subject(),
        "accepted_schema_subject": _accepted_schema_subject(),
        "trusted_w1_w2_content_addressed_authority_resolver": _Resolver(_record_store(pack, raw, contract)),
        "independently_supplied_authority_root": AUTHORITY_ROOT,
        "opaque_external_record_ids": _record_ids(contract, pack),
        "current_exact_reference_snapshot": _reference_snapshot(pack),
        "raw_candidate_pack_bytes": raw,
        "evaluation_time": EVALUATION_TIME,
    }
    kwargs.update(overrides)
    return kwargs


@pytest.fixture(scope="module")
def contract() -> dict:
    return _load_yaml(CONTRACT_PATH)


@pytest.fixture(scope="module")
def candidate(contract: dict) -> tuple[dict, bytes]:
    pack = build_candidate_pack(contract)
    return pack, render_candidate_bytes(pack)


# --------------------------------------------------------------------------------------
# Deliverable 1 — the candidate
# --------------------------------------------------------------------------------------


def test_candidate_validates_against_the_accepted_pack_schema(candidate):
    pack, raw = candidate
    _schema_registry().validate(PACK_SCHEMA_ID, pack)
    # The bytes, not just the object, are what review binds — validate what parses from them.
    _schema_registry().validate(PACK_SCHEMA_ID, yaml.safe_load(raw.decode("utf-8")))


def test_candidate_lane_and_obligation_structure_equals_the_contract(contract, candidate):
    pack, _ = candidate
    required_lanes = contract["required_pack_contract"]["lanes"]
    assert set(pack["lanes"]) == set(required_lanes)

    keys: set[tuple[str, str]] = set()
    for lane_id, lane_contract in required_lanes.items():
        lane = pack["lanes"][lane_id]
        assert [row["obligation_id"] for row in lane["obligation_rows"]] == [
            row["obligation_id"] for row in lane_contract["required_obligations"]
        ]
        assert lane["governing_reference_ids"] == lane_contract["exact_governing_reference_ids"]
        assert lane["fixture_ids"] == lane_contract["exact_fixture_ids"]
        keys |= {(lane_id, row["obligation_id"]) for row in lane["obligation_rows"]}

    # 69 distinct (lane_id, obligation_id) keys, no lane compensating for another.
    assert len(keys) == sum(len(lane["required_obligations"]) for lane in required_lanes.values())
    assert len(keys) == 69


def test_candidate_lane_enforcers_stay_inside_their_allowed_lanes(candidate):
    pack, _ = candidate
    references = {
        row["reference_id"]: row
        for row in pack["references"]["contract_references"] + pack["references"]["skill_references"]
    }
    for lane_id, lane in pack["lanes"].items():
        governing = set(lane["governing_reference_ids"])
        for reference_id in governing:
            assert lane_id in references[reference_id]["allowed_lane_ids"], reference_id
        for obligation in lane["obligation_rows"]:
            assert set(obligation["enforcing_reference_ids"]) <= governing, obligation["obligation_id"]


def test_candidate_carries_the_w1_allocated_object_identity(candidate):
    pack, _ = candidate
    allocation = _current_allocation()
    assert pack["assurance_pack_id"] == allocation["assurance_pack_id"]
    assert pack["assurance_pack_id"] == "asp_019fa860-3a4b-7784-839f-60f6277e6ce9"
    assert pack["assurance_pack_revision"] == allocation["assurance_pack_revision"]
    assert pack["canonical_repository_path"] == allocation["canonical_repository_path"]


def test_candidate_carries_the_declared_boundary_fixtures(contract, candidate):
    pack, _ = candidate
    declared = contract["required_pack_contract"]["external_acceptance_evidence"][
        "required_executed_boundary_fixture_ids"
    ]
    fixture_ids = {row["fixture_id"] for row in pack["required_fixtures"]}
    assert set(declared) <= fixture_ids
    assert set(declared) == {"apf_tested_object_no_op", "apf_degenerate_fallback", "apf_claim_escalation"}


def test_candidate_asserts_no_review_acceptance_or_self_hash(candidate):
    """The pack schema owns these prohibitions; this is the watched negative that proves it."""
    pack, _ = candidate
    registry = _schema_registry()

    accepted = deepcopy(pack)
    accepted["candidate_state"] = "owner_accepted"
    with pytest.raises(SchemaError):
        registry.validate(PACK_SCHEMA_ID, accepted)

    for self_referential_field in ("pack_raw_sha256", "pack_git_blob", "review_verdict", "owner_decision"):
        mutated = deepcopy(pack)
        mutated[self_referential_field] = "x" * 64
        with pytest.raises(SchemaError):
            registry.validate(PACK_SCHEMA_ID, mutated)


def test_candidate_carries_the_w1_allocated_producer_and_requirement_identities(candidate):
    """The producer may not mint any of these; they are read from the W1 allocation file."""
    pack, _ = candidate
    producer = _current_producer_allocation()
    requirement = _current_requirement_allocation()
    reference = pack["assurance_requirement_reference"]

    assert pack["producer_actor_id"] == producer["actor_id"]
    assert reference["assurance_requirement_id"] == requirement["assurance_requirement_id"]
    assert reference["revision"] == requirement["revision"]
    assert reference["acceptance_record_id"] == requirement["acceptance_record_id"]

    # One identity for one role. `future_pack_producer` is a single role in the eleven
    # declared distinct pairs, so two identities for it would make the matrix unevaluable.
    assert reference["prospective_producer_actor_id"] == pack["producer_actor_id"]
    assert requirement["prospective_producer_actor_id"] == producer["actor_id"]


def test_allocated_identities_satisfy_the_pack_schema_patterns():
    """Independently of the allocation file, the schema constrains the fields they land in."""
    schema_defs = _load_json(PACK_SCHEMA_PATH)["$defs"]
    requirement = _current_requirement_allocation()

    checks = (
        (_current_producer_allocation()["actor_id"], "actorId"),
        (requirement["prospective_producer_actor_id"], "actorId"),
        (requirement["assurance_requirement_id"], "assuranceRequirementId"),
        (requirement["acceptance_record_id"], "recordId"),
    )
    for value, definition in checks:
        assert re.fullmatch(schema_defs[definition]["pattern"], value), f"{value} fails {definition}"

    assert requirement["revision"] >= 1


def test_producer_is_distinct_from_every_role_the_contract_separates_it_from(contract):
    """The allocation's declared separations must be the contract's, not a hand-written subset."""
    declared_pairs = contract["required_pack_contract"]["external_acceptance_evidence"]["required_distinct_pairs"]
    contract_side = {
        other
        for pair in declared_pairs
        for other in pair
        if "future_pack_producer" in pair and other != "future_pack_producer"
    }
    allocation_side = set(_current_producer_allocation()["must_differ_from_roles"])
    assert allocation_side == contract_side, (
        f"allocation separations differ from the contract's: only-in-allocation="
        f"{sorted(allocation_side - contract_side)}, only-in-contract={sorted(contract_side - allocation_side)}"
    )


def test_requirement_acceptance_is_still_pending(candidate):
    """`acceptance_record_sha256` is the one field W1 cannot allocate ahead of the acceptance.

    It hashes an owner acceptance record that has to genuinely exist. Minting a hash over
    nothing is exactly the self-attestation the contract forbids, and the contract's
    `required_temporal_order` puts `requirement_accepted` before `candidate_authored`.

    This fails the moment the acceptance lands, which is the signal that the pack candidate
    can finally be authored — and it is deleted in that same change, not before.
    """
    pack, _ = candidate
    requirement = _current_requirement_allocation()

    assert requirement["acceptance_state"] == "pending_owner_acceptance"
    assert requirement["acceptance_record_sha256"] is None
    assert pack["assurance_requirement_reference"]["acceptance_record_sha256"] == PLACEHOLDER_REQUIREMENT_SHA256


def test_every_required_record_identity_is_allocated_or_declared_pending():
    """Enumerate the required identity set from the schemas instead of discovering it piecemeal.

    Three sessions have now stopped on the same class of gap — the producer and requirement
    identities, then `task_id`, then the relationship and remaining actor ids — because each
    was found by reading a schema at the moment it was needed. This derives the whole
    required set live from the two external record schemas and asserts each field is either
    allocated or explicitly declared pending, so a newly-required identity cannot appear
    silently and the pending list cannot rot into a stale hand-transcription.
    """
    schema = _load_json(EXTERNAL_RECORD_SCHEMA_PATH)["$defs"]
    identity_pattern = re.compile(r"\^(act|rel|asr|ard|arv|apr|tsk|agr|asp)_")

    required_identity_fields: dict[str, str] = {}
    for record_class in ("acceptedAssuranceRequirementRecord", "producerRelationshipEvidenceRecord"):
        definition = schema[record_class]
        for field in definition["required"]:
            pattern = definition["properties"].get(field, {}).get("pattern", "")
            match = identity_pattern.match(pattern)
            if match:
                required_identity_fields[field] = match.group(1)

    allocations = _load_yaml(IDENTITY_ALLOCATIONS_PATH)
    allocated_fields = {
        key
        for block in ("actor_allocations", "assurance_requirement_allocations")
        for row in allocations[block]
        for key, value in row.items()
        if isinstance(value, str) and re.match(r"^(act|rel|asr|ard|tsk)_[0-9a-f]{8}-", value)
    }
    pending = {row["field"]: row["id_prefix"] for row in allocations["pending_allocations"]}

    unaccounted = set(required_identity_fields) - allocated_fields - set(pending)
    assert (
        not unaccounted
    ), f"record schemas require identity fields that are neither allocated nor declared pending: {sorted(unaccounted)}"

    stale = set(pending) - set(required_identity_fields)
    assert not stale, f"pending_allocations lists fields no record schema requires: {sorted(stale)}"

    for field, prefix in pending.items():
        assert (
            prefix == required_identity_fields[field]
        ), f"{field} declared as {prefix}_ but the schema requires {required_identity_fields[field]}_"

    # Non-empty is the current, correct state. When W1 allocates the rest this fails, which is
    # the signal that the acceptance record can be authored — and this test is retired then.
    assert pending, "pending_allocations is empty: every required identity is allocated"


def test_identity_allocations_are_append_only_and_uniquely_revisioned():
    allocations = _load_yaml(IDENTITY_ALLOCATIONS_PATH)
    for block, id_field in (
        ("actor_allocations", "actor_id"),
        ("assurance_requirement_allocations", "assurance_requirement_id"),
    ):
        rows = allocations[block]
        assert rows, f"{block} is empty"
        ids = [row[id_field] for row in rows]
        assert len(set(ids)) == len(ids), f"duplicate allocated id in {block}"
        revisions = [(row["id_kind"], row["revision"]) for row in rows]
        assert len(set(revisions)) == len(revisions), f"duplicate (id_kind, revision) in {block}"

    kinds = _load_yaml(ROOT / ".research-system" / "config" / "id-kind-registry.yaml")["kinds"]
    for block, id_field in (
        ("actor_allocations", "actor_id"),
        ("assurance_requirement_allocations", "assurance_requirement_id"),
    ):
        for row in allocations[block]:
            assert row["id_kind"] in kinds, f"allocation names an unregistered kind: {row['id_kind']}"
            assert row[id_field].startswith(f"{kinds[row['id_kind']]}_")


def test_identity_allocations_bind_the_unmodified_accepted_contract():
    """The allocations derive authority from the owner-accepted contract at exact bytes."""
    allocations = _load_yaml(IDENTITY_ALLOCATIONS_PATH)
    subject = _repository_subject(CONTRACT_PATH)
    assert allocations["authorizing_contract_path"] == CONTRACT_PATH.relative_to(ROOT).as_posix()
    assert allocations["authorizing_contract_git_blob"] == subject["git_blob"]
    assert allocations["authorizing_contract_canonical_sha256"] == subject["canonical_sha256"]


# --------------------------------------------------------------------------------------
# Deliverable 2 — the semantic seam
# --------------------------------------------------------------------------------------


def test_loader_computes_the_subject_identity_from_the_raw_bytes_alone(contract, candidate):
    pack, raw = candidate
    subject = validate_tdl_private_pack_for_acceptance(**_loader_kwargs(pack, raw, contract))

    assert subject.pack_git_blob == git_blob_id(raw)
    assert subject.pack_raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert subject.assurance_pack_id == pack["assurance_pack_id"]
    assert subject.canonical_repository_path == pack["canonical_repository_path"]

    # Any byte change moves the subject, even one that leaves the parsed object identical.
    # The candidate names no identity of its own, so a comment-only edit is a different
    # subject and the records that bound the original no longer bind it.
    commented = b"# leading comment\n" + raw
    assert yaml.safe_load(commented.decode("utf-8")) == pack
    with pytest.raises(PackUnconsumable, match="binds a different subject"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, raw_candidate_pack_bytes=commented)
        )

    # Re-bound to records carrying the moved subject, it resolves — to a different subject.
    moved = validate_tdl_private_pack_for_acceptance(
        **_loader_kwargs(
            pack,
            commented,
            contract,
            raw_candidate_pack_bytes=commented,
            trusted_w1_w2_content_addressed_authority_resolver=_Resolver(_record_store(pack, commented, contract)),
        )
    )
    assert moved.pack_git_blob != subject.pack_git_blob
    assert moved.pack_raw_sha256 != subject.pack_raw_sha256


def test_loader_rejects_off_surface_candidate_bytes(contract, candidate):
    pack, raw = candidate
    for mutated in (raw.replace(b"\n", b"\r\n", 1), raw.rstrip(b"\n"), b"\xff" + raw):
        with pytest.raises(PackUnconsumable):
            validate_tdl_private_pack_for_acceptance(
                **_loader_kwargs(pack, raw, contract, raw_candidate_pack_bytes=mutated)
            )


def test_loader_rejects_a_stale_contract_or_schema_subject(contract, candidate):
    pack, raw = candidate
    stale_contract = _accepted_contract_subject() | {"canonical_sha256": "1" * 64}
    with pytest.raises(PackUnconsumable, match="upstream contract"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, accepted_upstream_contract_subject=stale_contract)
        )

    stale_schema = _accepted_schema_subject() | {"git_blob": "2" * 40}
    with pytest.raises(PackUnconsumable, match="pack schema"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, accepted_schema_subject=stale_schema)
        )


def test_loader_rejects_a_candidate_claiming_a_foreign_accepted_subject(contract, candidate):
    """A candidate that pins a different contract subject fails against the accepted one."""
    pack, _ = candidate
    swapped = deepcopy(pack)
    swapped["upstream_contract_reference"] = deepcopy(pack["schema_reference"]) | {
        "schema_id": "ars://contracts/wp6-3-tdl-private-assurance-pack",
        "repository_path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
    }
    raw = render_candidate_bytes(swapped)
    with pytest.raises(PackUnconsumable, match="upstream contract reference"):
        validate_tdl_private_pack_for_acceptance(**_loader_kwargs(swapped, raw, contract))


def test_loader_revalidates_every_reference_against_the_current_snapshot(contract, candidate):
    pack, raw = candidate
    reference_id = pack["references"]["contract_references"][0]["reference_id"]

    drifted = _reference_snapshot(pack)
    drifted[reference_id] = drifted[reference_id] | {"git_blob": "3" * 40}
    with pytest.raises(PackUnconsumable, match="identity drifted"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, current_exact_reference_snapshot=drifted)
        )

    deactivated = _reference_snapshot(pack)
    deactivated[reference_id] = deactivated[reference_id] | {"activation_state": "pending"}
    with pytest.raises(PackUnconsumable, match="activation changed"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, current_exact_reference_snapshot=deactivated)
        )

    ineligible = _reference_snapshot(pack)
    ineligible[reference_id] = ineligible[reference_id] | {"pack_acceptance_eligible": False}
    with pytest.raises(PackUnconsumable, match="not acceptance-eligible"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, current_exact_reference_snapshot=ineligible)
        )

    absent = {key: value for key, value in _reference_snapshot(pack).items() if key != reference_id}
    with pytest.raises(PackUnconsumable, match="does not resolve"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, current_exact_reference_snapshot=absent)
        )

    # The inverse direction: a reference active in the current snapshot that the candidate
    # never pinned. Without this the candidate could silently under-declare the governed set.
    widened = _reference_snapshot(pack) | {
        "contract/unpinned/added-after-authoring": {
            "git_blob": "6" * 40,
            "canonical_sha256": "6" * 64,
            "activation_state": "active",
            "pack_acceptance_eligible": True,
        }
    }
    with pytest.raises(PackUnconsumable, match="references the candidate omits"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, current_exact_reference_snapshot=widened)
        )


def test_loader_requires_every_declared_external_record_class(contract, candidate):
    pack, raw = candidate
    declared = contract["required_pack_contract"]["external_acceptance_evidence"]["required_record_types"]
    assert len(declared) == 11

    for record_class in declared:
        thinned = {k: v for k, v in _record_ids(contract, pack).items() if k != record_class}
        with pytest.raises(PackUnconsumable, match="no external record id supplied"):
            validate_tdl_private_pack_for_acceptance(
                **_loader_kwargs(pack, raw, contract, opaque_external_record_ids=thinned)
            )


def test_loader_resolves_every_record_at_every_declared_phase(contract, candidate):
    pack, raw = candidate
    resolver = _Resolver(_record_store(pack, raw, contract))
    validate_tdl_private_pack_for_acceptance(
        **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=resolver)
    )
    declared = contract["required_pack_contract"]["external_acceptance_evidence"]["required_record_types"]
    assert set(resolver.calls) == {(c, phase) for c in declared for phase in AUTHORITY_RESOLUTION_PHASES}
    assert tuple(AUTHORITY_RESOLUTION_PHASES) == tuple(
        contract["required_pack_contract"]["external_acceptance_evidence"]["authority_resolution_phases"]
    )


def test_loader_rejects_a_record_that_changes_between_phases(contract, candidate):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    revoked = store["active_authority_grant"] | {"grant_state": "revoked"}
    resolver = _Resolver(store, per_phase_override={("active_authority_grant", "consumption"): revoked})
    with pytest.raises(PackUnconsumable, match="unstable across authority phases"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=resolver)
        )


def test_loader_rejects_a_trusted_digest_that_does_not_match_the_linked_hash(contract, candidate):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    resolver = _Resolver(
        store,
        trusted_digests={"accepted_assurance_requirement": "4" * 64},
    )
    with pytest.raises(PackUnconsumable, match="accepted assurance requirement"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=resolver)
        )


def test_loader_rejects_a_trusted_revision_that_changes_between_phases(contract, candidate):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    record_id = _record_ids(contract, pack)["accepted_assurance_requirement"]
    body = store["accepted_assurance_requirement"]
    resolver = _Resolver(
        store,
        per_phase_resolution_override={
            ("accepted_assurance_requirement", "consumption"): ExternalRecordResolution(
                record_class="accepted_assurance_requirement",
                record_id=record_id,
                revision=2,
                canonical_sha256=PLACEHOLDER_REQUIREMENT_SHA256,
                record=body,
            )
        },
    )
    with pytest.raises(PackUnconsumable, match="unstable across authority phases"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=resolver)
        )


@pytest.mark.parametrize("invalid_revision", (True, False, 0, -1))
def test_loader_rejects_a_non_positive_or_boolean_trusted_revision(contract, candidate, invalid_revision):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    resolver = _Resolver(store, trusted_revisions={"canonical_actor": invalid_revision})

    with pytest.raises(PackUnconsumable, match="trusted identity is not exact: canonical_actor"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=resolver)
        )


def test_loader_rejects_inactive_foreign_or_mislabelled_records(contract, candidate):
    """Mutations are expressed in the fields the record's own schema defines.

    Foreign-root rejection is not testable here: no record schema defines ``authority_root``, so the
    binding is enforced at the resolution channel instead. Its control lives beside the resolver, in
    ``test_external_record_envelope_and_resolver.py``.
    """
    pack, raw = candidate
    mutations = {
        "grant_state": ("revoked", "not active"),
        "authority_grant_id": ("agr_00000000-0000-7000-8000-0000000000ff", "does not identify"),
        "record_type": ("canonical_actor", "does not identify"),
    }
    for field, (value, message) in mutations.items():
        store = _record_store(pack, raw, contract)
        store["active_authority_grant"] = store["active_authority_grant"] | {field: value}
        with pytest.raises(PackUnconsumable, match=message):
            validate_tdl_private_pack_for_acceptance(
                **_loader_kwargs(
                    pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store)
                )
            )


def test_loader_fails_closed_when_the_resolver_fails(contract, candidate):
    pack, raw = candidate

    class _Broken:
        def resolve(self, **_kwargs):
            raise RuntimeError("resolver offline")

    with pytest.raises(PackUnconsumable, match="trusted storage receipts"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Broken())
        )

    class _Raising:
        def resolve_with_receipt(self, **_kwargs):
            raise RuntimeError("resolver offline")

    with pytest.raises(PackUnconsumable, match="external record did not resolve at phase load"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Raising())
        )


def test_loader_binds_the_registered_object_and_accepted_requirement(contract, candidate):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    # The record's identity field *is* `assurance_pack_id`, so swapping it is caught earlier, as an
    # identity mismatch. Diverge on a non-identity binding field to reach the registered-object check.
    store["registered_pack_object"] = store["registered_pack_object"] | {"revision": 99}
    with pytest.raises(PackUnconsumable, match="W1-registered pack object"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )

    store = _record_store(pack, raw, contract)
    store["accepted_assurance_requirement"] = store["accepted_assurance_requirement"] | {"content_sha256": "4" * 64}
    with pytest.raises(PackUnconsumable, match="schema-forbidden content_sha256"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )

    store = _record_store(pack, raw, contract)
    store["accepted_assurance_requirement"] = store["accepted_assurance_requirement"] | {
        "prospective_producer_actor_id": "act_00000000-0000-7000-8000-0000000000fe"
    }
    with pytest.raises(PackUnconsumable, match="producer relationship is stale"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )


def test_producer_relationship_must_still_hold_at_the_evaluation_time(contract, candidate):
    """Actor equality is not the staleness rule.

    The accepted requirement pins a relationship record and an independence floor, and the relationship
    record carries its own validity window and grade. Each of these can go stale while every actor id
    still matches, which is exactly the case a producer-actor comparison waves through.
    """
    pack, raw = candidate
    # The relationship the requirement pins and the relationship the caller supplies an opaque id for are
    # bound at different points, so they can disagree. Mutate the requirement side: the record's own
    # `relationship_record_id` is its identity field, and swapping that is caught earlier as a mismatch.
    store = _record_store(pack, raw, contract)
    store["accepted_assurance_requirement"] = store["accepted_assurance_requirement"] | {
        "scope_relationship_record_id": "rel_00000000-0000-7000-8000-0000000000ff"
    }
    with pytest.raises(PackUnconsumable, match="not the relationship the requirement pins"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )

    mutations = (
        ({"object_actor_id": "act_00000000-0000-7000-8000-0000000000fd"}, "does not describe the candidate"),
        ({"expires_at": "2026-07-01T00:00:01Z"}, "not current at the evaluation time"),
        ({"effective_at": "2026-12-01T00:00:00Z"}, "not current at the evaluation time"),
        ({"grade": "I1"}, "no longer meets the accepted independence floor"),
        ({"grade": "unknown"}, "not a recognised independence grade"),
    )
    for mutation, message in mutations:
        store = _record_store(pack, raw, contract)
        store["producer_relationship_evidence"] = store["producer_relationship_evidence"] | mutation
        with pytest.raises(PackUnconsumable, match=message):
            validate_tdl_private_pack_for_acceptance(
                **_loader_kwargs(
                    pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store)
                )
            )


def test_a_stronger_producer_relationship_than_the_floor_is_accepted(contract, candidate):
    """The floor is a minimum, not an equality: I3 against an I2 floor must not block."""
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    store["producer_relationship_evidence"] = store["producer_relationship_evidence"] | {"grade": "I3"}
    validate_tdl_private_pack_for_acceptance(
        **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("missing", "independent pack review relationship_record_id is required"),
        ("foreign", "independent pack review does not bind the resolved producer relationship"),
        ("insufficient_grade", "does not meet the independent pack review floor"),
    ),
)
def test_independent_pack_review_requires_bound_sufficient_relationship_evidence(
    contract, candidate, mutation, message
):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    if mutation == "missing":
        store["independent_pack_review"].pop("relationship_record_id")
    elif mutation == "foreign":
        store["independent_pack_review"]["relationship_record_id"] = "rel_00000000-0000-7000-8000-0000000000ff"
    else:
        store["independent_pack_review"]["minimum_independence_grade"] = "I3"

    with pytest.raises(PackUnconsumable, match=message):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )


@pytest.mark.parametrize(
    "relationship_mutation",
    (
        {"subject_actor_id": "act_00000000-0000-7000-8000-0000000000fd"},
        {
            "subject_actor_id": lambda pack: pack["producer_actor_id"],
            "object_actor_id": PLACEHOLDER_SCOPE_REVIEWER_ACTOR_ID,
        },
        {"relationship_context": "requirement_scope_review"},
    ),
)
def test_independent_pack_review_requires_the_declared_actor_roles(contract, candidate, relationship_mutation):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    mutation = {key: value(pack) if callable(value) else value for key, value in relationship_mutation.items()}
    store["producer_relationship_evidence"] |= mutation

    with pytest.raises(PackUnconsumable, match="does not bind the declared reviewer and producer roles"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )


def test_loader_requires_review_and_owner_acceptance_to_bind_the_computed_subject(contract, candidate):
    pack, raw = candidate
    for record_class, label in (
        ("independent_pack_review", "independent pack review"),
        ("stephen_owner_acceptance", "owner acceptance"),
    ):
        store = _record_store(pack, raw, contract)
        store[record_class] = store[record_class] | {
            "subject": store[record_class]["subject"] | {"pack_raw_sha256": "5" * 64}
        }
        with pytest.raises(PackUnconsumable, match=label):
            validate_tdl_private_pack_for_acceptance(
                **_loader_kwargs(
                    pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store)
                )
            )

    store = _record_store(pack, raw, contract)
    store["stephen_owner_acceptance"] = store["stephen_owner_acceptance"] | {"review_record_id": "rec_elsewhere"}
    with pytest.raises(PackUnconsumable, match="does not bind the resolved independent pack review"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )


def test_loader_requires_owner_acceptance_to_follow_the_independent_review(contract, candidate):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    store["stephen_owner_acceptance"] = store["stephen_owner_acceptance"] | {"decided_at": "2026-07-28T09:30:00Z"}
    with pytest.raises(PackUnconsumable, match="must follow the independent review"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )

    # Order is checked against the declared temporal order, not a literal here.
    declared = contract["required_pack_contract"]["external_acceptance_evidence"]["required_temporal_order"]
    assert declared.index("independent_reviewed") < declared.index("owner_accepted")


def test_loader_fails_closed_on_inverted_or_expired_currency(contract, candidate):
    pack, _ = candidate

    inverted = deepcopy(pack)
    inverted["currency"] = inverted["currency"] | {"expires_at": inverted["currency"]["effective_at"]}
    raw_inverted = render_candidate_bytes(inverted)
    with pytest.raises(PackUnconsumable, match="currency time order"):
        validate_tdl_private_pack_for_acceptance(**_loader_kwargs(inverted, raw_inverted, contract))

    _, raw = candidate
    expired_at = EVALUATION_TIME + timedelta(days=400)
    with pytest.raises(PackUnconsumable, match="not current at the evaluation time"):
        validate_tdl_private_pack_for_acceptance(**_loader_kwargs(pack, raw, contract, evaluation_time=expired_at))


def test_closure_permits_a_retired_task_local_name_but_not_a_missing_durable_control():
    """Negative controls for the amended `_assert_test_surface_closure` semantics.

    The contract's declared constant is
    `every_defined_test_function_is_declared_durable_or_task_local` — defined SUBSET-OF
    declared. The equality assertion was stricter than that, which froze a task-local
    scope marker permanently once the contract was accepted at exact bytes. The amended
    check enforces the two real guarantees separately.

    Written before the amendment and observed to fail against the equality version.
    """
    bindings = {
        "durable_test_functions": ["test_durable_one", "test_durable_two"],
        "task_local_unbound_test_functions": ["test_task_local"],
        "binding_closure": "every_defined_test_function_is_declared_durable_or_task_local",
    }
    everything = {"test_durable_one", "test_durable_two", "test_task_local"}

    # All present: passes.
    _assert_test_surface_closure(bindings, defined_names=everything)

    # A task-local name whose task has ended is absent: permitted. This is the whole
    # meaning of task-local, and the case the equality assertion made impossible.
    _assert_test_surface_closure(bindings, defined_names=everything - {"test_task_local"})

    # A durable control silently deleted: still fails closed.
    with pytest.raises(AssertionError, match="declared durable control is missing"):
        _assert_test_surface_closure(bindings, defined_names=everything - {"test_durable_two"})

    # A test defined but never declared: still fails closed.
    with pytest.raises(AssertionError, match="undeclared test functions"):
        _assert_test_surface_closure(bindings, defined_names=everything | {"test_undeclared"})

    # A name declared in both lists at once remains a contradiction.
    overlapping = bindings | {"task_local_unbound_test_functions": ["test_durable_one"]}
    with pytest.raises(AssertionError):
        _assert_test_surface_closure(overlapping, defined_names=everything)


def test_missing_contract_or_record_keys_fail_closed_rather_than_raising_keyerror():
    """`PackUnconsumable` is documented as the only failure mode; a bare KeyError breaks that.

    These guards are not reachable through the entry point against the currently accepted
    contract — its bytes are pinned by hash, so the keys are always present. They become
    reachable across a contract revision, which the contract itself provides for
    (`supersession_is_immutable`, `durable_states` including `superseded`). Tested directly
    on the helper for that reason, rather than by feeding the entry point a contract it
    would reject earlier for the wrong reason.
    """
    assert _require_key({"present": 1}, "present", "label") == 1

    with pytest.raises(PackUnconsumable, match="does not declare absent"):
        _require_key({"present": 1}, "absent", "upstream contract")
    for not_a_mapping in (None, [], "text", 7):
        with pytest.raises(PackUnconsumable, match="is not a mapping"):
            _require_key(not_a_mapping, "any", "resolved external records")


def test_loader_requires_a_timezone_aware_evaluation_time(contract, candidate):
    pack, raw = candidate
    with pytest.raises(PackUnconsumable, match="timezone"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, evaluation_time=datetime(2026, 7, 28, 12))
        )


# --------------------------------------------------------------------------------------
# Deliverable 3 — the two carried-forward enforcement-layer defects
# --------------------------------------------------------------------------------------


def test_required_distinct_pairs_floor_is_bound_by_a_test_not_by_the_schema(contract):
    """The schema's `minItems: 7` is a floor, not the eleven the contract declares.

    A comment in the contract test module claimed the schema pinned the list to eleven
    pairs. It does not — it sets `minItems: 7` with no `maxItems`, so four of the eleven
    separations could be dropped with no schema signal. All eleven are load-bearing: each
    is consumed by the runtime distinct-pair loop. The accepted schema bytes are frozen,
    so the count is bound here instead.
    """
    pairs = contract["required_pack_contract"]["external_acceptance_evidence"]["required_distinct_pairs"]
    schema = _load_json(EXTERNAL_RECORD_SCHEMA_PATH)
    declared_floor = schema["$defs"]["externalAcceptanceEvidence"]["properties"]["required_distinct_pairs"]

    assert declared_floor["minItems"] == 7
    assert "maxItems" not in declared_floor
    assert len(pairs) == 11, "all eleven separations are load-bearing; the schema does not enforce the count"
    assert len({tuple(pair) for pair in pairs}) == 11


def test_two_key_status_fields_are_owned_by_the_external_record_schema():
    """Watched negative for the status disjuncts removed from the runtime validator.

    `key_a_status`, `key_b_status`, `forbidden_state_or_claim`, and the boundary-fixture
    outcome fields are `const` in the external-record schema, which validates every
    resolved record before the runtime check sees it. Runtime branches on them could never
    fire, so they could never be given a watched negative. This is that negative, at the
    layer that actually owns the constraint.
    """
    schema = _load_json(EXTERNAL_RECORD_SCHEMA_PATH)
    evidence_row = schema["$defs"]["obligationEvidenceRow"]["properties"]
    fixture_row = schema["$defs"]["boundaryFixtureExecutionRow"]["properties"]

    assert evidence_row["key_a_status"]["const"] == "passed"
    assert evidence_row["key_b_status"]["const"] == "passed"
    assert evidence_row["forbidden_state_or_claim"]["const"] == "absent"
    assert fixture_row["execution_status"]["const"] == "executed"
    assert fixture_row["expected_outcome"]["const"] == "blocked"
    assert fixture_row["observed_outcome"]["const"] == "blocked"
    assert fixture_row["key_a_status"]["const"] == "passed"
    assert fixture_row["key_b_status"]["const"] == "passed"

    # The evidence-id emptiness branches were unreachable for the same reason.
    non_empty = schema["$defs"]["nonEmptyStrings"]
    assert non_empty["minItems"] == 1
    assert evidence_row["key_a_evidence_ids"]["$ref"].endswith("nonEmptyStrings")
    assert evidence_row["key_b_evidence_ids"]["$ref"].endswith("nonEmptyStrings")
