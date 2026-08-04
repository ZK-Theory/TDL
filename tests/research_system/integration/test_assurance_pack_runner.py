"""Public-seam tests for the two-phase TDL_private assurance-pack runner."""

from __future__ import annotations

import subprocess
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from research_system.assurance import PackUnconsumable
from research_system.assurance.external_records import ExternalRecordResolution
from research_system.assurance.pack_loader import _revalidate_references
from research_system.assurance.runner import (
    AssurancePackRunnerConfig,
    SemanticRecordLocator,
    _FactsResolution,
    _GitObjectReader,
    accept_assurance_pack,
    prepare_assurance_pack,
)
from research_system.assurance import runner as runner_module
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.config import ControlBinding
from research_system import cli
from tests.research_system.contracts import test_wp6_3_tdl_private_assurance_pack_contract as frozen


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACK_PATH = ".research-system/packs/tdl-private-assurance.yaml"
FACTS_PRODUCER_SESSION_ID = "ctx_00000000-0000-7000-8000-000000000031"
FACTS_REVIEW_SESSION_ID = "ctx_00000000-0000-7000-8000-000000000032"
FACTS_HANDOFF_ID = "hnd_00000000-0000-7000-8000-000000000033"


class _RecordResolver:
    def __init__(self, record_store: dict[str, dict]) -> None:
        self.record_store = record_store
        self.calls: list[tuple[str, str]] = []

    def resolve_with_receipt(
        self,
        *,
        record_id: str,
        record_class: str,
        authority_root: str,
        phase: str,
    ) -> ExternalRecordResolution:
        self.calls.append((record_class, phase))
        record = self.record_store[record_id]
        return ExternalRecordResolution(
            record_class=record_class,
            record_id=record_id,
            revision=1,
            canonical_sha256=sha256_hex(canonical_bytes(record)),
            record=record,
        )


class _FactsReader:
    def __init__(self, facts: dict[str, _FactsResolution]) -> None:
        self.facts = facts
        self.calls: list[tuple[str, str]] = []

    def resolve(self, record_id: str, *, phase: str) -> _FactsResolution:
        self.calls.append((record_id, phase))
        return self.facts[record_id]


class _GrantAuthority:
    def __init__(self, *, project_id: str, requirement_id: str, failure: str | None = None) -> None:
        self.project_id = project_id
        self.requirement_id = requirement_id
        self.failure = failure

    def resolve_policy_action(self, *args: object) -> None:
        if self.failure == "integrity":
            from research_system.errors import IntegrityError

            raise IntegrityError("corrupt replay receipt")
        if self.failure in {"expired", "revoked"}:
            from research_system.errors import ArsError

            raise ArsError(f"{self.failure} grant")

    def scoped_grant_identity(self, grant_id: str) -> SimpleNamespace:
        if self.failure == "foreign":
            subject_id = "asr_00000000-0000-7000-8000-000000000099"
        else:
            subject_id = self.requirement_id
        return SimpleNamespace(
            authority_grant_id=grant_id,
            authority_grant_sha256="a" * 64,
            actor_id=frozen.ACT_OWNER,
            schema_id="ars://core/policy-action/AcceptR3AssuranceRequirement",
            schema_version="1.0.0",
            schema_sha256="b" * 64,
            activation_event_id="evt_00000000-0000-7000-8000-000000000001",
            activation_position=1,
            administration_decision_id="dec_00000000-0000-7000-8000-000000000001",
            administration_decision_sha256="c" * 64,
            status="active",
            revocation_event_id=None,
            subject_scope=SimpleNamespace(
                project_id=self.project_id,
                subject_kind="assurance_requirement",
                subject_id=subject_id,
            ),
        )


def _binding(repo: Path, control_root: Path) -> ControlBinding:
    control_root.mkdir(parents=True, exist_ok=True)
    return ControlBinding(
        code_roots=(repo,),
        control_root=control_root,
        project_id="prj_019fc96b-2ddc-7740-9d6c-425adf7fa3ab",
        schema_root=repo / ".research-system" / "schemas",
        store_identity="store_019fc96b-2ddc-7740-9d6c-425adf7fa3ab",
    )


