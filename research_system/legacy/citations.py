"""Pure citation extractor for WP9.4-2 LR-039 and LR-054 re-runs (WP9.4 note §11.1, §11.2, owner point I).

The extractor scans bytes committed at the binding's ``git_head`` (from each inventory row's Git blob, never the live
working tree) using delimiter splitting with tail tracking, exact 5-class candidate resolution (``tail``,
``cited file``, ``not_a_file``, ``ambiguous``, ``unregistered``), optional ``citation-disambiguation.json``, and
family projection through accepted membership tables or ``whole_file`` observations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from pathlib import Path
from typing import Any, Literal

from research_system.canonical import canonical_bytes, sha256_hex
from research_system.errors import IntegrityError
from research_system.legacy import evidence as w9_evidence
from research_system.legacy.reader import MANUSCRIPT_ROOT_ROLE, ReadRefused, _git, git_blob_id

RESULT_EXTENSIONS = (".json", ".npy", ".npz", ".csv", ".pkl")
_SINGLE_DELIMITERS = frozenset("`'\"()[]{}<>,;|*")
_DATE_PLACEHOLDERS = ("YYYYMMDD", "YYYY-MM-DD")
_HEX_OBJECT_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?\Z")


def _collapse_slashes(text: str) -> str:
    collapsed = text.replace("\\", "/")
    while "//" in collapsed:
        collapsed = collapsed.replace("//", "/")
    return collapsed


def _has_date_placeholder(token: str) -> bool:
    return any(placeholder in part for part in token.split("/") for placeholder in _DATE_PLACEHOLDERS)


def _has_empty_stem(token: str) -> bool:
    last_component = token.rsplit("/", 1)[-1]
    stem, dot, _ext = last_component.rpartition(".")
    return bool(dot and stem == "")


def tokenize_text(text: str) -> list[tuple[str, bool]]:
    """Split text into ``(normalized_token, is_tail)`` pairs per WP9.4 note §11.1 item 1."""

    tokens: list[tuple[str, bool]] = []
    length = len(text)
    index = 0
    while index < length:
        if text[index].isspace() or text[index] in _SINGLE_DELIMITERS:
            index += 1
            continue
        start = index
        while index < length and not text[index].isspace() and text[index] not in _SINGLE_DELIMITERS:
            index += 1
        is_tail = start > 0 and text[start - 1] == "}"
        normalized = _collapse_slashes(text[start:index]).rstrip(".:")
        if normalized:
            tokens.append((normalized, is_tail))
    return tokens


def _iter_json_strings(value: Any) -> list[str]:
    found: list[str] = []
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, str):
            found.append(current)
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, dict):
            stack.extend(current.values())
    return found


def scan_file_tokens(repository_path: str, raw: bytes) -> tuple[list[tuple[str, bool]] | None, bool]:
    """Decode UTF-8 (and JSON string values for ``.json``) into tokens, or return ``(None, False)`` for ``not_text``."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, False
    tokens = tokenize_text(text)
    if repository_path.lower().endswith(".json"):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = None
        if parsed is not None:
            for item in _iter_json_strings(parsed):
                tokens.extend(tokenize_text(item))
    return tokens, True


def _component_matches_tok_ending_in_reg(token: str, registered_paths: set[str]) -> list[str]:
    if token in registered_paths:
        return [token]
    return sorted(reg for reg in registered_paths if token.endswith(f"/{reg}"))


def _component_matches_reg_ending_in_tok(token: str, registered_paths: set[str]) -> list[str]:
    return sorted(reg for reg in registered_paths if reg == token or reg.endswith(f"/{token}"))


def _matches_directory(token: str, directories: set[str]) -> bool:
    if token in directories:
        return True
    trimmed = token.rstrip("/")
    return trimmed in directories or any(trimmed.endswith(f"/{directory}") for directory in directories)


def _is_candidate(token: str, is_tail: bool, registered_basenames: set[str]) -> bool:
    if is_tail:
        return True
    if "results/" in token:
        return True
    last_component = token.rsplit("/", 1)[-1]
    if last_component in registered_basenames:
        return True
    return "/" not in token and token.endswith(RESULT_EXTENSIONS)


def _apply_disambiguation(
    citing_path: str,
    token: str,
    registered_paths: set[str],
    disambiguation: Mapping[tuple[str, str], tuple[str, ...] | Literal["not_a_result"]],
) -> tuple[str, tuple[str, ...]]:
    entry = disambiguation.get((citing_path, token))
    if entry is None:
        return "ambiguous", ()
    if entry == "not_a_result":
        return "not_a_result", ()
    if any(path not in registered_paths for path in entry):
        return "unregistered_disambiguation", entry
    return "cited_file", tuple(entry)


