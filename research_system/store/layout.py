from __future__ import annotations

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
        codes = [root.resolve(strict=True) for root in code_roots]
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
