"""06s Phase 1: public SOURCE registration and its decisive failure cases."""

from pathlib import Path
import subprocess
import json
import shutil
from datetime import UTC, datetime
from types import SimpleNamespace
from dataclasses import replace
from copy import deepcopy
import os

import pytest

from research_system.discovery.spec_source_git import resolve_source
from research_system.errors import ConfigurationError, ConflictError, IntegrityError, SchemaError
from research_system import cli
from research_system.canonical import canonical_bytes
from research_system.config import SpecOperatorConfig
from research_system.discovery.spec import SpecCoordinator
from research_system.discovery.spec_source import source_ids, read_document
from research_system.discovery.spec_source import (
    DOCUMENT_KIND,
    registration_ref,
    validate_document,
    validate_source_refs,
    source_ref,
)
from research_system.schema_registry import runtime_schema_registry
from research_system.ids import new_id
from research_system.store.binding_service import load_verified_binding_context
from tests.research_system.factories import ACTORS, PROJECT_ID, REPO_ROOT, ControlPlaneHarness, activate_lifecycle_grant
from tests.research_system.integration.test_current_binding import _bound_fixture
from tests.research_system.integration.test_artefact_authority_commands import artefact_manifest
from tests.research_system.integration.test_wp6_6_discovery_runtime import _genesis, CATALOGUE_STREAM_ID


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def source_repo(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "SOURCE fixture")
    git(root, "config", "user.email", "source@example.invalid")
    git(root, "config", "core.autocrlf", "false")
    (root / "evidence.txt").write_bytes(b"exact source\r\n")
    git(root, "add", "evidence.txt")
    git(root, "commit", "-m", "source fixture")
    git(root, "tag", "light")
    git(root, "tag", "-a", "annotated", "-m", "annotated source")
    return root


def test_git_exact_heads_tags_oid_and_subpath(source_repo):
    oid = git(source_repo, "rev-parse", "HEAD")
    for locator, kind in (("main", "head"), ("light", "tag"), ("annotated", "tag"), (oid, "commit")):
        result, raw = resolve_source(str(source_repo), locator)
        assert result["status"] == "resolved"
        assert result["commit_oid"] == oid
        assert result["resolved_kind"] == kind
        assert result["resolution_trace"] and raw
        assert "subpath" not in result
        assert "candidates" not in result and "failure_kind" not in result
    result, raw = resolve_source(str(source_repo), "annotated:evidence.txt")
    assert result["subpath"] == "evidence.txt"
    assert raw == b"exact source\r\n"


def test_remote_fetch_with_master_branch(source_repo, monkeypatch):
    from research_system.discovery import spec_source_git

    git(source_repo, "branch", "master")
    original = spec_source_git.run_git
    url = "https://source.example.invalid/repo.git"

    def local_transport(root, *args, **kwargs):
        # Exercise real Git init/fetch/peel; substitute only the network endpoint.
        args = tuple(str(source_repo) if value == url else value for value in args)
        if args[0] == "fetch":
            return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False, **kwargs)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(spec_source_git, "run_git", local_transport)
    for locator in ("master:evidence.txt", "light:evidence.txt"):
        result, raw = resolve_source(url, locator)
        assert result["status"] == "resolved"
        assert raw == b"exact source\r\n"


