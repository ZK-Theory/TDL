# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1; P-080, P-081)
# Purpose: build valid W9 LR-003 to LR-015 flows on forged scratch ledgers, for replay tests and their controls.
"""Forged-ledger builders for W9 flows (WP9.3 note §4, §5, §6).

A :class:`Forger` appends W9 transactions to a copy of a scratch ledger that holds W11 and W9 genesis, with each
event's actor, time and grant set, and stream versions counted per stream, then re-hashes the copy. Nothing is written
back to a store. The record builders stamp each record as the preparer would (WP9.3 note §4.1, §5.1): the content hash
over the record without ``content_hash``, the pre-assigned ref hashes of §4.2, ``created_at`` and
``created_by_actor_id`` from the event. The W2 payload builders follow §5.2 field by field.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id
from research_system.legacy.records import (
    observation_record_id,
    observation_subject_digest,
    pre_assigned_ref,
    record_content_hash,
    review_attempt_id,
    review_context_manifest_id,
)
from research_system.legacy.replay.reducers import iso_z
from research_system.legacy.routes import LEGACY_ROW_ROUTES, W2_EVENT_TYPES
from tests.research_system.integration.test_wp6_6_discovery_runtime import _rehash_events

T0 = datetime(2026, 9, 1, tzinfo=UTC)
SHA1 = "1" * 40
REPRODUCTION_SESSION = "session-reproducer"


def at(minutes: float) -> str:
    """A ledger time ``minutes`` after ``T0``, formatted as the runtime formats it."""
    return iso_z(T0 + timedelta(minutes=minutes))


def stamp(record: dict[str, Any]) -> dict[str, Any]:
    """Set the record's content hash by §4.1's rule and return it."""
    record["content_hash"] = record_content_hash(record)
    return record


@dataclass
class Actors:
    """The distinct W9 roles of a flow (§5.5). The owner is the harness owner, actor-a."""

    owner: str
    analyst: str = field(default_factory=lambda: new_id("actor"))
    author: str = field(default_factory=lambda: new_id("actor"))
    observer: str = field(default_factory=lambda: new_id("actor"))
    reviewer: str = field(default_factory=lambda: new_id("actor"))
    reproducer: str = field(default_factory=lambda: new_id("actor"))


class Forger:
    """An immutable forged ledger: each ``append`` returns a new forger over the extended, re-hashed events."""

    def __init__(self, events: tuple[dict[str, Any], ...]) -> None:
        self.events = tuple(events)
        self.template = next(
            event for event in self.events if event["command_type"] == "ImportAcceptedW9CatalogueGenesis"
        )
        self.project_id = self.template["project_id"]

    def version(self, stream_id: str) -> int:
        return sum(1 for event in self.events if event["stream_id"] == stream_id)

    def append(
        self,
        command_type: str,
        members: list[tuple[str, str, dict[str, Any]]],
        *,
        actor: str,
        when: str,
        grant: str | None = None,
        stream_versions: dict[int, int] | None = None,
    ) -> Forger:
        """Append one transaction of ``(event_type, stream_id, payload)`` members.

        ``stream_versions`` overrides a member's stream version by its index, for the stream controls.
        """
        command_id = new_id("command")
        transaction_id = new_id("event_batch")
        counts: dict[str, int] = {}
        forged = []
        for index, (event_type, stream_id, payload) in enumerate(members, start=1):
            counts[stream_id] = counts.get(stream_id, self.version(stream_id)) + 1
            event = deepcopy(self.template)
            event.update(
                {
                    "event_id": new_id("event"),
                    "global_position": len(self.events) + index,
                    "stream_id": stream_id,
                    "stream_version": (stream_versions or {}).get(index - 1, counts[stream_id]),
                    "transaction_id": transaction_id,
                    "transaction_index": index,
                    "transaction_count": len(members),
                    "command_id": command_id,
                    "command_type": command_type,
                    "event_type": event_type,
                    "schema_id": f"ars://core/event/{event_type}"
                    if event_type in W2_EVENT_TYPES
                    else "ars://core/event",
                    "schema_version": "1.0.0",
                    "idempotency_key": f"w9-test:{command_id}",
                    "command_payload_hash": sha256_hex(canonical_bytes(members[0][2])),
                    "correlation_id": command_id,
                    "actor_id": actor,
                    "authority_grant_id": grant or new_id("authority_grant"),
                    "occurred_at": when,
                    "payload": deepcopy(payload),
                }
            )
            forged.append(event)
        return Forger(_rehash_events((*self.events, *forged)))

    def row(self, row_id: str, stream_id: str, payload: dict[str, Any], *, actor: str, when: str, **kwargs: Any):
        """Append a one-event row on ``stream_id``."""
        route = LEGACY_ROW_ROUTES[row_id]
        return self.append(
            route.command_type, [(route.events[0].event_type, stream_id, payload)], actor=actor, when=when, **kwargs
        )

    def foreign(self, command_type: str, event_type: str, stream_id: str, payload: dict[str, Any], **kwargs: Any):
        """Append a non-W9 event (for the cross-partition controls)."""
        return self.append(
            command_type,
            [(event_type, stream_id, payload)],
            actor=kwargs.pop("actor", self.template["actor_id"]),
            when=kwargs.pop("when", at(0)),
            **kwargs,
        )


# --- Records (§4.1, §4.2, §5.1) --------------------------------------------------------------------------------------


def _header(kind: str, project_id: str, actor: str, when: str) -> dict[str, Any]:
    return {
        "schema_id": f"ars://legacy/{kind}",
        "schema_version": "1.0.0",
        "record_id": new_id("scope_definition"),
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": project_id,
        "created_at": when,
        "created_by_actor_id": actor,
        "content_hash": "0" * 64,
    }


def physical_identity(target: str, file_id: str = "1") -> dict[str, Any]:
    return {
        "canonical_target": target,
        "reparse_chain": [],
        "volume_serial_number": "1",
        "stable_file_id": file_id,
        "link_count": 1,
        "case_aliases": [],
        "unicode_aliases": [],
        "short_name_aliases": [],
    }


def registration(
    project_id: str,
    actor: str,
    when: str,
    *,
    path: str = "results/x.json",
    role: str = "legacy_research_result",
    kind: str = "git_tracked",
    root_kind: str = "repository_root",
    target: str | None = None,
    file_id: str = "1",
    **extra: Any,
) -> dict[str, Any]:
    record = {
        **_header("legacy-path-registration", project_id, actor, when),
        "root_kind": root_kind,
        "root_id": "vault" if root_kind == "vault_root" else "repository",
        "normalized_path": path,
        "physical_identity": physical_identity(target or f"C:/scratch/{path}", file_id),
        "source_identity_kind": kind,
        "role": role,
        "ownership_mode": "legacy_owned",
        "writer_classes": ["owner_ruling"],
        "prohibited_consumers": [],
        **extra,
    }
    record["registration_decision_ref"] = pre_assigned_ref("decision", new_id("decision"), record["record_id"])
    return stamp(record)


def membership(
    project_id: str, author: str, when: str, *, path: str = "results/x.json", sha256: str, size: int, **extra: Any
) -> dict[str, Any]:
    record = {
        **_header("legacy-field-family-membership", project_id, author, when),
        "file_schema_id": "w9-test-file/1",
        "applies_to": [
            {"path": path, "identity_kind": "git_tracked", "git_blob": SHA1, "sha256": sha256, "size_bytes": size}
        ],
        "table_sha256": "c" * 64,
        "families": [
            {"name": "headline", "definition_source": "w9 test", "pointers": ["/headline"]},
            {"name": "other", "definition_source": "w9 test", "pointers": ["/other"]},
        ],
        "unassigned": [],
        "author_actor_id": author,
        **extra,
    }
    record["review_ref"] = pre_assigned_ref("review", new_id("review"), record["record_id"])
    record["acceptance_decision_ref"] = pre_assigned_ref("decision", new_id("decision"), record["record_id"])
    return stamp(record)


def tracked(path: str = "results/x.json", *, sha256: str = "a" * 64, size: int = 1, blob: str = SHA1) -> dict[str, Any]:
    return {
        "identity_kind": "git_tracked",
        "repository_path": path,
        "git_commit": SHA1,
        "git_blob": blob,
        "sha256": sha256,
        "byte_length": size,
    }


def record_ref(record: dict[str, Any]) -> dict[str, Any]:
    return {"id": record["record_id"], "record_revision": 1, "content_hash": record["content_hash"]}


def inventory(
    project_id: str,
    observer: str,
    when: str,
    registration_record: dict[str, Any],
    segmented: dict[str, Any],
    *,
    selector: str = "tracker_task_row",
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = [
        {
            "selector_kind": selector,
            **{key: None for key in ("unit_hash", "unit_ordinal", "dated", "task_id")},
            **row,
        }
        for row in segmented["rows"]
    ]
    record = {
        **_header("legacy-light-inventory", project_id, observer, when),
        "registration_ref": record_ref(registration_record),
        "source_identity": source or tracked(registration_record["normalized_path"]),
        "segmentation_contract": segmented["segmentation_contract"],
        "selector_kind": selector,
        "heading_level": None,
        "covered_region": {"form": "fixed_by_selector"},
        "structural_ranges": [],
        "suppressed_anchors": segmented["suppressed_anchors"],
        "file_facts": segmented["file_facts"],
        "read_started_at": "2026-09-01T00:00:00.000000Z",
        "read_ended_at": "2026-09-01T00:00:01.000000Z",
        "path_form": {
            "path_as_given": registration_record["normalized_path"],
            "resolved_through_link": False,
            "resolved_target": None,
        },
        "observer_actor_id": observer,
        "rows": rows,
    }
    record["independent_reproduction_ref"] = pre_assigned_ref("review", new_id("review"), record["record_id"])
    return stamp(record)


NON_INFERENCES = {
    "git_tracked": ["no authority from file presence (W0 §4)"],
    "untracked_file": ["no authority from file presence (W0 §4)", "no Git identity"],
    "vault_file": ["no authority from file presence (W0 §4)", "no Git identity"],
    "restricted_untracked_file": [
        "no authority from file presence (W0 §4)",
        "no Git identity",
        "no frozen copy in the ARS store",
    ],
}


def signature(document_path: str = "docs/w0.md", document_blob: str = "2" * 40) -> dict[str, Any]:
    """A test W0 signature pin (§9.1), injected as tests inject ``accepted_revisions``."""
    ref_id = new_id("decision")
    return {
        "ref": {"id": ref_id, "record_revision": 1, "content_hash": "5" * 64},
        "domain": f"w9-test-signature:{ref_id}",
        "accepted_at": "2026-08-01T00:00:00Z",
        "signature_record": {
            "repository_path": "docs/sig.md",
            "git_commit": SHA1,
            "git_blob": SHA1,
            "sha256": "6" * 64,
        },
        "signed_w0_documents": ({"repository_path": document_path, "git_blob": document_blob},),
    }


def signed_family(name: str, pin: dict[str, Any], w0_class: str = "authoritative") -> dict[str, Any]:
    document = pin["signed_w0_documents"][0]
    return {
        "family_name": name,
        "w0_class": w0_class,
        "signed_w0_revision_ref": {
            "locator_kind": "git_file",
            "repository_path": document["repository_path"],
            "git_commit": SHA1,
            "git_blob": document["git_blob"],
            "sha256": "7" * 64,
            "byte_length": 10,
            "line_span": None,
        },
        "signature_record_ref": dict(pin["ref"]),
    }


def observation(
    project_id: str,
    observer: str,
    when: str,
    registration_record: dict[str, Any],
    pin: dict[str, Any],
    *,
    count: int = 0,
    selector: dict[str, Any] | None = None,
    source: dict[str, Any] | None = None,
    families: list[dict[str, Any]] | None = None,
    importer: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    source = source or tracked(registration_record["normalized_path"])
    selector = selector or {"selector_kind": "whole_file"}
    record = {
        **_header("legacy-observation", project_id, observer, when),
        "registration_ref": record_ref(registration_record),
        "selector": selector,
        "source_identity": source,
        "segmentation_contract": "w9-segmentation/1.0.0" if selector["selector_kind"] == "inventory_item" else None,
        "file_facts": None,
        "importer": {
            "actor_id": importer or observer,
            "tool_id": "research_system.legacy.reader",
            "tool_version": "1.0.0",
            "tool_sha256": "8" * 64,
        },
        "observer_actor_id": observer,
        "observed_at": when,
        "families": families or [signed_family("whole_file", pin)],
        "qualifiers": [],
        "conflicts": [],
        "non_inferences": NON_INFERENCES[source["identity_kind"]],
        **extra,
    }
    record["record_id"] = observation_record_id(
        registration_record["record_id"],
        observation_subject_digest(record),
        count,
        registration_record["created_at"],
    )
    return stamp(record)


# --- W2 payloads (§5.2) ----------------------------------------------------------------------------------------------


def review_request(
    row_id: str,
    record: dict[str, Any],
    review_id: str,
    reviewer: str,
    when: str,
    *,
    sessions: tuple[str, ...] = ("session-analyst",),
    **overrides: Any,
) -> dict[str, Any]:
    prefixes = ("w9-analyst-session:", "w9-author-session:")
    payload = {
        "review_type": "migration",
        "new_review_id": review_id,
        "subject_ids": [record["record_id"]],
        "subject_hashes": [record["content_hash"]],
        "governing_refs": [f"W9:{row_id}"],
        "review_questions": ["Is the subject independently reproduced?"],
        "required_evidence_refs": [prefix + session for prefix, session in zip(prefixes, sessions, strict=False)],
        "required_lanes": ["provenance"],
        "reviewer_capability": [reviewer],
        "required_independence_grade": "independent",
        "visibility_policy": "owner-visible",
        "allowed_verdicts": ["approve", "changes_requested", "reject", "unable_to_verify"],
        "satisfaction_authority": "ars://legacy/policy/w9-authority-review@1.0.0",
        "deadline": iso_z(datetime.fromisoformat(when.removesuffix("Z") + "+00:00") + timedelta(days=1)),
        "escalation_rule": "owner-ruling",
    }
    payload.update(overrides)
    return payload


def verdict(
    request: dict[str, Any], requested_at: str, reviewer: str, *, verdict_value: str = "approve", **overrides: Any
) -> dict[str, Any]:
    review_id = request["new_review_id"]
    payload = {
        "review_id": review_id,
        "verdict": verdict_value,
        "findings": [],
        "limitations": [],
        "conditions": [],
        "required_evidence_refs": list(request["required_evidence_refs"]),
        "reviewer_actor_id": reviewer,
        "reviewer_profile": "w9-independent-reviewer",
        "reviewer_session": "session-reviewer",
        "reviewer_model_metadata": "w9-test-model",
        "context_manifest_id": review_context_manifest_id(review_id, requested_at),
        "context_manifest_sha256": "9" * 64,
        "unchanged_subject_sha256": request["subject_hashes"][0],
        "producing_attempt_id": review_attempt_id(review_id, requested_at),
        "trace_visibility_evidence_refs": [request["subject_hashes"][0]],
        "computed_independence_grade": "independent",
    }
    payload.update(overrides)
    return payload


def decision_proposal(row_id: str, record: dict[str, Any], decision_id: str, when: str, **overrides: Any) -> dict:
    time = datetime.fromisoformat(when.removesuffix("Z") + "+00:00")
    payload = {
        "new_decision_id": decision_id,
        "question": "Accept the proposed W9 record?",
        "recommendation": "accept",
        "options": ["accept", "reject"],
        "decision_revision": 1,
        "decision_kind": "migration_authority",
        "governing_evidence_refs": [
            f"W9:{row_id}",
            f"w9-subject:{record['record_id']}",
            f"w9-subject-sha256:{record['content_hash']}",
        ],
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": "owner",
        "expires_at": iso_z(time + timedelta(days=30)),
        "review_date": when,
        "consequences": ["the record becomes a W9 record"],
    }
    payload.update(overrides)
    return payload


def resolution(
    row_id: str,
    proposal: dict[str, Any],
    record: dict[str, Any],
    actor: str,
    grant: str,
    when: str,
    reviews: list[str],
    **overrides: Any,
) -> dict[str, Any]:
    payload = {
        "decision_id": proposal["new_decision_id"],
        "selected_option": "accept",
        "effective_scope": f"w9-record:{record['record_id']}",
        "decision_revision": 1,
        "deciding_actor_id": actor,
        "decision_authority_grant_id": grant,
        # The proposal's subject refs with the resolution row in place of the proposal row (Stephen, option A).
        "governing_evidence_refs": [f"W9:{row_id}", *proposal["governing_evidence_refs"][1:]],
        "considered_review_ids": reviews,
        "effective_at": when,
        "permitted_commands": [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    payload.update(overrides)
    return payload


# --- Whole flows -----------------------------------------------------------------------------------------------------


def registered(forger: Forger, actors: Actors, *, start: float = 0, **kwargs: Any) -> tuple[Forger, dict[str, Any]]:
    """LR-003 → LR-004 → LR-005: one recorded registration (no review)."""
    record = registration(forger.project_id, actors.analyst, at(start), **kwargs)
    forger = forger.row("LR-003", record["record_id"], record, actor=actors.analyst, when=at(start))
    decision_id = record["registration_decision_ref"]["id"]
    proposal = decision_proposal("LR-004", record, decision_id, at(start + 1))
    forger = forger.row("LR-004", decision_id, proposal, actor=actors.analyst, when=at(start + 1))
    grant = new_id("authority_grant")
    resolved = resolution("LR-005", proposal, record, actors.owner, grant, at(start + 2), [])
    forger = forger.append(
        "ResolveW9AuthorityDecision",
        [
            ("DecisionResolved", decision_id, resolved),
            ("LegacyPathRegistrationRecorded", record["record_id"], deepcopy(record)),
        ],
        actor=actors.owner,
        when=at(start + 2),
        grant=grant,
    )
    return forger, record


@dataclass
class Tweak:
    """One step's change for a negative control: payload field overrides, another actor, another time (minutes)."""

    payload: dict[str, Any] = field(default_factory=dict)
    actor: str | None = None
    minutes: float | None = None


