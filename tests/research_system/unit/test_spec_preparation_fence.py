from __future__ import annotations

import threading
from pathlib import Path

import pytest

from research_system.command.service import CommandService
from research_system.errors import ConflictError
from research_system.store.spec_preparation_fence import SpecPreparationFence
from tests.research_system.factories import control_plane


def test_spec_preparation_fence_is_reentrant_but_rejects_a_competing_writer(tmp_path: Path) -> None:
    """Nested public writers share the saga fence; another writer cannot."""

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    result: list[BaseException | None] = []

    def contend() -> None:
        try:
            with SpecPreparationFence(tmp_path):
                result.append(None)
        except BaseException as error:  # the result is asserted by the owning thread
            result.append(error)

    with SpecPreparationFence(tmp_path):
        with SpecPreparationFence(tmp_path):
            assert (runtime / "spec-preparation.lock").is_file()
        contender = threading.Thread(target=contend)
        contender.start()
        contender.join(timeout=5)
        assert not contender.is_alive()
        assert len(result) == 1
        assert isinstance(result[0], ConflictError)

    assert not (runtime / "spec-preparation.lock").exists()
    with SpecPreparationFence(tmp_path):
        assert (runtime / "spec-preparation.lock").is_file()


def test_command_service_startup_recovery_cannot_bypass_an_active_spec_saga(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Startup marker recovery enters the same fence before any recovery write."""

    harness = control_plane(tmp_path, auto_authority=False)
    calls: list[str] = []

    def recover_scoped(_service: CommandService) -> None:
        calls.append("scoped")

    def recover_owner(_service: CommandService) -> None:
        calls.append("owner")

    monkeypatch.setattr(CommandService, "_recover_scoped_activation_markers", recover_scoped)
    monkeypatch.setattr(CommandService, "_recover_owner_publication_markers", recover_owner)
    result: list[BaseException | None] = []

    def construct_contender() -> None:
        try:
            CommandService(
                harness.service.control_root,
                harness.ledger,
                harness.objects,
                harness.receipts,
                harness.schemas,
                authority_resolver=harness.authority_resolver,
                clock=harness.service.clock,
            )
            result.append(None)
        except BaseException as error:  # asserted by the owning thread
            result.append(error)

    with SpecPreparationFence(harness.service.control_root):
        contender = threading.Thread(target=construct_contender)
        contender.start()
        contender.join(timeout=5)
        assert not contender.is_alive()
        assert len(result) == 1
        assert isinstance(result[0], ConflictError)
        assert calls == []

    CommandService(
        harness.service.control_root,
        harness.ledger,
        harness.objects,
        harness.receipts,
        harness.schemas,
        authority_resolver=harness.authority_resolver,
        clock=harness.service.clock,
    )
    assert calls == ["scoped", "owner"]
