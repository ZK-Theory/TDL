# Research context: docs/plans/agentic-research-system/reviews/wp9-4-design-note-r4-review-7bd7d6a6-2026-11-19.md (P-085)
# Purpose: the r4 reviewer's asserting probes for the WP9.4 design note, revision 4 (7bd7d6a6). Stores and Git
# repositories are scratch ones under tmp_path; papers/ and results/ are read through Git only. A probe whose name
# contains ``defect`` passes while the defect it names is present (in the code at 7bd7d6a6, or in the note as written).
"""R4 review probes for the WP9.4 design note, revision 4, at ``7bd7d6a6``.

Run from the repository root:

    uv run --extra dev python -m pytest --no-cov -q -p no:cacheprovider \
        docs/plans/agentic-research-system/reviews/wp9-4-design-note-r4-review-artifacts/
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from research_system.errors import IntegrityError  # noqa: E402
from research_system.legacy import acceptance, preparers  # noqa: E402
from research_system.legacy.reader import LegacyReader, ReadRefused  # noqa: E402
from research_system.legacy.records import (  # noqa: E402
    OBSERVATION_PREPARER_SET_FIELDS,
    OBSERVATION_READ_DERIVED_FIELDS,
    record_content_hash,
)
from research_system.legacy.replay import reducers  # noqa: E402

REVIEWED = "7bd7d6a6e69be23670b152de7d57e247e9da1014"
REVISION_3 = "ede231e5"
CODE_BASE = "4312dc63"
NOTE = "docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md"
ANNEX = "docs/plans/agentic-research-system/transition/w9/wp9-1-catalogue-owner-annex.yaml"
W9_DESIGN = "docs/plans/agentic-research-system/design/09-migration-compatibility-and-pilot.md"
SCHEMAS = ".research-system/schemas"
ROOTS = ("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/")
GITKEEP = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


def _git(*args: str, cwd: Path = REPO_ROOT) -> bytes:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True).stdout


def _blob(path: str) -> bytes:
    return _git("show", f"{REVIEWED}:{path}")


def _text(path: str) -> str:
    return _blob(path).decode("utf-8")


def _lines(path: str) -> list[str]:
    return _text(path).splitlines()


def _note() -> str:
    return _text(NOTE)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _tree(prefix: str) -> list[str]:
    raw = _git("ls-tree", "-r", "-z", "--name-only", REVIEWED, prefix)
    return [path for path in raw.decode("utf-8").split("\0") if path]


def _annex_row(row: str) -> dict[str, Any]:
    return next(entry for entry in yaml.safe_load(_text(ANNEX))["rows"] if entry["owner_row_id"] == row)


# --- The subject -----------------------------------------------------------------------------------------------------


def test_subject_is_7bd7d6a6_changes_only_the_note_and_no_code_since_the_code_base() -> None:
    assert _git("rev-parse", "7bd7d6a6^{commit}").decode().strip() == REVIEWED
    assert _git("diff", "--name-only", REVISION_3, REVIEWED).decode().split() == [NOTE]
    code = ("research_system", ".research-system", "tools", "tests")
    assert _git("diff", "--name-only", CODE_BASE, REVIEWED, "--", *code).decode().strip() == ""


# --- Forged legacy states --------------------------------------------------------------------------------------------

ROOT_REG = "obj_root"
WHOLE = {"selector_kind": "whole_file"}


def _observation(record_id: str, registration: str, path: str, blob: str, selector: dict[str, Any]) -> dict[str, Any]:
    record = {
        "schema_id": "ars://legacy/legacy-observation",
        "record_id": record_id,
        "record_revision": 1,
        "registration_ref": {"id": registration, "record_revision": 1, "content_hash": "4" * 64},
        "selector": selector,
        "source_identity": {"identity_kind": "git_tracked", "repository_path": path, "git_blob": blob},
    }
    record["content_hash"] = record_content_hash(record)
    return record


def _observe(monkeypatch: pytest.MonkeyPatch, state: dict[str, Any], record: dict[str, Any]) -> None:
    registration = record["registration_ref"]["id"]
    monkeypatch.setattr(reducers, "_check_observation", lambda *args: registration)
    reducers.reduce_record(state, "LR-015", [{"payload": record}], {})


def _ref(record: dict[str, Any]) -> dict[str, Any]:
    return {"id": record["record_id"], "record_revision": 1, "content_hash": record["content_hash"]}


def _members(monkeypatch: pytest.MonkeyPatch, blobs: tuple[str, str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    state = reducers.new_legacy_state()
    members = [
        _observation("obj_m1", ROOT_REG, "papers/P01-A-JRSSA/drafts/.gitkeep", blobs[0], WHOLE),
        _observation("obj_m2", ROOT_REG, "papers/P01-A-JRSSA/figures/.gitkeep", blobs[1], WHOLE),
    ]
    for member in members:
        _observe(monkeypatch, state, member)
    return state, members


def _source_path(observation: dict[str, Any]) -> Any:
    return reducers._source_location(observation["source_identity"])[1]


def _latest_per_path(state: dict[str, Any], observation: dict[str, Any]) -> bool:
    """A model of reading 4: 'the latest for its source and selector', keyed by registration, path and selector."""
    history = state["observations_by_registration"][observation["registration_ref"]["id"]]
    later = history[history.index(observation["record_id"]) + 1 :]
    records = state["records"]["legacy_observation"]
    key = (_source_path(observation), reducers._selector_key(observation["selector"]))
    return not any((_source_path(records[o]), reducers._selector_key(records[o]["selector"])) == key for o in later)


def _stale_per_path(history: list[tuple[str, str, str]]) -> list[str]:
    """A model of reading 3: fingerprints compared per source path. ``history`` holds (record ID, path, blob)."""
    stale: list[str] = []
    for index, (_, path, blob) in enumerate(history):
        stale += [o for o, p, b in history[:index] if p == path and b != blob and o not in stale]
    return stale


# --- C-M1: the four readings -----------------------------------------------------------------------------------------


def test_c_major1_holds_reading_four_is_needed_and_a_per_path_key_admits_both_real_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, members = _members(monkeypatch, (GITKEEP, GITKEEP))
    with pytest.raises(IntegrityError, match="not the latest for its source and selector"):
        reducers._batch_rules(state, {"items": [{"observation_ref": _ref(members[0])}]})
    assert all(_latest_per_path(state, member) for member in members)
    note = _note()
    assert "That needs four readings of WP9.3's row checks" in note
    assert '**"the latest for its source and selector"** (`_batch_rules`, `:550-559`)' in note
    source = _lines("research_system/legacy/replay/reducers.py")
    assert "def _batch_rules" in source[538] and "not the latest for its source and selector" in source[558]


def test_c_major1_holds_whole_file_is_read_at_the_two_sites_the_note_names(monkeypatch: pytest.MonkeyPatch) -> None:
    state, members = _members(monkeypatch, (GITKEEP, GITKEEP))
    assert reducers._whole_file(state, members[0]) is True  # unread, a member closes the root at LR-020
    source = _lines("research_system/legacy/replay/reducers.py")
    callers = [n + 1 for n, line in enumerate(source) if "_whole_file(state" in line and "def " not in line]
    assert callers == [614, 629]


def test_c_major1_holds_the_four_readings_reduce_to_todays_checks_for_a_one_path_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = reducers.new_legacy_state()
    history = [("obj_o1", "a" * 40), ("obj_o2", "a" * 40), ("obj_o3", "b" * 40)]
    records = []
    for record_id, blob in history:
        records.append(_observation(record_id, "obj_reg", "results/x.npy", blob, WHOLE))
        _observe(monkeypatch, state, records[-1])
    assert _stale_per_path([(o, "results/x.npy", b) for o, b in history]) == state["stale_observations"]
    for record in records:
        try:
            reducers._batch_rules(state, {"items": [{"observation_ref": _ref(record)}]})
            today = True
        except IntegrityError:
            today = False
        assert today == (_latest_per_path(state, record) and record["record_id"] not in state["stale_observations"])


def test_r4_minor1_defect_the_one_path_premise_is_false_for_the_computational_log_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§10.2 says each reading reduces to today's check 'because LR-015's path rule gives such a registration one
    path'. The Computational-Log registration is the exception (reducers.py:472-484): its source is any accepted
    export's retained copy, so two observations of one registration can have two paths. A per-path stale rule would
    then stop an earlier export's observation going stale. The readings hold for other roles only if gated on role."""
    registration = {"role": reducers._CL_ROLE, "root_kind": "vault_root"}
    copies = [
        {"repository_path": f"evidence/cl-export-{n}.md", "git_commit": "c" * 40, "git_blob": blob}
        for n, blob in ((1, "a" * 40), (2, "b" * 40))
    ]
    context = {"accepted_cl_export": [{"retained_copy": copy} for copy in copies]}
    sources = [{"identity_kind": "git_tracked", **copy} for copy in copies]
    for source in sources:
        reducers._source_matches_registration(source, registration, context)  # both admitted: two paths
    state = reducers.new_legacy_state()
    for n, copy in enumerate(copies, start=1):
        _observe(
            monkeypatch, state, _observation(f"obj_cl{n}", "obj_cl", copy["repository_path"], copy["git_blob"], WHOLE)
        )
    assert state["stale_observations"] == ["obj_cl1"]
    assert _stale_per_path([(f"obj_cl{n}", c["repository_path"], c["git_blob"]) for n, c in enumerate(copies, 1)]) == []
    assert "because LR-015's\n  path rule gives such a registration one path" in _note()


