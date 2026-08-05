from __future__ import annotations

import os
import stat
from pathlib import Path

from research_system.errors import ArsError

_CONTROL_DIRECTORIES = (
    "objects",
    "events",
    "manifests",
    "receipts",
    "snapshots",
    "runtime",
)


def require_control_root_disjoint_from_code_roots(code_roots: list[Path], control_root: Path) -> Path:
    """Return the resolved control root, refusing any overlap with a code root.

    The disjointness check alone, with no directory creation, so a caller that merely *binds* to an
    existing store can assert the guarantee without writing to it. Externality is what makes control-store
    records incapable of being authored by a repository commit, so it must be assertable on the read path
    and not only at initialization.

    Args:
        code_roots: Registered code roots the control root must not overlap.
        control_root: Candidate control-store root.

    Returns:
        The resolved control root.

    Raises:
        ArsError: If no code roots are registered, a root is unresolvable, or the control root is, contains,
            or is contained by any code root.
    """
    if not code_roots:
        raise ArsError("registered code roots required")
    try:
        controls_parent = control_root.parent.resolve(strict=True)
        control = (controls_parent / control_root.name).resolve(strict=False)
        # Registered code roots are durable store provenance.  Resolve aliases
        # that still exist, but retain retired absolute paths for the lexical
        # disjointness check instead of making store validation depend on the
        # lifetime of a disposable linked worktree.
        codes = [root.resolve(strict=False) for root in code_roots]
    except OSError as exc:
        raise ArsError("control and code roots must be resolvable") from exc
    for code in codes:
        if control == code or code in control.parents or control in code.parents:
            raise ArsError("control root must be disjoint from every code root")
    return control


def require_external_control_root(code_roots: list[Path], control_root: Path) -> Path:
    control = require_control_root_disjoint_from_code_roots(code_roots, control_root)
    for name in _CONTROL_DIRECTORIES:
        (control / name).mkdir(parents=True, exist_ok=True)
    return control


def _require_physical_control_child(control: Path, name: str) -> None:
    child = control / name
    try:
        metadata = child.lstat()
    except FileNotFoundError as exc:
        raise ArsError(f"control root is missing required directory: {name}") from exc
    except OSError as exc:
        raise ArsError(f"control root required directory is unavailable: {name}") from exc
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & reparse_attribute:
        raise ArsError(f"control root required directory must be a physical child: {name}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ArsError(f"control root required path is not a directory: {name}")
    try:
        resolved_child = child.resolve(strict=True)
        if resolved_child.parent != control or not os.path.samefile(child.parent, control):
            raise ArsError(f"control root required directory is not physically bound to the root: {name}")
    except ArsError:
        raise
    except OSError as exc:
        raise ArsError(f"control root required directory identity is unavailable: {name}") from exc


def require_existing_control_root(code_roots: list[Path], control_root: Path) -> Path:
    """Return an existing control root with every required store directory present.

    This check is deliberately read-only.  Binding and validation callers must
    reject an absent or partial store rather than allowing the initializer to
    repair it as a side effect of loading configuration.
    """
    control = require_control_root_disjoint_from_code_roots(code_roots, control_root)
    if not control.is_dir():
        raise ArsError("control root must be an existing directory")
    for name in _CONTROL_DIRECTORIES:
        _require_physical_control_child(control, name)
    return control