def test_source_registration_holds_writer_lock_through_rejection(bound_source, source_repo, monkeypatch):
    from research_system.errors import ArsError
    from research_system.store.lock import CompositeWriterLock, WriterLockContentionError

    coordinator = bound_source.coordinator
    intent = source_intent(source_repo)
    artefact_id = source_ids(PROJECT_ID, intent)["artefact_id"]
    grant = activate_lifecycle_grant(
        bound_source.harness, subject_kind="artefact", subject_id=artefact_id, command_types=("RegisterArtefact",)
    )
    original_operator = coordinator.operator
    coordinator.operator = replace(original_operator, authority_grant_id=grant, operator_actor_id=ACTORS["actor-b"])
    stages = []

    def assert_competitor_blocked(stage):
        with pytest.raises(WriterLockContentionError):
            with CompositeWriterLock((coordinator.binding.control_root,), {"command_id": "competitor"}):
                pytest.fail("competing writer entered SOURCE publication transaction")
        stages.append(stage)

    original_write = coordinator.objects.write
    original_rollback = coordinator.objects.rollback_new_revision

    def write(kind, *args, **kwargs):
        if kind == DOCUMENT_KIND:
            assert_competitor_blocked("publish")
        return original_write(kind, *args, **kwargs)

    def rollback(kind, *args, **kwargs):
        if kind == DOCUMENT_KIND:
            assert_competitor_blocked("rollback")
        return original_rollback(kind, *args, **kwargs)

    monkeypatch.setattr(coordinator.objects, "write", write)
    monkeypatch.setattr(coordinator.objects, "rollback_new_revision", rollback)
    before = coordinator.ledger.snapshot()
    with pytest.raises(ArsError, match="SPEC effect rejected"):
        coordinator.advance(intent)
    assert coordinator.ledger.snapshot() == before
    assert stages == ["publish", "rollback"]
    assert not coordinator.objects.revision_exists(DOCUMENT_KIND, artefact_id, 1)
    coordinator.operator = replace(original_operator, authority_grant_id=grant)
    assert coordinator.advance(intent)["state"] == "prepared"
    read_document(artefact_id, objects=coordinator.objects, schemas=coordinator.schemas, ledger=coordinator.ledger)


def test_git_ambiguous_absent_unavailable_and_malformed(source_repo, tmp_path):
    git(source_repo, "tag", "main")
    result, raw = resolve_source(str(source_repo), "main")
    assert result["status"] == "ambiguous" and len(result["candidates"]) == 2
    assert raw is None and "commit_oid" not in result
    result, raw = resolve_source(str(source_repo), "missing")
    assert result["status"] == "absent" and raw is None
    assert result["resolution_trace"][-1] == "exhaustive: heads, tags and direct commit checked"
    result, raw = resolve_source(str(tmp_path / "unavailable"), "main")
    assert result["status"] == "unavailable" and result["failure_kind"] == "transport"
    assert raw is None
    for locator in ("", "main other", "main:../secret", "--upload-pack=bad", "main:a:b"):
        with pytest.raises(ConfigurationError):
            resolve_source(str(source_repo), locator)


def test_git_rejects_invalid_components_and_archive_transformations(source_repo):
    with pytest.raises(ConfigurationError):
        resolve_source(str(source_repo), "release.lock/v1")
    for attribute in ("evidence.txt export-ignore", "evidence.txt export-subst"):
        (source_repo / ".gitattributes").write_text(attribute + "\n")
        (source_repo / "evidence.txt").write_text("$Format:%H$\n")
        git(source_repo, "add", ".")
        git(source_repo, "commit", "-m", attribute)
        with pytest.raises(ConfigurationError, match="archive.*committed"):
            resolve_source(str(source_repo), "main")
        result, raw = resolve_source(str(source_repo), "main:evidence.txt")
        assert result["status"] == "resolved" and raw is not None


