from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from research_system.errors import ArsError
from research_system.canonical import canonical_bytes
from research_system.evals.executors.control_store import execute_s009, execute_s011
from research_system.evals.scenarios import FoundationPorts
from research_system.projection.grandfather import load_grandfather_decision
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
    (
        "research_system/command/service.py",
        "CommandService.submit",
        "self.ledger",
    ): "generic_and_guarded_command_producer",
    ("research_system/command/t2.py", "submit_t2", "service.ledger"): "t2_command_producer",
    (
        "research_system/store/ledger.py",
        "EventLedger._append_release_from_validated_submit",
        "self",
    ): "guarded_release_command_producer",
    (
        "research_system/store/ledger.py",
        "EventLedger._append_scoped_authority_from_validated_submit",
        "self",
    ): "guarded_scoped_authority_command_producer",
    ("research_system/evals/executors/control_store.py", "execute_s009", "ledger"): "commandless_evaluation_fixture",
    ("research_system/evals/executors/control_store.py", "execute_s011", "ledger"): "commandless_evaluation_fixture",
    (
        "research_system/evals/scenarios.py",
        "FoundationPorts.recover_writer",
        "ledger",
    ): "commandless_evaluation_fixture",
}
_PROTOCOL_VERSION = "G-RM-8-GRANDFATHER/1.0.0"
_DECISION_PATH = "research_system/projection/data/06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json"
_HISTORICAL_DECISION_PATH = (
    "docs/plans/agentic-research-system/implementation/06h-g-rm-8-grandfather-decision-3c75d3d-2026-08-09.json"
)
_PACKAGED_AUTHORITY_PATH = "research_system/projection/data/wp6_1_06h_grandfather_authority.yaml"
_INTEGRATED_PR229_MERGE = "a1c917f7e313d9636509795c525d12f97b695be3"
_PRODUCTION_CANDIDATE = "2f005f11754761ee81e56ef0f9da497ea2544feb"


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


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _git_is_ancestor(ancestor: str, descendant: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _validate_manifest_authority(document: dict) -> None:
    historical = document["historical_evidence"]
    decision_path = historical["decision_record"]
    assert document["accounted_base"] == _git_output("merge-base", "HEAD", "origin/main")
    assert document["integrated_pr229_merge"] == _INTEGRATED_PR229_MERGE
    assert document["production_candidate"] == _PRODUCTION_CANDIDATE
    assert historical["protocol_activation"] == _PROTOCOL_VERSION
    assert decision_path == _DECISION_PATH

    packaged_authority_file = REPO_ROOT / _PACKAGED_AUTHORITY_PATH
    packaged_authority_raw = packaged_authority_file.read_bytes()
    packaged_authority = yaml.safe_load(packaged_authority_raw)
    packaged_authority_committed = subprocess.run(
        ["git", "show", f"HEAD:{_PACKAGED_AUTHORITY_PATH}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert packaged_authority_raw == packaged_authority_committed
    assert packaged_authority["schema_id"] == document["schema_id"]
    assert packaged_authority["schema_version"] == document["schema_version"]
    assert packaged_authority["historical_evidence"] == historical

    decision_file = REPO_ROOT / decision_path
    decision = load_grandfather_decision(decision_file)
    raw = decision_file.read_bytes()
    historical_raw = (REPO_ROOT / _HISTORICAL_DECISION_PATH).read_bytes()
    committed = subprocess.run(
        ["git", "show", f"HEAD:{decision_path}"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout
    assert raw == historical_raw == committed == canonical_bytes(json.loads(raw)) + b"\n"
    assert historical["owner_protocol_decision"] == decision.sha256
    assert historical["selected_lineage"] == decision.candidate_lineage
    assert _git_is_ancestor(document["integrated_pr229_merge"], document["accounted_base"])
    assert _git_is_ancestor(historical["selected_lineage"], document["production_candidate"])
    assert _git_is_ancestor(document["production_candidate"], "HEAD")


def _append_sites_in_source(relative: str, source: str) -> set[tuple[str, str, str, str]]:
    found: set[tuple[str, str, str, str]] = set()
    stack: list[str] = []
    classes: list[str] = []
    aliases: list[set[str]] = [set()]
    append_aliases: list[dict[str, str]] = [{}]

    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            stack.append(node.name)
            classes.append(node.name)
            aliases.append(set(aliases[-1]))
            append_aliases.append(dict(append_aliases[-1]))
            self.generic_visit(node)
            append_aliases.pop()
            aliases.pop()
            classes.pop()
            stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            stack.append(node.name)
            aliases.append(set(aliases[-1]))
            append_aliases.append(dict(append_aliases[-1]))
            self.generic_visit(node)
            append_aliases.pop()
            aliases.pop()
            stack.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Assign(self, node: ast.Assign) -> None:
            source_receiver = ast.unparse(node.value)
            if "ledger" in source_receiver.lower() or source_receiver in aliases[-1]:
                aliases[-1].update(target.id for target in node.targets if isinstance(target, ast.Name))
            if isinstance(node.value, ast.Attribute) and node.value.attr == "append":
                receiver = ast.unparse(node.value.value)
                if "ledger" in receiver.lower() or receiver in aliases[-1]:
                    append_aliases[-1].update(
                        (target.id, receiver) for target in node.targets if isinstance(target, ast.Name)
                    )
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if (
                isinstance(node.target, ast.Name)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "append"
            ):
                receiver = ast.unparse(node.value.value)
                if "ledger" in receiver.lower() or receiver in aliases[-1]:
                    append_aliases[-1][node.target.id] = receiver
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "append":
                receiver = ast.unparse(node.func.value)
                proven_ledger_receiver = (
                    "ledger" in receiver.lower()
                    or receiver in aliases[-1]
                    or (receiver == "self" and classes and classes[-1] == "EventLedger")
                )
                if proven_ledger_receiver or receiver == "self":
                    site = (relative, ".".join(stack) if stack else "<module>", receiver)
                    found.add((*site, APPEND_SITE_CLASSIFICATIONS.get(site, "unclassified")))
            elif isinstance(node.func, ast.Name) and node.func.id in append_aliases[-1]:
                receiver = append_aliases[-1][node.func.id]
                site = (relative, ".".join(stack) if stack else "<module>", receiver)
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
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}


@pytest.mark.integration
def test_manifest_accounts_for_exact_runtime_bindings_and_append_sites() -> None:
    document = _manifest()
    authorities = document["accepted_authorities"]

    _validate_manifest_authority(document)
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


@pytest.mark.integration
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accounted_base", "1" * 40),
        ("integrated_pr229_merge", "2" * 40),
        ("production_candidate", "3" * 40),
        ("historical_evidence.protocol_activation", "G-RM-8-GRANDFATHER/9.9.9"),
        ("historical_evidence.decision_record", "docs/forged-decision.json"),
        ("historical_evidence.owner_protocol_decision", "4" * 64),
        ("historical_evidence.selected_lineage", "5" * 40),
    ],
)
def test_manifest_rejects_stale_or_forged_authority(field: str, value: str) -> None:
    document = deepcopy(_manifest())
    target = document
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value

    with pytest.raises(AssertionError):
        _validate_manifest_authority(document)


def test_manifest_binding_row_format_decodes_to_exact_lf_bytes() -> None:
    row_format = _manifest()["runtime_bindings"]["canonical_row_format"]

    assert row_format.encode("utf-8") == ("|".join(_BINDING_FIELDS) + "\n").encode("utf-8")


def test_manifest_controls_resolve_to_real_test_nodes() -> None:
    for node_id in _manifest()["controls"]:
        path_text, function = node_id.split("::", 1)
        path = REPO_ROOT / path_text
        assert path.is_file(), node_id
        assert function in _test_functions(path), node_id


def test_manifest_accounts_for_every_append_closure_smoke_control() -> None:
    path_text = "tests/research_system/smoke/test_wp6_1_06h_append_path_closure.py"
    listed = {node_id for node_id in _manifest()["controls"] if node_id.startswith(f"{path_text}::")}
    defined = {f"{path_text}::{function}" for function in _test_functions(REPO_ROOT / path_text)}

    assert listed == defined


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


def test_bound_method_alias_append_fails_reconciliation() -> None:
    expected = _manifest_append_sites(_manifest())
    alias_site = _append_sites_in_source(
        "research_system/command/bound_alias.py",
        "def submit_alias(service):\n    emit = service.ledger.append\n    emit([])\n",
    )
    assert alias_site == {
        (
            "research_system/command/bound_alias.py",
            "submit_alias",
            "service.ledger",
            "unclassified",
        )
    }
    planted = _append_sites() | alias_site

    with pytest.raises(AssertionError, match="submit_alias"):
        _reconcile_append_sites(expected, planted)


def test_nested_ledger_alias_append_fails_reconciliation() -> None:
    observed = _append_sites_in_source(
        "research_system/command/nested_alias.py",
        "def outer(ledger):\n    writer = ledger\n    def inner():\n        writer.append([])\n",
    )

    assert observed == {
        (
            "research_system/command/nested_alias.py",
            "outer.inner",
            "writer",
            "unclassified",
        )
    }
    with pytest.raises(AssertionError, match="nested_alias"):
        _reconcile_append_sites(set(), observed)


def test_duplicate_class_method_append_sites_remain_distinct() -> None:
    observed = _append_sites_in_source(
        "research_system/command/duplicate_methods.py",
        "class First:\n"
        "    def emit(self):\n"
        "        self.ledger.append([])\n"
        "class Second:\n"
        "    def emit(self):\n"
        "        self.ledger.append([])\n",
    )

    assert observed == {
        (
            "research_system/command/duplicate_methods.py",
            "First.emit",
            "self.ledger",
            "unclassified",
        ),
        (
            "research_system/command/duplicate_methods.py",
            "Second.emit",
            "self.ledger",
            "unclassified",
        ),
    }


def test_event_ledger_guarded_self_append_sites_are_discovered() -> None:
    expected = {
        (
            "research_system/store/ledger.py",
            "EventLedger._append_release_from_validated_submit",
            "self",
            "guarded_release_command_producer",
        ),
        (
            "research_system/store/ledger.py",
            "EventLedger._append_scoped_authority_from_validated_submit",
            "self",
            "guarded_scoped_authority_command_producer",
        ),
    }

    observed = {row for row in _append_sites() if row[0] == "research_system/store/ledger.py"}

    assert observed == expected


def test_unproved_direct_self_append_receiver_fails_closed() -> None:
    observed = _append_sites_in_source(
        "research_system/command/unproved_writer.py",
        "class UnprovedWriter:\n    def emit(self):\n        self.append([])\n",
    )

    assert observed == {
        (
            "research_system/command/unproved_writer.py",
            "UnprovedWriter.emit",
            "self",
            "unclassified",
        )
    }
    with pytest.raises(AssertionError, match="unproved_writer"):
        _reconcile_append_sites(set(), observed)
