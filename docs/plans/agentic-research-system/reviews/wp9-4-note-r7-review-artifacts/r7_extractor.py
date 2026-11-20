# Research context: docs/plans/agentic-research-system/transition/w9/wp9-4-design-note.md (revision 7, §11.1, point I)
# Purpose: R7 review probe. The note's §11.1 citation rule as revision 7 (a7485bef) writes it, run on the §15
# extractor fixtures and, read-only through `git show`, over both paper roots. Deterministic; no seed.
"""The WP9.4 note's section 11.1 rule, revision 7, rebuilt from the note's text for the r7 review.

The r6 review's extractor (``r6_extractor.py`` on ``claude/review-w9-wp9-4-note-r6-d51c67``) was the starting point.
The change is revision 7's tail rule (R6-m2): "A tail is never a cited file by itself ... a tail is ``ambiguous`` when
any registered path ends in it, and a disambiguation row names its set; otherwise it is reported as ``not_a_file``."

The note gives two descriptions of a tail: "a token produced by a brace split" and "and so begins with ``/``". The
probe implements both and reports where they disagree:

- ``provenance``: the token immediately follows a ``}`` in the text (a brace split produced it);
- ``slash``: the token begins with ``/``.

Other reading choices, kept from r6: "a suffix of" at a path-component boundary; trailing ``.``/``:`` stripped
repeatedly; JSON values (not keys) scanned.

Run from the worktree root:
    uv run --env-file .env python docs/plans/agentic-research-system/reviews/wp9-4-note-r7-review-artifacts/r7_extractor.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

COMMIT = "a7485bef"
ROOTS = ("papers/P01-A-JRSSA/", "papers/P01-B-JRSSB/")
RESULT_EXTENSIONS = (".json", ".npy", ".npz", ".csv", ".pkl")
SEPARATORS = "`'\"()[]{}<>,;|*"
_SEP = re.compile(r"[\s" + re.escape(SEPARATORS) + r"]+")
_DATE_TEMPLATE = re.compile(r"YYYYMMDD|YYYY-MM-DD")


def git(repo: Path, *args: str) -> bytes:
    """One read-only Git command."""
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True).stdout


def tokens(text: str) -> list[tuple[str, bool]]:
    """Item 1, with provenance: (token, produced by a brace split, i.e. the separator run before it holds ``}``)."""
    text = re.sub(r"/{2,}", "/", text.replace("\\", "/"))
    out: list[tuple[str, bool]] = []
    position = 0
    previous_separator = ""
    for match in _SEP.finditer(text + " "):
        raw = text[position : match.start()]
        if raw:
            while raw and raw[-1] in ".:":
                raw = raw[:-1]
            if raw:
                out.append((raw, "}" in previous_separator))
        previous_separator = match.group(0)
        position = match.end()
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
    """Items 2 and 3, and the tail rule: cited file, then ``not_a_file``, then ``ambiguous``, then ``unregistered``."""

    def __init__(
        self,
        registered: list[str],
        directories: set[str] = frozenset(),
        *,
        tail_mode: str = "provenance",
        disambiguation: dict[tuple[str, str], Any] | None = None,
    ) -> None:
        self.registered = sorted(registered)
        self.directories = set(directories)
        self.tail_mode = tail_mode
        self.disambiguation = disambiguation or {}
        self.by_basename: dict[str, list[str]] = {}
        for path in self.registered:
            self.by_basename.setdefault(PurePosixPath(path).name, []).append(path)

    @staticmethod
    def _is_suffix(short: str, long: str) -> bool:
        short = short.lstrip("/")
        return long == short or long.endswith("/" + short)

    def candidate(self, token: str) -> bool:
        """Item 2."""
        return (
            "results/" in token
            or token.rsplit("/", 1)[-1] in self.by_basename
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

    def is_tail(self, token: str, after_brace: bool) -> bool:
        return after_brace if self.tail_mode == "provenance" else token.startswith("/")

    def _row(self, citing: str, token: str, default: str) -> tuple[str, list[str]]:
        row = self.disambiguation.get((citing, token))
        if row == "not_a_result":
            return "reported_not_a_result", []
        if row:
            return "cited", sorted(row)
        return default, []

    def classify(self, citing: str, token: str, after_brace: bool = False) -> tuple[str, list[str]]:
        """The class, and for a cited file the registered paths it means."""
        if self.is_tail(token, after_brace):
            # Revision 7: never cited by itself; ambiguous when any registered path ends in it, else not_a_file.
            if any(self._is_suffix(token, path) for path in self.registered):
                return self._row(citing, token, "ambiguous")
            return "not_a_file", []
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
            return self._row(citing, token, "ambiguous")
        if under_results or (not has_dir and token.lower().endswith(RESULT_EXTENSIONS)):
            return "unregistered", []
        return "no_class", []

    def scan(self, files: dict[str, bytes], root: str) -> dict[str, Any]:
        """Scan one root; ``drafts/`` blocks, the rest is reported."""
        out: dict[str, Any] = {"drafts": {}, "other": {}, "not_text": [], "cited": {"drafts": set(), "other": set()}}
        out["brace_split_tokens"] = set()
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
                for token, after_brace in tokens(chunk):
                    if not self.candidate(token):
                        continue
                    if after_brace or token.startswith("/"):
                        out["brace_split_tokens"].add((scope, path, token, after_brace, token.startswith("/")))
                    klass, paths = self.classify(path, token, after_brace)
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

C = "drafts/x.tex"


def fixtures() -> list[tuple[str, str, list[str], dict[tuple[str, str], Any], dict[str, str]]]:
    """Section 15's extractor fixtures at revision 7: (description, text, registered, rows, expected class by token)."""
    base = FIXTURE_REGISTERED
    one = ["results/x_bhps/a.json"]
    two = ["results/x_bhps/a.json", "results/x_usoc/a.json"]
    zzz = ["results/zzz/a.json"]
    return [
        ("path literal", "see results/a/unique.json here", base, {}, {"results/a/unique.json": "cited"}),
        ("JSON-escaped Windows path", "results\\\\a\\\\unique.json", base, {}, {"results/a/unique.json": "cited"}),
        ("unique basename", "unique.json", base, {}, {"unique.json": "cited"}),
        ("ambiguous basename, no row", "05_analysis.json", base, {}, {"05_analysis.json": "ambiguous"}),
        (
            "ambiguous basename, with row",
            "05_analysis.json",
            base,
            {(C, "05_analysis.json"): ["results/a/05_analysis.json"]},
            {"05_analysis.json": "cited"},
        ),
        ("unregistered results/ file", "results/a/missing.json", base, {}, {"results/a/missing.json": "unregistered"}),
        ("bare unregistered", "new_result.json", base, {}, {"new_result.json": "unregistered"}),
        ("directory", "results/a", base + ["results/a/z.txt"], {}, {"results/a": "not_a_file"}),
        ("trailing slash", "results/a/", base, {}, {"results/a/": "not_a_file"}),
        ("ordinary word", "analysis", base, {}, {}),
        ("LaTeX-wrapped path", "\\texttt{results/p/ph_L5000.json}", base, {}, {"results/p/ph_L5000.json": "cited"}),
        (
            "registered YYYYMMDD-like name",
            "results/x/level1_comparison_20260101.json",
            base,
            {},
            {"results/x/level1_comparison_20260101.json": "cited"},
        ),
        (
            "partial path, one hit",
            "trajectory_tda_integration/post_audit/04_one.json",
            base,
            {},
            {"trajectory_tda_integration/post_audit/04_one.json": "cited"},
        ),
        ("partial path, two hits", "post_audit/04_two.json", base, {}, {"post_audit/04_two.json": "ambiguous"}),
        (
            "tail, one registered",
            "results/x_{survey}/a.json",
            one,
            {},
            {"results/x_": "not_a_file", "/a.json": "ambiguous"},
        ),
        (
            "tail, two registered",
            "results/x_{survey}/a.json",
            two,
            {},
            {"results/x_": "not_a_file", "/a.json": "ambiguous"},
        ),
        (
            "tail, only zzz registered",
            "results/x_{survey}/a.json",
            zzz,
            {},
            {"results/x_": "not_a_file", "/a.json": "ambiguous"},
        ),
        (
            "tail, only zzz, cleared by a row",
            "results/x_{survey}/a.json",
            zzz,
            {(C, "/a.json"): ["results/zzz/a.json"]},
            {"results/x_": "not_a_file", "/a.json": "cited"},
        ),
        # As section 15 words it. The tail's basename is registered nowhere, so item 2 never makes it a candidate:
        # this fixture FAILS as written (finding R7-m3), because the tail is dropped, not reported.
        (
            "tail no registered path ends in (AS WRITTEN; basename unregistered)",
            "results/x_{survey}/b.json",
            zzz,
            {},
            {"results/x_": "not_a_file", "/b.json": "not_a_file"},
        ),
        (
            "tail no registered path ends in (basename registered elsewhere)",
            "results/x_{survey}/post/a.json",
            zzz,
            {},
            {"results/x_": "not_a_file", "/post/a.json": "not_a_file"},
        ),
        ("component boundary", "x/a.json", ["results/xx/a.json"], {}, {"x/a.json": "ambiguous"}),
        (
            "two tokens one basename, two token-keyed rows",
            "alias/05_analysis.json notes/05_analysis.json",
            base,
            {
                (C, "alias/05_analysis.json"): ["results/a/05_analysis.json"],
                (C, "notes/05_analysis.json"): "not_a_result",
            },
            {"alias/05_analysis.json": "cited", "notes/05_analysis.json": "reported_not_a_result"},
        ),
        ("filename template", "table1_effects_{date_suffix}.json", base, {}, {".json": "not_a_file"}),
        (
            "YYYYMMDD template",
            "level1_comparison_YYYYMMDD.json",
            base,
            {},
            {"level1_comparison_YYYYMMDD.json": "not_a_file"},
        ),
        ("lone .json", ".json", base, {}, {".json": "not_a_file"}),
        (
            "row with two paths for one basename",
            "05_analysis.json",
            base,
            {(C, "05_analysis.json"): ["results/a/05_analysis.json", "results/b/05_analysis.json"]},
            {"05_analysis.json": "cited"},
        ),
        ("notes copy, no row", "notes/data.json", base, {}, {"notes/data.json": "ambiguous"}),
        (
            "notes copy, not_a_result row",
            "notes/data.json",
            base,
            {(C, "notes/data.json"): "not_a_result"},
            {"notes/data.json": "reported_not_a_result"},
        ),
        ("backtick and pipe separators", "| `results/a/unique.json` |", base, {}, {"results/a/unique.json": "cited"}),
        ("cited .npy", "results/e/embed.npy", base, {}, {"results/e/embed.npy": "cited"}),
        # Review probes, not in section 15.
        (
            "PROBE: brace split, tail without '/'",
            "results/trajectory_tda_{survey}_nulls.json",
            ["results/trajectory_tda_bhps_nulls.json"],
            {},
            {"results/trajectory_tda_": "not_a_file", "_nulls.json": "?"},
        ),
        (
            "PROBE: absolute path not from a brace split",
            "/home/u/TDL/results/a/unique.json",
            base,
            {},
            {"/home/u/TDL/results/a/unique.json": "?"},
        ),
        (
            "PROBE: tail whose basename is registered elsewhere",
            "results/x_{s}/post/a.json",
            ["results/y/a.json"],
            {},
            {"results/x_": "not_a_file", "/post/a.json": "?"},
        ),
    ]


