"""W9 legacy reducers and their invariants (06v WP9.2; WP9.2 note §7.4; WP9.3 note §4 to §9, §14).

Each reducer takes the mutable legacy projection, the transaction's row and events, and a context, and either applies
them or raises :class:`IntegrityError`. The invariants are 06v's:

- only the W9 §8.2 ownership transitions, and never ``successor_owned → legacy_owned`` (W9-T5);
- supersession is acyclic, and supersedes only a recorded record (WP9.3 note §3 row 5);
- no cycle among paper roots, mappings, transitions and recovery Decisions, and a recovery Decision never names its
  recovery root (W9-T21, reducer half);
- a restricted-kind source never carries a frozen-copy ref (W9-T11, store half).

Every record's ``content_hash`` is recomputed before any comparison (WP9.3 note §4.1, N-2), and every W9 identity
claim is refused when a non-W9 event takes the same ID, or when it is a pinned W0 signature ref (§4.3, §9.1).

WP9.3-1 routes LR-003 to LR-015. For those rows replay checks everything the ledger determines (note §6): the W2
payload encodings of §5.2, the pre-assigned ref hashes and reservations of §4.2 and §4.3, the lapse rule of §4.6,
approve-only satisfaction (§5.4), the distinctness rules of §5.5, G5 at every resolution (§6.1) and the row table of
§6.2. The rows of later packages keep WP9.2's reducer rules, plus the cross-cutting ones above; their packages add
theirs.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from research_system.errors import IntegrityError
from research_system.legacy.accepted_w9 import CATALOGUE_STREAM_ID, RESERVED_IDS, accepted_genesis_payload
from research_system.legacy.identities import pinned_signature_ids
from research_system.legacy.records import (
    observation_record_id,
    observation_subject_digest,
    pre_assigned_ref_hash,
    record_content_hash,
    require_content_hash,
    review_attempt_id,
    review_context_manifest_id,
)
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

# --- WP9.3-1 (note §2.3): the rows whose full replay checks this module makes. ---------------------------------------
WP9_3_1_ROWS = frozenset(f"LR-{number:03d}" for number in range(3, 16))
# The pre-assigned refs each proposal kind carries (§4.2), with the ref kind.
PRE_ASSIGNED_REFS: Mapping[str, Mapping[str, str]] = {
    "legacy_path_registration": {"registration_decision_ref": "decision"},
    "legacy_field_family_membership": {"review_ref": "review", "acceptance_decision_ref": "decision"},
    "legacy_light_inventory": {"independent_reproduction_ref": "review"},
}
# The review a WP9.3-1 request row opens, by the pre-assigned field that names it.
_REQUEST_REVIEW_FIELD = {"LR-007": "review_ref", "LR-012": "independent_reproduction_ref"}
_DECISION_PROPOSAL_FIELD = {"LR-004": "registration_decision_ref", "LR-009": "acceptance_decision_ref"}
# The review a Decision family requires satisfied (§6.1), by the record field that names it. A path registration has
# none.
_FAMILY_REVIEW_FIELD = {"legacy_field_family_membership": "review_ref"}
PROPOSAL_TERM = timedelta(days=30)
REVIEW_DEADLINE = timedelta(days=1)
# §5.2's fixed values.
REVIEW_TYPE = "migration"
REQUIRED_LANES = ["provenance"]
INDEPENDENCE_GRADE = "independent"
VISIBILITY_POLICY = "owner-visible"
ALLOWED_VERDICTS = ["approve", "changes_requested", "reject", "unable_to_verify"]
SATISFACTION_AUTHORITY = "ars://legacy/policy/w9-authority-review@1.0.0"
ESCALATION_RULE = "owner-ruling"
REVIEWER_PROFILE = "w9-independent-reviewer"
DECISION_KIND = "migration_authority"
DECISION_OPTIONS = ["accept", "reject"]
REQUIRED_AUTHORITY = "owner"
ANALYST_SESSION_PREFIX = "w9-analyst-session:"
AUTHOR_SESSION_PREFIX = "w9-author-session:"
SUBJECT_PREFIX = "w9-subject:"
SUBJECT_HASH_PREFIX = "w9-subject-sha256:"
EFFECTIVE_SCOPE_PREFIX = "w9-record:"
_PROJECTION_PREFIX = ".research-system/projections/legacy/"
_CONVENTIONS = re.compile(r"(^|[/\\])conventions\.md$", re.IGNORECASE)
# §9.3: the precedence tier 1 roles a corrected_by source must have.
TIER_ONE_ROLES = frozenset({"legacy_research_result", "legacy_pre_registration", "legacy_contract"})
_CL_ROLE = "legacy_decision_log_entry"


def new_legacy_state() -> dict[str, Any]:
    """Return an empty legacy projection."""

    return {
        "catalogue": None,
        "catalogue_revisions": [],
        "identities": {},
        "reserved_ids": [],
        "reservations": {},
        "proposals": {},
        "records": {},
        "reviews": {},
        "decisions": {},
        "ownership": {},
        "supersessions": {},
        "reference_edges": {},
        "observations_by_registration": {},
        "stale_observations": [],
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


def _refuse_foreign(identity: str, context: Mapping[str, Any]) -> None:
    """§4.3: refuse a W9 claim of an ID that a non-W9 event uses as a stream or creates, before or after the claim."""

    if identity in context.get("foreign_ids", frozenset()):
        raise IntegrityError("W9 identity is taken by a non-W9 event")
    if identity in pinned_signature_ids(context.get("pinned_signatures", ())):
        raise IntegrityError("W9 identity is a pinned W0 signature ref")


def claim_identity(state: dict[str, Any], identity: Any, kind: str, context: Mapping[str, Any] | None = None) -> None:
    """W9-C25: claim one pre-assigned W9 identity, refusing the reserved external refs and any collision."""

    if not isinstance(identity, str) or not identity:
        raise IntegrityError("W9 identity is invalid")
    if identity in RESERVED_IDS:
        raise IntegrityError("W9 identity is reserved for an external ref")
    if identity in state["identities"] or identity == CATALOGUE_STREAM_ID or identity in state["reservations"]:
        raise IntegrityError("W9 identity collision")
    _refuse_foreign(identity, context or {})
    state["identities"][identity] = kind


def _single(transaction: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return transaction[0]["payload"]


def _time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise IntegrityError("W9 event time must be UTC and end in Z")
    try:
        return datetime.fromisoformat(value.removesuffix("Z") + "+00:00").astimezone(UTC)
    except ValueError as exc:
        raise IntegrityError("W9 event time is not RFC 3339") from exc


def iso_z(value: datetime) -> str:
    """Format an aware time as the runtime does: ``isoformat`` in UTC, ``Z`` for the offset."""

    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_stream(event: Mapping[str, Any], stream_id: Any, version: int, what: str) -> None:
    """§4.5: each pre-assigned ID is one ledger stream, at the version its step takes."""

    if event.get("stream_id") != stream_id or event.get("stream_version") != version:
        raise IntegrityError(f"W9 {what} is not at its own stream's version {version}")


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


# --- Proposals, lapse and reservations (§4.2, §4.3, §4.6) ------------------------------------------------------------


def proposal_open(proposal: Mapping[str, Any], at: datetime) -> bool:
    """§4.6: a proposal is open while it is unresolved and has not lapsed."""

    return not proposal["recorded"] and at < proposal["lapse_at"]


def _open_proposal(state: Mapping[str, Any], record_id: Any, kind: str, at: datetime) -> Mapping[str, Any]:
    proposal = state["proposals"].get(record_id)
    if proposal is None or proposal["kind"] != kind:
        raise IntegrityError(f"W9 step names no {kind} proposal")
    if proposal["recorded"]:
        raise IntegrityError("W9 step names a proposal that is already recorded")
    if at >= proposal["lapse_at"]:
        raise IntegrityError("W9 step names a lapsed proposal")
    return proposal


def _reserve(state: dict[str, Any], ref_id: Any, kind: str, record_id: str, context: Mapping[str, Any]) -> None:
    """Reserve a pre-assigned ``rev_`` or ``dec_`` to the proposal that pre-assigns it (§4.3)."""

    if not isinstance(ref_id, str) or not ref_id.startswith("rev_" if kind == "review" else "dec_"):
        raise IntegrityError(f"W9 pre-assigned {kind} ref has the wrong kind")
    if ref_id in RESERVED_IDS:
        raise IntegrityError("W9 identity is reserved for an external ref")
    if ref_id in state["identities"] or ref_id in state["reservations"]:
        raise IntegrityError("W9 pre-assigned ID is already claimed or reserved")
    _refuse_foreign(ref_id, context)
    state["reservations"][ref_id] = {"kind": kind, "proposal": record_id, "used": False}


def _take_reservation(state: dict[str, Any], ref_id: Any, kind: str, record_id: str, as_kind: str) -> None:
    """A review request or Decision proposal takes exactly its proposal's reservation, and converts it (§4.3)."""

    reservation = state["reservations"].get(ref_id)
    if reservation is None or reservation["kind"] != kind or reservation["proposal"] != record_id:
        raise IntegrityError(f"W9 {kind} ID is not its proposal's pre-assigned {kind}")
    if reservation["used"]:
        raise IntegrityError(f"W9 pre-assigned {kind} is already used")
    reservation["used"] = True
    state["identities"][ref_id] = as_kind