@pytest.fixture
def bound_source(tmp_path, monkeypatch):
    scratch = tmp_path / "bound"
    for relative in (
        ".research-system/evals/expected/w11-portfolio-discovery-v1.json",
        ".research-system/contracts/w11/w11-materialization-bootstrap-contract.yaml",
    ):
        target = scratch / "repo" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / relative, target)
    fixture = _bound_fixture(scratch)
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: fixture.foundation_path)
    context = load_verified_binding_context(
        foundation_path=fixture.foundation_path,
        repository_root=fixture.repository_root,
        expected_control_root=fixture.control_root,
        expected_project_id=PROJECT_ID,
        expected_store_identity=str(fixture.binding["store_identity"]),
    )
    config = {
        "schema_id": "ars://operations/spec-operator-config",
        "schema_version": "1.0.0",
        "control_root": str(fixture.control_root),
        "project_id": PROJECT_ID,
        "store_identity": str(fixture.binding["store_identity"]),
        "route_id": "SPEC-GATE6-RUN-V1",
        "operator_actor_id": ACTORS["actor-a"],
        "actor_session_id": "ses_01978abc-1002-7000-8000-000000001002",
        "authority_grant_id": new_id("authority_grant"),
    }
    operator = SpecOperatorConfig.from_raw(canonical_bytes(config))
    coordinator = SpecCoordinator(context, operator, clock=lambda: datetime(2026, 9, 10, tzinfo=UTC))
    service = coordinator.service
    harness = ControlPlaneHarness(
        service,
        coordinator.ledger,
        coordinator.objects,
        service.receipts,
        coordinator.schemas,
        fixture.control_root,
        coordinator.ledger,
        coordinator.objects,
        service.receipts,
        coordinator.resolver,
        service,
    )
    genesis_grant = activate_lifecycle_grant(
        harness,
        subject_kind="scope_definition",
        subject_id=CATALOGUE_STREAM_ID,
        command_types=("ImportAcceptedW11CatalogueGenesis",),
    )
    genesis = _genesis()
    genesis["authority_grant_id"] = genesis_grant
    assert coordinator._discovery().submit(genesis).status == "accepted"
    return SimpleNamespace(fixture=fixture, coordinator=coordinator, harness=harness, config=config)


def source_intent(source_repo):
    manifest = artefact_manifest()
    production = {
        key: manifest[key]
        for key in (
            "task_id",
            "dispatch_id",
            "attempt_id",
            "context_packet_id",
            "producer_profile",
            "code_commit",
            "branch_identity",
            "worktree_identity",
            "environment_fingerprint",
        )
    }
    production["accepted_scope"] = manifest["authority"]["accepted_scope"]
    return {
        "action": "observe_source",
        "source_key": "paper-code",
        "title": "Exact paper source",
        "repository_url": str(source_repo),
        "requested_locator": "annotated:evidence.txt",
        "production": production,
    }


def invoke_cli(bound, tmp_path, capsys, intent, verb, grant, actor=None):
    intent_path = tmp_path / "intent.json"
    intent_path.write_bytes(canonical_bytes(intent))
    config_path = tmp_path / "operator.json"
    config_path.write_bytes(
        canonical_bytes(
            {
                **bound.config,
                "authority_grant_id": grant,
                "operator_actor_id": actor or bound.config["operator_actor_id"],
            }
        )
    )
    args = ["discovery", "spec", verb, "--operator-config", str(config_path)]
    if verb == "advance":
        args += ["--action", intent["action"], "--input", str(intent_path)]
    assert cli.main(args) == 0
    return json.loads(capsys.readouterr().out)