def _temporary_repository(tmp_path: Path, raw_candidate: bytes) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    source_reader = _GitObjectReader(REPOSITORY_ROOT)
    source_contract = runner_module._parse_yaml_bytes(
        source_reader.blob(
            source_reader.blob_at(
                source_reader.head_commit(), ".research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml"
            )
        ),
        "source contract",
    )
    repository_paths = {
        ".research-system/contracts/wp6-3-tdl-private-assurance-pack.yaml",
        ".research-system/schemas/assurance/assurance-pack.schema.json",
    }
    reference_rows = source_contract["required_pack_contract"]["references"]["exact_reference_rows"]
    repository_paths.update(row["repository_path"] for row in reference_rows)
    for repository_path in repository_paths:
        source = REPOSITORY_ROOT / repository_path
        target = repo / repository_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    candidate_path = repo / PACK_PATH
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(raw_candidate)
    subprocess.run(["git", "-C", str(repo), "init", "--quiet"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "runner-test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "runner-test"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "test candidate"], check=True, capture_output=True, text=True
    )
    return repo, candidate_path


def _facts_for(
    *,
    relationship: ExternalRecordResolution,
    subject: dict[str, object],
    reviewer: str,
    producer: str,
    scope: str,
    reviewed_at: str,
) -> _FactsResolution:
    body = {
        "record_type": "relationship_evidence_facts",
        "relationship_evidence_facts_id": relationship.record_id,
        "relationship_scope": scope,
        "protected_relationship": {
            "relationship_record_id": relationship.record_id,
            "revision": relationship.revision,
            "canonical_sha256": relationship.canonical_sha256,
            "relationship_context": relationship.record["relationship_context"],
            "grade": relationship.record["grade"],
            "effective_at": relationship.record["effective_at"],
            "expires_at": relationship.record["expires_at"],
        },
        "reviewed_subject": subject,
        "producer": {
            "actor_id": producer,
            "task_id": frozen.PRODUCER_TASK_ID,
            "session_id": FACTS_PRODUCER_SESSION_ID,
            "context_hash": "1" * 64,
            "model_family": "codex",
            "stable_handoff_or_run_id": FACTS_HANDOFF_ID,
        },
        "reviewer": {
            "actor_id": reviewer,
            "task_id": frozen.REVIEW_TASK_ID,
            "session_id": FACTS_REVIEW_SESSION_ID,
            "context_hash": "2" * 64,
            "model_family": "claude",
            "stable_handoff_or_run_id": FACTS_HANDOFF_ID,
        },
        "evidence_author_actor_id": reviewer,
        "producer_conclusions_visibility": "hidden_from_reviewer",
        "derived_comparisons": {
            "same_actor": False,
            "same_session": False,
            "same_context_hash": False,
            "same_model_family": False,
            "producer_conclusions_visible": False,
        },
        "independence_grade": "I2",
        "review_state": "completed",
        "reviewed_at": reviewed_at,
    }
    return _FactsResolution(relationship.record_id, 1, sha256_hex(canonical_bytes(body)), body)


def _runner_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    contract = frozen._load_yaml(frozen.CONTRACT_PATH)
    pack = frozen._proposed_pack(contract)
    pack, raw_candidate, record_store, _ = frozen._external_records(pack, contract)
    repo, candidate_path = _temporary_repository(tmp_path, raw_candidate)
    binding = _binding(repo, tmp_path / "control")
    config = AssurancePackRunnerConfig(binding=binding, repository_root=repo)
    record_resolver = _RecordResolver(record_store)
    reader = _GitObjectReader(repo)
    candidate = reader.candidate(candidate_path)
    parsed_pack = runner_module._candidate_pack(candidate)
    exact_subject = runner_module._candidate_subject(candidate, parsed_pack)
    exact_subject_dict = runner_module._pack_subject_dict(exact_subject)
    record_store[frozen.REVIEW_RECORD_ID]["subject"] = dict(exact_subject_dict)
    record_store[frozen.REVIEW_RECORD_ID]["two_key_closure_sha256"] = sha256_hex(
        canonical_bytes(
            {
                "obligation_evidence_rows": record_store[frozen.REVIEW_RECORD_ID]["obligation_evidence_rows"],
                "boundary_fixture_execution_rows": record_store[frozen.REVIEW_RECORD_ID][
                    "boundary_fixture_execution_rows"
                ],
            }
        )
    )
    record_store[frozen.OWNER_DECISION_ID]["subject"] = dict(exact_subject_dict)
    record_store[frozen.OWNER_DECISION_ID]["review_record_sha256"] = sha256_hex(
        canonical_bytes(record_store[frozen.REVIEW_RECORD_ID])
    )
    record_store[frozen.OWNER_DECISION_ID]["two_key_closure_sha256"] = record_store[frozen.REVIEW_RECORD_ID][
        "two_key_closure_sha256"
    ]

    scope_record = ExternalRecordResolution(
        "producer_relationship_evidence",
        frozen.SCOPE_RELATIONSHIP_ID,
        1,
        sha256_hex(canonical_bytes(record_store[frozen.SCOPE_RELATIONSHIP_ID])),
        record_store[frozen.SCOPE_RELATIONSHIP_ID],
    )
    review_relationship = ExternalRecordResolution(
        "producer_relationship_evidence",
        frozen.REVIEW_RELATIONSHIP_ID,
        1,
        sha256_hex(canonical_bytes(record_store[frozen.REVIEW_RELATIONSHIP_ID])),
        record_store[frozen.REVIEW_RELATIONSHIP_ID],
    )
    requirement = record_store[frozen.REQUIREMENT_RECORD_ID]
    requirement_subject = {
        "subject_kind": "assurance_requirement",
        "subject_id": requirement["assurance_requirement_id"],
        "subject_revision": requirement["revision"],
        "subject_sha256": sha256_hex(canonical_bytes(requirement)),
    }
    pack_subject = runner_module._candidate_subject(candidate, parsed_pack)
    facts = {
        "relationship_evidence_facts:requirement_scope": _facts_for(
            relationship=scope_record,
            subject=requirement_subject,
            reviewer=frozen.ACT_SCOPE_REVIEWER,
            producer=frozen.ACT_PRODUCER,
            scope="requirement_scope",
            reviewed_at="2026-07-28T08:40:00Z",
        ),
        "relationship_evidence_facts:pack_review": _facts_for(
            relationship=review_relationship,
            subject={
                "subject_kind": "assurance_pack",
                "subject_id": pack_subject.assurance_pack_id,
                "subject_revision": pack_subject.assurance_pack_revision,
                "subject_sha256": pack_subject.pack_raw_sha256,
            },
            reviewer=frozen.ACT_SCIENTIFIC_REVIEWER,
            producer=frozen.ACT_PRODUCER,
            scope="pack_review",
            reviewed_at="2026-07-28T10:30:00Z",
        ),
    }
    facts_reader = _FactsReader({value.record_id: value for value in facts.values()})
    authority = _GrantAuthority(
        project_id=binding.project_id,
        requirement_id=requirement["assurance_requirement_id"],
    )

    class _Registry:
        def resolve_identity(self, schema_id: str, schema_version: str) -> SimpleNamespace:
            return SimpleNamespace(schema_id=schema_id, schema_version=schema_version, sha256="b" * 64)

    monkeypatch.setattr(runner_module, "ControlStoreAuthorityResolver", lambda _: record_resolver)
    monkeypatch.setattr(runner_module, "_FactsReader", lambda *_: facts_reader)
    monkeypatch.setattr(runner_module, "LedgerAuthorityGrantResolver", lambda *_, **__: authority)
    monkeypatch.setattr(runner_module, "runtime_schema_registry", lambda *_: _Registry())

    locators = {
        "accepted_assurance_requirement": SemanticRecordLocator(
            "accepted_assurance_requirement", frozen.REQUIREMENT_RECORD_ID
        ),
        "contract_schema_authorship": SemanticRecordLocator(
            "contract_schema_authorship", frozen.CONTRACT_AUTHORSHIP_RECORD_ID
        ),
        "independent_contract_review": SemanticRecordLocator(
            "independent_contract_review", frozen.CONTRACT_REVIEW_RECORD_ID
        ),
        "independent_schema_review": SemanticRecordLocator("independent_schema_review", frozen.SCHEMA_REVIEW_RECORD_ID),
        "stephen_contract_schema_acceptance": SemanticRecordLocator(
            "stephen_contract_schema_acceptance", frozen.CONTRACT_SCHEMA_ACCEPTANCE_ID
        ),
        "active_authority_grant": SemanticRecordLocator("active_authority_grant", frozen.OWNER_GRANT_ID),
        "registered_pack_object": SemanticRecordLocator("registered_pack_object", frozen.ASSURANCE_PACK_ID),
        "independent_pack_review": SemanticRecordLocator("independent_pack_review", frozen.REVIEW_RECORD_ID),
        "stephen_owner_acceptance": SemanticRecordLocator("stephen_owner_acceptance", frozen.OWNER_DECISION_ID),
        "requirement_scope_relationship": SemanticRecordLocator(
            "producer_relationship_evidence", frozen.SCOPE_RELATIONSHIP_ID
        ),
        "pack_review_relationship": SemanticRecordLocator(
            "producer_relationship_evidence", frozen.REVIEW_RELATIONSHIP_ID
        ),
        "relationship_evidence_facts:requirement_scope": SemanticRecordLocator(
            "relationship_evidence_facts", facts["relationship_evidence_facts:requirement_scope"].record_id
        ),
        "relationship_evidence_facts:pack_review": SemanticRecordLocator(
            "relationship_evidence_facts", facts["relationship_evidence_facts:pack_review"].record_id
        ),
    }
    for actor_id in (
        frozen.ACT_CONTRACT_AUTHOR,
        frozen.ACT_PRODUCER,
        frozen.ACT_REQUIREMENT_AUTHOR,
        frozen.ACT_SCOPE_REVIEWER,
        frozen.ACT_SCIENTIFIC_REVIEWER,
        frozen.ACT_OWNER,
        frozen.ACT_CONTRACT_REVIEWER,
        frozen.ACT_SCHEMA_REVIEWER,
    ):
        locators[f"canonical_actor:{actor_id}"] = SemanticRecordLocator("canonical_actor", actor_id)
    return config, candidate_path, locators, record_resolver, facts_reader, authority


def _policy_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str):
    contract = frozen._load_yaml(frozen.CONTRACT_PATH)
    pack = frozen._proposed_pack(contract)
    pack, _, record_store, _ = frozen._external_records(pack, contract)
    binding = _binding(REPOSITORY_ROOT, tmp_path / "control")
    requirement = record_store[frozen.REQUIREMENT_RECORD_ID]
    records = {
        "accepted_assurance_requirement": ExternalRecordResolution(
            "accepted_assurance_requirement",
            frozen.REQUIREMENT_RECORD_ID,
            1,
            sha256_hex(canonical_bytes(requirement)),
            requirement,
        ),
        "active_authority_grant": ExternalRecordResolution(
            "active_authority_grant",
            frozen.OWNER_GRANT_ID,
            1,
            sha256_hex(canonical_bytes(record_store[frozen.OWNER_GRANT_ID])),
            record_store[frozen.OWNER_GRANT_ID],
        ),
    }
    authority = _GrantAuthority(
        project_id=binding.project_id,
        requirement_id=requirement["assurance_requirement_id"],
        failure=failure,
    )

    class _Registry:
        def resolve_identity(self, schema_id: str, schema_version: str) -> SimpleNamespace:
            return SimpleNamespace(schema_id=schema_id, schema_version=schema_version, sha256="b" * 64)

    monkeypatch.setattr(runner_module, "LedgerAuthorityGrantResolver", lambda *_, **__: authority)
    monkeypatch.setattr(runner_module, "runtime_schema_registry", lambda *_: _Registry())
    return binding, pack, records


