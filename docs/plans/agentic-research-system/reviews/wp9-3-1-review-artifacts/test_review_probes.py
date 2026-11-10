# Research context: docs/plans/agentic-research-system/reviews/wp9-3-1-review-23f8f737-2026-11-10.md (P-080)
# Purpose: the WP9.3-1 reviewer's asserting probes. Each runs on scratch stores and repositories under tmp_path, or on
# pure functions, and asserts what the code does today. A passing probe confirms the finding it names.
"""Reviewer probes for WP9.3-1 at ``23f8f737``: M-1, M-2, the D-4 delta and a W9 command through the generic writer."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system import cli  # noqa: E402
from research_system.errors import IntegrityError  # noqa: E402
from research_system.legacy.preparers import check_resegmentation, inventory_rows  # noqa: E402
from research_system.legacy.segmentation import segment  # noqa: E402


# --- M-1: ars submit's in-lock recheck disappears for an unadmitted checkout --------------------------------------------


@pytest.mark.slow
def test_m1_after_a_pin_advance_ars_submit_from_the_old_checkout_runs_with_no_recheck(tmp_path, monkeypatch) -> None:
    """On the PR's own v1.2 advance fixture: after the advance, the old checkout is refused by load_current_binding,
    and _foundation_binding_check turns that refusal into "no recheck" instead of a refusal."""
    from research_system.errors import ArsError
    from tests.research_system.factories import PROJECT_ID
    from tests.research_system.integration.test_w9_wp9_3_binding_head import _admit, _pin_intent

    service, intent, predecessor_root, pinned, _ = _pin_intent(tmp_path)
    foundation = predecessor_root / ".research-system" / "config" / "foundation.yaml"
    monkeypatch.setattr(cli, "canonical_foundation_path", lambda: foundation)
    binding = SimpleNamespace(
        project_id=PROJECT_ID, store_identity=service.store_identity, control_root=service.control_root
    )
    # Before the advance, the bound (old) checkout is admitted, so ars submit gets the recheck.
    assert callable(cli._foundation_binding_check(binding))
    assert service.advance(intent)["status"] == "advanced"
    # After it, the old checkout is refused by the code-root check: the W9 and W11 paths stop here.
    with pytest.raises(ArsError) as refused:
        _admit(service, predecessor_root)
    assert isinstance(refused.value, IntegrityError)
    # The generic path does not: the same refusal becomes "no recheck", and ars submit builds CommandService with
    # binding_check=None, so a grant-free VerifyEvidenceDeletion from this checkout is not refused by any recheck.
    assert cli._foundation_binding_check(binding) is None


# --- M-2: LR-011 does not check a "first anchor after" region's resolution ----------------------------------------------

_SOURCE = b"# Title\n\n## a\nlegacy text a\n\n## b\nlegacy text b\n\n## c\nlegacy text c\n"


def _inventory(region: dict, kwargs: dict) -> dict:
    segmented = segment(_SOURCE, "heading_section", level=2, **kwargs)
    return {
        "selector_kind": "heading_section",
        "heading_level": 2,
        "covered_region": region,
        "structural_ranges": [],
        "rows": inventory_rows(segmented, "heading_section"),
        "suppressed_anchors": segmented["suppressed_anchors"],
        "file_facts": segmented["file_facts"],
    }


def _after(after_line: int, first: int, last: int) -> dict:
    import hashlib

    line = _SOURCE.split(b"\n")[after_line - 1] + b"\n"
    return {
        "form": "first_anchor_after",
        "after_line": after_line,
        "after_line_sha256": hashlib.sha256(line).hexdigest(),
        "resolved_first_line": first,
        "resolved_last_line": last,
    }


def test_m2_control_the_true_resolution_is_admitted() -> None:
    """The first anchor after line 1 is line 3; the region runs to line 10, the end."""
    record = _inventory(_after(1, 3, 10), {"region": (3, 10)})
    check_resegmentation(_SOURCE, record)
    assert [row["anchor_text"] for row in record["rows"]] == ["a", "b", "c"]


@pytest.mark.parametrize(
    ("first", "last", "kept"),
    [(6, 10, ["b", "c"]), (3, 5, ["a"]), (6, 8, ["b"])],
    ids=["skips-the-first-anchor", "stops-before-the-end", "both"],
)
def test_m2_a_wrong_resolution_of_first_anchor_after_is_admitted(first: int, last: int, kept: list[str]) -> None:
    """Same after_line and hash, a resolved range that drops items: the LR-011 preparer check passes."""
    record = _inventory(_after(1, first, last), {"region": (first, last)})
    check_resegmentation(_SOURCE, record)  # no IntegrityError: the omission is not detected
    assert [row["anchor_text"] for row in record["rows"]] == kept


def test_m2_control_the_check_does_fire_on_a_wrong_after_line_hash() -> None:
    region = {**_after(1, 3, 10), "after_line_sha256": "0" * 64}
    with pytest.raises(IntegrityError, match="anchor-line hashes"):
        check_resegmentation(_SOURCE, _inventory(region, {"region": (3, 10)}))


# --- A W9 command through the generic writer --------------------------------------------------------------------------


def test_w9_command_types_are_not_generic_commands() -> None:
    """The seven new command bindings must not make CommandService build events for a W9 command."""
    import ast

    source = (REPO_ROOT / "research_system/command/service.py").read_text(encoding="utf-8")
    names = {node.value for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Constant)}
    w9 = {
        "ProposeLegacyRecord",
        "RequestW9AuthorityReview",
        "RecordW9AuthorityReview",
        "ProposeW9AuthorityDecision",
        "ResolveW9AuthorityDecision",
        "RecordLegacyLightInventory",
        "ObserveLegacyRecord",
    }
    assert not w9 & names
