"""The WP9.3 preparers: LR-003 to LR-015 (WP9.3-1) and LR-016 to LR-020 (WP9.3-2) (WP9.3 note §5 to §8, §10).

The acceptance's environment checks (the window, the anchors and the change list) live in
:mod:`research_system.legacy.acceptance`, which LR-016 and LR-020 call.

Each preparer builds one command's prepared transaction from its small command payload and the replayed projections,
and adds what only the environment can show: file bytes, Git, the evidence area, the store binding, authority and the
clock (§6). The runtime then runs the prepared transaction through replay's own per-transaction step on a copy of the
projection before it appends, so a preparer is never weaker than replay.

Command payloads (§5.1):

| Command | Payload |
|---|---|
| ``ProposeLegacyRecord`` | the record, without ``created_at``, ``created_by_actor_id`` and ``content_hash`` |
| ``RequestW9AuthorityReview`` | ``subject_record_id``, ``reviewer_actor_id``, ``review_questions``, ``analyst_session`` and, for a membership table, ``author_session`` |
| ``RecordW9AuthorityReview`` | ``review_id``, ``verdict``, ``findings``, ``limitations``, ``reviewer_session``, ``reviewer_model_metadata``, ``context_manifest_sha256`` |
| ``ProposeW9AuthorityDecision`` | ``subject_record_id``, ``question``, ``recommendation``, ``consequences`` |
| ``ResolveW9AuthorityDecision`` | ``decision_id``, ``selected_option`` (``accept``) |
| ``RecordLegacyLightInventory`` | ``record_id`` |
| ``ObserveLegacyRecord`` | the observation, without its preparer-set and read-derived fields, plus ``frozen_copy_ref`` for an ``untracked_file`` or ``vault_file`` source |

The resolution's ``governing_evidence_refs`` are the proposal's subject refs with the row ref replaced by the
resolution row, so that row assignment finds the resolution row (Stephen, 2026-11-09, option A; note §5.2 read so).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from research_system.canonical import sha256_hex
from research_system.errors import IntegrityError
from research_system.legacy import evidence as w9_evidence
from research_system.legacy.json_families import JsonBlocked, assign, parse_strict
from research_system.legacy.projection_read import legacy_content_matches
from research_system.legacy.reader import LegacyReader, ReadRefused, git_blob_id, handle_bound_read
from research_system.legacy.records import (
    OBSERVATION_PREPARER_SET_FIELDS,
    OBSERVATION_READ_DERIVED_FIELDS,
    PREPARER_SET_FIELDS,
    adoption_eligibility_decision_id,
    observation_record_id,
    observation_subject_digest,
    record_content_hash,
    review_attempt_id,
    review_context_manifest_id,
)
from research_system.legacy.replay import reducers as r
from research_system.legacy.routes import record_kind
from research_system.legacy.segmentation import SegmentationError, resolve_first_anchor_after, segment

# The rows a preparer builds, by what the command names (§2.1). WP9.3-2 adds acceptance; WP9.4-1 adds adoption,
# eligibility, and discharge.
REQUEST_ROWS = {
    "legacy_field_family_membership": "LR-007",
    "legacy_light_inventory": "LR-012",
    "legacy_closed_reference_acceptance": "LR-017",
    r.ADOPTION: "LR-026",
    r.DISCHARGE: "LR-031",
}
DECISION_ROWS = {
    "legacy_path_registration": "LR-004",
    "legacy_field_family_membership": "LR-009",
    "legacy_closed_reference_acceptance": "LR-019",
    r.ADOPTION: "LR-028",
    r.DISCHARGE: "LR-033",
}
RESOLUTION_ROWS = {
    "LR-004": "LR-005",
    "LR-009": "LR-010",
    "LR-019": "LR-020",
    "LR-024": "LR-025",
    "LR-028": "LR-029",
    "LR-033": "LR-034",
}
RECORDED_EVENTS = {
    "LR-005": "LegacyPathRegistrationRecorded",
    "LR-010": "LegacyFieldFamilyMembershipRecorded",
    "LR-020": "LegacyClosedReferenceAcceptanceRecorded",
    "LR-029": "LegacyAdoptionDecisionRecorded",
    "LR-034": "LegacyDischargeRelationRecorded",
}
RESOLVER_ROWS = frozenset(RESOLUTION_ROWS.values())
# The stream version each command expects (§4.5): the claiming steps open a new stream.
EXPECTED_VERSIONS = {
    "ProposeLegacyRecord": 0,
    "RequestW9AuthorityReview": 0,
    "RecordW9AuthorityReview": 1,
    "ProposeW9AuthorityDecision": 0,
    "ResolveW9AuthorityDecision": 1,
    "RecordLegacyLightInventory": 1,
    "ObserveLegacyRecord": 0,
}
_FROZEN_COPY_KINDS = frozenset({"untracked_file", "vault_file"})


@dataclass
class Prepared:
    """A prepared W9 transaction: its events, and the window re-reads the runtime runs after the shadow step (§7.2)."""

    events: list[tuple[str, str, dict[str, Any]]]
    rereads: list[Callable[[], None]] = field(default_factory=list)


@dataclass(frozen=True)
class Environment:
    """What only the environment can show (§6): the reader, the generic projection and the control root."""

    reader: LegacyReader | None
    generic: Mapping[str, Any]
    control_root: Path
    vault_root: Path | None


def _iso(now: datetime) -> str:
    return r.iso_z(now)


def _need_reader(environment: Environment) -> LegacyReader:
    if environment.reader is None:
        raise IntegrityError("the W9 runtime has no reader for this row's source")
    return environment.reader


def _refuse_supplied(payload: Mapping[str, Any], fields: frozenset[str]) -> None:
    supplied = sorted(set(payload) & fields)
    if supplied:
        raise IntegrityError(f"W9 command payload supplies preparer-set fields: {', '.join(supplied)}")


def _recorded(legacy: Mapping[str, Any], kind: str, record_id: Any) -> Mapping[str, Any]:
    record = legacy["records"].get(kind, {}).get(record_id)
    if record is None:
        raise IntegrityError(f"W9 command names no recorded {kind}")
    return record


def _proposal(legacy: Mapping[str, Any], record_id: Any) -> Mapping[str, Any]:
    proposal = legacy["proposals"].get(record_id)
    if proposal is None:
        raise IntegrityError("W9 command names no W9 proposal")
    return proposal


def _root(environment: Environment, root_kind: Any) -> Path:
    if root_kind == "vault_root":
        if environment.vault_root is None:
            raise IntegrityError("the W9 runtime has no vault root configured")
        return environment.vault_root
    return _need_reader(environment).repository_root


def _same_physical_identity(observed: Mapping[str, Any], declared: Mapping[str, Any]) -> bool:
    return os.path.normcase(str(observed.get("canonical_target"))) == os.path.normcase(
        str(declared.get("canonical_target"))
    ) and all(
        observed.get(key) == declared.get(key) for key in ("volume_serial_number", "stable_file_id", "link_count")
    )


def _require_physical_identity(environment: Environment, registration: Mapping[str, Any]) -> None:
    """LR-003 and LR-005: a handle-bound read shows the path resolves to the declared physical identity (§7.1)."""

    root_kind = registration.get("root_kind")
    try:
        _, physical, file_key = handle_bound_read(
            _root(environment, root_kind), str(registration.get("normalized_path"))
        )
    except ReadRefused as exc:
        raise IntegrityError(f"W9 registration path cannot be read handle-bound: {exc}") from exc
    if root_kind == "vault_root" and registration.get("role") != "conventions_lock":
        conventions = _need_reader(environment).repository_root / "CONVENTIONS.md"
        try:
            observed = conventions.stat()
        except OSError:
            observed = None
        if observed is not None and file_key == (observed.st_dev, observed.st_ino):
            raise IntegrityError("W9 vault registration resolves to the repository's CONVENTIONS.md")
    if not _same_physical_identity(physical, registration.get("physical_identity", {})):
        raise IntegrityError("W9 registration path does not resolve to its declared physical identity")


def _read_member(environment: Environment, entry: Mapping[str, Any]) -> bytes:
    root_kind = "vault_root" if entry.get("identity_kind") == "vault_file" else "repository_root"
    try:
        raw, _, _ = handle_bound_read(_root(environment, root_kind), str(entry.get("path")))
    except ReadRefused as exc:
        raise IntegrityError(f"W9 membership applies_to file cannot be read: {exc}") from exc
    if sha256_hex(raw) != entry.get("sha256") or len(raw) != entry.get("size_bytes"):
        raise IntegrityError("W9 membership applies_to bytes differ from the table's")
    if entry.get("identity_kind") == "git_tracked" and git_blob_id(raw) != entry.get("git_blob"):
        raise IntegrityError("W9 membership applies_to bytes differ from the table's")
    return raw


def _check_membership_bytes(environment: Environment, record: Mapping[str, Any]) -> None:
    """LR-006 (template §3 rules 1, 2, 10): each file re-read, parsed and covered exhaustively by the table."""

    for entry in record.get("applies_to", []):
        raw = _read_member(environment, entry)
        try:
            assign(record.get("families", []), record.get("unassigned", []), parse_strict(raw).value)
        except JsonBlocked as exc:
            raise IntegrityError(f"W9 membership table does not cover its bytes: {exc}") from exc


def _frozen_copy_ref(source: Mapping[str, Any], payload: Mapping[str, Any]) -> Any:
    ref = payload.get("frozen_copy_ref")
    if source["identity_kind"] in _FROZEN_COPY_KINDS:
        if ref is None:
            raise IntegrityError("W9 untracked or vault source needs its frozen copy ref")
        return deepcopy(ref)
    if ref is not None:
        raise IntegrityError("W9 source of this kind carries no frozen copy")
    return None


def check_frozen_copy(environment: Environment, ref: Mapping[str, Any], sha256: str, byte_length: int) -> None:
    """§7.3: the ref names a generic artefact in the control root whose bytes are the observed bytes."""

    from research_system.artefacts.runtime import ControlRootArtefactContentReader
    from research_system.errors import ArsError

    stream = environment.generic.get("streams", {}).get(ref.get("id"))
    manifest = stream.get("manifest") if isinstance(stream, Mapping) else None
    if not isinstance(manifest, Mapping):
        raise IntegrityError("W9 frozen copy ref names no registered artefact")
    if ref.get("content_hash") != manifest.get("content_sha256") or ref.get("record_revision") != 1:
        raise IntegrityError("W9 frozen copy ref differs from its registered artefact")
    try:
        raw = ControlRootArtefactContentReader(environment.control_root).read(
            root_id=str(manifest.get("root_id")), relative_path=str(manifest.get("relative_path"))
        )
    except (ArsError, OSError) as exc:
        raise IntegrityError(f"W9 frozen copy cannot be read: {exc}") from exc
    if sha256_hex(raw) != sha256 or len(raw) != byte_length:
        raise IntegrityError("W9 frozen copy bytes differ from the observed bytes")


def _resolution_kwargs(record: Mapping[str, Any]) -> dict[str, Any]:
    """The heading level and structural ranges a record declares, as ``segment`` and the resolution take them."""
    kwargs: dict[str, Any] = {}
    if record.get("heading_level") is not None:
        kwargs["level"] = record["heading_level"]
    if record.get("structural_ranges"):
        kwargs["structural"] = [(item["first_line"], item["last_line"]) for item in record["structural_ranges"]]
    return kwargs


def segment_kwargs(record: Mapping[str, Any]) -> dict[str, Any]:
    """The ``segment`` arguments an inventory record declares (§8.3); the builder and LR-011 share them."""
    region = record.get("covered_region", {})
    kwargs = _resolution_kwargs(record)
    if region.get("form") == "line_range":
        kwargs["region"] = (region["first_line"], region["last_line"])
    elif region.get("form") == "first_anchor_after":
        kwargs["region"] = (region["resolved_first_line"], region["resolved_last_line"])
    return kwargs


def anchor_line_sha256s(segmented: Mapping[str, Any]) -> list[Any]:
    """A ``line_range`` declaration's hashes: each segmented row's anchor-line SHA-256, in order (contract §3)."""
    return [row["anchor_line_sha256"] for row in segmented["rows"]]


def after_line_sha256(raw: bytes, after_line: Any) -> str | None:
    """The SHA-256 of the named structural line's bytes, terminator included; ``None`` for no such line.

    A line outside the file, or a value that is not a line number, has no hash, so a declaration naming it is refused.
    """
    lines = raw.split(b"\n")
    if not isinstance(after_line, int) or isinstance(after_line, bool) or not 1 <= after_line <= len(lines):
        return None
    return sha256_hex(lines[after_line - 1] + (b"\n" if after_line < len(lines) else b""))


def inventory_rows(segmented: Mapping[str, Any], selector_kind: str) -> list[dict[str, Any]]:
    """§8.3, §3 row 12: each segmenter row, with the inventory's selector kind added and absent fields null."""

    return [
        {
            "selector_kind": selector_kind,
            **dict.fromkeys(("unit_hash", "unit_ordinal", "dated", "task_id")),
            **row,
        }
        for row in segmented["rows"]
    ]


