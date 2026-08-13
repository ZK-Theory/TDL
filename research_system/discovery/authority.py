"""Pure OR-110--OR-121 authority lifecycle preparation and replay.

Persistence is deliberately owned by :mod:`research_system.discovery.runtime`.
This module validates the immutable subject chain and returns the exact ordered
event tuples that the runtime can append as one authorized transaction.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from copy import deepcopy

from research_system.canonical import canonical_bytes, sha256_hex


class AuthorityRejected(ValueError):
    """An authority transition did not preserve the accepted W11 subject."""


_KINDS = {"dossier_expected_set", "path_registration"}
_ROWS = {
    "dossier_expected_set": {
        action: f"OR-{number}"
        for action, number in zip(
            ("register", "observe", "request_review", "record_review", "propose", "resolve"),
            range(110, 116),
            strict=True,
        )
    },
    "path_registration": {
        action: f"OR-{number}"
        for action, number in zip(
            ("register", "observe", "request_review", "record_review", "propose", "resolve"),
            range(116, 122),
            strict=True,
        )
    },
}
_REGISTERED = {
    "dossier_expected_set": "DossierExpectedSetContentRegistered",
    "path_registration": "PathRegistrationContentRegistered",
}
_ACCEPTED = {
    "dossier_expected_set": "DossierExpectedSetAccepted",
    "path_registration": "PathRegistrationAccepted",
}
_W2_SCHEMAS = {
    "ReviewRequested": "ars://core/event/ReviewRequested",
    "ReviewVerdictRecorded": "ars://core/event/ReviewVerdictRecorded",
    "DecisionProposed": "ars://core/event/DecisionProposed",
    "DecisionResolved": "ars://core/event/DecisionResolved",
}


def subject_sha256(subject: Mapping[str, object]) -> str:
    """Hash the complete authority subject, excluding only its digest field."""

    preimage = dict(subject)
    preimage.pop("subject_sha256", None)
    return sha256_hex(canonical_bytes(preimage))


def _content_sha256(subject: Mapping[str, object]) -> str:
    """Hash only the serialized Stage-B content carried by an authority subject."""

    preimage = {
        key: value
        for key, value in subject.items()
        if key not in {"content_sha256", "subject_sha256"} and not key.startswith("authority_file_")
    }
    return sha256_hex(canonical_bytes(preimage))


def _sha256(value: object, label: str) -> str:
    """Validate and return one lowercase SHA-256 value."""
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise AuthorityRejected(f"invalid_{label}")
    return value


def _identity(value: object, label: str) -> str:
    """Validate and return one non-empty immutable identity."""
    if not isinstance(value, str) or not value:
        raise AuthorityRejected(f"invalid_{label}")
    return value


def validate_registered_roots(value: object) -> tuple[dict[str, object], ...]:
    """Validate the exact authorized registered-root authority payload."""

    required = {"root_id", "path", "registration_revision", "registration_hash", "authorized"}
    if not isinstance(value, list) or not value:
        raise AuthorityRejected("invalid_registered_roots")
    roots: list[dict[str, object]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != required:
            raise AuthorityRejected("invalid_registered_root")
        root_id = _identity(raw.get("root_id"), "root_id")
        path = _identity(raw.get("path"), "root_path")
        revision = raw.get("registration_revision")
        if (
            root_id in seen
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
            or raw.get("authorized") is not True
        ):
            raise AuthorityRejected("invalid_registered_root")
        seen.add(root_id)
        roots.append(
            {
                "root_id": root_id,
                "path": path,
                "registration_revision": revision,
                "registration_hash": _sha256(raw.get("registration_hash"), "registration_hash"),
                "authorized": True,
            }
        )
    return tuple(roots)


def _validate_registered_subject(
    kind: str,
    subject: Mapping[str, object],
    state: Mapping[str, Mapping[str, object]],
) -> None:
    """Join the accepted outer authority envelope to its complete nested subject."""

    _identity(subject.get("record_id"), "record_id")
    _identity(subject.get("project_id"), "project_id")
    _identity(subject.get("scope_id"), "scope_id")
    if kind == "dossier_expected_set":
        expected = subject.get("expected_set")
        profile = subject.get("admission_profile_decision")
        if (
            not isinstance(expected, Mapping)
            or not isinstance(profile, Mapping)
            or subject.get("record_id") != expected.get("expected_set_id")
            or subject.get("record_revision") != expected.get("revision")
            or subject.get("project_id") != expected.get("project_id")
            or subject.get("scope_id") != expected.get("dossier_id")
            or subject.get("content_sha256") != expected.get("content_hash")
            or profile.get("profile_id") != expected.get("admission_profile_id")
            or profile.get("profile_revision") != expected.get("admission_profile_revision")
            or profile.get("dispatchable") is not False
            or profile.get("provider_execution") != "forbidden"
        ):
            raise AuthorityRejected("subject_envelope_mismatch")
        _sha256(subject.get("content_sha256"), "content_sha256")
    else:
        validate_registered_roots(subject.get("registered_roots"))
        dossier = state.get("dossier_expected_set")
        dossier_subject = dossier.get("subject") if isinstance(dossier, Mapping) else None
        expected = dossier_subject.get("expected_set") if isinstance(dossier_subject, Mapping) else None
        content_digest = _sha256(subject.get("content_sha256"), "content_sha256")
        if (
            not isinstance(dossier, Mapping)
            or not isinstance(expected, Mapping)
            or dossier.get("status") != "accepted"
            or subject.get("scope_id") != expected.get("dossier_id")
            or subject.get("project_id") != expected.get("project_id")
        ):
            raise AuthorityRejected("path_scope_mismatch")
        if content_digest != _content_sha256(subject):
            raise AuthorityRejected("content_hash_mismatch")


def _event(kind: str, action: str, event_type: str, payload: Mapping[str, object]) -> dict[str, object]:
    """Build one immutable authority transition event."""
    return {
        "owner_row_id": _ROWS[kind][action],
        "authority_kind": kind,
        "event_type": event_type,
        "payload": deepcopy(dict(payload)),
    }


def replay_authority(events: Iterable[Mapping[str, object]]) -> dict[str, dict[str, object]]:
    """Rebuild accepted authority solely from immutable ordered events."""

    state: dict[str, dict[str, object]] = {}
    for raw_event in events:
        event = deepcopy(dict(raw_event))
        kind = event.get("authority_kind")
        if kind not in _KINDS:
            raise AuthorityRejected("unknown_authority_kind")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise AuthorityRejected("invalid_event_payload")
        current = state.get(kind)
        event_type = event.get("event_type")

        if event_type == _REGISTERED[kind]:
            if current is not None:
                raise AuthorityRejected("identity_collision")
            subject = payload.get("subject")
            if not isinstance(subject, dict):
                raise AuthorityRejected("invalid_subject")
            digest = _sha256(subject.get("subject_sha256"), "subject_sha256")
            if subject_sha256(subject) != digest:
                raise AuthorityRejected("subject_hash_mismatch")
            revision = subject.get("record_revision")
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
                raise AuthorityRejected("stale_revision")
            if subject.get("authority_kind") != kind:
                raise AuthorityRejected("subject_kind_mismatch")
            if kind == "path_registration" and subject.get("collision_status", "no_collision") != "no_collision":
                raise AuthorityRejected("path_collision")
            _validate_registered_subject(kind, subject, state)
            author = _identity(payload.get("actor_id"), "actor_id")
            state[kind] = {
                "status": "registered",
                "subject": subject,
                "subject_sha256": digest,
                "actors": {"author": author},
            }
            continue
        if current is None:
            raise AuthorityRejected("authority_not_registered")
        status = current["status"]
        actors = current["actors"]

        if event_type == "W11AuthorityFileObserved":
            if status != "registered":
                raise AuthorityRejected("invalid_observation_order")
            observer = _identity(payload.get("actor_id"), "actor_id")
            if observer == actors["author"]:
                raise AuthorityRejected("actor_not_independent")
            if payload.get("subject_sha256") != current["subject_sha256"]:
                raise AuthorityRejected("subject_hash_mismatch")
            subject = current["subject"]
            expected_file_identity = {
                "repository_path": subject.get("authority_file_path"),
                "git_commit": subject.get("authority_file_git_commit"),
                "git_blob": subject.get("authority_file_git_blob"),
                "file_size": subject.get("authority_file_size"),
                "file_sha256": subject.get("authority_file_sha256"),
            }
            if any(payload.get(key) != value for key, value in expected_file_identity.items()):
                raise AuthorityRejected("file_identity_mismatch")
            current.update(
                status="observed",
                file_sha256=_sha256(payload.get("file_sha256"), "file_sha256"),
                file_observation=payload,
            )
            actors["observer"] = observer
        elif event_type == "ReviewRequested":
            if status != "observed":
                raise AuthorityRejected("invalid_review_request_order")
            if payload.get("subject_sha256") != current["subject_sha256"]:
                raise AuthorityRejected("subject_hash_mismatch")
            if payload.get("file_sha256") != current["file_sha256"]:
                raise AuthorityRejected("file_identity_mismatch")
            reviewer = payload.get("reviewer_actor_id")
            requester = _identity(payload.get("actor_id"), "actor_id")
            reviewer = _identity(reviewer, "reviewer_actor_id")
            if reviewer in {actors["author"], actors["observer"], requester}:
                raise AuthorityRejected("actor_not_independent")
            current.update(status="review_requested", review_id=_identity(payload.get("review_id"), "review_id"))
            actors["review_requester"] = requester
            actors["reviewer"] = reviewer
        elif event_type == "ReviewVerdictRecorded":
            if status != "review_requested" or payload.get("actor_id") != actors["reviewer"]:
                raise AuthorityRejected("invalid_review_actor_or_order")
            if payload.get("verdict") != "approve":
                raise AuthorityRejected("review_not_positive")
            if payload.get("unchanged_subject_sha256") != current["subject_sha256"]:
                raise AuthorityRejected("subject_hash_mismatch")
            if payload.get("unchanged_file_sha256") != current["file_sha256"]:
                raise AuthorityRejected("file_identity_mismatch")
            _sha256(payload.get("reconstruction_sha256"), "reconstruction_sha256")
            current.update(status="reviewed", review_verdict=payload)
        elif event_type == "DecisionProposed":
            proposer = _identity(payload.get("actor_id"), "actor_id")
            decision_id = _identity(payload.get("decision_id"), "decision_id")
            if status != "reviewed" or payload.get("proposed_decision") != "accept":
                raise AuthorityRejected("invalid_decision_proposal")
            if (
                payload.get("subject_sha256") != current["subject_sha256"]
                or payload.get("file_sha256") != current["file_sha256"]
            ):
                raise AuthorityRejected("decision_subject_mismatch")
            if proposer in set(actors.values()):
                raise AuthorityRejected("actor_not_independent")
            current.update(status="decision_proposed", decision_id=decision_id)
            actors["decision_proposer"] = proposer
        elif event_type == "DecisionResolved":
            if status != "decision_proposed" or payload.get("decision_id") != current["decision_id"]:
                raise AuthorityRejected("invalid_owner_resolution")
            owner = _identity(payload.get("actor_id"), "actor_id")
            transaction_id = _identity(payload.get("transaction_id"), "transaction_id")
            if payload.get("decision") != "accept" or owner in set(actors.values()):
                raise AuthorityRejected("owner_not_independent")
            current.update(status="resolved", transaction_id=transaction_id)
            actors["owner"] = owner
        elif event_type == _ACCEPTED[kind]:
            if status != "resolved" or payload.get("transaction_id") != current["transaction_id"]:
                raise AuthorityRejected("acceptance_transaction_mismatch")
            if (
                payload.get("subject_sha256") != current["subject_sha256"]
                or payload.get("file_sha256") != current["file_sha256"]
            ):
                raise AuthorityRejected("acceptance_subject_mismatch")
            current["status"] = "accepted"
        else:
            raise AuthorityRejected("unexpected_authority_event")
    return state


def prepare_authority_transition(
    *,
    events: Iterable[Mapping[str, object]],
    kind: str,
    action: str,
    actor_id: str,
    payload: Mapping[str, object],
) -> tuple[dict[str, object], ...]:
    """Validate one OR row and prepare its complete ordered event write-set."""

    if kind not in _KINDS or action not in _ROWS[kind]:
        raise AuthorityRejected("unsupported_authority_transition")
    history = tuple(events)
    state = replay_authority(history)
    current = state.get(kind)
    if current is not None and current.get("status") == "accepted":
        raise AuthorityRejected("already_accepted")

    base = deepcopy(dict(payload))
    base["actor_id"] = actor_id
    if action == "register":
        if current is not None:
            raise AuthorityRejected("identity_collision")
        candidate = _event(kind, action, _REGISTERED[kind], base)
    elif action == "observe":
        if current is None or current["status"] != "registered":
            raise AuthorityRejected("invalid_observation_order")
        _sha256(base.get("file_sha256"), "file_sha256")
        if not isinstance(base.get("file_size"), int) or base["file_size"] < 0:
            raise AuthorityRejected("invalid_file_size")
        candidate = _event(kind, action, "W11AuthorityFileObserved", base)
    elif action == "request_review":
        if current is None:
            raise AuthorityRejected("authority_not_registered")
        base.update(
            schema_id=_W2_SCHEMAS["ReviewRequested"],
            schema_version="1.0.0",
            review_id=f"rev_{kind}_{current['subject_sha256'][:12]}",
            subject_sha256=current["subject_sha256"],
            file_sha256=current.get("file_sha256"),
        )
        candidate = _event(kind, action, "ReviewRequested", base)
    elif action == "record_review":
        if current is None:
            raise AuthorityRejected("authority_not_registered")
        if current["status"] != "review_requested":
            raise AuthorityRejected("invalid_review_actor_or_order")
        base.update(schema_id=_W2_SCHEMAS["ReviewVerdictRecorded"], schema_version="1.0.0")
        candidate = _event(kind, action, "ReviewVerdictRecorded", base)
    elif action == "propose":
        if current is None:
            raise AuthorityRejected("authority_not_registered")
        base.update(
            schema_id=_W2_SCHEMAS["DecisionProposed"],
            schema_version="1.0.0",
            subject_sha256=current["subject_sha256"],
            file_sha256=current.get("file_sha256"),
        )
        candidate = _event(kind, action, "DecisionProposed", base)
    else:
        if current is None:
            raise AuthorityRejected("authority_not_registered")
        if current["status"] != "decision_proposed":
            raise AuthorityRejected("invalid_owner_resolution")
        base.update(schema_id=_W2_SCHEMAS["DecisionResolved"], schema_version="1.0.0")
        resolved = _event(kind, action, "DecisionResolved", base)
        accepted_payload = {
            "authority_kind": kind,
            "subject": deepcopy(current["subject"]),
            "subject_sha256": current["subject_sha256"],
            "file_observation": deepcopy(current["file_observation"]),
            "file_sha256": current["file_sha256"],
            "review_verdict": deepcopy(current["review_verdict"]),
            "decision_id": base.get("decision_id"),
            "transaction_id": base.get("transaction_id"),
            "acceptor_actor_id": actor_id,
        }
        prepared = (resolved, _event(kind, action, _ACCEPTED[kind], accepted_payload))
        replay_authority((*history, *prepared))
        return prepared

    replay_authority((*history, candidate))
    return (candidate,)
