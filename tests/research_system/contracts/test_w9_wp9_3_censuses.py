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


# --- The CommandService construction census (§9.1; WP9.3-1b review M-1) -------------------------------------------------

SERVICE_CLASS = "CommandService"
# Production code that may build CommandService with no binding check, and why. Nothing else may.
SERVICE_WITHOUT_BINDING = {
    "research_system/evals/executors/release_tranche.py": (
        "the release-tranche executor builds and writes only the scratch stores it initializes itself "
        "(initialize_authority_control_store); no foundation names them and no binding exists to recheck"
    ),
}


def _service_constructions(path: str, source: str) -> list[tuple[str, str, int, bool]]:
    """Every call of CommandService, of a subclass, or of a name bound to either, with whether it passes a check.

    A check is a ``binding_check=`` keyword whose value is not a constant, so ``binding_check=None`` does not count.
    Review n-3 (WP9.3-1b addendum): a class reached through ``functools.partial``, ``getattr`` or
    ``operator.attrgetter`` with a constant name, or a ``globals()``, ``vars()`` or ``__dict__`` subscript, is followed
    too. Through ``partial``, only a check the ``partial`` call itself binds counts, since the call that finally
    constructs may be anywhere.
    """
    tree = ast.parse(source)
    names = {SERVICE_CLASS}
    # Partial bindings are keyed by (lexical scope, name): a binding in one function never decides another function's
    # calls (CodeRabbit, #432). A scope is the chain of enclosing defs, classes and lambdas; a call resolves its name
    # from the innermost scope that binds it to a class value, as Python resolves a local before an enclosing name.
    # A class body encloses nothing (review m-5, WP9.3-2 addendum): a free name in a method, a lambda or a nested
    # class body resolves from the enclosing functions and the module, never from a class body around it. So a class
    # scope is searched only for a call made in that class body itself.
    Scope = tuple[str, ...]
    partials: dict[tuple[Scope, str], bool] = {}  # with whether every partial binding there binds a check
    bound: set[tuple[Scope, str]] = set()  # every (scope, name) given a class value
    scope_of: dict[int, Scope] = {}
    class_scopes: set[Scope] = set()

    def assign_scopes(node: ast.AST, scope: Scope) -> None:
        for child in ast.iter_child_nodes(node):
            scope_of[id(child)] = scope
            inner = scope
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
                inner = (*scope, f"{getattr(child, 'name', '<lambda>')}@{child.lineno}:{child.col_offset}")
                if isinstance(child, ast.ClassDef):
                    class_scopes.add(inner)
            assign_scopes(child, inner)

    assign_scopes(tree, ())

    def partial_flag(scope: Scope, name: str) -> bool | None:
        """The partial check flag of ``name`` as seen from ``scope``, or ``None`` when it resolves to no partial."""
        for depth in range(len(scope), -1, -1):
            if depth < len(scope) and scope[:depth] in class_scopes:
                continue  # an enclosing class body is not on a nested scope's resolution path (m-5)
            if (scope[:depth], name) in bound:
                return partials.get((scope[:depth], name))
        return None

    partial_names = {"partial"}
    # Review m-1: an import alias is the class (or ``functools.partial``) under another name.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname and alias.name == SERVICE_CLASS:
                    names.add(alias.asname)
                elif alias.asname and alias.name == "partial":
                    partial_names.add(alias.asname)

    def call_name(call: ast.Call) -> str | None:
        function = call.func
        return function.id if isinstance(function, ast.Name) else getattr(function, "attr", None)

    def string(node: ast.expr | None) -> str | None:
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    def has_check(call: ast.Call) -> bool:
        return any(
            keyword.arg == "binding_check" and not isinstance(keyword.value, ast.Constant) for keyword in call.keywords
        )

    def overrides_check(call: ast.Call) -> bool:
        """Whether calling a partial may replace its bound check: a constant ``binding_check=`` (``None`` included),
        or a ``**`` mapping, which can carry one. Invocation keywords override a partial's own (functools)."""
        return any(
            keyword.arg is None or (keyword.arg == "binding_check" and isinstance(keyword.value, ast.Constant))
            for keyword in call.keywords
        )

    def is_partial(value: ast.expr) -> bool:
        return (
            isinstance(value, ast.Call)
            and call_name(value) in partial_names
            and bool(value.args)
            and class_valued(value.args[0])
        )

    def namespace(value: ast.expr) -> bool:
        """``globals()``, ``vars(x)`` or ``x.__dict__``: a mapping from names to module or class attributes."""
        if isinstance(value, ast.Call):
            return call_name(value) in {"globals", "vars", "locals"}
        return isinstance(value, ast.Attribute) and value.attr == "__dict__"

    def class_valued(value: ast.expr) -> bool:
        """Whether an expression evaluates to one of the classes, not to an instance or a call's result."""
        if isinstance(value, ast.Name):
            return value.id in names
        if isinstance(value, ast.NamedExpr):
            return class_valued(value.value)
        if isinstance(value, ast.IfExp):
            return class_valued(value.body) or class_valued(value.orelse)
        if isinstance(value, ast.Subscript):
            if namespace(value.value):
                return string(value.slice) in names
            return class_valued(value.value)
        if isinstance(value, ast.Dict):
            return any(item is not None and class_valued(item) for item in value.values)
        if isinstance(value, ast.Call):
            if is_partial(value):
                return True
            if call_name(value) == "getattr" and len(value.args) >= 2:
                return string(value.args[1]) in names
            getter = value.func
            if isinstance(getter, ast.Call) and call_name(getter) == "attrgetter" and getter.args:
                return string(getter.args[0]) in names
        return False

    # The census is flow-insensitive: a name bound more than once may hold any of its bindings when called. So a name
    # counts as a checked partial only if every class-valued binding of it is a checked partial (or an alias of one);
    # one binding to the class itself, or to an unchecked partial, makes every call through that name unchecked
    # (CodeRabbit, #432: ``alias = factory`` then ``alias = CommandService``).
    for _ in range(64):  # a fixpoint; the bound only guards against an oscillation no fixture has shown
        before = set(names), dict(partials), set(bound)
        # per (scope, name): True or False for a partial binding, None for any other class-valued binding
        flags: dict[tuple[Scope, str], list[bool | None]] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(class_valued(base) for base in node.bases):
                names.add(node.name)
            elif isinstance(node, ast.Assign | ast.AnnAssign | ast.NamedExpr) and (
                node.value is not None and class_valued(node.value)
            ):
                # Review m-1: an annotated assignment and a walrus bind a name as a plain assignment does.
                written = node.targets if isinstance(node, ast.Assign) else [node.target]
                targets = [target.id for target in written if isinstance(target, ast.Name)]
                names.update(targets)
                scope = scope_of[id(node)]
                flag: bool | None = None
                if is_partial(node.value):
                    flag = has_check(node.value)
                elif isinstance(node.value, ast.Name):
                    # ``alias = factory``: the alias is the same partial, with the same bound check (CodeRabbit, #432).
                    flag = partial_flag(scope, node.value.id)
                for target in targets:
                    bound.add((scope, target))
                    flags.setdefault((scope, target), []).append(flag)
        partials = {
            key: all(flag is True for flag in seen)
            for key, seen in flags.items()
            if any(flag is not None for flag in seen)
        }
        if (names, partials, bound) == before:
            break
    else:
        raise AssertionError("the CommandService census did not reach a fixpoint")
    sites: list[tuple[str, str, int, bool]] = []

    def visit(node: ast.AST, scope: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            inner = [*scope, child.name] if isinstance(child, ast.FunctionDef | ast.ClassDef) else scope
            if isinstance(child, ast.Call):
                function = child.func
                called = function.id if isinstance(function, ast.Name) else getattr(function, "attr", None)
                direct = isinstance(function, ast.Name | ast.Attribute) and called in names
                indirect = isinstance(function, ast.Call | ast.Subscript | ast.NamedExpr) and class_valued(function)
                if direct or indirect:
                    flag = partial_flag(scope_of[id(child)], function.id) if isinstance(function, ast.Name) else None
                    if is_partial(function):
                        checked = has_check(function) and not overrides_check(child)
                    elif flag is not None:
                        checked = flag and not overrides_check(child)
                    else:
                        checked = has_check(child)
                    sites.append((path, ".".join(scope), child.lineno, checked))
            visit(child, inner)

    visit(tree, [])
    return sites


def test_every_production_command_service_construction_passes_a_binding_check() -> None:
    """Review M-1 (WP9.3-1b): a lock site's ``_recheck_binding`` is only as good as what its caller supplies."""
    unchecked: list[str] = []
    checked: list[tuple[str, str]] = []
    for relative, source in _tracked_python():
        if SERVICE_CLASS not in source or relative == "research_system/command/service.py":
            continue
        for path, scope, line, has_check in _service_constructions(relative, source):
            if has_check:
                checked.append((path, scope))
            elif path not in SERVICE_WITHOUT_BINDING:
                unchecked.append(f"{path}:{line} ({scope}) builds CommandService with no binding check")
    assert unchecked == []
    # Positive control: the seven CLI writers and SpecCoordinator's service are all found, each with its check.
    assert {
        ("research_system/cli.py", "_store_backup"),
        ("research_system/cli.py", "_store_verify_restore"),
        ("research_system/cli.py", "_command_submit"),
        ("research_system/cli.py", "_brief_runtime"),
        ("research_system/cli.py", "_authority_activate_grant"),
        ("research_system/cli.py", "_publication_evidence"),
        ("research_system/cli.py", "_eval_publish_release"),
        ("research_system/discovery/spec.py", "SpecCoordinator._command_service"),
    } <= set(checked)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("def f():\n    return CommandService(1, 2)\n", [("fixture.py", "f", 2, False)]),
        ("def f():\n    return CommandService(1, binding_check=None)\n", [("fixture.py", "f", 2, False)]),
        ("def f(c):\n    return CommandService(1, binding_check=c)\n", [("fixture.py", "f", 2, True)]),
        (
            "class Quiet(CommandService):\n    pass\n\nmade = Quiet\n\ndef f():\n    return made(1)\n",
            [("fixture.py", "f", 7, False)],
        ),
        (
            "def f(kind):\n    service_type = CommandService if kind else Other\n    return service_type(1)\n",
            [("fixture.py", "f", 3, False)],
        ),
    ],
    ids=["direct", "none", "checked", "subclass-alias", "conditional-alias"],
)
def test_the_service_census_follows_aliases_and_refuses_a_none_check(source: str, expected: list) -> None:
    assert _service_constructions("fixture.py", source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "import functools\nfactory = functools.partial(CommandService, 1)\n\ndef f():\n    return factory()\n",
            [("fixture.py", "f", 5, False)],
        ),
        (
            "from functools import partial\n\ndef f(c):\n    return partial(CommandService, binding_check=c)()\n",
            [("fixture.py", "f", 4, True)],
        ),
        (
            "from functools import partial\n\ndef f(c):\n    return partial(CommandService, 1)(binding_check=c)\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "import research_system.command.service as m\n\ndef f():\n    return getattr(m, 'CommandService')(1)\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "import operator\n\ndef f(m):\n    return operator.attrgetter('CommandService')(m)(1)\n",
            [("fixture.py", "f", 4, False)],
        ),
        ("def f():\n    return globals()['CommandService'](1)\n", [("fixture.py", "f", 2, False)]),
        ("def f(m):\n    return vars(m)['CommandService'](1)\n", [("fixture.py", "f", 2, False)]),
        ("def f(m):\n    return m.__dict__['CommandService'](1)\n", [("fixture.py", "f", 2, False)]),
        (
            "from functools import partial\n\ndef f(c):\n    factory = partial(CommandService, binding_check=c)\n"
            "    alias = factory\n    return alias()\n",
            [("fixture.py", "f", 6, True)],
        ),
        (
            "from functools import partial\n\ndef f(c):\n    factory = partial(CommandService, 1)\n"
            "    alias = factory\n    return alias()\n",
            [("fixture.py", "f", 6, False)],
        ),
        (
            "from functools import partial\n\ndef f(c):\n    factory = partial(CommandService, binding_check=c)\n"
            "    return factory(binding_check=None)\n",
            [("fixture.py", "f", 5, False)],
        ),
        (
            "from functools import partial\n\ndef f(c):\n    return partial(CommandService, binding_check=c)(binding_check=None)\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "from functools import partial\n\ndef f(c, k):\n    factory = partial(CommandService, binding_check=c)\n"
            "    return factory(**k)\n",
            [("fixture.py", "f", 5, False)],
        ),
        (
            "from research_system.command.service import CommandService as Svc\n\ndef f():\n    return Svc(1)\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "from research_system.command.service import CommandService as Svc\n\n"
            "def f(c):\n    return Svc(1, binding_check=c)\n",
            [("fixture.py", "f", 4, True)],
        ),
        (
            "from functools import partial as p\n\ndef f():\n    return p(CommandService, 1)()\n",
            [("fixture.py", "f", 4, False)],
        ),
        (
            "from typing import Any\nfrom functools import partial\n\nfactory: Any = partial(CommandService, 1)\n\n"
            "def f():\n    return factory()\n",
            [("fixture.py", "f", 7, False)],
        ),
        (
            "def f():\n    if (made := CommandService):\n        return made(1)\n",
            [("fixture.py", "f", 3, False)],
        ),
        (
            "def f():\n    return (made := CommandService)(1)\n",
            [("fixture.py", "f", 2, False)],
        ),
        (
            "from functools import partial\n\ndef f(check):\n    factory = partial(CommandService, binding_check=check)\n"
            "    alias = factory\n    alias = CommandService\n    return alias()\n",
            [("fixture.py", "f", 7, False)],
        ),
        (
            "from functools import partial\n\ndef f(check):\n    factory = partial(CommandService, binding_check=check)\n"
            "    factory = partial(CommandService, 1)\n    return factory()\n",
            [("fixture.py", "f", 6, False)],
        ),
        (
            "from functools import partial\n\ndef direct(check):\n    factory = CommandService\n"
            "    return factory(binding_check=check)\n\ndef bound(check):\n"
            "    factory = partial(CommandService, binding_check=check)\n    return factory()\n",
            [("fixture.py", "direct", 5, True), ("fixture.py", "bound", 9, True)],
        ),
        (
            "from functools import partial\n\nfactory = partial(CommandService, 1)\n\ndef f(check):\n"
            "    factory = partial(CommandService, binding_check=check)\n    return factory()\n\n"
            "def g():\n    return factory()\n",
            [("fixture.py", "f", 7, True), ("fixture.py", "g", 10, False)],
        ),
    ],
    ids=[
        "partial-alias",
        "partial-checked",
        "partial-check-on-call",
        "getattr",
        "attrgetter",
        "globals",
        "vars",
        "dict",
        "checked-partial-alias",
        "unchecked-partial-alias",
        "named-partial-none-override",
        "inline-partial-none-override",
        "partial-splat-override",
        "import-alias",
        "import-alias-checked",
        "partial-import-alias",
        "annotated-partial",
        "walrus",
        "walrus-called",
        "alias-rebound-to-class",
        "partial-rebound-unchecked",
        "same-name-in-two-functions",
        "local-shadows-module-partial",
    ],
)
def test_the_service_census_sees_partial_and_string_lookups(source: str, expected: list) -> None:
    """Review n-3 (WP9.3-1b addendum; P-083 item 6): a construction through ``functools.partial`` or a constant-string
    lookup is a construction. Through ``partial``, only a check the ``partial`` call itself binds counts."""
    assert _service_constructions("fixture.py", source) == expected


