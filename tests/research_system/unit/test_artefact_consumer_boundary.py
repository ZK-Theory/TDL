from __future__ import annotations

import ast
from pathlib import Path

from research_system.artefacts.authority import (
    AcceptedContractSubject,
    ArtefactAuthorityContractLoader,
    ContractIdentityError,
)
from tests.research_system.factories import REPO_ROOT


SUBJECT = AcceptedContractSubject(
    manifest_git_blob="7af3af9fbec1e5a1427162885eaeb6a82cbfca7b",
    manifest_sha256="b32821b6487a2d2a9941966a01dca1bdf62c3d3e57255f4c8f6933282a197ad1",
)


def _direct_artefact_accesses() -> set[tuple[str, str, str]]:
    found: set[tuple[str, str, str]] = set()
    for path in sorted((REPO_ROOT / "research_system").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr not in {"read", "write"}
            ):
                continue
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "artefact":
                owners: list[str] = []
                current: ast.AST = node
                while current in parents:
                    current = parents[current]
                    if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        owners.append(current.name)
                found.add(
                    (
                        path.relative_to(REPO_ROOT).as_posix(),
                        ".".join(reversed(owners)),
                        node.func.attr,
                    )
                )
    return found


def _fixed_consumer_calls() -> set[tuple[str, str, str, str]]:
    found: set[tuple[str, str, str, str]] = set()
    for path in sorted((REPO_ROOT / "research_system").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {
                "resolve_for_result",
                "resolve_for_review",
                "resolve_for_manuscript",
                "resolve_for_claim",
                "resolve_sensitive_sidecar",
            }:
                continue
            consumer = next(
                (
                    keyword.value.value
                    for keyword in node.keywords
                    if keyword.arg == "consumer_id"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ),
                "",
            )
            owners: list[str] = []
            current: ast.AST = node
            while current in parents:
                current = parents[current]
                if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    owners.append(current.name)
            found.add(
                (
                    path.relative_to(REPO_ROOT).as_posix(),
                    ".".join(reversed(owners)),
                    node.func.attr,
                    consumer,
                )
            )
    return found


def test_first_party_artefact_accesses_are_exactly_classified():
    assert _direct_artefact_accesses() == {
        (
            "research_system/artefacts/use_resolver.py",
            "ArtefactUseResolver._resolve",
            "read",
        ),
        (
            "research_system/command/service.py",
            "CommandService._ensure_artefact_materialized",
            "read",
        ),
        (
            "research_system/command/service.py",
            "CommandService._ensure_artefact_materialized",
            "write",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "prepare_session_brief",
            "write",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "_evidence_revision_history",
            "read",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "record_session_evidence",
            "write",
        ),
    }


def test_migrated_canonical_consumers_use_fixed_policy_methods_and_purposes():
    assert {
        (
            "research_system/evals/release_publication.py",
            "StoredReleasePublicationEvidence._resolve",
            "resolve_for_result",
            "release_publication",
        ),
        (
            "research_system/session_exchange/exchange.py",
            "record_session_evidence",
            "resolve_for_review",
            "rm04_followup_review",
        ),
    }.issubset(_fixed_consumer_calls())


def test_contract_loader_rejects_wrong_independent_manifest_subject():
    wrong = AcceptedContractSubject(manifest_git_blob="0" * 40, manifest_sha256="0" * 64)

    try:
        ArtefactAuthorityContractLoader(wrong).load()
    except ContractIdentityError as exc:
        assert "independently accepted subject" in str(exc)
    else:
        raise AssertionError("wrong accepted manifest subject was consumed")


def test_contract_loader_materialization_is_exact_and_catalogue_complete():
    contract = ArtefactAuthorityContractLoader(SUBJECT).load()

    assert tuple(contract.predicates_by_kind) == (
        "result_evidence",
        "review_evidence",
        "manuscript_evidence",
        "claim_evidence",
        "sensitive_sidecar",
    )
    assert contract.interface["public_resolver"]["replay_state_root"] == "streams"
    assert contract.interface["public_resolver"]["failure_contract"]["side_effects"] == "none"
    assert Path(REPO_ROOT / ".research-system/contracts/artefact-authority-v1/identity-manifest.yaml").is_file()
