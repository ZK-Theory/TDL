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
§6.2. WP9.3-2 routes LR-016 to LR-020, the closed-reference acceptance, with the batch rules of §10.1, the structural
``pilot_promotion`` rules of §10.2, and the derived ownership list of §10.5 (owner point E). The rows of later packages
keep WP9.2's reducer rules, plus the cross-cutting ones above; their packages add theirs.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.legacy.accepted_w9 import CATALOGUE_STREAM_ID, RESERVED_IDS, accepted_genesis_payload
from research_system.legacy.identities import pinned_signature_ids
from research_system.legacy.projection_read import adoption_suspension_cause

# The reader owns §7.4's fixed strings, and its module blob is in the importer hash (WP9.3-1 record §2), so replay reads
# them from there rather than from a copy (WP9.3-1b, review i-2).
from research_system.legacy.reader import MANUSCRIPT_ROOT_ROLE, NON_INFERENCES
from research_system.legacy.records import (
    adoption_eligibility_decision_id,
    adoption_review_id,
    citation_status_record_id,
    observation_record_id,
    observation_subject_digest,
    ownership_record_id,
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

# --- WP9.3 and WP9.4-1: the rows whose full replay checks this module makes. -------------------------------------
WP9_3_1_ROWS = frozenset(f"LR-{number:03d}" for number in range(3, 16))
# WP9.3-2 adds LR-016 to LR-020, the closed-reference acceptance (note §10).
WP9_3_ROWS = frozenset(f"LR-{number:03d}" for number in range(3, 21))
# WP9.4-1 adds LR-023 to LR-034, adoption, eligibility and discharge (WP9.4 note §2.4, §5.1).
WP9_4_1_ROWS = frozenset(f"LR-{number:03d}" for number in range(23, 35))
# WP9.4-2 adds LR-035, LR-039, and LR-040 to LR-055, the full path (WP9.4 note §2.4, §10 to §12).
WP9_4_2_ROWS = frozenset({"LR-035", "LR-039", *(f"LR-{number:03d}" for number in range(40, 56))})
WP9_4_ROWS = WP9_4_1_ROWS | WP9_4_2_ROWS
CHECKED_ROWS = WP9_3_ROWS | WP9_4_ROWS
ACCEPTANCE = "legacy_closed_reference_acceptance"
OWNERSHIP = "legacy_ownership_transitioned"
ADOPTION = "legacy_adoption_decision"
DISCHARGE = "legacy_discharge_relation"
PAPER_ROOT = "legacy_paper_root"
CITATION_STATUS = "legacy_paper_citation_status"
SOURCE_INVENTORY = "legacy_source_inventory"
TRANSITION_MAPPING = "legacy_transition_mapping"
NO_REVIEW_REQUIRED = object()
# The pre-assigned refs each proposal kind carries (§4.2; WP9.4 §5.1), with the ref kind.
PRE_ASSIGNED_REFS: Mapping[str, Mapping[str, str]] = {
    "legacy_path_registration": {"registration_decision_ref": "decision"},
    "legacy_field_family_membership": {"review_ref": "review", "acceptance_decision_ref": "decision"},
    "legacy_light_inventory": {"independent_reproduction_ref": "review"},
    ACCEPTANCE: {"independent_review_ref": "review", "decision_ref": "decision"},
    ADOPTION: {"decision_ref": "decision"},
    DISCHARGE: {"reviewer_ref": "review", "decision_ref": "decision"},
    SOURCE_INVENTORY: {"reviewer_ref": "review", "decision_ref": "decision"},
    TRANSITION_MAPPING: {"reviewer_ref": "review", "decision_ref": "decision"},
    OWNERSHIP: {"reviewer_ref": "review", "decision_ref": "decision"},
}
_DECISION_PROPOSAL_FIELD = {
    "LR-004": "registration_decision_ref",
    "LR-009": "acceptance_decision_ref",
    "LR-019": "decision_ref",
    "LR-028": "decision_ref",
    "LR-033": "decision_ref",
    "LR-043": "decision_ref",
    "LR-048": "decision_ref",
    "LR-053": "decision_ref",
}
_REVIEW_FIELD_BY_KIND = {
    "legacy_field_family_membership": "review_ref",
    "legacy_light_inventory": "independent_reproduction_ref",
    ACCEPTANCE: "independent_review_ref",
    DISCHARGE: "reviewer_ref",
    SOURCE_INVENTORY: "reviewer_ref",
    TRANSITION_MAPPING: "reviewer_ref",
    OWNERSHIP: "reviewer_ref",
}


def review_id_for(kind: str, record: Mapping[str, Any]) -> Any:
    """Resolve the W9 review ID a proposal or Decision kind requires (§5.2, owner point C, M-2).

    Returns the record's pre-assigned field ID for kinds that carry one, the derived adoption review ID for
    ``legacy_adoption_decision``, and :data:`NO_REVIEW_REQUIRED` for ``legacy_path_registration`` alone. Never
    defaults to ``None`` for an unlisted kind.
    """

    if kind == "legacy_path_registration":
        return NO_REVIEW_REQUIRED
    if kind == ADOPTION:
        return adoption_review_id(str(record["record_id"]), str(record["created_at"]))
    field = _REVIEW_FIELD_BY_KIND.get(kind)
    if field is None:
        raise IntegrityError(f"W9 record kind has no review resolver entry: {kind}")
    return record[field]["id"]


def ownership_resolution_row(record: Mapping[str, Any]) -> str:
    """Return ``LR-054`` or ``LR-055`` from an ownership proposal's transition direction (§5.1, §10.5)."""

    direction = (record.get("from_mode"), record.get("to_mode"))
    if direction == ("legacy_owned", "successor_owned"):
        return "LR-054"
    if direction == ("successor_owned", "closed_reference"):
        return "LR-055"
    raise IntegrityError(
        "W9 ownership proposal direction must be legacy_owned -> successor_owned or successor_owned -> closed_reference"
    )


# §10.1 and §2.1: the first batch only, which is the integration pilot, of at most 20 items.
MAX_BATCH_ITEMS = 20
# §10.2: LR-020's accepted pilot_promotion set (annex lines 729-743 and the catalogue's LR-020 row). The four
# unconditional fixtures are required on every item. Code cannot decide a "when" condition, so the three conditional ones
# are admitted and their applicability is the reviewer's and Stephen's. A fixture outside the seven is refused (the
# WP9.3-2 plan's Q2; Stephen, 2026-11-11, "Yes, as recommended").
UNCONDITIONAL_FIXTURES = ("F-018", "F-023", "F-037", "S-014")
CONDITIONAL_FIXTURES = ("F-017", "S-005", "F-038")
PILOT_FIXTURES = frozenset((*UNCONDITIONAL_FIXTURES, *CONDITIONAL_FIXTURES))
# WP9.4 note §5.4 (owner point L): fixture sets for LR-029, LR-034, LR-044, LR-049, LR-054, and LR-055.
ADOPTION_UNCONDITIONAL_FIXTURES = ("S-017",)
ADOPTION_CONDITIONAL_FIXTURES = ("F-015", "F-019", "F-038")
ADOPTION_FIXTURES = frozenset((*ADOPTION_UNCONDITIONAL_FIXTURES, *ADOPTION_CONDITIONAL_FIXTURES))
DISCHARGE_UNCONDITIONAL_FIXTURES: tuple[str, ...] = ()
DISCHARGE_CONDITIONAL_FIXTURES: tuple[str, ...] = ()
DISCHARGE_FIXTURES: frozenset[str] = frozenset()
SOURCE_INVENTORY_UNCONDITIONAL_FIXTURES = ("F-018", "F-023", "F-037")
SOURCE_INVENTORY_FIXTURES = frozenset(SOURCE_INVENTORY_UNCONDITIONAL_FIXTURES)
MAPPING_UNCONDITIONAL_FIXTURES: tuple[str, ...] = ()
MAPPING_FIXTURES: frozenset[str] = frozenset()
OWNERSHIP_54_UNCONDITIONAL_FIXTURES = ("F-006", "F-019", "F-023", "F-037")
OWNERSHIP_54_FIXTURES = frozenset((*OWNERSHIP_54_UNCONDITIONAL_FIXTURES, "F-038"))
OWNERSHIP_55_UNCONDITIONAL_FIXTURES = ("F-006", "F-019", "F-037")
OWNERSHIP_55_FIXTURES = frozenset((*OWNERSHIP_55_UNCONDITIONAL_FIXTURES, "F-038"))
_WP9_4_REQUEST_TO_RESOLUTION = {
    "LR-026": "LR-029",
    "LR-031": "LR-034",
    "LR-041": "LR-044",
    "LR-046": "LR-049",
}
_WP9_4_DECISION_TO_RESOLUTION = {
    "LR-028": "LR-029",
    "LR-033": "LR-034",
    "LR-043": "LR-044",
    "LR-048": "LR-049",
}
_WP9_4_ALLOWED_FIXTURES = {
    "LR-029": ADOPTION_FIXTURES,
    "LR-034": DISCHARGE_FIXTURES,
    "LR-044": SOURCE_INVENTORY_FIXTURES,
    "LR-049": MAPPING_FIXTURES,
    "LR-054": OWNERSHIP_54_FIXTURES,
    "LR-055": OWNERSHIP_55_FIXTURES,
}
_WP9_4_UNCONDITIONAL_FIXTURES = {
    "LR-029": ADOPTION_UNCONDITIONAL_FIXTURES,
    "LR-034": DISCHARGE_UNCONDITIONAL_FIXTURES,
    "LR-044": SOURCE_INVENTORY_UNCONDITIONAL_FIXTURES,
    "LR-049": MAPPING_UNCONDITIONAL_FIXTURES,
    "LR-054": OWNERSHIP_54_UNCONDITIONAL_FIXTURES,
    "LR-055": OWNERSHIP_55_UNCONDITIONAL_FIXTURES,
}


def _resolution_row_for(row_id: str, record: Mapping[str, Any]) -> str | None:
    if row_id in {"LR-051", "LR-053"}:
        return ownership_resolution_row(record)
    return _WP9_4_REQUEST_TO_RESOLUTION.get(row_id) or _WP9_4_DECISION_TO_RESOLUTION.get(row_id)


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
ELIGIBLE_SESSION_PREFIX = "w9-eligible-session:"
ELIGIBLE_FAMILY_PREFIX = "w9-eligible-family:"
ELIGIBLE_VERSION_PREFIX = "w9-eligible-version:"
ELIGIBLE_PROFILE_PREFIX = "w9-eligible-profile:"
ELIGIBLE_GRADE_PREFIX = "w9-eligible-grade:"
APPLICABLE_FIXTURES_PREFIX = "w9-applicable-fixtures:"
FIXTURE_REF_PREFIX = "w9-fixture:"
OPEN_ITEMS_BLOB_PREFIX = "w9-open-items-blob:"
MANUSCRIPT_USE_PREFIX = "w9-use:manuscript-claims/"
TASK_USE_PREFIX = "w9-use:task-input/"
CLAIM_USE_PREFIX = "w9-use:claim-evidence/"
USE_PAPER_KEYS = frozenset({"P01-A", "P01-B"})
USE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*\Z")
_FIXTURE_REF_ID_RE = re.compile(r"^(rev|art|dec)_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
_SHA1_RE = re.compile(r"^[0-9a-f]{40}\Z")
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
        "current_citation_status_by_root": {},
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


def _folded_path(record: Mapping[str, Any]) -> str:
    return str(record.get("normalized_path", "")).rstrip("/").casefold()


def _normalized_target(record: Mapping[str, Any]) -> str:
    target = str(record.get("physical_identity", {}).get("canonical_target", "")).replace("\\", "/")
    while "//" in target:
        target = target.replace("//", "/")
    return target.rstrip("/").casefold()


def _registration_conflicts(state: Mapping[str, Any], record: Mapping[str, Any], at: datetime) -> bool:
    mine = record.get("physical_identity", {})
    mine_vol_id = (mine.get("volume_serial_number"), mine.get("stable_file_id"))
    mine_has_vol_id = mine_vol_id[0] is not None and mine_vol_id[1] is not None
    mine_is_root = record.get("role") == MANUSCRIPT_ROOT_ROLE
    mine_path = _folded_path(record)
    mine_target = _normalized_target(record)

    def same(other: Mapping[str, Any]) -> bool:
        other_path = _folded_path(other)
        if (other.get("root_kind"), other_path) == (record.get("root_kind"), mine_path):
            return True
        theirs = other.get("physical_identity", {})
        if mine_has_vol_id and mine_vol_id == (theirs.get("volume_serial_number"), theirs.get("stable_file_id")):
            return True
        theirs_is_root = other.get("role") == MANUSCRIPT_ROOT_ROLE
        if mine_is_root or theirs_is_root:
            same_kind = other.get("root_kind") == record.get("root_kind")
            if same_kind and mine_path and other_path:
                if theirs_is_root and mine_path.startswith(f"{other_path}/"):
                    return True
                if mine_is_root and other_path.startswith(f"{mine_path}/"):
                    return True
            other_target = _normalized_target(other)
            if mine_target and other_target:
                if theirs_is_root and mine_target.startswith(f"{other_target}/"):
                    return True
                if mine_is_root and other_target.startswith(f"{mine_target}/"):
                    return True
        return False

    if any(same(other) for other in state["records"].get("legacy_path_registration", {}).values()):
        return True
    return any(
        proposal["kind"] == "legacy_path_registration" and proposal_open(proposal, at) and same(proposal["record"])
        for proposal in state["proposals"].values()
    )


def _check_registration(state: Mapping[str, Any], record: Mapping[str, Any], at: datetime) -> None:
    """LR-003's replay checks (§6.2; WP9.4 §10.2 owner point O)."""

    if record.get("role") == MANUSCRIPT_ROOT_ROLE and record.get("source_identity_kind") != "git_tracked":
        raise IntegrityError("W9 legacy_manuscript_root registration must be git_tracked")
    if _registration_conflicts(state, record, at):
        raise IntegrityError("W9 registration of a path or physical identity already registered or proposed")
    path = str(record.get("normalized_path", ""))
    if path.casefold().startswith(_PROJECTION_PREFIX) and record.get("role") != "legacy_read_only_projection":
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
    if registration.get("role") == MANUSCRIPT_ROOT_ROLE:
        root_path = str(registration.get("normalized_path", ""))
        root_prefix = root_path if root_path.endswith("/") else f"{root_path}/"
        if (
            kind != "git_tracked"
            or kind != registration.get("source_identity_kind")
            or root_kind != "repository_root"
            or not isinstance(path, str)
            or not path.startswith(root_prefix)
            or len(path) <= len(root_prefix)
            or path.endswith("/")
        ):
            raise IntegrityError("W9 source does not match its registration's kind, root and path")
        return
    if (
        kind != registration.get("source_identity_kind")
        or path != registration.get("normalized_path")
        or (root_kind == "vault_root") != (kind == "vault_file")
    ):
        raise IntegrityError("W9 source does not match its registration's kind, root and path")


def _check_inventory(state: Mapping[str, Any], record: Mapping[str, Any], event: Mapping[str, Any], context) -> None:
    """LR-011's replay checks (§6.2)."""

    registration = _recorded(state, "legacy_path_registration", record.get("registration_ref"))
    if registration.get("role") == MANUSCRIPT_ROOT_ROLE:
        raise IntegrityError("W9 light inventory cannot target a legacy_manuscript_root registration")
    _source_matches_registration(record.get("source_identity", {}), registration, context)
    if event.get("actor_id") != record.get("observer_actor_id"):
        raise IntegrityError("W9 inventory observer is not the event's actor")
    rows = record.get("rows", [])
    if [row.get("row_ordinal") for row in rows] != list(range(1, len(rows) + 1)):
        raise IntegrityError("W9 inventory row ordinals do not run 1 to n")
    # Every row repeating the inventory's selector kind is the record schema's rule (its allOf), checked by the same
    # replay step before this reducer runs.
    if _time(record.get("read_ended_at")) < _time(record.get("read_started_at")):
        raise IntegrityError("W9 inventory read ends before it starts")


# --- The closed-reference acceptance (WP9.3-2; note §10) -------------------------------------------------------------


def acceptance_observations(state: Mapping[str, Any], record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Each item's observation, resolved by §4.4: a recorded observation at its revision and recomputed hash."""

    items = record.get("items")
    if not isinstance(items, list):
        raise IntegrityError("W9 acceptance carries no items")
    return [
        _recorded(state, "legacy_observation", item.get("observation_ref") if isinstance(item, Mapping) else None)
        for item in items
    ]


def _whole_file(state: Mapping[str, Any], observation: Mapping[str, Any]) -> bool:
    """§10.5 (and WP9.4 §10.2 K reading 2): an observation covers the whole file when it is ``whole_file``, or a
    ``json_family_set`` naming every family of its accepted membership table — except for ``legacy_manuscript_root``
    member observations, which never cover the root itself."""

    reg_id = observation.get("registration_ref", {}).get("id")
    registration = state.get("records", {}).get("legacy_path_registration", {}).get(reg_id, {})
    if registration.get("role") == MANUSCRIPT_ROOT_ROLE:
        return False
    selector = observation.get("selector", {})
    if selector.get("selector_kind") == "whole_file":
        return True
    if selector.get("selector_kind") != "json_family_set":
        return False
    table = _recorded(state, "legacy_field_family_membership", selector.get("membership_ref"))
    return set(selector.get("family_names", [])) == {family.get("name") for family in table.get("families", [])}


def _batch_rules(state: Mapping[str, Any], record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """§10.1's batch rules, at LR-016 and again at LR-020 (review M-1). Returns the items' observations."""

    if state["records"].get(ACCEPTANCE):
        raise IntegrityError("W9 acceptance after the first batch needs the integration-pilot outcome Decision")
    observations = acceptance_observations(state, record)
    if not 1 <= len(observations) <= MAX_BATCH_ITEMS:
        raise IntegrityError("W9 acceptance batch must hold 1 to 20 items")
    ids = [observation["record_id"] for observation in observations]
    if len(set(ids)) != len(ids):
        raise IntegrityError("W9 acceptance batch names an observation twice")
    for observation in observations:
        observation_id = observation["record_id"]
        if observation_id in state["stale_observations"]:
            raise IntegrityError("W9 acceptance item's observation is stale")
        registration_id = observation["registration_ref"]["id"]
        registration = state["records"]["legacy_path_registration"][registration_id]
        per_member = registration.get("role") == MANUSCRIPT_ROOT_ROLE
        _, obs_path = _source_location(observation["source_identity"])
        history = state["observations_by_registration"].get(registration_id, [])
        later = history[history.index(observation_id) + 1 :] if observation_id in history else []
        selector = _selector_key(observation.get("selector"))
        if any(
            (
                not per_member
                or _source_location(state["records"]["legacy_observation"][other]["source_identity"])[1] == obs_path
            )
            and _selector_key(state["records"]["legacy_observation"][other]["selector"]) == selector
            for other in later
        ):
            raise IntegrityError("W9 acceptance item's observation is not the latest for its source and selector")
    return observations


def _selector_key(selector: Any) -> Any:
    """A selector compared as §8.2 reads it: a ``json_family_set`` names a set of families, so their order is not
    part of the selector (as in ``_check_selector`` and ``_whole_file``). Every other field compares as recorded."""

    if not isinstance(selector, Mapping) or selector.get("selector_kind") != "json_family_set":
        return selector
    names = selector.get("family_names")
    if not isinstance(names, list):
        return dict(selector)
    return {**selector, "family_names": sorted({str(name) for name in names})}


def _check_pilot_promotion(item: Mapping[str, Any]) -> None:
    """§10.2 (O-37): each fixture at most once, the four unconditional fixtures, the ref kinds, and LR-020's seven."""

    entries = item.get("pilot_promotion")
    if not isinstance(entries, list):
        raise IntegrityError("W9 acceptance item carries no pilot_promotion list")
    fixtures = [entry.get("fixture_id") for entry in entries]
    if len(set(fixtures)) != len(fixtures):
        raise IntegrityError("W9 acceptance item lists a fixture twice")
    outside = sorted(str(fixture) for fixture in set(fixtures) - PILOT_FIXTURES)
    if outside:
        raise IntegrityError(f"W9 acceptance item lists a fixture LR-020 does not name: {outside[0]}")
    missing = [fixture for fixture in UNCONDITIONAL_FIXTURES if fixture not in fixtures]
    if missing:
        raise IntegrityError(f"W9 acceptance item lacks the unconditional fixture {missing[0]}")
    for entry in entries:
        ref_id = str(entry.get("ref", {}).get("id"))
        if entry.get("disposition") == "waiver" and not ref_id.startswith("dec_"):
            raise IntegrityError("W9 pilot_promotion waiver ref must be a Decision")
        if entry.get("disposition") == "evidence" and not ref_id.startswith(("rev_", "art_")):
            raise IntegrityError("W9 pilot_promotion evidence ref must be a review or an artefact")


def check_acceptance(state: Mapping[str, Any], record: Mapping[str, Any], context: Mapping[str, Any]) -> None:
    """LR-016's replay checks (§6.2, §10.1, §10.2, §10.3, §10.4, §10.5). The window, the anchors' Git facts and the
    change list's contents are the preparer's (§7.2, §10.3, §10.4)."""

    if state["catalogue"] is None:
        raise IntegrityError("W9 acceptance requires W9 genesis")
    if not context.get("pinned_signatures"):
        raise IntegrityError("W9 acceptance requires a pinned W0 signature")
    observations = _batch_rules(state, record)
    for item in record["items"]:
        _check_pilot_promotion(item)
    for anchor in record.get("anchors", []):
        if anchor.get("anchor_kind") != "git_commit":
            raise IntegrityError("W9 acceptance anchor must be a git_commit anchor (owner point G)")
    if record.get("enforcement_change_list") is None:
        raise IntegrityError("W9 acceptance names no shared-surface change list")
    whole = [str(o["registration_ref"]["id"]) for o in observations if _whole_file(state, o)]
    if len(set(whole)) != len(whole):
        raise IntegrityError("W9 acceptance batch holds two whole-file items of one registration")


def derive_ownership(state: Mapping[str, Any], record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """§10.5 (owner point E; P-081 item 5): the ownership records LR-020 will emit, as a function of the acceptance and
    the projection at this position. One per whole-file item whose registration is ``legacy_owned``, in item order."""

    transitions = []
    for observation in acceptance_observations(state, record):
        registration_ref = observation["registration_ref"]
        registration_id = str(registration_ref["id"])
        registration = state["records"]["legacy_path_registration"][registration_id]
        mode = state["ownership"].get(registration_id, registration.get("ownership_mode"))
        if not _whole_file(state, observation) or mode != "legacy_owned":
            continue
        transition: dict[str, Any] = {
            "schema_id": "ars://legacy/legacy-ownership-transitioned",
            "schema_version": "1.0.0",
            "record_id": ownership_record_id(str(record["record_id"]), registration_id, str(record["created_at"])),
            "record_revision": 1,
            "supersedes_revision": None,
            "project_id": record.get("project_id"),
            "created_at": record.get("created_at"),
            "created_by_actor_id": record.get("created_by_actor_id"),
            "mapping_ref": None,
            "subject_registration_ref": deepcopy(dict(registration_ref)),
            "paper_root_ref": None,
            "from_mode": "legacy_owned",
            "to_mode": "closed_reference",
            "reviewer_ref": deepcopy(record.get("independent_review_ref")),
            "decision_ref": deepcopy(record.get("decision_ref")),
        }
        transition["content_hash"] = record_content_hash(transition)
        transitions.append(transition)
    return transitions


def _reserve_ownership(state: dict[str, Any], ownership_id: str, record_id: str, context: Mapping[str, Any]) -> None:
    """§4.3: a batch's ownership record IDs are derived and reserved at LR-016."""

    if ownership_id in RESERVED_IDS or ownership_id in state["identities"] or ownership_id in state["reservations"]:
        raise IntegrityError("W9 ownership record ID is already claimed or reserved")
    _refuse_foreign(ownership_id, context)
    state["reservations"][ownership_id] = {"kind": "ownership", "proposal": record_id, "used": False}


def batch_observers(state: Mapping[str, Any], proposal: Mapping[str, Any]) -> set[Any]:
    """The observers of a batch's items, whom LR-017's reviewer may not be (§5.5, §6.2 LR-017)."""

    return {observation.get("observer_actor_id") for observation in acceptance_observations(state, proposal["record"])}


def _check_acceptance_resolution(
    state: Mapping[str, Any], decision: Mapping[str, Any], transaction: Sequence[Mapping[str, Any]]
) -> None:
    """LR-020 beyond G5 (§6.2, §10.5, §10.6): the batch rules again, and the ownership records exactly the stored list
    and the list recomputed here, each on its own stream at version 1, carrying the acceptance's refs."""

    record_id = decision["subject"][0]
    proposal = state["proposals"][record_id]
    record = transaction[1]["payload"]
    _batch_rules(state, record)
    emitted = [event["payload"] for event in transaction[2:]]
    for event, transition in zip(transaction[2:], emitted, strict=True):
        if transition.get("reviewer_ref") != record.get("independent_review_ref") or transition.get(
            "decision_ref"
        ) != record.get("decision_ref"):
            raise IntegrityError("W9 ownership record's copied refs are not the acceptance's")
        _require_stream(event, transition.get("record_id"), 1, "ownership record")
    if emitted != proposal.get("ownership"):
        raise IntegrityError("W9 acceptance's ownership records differ from the list stored at LR-016")
    if derive_ownership(state, record) != proposal["ownership"]:
        raise IntegrityError("W9 acceptance's ownership list recomputed at LR-020 differs from the stored list")


# --- Adoption and discharge (WP9.4-1; note §5 to §8) --------------------------------------------------------------------


def _is_claim_or_manuscript_use(record: Mapping[str, Any]) -> bool:
    desc = str(record.get("intended_use", {}).get("description", ""))
    return desc.startswith((MANUSCRIPT_USE_PREFIX, CLAIM_USE_PREFIX))


def _parse_use(intended_use: Mapping[str, Any]) -> str:
    """Validate §6.2's intended-use forms and ``successor_ref`` rules (owner point F)."""

    desc = intended_use.get("description")
    succ = intended_use.get("successor_ref")
    if isinstance(desc, str) and desc.startswith(MANUSCRIPT_USE_PREFIX):
        key = desc.removeprefix(MANUSCRIPT_USE_PREFIX)
        if key not in USE_PAPER_KEYS:
            raise IntegrityError("W9 adoption manuscript-claims key must be P01-A or P01-B")
        if succ is not None:
            raise IntegrityError("W9 adoption intended_use successor_ref is not permitted for this use")
        return "manuscript"
    if isinstance(desc, str) and desc.startswith(TASK_USE_PREFIX):
        key = desc.removeprefix(TASK_USE_PREFIX)
        if not USE_KEY_RE.match(key):
            raise IntegrityError("W9 adoption use key is malformed")
        if succ is not None and not (isinstance(succ, Mapping) and str(succ.get("id", "")).startswith("tsk_")):
            raise IntegrityError("W9 adoption intended_use successor_ref is not permitted for this use")
        return "task_input"
    if isinstance(desc, str) and desc.startswith(CLAIM_USE_PREFIX):
        key = desc.removeprefix(CLAIM_USE_PREFIX)
        if not USE_KEY_RE.match(key):
            raise IntegrityError("W9 adoption use key is malformed")
        if succ is not None:
            raise IntegrityError("W9 adoption intended_use successor_ref is not permitted for this use")
        return "claim_evidence"
    raise IntegrityError("W9 adoption intended_use description is not a permitted use form")


def _check_adoption_proposal(state: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    """LR-023's replay checks (§6.1 to §6.3, §6.5, §7)."""

    obs_ref = record.get("observation_ref")
    obs = _recorded(state, "legacy_observation", obs_ref)
    obs_id = obs["record_id"]
    if obs_id in state["supersessions"]:
        raise IntegrityError("W9 adoption observation is superseded")
    matching_acceptances = [
        acc_id
        for acc_id, acc in state["records"].get(ACCEPTANCE, {}).items()
        if any(
            isinstance(item.get("observation_ref"), Mapping) and item["observation_ref"].get("id") == obs_id
            for item in acc.get("items", ())
        )
    ]
    if not matching_acceptances:
        raise IntegrityError("W9 adoption observation has no recorded closed-reference acceptance")
    if any(acc_id in state["supersessions"] for acc_id in matching_acceptances):
        raise IntegrityError("W9 adoption observation acceptance is superseded")

    selector = obs.get("selector", {})
    selector_kind = selector.get("selector_kind")
    if selector_kind == "inventory_item":
        raise IntegrityError("W9 inventory item observation cannot be adopted")

    subject = record.get("subject", {})
    subject_kind = subject.get("subject_kind")
    if subject_kind == "families":
        if selector_kind != "json_family_set":
            raise IntegrityError("W9 family adoption requires a json_family_set observation")
        obs_families = {family.get("family_name") for family in obs.get("families", ())}
        if not set(subject.get("family_names", ())) <= obs_families:
            raise IntegrityError("W9 adoption names a family not in its observation")
    elif subject_kind == "whole_file":
        if selector_kind != "whole_file":
            raise IntegrityError("W9 whole-file adoption requires a whole_file observation")
        reg = state["records"]["legacy_path_registration"][obs["registration_ref"]["id"]]
        _, source_path = _source_location(obs["source_identity"])
        if any(
            isinstance(path, str) and path.lower().endswith(".json")
            for path in (reg.get("normalized_path"), source_path)
        ):
            raise IntegrityError("W9 whole-file adoption cannot name a .json source")

    use_kind = _parse_use(record.get("intended_use", {}))
    obs_open = [q for q in obs.get("qualifiers", ()) if q.get("qualifier_kind") == "open_review_finding"]
    obs_open_canon = {canonical_bytes(q) for q in obs_open}
    declared = record.get("qualifiers_to_discharge", ())
    declared_canon = [canonical_bytes(q) for q in declared]
    if len(declared_canon) != len(set(declared_canon)):
        raise IntegrityError("W9 adoption qualifiers_to_discharge repeats a qualifier")
    if use_kind in {"manuscript", "claim_evidence"}:
        if obs_open_canon:
            raise IntegrityError("W9 claim-use adoption refused while observation has open review findings")
        if declared:
            raise IntegrityError("W9 claim-use adoption must carry no qualifiers_to_discharge")
        if record.get("w5_consequence") != "admissible_for_named_use":
            raise IntegrityError("W9 adoption w5_consequence must be admissible_for_named_use")
    else:
        if set(declared_canon) != obs_open_canon:
            raise IntegrityError(
                "W9 task-input adoption qualifiers_to_discharge must equal observation open review findings"
            )
        expected_consequence = "task_input_with_open_findings" if obs_open_canon else "admissible_for_named_use"
        if record.get("w5_consequence") != expected_consequence:
            raise IntegrityError(f"W9 adoption w5_consequence must be {expected_consequence}")

    cause = adoption_suspension_cause(state, record)
    if cause is not None:
        raise IntegrityError(f"W9 adoption would be suspended at proposal: {cause}")


def _check_discharge_proposal(state: Mapping[str, Any], record: Mapping[str, Any], at: datetime) -> None:
    """LR-030's replay checks (§8): at most one open or non-superseded recorded relation per ``(item_kind, item_id)``."""

    item = record.get("legacy_item", {})
    key = (item.get("item_kind"), item.get("item_id"))
    for proposal in state["proposals"].values():
        if proposal.get("kind") == DISCHARGE and proposal_open(proposal, at):
            other = proposal["record"].get("legacy_item", {})
            if (other.get("item_kind"), other.get("item_id")) == key:
                raise IntegrityError("W9 discharge relation already open for this legacy item")
    for rec_id, other_record in state["records"].get(DISCHARGE, {}).items():
        if rec_id in state["supersessions"]:
            continue
        other = other_record.get("legacy_item", {})
        if (other.get("item_kind"), other.get("item_id")) == key:
            raise IntegrityError("W9 legacy item already has a recorded discharge relation")


def _required_fixtures(resolution_row: str, record: Mapping[str, Any]) -> tuple[str, ...]:
    unconditional = _WP9_4_UNCONDITIONAL_FIXTURES[resolution_row]
    if resolution_row == "LR-029" and _is_claim_or_manuscript_use(record):
        return tuple(sorted((*unconditional, "F-019")))
    return unconditional


def _parse_applicable_fixtures(
    questions: Sequence[Any], resolution_row: str, record: Mapping[str, Any]
) -> tuple[str, ...]:
    """Validate and parse the ``w9-applicable-fixtures:...`` question entry on LR-026 and LR-031 (§5.4)."""

    matches = [q for q in questions if isinstance(q, str) and q.startswith(APPLICABLE_FIXTURES_PREFIX)]
    if len(matches) != 1:
        raise IntegrityError("W9 review request must carry one w9-applicable-fixtures entry")
    raw = matches[0].removeprefix(APPLICABLE_FIXTURES_PREFIX)
    if not raw:
        fixtures: tuple[str, ...] = ()
    else:
        parts = raw.split(",")
        if any(not part for part in parts) or parts != sorted(parts) or len(parts) != len(set(parts)):
            raise IntegrityError("W9 review request w9-applicable-fixtures entry is malformed or not sorted")
        fixtures = tuple(parts)
    allowed = _WP9_4_ALLOWED_FIXTURES[resolution_row]
    outside = sorted(set(fixtures) - allowed)
    if outside:
        raise IntegrityError(f"W9 review request lists a fixture {resolution_row} does not name: {outside[0]}")
    required = _required_fixtures(resolution_row, record)
    missing = [fixture for fixture in required if fixture not in fixtures]
    if missing:
        raise IntegrityError(f"W9 review request lacks required fixture {missing[0]}")
    if not any(isinstance(q, str) and not q.startswith(APPLICABLE_FIXTURES_PREFIX) and q.strip() for q in questions):
        raise IntegrityError("W9 review request carries no review question besides the applicable-fixtures entry")
    return fixtures


def _parse_fixture_refs(entries: Sequence[Any], resolution_row: str, record: Mapping[str, Any]) -> tuple[str, ...]:
    """Validate sorted ``w9-fixture:<fixture_id>:<ref_id>`` Decision entries against allowed and required fixtures."""

    seen: list[str] = []
    for entry in entries:
        if not isinstance(entry, str) or not entry.startswith(FIXTURE_REF_PREFIX):
            raise IntegrityError("W9 Decision fixture entry is malformed")
        rest = entry.removeprefix(FIXTURE_REF_PREFIX)
        fixture_id, sep, ref_id = rest.partition(":")
        if not sep or not fixture_id or not _FIXTURE_REF_ID_RE.match(ref_id):
            raise IntegrityError("W9 Decision fixture entry is malformed")
        seen.append(fixture_id)
    if len(seen) != len(set(seen)):
        raise IntegrityError("W9 Decision lists a fixture twice")
    if seen != sorted(seen):
        raise IntegrityError("W9 Decision fixture entries are not sorted")
    allowed = _WP9_4_ALLOWED_FIXTURES[resolution_row]
    outside = sorted(set(seen) - allowed)
    if outside:
        raise IntegrityError(f"W9 Decision lists a fixture {resolution_row} does not name: {outside[0]}")
    required = _required_fixtures(resolution_row, record)
    missing = [fixture for fixture in required if fixture not in seen]
    if missing:
        raise IntegrityError(f"W9 Decision lacks required fixture {missing[0]}")
    return tuple(seen)


def _parse_decision_tail(resolution_row: str, tail: Sequence[Any], record: Mapping[str, Any]) -> tuple[str, ...]:
    """Parse post-subject entries of a WP9.4 Decision (§5.4, §8, §10.5; WP9.4-2 record §3.1 item 4)."""

    if resolution_row in {"LR-034", "LR-054"}:
        if (
            not tail
            or not isinstance(tail[-1], str)
            or not tail[-1].startswith(OPEN_ITEMS_BLOB_PREFIX)
            or not _SHA1_RE.match(tail[-1].removeprefix(OPEN_ITEMS_BLOB_PREFIX))
        ):
            label = "discharge" if resolution_row == "LR-034" else resolution_row
            raise IntegrityError(f"W9 {label} Decision must carry one valid w9-open-items-blob entry")
        return _parse_fixture_refs(tail[:-1], resolution_row, record)
    return _parse_fixture_refs(tail, resolution_row, record)


def _pilot_outcome_passed(state: Mapping[str, Any]) -> bool:
    """Return whether a passed integration-pilot outcome Decision (LR-022) is recorded (§10.1, §10.5)."""

    return any(
        decision.get("resolve_row") == "LR-022"
        and decision.get("decision_kind") == "result_interpretation"
        and decision.get("selected_option") == "passed"
        for decision in state.get("decisions", {}).values()
    )


def _accepted_observation_ids(state: Mapping[str, Any]) -> set[str]:
    supersessions = state.get("supersessions", {})
    accepted: set[str] = set()
    for acc_id, acc in state.get("records", {}).get(ACCEPTANCE, {}).items():
        if acc_id in supersessions:
            continue
        for item in acc.get("items", ()):
            obs_ref = item.get("observation_ref")
            if isinstance(obs_ref, Mapping):
                obs_id = obs_ref.get("id")
                if isinstance(obs_id, str) and obs_id not in supersessions:
                    accepted.add(obs_id)
    return accepted


def _check_source_inventory(
    state: Mapping[str, Any], record: Mapping[str, Any], event: Mapping[str, Any] | None
) -> None:
    """LR-040 & LR-044 replay checks (WP9.4 note §10.3)."""

    reg_ref = record.get("root_registration_ref")
    reg = _recorded(state, "legacy_path_registration", reg_ref)
    reg_id = str(reg["record_id"])
    supersessions = state.get("supersessions", {})
    if reg_id in supersessions:
        raise IntegrityError("W9 source inventory names a superseded root registration")
    if reg.get("role") != MANUSCRIPT_ROOT_ROLE:
        raise IntegrityError("W9 source inventory registration must have role legacy_manuscript_root")
    current_mode = state["ownership"].get(reg_id, reg.get("ownership_mode"))
    if current_mode != "legacy_owned":
        raise IntegrityError("W9 source inventory root registration is not legacy_owned")
    if event is not None and event.get("actor_id") != record.get("observer_actor_id"):
        raise IntegrityError("W9 source inventory observer is not the event's actor")

    rows = record.get("rows", [])
    if [row.get("row_ordinal") for row in rows] != list(range(1, len(rows) + 1)):
        raise IntegrityError("W9 source inventory row ordinals do not run 1 to n")
    root_path = str(reg.get("normalized_path", ""))
    root_prefix = root_path if root_path.endswith("/") else f"{root_path}/"
    accepted_obs_ids = _accepted_observation_ids(state)
    seen_paths: set[str] = set()
    for row in rows:
        repo_path = str(row.get("repository_path", ""))
        if repo_path in seen_paths:
            raise IntegrityError("W9 source inventory repeats a repository_path")
        if not repo_path.startswith(root_prefix) or len(repo_path) <= len(root_prefix) or repo_path.endswith("/"):
            raise IntegrityError("W9 source inventory row path is not strictly under its root")
        seen_paths.add(repo_path)
        obs = _recorded(state, "legacy_observation", row.get("observation_ref"))
        obs_id = str(obs["record_id"])
        if obs_id in supersessions:
            raise IntegrityError("W9 source inventory row observation is superseded")
        if obs_id not in accepted_obs_ids:
            raise IntegrityError("W9 source inventory row observation is not in a closed-reference acceptance")
        if obs.get("registration_ref", {}).get("id") != reg_id:
            raise IntegrityError("W9 source inventory row observation names another registration")
        if obs.get("selector", {}).get("selector_kind") != "whole_file":
            raise IntegrityError("W9 source inventory row observation is not whole_file")
        source = obs.get("source_identity", {})
        if (
            source.get("identity_kind") != "git_tracked"
            or source.get("repository_path") != repo_path
            or source.get("git_blob") != row.get("git_blob")
        ):
            raise IntegrityError("W9 source inventory row differs from its observation's path or blob")


def _check_transition_mapping(
    state: Mapping[str, Any], record: Mapping[str, Any], event: Mapping[str, Any] | None
) -> None:
    """LR-045 & LR-049 replay checks (WP9.4 note §10.4)."""

    supersessions = state.get("supersessions", {})
    inv = _recorded(state, SOURCE_INVENTORY, record.get("source_inventory_ref"))
    inv_id = str(inv["record_id"])
    if inv_id in supersessions:
        raise IntegrityError("W9 mapping names a superseded source inventory")
    root = _recorded(state, PAPER_ROOT, record.get("target_paper_root_ref"))
    root_id = str(root["record_id"])
    if root_id in supersessions:
        raise IntegrityError("W9 mapping names a superseded paper root")
    inv_reg = _recorded(state, "legacy_path_registration", inv.get("root_registration_ref"))
    if root.get("manuscript_root_path") != inv_reg.get("normalized_path"):
        raise IntegrityError("W9 mapping target paper root path differs from inventory root registration path")
    if event is not None and event.get("actor_id") != record.get("analyst_actor_id"):
        raise IntegrityError("W9 mapping analyst is not the event's actor")
    ordinals = record.get("mapped_row_ordinals", [])
    inv_ordinals = {row.get("row_ordinal") for row in inv.get("rows", ())}
    if not ordinals or len(ordinals) != len(set(ordinals)) or not set(ordinals) <= inv_ordinals:
        raise IntegrityError("W9 mapping mapped_row_ordinals must be a unique non-empty subset of inventory rows")


def _check_ownership_proposal(state: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    """LR-050 replay checks (WP9.4 note §10.5; W9-T5)."""

    from_mode, to_mode = record.get("from_mode"), record.get("to_mode")
    if (from_mode, to_mode) == ("legacy_owned", "closed_reference"):
        raise IntegrityError("W9 LR-050 refuses legacy_owned to closed_reference")
    res_row = ownership_resolution_row(record)
    supersessions = state.get("supersessions", {})
    subject_reg = _recorded(state, "legacy_path_registration", record.get("subject_registration_ref"))
    subject_id = str(subject_reg["record_id"])
    if subject_id in supersessions:
        raise IntegrityError("W9 ownership transition names a superseded registration")
    current = state["ownership"].get(subject_id, subject_reg.get("ownership_mode"))
    if from_mode != current or not ownership_transition_allowed(from_mode, to_mode):
        raise IntegrityError("W9 ownership transition is not allowed from the registration's current mode")
    if res_row == "LR-054":
        if subject_reg.get("role") != MANUSCRIPT_ROOT_ROLE:
            raise IntegrityError("W9 LR-054 subject registration must have role legacy_manuscript_root")
        mapping = _recorded(state, TRANSITION_MAPPING, record.get("mapping_ref"))
        mapping_id = str(mapping["record_id"])
        if mapping_id in supersessions:
            raise IntegrityError("W9 ownership transition names a superseded mapping")
        root = _recorded(state, PAPER_ROOT, record.get("paper_root_ref"))
        root_id = str(root["record_id"])
        if root_id in supersessions:
            raise IntegrityError("W9 ownership transition names a superseded paper root")
        if mapping.get("target_paper_root_ref", {}).get("id") != root_id:
            raise IntegrityError("W9 mapping target paper root differs from ownership paper_root_ref")
        inv = _recorded(state, SOURCE_INVENTORY, mapping.get("source_inventory_ref"))
        inv_id = str(inv["record_id"])
        if inv_id in supersessions:
            raise IntegrityError("W9 ownership transition mapping names a superseded inventory")
        if inv.get("root_registration_ref", {}).get("id") != subject_id or (
            subject_reg.get("normalized_path") != root.get("manuscript_root_path")
        ):
            raise IntegrityError("W9 ownership subject registration does not match mapping inventory root")


def _check_ownership_resolution(state: Mapping[str, Any], row_id: str, record: Mapping[str, Any]) -> None:
    """LR-054 and LR-055 replay checks at resolution (WP9.4 note §10.5, §11.3)."""

    if _ROW_DIRECTIONS.get(row_id) != (record.get("from_mode"), record.get("to_mode")):
        raise IntegrityError(f"W9 ownership transition differs from accepted {row_id}")
    _check_ownership_proposal(state, record)
    if row_id != "LR-054":
        return
    if not _pilot_outcome_passed(state):
        raise IntegrityError("W9 LR-054 requires a passed integration-pilot outcome Decision (LR-022)")
    root_id = str(record["paper_root_ref"]["id"])
    status_id = state.get("current_citation_status_by_root", {}).get(root_id)
    supersessions = state.get("supersessions", {})
    if status_id is None or status_id in supersessions:
        raise IntegrityError("W9 LR-054 requires a current citation status for the paper root")
    status = state["records"][CITATION_STATUS][status_id]
    derivation = status.get("derivation", {})
    if derivation.get("extractor_output_sha256") != derivation.get("reviewer_derivation_sha256"):
        raise IntegrityError("W9 LR-054 citation status extractor and reviewer derivations differ")
    for entry in status.get("families", ()):
        if entry.get("status") != "adopted":
            raise IntegrityError("W9 LR-054 citation status has an unadopted cited family")
        adoption = _recorded(state, ADOPTION, entry.get("adoption_ref"))
        if adoption_suspension_cause(state, adoption) is not None:
            raise IntegrityError("W9 LR-054 citation status cites a suspended adoption")
    mapping = _recorded(state, TRANSITION_MAPPING, record.get("mapping_ref"))
    inv = _recorded(state, SOURCE_INVENTORY, mapping.get("source_inventory_ref"))
    status_actors = {status.get("created_by_actor_id"), derivation.get("reviewer_actor_id")}
    producers = {record.get("created_by_actor_id"), mapping.get("analyst_actor_id"), inv.get("observer_actor_id")}
    if status_actors & producers:
        raise IntegrityError("W9 citation status reviewer is not independent of the transition's producers")


def _check_paper_root_lr035(
    state: Mapping[str, Any], record: Mapping[str, Any], event: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    """LR-035 replay checks (WP9.4 note §10.1)."""

    record_id = record.get("record_id")
    if isinstance(record_id, str):
        _refuse_foreign(record_id, context)
    _require_stream(event, record_id, 1, "paper root")
    _created_fields(record, event)
    if record.get("recovery") is not None:
        raise IntegrityError("W9 LR-035 refuses a recovery paper root")
    if not _pilot_outcome_passed(state):
        raise IntegrityError("W9 LR-035 requires a passed integration-pilot outcome Decision (LR-022)")
    supersessions = state.get("supersessions", {})
    for existing_id, existing in state.get("records", {}).get(PAPER_ROOT, {}).items():
        if existing_id not in supersessions and existing.get("paper_key") == record.get("paper_key"):
            raise IntegrityError("W9 paper root already exists for this paper_key")


def _adoption_covers_cited_family(
    adoption: Mapping[str, Any], obs_id: str, family_name: str, expected_use: str
) -> bool:
    if adoption.get("observation_ref", {}).get("id") != obs_id:
        return False
    if adoption.get("intended_use", {}).get("description") != expected_use:
        return False
    subject = adoption.get("subject", {})
    if family_name == "whole_file":
        return subject.get("subject_kind") == "whole_file"
    return subject.get("subject_kind") == "families" and family_name in subject.get("family_names", ())


def _check_citation_status_lr039(
    state: Mapping[str, Any], record: Mapping[str, Any], event: Mapping[str, Any], context: Mapping[str, Any]
) -> None:
    """LR-039 replay checks (WP9.4 note §5.6, §11.3)."""

    _created_fields(record, event)
    supersessions = state.get("supersessions", {})
    root = _recorded(state, PAPER_ROOT, record.get("root_ref"))
    root_id = str(root["record_id"])
    if root_id in supersessions:
        raise IntegrityError("W9 citation status names a superseded paper root")
    derivation = record.get("derivation", {})
    root_creator = root.get("created_by_actor_id")
    if event.get("actor_id") == root_creator or derivation.get("reviewer_actor_id") == root_creator:
        raise IntegrityError("W9 citation status submitter or reviewer is the paper root's creator")
    if derivation.get("reviewer_actor_id") != event.get("actor_id"):
        raise IntegrityError("W9 citation status reviewer_actor_id is not the event's actor")

    current_status_id = state.get("current_citation_status_by_root", {}).get(root_id)
    sup_ref = record.get("supersedes_status_ref")
    if current_status_id is None:
        if sup_ref is not None:
            raise IntegrityError("W9 citation status supersedes_status_ref must be null when root has no prior status")
        supersedes_id = None
    else:
        cur = state["records"][CITATION_STATUS][current_status_id]
        if (
            not isinstance(sup_ref, Mapping)
            or sup_ref.get("id") != current_status_id
            or sup_ref.get("record_revision") != cur.get("record_revision")
            or sup_ref.get("content_hash") != cur.get("content_hash")
        ):
            raise IntegrityError(
                "W9 citation status supersedes_status_ref must name the root's current citation status"
            )
        supersedes_id = current_status_id

    families = record.get("families", ())
    pairs = [(str(entry.get("observation_ref", {}).get("id")), str(entry.get("family_name"))) for entry in families]
    if len(pairs) != len(set(pairs)):
        raise IntegrityError("W9 citation status repeats an (observation, family) pair")
    expected_set_sha = sha256_hex(canonical_bytes(sorted([obs_id, fname] for obs_id, fname in pairs)))
    if record.get("cited_family_set_sha256") != expected_set_sha:
        raise IntegrityError("W9 citation status cited_family_set_sha256 differs from families")

    accepted_obs_ids = _accepted_observation_ids(state)
    expected_use = f"{MANUSCRIPT_USE_PREFIX}{root.get('paper_key')}"
    adoptions = state.get("records", {}).get(ADOPTION, {})
    for entry in families:
        obs = _recorded(state, "legacy_observation", entry.get("observation_ref"))
        obs_id = str(obs["record_id"])
        if obs_id in supersessions or obs_id not in accepted_obs_ids:
            raise IntegrityError("W9 citation status cites a superseded or unaccepted observation")
        fname = str(entry.get("family_name"))
        sel = obs.get("selector", {})
        sel_kind = sel.get("selector_kind")
        if sel_kind == "whole_file":
            family_in_obs = fname == "whole_file"
        else:
            family_in_obs = (
                sel_kind == "json_family_set" and fname != "whole_file" and fname in sel.get("family_names", ())
            )
        if not family_in_obs:
            raise IntegrityError("W9 citation status family does not belong to the cited observation")
        if entry.get("status") == "adopted":
            adoption = _recorded(state, ADOPTION, entry.get("adoption_ref"))
            if not _adoption_covers_cited_family(adoption, obs_id, fname, expected_use):
                raise IntegrityError(
                    "W9 citation status adoption does not cover the cited observation, family, or paper"
                )
            if adoption_suspension_cause(state, adoption) is not None:
                raise IntegrityError("W9 citation status cites a suspended adoption")
        else:
            if entry.get("adoption_ref") is not None:
                raise IntegrityError("W9 citation status unadopted family must carry null adoption_ref")
            if any(
                _adoption_covers_cited_family(adp, obs_id, fname, expected_use)
                and adoption_suspension_cause(state, adp) is None
                for adp in adoptions.values()
            ):
                raise IntegrityError("W9 citation status marks an actively adopted family as unadopted")

    derived = citation_status_record_id(
        root_id,
        supersedes_id,
        str(record.get("cited_family_set_sha256")),
        str(derivation.get("extractor_output_sha256")),
        str(derivation.get("reviewer_derivation_sha256")),
        str(root.get("created_at")),
    )
    if record.get("record_id") != derived:
        raise IntegrityError("W9 citation status record_id is not derived from its subject")
    _refuse_foreign(derived, context)
    _require_stream(event, derived, 1, "citation status")


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
    if row_id in CHECKED_ROWS:
        if isinstance(record_id, str):
            _refuse_foreign(record_id, context)
        _require_stream(event, record_id, 1, "proposal")
        _created_fields(record, event)
        _check_pre_assigned(record, kind)
        if kind == "legacy_path_registration":
            _check_registration(state, record, at)
        elif kind == "legacy_field_family_membership":
            _check_membership(record, event)
        elif kind == "legacy_light_inventory":
            _check_inventory(state, record, event, context)
        elif kind == ACCEPTANCE:
            check_acceptance(state, record, context)
        elif kind == ADOPTION:
            _check_adoption_proposal(state, record)
        elif kind == DISCHARGE:
            _check_discharge_proposal(state, record, at)
        elif kind == SOURCE_INVENTORY:
            _check_source_inventory(state, record, event)
        elif kind == TRANSITION_MAPPING:
            _check_transition_mapping(state, record, event)
        elif kind == OWNERSHIP:
            _check_ownership_proposal(state, record)
    claim_identity(state, record_id, "proposal", context)
    ownership: list[dict[str, Any]] = []
    if row_id in CHECKED_ROWS:
        for field, ref_kind in PRE_ASSIGNED_REFS.get(kind, {}).items():
            _reserve(state, record[field]["id"], ref_kind, str(record_id), context)
        if kind == ADOPTION:
            _reserve(
                state,
                adoption_review_id(str(record_id), str(record["created_at"])),
                "review",
                str(record_id),
                context,
            )
            _reserve(
                state,
                adoption_eligibility_decision_id(str(record_id), str(record["created_at"])),
                "decision",
                str(record_id),
                context,
            )
        if kind == ACCEPTANCE:
            # §10.5 (owner point E): derived from the proposal and the ledger before it, reserved, and stored with it.
            ownership = derive_ownership(state, record)
            for transition in ownership:
                _reserve_ownership(state, transition["record_id"], str(record_id), context)
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
    if kind == ACCEPTANCE and row_id in WP9_3_ROWS:
        state["proposals"][record_id]["ownership"] = ownership


# --- Reviews (§5.2, §5.4, §5.5) --------------------------------------------------------------------------------------


def _session_refs(refs: Any, row_id: str) -> tuple[list[str], str | None]:
    """``required_evidence_refs``: excluded sessions and, for LR-026, the separate eligible session (§5.5, C-m1)."""

    prefixes = [ANALYST_SESSION_PREFIX]
    if row_id == "LR-007":
        prefixes.append(AUTHOR_SESSION_PREFIX)
    elif row_id == "LR-026":
        prefixes.append(ELIGIBLE_SESSION_PREFIX)
    if not isinstance(refs, list) or len(refs) != len(prefixes):
        raise IntegrityError("W9 review request session refs are not the required count")
    values = []
    for ref, prefix in zip(refs, prefixes, strict=True):
        if not isinstance(ref, str) or not ref.startswith(prefix) or not ref.removeprefix(prefix):
            raise IntegrityError("W9 review request session ref is malformed or empty")
        values.append(ref.removeprefix(prefix))
    if row_id == "LR-026":
        return [values[0]], values[1]
    return values, None


def _creator_role_actor(proposal: Mapping[str, Any]) -> Any:
    """The creator §5.5's analyst rule names: an observer (LR-011, LR-040) or a membership author (LR-006)."""

    record = proposal["record"]
    if proposal["kind"] == "legacy_field_family_membership":
        return record.get("author_actor_id")
    if proposal["kind"] in {"legacy_light_inventory", "legacy_source_inventory"}:
        return record.get("observer_actor_id")
    return None


def _refuse_analyst_creator(proposal: Mapping[str, Any], analyst: Any) -> None:
    """§5.3, §5.5: the analyst who requests a review or proposes a Decision is not the creator, except for the
    analyst's own proposals."""

    if proposal["kind"] not in {
        "legacy_path_registration",
        ACCEPTANCE,
        ADOPTION,
        DISCHARGE,
        "legacy_transition_mapping",
        OWNERSHIP,
    } and analyst in {
        proposal["actor_id"],
        _creator_role_actor(proposal),
    }:
        raise IntegrityError("W9 analyst is the proposal's creator")


def _check_review_request(
    state: dict[str, Any], row_id: str, event: Mapping[str, Any], payload: Mapping[str, Any], at: datetime
) -> tuple[str, list[str], str, str | None, Mapping[str, Any] | None, tuple[str, ...] | None]:
    """Review request replay checks (WP9.3 §5.2, §5.5, §6.2; WP9.4 §5.2 to §5.5)."""

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
    if review_id != review_id_for(kind, proposal["record"]):
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
    if not isinstance(questions, list) or not questions or any(not isinstance(q, str) or not q for q in questions):
        raise IntegrityError("W9 review request carries no review question")
    reviewers = payload.get("reviewer_capability")
    if not isinstance(reviewers, list) or len(reviewers) != 1 or not isinstance(reviewers[0], str):
        raise IntegrityError("W9 review request must name exactly one reviewer")
    sessions, eligible_session = _session_refs(payload.get("required_evidence_refs"), row_id)
    eligibility: Mapping[str, Any] | None = None
    if row_id == "LR-026":
        elig_id = adoption_eligibility_decision_id(str(record_id), str(proposal["record"]["created_at"]))
        elig_decision = state["decisions"].get(elig_id)
        if (
            elig_decision is None
            or elig_decision.get("resolve_row") != "LR-025"
            or elig_decision.get("selected_option") != "accept"
        ):
            raise IntegrityError("W9 adoption review requires an accepted eligibility Decision")
        if elig_decision.get("subject") != (record_id, proposal["content_hash"]):
            raise IntegrityError("W9 eligibility Decision does not match the adoption proposal")
        eligibility = elig_decision["eligibility"]
        if eligible_session != eligibility["session"]:
            raise IntegrityError("W9 adoption review request eligible session differs from the eligibility Decision")
        if eligible_session in sessions:
            raise IntegrityError("W9 adoption review request names the analyst session as the eligible session")
    applicable_fixtures: tuple[str, ...] | None = None
    resolution_row = _resolution_row_for(row_id, proposal["record"])
    if resolution_row is not None:
        applicable_fixtures = _parse_applicable_fixtures(questions, resolution_row, proposal["record"])
    analyst, reviewer = event.get("actor_id"), reviewers[0]
    creator = proposal["actor_id"]
    _refuse_analyst_creator(proposal, analyst)
    excluded = {creator, analyst, _creator_role_actor(proposal)}
    if reviewer in excluded:
        raise IntegrityError("W9 reviewer is the proposal's creator, author or the requesting analyst")
    if proposal["kind"] == ACCEPTANCE and reviewer in batch_observers(state, proposal):
        raise IntegrityError("W9 acceptance reviewer observed an item of the batch")
    _require_stream(event, review_id, 1, "review request")
    _take_reservation(state, review_id, "review", str(record_id), "review")
    return str(record_id), sessions, reviewer, eligible_session, eligibility, applicable_fixtures


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
    if row_id in CHECKED_ROWS:
        record_id, sessions, reviewer, eligible_session, eligibility, applicable_fixtures = _check_review_request(
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
        if eligible_session is not None and eligibility is not None:
            entry["eligible_session"] = eligible_session
            entry["eligibility"] = dict(eligibility)
        if applicable_fixtures is not None:
            entry["applicable_fixtures"] = applicable_fixtures
    else:
        claim_identity(state, review_id, "review", context)
    state["reviews"][review_id] = entry


def _check_verdict(
    state: Mapping[str, Any], review: Mapping[str, Any], event: Mapping[str, Any], payload: Mapping[str, Any]
) -> None:
    """Review verdict replay checks (WP9.3 §5.2; WP9.4 §5.5; W9-C21, W9-C22)."""

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
    is_adoption = review.get("request_row") == "LR-026"
    expected_profile = review["eligibility"]["profile"] if is_adoption else REVIEWER_PROFILE
    fixed = {
        "conditions": [],
        "required_evidence_refs": review["required_evidence_refs"],
        "reviewer_profile": expected_profile,
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
    if is_adoption:
        if session != review.get("eligible_session"):
            raise IntegrityError("W9 adoption verdict session differs from the eligible session")
        expected_model = f"{review['eligibility']['family']}@{review['eligibility']['version']}"
        if payload.get("reviewer_model_metadata") != expected_model:
            raise IntegrityError("W9 adoption verdict reviewer_model_metadata differs from the eligibility Decision")
    _require_stream(event, review_id, 2, "review verdict")


def reduce_review_verdict(
    state: dict[str, Any], row_id: str, transaction: Sequence[Mapping[str, Any]], context: Mapping[str, Any]
) -> None:
    """``RecordW9AuthorityReview``: record the one verdict on an open W9 review."""

    payload = _single(transaction)
    review = state["reviews"].get(payload.get("review_id"))
    if review is None or review["verdict_row"] is not None:
        raise IntegrityError("W9 review verdict has no open W9 review")
    if row_id in CHECKED_ROWS:
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


def _check_eligibility_proposal(
    state: dict[str, Any], event: Mapping[str, Any], payload: Mapping[str, Any]
) -> tuple[str, str, datetime, dict[str, str]]:
    """LR-024's replay checks (§5.5, owner point B): before any review exists."""

    at = _time(event.get("occurred_at"))
    refs = payload.get("governing_evidence_refs")
    expected_prefixes = (
        None,
        SUBJECT_PREFIX,
        SUBJECT_HASH_PREFIX,
        ELIGIBLE_SESSION_PREFIX,
        ELIGIBLE_FAMILY_PREFIX,
        ELIGIBLE_VERSION_PREFIX,
        ELIGIBLE_PROFILE_PREFIX,
        ELIGIBLE_GRADE_PREFIX,
    )
    if not isinstance(refs, list) or len(refs) != 8 or refs[0] != "W9:LR-024":
        raise IntegrityError("W9 eligibility Decision proposal must carry exactly 8 governing_evidence_refs")
    values: list[str] = []
    for ref, prefix in zip(refs[1:], expected_prefixes[1:], strict=True):
        if not isinstance(ref, str) or not ref.startswith(prefix) or not ref.removeprefix(prefix):
            raise IntegrityError("W9 eligibility Decision proposal governing_evidence_refs are malformed")
        values.append(ref.removeprefix(prefix))
    record_id, subject_hash, session, family, version, profile, grade = values
    if grade != INDEPENDENCE_GRADE:
        raise IntegrityError("W9 eligibility Decision grade must be independent")
    proposal = _open_proposal(state, record_id, ADOPTION, at)
    if subject_hash != proposal["content_hash"]:
        raise IntegrityError("W9 Decision proposal subject hash is not the proposal's current hash")
    decision_id = payload.get("new_decision_id")
    expected_id = adoption_eligibility_decision_id(record_id, str(proposal["record"]["created_at"]))
    if decision_id != expected_id:
        raise IntegrityError("W9 eligibility Decision ID is not the derived eligibility Decision ID")
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
    _refuse_analyst_creator(proposal, event.get("actor_id"))
    _require_stream(event, decision_id, 1, "Decision proposal")
    _take_reservation(state, decision_id, "decision", record_id, "decision")
    expires = at + PROPOSAL_TERM
    state["proposals"][record_id]["lapse_at"] = max(state["proposals"][record_id]["lapse_at"], expires)
    return (
        record_id,
        subject_hash,
        expires,
        {
            "session": session,
            "family": family,
            "version": version,
            "profile": profile,
            "grade": grade,
        },
    )


def _check_decision_proposal(
    state: dict[str, Any], row_id: str, event: Mapping[str, Any], payload: Mapping[str, Any]
) -> tuple[str, str, datetime]:
    """Decision proposal replay checks (WP9.3 §5.2; WP9.4 §5.2, §5.4, §8)."""

    at = _time(event.get("occurred_at"))
    refs = payload.get("governing_evidence_refs")
    if not isinstance(refs, list) or len(refs) < 3 or refs[0] != f"W9:{row_id}":
        raise IntegrityError("W9 Decision proposal does not encode its subject")
    if not (isinstance(refs[1], str) and refs[1].startswith(SUBJECT_PREFIX)) or not (
        isinstance(refs[2], str) and refs[2].startswith(SUBJECT_HASH_PREFIX)
    ):
        raise IntegrityError("W9 Decision proposal does not encode its subject")
    if row_id in WP9_3_ROWS and len(refs) != 3:
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
    review_id = review_id_for(kind, proposal["record"])
    if review_id is not NO_REVIEW_REQUIRED and not review_satisfied(
        state, review_id, record_id, proposal["content_hash"]
    ):
        raise IntegrityError("W9 Decision proposal has no satisfied review on the current hash")
    resolution_row = _resolution_row_for(row_id, proposal["record"])
    if resolution_row is not None:
        fixture_ids = _parse_decision_tail(resolution_row, refs[3:], proposal["record"])
        if review_id is not NO_REVIEW_REQUIRED and fixture_ids != state["reviews"][review_id]["applicable_fixtures"]:
            raise IntegrityError("W9 Decision proposal fixture set differs from the review's applicable fixtures")
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
        "decision_kind": payload.get("decision_kind"),
        "governing_evidence_refs": list(payload.get("governing_evidence_refs", [])),
    }
    if row_id == "LR-024":
        record_id, subject_hash, expires, eligibility = _check_eligibility_proposal(state, event, payload)
        entry.update(subject=(record_id, subject_hash), expires_at=expires, eligibility=eligibility)
    elif row_id in CHECKED_ROWS:
        record_id, subject_hash, expires = _check_decision_proposal(state, row_id, event, payload)
        entry.update(subject=(record_id, subject_hash), expires_at=expires)
    else:
        claim_identity(state, decision_id, "decision", context)
    state["decisions"][decision_id] = entry


def _decision_family(row_id: str) -> str:
    return LEGACY_ROW_ROUTES[row_id].payload_discriminant.split("/", 2)[1]


def _record_resolved(
    state: dict[str, Any],
    row_id: str,
    decision_id: str,
    record: Mapping[str, Any],
    context: Mapping[str, Any],
    subject_id: Any = None,
) -> str:
    """G5: bind a resolved record to its open proposal and to the resolving Decision.

    LR-020's ownership transitions are the exception: the acceptance writes one per accepted whole-file item, with no
    proposal of their own (P-072 item 2). Under WP9.3-2 each takes the reservation its acceptance made at LR-016
    (note §10.5, §14), where the list was derived and stored.
    """

    record_id = record.get("record_id")
    kind = record_kind(record.get("schema_id"))
    content_hash = require_content_hash(record)
    decision_ref = record.get(_DECISION_FIELDS.get(kind, "decision_ref"))
    if not isinstance(decision_ref, Mapping) or decision_ref.get("id") != decision_id:
        raise IntegrityError("W9 resolved record names another Decision")
    if row_id == "LR-020" and kind == OWNERSHIP:
        if row_id in WP9_3_ROWS:
            _take_reservation(state, record_id, "ownership", str(subject_id), kind)
        else:
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


def _check_eligibility_resolution(
    state: Mapping[str, Any], decision: Mapping[str, Any], transaction: Sequence[Mapping[str, Any]]
) -> str:
    """LR-025's record-less replay checks (§5.5, owner point B, R-M4)."""

    if len(transaction) != 1:
        raise IntegrityError("W9 eligibility resolution must not emit a record")
    event, payload = transaction[0], transaction[0]["payload"]
    at = _time(event.get("occurred_at"))
    selected = payload.get("selected_option")
    if selected not in DECISION_OPTIONS:
        raise IntegrityError("W9 eligibility resolution selected_option is not valid")
    record_id, _ = decision["subject"]
    fixed = {
        "selected_option": selected,
        "effective_scope": f"{EFFECTIVE_SCOPE_PREFIX}{record_id}",
        "decision_revision": 1,
        "deciding_actor_id": event.get("actor_id"),
        "decision_authority_grant_id": event.get("authority_grant_id"),
        "governing_evidence_refs": ["W9:LR-025", *decision["governing_evidence_refs"][1:]],
        "considered_review_ids": [],
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
    _require_stream(event, payload.get("decision_id"), 2, "Decision resolution")
    return str(selected)


def _check_resolution(
    state: Mapping[str, Any], row_id: str, decision: Mapping[str, Any], transaction: Sequence[Mapping[str, Any]]
) -> None:
    """G5 at resolution (§5.2, §6.1, §6.5, §8), including F-8's first limb."""

    event, payload = transaction[0], transaction[0]["payload"]
    at = _time(event.get("occurred_at"))
    record = transaction[1]["payload"]
    record_id, subject_hash = decision["subject"]
    if record.get("record_id") != record_id or record_content_hash(record) != subject_hash:
        raise IntegrityError("W9 resolved record is not its Decision's subject")
    kind = record_kind(record.get("schema_id"))
    review_id = review_id_for(kind, record)
    considered = [] if review_id is NO_REVIEW_REQUIRED else [review_id]
    fixed = {
        "selected_option": "accept",
        "effective_scope": f"{EFFECTIVE_SCOPE_PREFIX}{record_id}",
        "decision_revision": 1,
        "deciding_actor_id": event.get("actor_id"),
        "decision_authority_grant_id": event.get("authority_grant_id"),
        # The proposal's subject refs with its row ref replaced by the resolution row, so that row assignment, which
        # assigns a DecisionResolved by its one W9: ref, finds this row (Stephen, 2026-11-09, option A).
        "governing_evidence_refs": [f"W9:{row_id}", *decision["governing_evidence_refs"][1:]],
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
    if review_id is not NO_REVIEW_REQUIRED and not review_satisfied(state, considered[0], record_id, subject_hash):
        raise IntegrityError("W9 resolution's review is not satisfied on the record's hash")
    if row_id in _WP9_4_ALLOWED_FIXTURES:
        _parse_decision_tail(row_id, payload["governing_evidence_refs"][3:], record)
    if row_id == "LR-029":
        cause = adoption_suspension_cause(state, record)
        if cause is not None:
            raise IntegrityError(f"W9 adoption is suspended at resolution: {cause}")
    elif row_id == "LR-044":
        _check_source_inventory(state, record, None)
    elif row_id == "LR-049":
        _check_transition_mapping(state, record, None)
    elif row_id in {"LR-054", "LR-055"}:
        _check_ownership_resolution(state, row_id, record)
    _require_stream(event, payload.get("decision_id"), 2, "Decision resolution")
    _require_stream(transaction[1], record_id, 2, "resolved record")
    if kind == ACCEPTANCE:
        _check_acceptance_resolution(state, decision, transaction)


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
    if row_id == "LR-025":
        decision["selected_option"] = _check_eligibility_resolution(state, decision, transaction)
        decision["resolve_row"] = row_id
        return
    if row_id in CHECKED_ROWS:
        _check_resolution(state, row_id, decision, transaction)
    decision["selected_option"] = payload.get("selected_option")
    decision["resolve_row"] = row_id
    if _decision_family(row_id) == _RECOVERY_DECISION_FAMILY:
        _add_edges(state, decision_id, [ref for ref in decision["governing_evidence_refs"] if ref.startswith("obj_")])
    for event in transaction[1:]:
        record = event["payload"]
        record_id = _record_resolved(state, row_id, decision_id, record, context, decision.get("subject", (None,))[0])
        kind = record_kind(record.get("schema_id"))
        refuse_restricted_frozen_copy(record)
        if kind == "legacy_ownership_transitioned":
            _apply_ownership(state, row_id, record)
        elif kind == "legacy_record_supersession":
            _apply_supersession(state, record)
        if kind in {OWNERSHIP, TRANSITION_MAPPING, SOURCE_INVENTORY}:
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
    if row_id in WP9_3_ROWS:
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
    # Review i-2: both are preparer-set from the one clock read and the source kind (§5.1, §7.4), so replay checks them.
    if record.get("observed_at") != event.get("occurred_at"):
        raise IntegrityError("W9 observation observed_at is not the event's time")
    non_inferences = record.get("non_inferences")
    kind = record.get("source_identity", {}).get("identity_kind")
    if not isinstance(non_inferences, list | tuple) or tuple(non_inferences) != NON_INFERENCES.get(kind):
        raise IntegrityError("W9 observation non_inferences are not the fixed strings for its source kind")
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
    if kind == "legacy_observation" and row_id in WP9_3_ROWS:
        registration_id = _check_observation(state, record, event, context)
    elif kind == PAPER_ROOT and row_id in WP9_4_ROWS:
        _check_paper_root_lr035(state, record, event, context)
    elif kind == CITATION_STATUS and row_id in WP9_4_ROWS:
        _check_citation_status_lr039(state, record, event, context)
    claim_identity(state, record_id, kind, context)
    if kind == PAPER_ROOT:
        recovery = record.get("recovery")
        if recovery is not None:
            predecessor_id = recovery.get("predecessor_root_ref", {}).get("id")
            decision_id = recovery.get("recovery_decision_ref", {}).get("id")
            decision = state["decisions"].get(decision_id)
            if predecessor_id not in state["records"].get(PAPER_ROOT, {}):
                raise IntegrityError("W9 recovery root names no recorded predecessor root")
            if decision is None or decision["resolve_row"] != _PAPER_ROOT_RECOVERY_ROW:
                raise IntegrityError("W9 recovery root names no resolved recovery Decision")
            if f"{record_id}" in decision["governing_evidence_refs"]:
                raise IntegrityError("W9 recovery Decision names its recovery root")
        _add_edges(state, str(record_id), list(_ref_ids(record)))
    elif kind == CITATION_STATUS:
        _add_edges(state, str(record_id), list(_ref_ids(record)))
        state.setdefault("current_citation_status_by_root", {})[str(record["root_ref"]["id"])] = str(record_id)
    state["records"].setdefault(kind, {})[record_id] = deepcopy(record)
    if registration_id is not None:
        registration = state["records"]["legacy_path_registration"][registration_id]
        earlier = state["observations_by_registration"].setdefault(registration_id, [])
        fingerprint = _source_fingerprint(record["source_identity"])
        _, source_path = _source_location(record["source_identity"])
        per_member = registration.get("role") == MANUSCRIPT_ROOT_ROLE
        for observation_id in earlier:
            other = state["records"]["legacy_observation"][observation_id]
            if per_member and _source_location(other["source_identity"])[1] != source_path:
                continue
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
