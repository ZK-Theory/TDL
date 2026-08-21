from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import research_system.discovery.runtime as discovery_runtime_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.discovery.runtime import (
    DiscoveryRuntime,
    _Spec02ExecutionAuthority,
    _SpecExecutionAuthorityResolver,
    _SPEC_02_APPROVAL_AUTHORITY_REASON,
    _SPEC_02_APPROVAL_EVIDENCE_PREFIX,
    _LEGACY_SPEC_02_APPROVAL_PUBLICATION,
    _is_exact_legacy_spec_02_approval_publication,
    _is_exact_legacy_spec_02_return,
    _runtime_git,
    _spec_02_plan_contract_matches,
    _spec_02_return_evidence_matches,
)
from research_system.discovery.rules import _is_spec_route_candidate


class _AcceptingSchemas:
    def validate(self, _schema_id: str, _value: object, *, schema_version: str) -> None:
        assert schema_version == "1.0.0"


class _ReturnValidationHarness:
    """Expose only the dependencies of the production return validator."""

    _spec_02_resource_allowed = staticmethod(DiscoveryRuntime._spec_02_resource_allowed)
    _spec_02_resource_use_allowed = staticmethod(DiscoveryRuntime._spec_02_resource_use_allowed)
    _spec_02_return_allowed = DiscoveryRuntime._spec_02_return_allowed

    def __init__(self, control_root) -> None:
        self.control_root = control_root
        self.schemas = _AcceptingSchemas()


def test_spec_route_candidate_accepts_the_exact_assay_bar_relation_for_historical_replay() -> None:
    candidate_id = "obj_01a00620-0f74-7613-a7b0-dffbb50d9663"
    assay_id = "asy_01a00620-0f74-74e6-b440-f760f4eb6731"
    candidate = {"candidate_id": candidate_id, "assay_id": assay_id, "source_observation_refs": ["source"]}
    state = {
        "source_observations": {"source": {"batch": {"source_query": "historical DOI query"}}},
        "assay_bar_authority": {
            "status": "accepted",
            "acceptance_sha256": "a" * 64,
            "producer_relation_sha256": "b" * 64,
        },
        "assays": {
            assay_id: {
                "candidate_id": candidate_id,
                "assay_bar_acceptance_sha256": "a" * 64,
                "producer_relation_sha256": "b" * 64,
            }
        },
    }

    assert _is_spec_route_candidate(state, candidate)
    state["assays"][assay_id]["producer_relation_sha256"] = "c" * 64
    assert not _is_spec_route_candidate(state, candidate)


def test_spec_route_candidate_rejects_reused_historical_bar_relation() -> None:
    candidate = {"candidate_id": "foreign", "assay_id": "foreign-assay", "source_observation_refs": []}
    state = {
        "source_observations": {},
        "assay_bar_authority": {
            "status": "accepted",
            "acceptance_sha256": "a" * 64,
            "producer_relation_sha256": "b" * 64,
        },
        "assays": {
            "foreign-assay": {
                "candidate_id": "foreign",
                "assay_bar_acceptance_sha256": "a" * 64,
                "producer_relation_sha256": "b" * 64,
            }
        },
    }

    assert not _is_spec_route_candidate(state, candidate)