def _check_pre_assigned(record: Mapping[str, Any], kind: str) -> None:
    for field, ref_kind in PRE_ASSIGNED_REFS.get(kind, {}).items():
        ref = record.get(field)
        if (
            not isinstance(ref, Mapping)
            or ref.get("record_revision") != 1
            or ref.get("content_hash") != pre_assigned_ref_hash(ref_kind, str(ref.get("id")), str(record["record_id"]))
        ):
            raise IntegrityError(f"W9 pre-assigned {field} hash is not the pre-assigned ref rule")


def _created_fields(record: Mapping[str, Any], event: Mapping[str, Any]) -> None:
    """The preparer-set fields of a created record are the event's actor, project and time (§5.1)."""

    if record.get("created_by_actor_id") != event.get("actor_id"):
        raise IntegrityError("W9 record created_by_actor_id is not the event's actor")
    if record.get("created_at") != event.get("occurred_at"):
        raise IntegrityError("W9 record created_at is not the event's time")
    if "project_id" in event and record.get("project_id") != event.get("project_id"):
        raise IntegrityError("W9 record project_id is not the ledger's project")


def _recorded(state: Mapping[str, Any], kind: str, ref: Any) -> Mapping[str, Any]:
    """§4.4: a recordRef to a W9 record resolves to a recorded record of its kind, at its revision and hash."""

    if not isinstance(ref, Mapping):
        raise IntegrityError(f"W9 ref to a {kind} is not a ref")
    record = state["records"].get(kind, {}).get(ref.get("id"))
    if record is None:
        raise IntegrityError(f"W9 ref names no recorded {kind}")
    if ref.get("record_revision") != record.get("record_revision") or ref.get("content_hash") != record_content_hash(
        record
    ):
        raise IntegrityError(f"W9 ref to a {kind} is not at its recorded hash")
    return record