_PARTIAL_IMPORT = "from functools import partial\n\n"
_UNCHECKED_PARTIAL = "partial(CommandService, 1)"
_CHECKED_PARTIAL = "partial(CommandService, binding_check=check)"


@pytest.mark.parametrize(
    ("source", "trigger", "expected"),
    [
        (
            f"{_PARTIAL_IMPORT}factory = {_UNCHECKED_PARTIAL}\n\ndef make(check):\n    class C:\n"
            f"        factory = {_CHECKED_PARTIAL}\n        def build(self):\n            return factory()\n    return C\n",
            "make('the check')().build()\n",
            [("fixture.py", "make.C.build", 9, False)],
        ),
        (
            f"{_PARTIAL_IMPORT}factory = {_UNCHECKED_PARTIAL}\n\ndef make(check):\n    class C:\n"
            f"        factory = {_CHECKED_PARTIAL}\n        made = factory()\n    return C\n",
            "make('the check')\n",
            [("fixture.py", "make.C", 8, True)],
        ),
        (
            f"{_PARTIAL_IMPORT}check = 'the check'\nfactory = {_CHECKED_PARTIAL}\n\nclass C:\n"
            f"    factory = {_UNCHECKED_PARTIAL}\n    def build(self):\n        return factory()\n",
            "C().build()\n",
            [("fixture.py", "C.build", 9, True)],
        ),
        (
            f"{_PARTIAL_IMPORT}def make(check):\n    factory = {_CHECKED_PARTIAL}\n    class C:\n"
            f"        factory = {_UNCHECKED_PARTIAL}\n        def build(self):\n            return factory()\n    return C\n",
            "make('the check')().build()\n",
            [("fixture.py", "make.C.build", 8, True)],
        ),
        (
            f"{_PARTIAL_IMPORT}factory = {_UNCHECKED_PARTIAL}\n\ndef make(check):\n    class A:\n"
            f"        factory = {_CHECKED_PARTIAL}\n        class B:\n            made = factory()\n    return A\n",
            "make('the check')\n",
            [("fixture.py", "make.A.B", 9, False)],
        ),
    ],
    ids=[
        "method-skips-class-body",
        "class-body-call",
        "class-body-reverse-shadow",
        "method-resolves-enclosing-function",
        "nested-class-body-skips-outer-class",
    ],
)
def test_a_class_body_does_not_enclose_its_methods(source: str, trigger: str, expected: list) -> None:
    """Review m-5 (WP9.3-2 addendum): a free name in a method or a nested class body resolves from the enclosing
    functions and the module, never from a class body around it; a call in the class body itself does see the class's
    names. Before the fix the first and last cases were false passes and the third and fourth false failures. Each
    case also runs the source with a recording stand-in, so Python itself confirms the expected verdict."""
    assert _service_constructions("fixture.py", source) == expected
    calls: list[object] = []

    def recorder(*args: object, **kwargs: object) -> None:
        calls.append(kwargs.get("binding_check", "unchecked"))

    exec(compile(source + trigger, "fixture.py", "exec"), {"CommandService": recorder, "__name__": "fixture"})
    assert calls == [("the check" if expected[0][3] else "unchecked")]