def check_resegmentation(raw: bytes, record: Mapping[str, Any]) -> dict[str, Any]:
    """LR-011 (§6.2; contract §3): re-segmentation reproduces every row, and the declarations match their hashes."""

    try:
        segmented = segment(raw, str(record.get("selector_kind")), **segment_kwargs(record))
    except SegmentationError as exc:
        raise IntegrityError(f"W9 inventory source cannot be segmented: {exc}") from exc
    if inventory_rows(segmented, str(record["selector_kind"])) != record.get("rows"):
        raise IntegrityError("W9 inventory rows differ from re-segmentation")
    if segmented["suppressed_anchors"] != record.get("suppressed_anchors"):
        raise IntegrityError("W9 inventory suppressed anchors differ from re-segmentation")
    if segmented["file_facts"] != record.get("file_facts"):
        raise IntegrityError("W9 inventory file facts differ from re-segmentation")
    region = record.get("covered_region", {})
    if region.get("form") == "line_range":
        if region.get("anchor_line_sha256s") != anchor_line_sha256s(segmented):
            raise IntegrityError("W9 inventory region declaration differs from its anchor-line hashes")
    elif region.get("form") == "first_anchor_after":
        after = region.get("after_line")
        if region.get("after_line_sha256") != after_line_sha256(raw, after):
            raise IntegrityError("W9 inventory region declaration differs from its anchor-line hashes")
        # P-082 item 5 (review M-2): the declared range must be the resolution the bytes give, so no row drops out.
        # The resolver refuses a non-integer after_line itself, for every caller.
        try:
            resolved = resolve_first_anchor_after(
                raw, str(record["selector_kind"]), after, **_resolution_kwargs(record)
            )
        except SegmentationError as exc:
            raise IntegrityError(f"W9 inventory region cannot be resolved: {exc}") from exc
        if (region.get("resolved_first_line"), region.get("resolved_last_line")) != resolved:
            raise IntegrityError("W9 inventory region resolution differs from the first anchor after its after_line")
    return segmented


