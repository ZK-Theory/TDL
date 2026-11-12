# Research context: docs/plans/agentic-research-system/transition/w9/wp9-3-design-note.md (WP9.3-2 §12.2; D-7; M-4)
# Purpose: the Computational-Log export recheck: the runtime segmenter rechecks an export the reference tool produced.
"""Export recheck controls (WP9.3 note §12.2, §17 "Export recheck"; contract §6.3).

Every log is synthetic and every export is built by the reference implementation, ``tools/w9_segmentation.py``, so
the two implementations agree or the export is void. Nothing reads the live log (L-0b is not authorized).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research_system import cli
from research_system.legacy import evidence
from research_system.legacy.evidence import EvidenceRefused
from research_system.legacy.export_recheck import recheck_cl_export
from tests.research_system.integration.test_w9_legacy_runtime import _tree_bytes
from tests.research_system.unit.test_w9_evidence_acceptance import SYNTHETIC_LOG, git, reference_export

EDITED = SYNTHETIC_LOG.replace(b"Another line.", b"Anothex line.")


def test_a_byte_equal_retained_copy_reproduces() -> None:
    report = recheck_cl_export(reference_export(), SYNTHETIC_LOG)
    assert report["void"] is False
    assert report["rows"]["differing_ordinals"] == []
    assert report["rows"]["exported"] == report["rows"]["rechecked"] > 0
    assert report["rechecked_by"] == "research_system/legacy/segmentation.py"


def test_a_one_byte_change_in_the_retained_copy_voids_the_export() -> None:
    assert len(EDITED) == len(SYNTHETIC_LOG) and EDITED != SYNTHETIC_LOG
    report = recheck_cl_export(reference_export(), EDITED)
    assert report["void"] is True
    assert report["retained_copy_equal"] is False
    assert report["rows"]["differing_ordinals"] == [2]


def test_an_export_naming_another_blob_for_its_retained_copy_is_void() -> None:
    """The copy check compares the Git blob as well as the SHA-256 and length."""
    export = copy.deepcopy(reference_export())
    export["retained_copy"]["git_blob"] = "0" * 40
    report = recheck_cl_export(export, SYNTHETIC_LOG)
    assert report["void"] is True and report["retained_copy_equal"] is False
    assert report["rows"]["differing_ordinals"] == []


def test_a_tampered_exported_row_voids_the_export_naming_its_ordinal() -> None:
    export = copy.deepcopy(reference_export())
    export["segmentation"]["rows"][1]["raw_row_sha256"] = "0" * 64
    report = recheck_cl_export(export, SYNTHETIC_LOG)
    assert report["void"] is True and report["retained_copy_equal"] is True
    assert report["rows"]["differing_ordinals"] == [2]


def test_tampered_suppressed_anchors_or_file_facts_void_the_export() -> None:
    export = copy.deepcopy(reference_export())
    export["segmentation"]["suppressed_anchors"].append({"line": 1})
    assert recheck_cl_export(export, SYNTHETIC_LOG)["suppressed_anchors_equal"] is False
    export = copy.deepcopy(reference_export())
    export["segmentation"]["file_facts"] = {**export["segmentation"]["file_facts"], "line_count": 99}
    report = recheck_cl_export(export, SYNTHETIC_LOG)
    assert report["void"] is True and report["file_facts_equal"] is False


def test_an_export_produced_by_the_runtime_segmenter_is_refused() -> None:
    """Review M-4: the recheck refuses an export whose recorded producer is the runtime segmenter itself."""
    export = reference_export()
    export["producer"] = {"repository_path": "research_system/legacy/segmentation.py", "git_blob": "a" * 40}
    with pytest.raises(EvidenceRefused, match="names the runtime segmenter, which only rechecks it"):
        recheck_cl_export(export, SYNTHETIC_LOG)


def test_an_export_from_another_reference_blob_is_refused() -> None:
    export = reference_export()
    export["producer"] = {**export["producer"], "git_blob": "b" * 40}
    with pytest.raises(EvidenceRefused, match="producer is not the accepted reference implementation"):
        recheck_cl_export(export, SYNTHETIC_LOG)


def test_a_malformed_export_is_refused_before_any_segmentation() -> None:
    export = reference_export()
    del export["classifications"]
    with pytest.raises(EvidenceRefused, match="W9 Computational-Log export does not have the fixed format"):
        recheck_cl_export(export, SYNTHETIC_LOG)


# --- The tool (note §12, §13; "Tools write nothing") ------------------------------------------------------------------


def _repository(tmp_path: Path, retained: bytes = SYNTHETIC_LOG) -> tuple[Path, str]:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    export = reference_export()
    copy_path = root / export["retained_copy"]["repository_path"]
    copy_path.parent.mkdir(parents=True)
    copy_path.write_bytes(retained)
    (root / ".research-system/evidence/w9/cl-export.json").write_text(json.dumps(export), encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "export")
    return root, git(root, "rev-parse", "HEAD")


def _argv(root: Path, commit: str, output: Path, vault: Path) -> list[str]:
    return [
        "legacy",
        "export",
        "recheck",
        "--repository-root",
        str(root),
        "--git-commit",
        commit,
        "--export",
        ".research-system/evidence/w9/cl-export.json",
        "--vault-root",
        str(vault),
        "--output",
        str(output),
    ]


def test_the_tool_rechecks_from_git_and_leaves_its_input_tree_byte_identical(tmp_path: Path) -> None:
    root, commit = _repository(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()
    before = _tree_bytes(root), _tree_bytes(vault)
    # The working tree is never read: an edit there does not change the report.
    copy_path = root / ".research-system/evidence/w9/cl-retained-copy.md"
    copy_path.write_bytes(EDITED)
    edited = _tree_bytes(root), _tree_bytes(vault)
    output = tmp_path / "out" / "report.json"
    output.parent.mkdir()
    assert cli.main(_argv(root, commit, output, vault)) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["void"] is False
    assert (_tree_bytes(root), _tree_bytes(vault)) == edited != before


def test_the_tool_exits_1_on_a_void_export(tmp_path: Path) -> None:
    root, commit = _repository(tmp_path, retained=EDITED)
    vault = tmp_path / "vault"
    vault.mkdir()
    output = tmp_path / "report.json"
    assert cli.main(_argv(root, commit, output, vault)) == 1
    assert json.loads(output.read_text(encoding="utf-8"))["void"] is True


@pytest.mark.parametrize(
    ("where", "message"),
    [
        ("apm", "W9 tool output is under .apm/"),
        ("vault", "W9 tool output is under the vault"),
        ("store", "W9 tool output is inside a store"),
        ("repository", "W9 tool output is inside the repository it reads"),
        ("existing", "W9 tool output already exists"),
    ],
)
def test_the_tool_refuses_each_forbidden_output_before_reading(
    tmp_path: Path, capsys, where: str, message: str
) -> None:
    root, commit = _repository(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()
    store = tmp_path / "store"
    (store / "manifests").mkdir(parents=True)
    (store / "manifests" / "store-identity.json").write_text("{}", encoding="utf-8")
    outputs = {
        "apm": tmp_path / ".APM" / "report.json",
        "vault": vault / "report.json",
        "store": store / "report.json",
        "repository": root / "report.json",
        "existing": tmp_path / "existing.json",
    }
    outputs["existing"].write_text("{}", encoding="utf-8")
    before = _tree_bytes(tmp_path)
    assert cli.main(_argv(root, commit, outputs[where], vault)) == 1
    assert message in capsys.readouterr().err
    assert _tree_bytes(tmp_path) == before


def test_the_tool_refuses_a_commit_or_path_that_could_reach_git_as_an_option(tmp_path: Path, capsys) -> None:
    root, commit = _repository(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()
    for bad in ("HEAD", commit.upper(), commit[:39]):
        assert cli.main(_argv(root, bad, tmp_path / "a.json", vault)) == 1
        assert "W9 export recheck --git-commit needs a lowercase hex object ID" in capsys.readouterr().err
    argv = _argv(root, commit, tmp_path / "b.json", vault)
    for bad in ("../outside.json", "HEAD:x", "/abs.json"):  # argparse itself refuses a value starting with "-"
        argv[argv.index("--export") + 1] = bad
        assert cli.main(argv) == 1
        assert "W9 export recheck --export is not a repository-relative path" in capsys.readouterr().err
    assert not (tmp_path / "a.json").exists() and not (tmp_path / "b.json").exists()


def test_the_export_file_name_is_left_to_the_accepted_entry() -> None:
    """The W9 paths addendum leaves the export's file name open: the recheck takes the path the operator names, and
    evidence.py fixes only the format."""
    assert not hasattr(evidence, "CL_EXPORT")
    assert evidence.CL_EXPORT_FORMAT == "w9-cl-export/1"
