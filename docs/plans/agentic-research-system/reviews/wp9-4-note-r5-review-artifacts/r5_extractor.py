# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (P06, W9)
# Purpose: re-run the note's §11.1 citation rule (revision 5) over the P01-A and P01-B roots, read-only, for review.
"""The WP9.4 note's §11.1 citation rule as revision 5 (32755276) writes it, for the r5 review's probes.

Research context: P06 (agentic research system), W9 transition, WP9.4 design note review. Read-only: every file is
read through ``git show <commit>:<path>``; nothing is written outside pytest's ``tmp_path``. No seed: deterministic.

Written fresh from the note's text, not from the earlier reviews' probe code. The reading choices the text leaves open
are named where they are made:

- "a suffix of the token equals a registered path" and "a suffix of exactly one registered path" are read at a
  path-component boundary (the string-suffix reading is reported separately by ``suffix_mode="string"``);
- "every decoded string value" of a ``.json`` file is read as values only; keys are scanned too when ``keys=True``.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

RESULT_EXTENSIONS = (".json", ".npy", ".npz", ".csv", ".pkl")
SEPARATORS = "`'\"()[]{}<>,;|*"
_SPLIT = re.compile(r"[\s" + re.escape(SEPARATORS) + r"]+")
_TEMPLATE = re.compile(r"[{}]|YYYYMMDD|YYYY-MM-DD")


def git(repo: Path, *args: str) -> bytes:
    """Run one read-only Git command and return its stdout."""
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True).stdout


def normalize(text: str) -> str:
    """§11.1 item 1: ``\\`` read as ``/``, repeated ``/`` collapsed."""
    return re.sub(r"/{2,}", "/", text.replace("\\", "/"))


def tokens(text: str) -> list[str]:
    """§11.1 item 1: split on whitespace and the separators; strip a trailing ``.`` or ``:``."""
    out = []
    for raw in _SPLIT.split(normalize(text)):
        token = raw
        while token and token[-1] in ".:":
            token = token[:-1]
        if token:
            out.append(token)
    return out


def _json_strings(node: Any, keys: bool) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [s for item in node for s in _json_strings(item, keys)]
    if isinstance(node, dict):
        found = [s for value in node.values() for s in _json_strings(value, keys)]
        if keys:
            found += [str(key) for key in node]
        return found
    return []


@dataclass
class Report:
    """One root's classification, split by blocking (``drafts/``) and reported (the rest)."""

    cited: dict[str, set[str]] = field(default_factory=lambda: {"drafts": set(), "other": set()})
    classes: dict[str, dict[str, set[tuple[str, str]]]] = field(default_factory=dict)
    not_text: set[str] = field(default_factory=set)

    def add(self, scope: str, klass: str, citing: str, token: str) -> None:
        """Record one candidate's class."""
        self.classes.setdefault(scope, {}).setdefault(klass, set()).add((citing, token))

    def names(self, scope: str, klass: str) -> set[str]:
        """The distinct tokens of one class in one scope."""
        return {token for _, token in self.classes.get(scope, {}).get(klass, set())}