def _comparable_source(identity: Mapping[str, Any]) -> dict[str, Any]:
    compared = {key: value for key, value in identity.items() if key != "frozen_copy_ref"}
    if compared.get("identity_kind") == "git_tracked":
        compared.pop("git_commit", None)
    return compared


def _check_adoption_source(environment: Environment, legacy: Mapping[str, Any], record: Mapping[str, Any]) -> None:
    """LR-023 and LR-029 (W9-T6, O-33, §6.1): re-read observed source and verify binary/restricted whole-file."""

    obs_ref = record.get("observation_ref")
    obs_id = obs_ref.get("id") if isinstance(obs_ref, Mapping) else None
    observation = _recorded(legacy, "legacy_observation", obs_id)
    registration = _recorded(legacy, "legacy_path_registration", observation["registration_ref"]["id"])
    recorded_src = observation["source_identity"]
    try:
        read = _need_reader(environment).read(registration)
    except ReadRefused as exc:
        raise IntegrityError(f"W9 adoption source cannot be read: {exc}") from exc
    if _comparable_source(read.source_identity) != _comparable_source(recorded_src):
        raise IntegrityError("W9 adoption source re-reads differently from its observation")
    if recorded_src.get("identity_kind") in _FROZEN_COPY_KINDS:
        check_frozen_copy(
            environment,
            recorded_src["frozen_copy_ref"],
            recorded_src["sha256"],
            recorded_src["byte_length"],
        )
    subject = record.get("subject")
    if isinstance(subject, Mapping) and subject.get("subject_kind") == "whole_file":
        _, source_path = r._source_location(recorded_src)
        is_json = any(
            isinstance(path, str) and path.lower().endswith(".json")
            for path in (registration.get("normalized_path"), source_path)
        )
        is_restricted = recorded_src.get("identity_kind") == "restricted_untracked_file" or (
            isinstance(source_path, str) and source_path.lower().endswith(r.RESTRICTED_SUFFIXES)
        )
        if not is_json and not is_restricted:
            try:
                read.raw.decode("utf-8")
            except UnicodeDecodeError:
                pass
            else:
                raise IntegrityError("W9 whole-file adoption requires a binary or restricted source")


