# Research context: docs/plans/agentic-research-system/transition/w9/wp9-2-design-note.md (WP9.2-2; P-077, P-078)
# Purpose: store-free controls for the W9 route table, row assignment, accepted pins and reducer invariants.
"""Store-free W9 legacy controls (06v WP9.2; design note §§2.3, 3, 4, 5, 7.4, 9).

The expected sides here are independent of the code under test: the per-row tags are written out from design note §3,
the identities are the O-8, O-3 and envelope tests' own literals, and the catalogue is read from its accepted commit.
"""

from __future__ import annotations

import ast
import json
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from research_system.discovery.routes import (
    ARTEFACT_EVENT_TYPES,
    CONTEXT_EVENT_TYPES,
    CONTROL_EVENT_TYPES,
    shared_event_partition,
)
from research_system.errors import IntegrityError
from research_system.legacy import accepted_w9, routes
from research_system.legacy.commands import LEGACY_COMMAND_TYPES, is_legacy_projection_event
from research_system.legacy.replay import reducers
from research_system.schema_registry import _RUNTIME_BINDINGS, bundled_runtime_schema_registry
from tests.research_system.contracts.test_w9_acceptance_envelope import external_ref_id
from tests.research_system.contracts.test_w9_contract_materialization import O3_ACCEPTED
from tests.research_system.contracts.test_w9_expected_catalogue import O8_ACCEPTED

REPO_ROOT = Path(__file__).resolve().parents[3]
O8_COMMIT = "7979e85a075ab6a643a7b201ac4186b0b2090d74"
# The envelope's own pins (WP9.2-1 record §2; envelope test).
ENVELOPE = {
    "path": ".research-system/evals/expected/w9-catalogue-acceptance-envelope-v1.json",
    "commit": "69e9e059348baad153884f43b34ee6c52df63add",
    "blob": "9b28528c119ef45244b277ccd30855c68826e41f",
    "sha256": "c26f468c9cfa0195d82812f05faa4e6e663a3ceb9737d31f8f5f1bd190465999",
    "bytes": 11185,
}
# Design note §3, written out row by row.
EXPECTED_TAGS = {
    "LR-002": "catalogue_revision",
    **{f"LR-{n:03d}": "WP9.3" for n in range(3, 21)},
    "LR-021": "WP9.7",
    "LR-022": "WP9.7",
    "LR-023": "WP9.4",
    "LR-024": "WP9.7",
    "LR-025": "WP9.7",
    **{f"LR-{n:03d}": "WP9.4" for n in range(26, 36)},
    "LR-036": "WP9.6",
    "LR-037": "WP9.6",
    "LR-038": "WP9.6",
    "LR-039": "WP9.4",
    **{f"LR-{n:03d}": "WP9.4" for n in range(40, 56)},
    **{f"LR-{n:03d}": "WP9.6" for n in range(56, 61)},
    "LR-061": "WP9.7",
}