def _registration_conflicts(state: Mapping[str, Any], record: Mapping[str, Any], at: datetime) -> bool:
    def same(other: Mapping[str, Any]) -> bool:
        if (other.get("root_kind"), other.get("root_id"), other.get("normalized_path")) == (
            record.get("root_kind"),
            record.get("root_id"),
            record.get("normalized_path"),
        ):
            return True
        mine, theirs = record.get("physical_identity", {}), other.get("physical_identity", {})
        return (mine.get("canonical_target"), mine.get("stable_file_id")) == (
            theirs.get("canonical_target"),
            theirs.get("stable_file_id"),
        )

    if any(same(other) for other in state["records"].get("legacy_path_registration", {}).values()):
        return True
    return any(
        proposal["kind"] == "legacy_path_registration" and proposal_open(proposal, at) and same(proposal["record"])
        for proposal in state["proposals"].values()
    )


def _check_registration(state: Mapping[str, Any], record: Mapping[str, Any], at: datetime) -> None:
    """LR-003's replay checks (§6.2)."""

    if _registration_conflicts(state, record, at):
        raise IntegrityError("W9 registration of a path or physical identity already registered or proposed")
    path = str(record.get("normalized_path", ""))
    if path.startswith(_PROJECTION_PREFIX) and record.get("role") != "legacy_read_only_projection":
        raise IntegrityError("W9 legacy role under the legacy projection directory")
    target = str(record.get("physical_identity", {}).get("canonical_target", ""))
    if record.get("role") != "conventions_lock" and (_CONVENTIONS.search(target) or _CONVENTIONS.search(path)):
        raise IntegrityError("W9 registration resolves to CONVENTIONS.md outside the conventions lock")


def _check_membership(record: Mapping[str, Any], event: Mapping[str, Any]) -> None:
    """LR-006's replay checks (§6.2; W9-T3)."""

    if event.get("actor_id") != record.get("author_actor_id"):
        raise IntegrityError("W9 membership table is not proposed by its author")
    names = [family.get("name") for family in record.get("families", [])]
    if len(names) != len(set(names)):
        raise IntegrityError("W9 membership family names are not unique")
    seen: set[str] = set()
    for family in record.get("families", []):
        pointers = set(family.get("pointers", []))
        if pointers & seen:
            raise IntegrityError("W9 membership pointer or pattern is in two families")
        seen |= pointers
    if seen & set(record.get("unassigned", [])):
        raise IntegrityError("W9 membership unassigned pointer is also in a family")


def _source_location(source: Mapping[str, Any]) -> tuple[Any, Any]:
    kind = source.get("identity_kind")
    path = (
        source.get("vault_path")
        if kind == "vault_file"
        else source.get("repository_path" if kind == "git_tracked" else "path")
    )
    return kind, path