def test_prepare_then_acceptance_reloads_exact_subject_and_ignores_working_tree_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, candidate_path, locators, record_resolver, facts_reader, _ = _runner_inputs(tmp_path, monkeypatch)
    evaluation_time = datetime(2026, 7, 28, 12, tzinfo=UTC)
    run_id = "run_019fc96b-2ddc-7740-9d6c-425adf7fa3ab"
    prepare_locators = {key: value for key, value in locators.items() if key not in runner_module._FUTURE_PREPARE_KEYS}

    prepared = prepare_assurance_pack(
        config=config,
        candidate_path=candidate_path,
        evaluation_time=evaluation_time,
        run_id=run_id,
        record_locators=prepare_locators,
    )
    preparation_bytes = prepared.evidence_path.read_bytes()
    candidate_path.write_bytes(b"working-tree substitution is not a Git object")

    accepted = accept_assurance_pack(
        config=config,
        candidate_path=candidate_path,
        evaluation_time=evaluation_time,
        run_id=run_id,
        record_locators=locators,
    )

    assert prepared.state == "prepared"
    assert accepted.state == "consumption_authorized"
    assert accepted.subject == prepared.subject
    assert prepared.evidence_path.read_bytes() == preparation_bytes
    assert {phase for _, phase in record_resolver.calls} == {"load", "acceptance", "consumption"}
    assert {phase for _, phase in facts_reader.calls} == {"load", "acceptance", "consumption"}