def _classify_candidate(
    citing_path: str,
    token: str,
    is_tail: bool,
    registered_paths: set[str],
    by_basename: Mapping[str, list[str]],
    directories: set[str],
    disambiguation: Mapping[tuple[str, str], tuple[str, ...] | Literal["not_a_result"]],
) -> tuple[str, tuple[str, ...]]:
    """Classify one candidate per the exact five-class order in WP9.4 note §11.1 item 3."""

    # 1. tail (tested before every other class, R7-m3)
    if is_tail:
        if _has_empty_stem(token) or _has_date_placeholder(token):
            return "not_a_file", ()
        if any(reg.endswith(token) for reg in registered_paths):
            return _apply_disambiguation(citing_path, token, registered_paths, disambiguation)
        return "not_a_file", ()

    has_results = "results/" in token
    has_dir = "/" in token
    last_component = token.rsplit("/", 1)[-1]

    # 2. cited file (tested first among non-tails)
    tok_suffix_regs = _component_matches_tok_ending_in_reg(token, registered_paths)
    if tok_suffix_regs:
        longest = max(tok_suffix_regs, key=len)
        return "cited_file", (longest,)
    if not has_dir:
        basename_matches = by_basename.get(token, [])
        if len(basename_matches) == 1:
            return "cited_file", (basename_matches[0],)
    elif not has_results:
        partial_matches = _component_matches_reg_ending_in_tok(token, registered_paths)
        if len(partial_matches) == 1:
            return "cited_file", (partial_matches[0],)
    else:
        partial_matches = []

    # 3. not_a_file (tested after cited file)
    if has_results and (_matches_directory(token, directories) or token.endswith("/") or "." not in last_component):
        return "not_a_file", ()
    if _has_date_placeholder(token) or _has_empty_stem(token):
        return "not_a_file", ()

    # 4. ambiguous
    if not has_dir and len(by_basename.get(token, [])) > 1:
        return _apply_disambiguation(citing_path, token, registered_paths, disambiguation)
    if has_dir and not has_results and (len(partial_matches) > 1 or last_component in by_basename):
        return _apply_disambiguation(citing_path, token, registered_paths, disambiguation)

    # 5. unregistered
    if has_results or (not has_dir and token.endswith(RESULT_EXTENSIONS) and token not in by_basename):
        return "unregistered", ()

    raise IntegrityError(f"W9 citation extractor encountered unclassed candidate {token!r} in {citing_path}")


def _blocker_sort_key(blocker: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(blocker.get("kind", "")),
        str(blocker.get("citing_path", "")),
        str(blocker.get("token", "")),
        str(blocker.get("path", "")) + ":" + str(blocker.get("family_name", "")),
    )