def _catalogue() -> dict[str, Any]:
    raw = subprocess.run(
        ["git", "show", f"{O8_COMMIT}:{accepted_w9.ACCEPTED['catalogue_path']}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout
    return json.loads(raw)


def _rows() -> dict[str, dict[str, Any]]:
    return {row["owner_row_id"]: row for row in _catalogue()["owner_contract_rows"]}


# --- Accepted identities ---------------------------------------------------------------------------------------------


def test_accepted_equals_the_independent_o8_o3_and_envelope_pins() -> None:
    accepted = accepted_w9.ACCEPTED
    assert accepted["accepted_commit"] == O8_ACCEPTED["main_commit"]
    for kind in ("catalogue", "annex"):
        pin = O8_ACCEPTED[kind]
        assert (accepted[f"{kind}_path"], accepted[f"{kind}_blob"], accepted[f"{kind}_sha256"]) == (
            pin["path"],
            pin["blob"],
            pin["sha256"],
        )
        assert accepted[f"{kind}_bytes"] == pin["bytes"]
    assert (
        accepted["bootstrap_path"],
        accepted["bootstrap_commit"],
        accepted["bootstrap_blob"],
        accepted["bootstrap_sha256"],
        accepted["bootstrap_bytes"],
    ) == (
        O3_ACCEPTED["path"],
        O3_ACCEPTED["main_commit"],
        O3_ACCEPTED["blob"],
        O3_ACCEPTED["sha256"],
        O3_ACCEPTED["bytes"],
    )
    assert (
        accepted["envelope_path"],
        accepted["envelope_commit"],
        accepted["envelope_blob"],
        accepted["envelope_sha256"],
        accepted["envelope_bytes"],
    ) == tuple(ENVELOPE.values())


def test_reserved_ids_derive_from_their_domain_strings() -> None:
    prefixes = {"observation": "obj", "review": "rev", "decision": "dec"}
    for kind, ref in accepted_w9.RESERVED_EXTERNAL_REFS.items():
        namespace, domain_kind, entry, located = ref["domain"].split(":", 3)
        path, commit = located.rsplit("@", 1)
        assert (namespace, domain_kind, len(commit)) == ("w9-external", kind, 40)
        assert external_ref_id(prefixes[kind], kind, entry, path, commit) == ref["id"]
    envelope = json.loads((REPO_ROOT / ENVELOPE["path"]).read_bytes())
    assert {
        envelope["independent_observation_ref"]["id"],
        envelope["independent_review_ref"]["id"],
        envelope["acceptance_decision_ref"]["id"],
    } == accepted_w9.RESERVED_IDS


def test_genesis_payload_is_schema_valid_and_carries_the_contract_values() -> None:
    payload = accepted_w9.accepted_genesis_payload()
    registry = bundled_runtime_schema_registry()
    registry.validate("ars://legacy/import-accepted-w9-catalogue-genesis", payload, schema_version="1.0.0")
    contract = yaml.safe_load((REPO_ROOT / O3_ACCEPTED["path"]).read_text(encoding="utf-8"))
    assert payload["verification_requirements"] == contract["verification_rules"]
    assert payload["required_w11_catalogue"] == contract["required_w11_catalogue"]
    assert payload["refused_store_identities"] == contract["refused_store_identities"]
    assert payload["requested_genesis_transaction_id"] == "w9-genesis-request-v1"
    assert not payload["requested_genesis_transaction_id"].startswith("txb_")
    assert accepted_w9.accepted_genesis_payload() is not accepted_w9.accepted_genesis_payload()


# --- The predicate, the binding row and the route classes ------------------------------------------------------------


def test_legacy_command_types_equal_the_accepted_catalogue_command_set() -> None:
    assert LEGACY_COMMAND_TYPES == {row["command_type"] for row in _rows().values()}


def test_only_genesis_has_a_runtime_binding_row() -> None:
    bound = {binding.command_type for binding in _RUNTIME_BINDINGS if binding.command_type in LEGACY_COMMAND_TYPES}
    assert bound == {"ImportAcceptedW9CatalogueGenesis"}
    assert not any(binding.producer_command_type in LEGACY_COMMAND_TYPES for binding in _RUNTIME_BINDINGS)


def test_route_registry_is_exact_to_the_accepted_catalogue() -> None:
    routes.validate_legacy_route_registry(_catalogue())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda rows: rows[14].update(command_type="ObserveW11AuthorityFile"),
        lambda rows: rows[4].update(payload_discriminant="resolve-w9-authority-decision/other"),
        lambda rows: rows[19]["ordered_events"].pop(),
        lambda rows: rows[19]["ordered_events"][2].update(multiplicity="1"),
        lambda rows: rows.pop(),
    ],
)
def test_route_registry_refuses_a_changed_catalogue(mutate: Any) -> None:
    catalogue = deepcopy(_catalogue())
    mutate(catalogue["owner_contract_rows"])
    with pytest.raises(IntegrityError, match="W9 route registry"):
        routes.validate_legacy_route_registry(catalogue)


