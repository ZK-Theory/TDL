from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.errors import ArsError
from research_system.methods.brief import _resolve_methods_asset, export_brief, finalize_brief_manifest
from research_system.methods.pack import load_methods_pack
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


def test_methods_asset_binding_rejects_unknown_or_stale_identity() -> None:
    pack = load_methods_pack(ROOT)
    asset = pack.assets[0]
    exact = {
        "asset_id": asset.asset_id,
        "version": asset.version,
        "identity": asset.identity,
        "identity_scheme": asset.identity_scheme,
    }

    assert _resolve_methods_asset(pack, exact) is asset
    with pytest.raises(ArsError, match="not a current RM-02"):
        _resolve_methods_asset(pack, {**exact, "asset_id": "mth_unknown"})
    with pytest.raises(ArsError, match="current RM-02 identity"):
        _resolve_methods_asset(pack, {**exact, "identity": "0" * 40})


def test_export_refreshes_context_before_durable_registration(monkeypatch) -> None:
    first_context = SimpleNamespace(
        context_id=CTX,
        revision=1,
        packet_sha256="1" * 64,
        delivery={"delivery_receipt_id": "delivery-1"},
    )
    changed_context = SimpleNamespace(
        context_id=CTX,
        revision=1,
        packet_sha256="2" * 64,
        delivery={"delivery_receipt_id": "delivery-2"},
    )
    snapshots = iter((("delivered",), ("delivered", "expired")))
    resolved_events: list[tuple[str, ...]] = []
    registrations: list[object] = []

    def context_events() -> tuple[str, ...]:
        return next(snapshots)

    def context_resolver(**kwargs):
        resolved_events.append(kwargs["events"])
        return first_context if len(resolved_events) == 1 else changed_context

    monkeypatch.setattr(
        "research_system.methods.brief.finalize_brief_manifest",
        lambda manifest, **_kwargs: manifest,
    )
    monkeypatch.setattr(
        "research_system.methods.brief.register_candidate_document",
        lambda **kwargs: registrations.append(kwargs),
    )

    with pytest.raises(ArsError, match="context packet changed"):
        export_brief(
            request={
                "brief_purpose": "independent_review",
                "context": {
                    "scope": "rm-03-export",
                    "evaluation_time": datetime(2026, 8, 9, tzinfo=UTC),
                },
                "created_at": "2026-08-09T00:00:00Z",
                "subjects": [],
                "assets": [],
                "expected_import_types": ["ExploratoryMemo"],
                "prohibitions": [],
                "required_session_fields": [],
            },
            context_resolver=context_resolver,
            context_events=context_events,
            context_objects=object(),
            context_source_resolver=object(),
            artefact_consumers=object(),
            methods_pack=object(),
            schema_registry=object(),
            registration=SimpleNamespace(
                artefact_id=ART,
                project_id="prj_01978abc-1000-7000-8000-000000001000",
            ),
            document_store=object(),
            command_service=object(),
        )

    assert resolved_events == [("delivered",), ("delivered", "expired")]
    assert registrations == []


def test_export_rejects_review_without_review_subject_before_resolution() -> None:
    resolutions: list[object] = []

    def context_resolver(**kwargs):
        resolutions.append(kwargs)
        raise AssertionError("context resolution must not run")

    with pytest.raises(ArsError, match="requires exactly one review_subject"):
        export_brief(
            request={
                "expected_import_types": ["ReviewFindingSet"],
                "subjects": [{"role": "supporting_evidence"}],
            },
            context_resolver=context_resolver,
            context_events=lambda: (),
            context_objects=object(),
            context_source_resolver=object(),
            artefact_consumers=object(),
            methods_pack=object(),
            schema_registry=object(),
            registration=object(),
            document_store=object(),
            command_service=object(),
        )

    assert resolutions == []


def test_export_rejects_duplicate_review_subjects_before_resolution() -> None:
    resolutions: list[object] = []

    def context_resolver(**kwargs):
        resolutions.append(kwargs)
        raise AssertionError("context resolution must not run")

    with pytest.raises(ArsError, match="requires exactly one review_subject"):
        export_brief(
            request={
                "expected_import_types": ["ReviewFindingSet"],
                "subjects": [
                    {"role": "review_subject"},
                    {"role": "review_subject"},
                ],
            },
            context_resolver=context_resolver,
            context_events=lambda: (),
            context_objects=object(),
            context_source_resolver=object(),
            artefact_consumers=object(),
            methods_pack=object(),
            schema_registry=object(),
            registration=object(),
            document_store=object(),
            command_service=object(),
        )

    assert resolutions == []
