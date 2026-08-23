"""Focused controls for directory durability cleanup semantics."""

from pathlib import Path

import pytest

from research_system.store import durability as durability_module


def test_fsync_directory_preserves_primary_fsync_error_when_close_also_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cleanup failure must not replace the failed durability operation."""

    descriptor = 71
    close_attempts: list[int] = []

    monkeypatch.setattr(durability_module.os, "open", lambda *_args, **_kwargs: descriptor)

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("primary fsync failure")

    def fail_close(value: int) -> None:
        close_attempts.append(value)
        raise OSError("descriptor close failure")

    monkeypatch.setattr(durability_module.os, "fsync", fail_fsync)
    monkeypatch.setattr(durability_module.os, "close", fail_close)

    with pytest.raises(OSError, match="primary fsync failure"):
        durability_module.fsync_directory(tmp_path)

    assert close_attempts == [descriptor]


def test_fsync_directory_does_not_retry_a_failed_numeric_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed close is terminal-uncertain and is never retried by integer fd."""

    descriptor = 72
    close_attempts: list[int] = []

    monkeypatch.setattr(durability_module.os, "open", lambda *_args, **_kwargs: descriptor)

    def fail_fsync(_descriptor: int) -> None:
        raise OSError("primary fsync failure")

    def fail_once_then_succeed(value: int) -> None:
        close_attempts.append(value)
        if len(close_attempts) == 1:
            raise OSError("descriptor close failure")

    monkeypatch.setattr(durability_module.os, "fsync", fail_fsync)
    monkeypatch.setattr(durability_module.os, "close", fail_once_then_succeed)

    with pytest.raises(OSError, match="primary fsync failure"):
        durability_module.fsync_directory(tmp_path)

    assert close_attempts == [descriptor]