def _service_name_strings(source: str) -> list[int]:
    """Lines holding the literal string ``CommandService`` outside an import: the backstop for string lookups the
    census cannot resolve (n-3). A string annotation (a forward reference) is a type, not a lookup, so it is skipped.
    A name computed at run time stays outside any AST census (note §18)."""
    tree = ast.parse(source)
    annotations: set[int] = set()
    for node in ast.walk(tree):
        parts: list[ast.AST | None] = []
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            arguments = node.args
            parts.append(node.returns)
            parts += [a.annotation for a in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]]
            parts += [arguments.vararg and arguments.vararg.annotation, arguments.kwarg and arguments.kwarg.annotation]
        elif isinstance(node, ast.AnnAssign):
            parts.append(node.annotation)
        for part in parts:
            if part is not None:
                annotations.update(id(inner) for inner in ast.walk(part))
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and node.value == SERVICE_CLASS and id(node) not in annotations
    ]


def test_no_production_file_names_command_service_in_a_string() -> None:
    """Positive control: no production file outside the defining module holds the class name as a string."""
    hits = [
        f"{relative}:{line}"
        for relative, source in _tracked_python()
        if relative.startswith("research_system/")
        and relative != "research_system/command/service.py"
        and SERVICE_CLASS in source
        for line in _service_name_strings(source)
    ]
    assert hits == []


