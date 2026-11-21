# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 8, §11.1, §11.2, §15)
# Purpose: unit tests for the pure citation extractor, five-class resolution, disambiguation file, and Git isolation.
"""Unit tests for WP9.4-2's citation extractor and ``w9-citation-disambiguation/1`` reader."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.legacy import citations, evidence
from research_system.legacy.reader import git_blob_id


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def _proj(*paths: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, path in enumerate(paths, start=1):
        obs_id = f"obj_00000000-0000-7000-8000-{index:012x}"
        if path.lower().endswith(".json"):
            result[path] = {"pairs": ((obs_id, "headline"), (obs_id, "diagnostics")), "blocker_kind": None}
        else:
            result[path] = {"pairs": ((obs_id, "whole_file"),), "blocker_kind": None}
    return result


def test_extractor_covers_every_design_note_fixture_and_five_class_boundary() -> None:
    """WP9.4 note §11.1 & §15: tokenizer, tail-first order, five classes, templates, scope, and binary report."""
    registered = _proj(
        "results/a/unique.json",
        "results/a/ph_L5000.json",
        "results/a/real_YYYYMMDD.json",
        "results/a/model.npy",
        "results/a/amb.json",
        "results/b/amb.json",
        "results/trajectory_tda_integration/post_audit/04_nulls.json",
        "results/trajectory_tda_bhps/post_audit/04_nulls.json",
        "results/trajectory_tda_bhps_nulls.json",
        "results/xx/data.json",
        "results/yy/data.json",
        "results/zzz/tail_only.json",
        "results/a/backtick.json",
        "results/a/pipe.json",
    )
    root_path = "papers/P01-A-JRSSA/"
    draft_main = "papers/P01-A-JRSSA/drafts/sections/main.tex"
    draft_json = "papers/P01-A-JRSSA/drafts/sections/config.json"
    draft_bin = "papers/P01-A-JRSSA/drafts/figures/plot.png"
    out_of_scope = "papers/P01-A-JRSSA/notes/claim-trace.md"

    main_text = (
        "Literal results/a/unique.json. "
        "Unique basename ph_L5000.json: "
        "Latex \\texttt{results/a/real_YYYYMMDD.json} "
        "Partial unique trajectory_tda_integration/post_audit/04_nulls.json "
        "Absolute /home/u/TDL/results/a/model.npy "
        "Ordinary words results methods unknown_token "
        "Dir results/a/ and extless results/trajectory_tda_integration and known dir results/a "
        "Templates: table1_effects_{date_suffix}.json level1_comparison_YYYYMMDD.json .json "
        "ladder_{survey}_L{landmarks}_B{B}_{date}.json "
        "Tail unknown: results/x_{survey}/never_registered.json "
        "Ambiguous basename amb.json "
        "Ambiguous partial post_audit/04_nulls.json "
        "Tail ambiguous single: results/x_{survey}/tail_only.json "
        "Tail string match: results/trajectory_tda_{survey}_nulls.json "
        "Third ambiguous clause: x/data.json "
        "Unregistered path results/unregistered/ghost.json "
        "Bare unregistered new_result.json "
        "Backtick `results/a/backtick.json` and pipe | results/a/pipe.json |"
    ).encode("utf-8")

    json_payload = {
        "win": "C:\\Users\\steph\\TDL\\results\\a\\unique.json",
        "non_res": "notes/data.json",
        "dis_multi": "amb.json",
    }
    json_bytes = json.dumps(json_payload).encode("utf-8")
    bin_bytes = b"\x89PNG\r\n\x1a\n\xff\xfe\xfd"
    note_bytes = b"Out-of-scope note citing results/a/amb.json and results/missing_in_note.json.\n"

    disambiguation = {
        (draft_main, "/tail_only.json"): ("results/zzz/tail_only.json",),
        (draft_json, "notes/data.json"): "not_a_result",
        (draft_json, "amb.json"): ("results/a/amb.json", "results/b/amb.json"),
    }

    output = citations.extract_citations_from_files(
        root_path=root_path,
        inventory_files=[
            (draft_main, main_text),
            (draft_json, json_bytes),
            (draft_bin, bin_bytes),
            (out_of_scope, note_bytes),
        ],
        registered_results=registered,
        result_directories={"results", "results/a", "results/b"},
        disambiguation=disambiguation,
        disambiguation_blob="d" * 40,
    )

    assert output["cited_files"] == [
        "results/a/amb.json",
        "results/a/backtick.json",
        "results/a/model.npy",
        "results/a/ph_L5000.json",
        "results/a/pipe.json",
        "results/a/real_YYYYMMDD.json",
        "results/a/unique.json",
        "results/b/amb.json",
        "results/trajectory_tda_integration/post_audit/04_nulls.json",
        "results/zzz/tail_only.json",
    ]
    assert ["obj_00000000-0000-7000-8000-000000000004", "whole_file"] in output["cited_family_set"]
    assert output["blockers"] == [
        {"kind": "ambiguous", "citing_path": draft_main, "token": "_nulls.json"},
        {"kind": "ambiguous", "citing_path": draft_main, "token": "amb.json"},
        {"kind": "ambiguous", "citing_path": draft_main, "token": "post_audit/04_nulls.json"},
        {"kind": "ambiguous", "citing_path": draft_main, "token": "x/data.json"},
        {"kind": "unregistered", "citing_path": draft_main, "token": "new_result.json"},
        {"kind": "unregistered", "citing_path": draft_main, "token": "results/unregistered/ghost.json"},
    ]
    assert output["report"]["not_text"] == [draft_bin]
    reported_not_a_file = {(row["citing_path"], row["token"]) for row in output["report"]["not_a_file"]}
    for tok in (
        "results/a/",
        "results/trajectory_tda_integration",
        "results/a",
        ".json",
        "level1_comparison_YYYYMMDD.json",
        "results/x_",
        "/never_registered.json",
        "_L",
        "_B",
    ):
        assert (draft_main, tok) in reported_not_a_file
    assert output["report"]["disambiguated_not_a_result"] == [{"citing_path": draft_json, "token": "notes/data.json"}]
    assert output["report"]["out_of_scope_cited"] == [{"citing_path": out_of_scope, "path": "results/a/amb.json"}]
    assert output["report"]["out_of_scope_other"] == [
        {"kind": "unregistered", "citing_path": out_of_scope, "token": "results/missing_in_note.json"}
    ]
    assert output["cited_family_set_sha256"] == sha256_hex(canonical_bytes(output["cited_family_set"]))

    # Edits to out-of-scope note report do NOT change extractor_output_sha256.
    output2 = citations.extract_citations_from_files(
        root_path=root_path,
        inventory_files=[
            (draft_main, main_text),
            (draft_json, json_bytes),
            (draft_bin, bin_bytes),
            (out_of_scope, b"Completely different note with results/a/ph_L5000.json.\n"),
        ],
        registered_results=registered,
        result_directories={"results", "results/a", "results/b"},
        disambiguation=disambiguation,
        disambiguation_blob="d" * 40,
    )
    assert output2["extractor_output_sha256"] == output["extractor_output_sha256"]
    assert output2["cited_family_set_sha256"] == output["cited_family_set_sha256"]

    # Changing disambiguation_blob changes extractor_output_sha256 even with identical cited set/blockers.
    output3 = citations.extract_citations_from_files(
        root_path=root_path,
        inventory_files=[
            (draft_main, main_text),
            (draft_json, json_bytes),
            (draft_bin, bin_bytes),
            (out_of_scope, note_bytes),
        ],
        registered_results=registered,
        result_directories={"results", "results/a", "results/b"},
        disambiguation=disambiguation,
        disambiguation_blob="e" * 40,
    )
    assert output3["extractor_output_sha256"] != output["extractor_output_sha256"]

    # Deeply nested JSON hits json.loads RecursionError. Its decoded strings cannot be scanned, so a fully
    # \u-escaped result path would go unseen: the scan refuses, for the escaped and the plain spelling alike.
    escaped = "".join(f"\\u{ord(ch):04x}" for ch in "results/a/unique.json").encode("ascii")
    for inner in (b'"results/a/unique.json"', b'"' + escaped + b'"'):
        deep_json = b"[" * 5000 + inner + b"]" * 5000
        with pytest.raises(IntegrityError, match="JSON nested too deeply to scan"):
            citations.scan_file_tokens("papers/P01-A-JRSSA/drafts/deep.json", deep_json)
    # Control: the same escaped path at shallow depth is decoded and scanned.
    shallow_tokens, _ = citations.scan_file_tokens("papers/P01-A-JRSSA/drafts/s.json", b'["' + escaped + b'"]')
    assert shallow_tokens is not None and ("results/a/unique.json", False) in shallow_tokens

    # An unpaired surrogate in a decoded JSON string refuses (it cannot be hashed as UTF-8); a paired one is kept.
    with pytest.raises(IntegrityError, match="unpaired surrogate"):
        citations.scan_file_tokens("papers/P01-A-JRSSA/drafts/u.json", b'["results/\\ud800.json"]')
    paired_tokens, _ = citations.scan_file_tokens(
        "papers/P01-A-JRSSA/drafts/p.json", b'["results/\\ud83d\\ude00.json"]'
    )
    assert paired_tokens is not None and ("results/\U0001f600.json", False) in paired_tokens


def test_extractor_clears_single_reg_tail_with_disambiguation_and_checks_same_file_tokens() -> None:
    """Two tokens with one basename in the same file resolve cleanly by token-keyed rows (C-m2, R7-m3)."""
    registered = _proj(
        "results/trajectory_tda_bhps/05_analysis.json", "results/trajectory_tda_integration/05_analysis.json"
    )
    draft_py = "papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py"
    code = (
        'A = "notes/05_analysis.json"\n'
        'B = "alias/05_analysis.json"\n'
        'T = f"results/x_{survey}/05_analysis.json"\n'
        'U = "results/trajectory_tda_{survey}/post_audit/none.json"\n'
    ).encode("utf-8")
    # Without disambiguation: /05_analysis.json tail blocks even if only one path existed; plus notes/ and alias/ block.
    blocked = citations.extract_citations_from_files(
        root_path="papers/P01-A-JRSSA/",
        inventory_files=[(draft_py, code)],
        registered_results=registered,
    )
    assert {row["token"] for row in blocked["blockers"]} == {
        "/05_analysis.json",
        "alias/05_analysis.json",
        "notes/05_analysis.json",
    }

    cleared = citations.extract_citations_from_files(
        root_path="papers/P01-A-JRSSA/",
        inventory_files=[(draft_py, code)],
        registered_results=registered,
        disambiguation={
            (draft_py, "notes/05_analysis.json"): "not_a_result",
            (draft_py, "alias/05_analysis.json"): (
                "results/trajectory_tda_bhps/05_analysis.json",
                "results/trajectory_tda_integration/05_analysis.json",
            ),
            (draft_py, "/05_analysis.json"): ("results/trajectory_tda_bhps/05_analysis.json",),
        },
    )
    assert cleared["blockers"] == []
    assert cleared["cited_files"] == [
        "results/trajectory_tda_bhps/05_analysis.json",
        "results/trajectory_tda_integration/05_analysis.json",
    ]


def test_extractor_blocks_cited_files_without_accepted_observations_or_tables() -> None:
    """§11.1 item 4: cited result without accepted observation, table, or family produces a blocker entry."""
    registered = {
        "results/unobserved.json": {"pairs": (), "blocker_kind": "unobserved"},
        "results/no_table.json": {"pairs": (), "blocker_kind": "missing_membership_table"},
        "results/partial.json": {
            "pairs": (("obj_00000000-0000-7000-8000-000000000001", "headline"),),
            "blocker_kind": "unobserved_family",
            "missing_families": ("meta",),
        },
    }
    output = citations.extract_citations_from_files(
        root_path="papers/P01-A-JRSSA/",
        inventory_files=[
            (
                "papers/P01-A-JRSSA/drafts/s.md",
                b"results/unobserved.json results/no_table.json results/partial.json\n",
            )
        ],
        registered_results=registered,
    )
    assert output["blockers"] == [
        {"kind": "missing_membership_table", "path": "results/no_table.json"},
        {"kind": "unobserved", "path": "results/unobserved.json"},
        {"kind": "unobserved_family", "path": "results/partial.json", "family_name": "meta"},
    ]


def test_read_citation_disambiguation_validation_and_git_only_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """evidence.read_citation_disambiguation reads from Git at git_head only and validates schema/sorting."""
    root = tmp_path / "repo"
    (root / "papers" / "P01-A-JRSSA" / "drafts").mkdir(parents=True)
    draft_raw = b"See 05_analysis.json\n"
    (root / "papers" / "P01-A-JRSSA" / "drafts" / "s.md").write_bytes(draft_raw)
    _git(root, "init", "-q")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "no-disambig")
    h1 = _git(root, "rev-parse", "HEAD")

    assert evidence.read_citation_disambiguation(root, h1) == ({}, None)

    # Write disambiguation in working tree only: must remain invisible at h1!
    ev_dir = root / evidence.EVIDENCE_DIRECTORY
    ev_dir.mkdir(parents=True)
    dis_file = ev_dir / "citation-disambiguation.json"
    payload = {
        "format": evidence.CITATION_DISAMBIGUATION_FORMAT,
        "entries": [
            {
                "citing_path": "papers/P01-A-JRSSA/drafts/s.md",
                "token": "05_analysis.json",
                "resolution": ["results/a/05_analysis.json", "results/b/05_analysis.json"],
            }
        ],
    }
    dis_bytes = (json.dumps(payload) + "\n").encode("utf-8")
    dis_file.write_bytes(dis_bytes)
    assert evidence.read_citation_disambiguation(root, h1) == ({}, None)

    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "with-disambig")
    h2 = _git(root, "rev-parse", "HEAD")

    # Install replacement ref pointing h2 -> h1: reader must still see h2's committed disambiguation!
    _git(root, "replace", h2, h1)
    loaded, blob = evidence.read_citation_disambiguation(root, h2)
    assert loaded == {
        ("papers/P01-A-JRSSA/drafts/s.md", "05_analysis.json"): (
            "results/a/05_analysis.json",
            "results/b/05_analysis.json",
        )
    }
    assert blob == git_blob_id(dis_bytes)
    with monkeypatch.context() as mp:
        mp.setattr(evidence, "blob_at", lambda *a, **kw: "f" * 40)
        with pytest.raises(
            evidence.EvidenceRefused,
            match="W9 citation disambiguation bytes do not hash to their blob at git_head",
        ):
            evidence.read_citation_disambiguation(root, h2)

    # Bad formats raise EvidenceRefused with each guard's own message (keeping citing_path valid outside path tests).
    disambig_valid_path = "papers/P01-A-JRSSA/drafts/s.md"
    for bad, expected_msg in (
        ({"format": "wrong/1", "entries": []}, "W9 citation disambiguation does not have the fixed format"),
        (
            {"format": evidence.CITATION_DISAMBIGUATION_FORMAT, "entries": [], "extra": 1},
            f"W9 {evidence.CITATION_DISAMBIGUATION} does not have the fixed format",
        ),
        (
            {
                "format": evidence.CITATION_DISAMBIGUATION_FORMAT,
                "entries": [{"citing_path": "../bad.md", "token": "05_analysis.json", "resolution": "not_a_result"}],
            },
            "W9 citation disambiguation entry has invalid citing_path or token",
        ),
        (
            {
                "format": evidence.CITATION_DISAMBIGUATION_FORMAT,
                "entries": [{"citing_path": disambig_valid_path, "token": "05_analysis.json", "resolution": []}],
            },
            "W9 citation disambiguation resolution must be sorted paths or 'not_a_result'",
        ),
        (
            {
                "format": evidence.CITATION_DISAMBIGUATION_FORMAT,
                "entries": [
                    {
                        "citing_path": disambig_valid_path,
                        "token": "05_analysis.json",
                        "resolution": ["results/b/05_analysis.json", "results/a/05_analysis.json"],
                    }
                ],
            },
            "W9 citation disambiguation resolution must be sorted paths or 'not_a_result'",
        ),
        (
            {
                "format": evidence.CITATION_DISAMBIGUATION_FORMAT,
                "entries": [
                    {"citing_path": disambig_valid_path, "token": "05_analysis.json", "resolution": "not_a_result"},
                    {
                        "citing_path": disambig_valid_path,
                        "token": "05_analysis.json",
                        "resolution": ["results/a/05_analysis.json"],
                    },
                ],
            },
            "W9 citation disambiguation names a (citing_path, token) twice",
        ),
        *(
            (
                {
                    "format": evidence.CITATION_DISAMBIGUATION_FORMAT,
                    "entries": [{"citing_path": disambig_valid_path, "token": token, "resolution": "not_a_result"}],
                },
                "W9 citation disambiguation token is not in the scanner's normalised form",
            )
            for token in ("old\\x.npy", "old//x.npy", "old/x.npy.", "old/x.npy:", "old x.npy", "(old/x.npy)")
        ),
    ):
        dis_file.write_bytes((json.dumps(bad) + "\n").encode("utf-8"))
        _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "bad")
        bad_head = _git(root, "rev-parse", "HEAD")
        with pytest.raises(evidence.EvidenceRefused) as exc_info:
            evidence.read_citation_disambiguation(root, bad_head)
        assert str(exc_info.value) == expected_msg

    # F4: deeply nested JSON triggers RecursionError -> EvidenceRefused.
    dis_file.write_bytes(b"[" * 5000 + b"]" * 5000)
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "deep-json")
    deep_head = _git(root, "rev-parse", "HEAD")
    with pytest.raises(evidence.EvidenceRefused, match="W9 evidence file is not JSON"):
        evidence.read_citation_disambiguation(root, deep_head)

    # F5: empty results listing returns set(); failed git ls-tree raises IntegrityError.
    assert citations._git_result_directories(root, h1) == set()
    with pytest.raises(IntegrityError, match="W9 citation extractor cannot list results directories at git_head"):
        citations._git_result_directories(root, "0" * 40)


def test_disambiguation_token_rule_agrees_with_the_scanner() -> None:
    """The reader admits a token exactly when the scanner would emit that token unchanged."""

    assert evidence.SCANNER_DELIMITERS == citations._SINGLE_DELIMITERS
    for token in (
        "old/x.npy",
        "05_analysis.json",
        "results/a/b.csv",
        "old\\x.npy",
        "old//x.npy",
        "old/x.npy.",
        "old/x.npy:",
        "old x.npy",
        "(old/x.npy)",
        "a|b.json",
        "x\ty.npy",
    ):
        assert evidence._is_scanner_token(token) is (citations.tokenize_text(token) == [(token, False)]), token
    assert evidence._is_scanner_token("old/x.npy") is True


def test_extract_citations_reads_git_blobs_at_git_head_and_ignores_live_edits(tmp_path: Path) -> None:
    """extract_citations reads row blobs from Git and result directories from git_head, never the working tree."""
    root = tmp_path / "git_extract"
    (root / "papers" / "P01-A-JRSSA" / "drafts").mkdir(parents=True)
    (root / "results" / "subdir").mkdir(parents=True)
    draft_path = "papers/P01-A-JRSSA/drafts/d.md"
    draft_bytes = b"Citing results/subdir and results/subdir/r.json.\n"
    (root / draft_path).write_bytes(draft_bytes)
    (root / "results" / "subdir" / "r.json").write_bytes(b'{"v": 1}\n')
    _git(root, "init", "-q")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init")
    head = _git(root, "rev-parse", "HEAD")

    # Mutate working tree after commit: extractor must read committed blob only!
    (root / draft_path).write_bytes(b"Uncommitted blocker results/unregistered_live.json\n")

    reg_root_id = "obj_00000000-0000-7000-8000-000000000001"
    reg_res_id = "obj_00000000-0000-7000-8000-000000000002"
    table_id = "obj_00000000-0000-7000-8000-000000000003"
    obs_draft_id = "obj_00000000-0000-7000-8000-000000000004"
    obs_res_id = "obj_00000000-0000-7000-8000-000000000005"
    acc_id = "obj_00000000-0000-7000-8000-000000000006"

    table = {
        "record_id": table_id,
        "record_revision": 1,
        "families": [{"name": "headline"}],
        "unassigned": [],
    }
    table["content_hash"] = hashlib.sha256(b"t").hexdigest()
    inventory = {
        "root_registration_ref": {"id": reg_root_id, "record_revision": 1, "content_hash": "a" * 64},
        "rows": [
            {
                "row_ordinal": 1,
                "repository_path": draft_path,
                "git_blob": git_blob_id(draft_bytes),
                "observation_ref": {"id": obs_draft_id, "record_revision": 1, "content_hash": "b" * 64},
            }
        ],
    }
    legacy = {
        "records": {
            "legacy_path_registration": {
                reg_root_id: {
                    "record_id": reg_root_id,
                    "role": "legacy_manuscript_root",
                    "normalized_path": "papers/P01-A-JRSSA/",
                },
                reg_res_id: {
                    "record_id": reg_res_id,
                    "role": "legacy_research_result",
                    "normalized_path": "results/subdir/r.json",
                },
            },
            "legacy_field_family_membership": {table_id: table},
            "legacy_observation": {
                obs_draft_id: {
                    "record_id": obs_draft_id,
                    "source_identity": {"identity_kind": "git_tracked", "git_blob": git_blob_id(draft_bytes)},
                },
                obs_res_id: {
                    "record_id": obs_res_id,
                    "selector": {
                        "selector_kind": "json_family_set",
                        "membership_ref": {"id": table_id},
                        "family_names": ["headline"],
                    },
                },
            },
            "legacy_closed_reference_acceptance": {
                acc_id: {"record_id": acc_id, "items": [{"observation_ref": {"id": obs_res_id}}]}
            },
        },
        "observations_by_registration": {reg_res_id: [obs_res_id]},
        "supersessions": {},
    }
    res = citations.extract_citations(root, head, inventory, legacy)
    assert res["blockers"] == []
    assert res["cited_family_set"] == [[obs_res_id, "headline"]]
    assert res["report"]["not_a_file"] == [{"citing_path": draft_path, "token": "results/subdir"}]
