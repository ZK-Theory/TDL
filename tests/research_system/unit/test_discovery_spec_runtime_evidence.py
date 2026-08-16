from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.runtime import DiscoveryRuntime, _Spec02ExecutionAuthority, _runtime_git


class _AcceptingSchemas:
    def validate(self, _schema_id: str, _value: object, *, schema_version: str) -> None:
        assert schema_version == "1.0.0"


def test_runtime_git_probe_ignores_hostile_configuration_environment(tmp_path, monkeypatch) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    subprocess.run(["git", "-C", str(repository), "init", "--quiet"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.email", "tests@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "Tests"], check=True)
    (repository / "source.txt").write_text("source\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "source.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "--quiet", "-m", "fixture"], check=True)
    expected = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "malformed")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "malicious")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "missing-config"))

    assert (
        str(_runtime_git(repository, "rev-parse", "HEAD", unavailable_message="runtime Git unavailable")).strip()
        == expected
    )


def _registered_document(
    tmp_path,
    artefact_type: str,
    document: dict[str, Any],
    suffix: str,
    *,
    producer_actor_id: str,
    authority_grant_id: str = "ordinary-grant",
) -> dict[str, Any]:
    raw = canonical_bytes(document)
    relative_path = f"objects/{suffix}.json"
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {
        "event_type": "ArtefactRegistered",
        "actor_id": producer_actor_id,
        "authority_grant_id": authority_grant_id,
        "payload": {
            "manifest": {
                "artefact_type": artefact_type,
                "relative_path": relative_path,
                "content_sha256": sha256_hex(raw),
                "producer_actor_id": producer_actor_id,
            }
        },
    }


def _approval_fixture(tmp_path) -> tuple[DiscoveryRuntime, dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...]]:
    runtime = DiscoveryRuntime.__new__(DiscoveryRuntime)
    runtime.control_root = tmp_path
    runtime.schemas = _AcceptingSchemas()
    runtime.clock = lambda: datetime(2026, 8, 1, 12, 30, tzinfo=UTC)
    runtime.authority_resolver = SimpleNamespace(owner_published_grant_ids=lambda: frozenset({"owner-grant"}))
    runtime._prospective_spec_document = None
    candidate = {
        "candidate_id": "candidate",
        "decision_id": "promotion",
        "source_observation_refs": ["source"],
    }
    projection = {"source_observations": {"source": {"batch": {"source_query": "exact:SPEC-GATE6-RUN-V1"}}}}
    source_sha256 = "a" * 64
    promotion = {
        "event_type": "CandidatePromotionApplied",
        "stream_id": "candidate",
        "event_id": "promotion",
        "event_hash": "b" * 64,
        "actor_id": "owner",
        "payload": {"row_id": "OR-013", "selected_option": "PROMOTE"},
    }
    approval = {
        "approved_at": "2026-08-01T12:15:00Z",
        "valid_window": {"starts_at": "2026-08-01T12:00:00Z", "expires_at": "2026-08-01T13:00:00Z"},
        "owner": {"actor_id": "owner"},
        "registrar": {"actor_id": "registrar"},
        "spec_01_promotion": {"id": "promotion", "sha256": "b" * 64},
        "spec_02_subject": {"id": "SPEC-02", "sha256": source_sha256},
        "brief_identity": {"id": "spec-02.md", "sha256": source_sha256},
        "entry_mode": "standard_promotion",
        "scientific_promotion": True,
        "source_correction": None,
    }
    brief = {
        "stage": "SPEC-02",
        "route_source": {"relative_path": "spec-02.md", "raw_sha256": source_sha256},
        "operator_session": {"operator_actor_id": "owner"},
    }
    events = (
        promotion,
        _registered_document(
            tmp_path,
            "spec_02_live_run_approval",
            approval,
            "approval",
            producer_actor_id="registrar",
            authority_grant_id="owner-grant",
        ),
        _registered_document(tmp_path, "spec_02_operator_brief", brief, "brief", producer_actor_id="owner"),
    )
    return runtime, candidate, projection, events