# --- R4-M1: sites outside replay keyed on the registration's path ------------------------------------------------------


@pytest.fixture
def scratch_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "repo"
    (root / "papers/P01-A-JRSSA/drafts").mkdir(parents=True)
    (root / "papers/P01-A-JRSSA/figures").mkdir(parents=True)
    (root / "papers/P01-A-JRSSA/drafts/a.md").write_text("draft a\n", encoding="utf-8")
    (root / "papers/P01-A-JRSSA/figures/b.md").write_text("draft b\n", encoding="utf-8")
    _git("init", "-q", cwd=root)
    _git("add", ".", cwd=root)
    _git("-c", "user.email=r@example.invalid", "-c", "user.name=r", "commit", "-qm", "scratch", cwd=root)
    return root, _git("rev-parse", "HEAD", cwd=root).decode().strip()


ROOT_REGISTRATION = {
    "record_id": ROOT_REG,
    "role": "legacy_manuscript_root",
    "root_kind": "repository_root",
    "source_identity_kind": "git_tracked",
    "normalized_path": "papers/P01-A-JRSSA/",
}


def test_r4_major1_defect_the_reader_reads_the_registrations_path_and_cannot_be_given_a_member(
    scratch_repo: tuple[Path, str],
) -> None:
    """LegacyReader.read takes the registration only and reads its normalized_path (reader.py:275-285). The LR-015
    preparer (preparers.py:594, :633), the observation-id helper (:652) and the acceptance re-read (acceptance.py:69)
    all call it that way. Under option 1 the registration's path is the root directory, so no member can be read."""
    root, head = scratch_repo
    reader = LegacyReader(repository_root=root, git_head=head)
    assert list(inspect.signature(LegacyReader.read).parameters) == ["self", "registration"]
    with pytest.raises(ReadRefused):
        reader.read(ROOT_REGISTRATION)
    member = reader.read({**ROOT_REGISTRATION, "normalized_path": "papers/P01-A-JRSSA/drafts/a.md"})
    assert member.source_identity["repository_path"] == "papers/P01-A-JRSSA/drafts/a.md"  # only as its own registration
    calls = {
        "research_system/legacy/preparers.py": [594, 633, 652],
        "research_system/legacy/acceptance.py": [69],
    }
    for path, numbers in calls.items():
        lines = _lines(path)
        assert all("reader.read(registration)" in lines[n - 1] for n in numbers), path