def test_acceptance_public_seam_rejects_incomplete_two_key_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, candidate_path, locators, record_resolver, _, _ = _runner_inputs(tmp_path, monkeypatch)
    record_store = record_resolver.record_store
    record_store[frozen.REVIEW_RECORD_ID]["obligation_evidence_rows"].pop()
    record_store[frozen.OWNER_DECISION_ID]["review_record_sha256"] = sha256_hex(
        canonical_bytes(record_store[frozen.REVIEW_RECORD_ID])
    )
    evaluation_time = datetime(2026, 7, 28, 12, tzinfo=UTC)
    run_id = "run_019fc96b-2ddc-7740-9d6c-425adf7fa3ad"
    prepare_locators = {key: value for key, value in locators.items() if key not in runner_module._FUTURE_PREPARE_KEYS}
    prepare_assurance_pack(
        config=config,
        candidate_path=candidate_path,
        evaluation_time=evaluation_time,
        run_id=run_id,
        record_locators=prepare_locators,
    )

    with pytest.raises(PackUnconsumable, match="two-key evidence does not close every required obligation"):
        accept_assurance_pack(
            config=config,
            candidate_path=candidate_path,
            evaluation_time=evaluation_time,
            run_id=run_id,
            record_locators=locators,
        )


def test_acceptance_public_seam_rejects_reused_pack_review_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, candidate_path, locators, record_resolver, _, _ = _runner_inputs(tmp_path, monkeypatch)
    record_store = record_resolver.record_store
    provenance = record_store[frozen.REVIEW_RECORD_ID]["operator_provenance"]
    provenance["review_task_id"] = provenance["producer_task_id"]
    record_store[frozen.OWNER_DECISION_ID]["review_record_sha256"] = sha256_hex(
        canonical_bytes(record_store[frozen.REVIEW_RECORD_ID])
    )
    evaluation_time = datetime(2026, 7, 28, 12, tzinfo=UTC)
    run_id = "run_019fc96b-2ddc-7740-9d6c-425adf7fa3ae"
    prepare_locators = {key: value for key, value in locators.items() if key not in runner_module._FUTURE_PREPARE_KEYS}
    prepare_assurance_pack(
        config=config,
        candidate_path=candidate_path,
        evaluation_time=evaluation_time,
        run_id=run_id,
        record_locators=prepare_locators,
    )

    with pytest.raises(PackUnconsumable, match="pack review task provenance"):
        accept_assurance_pack(
            config=config,
            candidate_path=candidate_path,
            evaluation_time=evaluation_time,
            run_id=run_id,
            record_locators=locators,
        )