def registered_result_projections(legacy: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Build per-path accepted-observation / membership projections from replayed W9 state (§11.1 item 4)."""

    records = legacy.get("records", {})
    supersessions = legacy.get("supersessions", {})
    registrations = records.get("legacy_path_registration", {})
    observations = records.get("legacy_observation", {})
    memberships = records.get("legacy_field_family_membership", {})
    acceptances = records.get("legacy_closed_reference_acceptance", {})
    obs_by_reg = legacy.get("observations_by_registration", {})

    accepted_obs_ids: set[str] = set()
    for acc_id, acc in acceptances.items():
        if acc_id in supersessions:
            continue
        for item in acc.get("items", ()):
            obs_ref = item.get("observation_ref")
            if isinstance(obs_ref, Mapping):
                obs_id = obs_ref.get("id")
                if isinstance(obs_id, str) and obs_id not in supersessions:
                    accepted_obs_ids.add(obs_id)

    projections: dict[str, dict[str, Any]] = {}
    for reg_id, reg in registrations.items():
        if reg_id in supersessions or reg.get("role") != "legacy_research_result":
            continue
        norm_path = str(reg.get("normalized_path", ""))
        reg_obs_ids = [oid for oid in obs_by_reg.get(reg_id, ()) if oid in accepted_obs_ids]
        reg_obs = [observations[oid] for oid in reg_obs_ids if oid in observations]

        if norm_path.lower().endswith(".json"):
            if not reg_obs:
                projections[norm_path] = {"pairs": (), "blocker_kind": "unobserved"}
                continue
            table_id: str | None = None
            for obs in reversed(reg_obs):
                sel = obs.get("selector", {})
                if sel.get("selector_kind") == "json_family_set":
                    cand_id = sel.get("membership_ref", {}).get("id")
                    if isinstance(cand_id, str) and cand_id in memberships and cand_id not in supersessions:
                        table_id = cand_id
                        break
            if table_id is None:
                projections[norm_path] = {"pairs": (), "blocker_kind": "missing_membership_table"}
                continue
            table = memberships[table_id]
            table_family_names = [str(family["name"]) for family in table.get("families", ())]
            pairs: list[tuple[str, str]] = []
            missing_families: list[str] = []
            for fname in table_family_names:
                matched_obs_id: str | None = None
                for obs in reversed(reg_obs):
                    sel = obs.get("selector", {})
                    if (
                        sel.get("selector_kind") == "json_family_set"
                        and sel.get("membership_ref", {}).get("id") == table_id
                        and fname in sel.get("family_names", ())
                    ):
                        matched_obs_id = str(obs["record_id"])
                        break
                if matched_obs_id is None:
                    missing_families.append(fname)
                else:
                    pairs.append((matched_obs_id, fname))
            if missing_families:
                projections[norm_path] = {
                    "pairs": tuple(pairs),
                    "blocker_kind": "unobserved_family",
                    "missing_families": tuple(missing_families),
                }
            else:
                projections[norm_path] = {"pairs": tuple(pairs), "blocker_kind": None}
        else:
            whole_obs_id: str | None = None
            for obs in reversed(reg_obs):
                if obs.get("selector", {}).get("selector_kind") == "whole_file":
                    whole_obs_id = str(obs["record_id"])
                    break
            if whole_obs_id is None:
                projections[norm_path] = {"pairs": (), "blocker_kind": "unobserved"}
            else:
                projections[norm_path] = {"pairs": ((whole_obs_id, "whole_file"),), "blocker_kind": None}
    return projections


def extract_citations_from_files(
    *,
    root_path: str,
    inventory_files: Sequence[tuple[str, bytes]],
    registered_results: Mapping[str, Mapping[str, Any]],
    result_directories: set[str] | frozenset[str] = frozenset(),
    disambiguation: Mapping[tuple[str, str], tuple[str, ...] | Literal["not_a_result"]] = (),
    disambiguation_blob: str | None = None,
) -> dict[str, Any]:
    """Pure citation extractor over inventory file bytes (§11.1 items 1–7, §11.2)."""

    root_prefix = root_path if root_path.endswith("/") else f"{root_path}/"
    drafts_prefix = f"{root_prefix}drafts/"
    registered_paths = set(registered_results)
    by_basename: dict[str, list[str]] = {}
    for path in sorted(registered_paths):
        by_basename.setdefault(path.rsplit("/", 1)[-1], []).append(path)
    registered_basenames = set(by_basename)
    directories = {d.rstrip("/") for d in result_directories}
    disambiguation_map = dict(disambiguation) if not isinstance(disambiguation, Mapping) else disambiguation

    cited_files: set[str] = set()
    blocker_map: dict[tuple[str, ...], dict[str, Any]] = {}
    not_text_files: list[str] = []
    not_a_file_tokens: set[tuple[str, str]] = set()
    disambiguated_not_a_result: set[tuple[str, str]] = set()
    out_of_scope_cited: set[tuple[str, str]] = set()
    out_of_scope_other: list[dict[str, str]] = []

    def add_blocker(entry: dict[str, Any]) -> None:
        key = (
            str(entry.get("kind", "")),
            str(entry.get("citing_path", "")),
            str(entry.get("token", "")),
            str(entry.get("path", "")),
            str(entry.get("family_name", "")),
        )
        blocker_map[key] = entry

    for repo_path, raw in inventory_files:
        in_drafts = repo_path.startswith(drafts_prefix)
        tokens, is_text = scan_file_tokens(repo_path, raw)
        if not is_text or tokens is None:
            not_text_files.append(repo_path)
            continue
        seen_candidates: set[tuple[str, bool]] = set()
        for token, is_tail in tokens:
            if not _is_candidate(token, is_tail, registered_basenames):
                continue
            cand_key = (token, is_tail)
            if cand_key in seen_candidates:
                continue
            seen_candidates.add(cand_key)
            status, payload = _classify_candidate(
                repo_path,
                token,
                is_tail,
                registered_paths,
                by_basename,
                directories,
                disambiguation_map,
            )
            if not in_drafts:
                if status == "cited_file":
                    for target in payload:
                        out_of_scope_cited.add((repo_path, target))
                elif status == "not_a_file":
                    not_a_file_tokens.add((repo_path, token))
                elif status == "not_a_result":
                    disambiguated_not_a_result.add((repo_path, token))
                else:
                    out_of_scope_other.append({"kind": status, "citing_path": repo_path, "token": token})
                continue
            if status == "cited_file":
                cited_files.update(payload)
            elif status == "not_a_file":
                not_a_file_tokens.add((repo_path, token))
            elif status == "not_a_result":
                disambiguated_not_a_result.add((repo_path, token))
            elif status in {"ambiguous", "unregistered"}:
                add_blocker({"kind": status, "citing_path": repo_path, "token": token})
            elif status == "unregistered_disambiguation":
                for target in payload:
                    if target not in registered_paths:
                        add_blocker({"kind": "unregistered", "citing_path": repo_path, "token": token, "path": target})

    family_pairs: set[tuple[str, str]] = set()
    for cited in sorted(cited_files):
        info = registered_results[cited]
        blocker_kind = info.get("blocker_kind")
        pairs = info.get("pairs", ())
        for pair in pairs:
            family_pairs.add((str(pair[0]), str(pair[1])))
        if blocker_kind == "unobserved_family":
            for fname in info.get("missing_families", ()):
                add_blocker({"kind": "unobserved_family", "path": cited, "family_name": fname})
        elif blocker_kind is not None:
            add_blocker({"kind": blocker_kind, "path": cited})

    cited_family_set = [[obs_id, family_name] for obs_id, family_name in sorted(family_pairs)]
    blockers = sorted(blocker_map.values(), key=_blocker_sort_key)
    cited_family_set_sha256 = sha256_hex(canonical_bytes(cited_family_set))
    hashed_output = {
        "cited_family_set": cited_family_set,
        "blockers": blockers,
        "disambiguation_blob": disambiguation_blob,
    }
    extractor_output_sha256 = sha256_hex(canonical_bytes(hashed_output))
    return {
        "cited_family_set": cited_family_set,
        "blockers": blockers,
        "disambiguation_blob": disambiguation_blob,
        "cited_family_set_sha256": cited_family_set_sha256,
        "extractor_output_sha256": extractor_output_sha256,
        "cited_files": sorted(cited_files),
        "report": {
            "not_text": sorted(not_text_files),
            "not_a_file": [{"citing_path": p, "token": t} for p, t in sorted(not_a_file_tokens)],
            "disambiguated_not_a_result": [
                {"citing_path": p, "token": t} for p, t in sorted(disambiguated_not_a_result)
            ],
            "out_of_scope_cited": [{"citing_path": p, "path": t} for p, t in sorted(out_of_scope_cited)],
            "out_of_scope_other": sorted(
                out_of_scope_other, key=lambda item: (item["kind"], item["citing_path"], item["token"])
            ),
        },
    }


def _git_result_directories(repository_root: Path, git_head: str) -> set[str]:
    try:
        raw = _git(repository_root, "ls-tree", "-r", "-t", "-z", git_head, "--", "results")
    except ReadRefused:
        return set()
    dirs: set[str] = set()
    for entry in raw.split("\0"):
        if not entry or "\t" not in entry:
            continue
        meta, path = entry.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 2 and parts[1] == "tree":
            dirs.add(path.rstrip("/"))
    return dirs


def _read_inventory_row_blobs(
    repository_root: Path, git_head: str, inventory: Mapping[str, Any], legacy: Mapping[str, Any]
) -> list[tuple[str, bytes]]:
    observations = legacy.get("records", {}).get("legacy_observation", {})
    files: list[tuple[str, bytes]] = []
    for row in inventory.get("rows", ()):
        repo_path = str(row["repository_path"])
        obs = observations.get(row["observation_ref"]["id"])
        blob = str(obs["source_identity"]["git_blob"]) if obs is not None else str(row["git_blob"])
        if not _HEX_OBJECT_RE.match(blob):
            raise IntegrityError(f"W9 citation extractor invalid git_blob for {repo_path}")
        try:
            raw = _git(repository_root, "cat-file", "-p", blob, text=False)
        except ReadRefused as exc:
            raise IntegrityError(f"W9 citation extractor cannot read blob {blob} for {repo_path}: {exc}") from exc
        if git_blob_id(raw) != blob:
            raise IntegrityError(f"W9 citation extractor blob mismatch for {repo_path}")
        files.append((repo_path, raw))
    return files


def extract_citations(
    repository_root: Path,
    git_head: str | None,
    inventory: Mapping[str, Any],
    legacy: Mapping[str, Any],
) -> dict[str, Any]:
    """Run WP9.4-2's citation extractor for a recorded source inventory at ``git_head``."""

    if not git_head:
        raise IntegrityError("W9 citation extractor needs the binding's git_head")
    reg_id = inventory["root_registration_ref"]["id"]
    root_reg = legacy["records"]["legacy_path_registration"][reg_id]
    if root_reg.get("role") != MANUSCRIPT_ROOT_ROLE:
        raise IntegrityError("W9 source inventory root registration must have role legacy_manuscript_root")
    inventory_files = _read_inventory_row_blobs(repository_root, str(git_head), inventory, legacy)
    disambiguation, disambiguation_blob = w9_evidence.read_citation_disambiguation(repository_root, str(git_head))
    result_directories = _git_result_directories(repository_root, str(git_head))
    projections = registered_result_projections(legacy)
    return extract_citations_from_files(
        root_path=str(root_reg["normalized_path"]),
        inventory_files=inventory_files,
        registered_results=projections,
        result_directories=result_directories,
        disambiguation=disambiguation,
        disambiguation_blob=disambiguation_blob,
    )