def test_spec_runtime_rejects_malformed_utf8_registered_approval(tmp_path) -> None:
    runtime, candidate, projection, events = _approval_fixture(tmp_path)
    approval_path = tmp_path / events[1]["payload"]["manifest"]["relative_path"]
    approval_path.write_bytes(b"\xff")

    assert runtime._spec_02_execution_approval(candidate, projection, events=events) is None


def test_spec_runtime_rejects_approval_claimed_after_evaluation_time(tmp_path) -> None:
    runtime, candidate, projection, events = _approval_fixture(tmp_path)
    approval_path = tmp_path / events[1]["payload"]["manifest"]["relative_path"]
    approval = json.loads(approval_path.read_bytes())
    approval["approved_at"] = "2026-08-01T12:45:00Z"
    raw = canonical_bytes(approval)
    approval_path.write_bytes(raw)
    events[1]["payload"]["manifest"]["content_sha256"] = sha256_hex(raw)

    assert runtime._spec_02_execution_approval(candidate, projection, events=events) is None


def test_spec_runtime_rejects_registrar_identity_not_bound_to_registration_event(tmp_path) -> None:
    runtime, candidate, projection, events = _approval_fixture(tmp_path)
    events[1]["actor_id"] = "owner"

    assert runtime._spec_02_execution_approval(candidate, projection, events=events) is None


def test_spec_runtime_requires_owner_published_approval_registration_grant(tmp_path) -> None:
    runtime, candidate, projection, events = _approval_fixture(tmp_path)
    events[1]["authority_grant_id"] = "ordinary-grant"

    assert runtime._spec_02_execution_approval(candidate, projection, events=events) is None


def test_spec_return_binds_embedded_verdict_and_prepared_brief(tmp_path) -> None:
    runtime, _candidate, _projection, _events = _approval_fixture(tmp_path)
    verdict = {"verdict": "PASS"}
    verdict_sha256 = sha256_hex(canonical_bytes(verdict))
    brief = {
        "brief_manifest": {"brief_artefact_id": "brief"},
        "brief_manifest_sha256": "c" * 64,
        "operator_session": {"session_id": "session"},
        "route_source": {"raw_sha256": "d" * 64},
    }
    authority = _Spec02ExecutionAuthority(
        approval={
            "limits": {
                "resource_ids": ["resource"],
                "budget_gbp": 1,
                "wall_time_seconds": 1,
                "cpu_seconds": 1,
                "peak_memory_bytes": 1,
            }
        },
        brief=brief,
        correction=None,
    )
    relation = {"resource_ref": {"id": "resource"}}
    command = SimpleNamespace(
        actor_id="operator",
        envelope={"payload": {"verdict": "PASS", "verdict_sha256": verdict_sha256, "verdict_artifact": verdict}},
    )
    document = {
        "stage": "SPEC-02",
        "route_id": "SPEC-GATE6-RUN-V1",
        "document_type": "spec_02_return",
        "outcome": "COMPLETE",
        "responds_to": {
            "brief_artefact_id": "brief",
            "brief_manifest_sha256": "c" * 64,
            "operator_session_id": "session",
        },
        "producer": {"actor_id": "operator", "relation_sha256": sha256_hex(canonical_bytes(relation))},
        "sources": [{"name": "accepted-spec-source", "sha256": "d" * 64}],
        "artifact_hashes": [{"name": "embedded_artefact", "sha256": verdict_sha256}],
        "resource_use": {"external_cost_gbp": 1, "elapsed_seconds": 1, "cpu_seconds": 1, "peak_memory_bytes": 1},
        "embedded_artefact": verdict,
    }
    runtime._prospective_spec_document = document
    spike = {"execution_authority_relation": relation}

    assert runtime._spec_02_return_allowed(command=command, authority=authority, spike=spike, events=())
    document["embedded_artefact"] = {"verdict": "PARTIAL"}
    assert not runtime._spec_02_return_allowed(command=command, authority=authority, spike=spike, events=())
    document["embedded_artefact"] = verdict
    document["responds_to"]["brief_artefact_id"] = "other"
    assert not runtime._spec_02_return_allowed(command=command, authority=authority, spike=spike, events=())
