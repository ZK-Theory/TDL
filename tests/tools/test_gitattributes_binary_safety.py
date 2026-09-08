# Research context: repo hygiene — guards the repo-wide `* text=auto eol=lf` default
# Purpose: prove the default cannot silently corrupt committed binary files.
"""Binary-safety guard for the repo-wide `* text=auto eol=lf` default.

Why: `text=auto` decides text-vs-binary by "no NUL byte in the first 8000 bytes". That
heuristic is wrong for most of this repo's committed PDFs — a sampled figure is 83250
bytes with 110 CRLF pairs and no NUL until well past the 8000-byte mark, so git would
classify it as text and strip its CR bytes on the next normalization, corrupting it.
99 of 160 committed PDFs match that shape.

The repo-wide default is therefore only safe while binary types are declared explicitly.
This is the test that keeps it that way: it guards the hazard the default introduces,
rather than the behaviour the default provides.

Asserted on the checked-out tree, not on a fixed list of extensions, so a newly
committed binary type that nobody thought to declare fails here rather than in a
corrupted artifact months later.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
NUL = b"\x00"
CRLF = b"\r\n"
# git's own text/binary cutoff
PEEK = 8000


def _tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def _blobs(paths: list[str]) -> dict[str, bytes]:
    request = "".join(f"HEAD:{p}\n" for p in paths).encode("utf-8", "surrogateescape")
    proc = subprocess.run(["git", "cat-file", "--batch"], cwd=REPO_ROOT, input=request, capture_output=True, check=True)
    data, out, pos = proc.stdout, {}, 0
    for path in paths:
        newline = data.index(b"\n", pos)
        header = data[pos:newline].decode("utf-8", "replace")
        if header.endswith(("missing", "ambiguous")):
            pos = newline + 1
            continue
        size = int(header.rsplit(" ", 1)[1])
        start = newline + 1
        out[path] = data[start : start + size]
        pos = start + size + 1
    return out


def _check_attr(rel: str, attr: str) -> str:
    out = subprocess.run(
        ["git", "check-attr", attr, "--", rel], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout
    return out.rsplit(":", 1)[-1].strip()


@pytest.fixture(scope="module")
def at_risk_blobs() -> dict[str, bytes]:
    """Committed files that `text=auto` would misclassify as text and then rewrite.

    A file is at risk when it carries CR bytes (so conversion would change it) but has
    no NUL inside git's 8000-byte sniff window (so git will not recognise it as binary).
    """
    paths = _tracked()
    return {rel: blob for rel, blob in _blobs(paths).items() if CRLF in blob and NUL not in blob[:PEEK]}


def test_every_at_risk_file_is_declared_binary_or_is_genuinely_text(at_risk_blobs: dict[str, bytes]) -> None:
    """No file may be both at risk and left to the heuristic.

    Genuine text files carrying CRLF are fine — normalizing them is the point. What must
    not happen is a *binary* file being normalized. The separation is by declaration: an
    at-risk file must either be declared binary (`text: unset`) or be a source/text
    extension where LF conversion is intended.
    """
    text_extensions = {".md", ".py", ".yaml", ".yml", ".json", ".txt", ".sh", ".toml", ".cfg", ".ini", ".r", ".tex"}
    undeclared = [
        rel
        for rel, _ in at_risk_blobs.items()
        if _check_attr(rel, "text") != "unset" and Path(rel).suffix.lower() not in text_extensions
    ]
    assert not undeclared, (
        "these committed files carry CR bytes and have no NUL in git's 8000-byte sniff "
        "window, so `text=auto` will treat them as text and strip the CRs — declare them "
        f"binary in .gitattributes: {undeclared}"
    )


def test_committed_pdfs_are_declared_binary() -> None:
    """The specific class that motivated this guard, asserted by name."""
    pdfs = [rel for rel in _tracked() if rel.lower().endswith(".pdf")]
    assert pdfs, "no committed PDFs found — discovery is broken"
    not_binary = [rel for rel in pdfs if _check_attr(rel, "text") != "unset"]
    assert not not_binary, f"PDFs not declared binary and therefore at risk of CR-stripping: {not_binary}"


def test_negative_control_the_heuristic_really_would_misclassify_these(at_risk_blobs: dict[str, bytes]) -> None:
    """Proves the guard above is not vacuous — the hazard it describes is real here.

    If no committed file were actually at risk, every assertion in this module would pass
    trivially and keep passing after the binary declarations were deleted. Requires at
    least one real at-risk file, and that it is a PDF, matching the surveyed hazard.
    """
    assert at_risk_blobs, "no at-risk files found — the hazard this module guards has changed shape"
    assert any(rel.lower().endswith(".pdf") for rel in at_risk_blobs)


def test_negative_control_an_undeclared_binary_extension_would_be_caught() -> None:
    """Proves the declaration check discriminates, using paths git resolves by pattern.

    `git check-attr` answers for any pathname, existing or not, so this asserts the
    attribute rules themselves: a declared binary extension resolves `text: unset`, an
    undeclared one does not — which is exactly the state the test above rejects.
    """
    assert _check_attr("sample.pdf", "text") == "unset"
    assert _check_attr("sample.parquet", "text") != "unset"