def test_route_classes_are_one_routed_and_sixty_deferred_with_the_design_note_tags() -> None:
    assert routes.LEGACY_ROUTED_ROWS == {"LR-001"}
    assert routes.LEGACY_DEFERRED_ROWS == EXPECTED_TAGS


def test_c5_no_row_emits_a_shared_event_type() -> None:
    shared = (
        ARTEFACT_EVENT_TYPES | CONTEXT_EVENT_TYPES | CONTROL_EVENT_TYPES | {"PartialOutcomeRecorded", "LeaseReleased"}
    )
    emitted = {routes.legacy_event_name(slot["event"]) for row in _rows().values() for slot in row["ordered_events"]}
    assert not emitted & shared


# Design note §2.3 C4: the consumers of shared_event_partition, and the one that names "legacy" (U-7 site 3).
C4_CONSUMERS = frozenset(
    {
        "research_system/discovery/runtime.py",
        "research_system/discovery/spec.py",
        "research_system/discovery/spec_assay.py",
        "research_system/discovery/replay/driver.py",
    }
)
C4_SITE_3 = "research_system/discovery/replay/driver.py"
_PARTITION_FUNCTIONS = frozenset({"shared_event_partition", "_shared_event_partition"})


def _selected_partitions(comparator: ast.expr, where: str) -> set[str]:
    """The partitions a comparison names; anything but string literals fails."""

    if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
        return {comparator.value}
    if isinstance(comparator, (ast.Set, ast.Tuple, ast.List)) and comparator.elts:
        if all(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in comparator.elts):
            return {item.value for item in comparator.elts}  # type: ignore[attr-defined]
    raise AssertionError(f"{where}: partition compared with a non-literal {ast.unparse(comparator)}")


def _is_continue_guard(compare: ast.Compare, parents: dict[ast.AST, ast.AST]) -> bool:
    guard = parents.get(compare)
    return (
        isinstance(guard, ast.If)
        and guard.test is compare
        and len(guard.body) == 1
        and isinstance(guard.body[0], ast.Continue)
        and not guard.orelse
    )


def _partition_comparisons(path: str) -> list[tuple[ast.Compare, dict[ast.AST, ast.AST]]]:
    """Every comparison that decides on a partition in ``path``, following an assigned partition to its uses."""

    tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _PARTITION_FUNCTIONS
    ]
    assert calls, path
    comparisons = []
    for call in calls:
        where = f"{path}:{call.lineno}"
        parent = parents[call]
        if isinstance(parent, ast.Compare) and parent.left is call:
            comparisons.append(parent)
            continue
        # An assigned partition: every use in its function must be a comparison, and it must not be rebound.
        assert isinstance(parent, ast.Assign) and len(parent.targets) == 1, f"{where}: unrecognised consumer shape"
        target = parent.targets[0]
        assert isinstance(target, ast.Name), f"{where}: unrecognised consumer shape"
        scope: ast.AST = parent
        while not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            scope = parents[scope]
        names = [node for node in ast.walk(scope) if isinstance(node, ast.Name) and node.id == target.id]
        assert sum(isinstance(node.ctx, ast.Store) for node in names) == 1, f"{where}: {target.id} is rebound"
        uses = [node for node in names if isinstance(node.ctx, ast.Load)]
        assert uses, f"{where}: {target.id} is never compared"
        for use in uses:
            compare = parents[use]
            assert isinstance(compare, ast.Compare) and compare.left is use, (
                f"{path}:{use.lineno}: {target.id} used other than as the left side of a comparison"
            )
            comparisons.append(compare)
    return [(compare, parents) for compare in comparisons]


