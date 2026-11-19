# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (P06, W9)
# Purpose: asserting probes for the independent review of the WP9.4 design note, revision 5 (32755276).
"""Probes for the r5 review. Read-only: Git reads only, scratch repositories under ``tmp_path``; no store is opened.

A probe whose name contains ``defect`` passes because the defect is present.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from research_system.legacy import preparers
from research_system.legacy.reader import LegacyReader, ReadRefused, handle_bound_read
from research_system.legacy.records import (
    OBSERVATION_PREPARER_SET_FIELDS,
    OBSERVATION_READ_DERIVED_FIELDS,
    observation_subject_digest,
)
from research_system.legacy.replay import reducers

sys.path.insert(0, str(Path(__file__).parent))
import r5_extractor as x  # noqa: E402

REPO = Path(__file__).resolve().parents[5]
NOTE = "docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md"
REGISTER = "docs/plans/agentic-research-system/03-decisions-and-open-questions.md"
W9 = REPO / ".research-system/schemas/contracts/w9"
FOUR = {
    "04_nulls_wasserstein_w2_20260407.json",
    "04_nulls_wasserstein_w2_L5000_20260502.json",
    "05_analysis.json",
    "stratified_markov1_W2_L5000_20260502.json",
}


def _git(*args: str, cwd: Path = REPO) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8").stdout


def _note() -> str:
    return _git("show", f"32755276:{NOTE}")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


# --- Subject ------------------------------------------------------------------------------------------------------


def test_subject_revision_5_changes_only_the_note_and_no_code_since_the_base() -> None:
    assert _git("diff", "--name-only", "7bd7d6a6", "32755276").split() == [NOTE]
    assert (
        _git("diff", "--name-only", "4312dc63", "53ac0d64", "--", "research_system", ".research-system", "tools") == ""
    )
    # P-086's commit changes the note's status line only.
    changed = [
        line
        for line in _git("diff", "-U0", "32755276", "53ac0d64", "--", NOTE).splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    assert len(changed) == 2 and "P-086" in changed[1]


# --- §10.2 item 5: the member_path carrier ------------------------------------------------------------------------


def test_member_path_needs_no_command_schema_change_the_payload_is_an_open_object() -> None:
    schema = json.loads((REPO / ".research-system/schemas/core/command.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["payload"] == {"type": "object"}
    assert "member_path" not in OBSERVATION_PREPARER_SET_FIELDS | OBSERVATION_READ_DERIVED_FIELDS


def test_member_path_must_be_stripped_the_observation_schema_is_closed() -> None:
    schema = json.loads((W9 / "legacy-observation.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False and "member_path" not in schema["properties"]
    # Today's prepare_observation strips frozen_copy_ref only: a member_path would reach the record and be refused.
    source = Path(preparers.__file__).read_text(encoding="utf-8")  # prepare_observation and observation_id
    assert (
        source.count('body = {key: deepcopy(value) for key, value in payload.items() if key != "frozen_copy_ref"}') == 2
    )


def test_member_path_is_bound_by_the_derived_id_through_source_identity() -> None:
    base = {
        "registration_ref": {"id": "obj_root"},
        "selector": {"selector_kind": "whole_file"},
        "importer": {"tool_id": "t", "tool_version": "1", "tool_sha256": "0" * 64},
    }
    one = {
        **base,
        "source_identity": {
            "identity_kind": "git_tracked",
            "repository_path": "papers/P01-A-JRSSA/drafts/.gitkeep",
            "git_blob": "e69de29b",
        },
    }
    two = {
        **base,
        "source_identity": {**one["source_identity"], "repository_path": "papers/P01-A-JRSSA/figures/.gitkeep"},
    }
    assert observation_subject_digest(one) != observation_subject_digest(two)


def test_r5_defect_the_carrier_names_repository_path_but_the_root_kind_is_not_pinned_to_git_tracked() -> None:
    schema = json.loads((W9 / "legacy-path-registration.schema.json").read_text(encoding="utf-8"))
    root_clause = next(
        c for c in schema["allOf"] if c["if"]["properties"]["role"].get("const") == "legacy_manuscript_root"
    )
    assert "source_identity_kind" not in root_clause["then"]["properties"]
    # The repository-root branch admits three kinds for any role; only two of them carry repository_path.
    kinds = schema["allOf"][-2]["else"]["properties"]["source_identity_kind"]["enum"]
    assert kinds == ["git_tracked", "untracked_file", "restricted_untracked_file"]
    assert "source_identity_kind" not in _note()[_note().index("### 10.2") : _note().index("### 10.3")]


@pytest.fixture
def scratch_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    member = repo / "papers/P01-A-JRSSA/drafts/v1.md"
    member.parent.mkdir(parents=True)
    member.write_bytes(b"draft\n")
    (repo / "papers/P01-A-JRSSA/notes").mkdir()
    (repo / "papers/P01-A-JRSSA/notes/n.md").write_bytes(b"note\n")
    for args in (("init", "-q"), ("add", "-A"), ("-c", "user.name=r", "-c", "user.email=r@x", "commit", "-qm", "s")):
        _git(*args, cwd=repo)
    return repo, _git("rev-parse", "HEAD", cwd=repo).strip()


def _registration(path: str, kind: str = "git_tracked") -> dict[str, Any]:
    return {"role": "legacy_manuscript_root", "source_identity_kind": kind, "normalized_path": path}


def test_r4_major1_holds_today_the_reader_refuses_the_root_and_a_member_read_is_feasible(scratch_repo) -> None:
    repo, head = scratch_repo
    reader = LegacyReader(repository_root=repo, git_head=head)
    with pytest.raises(ReadRefused):
        reader.read(_registration("papers/P01-A-JRSSA/"))
    # Item 5's read, simulated by naming the member: a git_tracked identity whose repository_path is the member.
    read = reader.read(_registration("papers/P01-A-JRSSA/drafts/v1.md"))
    assert read.source_identity["repository_path"] == "papers/P01-A-JRSSA/drafts/v1.md"
    # For an untracked root kind the same read carries "path", not "repository_path".
    untracked = reader.read(_registration("papers/P01-A-JRSSA/drafts/v1.md", "untracked_file"))
    assert "repository_path" not in untracked.source_identity and untracked.source_identity["path"]


def test_replay_path_rule_today_refuses_a_member_so_reading_1_is_needed() -> None:
    source = {"identity_kind": "git_tracked", "repository_path": "papers/P01-A-JRSSA/drafts/v1.md"}
    registration = {**_registration("papers/P01-A-JRSSA/"), "root_kind": "repository_root"}
    with pytest.raises(Exception, match="kind, root and path"):
        reducers._source_matches_registration(source, registration, {})


def test_item_5_names_every_reader_call_on_option_1s_route() -> None:
    calls = _git("grep", "-n", r"reader\.read(\|\.read(registration)", "--", "research_system/legacy").splitlines()
    sites = {line.split(":")[0] + ":" + line.split(":")[1] for line in calls}
    assert sites == {
        "research_system/legacy/acceptance.py:69",
        "research_system/legacy/inventory.py:141",
        "research_system/legacy/preparers.py:360",
        "research_system/legacy/preparers.py:594",
        "research_system/legacy/preparers.py:633",
        "research_system/legacy/preparers.py:652",
    }
    # inventory.py:141 and preparers.py:360 are the light inventory's (LR-011, LR-014), not a member's route.


# --- §10.2 owner point O: the root's directory identity -----------------------------------------------------------


def test_r4_major2_holds_today_handle_bound_read_refuses_both_forms_of_the_root(scratch_repo) -> None:
    repo, _ = scratch_repo
    for path in ("papers/P01-A-JRSSA/", "papers/P01-A-JRSSA"):
        with pytest.raises(ReadRefused):
            handle_bound_read(repo, path)


def test_owner_point_o_directory_identity_fits_the_schema_and_is_stable_on_windows(scratch_repo) -> None:
    repo, _ = scratch_repo
    root = repo / "papers/P01-A-JRSSA"
    before = os.stat(root, follow_symlinks=False)
    identity = {
        "canonical_target": root.resolve(strict=True).as_posix(),
        "reparse_chain": [],
        "volume_serial_number": str(before.st_dev),
        "stable_file_id": str(before.st_ino),
        "link_count": int(before.st_nlink),
        "case_aliases": [],
        "unicode_aliases": [],
        "short_name_aliases": [],
    }
    schema = json.loads((W9 / "legacy-path-registration.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(identity, {**schema["$defs"]["physicalIdentity"], "$defs": schema["$defs"]})
    (root / "new_subdirectory").mkdir()
    (root / "new_file.md").write_bytes(b"x")
    after = os.stat(root, follow_symlinks=False)
    keys = ("st_dev", "st_ino", "st_nlink")
    if sys.platform == "win32":
        assert before.st_ino != 0 and [getattr(before, k) for k in keys] == [getattr(after, k) for k in keys]
    else:  # POSIX: a directory's link count is 2 + its subdirectories, so it moves with the tree.
        assert after.st_nlink == before.st_nlink + 1


def test_r5_defect_replay_has_no_prefix_collision_check_so_a_file_registration_under_the_root_is_admitted() -> None:
    root = {
        "root_kind": "repository_root",
        "root_id": "repo",
        "normalized_path": "papers/P01-A-JRSSA/",
        "physical_identity": {"canonical_target": "C:/r/papers/P01-A-JRSSA", "stable_file_id": "1"},
    }
    inner = {
        "root_kind": "repository_root",
        "root_id": "repo",
        "normalized_path": "papers/P01-A-JRSSA/_project.md",
        "physical_identity": {"canonical_target": "C:/r/papers/P01-A-JRSSA/_project.md", "stable_file_id": "2"},
    }
    state = {"records": {"legacy_path_registration": {"obj_root": root}}, "proposals": {}}
    assert reducers._registration_conflicts(state, inner, None) is False
    # The schema confines the root role's path, but no other role's path away from the roots.
    schema = (W9 / "legacy-path-registration.schema.json").read_text(encoding="utf-8")
    assert schema.count("papers/P01-A-JRSSA/") == 1
    w11 = (REPO / "docs/plans/agentic-research-system/design/11-portfolio-and-discovery-lifecycle.md").read_text(
        encoding="utf-8"
    )
    assert (
        "resolved-prefix collisions" in w11
        and "prefix" not in _note()[_note().index("**The root registration") :][:2500]
    )


# --- §11.1: the extractor on the real roots -----------------------------------------------------------------------


@pytest.fixture(scope="module")
def runs() -> dict[str, x.Report]:
    return {root: x.run_root(REPO, "32755276", root) for root in ("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/")}


def test_extractor_p01a_drafts_leave_exactly_the_four_ambiguous_names(runs) -> None:
    report = runs["papers/P01-A-JRSSA/"]
    assert report.names("drafts", "ambiguous") == FOUR
    assert report.names("drafts", "unregistered") == set()
    assert report.names("drafts", "no_class") == set()
    assert len(report.cited["drafts"]) == 23
    assert report.names("drafts", "not_a_file") == {
        ".json",
        "results/trajectory_tda_bhps/post_audit/",
        "results/trajectory_tda_bhps/stratified_markov/",
        "results/trajectory_tda_integration/post_audit/",
        "results/trajectory_tda_integration/stratified_markov/",
    }


def test_extractor_p01a_four_names_come_from_two_citing_files_and_token_keyed_rows_clear_them(runs) -> None:
    entries = runs["papers/P01-A-JRSSA/"].classes["drafts"]["ambiguous"]
    citing = {path for path, _ in entries}
    assert citing == {
        "papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py",
        "papers/P01-A-JRSSA/drafts/sections/supplement-S0-null-specification.md",
    }
    registered = x.tracked(REPO, "32755276", "results/")
    rows = {
        (path, token): sorted(p for p in registered if p.endswith("/" + token))[
            : 2 if token != "05_analysis.json" else 1
        ]
        for path, token in entries
    }
    extractor = x.Extractor(registered, x.tracked_dirs(REPO, "32755276", "results/"), disambiguation=rows)
    files = {p: _git("show", f"32755276:{p}").encode() for p in x.tracked(REPO, "32755276", "papers/P01-A-JRSSA/")}
    cleared = extractor.scan(files, "papers/P01-A-JRSSA/")
    assert cleared.names("drafts", "ambiguous") == set() and cleared.names("drafts", "unregistered") == set()


def test_extractor_p01b_drafts_have_no_blocker(runs) -> None:
    report = runs["papers/P01-B-JRSSB/"]
    for klass in ("ambiguous", "unregistered", "no_class"):
        assert report.names("drafts", klass) == set()
    assert report.cited["drafts"] == {
        "results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json",
        "results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json",
    }


def test_extractor_no_candidate_in_no_class_anywhere_and_no_file_is_not_text(runs) -> None:
    for report in runs.values():
        assert report.not_text == set()
        for scope in ("drafts", "other"):
            assert report.names(scope, "no_class") == set()


def test_extractor_string_suffix_reading_gives_the_same_classes(runs) -> None:
    for root, report in runs.items():
        other = x.run_root(REPO, "32755276", root, suffix_mode="string")
        assert other.classes == report.classes and other.cited == report.cited


def test_r5_defect_braces_are_separators_so_the_brace_template_test_is_dead_and_r4m4s_example_splits() -> None:
    template = "see results/trajectory_tda_{survey}/post_audit/04_nulls_wasserstein_w2_20260407.json here"
    assert all("{" not in t and "}" not in t for t in x.tokens(template))
    assert x.tokens(template)[1:4] == [
        "results/trajectory_tda_",
        "survey",
        "/post_audit/04_nulls_wasserstein_w2_20260407.json",
    ]
    registered = [
        "results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json",
        "results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json",
    ]
    extractor = x.Extractor(registered, {"results/trajectory_tda_bhps"})
    # The note says this string is a template (not_a_file). Its fragment is a partial path of two registered files.
    assert extractor.classify("d.md", "/post_audit/04_nulls_wasserstein_w2_20260407.json")[0] == "ambiguous"
    assert extractor.classify("d.md", "results/trajectory_tda_")[0] == "not_a_file"
    # §15's fixture "results/x_{survey}/a.json as not_a_file": with results/x_bhps/a.json registered, the fragment
    # /a.json is a cited file.
    single = x.Extractor(["results/x_bhps/a.json"], set())
    assert x.tokens("results/x_{survey}/a.json") == ["results/x_", "survey", "/a.json"]
    assert single.classify("d.md", "results/x_")[0] == "not_a_file"
    assert not single.candidate("survey")
    assert single.classify("d.md", "/a.json")[0] == "cited"


def test_latex_wrapped_path_is_cited_under_revision_5() -> None:
    registered = ["results/trajectory_tda_robustness/landmark_sensitivity/ph_L5000.json"]
    extractor = x.Extractor(registered, set())
    found = [t for t in x.tokens(r"\texttt{results/trajectory_tda_robustness/landmark_sensitivity/ph_L5000.json}")]
    assert registered[0] in found and extractor.classify("d.tex", registered[0])[0] == "cited"


# --- §23 and P-086 ------------------------------------------------------------------------------------------------


def test_section_23_lists_every_r4_finding_and_every_codrabbit_comment() -> None:
    section = _note()[_note().index("## 23.") :]
    for finding in ("R4-M1", "R4-M2", *[f"R4-m{i}" for i in range(1, 5)], *[f"R4-i{i}" for i in range(1, 6)]):
        assert f"| {finding} |" in section
    assert section.count("| **Fixed") >= 4


def test_p086_matches_section_19_on_e_and_o_and_names_five_readings_for_k() -> None:
    register = _flat(_git("show", f"53ac0d64:{REGISTER}"))
    entry = register[register.index("### P-086") : register.index("## Decision protocol")]
    assert "**and at promotion**" in entry
    assert "five recorded readings" in entry and "`member_path` payload key" in entry
    assert "read the directory handle-bound under W11 §7.3" in entry
    assert "Revision 5 itself has not been reviewed" in entry