def test_spec_02_resource_use_must_match_registered_exact_attempt_measurement(tmp_path) -> None:
    resource_use = {
        "elapsed_seconds": 5,
        "cpu_seconds": 3,
        "peak_memory_bytes": 1024,
        "external_cost_gbp": 0,
    }
    candidate_id = "candidate"
    spike = {"spike_id": "spike", "attempt_id": "attempt", "attempt_sha256": "a" * 64}
    producer = {"actor_id": "operator"}
    evidence_types = {
        "raw_output": "evaluation_run",
        "source": "evaluation_run",
        "checks": "validation_report",
        "result": "evaluation_run",
        "resource_measurement": "resource_measurement",
    }
    streams: dict[str, Any] = {}
    artifact_hashes: list[dict[str, str]] = []
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    for name, artefact_type in evidence_types.items():
        content: object = resource_use if name == "resource_measurement" else f"exact deterministic {name}"
        value = {
            "schema_id": "ars://portfolio/spec-route-evidence",
            "schema_version": "1.0.0",
            "route_id": "SPEC-GATE6-RUN-V1",
            "stage": "SPEC-02",
            "evidence_kind": name,
            "candidate_id": candidate_id,
            "spike_id": spike["spike_id"],
            "attempt_id": spike["attempt_id"],
            "attempt_sha256": spike["attempt_sha256"],
            "content": content,
        }
        raw = canonical_bytes(value)
        digest = sha256_hex(raw)
        relative = f"evidence/{name}.json"
        (tmp_path / relative).write_bytes(raw)
        streams[name] = {
            "content_sha256": digest,
            "manifest": {
                "root_id": "control",
                "relative_path": relative,
                "artefact_type": artefact_type,
                "producer_actor_id": producer["actor_id"],
                "attempt_id": spike["attempt_id"],
                "authority": {"accepted_scope": "spec-gate6-run"},
            },
        }
        artifact_hashes.append({"name": name, "sha256": digest})
    document = {"artifact_hashes": artifact_hashes, "producer": producer, "resource_use": resource_use}

    assert _spec_02_return_evidence_matches(
        document,
        projection={"artefact_streams": streams},
        control_root=tmp_path,
        candidate_id=candidate_id,
        spike=spike,
    )
    document["resource_use"] = {**resource_use, "elapsed_seconds": 1}
    assert not _spec_02_return_evidence_matches(
        document,
        projection={"artefact_streams": streams},
        control_root=tmp_path,
        candidate_id=candidate_id,
        spike=spike,
    )
    document["resource_use"] = resource_use
    streams["resource_measurement"]["manifest"]["attempt_id"] = "other-attempt"
    assert not _spec_02_return_evidence_matches(
        document,
        projection={"artefact_streams": streams},
        control_root=tmp_path,
        candidate_id=candidate_id,
        spike=spike,
    )


def test_spec_02_legacy_return_adapter_is_one_exact_frozen_transaction() -> None:
    transaction_id = "legacy-transaction"
    hashes = (
        "a5b04ff1a955a7bfdc764e3e3ede56a0b24aae65c7825f4fd08f5313c22503ca",
        "eeb8b10c55994a88f28c53d32c7b0a64caf6c096de3a5a813fe7cc065da11e2d",
    )
    events = tuple({"transaction_id": transaction_id, "event_hash": value} for value in hashes)
    event = {
        "command_type": "RecordSpikeVerdict",
        "transaction_id": transaction_id,
        "payload": {"row_id": "OR-018"},
    }

    assert _is_exact_legacy_spec_02_return(event, events)
    changed = (*events[:-1], {**events[-1], "event_hash": "f" * 64})
    assert not _is_exact_legacy_spec_02_return(event, changed)
    assert not _is_exact_legacy_spec_02_return({**event, "payload": {"row_id": "OR-019"}}, events)


def test_spec_02_legacy_approval_adapter_is_one_exact_frozen_publication() -> None:
    binding = _LEGACY_SPEC_02_APPROVAL_PUBLICATION
    event = {
        "event_id": binding["event_id"],
        "event_hash": binding["event_hash"],
        "command_id": binding["command_id"],
        "command_payload_hash": binding["command_payload_hash"],
    }
    arguments = {
        "approval_sha256": binding["approval_sha256"],
        "approval_grant_id": binding["approval_grant_id"],
        "approval_artefact_id": binding["approval_artefact_id"],
    }

    assert _is_exact_legacy_spec_02_approval_publication(event, **arguments)
    assert not _is_exact_legacy_spec_02_approval_publication(
        {**event, "event_hash": "f" * 64},
        **arguments,
    )
    assert not _is_exact_legacy_spec_02_approval_publication(
        event,
        **{**arguments, "approval_sha256": "f" * 64},
    )