def _legacy_continue_guards(path: str) -> int:
    """Check every partition decision in ``path``; return how many are a ``== "legacy": continue`` guard."""

    guards = 0
    for compare, parents in _partition_comparisons(path):
        where = f"{path}:{compare.lineno}"
        assert len(compare.ops) == 1, where
        op = compare.ops[0]
        named = _selected_partitions(compare.comparators[0], where)
        if isinstance(op, (ast.NotEq, ast.NotIn)):
            assert _is_continue_guard(compare, parents), f"{where}: an exclusion that is not a continue guard"
            assert "legacy" not in named, f"{where}: an exclusion guard that admits legacy"
        else:
            assert isinstance(op, (ast.Eq, ast.In)), f"{where}: {ast.unparse(compare)}"
        if "legacy" in named:
            assert isinstance(op, ast.Eq) and named == {"legacy"}, f"{where}: legacy selected with another partition"
            assert _is_continue_guard(compare, parents), f"{where}: legacy selected for handling"
            guards += 1
    return guards


def test_c4_every_partition_consumer_selects_by_equality_or_membership() -> None:
    """Design note §2.3 C4: each consumer acts only on partitions it names, so "legacy" falls through unhandled.

    A consumer either compares the call's result directly or assigns it and compares the name. Every comparison is
    against string literals; ``==`` and ``in`` select, and ``!=`` and ``not in`` are allowed only as a bare
    ``continue`` guard. The one comparison naming "legacy" is U-7 site 3's ``continue`` in the Discovery driver.
    """

    consumers = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "research_system").rglob("*.py")
        if "shared_event_partition" in path.read_text(encoding="utf-8")
    } - {"research_system/discovery/routes.py"}
    assert consumers == C4_CONSUMERS
    assert {path: _legacy_continue_guards(path) for path in sorted(C4_CONSUMERS)} == {
        path: int(path == C4_SITE_3) for path in sorted(C4_CONSUMERS)
    }

    event = {"command_type": "ObserveLegacyRecord", "event_type": "LegacyRecordObserved"}
    assert shared_event_partition(event) == "legacy"
    assert is_legacy_projection_event(event)


def _write_consumer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> str:
    path = "research_system/discovery/replay/driver.py"
    (tmp_path / path).parent.mkdir(parents=True)
    (tmp_path / path).write_text("def f(events, k):\n    for e in events:\n" + body, encoding="utf-8")
    monkeypatch.setattr(f"{__name__}.REPO_ROOT", tmp_path)
    return path