def membership_recorded(
    forger: Forger,
    actors: Actors,
    *,
    sha256: str,
    size: int,
    start: float = 10,
    tweaks: dict[str, Tweak] | None = None,
    stop_after: str | None = None,
    **kwargs: Any,
) -> tuple[Forger, dict[str, Any]]:
    """LR-006 → LR-007 → LR-008 → LR-009 → LR-010: one recorded membership table.

    ``tweaks`` changes one step by row; ``stop_after`` ends the flow after that row.
    """
    tweaks = tweaks or {}

    def step(row: str, default_actor: str, offset: float) -> tuple[str, str, dict[str, Any]]:
        tweak = tweaks.get(row, Tweak())
        return (
            tweak.actor or default_actor,
            at(start + (offset if tweak.minutes is None else tweak.minutes)),
            tweak.payload,
        )

    record = membership(forger.project_id, actors.author, at(start), sha256=sha256, size=size, **kwargs)
    forger = forger.row("LR-006", record["record_id"], record, actor=actors.author, when=at(start))
    if stop_after == "LR-006":
        return forger, record
    review_id = record["review_ref"]["id"]
    actor, when, changes = step("LR-007", actors.analyst, 1)
    request = review_request(
        "LR-007", record, review_id, actors.reviewer, when, sessions=("session-analyst", "session-author")
    )
    request.update(changes)
    forger = forger.row("LR-007", review_id, request, actor=actor, when=when)
    if stop_after == "LR-007":
        return forger, record
    requested_at = when
    actor, when, changes = step("LR-008", actors.reviewer, 2)
    forger = forger.row(
        "LR-008", review_id, {**verdict(request, requested_at, actors.reviewer), **changes}, actor=actor, when=when
    )
    if stop_after == "LR-008":
        return forger, record
    decision_id = record["acceptance_decision_ref"]["id"]
    actor, when, changes = step("LR-009", actors.analyst, 3)
    proposal = {**decision_proposal("LR-009", record, decision_id, when), **changes}
    forger = forger.row("LR-009", decision_id, proposal, actor=actor, when=when)
    if stop_after == "LR-009":
        return forger, record
    grant = new_id("authority_grant")
    actor, when, changes = step("LR-010", actors.owner, 4)
    resolved = {**resolution("LR-010", proposal, record, actor, grant, when, [review_id]), **changes}
    forger = forger.append(
        "ResolveW9AuthorityDecision",
        [
            ("DecisionResolved", decision_id, resolved),
            ("LegacyFieldFamilyMembershipRecorded", record["record_id"], deepcopy(record)),
        ],
        actor=actor,
        when=when,
        grant=grant,
    )
    return forger, record