def test_acceptance_public_seam_rejects_foreign_body_r3_owner_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, candidate_path, locators, record_resolver, _, _ = _runner_inputs(tmp_path, monkeypatch)
    record_store = record_resolver.record_store
    record_store[frozen.OWNER_DECISION_ID]["authority_grant_id"] = "agr_00000000-0000-7000-8000-0000000000ff"
    evaluation_time = datetime(2026, 7, 28, 12, tzinfo=UTC)
    run_id = "run_019fc96b-2ddc-7740-9d6c-425adf7fa3af"
    prepare_locators = {key: value for key, value in locators.items() if key not in runner_module._FUTURE_PREPARE_KEYS}
    prepare_assurance_pack(
        config=config,
        candidate_path=candidate_path,
        evaluation_time=evaluation_time,
        run_id=run_id,
        record_locators=prepare_locators,
    )

    with pytest.raises(PackUnconsumable, match="owner acceptance authority grant identity is foreign"):
        accept_assurance_pack(
            config=config,
            candidate_path=candidate_path,
            evaluation_time=evaluation_time,
            run_id=run_id,
            record_locators=locators,
        )


def test_changed_retry_conflicts_without_mutating_immutable_preparation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, candidate_path, locators, _, _, _ = _runner_inputs(tmp_path, monkeypatch)
    prepare_locators = {key: value for key, value in locators.items() if key not in runner_module._FUTURE_PREPARE_KEYS}
    prepared = prepare_assurance_pack(
        config=config,
        candidate_path=candidate_path,
        evaluation_time=datetime(2026, 7, 28, 12, tzinfo=UTC),
        run_id="run_019fc96b-2ddc-7740-9d6c-425adf7fa3ac",
        record_locators=prepare_locators,
    )
    before = prepared.evidence_path.read_bytes()
    with pytest.raises(PackUnconsumable, match="idempotency identity conflicts"):
        runner_module._immutable_write(prepared.evidence_path, {"changed": True})
    assert prepared.evidence_path.read_bytes() == before


