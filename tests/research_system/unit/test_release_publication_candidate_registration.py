from __future__ import annotations

from types import SimpleNamespace

from research_system import cli
from research_system.canonical import canonical_bytes, sha256_hex


def test_new_release_snapshots_register_exact_candidates_and_stop_pending(monkeypatch, tmp_path) -> None:
    source = {"release_gate_decision_id": "rel_one", "decided_at": "2026-08-08T12:00:00Z"}
    binding = SimpleNamespace(
        schema_root=tmp_path / "schemas",
        control_root=tmp_path,
        project_id="prj_01978abc-1001-7000-8000-000000001001",
        store_identity="store-one",
        origin_witness="witness",
        origin_witness_path=tmp_path / "witness",
    )
    binding.schema_root.mkdir()

    class Schemas:
        def validate(self, schema_id, value):
            assert schema_id.startswith("ars://evals/")

    class Authority:
        def __init__(self, *args, **kwargs):
            pass

        def validate_replayed_administration_state(self, value):
            return None

    class Ledger:
        def __init__(self, *args, **kwargs):
            pass

        def iter_events(self):
            return ()

    class Decision:
        pass

    monkeypatch.setattr(cli, "runtime_schema_registry", lambda root: Schemas())
    monkeypatch.setattr(cli, "LedgerAuthorityGrantResolver", Authority)
    monkeypatch.setattr(cli, "EventLedger", Ledger)
    monkeypatch.setattr(cli, "ObjectStore", lambda root: object())
    monkeypatch.setattr(cli, "ReceiptStore", lambda root: object())
    monkeypatch.setattr(cli, "CommandService", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "replay", lambda *args, **kwargs: {"release_decisions": {}})
    monkeypatch.setattr(cli, "_eval_roots", lambda path: (tmp_path, tmp_path))
    monkeypatch.setattr(cli, "run_p0_coverage", lambda *args, **kwargs: object())
    monkeypatch.setattr(cli, "run_all_scenarios", lambda: ())
    monkeypatch.setattr(cli, "build_release_decision", lambda *args, **kwargs: (Decision(), False))
    monkeypatch.setattr(cli, "decision_document", lambda record: source)
    monkeypatch.setattr(
        cli, "build_release_snapshot_documents", lambda *args, **kwargs: ({"kind": "manifest"}, {"kind": "control"})
    )
    monkeypatch.setattr(
        cli,
        "content_artefact_id",
        lambda value: "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b"
        if value["kind"] == "manifest"
        else "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6c",
    )
    registrations = []
    monkeypatch.setattr(cli, "register_candidate_document", lambda **kwargs: registrations.append(kwargs))

    resolver, manifest_ref, control_ref, pending = cli._publication_evidence(
        binding,
        source,
        actor_id="act_01978abc-1002-7000-8000-000000001002",
        authority_grant_id="agr_01978abc-1003-7000-8000-000000001003",
        registration_context={
            "task_id": "tsk_01978abc-1004-7000-8000-000000001004",
            "dispatch_id": "dsp_01978abc-1005-7000-8000-000000001005",
            "attempt_id": "att_01978abc-1006-7000-8000-000000001006",
            "context_packet_id": "ctx_01978abc-1007-7000-8000-000000001007",
            "producer_profile": "release-evidence",
            "code_commit": "git:sha1:" + "1" * 40,
            "branch_identity": "codex/test",
            "worktree_identity": "test",
            "environment_fingerprint": "2" * 64,
            "created_at": "2026-08-08T12:00:00Z",
            "observed_at": "2026-08-08T12:00:00Z",
            "relative_directory": "release/evidence",
        },
    )

    assert resolver is None and pending is True
    assert (manifest_ref, control_ref) == (
        "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6b",
        "art_019fe35c-2a75-7650-b2cd-7d8bdef1fe6c",
    )
    assert len(registrations) == 2
    assert all(item["registration"].manifest["authority"]["use_authority"] == "candidate" for item in registrations)

    manifest_document = {"kind": "manifest"}
    control_document = {"kind": "control"}
    streams = {
        manifest_ref: {
            "content_sha256": sha256_hex(canonical_bytes(manifest_document)),
            "use_authority": "candidate",
        },
        control_ref: {
            "content_sha256": sha256_hex(canonical_bytes(control_document)),
            "use_authority": "candidate",
        },
    }
    monkeypatch.setattr(cli, "replay", lambda *args, **kwargs: {"release_decisions": {}, "streams": streams})

    resolver, _, _, pending = cli._publication_evidence(
        binding,
        source,
        actor_id="act_01978abc-1002-7000-8000-000000001002",
        authority_grant_id="agr_01978abc-1003-7000-8000-000000001003",
        registration_context=None,
    )

    assert resolver is None and pending is True
    assert len(registrations) == 2

    class StoredEvidence:
        def __init__(self, **kwargs):
            pass

        def resolve_evaluation_runs(self, reference):
            assert reference == manifest_ref
            return manifest_document

        def resolve_control_binding(self, reference):
            assert reference == control_ref
            return control_document

        def rederive_release_decision(self, manifest, control):
            assert (manifest, control) == (manifest_document, control_document)
            return source, False

    for stream in streams.values():
        stream["use_authority"] = "accepted_for_scope"
    monkeypatch.setattr(cli, "StoredReleasePublicationEvidence", StoredEvidence)
    monkeypatch.setattr(cli, "build_artefact_consumers", lambda binding: object())

    resolver, resumed_manifest_ref, resumed_control_ref, pending = cli._publication_evidence(
        binding,
        source,
        actor_id="act_01978abc-1002-7000-8000-000000001002",
        authority_grant_id="agr_01978abc-1003-7000-8000-000000001003",
        registration_context=None,
    )

    assert isinstance(resolver, StoredEvidence) and pending is False
    assert (resumed_manifest_ref, resumed_control_ref) == (manifest_ref, control_ref)
    assert len(registrations) == 2
