# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 6, §11.1, point I)
# Purpose: R6 review probe. The note's §11.1 citation rule as revision 6 (b13f1592) writes it, run on the §15
# extractor fixtures and, read-only through `git show`, over both paper roots. Deterministic; no seed.
"""The WP9.4 note's section 11.1 rule, revision 6, written fresh from the note's text for the r6 review.

The r5 review's extractor (``r5_extractor.py`` on ``claude/review-w9-wp9-4-note-r5-bdb004``) was read as a
reference only. Differences from it, each following revision 6's text:

- braces are not a template marker (revision 6 removed ``{`` and ``}`` from the ``not_a_file`` row);
- "ends in a registered result's basename" (item 2) is evaluated two ways, by last component and by plain string,
  and any difference is reported.

Reading choices the text leaves open are named where they are made:

- "a suffix of" is read at a path-component boundary, as revision 6 now says (R5-i4); a string reading is also run;
- "a trailing ``.`` or ``:`` is stripped" is applied repeatedly;
- "every decoded string value" of a ``.json`` file means values, not keys.

Run from the worktree root:
    uv run --env-file .env python docs/plans/agentic-research-system/reviews/wp9-4-note-r6-review-artifacts/r6_extractor.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

COMMIT = "b13f1592"
ROOTS = ("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/")
RESULT_EXTENSIONS = (".json", ".npy", ".npz", ".csv", ".pkl")
SEPARATORS = "`'\"()[]{}<>,;|*"
_SPLIT = re.compile(r"[\s" + re.escape(SEPARATORS) + r"]+")
_DATE_TEMPLATE = re.compile(r"YYYYMMDD|YYYY-MM-DD")


def git(repo: Path, *args: str) -> bytes:
    """One read-only Git command."""
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True).stdout


def tokens(text: str) -> list[str]:
    """Item 1: backslash read as slash, repeated slashes collapsed, split on whitespace and the separators."""
    text = re.sub(r"/{2,}", "/", text.replace("\\", "/"))
    out = []
    for raw in _SPLIT.split(text):
        while raw and raw[-1] in ".:":
            raw = raw[:-1]
        if raw:
            out.append(raw)
    return out


def _json_strings(node: Any) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        return [s for item in node for s in _json_strings(item)]
    if isinstance(node, dict):
        return [s for value in node.values() for s in _json_strings(value)]
    return []


class Extractor:
    """Items 2 and 3: cited file, then ``not_a_file``, then ``ambiguous``, then ``unregistered``."""

    def __init__(
        self,
        registered: list[str],
        directories: set[str] = frozenset(),
        *,
        suffix_mode: str = "component",
        basename_mode: str = "component",
        disambiguation: dict[tuple[str, str], Any] | None = None,
    ) -> None:
        self.registered = sorted(registered)
        self.directories = set(directories)
        self.suffix_mode = suffix_mode
        self.basename_mode = basename_mode
        self.disambiguation = disambiguation or {}
        self.by_basename: dict[str, list[str]] = {}
        for path in self.registered:
            self.by_basename.setdefault(PurePosixPath(path).name, []).append(path)

    def _is_suffix(self, short: str, long: str) -> bool:
        if self.suffix_mode == "string":
            return long.endswith(short)
        short = short.lstrip("/")
        return long == short or long.endswith("/" + short)

    def _ends_in_basename(self, token: str) -> bool:
        if self.basename_mode == "string":
            return any(token.endswith(name) for name in self.by_basename)
        return token.rsplit("/", 1)[-1] in self.by_basename

    def candidate(self, token: str) -> bool:
        """Item 2."""
        return (
            "results/" in token
            or self._ends_in_basename(token)
            or ("/" not in token and token.lower().endswith(RESULT_EXTENSIONS))
        )

    def _suffix_hits(self, token: str) -> list[str]:
        return [path for path in self.registered if self._is_suffix(token, path)]

    def _token_suffix_registered(self, token: str) -> str | None:
        parts = token.split("/")
        for start in range(len(parts)):
            tail = "/".join(parts[start:])
            if tail in self.registered:
                return tail
        return None

    def classify(self, citing: str, token: str) -> tuple[str, list[str]]:
        """The class, and for a cited file the registered paths it means."""
        has_dir = "/" in token
        under_results = "results/" in token
        hit = self._token_suffix_registered(token)
        if hit is not None:
            return "cited", [hit]
        if not has_dir and len(self.by_basename.get(token, [])) == 1:
            return "cited", list(self.by_basename[token])
        if has_dir and not under_results:
            hits = self._suffix_hits(token)
            if len(hits) == 1:
                return "cited", hits
        if under_results:
            tail = token[token.index("results/") :]
            if tail.endswith("/") or tail.rstrip("/") in self.directories or PurePosixPath(tail).suffix == "":
                return "not_a_file", []
        components = [c for c in token.split("/") if c]
        last = components[-1] if components else ""
        # The last component's stem is empty: ".json" (PurePosixPath reads a dotfile name as all stem).
        empty_stem = last.startswith(".") and last.count(".") == 1
        if any(_DATE_TEMPLATE.search(c) for c in components) or empty_stem:
            return "not_a_file", []
        ambiguous = False
        if not has_dir and len(self.by_basename.get(token, [])) > 1:
            ambiguous = True
        elif has_dir and not under_results:
            hits = self._suffix_hits(token)
            if len(hits) > 1 or (not hits and last in self.by_basename):
                ambiguous = True
        if ambiguous:
            row = self.disambiguation.get((citing, token))
            if row == "not_a_result":
                return "reported_not_a_result", []
            if row:
                return "cited", sorted(row)
            return "ambiguous", []
        if under_results or (not has_dir and token.lower().endswith(RESULT_EXTENSIONS)):
            return "unregistered", []
        return "no_class", []

    def scan(self, files: dict[str, bytes], root: str) -> dict[str, Any]:
        """Scan one root; ``drafts/`` blocks, the rest is reported."""
        out: dict[str, Any] = {"drafts": {}, "other": {}, "not_text": [], "cited": {"drafts": set(), "other": set()}}
        for path, raw in sorted(files.items()):
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                out["not_text"].append(path)
                continue
            chunks = [text]
            if path.endswith(".json"):
                try:
                    chunks += _json_strings(json.loads(text))
                except ValueError:
                    pass
            scope = "drafts" if path.startswith(root + "drafts/") else "other"
            for chunk in chunks:
                for token in tokens(chunk):
                    if not self.candidate(token):
                        continue
                    klass, paths = self.classify(path, token)
                    out[scope].setdefault(klass, set()).add((path, token))
                    if klass == "cited":
                        out["cited"][scope].update(paths)
        return out


FIXTURE_REGISTERED = [
    "results/a/unique.json",
    "results/a/05_analysis.json",
    "results/b/05_analysis.json",
    "results/x/level1_comparison_20260101.json",
    "results/trajectory_tda_integration/post_audit/04_one.json",
    "results/trajectory_tda_bhps/post_audit/04_two.json",
    "results/trajectory_tda_usoc/post_audit/04_two.json",
    "results/x/data.json",
    "results/p/ph_L5000.json",
    "results/e/embed.npy",
]


def fixtures() -> list[tuple[str, str, list[str], dict[str, str]]]:
    """Section 15's extractor fixtures: (description, text, registered, expected class by token)."""
    base = FIXTURE_REGISTERED
    return [
        ("path literal", "see results/a/unique.json here", base, {"results/a/unique.json": "cited"}),
        ("JSON-escaped Windows path", "results\\\\a\\\\unique.json", base, {"results/a/unique.json": "cited"}),
        ("unique basename", "unique.json", base, {"unique.json": "cited"}),
        ("ambiguous basename", "05_analysis.json", base, {"05_analysis.json": "ambiguous"}),
        ("unregistered results/ file", "results/a/missing.json", base, {"results/a/missing.json": "unregistered"}),
        ("bare unregistered", "new_result.json", base, {"new_result.json": "unregistered"}),
        ("directory", "results/a", base + ["results/a/z.txt"], {"results/a": "not_a_file"}),
        ("trailing slash", "results/a/", base, {"results/a/": "not_a_file"}),
        ("ordinary word", "analysis", base, {}),
        ("LaTeX-wrapped path", "\\texttt{results/p/ph_L5000.json}", base, {"results/p/ph_L5000.json": "cited"}),
        (
            "registered YYYYMMDD-like name",
            "results/x/level1_comparison_20260101.json",
            base,
            {"results/x/level1_comparison_20260101.json": "cited"},
        ),
        (
            "partial path, one hit",
            "trajectory_tda_integration/post_audit/04_one.json",
            base,
            {"trajectory_tda_integration/post_audit/04_one.json": "cited"},
        ),
        ("partial path, two hits", "post_audit/04_two.json", base, {"post_audit/04_two.json": "ambiguous"}),
        (
            "dir template, one registered",
            "results/x_{survey}/a.json",
            ["results/x_bhps/a.json"],
            {"results/x_": "not_a_file", "/a.json": "cited"},
        ),
        (
            "dir template, two registered",
            "results/x_{survey}/a.json",
            ["results/x_bhps/a.json", "results/x_usoc/a.json"],
            {"results/x_": "not_a_file", "/a.json": "ambiguous"},
        ),
        ("component boundary", "x/a.json", ["results/xx/a.json"], {"x/a.json": "ambiguous"}),
        ("filename template", "table1_effects_{date_suffix}.json", base, {".json": "not_a_file"}),
        (
            "YYYYMMDD template",
            "level1_comparison_YYYYMMDD.json",
            base,
            {"level1_comparison_YYYYMMDD.json": "not_a_file"},
        ),
        ("lone .json", ".json", base, {".json": "not_a_file"}),
        ("notes copy", "notes/data.json", base, {"notes/data.json": "ambiguous"}),
        ("backtick and pipe separators", "| `results/a/unique.json` |", base, {"results/a/unique.json": "cited"}),
        ("cited .npy", "results/e/embed.npy", base, {"results/e/embed.npy": "cited"}),
        # Not in section 15. The review's own probe of the template tail (R6-m2):
        (
            "PROBE: template tail, unrelated dir",
            "results/x_{survey}/a.json",
            ["results/zzz/a.json"],
            {"results/x_": "not_a_file", "/a.json": "cited"},
        ),
        (
            "PROBE: template tail, other parent",
            "results/x_{survey}/post/a.json",
            ["results/y/a.json"],
            {"results/x_": "not_a_file", "/post/a.json": "ambiguous"},
        ),
    ]


