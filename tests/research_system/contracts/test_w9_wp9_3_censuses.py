# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-1 §4.3, §9.1, §17)
# Purpose: the WP9.3-1 censuses: runtime constructions, CommandService lock sites, grant-free command types, the
# created-ID table's coverage, and the bootstrap's identities. Each census has a positive control on the tree and
# negative controls on fixtures that must fail it.
"""WP9.3-1 censuses (WP9.3 note §4.3, §9.1, §17, §18).

What a census cannot see is a human-review question (note §18): a runtime built by code outside the repository or by a
dynamic import, and whether each created-ID class matches what its reducer does.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

from research_system.command import service, t2
from research_system.discovery.replay.registry import REDUCERS as DISCOVERY_REDUCERS
from research_system.legacy.accepted_w9 import RESERVED_IDS
from research_system.legacy.identities import NON_W9_ID_FIELDS, W9_CLAIMABLE_PREFIXES, w9_fixed_identities

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_CLASSES = frozenset({"LegacyRuntime", "DiscoveryRuntime"})
# §17: exactly two allowed construction sites, each binding through load_current_binding.
ALLOWED_CONSTRUCTIONS = frozenset(
    {
        ("research_system/discovery/spec.py", "SpecCoordinator._discovery"),
        ("research_system/cli.py", "_legacy_submit"),
    }
)
DEFINING_MODULES = {
    "LegacyRuntime": "research_system/legacy/runtime.py",
    "DiscoveryRuntime": "research_system/discovery/runtime.py",
}


# --- The runtime-construction census (§17) -----------------------------------------------------------------------------


class _Census(ast.NodeVisitor):
    """Count constructions of LegacyRuntime and DiscoveryRuntime, following every name bound to either class."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.bound: set[str] = set()
        self.scope: list[str] = []
        self.constructions: list[tuple[str, str, int, bool]] = []
        self.subclasses: list[tuple[str, int]] = []

    def _is_class(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.bound or node.id in RUNTIME_CLASSES
        if isinstance(node, ast.Attribute):
            return node.attr in RUNTIME_CLASSES or self._is_class(node.value) and False
        if isinstance(node, ast.Call):
            function = node.func
            name = function.attr if isinstance(function, ast.Attribute) else getattr(function, "id", None)
            if name == "partial" and node.args and self._is_class(node.args[0]):
                return True
            if name == "getattr" and len(node.args) >= 2:
                attribute = node.args[1]
                return isinstance(attribute, ast.Constant) and attribute.value in RUNTIME_CLASSES
        return False

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name in RUNTIME_CLASSES:
                self.bound.add(alias.asname or alias.name)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._is_class(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.bound.add(target.id)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for base in node.bases:
            if self._is_class(base):
                self.subclasses.append((self.path, node.lineno))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_class(node.func):
            # Review i-5: the argument must be a binding's ``revalidate`` (an attribute ending ``.revalidate``), so a
            # present but empty ``binding_check=None``, or any other constant or name, does not count as the binding.
            binding = any(
                keyword.arg == "binding_check"
                and isinstance(keyword.value, ast.Attribute)
                and keyword.value.attr == "revalidate"
                for keyword in node.keywords
            )
            self.constructions.append((self.path, ".".join(self.scope), node.lineno, binding))
        self.generic_visit(node)


def _census(path: str, source: str) -> _Census:
    census = _Census(path)
    tree = ast.parse(source)
    # Two passes, so a name bound after its first use in the file is still followed.
    census.visit(tree)
    census.constructions.clear()
    census.subclasses.clear()
    census.visit(tree)
    return census


def _violations(path: str, source: str) -> list[str]:
    census = _census(path, source)
    problems = []
    for subclass_path, line in census.subclasses:
        if not any(subclass_path == module for module in DEFINING_MODULES.values()):
            problems.append(f"{subclass_path}:{line}: subclasses a W9 or W11 runtime")
    for site_path, scope, line, binding in census.constructions:
        if (site_path, scope) not in ALLOWED_CONSTRUCTIONS:
            problems.append(f"{site_path}:{line}: constructs a W9 or W11 runtime outside the two allowed sites")
        elif not binding:
            problems.append(f"{site_path}:{line}: constructs a runtime without its binding check")
    return problems


def _tracked_python() -> Iterator[tuple[str, str]]:
    listed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "*.py"], check=True, capture_output=True, text=True
    ).stdout.split()
    for relative in listed:
        if relative.startswith("tests/") or not (REPO_ROOT / relative).is_file():
            continue
        yield relative, (REPO_ROOT / relative).read_text(encoding="utf-8", errors="replace")