def run_fixtures() -> int:
    failures = 0
    print("== Section 15 extractor fixtures at revision 7 (and review probes, expected '?') ==")
    for mode in ("provenance", "slash"):
        print(f"-- tail_mode={mode}")
        for name, text, registered, rows, expected in fixtures():
            ex = Extractor(
                registered, {"results/a"} if name == "directory" else set(), tail_mode=mode, disambiguation=rows
            )
            got = {t: ex.classify(C, t, brace)[0] for t, brace in tokens(text) if ex.candidate(t)}
            probe = name.startswith("PROBE")
            ok = probe or got == expected
            failures += not ok
            tag = "probe" if probe else ("ok  " if ok else "FAIL")
            print(f"  {tag} {name}: {got}" + ("" if ok else f"  expected {expected}"))
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
        for mode in ("provenance", "slash"):
            ex = Extractor(registered, dirs, tail_mode=mode)
            rep = ex.scan(files, root)
            d = rep["drafts"]
            print(f"\n{root} (tail_mode={mode}): {len(paths)} files, not_text={len(rep['not_text'])}")
            print(f"  drafts: cited files={len(rep['cited']['drafts'])}")
            for klass in ("ambiguous", "unregistered", "not_a_file", "no_class", "reported_not_a_result"):
                names = sorted({t for _, t in d.get(klass, set())})
                print(f"  drafts {klass}: {len(names)} {names}")
            other = rep["other"]
            print("  other (reported): " + ", ".join(f"{k}={len({t for _, t in v})}" for k, v in sorted(other.items())))
            print("  candidate tokens after a brace or starting '/': (scope, file, token, after_brace, starts_slash)")
            for row in sorted(rep["brace_split_tokens"]):
                print(f"    {row}")


def main() -> int:
    failures = run_fixtures()
    run_roots(Path.cwd())
    print(f"\nfixture failures: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