def test_r4_major1_defect_the_observation_payload_has_no_carrier_for_a_member_path() -> None:
    """The preparer refuses a supplied source_identity (records.py:30; preparers.py:584), and the whole_file selector
    is closed with no path (legacy-observation.schema.json). So the command cannot name which member to observe."""
    with pytest.raises(IntegrityError, match="supplies preparer-set fields: source_identity"):
        preparers._refuse_supplied(
            {"registration_ref": {"id": ROOT_REG}, "selector": WHOLE, "source_identity": {"repository_path": "x"}},
            OBSERVATION_PREPARER_SET_FIELDS | OBSERVATION_READ_DERIVED_FIELDS | {"non_inferences"},
        )
    schema = json.loads(_text(f"{SCHEMAS}/contracts/w9/legacy-observation.schema.json"))
    whole = schema["properties"]["selector"]["oneOf"][0]
    assert whole["properties"] == {"selector_kind": {"const": "whole_file"}} and whole["additionalProperties"] is False


def test_r4_major1_defect_the_acceptance_reread_refuses_every_member_of_a_root_registration(
    scratch_repo: tuple[Path, str],
) -> None:
    root, head = scratch_repo
    reader = LegacyReader(repository_root=root, git_head=head)
    environment = preparers.Environment(reader=reader, generic={}, control_root=root, vault_root=None)
    blob = _git("rev-parse", f"{head}:papers/P01-A-JRSSA/drafts/a.md", cwd=root).decode().strip()
    member = _observation("obj_m1", ROOT_REG, "papers/P01-A-JRSSA/drafts/a.md", blob, WHOLE)
    legacy = {
        "records": {"legacy_observation": {"obj_m1": member}, "legacy_path_registration": {ROOT_REG: ROOT_REGISTRATION}}
    }
    with pytest.raises(IntegrityError, match="acceptance item's source cannot be read"):
        acceptance.reread_items(environment, legacy, {"items": [{"observation_ref": _ref(member)}]})


