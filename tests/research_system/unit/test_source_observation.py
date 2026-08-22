from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.git_reference import AdvertisedGitReference
from research_system.discovery.replay.scout_candidate import reduce_scout_observation_ingested
from research_system.discovery.replay.scope import EventScope
from research_system.discovery.source_observation import (
    CausalLedgerPrefix,
    SourceReferenceNotResolved,
    prepare_spec_source_observation,
)
from research_system.errors import ConfigurationError, IntegrityError
from research_system.schema_registry import cached_schema_registry


SCHEMA_ROOT = Path(__file__).resolve().parents[3] / ".research-system" / "schemas"
COMMIT_OID = "145efcde673f1a1897eff250b77221d26c34c479"
TAIL_HASH = "8" * 64
PREFIX_HASH = "9" * 64


@dataclass
class SourceTransport:
    files: dict[str, bytes]
    reference_name: str = "neurips2024"

    def __post_init__(self) -> None:
        self.read_calls: list[tuple[str, str, tuple[str, ...]]] = []

    def advertise(self, repository_url: str) -> tuple[AdvertisedGitReference, ...]:
        del repository_url
        return (
            AdvertisedGitReference(
                canonical_ref=f"refs/tags/{self.reference_name}",
                object_oid=COMMIT_OID,
            ),
        )

    def resolve_commit(self, repository_url: str, revision: str) -> str | None:
        del repository_url
        if revision == f"refs/tags/{self.reference_name}":
            return COMMIT_OID
        return None

    def read_paths(
        self,
        repository_url: str,
        commit_oid: str,
        paths: tuple[str, ...],
    ) -> dict[str, bytes]:
        self.read_calls.append((repository_url, commit_oid, paths))
        return {path: self.files[path] for path in paths if path in self.files}


def _prefix() -> CausalLedgerPrefix:
    return CausalLedgerPrefix(
        global_position=37,
        event_hash=TAIL_HASH,
        raw_prefix_sha256=PREFIX_HASH,
    )


def test_source_observation_binds_resolved_commit_exact_bytes_and_causal_prefix() -> None:
    environment = b"name: eff-ph\r\ndependencies:\r\n  - python=3.9\r\n"
    computation = b"def compute():\n    return 'exact'\n"
    transport = SourceTransport(
        {
            "environment.yml": environment,
            "scripts/compute_ph.py": computation,
        }
    )

    document = prepare_spec_source_observation(
        locator="https://github.com/berenslab/eff-ph/tree/neurips2024",
        required_paths=("scripts/compute_ph.py", "environment.yml"),
        source_observation_id="obj_019fed25-b33e-7740-b280-6f661aaef301",
        route_id="SPEC-01",
        producer_actor_id="act_01978abc-1001-7000-8000-000000001001",
        observed_at="2026-08-22T12:00:00Z",
        causal_prefix=_prefix(),
        transport=transport,
        schemas=cached_schema_registry(SCHEMA_ROOT),
    )

    assert document["resolution"]["commit_oid"] == COMMIT_OID
    assert document["resolution"]["resolved_kind"] == "lightweight_tag"
    assert document["causal_ledger_prefix"] == {
        "global_position": 37,
        "event_hash": TAIL_HASH,
        "raw_prefix_sha256": PREFIX_HASH,
    }
    assert [item["path"] for item in document["source_files"]] == [
        "environment.yml",
        "scripts/compute_ph.py",
    ]
    assert base64.b64decode(document["source_files"][0]["content_base64"], validate=True) == environment
    assert document["source_files"][0]["content_sha256"] == sha256_hex(environment)
    assert document["source_bundle_sha256"] == sha256_hex(canonical_bytes(document["source_files"]))
    assert transport.read_calls == [
        (
            "https://github.com/berenslab/eff-ph.git",
            COMMIT_OID,
            ("environment.yml", "scripts/compute_ph.py"),
        )
    ]


def test_unresolved_source_never_reads_or_constructs_content() -> None:
    transport = SourceTransport({}, reference_name="other")

    with pytest.raises(SourceReferenceNotResolved) as caught:
        prepare_spec_source_observation(
            locator="https://github.com/berenslab/eff-ph/tree/neurips2024",
            required_paths=("environment.yml",),
            source_observation_id="obj_019fed25-b33e-7740-b280-6f661aaef301",
            route_id="SPEC-01",
            producer_actor_id="act_01978abc-1001-7000-8000-000000001001",
            observed_at="2026-08-22T12:00:00Z",
            causal_prefix=_prefix(),
            transport=transport,
            schemas=cached_schema_registry(SCHEMA_ROOT),
        )

    assert caught.value.resolution.status == "absent"
    assert transport.read_calls == []


@pytest.mark.parametrize(
    "paths",
    [
        ("/environment.yml",),
        ("../environment.yml",),
        ("scripts\\compute_ph.py",),
        ("environment.yml", "environment.yml"),
        ([],),
        ({"path": "environment.yml"},),
    ],
)
def test_source_observation_rejects_noncanonical_or_duplicate_paths(paths: tuple[object, ...]) -> None:
    with pytest.raises(ConfigurationError, match="source path"):
        prepare_spec_source_observation(
            locator="https://github.com/berenslab/eff-ph/tree/neurips2024",
            required_paths=paths,  # type: ignore[arg-type]
            source_observation_id="obj_019fed25-b33e-7740-b280-6f661aaef301",
            route_id="SPEC-01",
            producer_actor_id="act_01978abc-1001-7000-8000-000000001001",
            observed_at="2026-08-22T12:00:00Z",
            causal_prefix=_prefix(),
            transport=SourceTransport({}),
            schemas=cached_schema_registry(SCHEMA_ROOT),
        )