def _check_discharge_artefact(
    environment: Environment, legacy: Mapping[str, Any], record: Mapping[str, Any]
) -> Mapping[str, Any]:
    """LR-030 and LR-034 (§4.2, §4.4, §8): successor artefact is accepted_for_scope and matches no legacy bytes."""

    from research_system.artefacts.runtime import ControlRootArtefactContentReader
    from research_system.errors import ArsError

    ref = record.get("successor_result_ref")
    if not isinstance(ref, Mapping):
        raise IntegrityError("W9 discharge relation carries no successor_result_ref")
    stream = environment.generic.get("streams", {}).get(ref.get("id"))
    manifest = stream.get("manifest") if isinstance(stream, Mapping) else None
    if not isinstance(manifest, Mapping):
        raise IntegrityError("W9 discharge successor result names no registered artefact")
    if ref.get("record_revision") != 1 or ref.get("content_hash") != manifest.get("content_sha256"):
        raise IntegrityError("W9 discharge successor result ref differs from its registered artefact")
    if stream.get("use_authority") != "accepted_for_scope":
        raise IntegrityError("W9 discharge successor result is not accepted_for_scope")
    try:
        raw = ControlRootArtefactContentReader(environment.control_root).read(
            root_id=str(manifest.get("root_id")),
            relative_path=str(manifest.get("relative_path")),
        )
    except (ArsError, OSError) as exc:
        raise IntegrityError(f"W9 discharge successor result cannot be read: {exc}") from exc
    digest = sha256_hex(raw)
    if digest != manifest.get("content_sha256") or len(raw) != manifest.get("size_bytes"):
        raise IntegrityError("W9 discharge successor result bytes differ from its manifest")
    if legacy_content_matches(legacy, digest, git_blob_id(raw)):
        raise IntegrityError("W9 discharge successor result matches a recorded legacy observation")
    return manifest


def _check_discharge_open_item(
    environment: Environment, record: Mapping[str, Any], *, expected_blob: str | None = None
) -> str:
    """LR-030 and LR-034 (owner point H, §8): legacy item resolves against legacy-open-items.json at git_head."""

    reader = _need_reader(environment)
    items, blob = w9_evidence.require_open_items(reader.repository_root, reader.git_head, expected_blob=expected_blob)
    item = record.get("legacy_item", {})
    if not isinstance(item, Mapping) or not w9_evidence.has_open_item(
        items, str(item.get("item_kind")), str(item.get("item_id"))
    ):
        raise IntegrityError("W9 discharge item is not in the open-item list at git_head")
    return blob


# --- The seven commands ----------------------------------------------------------------------------------------------