def run_fixtures() -> int:
    failures = 0
    print("== Section 15 extractor fixtures (and two review probes) ==")
    for name, text, registered, expected in fixtures():
        ex = Extractor(registered, {"results/a"} if name == "directory" else set())
        got = {t: ex.classify("drafts/x.tex", t)[0] for t in tokens(text) if ex.candidate(t)}
        ok = got == expected
        failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'} {name}: {got}" + ("" if ok else f"  expected {expected}"))
    # x/a.json: section 15 says "not matched as a suffix of results/xx/a.json"; it then falls to ambiguous by the
    # third ambiguous clause (ends in a registered basename, not a suffix). The fixture above records that.
    return failures


def run_roots(repo: Path) -> None:
    registered = [
        p for p in git(repo, "ls-tree", "-r", "--name-only", COMMIT, "--", "results/").decode().splitlines() if p
    ]
    dirs = {
        p for p in git(repo, "ls-tree", "-r", "-d", "--name-only", COMMIT, "--", "results/").decode().splitlines() if p
    }
    print(f"\n== Real roots at {COMMIT}, registration set = {len(registered)} tracked files under results/ ==")
    for root in ROOTS:
        paths = [p for p in git(repo, "ls-tree", "-r", "--name-only", COMMIT, "--", root).decode().splitlines() if p]
        files = {p: git(repo, "show", f"{COMMIT}:{p}") for p in paths}
        for suffix_mode, basename_mode in (
            ("component", "component"),
            ("string", "component"),
            ("component", "string"),
        ):
            ex = Extractor(registered, dirs, suffix_mode=suffix_mode, basename_mode=basename_mode)
            rep = ex.scan(files, root)
            d = rep["drafts"]
            print(
                f"\n{root} (suffix={suffix_mode}, basename={basename_mode}): {len(paths)} files, "
                f"not_text={len(rep['not_text'])}"
            )
            print(f"  drafts: cited files={len(rep['cited']['drafts'])}")
            for klass in ("ambiguous", "unregistered", "not_a_file", "no_class", "reported_not_a_result"):
                names = sorted({t for _, t in d.get(klass, set())})
                print(f"  drafts {klass}: {len(names)} {names}")
            leading = sorted({t for k in d for _, t in d[k] if t.startswith("/")} if d else [])
            print(f"  drafts tokens starting '/' (template tails): {leading}")
            other = rep["other"]
            print("  other (reported): " + ", ".join(f"{k}={len({t for _, t in v})}" for k, v in sorted(other.items())))
            other_leading = sorted({t for k in other for _, t in other[k] if t.startswith("/")})
            print(f"  other tokens starting '/': {other_leading}")


def main() -> int:
    failures = run_fixtures()
    run_roots(Path.cwd())
    print(f"\nfixture failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
