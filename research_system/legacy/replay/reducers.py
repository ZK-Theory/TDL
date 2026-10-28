"""W9 legacy reducers and their invariants (06v WP9.2; design note §7.4).

Each reducer takes the mutable legacy projection, the transaction's row and events, and either applies them or raises
:class:`IntegrityError`. The invariants are 06v's:

- only the W9 §8.2 ownership transitions, and never ``successor_owned → legacy_owned`` (W9-T5);
- supersession is acyclic;
- no cycle among paper roots, mappings, transitions and recovery Decisions, and a recovery Decision never names its
  recovery root (W9-T21, reducer half);
- a restricted-kind source never carries a frozen-copy ref (W9-T11, store half).

Every record a Decision resolves is bound to its proposal under catalogue precondition G5: the same pre-assigned ID,
the exact content, and the resolving Decision's ID.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from copy import deepcopy
from typing import Any

from research_system.errors import IntegrityError
from research_system.legacy.accepted_w9 import CATALOGUE_STREAM_ID, RESERVED_IDS, accepted_genesis_payload
from research_system.legacy.routes import LEGACY_ROW_ROUTES, record_kind

OWNERSHIP_TRANSITIONS = frozenset(
    {
        ("legacy_owned", "successor_owned"),
        ("legacy_owned", "closed_reference"),
        ("successor_owned", "closed_reference"),
    }
)
# The direction each ownership row admits; LR-020 closes whole-file legacy items on acceptance (P-072 item 2).
_ROW_DIRECTIONS = {
    "LR-020": ("legacy_owned", "closed_reference"),
    "LR-054": ("legacy_owned", "successor_owned"),
    "LR-055": ("successor_owned", "closed_reference"),
}
# The field of each recorded kind that names the Decision resolving it.
_DECISION_FIELDS = {
    "legacy_path_registration": "registration_decision_ref",
    "legacy_field_family_membership": "acceptance_decision_ref",
}
RESTRICTED_SUFFIXES = (".csv", ".pkl")
_PAPER_ROOT_RECOVERY_ROW = "LR-037"
# W9-T21 names recovery Decisions only: other Decisions are graph targets, never sources (design note §7.4).
_RECOVERY_DECISION_FAMILY = "legacy_paper_root_recovery"
# LR-014 (re-review M-1): the inventory's reproduction review is answered under LR-013, and only approval is positive.
_REPRODUCTION_VERDICT_ROW = "LR-013"
_POSITIVE_REPRODUCTION_VERDICTS = frozenset({"approve"})


def new_legacy_state() -> dict[str, Any]:
    """Return an empty legacy projection."""

    return {
        "catalogue": None,
        "catalogue_revisions": [],
        "identities": {},
        "reserved_ids": [],
        "proposals": {},
        "records": {},
        "reviews": {},
        "decisions": {},
        "ownership": {},
        "supersessions": {},
        "reference_edges": {},
        "row_counts": {},
    }


def ownership_transition_allowed(from_mode: Any, to_mode: Any) -> bool:
    """Return whether a W9 §8.2 ownership transition is allowed. ``successor_owned → legacy_owned`` never is."""

    return (from_mode, to_mode) in OWNERSHIP_TRANSITIONS


def _restricted_path(value: Any) -> bool:
    return isinstance(value, str) and value.lower().endswith(RESTRICTED_SUFFIXES)


def _source_identities(node: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(node, Mapping):
        if "identity_kind" in node:
            yield node
        for value in node.values():
            yield from _source_identities(value)
    elif isinstance(node, list):
        for value in node:
            yield from _source_identities(value)


def refuse_restricted_frozen_copy(record: Mapping[str, Any]) -> None:
    """W9-T11, store half: a restricted-kind source never carries a frozen-copy ref.

    The schemas close ``restricted_untracked_file`` and refuse restricted suffixes elsewhere; this repeats the rule at
    the store so that a record reaching the reducer by any path is refused too.

    Raises:
        IntegrityError: If any source identity in the record is restricted and carries ``frozen_copy_ref``.
    """

    for identity in _source_identities(record):
        restricted = identity.get("identity_kind") == "restricted_untracked_file" or any(
            _restricted_path(identity.get(key)) for key in ("path", "repository_path", "vault_path")
        )
        if restricted and "frozen_copy_ref" in identity:
            raise IntegrityError("W9 restricted source carries a frozen-copy ref")


def _ref_ids(node: Any) -> Iterator[str]:
    """Yield every ``id`` of a nested ref object."""

    if isinstance(node, Mapping):
        identity = node.get("id")
        if isinstance(identity, str) and {"record_revision", "content_hash"} <= set(node):
            yield identity
        for value in node.values():
            yield from _ref_ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from _ref_ids(value)


def _add_edges(state: dict[str, Any], source: str, targets: Sequence[str]) -> None:
    """Add reference edges and refuse any self-reference or cycle (W9-T21, reducer half)."""

    edges: dict[str, list[str]] = state["reference_edges"]
    if source in targets:
        raise IntegrityError("W9 record references itself")
    # The graph is acyclic before this call, so the new edges close a cycle exactly when a target reaches the source.
    # The walk is iterative and visits each node once, so a long reference chain cannot exhaust the stack (review F-9).
    seen: set[str] = set()
    pending = list(targets)
    while pending:
        node = pending.pop()
        if node == source:
            raise IntegrityError("W9 reference cycle among roots, mappings, transitions and Decisions")
        if node not in seen:
            seen.add(node)
            pending.extend(edges.get(node, ()))
    edges[source] = sorted({*edges.get(source, []), *targets})


def claim_identity(state: dict[str, Any], identity: Any, kind: str) -> None:
    """W9-C25: claim one pre-assigned W9 identity, refusing the reserved external refs and any collision."""

    if not isinstance(identity, str) or not identity:
        raise IntegrityError("W9 identity is invalid")
    if identity in RESERVED_IDS:
        raise IntegrityError("W9 identity is reserved for an external ref")
    if identity in state["identities"] or identity == CATALOGUE_STREAM_ID:
        raise IntegrityError("W9 identity collision")
    state["identities"][identity] = kind


def _single(transaction: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return transaction[0]["payload"]


def reduce_genesis(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """LR-001: import the accepted W9 catalogue once, after W11 genesis, and reserve the external refs."""

    event = transaction[0]
    if state["catalogue"] is not None:
        raise IntegrityError("second W9 genesis")
    if not context.get("w11_genesis_seen"):
        raise IntegrityError("W9 genesis requires a prior W11 genesis")
    if event.get("stream_id") != CATALOGUE_STREAM_ID or event.get("stream_version") != 1:
        raise IntegrityError("W9 genesis stream identity mismatch")
    if event.get("payload") != accepted_genesis_payload():
        raise IntegrityError("W9 genesis payload differs from the accepted identity")
    for identity in sorted(RESERVED_IDS):
        if identity in state["identities"]:
            raise IntegrityError("W9 reserved identity already claimed")
        state["identities"][identity] = "reserved_external_ref"
    state["reserved_ids"] = sorted(RESERVED_IDS)
    state["catalogue"] = deepcopy(event["payload"])


def reduce_revision(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """LR-002: import an accepted catalogue revision. Inert in v1: no accepted revision exists (P-071 item 4)."""

    payload = _single(transaction)
    accepted = context.get("accepted_revisions", ())
    if payload not in accepted:
        raise IntegrityError("W9 catalogue revision is not an accepted revision")
    if transaction[0].get("stream_id") != CATALOGUE_STREAM_ID:
        raise IntegrityError("W9 catalogue revision stream identity mismatch")
    if payload in state["catalogue_revisions"]:
        raise IntegrityError("W9 catalogue revision already imported")
    state["catalogue_revisions"].append(deepcopy(payload))


def reduce_proposal(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``ProposeLegacyRecord``: open a proposal under its pre-assigned record ID."""

    record = _single(transaction)
    refuse_restricted_frozen_copy(record)
    claim_identity(state, record.get("record_id"), "proposal")
    state["proposals"][record["record_id"]] = {
        "row": row_id,
        "kind": record_kind(record.get("schema_id")),
        "record": deepcopy(record),
        "recorded": False,
    }


