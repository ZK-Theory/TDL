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


def _files_referencing_lf_canonical_bytes() -> list[str]:
    hits: list[str] = []
    for rel in _tracked_files():
        if not rel.endswith(SCHEMA_OR_TEST_SUFFIXES):
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


def _check_attr(rel_path: str, attr: str) -> str:
    out = subprocess.run(
        ["git", "check-attr", attr, "--", rel_path],
        cwd=REPO_ROOT,
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


def test_negative_control_an_unrelated_root_is_not_pinned_to_lf() -> None:
    """Proves the check can fail: CONVENTIONS.md carries no LF-canonical marker and must
    not resolve to eol=lf, or the coverage assertion above would be vacuously true."""
    assert _check_attr("CONVENTIONS.md", "eol") != "lf"