def test_interrupted_publication_has_no_final_artifact_and_retries_are_write_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "runtime" / "preparation.json"
    value = {"evidence": {"state": "prepared"}}

    def interrupt(temporary: Path) -> None:
        assert temporary.exists()
        assert temporary.parent == path.parent
        assert not path.exists()
        raise RuntimeError("injected publication interruption")

    monkeypatch.setattr(runner_module, "_after_immutable_temp_fsync", interrupt, raising=False)
    with pytest.raises(RuntimeError, match="injected publication interruption"):
        runner_module._immutable_write(path, value)
    assert not path.exists()
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))

    monkeypatch.setattr(runner_module, "_after_immutable_temp_fsync", lambda _temporary: None, raising=False)
    runner_module._immutable_write(path, value)
    published = path.read_bytes()
    assert published == canonical_bytes(value)

    runner_module._immutable_write(path, value)
    assert path.read_bytes() == published
    with pytest.raises(PackUnconsumable, match="idempotency identity conflicts"):
        runner_module._immutable_write(path, {"changed": True})
    assert path.read_bytes() == published


@pytest.mark.parametrize("failure", ("foreign", "expired", "revoked", "integrity"))
def test_replay_backed_policy_rejects_wrong_expired_revoked_or_corrupt_grants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    binding, pack, records = _policy_inputs(tmp_path, monkeypatch, failure)
    with pytest.raises(PackUnconsumable, match="replay-backed"):
        runner_module._policy_and_requirement(
            binding,
            binding.store_identity,
            records,
            pack,
            datetime(2026, 7, 28, 12, tzinfo=UTC),
        )
    assert list((tmp_path / "control").iterdir()) == []