def test_spec_02_legacy_return_adapter_replays_only_its_bound_raw_artefacts(tmp_path, monkeypatch) -> None:
    candidate_id = "candidate"
    spike = {"spike_id": "spike", "attempt_id": "attempt"}
    producer_actor_id = "producer"
    evidence_bindings: dict[str, dict[str, str]] = {}
    streams: dict[str, dict[str, Any]] = {}
    artifact_hashes: list[dict[str, str]] = []
    for name, artefact_type in {
        "raw_output": "evaluation_run",
        "source": "evaluation_run",
        "checks": "validation_report",
        "result": "evaluation_run",
    }.items():
        artefact_id = f"artefact-{name}"
        raw = canonical_bytes({"evidence": name})
        digest = sha256_hex(raw)
        relative_path = f"evidence/{name}.json"
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        evidence_bindings[name] = {
            "artefact_id": artefact_id,
            "artefact_type": artefact_type,
            "content_sha256": digest,
        }
        streams[artefact_id] = {
            "content_sha256": digest,
            "manifest": {
                "artefact_id": artefact_id,
                "root_id": "control",
                "relative_path": relative_path,
                "artefact_type": artefact_type,
                "producer_actor_id": producer_actor_id,
                "attempt_id": spike["attempt_id"],
                "authority": {"accepted_scope": "legacy-scope"},
            },
        }
        artifact_hashes.append({"name": name, "sha256": digest})
    document = {"artifact_hashes": artifact_hashes, "producer": {"actor_id": producer_actor_id}}
    monkeypatch.setattr(
        discovery_runtime_module,
        "_LEGACY_SPEC_02_RETURN_BINDING",
        {
            "return_sha256": sha256_hex(canonical_bytes(document)),
            "candidate_id": candidate_id,
            "spike_id": spike["spike_id"],
            "attempt_id": spike["attempt_id"],
            "producer_actor_id": producer_actor_id,
            "accepted_scope": "legacy-scope",
            "evidence": evidence_bindings,
        },
    )

    assert _spec_02_return_evidence_matches(
        document,
        projection={"artefact_streams": streams},
        control_root=tmp_path,
        candidate_id=candidate_id,
        spike=spike,
        legacy_frozen=True,
    )
    streams["artefact-checks"]["manifest"]["authority"]["accepted_scope"] = "other"
    assert not _spec_02_return_evidence_matches(
        document,
        projection={"artefact_streams": streams},
        control_root=tmp_path,
        candidate_id=candidate_id,
        spike=spike,
        legacy_frozen=True,
    )


def test_legacy_spec_02_plan_version_is_replay_only() -> None:
    authority = _Spec02ExecutionAuthority(
        approval={"spec_02_subject": {"id": "SPEC-02", "sha256": "a" * 64}},
        brief={"route_source": {"raw_sha256": "a" * 64}},
        correction=None,
    )
    plan = {"planned_contracts": ["W11:OR-018", "SPEC-02:v1.1.0"]}

    assert not _spec_02_plan_contract_matches(plan, authority)
    assert _spec_02_plan_contract_matches(plan, authority, allow_legacy_version=True)


class _ApprovalResolverHarness(_SpecExecutionAuthorityResolver):
    """Supply a frozen authority event snapshot while exercising production matching."""

    def __init__(self, *, authority_events: list[dict[str, Any]], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.authority_events = authority_events

    def _authority_decision_context(
        self,
        _projection: dict[str, Any],
        _events: tuple[dict[str, Any], ...],
    ) -> tuple[object, tuple[dict[str, Any], ...]]:
        return SimpleNamespace(owner_actor_id="owner", root_grant_id="root-grant"), tuple(self.authority_events)


def _approval_intent(approval: dict[str, Any], approval_sha256: str, artefact_id: str) -> dict[str, Any]:
    return {
        "target_actor_id": "registrar",
        "target_actor_class": "agent",
        "authority_lane": "producer/spec_brief_registration",
        "actor_role": "SPEC brief producer",
        "subject_scope": {
            "project_id": "project",
            "subject": {"kind": "artefact", "id": artefact_id},
        },
        "evidence_refs": [f"{_SPEC_02_APPROVAL_EVIDENCE_PREFIX}{approval_sha256}"],
        "effective_at": approval["valid_window"]["starts_at"],
        "expires_at": approval["valid_window"]["expires_at"],
        "reason": _SPEC_02_APPROVAL_AUTHORITY_REASON,
        "owner_action": "activate_authority_grant",
    }


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
                "artefact_id": f"{suffix}-artefact",
                "artefact_type": artefact_type,
                "relative_path": relative_path,
                "content_sha256": sha256_hex(raw),
                "producer_actor_id": producer_actor_id,
            }
        },
    }