def test_r4_major1_the_note_names_no_preparer_or_reader_site_for_option_one() -> None:
    section = _note().split("### 10.2")[1].split("### 10.3")[0]
    for name in ("prepare_observation", "reread_items", "observation_id", "LegacyReader", "reader.read"):
        assert name not in section
    assert "All four are code changes in WP9.4-2: to the path rule, to `_whole_file`, to the stale" in section


def test_r4_info_the_shared_surface_change_list_keys_on_the_registration() -> None:
    lines = _lines("research_system/legacy/acceptance.py")
    assert 'key = {name: registration.get(name) for name in ("root_kind", "root_id", "normalized_path")}' in lines[124]


# --- R4-M2: the root registration itself -----------------------------------------------------------------------------


def test_r4_major2_defect_a_root_registration_cannot_be_proposed_or_resolved(scratch_repo: tuple[Path, str]) -> None:
    """LR-003 and LR-005 read the registration's path handle-bound (preparers.py:332, :541-542; annex LR-003 'one
    physical identity, read handle-bound'). The schema fixes a root's path to 'papers/P01-A-JRSSA/' (with the slash),
    which the reader refuses; without the slash it is a directory, which the reader also refuses. So no
    legacy_manuscript_root registration can be recorded, and LR-040's 'root's registration live' never holds."""
    root, head = scratch_repo
    environment = preparers.Environment(
        reader=LegacyReader(repository_root=root, git_head=head), generic={}, control_root=root, vault_root=None
    )
    for path in ("papers/P01-A-JRSSA/", "papers/P01-A-JRSSA"):
        with pytest.raises(IntegrityError, match="cannot be read handle-bound"):
            preparers._require_physical_identity(environment, {**ROOT_REGISTRATION, "normalized_path": path})
    schema = json.loads(_text(f"{SCHEMAS}/contracts/w9/legacy-path-registration.schema.json"))
    enums = [
        branch["then"]["properties"]["normalized_path"].get("enum")
        for branch in schema["allOf"]
        if branch.get("if", {}).get("properties", {}).get("role", {}).get("const") == "legacy_manuscript_root"
    ]
    assert enums == [["papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/"]]
    assert "one physical identity, read handle-bound" in " ".join(_annex_row("LR-003")["preconditions"])
    assert "LR-003" not in _note().split("### 10.2")[1].split("### 10.4")[0]


# --- C-m1, C-m3, C-m4, C-i1 ------------------------------------------------------------------------------------------


def test_c_minor1_holds_with_the_eligible_session_stored_apart_the_check_refuses_only_the_analyst() -> None:
    review = {"sessions": ["s-analyst"], "eligible_session": "s-eligible"}  # §5.5's revision 4 encoding
    assert "s-eligible" not in review["sessions"] and "s-analyst" in review["sessions"]
    flat = _flat(_note())
    assert "the analyst's session in `sessions`, which `_check_verdict` excludes" in flat
    assert "it must differ from the analyst's session and **equal** the request's eligible session" in flat
    source = _lines("research_system/legacy/replay/reducers.py")
    assert "sessions = _session_refs" in source[818] and "sessions=sessions" in source[852]
    assert 'session in review["sessions"]' in source[893]


