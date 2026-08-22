from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.discovery.source_correction import (
    prepare_spec_source_correction,
    validate_spec_source_correction,
)
from research_system.errors import ConfigurationError, IntegrityError
from research_system.schema_registry import cached_schema_registry


SCHEMA_ROOT = Path(__file__).resolve().parents[3] / ".research-system" / "schemas"
SOURCE_ID = "art_019fed25-b33e-7740-b280-6f661aaef401"
EVIDENCE_ID = "art_019fed25-b33e-7740-b280-6f661aaef402"
SOURCE_EVENT_ID = "evt_019fed25-b33e-7740-b280-6f661aaef403"
EVIDENCE_EVENT_ID = "evt_019fed25-b33e-7740-b280-6f661aaef404"
SOURCE_HASH = "1" * 64
EVIDENCE_HASH = "2" * 64
SOURCE_EVENT_HASH = "3" * 64
EVIDENCE_EVENT_HASH = "4" * 64
PREFIX_HASH = "5" * 64


def _event(position, artefact_id, event_id, event_hash, content_hash, *, source=False):
    manifest = {
        "artefact_id": artefact_id,
        "artefact_type": "spec_source_observation" if source else "spec_01_scorecard",
        "artefact_schema_id": (
            "ars://portfolio/spec-source-observation" if source else "ars://portfolio/spec-01-scorecard"
        ),
        "artefact_schema_version": "1.0.0",
        "content_sha256": content_hash,
    }
    return {
        "global_position": position,
        "event_type": "ArtefactRegistered",
        "stream_id": artefact_id,
        "event_id": event_id,
        "event_hash": event_hash,
        "payload": {"new_artefact_id": artefact_id, "manifest": manifest},
    }


class Ledger:
    def __init__(self):
        self.events = (
            _event(1, EVIDENCE_ID, EVIDENCE_EVENT_ID, EVIDENCE_EVENT_HASH, EVIDENCE_HASH),
            _event(2, SOURCE_ID, SOURCE_EVENT_ID, SOURCE_EVENT_HASH, SOURCE_HASH, source=True),
        )

    def snapshot(self):
        return SimpleNamespace(
            events=self.events,
            global_position=2,
            event_hash=SOURCE_EVENT_HASH,
        )

    def raw_prefix_sha256(self, global_position):
        assert global_position == 2
        return PREFIX_HASH


def _ref(artefact_id, content_hash, event_id, event_hash, position):
    return {
        "artefact_id": artefact_id,
        "content_sha256": content_hash,
        "registration_event_id": event_id,
        "registration_event_hash": event_hash,
        "registration_global_position": position,
    }


def _prepare(
    ledger,
    *,
    recorded_at: object = "2026-08-22T12:00:00Z",
    amended_evidence_refs=None,
    scientific_disposition: str = "PARK",
):
    return prepare_spec_source_correction(
        route_id="SPEC-GATE6-RUN-V2",
        correction_id="correction:neurips2024-tag",
        recorded_at=recorded_at,  # type: ignore[arg-type]
        producer_actor_id="act_01978abc-1001-7000-8000-000000001001",
        producer_session_id="session:source-correction",
        amended_evidence_refs=(
            (_ref(EVIDENCE_ID, EVIDENCE_HASH, EVIDENCE_EVENT_ID, EVIDENCE_EVENT_HASH, 1),)
            if amended_evidence_refs is None
            else amended_evidence_refs
        ),
        corrected_source_observation_ref=_ref(
            SOURCE_ID,
            SOURCE_HASH,
            SOURCE_EVENT_ID,
            SOURCE_EVENT_HASH,
            2,
        ),
        incorrect_assertions=("paper-cited neurips2024 branch is absent",),
        withdrawn_conditions=("primary_paper_code_discrepancy",),
        preserved_findings=("future_estimand_unidentified",),
        scientific_disposition=scientific_disposition,
        ledger=ledger,
        schemas=cached_schema_registry(SCHEMA_ROOT),
    )


def test_v2_source_correction_binds_exact_amended_events_and_raw_prefix_append_only() -> None:
    ledger = Ledger()
    before = deepcopy(ledger.events)

    correction = _prepare(ledger)

    assert correction["causal_ledger_prefix"] == {
        "global_position": 2,
        "event_hash": SOURCE_EVENT_HASH,
        "raw_prefix_sha256": PREFIX_HASH,
    }
    assert correction["amended_evidence_refs"][0]["registration_event_id"] == EVIDENCE_EVENT_ID
    assert correction["corrected_source_observation_ref"]["registration_event_id"] == SOURCE_EVENT_ID
    assert ledger.events == before


