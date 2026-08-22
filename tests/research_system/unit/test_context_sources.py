import pytest

from research_system.canonical import sha256_hex
from research_system.context.models import SourceFragment
from research_system.context.spec_bridge import _event_changes_spec_source_closure, build_spec_context_snapshot
from research_system.context.sources import resolve_sources
from research_system.errors import ArsError


class _Resolver:
    def __init__(self, fragments):
        self.fragments = fragments

    def resolve(self, source_ids):
        return tuple(fragment for fragment in self.fragments if fragment.source_id in source_ids)


def test_spec_replay_source_is_system_derived_and_tail_bound():
    projection = {
        "artefact_streams": {
            "art_source": {
                "use_authority": "accepted_for_scope",
                "content_sha256": "1" * 64,
                "manifest": {"artefact_type": "spec_operator_source", "relative_path": "spec.md"},
            },
            "art_methods": {
                "use_authority": "accepted_for_scope",
                "content_sha256": "2" * 64,
                "manifest": {"artefact_type": "methods_asset", "relative_path": "method.md"},
            },
        },
        "candidates": {"can_1": {"status": "assay_requested"}},
    }
    replayed = []

    def replay(events):
        replayed.append(tuple(events))
        return projection

    first = build_spec_context_snapshot(
        ({"global_position": 7, "event_hash": "a" * 64},),
        projection_for_events=replay,
        route_id="SPEC-GATE6-RUN-V1",
    )
    same = build_spec_context_snapshot(
        ({"global_position": 7, "event_hash": "a" * 64},),
        projection_for_events=replay,
        route_id="SPEC-GATE6-RUN-V1",
    )
    changed = build_spec_context_snapshot(
        ({"global_position": 8, "event_hash": "b" * 64},),
        projection_for_events=replay,
        route_id="SPEC-GATE6-RUN-V1",
    )
    assert first == same
    assert first.source.source_id != changed.source.source_id
    assert replayed == [
        ({"global_position": 7, "event_hash": "a" * 64},),
        ({"global_position": 7, "event_hash": "a" * 64},),
        ({"global_position": 8, "event_hash": "b" * 64},),
    ]


def test_spec_replay_source_propagates_production_projection_rejection():
    def rejected(_events):
        raise ArsError("SPEC-02 execution lacks valid durable approval evidence")

    with pytest.raises(ArsError, match="valid durable approval"):
        build_spec_context_snapshot(
            ({"global_position": 7, "event_hash": "a" * 64},),
            projection_for_events=rejected,
            route_id="SPEC-GATE6-RUN-V1",
        )


def test_spec_context_source_closure_tracks_new_and_preexisting_typed_inputs():
    artefact_id = "art_relevant"
    registration = {
        "event_type": "ArtefactRegistered",
        "stream_id": artefact_id,
        "payload": {
            "new_artefact_id": artefact_id,
            "manifest": {
                "artefact_id": artefact_id,
                "artefact_type": "methods_asset",
                "content_sha256": "1" * 64,
            },
        },
    }
    accepted = {
        "event_type": "ArtefactUseAuthoritySet",
        "stream_id": artefact_id,
        "payload": {"artefact_id": artefact_id, "use_authority": "accepted_for_scope"},
    }
    arguments = {
        "accepted_artefact_ids": set(),
        "candidate_ids": set(),
        "dossier_id": "obj_dossier",
        "required_spec_source_sha256": "2" * 64,
    }

    assert _event_changes_spec_source_closure(
        registration,
        known_spec_artefact_ids=set(),
        **arguments,
    )
    assert _event_changes_spec_source_closure(
        accepted,
        known_spec_artefact_ids={artefact_id},
        **arguments,
    )
    assert not _event_changes_spec_source_closure(
        {**accepted, "stream_id": "art_unrelated", "payload": {"artefact_id": "art_unrelated"}},
        known_spec_artefact_ids={artefact_id},
        **arguments,
    )


def _fragment(source_id, content):
    return SourceFragment(
        source_id,
        "r1",
        100,
        True,
        content,
        sha256_hex(content.encode("utf-8")),
    )


def test_source_resolver_returns_verified_stable_required_closure():
    fragments = [_fragment("b", "second"), _fragment("a", "first")]
    resolved = resolve_sources(_Resolver(fragments), {"a", "b"})
    assert tuple(item.source_id for item in resolved) == ("a", "b")


def test_source_resolver_rejects_missing_or_hash_divergent_source():
    with pytest.raises(ArsError, match="mandatory source omitted"):
        resolve_sources(_Resolver([_fragment("a", "first")]), {"a", "b"})
    invalid = SourceFragment("a", "r1", 100, True, "changed", "0" * 64)
    with pytest.raises(ArsError, match="source hash mismatch"):
        resolve_sources(_Resolver([invalid]), {"a"})