def test_runtime_construction_census_passes_on_the_tree() -> None:
    """Positive control: imports, re-exports and annotations pass; the two allowed sites each construct once."""
    problems: list[str] = []
    sites: list[tuple[str, str]] = []
    for relative, source in _tracked_python():
        if "LegacyRuntime" not in source and "DiscoveryRuntime" not in source:
            continue
        problems += _violations(relative, source)
        sites += [(path, scope) for path, scope, _, _ in _census(relative, source).constructions]
    assert problems == []
    assert sorted(sites) == sorted(ALLOWED_CONSTRUCTIONS)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "from research_system.legacy.runtime import LegacyRuntime\n\ndef build(ledger):\n    return LegacyRuntime(1, ledger)\n",
            "fixture.py:4: constructs a W9 or W11 runtime outside the two allowed sites",
        ),
        (
            "from research_system.discovery import DiscoveryRuntime as Runtime\nmade = Runtime\n\ndef build():\n    return made(1)\n",
            "fixture.py:5: constructs a W9 or W11 runtime outside the two allowed sites",
        ),
        (
            "import functools\nfrom research_system.legacy.runtime import LegacyRuntime\n"
            "factory = functools.partial(LegacyRuntime, 1)\n\ndef build():\n    return factory()\n",
            "fixture.py:6: constructs a W9 or W11 runtime outside the two allowed sites",
        ),
        (
            "import research_system.discovery.runtime as module\n\ndef build():\n"
            "    return getattr(module, 'DiscoveryRuntime')(1)\n",
            "fixture.py:4: constructs a W9 or W11 runtime outside the two allowed sites",
        ),
        (
            "from research_system.legacy.runtime import LegacyRuntime\n\nclass Quiet(LegacyRuntime):\n    pass\n",
            "fixture.py:3: subclasses a W9 or W11 runtime",
        ),
    ],
    ids=["direct", "alias", "partial", "getattr", "subclass"],
)
def test_runtime_construction_census_fails_a_fixture_that_escapes_the_binding(source: str, message: str) -> None:
    assert message in _violations("fixture.py", source)


@pytest.mark.parametrize(
    "argument",
    ["", ", binding_check=None", ", binding_check=check", ", binding_check=lambda: None", ", binding_check=self.check"],
    ids=["absent", "none", "a-name", "a-lambda", "another-attribute"],
)
def test_an_allowed_site_without_its_binding_check_fails_the_census(argument: str) -> None:
    """Review i-5: only ``binding_check=<binding>.revalidate`` counts as the site's binding."""
    source = f"class SpecCoordinator:\n    def _discovery(self):\n        return DiscoveryRuntime(1, 2{argument})\n"
    assert _violations("research_system/discovery/spec.py", source) == [
        "research_system/discovery/spec.py:3: constructs a runtime without its binding check"
    ]
    passing = "class SpecCoordinator:\n    def _discovery(self):\n        return DiscoveryRuntime(1, binding_check=b.revalidate)\n"
    assert _violations("research_system/discovery/spec.py", passing) == []


# --- The CommandService lock-site census (§9.1) ------------------------------------------------------------------------

LOCK_CONSTRUCTORS = frozenset({"WriterLock", "CompositeWriterLock"})
LOCK_FACTORY = "_take_scoped_activation_recovery_lock"


def _lock_sites(source: str, class_name: str = "CommandService") -> dict[str, bool]:
    """Every method that holds the control-root writer lock, and whether it rechecks the binding inside it."""
    sites: dict[str, bool] = {}
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.ClassDef) and node.name == class_name):
            continue
        for method in node.body:
            if not isinstance(method, ast.FunctionDef) or method.name == LOCK_FACTORY:
                continue
            calls = [call for call in ast.walk(method) if isinstance(call, ast.Call)]
            names = {
                call.func.attr if isinstance(call.func, ast.Attribute) else getattr(call.func, "id", "")
                for call in calls
            }
            if names & (LOCK_CONSTRUCTORS | {LOCK_FACTORY}):
                sites[method.name] = "_recheck_binding" in names
    return sites


