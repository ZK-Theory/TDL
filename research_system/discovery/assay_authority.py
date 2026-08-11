"""Replay the closed OR-101--OR-109 Assay-bar authority chain."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from research_system.canonical import canonical_bytes, sha256_hex


class AssayAuthorityRejected(ValueError):
    """The Assay-bar authority chain is incomplete, stale, or tampered."""


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise AssayAuthorityRejected(f"invalid_{label}")
    return value


def content_sha256(content: Mapping[str, Any]) -> str:
    """Hash exact W11 content while excluding its declared self-digest."""

    preimage = dict(content)
    preimage.pop("content_hash", None)
    return sha256_hex(canonical_bytes(preimage))


def producer_relation_sha256(producer_ref: Mapping[str, Any]) -> str:
    """Hash the exact prospective producer relation used by OR-003."""

    return sha256_hex(canonical_bytes(dict(producer_ref)))


def replay_assay_bar_authority(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Rebuild the current Assay-bar authority solely from ordered events."""

    state: dict[str, Any] = {
        "contents": {},
        "observations": {},
        "status": "empty",
        "history": [],
    }
    actors: set[object] = set()
    for raw_event in events:
        event = deepcopy(dict(raw_event))
        if event.get("authority_kind") != "assay_bar":
            raise AssayAuthorityRejected("unknown_authority_kind")
        payload = event.get("payload")
        if not isinstance(payload, dict):
            raise AssayAuthorityRejected("invalid_event_payload")
        event_type = event.get("event_type")

        if event_type in {"AssayRubricContentRegistered", "AssayEvidenceScopeContentRegistered"}:
            kind = "rubric" if event_type == "AssayRubricContentRegistered" else "scope"
            content = payload.get("content")
            if not isinstance(content, dict):
                raise AssayAuthorityRejected("invalid_content")
            if state["status"] == "stale":
                if kind != "rubric":
                    raise AssayAuthorityRejected("invalid_successor_order")
                prior_revision = state["contents"].get(kind, {}).get("content", {}).get("record_revision")
                if not isinstance(prior_revision, int) or not isinstance(content.get("record_revision"), int):
                    raise AssayAuthorityRejected("stale_revision")
                if content["record_revision"] <= prior_revision:
                    raise AssayAuthorityRejected("stale_revision")
                history = state["history"]
                history.append({key: deepcopy(value) for key, value in state.items() if key != "history"})
                state.clear()
                state.update(contents={}, observations={}, status="empty", history=history)
                actors.clear()
            if kind in state["contents"] or state["status"] not in {"empty", "content_registered"}:
                raise AssayAuthorityRejected("identity_collision")
            digest = _digest(content.get("content_hash"), "content_hash")
            if content_sha256(content) != digest or payload.get("content_sha256") != digest:
                raise AssayAuthorityRejected("content_hash_mismatch")
            if not isinstance(payload.get("authority_file_path"), str):
                raise AssayAuthorityRejected("authority_file_path_missing")
            state["contents"][kind] = {
                "content": content,
                "content_sha256": digest,
                "authority_file_path": payload["authority_file_path"],
                "author_actor_id": payload.get("actor_id"),
            }
            actors.add(payload.get("actor_id"))
            state["status"] = "content_registered"
            continue

        if event_type == "W11AuthorityFileObserved":
            kind = payload.get("content_kind")
            content_state = state["contents"].get(kind)
            if not isinstance(content_state, dict) or kind in state["observations"]:
                raise AssayAuthorityRejected("invalid_observation_order")
            if payload.get("actor_id") in actors:
                raise AssayAuthorityRejected("actor_not_independent")
            if payload.get("content_sha256") != content_state.get("content_sha256"):
                raise AssayAuthorityRejected("content_hash_mismatch")
            _digest(payload.get("file_sha256"), "file_sha256")
            state["observations"][kind] = deepcopy(payload)
            actors.add(payload.get("actor_id"))
            state["status"] = "observed" if set(state["observations"]) == {"rubric", "scope"} else "content_registered"
            continue

        if event_type == "ReviewRequested":
            if state["status"] != "observed":
                raise AssayAuthorityRejected("invalid_review_request_order")
            reviewer = payload.get("reviewer_actor_id")
            if reviewer in actors or reviewer == payload.get("actor_id"):
                raise AssayAuthorityRejected("actor_not_independent")
            producer_ref = payload.get("prospective_producer_ref")
            if not isinstance(producer_ref, dict):
                raise AssayAuthorityRejected("invalid_producer_relation")
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
                review_id=payload.get("review_id"),
                reviewer_actor_id=reviewer,
                prospective_producer_ref=producer_ref,
                producer_relation_sha256=producer_relation_sha256(producer_ref),
                subject=subject,
                subject_sha256=subject_hash,
            )
            actors.update({payload.get("actor_id"), reviewer})
            continue

        if event_type == "ReviewVerdictRecorded":
            if (
                state["status"] != "review_requested"
                or payload.get("actor_id") != state.get("reviewer_actor_id")
                or payload.get("verdict") != "approve"
                or payload.get("unchanged_subject_sha256") != state.get("subject_sha256")
            ):
                raise AssayAuthorityRejected("invalid_review_verdict")
            _digest(payload.get("reconstruction_sha256"), "reconstruction_sha256")
            state.update(status="reviewed", review_verdict=deepcopy(payload))
            continue

        if event_type == "DecisionProposed":
            if (
                state["status"] != "reviewed"
                or payload.get("proposed_decision") != "accept"
                or payload.get("subject_sha256") != state.get("subject_sha256")
                or payload.get("actor_id") in actors
            ):
                raise AssayAuthorityRejected("invalid_decision_proposal")
            state.update(status="decision_proposed", decision_id=payload.get("decision_id"))
            actors.add(payload.get("actor_id"))
            continue

        if event_type == "DecisionResolved":
            if (
                state["status"] != "decision_proposed"
                or payload.get("decision_id") != state.get("decision_id")
                or payload.get("decision") != "accept"
                or payload.get("actor_id") in actors
            ):
                raise AssayAuthorityRejected("invalid_owner_resolution")
            state.update(status="resolved", transaction_id=payload.get("transaction_id"))
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
            )
            continue

        if event_type == "AssayBarStaled":
            if state["status"] != "accepted" or payload.get("acceptance_sha256") != state.get("acceptance_sha256"):
                raise AssayAuthorityRejected("invalid_staleness_transition")
            state.update(status="stale", staleness=deepcopy(payload))
            continue

        raise AssayAuthorityRejected("unexpected_authority_event")
    return state