def test_r4_info_a_third_production_route_to_resolve_for_result_is_unnamed() -> None:
    lines = _lines("research_system/methods/brief.py")
    assert '"result_analysis": ("resolve_for_result"' in lines[26]
    assert '"result_reproduction": ("resolve_for_result"' in lines[27]
    assert "methods/brief.py:27" not in _note()


def test_r4_minor2_defect_claim_13_overclaims_the_promotion_site_rule_does_not_see_a_later_suspension() -> None:
    """Every predicate needs accepted_for_scope, so the promotion-site rule refuses an unadmitted copy at promotion.
    But the note itself says the at-use check is needed 'because an adoption can suspend after the artefact is
    promoted', and keeps the at-use check to claim and manuscript. A result or review copy promoted while its adoption
    was active stays resolvable after the adoption suspends."""
    policy = yaml.safe_load(_text(".research-system/policies/artefact-consumer-predicates.v1.yaml"))
    text = json.dumps(policy)
    assert text.count('"use_authority": ["accepted_for_scope"]') == 5
    flat = _flat(_note())
    assert "The check is needed at use because an adoption can suspend after the artefact is promoted" in flat
    assert "the at-use rule above covers claim and manuscript only" in flat
    assert (
        "with the promotion-site rule, no consumer of any of the five kinds can resolve a legacy copy that no active "
        "adoption admits" in flat
    )


def test_c_minor4_holds_only_create_task_and_amend_task_carry_a_task_definition() -> None:
    carriers = []
    for path in _tree(f"{SCHEMAS}/core/commands/"):
        text = _text(path)
        if "task_definition" in text or "replacement_definition" in text:
            carriers.append(Path(path).name)
    assert carriers == ["amend_task.schema.json", "create_task.schema.json"]
    amend = _text(f"{SCHEMAS}/core/commands/amend_task.schema.json")
    assert '"aliases"' in amend and '"source_import_refs"' in amend


def test_c_info1_holds_the_resolution_preparer_appends_a_record_event_for_every_row_today() -> None:
    lines = _lines("research_system/legacy/preparers.py")
    assert "(RECORDED_EVENTS[row], record_id, record)" in lines[527]
    assert "LR-025" not in preparers.RECORDED_EVENTS
    assert "`prepare_resolution` always appends a recorded" in _note()


# --- CodeRabbit's threads and the comment not taken -------------------------------------------------------------------


def test_coderabbit_holds_restricted_suffixes_are_the_d9_list_and_every_read_carries_a_sha256() -> None:
    assert reducers.RESTRICTED_SUFFIXES == (".csv", ".pkl")
    lines = _lines("research_system/legacy/reader.py")
    assert 'identity["sha256"] = sha256_hex(raw)' in lines[341]


def test_coderabbit_comment_not_taken_the_accepted_texts_allow_unadopted_families() -> None:
    design = _flat(_text(W9_DESIGN))
    assert 'is either adopted for "evidence for the manuscript claims of paper X" (§9) or marked unadopted' in design
    assert "every cited family adopted or marked unadopted (§12.1)" in " ".join(_annex_row("LR-054")["preconditions"])


# --- §11.1, the extractor --------------------------------------------------------------------------------------------

SEPARATORS = re.compile(r"[\s`'\"()\[\]<>,;|*]+")
RESULT_EXTENSIONS = (".json", ".npy", ".npz", ".csv", ".pkl")
TEMPLATE_MARKERS = ("{", "}", "YYYYMMDD", "YYYY-MM-DD")


def _json_strings(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for key, value in node.items() for s in (*_json_strings(key), *_json_strings(value))]
    if isinstance(node, list):
        return [s for value in node for s in _json_strings(value)]
    return []


def tokens(text: str) -> list[str]:
    text = re.sub(r"/{2,}", "/", text.replace("\\", "/"))
    out = []
    for token in SEPARATORS.split(text):
        token = token.rstrip(".:")
        if token:
            out.append(token)
    return out


