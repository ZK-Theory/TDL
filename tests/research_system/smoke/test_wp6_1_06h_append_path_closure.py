from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path
import subprocess

import pytest
import yaml

from research_system.errors import ArsError
from research_system.evals.executors.control_store import execute_s009, execute_s011
from research_system.evals.scenarios import FoundationPorts
from research_system.schema_registry import runtime_schema_registry
from research_system.store.ledger import EventLedger
from tests.research_system.factories import PROJECT_ID, REPO_ROOT, control_plane, create_task_command


MANIFEST_PATH = Path(__file__).with_name("wp6_1_06h_current_append_manifest.yaml")
SCHEMAS = REPO_ROOT / ".research-system" / "schemas"
_BINDING_FIELDS = (
    "schema_id",
    "schema_version",
    "command_type",
    "event_type",
    "producer_command_type",
    "policy_action_type",
)
APPEND_SITE_CLASSIFICATIONS = {
    (
        "research_system/authority.py",
        "initialize_authority_control_store",
        "ledger",
    ): "system_bootstrap_command_producer",
    ("research_system/command/service.py", "submit", "self.ledger"): "generic_and_guarded_command_producer",
    ("research_system/command/t2.py", "submit_t2", "service.ledger"): "t2_command_producer",
    ("research_system/evals/executors/control_store.py", "execute_s009", "ledger"): "commandless_evaluation_fixture",
    ("research_system/evals/executors/control_store.py", "execute_s011", "ledger"): "commandless_evaluation_fixture",
    ("research_system/evals/scenarios.py", "recover_writer", "ledger"): "commandless_evaluation_fixture",
}


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def _binding_digest(row_format: str) -> tuple[int, str]:
    expected_format = "|".join(_BINDING_FIELDS) + "\n"
    assert row_format.encode("utf-8") == expected_format.encode("utf-8")
    field_names = tuple(row_format[:-1].split("|"))
    terminator = row_format[-1].encode("utf-8")
    bindings = runtime_schema_registry(SCHEMAS).active_bindings()
    encoded = b"".join(
        b"|".join(str(getattr(binding, field_name) or "").encode("utf-8") for field_name in field_names) + terminator
        for binding in bindings
    )
    return len(bindings), sha256(encoded).hexdigest()


