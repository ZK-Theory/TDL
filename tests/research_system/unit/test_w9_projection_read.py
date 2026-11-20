# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §4.2, §4.3, §7, §9, §15)
# Purpose: unit tests for research_system.legacy.projection_read (suspension projection, admissibility, ref resolution, content matching).
"""Unit tests for the legacy read interface (WP9.4-1 §4.2, §4.3, §7, §9)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy.projection_read import (
    adoption_status,
    adoption_suspension_cause,
    family_admissible,
    legacy_content_matches,
    resolve_adoption_ref,
)
from research_system.legacy.replay import reducers


def _state_with_family_adoption(
    *,
    role: str = "legacy_research_result",
    reg_path: str = "results/x.json",
    identity_kind: str = "git_tracked",
    git_blob: str | None = "1" * 40,
    sha256: str = "a" * 64,
    families: list[str] | None = None,
    use: str = "w9-use:claim-evidence/c1",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state = reducers.new_legacy_state()
    reg_id = new_id("scope_definition")
    obs_id = new_id("scope_definition")
    acc_id = new_id("scope_definition")
    adp_id = new_id("scope_definition")
    dec_id = new_id("decision")
    mem_id = new_id("scope_definition")

    reg = {
        "record_id": reg_id,
        "role": role,
        "normalized_path": reg_path,
        "source_identity_kind": identity_kind,
    }
    if identity_kind == "git_tracked":
        src = {
            "identity_kind": "git_tracked",
            "repository_path": reg_path,
            "git_commit": "0" * 40,
            "git_blob": git_blob,
            "sha256": sha256,
            "byte_length": 42,
        }
    elif identity_kind == "restricted_untracked_file":
        src = {
            "identity_kind": "restricted_untracked_file",
            "path": reg_path,
            "sha256": sha256,
            "byte_length": 42,
        }
    else:
        src = {
            "identity_kind": identity_kind,
            "path": reg_path,
            "sha256": sha256,
            "byte_length": 42,
            "frozen_copy_ref": {"id": new_id("artefact"), "record_revision": 1, "content_hash": "b" * 64},
        }
    fams = ["headline"] if families is None else families
    obs = {
        "record_id": obs_id,
        "registration_ref": {"id": reg_id, "record_revision": 1, "content_hash": "c" * 64},
        "selector": {
            "selector_kind": "json_family_set",
            "membership_ref": {"id": mem_id, "record_revision": 1, "content_hash": "d" * 64},
            "family_names": list(fams),
        },
        "source_identity": src,
        "families": [{"family_name": name, "w0_class": "authoritative"} for name in fams],
        "qualifiers": [],
    }
    acc = {
        "record_id": acc_id,
        "items": [{"observation_ref": {"id": obs_id, "record_revision": 1, "content_hash": "e" * 64}}],
    }
    adp = {
        "record_id": adp_id,
        "observation_ref": {"id": obs_id, "record_revision": 1, "content_hash": "e" * 64},
        "subject": {"subject_kind": "families", "family_names": list(fams)},
        "intended_use": {"description": use, "successor_ref": None},
        "w5_consequence": "admissible_for_named_use",
        "qualifiers_to_discharge": [],
        "decision_ref": {"id": dec_id, "record_revision": 1, "content_hash": "f" * 64},
    }
    state["records"]["legacy_path_registration"] = {reg_id: reg}
    state["records"]["legacy_observation"] = {obs_id: obs}
    state["records"]["legacy_closed_reference_acceptance"] = {acc_id: acc}
    state["records"]["legacy_adoption_decision"] = {adp_id: adp}
    state["observations_by_registration"][reg_id] = [obs_id]
    return state, obs, adp


def _add_whole_file_adoption(
    *,
    role: str = "legacy_research_result",
    reg_path: str = "data/rows.pkl",
    obs_path: str | None = None,
    identity_kind: str = "restricted_untracked_file",
    git_blob: str | None = None,
    sha256: str = "9" * 64,
    use: str = "w9-use:task-input/calib-1",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    state = reducers.new_legacy_state()
    reg_id = new_id("scope_definition")
    obs_id = new_id("scope_definition")
    acc_id = new_id("scope_definition")
    adp_id = new_id("scope_definition")
    dec_id = new_id("decision")
    actual_path = obs_path or reg_path
    src: dict[str, Any]
    if identity_kind == "git_tracked":
        src = {
            "identity_kind": "git_tracked",
            "repository_path": actual_path,
            "git_commit": "0" * 40,
            "git_blob": git_blob or ("2" * 40),
            "sha256": sha256,
            "byte_length": 16,
        }
    else:
        src = {
            "identity_kind": "restricted_untracked_file",
            "path": actual_path,
            "sha256": sha256,
            "byte_length": 16,
        }
    state["records"]["legacy_path_registration"] = {
        reg_id: {"record_id": reg_id, "role": role, "normalized_path": reg_path, "source_identity_kind": identity_kind}
    }
    obs = {
        "record_id": obs_id,
        "registration_ref": {"id": reg_id, "record_revision": 1, "content_hash": "c" * 64},
        "selector": {"selector_kind": "whole_file"},
        "source_identity": src,
        "families": [{"family_name": "whole_file", "w0_class": "authoritative"}],
        "qualifiers": [],
    }
    state["records"]["legacy_observation"] = {obs_id: obs}
    state["records"]["legacy_closed_reference_acceptance"] = {
        acc_id: {
            "record_id": acc_id,
            "items": [{"observation_ref": {"id": obs_id, "record_revision": 1, "content_hash": "e" * 64}}],
        }
    }
    adp = {
        "record_id": adp_id,
        "observation_ref": {"id": obs_id, "record_revision": 1, "content_hash": "e" * 64},
        "subject": {"subject_kind": "whole_file", "rehash_at_use": True},
        "intended_use": {"description": use, "successor_ref": None},
        "w5_consequence": "admissible_for_named_use",
        "qualifiers_to_discharge": [],
        "decision_ref": {"id": dec_id, "record_revision": 1, "content_hash": "f" * 64},
    }
    state["records"]["legacy_adoption_decision"] = {adp_id: adp}
    state["observations_by_registration"][reg_id] = [obs_id]
    return state, obs, adp


# --- adoption_status & suspension causes (§7, §15 W9-T9) ------------------------------------------------------------


def test_adoption_status_unknown_id_raises() -> None:
    state = reducers.new_legacy_state()
    unknown = new_id("scope_definition")
    with pytest.raises(IntegrityError, match="W9 adoption record not found"):
        adoption_status(state, unknown)


def test_adoption_status_active_when_no_cause_exists() -> None:
    state, _, adp = _state_with_family_adoption()
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "active",
        "cause": None,
    }


def test_adoption_status_suspends_on_stale_observation_even_for_disjoint_family_reobservation() -> None:
    """Note §7 (review M-1): stale_observations suspends even when later obs selects disjoint families."""
    state, obs, adp = _state_with_family_adoption(families=["headline"])
    reg_id = obs["registration_ref"]["id"]
    later_id = new_id("scope_definition")
    later_obs = deepcopy(obs)
    later_obs["record_id"] = later_id
    later_obs["selector"]["family_names"] = ["other"]
    later_obs["families"] = [{"family_name": "other", "w0_class": "authoritative"}]
    later_obs["source_identity"]["sha256"] = "b" * 64
    state["records"]["legacy_observation"][later_id] = later_obs
    state["observations_by_registration"][reg_id].append(later_id)
    state["stale_observations"].append(obs["record_id"])
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "observation_stale",
    }


def test_adoption_status_suspends_on_same_family_reobservation_even_with_same_bytes() -> None:
    state, obs, adp = _state_with_family_adoption(families=["headline"])
    reg_id = obs["registration_ref"]["id"]
    later_id = new_id("scope_definition")
    later_obs = deepcopy(obs)
    later_obs["record_id"] = later_id
    state["records"]["legacy_observation"][later_id] = later_obs
    state["observations_by_registration"][reg_id].append(later_id)
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "later_observation",
    }


def test_adoption_status_stays_active_on_disjoint_family_reobservation_with_unchanged_bytes() -> None:
    state, obs, adp = _state_with_family_adoption(families=["headline"])
    reg_id = obs["registration_ref"]["id"]
    later_id = new_id("scope_definition")
    later_obs = deepcopy(obs)
    later_obs["record_id"] = later_id
    later_obs["selector"]["family_names"] = ["other"]
    later_obs["families"] = [{"family_name": "other", "w0_class": "authoritative"}]
    state["records"]["legacy_observation"][later_id] = later_obs
    state["observations_by_registration"][reg_id].append(later_id)
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "active",
        "cause": None,
    }


def test_whole_file_adoption_suspends_on_later_observation_of_non_root_registration() -> None:
    state, obs, adp = _add_whole_file_adoption()
    reg_id = obs["registration_ref"]["id"]
    later_id = new_id("scope_definition")
    later_obs = deepcopy(obs)
    later_obs["record_id"] = later_id
    state["records"]["legacy_observation"][later_id] = later_obs
    state["observations_by_registration"][reg_id].append(later_id)
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "later_observation",
    }


def test_whole_file_adoption_under_manuscript_root_compares_source_path() -> None:
    """Note §7 (CodeRabbit rev 3): under legacy_manuscript_root, observing b.npy leaves a.npy active; observing a.npy suspends."""
    state, obs, adp = _add_whole_file_adoption(
        role="legacy_manuscript_root",
        reg_path="papers/P01-A-JRSSA/",
        obs_path="papers/P01-A-JRSSA/a.npy",
        identity_kind="git_tracked",
    )
    reg_id = obs["registration_ref"]["id"]
    other_member_id = new_id("scope_definition")
    other_member = deepcopy(obs)
    other_member["record_id"] = other_member_id
    other_member["source_identity"]["repository_path"] = "papers/P01-A-JRSSA/b.npy"
    state["records"]["legacy_observation"][other_member_id] = other_member
    state["observations_by_registration"][reg_id].append(other_member_id)
    assert adoption_status(state, adp["record_id"])["status"] == "active"

    same_member_id = new_id("scope_definition")
    same_member = deepcopy(obs)
    same_member["record_id"] = same_member_id
    state["records"]["legacy_observation"][same_member_id] = same_member
    state["observations_by_registration"][reg_id].append(same_member_id)
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "later_observation",
    }


def test_item_selector_clause_implemented_for_forward_compatibility() -> None:
    """Note §7 lines 698-699: inventory_item selector matching checks item identity fields."""
    state, obs, adp = _add_whole_file_adoption()
    reg_id = obs["registration_ref"]["id"]
    inv_id = new_id("scope_definition")
    obs["selector"] = {
        "selector_kind": "inventory_item",
        "inventory_ref": {"id": inv_id, "record_revision": 1, "content_hash": "0" * 64},
        "row_ordinal": 2,
        "anchor_text": "## 2026-01-01 Entry",
        "raw_row_sha256": "1" * 64,
    }
    adp["subject"] = {"subject_kind": "inventory_item"}
    other_id = new_id("scope_definition")
    other_obs = deepcopy(obs)
    other_obs["record_id"] = other_id
    other_obs["selector"]["row_ordinal"] = 3
    state["records"]["legacy_observation"][other_id] = other_obs
    state["observations_by_registration"][reg_id].append(other_id)
    assert adoption_suspension_cause(state, adp) is None

    same_id = new_id("scope_definition")
    same_obs = deepcopy(obs)
    same_obs["record_id"] = same_id
    state["records"]["legacy_observation"][same_id] = same_obs
    state["observations_by_registration"][reg_id].append(same_id)
    assert adoption_suspension_cause(state, adp) == "later_observation"


@pytest.mark.parametrize("target", ["observation", "acceptance", "adoption"])
def test_adoption_status_suspends_on_supersession(target: str) -> None:
    state, obs, adp = _state_with_family_adoption()
    acc_id = next(iter(state["records"]["legacy_closed_reference_acceptance"]))
    superseded_id = {"observation": obs["record_id"], "acceptance": acc_id, "adoption": adp["record_id"]}[target]
    state["supersessions"][superseded_id] = new_id("scope_definition")
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": f"{target}_superseded",
    }


def test_adoption_status_suspends_when_superseding_acceptance_names_same_observation() -> None:
    """Superseding acc_1 even when replacing acc_2 also lists the observation still suspends."""
    state, obs, adp = _state_with_family_adoption()
    acc1_id = next(iter(state["records"]["legacy_closed_reference_acceptance"]))
    acc2_id = new_id("scope_definition")
    acc2 = deepcopy(state["records"]["legacy_closed_reference_acceptance"][acc1_id])
    acc2["record_id"] = acc2_id
    state["records"]["legacy_closed_reference_acceptance"][acc2_id] = acc2
    state["supersessions"][acc1_id] = acc2_id
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "acceptance_superseded",
    }


def test_adoption_status_suspends_on_use_mismatch_lr061() -> None:
    state, _, adp = _state_with_family_adoption()
    mismatch_id = new_id("scope_definition")
    state["records"]["legacy_adoption_use_mismatch"] = {
        mismatch_id: {
            "record_id": mismatch_id,
            "adoption_ref": {"id": adp["record_id"], "record_revision": 1, "content_hash": "a" * 64},
        }
    }
    assert adoption_status(state, adp["record_id"]) == {
        "adoption_id": adp["record_id"],
        "status": "suspended",
        "cause": "use_mismatch",
    }


# --- resolve_adoption_ref (§4.3, §9, §15 W9-T8) ----------------------------------------------------------------------


def test_resolve_adoption_ref_returns_observed_identity_for_family_and_whole_file_adoptions() -> None:
    state, obs, adp = _state_with_family_adoption(git_blob="4" * 40, sha256="5" * 64)
    resolved = resolve_adoption_ref(state, f"w9-adoption:{adp['record_id']}")
    assert resolved == {
        "adoption_id": adp["record_id"],
        "observation_ref": adp["observation_ref"],
        "observation_id": obs["record_id"],
        "subject": adp["subject"],
        "intended_use": adp["intended_use"],
        "status": "active",
        "cause": None,
        "source_identity": {
            "identity_kind": "git_tracked",
            "path": "results/x.json",
            "sha256": "5" * 64,
            "git_blob": "4" * 40,
            "byte_length": 42,
        },
    }

    wstate, wobs, wadp = _add_whole_file_adoption(identity_kind="restricted_untracked_file", sha256="6" * 64)
    wresolved = resolve_adoption_ref(wstate, f"w9-adoption:{wadp['record_id']}")
    assert wresolved["source_identity"] == {
        "identity_kind": "restricted_untracked_file",
        "path": "data/rows.pkl",
        "sha256": "6" * 64,
        "git_blob": None,
        "byte_length": 16,
    }
    assert wresolved["observation_id"] == wobs["record_id"]


def test_resolve_adoption_ref_rejects_malformed_or_unknown_refs() -> None:
    state = reducers.new_legacy_state()
    for bad in (
        "",
        new_id("scope_definition"),
        f"w9-adoption:{new_id('decision')}",
        "w9-adoption:obj_not-a-uuid",
        f"w9-adoption:{new_id('scope_definition')}:extra",
    ):
        with pytest.raises(IntegrityError, match="W9 adoption ref is malformed"):
            resolve_adoption_ref(state, bad)
    with pytest.raises(IntegrityError, match="W9 adoption record not found"):
        resolve_adoption_ref(state, f"w9-adoption:{new_id('scope_definition')}")


# --- family_admissible (§6.2, §9, §15 W9-T1 / W9-T8 / W9-T17) --------------------------------------------------------


def test_w9_t1_done_status_word_in_source_yields_no_recorded_adoption() -> None:
    """W9-T1 at LR-029: a literal Done status word inside observed data grants no adoption."""
    state = reducers.new_legacy_state()
    reg_id = new_id("scope_definition")
    obs_id = new_id("scope_definition")
    acc_id = new_id("scope_definition")
    state["records"]["legacy_path_registration"] = {
        reg_id: {"record_id": reg_id, "role": "legacy_research_result", "normalized_path": "results/x.json"}
    }
    state["records"]["legacy_observation"] = {
        obs_id: {
            "record_id": obs_id,
            "registration_ref": {"id": reg_id, "record_revision": 1, "content_hash": "a" * 64},
            "selector": {"selector_kind": "json_family_set", "family_names": ["headline"]},
            "source_identity": {
                "identity_kind": "git_tracked",
                "repository_path": "results/x.json",
                "git_commit": "0" * 40,
                "git_blob": "1" * 40,
                "sha256": "a" * 64,
                "byte_length": 18,
            },
            "families": [{"family_name": "headline", "w0_class": "Done"}],
            "qualifiers": [],
        }
    }
    state["records"]["legacy_closed_reference_acceptance"] = {
        acc_id: {
            "record_id": acc_id,
            "items": [{"observation_ref": {"id": obs_id, "record_revision": 1, "content_hash": "b" * 64}}],
        }
    }
    assert family_admissible(state, obs_id, "headline", "w9-use:claim-evidence/c1") == {
        "admissible": False,
        "reason": "unadopted",
        "adoption_id": None,
    }


def test_w9_t8_and_w9_t17_family_admissible_predicates() -> None:
    state, obs, adp = _state_with_family_adoption(families=["headline"], use="w9-use:task-input/t1")
    obs_id = obs["record_id"]
    # Exact match -> admissible
    assert family_admissible(state, obs_id, "headline", "w9-use:task-input/t1") == {
        "admissible": True,
        "reason": None,
        "adoption_id": adp["record_id"],
    }
    # Accepted observation, unadopted family -> unadopted
    assert family_admissible(state, obs_id, "other", "w9-use:task-input/t1") == {
        "admissible": False,
        "reason": "unadopted",
        "adoption_id": None,
    }
    # Different key -> other_use
    assert family_admissible(state, obs_id, "headline", "w9-use:task-input/t2") == {
        "admissible": False,
        "reason": "other_use",
        "adoption_id": None,
    }
    # Suspended adoption for exact use -> suspended
    state["stale_observations"].append(obs_id)
    assert family_admissible(state, obs_id, "headline", "w9-use:task-input/t1") == {
        "admissible": False,
        "reason": "suspended",
        "adoption_id": adp["record_id"],
    }


def test_family_admissible_answers_whole_file_for_whole_file_adoption() -> None:
    state, obs, adp = _add_whole_file_adoption(use="w9-use:task-input/calibration")
    assert family_admissible(state, obs["record_id"], "whole_file", "w9-use:task-input/calibration") == {
        "admissible": True,
        "reason": None,
        "adoption_id": adp["record_id"],
    }
    assert family_admissible(state, obs["record_id"], "headline", "w9-use:task-input/calibration") == {
        "admissible": False,
        "reason": "unadopted",
        "adoption_id": None,
    }


# --- legacy_content_matches (§4.2, §9, §15 W9-T17) -------------------------------------------------------------------


def test_legacy_content_matches_by_sha256_or_git_blob_and_never_matches_absent_values() -> None:
    state, tracked_obs, _ = _state_with_family_adoption(identity_kind="git_tracked", git_blob="3" * 40, sha256="a" * 64)
    untracked_id = new_id("scope_definition")
    untracked_obs = {
        "record_id": untracked_id,
        "source_identity": {
            "identity_kind": "restricted_untracked_file",
            "path": "data/rows.pkl",
            "sha256": "b" * 64,
            "byte_length": 12,
        },
    }
    state["records"]["legacy_observation"][untracked_id] = untracked_obs
    # An unrecorded proposal must never appear in content matches (§4.2).
    proposed_id = new_id("scope_definition")
    state["proposals"][proposed_id] = {
        "kind": "legacy_observation",
        "recorded": False,
        "record": {"record_id": proposed_id, "source_identity": {"sha256": "c" * 64, "git_blob": "4" * 40}},
    }

    assert [m["record_id"] for m in legacy_content_matches(state, "a" * 64, None)] == [tracked_obs["record_id"]]
    assert [m["record_id"] for m in legacy_content_matches(state, "f" * 64, "3" * 40)] == [tracked_obs["record_id"]]
    assert [m["record_id"] for m in legacy_content_matches(state, "b" * 64, None)] == [untracked_id]
    # CodeRabbit rev 3: two sources both lacking git_blob must NOT match when sha256 does not match.
    assert legacy_content_matches(state, "e" * 64, None) == []
    assert legacy_content_matches(state, "e" * 64, "") == []
    assert legacy_content_matches(state, None, None) == []
    assert legacy_content_matches(state, "c" * 64, "4" * 40) == []