def test_the_string_backstop_flags_a_lookup_the_census_cannot_resolve() -> None:
    source = "def f(m, suffix):\n    name = 'CommandService'\n    return getattr(m, name)(1)\n"
    assert _service_constructions("fixture.py", source) == []  # the census alone misses it
    assert _service_name_strings(source) == [2]
    annotated = "def f(x: 'CommandService') -> tuple['CommandService', int]:\n    y: 'CommandService' = x\n"
    assert _service_name_strings(annotated) == []


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


def _admits_w9_id(pattern: str, path: list[str]) -> bool:
    """Whether a schema pattern accepts one of W9's own IDs (review i-4).

    A JSON Schema pattern is ECMA-262, so Python's ``re`` may reject a valid one. That fails the census loudly, naming the
    field, rather than reading as "no match" and letting a field escape it (PR #428 review).
    """
    try:
        return any(re.search(pattern, sample) for sample in _W9_SAMPLE_IDS)
    except re.error as exc:
        raise AssertionError(f"schema pattern at {'/'.join(path)} cannot be checked by Python re: {exc}") from exc


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
        if isinstance(pattern, str) and (_ID_PATTERN.match(pattern) or _admits_w9_id(pattern, path)):
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


def test_a_schema_pattern_python_cannot_compile_fails_the_census_naming_its_field() -> None:
    fixture = {
        "$id": "ars://core/event/FixtureCreated",
        "properties": {"payload": {"properties": {"odd_id": {"type": "string", "pattern": "^\\p{L}+$"}}}},
    }
    with pytest.raises(AssertionError, match="schema pattern at payload/odd_id cannot be checked by Python re"):
        _unclassified([fixture])


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
