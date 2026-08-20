from types import SimpleNamespace

import pytest

from research_system.discovery import source_correction
from research_system.discovery.replay.transactions import is_exact_legacy_unclosed_spike_verdict
from research_system.errors import IntegrityError


@pytest.mark.parametrize(
    ("stdout", "expected"),
    (
        (
            "a" * 40 + "\trefs/tags/neurips2024\n",
            "a" * 40,
        ),
        (
            "a" * 40 + "\trefs/tags/neurips2024\n" + "b" * 40 + "\trefs/tags/neurips2024^{}\n",
            "b" * 40,
        ),
    ),
)
def test_resolve_remote_tag_selects_lightweight_or_peeled_commit(
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    expected: str,
) -> None:
    monkeypatch.setattr(
        source_correction,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=stdout, stderr=""),
    )

    assert (
        source_correction.resolve_remote_tag(
            "https://github.com/berenslab/eff-ph.git",
            "refs/tags/neurips2024",
        )
        == expected
    )


@pytest.mark.parametrize(
    "stdout",
    (
        "a" * 40 + "\trefs/tags/neurips2024^{}\n",
        "a" * 40 + "\trefs/tags/neurips2024\n" + "b" * 40 + "\trefs/tags/neurips2024\n",
        "not-an-oid\trefs/tags/neurips2024\n",
        "a" * 40 + "\trefs/tags/other\n",
    ),
)
def test_resolve_remote_tag_rejects_incomplete_or_ambiguous_results(
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
) -> None:
    monkeypatch.setattr(
        source_correction,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=stdout, stderr=""),
    )

    with pytest.raises(IntegrityError, match="not exact"):
        source_correction.resolve_remote_tag(
            "https://github.com/berenslab/eff-ph.git",
            "refs/tags/neurips2024",
        )


@pytest.mark.parametrize(
    "git_ref",
    (
        {"repository_url": None, "resolved_ref": "refs/tags/x", "commit_oid": "a" * 40, "required_paths": []},
        {
            "repository_url": "https://example.test/r.git",
            "resolved_ref": 1,
            "commit_oid": "a" * 40,
            "required_paths": [],
        },
        {
            "repository_url": "https://example.test/r.git",
            "resolved_ref": "",
            "commit_oid": "a" * 40,
            "required_paths": [],
        },
    ),
)
def test_verify_source_correction_rejects_malformed_remote_identity_before_resolution(
    monkeypatch: pytest.MonkeyPatch,
    git_ref: dict[str, object],
) -> None:
    monkeypatch.setattr(
        source_correction,
        "resolve_remote_tag",
        lambda *_args: pytest.fail("malformed identity reached remote resolution"),
    )

    with pytest.raises(IntegrityError, match="remote identity is invalid"):
        source_correction.verify_source_correction_remote({"corrected_git_reference": git_ref})


def test_legacy_unclosed_spike_verdict_is_an_exact_immutable_exception() -> None:
    events = (
        {"event_hash": "a5b04ff1a955a7bfdc764e3e3ede56a0b24aae65c7825f4fd08f5313c22503ca"},
        {"event_hash": "eeb8b10c55994a88f28c53d32c7b0a64caf6c096de3a5a813fe7cc065da11e2d"},
    )

    assert is_exact_legacy_unclosed_spike_verdict(events)
    assert not is_exact_legacy_unclosed_spike_verdict((events[0], {"event_hash": "f" * 64}))