def _source_matches_registration(
    source: Mapping[str, Any], registration: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    """§6.2 (LR-011, LR-015; §3 row 13): a source matches its registration's kind, root and path.

    The one exception (§7.1): a Computational-Log registration's source is the pinned export's retained copy.
    """

    if registration.get("role") == _CL_ROLE:
        exports = context.get("accepted_cl_export", ())
        retained = [entry["retained_copy"] for entry in exports]
        if not retained:
            raise IntegrityError("W9 Computational-Log source needs an accepted export")
        if not any(
            source.get("identity_kind") == "git_tracked"
            and (source.get("repository_path"), source.get("git_commit"), source.get("git_blob"))
            == (copy.get("repository_path"), copy.get("git_commit"), copy.get("git_blob"))
            for copy in retained
        ):
            raise IntegrityError("W9 Computational-Log source is not the accepted export's retained copy")
        return
    kind, path = _source_location(source)
    root_kind = registration.get("root_kind")
    if (
        kind != registration.get("source_identity_kind")
        or path != registration.get("normalized_path")
        or (root_kind == "vault_root") != (kind == "vault_file")
    ):
        raise IntegrityError("W9 source does not match its registration's kind, root and path")


def _check_inventory(state: Mapping[str, Any], record: Mapping[str, Any], event: Mapping[str, Any], context) -> None:
    """LR-011's replay checks (§6.2)."""

    registration = _recorded(state, "legacy_path_registration", record.get("registration_ref"))
    _source_matches_registration(record.get("source_identity", {}), registration, context)
    if event.get("actor_id") != record.get("observer_actor_id"):
        raise IntegrityError("W9 inventory observer is not the event's actor")
    rows = record.get("rows", [])
    if [row.get("row_ordinal") for row in rows] != list(range(1, len(rows) + 1)):
        raise IntegrityError("W9 inventory row ordinals do not run 1 to n")
    if any(row.get("selector_kind") != record.get("selector_kind") for row in rows):
        raise IntegrityError("W9 inventory row does not repeat the inventory's selector kind")
    if _time(record.get("read_ended_at")) < _time(record.get("read_started_at")):
        raise IntegrityError("W9 inventory read ends before it starts")


def reduce_proposal(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``ProposeLegacyRecord``: open a proposal under its pre-assigned record ID."""

    event = transaction[0]
    record = _single(transaction)
    refuse_restricted_frozen_copy(record)
    content_hash = require_content_hash(record)
    kind = record_kind(record.get("schema_id"))
    record_id = record.get("record_id")
    at = _time(event.get("occurred_at"))
    if row_id in WP9_3_1_ROWS:
        _require_stream(event, record_id, 1, "proposal")
        _created_fields(record, event)
        _check_pre_assigned(record, kind)
        if kind == "legacy_path_registration":
            _check_registration(state, record, at)
        elif kind == "legacy_field_family_membership":
            _check_membership(record, event)
        elif kind == "legacy_light_inventory":
            _check_inventory(state, record, event, context)
    claim_identity(state, record_id, "proposal", context)
    if row_id in WP9_3_1_ROWS:
        for field, ref_kind in PRE_ASSIGNED_REFS.get(kind, {}).items():
            _reserve(state, record[field]["id"], ref_kind, str(record_id), context)
    state["proposals"][record_id] = {
        "row": row_id,
        "kind": kind,
        "record": deepcopy(record),
        "content_hash": content_hash,
        "recorded": False,
        "actor_id": event.get("actor_id"),
        "created_at": event.get("occurred_at"),
        "lapse_at": at + PROPOSAL_TERM,
    }


# --- Reviews (§5.2, §5.4, §5.5) --------------------------------------------------------------------------------------


def _session_refs(refs: Any, row_id: str) -> list[str]:
    """``required_evidence_refs``: the analyst's session, and for a membership table the author's, in that order."""

    prefixes = [ANALYST_SESSION_PREFIX] + ([AUTHOR_SESSION_PREFIX] if row_id == "LR-007" else [])
    if not isinstance(refs, list) or len(refs) != len(prefixes):
        raise IntegrityError("W9 review request session refs are not the required count")
    sessions = []
    for ref, prefix in zip(refs, prefixes, strict=True):
        if not isinstance(ref, str) or not ref.startswith(prefix) or not ref.removeprefix(prefix):
            raise IntegrityError("W9 review request session ref is malformed or empty")
        sessions.append(ref.removeprefix(prefix))
    return sessions


def _creator_role_actor(proposal: Mapping[str, Any]) -> Any:
    """The creator §5.5's analyst rule names: an observer (LR-011) or a membership author (LR-006)."""

    record = proposal["record"]
    if proposal["kind"] == "legacy_field_family_membership":
        return record.get("author_actor_id")
    if proposal["kind"] == "legacy_light_inventory":
        return record.get("observer_actor_id")
    return None


def _refuse_analyst_creator(proposal: Mapping[str, Any], analyst: Any) -> None:
    """§5.5: the analyst who requests a review or proposes a Decision is not the creator, where the creator is an
    observer (LR-011) or a membership author (LR-006). A path registration is the analyst's own proposal (LR-003)."""

    if proposal["kind"] != "legacy_path_registration" and analyst in {
        proposal["actor_id"],
        _creator_role_actor(proposal),
    }:
        raise IntegrityError("W9 analyst is the proposal's creator")


def _check_review_request(
    state: dict[str, Any], row_id: str, event: Mapping[str, Any], payload: Mapping[str, Any], at: datetime
) -> tuple[str, list[str], str]:
    """LR-007 and LR-012's replay checks (§5.2, §5.5, §6.2)."""

    subject_ids, subject_hashes = payload.get("subject_ids"), payload.get("subject_hashes")
    if not isinstance(subject_ids, list) or not isinstance(subject_hashes, list) or len(subject_ids) != 1:
        raise IntegrityError("W9 review request must name exactly one subject")
    if len(subject_hashes) != 1:
        raise IntegrityError("W9 review request subjects and hashes are not paired")
    record_id = subject_ids[0]
    kind = LEGACY_ROW_ROUTES[row_id].record_schema_id.removeprefix("ars://legacy/").replace("-", "_")
    proposal = _open_proposal(state, record_id, kind, at)
    if subject_hashes[0] != proposal["content_hash"]:
        raise IntegrityError("W9 review request subject hash is not the proposal's current hash")
    review_id = payload.get("new_review_id")
    if review_id != proposal["record"][_REQUEST_REVIEW_FIELD[row_id]]["id"]:
        raise IntegrityError("W9 review ID is not the proposal's pre-assigned review")
    fixed = {
        "review_type": REVIEW_TYPE,
        "governing_refs": [f"W9:{row_id}"],
        "required_lanes": REQUIRED_LANES,
        "required_independence_grade": INDEPENDENCE_GRADE,
        "visibility_policy": VISIBILITY_POLICY,
        "allowed_verdicts": ALLOWED_VERDICTS,
        "satisfaction_authority": SATISFACTION_AUTHORITY,
        "escalation_rule": ESCALATION_RULE,
        "deadline": iso_z(at + REVIEW_DEADLINE),
    }
    for field, value in fixed.items():
        if payload.get(field) != value:
            raise IntegrityError(f"W9 review request {field} is not the fixed value")
    questions = payload.get("review_questions")
    if not isinstance(questions, list) or not questions:
        raise IntegrityError("W9 review request carries no review question")
    reviewers = payload.get("reviewer_capability")
    if not isinstance(reviewers, list) or len(reviewers) != 1 or not isinstance(reviewers[0], str):
        raise IntegrityError("W9 review request must name exactly one reviewer")
    sessions = _session_refs(payload.get("required_evidence_refs"), row_id)
    analyst, reviewer = event.get("actor_id"), reviewers[0]
    creator = proposal["actor_id"]
    _refuse_analyst_creator(proposal, analyst)
    excluded = {creator, analyst, _creator_role_actor(proposal)}
    if reviewer in excluded:
        raise IntegrityError("W9 reviewer is the proposal's creator, author or the requesting analyst")
    _require_stream(event, review_id, 1, "review request")
    _take_reservation(state, review_id, "review", str(record_id), "review")
    return str(record_id), sessions, reviewer


def reduce_review_request(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``RequestW9AuthorityReview``: open a W9 review under its pre-assigned review ID."""

    event = transaction[0]
    payload = _single(transaction)
    review_id = payload.get("new_review_id")
    entry: dict[str, Any] = {
        "request_row": row_id,
        "subjects": list(zip(payload.get("subject_ids", []), payload.get("subject_hashes", []), strict=False)),
        "verdict_row": None,
        "verdict": None,
    }
    if row_id in WP9_3_1_ROWS:
        record_id, sessions, reviewer = _check_review_request(
            state, row_id, event, payload, _time(event.get("occurred_at"))
        )
        entry.update(
            subject=(record_id, payload["subject_hashes"][0]),
            sessions=sessions,
            reviewer=reviewer,
            analyst=event.get("actor_id"),
            requested_at=event.get("occurred_at"),
            required_evidence_refs=list(payload["required_evidence_refs"]),
            allowed_verdicts=list(payload["allowed_verdicts"]),
        )
    else:
        claim_identity(state, review_id, "review", context)
    state["reviews"][review_id] = entry


def _check_verdict(
    state: Mapping[str, Any], review: Mapping[str, Any], event: Mapping[str, Any], payload: Mapping[str, Any]
) -> None:
    """LR-008 and LR-013's replay checks (§5.2; W9-C21, W9-C22)."""

    if event.get("actor_id") != review["reviewer"] or payload.get("reviewer_actor_id") != review["reviewer"]:
        raise IntegrityError("W9 verdict is not recorded by the reviewer the request named")
    if payload.get("verdict") not in review["allowed_verdicts"]:
        raise IntegrityError("W9 verdict is not an allowed verdict")
    review_id = payload["review_id"]
    record_id, subject_hash = review["subject"]
    proposal = _open_proposal(
        state, record_id, state["proposals"].get(record_id, {}).get("kind", ""), _time(event.get("occurred_at"))
    )
    if payload.get("unchanged_subject_sha256") != subject_hash or subject_hash != proposal["content_hash"]:
        raise IntegrityError("W9 verdict subject hash is stale")
    fixed = {
        "conditions": [],
        "required_evidence_refs": review["required_evidence_refs"],
        "reviewer_profile": REVIEWER_PROFILE,
        "context_manifest_id": review_context_manifest_id(review_id, review["requested_at"]),
        "producing_attempt_id": review_attempt_id(review_id, review["requested_at"]),
        "trace_visibility_evidence_refs": [subject_hash],
        "computed_independence_grade": INDEPENDENCE_GRADE,
    }
    for field, value in fixed.items():
        if payload.get(field) != value:
            raise IntegrityError(f"W9 verdict {field} is not the derived value")
    session = payload.get("reviewer_session")
    if not isinstance(session, str) or session in review["sessions"]:
        raise IntegrityError("W9 reviewer session is a session the request records")
    _require_stream(event, review_id, 2, "review verdict")


def reduce_review_verdict(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``RecordW9AuthorityReview``: record the one verdict on an open W9 review."""

    payload = _single(transaction)
    review = state["reviews"].get(payload.get("review_id"))
    if review is None or review["verdict_row"] is not None:
        raise IntegrityError("W9 review verdict has no open W9 review")
    if row_id in WP9_3_1_ROWS:
        _check_verdict(state, review, transaction[0], payload)
    review["verdict_row"] = row_id
    review["verdict"] = payload.get("verdict")


def review_satisfied(state: Mapping[str, Any], review_id: Any, record_id: Any, content_hash: Any) -> bool:
    """§5.4: one ``approve`` verdict, under the verdict row answering its request row, on the subject's current hash."""

    from research_system.legacy.routes import verdict_row_for_request

    review = state["reviews"].get(review_id)
    return (
        review is not None
        and review.get("verdict") == "approve"
        and review.get("verdict_row") == verdict_row_for_request(review["request_row"])
        and review.get("subject") == (record_id, content_hash)
    )


# --- Decisions (§5.2, §6.1) ------------------------------------------------------------------------------------------


def _check_decision_proposal(
    state: dict[str, Any], row_id: str, event: Mapping[str, Any], payload: Mapping[str, Any]
) -> tuple[str, str, datetime]:
    """LR-004 and LR-009's replay checks."""

    at = _time(event.get("occurred_at"))
    refs = payload.get("governing_evidence_refs")
    if not isinstance(refs, list) or len(refs) != 3 or refs[0] != f"W9:{row_id}":
        raise IntegrityError("W9 Decision proposal does not encode its subject")
    if not (isinstance(refs[1], str) and refs[1].startswith(SUBJECT_PREFIX)) or not (
        isinstance(refs[2], str) and refs[2].startswith(SUBJECT_HASH_PREFIX)
    ):
        raise IntegrityError("W9 Decision proposal does not encode its subject")
    record_id, subject_hash = refs[1].removeprefix(SUBJECT_PREFIX), refs[2].removeprefix(SUBJECT_HASH_PREFIX)
    kind = LEGACY_ROW_ROUTES[row_id].record_schema_id.removeprefix("ars://legacy/").replace("-", "_")
    proposal = _open_proposal(state, record_id, kind, at)
    if subject_hash != proposal["content_hash"]:
        raise IntegrityError("W9 Decision proposal subject hash is not the proposal's current hash")
    decision_id = payload.get("new_decision_id")
    if decision_id != proposal["record"][_DECISION_PROPOSAL_FIELD[row_id]]["id"]:
        raise IntegrityError("W9 Decision ID is not the proposal's pre-assigned Decision")
    fixed = {
        "decision_revision": 1,
        "decision_kind": DECISION_KIND,
        "options": DECISION_OPTIONS,
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": REQUIRED_AUTHORITY,
        "review_date": event.get("occurred_at"),
        "expires_at": iso_z(at + PROPOSAL_TERM),
    }
    for field, value in fixed.items():
        if payload.get(field) != value:
            raise IntegrityError(f"W9 Decision proposal {field} is not the fixed value")
    review_field = _FAMILY_REVIEW_FIELD.get(kind)
    if review_field and not review_satisfied(
        state, proposal["record"][review_field]["id"], record_id, proposal["content_hash"]
    ):
        raise IntegrityError("W9 Decision proposal has no satisfied review on the current hash")
    _refuse_analyst_creator(proposal, event.get("actor_id"))
    _require_stream(event, decision_id, 1, "Decision proposal")
    _take_reservation(state, decision_id, "decision", record_id, "decision")
    expires = at + PROPOSAL_TERM
    state["proposals"][record_id]["lapse_at"] = max(state["proposals"][record_id]["lapse_at"], expires)
    return record_id, subject_hash, expires


def reduce_decision_proposal(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``ProposeW9AuthorityDecision``: open a Decision under its pre-assigned ID (W9-C25 refuses the reserved one)."""

    event = transaction[0]
    payload = _single(transaction)
    decision_id = payload.get("new_decision_id")
    entry: dict[str, Any] = {
        "propose_row": row_id,
        "resolve_row": None,
        "governing_evidence_refs": list(payload.get("governing_evidence_refs", [])),
    }
    if row_id in WP9_3_1_ROWS:
        record_id, subject_hash, expires = _check_decision_proposal(state, row_id, event, payload)
        entry.update(subject=(record_id, subject_hash), expires_at=expires)
    else:
        claim_identity(state, decision_id, "decision", context)
    state["decisions"][decision_id] = entry


def _decision_family(row_id: str) -> str:
    return LEGACY_ROW_ROUTES[row_id].payload_discriminant.split("/", 2)[1]


def _record_resolved(
    state: dict[str, Any], row_id: str, decision_id: str, record: Mapping[str, Any], context: Mapping[str, Any]
) -> str:
    """G5: bind a resolved record to its open proposal and to the resolving Decision.

    LR-020's ownership transitions are the exception: the acceptance writes one per accepted whole-file item, with no
    proposal of their own (P-072 item 2), so each claims its own identity.
    """

    record_id = record.get("record_id")
    kind = record_kind(record.get("schema_id"))
    content_hash = require_content_hash(record)
    decision_ref = record.get(_DECISION_FIELDS.get(kind, "decision_ref"))
    if not isinstance(decision_ref, Mapping) or decision_ref.get("id") != decision_id:
        raise IntegrityError("W9 resolved record names another Decision")
    if row_id == "LR-020" and kind == "legacy_ownership_transitioned":
        claim_identity(state, record_id, kind, context)
        state["records"].setdefault(kind, {})[record_id] = deepcopy(record)
        return str(record_id)
    proposal = state["proposals"].get(record_id)
    if proposal is None or proposal["recorded"] or proposal["kind"] != kind or proposal["record"] != record:
        raise IntegrityError("W9 resolved record differs from its open proposal")
    if proposal["content_hash"] != content_hash:
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


def _is_recorded(state: Mapping[str, Any], record_id: Any) -> bool:
    return any(record_id in records for records in state["records"].values())


def _apply_supersession(state: dict[str, Any], record: Mapping[str, Any]) -> None:
    """Supersession is acyclic: a recorded record superseded once, by another record, with no chain back to itself."""

    superseded = record.get("superseded_ref", {}).get("id")
    replacing = record.get("replacing_ref", {}).get("id")
    if not _is_recorded(state, superseded):
        raise IntegrityError("W9 supersession names no recorded record")
    chain: dict[str, str] = state["supersessions"]
    if superseded == replacing or superseded in chain:
        raise IntegrityError("W9 supersession is invalid")
    cursor = replacing
    while cursor in chain:
        cursor = chain[cursor]
        if cursor == superseded:
            raise IntegrityError("W9 supersession cycle")
    chain[superseded] = replacing


def _check_resolution(
    state: Mapping[str, Any], row_id: str, decision: Mapping[str, Any], transaction: Sequence[Mapping[str, Any]]
) -> None:
    """G5 at LR-005 and LR-010 (§5.2, §6.1), including F-8's first limb."""

    event, payload = transaction[0], transaction[0]["payload"]
    at = _time(event.get("occurred_at"))
    record = transaction[1]["payload"]
    record_id, subject_hash = decision["subject"]
    if record.get("record_id") != record_id or record_content_hash(record) != subject_hash:
        raise IntegrityError("W9 resolved record is not its Decision's subject")
    kind = record_kind(record.get("schema_id"))
    review_field = _FAMILY_REVIEW_FIELD.get(kind)
    considered = [] if review_field is None else [record[review_field]["id"]]
    fixed = {
        "selected_option": "accept",
        "effective_scope": f"{EFFECTIVE_SCOPE_PREFIX}{record_id}",
        "decision_revision": 1,
        "deciding_actor_id": event.get("actor_id"),
        "decision_authority_grant_id": event.get("authority_grant_id"),
        "governing_evidence_refs": decision["governing_evidence_refs"],
        "considered_review_ids": considered,
        "effective_at": event.get("occurred_at"),
        "permitted_commands": [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    for field, value in fixed.items():
        if payload.get(field) != value:
            raise IntegrityError(f"W9 Decision resolution {field} is not the required value")
    if at > decision["expires_at"]:
        raise IntegrityError("W9 Decision resolved after it expired")
    proposal = state["proposals"].get(record_id)
    if proposal is None or proposal["recorded"] or at >= proposal["lapse_at"]:
        raise IntegrityError("W9 step names a lapsed proposal")
    if review_field and not review_satisfied(state, considered[0], record_id, subject_hash):
        raise IntegrityError("W9 resolution's review is not satisfied on the record's hash")
    _require_stream(event, payload.get("decision_id"), 2, "Decision resolution")
    _require_stream(transaction[1], record_id, 2, "resolved record")


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
    if row_id in WP9_3_1_ROWS:
        _check_resolution(state, row_id, decision, transaction)
    decision["resolve_row"] = row_id
    if _decision_family(row_id) == _RECOVERY_DECISION_FAMILY:
        _add_edges(state, decision_id, [ref for ref in decision["governing_evidence_refs"] if ref.startswith("obj_")])
    for event in transaction[1:]:
        record = event["payload"]
        record_id = _record_resolved(state, row_id, decision_id, record, context)
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
    the proposal's recomputed content hash, answered with approval under LR-013.
    """

    event = transaction[0]
    record = _single(transaction)
    refuse_restricted_frozen_copy(record)
    content_hash = require_content_hash(record)
    record_id = record.get("record_id")
    proposal = state["proposals"].get(record_id)
    if (
        proposal is None
        or proposal["recorded"]
        or proposal["kind"] != "legacy_light_inventory"
        or proposal["record"] != record
    ):
        raise IntegrityError("W9 light inventory differs from its open proposal")
    if row_id in WP9_3_1_ROWS:
        if _time(event.get("occurred_at")) >= proposal["lapse_at"]:
            raise IntegrityError("W9 step names a lapsed proposal")
        if event.get("actor_id") != record.get("observer_actor_id"):
            raise IntegrityError("W9 light inventory is not recorded by its observer")
        _require_stream(event, record_id, 2, "recorded inventory")
    reproduction = record.get("independent_reproduction_ref")
    review = state["reviews"].get(reproduction.get("id") if isinstance(reproduction, Mapping) else None)
    if (
        review is None
        or review["verdict_row"] != _REPRODUCTION_VERDICT_ROW
        or review["verdict"] not in _POSITIVE_REPRODUCTION_VERDICTS
        or (record_id, content_hash) not in review["subjects"]
    ):
        raise IntegrityError("W9 light inventory has no approved reproduction review of its proposal")
    proposal["recorded"] = True
    state["records"].setdefault("legacy_light_inventory", {})[record_id] = deepcopy(record)


# --- Observations (§5.3, §6.2 LR-015, §8, §9) ------------------------------------------------------------------------


def _git_file_locators(node: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(node, Mapping):
        if node.get("locator_kind") == "git_file":
            yield node
        for value in node.values():
            yield from _git_file_locators(value)
    elif isinstance(node, list):
        for value in node:
            yield from _git_file_locators(value)


def _check_signatures(record: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    """§9.1 (O-27): every family's class comes from a pinned W0 signature."""

    pinned = tuple(context.get("pinned_signatures", ()))
    if not pinned:
        raise IntegrityError("no accepted W0-D1 signature")
    for family in record.get("families", []):
        signature = next((entry for entry in pinned if dict(entry["ref"]) == family.get("signature_record_ref")), None)
        if signature is None:
            raise IntegrityError("W9 family's signature ref is not a pinned W0 signature")
        revision = family.get("signed_w0_revision_ref")
        if (
            not isinstance(revision, Mapping)
            or revision.get("locator_kind") != "git_file"
            or not any(
                (revision.get("repository_path"), revision.get("git_blob"))
                == (document.get("repository_path"), document.get("git_blob"))
                for document in signature["signed_w0_documents"]
            )
        ):
            raise IntegrityError("W9 family's signed W0 revision is not a document its signature signs")


def _registered_role(state: Mapping[str, Any], repository_path: Any) -> Any:
    for registration in state["records"].get("legacy_path_registration", {}).values():
        if (
            registration.get("root_kind") == "repository_root"
            and registration.get("normalized_path") == repository_path
        ):
            return registration.get("role")
    return None


def _check_qualifiers(state: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    """§9.3 (W9-T13): ``corrected_by`` names a precedence tier 1 source; a line span is never inverted."""

    for locator in _git_file_locators(record):
        span = locator.get("line_span")
        if isinstance(span, Mapping) and span.get("first_line", 0) > span.get("last_line", 0):
            raise IntegrityError("W9 locator line span is inverted")
    for qualifier in record.get("qualifiers", []):
        if qualifier.get("qualifier_kind") != "corrected_by":
            continue
        source = qualifier.get("source_ref", {})
        if source.get("locator_kind") == "git_file":
            role = _registered_role(state, source.get("repository_path"))
        else:
            observed = state["records"].get("legacy_observation", {}).get(source.get("id"))
            if observed is not None and source.get("content_hash") != record_content_hash(observed):
                observed = None
            registration = (
                state["records"].get("legacy_path_registration", {}).get(observed["registration_ref"]["id"])
                if observed is not None
                else None
            )
            role = registration.get("role") if registration is not None else None
        if role not in TIER_ONE_ROLES:
            raise IntegrityError("W9 corrected_by source is not a precedence tier 1 source")


def _names_observed_source(ref: Mapping[str, Any], source: Mapping[str, Any]) -> bool:
    _, path = _source_location(source)
    return (ref.get("locator_kind") == "git_file" and ref.get("repository_path") == path) or (
        ref.get("locator_kind") == "vault_file" and ref.get("vault_path") == path
    )


def _check_precedence(record: Mapping[str, Any]) -> None:
    """§9.4 (W9-T4): a ``stale_projection`` family carries a conflict naming the observed record and a stronger one."""

    if not any(family.get("w0_class") == "stale_projection" for family in record.get("families", [])):
        return
    source = record.get("source_identity", {})
    if not any(
        len(conflict.get("conflicting_record_refs", [])) >= 2
        and any(_names_observed_source(ref, source) for ref in conflict["conflicting_record_refs"])
        for conflict in record.get("conflicts", [])
    ):
        raise IntegrityError("W9 stale_projection family has no conflict naming the observed record")


def _check_selector(state: Mapping[str, Any], record: Mapping[str, Any], registration_id: str) -> None:
    """§8.2, §8.4: the selector by its kind (W9-T3, W9-T22)."""

    selector = record.get("selector", {})
    kind = selector.get("selector_kind")
    names = [family.get("family_name") for family in record.get("families", [])]
    if kind in {"whole_file", "inventory_item"}:
        expected = "whole_file" if kind == "whole_file" else "item"
        if names != [expected]:
            raise IntegrityError(f"W9 {kind} observation must carry exactly one family named {expected}")
    if kind == "inventory_item":
        inventory = _recorded(state, "legacy_light_inventory", selector.get("inventory_ref"))
        if inventory["registration_ref"].get("id") != registration_id:
            raise IntegrityError("W9 inventory item names an inventory of another registration")
        rows = inventory.get("rows", [])
        ordinal = selector.get("row_ordinal")
        row = rows[ordinal - 1] if isinstance(ordinal, int) and 1 <= ordinal <= len(rows) else None
        if (
            row is None
            or row.get("row_kind") != "item"
            or row.get("anchor_text") != selector.get("anchor_text")
            or row.get("raw_row_sha256") != selector.get("raw_row_sha256")
        ):
            raise IntegrityError("W9 inventory item selector names no observable item row")
    elif kind == "json_family_set":
        table = _recorded(state, "legacy_field_family_membership", selector.get("membership_ref"))
        if table.get("unassigned"):
            raise IntegrityError("W9 membership table has unassigned pointers")
        table_names = {family.get("name") for family in table.get("families", [])}
        if set(names) != set(selector.get("family_names", [])) or len(names) != len(set(names)):
            raise IntegrityError("W9 observation families differ from the selector's family names")
        if not set(names) <= table_names:
            raise IntegrityError("W9 observation family is not a family of its membership table")
        source = record.get("source_identity", {})
        _, path = _source_location(source)
        if not any(
            entry.get("path") == path and entry.get("sha256") == source.get("sha256")
            for entry in table.get("applies_to", [])
        ):
            raise IntegrityError("W9 observed bytes are not bytes its membership table applies to")
        author = table.get("author_actor_id")
        if author in {record.get("observer_actor_id"), record.get("importer", {}).get("actor_id")}:
            raise IntegrityError("W9 membership table author is the observation's observer or importer")


def _source_fingerprint(source: Mapping[str, Any]) -> Any:
    return source.get("git_blob") if source.get("identity_kind") == "git_tracked" else source.get("sha256")


def _check_observation(
    state: Mapping[str, Any], record: Mapping[str, Any], event: Mapping[str, Any], context: Mapping[str, Any]
) -> str:
    """LR-015's replay checks (§6.2). Returns the registration's ID."""

    _created_fields(record, event)
    if event.get("actor_id") != record.get("observer_actor_id"):
        raise IntegrityError("W9 observer is not the event's actor")
    registration_ref = record.get("registration_ref", {})
    registration = _recorded(state, "legacy_path_registration", registration_ref)
    registration_id = str(registration_ref.get("id"))
    _source_matches_registration(record.get("source_identity", {}), registration, context)
    count = len(state["observations_by_registration"].get(registration_id, []))
    derived = observation_record_id(
        registration_id, observation_subject_digest(record), count, str(registration.get("created_at"))
    )
    if record.get("record_id") != derived:
        raise IntegrityError("W9 observation record_id is not derived from its subject")
    _require_stream(event, derived, 1, "observation")
    _check_selector(state, record, registration_id)
    _check_signatures(record, context)
    _check_qualifiers(state, record)
    _check_precedence(record)
    return registration_id


def reduce_record(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """Record-writing rows with no Decision or proposal: observation, paper root, citation status and use mismatch."""

    event = transaction[0]
    record = _single(transaction)
    refuse_restricted_frozen_copy(record)
    require_content_hash(record)
    kind = record_kind(record.get("schema_id"))
    record_id = record.get("record_id")
    registration_id = None
    if kind == "legacy_observation" and row_id in WP9_3_1_ROWS:
        registration_id = _check_observation(state, record, event, context)
    claim_identity(state, record_id, kind, context)
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
    if registration_id is not None:
        earlier = state["observations_by_registration"].setdefault(registration_id, [])
        fingerprint = _source_fingerprint(record["source_identity"])
        for observation_id in earlier:
            other = state["records"]["legacy_observation"][observation_id]
            if (
                _source_fingerprint(other["source_identity"]) != fingerprint
                and observation_id not in state["stale_observations"]
            ):
                state["stale_observations"].append(observation_id)
        earlier.append(str(record_id))


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
