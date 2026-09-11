"""Checkout-attribute coverage canary for canonical-LF-byte contracts (obs 130).

Why: the contract system declares `canonical_byte_surface: git_blob_utf8_lf`
and several validators hash or compare working-tree bytes against pinned
`*_lf_sha256` values. On a checkout with `core.autocrlf=true` (the Windows
default) git materialises those pure-LF blobs as CRLF unless `.gitattributes`
pins `eol=lf` for their root — and `.gitattributes` was previously grown one
path at a time as each work package hit the failure, leaving whole roots
uncovered until 133 downstream contract-test failures surfaced it at once.

This canary discovers every file that references either marker and asserts
`git check-attr` resolves `eol=lf` for it directly, so a *new* root added in
the future without a matching `.gitattributes` pattern fails here — locally,
immediately, for the right reason — rather than as a wall of hash mismatches.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKERS = ("canonical_byte_surface", "_lf_sha256")

# This file names both markers — in MARKERS above, and throughout the docstring
# explaining them — so an unrestricted scan matches the detector itself and
# reports it as an uncovered marker file. That finding is false: nothing hashes
# or byte-compares this module, so no `eol=lf` pin is owed for it. Left in, the
# canary is permanently red on a green tree, and a real uncovered root arriving
# later reads as "the known failure" rather than as news. Resolved by path so a
# rename carries the exclusion with it.
SELF = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


# Restrict to file types that actually declare or check the byte surface —
# contract/schema definitions and their binding tests — not prose (.md docs,
# handoffs, review write-ups) that merely discusses the concept. A narrative
# mention is not a validator depending on checkout bytes.
SCHEMA_OR_TEST_SUFFIXES = (".yaml", ".yml", ".py")


def _files_referencing_lf_canonical_bytes(*, exclude_self: bool = True) -> list[str]:
    hits: list[str] = []
    for rel in _tracked_files():
        if not rel.endswith(SCHEMA_OR_TEST_SUFFIXES):
            continue
        if exclude_self and rel == SELF:
            continue
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marker in text for marker in MARKERS):
            hits.append(rel)
    return hits


def _check_attr(rel_path: str, attr: str, cwd: Path = REPO_ROOT) -> str:
    out = subprocess.run(
        ["git", "check-attr", attr, "--", rel_path],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    # Format: "<path>: <attr>: <value>"
    return out.rsplit(":", 1)[-1].strip()


@pytest.fixture(scope="module")
def lf_sensitive_files() -> list[str]:
    hits = _files_referencing_lf_canonical_bytes()
    assert hits, (
        "no tracked file references canonical_byte_surface / _lf_sha256 — "
        "either the markers changed or this canary's discovery is broken"
    )
    return hits


def test_every_lf_canonical_byte_marker_file_is_covered_by_gitattributes(
    lf_sensitive_files: list[str],
) -> None:
    uncovered = [rel for rel in lf_sensitive_files if _check_attr(rel, "eol") != "lf"]
    assert not uncovered, (
        "the following files reference a canonical-LF-byte marker but "
        f".gitattributes does not pin eol=lf for them: {uncovered}"
    )


def test_negative_control_the_attribute_reader_still_discriminates() -> None:
    """Proves `_check_attr` reads real state rather than returning "lf" for everything.

    This control used to assert that CONVENTIONS.md resolved to something other than
    `eol=lf`. Since `.gitattributes` gained the repo-wide `* text=auto eol=lf` default,
    no path resolves otherwise, so that assertion could no longer fail for the right
    reason — it would have passed only until the default landed, then broken, and been
    "fixed" by deleting it.

    The discriminating axis is now `text`: a binary-declared path must resolve
    `text: unset` while a source file must not. That is also the property actually worth
    guarding — see test_gitattributes_binary_safety.py for why (99 committed PDFs would
    otherwise be classified as text and have their CR bytes stripped).
    """
    assert _check_attr("example.pdf", "text") == "unset"
    assert _check_attr("example.py", "text") != "unset"


def test_self_exclusion_removes_exactly_this_file_and_nothing_else() -> None:
    """The exclusion must be surgical, or it becomes a hole the canary cannot see through.

    Skipping the detector's own source is only safe while it skips *precisely* that —
    a broader predicate (any file under tests/tools, say, or anything mentioning the
    markers in a docstring) would silently stop covering real binding tests that live
    alongside it. Pin the difference to the single expected path.
    """
    with_self = set(_files_referencing_lf_canonical_bytes(exclude_self=False))
    without_self = set(_files_referencing_lf_canonical_bytes())
    assert with_self - without_self == {SELF}
    assert without_self


def test_negative_control_an_excluded_path_would_still_be_flagged(tmp_path: Path) -> None:
    """Proves the coverage predicate still reports a true positive.

    The canary went red because of a false positive; the failure mode of fixing that is
    a canary which no longer reports true ones. This used to be shown against
    CONVENTIONS.md, which carried no eol pin — but the repo-wide `* text=auto eol=lf`
    default means no path in this repo resolves to anything else, so that formulation
    could no longer fail for the right reason.

    The risk the coverage assertion now guards is not an unpinned root (the default
    covers every root) but a deliberate *exclusion* re-introducing one. Built hermetically
    in a scratch repo, since this repo correctly has no such exclusion to point at.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    (repo / ".gitattributes").write_text("* text=auto eol=lf\nlegacy/** eol=crlf\n", encoding="utf-8", newline="\n")

    assert _check_attr("src/thing.py", "eol", cwd=repo) == "lf"
    assert _check_attr("legacy/thing.py", "eol", cwd=repo) != "lf"

    uncovered = [rel for rel in ["src/thing.py", "legacy/thing.py"] if _check_attr(rel, "eol", cwd=repo) != "lf"]
    assert uncovered == ["legacy/thing.py"]


def test_the_real_contract_roots_are_still_covered() -> None:
    """The 21 files this canary exists for must remain in scope after the exclusion."""
    discovered = _files_referencing_lf_canonical_bytes()
    for root in (".research-system/contracts/", "tests/research_system/"):
        assert any(rel.startswith(root) for rel in discovered), f"no discovered file under {root}"
