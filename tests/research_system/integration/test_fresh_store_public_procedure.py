"""The fresh-store procedure through the genuine CLI, with nothing patched (P-058, 2026-10-07, P5-1 and P5-3).

Every SPEC test reaches its scratch store by replacing the foundation seam, restoring by copytree and
hand-writing the binding chain. So no test saw that main could neither create a store the committed
foundation does not name (4c review B-1) nor bind a freshly initialized one (design pass B-2). This
test leaves every seam genuine. It runs ``ars`` as a subprocess from a non-linked scratch clone, whose
own committed foundation is what ``canonical_foundation_path()`` selects:

    reserve -> commit the re-pin in the clone -> store init -> first binding -> spec status

It is the binding test for observations 2026-10-07-every-spec-test-monkeypatched-the-foundation-seam
and 2026-10-07-scratch-spec-stores-bound-by-hand-written-fixtures.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from research_system.authority import authority_bootstrap_sha256
from research_system.canonical import canonical_bytes, sha256_hex
from research_system.ids import new_id
from research_system.store.binding_service import (
    REPAIR_INTENT_SCHEMA_ID,
    RepairStoreBinding,
    StoreBindingService,
)
from research_system.store import current_binding
from research_system.store.current_binding import _ROUTE_RELATIVE_PATH, _SOURCE_RELATIVE_PATHS
from research_system.errors import ConflictError, IntegrityError
from tests.research_system.factories import PROJECT_ID, REPO_ROOT, authority_bootstrap
from tests.research_system.integration.test_current_binding import _git

pytestmark = pytest.mark.slow

_RUN_CLI = (
    "import sys; root = sys.argv.pop(1); sys.path.insert(0, root); import research_system; "
    "assert research_system.__file__.startswith(root), research_system.__file__; "
    "from research_system import cli; raise SystemExit(cli.main(sys.argv[1:]))"
)
_FOUNDATION = Path(".research-system/config/foundation.yaml")


def _clone(destination: Path) -> Path:
    """A non-linked clone of this checkout, including its uncommitted changes, committed in the clone."""
    subprocess.run(
        ["git", "-c", "core.longpaths=true", "clone", "--quiet", "--no-checkout", str(REPO_ROOT), str(destination)],
        check=True,
        capture_output=True,
    )
    for key, value in (
        ("core.longpaths", "true"),
        ("core.autocrlf", "false"),
        ("user.email", "fresh-store@example.invalid"),
        ("user.name", "Fresh store procedure"),
    ):
        _git(destination, "config", key, value)
    _git(destination, "switch", "--quiet", "-c", "main", _git(REPO_ROOT, "rev-parse", "HEAD"))
    status = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    changed = False
    for entry in (item.decode("utf-8") for item in status if item):
        relative = entry[3:]
        source, target = REPO_ROOT / relative, destination / relative
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        elif target.exists():
            target.unlink()
        changed = True
    if changed:
        _git(destination, "add", "-A")
        _git(destination, "commit", "--quiet", "-m", "this checkout's uncommitted changes")
    assert (destination / ".git").is_dir()
    return destination.resolve()


def _ars(clone: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-c", _RUN_CLI, str(clone), *argv],
        cwd=clone,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _ok(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 0, result.stderr[-3000:]
    return json.loads(result.stdout)


def _refused(result: subprocess.CompletedProcess[str], message: str) -> None:
    assert result.returncode != 0, result.stdout
    assert message in result.stderr, result.stderr[-3000:]


def _first_binding_intent(clone: Path, control: Path, origin: Path, store: str, pin: str, key: str) -> dict:
    now = datetime.now(UTC)
    return {
        "schema_id": REPAIR_INTENT_SCHEMA_ID,
        "schema_version": "1.1.0",
        "command_type": "RepairStoreBinding",
        "control_root": str(control),
        "candidate_repository_root": str(clone),
        "expected_project_id": PROJECT_ID,
        "expected_store_identity": store,
        "expected_origin_authority_root": str(origin),
        "expected_origin_witness_sha256": pin,
        "intended_schema_root": str(clone / ".research-system" / "schemas"),
        "stale_evidence_refs": [],
        "spec_route_ref": _ROUTE_RELATIVE_PATH.as_posix(),
        "spec_source_refs": [path.as_posix() for path in _SOURCE_RELATIVE_PATHS],
        "valid_from": (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": (now + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "owner_actor_id": authority_bootstrap()["owner_actor_id"],
        "owner_action": "bind-initialized-store",
        "idempotency_key": key,
        "reason": "bind the freshly initialized store to its durable checkout",
    }


def _event_count(control: Path) -> int:
    return sum(
        len([line for line in path.read_text(encoding="utf-8").splitlines() if line])
        for path in (control / "events").rglob("*.jsonl")
    )


def test_a_fresh_store_is_reserved_pinned_initialized_and_bound_through_the_genuine_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    clone = _clone(tmp_path / "clone")
    control = tmp_path / "control"
    origin = tmp_path / "origin"
    origin.mkdir()
    bootstrap = authority_bootstrap()
    bootstrap_path = tmp_path / "bootstrap.json"
    bootstrap_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-input",
                "schema_version": "1.0.0",
                "approved_bootstrap_sha256": authority_bootstrap_sha256(bootstrap),
                "manifest": bootstrap,
            }
        )
    )
    init_argv = (
        "store", "init", "--code-root", str(clone), "--control-root", str(control),
        "--project-id", PROJECT_ID, "--authority-bootstrap", str(bootstrap_path),
    )  # fmt: skip

    # B-1 premise: the committed foundation names another store, so init refuses before any write.
    _refused(_ars(clone, *init_argv), "canonical foundation origin witness path is not canonical")
    assert not control.exists()

    # Reserve: a stage, its manifest and the witness, and no store.
    foundation_output = tmp_path / "foundation.yaml"
    reserved = _ok(
        _ars(
            clone,
            "store",
            "reserve",
            "--code-root",
            str(clone),
            "--control-root",
            str(control),
            "--origin-authority-root",
            str(origin),
            "--project-id",
            PROJECT_ID,
            "--authority-bootstrap",
            str(bootstrap_path),
            "--foundation-output",
            str(foundation_output),
        )  # fmt: skip
    )
    assert reserved["status"] == "reserved" and not control.exists()
    witness = Path(reserved["origin_witness_path"])
    assert sha256_hex(witness.read_bytes()) == reserved["origin_witness_sha256"]
    assert len(list(tmp_path.glob(".control.authority-stage-*"))) == 1
    assert reserved["foundation"]["code_roots"] == [str(clone)]

    # The re-pin is a commit in the checkout whose foundation the CLI selects.
    shutil.copyfile(foundation_output, clone / _FOUNDATION)
    _git(clone, "add", _FOUNDATION.as_posix())
    _git(clone, "commit", "--quiet", "-m", "re-pin the foundation to the reserved store")

    # Init consumes the reservation under the pin.
    initialized = _ok(_ars(clone, *init_argv))
    assert initialized["store_identity"] == reserved["store_identity"]
    assert initialized["origin_witness_sha256"] == reserved["origin_witness_sha256"]
    assert not list(tmp_path.glob(".control.authority-stage-*"))

    operator = tmp_path / "operator.json"
    operator.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://operations/spec-operator-config",
                "schema_version": "1.0.0",
                "control_root": str(control.resolve()),
                "project_id": PROJECT_ID,
                "store_identity": reserved["store_identity"],
                "route_id": "SPEC-GATE6-RUN-V1",
                "operator_actor_id": new_id("actor"),
                "actor_session_id": "ses_" + new_id("actor").partition("_")[2],
                "authority_grant_id": new_id("authority_grant"),
            }
        )
    )
    # B-2 premise: an initialized store has no binding yet.
    _refused(_ars(clone, "discovery", "spec", "status", "--operator-config", str(operator)), "binding")

    intent = _first_binding_intent(
        clone, control.resolve(), origin.resolve(), reserved["store_identity"], reserved["origin_witness_sha256"],
        "fresh-store-first-binding",
    )  # fmt: skip
    intent_path = tmp_path / "first-binding.json"
    intent_path.write_bytes(canonical_bytes(intent))
    bound = _ok(_ars(clone, "store", "repair-binding", "--intent", str(intent_path)))
    assert bound["status"] == "initial-binding-published"
    assert bound["binding"]["owner_action"] == "bind-initialized-store"
    assert bound["binding"]["git_head"] == _git(clone, "rev-parse", "HEAD")
    events = _event_count(control)

    # The exact retry reads the receipt; nothing is appended.
    retried = _ok(_ars(clone, "store", "repair-binding", "--intent", str(intent_path)))
    assert retried["binding_sha256"] == bound["binding_sha256"] and _event_count(control) == events

    # The SPEC route now reaches the fresh store through the committed foundation.
    status = _ok(_ars(clone, "discovery", "spec", "status", "--operator-config", str(operator)))
    assert isinstance(status, dict)

    # A second first binding, under another key, is refused before any write.
    other = {**intent, "idempotency_key": "fresh-store-second-binding"}
    other_path = tmp_path / "second-binding.json"
    other_path.write_bytes(canonical_bytes(other))
    _refused(_ars(clone, "store", "repair-binding", "--intent", str(other_path)), "a store that has a binding")

    # The initial root joins the origin witness instead of a restore: once a restore appears, it is refused.
    admission = {
        "foundation_path": clone / _FOUNDATION,
        "repository_root": clone,
        "expected_control_root": control.resolve(),
        "expected_project_id": PROJECT_ID,
        "expected_store_identity": reserved["store_identity"],
    }
    assert current_binding.load_current_binding(**admission).binding_sha256 == bound["binding_sha256"]
    forged_restore = {"transaction_id": "forged", "intended_manifest_sha256": "0" * 64}
    monkeypatch.setattr(current_binding, "load_restore_binding_transaction", lambda _root: forged_restore)
    with pytest.raises(IntegrityError, match="origin manifest"):
        current_binding.load_current_binding(**admission)
    assert _event_count(control) == events


def test_reserve_refuses_a_checkout_with_linked_worktrees(tmp_path: Path) -> None:
    clone = _clone(tmp_path / "clone")
    linked = tmp_path / "linked"
    _git(clone, "worktree", "add", "--quiet", "--detach", str(linked), "HEAD")
    origin = tmp_path / "origin"
    origin.mkdir()
    bootstrap = authority_bootstrap()
    bootstrap_path = tmp_path / "bootstrap.json"
    bootstrap_path.write_bytes(
        canonical_bytes(
            {
                "schema_id": "ars://core/authority-bootstrap-input",
                "schema_version": "1.0.0",
                "approved_bootstrap_sha256": authority_bootstrap_sha256(bootstrap),
                "manifest": bootstrap,
            }
        )
    )
    for code_root, message in (
        (clone, "no linked worktrees"),
        (linked.resolve(), "it is a linked Git worktree"),
    ):
        result = _ars(
            clone, "store", "reserve", "--code-root", str(code_root), "--control-root", str(tmp_path / "control"),
            "--origin-authority-root", str(origin), "--project-id", PROJECT_ID,
            "--authority-bootstrap", str(bootstrap_path), "--foundation-output", str(tmp_path / "foundation.yaml"),
        )  # fmt: skip
        _refused(result, message)
    assert not list(origin.rglob("*.json")) and not (tmp_path / "foundation.yaml").exists()


def test_the_first_binding_of_an_initialized_store_refuses_a_restored_store(tmp_path: Path) -> None:
    """A restored store roots its chain through a stale repair; the initial action must not bind it."""
    from tests.research_system.integration.test_store_binding_service import _service_fixture

    service, repair, candidate = _service_fixture(tmp_path, stale=True)
    payload = repair.semantic_payload()
    payload.update(
        schema_id=REPAIR_INTENT_SCHEMA_ID,
        schema_version="1.1.0",
        command_type="RepairStoreBinding",
        stale_evidence_refs=[],
        owner_action="bind-initialized-store",
    )
    intent = RepairStoreBinding.from_mapping(payload)
    assert isinstance(service, StoreBindingService) and candidate.is_dir()
    with pytest.raises(ConflictError, match="a restored store"):
        service.repair(intent)
