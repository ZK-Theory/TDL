from __future__ import annotations

from pathlib import Path

import pytest

from research_system.errors import ArsError
from research_system.methods.brief import finalize_brief_manifest
from research_system.methods.importer import validate_return_bundle
from research_system.schema_registry import SchemaRegistry

ROOT = Path(__file__).parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"


def _manifest() -> dict[str, object]:
    return {
        "brief_artefact_id": "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b",
        "brief_purpose": "independent_review",
        "context_packet": {
            "context_id": "ctx_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b",
            "revision": 1,
            "packet_sha256": "1" * 64,
            "delivery_receipt_id": "delivery-1",
            "delivery_receipt_sha256": "2" * 64,
        },
        "created_at": "2026-08-08T12:00:00Z",
        "subjects": [
            {
                "subject_id": "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b",
                "subject_kind": "artefact",
                "path_or_name": "candidate.json",
                "sha256": "3" * 64,
                "role": "review_subject",
                "use_predicate_id": "review-evidence",
                "use_predicate_version": "1.0.0",
                "use_predicate_sha256": "4" * 64,
            }
        ],
        "assets": [
            {
                "asset_id": "adversarial-review",
                "version": "1.0.0",
                "identity": "5" * 64,
                "identity_scheme": "lf_canonical_sha256",
                "accepted_use_event_id": "evt_accepted_asset",
                "accepted_use_event_sha256": "6" * 64,
            }
        ],
        "expected_import_types": ["ReviewFindingSet"],
        "deidentification": None,
        "prohibitions": ["no execution", "no provider operation"],
        "required_session_fields": ["operator_actor_id", "application_family"],
        "verification_context": None,
    }


def _session(brief_hash: str) -> dict[str, object]:
    return {
        "operator_actor_id": "act_01978abc-1002-7000-8000-000000001002",
        "application_family": "operator-selected editor",
        "application_version": "2026.08",
        "application_choice_by": "operator",
        "session_date": "2026-08-08",
        "responds_to_brief_manifest_sha256": brief_hash,
    }


def _findings(brief_hash: str) -> dict[str, object]:
    return {
        "document_type": "ReviewFindingSet",
        "responds_to_brief_manifest_sha256": brief_hash,
        "status": "imported",
        "review_subject": _manifest()["subjects"][0],
        "findings": [
            {
                "finding_id": "finding-1",
                "candidate_id": "candidate-1",
                "severity": "medium",
                "location": "candidate.json",
                "summary": "The returned observation is bounded.",
                "evidence": "candidate.json",
                "consequence": "The candidate needs correction before acceptance.",
                "required_disposition": "correct before acceptance",
                "self_critique_result": "confirmed",
            }
        ],
        "candidate_dispositions": [
            {
                "candidate_id": "candidate-1",
                "summary": "The returned observation may be too broad.",
                "disposition": "retained",
                "rationale": "The cited bytes reproduce the issue after self-critique.",
            }
        ],
    }


def test_validate_return_bundle_binds_exact_brief_and_raw_bytes() -> None:
    registry = SchemaRegistry(SCHEMAS)
    brief = finalize_brief_manifest(_manifest(), schema_registry=registry)
    returned = validate_return_bundle(
        brief=brief,
        session=_session(brief["brief_sha256"]),
        document=_findings(brief["brief_sha256"]),
        schema_registry=registry,
    )

    assert returned.document_type == "ReviewFindingSet"
    assert returned.content_sha256 == returned.sha256_of(returned.raw_bytes)
    assert returned.use_authority == "candidate"


def test_validate_return_bundle_accepts_clean_review_with_no_candidates() -> None:
    registry = SchemaRegistry(SCHEMAS)
    brief = finalize_brief_manifest(_manifest(), schema_registry=registry)
    document = _findings(brief["brief_sha256"])
    document["findings"] = []
    document["candidate_dispositions"] = []

    returned = validate_return_bundle(
        brief=brief,
        session=_session(brief["brief_sha256"]),
        document=document,
        schema_registry=registry,
    )

    assert returned.value["findings"] == []
    assert returned.value["candidate_dispositions"] == []


def test_validate_return_bundle_rejects_cross_brief_and_hidden_reasoning() -> None:
    registry = SchemaRegistry(SCHEMAS)
    brief = finalize_brief_manifest(_manifest(), schema_registry=registry)
    with pytest.raises(ArsError, match="session does not bind"):
        validate_return_bundle(
            brief=brief,
            session=_session("f" * 64),
            document=_findings(brief["brief_sha256"]),
            schema_registry=registry,
        )
    with pytest.raises(ArsError, match="returned document schema"):
        validate_return_bundle(
            brief=brief,
            session=_session(brief["brief_sha256"]),
            document={**_findings(brief["brief_sha256"]), "hidden_reasoning": "forbidden"},
            schema_registry=registry,
        )


def test_validate_return_bundle_rejects_review_subject_or_disposition_substitution() -> None:
    registry = SchemaRegistry(SCHEMAS)
    brief = finalize_brief_manifest(_manifest(), schema_registry=registry)
    wrong_subject = _findings(brief["brief_sha256"])
    wrong_subject["review_subject"] = {
        **wrong_subject["review_subject"],
        "sha256": "f" * 64,
    }
    with pytest.raises(ArsError, match="exact brief review subject"):
        validate_return_bundle(
            brief=brief,
            session=_session(brief["brief_sha256"]),
            document=wrong_subject,
            schema_registry=registry,
        )

    missing_finding = _findings(brief["brief_sha256"])
    missing_finding["findings"] = []
    with pytest.raises(ArsError, match="retained candidates do not match findings"):
        validate_return_bundle(
            brief=brief,
            session=_session(brief["brief_sha256"]),
            document=missing_finding,
            schema_registry=registry,
        )
