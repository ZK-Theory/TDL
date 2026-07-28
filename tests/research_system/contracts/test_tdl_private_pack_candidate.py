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
from research_system.errors import SchemaError
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
CONTRACT_PATH = ROOT / ".research-system" / "contracts" / "wp6-3-tdl-private-assurance-pack.yaml"
PACK_SCHEMA_PATH = SCHEMAS / "assurance" / "assurance-pack.schema.json"
EXTERNAL_RECORD_SCHEMA_PATH = SCHEMAS / "contracts" / "wp6-3-tdl-private-assurance-pack.schema.json"
ALLOCATIONS_PATH = ROOT / ".research-system" / "config" / "assurance-pack-object-allocations.yaml"
PACK_SCHEMA_ID = "ars://assurance/packs/tdl-private/1.0"

EVALUATION_TIME = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)

# The four external identities the candidate must carry are allocated by W1 authority in
# external records, exactly as `assurance_pack_id` was. No canonical actor record and no
# accepted assurance requirement exists at this base, so these are placeholders, and
# `test_external_identity_prerequisites_are_still_unallocated` fails the moment real ones
# land — turning a silent absence into a loud one.
PLACEHOLDER_PRODUCER_ACTOR_ID = "act_00000000-0000-7000-8000-000000000000"
PLACEHOLDER_ASSURANCE_REQUIREMENT_ID = "asr_00000000-0000-7000-8000-000000000000"
PLACEHOLDER_REQUIREMENT_RECORD_ID = "ard_00000000-0000-7000-8000-000000000000"
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
        "producer_actor_id": PLACEHOLDER_PRODUCER_ACTOR_ID,
        "upstream_contract_reference": _accepted_contract_subject(),
        "schema_reference": _accepted_schema_subject(),
        "assurance_requirement_reference": {
            "assurance_requirement_id": PLACEHOLDER_ASSURANCE_REQUIREMENT_ID,
            "revision": 1,
            "acceptance_record_id": PLACEHOLDER_REQUIREMENT_RECORD_ID,
            "acceptance_record_sha256": PLACEHOLDER_REQUIREMENT_SHA256,
            "prospective_producer_actor_id": PLACEHOLDER_PRODUCER_ACTOR_ID,
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


def _record_ids(contract: dict) -> dict[str, str]:
    classes = contract["required_pack_contract"]["external_acceptance_evidence"]["required_record_types"]
    return {record_class: f"rec_{record_class}" for record_class in classes}


def _record_store(pack: dict, raw: bytes, contract: dict) -> dict[str, dict]:
    """Build a complete, internally consistent external record store for the loader."""
    ids = _record_ids(contract)
    subject = _subject_block(raw, pack)
    requirement_reference = pack["assurance_requirement_reference"]
    store = {
        record_class: {
            "record_id": record_id,
            "record_type": record_class,
            "authority_root": AUTHORITY_ROOT,
            "lifecycle_state": "active",
        }
        for record_class, record_id in ids.items()
    }
    store["registered_pack_object"] |= {
        "assurance_pack_id": pack["assurance_pack_id"],
        "assurance_pack_revision": pack["assurance_pack_revision"],
        "canonical_repository_path": pack["canonical_repository_path"],
    }
    store["accepted_assurance_requirement"] |= {
        "assurance_requirement_id": requirement_reference["assurance_requirement_id"],
        "revision": requirement_reference["revision"],
        "content_sha256": requirement_reference["acceptance_record_sha256"],
        "prospective_producer_actor_id": pack["producer_actor_id"],
    }
    store["independent_pack_review"] |= {"subject": subject, "decided_at": "2026-07-28T10:00:00Z"}
    store["stephen_owner_acceptance"] |= {
        "subject": subject,
        "decided_at": "2026-07-28T11:00:00Z",
        "review_record_id": ids["independent_pack_review"],
    }
    return store


class _Resolver:
    """Trusted resolver stub. Records every (record_class, phase) it was asked for."""

    def __init__(self, store: dict[str, dict], *, per_phase_override: dict | None = None) -> None:
        self.store = store
        self.per_phase_override = per_phase_override or {}
        self.calls: list[tuple[str, str]] = []

    def resolve(self, *, record_id: str, record_class: str, authority_root: str, phase: str) -> dict:
        self.calls.append((record_class, phase))
        if (record_class, phase) in self.per_phase_override:
            return self.per_phase_override[(record_class, phase)]
        if record_class not in self.store:
            raise KeyError(record_class)
        return self.store[record_class]


def _loader_kwargs(pack: dict, raw: bytes, contract: dict, **overrides) -> dict:
    kwargs = {
        "accepted_upstream_contract_subject": _accepted_contract_subject(),
        "accepted_schema_subject": _accepted_schema_subject(),
        "trusted_w1_w2_content_addressed_authority_resolver": _Resolver(_record_store(pack, raw, contract)),
        "independently_supplied_authority_root": AUTHORITY_ROOT,
        "opaque_external_record_ids": _record_ids(contract),
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


def test_external_identity_prerequisites_are_still_unallocated(candidate):
    """Fail loudly once the missing W1 allocations land, instead of shipping placeholders.

    The candidate needs four external identities — a canonical producer actor and the
    accepted assurance requirement's id, acceptance record id, and content hash. The
    contract's `required_temporal_order` puts `requirement_accepted` before
    `candidate_authored`, but no such record exists at this base and the producer may not
    mint one. This test pins the placeholders so their replacement is a deliberate,
    visible edit rather than a silent one.
    """
    pack, _ = candidate
    reference = pack["assurance_requirement_reference"]
    assert pack["producer_actor_id"] == PLACEHOLDER_PRODUCER_ACTOR_ID
    assert reference["assurance_requirement_id"] == PLACEHOLDER_ASSURANCE_REQUIREMENT_ID
    assert reference["acceptance_record_id"] == PLACEHOLDER_REQUIREMENT_RECORD_ID
    assert reference["acceptance_record_sha256"] == PLACEHOLDER_REQUIREMENT_SHA256

    allocated_kinds = {row["id_kind"] for row in _load_yaml(ALLOCATIONS_PATH)["allocations"]}
    assert "canonical_actor" not in allocated_kinds
    assert "assurance_requirement" not in allocated_kinds


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


def test_loader_requires_every_declared_external_record_class(contract, candidate):
    pack, raw = candidate
    declared = contract["required_pack_contract"]["external_acceptance_evidence"]["required_record_types"]
    assert len(declared) == 11

    for record_class in declared:
        thinned = {k: v for k, v in _record_ids(contract).items() if k != record_class}
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
    revoked = store["active_authority_grant"] | {"lifecycle_state": "revoked"}
    resolver = _Resolver(store, per_phase_override={("active_authority_grant", "consumption"): revoked})
    with pytest.raises(PackUnconsumable, match="unstable across authority phases"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=resolver)
        )


def test_loader_rejects_inactive_foreign_or_mislabelled_records(contract, candidate):
    pack, raw = candidate
    mutations = {
        "lifecycle_state": ("superseded", "not active"),
        "authority_root": ("some-other-root", "foreign authority root"),
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

    with pytest.raises(PackUnconsumable, match="did not resolve"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Broken())
        )


def test_loader_binds_the_registered_object_and_accepted_requirement(contract, candidate):
    pack, raw = candidate
    store = _record_store(pack, raw, contract)
    store["registered_pack_object"] = store["registered_pack_object"] | {
        "assurance_pack_id": "asp_00000000-0000-7000-8000-0000000000ff"
    }
    with pytest.raises(PackUnconsumable, match="W1-registered pack object"):
        validate_tdl_private_pack_for_acceptance(
            **_loader_kwargs(pack, raw, contract, trusted_w1_w2_content_addressed_authority_resolver=_Resolver(store))
        )

    store = _record_store(pack, raw, contract)
    store["accepted_assurance_requirement"] = store["accepted_assurance_requirement"] | {"content_sha256": "4" * 64}
    with pytest.raises(PackUnconsumable, match="accepted assurance requirement"):
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
    expired_at = _load_yaml(CONTRACT_PATH) and EVALUATION_TIME + timedelta(days=400)
    with pytest.raises(PackUnconsumable, match="not current at the evaluation time"):
        validate_tdl_private_pack_for_acceptance(**_loader_kwargs(pack, raw, contract, evaluation_time=expired_at))


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