class Extractor:
    """§11.1 items 2 and 3, revision 5: cited file, then ``not_a_file``, then ``ambiguous``, then ``unregistered``."""

    def __init__(
        self,
        registered: list[str],
        directories: set[str],
        *,
        suffix_mode: str = "component",
        disambiguation: dict[tuple[str, str], Any] | None = None,
    ) -> None:
        """Bind the registration set (normalized repository paths) and the tracked directories under results/."""
        self.registered = sorted(registered)
        self.directories = directories
        self.suffix_mode = suffix_mode
        self.disambiguation = disambiguation or {}
        self.by_basename: dict[str, list[str]] = {}
        for path in self.registered:
            self.by_basename.setdefault(PurePosixPath(path).name, []).append(path)

    def _is_suffix(self, short: str, long: str) -> bool:
        if self.suffix_mode == "string":
            return long.endswith(short)
        short = short.lstrip("/")
        return long == short or long.endswith("/" + short)

    def candidate(self, token: str) -> bool:
        """§11.1 item 2."""
        last = token.rsplit("/", 1)[-1]
        return (
            "results/" in token
            or last in self.by_basename
            or ("/" not in token and token.lower().endswith(RESULT_EXTENSIONS))
        )

    def _suffix_hits(self, token: str) -> list[str]:
        return [path for path in self.registered if self._is_suffix(token, path)]

    def _token_suffix_registered(self, token: str) -> str | None:
        # "A suffix of the token equals a registered path": some trailing component run of the token is a path.
        parts = token.split("/")
        for start in range(len(parts)):
            tail = "/".join(parts[start:])
            if tail in self.registered:
                return tail
        return None

    def _template(self, token: str) -> bool:
        components = [c for c in token.split("/") if c]
        if any(_TEMPLATE.search(c) for c in components):
            return True
        last = components[-1] if components else ""
        return PurePosixPath(last).stem == "" or last.startswith(".") and "." not in last[1:]

    def classify(self, citing: str, token: str) -> tuple[str, list[str]]:
        """Return the class and, for a cited file, the registered paths it means."""
        has_dir = "/" in token.strip("/") or token.startswith("/")
        under_results = "results/" in token
        # 1. cited file, tested first.
        hit = self._token_suffix_registered(token)
        if hit is not None:
            return "cited", [hit]
        if not has_dir and len(self.by_basename.get(token, [])) == 1:
            return "cited", list(self.by_basename[token])
        if has_dir and not under_results:
            hits = self._suffix_hits(token)
            if len(hits) == 1:
                return "cited", hits
        # 2. not_a_file.
        if under_results:
            tail = token[token.index("results/") :]
            if tail.endswith("/") or tail.rstrip("/") in self.directories or PurePosixPath(tail).suffix == "":
                return "not_a_file", []
        if self._template(token):
            return "not_a_file", []
        # 3. ambiguous (cleared by a disambiguation row).
        ambiguous = False
        if not has_dir and len(self.by_basename.get(token, [])) > 1:
            ambiguous = True
        elif has_dir and not under_results:
            hits = self._suffix_hits(token)
            if len(hits) > 1 or (not hits and token.rsplit("/", 1)[-1] in self.by_basename):
                ambiguous = True
        if ambiguous:
            row = self.disambiguation.get((citing, token))
            if row == "not_a_result":
                return "reported_not_a_result", []
            if row:
                return "cited", sorted(row)
            return "ambiguous", []
        # 4. unregistered.
        if under_results or (not has_dir and token.lower().endswith(RESULT_EXTENSIONS)):
            return "unregistered", []
        return "no_class", []

    def scan(self, files: dict[str, bytes], root: str, *, keys: bool = False) -> Report:
        """Scan one root's files; ``drafts/`` blocks, the rest is reported."""
        report = Report()
        for path, raw in sorted(files.items()):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                report.not_text.add(path)
                continue
            texts = [text]
            if path.endswith(".json"):
                try:
                    texts += _json_strings(json.loads(text), keys)
                except ValueError:
                    pass
            scope = "drafts" if path.startswith(root + "drafts/") else "other"
            for chunk in texts:
                for token in tokens(chunk):
                    if not self.candidate(token):
                        continue
                    klass, paths = self.classify(path, token)
                    report.add(scope, klass, path, token)
                    if klass == "cited":
                        report.cited[scope].update(paths)
        return report


def tracked(repo: Path, commit: str, prefix: str) -> list[str]:
    """Tracked file paths under ``prefix`` at ``commit``."""
    out = git(repo, "ls-tree", "-r", "--name-only", commit, "--", prefix).decode()
    return [line for line in out.splitlines() if line]


def tracked_dirs(repo: Path, commit: str, prefix: str) -> set[str]:
    """Tracked directories under ``prefix`` at ``commit``."""
    out = git(repo, "ls-tree", "-r", "-d", "--name-only", commit, "--", prefix).decode()
    return {line for line in out.splitlines() if line}


def run_root(repo: Path, commit: str, root: str, **kwargs: Any) -> Report:
    """Run the rule over one paper root at ``commit``, with the tracked results/ files as the registration set."""
    registered = tracked(repo, commit, "results/")
    extractor = Extractor(registered, tracked_dirs(repo, commit, "results/"), **kwargs)
    files = {path: git(repo, "show", f"{commit}:{path}") for path in tracked(repo, commit, root)}
    return extractor.scan(files, root)