class Extractor:
    """§11.1 items 1-3 and 7 as revision 4 writes them, with no disambiguation file."""

    def __init__(self, registered: list[str], directories: set[str]) -> None:
        self.registered = set(registered)
        self.directories = directories
        self.by_base: dict[str, list[str]] = defaultdict(list)
        for path in registered:
            self.by_base[path.rsplit("/", 1)[-1]].append(path)

    def candidate(self, token: str) -> bool:
        last = token.rsplit("/", 1)[-1]
        return "results/" in token or last in self.by_base or ("/" not in token and token.endswith(RESULT_EXTENSIONS))

    def _cited_under_results(self, token: str) -> str | None:
        return next((p for p in self.registered if token == p or token.endswith("/" + p)), None)

    def _suffix_of_registered(self, token: str) -> bool:
        return any(p == token or p.endswith("/" + token) for p in self.registered)

    def classify(self, token: str) -> tuple[str, str | None]:
        last = token.rsplit("/", 1)[-1]
        under = "results/" in token
        relative = token[token.find("results/") :] if under else None
        if (
            under
            and (relative.rstrip("/") in self.directories or token.endswith("/") or "." not in last)
            or any(marker in last for marker in TEMPLATE_MARKERS)
            or (last.rsplit(".", 1)[0] == "" if "." in last else False)
        ):
            return "not_a_file", None
        if under:
            cited = self._cited_under_results(token)
            return ("cited", cited) if cited else ("unregistered", None)
        if "/" not in token:
            matches = self.by_base.get(token, [])
            if len(matches) == 1:
                return "cited", matches[0]
            if len(matches) > 1:
                return "ambiguous", None
            if token.endswith(RESULT_EXTENSIONS):
                return "unregistered", None
            return "no_class", None
        if last in self.by_base and not self._suffix_of_registered(token):
            return "ambiguous", None
        return "no_class", None

    def scan(self, files: dict[str, bytes], root: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            scope: {"cited": {}, "ambiguous": set(), "unregistered": set(), "not_a_file": set(), "no_class": set()}
            for scope in ("drafts", "outside")
        }
        result["not_text"] = []
        for path, raw in sorted(files.items()):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                result["not_text"].append(path)
                continue
            texts = [text]
            if path.endswith(".json"):
                try:
                    texts += _json_strings(json.loads(text))
                except json.JSONDecodeError:
                    pass
            scope = "drafts" if path.startswith(root + "drafts/") else "outside"
            for token in {t for piece in texts for t in tokens(piece) if self.candidate(t)}:
                cls, target = self.classify(token)
                if cls == "cited":
                    result[scope]["cited"].setdefault(target, set()).add(path)
                else:
                    result[scope][cls].add((token, path))
        return result


def project(cited: dict[str, dict[str, Any]]) -> tuple[list[tuple[str, str]], list[str]]:
    """§11.1 item 4: (observation ID, family) pairs, or ``whole_file`` for a file with no JSON family; blockers."""
    pairs, blockers = [], []
    for path, facts in sorted(cited.items()):
        if facts.get("observation_id") is None:
            blockers.append(f"no accepted observation: {path}")
        elif not path.endswith(".json"):
            pairs.append((facts["observation_id"], "whole_file"))
        elif facts.get("families") is None:
            blockers.append(f"no accepted membership table: {path}")
        else:
            pairs += [(facts["observation_id"], family) for family in facts["families"]]
    return sorted(pairs), blockers


def _registration_set() -> tuple[list[str], set[str]]:
    registered = _tree("results/")
    raw = _git("ls-tree", "-r", "-t", "-z", REVIEWED, "results/").decode("utf-8")
    directories = {entry.split("\t", 1)[1] for entry in raw.split("\0") if entry and " tree " in entry}
    return registered, directories


@pytest.fixture(scope="module")
def extracted() -> dict[str, dict[str, Any]]:
    registered, directories = _registration_set()
    extractor = Extractor(registered, directories)
    return {root: extractor.scan({p: _blob(p) for p in _tree(root)}, root) for root in ROOTS}


def _names(entries: set[tuple[str, str]]) -> set[str]:
    return {token.rsplit("/", 1)[-1] for token, _ in entries}


def test_extractor_holds_p01a_drafts_leave_exactly_the_four_ambiguous_names(extracted) -> None:
    drafts = extracted["papers/P01-A-JRSSA/"]["drafts"]
    assert _names(drafts["ambiguous"]) == {
        "04_nulls_wasserstein_w2_20260407.json",
        "04_nulls_wasserstein_w2_L5000_20260502.json",
        "stratified_markov1_W2_L5000_20260502.json",
        "05_analysis.json",
    }
    assert drafts["unregistered"] == set() and drafts["no_class"] == set()
    assert len(drafts["cited"]) == 23
    assert ("table1_effects_{date_suffix}.json", "papers/P01-A-JRSSA/drafts/sections/compute_table1_effects.py") in (
        drafts["not_a_file"]
    )