def prepare_proposal(
    payload: Mapping[str, Any], *, actor: str, now: datetime, legacy: Mapping[str, Any], environment: Environment
) -> Prepared:
    """``ProposeLegacyRecord`` (LR-003, LR-006, LR-011, LR-016, LR-023, LR-030): stamp and check the environment."""

    _refuse_supplied(payload, PREPARER_SET_FIELDS)
    record = {**deepcopy(dict(payload)), "created_by_actor_id": actor, "created_at": _iso(now)}
    record["content_hash"] = record_content_hash(record)
    kind = record_kind(record.get("schema_id"))
    prepared = Prepared([(f"{_event_base(kind)}Proposed", str(record.get("record_id")), record)])
    if kind == "legacy_path_registration":
        reader = _need_reader(environment)
        w9_evidence.require_detector_controls(
            w9_evidence.read_evidence(reader.repository_root, reader.git_head, w9_evidence.DETECTOR_CONTROLS)
        )
        _require_physical_identity(environment, record)
    elif kind == "legacy_field_family_membership":
        _check_membership_bytes(environment, record)
    elif kind == "legacy_light_inventory":
        registration = _recorded(legacy, "legacy_path_registration", record.get("registration_ref", {}).get("id"))
        read = _read_source(environment, registration, record.get("source_identity", {}), record)
        check_resegmentation(read, record)
    elif kind == "legacy_closed_reference_acceptance":
        from research_system.legacy import acceptance

        # LR-016 (§6.2, §7.2, §10.3, §10.4): the window, the anchors and the change list, the window again at commit.
        prepared.rereads.extend(acceptance.check_environment(environment, legacy, record))
    elif kind == r.ADOPTION:
        _check_adoption_source(environment, legacy, record)

        def reread_adoption_source() -> None:
            _check_adoption_source(environment, legacy, record)

        prepared.rereads.append(reread_adoption_source)
    elif kind == r.DISCHARGE:

        def check_discharge_env() -> None:
            _check_discharge_open_item(environment, record)
            _check_discharge_artefact(environment, legacy, record)

        check_discharge_env()
        prepared.rereads.append(check_discharge_env)
    return prepared


def _event_base(kind: str) -> str:
    return "".join(part.capitalize() for part in kind.split("_"))


def _read_source(
    environment: Environment,
    registration: Mapping[str, Any],
    declared: Mapping[str, Any],
    holder: Mapping[str, Any],
) -> bytes:
    """Re-read a source by its kind and require the declared identity (LR-011, LR-014)."""

    try:
        read = _need_reader(environment).read(registration)
    except ReadRefused as exc:
        raise IntegrityError(f"W9 source cannot be read: {exc}") from exc
    expected = {key: value for key, value in declared.items() if key != "frozen_copy_ref"}
    if read.source_identity != expected:
        raise IntegrityError("W9 source re-read differs from its recorded identity")
    if declared.get("identity_kind") in _FROZEN_COPY_KINDS:
        check_frozen_copy(environment, declared["frozen_copy_ref"], declared["sha256"], declared["byte_length"])
    return read.raw


def prepare_review_request(
    payload: Mapping[str, Any], *, actor: str, now: datetime, legacy: Mapping[str, Any], environment: Environment
) -> Prepared:
    """``RequestW9AuthorityReview``: build ``ReviewRequested`` by §5.2 and WP9.4 §5.4 to §5.5."""

    proposal = _proposal(legacy, payload.get("subject_record_id"))
    row = REQUEST_ROWS.get(proposal["kind"])
    if row is None:
        raise IntegrityError("W9 proposal of this kind has no review row")
    expected = {"subject_record_id", "reviewer_actor_id", "review_questions", "analyst_session"}
    if row == "LR-007":
        expected.add("author_session")
    elif row == "LR-026":
        expected.add("eligible_session")
    if set(payload) != expected:
        raise IntegrityError(f"W9 review request payload must carry exactly: {', '.join(sorted(expected))}")
    sessions = [f"{r.ANALYST_SESSION_PREFIX}{payload['analyst_session']}"]
    if row == "LR-007":
        sessions.append(f"{r.AUTHOR_SESSION_PREFIX}{payload['author_session']}")
    elif row == "LR-026":
        sessions.append(f"{r.ELIGIBLE_SESSION_PREFIX}{payload['eligible_session']}")
    record = proposal["record"]
    if row == "LR-031":
        ref_id = record.get("successor_result_ref", {}).get("id")
        stream = environment.generic.get("streams", {}).get(ref_id)
        manifest = stream.get("manifest") if isinstance(stream, Mapping) else None
        if not isinstance(manifest, Mapping):
            raise IntegrityError("W9 discharge successor result names no registered artefact")
        if payload["reviewer_actor_id"] == manifest.get("producer_actor_id"):
            raise IntegrityError("W9 discharge reviewer is the successor result's producer")
    review_id = r.review_id_for(proposal["kind"], record)
    request = {
        "review_type": r.REVIEW_TYPE,
        "new_review_id": review_id,
        "subject_ids": [record["record_id"]],
        "subject_hashes": [proposal["content_hash"]],
        "governing_refs": [f"W9:{row}"],
        "review_questions": deepcopy(payload["review_questions"]),
        "required_evidence_refs": sessions,
        "required_lanes": list(r.REQUIRED_LANES),
        "reviewer_capability": [payload["reviewer_actor_id"]],
        "required_independence_grade": r.INDEPENDENCE_GRADE,
        "visibility_policy": r.VISIBILITY_POLICY,
        "allowed_verdicts": list(r.ALLOWED_VERDICTS),
        "satisfaction_authority": r.SATISFACTION_AUTHORITY,
        "deadline": _iso(now + r.REVIEW_DEADLINE),
        "escalation_rule": r.ESCALATION_RULE,
    }
    return Prepared([("ReviewRequested", review_id, request)])