def test_every_command_service_lock_site_that_can_append_rechecks_the_binding() -> None:
    sites = _lock_sites((REPO_ROOT / "research_system/command/service.py").read_text(encoding="utf-8"))
    # Exactly these three sites (note §9.1); a new one fails until it is listed and rechecks.
    assert sites == {
        "_submission_lock": True,
        "with_locked_authority": True,
        "_recover_scoped_activation_markers": True,
    }
    # submit and submit_t2 take _submission_lock, which rechecks; neither constructs a lock of its own.
    t2_source = (REPO_ROOT / "research_system/command/t2.py").read_text(encoding="utf-8")
    assert "_submission_lock(command)" in t2_source and "WriterLock(" not in t2_source


def test_a_fixture_lock_site_without_the_recheck_fails_the_census() -> None:
    source = (
        "class CommandService:\n"
        "    def careful(self):\n"
        "        with CompositeWriterLock(()):\n"
        "            self._recheck_binding()\n"
        "    def careless(self):\n"
        "        with CompositeWriterLock(()):\n"
        "            pass\n"
    )
    assert _lock_sites(source) == {"careful": True, "careless": False}


# --- The grant-free census (§9.1) ---------------------------------------------------------------------------------------

# Generic command types the service writes without resolving a grant under its writer lock (§9.1). Each is a known
# limit on a later pin's checklist. A new one fails this census until it is named here.
GRANT_FREE_COMMAND_TYPES = frozenset({"RecordProviderReceipt", "VerifyEvidenceDeletion"})
# Of those, the types that can take an ID §4.3's created-ID table counts: VerifyEvidenceDeletion appends to the caller's
# target stream, which may be any ID (a dec_ in tests/research_system/unit/test_retention.py). RecordProviderReceipt
# appends to its cost grant's cgr_ stream and creates no obj_, rev_ or dec_ (wp6-2-t2 event schemas).
GRANT_FREE_W9_CLAIMABLE = frozenset({"VerifyEvidenceDeletion"})


def _dispatched_command_types(source: str, namespace: object) -> set[str]:
    universe: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.FunctionDef) and node.name == "_build_event"):
            continue
        for compare in ast.walk(node):
            if not (isinstance(compare, ast.Compare) and getattr(compare.left, "id", None) == "command_type"):
                continue
            for comparator in compare.comparators:
                if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                    universe.add(comparator.value)
                elif isinstance(comparator, (ast.Set, ast.Tuple, ast.List)):
                    universe |= {item.value for item in comparator.elts if isinstance(item, ast.Constant)}
                elif isinstance(comparator, ast.Name):
                    universe |= set(getattr(namespace, comparator.id))
    return universe


def _grant_free(source: str, namespace: object) -> set[str]:
    universe = _dispatched_command_types(source, namespace) | set(t2.T2_COMMAND_TYPES)
    return universe - set(service._AUTHORITY_COORDINATED_COMMAND_TYPES)


def test_the_grant_free_census_names_every_type_that_writes_without_a_grant() -> None:
    source = (REPO_ROOT / "research_system/command/service.py").read_text(encoding="utf-8")
    assert _grant_free(source, service) == GRANT_FREE_COMMAND_TYPES
    assert GRANT_FREE_W9_CLAIMABLE <= GRANT_FREE_COMMAND_TYPES


def test_a_fixture_type_that_writes_without_a_grant_fails_the_census() -> None:
    source = (
        "def _build_event(self, command_type):\n"
        "    if command_type == 'VerifyEvidenceDeletion':\n        pass\n"
        "    elif command_type == 'RecordProviderReceipt':\n        pass\n"
        "    elif command_type == 'WriteWithoutAGrant':\n        pass\n"
    )
    assert _grant_free(source, service) - GRANT_FREE_COMMAND_TYPES == {"WriteWithoutAGrant"}


# --- The created-ID table's coverage (§4.3) -----------------------------------------------------------------------------

_ID_PATTERN = re.compile(r"^\^(" + "|".join(prefix.rstrip("_") for prefix in W9_CLAIMABLE_PREFIXES) + r")_\[0-9a-f\]")
# One real W9 ID of each claimable kind: the accepted reserved refs (an obj_, a rev_ and a dec_).
_W9_SAMPLE_IDS = tuple(sorted(RESERVED_IDS))
EVENT_SCHEMA_DIRECTORIES = (
    ".research-system/schemas/core/events",
    ".research-system/schemas/wp6-2-t2/events",
    ".research-system/schemas/wp6-2-live-issue/events",
)