@pytest.mark.parametrize(
    "dimension",
    ("same_session", "same_context_hash", "same_model_family", "producer_conclusions_visible"),
)
def test_relationship_facts_recompute_grade_from_concrete_provenance(dimension: str) -> None:
    relationship_record = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": frozen.SCOPE_RELATIONSHIP_ID,
        "relationship_context": "requirement_scope_review",
        "subject_actor_id": frozen.ACT_SCOPE_REVIEWER,
        "object_actor_id": frozen.ACT_PRODUCER,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-01T00:00:00Z",
        "expires_at": "2026-12-31T00:00:00Z",
    }
    relationship = ExternalRecordResolution(
        "producer_relationship_evidence",
        frozen.SCOPE_RELATIONSHIP_ID,
        1,
        sha256_hex(canonical_bytes(relationship_record)),
        relationship_record,
    )
    facts = _facts_for(
        relationship=relationship,
        subject={
            "subject_kind": "assurance_requirement",
            "subject_id": frozen.ASSURANCE_REQUIREMENT_ID,
            "subject_revision": 1,
            "subject_sha256": "d" * 64,
        },
        reviewer=frozen.ACT_SCOPE_REVIEWER,
        producer=frozen.ACT_PRODUCER,
        scope="requirement_scope",
        reviewed_at="2026-07-28T08:40:00Z",
    )
    body = deepcopy(facts.record)
    if dimension == "same_session":
        body["reviewer"]["session_id"] = body["producer"]["session_id"]
    elif dimension == "same_context_hash":
        body["reviewer"]["context_hash"] = body["producer"]["context_hash"]
    elif dimension == "same_model_family":
        body["reviewer"]["model_family"] = body["producer"]["model_family"]
    else:
        body["producer_conclusions_visibility"] = "visible_to_reviewer"
    changed = _FactsResolution(facts.record_id, 1, sha256_hex(canonical_bytes(body)), body)
    with pytest.raises(PackUnconsumable, match="comparisons are not independently derived"):
        runner_module._check_fact(
            changed,
            relationship,
            relationship_scope="requirement_scope",
            expected_subject=body["reviewed_subject"],
            expected_reviewer=frozen.ACT_SCOPE_REVIEWER,
            expected_producer=frozen.ACT_PRODUCER,
            evaluation_time=datetime(2026, 7, 28, 12, tzinfo=UTC),
        )


def test_relationship_facts_fail_closed_on_self_attestation() -> None:
    relationship_record = {
        "record_type": "producer_relationship_evidence",
        "relationship_record_id": frozen.SCOPE_RELATIONSHIP_ID,
        "relationship_context": "requirement_scope_review",
        "subject_actor_id": frozen.ACT_PRODUCER,
        "object_actor_id": frozen.ACT_PRODUCER,
        "grade": "I2",
        "status": "active",
        "effective_at": "2026-07-01T00:00:00Z",
        "expires_at": "2026-12-31T00:00:00Z",
    }
    relationship = ExternalRecordResolution(
        "producer_relationship_evidence",
        frozen.SCOPE_RELATIONSHIP_ID,
        1,
        sha256_hex(canonical_bytes(relationship_record)),
        relationship_record,
    )
    facts = _facts_for(
        relationship=relationship,
        subject={
            "subject_kind": "assurance_requirement",
            "subject_id": frozen.ASSURANCE_REQUIREMENT_ID,
            "subject_revision": 1,
            "subject_sha256": "d" * 64,
        },
        reviewer=frozen.ACT_PRODUCER,
        producer=frozen.ACT_PRODUCER,
        scope="requirement_scope",
        reviewed_at="2026-07-28T08:40:00Z",
    )
    with pytest.raises(PackUnconsumable, match="protected relationship/subject"):
        runner_module._check_fact(
            facts,
            relationship,
            relationship_scope="requirement_scope",
            expected_subject=facts.record["reviewed_subject"],
            expected_reviewer=frozen.ACT_PRODUCER,
            expected_producer=frozen.ACT_PRODUCER,
            evaluation_time=datetime(2026, 7, 28, 12, tzinfo=UTC),
        )