def reduce_review_request(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``RequestW9AuthorityReview``: open a W9 review under its pre-assigned review ID."""

    payload = _single(transaction)
    review_id = payload.get("new_review_id")
    claim_identity(state, review_id, "review")
    state["reviews"][review_id] = {
        "request_row": row_id,
        "subjects": list(zip(payload.get("subject_ids", []), payload.get("subject_hashes", []), strict=False)),
        "verdict_row": None,
        "verdict": None,
    }


def reduce_review_verdict(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``RecordW9AuthorityReview``: record the one verdict on an open W9 review."""

    payload = _single(transaction)
    review = state["reviews"].get(payload.get("review_id"))
    if review is None or review["verdict_row"] is not None:
        raise IntegrityError("W9 review verdict has no open W9 review")
    review["verdict_row"] = row_id
    review["verdict"] = payload.get("verdict")


def reduce_decision_proposal(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``ProposeW9AuthorityDecision``: open a Decision under its pre-assigned ID (W9-C25 refuses the reserved one)."""

    payload = _single(transaction)
    decision_id = payload.get("new_decision_id")
    claim_identity(state, decision_id, "decision")
    state["decisions"][decision_id] = {
        "propose_row": row_id,
        "resolve_row": None,
        "governing_evidence_refs": list(payload.get("governing_evidence_refs", [])),
    }


def _decision_family(row_id: str) -> str:
    return LEGACY_ROW_ROUTES[row_id].payload_discriminant.split("/", 2)[1]


def _record_resolved(state: dict[str, Any], row_id: str, decision_id: str, record: Mapping[str, Any]) -> str:
    """G5: bind a resolved record to its open proposal and to the resolving Decision.

    LR-020's ownership transitions are the exception: the acceptance writes one per accepted whole-file item, with no
    proposal of their own (P-072 item 2), so each claims its own identity.
    """

    record_id = record.get("record_id")
    kind = record_kind(record.get("schema_id"))
    decision_ref = record.get(_DECISION_FIELDS.get(kind, "decision_ref"))
    if not isinstance(decision_ref, Mapping) or decision_ref.get("id") != decision_id:
        raise IntegrityError("W9 resolved record names another Decision")
    if row_id == "LR-020" and kind == "legacy_ownership_transitioned":
        claim_identity(state, record_id, kind)
        state["records"].setdefault(kind, {})[record_id] = deepcopy(record)
        return str(record_id)
    proposal = state["proposals"].get(record_id)
    if proposal is None or proposal["recorded"] or proposal["kind"] != kind or proposal["record"] != record:
        raise IntegrityError("W9 resolved record differs from its open proposal")
    proposal["recorded"] = True
    state["records"].setdefault(kind, {})[record_id] = deepcopy(record)
    return str(record_id)


def _apply_ownership(state: dict[str, Any], row_id: str, record: Mapping[str, Any]) -> None:
    """W9-T5: apply one ownership transition from the registration's current mode."""

    subject = record.get("subject_registration_ref")
    subject_id = subject.get("id") if isinstance(subject, Mapping) else None
    registration = state["records"].get("legacy_path_registration", {}).get(subject_id)
    if registration is None:
        raise IntegrityError("W9 ownership transition names no recorded registration")
    current = state["ownership"].get(subject_id, registration.get("ownership_mode"))
    from_mode, to_mode = record.get("from_mode"), record.get("to_mode")
    if from_mode != current or not ownership_transition_allowed(from_mode, to_mode):
        raise IntegrityError("W9 ownership transition is not allowed from the registration's current mode")
    if _ROW_DIRECTIONS.get(row_id, (from_mode, to_mode)) != (from_mode, to_mode):
        raise IntegrityError(f"W9 ownership transition differs from accepted {row_id}")
    state["ownership"][subject_id] = to_mode


def _apply_supersession(state: dict[str, Any], record: Mapping[str, Any]) -> None:
    """Supersession is acyclic: a record superseded once, by another record, with no chain back to itself."""

    superseded = record.get("superseded_ref", {}).get("id")
    replacing = record.get("replacing_ref", {}).get("id")
    chain: dict[str, str] = state["supersessions"]
    if superseded == replacing or superseded in chain:
        raise IntegrityError("W9 supersession is invalid")
    cursor = replacing
    while cursor in chain:
        cursor = chain[cursor]
        if cursor == superseded:
            raise IntegrityError("W9 supersession cycle")
    chain[superseded] = replacing


def reduce_decision_resolution(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``ResolveW9AuthorityDecision``: resolve one open Decision and record what it governs."""

    payload = _single(transaction)
    decision_id = payload.get("decision_id")
    decision = state["decisions"].get(decision_id)
    if decision is None or decision["resolve_row"] is not None:
        raise IntegrityError("W9 Decision resolution has no open W9 Decision")
    if _decision_family(decision["propose_row"]) != _decision_family(row_id):
        raise IntegrityError("W9 Decision is resolved under another Decision family")
    decision["resolve_row"] = row_id
    if _decision_family(row_id) == _RECOVERY_DECISION_FAMILY:
        _add_edges(state, decision_id, [ref for ref in decision["governing_evidence_refs"] if ref.startswith("obj_")])
    for event in transaction[1:]:
        record = event["payload"]
        record_id = _record_resolved(state, row_id, decision_id, record)
        kind = record_kind(record.get("schema_id"))
        refuse_restricted_frozen_copy(record)
        if kind == "legacy_ownership_transitioned":
            _apply_ownership(state, row_id, record)
        elif kind == "legacy_record_supersession":
            _apply_supersession(state, record)
        if kind in {"legacy_ownership_transitioned", "legacy_transition_mapping"}:
            _add_edges(state, record_id, list(_ref_ids(record)))


def reduce_light_inventory(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """LR-014: record a proposed light inventory once its reproduction review approved it (re-review M-1).

    The record is the open LR-011 proposal's exact bytes under the proposal's pre-assigned ID, which LR-011 already
    claimed, so no identity is claimed here. Its ``independent_reproduction_ref`` names a W9 review of that proposal, on
    the proposal's content hash, answered with approval under LR-013.
    """

    record = _single(transaction)
    refuse_restricted_frozen_copy(record)
    record_id = record.get("record_id")
    proposal = state["proposals"].get(record_id)
    if (
        proposal is None
        or proposal["recorded"]
        or proposal["kind"] != "legacy_light_inventory"
        or proposal["record"] != record
    ):
        raise IntegrityError("W9 light inventory differs from its open proposal")
    reproduction = record.get("independent_reproduction_ref")
    review = state["reviews"].get(reproduction.get("id") if isinstance(reproduction, Mapping) else None)
    if (
        review is None
        or review["verdict_row"] != _REPRODUCTION_VERDICT_ROW
        or review["verdict"] not in _POSITIVE_REPRODUCTION_VERDICTS
        or (record_id, record.get("content_hash")) not in review["subjects"]
    ):
        raise IntegrityError("W9 light inventory has no approved reproduction review of its proposal")
    proposal["recorded"] = True
    state["records"].setdefault("legacy_light_inventory", {})[record_id] = deepcopy(record)


def reduce_record(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """Record-writing rows with no Decision or proposal: observation, paper root, citation status and use mismatch."""

    record = _single(transaction)
    refuse_restricted_frozen_copy(record)
    kind = record_kind(record.get("schema_id"))
    record_id = record.get("record_id")
    claim_identity(state, record_id, kind)
    if kind == "legacy_paper_root":
        recovery = record.get("recovery")
        if recovery is not None:
            predecessor_id = recovery.get("predecessor_root_ref", {}).get("id")
            decision_id = recovery.get("recovery_decision_ref", {}).get("id")
            decision = state["decisions"].get(decision_id)
            if predecessor_id not in state["records"].get("legacy_paper_root", {}):
                raise IntegrityError("W9 recovery root names no recorded predecessor root")
            if decision is None or decision["resolve_row"] != _PAPER_ROOT_RECOVERY_ROW:
                raise IntegrityError("W9 recovery root names no resolved recovery Decision")
            if f"{record_id}" in decision["governing_evidence_refs"]:
                raise IntegrityError("W9 recovery Decision names its recovery root")
        _add_edges(state, str(record_id), list(_ref_ids(record)))
    state["records"].setdefault(kind, {})[record_id] = deepcopy(record)


REDUCERS: dict[str, Callable[[dict[str, Any], str, Sequence[Mapping[str, Any]], Mapping[str, Any]], None]] = {
    "ImportAcceptedW9CatalogueGenesis": reduce_genesis,
    "ImportAcceptedW9CatalogueRevision": reduce_revision,
    "ProposeLegacyRecord": reduce_proposal,
    "RequestW9AuthorityReview": reduce_review_request,
    "RecordW9AuthorityReview": reduce_review_verdict,
    "ProposeW9AuthorityDecision": reduce_decision_proposal,
    "ResolveW9AuthorityDecision": reduce_decision_resolution,
    "RecordLegacyLightInventory": reduce_light_inventory,
    "ObserveLegacyRecord": reduce_record,
    "CreateLegacyPaperRoot": reduce_record,
    "RecordPaperCitationStatus": reduce_record,
    "RecordAdoptionUseMismatch": reduce_record,
}