def _id_fields(node, root, path, found, seen) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/") and (ref, tuple(path)) not in seen:
            seen.add((ref, tuple(path)))
            target = root
            for part in ref[2:].split("/"):
                target = target[part]
            _id_fields(target, root, path, found, seen)
        pattern = node.get("pattern")
        # Review i-4: a field counts when its pattern starts with a W9 kind, or when the compiled pattern accepts one
        # of W9's own IDs, so a broader pattern (``^[a-z]+_<uuid7>$``) is caught too.
        if isinstance(pattern, str) and (
            _ID_PATTERN.match(pattern) or any(re.search(pattern, sample) for sample in _W9_SAMPLE_IDS)
        ):
            found.add("/".join(path))
        for name, child in node.get("properties", {}).items():
            _id_fields(child, root, [*path, name], found, seen)
        if "items" in node:
            _id_fields(node["items"], root, [*path, "[]"], found, seen)
        for key in ("allOf", "anyOf", "oneOf", "then", "else"):
            children = node.get(key)
            for child in children if isinstance(children, list) else ([children] if children else []):
                _id_fields(child, root, path, found, seen)


def _schema_id_fields(schema: dict) -> dict[str, set[str]]:
    found: set[str] = set()
    _id_fields(schema, schema, [], found, set())
    event_type = str(schema.get("$id", "")).rsplit("/", 1)[-1]
    return {event_type: {field.removeprefix("payload/") for field in found if field.startswith("payload/")}}


def _unclassified(schemas: list[dict]) -> list[str]:
    missing = []
    for schema in schemas:
        for event_type, fields in _schema_id_fields(schema).items():
            for field in sorted(fields - set(NON_W9_ID_FIELDS.get(event_type, {}))):
                missing.append(f"{event_type}: {field}")
    return missing


def test_the_created_id_table_classifies_every_w9_claimable_id_field_of_every_event_schema() -> None:
    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for directory in EVENT_SCHEMA_DIRECTORIES
        for path in sorted((REPO_ROOT / directory).glob("*.json"))
    ]
    assert len(schemas) > 100
    assert _unclassified(schemas) == []


def test_the_coverage_test_fails_on_a_fixture_schema_whose_created_id_field_the_table_omits() -> None:
    fixture = {
        "$id": "ars://core/event/FixtureCreated",
        "properties": {
            "payload": {
                "properties": {"new_fixture_id": {"type": "string", "pattern": "^obj_[0-9a-f]{8}-x$"}},
            }
        },
    }
    assert _unclassified([fixture]) == ["FixtureCreated: new_fixture_id"]


def test_the_coverage_test_fails_on_a_fixture_field_whose_broad_pattern_admits_a_w9_id() -> None:
    """Review i-4: a pattern that does not start with a W9 kind but accepts one is still a W9-claimable field."""
    uuid7 = "[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    fixture = {
        "$id": "ars://core/event/FixtureCreated",
        "properties": {
            "payload": {
                "properties": {
                    "any_record_id": {"type": "string", "pattern": f"^[a-z][a-z0-9]*_{uuid7}$"},
                    "actor_only_id": {"type": "string", "pattern": f"^act_{uuid7}$"},
                }
            }
        },
    }
    assert _unclassified([fixture]) == ["FixtureCreated: any_record_id"]


def test_the_created_id_table_names_every_event_discoverys_reducers_handle() -> None:
    """W11 E: events have no per-type payload schema, so the table must list each registry event type."""
    assert set(DISCOVERY_REDUCERS) <= set(NON_W9_ID_FIELDS)


# --- The authority bootstrap's identities (§4.3) ------------------------------------------------------------------------


def test_the_authority_bootstraps_fixed_ids_are_disjoint_from_w9s(tmp_path: Path) -> None:
    from tests.research_system.factories import control_plane

    harness = control_plane(tmp_path)
    streams = {event["stream_id"] for event in harness.authority_ledger.iter_events()}
    assert streams and all(stream.startswith("agr_") for stream in streams)
    assert not streams & w9_fixed_identities()
