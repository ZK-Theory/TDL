"""Read interface over the replayed W9 legacy projection (WP9.4 note §4.2, §4.3, §7, §9).

A pure leaf module: imports only standard library and :class:`~research_system.errors.IntegrityError`. Downstream
guards outside :mod:`research_system.legacy` read the legacy projection through this interface rather than importing
internal reducers or state structures.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from research_system.errors import IntegrityError

ADOPTION_REF_PATTERN = re.compile(
    r"^w9-adoption:(obj_[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})\Z"
)
_ROOT_ROLE = "legacy_manuscript_root"


def _source_path(source: Mapping[str, Any]) -> Any:
    kind = source.get("identity_kind")
    if kind == "vault_file":
        return source.get("vault_path")
    if kind == "git_tracked":
        return source.get("repository_path")
    return source.get("path")


def _item_selector_key(selector: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        selector.get("selector_kind"),
        selector.get("row_ordinal"),
        selector.get("anchor_text"),
        selector.get("raw_row_sha256"),
    )


def adoption_suspension_cause(state: Mapping[str, Any], adoption: Mapping[str, Any]) -> str | None:
    """Derive ``P:legacy-adoption-status`` for one adoption record (annex ``suspension_rule``; WP9.4 note §7).

    Suspension is derived at replay from the current projection, never stored in the adoption record:

    1. **Supersession** of the adoption itself, its observation, or that observation's closed-reference acceptance.
    2. **Recorded use-time mismatch** naming the adoption (``legacy_adoption_use_mismatch`` / LR-061).
    3. **Stale observation** (its own observation in ``stale_observations``, M-1) or a **later observation** of its
       source: for a whole-file adoption, any later observation of the registration (or, for a
       ``legacy_manuscript_root``, any later observation with the same source path); for a family adoption, any later
       ``json_family_set`` observation of the registration naming an adopted family (or, for a
       ``legacy_manuscript_root``, any later such observation with the same source path); for an item observation
       (forward-compatible), any later matching item selector.
    """

    adoption_id = adoption.get("record_id")
    supersessions = state.get("supersessions", {})
    if adoption_id in supersessions:
        return "adoption_superseded"

    obs_ref = adoption.get("observation_ref")
    obs_id = obs_ref.get("id") if isinstance(obs_ref, Mapping) else None
    if obs_id in supersessions:
        return "observation_superseded"

    records = state.get("records", {})
    acceptances = records.get("legacy_closed_reference_acceptance", {})
    matching_acceptances = [
        acc_id
        for acc_id, acc in acceptances.items()
        if any(
            isinstance(item.get("observation_ref"), Mapping) and item["observation_ref"].get("id") == obs_id
            for item in acc.get("items", ())
        )
    ]
    if any(acc_id in supersessions for acc_id in matching_acceptances):
        return "acceptance_superseded"

    mismatches = records.get("legacy_adoption_use_mismatch", {})
    if any(
        isinstance(mismatch.get("adoption_ref"), Mapping) and mismatch["adoption_ref"].get("id") == adoption_id
        for mismatch in mismatches.values()
    ):
        return "use_mismatch"

    if obs_id in state.get("stale_observations", ()):
        return "observation_stale"

    observations = records.get("legacy_observation", {})
    obs = observations.get(obs_id)
    if obs is None:
        return None

    reg_ref = obs.get("registration_ref")
    reg_id = reg_ref.get("id") if isinstance(reg_ref, Mapping) else None
    reg = records.get("legacy_path_registration", {}).get(reg_id, {})
    history = state.get("observations_by_registration", {}).get(reg_id, ())
    if obs_id not in history:
        return None

    later_ids = history[history.index(obs_id) + 1 :]
    subject = adoption.get("subject", {})
    subject_kind = subject.get("subject_kind")
    obs_sel = obs.get("selector", {})
    obs_path = _source_path(obs.get("source_identity", {}))
    adopted_families = set(subject.get("family_names", ()))

    for other_id in later_ids:
        other = observations.get(other_id)
        if other is None:
            continue
        other_sel = other.get("selector", {})
        if subject_kind == "whole_file":
            if reg.get("role") == _ROOT_ROLE:
                if _source_path(other.get("source_identity", {})) == obs_path:
                    return "later_observation"
            else:
                return "later_observation"
        elif subject_kind == "families":
            if other_sel.get("selector_kind") == "json_family_set" and (
                set(other_sel.get("family_names", ())) & adopted_families
            ):
                if reg.get("role") != _ROOT_ROLE or _source_path(other.get("source_identity", {})) == obs_path:
                    return "later_observation"
        elif obs_sel.get("selector_kind") == "inventory_item":
            if other_sel.get("selector_kind") == "inventory_item" and _item_selector_key(
                other_sel
            ) == _item_selector_key(obs_sel):
                return "later_observation"

    return None


def adoption_status(state: Mapping[str, Any], adoption_id: str) -> dict[str, Any]:
    """Return ``active`` or ``suspended`` with the suspension cause for one recorded adoption (§7, §9).

    Raises:
        IntegrityError: If ``adoption_id`` is not a recorded ``legacy_adoption_decision``.
    """

    adoption = state.get("records", {}).get("legacy_adoption_decision", {}).get(adoption_id)
    if adoption is None:
        raise IntegrityError(f"W9 adoption record not found: {adoption_id}")
    cause = adoption_suspension_cause(state, adoption)
    return {
        "adoption_id": adoption_id,
        "status": "active" if cause is None else "suspended",
        "cause": cause,
    }


def resolve_adoption_ref(state: Mapping[str, Any], ref: str) -> dict[str, Any]:
    """Resolve a ``w9-adoption:<obj_id>`` reference to its adoption and observed source identity (§4.3, §9).

    Returns the adoption's observation reference/ID, subject, intended use, derived status/cause, and the observed
    ``source_identity`` (``identity_kind``, ``path``, ``sha256``, ``git_blob`` or ``None``, ``byte_length``) for both
    family and whole-file adoptions.

    Raises:
        IntegrityError: If ``ref`` is malformed or names no recorded adoption or observation.
    """

    if not isinstance(ref, str):
        raise IntegrityError(f"W9 adoption ref is malformed: {ref!r}")
    match = ADOPTION_REF_PATTERN.match(ref)
    if match is None:
        raise IntegrityError(f"W9 adoption ref is malformed: {ref!r}")
    adoption_id = match.group(1)
    status = adoption_status(state, adoption_id)
    adoption = state["records"]["legacy_adoption_decision"][adoption_id]
    obs_ref = adoption["observation_ref"]
    obs_id = obs_ref["id"]
    observation = state.get("records", {}).get("legacy_observation", {}).get(obs_id)
    if observation is None:
        raise IntegrityError(f"W9 adoption observation not found: {obs_id}")
    src = observation.get("source_identity", {})
    return {
        "adoption_id": adoption_id,
        "observation_ref": deepcopy(obs_ref),
        "observation_id": obs_id,
        "subject": deepcopy(adoption["subject"]),
        "intended_use": deepcopy(adoption["intended_use"]),
        "status": status["status"],
        "cause": status["cause"],
        "source_identity": {
            "identity_kind": src.get("identity_kind"),
            "path": _source_path(src),
            "sha256": src.get("sha256"),
            "git_blob": src.get("git_blob"),
            "byte_length": src.get("byte_length"),
        },
    }


def _covers_family(adoption: Mapping[str, Any], family_name: str) -> bool:
    subject = adoption.get("subject", {})
    kind = subject.get("subject_kind")
    if kind == "families":
        return family_name in subject.get("family_names", ())
    if kind == "whole_file":
        return family_name == "whole_file"
    return False


def family_admissible(state: Mapping[str, Any], observation_id: str, family_name: str, use: str) -> dict[str, Any]:
    """Return whether ``(observation_id, family_name)`` is admissible under ``use`` (§6.2, §9).

    True only when an active adoption of ``observation_id`` covers ``family_name`` (or ``"whole_file"`` for a
    whole-file adoption) and its ``intended_use.description`` equals ``use`` exactly. Otherwise false with reason
    ``unadopted``, ``suspended``, or ``other_use``.
    """

    adoptions = state.get("records", {}).get("legacy_adoption_decision", {})
    matching = [
        (rec_id, adp)
        for rec_id, adp in adoptions.items()
        if isinstance(adp.get("observation_ref"), Mapping)
        and adp["observation_ref"].get("id") == observation_id
        and _covers_family(adp, family_name)
    ]
    if not matching:
        return {"admissible": False, "reason": "unadopted", "adoption_id": None}

    suspended_same_use: str | None = None
    has_other_use = False
    for rec_id, adp in matching:
        desc = adp.get("intended_use", {}).get("description")
        if desc == use:
            if adoption_suspension_cause(state, adp) is None:
                return {"admissible": True, "reason": None, "adoption_id": rec_id}
            if suspended_same_use is None:
                suspended_same_use = rec_id
        else:
            has_other_use = True

    if suspended_same_use is not None:
        return {"admissible": False, "reason": "suspended", "adoption_id": suspended_same_use}
    if has_other_use:
        return {"admissible": False, "reason": "other_use", "adoption_id": None}
    return {"admissible": False, "reason": "unadopted", "adoption_id": None}


def legacy_content_matches(
    state: Mapping[str, Any], sha256: str | None, git_blob: str | None = None
) -> list[dict[str, Any]]:
    """Return every recorded observation matching ``sha256``, or ``git_blob`` when both sides carry one (§4.2, §9).

    An absent or empty hash/blob never matches, so two untracked files lacking a Git blob never match on absence.
    Reads recorded observations only, never open proposals.
    """

    want_sha = sha256 if isinstance(sha256, str) and sha256 else None
    want_blob = git_blob if isinstance(git_blob, str) and git_blob else None
    if want_sha is None and want_blob is None:
        return []

    matches: list[dict[str, Any]] = []
    for observation in state.get("records", {}).get("legacy_observation", {}).values():
        src = observation.get("source_identity", {})
        obs_sha = src.get("sha256")
        obs_blob = src.get("git_blob")
        sha_hit = want_sha is not None and isinstance(obs_sha, str) and bool(obs_sha) and obs_sha == want_sha
        blob_hit = want_blob is not None and isinstance(obs_blob, str) and bool(obs_blob) and obs_blob == want_blob
        if sha_hit or blob_hit:
            matches.append(deepcopy(observation))
    return matches