def test_source_observation_rejects_a_missing_required_commit_path() -> None:
    with pytest.raises(IntegrityError, match="required source paths"):
        prepare_spec_source_observation(
            locator="https://github.com/berenslab/eff-ph/tree/neurips2024",
            required_paths=("environment.yml", "scripts/compute_ph.py"),
            source_observation_id="obj_019fed25-b33e-7740-b280-6f661aaef301",
            route_id="SPEC-01",
            producer_actor_id="act_01978abc-1001-7000-8000-000000001001",
            observed_at="2026-08-22T12:00:00Z",
            causal_prefix=_prefix(),
            transport=SourceTransport({"environment.yml": b"name: eff-ph\n"}),
            schemas=cached_schema_registry(SCHEMA_ROOT),
        )


def test_replay_rejects_or029_v2_bound_to_a_non_source_artefact() -> None:
    """A rehashed history cannot substitute another registered artefact type."""

    observation_id = "obj_019fed25-b33e-7740-b280-6f661aaef305"
    candidate_id = "obj_019fed25-b33e-7740-b280-6f661aaef306"
    artefact_id = "art_019fed25-b33e-7740-b280-6f661aaef307"
    source_ref = {
        "ref_kind": "artefact",
        "artefact_id": artefact_id,
        "content_hash": "1" * 64,
        "registration_event_id": "evt_019fed25-b33e-7740-b280-6f661aaef308",
        "registration_event_hash": "2" * 64,
        "registration_global_position": 4,
    }
    batch = {
        "schema_id": "ars://portfolio/scout-observation-batch",
        "schema_version": "2.0.0",
        "source_query": "https://github.com/berenslab/eff-ph/tree/neurips2024",
        "source_version": COMMIT_OID,
        "observed_at": "2026-08-22T12:00:00Z",
        "returned_identifiers": [observation_id],
        "normalized_dedup_keys": ["berenslab/eff-ph@neurips2024"],
        "raw_source_refs": [source_ref],
        "matching_facts": ["the locator resolved"],
        "omissions_or_errors": [],
        "viability_judgment_absent": True,
    }
    batch_sha256 = sha256_hex(canonical_bytes(batch))
    blueprint = {
        "candidate_id": candidate_id,
        "revision": 1,
        "content_sha256": sha256_hex(
            canonical_bytes([{"observation_id": observation_id, "content_sha256": batch_sha256}])
        ),
        "source_observation_refs": [observation_id],
        "title": "candidate derived from a wrong artefact type",
    }
    scout_payload = {
        "row_id": "OR-029",
        "observation_id": observation_id,
        "batch": batch,
        "content_sha256": batch_sha256,
        "normalized_dedup_keys": batch["normalized_dedup_keys"],
        "candidate_blueprints_sha256": sha256_hex(canonical_bytes([blueprint])),
    }
    command_payload = {
        "row_id": "OR-029",
        "observation_id": observation_id,
        "batch": batch,
        "batch_sha256": batch_sha256,
        "candidate_blueprints": [blueprint],
    }
    scout_event = {
        "event_type": "ScoutObservationIngested",
        "command_type": "IngestScoutObservationBatch",
        "transaction_id": "txn:source-observation",
        "stream_id": observation_id,
        "global_position": 5,
        "stream_version": 1,
        "command_payload_hash": sha256_hex(canonical_bytes(command_payload)),
        "payload": scout_payload,
    }
    candidate_event = {
        "event_type": "CandidateRegistered",
        "command_type": "IngestScoutObservationBatch",
        "transaction_id": "txn:source-observation",
        "stream_id": candidate_id,
        "payload": {
            **blueprint,
            "owner_row_id": "OR-029",
            "source_observation_multiset_hash": blueprint["content_sha256"],
        },
    }
    state = {
        "source_observations": {},
        "artefact_streams": {
            artefact_id: {
                "content_sha256": source_ref["content_hash"],
                "registration_event_id": source_ref["registration_event_id"],
                "registration_event_hash": source_ref["registration_event_hash"],
                "registration_global_position": source_ref["registration_global_position"],
                "manifest": {
                    "artefact_type": "spec_01_scorecard",
                    "artefact_schema_id": "ars://portfolio/spec-01-scorecard",
                    "artefact_schema_version": "1.0.0",
                },
            }
        },
    }
    scope = EventScope(
        state=state,
        event=scout_event,
        payload=scout_payload,
        event_type="ScoutObservationIngested",
        active_schemas=cached_schema_registry(SCHEMA_ROOT),
        transaction_events={"txn:source-observation": [scout_event, candidate_event]},
        operational_events=[],
        canonical_artefact_streams={},
        required_string=lambda key: scout_payload[key],
        required_int=lambda key: scout_payload[key],
        required_string_list=lambda key: scout_payload[key],
        aggregate_identity_exists=lambda _identity: False,
        claim_authority_stream=lambda *_args, **_kwargs: None,
        candidate_spike_link_matches=lambda *_args, **_kwargs: False,
        preceding_transaction_event_matches=lambda *_args, **_kwargs: False,
        following_transaction_event_matches=lambda *_args, **_kwargs: False,
        review_verdict_precedes=lambda *_args, **_kwargs: False,
        candidate_assay_link_matches=lambda *_args, **_kwargs: False,
        candidate_spike_plan_link_matches=lambda *_args, **_kwargs: False,
        spike_operational_closure_matches=lambda *_args, **_kwargs: False,
        dossier_materialization_transaction_matches=lambda *_args, **_kwargs: False,
    )

    with pytest.raises(IntegrityError, match="invalid Scout observation event"):
        reduce_scout_observation_ingested(scope)
