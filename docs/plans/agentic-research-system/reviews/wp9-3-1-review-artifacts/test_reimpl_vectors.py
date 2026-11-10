# Research context: docs/plans/agentic-research-system/transition/w9/w9-segmentation-contract-v1.md (owner point I, P-068)
# Purpose: run the accepted contract vectors, tests/tools/test_w9_segmentation.py, verbatim against the reviewer's
# independent re-implementation. The vector file's source is executed here with exactly one line changed: the import of
# the reference tool is replaced by the import of reimpl_segmentation. Any other difference fails the module import.
"""The contract's vectors against ``reimpl_segmentation`` (contract §7, "Independence")."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
VECTORS = REPO_ROOT / "tests" / "tools" / "test_w9_segmentation.py"
sys.path.insert(0, str(HERE))

_ORIGINAL_IMPORT = "import w9_segmentation as seg  # noqa: E402\n"
_SWAPPED_IMPORT = "import reimpl_segmentation as seg  # noqa: E402\nseg.SegmentationError = seg.ReimplError\n"
_TOOLS_PATH = 'sys.path.insert(0, str(REPO_ROOT / "tools"))\n'

_source = VECTORS.read_text(encoding="utf-8")
assert _source.count(_ORIGINAL_IMPORT) == 1, "the vector file's import line changed"
assert _source.count(_TOOLS_PATH) == 1, "the vector file's tools path line changed"
_patched = _source.replace(_ORIGINAL_IMPORT, _SWAPPED_IMPORT).replace(_TOOLS_PATH, "")
VECTOR_SHA256 = hashlib.sha256(VECTORS.read_bytes()).hexdigest()
exec(compile(_patched, str(VECTORS), "exec"), globals())  # noqa: S102 - the accepted vectors, run against the reimpl


def test_reference_tool_was_not_imported() -> None:
    """The vectors ran against the re-implementation, not the reference tool."""
    assert seg.__name__ == "reimpl_segmentation"  # noqa: F821 - bound by the exec above
    assert seg.segment.__module__ == "reimpl_segmentation"  # noqa: F821