def prepare_review_verdict(
    payload: Mapping[str, Any], *, actor: str, now: datetime, legacy: Mapping[str, Any], environment: Environment
) -> Prepared:
    """``RecordW9AuthorityReview``: build ``ReviewVerdictRecorded`` by §5.2 and WP9.4 §5.5."""

    expected = {
        "review_id",
        "verdict",
        "findings",
        "limitations",
        "reviewer_session",
        "reviewer_model_metadata",
        "context_manifest_sha256",
    }
    if set(payload) != expected:
        raise IntegrityError(f"W9 review verdict payload must carry exactly: {', '.join(sorted(expected))}")
    review_id = payload["review_id"]
    review = legacy["reviews"].get(review_id)
    if review is None or "subject" not in review:
        raise IntegrityError("W9 verdict names no open W9 review")
    subject_hash = review["subject"][1]
    profile = review["eligibility"]["profile"] if review.get("request_row") == "LR-026" else r.REVIEWER_PROFILE
    verdict = {
        "review_id": review_id,
        "verdict": payload["verdict"],
        "findings": deepcopy(payload["findings"]),
        "limitations": deepcopy(payload["limitations"]),
        "conditions": [],
        "required_evidence_refs": list(review["required_evidence_refs"]),
        "reviewer_actor_id": actor,
        "reviewer_profile": profile,
        "reviewer_session": payload["reviewer_session"],
        "reviewer_model_metadata": payload["reviewer_model_metadata"],
        "context_manifest_id": review_context_manifest_id(review_id, review["requested_at"]),
        "context_manifest_sha256": payload["context_manifest_sha256"],
        "unchanged_subject_sha256": subject_hash,
        "producing_attempt_id": review_attempt_id(review_id, review["requested_at"]),
        "trace_visibility_evidence_refs": [subject_hash],
        "computed_independence_grade": r.INDEPENDENCE_GRADE,
    }
    return Prepared([("ReviewVerdictRecorded", review_id, verdict)])


def prepare_decision_proposal(
    payload: Mapping[str, Any], *, actor: str, now: datetime, legacy: Mapping[str, Any], environment: Environment
) -> Prepared:
    """``ProposeW9AuthorityDecision``: build ``DecisionProposed`` (WP9.3 §5.2; WP9.4 §5.4, §5.5, §8)."""

    base = {"subject_record_id", "question", "recommendation", "consequences"}
    optional = {"eligibility", "fixture_refs", "open_items_blob"}
    keys = set(payload)
    if not base <= keys or (keys - base - optional):
        raise IntegrityError(
            "W9 Decision proposal payload requires consequences, question, recommendation, subject_record_id "
            "and allows optional eligibility, fixture_refs, open_items_blob"
        )
    proposal = _proposal(legacy, payload["subject_record_id"])
    kind = proposal["kind"]
    record = proposal["record"]

    if "eligibility" in payload:
        if kind != r.ADOPTION:
            raise IntegrityError("W9 eligibility Decision is admitted for an adoption proposal only")
        if "fixture_refs" in payload or "open_items_blob" in payload:
            raise IntegrityError("W9 eligibility Decision accepts no fixture_refs or open_items_blob")
        elig = payload["eligibility"]
        elig_keys = ("session", "family", "version", "profile", "grade")
        if (
            not isinstance(elig, Mapping)
            or set(elig) != set(elig_keys)
            or any(not isinstance(elig[k], str) or not elig[k] for k in elig_keys)
        ):
            raise IntegrityError("W9 eligibility payload must carry session, family, version, profile and grade")
        decision_id = adoption_eligibility_decision_id(record["record_id"], record["created_at"])
        governing_refs = [
            "W9:LR-024",
            f"{r.SUBJECT_PREFIX}{record['record_id']}",
            f"{r.SUBJECT_HASH_PREFIX}{proposal['content_hash']}",
            f"{r.ELIGIBLE_SESSION_PREFIX}{elig['session']}",
            f"{r.ELIGIBLE_FAMILY_PREFIX}{elig['family']}",
            f"{r.ELIGIBLE_VERSION_PREFIX}{elig['version']}",
            f"{r.ELIGIBLE_PROFILE_PREFIX}{elig['profile']}",
            f"{r.ELIGIBLE_GRADE_PREFIX}{elig['grade']}",
        ]
    else:
        row = DECISION_ROWS.get(kind)
        if row is None:
            raise IntegrityError("W9 proposal of this kind has no Decision row")
        if row in r.WP9_3_ROWS and ("fixture_refs" in payload or "open_items_blob" in payload):
            raise IntegrityError(f"W9 {row} does not accept fixture_refs or open_items_blob")
        if row == "LR-028" and "open_items_blob" in payload:
            raise IntegrityError("W9 LR-028 does not accept open_items_blob")
        fixture_refs = payload.get("fixture_refs", [])
        if not isinstance(fixture_refs, list) or any(not isinstance(item, str) for item in fixture_refs):
            raise IntegrityError("W9 Decision fixture_refs must be a list of strings")
        decision_id = record[r._DECISION_PROPOSAL_FIELD[row]]["id"]
        governing_refs = [
            f"W9:{row}",
            f"{r.SUBJECT_PREFIX}{record['record_id']}",
            f"{r.SUBJECT_HASH_PREFIX}{proposal['content_hash']}",
            *fixture_refs,
        ]
        if row == "LR-033":
            blob = payload.get("open_items_blob")
            if not isinstance(blob, str) or not blob:
                raise IntegrityError("W9 LR-033 requires open_items_blob")
            _check_discharge_open_item(environment, record, expected_blob=blob)
            governing_refs.append(f"{r.OPEN_ITEMS_BLOB_PREFIX}{blob}")

    decision = {
        "new_decision_id": decision_id,
        "question": payload["question"],
        "recommendation": payload["recommendation"],
        "options": list(r.DECISION_OPTIONS),
        "decision_revision": 1,
        "decision_kind": r.DECISION_KIND,
        "governing_evidence_refs": governing_refs,
        "affected_task_ids": [],
        "affected_claim_ids": [],
        "required_authority": r.REQUIRED_AUTHORITY,
        "expires_at": _iso(now + r.PROPOSAL_TERM),
        "review_date": _iso(now),
        "consequences": deepcopy(payload["consequences"]),
    }
    return Prepared([("DecisionProposed", decision_id, decision)])