def test_extractor_holds_p01b_drafts_leave_no_blocker(extracted) -> None:
    drafts = extracted["papers/P01-B-JRSSB/"]["drafts"]
    assert drafts["ambiguous"] == drafts["unregistered"] == drafts["no_class"] == set()
    assert sorted(drafts["cited"]) == [
        "results/trajectory_tda_bhps/post_audit/04_nulls_wasserstein_w2_20260407.json",
        "results/trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json",
    ]


def test_extractor_holds_no_file_is_not_text_and_no_candidate_falls_in_no_class(extracted) -> None:
    for root in ROOTS:
        assert extracted[root]["not_text"] == []
        assert extracted[root]["drafts"]["no_class"] == extracted[root]["outside"]["no_class"] == set()


def test_r4_minor3_defect_the_template_test_drops_a_real_brace_expanded_citation(extracted) -> None:
    """P01-A's notes cite `ph_L{2500,5000,8000}.json` under landmark_sensitivity/. All three files are registered.
    The tokenizer splits on ',', leaving `8000}.json`, which the template test classes not_a_file. It is outside
    drafts/, so it is reported, not hashed; under I's whole-root alternative it would drop three cited files."""
    registered, _ = _registration_set()
    for landmarks in (2500, 5000, 8000):
        assert f"results/trajectory_tda_robustness/landmark_sensitivity/ph_L{landmarks}.json" in registered
    outside = extracted["papers/P01-A-JRSSA/"]["outside"]["not_a_file"]
    assert any(token == "8000}.json" and "reviewer-response-plan" in path for token, path in outside)


def test_r4_minor3_defect_a_latex_wrapped_citation_of_a_registered_file_is_classed_not_a_file() -> None:
    registered, directories = _registration_set()
    extractor = Extractor(registered, directories)
    path = "results/trajectory_tda_robustness/landmark_sensitivity/ph_L5000.json"
    for text in (f"\\texttt{{{path}}}", f"\\path{{{path}}}"):
        (token,) = [t for t in tokens(text) if extractor.candidate(t)]
        assert extractor.classify(token) == ("not_a_file", None), text
    assert [t for t in tokens("\\texttt{ph_L5000.json}") if extractor.candidate(t)] == []  # not even a candidate
    assert extractor.classify(path) == ("cited", path)


def test_r4_minor4_defect_a_partial_path_that_is_a_suffix_of_a_registered_path_falls_in_no_class() -> None:
    """The widened ambiguous class excludes 'a suffix of a registered path', and the cited class takes a token whose
    suffix is a registered path. A token that is a proper suffix of one, with a directory part and no `results/`, is
    in neither, nor in unregistered or not_a_file. No such token is in either root today."""
    registered, directories = _registration_set()
    extractor = Extractor(registered, directories)
    token = "trajectory_tda_integration/post_audit/04_nulls_wasserstein_w2_20260407.json"
    assert extractor.candidate(token)
    assert extractor.classify(token) == ("no_class", None)


def test_r4_minor4_defect_a_template_in_a_directory_part_is_a_blocker_nothing_can_clear() -> None:
    registered, directories = _registration_set()
    extractor = Extractor(registered, directories)
    assert extractor.classify("results/trajectory_tda_{survey}/post_audit/04_nulls.json") == ("unregistered", None)


def test_extractor_widened_ambiguous_and_the_projection() -> None:
    extractor = Extractor(["results/x/data.json", "results/x/emb.npy"], {"results", "results/x"})
    assert extractor.classify("notes/data.json") == ("ambiguous", None)
    assert extractor.classify("data.json") == ("cited", "results/x/data.json")
    assert extractor.classify(".json") == ("not_a_file", None)
    assert extractor.classify("level1_comparison_YYYYMMDD.json") == ("not_a_file", None)
    assert extractor.classify("new_result.json") == ("unregistered", None)
    pairs, blockers = project(
        {
            "results/x/emb.npy": {"observation_id": "obj_e"},
            "results/x/data.json": {"observation_id": "obj_d", "families": None},
        }
    )
    assert pairs == [("obj_e", "whole_file")] and blockers == ["no accepted membership table: results/x/data.json"]
