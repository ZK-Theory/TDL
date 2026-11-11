"""The Computational-Log export recheck (WP9.3 note §12.2; D-7; segmentation contract §6.3; review M-4).

The export and its check come from two implementations. The reference implementation, ``tools/w9_segmentation.py`` at
blob ``43e1454d`` (P-068), produces the export at L-0b, which is not authorized here. WP9.3 adds no export mode. This
module is the recheck: the runtime segmenter re-segments the retained copy and compares every row, the file facts and
the suppressed anchors with the committed export. Any mismatch reports the export void (contract §6.3). An export whose
recorded producer is the runtime segmenter itself, or any producer but the accepted reference blob, is refused, so a
defect in one module can never certify its own hashes.

The recheck is a tool (note §12, §13): it reads the export and its retained copy from Git, writes only the report the
operator names, and opens no store.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from research_system.legacy.evidence import (
    CL_EXPORT_PRODUCER,
    RUNTIME_SEGMENTER_PATH,
    EvidenceRefused,
    require_cl_export,
)
from research_system.legacy.reader import git_blob_id
from research_system.legacy.segmentation import SegmentationError, segment

REPORT_FORMAT = "w9-cl-export-recheck/1"


def recheck_cl_export(export: Any, retained_raw: bytes) -> dict[str, Any]:
    """Re-segment the retained copy with the runtime segmenter and compare it with the export, row by row.

    Args:
        export: The committed export, in ``w9-cl-export/1``.
        retained_raw: The retained copy's bytes, as committed.

    Returns:
        A report: ``void`` is true when anything differs, and the report says what.

    Raises:
        EvidenceRefused: If the export is malformed, or its producer is not the accepted reference implementation.
    """

    body = require_cl_export(export)
    producer = body["producer"]
    if producer.get("repository_path") == RUNTIME_SEGMENTER_PATH:
        raise EvidenceRefused("W9 Computational-Log export names the runtime segmenter, which only rechecks it")
    if dict(producer) != dict(CL_EXPORT_PRODUCER):
        raise EvidenceRefused("W9 Computational-Log export's producer is not the accepted reference implementation")
    copy = body["retained_copy"]
    copy_equal = (
        hashlib.sha256(retained_raw).hexdigest() == copy["sha256"]
        and len(retained_raw) == copy["byte_length"]
        and git_blob_id(retained_raw) == copy["git_blob"]
    )
    region = body["selector"]["region"]
    expected: Mapping[str, Any] = body["segmentation"]
    try:
        observed = segment(retained_raw, "computational_log_entry", region=(region["first_line"], region["last_line"]))
    except SegmentationError as exc:
        return {
            "format": REPORT_FORMAT,
            "void": True,
            "retained_copy_equal": copy_equal,
            "segmentation_error": str(exc),
        }
    expected_rows, observed_rows = list(expected["rows"]), list(observed["rows"])
    differing = [
        index + 1
        for index in range(max(len(expected_rows), len(observed_rows)))
        if index >= len(expected_rows) or index >= len(observed_rows) or expected_rows[index] != observed_rows[index]
    ]
    facts_equal = expected["file_facts"] == observed["file_facts"]
    suppressed_equal = expected["suppressed_anchors"] == observed["suppressed_anchors"]
    hashes_equal = (
        expected["file_sha256"] == observed["file_sha256"] and expected["file_bytes"] == observed["file_bytes"]
    )
    return {
        "format": REPORT_FORMAT,
        "void": not (copy_equal and hashes_equal and facts_equal and suppressed_equal and not differing),
        "retained_copy_equal": copy_equal,
        "file_hash_equal": hashes_equal,
        "rows": {"exported": len(expected_rows), "rechecked": len(observed_rows), "differing_ordinals": differing},
        "file_facts_equal": facts_equal,
        "suppressed_anchors_equal": suppressed_equal,
        "rechecked_by": RUNTIME_SEGMENTER_PATH,
    }