def prepare_resolution(
    payload: Mapping[str, Any],
    *,
    actor: str,
    now: datetime,
    legacy: Mapping[str, Any],
    environment: Environment,
    grant_id: str,
) -> Prepared:
    """``ResolveW9AuthorityDecision``: G5's resolution and optional record event (§5.2, §5.5, §6.1, §8)."""

    if set(payload) != {"decision_id", "selected_option"}:
        raise IntegrityError("W9 Decision resolution payload must carry exactly: decision_id, selected_option")
    decision_id = payload["decision_id"]
    decision = legacy["decisions"].get(decision_id)
    if decision is None or "subject" not in decision:
        raise IntegrityError("W9 resolution names no open W9 Decision")
    row = RESOLUTION_ROWS[decision["propose_row"]]
    record_id = decision["subject"][0]
    proposal = _proposal(legacy, record_id)
    selected = payload["selected_option"]
    if row == "LR-025":
        if selected not in r.DECISION_OPTIONS:
            raise IntegrityError("W9 eligibility Decision resolution must select accept or reject")
        resolution = {
            "decision_id": decision_id,
            "selected_option": selected,
            "effective_scope": f"{r.EFFECTIVE_SCOPE_PREFIX}{record_id}",
            "decision_revision": 1,
            "deciding_actor_id": actor,
            "decision_authority_grant_id": grant_id,
            "governing_evidence_refs": [f"W9:{row}", *decision["governing_evidence_refs"][1:]],
            "considered_review_ids": [],
            "effective_at": _iso(now),
            "permitted_commands": [],
            "superseded_decision_ids": [],
            "conditions": [],
            "revisit_triggers": [],
        }
        return Prepared([("DecisionResolved", decision_id, resolution)])

    if selected != "accept":
        raise IntegrityError("W9 Decision resolution must select accept")
    record = deepcopy(proposal["record"])
    review_id = r.review_id_for(proposal["kind"], record)
    considered = [] if review_id is r.NO_REVIEW_REQUIRED else [review_id]
    resolution = {
        "decision_id": decision_id,
        "selected_option": "accept",
        "effective_scope": f"{r.EFFECTIVE_SCOPE_PREFIX}{record_id}",
        "decision_revision": 1,
        "deciding_actor_id": actor,
        "decision_authority_grant_id": grant_id,
        "governing_evidence_refs": [f"W9:{row}", *decision["governing_evidence_refs"][1:]],
        "considered_review_ids": considered,
        "effective_at": _iso(now),
        "permitted_commands": [],
        "superseded_decision_ids": [],
        "conditions": [],
        "revisit_triggers": [],
    }
    prepared = Prepared([("DecisionResolved", decision_id, resolution), (RECORDED_EVENTS[row], record_id, record)])
    if row == "LR-020":
        from research_system.legacy import acceptance

        # §10.5: the ownership records replay derived and stored at LR-016, each on its own stream. §10.6: the window,
        # the anchors and the change list again, against the binding at resolution, and the window again at commit.
        prepared.events.extend(
            ("LegacyOwnershipTransitionedRecorded", transition["record_id"], deepcopy(transition))
            for transition in proposal.get("ownership", [])
        )
        prepared.rereads.extend(acceptance.check_environment(environment, legacy, record))
    elif row == "LR-005":
        # §7.2: the physical identity re-read unchanged, at commit.
        _require_physical_identity(environment, record)
        prepared.rereads.append(lambda: _require_physical_identity(environment, record))
    elif row == "LR-029":
        # §6.5, W9-T6, O-33: source re-reads to observed identity at commit.
        _check_adoption_source(environment, legacy, record)
        prepared.rereads.append(lambda: _check_adoption_source(environment, legacy, record))
    elif row == "LR-034":
        # §8: artefact accepted & no legacy match, open-item blob unchanged & item present, G3 again.
        expected_blob = decision["governing_evidence_refs"][-1].removeprefix(r.OPEN_ITEMS_BLOB_PREFIX)

        def check_discharge_resolution() -> None:
            manifest = _check_discharge_artefact(environment, legacy, record)
            _check_discharge_open_item(environment, record, expected_blob=expected_blob)
            review = legacy["reviews"].get(record["reviewer_ref"]["id"])
            if review is None:
                raise IntegrityError("W9 discharge resolution names no recorded review")
            if review.get("reviewer") == manifest.get("producer_actor_id"):
                raise IntegrityError("W9 discharge reviewer is the successor result's producer")

        check_discharge_resolution()
        prepared.rereads.append(check_discharge_resolution)
    else:
        # Template §3 rule 10: applies_to bytes re-hashed equal, at commit.
        def reread_members() -> None:
            for entry in record.get("applies_to", []):
                _read_member(environment, entry)

        reread_members()
        prepared.rereads.append(reread_members)
    return prepared