def test_source_correction_rejects_an_unrelated_registration_event() -> None:
    ledger = Ledger()
    correction = _prepare(ledger)
    correction["amended_evidence_refs"][0]["registration_event_hash"] = "6" * 64

    with pytest.raises(IntegrityError, match="does not match its registration event"):
        validate_spec_source_correction(
            correction,
            ledger=ledger,
            schemas=cached_schema_registry(SCHEMA_ROOT),
        )


def test_source_correction_rejects_a_stale_or_fabricated_raw_prefix() -> None:
    ledger = Ledger()
    correction = _prepare(ledger)
    correction["causal_ledger_prefix"]["raw_prefix_sha256"] = "7" * 64

    with pytest.raises(IntegrityError, match="causal prefix"):
        validate_spec_source_correction(
            correction,
            ledger=ledger,
            schemas=cached_schema_registry(SCHEMA_ROOT),
        )


def test_source_correction_rejects_amended_evidence_beyond_its_causal_prefix() -> None:
    ledger = Ledger()
    correction = _prepare(ledger)
    correction["amended_evidence_refs"][0]["registration_global_position"] = 3

    with pytest.raises(IntegrityError, match="outside the causal prefix"):
        validate_spec_source_correction(
            correction,
            ledger=ledger,
            schemas=cached_schema_registry(SCHEMA_ROOT),
        )


def test_source_correction_rejects_duplicate_amended_evidence() -> None:
    ledger = Ledger()
    reference = _ref(EVIDENCE_ID, EVIDENCE_HASH, EVIDENCE_EVENT_ID, EVIDENCE_EVENT_HASH, 1)

    with pytest.raises(IntegrityError, match="schema|repeats amended evidence"):
        _prepare(ledger, amended_evidence_refs=(reference, deepcopy(reference)))


def test_v2_source_correction_uses_the_canonical_uppercase_partial_token() -> None:
    ledger = Ledger()
    assert _prepare(ledger, scientific_disposition="PARTIAL")["scientific_disposition"] == "PARTIAL"

    with pytest.raises(IntegrityError, match="schema"):
        _prepare(ledger, scientific_disposition="Partial")


@pytest.mark.parametrize("recorded_at", [None, 1, []])
def test_source_correction_rejects_non_string_recorded_at(recorded_at: object) -> None:
    with pytest.raises(ConfigurationError, match="source correction time"):
        _prepare(Ledger(), recorded_at=recorded_at)


def test_historical_v1_correction_schema_remains_registered_unchanged() -> None:
    historical = {
        "schema_id": "ars://portfolio/spec-01-source-correction",
        "schema_version": "1.0.0",
        "document_type": "spec_01_source_correction",
        "route_id": "SPEC-GATE6-RUN-V1",
        "correction_id": "correction:neurips2024-tag",
        "recorded_at": "2026-08-18T00:00:00Z",
        "producer": {
            "actor_id": "act_historical",
            "session_id": "historical-session",
            "role": "source-correction verifier",
        },
        "scorecard_ref": {"id": "scorecard", "sha256": "1" * 64},
        "decision_ref": {"id": "decision", "sha256": "2" * 64},
        "incorrect_assertions": ["paper-cited neurips2024 branch is absent from the live Git remote"],
        "corrected_git_reference": {
            "cited_locator": "https://github.com/berenslab/eff-ph/tree/neurips2024",
            "repository_url": "https://github.com/berenslab/eff-ph.git",
            "requested_ref": "neurips2024",
            "resolved_ref": "refs/tags/neurips2024",
            "ref_kind": "tag",
            "commit_oid": "145efcde673f1a1897eff250b77221d26c34c479",
            "retrieval_methods": ["direct_locator", "git_ls_remote_tags", "detached_clone"],
            "required_paths": [
                {"path": "environment.yml", "sha256": "3" * 64},
                {"path": "scripts/compute_ph.py", "sha256": "4" * 64},
            ],
        },
        "correction_effect": {
            "withdrawn_condition_codes": ["primary_paper_code_discrepancy"],
            "withdrawn_limitations": [
                "The paper-cited neurips2024 code branch is absent from the live Git remote; only main and scRNA heads were advertised."
            ],
            "withdrawn_revisit_triggers": [
                "paper-code provenance restored",
                "an immutable replacement for the absent paper-cited branch is supplied",
            ],
            "preserved_findings": [
                "future_estimand_unidentified",
                "representation_freeze_missing",
                "primary_claim_missing",
            ],
        },
        "scientific_disposition": "PARK",
    }

    cached_schema_registry(SCHEMA_ROOT).validate(
        "ars://portfolio/spec-01-source-correction",
        historical,
        schema_version="1.0.0",
    )