# --- The closed-reference acceptance (WP9.3-2; note §10) -------------------------------------------------------------

# LR-020's four unconditional fixtures (note §10.2), restated here as an independent test literal.
UNCONDITIONAL_FIXTURES = ("F-018", "F-023", "F-037", "S-014")


def evidence_ref(prefix: str = "review") -> dict[str, Any]:
    return {"id": new_id(prefix), "record_revision": 1, "content_hash": "e" * 64}


def pilot_promotion(**dispositions: dict[str, Any]) -> list[dict[str, Any]]:
    """The four unconditional fixtures as evidence, each with a review ref; ``dispositions`` replaces or adds entries."""
    entries = {
        fixture: {"fixture_id": fixture, "disposition": "evidence", "ref": evidence_ref()}
        for fixture in UNCONDITIONAL_FIXTURES
    }
    for fixture, entry in dispositions.items():
        entries[fixture.replace("_", "-")] = entry
    return list(entries.values())


def acceptance(
    project_id: str,
    analyst: str,
    when: str,
    observations: list[dict[str, Any]],
    *,
    change_list: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """An LR-016 proposal: a batch of ``observations``, each with the unconditional fixtures, stamped (§4.1, §4.2)."""
    record = {
        **_header("legacy-closed-reference-acceptance", project_id, analyst, when),
        "items": [
            {"observation_ref": record_ref(observation), "pilot_promotion": pilot_promotion()}
            for observation in observations
        ],
        "threshold_preregistration_sha256": "3" * 64,
        "governing_record_set_sha256": "4" * 64,
        "anchors": [
            {"anchored": "threshold_preregistration", "anchor_kind": "git_commit", "value": SHA1},
            {"anchored": "governing_record_set", "anchor_kind": "git_commit", "value": SHA1},
        ],
        "enforcement_change_list": change_list or {"git_commit": SHA1, "git_blob": SHA1},
    }
    record.update(overrides)
    record["independent_review_ref"] = pre_assigned_ref("review", new_id("review"), record["record_id"])
    record["decision_ref"] = pre_assigned_ref("decision", new_id("decision"), record["record_id"])
    return stamp(record)


def ownership_transition(record: dict[str, Any], registration_record: dict[str, Any]) -> dict[str, Any]:
    """One ownership record LR-020 emits, built from note §10.5's text, not from the reducer that derives it."""
    from research_system.legacy.records import ownership_record_id

    transition = {
        "schema_id": "ars://legacy/legacy-ownership-transitioned",
        "schema_version": "1.0.0",
        "record_id": ownership_record_id(record["record_id"], registration_record["record_id"], record["created_at"]),
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": record["project_id"],
        "created_at": record["created_at"],
        "created_by_actor_id": record["created_by_actor_id"],
        "mapping_ref": None,
        "subject_registration_ref": record_ref(registration_record),
        "paper_root_ref": None,
        "from_mode": "legacy_owned",
        "to_mode": "closed_reference",
        "reviewer_ref": deepcopy(record["independent_review_ref"]),
        "decision_ref": deepcopy(record["decision_ref"]),
    }
    return stamp(transition)


def acceptance_recorded(
    forger: Forger,
    actors: Actors,
    record: dict[str, Any],
    transitions: list[dict[str, Any]],
    *,
    start: float = 60,
    tweaks: dict[str, Tweak] | None = None,
    stop_after: str | None = None,
    emitted: list[dict[str, Any]] | None = None,
) -> Forger:
    """LR-016 → LR-017 → LR-018 → LR-019 → LR-020 for one batch. ``emitted`` replaces the ownership records LR-020
    writes (for the list controls); ``transitions`` is what the test expects replay to derive."""
    tweaks = tweaks or {}

    def step(row: str, default_actor: str, offset: float) -> tuple[str, str, dict[str, Any]]:
        tweak = tweaks.get(row, Tweak())
        return (
            tweak.actor or default_actor,
            at(start + (offset if tweak.minutes is None else tweak.minutes)),
            tweak.payload,
        )

    actor, when, _ = step("LR-016", actors.analyst, 0)
    forger = forger.row("LR-016", record["record_id"], record, actor=actor, when=when)
    if stop_after == "LR-016":
        return forger
    review_id = record["independent_review_ref"]["id"]
    actor, when, changes = step("LR-017", actors.analyst, 1)
    request = {**review_request("LR-017", record, review_id, actors.reviewer, when), **changes}
    forger = forger.row("LR-017", review_id, request, actor=actor, when=when)
    if stop_after == "LR-017":
        return forger
    requested_at = when
    actor, when, changes = step("LR-018", actors.reviewer, 2)
    answer = {**verdict(request, requested_at, request["reviewer_capability"][0]), **changes}
    forger = forger.row("LR-018", review_id, answer, actor=actor, when=when)
    if stop_after == "LR-018":
        return forger
    decision_id = record["decision_ref"]["id"]
    actor, when, changes = step("LR-019", actors.analyst, 3)
    proposal = {**decision_proposal("LR-019", record, decision_id, when), **changes}
    forger = forger.row("LR-019", decision_id, proposal, actor=actor, when=when)
    if stop_after == "LR-019":
        return forger
    grant = new_id("authority_grant")
    actor, when, changes = step("LR-020", actors.owner, 4)
    resolved = {**resolution("LR-020", proposal, record, actor, grant, when, [review_id]), **changes}
    members = [
        ("DecisionResolved", decision_id, resolved),
        ("LegacyClosedReferenceAcceptanceRecorded", record["record_id"], deepcopy(record)),
        *(
            ("LegacyOwnershipTransitionedRecorded", transition["record_id"], deepcopy(transition))
            for transition in (transitions if emitted is None else emitted)
        ),
    ]
    return forger.append("ResolveW9AuthorityDecision", members, actor=actor, when=when, grant=grant)


def inventory_recorded(
    forger: Forger, actors: Actors, registration_record: dict[str, Any], segmented: dict[str, Any], *, start: float = 20
) -> tuple[Forger, dict[str, Any]]:
    """LR-011 → LR-012 → LR-013 → LR-014: one recorded light inventory."""
    record = inventory(forger.project_id, actors.observer, at(start), registration_record, segmented)
    forger = forger.row("LR-011", record["record_id"], record, actor=actors.observer, when=at(start))
    review_id = record["independent_reproduction_ref"]["id"]
    request = review_request("LR-012", record, review_id, actors.reproducer, at(start + 1))
    forger = forger.row("LR-012", review_id, request, actor=actors.analyst, when=at(start + 1))
    forger = forger.row(
        "LR-013",
        review_id,
        verdict(request, at(start + 1), actors.reproducer, reviewer_session=REPRODUCTION_SESSION),
        actor=actors.reproducer,
        when=at(start + 2),
    )
    forger = forger.row("LR-014", record["record_id"], deepcopy(record), actor=actors.observer, when=at(start + 3))
    return forger, record