def prepare_light_inventory(
    payload: Mapping[str, Any], *, actor: str, now: datetime, legacy: Mapping[str, Any], environment: Environment
) -> Prepared:
    """``RecordLegacyLightInventory`` (LR-014): the proposal's exact record; its source re-read unchanged (§7.2)."""

    if set(payload) != {"record_id"}:
        raise IntegrityError("W9 light inventory payload must carry exactly: record_id")
    proposal = _proposal(legacy, payload["record_id"])
    if proposal["kind"] != "legacy_light_inventory":
        raise IntegrityError("W9 command names no light inventory proposal")
    record = deepcopy(proposal["record"])
    registration = _recorded(legacy, "legacy_path_registration", record["registration_ref"]["id"])

    def reread() -> None:
        _read_source(environment, registration, record["source_identity"], record)

    reread()
    return Prepared([("LegacyLightInventoryRecorded", record["record_id"], record)], [reread])


def prepare_observation(
    payload: Mapping[str, Any],
    *,
    actor: str,
    now: datetime,
    legacy: Mapping[str, Any],
    environment: Environment,
) -> Prepared:
    """``ObserveLegacyRecord`` (LR-015): the read (§7), the frozen copy (§7.3), the derived ID (§5.3)."""

    _refuse_supplied(payload, OBSERVATION_PREPARER_SET_FIELDS | OBSERVATION_READ_DERIVED_FIELDS | {"non_inferences"})
    reader = _need_reader(environment)
    body = {key: deepcopy(value) for key, value in payload.items() if key != "frozen_copy_ref"}
    registration_id = body.get("registration_ref", {}).get("id")
    registration = _recorded(legacy, "legacy_path_registration", registration_id)
    w9_evidence.require_registered(
        w9_evidence.read_evidence(reader.repository_root, reader.git_head, w9_evidence.REGISTRATION_MANIFEST),
        registration,
    )
    try:
        read = reader.read(registration)
    except ReadRefused as exc:
        raise IntegrityError(f"W9 source cannot be read: {exc}") from exc
    source = dict(read.source_identity)
    frozen = _frozen_copy_ref(source, payload)
    if frozen is not None:
        source["frozen_copy_ref"] = frozen
        check_frozen_copy(environment, frozen, source["sha256"], source["byte_length"])
    selector = body.get("selector", {})
    file_facts = None
    if selector.get("selector_kind") == "inventory_item":
        inventory = _recorded(legacy, "legacy_light_inventory", selector.get("inventory_ref", {}).get("id"))
        file_facts = check_resegmentation(read.raw, {**inventory, "source_identity": source})["file_facts"]
    elif selector.get("selector_kind") == "json_family_set":
        table = _recorded(legacy, "legacy_field_family_membership", selector.get("membership_ref", {}).get("id"))
        try:
            assign(table.get("families", []), table.get("unassigned", []), parse_strict(read.raw).value)
        except JsonBlocked as exc:
            raise IntegrityError(f"W9 membership table does not cover the observed bytes: {exc}") from exc
    record = {
        **body,
        "source_identity": source,
        "file_facts": file_facts,
        "importer": reader.importer_identity(actor),
        "non_inferences": list(read.non_inferences),
        "created_by_actor_id": actor,
        "created_at": _iso(now),
        "observed_at": _iso(now),
    }
    count = len(legacy["observations_by_registration"].get(registration_id, []))
    record["record_id"] = observation_record_id(
        str(registration_id), observation_subject_digest(record), count, str(registration["created_at"])
    )
    record["content_hash"] = record_content_hash(record)

    def reread() -> None:
        # The final re-read (§7.2): the recorded hashes and frozen copy are those of these bytes, so any change up to
        # it aborts with no event and no receipt.
        try:
            final = reader.read(registration)
        except ReadRefused as exc:
            raise IntegrityError(f"W9 source cannot be re-read: {exc}") from exc
        if final.raw != read.raw:
            raise IntegrityError("W9 source changed within the observation window")

    return Prepared([("LegacyRecordObserved", record["record_id"], record)], [reread])


def observation_id(
    payload: Mapping[str, Any], *, actor: str, legacy: Mapping[str, Any], environment: Environment
) -> str:
    """The derived ``record_id`` the LR-015 preparer will compute for an envelope (§5.3, §13). Reads; writes nothing."""

    body = {key: deepcopy(value) for key, value in payload.items() if key != "frozen_copy_ref"}
    registration_id = body.get("registration_ref", {}).get("id")
    registration = _recorded(legacy, "legacy_path_registration", registration_id)
    reader = _need_reader(environment)
    try:
        read = reader.read(registration)
    except ReadRefused as exc:
        raise IntegrityError(f"W9 source cannot be read: {exc}") from exc
    source = dict(read.source_identity)
    frozen = _frozen_copy_ref(source, payload)
    if frozen is not None:
        source["frozen_copy_ref"] = frozen
    subject = {**body, "source_identity": source, "importer": reader.importer_identity(actor)}
    count = len(legacy["observations_by_registration"].get(registration_id, []))
    return observation_record_id(
        str(registration_id), observation_subject_digest(subject), count, str(registration["created_at"])
    )
