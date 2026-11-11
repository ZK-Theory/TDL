"""The ``.apm/bus/`` inventory and the ``.apm/`` file-level inventory (WP9.3 note §12.3, §12.4; O-19, O-36, W9-T18).

Both are tools (note §12, §13): they read ``.apm/``, write only the output file the operator names, refuse an output
under ``.apm/``, under the vault, inside a store or inside the repository they read, and open no store. In v1 neither
has a store record (P-071 item 4).

- **The bus inventory** (§12.3; W9 §13.3 item 2): a dated, handle-bound list of the bus directory's files, each with
  its relative path, size and SHA-256. It is the non-import record of the bus, written as a file.
- **The file-level inventory** (§12.4; W9 §13.3 item 5; W9-T18): the tracked ``.apm/`` files at a commit, the untracked
  ``.apm/memory/stage-NN/`` logs and the bus files, each mapped to exactly one closure or one non-import record from
  an operator-supplied closure map. A missing or extra file, a file in two places, a closure item with no accepted
  observation, an observation of no item, or a blocker row left in a closure blocks. File closure is deferred
  (P-071 item 4), so in v1 this is W9-T18's tool, run on synthetic trees.

The closure map, ``w9-apm-closure-map/1`` (a reading recorded in the WP9.3-2 record):
``{"format", "closures": [{"file", "inventory", "observations": [...]}], "non_import": [{"files": [...],
"record": {"kind", "sha256"}}]}``. ``inventory`` and each observation are record files whose ``content_hash`` is
recomputed; a closure's inventory names its file, and each observation names an item row of that inventory.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from research_system.errors import IntegrityError
from research_system.legacy.reader import ReadRefused, _git, handle_bound_read
from research_system.legacy.records import record_content_hash

BUS_FORMAT = "w9-apm-bus-inventory/1"
FILES_FORMAT = "w9-apm-file-inventory/1"
CLOSURE_MAP_FORMAT = "w9-apm-closure-map/1"
_STAGE = re.compile(r"stage-[0-9]+\Z")


def _walk_files(root: Path, start: Path) -> list[str]:
    """Every regular file under ``start``, as a POSIX path relative to ``root``. A linked directory refuses."""

    found = []
    for directory, subdirectories, files in os.walk(start, followlinks=False):
        here = Path(directory)
        for name in subdirectories:
            child = here / name
            if child.is_symlink() or child.is_junction():
                raise IntegrityError(
                    f"W9 .apm inventory meets a linked directory: {child.relative_to(root).as_posix()}"
                )
        found.extend((here / name).relative_to(root).as_posix() for name in files)
    return sorted(found)


def build_bus_inventory(apm_root: Path, *, recorded_at: datetime | None = None) -> dict[str, Any]:
    """§12.3: the bus directory's files, each read handle-bound, with its size and SHA-256.

    Raises:
        IntegrityError: If the bus directory is absent, or a file cannot be read handle-bound (a link, a junction, a
            file with more than one link, or one that changes during its read).
    """

    bus = apm_root / "bus"
    if not bus.is_dir() or bus.is_symlink() or bus.is_junction():
        raise IntegrityError("W9 .apm inventory needs a real bus directory")
    entries = []
    for relative in _walk_files(bus, bus):
        try:
            raw, _, _ = handle_bound_read(bus, relative)
        except ReadRefused as exc:
            raise IntegrityError(f"W9 .apm bus file cannot be read handle-bound: {relative}: {exc}") from exc
        entries.append({"path": relative, "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    moment = (recorded_at or datetime.now(UTC)).astimezone(UTC)
    return {
        "format": BUS_FORMAT,
        "recorded_at": moment.isoformat().replace("+00:00", "Z"),
        "root": ".apm/bus",
        "files": entries,
    }


def apm_universe(repository_root: Path, git_commit: str) -> list[str]:
    """§12.4: the tracked ``.apm/`` files at ``git_commit``, the untracked stage logs, and the bus files."""

    tracked = str(_git(repository_root, "ls-tree", "-r", "-z", "--name-only", git_commit, "--", ".apm"))
    paths = {path for path in tracked.split("\0") if path}
    memory = repository_root / ".apm" / "memory"
    if memory.is_dir():
        for stage in sorted(memory.iterdir()):
            if stage.is_dir() and _STAGE.match(stage.name):
                paths.update(_walk_files(repository_root, stage))
    bus = repository_root / ".apm" / "bus"
    if bus.is_dir():
        paths.update(_walk_files(repository_root, bus))
    return sorted(paths)


def _verified(record: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(record, Mapping) or record.get("content_hash") != record_content_hash(record):
        raise IntegrityError(f"W9 .apm closure map {what} is not at its recomputed content hash")
    return record


def _source_path(record: Mapping[str, Any]) -> Any:
    source = record.get("source_identity", {})
    return source.get("repository_path", source.get("path"))


def build_apm_file_inventory(repository_root: Path, git_commit: str, closure_map: Any) -> dict[str, Any]:
    """§12.4 (W9-T18): map every ``.apm/`` file to exactly one closure or non-import record, and report what blocks.

    Raises:
        IntegrityError: If the closure map is malformed, or a record in it is not at its recomputed content hash.
    """

    if not isinstance(closure_map, Mapping) or set(closure_map) != {"format", "closures", "non_import"}:
        raise IntegrityError("W9 .apm closure map does not have the fixed format")
    if closure_map["format"] != CLOSURE_MAP_FORMAT:
        raise IntegrityError("W9 .apm closure map does not have the fixed format")
    universe = apm_universe(repository_root, git_commit)
    placed: dict[str, int] = {}
    items_missing: list[dict[str, Any]] = []
    items_extra: list[dict[str, Any]] = []
    blockers_left: list[dict[str, Any]] = []
    for closure in closure_map["closures"]:
        if not isinstance(closure, Mapping) or set(closure) != {"file", "inventory", "observations"}:
            raise IntegrityError("W9 .apm closure does not have the fixed format")
        path = str(closure["file"])
        placed[path] = placed.get(path, 0) + 1
        inventory = _verified(closure["inventory"], "inventory")
        if _source_path(inventory) != path:
            raise IntegrityError(f"W9 .apm closure's inventory names another file: {path}")
        rows = inventory.get("rows", [])
        blockers_left += [
            {"file": path, "row_ordinal": row.get("row_ordinal"), "blocker_reason": row.get("blocker_reason")}
            for row in rows
            if row.get("row_kind") == "blocker"
        ]
        items = {row.get("row_ordinal") for row in rows if row.get("row_kind") == "item"}
        observed = set()
        for observation in closure["observations"]:
            selector = _verified(observation, "observation").get("selector", {})
            ordinal = selector.get("row_ordinal")
            if selector.get("inventory_ref", {}).get("id") != inventory.get("record_id") or ordinal not in items:
                items_extra.append({"file": path, "row_ordinal": ordinal})
            else:
                observed.add(ordinal)
        items_missing += [{"file": path, "row_ordinal": ordinal} for ordinal in sorted(items - observed)]
    for record in closure_map["non_import"]:
        if not isinstance(record, Mapping) or set(record) != {"files", "record"}:
            raise IntegrityError("W9 .apm non-import record does not have the fixed format")
        for path in record["files"]:
            placed[str(path)] = placed.get(str(path), 0) + 1
    missing = [path for path in universe if path not in placed]
    extra = sorted(path for path in placed if path not in universe)
    double = sorted(path for path, count in placed.items() if count > 1)
    blocked = bool(missing or extra or double or items_missing or items_extra or blockers_left)
    return {
        "format": FILES_FORMAT,
        "git_commit": git_commit,
        "files": len(universe),
        "blocked": blocked,
        "missing": missing,
        "extra": extra,
        "in_two_places": double,
        "items_missing": items_missing,
        "items_extra": items_extra,
        "blockers_left": blockers_left,
    }


def apm_root_of(path: Path) -> Path:
    """The ``.apm`` directory the operator named, which must be called ``.apm``."""

    resolved = path.resolve()
    if PurePosixPath(resolved.as_posix()).name.lower() != ".apm":
        raise IntegrityError("W9 .apm inventory needs --apm-root to name the .apm directory")
    return resolved
