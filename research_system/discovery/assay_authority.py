"""Replay the closed OR-101--OR-109 Assay-bar authority chain."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from research_system.canonical import canonical_bytes, sha256_hex


class AssayAuthorityRejected(ValueError):
    """The Assay-bar authority chain is incomplete, stale, or tampered."""


def _digest(value: object, label: str) -> str:
    """Return one exact lowercase SHA-256 identity or reject it."""

    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise AssayAuthorityRejected(f"invalid_{label}")
    return value


def _identity(value: object, label: str) -> str:
    """Return one non-empty authority identity or reject it."""

    if not isinstance(value, str) or not value:
        raise AssayAuthorityRejected(f"invalid_{label}")
    return value


def _record_ref(value: object, label: str) -> dict[str, Any]:
    """Validate and copy one immutable record reference."""

    if not isinstance(value, dict) or set(value) != {"id", "record_revision", "content_hash"}:
        raise AssayAuthorityRejected(f"invalid_{label}")
    record_id = _identity(value.get("id"), f"{label}_id")
    revision = value.get("record_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise AssayAuthorityRejected(f"invalid_{label}_revision")
    return {
        "id": record_id,
        "record_revision": revision,
        "content_hash": _digest(value.get("content_hash"), f"{label}_content_hash"),
    }


def content_sha256(content: Mapping[str, Any]) -> str:
    """Hash exact W11 content while excluding its declared self-digest."""

    preimage = dict(content)
    preimage.pop("content_hash", None)
    return sha256_hex(canonical_bytes(preimage))


def producer_relation_sha256(producer_ref: Mapping[str, Any]) -> str:
    """Hash the exact prospective producer relation used by OR-003."""

    return sha256_hex(canonical_bytes(dict(producer_ref)))


def assay_reconstruction_sha256(state: Mapping[str, Any], context_manifest_id: str) -> str:
    """Hash the exact Assay-bar review context reconstructed from durable authority state."""

    manifest_id = _identity(context_manifest_id, "context_manifest_id")
    contents = state.get("contents")
    observations = state.get("observations")
    if not isinstance(contents, Mapping) or not isinstance(observations, Mapping):
        raise AssayAuthorityRejected("invalid_reconstruction_context")
    rubric = contents.get("rubric")
    scope = contents.get("scope")
    rubric_observation = observations.get("rubric")
    scope_observation = observations.get("scope")
    if not all(isinstance(value, Mapping) for value in (rubric, scope, rubric_observation, scope_observation)):
        raise AssayAuthorityRejected("invalid_reconstruction_context")
    rubric_content = rubric.get("content")
    scope_content = scope.get("content")
    if not isinstance(rubric_content, Mapping) or not isinstance(scope_content, Mapping):
        raise AssayAuthorityRejected("invalid_reconstruction_context")
    manifest = {
        "context_manifest_id": manifest_id,
        "authority_kind": "assay_bar",
        "subject_sha256": _digest(state.get("subject_sha256"), "subject_sha256"),
        "rubric_ref": {
            "id": _identity(rubric_content.get("record_id"), "rubric_record_id"),
            "record_revision": rubric_content.get("record_revision"),
            "content_hash": _digest(rubric.get("content_sha256"), "rubric_content_hash"),
        },
        "scope_ref": {
            "id": _identity(scope_content.get("record_id"), "scope_record_id"),
            "record_revision": scope_content.get("record_revision"),
            "content_hash": _digest(scope.get("content_sha256"), "scope_content_hash"),
        },
        "rubric_file_sha256": _digest(rubric_observation.get("file_sha256"), "rubric_file_sha256"),
        "scope_file_sha256": _digest(scope_observation.get("file_sha256"), "scope_file_sha256"),
        "prospective_producer_ref": _record_ref(state.get("prospective_producer_ref"), "prospective_producer_ref"),
    }
    if not all(
        type(manifest[key].get("record_revision")) is int and manifest[key]["record_revision"] >= 1
        for key in ("rubric_ref", "scope_ref")
    ):
        raise AssayAuthorityRejected("invalid_reconstruction_context")
    return sha256_hex(canonical_bytes(manifest))


def replay_assay_bar_authority(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Rebuild the current Assay-bar authority solely from ordered events."""

    state: dict[str, Any] = {
        "contents": {},
        "observations": {},
        "status": "empty",
        "history": [],
    }
    actors: set[str] = set()
    for raw_event in events:
        if raw_event.get("authority_kind") != "assay_bar":
            raise AssayAuthorityRejected("unknown_authority_kind")
        raw_payload = raw_event.get("payload")
        if not isinstance(raw_payload, Mapping):
            raise AssayAuthorityRejected("invalid_event_payload")
        payload = deepcopy(dict(raw_payload))
        event_type = raw_event.get("event_type")

        if event_type in {"AssayRubricContentRegistered", "AssayEvidenceScopeContentRegistered"}:
            kind = "rubric" if event_type == "AssayRubricContentRegistered" else "scope"
            content = payload.get("content")
            if not isinstance(content, dict):
                raise AssayAuthorityRejected("invalid_content")
            if state["status"] == "stale":
                if kind != "rubric":
                    raise AssayAuthorityRejected("invalid_successor_order")
                prior_revision = state["contents"].get(kind, {}).get("content", {}).get("record_revision")
                if (
                    type(prior_revision) is not int
                    or prior_revision < 1
                    or type(content.get("record_revision")) is not int
                    or content["record_revision"] < 1
                ):
                    raise AssayAuthorityRejected("stale_revision")
                if (
                    content["record_revision"] != prior_revision + 1
                    or content.get("supersedes_revision") != prior_revision
                ):
                    raise AssayAuthorityRejected("stale_revision")
                history = state["history"]
                history.append({key: deepcopy(value) for key, value in state.items() if key != "history"})
                predecessor_contents = deepcopy(state["contents"])
                state.clear()
                state.update(
                    contents={},
                    observations={},
                    status="empty",
                    history=history,
                    predecessor_contents=predecessor_contents,
                )
                actors.clear()
            if kind in state["contents"] or state["status"] not in {"empty", "content_registered"}:
                raise AssayAuthorityRejected("identity_collision")
            digest = _digest(content.get("content_hash"), "content_hash")
            if content_sha256(content) != digest or payload.get("content_sha256") != digest:
                raise AssayAuthorityRejected("content_hash_mismatch")
            authority_file_path = payload.get("authority_file_path")
            if not isinstance(authority_file_path, str) or not authority_file_path:
                raise AssayAuthorityRejected("authority_file_path_missing")
            actor_id = _identity(payload.get("actor_id"), "actor_id")
            predecessor_contents = state.get("predecessor_contents")
            if kind == "scope" and isinstance(predecessor_contents, Mapping):
                prior_scope = predecessor_contents.get("scope")
                prior_scope_content = prior_scope.get("content") if isinstance(prior_scope, Mapping) else None
                prior_revision = (
                    prior_scope_content.get("record_revision") if isinstance(prior_scope_content, Mapping) else None
                )
                if (
                    type(prior_revision) is not int
                    or prior_revision < 1
                    or type(content.get("record_revision")) is not int
                    or content["record_revision"] < 1
                    or content.get("record_revision") != prior_revision + 1
                    or content.get("supersedes_revision") != prior_revision
                ):
                    raise AssayAuthorityRejected("stale_revision")
            if kind == "scope":
                rubric = state["contents"].get("rubric")
                rubric_content = rubric.get("content") if isinstance(rubric, Mapping) else None
                if not isinstance(rubric_content, Mapping) or content.get("rubric_ref") != {
                    "id": rubric_content.get("record_id"),
                    "record_revision": rubric_content.get("record_revision"),
                    "content_hash": rubric.get("content_sha256"),
                }:
                    raise AssayAuthorityRejected("scope_rubric_mismatch")
            state["contents"][kind] = {
                "content": content,
                "content_sha256": digest,
                "authority_file_path": authority_file_path,
                "author_actor_id": actor_id,
            }
            actors.add(actor_id)
            state["status"] = "content_registered"
            continue

        if event_type == "W11AuthorityFileObserved":
            kind = payload.get("content_kind")
            if kind not in {"rubric", "scope"}:
                raise AssayAuthorityRejected("invalid_observation_order")
            content_state = state["contents"].get(kind)
            if not isinstance(content_state, dict) or kind in state["observations"]:
                raise AssayAuthorityRejected("invalid_observation_order")
            observer = _identity(payload.get("actor_id"), "actor_id")
            if observer in actors:
                raise AssayAuthorityRejected("actor_not_independent")
            if payload.get("content_sha256") != content_state.get("content_sha256"):
                raise AssayAuthorityRejected("content_hash_mismatch")
            _digest(payload.get("file_sha256"), "file_sha256")
            state["observations"][kind] = deepcopy(payload)
            actors.add(observer)
            state["status"] = "observed" if set(state["observations"]) == {"rubric", "scope"} else "content_registered"
            continue

        if event_type == "ReviewRequested":
            if state["status"] != "observed":
                raise AssayAuthorityRejected("invalid_review_request_order")
            reviewer = payload.get("reviewer_actor_id")
            requester = _identity(payload.get("actor_id"), "actor_id")
            reviewer = _identity(reviewer, "reviewer_actor_id")
            if reviewer in actors or reviewer == requester:
                raise AssayAuthorityRejected("actor_not_independent")
            producer_ref = _record_ref(payload.get("prospective_producer_ref"), "producer_relation")
            if reviewer == producer_ref["id"]:
                raise AssayAuthorityRejected("actor_not_independent")
            subject = {
                "rubric_sha256": state["contents"]["rubric"]["content_sha256"],
                "scope_sha256": state["contents"]["scope"]["content_sha256"],
                "rubric_file_sha256": state["observations"]["rubric"]["file_sha256"],
                "scope_file_sha256": state["observations"]["scope"]["file_sha256"],
                "prospective_producer_ref": producer_ref,
            }
            subject_hash = sha256_hex(canonical_bytes(subject))
            if payload.get("subject_sha256") != subject_hash:
                raise AssayAuthorityRejected("subject_hash_mismatch")
            state.update(
                status="review_requested",
                review_id=_identity(payload.get("review_id"), "review_id"),
                reviewer_actor_id=reviewer,
                prospective_producer_ref=producer_ref,
                producer_relation_sha256=producer_relation_sha256(producer_ref),
                subject=subject,
                subject_sha256=subject_hash,
            )
            actors.update({requester, reviewer})
            continue

        if event_type == "ReviewVerdictRecorded":
            if (
                state["status"] != "review_requested"
                or payload.get("actor_id") != state.get("reviewer_actor_id")
                or payload.get("verdict") != "approve"
                or payload.get("unchanged_subject_sha256") != state.get("subject_sha256")
            ):
                raise AssayAuthorityRejected("invalid_review_verdict")
            context_manifest_id = _identity(payload.get("context_manifest_id"), "context_manifest_id")
            if payload.get("reconstruction_sha256") != assay_reconstruction_sha256(state, context_manifest_id):
                raise AssayAuthorityRejected("reconstruction_hash_mismatch")
            state.update(status="reviewed", review_verdict=deepcopy(payload))
            continue

        if event_type == "DecisionProposed":
            proposer = _identity(payload.get("actor_id"), "actor_id")
            decision_id = _identity(payload.get("decision_id"), "decision_id")
            if (
                state["status"] != "reviewed"
                or payload.get("proposed_decision") != "accept"
                or payload.get("subject_sha256") != state.get("subject_sha256")
                or proposer in actors
            ):
                raise AssayAuthorityRejected("invalid_decision_proposal")
            state.update(status="decision_proposed", decision_id=decision_id)
            actors.add(proposer)
            continue

        if event_type == "DecisionResolved":
            owner = _identity(payload.get("actor_id"), "actor_id")
            transaction_id = _identity(payload.get("transaction_id"), "transaction_id")
            if (
                state["status"] != "decision_proposed"
                or payload.get("decision_id") != state.get("decision_id")
                or payload.get("decision") != "accept"
                or owner in actors
            ):
                raise AssayAuthorityRejected("invalid_owner_resolution")
            state.update(status="resolved", transaction_id=transaction_id)
            continue

        if event_type == "AssayBarAccepted":
            if state["status"] != "resolved" or payload.get("transaction_id") != state.get("transaction_id"):
                raise AssayAuthorityRejected("acceptance_transaction_mismatch")
            if payload.get("subject_sha256") != state.get("subject_sha256") or payload.get(
                "producer_relation_sha256"
            ) != state.get("producer_relation_sha256"):
                raise AssayAuthorityRejected("acceptance_subject_mismatch")
            acceptance = deepcopy(payload)
            state.update(
                status="accepted",
                acceptance=acceptance,
                acceptance_sha256=sha256_hex(canonical_bytes(acceptance)),
                accepted_global_position=payload.get("accepted_global_position"),
            )
            continue

        if event_type == "AssayBarStaled":
            if state["status"] != "accepted" or payload.get("acceptance_sha256") != state.get("acceptance_sha256"):
                raise AssayAuthorityRejected("invalid_staleness_transition")
            state.update(status="stale", staleness=deepcopy(payload))
            continue

        raise AssayAuthorityRejected("unexpected_authority_event")
    return state