def test_current_reference_resolution_fails_on_missing_stale_and_ambiguous_inputs() -> None:
    contract = frozen._load_yaml(frozen.CONTRACT_PATH)
    pack = frozen._proposed_pack(contract)
    reader = _GitObjectReader(REPOSITORY_ROOT)
    snapshot = runner_module.GitCurrentReferenceResolver(reader).resolve(contract)
    with pytest.raises(PackUnconsumable, match="does not resolve"):
        _revalidate_references(pack, {})
    stale = deepcopy(snapshot)
    stale[next(iter(stale))]["canonical_sha256"] = "e" * 64
    with pytest.raises(PackUnconsumable, match="identity drifted"):
        _revalidate_references(pack, stale)
    ambiguous = deepcopy(contract)
    ambiguous["required_pack_contract"]["references"]["exact_reference_rows"].append(
        deepcopy(ambiguous["required_pack_contract"]["references"]["exact_reference_rows"][0])
    )
    with pytest.raises(PackUnconsumable, match="duplicate"):
        runner_module.GitCurrentReferenceResolver(reader).resolve(ambiguous)


def test_public_locator_and_time_inputs_fail_closed_before_any_store_mutation(tmp_path: Path) -> None:
    separate = runner_module._normalise_locators(
        {
            "requirement_scope_relationship": SemanticRecordLocator(
                "producer_relationship_evidence", frozen.SCOPE_RELATIONSHIP_ID
            ),
            "pack_review_relationship": SemanticRecordLocator(
                "producer_relationship_evidence", frozen.REVIEW_RELATIONSHIP_ID
            ),
        }
    )
    assert separate["requirement_scope_relationship"].record_id != separate["pack_review_relationship"].record_id
    with pytest.raises(PackUnconsumable, match="class mismatch"):
        runner_module._normalise_locators(
            {"accepted_assurance_requirement": SemanticRecordLocator("canonical_actor", frozen.ACT_OWNER)}
        )
    with pytest.raises(PackUnconsumable, match="RFC 3339"):
        runner_module._parse_time("not-a-date", "evaluation_time")
    assert not list(tmp_path.iterdir())


def test_cli_requires_bound_authority_inputs_and_exposes_both_phases() -> None:
    help_text = cli._parser().format_help()
    assert "assurance-pack" in help_text
    with pytest.raises(SystemExit):
        cli._parser().parse_args(["assurance-pack", "run"])
    parsed = cli._parser().parse_args(
        [
            "assurance-pack",
            "run",
            "--config",
            "binding.yaml",
            "--candidate",
            PACK_PATH,
            "--evaluation-time",
            "2026-08-03T12:00:00Z",
            "--run-id",
            "run_019fc96b-2ddc-7740-9d6c-425adf7fa3ab",
            "--phase",
            "prepare",
            "--record-locator",
            "accepted_assurance_requirement=accepted_assurance_requirement:ard_019fc96b-2ddc-7740-9d6c-425adf7fa3ab",
        ]
    )
    assert parsed.phase == "prepare"
    facts = cli._parser().parse_args(
        [
            "assurance-pack",
            "publish-relationship-facts",
            "--config",
            "binding.yaml",
            "--facts",
            "relationship-facts.json",
        ]
    )
    assert facts.assurance_pack_action == "publish-relationship-facts"


def test_prepare_public_seam_rejects_without_future_review_or_owner_records(
    tmp_path: Path,
) -> None:
    """Prepare must be a real public phase, not a test-only loader shortcut."""

    with pytest.raises(PackUnconsumable, match="future pack review and owner acceptance records are not used"):
        prepare_assurance_pack(
            config=AssurancePackRunnerConfig(
                binding=object(),  # type: ignore[arg-type]
                repository_root=tmp_path,
            ),
            candidate_path=tmp_path / ".research-system" / "packs" / "tdl-private-assurance.yaml",
            evaluation_time=datetime(2026, 8, 3, 12, tzinfo=UTC),
            run_id="run_019fc96b-2ddc-7740-9d6c-425adf7fa3ab",
            record_locators={
                "independent_pack_review": SemanticRecordLocator(
                    "independent_pack_review", "arv_019fc96b-2ddc-7740-9d6c-425adf7fa3ab"
                )
            },
        )
