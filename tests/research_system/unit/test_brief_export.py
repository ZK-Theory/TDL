from __future__ import annotations

from pathlib import Path

import pytest

from research_system.errors import ArsError
from research_system.methods.brief import finalize_brief_manifest
from research_system.schema_registry import SchemaRegistry


ROOT = Path(__file__).parents[3]
SCHEMAS = ROOT / ".research-system" / "schemas"
ART = "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b"
CTX = "ctx_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b"


def _manifest() -> dict[str, object]:
    return {
        "brief_artefact_id": ART,
        "brief_purpose": "independent_review",
        "context_packet": {
            "context_id": CTX,
            "revision": 1,
            "packet_sha256": "1" * 64,
            "delivery_receipt_id": "delivery-1",
            "delivery_receipt_sha256": "2" * 64,
        },
        "created_at": "2026-08-08T12:00:00Z",
        "subjects": [
            {
                "subject_id": ART,
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


def test_finalize_brief_manifest_is_content_addressed_and_schema_valid() -> None:
    registry = SchemaRegistry(SCHEMAS)
    first = finalize_brief_manifest(_manifest(), schema_registry=registry)
    second = finalize_brief_manifest(_manifest(), schema_registry=registry)

    assert first == second
    assert first["brief_sha256"] == second["brief_sha256"]
    registry.validate("ars://methods/brief-manifest", first)


def test_finalize_brief_manifest_rejects_hidden_reasoning_and_caller_hash() -> None:
    registry = SchemaRegistry(SCHEMAS)
    with pytest.raises(ArsError, match="caller-supplied brief_sha256"):
        finalize_brief_manifest({**_manifest(), "brief_sha256": "0" * 64}, schema_registry=registry)
    with pytest.raises(ArsError, match="brief manifest schema"):
        finalize_brief_manifest({**_manifest(), "hidden_reasoning": "forbidden"}, schema_registry=registry)