@pytest.mark.parametrize(
    ("body", "guards"),
    [
        ('        if shared_event_partition(e) != "artefact":\n            continue\n', 0),
        ('        if shared_event_partition(e) in {"context", "control"}:\n            pass\n', 0),
        (
            '        p = shared_event_partition(e)\n        if p == "artefact":\n            pass\n'
            '        if p == "legacy":\n            continue\n',
            1,
        ),
    ],
    ids=["exclusion-guard", "membership", "site-3-shape"],
)
def test_c4_check_accepts_a_safe_consumer(
    body: str, guards: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _legacy_continue_guards(_write_consumer(tmp_path, monkeypatch, body)) == guards


@pytest.mark.parametrize(
    "body",
    [
        '        if shared_event_partition(e) != "legacy":\n            continue\n',
        '        if shared_event_partition(e) != "artefact":\n            handle(e)\n',
        '        if shared_event_partition(e) == "legacy":\n            handle(e)\n',
        '        if shared_event_partition(e) in {"legacy", "context"}:\n            continue\n',
        "        p = shared_event_partition(e)\n        handlers[p](e)\n",
        '        p = shared_event_partition(e)\n        p = "artefact"\n        if p == "artefact":\n            pass\n',
        "        if shared_event_partition(e) == k:\n            pass\n",
        "        handle(e, shared_event_partition(e))\n",
    ],
    ids=[
        "guard-admits-legacy",
        "exclusion-without-continue",
        "legacy-handled",
        "legacy-in-a-set",
        "dispatch-table",
        "rebound",
        "non-literal",
        "passed-on",
    ],
)
def test_c4_check_refuses_an_unsafe_consumer(body: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative controls: each shape would let a consumer act on "legacy" or hide what it selects."""

    with pytest.raises(AssertionError):
        _legacy_continue_guards(_write_consumer(tmp_path, monkeypatch, body))


# --- Row assignment (design note §4) ---------------------------------------------------------------------------------


def _transaction_for(row_id: str, row: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    command_type = row["command_type"]
    events = [routes.legacy_event_name(slot["event"]) for slot in row["ordered_events"] if slot["multiplicity"] == "1"]
    first = events[0]
    requests: dict[str, str] = {}
    if first == "ReviewRequested":
        payload = {"new_review_id": "rev_x", "governing_refs": [f"W9:{row_id}", "doc:other"]}
    elif first == "ReviewVerdictRecorded":
        request_row = next(r for r, v in routes._VERDICT_ROW_FOR_REQUEST.items() if v == row_id)
        requests = {"rev_x": request_row}
        payload = {"review_id": "rev_x"}
    elif first in {"DecisionProposed", "DecisionResolved"}:
        payload = {"governing_evidence_refs": ["obj_x", f"W9:{row_id}"]}
    else:
        payload = {"schema_id": row["record_schema_id"]}
        if command_type == "CreateLegacyPaperRoot":
            payload["recovery"] = None if row["payload_discriminant"].endswith("ordinary") else {"x": 1}
    transaction = [{"command_type": command_type, "event_type": first, "payload": payload}]
    transaction += [{"command_type": command_type, "event_type": name, "payload": {}} for name in events[1:]]
    return transaction, requests


def test_row_assignment_is_a_bijection_onto_the_61_rows() -> None:
    assigned = {}
    for row_id, row in _rows().items():
        transaction, requests = _transaction_for(row_id, row)
        assigned[row_id] = routes.assign_row(transaction, requests)
    assert assigned == {row_id: row_id for row_id in accepted_w9.ROW_IDS}


def test_e_only_discriminants_equal_the_accepted_ones() -> None:
    e_only = {
        row_id: row
        for row_id, row in _rows().items()
        if routes.legacy_event_name(row["ordered_events"][0]["event"]) not in routes.W2_EVENT_TYPES
    }
    assert len(e_only) == 18
    for row in e_only.values():
        record = {"schema_id": row["record_schema_id"]}
        if row["command_type"] == "CreateLegacyPaperRoot":
            record["recovery"] = None if row["payload_discriminant"].endswith("ordinary") else {}
        assert routes.e_only_discriminant(row["command_type"], record) == row["payload_discriminant"]


@pytest.mark.parametrize(
    ("refs", "message"),
    [
        (["W9:LR-004", "W9:LR-005"], "exactly one W9 row"),
        (["doc:other"], "exactly one W9 row"),
        (["W9:LR-04"], "exactly one W9 row"),
        ("W9:LR-004", "malformed"),
    ],
)
def test_a_w2_event_must_name_exactly_one_w9_row(refs: Any, message: str) -> None:
    with pytest.raises(IntegrityError, match=message):
        routes.w9_row_ref(refs)


def test_a_w2_event_naming_another_commands_row_is_refused() -> None:
    transaction = [
        {
            "command_type": "ProposeW9AuthorityDecision",
            "event_type": "DecisionProposed",
            "payload": {"governing_evidence_refs": ["W9:LR-005"]},
        }
    ]
    with pytest.raises(IntegrityError, match="names a row of another command"):
        routes.assign_row(transaction, {})


def test_lr_054_and_lr_055_are_separated_by_their_w2_ref() -> None:
    for row_id in ("LR-054", "LR-055"):
        transaction, _ = _transaction_for(row_id, _rows()[row_id])
        assert routes.assign_row(transaction, {}) == row_id


@pytest.mark.parametrize(
    ("row_id", "event_types", "valid"),
    [
        ("LR-020", ["DecisionResolved", "LegacyClosedReferenceAcceptanceRecorded"], True),
        (
            "LR-020",
            ["DecisionResolved", "LegacyClosedReferenceAcceptanceRecorded"]
            + ["LegacyOwnershipTransitionedRecorded"] * 3,
            True,
        ),
        ("LR-020", ["DecisionResolved"], False),
        ("LR-005", ["DecisionResolved", "LegacyPathRegistrationRecorded", "LegacyPathRegistrationRecorded"], False),
        ("LR-001", ["W9CatalogueGenesisImported"], True),
    ],
)
def test_transaction_shape_follows_the_accepted_ordered_events(
    row_id: str, event_types: list[str], valid: bool
) -> None:
    if valid:
        routes.validate_transaction_shape(row_id, event_types)
    else:
        with pytest.raises(IntegrityError, match=f"differs from accepted {row_id}"):
            routes.validate_transaction_shape(row_id, event_types)


# --- Reducer invariants (design note §7.4) ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("from_mode", "to_mode", "allowed"),
    [
        ("legacy_owned", "successor_owned", True),
        ("legacy_owned", "closed_reference", True),
        ("successor_owned", "closed_reference", True),
        ("successor_owned", "legacy_owned", False),
        ("closed_reference", "legacy_owned", False),
        ("closed_reference", "successor_owned", False),
        ("legacy_owned", "legacy_owned", False),
    ],
)
def test_w9_t5_only_the_w9_8_2_transitions(from_mode: str, to_mode: str, allowed: bool) -> None:
    assert reducers.ownership_transition_allowed(from_mode, to_mode) is allowed


@pytest.mark.parametrize(
    "identity",
    [
        {"identity_kind": "restricted_untracked_file", "path": "x/y.bin", "frozen_copy_ref": {}},
        {"identity_kind": "untracked_file", "path": "results/x.CSV", "frozen_copy_ref": {}},
        {"identity_kind": "vault_file", "vault_path": "a/b.pkl", "frozen_copy_ref": {}},
    ],
)
def test_w9_t11_store_half_a_restricted_source_never_carries_a_frozen_copy(identity: dict[str, Any]) -> None:
    with pytest.raises(IntegrityError, match="restricted source carries a frozen-copy ref"):
        reducers.refuse_restricted_frozen_copy({"source_identity": identity})
    allowed = {key: value for key, value in identity.items() if key != "frozen_copy_ref"}
    reducers.refuse_restricted_frozen_copy({"source_identity": allowed})


def test_supersession_is_acyclic() -> None:
    state = reducers.new_legacy_state()

    def supersede(old: str, new: str) -> None:
        reducers._apply_supersession(state, {"superseded_ref": {"id": old}, "replacing_ref": {"id": new}})

    supersede("obj_a", "obj_b")
    supersede("obj_b", "obj_c")
    with pytest.raises(IntegrityError, match="supersession cycle"):
        supersede("obj_c", "obj_a")
    with pytest.raises(IntegrityError, match="supersession is invalid"):
        supersede("obj_d", "obj_d")
    with pytest.raises(IntegrityError, match="supersession is invalid"):
        supersede("obj_a", "obj_d")


def test_w9_t21_reducer_half_reference_cycles_are_refused() -> None:
    state = reducers.new_legacy_state()
    reducers._add_edges(state, "obj_root", ["dec_recovery"])
    reducers._add_edges(state, "obj_mapping", ["obj_root"])
    with pytest.raises(IntegrityError, match="reference cycle"):
        reducers._add_edges(state, "dec_recovery", ["obj_mapping"])
    with pytest.raises(IntegrityError, match="references itself"):
        reducers._add_edges(state, "obj_transition", ["obj_transition"])


def test_w9_c25_the_reserved_ids_are_refused_as_pre_assigned_ids() -> None:
    state = reducers.new_legacy_state()
    for identity in accepted_w9.RESERVED_IDS:
        with pytest.raises(IntegrityError, match="reserved for an external ref"):
            reducers.claim_identity(state, identity, "decision")
    reducers.claim_identity(state, "dec_01a17eb7-5ae0-7000-8000-00000000000a", "decision")
    with pytest.raises(IntegrityError, match="identity collision"):
        reducers.claim_identity(state, "dec_01a17eb7-5ae0-7000-8000-00000000000a", "decision")
    with pytest.raises(IntegrityError, match="identity collision"):
        reducers.claim_identity(state, accepted_w9.CATALOGUE_STREAM_ID, "proposal")
