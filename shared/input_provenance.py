# Research context: TDA-Research/03-Papers/P01-A-JRSSA/_project.md
# Purpose: Pre-dispatch / commit-time input-provenance checking. Verifies that
#   the input files a Task consumes exist on disk and carry the recorded
#   signature (sha256 or vintage date), and that co-consumed inputs share a
#   coherent data vintage. Authored after the Manager-11 B9 dispatch shipped a
#   Task whose OM input (regenerated 2026-05-02) was incoherent with the GMM
#   labels (2026-04-08), moving the ARI from 0.2612 to 0.2062.
"""Input-provenance manifests and the checker shared by both enforcement points.

An *input-provenance manifest* is a YAML data file (not a contract) under
``contracts/manifests/input-provenance/`` declaring the input files a Task
consumes, each with a recorded signature, plus a vintage-coherence bound. Two
enforcement points consume the same manifest:

- **Manager pre-dispatch (R-B):** ``manager_predispatch_check.py`` runs
  :func:`check_manifest` at dispatch time and refuses to issue a Task whose
  inputs are missing or incoherent.
- **Worker commit-time (R-C):** the ``input-provenance-manifest-coherence``
  contract's binding test runs :func:`check_manifest` over every *enforced*
  manifest, so an input that drifts between dispatch and commit fails the
  Worker's own pre-commit gate.

A manifest with ``enforced: false`` documents an expected coherent state that is
not yet satisfied (e.g. an unresolved data-vintage decision); R-B still reports
on it, but the commit gate skips it until it is flipped to ``enforced: true``.

**Two-root rule (git does not preserve mtimes).** A fresh worktree resets every
tracked file's mtime to checkout time, so mtime/``vintage_date`` is meaningless
for committed files; their git-stable signature is the content ``sha256``.
Gitignored intermediates are not in worktrees at all — they live at ``PROJ_ROOT``
(the main checkout) where their mtime reflects real regeneration time. Each
input therefore declares ``root: worktree`` (default; checked under the running
checkout, signed by sha256) or ``root: proj_root`` (checked under the main
checkout, where ``vintage_date`` against mtime is meaningful). Vintage-spread
coherence is computed only across ``proj_root`` inputs for the same reason.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

MANIFEST_DIR = "contracts/manifests/input-provenance"


@dataclass
class InputStatus:
    """Per-input result of checking a manifest entry against disk."""

    path: str
    role: str
    root: str
    exists: bool
    disk_vintage: str | None
    disk_sha256: str | None
    signature_ok: bool
    violations: list[str] = field(default_factory=list)


@dataclass
class ManifestResult:
    """Aggregate result of checking one manifest against disk."""

    manifest_id: str
    task: str | None
    enforced: bool
    inputs: list[InputStatus]
    all_present: bool
    signatures_ok: bool
    coherent: bool
    vintage_spread_days: int | None
    max_vintage_spread_days: int | None
    violations: list[str]

    @property
    def ok(self) -> bool:
        """True when every input is present, signed, and the set is coherent."""
        return self.all_present and self.signatures_ok and self.coherent


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _disk_vintage(path: Path) -> str:
    ts = path.stat().st_mtime
    return _dt.date.fromtimestamp(ts).isoformat()


def resolve_proj_root(repo_root: Path) -> Path:
    """Return the main checkout (``PROJ_ROOT``), even when run from a worktree.

    The main worktree is the parent of git's common dir. Falls back to
    ``repo_root`` if git is unavailable.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return repo_root
    common_dir = Path(out)
    # common dir is <main-checkout>/.git; its parent is the main checkout.
    return common_dir.parent if common_dir.name == ".git" else repo_root


