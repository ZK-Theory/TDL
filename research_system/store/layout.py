from __future__ import annotations

from pathlib import Path

from research_system.errors import ArsError

_CONTROL_DIRECTORIES = (
    'objects',
    'events',
    'manifests',
    'receipts',
    'snapshots',
    'runtime',
)


def require_external_control_root(
    code_roots: list[Path], control_root: Path
) -> Path:
    if not code_roots:
        raise ArsError('registered code roots required')
    try:
        controls_parent = control_root.parent.resolve(strict=True)
        control = (controls_parent / control_root.name).resolve(strict=False)
        codes = [root.resolve(strict=True) for root in code_roots]
    except OSError as exc:
        raise ArsError('control and code roots must be resolvable') from exc
    for code in codes:
        if control == code or code in control.parents or control in code.parents:
            raise ArsError('control root must be disjoint from every code root')
    for name in _CONTROL_DIRECTORIES:
        (control / name).mkdir(parents=True, exist_ok=True)
    return control
