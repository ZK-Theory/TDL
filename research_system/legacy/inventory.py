# Research context: docs/plans/agentic-research-system/03-decisions-and-open-questions.md (P-082 item 5; review M-3)
# Purpose: the light-inventory builder and its reproduction mode for LR-011 and LR-013 (WP9.3 note §8.3, §12.1).
"""The light-inventory builder and its reproduction mode (WP9.3 note §8.3, §12.1; P-082 item 5, review M-3).

**Build mode** produces an LR-011 proposal's content from the bytes of a registered source. It reads through the
preparer's own reader, segments with the runtime segmenter, records the covered region's declaration together with its
resolution, and then checks its own output with LR-011's check (``check_resegmentation``). So a built proposal is one
the preparer admits on the same bytes.

**Reproduction mode** re-segments given bytes (the Git blob, or the frozen copy) against a recorded or proposed
inventory, and reports row-by-row equality. LR-013's reproducer reads that report.

Neither mode opens a store, computes an observation ID (that needs the store's projection; ``ars legacy
observation-id`` does it, note §13), or derives an ownership list. The ownership list belongs to a batch, which is
WP9.3-2's (note §10.5).
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.ids import new_id
from research_system.legacy.preparers import (
    after_line_sha256,
    anchor_line_sha256s,
    check_resegmentation,
    inventory_rows,
    segment_kwargs,
)
from research_system.legacy.reader import LegacyReader
from research_system.legacy.records import pre_assigned_ref
from research_system.legacy.segmentation import CONTRACT_ID, SegmentationError, resolve_first_anchor_after, segment


INVENTORY_SCHEMA_ID = "ars://legacy/legacy-light-inventory"
INVENTORY_SCHEMA_VERSION = "1.0.0"
# Note §8.3 and contract §3: only these two selectors take a declared region; the others have fixed regions.
DECLARED_REGION_SELECTORS = frozenset({"heading_section", "computational_log_entry"})
_FROZEN_COPY_KINDS = frozenset({"untracked_file", "vault_file"})


def _covered_region(
    raw: bytes,
    selector_kind: str,
    region: tuple[Any, ...] | None,
    *,
    heading_level: int | None,
    structural: Sequence[tuple[int, int]],
) -> tuple[dict[str, Any], tuple[int, int] | None]:
    """The declaration to record, and the line range to segment over (``None`` for the selector's whole region)."""

    if region is None:
        if selector_kind == "heading_section":
            raise IntegrityError("W9 heading_section inventory declares its covered region")
        return {"form": "fixed_by_selector"}, None
    if selector_kind not in DECLARED_REGION_SELECTORS:
        raise IntegrityError(f"W9 {selector_kind} inventory has a fixed region and declares none")
    form = region[0]
    if form == "line_range" and len(region) == 3:
        return {"form": "line_range", "first_line": region[1], "last_line": region[2]}, (region[1], region[2])
    if form == "first_anchor_after" and len(region) == 2:
        after_line = region[1]
        try:
            first, last = resolve_first_anchor_after(
                raw, selector_kind, after_line, level=heading_level, structural=structural
            )
        except SegmentationError as exc:
            raise IntegrityError(f"W9 inventory region cannot be resolved: {exc}") from exc
        declaration = {
            "form": "first_anchor_after",
            "after_line": after_line,
            "after_line_sha256": after_line_sha256(raw, after_line),
            "resolved_first_line": first,
            "resolved_last_line": last,
        }
        return declaration, (first, last)
    raise IntegrityError(f"W9 inventory region is not a known form: {region!r}")


def build_light_inventory(
    registration: Mapping[str, Any],
    *,
    reader: LegacyReader,
    selector_kind: str,
    observer_actor_id: str,
    project_id: str,
    heading_level: int | None = None,
    region: tuple[Any, ...] | None = None,
    structural_ranges: Sequence[tuple[int, int]] = (),
    frozen_copy_ref: Mapping[str, Any] | None = None,
    record_id: str | None = None,
    review_id: str | None = None,
) -> dict[str, Any]:
    """Build an LR-011 ``ProposeLegacyRecord`` payload for a light inventory (note §8.3, §12.1).

    Args:
        registration: The recorded LR-003 registration the source is read under.
        reader: The reader, bound to the repository, its ``git_head`` and the vault root.
        selector_kind: One of the contract's six selector kinds.
        observer_actor_id: The observer, who proposes the inventory (LR-011) and records it (LR-014).
        project_id: The store's project.
        heading_level: The heading level k, for ``heading_section``.
        region: ``None`` for the selector's fixed region (or the whole page of ``computational_log_entry``);
            ``("line_range", first, last)``; or ``("first_anchor_after", after_line)``, which the builder resolves.
        structural_ranges: Declared structural ranges, 1-based and inclusive.
        frozen_copy_ref: The frozen copy's artefact ref, required for ``untracked_file`` and ``vault_file``.
        record_id: The record ID; a fresh one when omitted.
        review_id: The pre-assigned reproduction review's ID; a fresh one when omitted.

    Returns:
        The payload, without the preparer-set fields (``created_by_actor_id``, ``created_at``, ``content_hash``).

    Raises:
        IntegrityError: If the selector's level or structural ranges break the record schema's rule, the source cannot
            be read, the region cannot be resolved or segmented, a frozen copy ref is missing or not allowed, or the
            built inventory fails LR-011's re-segmentation check.
    """

    # WP9.3-1b review i-1: the record schema's selector rule, before any read, so no proposal the schema refuses is
    # handed out. Only heading_section takes a heading level and structural ranges, and it requires the level.
    if selector_kind == "heading_section":
        if heading_level is None:
            raise IntegrityError("W9 heading_section inventory declares its heading level")
        if isinstance(heading_level, bool) or not isinstance(heading_level, int) or not 1 <= heading_level <= 6:
            raise IntegrityError("W9 heading_section inventory heading level is outside 1 to 6")
    elif heading_level is not None or structural_ranges:
        raise IntegrityError(f"W9 {selector_kind} inventory takes no heading level and no structural ranges")
    read = reader.read(registration)
    source_identity = dict(read.source_identity)
    kind = source_identity.get("identity_kind")
    if kind in _FROZEN_COPY_KINDS:
        if frozen_copy_ref is None:
            raise IntegrityError("W9 untracked or vault source needs its frozen copy ref")
        source_identity["frozen_copy_ref"] = deepcopy(dict(frozen_copy_ref))
    elif frozen_copy_ref is not None:
        raise IntegrityError("W9 source of this kind carries no frozen copy")
    structural = [(int(first), int(last)) for first, last in structural_ranges]
    covered_region, _ = _covered_region(
        read.raw, selector_kind, region, heading_level=heading_level, structural=structural
    )
    record_id = record_id or new_id("scope_definition")
    record: dict[str, Any] = {
        "schema_id": INVENTORY_SCHEMA_ID,
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "record_id": record_id,
        "record_revision": 1,
        "supersedes_revision": None,
        "project_id": project_id,
        "registration_ref": {
            "id": registration["record_id"],
            "record_revision": registration["record_revision"],
            "content_hash": registration["content_hash"],
        },
        "source_identity": source_identity,
        "segmentation_contract": CONTRACT_ID,
        "selector_kind": selector_kind,
        "heading_level": heading_level,
        "covered_region": covered_region,
        "structural_ranges": [{"first_line": first, "last_line": last} for first, last in structural],
        "read_started_at": read.read_started_at,
        "read_ended_at": read.read_ended_at,
        "path_form": read.path_form,
        "observer_actor_id": observer_actor_id,
    }
    try:
        segmented = segment(read.raw, selector_kind, **segment_kwargs(record))
    except SegmentationError as exc:
        raise IntegrityError(f"W9 inventory source cannot be segmented: {exc}") from exc
    if covered_region["form"] == "line_range":
        covered_region["anchor_line_sha256s"] = anchor_line_sha256s(segmented)
    record["suppressed_anchors"] = segmented["suppressed_anchors"]
    record["file_facts"] = segmented["file_facts"]
    record["rows"] = inventory_rows(segmented, selector_kind)
    record["independent_reproduction_ref"] = pre_assigned_ref("review", review_id or new_id("review"), record_id)
    # LR-011's re-segmentation check on the builder's own output; the schema's selector rule ran before the read.
    check_resegmentation(read.raw, record)
    return record


def reproduce_light_inventory(record: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
    """Re-segment the source bytes against an inventory and report row-by-row equality (note §12.1; LR-013).

    A difference is reported, not raised, because LR-013's reproducer reads the report and records its verdict.

    Args:
        record: The inventory (a proposal or a recorded record).
        raw: The source bytes: the Git blob for ``git_tracked``, or the frozen copy.

    Returns:
        ``reproduced`` (every check equal), the row comparison by ordinal, the suppressed anchors, the file facts, and
        the region declaration's hashes and resolution.

    Raises:
        IntegrityError: If the bytes are not the inventory's source (SHA-256 or length).
    """

    source = record.get("source_identity", {})
    if sha256_hex(raw) != source.get("sha256") or len(raw) != source.get("byte_length"):
        raise IntegrityError("W9 reproduction bytes are not the inventory's source")
    selector_kind = str(record.get("selector_kind"))
    report: dict[str, Any] = {"selector_kind": selector_kind, "segmentation_contract": CONTRACT_ID}
    try:
        segmented = segment(raw, selector_kind, **segment_kwargs(record))
    except SegmentationError as exc:
        return {**report, "reproduced": False, "segmentation_error": str(exc)}
    expected = list(record.get("rows", []))
    observed = inventory_rows(segmented, selector_kind)
    differing = [
        ordinal
        for ordinal in range(1, max(len(expected), len(observed)) + 1)
        if (expected[ordinal - 1] if ordinal <= len(expected) else None)
        != (observed[ordinal - 1] if ordinal <= len(observed) else None)
    ]
    region = dict(record.get("covered_region", {}))
    form = region.get("form")
    hashes_equal: bool | None = None
    resolution_equal: bool | None = None
    if form == "line_range":
        hashes_equal = region.get("anchor_line_sha256s") == anchor_line_sha256s(segmented)
    elif form == "first_anchor_after":
        after = region.get("after_line")
        hashes_equal = region.get("after_line_sha256") == after_line_sha256(raw, after)
        try:
            resolved = resolve_first_anchor_after(raw, selector_kind, after, **_level_and_structure(record))
        except (SegmentationError, TypeError):
            resolved = None
        resolution_equal = (region.get("resolved_first_line"), region.get("resolved_last_line")) == resolved
    suppressed_equal = segmented["suppressed_anchors"] == record.get("suppressed_anchors")
    facts_equal = segmented["file_facts"] == record.get("file_facts")
    reproduced = (
        not differing
        and suppressed_equal
        and facts_equal
        and hashes_equal is not False
        and resolution_equal is not False
    )
    return {
        **report,
        "reproduced": reproduced,
        "rows": {"expected": len(expected), "observed": len(observed), "differing_ordinals": differing},
        "suppressed_anchors_equal": suppressed_equal,
        "file_facts_equal": facts_equal,
        "region": {"form": form, "hashes_equal": hashes_equal, "resolution_equal": resolution_equal},
    }


def refuse_tool_output(output: Path, *, repository_root: Path | None, vault_root: Path) -> Path:
    """Note §12: a tool writes only to an output path the operator names, never under ``.apm/``, the vault or a store.

    The output must also lie outside the repository the tool reads (a reading recorded in the WP9.3-1b record): a file
    written there would change the input tree, which §17's "Tools write nothing" row forbids, and would make the
    reader's dual Git read refuse. It must not exist yet. Every check runs before any input is read.

    The vault check is unconditional (WP9.3-1b review m-3): a tool cannot know the vault unless it is told, so every
    tool takes the vault root and checks it. Paths are resolved, so the repository's ``vault/`` junction, which
    resolves out of the repository, is caught as the vault.

    Args:
        output: The output path the operator named.
        repository_root: The repository the tool reads, if any.
        vault_root: The real vault path, always required.

    Returns:
        The resolved output path.

    Raises:
        IntegrityError: Naming the first rule the path breaks.
    """

    resolved = output.resolve()
    if any(part.lower() == ".apm" for part in resolved.parts):
        raise IntegrityError(f"W9 tool output is under .apm/: {output}")
    if not isinstance(vault_root, Path):
        raise IntegrityError("W9 tool output guard needs the vault root")
    if resolved.is_relative_to(vault_root.resolve()):
        raise IntegrityError(f"W9 tool output is under the vault: {output}")
    for directory in resolved.parents:
        # lexists: a manifest path that is a directory or a dangling link still marks a store.
        if os.path.lexists(directory / "manifests" / "store-identity.json"):
            raise IntegrityError(f"W9 tool output is inside a store: {output}")
    if repository_root is not None and resolved.is_relative_to(repository_root.resolve()):
        raise IntegrityError(f"W9 tool output is inside the repository it reads: {output}")
    if os.path.lexists(resolved):
        raise IntegrityError(f"W9 tool output already exists: {output}")
    return resolved


def write_tool_output(resolved: Path, value: Any) -> None:
    """Write canonical JSON to a path ``refuse_tool_output`` returned, never replacing a file."""
    with resolved.open("xb") as handle:
        handle.write(canonical_bytes(value))


def _level_and_structure(record: Mapping[str, Any]) -> dict[str, Any]:
    """The level and structural ranges a record declares, without its region, as the resolution takes them."""
    kwargs = segment_kwargs(record)
    kwargs.pop("region", None)
    return kwargs