def _git_object(path: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _append_sites_in_source(relative: str, source: str) -> set[tuple[str, str, str, str]]:
    found: set[tuple[str, str, str, str]] = set()
    stack: list[str] = []
    aliases: list[set[str]] = [set()]

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            stack.append(node.name)
            aliases.append(set())
            self.generic_visit(node)
            aliases.pop()
            stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Assign(self, node: ast.Assign) -> None:
            source_receiver = ast.unparse(node.value)
            if "ledger" in source_receiver.lower() or source_receiver in aliases[-1]:
                aliases[-1].update(target.id for target in node.targets if isinstance(target, ast.Name))
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                receiver = ast.unparse(node.func.value)
                if "ledger" in receiver.lower() or receiver in aliases[-1]:
                    site = (relative, stack[-1] if stack else "<module>", receiver)
                    found.add((*site, APPEND_SITE_CLASSIFICATIONS.get(site, "unclassified")))
            self.generic_visit(node)

    Visitor().visit(ast.parse(source))
    return found


def _append_sites() -> set[tuple[str, str, str, str]]:
    found: set[tuple[str, str, str, str]] = set()
    for path in sorted((REPO_ROOT / "research_system").rglob("*.py")):
        relative = path.relative_to(REPO_ROOT).as_posix()
        found.update(_append_sites_in_source(relative, path.read_text(encoding="utf-8")))
    return found


def _manifest_append_sites(document: dict) -> set[tuple[str, str, str, str]]:
    return {(row["path"], row["symbol"], row["receiver"], row["classification"]) for row in document["append_sites"]}


def _reconcile_append_sites(
    expected: set[tuple[str, str, str, str]],
    observed: set[tuple[str, str, str, str]],
) -> None:
    missing = sorted(observed - expected)
    stale = sorted(expected - observed)
    assert not missing and not stale, f"unmanifested={missing}; stale={stale}"


def _test_functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_manifest_accounts_for_exact_runtime_bindings_and_append_sites() -> None:
    document = _manifest()
    authorities = document["accepted_authorities"]

    assert (
        _git_object(authorities["owner_source_catalogue"]["repository_path"])
        == (authorities["owner_source_catalogue"]["git_blob_id"])
    )
    assert _git_object(".research-system/schemas/core/commands") == authorities["command_schema_tree"]
    assert _git_object(".research-system/schemas/core/events") == authorities["event_schema_tree"]
    assert _binding_digest(document["runtime_bindings"]["canonical_row_format"]) == (
        document["runtime_bindings"]["count"],
        document["runtime_bindings"]["sha256"],
    )
    _reconcile_append_sites(_manifest_append_sites(document), _append_sites())


def test_manifest_binding_row_format_decodes_to_exact_lf_bytes() -> None:
    row_format = _manifest()["runtime_bindings"]["canonical_row_format"]

    assert row_format.encode("utf-8") == ("|".join(_BINDING_FIELDS) + "\n").encode("utf-8")


def test_manifest_controls_resolve_to_real_test_nodes() -> None:
    for node_id in _manifest()["controls"]:
        path_text, function = node_id.split("::", 1)
        path = REPO_ROOT / path_text
        assert path.is_file(), node_id
        assert function in _test_functions(path), node_id


def test_public_generic_append_uses_registered_schema_record(tmp_path: Path) -> None:
    harness = control_plane(tmp_path)
    command = create_task_command(
        "cmd_019fe500-0001-7000-8000-000000000001",
        "06h-current-public-path",
        "tsk_019fe500-0002-7000-8000-000000000002",
        {"title": "06h current append proof"},
    )

    receipt = harness.service.submit(command)
    event = tuple(harness.ledger.iter_events())[0]
    registered = harness.service.schemas.validate_active(
        command["schema_id"],
        command,
        schema_version=command["schema_version"],
    )

    assert receipt.status == "accepted"
    assert event["command_schema_id"] == registered.schema_id
    assert event["command_schema_version"] == registered.schema_version
    assert event["command_schema_sha256"] == registered.raw_bytes_sha256


@pytest.mark.parametrize(
    "schema_id",
    ["ars://core/event/TaskCreated", "ars://wp6-2/t2/event/CostGrantIssued"],
    ids=["generic", "t2"],
)
def test_runtime_ledger_rejects_missing_triple_for_generic_and_t2(
    tmp_path: Path,
    schema_id: str,
) -> None:
    ledger = EventLedger(
        tmp_path,
        project_id=PROJECT_ID,
        schemas=runtime_schema_registry(SCHEMAS),
    )

    with pytest.raises(ArsError, match="complete command schema identity"):
        ledger.append(
            [
                {
                    "event_type": schema_id.rsplit("/", 1)[-1],
                    "stream_id": "tsk_019fe500-0003-7000-8000-000000000003",
                    "schema_id": schema_id,
                }
            ]
        )

    assert tuple(ledger.iter_batches()) == ()


def test_commandless_fixture_classification_matches_public_append_behavior(tmp_path: Path, monkeypatch) -> None:
    observed: list[dict] = []
    real_append = EventLedger.append

    def record_append(ledger, events, *args, **kwargs):
        rows = [dict(event) for event in events]
        observed.extend(rows)
        return real_append(ledger, rows, *args, **kwargs)

    monkeypatch.setattr(EventLedger, "append", record_append)

    assert execute_s009("candidate", {})["checksum_match"] is True
    assert (
        execute_s011("candidate", {"action": {"windows": ["after-fsync"]}})["receipt_matches_committed_batch"] is True
    )
    assert FoundationPorts().recover_writer().replay_integrity == "pass"
    assert len(observed) == 3
    assert all(
        not {"command_schema_id", "command_schema_version", "command_schema_sha256"}.intersection(event)
        for event in observed
    )


def test_changed_append_site_classification_fails_reconciliation() -> None:
    expected = _manifest_append_sites(_manifest())
    observed = _append_sites()
    authority = next(row for row in observed if row[0] == "research_system/authority.py")
    changed = (authority[0], authority[1], authority[2], "commandless_system_bootstrap")

    with pytest.raises(AssertionError, match="commandless_system_bootstrap"):
        _reconcile_append_sites(expected, (observed - {authority}) | {changed})


def test_unmanifested_append_site_fails_reconciliation() -> None:
    expected = _manifest_append_sites(_manifest())
    planted = _append_sites() | {
        ("research_system/command/new_family.py", "submit_new_family", "service.ledger", "unclassified")
    }

    with pytest.raises(AssertionError, match="new_family"):
        _reconcile_append_sites(expected, planted)


def test_ledger_alias_append_fails_reconciliation() -> None:
    expected = _manifest_append_sites(_manifest())
    planted = _append_sites() | _append_sites_in_source(
        "research_system/command/aliased.py",
        "def submit_alias(ledger):\n    writer = ledger\n    writer.append([])\n",
    )

    with pytest.raises(AssertionError, match="submit_alias"):
        _reconcile_append_sites(expected, planted)