def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate an input-provenance manifest YAML.

    Args:
        path: Path to the manifest YAML.

    Returns:
        The parsed manifest mapping.

    Raises:
        ValueError: If the manifest is malformed (not a mapping, missing
            ``id`` or ``inputs``, or an input lacks ``path``).
    """
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest is not a mapping")
    if "id" not in data or "inputs" not in data:
        raise ValueError(f"{path}: manifest missing required 'id' or 'inputs'")
    if not isinstance(data["inputs"], list) or not data["inputs"]:
        raise ValueError(f"{path}: manifest 'inputs' must be a non-empty list")
    for entry in data["inputs"]:
        if not isinstance(entry, dict) or "path" not in entry:
            raise ValueError(f"{path}: every input entry needs a 'path'")
    return data


def check_manifest(manifest: dict[str, Any], repo_root: Path, proj_root: Path | None = None) -> ManifestResult:
    """Check one manifest's declared inputs against the files on disk.

    Each input declares ``root: worktree`` (default; resolved under ``repo_root``
    and signed by ``sha256``) or ``root: proj_root`` (resolved under the main
    checkout, where ``vintage_date`` against mtime is meaningful). For each
    input: confirm it exists, that its on-disk ``sha256`` matches the recorded
    ``expected.sha256`` (when pinned), and — for ``proj_root`` inputs — that its
    on-disk vintage matches ``expected.vintage_date`` (when pinned). Then confirm
    the ``proj_root`` inputs' vintage spread is within
    ``coherence.max_vintage_spread_days``.

    Args:
        manifest: A parsed manifest mapping (see :func:`load_manifest`).
        repo_root: Checkout the ``worktree``-root ``path`` values resolve under.
        proj_root: Main checkout that ``proj_root``-root inputs resolve under.
            Defaults to :func:`resolve_proj_root` of ``repo_root``.

    Returns:
        A :class:`ManifestResult` aggregating per-input and coherence outcomes.
    """
    coherence = manifest.get("coherence") or {}
    max_spread = coherence.get("max_vintage_spread_days")
    proj_root = proj_root or resolve_proj_root(repo_root)

    statuses: list[InputStatus] = []
    proj_root_vintages: list[_dt.date] = []
    for entry in manifest["inputs"]:
        rel = str(entry["path"])
        role = str(entry.get("role", ""))
        root = str(entry.get("root", "worktree"))
        expected = entry.get("expected") or {}
        base = proj_root if root == "proj_root" else repo_root
        abs_path = base / rel
        exists = abs_path.is_file()
        viols: list[str] = []
        disk_vintage: str | None = None
        disk_sha: str | None = None
        signature_ok = True

        if not exists:
            viols.append(f"missing on disk ({root}): {rel}")
            signature_ok = False
        else:
            disk_vintage = _disk_vintage(abs_path)
            exp_sha = expected.get("sha256")
            if exp_sha:
                disk_sha = _sha256(abs_path)
                if disk_sha != exp_sha:
                    signature_ok = False
                    viols.append(f"sha256 mismatch: disk {disk_sha[:16]}.. != expected {str(exp_sha)[:16]}..")
            exp_vintage = expected.get("vintage_date")
            if root == "proj_root":
                proj_root_vintages.append(_dt.date.fromisoformat(disk_vintage))
                if exp_vintage and disk_vintage != str(exp_vintage):
                    signature_ok = False
                    viols.append(f"vintage mismatch: disk {disk_vintage} != expected {exp_vintage}")
            elif exp_vintage:
                viols.append(
                    "vintage_date is ignored for a worktree-root input (mtime is reset on checkout); pin sha256 instead"
                )

        statuses.append(
            InputStatus(
                path=rel,
                role=role,
                root=root,
                exists=exists,
                disk_vintage=disk_vintage,
                disk_sha256=disk_sha,
                signature_ok=signature_ok,
                violations=viols,
            )
        )

    spread_days: int | None = None
    coherent = True
    if len(proj_root_vintages) >= 2:
        spread_days = (max(proj_root_vintages) - min(proj_root_vintages)).days
        if max_spread is not None and spread_days > int(max_spread):
            coherent = False

    all_present = all(s.exists for s in statuses)
    signatures_ok = all(s.signature_ok for s in statuses)

    violations: list[str] = []
    for s in statuses:
        violations.extend(s.violations)
    if not coherent and spread_days is not None:
        violations.append(
            f"vintage spread {spread_days}d exceeds max_vintage_spread_days {max_spread} across co-consumed inputs"
        )

    return ManifestResult(
        manifest_id=str(manifest.get("id", "<unknown>")),
        task=manifest.get("task"),
        enforced=bool(manifest.get("enforced", False)),
        inputs=statuses,
        all_present=all_present,
        signatures_ok=signatures_ok,
        coherent=coherent,
        vintage_spread_days=spread_days,
        max_vintage_spread_days=(None if max_spread is None else int(max_spread)),
        violations=violations,
    )


def discover_manifests(repo_root: Path) -> list[Path]:
    """Return every manifest YAML under the input-provenance manifest dir."""
    manifest_dir = repo_root / MANIFEST_DIR
    if not manifest_dir.is_dir():
        return []
    return sorted(manifest_dir.glob("*.yaml"))