def _approval_fixture(
    tmp_path,
) -> tuple[_SpecExecutionAuthorityResolver, dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...]]:
    """Build the validator's complete dependency surface and prove its positive control."""

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
    approval_sha256 = events[1]["payload"]["manifest"]["content_sha256"]
    artefact_id = events[1]["payload"]["manifest"]["artefact_id"]
    intent = _approval_intent(approval, approval_sha256, artefact_id)
    subject_scope = intent["subject_scope"]
    authority_events = [
        {
            "event_type": "OwnerAuthorityAdministrationDecisionPublished",
            "command_type": "PublishOwnerAuthorityAdministrationDecision",
            "actor_id": "owner",
            "authority_grant_id": "root-grant",
            "command_payload_hash": sha256_hex(canonical_bytes({"intent": intent})),
            "payload": {
                "decision": {
                    "owner_actor_id": "owner",
                    "target_grant_id": "owner-grant",
                    "subject_scope": subject_scope,
                    "effective_at": approval["valid_window"]["starts_at"],
                    "expires_at": approval["valid_window"]["expires_at"],
                },
                "proposed_grant": {
                    "authority_grant_id": "owner-grant",
                    "actor_id": "registrar",
                    "subject_scope": subject_scope,
                },
            },
        }
    ]
    resolver = _ApprovalResolverHarness(
        control_root=tmp_path,
        schemas=_AcceptingSchemas(),
        clock=lambda: datetime(2026, 8, 1, 12, 30, tzinfo=UTC),
        authority_resolver=SimpleNamespace(
            control_root=tmp_path / "authority",
            project_id="project",
            owner_published_grant_ids=lambda: frozenset({"owner-grant"}),
        ),
        authority_events=authority_events,
    )
    assert resolver.resolve(candidate, projection, events=events) is not None
    return resolver, candidate, projection, events


def test_spec_runtime_rejects_malformed_utf8_registered_approval(tmp_path) -> None:
    resolver, candidate, projection, events = _approval_fixture(tmp_path)
    approval_path = tmp_path / events[1]["payload"]["manifest"]["relative_path"]
    approval_path.write_bytes(b"\xff")

    assert resolver.resolve(candidate, projection, events=events) is None


def test_spec_runtime_rejects_approval_claimed_after_evaluation_time(tmp_path) -> None:
    resolver, candidate, projection, events = _approval_fixture(tmp_path)
    approval_path = tmp_path / events[1]["payload"]["manifest"]["relative_path"]
    approval = json.loads(approval_path.read_bytes())
    approval["approved_at"] = "2026-08-01T12:45:00Z"
    raw = canonical_bytes(approval)
    approval_path.write_bytes(raw)
    events[1]["payload"]["manifest"]["content_sha256"] = sha256_hex(raw)
    artefact_id = events[1]["payload"]["manifest"]["artefact_id"]
    intent = _approval_intent(approval, sha256_hex(raw), artefact_id)
    resolver.authority_events[0]["command_payload_hash"] = sha256_hex(canonical_bytes({"intent": intent}))

    assert resolver.resolve(candidate, projection, events=events) is None


def test_spec_runtime_rejects_registrar_identity_not_bound_to_registration_event(tmp_path) -> None:
    resolver, candidate, projection, events = _approval_fixture(tmp_path)
    events[1]["actor_id"] = "owner"

    assert resolver.resolve(candidate, projection, events=events) is None


def test_spec_runtime_requires_owner_published_approval_registration_grant(tmp_path) -> None:
    resolver, candidate, projection, events = _approval_fixture(tmp_path)
    events[1]["authority_grant_id"] = "ordinary-grant"

    assert resolver.resolve(candidate, projection, events=events) is None


def test_spec_runtime_rejects_rehashed_owner_decision_without_exact_approval_command(tmp_path) -> None:
    resolver, candidate, projection, events = _approval_fixture(tmp_path)
    resolver.authority_events[0]["command_payload_hash"] = sha256_hex(
        canonical_bytes({"intent": {"evidence_refs": ["spec-02-approval-sha256:" + "f" * 64]}})
    )

    assert resolver.resolve(candidate, projection, events=events) is None


def test_spec_return_binds_embedded_verdict_and_prepared_brief(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(discovery_runtime_module, "_spec_02_return_evidence_matches", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(discovery_runtime_module, "_spec_02_pass_rerun_matches", lambda *_args, **_kwargs: True)
    runtime = _ReturnValidationHarness(tmp_path)
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
    spike = {"execution_authority_relation": relation}

    assert runtime._spec_02_return_allowed(
        command=command,
        authority=authority,
        spike=spike,
        projection={},
        events=(),
        prospective_document=document,
    )
    document["embedded_artefact"] = {"verdict": "PARTIAL"}
    assert not runtime._spec_02_return_allowed(
        command=command,
        authority=authority,
        spike=spike,
        projection={},
        events=(),
        prospective_document=document,
    )
    document["embedded_artefact"] = verdict
    document["responds_to"]["brief_artefact_id"] = "other"
    assert not runtime._spec_02_return_allowed(
        command=command,
        authority=authority,
        spike=spike,
        projection={},
        events=(),
        prospective_document=document,
    )