def test_public_advance_status_registration_and_replay(bound_source, source_repo, tmp_path, capsys):
    bound = bound_source
    intent = source_intent(source_repo)
    ids = source_ids(PROJECT_ID, intent)
    register_grant = activate_lifecycle_grant(
        bound.harness, subject_kind="artefact", subject_id=ids["artefact_id"], command_types=("RegisterArtefact",)
    )
    scout_grant = activate_lifecycle_grant(
        bound.harness,
        subject_kind="scope_definition",
        subject_id=ids["observation_id"],
        command_types=("IngestScoutObservationBatch",),
    )
    initial = invoke_cli(bound, tmp_path, capsys, intent, "status", register_grant)
    assert initial["actions"] == []
    prepared = invoke_cli(bound, tmp_path, capsys, intent, "advance", register_grant)
    assert prepared["state"] == "prepared" and prepared["next_effect"] == "IngestScoutObservationBatch"
    before_wrong_grant = bound.coordinator.ledger.snapshot()
    assert (
        cli.main(
            [
                "discovery",
                "spec",
                "advance",
                "--operator-config",
                str(tmp_path / "operator.json"),
                "--action",
                "observe_source",
                "--input",
                str(tmp_path / "intent.json"),
            ]
        )
        == 1
    )
    capsys.readouterr()
    assert bound.coordinator.ledger.snapshot() == before_wrong_grant
    completed = invoke_cli(bound, tmp_path, capsys, intent, "advance", scout_grant)
    assert completed["state"] == "completed" and len(completed["effects"]) == 2
    ledger = bound.coordinator.ledger
    tail = ledger.snapshot().global_position
    retried = invoke_cli(bound, tmp_path, capsys, intent, "advance", scout_grant)
    assert retried["state"] == "completed" and ledger.snapshot().global_position == tail
    document, registration = read_document(
        ids["artefact_id"], objects=bound.coordinator.objects, schemas=bound.coordinator.schemas, ledger=ledger
    )
    assert document["source_bytes_base64"] == "ZXhhY3Qgc291cmNlDQo="
    assert document["causal_prefix"]["global_position"] < registration["global_position"]
    assert document["causal_prefix"]["raw_prefix_sha256"] == ledger.raw_prefix_sha256(
        document["causal_prefix"]["global_position"]
    )
    # A fresh process imports the public CLI and changes only its scratch foundation selection.
    code = (
        "import sys; from pathlib import Path; from research_system import cli; "
        "cli.canonical_foundation_path=lambda:Path(sys.argv[1]); "
        "raise SystemExit(cli.main(sys.argv[2:]))"
    )
    result = subprocess.run(
        [
            __import__("sys").executable,
            "-B",
            "-c",
            code,
            str(bound.fixture.foundation_path),
            "discovery",
            "spec",
            "status",
            "--operator-config",
            str(tmp_path / "operator.json"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    replayed = json.loads(result.stdout)["actions"][0]
    assert replayed["registration"] == completed["registration"] and replayed["state"] == "completed"


def test_correction_publication_failures_and_governed_backup(bound_source, source_repo, tmp_path, capsys, monkeypatch):
    from research_system.artefacts.authority import ArtefactAuthorityContractLoader
    from research_system.artefacts.runtime import ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT
    from research_system.artefacts.use_resolver import predicate_reference
    from research_system.command.service import CommandService
    from research_system.operations.backups import BackupMaterializer, BackupArtefactInput
    from research_system.canonical import sha256_hex
    from tests.research_system.integration.test_artefact_authority_commands import command
    from tests.research_system.integration.test_wp64_create_backup import _registry

    bound = bound_source
    coordinator = bound.coordinator
    intent = source_intent(source_repo)
    ids = source_ids(PROJECT_ID, intent)
    grant = activate_lifecycle_grant(
        bound.harness, subject_kind="artefact", subject_id=ids["artefact_id"], command_types=("RegisterArtefact",)
    )
    # A failed immutable publication never reaches authoritative AR.
    original_write = type(coordinator.objects).write

    def fail_source(self, kind, *args, **kwargs):
        if kind == DOCUMENT_KIND:
            raise OSError("injected source publication failure")
        return original_write(self, kind, *args, **kwargs)

    before = coordinator.ledger.snapshot()
    with monkeypatch.context() as failure:
        failure.setattr(type(coordinator.objects), "write", fail_source)
        with pytest.raises(OSError, match="injected source publication"):
            invoke_cli(bound, tmp_path, capsys, intent, "advance", grant)
    assert coordinator.ledger.snapshot() == before
    assert not coordinator.objects.revision_exists("artefact", ids["artefact_id"], 1)
    assert not coordinator.objects.revision_exists(DOCUMENT_KIND, ids["artefact_id"], 1)
    invoke_cli(bound, tmp_path, capsys, intent, "advance", grant)
    prior_document, prior_event = read_document(
        ids["artefact_id"], objects=coordinator.objects, schemas=coordinator.schemas, ledger=coordinator.ledger
    )
    prior_bytes = canonical_bytes(prior_document)
    forged = deepcopy(prior_document)
    forged["causal_prefix"]["raw_prefix_sha256"] = "0" * 64
    with pytest.raises(IntegrityError, match="causal prefix"):
        validate_document(forged, schemas=coordinator.schemas, ledger=coordinator.ledger, registration=prior_event)
    forged_ref = source_ref(prior_event)
    forged_ref["content_hash"] = "0" * 64
    with pytest.raises(IntegrityError, match="earlier exact registration"):
        validate_source_refs(
            {"raw_source_refs": [forged_ref]},
            coordinator.ledger.snapshot().events,
            before_position=coordinator.ledger.snapshot().global_position + 1,
        )
    correction = {
        **intent,
        "action": "correct_spec_01_source",
        "source_key": "paper-source-correction",
        "corrects_artefact_id": ids["artefact_id"],
        "correction_reason": "Append the exact corrected source without rewriting prior evidence.",
    }
    missing = {**correction, "corrects_artefact_id": new_id("artefact")}
    before = coordinator.ledger.snapshot()
    with pytest.raises(IntegrityError, match="prior artefact registration"):
        coordinator.advance(missing)
    assert coordinator.ledger.snapshot() == before
    correction_id = source_ids(PROJECT_ID, correction)["artefact_id"]
    register = activate_lifecycle_grant(
        bound.harness, subject_kind="artefact", subject_id=correction_id, command_types=("RegisterArtefact",)
    )
    prepared = invoke_cli(bound, tmp_path, capsys, correction, "advance", register)
    assert prepared["state"] == "prepared" and prepared["next_effect"] == "RecordScientificReview"
    corrected_document, correction_event = read_document(
        correction_id, objects=coordinator.objects, schemas=coordinator.schemas, ledger=coordinator.ledger
    )
    assert corrected_document["schema_version"] == "2.0.0"
    wrong_action = deepcopy(corrected_document)
    wrong_action["intent"] = intent
    with pytest.raises(SchemaError):
        coordinator.schemas.validate(corrected_document["schema_id"], wrong_action, schema_version="2.0.0")
    assert corrected_document["prior_evidence"] == registration_ref(prior_event)
    assert corrected_document["causal_prefix"]["global_position"] < correction_event["global_position"]
    assert canonical_bytes(coordinator.objects.read(DOCUMENT_KIND, ids["artefact_id"], 1)) == prior_bytes
    reviewer = ACTORS["actor-b"]
    review_grant = activate_lifecycle_grant(
        bound.harness,
        subject_kind="artefact",
        subject_id=correction_id,
        actor_id=reviewer,
        command_types=("RecordScientificReview",),
        grant_id=new_id("authority_grant"),
    )
    review_id, evidence_id = new_id("review"), new_id("assurance_record")
    evidence = {"review_id": review_id, "evidence_refs": [evidence_id]}
    coordinator.service.governing_evidence_resolver.publish(
        evidence_id,
        {
            "schema_id": "ars://evidence/governing-scientific-review",
            "schema_version": "1.0.0",
            "project_id": PROJECT_ID,
            "review_id": review_id,
            "subject_sha256": prepared["registration"]["content_sha256"],
            "reviewer_actor_id": reviewer,
            "eligible": True,
            "related": False,
            "independence_grade": "I1",
            "status": "active",
        },
    )
    reviewed = invoke_cli(
        bound, tmp_path, capsys, {**correction, "evidence": evidence}, "advance", review_grant, actor=reviewer
    )
    assert reviewed["state"] == "prepared" and reviewed["next_effect"] == "SetArtefactUseAuthority"
    use_grant = activate_lifecycle_grant(
        bound.harness,
        subject_kind="artefact",
        subject_id=correction_id,
        command_types=("SetArtefactUseAuthority",),
        grant_id=new_id("authority_grant"),
    )
    predicate, predicate_hash = (
        ArtefactAuthorityContractLoader(ACCEPTED_ARTEFACT_AUTHORITY_SUBJECT).load().predicate_for("result_evidence")
    )
    use_evidence = {
        "consumer_predicate": predicate_reference(
            predicate["predicate_id"], predicate["predicate_version"], predicate_hash
        ),
        "evidence_refs": [review_id, evidence_id],
    }
    accepted = invoke_cli(bound, tmp_path, capsys, {**correction, "evidence": use_evidence}, "advance", use_grant)
    assert accepted["state"] == "completed" and len(accepted["effects"]) == 3
    # Existing governed backup admission must include the new object family.
    backup_id = new_id("command")
    backup_grant = activate_lifecycle_grant(
        bound.harness,
        subject_kind="project_store",
        subject_id=PROJECT_ID,
        command_types=("CreateBackup",),
        grant_id=new_id("authority_grant"),
    )
    destination = tmp_path / "source-backup"
    registry = replace(
        _registry(tmp_path, coordinator.binding, destination, command_id=backup_id),
        verifier_authority_bindings=((ACTORS["actor-a"], backup_grant),),
    )
    manifest = correction_event["payload"]["manifest"]
    source_path = coordinator.binding.control_root / manifest["relative_path"]
    now = coordinator.clock().isoformat().replace("+00:00", "Z")
    materializer = BackupMaterializer(
        command_id=backup_id,
        source_root=coordinator.binding.control_root,
        destination_root=destination,
        stage_root=registry.staging_root,
        receipt_id=new_id("backup_receipt"),
        receipt_revision=1,
        registry=registry,
        artefacts=(
            BackupArtefactInput(
                correction_id, source_path, manifest["content_sha256"], "available", ("source-registration",), now
            ),
        ),
        verified_at=now,
        verified_by_actor_id=ACTORS["actor-a"],
        verification_authority_grant_id=backup_grant,
        approved_witness=coordinator.binding.origin_witness,
        approved_witness_path=coordinator.binding.origin_witness_path,
        schema_registry=coordinator.schemas,
    )
    snapshot = coordinator.ledger.snapshot()
    payload = materializer.derive_event_payload(
        snapshot_id="source-phase1",
        destination_class="test-local-control-copy",
        schema_versions=["spec-source-observation@1.0.0", "spec-01-source-correction@2.0.0"],
        tool_versions=["ars-phase1"],
        encryption_class="test-owner-approved",
        redaction_class="test-owner-approved",
        ledger_snapshot=snapshot,
    )
    backup_command = command(
        command_id=backup_id,
        command_type="CreateBackup",
        actor_id=ACTORS["actor-a"],
        authority_grant_id=backup_grant,
        target_stream_id=PROJECT_ID,
        expected_stream_version=snapshot.stream_versions.get(PROJECT_ID, 0),
        payload=payload,
    )
    backup_command["submitted_at"] = now
    backup_service = CommandService(
        coordinator.binding.control_root,
        coordinator.ledger,
        coordinator.objects,
        coordinator.service.receipts,
        coordinator.schemas,
        authority_resolver=coordinator.resolver,
        clock=coordinator.clock,
        backup_materializer=materializer,
    )
    receipt = backup_service.submit(backup_command)
    assert receipt.status == "accepted", receipt
    assert sha256_hex((destination / manifest["relative_path"]).read_bytes()) == manifest["content_sha256"]
    assert coordinator.ledger.snapshot().global_position == snapshot.global_position + 1
    assert backup_service.submit(backup_command).status in {"accepted", "replayed"}
    assert coordinator.ledger.snapshot().global_position == snapshot.global_position + 1
    # The restored-root repair must still reject different copied manifest bytes.
    candidate_manifest_path = destination / "manifests/store-identity.json"
    candidate_manifest_raw = candidate_manifest_path.read_bytes()
    candidate_manifest_path.write_bytes(candidate_manifest_raw + b"\n")
    with pytest.raises(ConflictError, match="file content differs"):
        backup_service.submit(backup_command)
    assert coordinator.ledger.snapshot().global_position == snapshot.global_position + 1


def test_source_outcome_contract_and_historical_correction_bytes(source_repo):
    schemas = runtime_schema_registry(REPO_ROOT / ".research-system/schemas")
    schema = "ars://portfolio/git-reference-resolution"
    resolved, _ = resolve_source(str(source_repo), "main")
    schemas.validate(schema, resolved)
    for name, value in (("candidates", []), ("failure_kind", "transport"), ("unexpected", True)):
        with pytest.raises(SchemaError):
            schemas.validate(schema, {**resolved, name: value})
    base = {key: resolved[key] for key in ("repository_url", "requested_locator", "resolution_trace")}
    for value in (
        {**base, "status": "ambiguous", "candidates": []},
        {**base, "status": "unavailable", "failure_kind": "absent"},
        {**base, "status": "absent"},
    ):
        with pytest.raises(SchemaError):
            schemas.validate(schema, value)
    historical = REPO_ROOT / ".research-system/schemas/contracts/wp6-6/spec-01-source-correction-v1.schema.json"
    assert historical.read_bytes() == subprocess.check_output(
        ["git", "show", "cce2cb731182e00e0a7f512e775bf78f8cbb6460"], cwd=REPO_ROOT
    )
    assert (
        schemas.resolve_identity("ars://portfolio/spec-01-source-correction", "1.0.0").raw_bytes
        == historical.read_bytes()
    )


def test_source_failure_classification_and_action_contract(source_repo, monkeypatch):
    from research_system.discovery import spec_source_git
    from research_system.discovery.spec import ACTION_EFFECTS

    assert ACTION_EFFECTS == {
        "observe_source": ("RegisterArtefact", "IngestScoutObservationBatch"),
        "correct_spec_01_source": ("RegisterArtefact", "RecordScientificReview", "SetArtefactUseAuthority"),
        "close_task": (
            "SubmitForReview",
            "RequestReview",
            "AssignReview",
            "StartReview",
            "RecordReviewVerdict",
            "SatisfyReview",
            "AcceptTask",
        ),
    }

    def timed_out(*args, **kwargs):
        raise ConfigurationError("Git validation unavailable") from subprocess.TimeoutExpired("git", 60)

    with monkeypatch.context() as timeout:
        timeout.setattr(spec_source_git, "run_git", timed_out)
        result, raw = resolve_source(str(source_repo), "main")
        assert result["status"] == "unavailable" and result["failure_kind"] == "timeout" and raw is None

    def denied(*args, **kwargs):
        return subprocess.CompletedProcess(args, 128, b"", b"fatal: Authentication failed")

    with monkeypatch.context() as auth:
        auth.setattr(spec_source_git, "run_git", denied)
        result, _ = resolve_source(str(source_repo), "main")
        assert result["status"] == "unavailable" and result["failure_kind"] == "auth"
    original = spec_source_git.run_git

    def failed_probe(root, *args, **kwargs):
        if args[0] == "cat-file":
            return subprocess.CompletedProcess(args, 128, b"", b"repository disappeared")
        return original(root, *args, **kwargs)

    with monkeypatch.context() as transport:
        transport.setattr(spec_source_git, "run_git", failed_probe)
        for locator in (git(source_repo, "rev-parse", "HEAD"), "main:missing"):
            result, _ = resolve_source(str(source_repo), locator)
            assert result["status"] == "unavailable" and result["failure_kind"] == "transport"


@pytest.mark.skipif(os.environ.get("ARS_SOURCE_NETWORK_PROOF") != "1", reason="explicit public Git acceptance probe")
def test_neurips2024_exact_public_registration(bound_source, tmp_path, capsys):
    intent = source_intent("https://github.com/berenslab/eff-ph.git")
    intent["requested_locator"] = "neurips2024"
    ids = source_ids(PROJECT_ID, intent)
    grant = activate_lifecycle_grant(
        bound_source.harness,
        subject_kind="artefact",
        subject_id=ids["artefact_id"],
        command_types=("RegisterArtefact",),
    )
    result = invoke_cli(bound_source, tmp_path, capsys, intent, "advance", grant)
    assert result["resolution"]["canonical_ref"] == "refs/tags/neurips2024"
    assert result["resolution"]["commit_oid"] == "145efcde673f1a1897eff250b77221d26c34c479"
    assert result["source_sha256"] == "3eea9174db28f4dd5bcf4e622709280f25fd6bfe0843ff1fc2e1d1559401f9df"
    document, _ = read_document(
        ids["artefact_id"],
        objects=bound_source.coordinator.objects,
        schemas=bound_source.coordinator.schemas,
        ledger=bound_source.coordinator.ledger,
    )
    assert document["source_size_bytes"] == 24145920
