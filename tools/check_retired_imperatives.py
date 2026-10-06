#!/usr/bin/env python
"""Retirement gate: a document that declares itself superseded must quote its retired prose.

Why this exists
---------------
Research-observer observation ``2026-08-22-retired-procedure-kept-live-imperatives``
recorded the failure and its remedy: *"A warning does not make executable prose
historical."* The remedy was not applied, because the natural move when retiring a
plan is to add a banner and stop. Three independent authors did exactly that:

1. ``06p`` (2026-08-13) labelled its Jira operation section non-operative and left the
   instruction block underneath. It was resolved only by later deletion, in PR #259.
2. ``06s`` v2 Phase 0 step 4 instructed its executor to add "a superseded-by-06s banner
   line to 06q's header (no other 06q edits)" -- codifying the insufficient remedy in
   the successor plan itself.
3. PR #271 executed that step. Its whole 06q change is one banner line, and the banner
   even enumerates the imperatives it is failing to neutralise ("including its
   sole-authority, no-successor, retirement and fresh-live-SPEC-02 instructions"),
   leaving 480 lines of construction sequence readable as instructions.

Prose guidance had the diagnosis available in writing on all three occasions and did
not change the outcome, so this is the mechanical form of the same rule.

What it enforces
----------------
Two rules over Markdown plan documents in the scanned roots.

**R1 -- declaration required.** A document whose *header region* (everything before its
first ``## `` heading) says it is superseded, retired, non-operative, or historical must
carry a machine-readable ``retirement-scope`` declaration. Omitting the declaration is
the failure; declaring ``retired: []`` is a legitimate answer that the author has to
write down deliberately. Scoping the marker search to the header region is what keeps a
document that merely *mentions* supersession in a table row or a body paragraph out of
scope -- only a document making the claim about itself is captured.

**R2 -- declared scope must be quoted.** Every non-blank line inside a declared retired
span must be blockquoted, except the span's own opening heading, anything inside a
fenced code block, and anything inside a nested ``retained`` carve-out. Quoting, not
deleting: the retired text stays in the file as evidence of what was planned and why it
was replaced.

Carve-outs matter and are not a loophole. Retirement is per-claim, not per-heading: 06s
retires 06q section 4 as a construction sequence while explicitly keeping Step 5's
finite SPEC action composition as reference material, and blockquoting material that
executors are still instructed to read would degrade it. ``retained`` is how a document
says which sub-span survived.

Failure modes this deliberately does *not* try to catch
-------------------------------------------------------
It does not parse English for imperative mood. That would need a judgement call per
sentence and would produce a gate nobody trusts. It asks the cheaper, decisive
question instead: is the retired region marked as quotation? A quoted block cannot be
mistaken for an instruction regardless of the verbs inside it.

It also does not verify that a declared scope is *complete* -- an author who declares a
narrow ``retired`` span leaves the rest live by their own statement, which is a review
question, not a mechanical one.

Usage
-----
    python tools/check_retired_imperatives.py            # scan default roots
    python tools/check_retired_imperatives.py --root docs/plans/x

Exit status is 0 when clean and 1 when any document fails, so it is usable directly as
a gate. The bound test in tests/tools/test_retired_imperatives.py is the enforcing
artifact; this CLI is for running it by hand.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

# Where the rule applies. Kept narrow on purpose: these are the ARS implementation plans
# where supersession actually happens and where all three recorded instances occurred.
# Widening the scan is a one-line change plus whatever retrofit the new root needs.
DEFAULT_ROOTS = ("docs/plans/agentic-research-system/implementation",)

# Self-retirement vocabulary. `superseded` and `supersedes` are distinct words, which is
# what separates a retired document ("SUPERSEDED by 06s") from its successor
# ("Supersedes: 06q") -- the successor must not be captured by its own announcement.
RETIREMENT_MARKERS = (
    r"\bsuperseded\b",
    r"\bnon-operative\b",
    r"\bnonoperative\b",
    r"\bretired\b",
    r"\bhistorical baseline\b",
    r"\bno longer active\b",
)
_MARKER_RE = re.compile("|".join(RETIREMENT_MARKERS), re.IGNORECASE)

_DECLARATION_RE = re.compile(r"<!--\s*retirement-scope:(?P<body>.*?)-->", re.DOTALL)
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")

# The whole body after the header region, for a document retired in its entirety.
WHOLE_BODY = "*"


@dataclass(frozen=True)
class Finding:
    """One rule breach, addressed to whoever has to fix it."""

    path: str
    rule: str
    line: int | None
    message: str

    def render(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: [{self.rule}] {self.message}"


@dataclass(frozen=True)
class Span:
    """A half-open [start, end) line range, 0-indexed, opened by a heading."""

    label: str
    start: int
    end: int
    level: int


def _header_region(lines: list[str]) -> list[str]:
    """Everything before the first `## ` heading.

    A document's claim about its own status lives in its header block. Searching the
    whole file for retirement vocabulary would capture every plan that discusses another
    plan's retirement, which is most of them.
    """
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match and len(match.group("hashes")) == 2:
            return lines[:index]
    return lines


# Fields whose *value* is a claim about this document's own standing. Restricting the
# marker search to these is what separates "I am retired" from "I preserve someone
# else's retired evidence branches" -- 06s's `**Preserves:**` line contains the word
# "retired" while 06s is the live successor, and an unrestricted header scan
# misclassifies it. The header region alone is not a tight enough filter.
_SELF_STATUS_FIELDS = ("status", "authority")
_FIELD_RE = re.compile(r"^\*\*(?P<name>[^:*]+):?\*\*\s*(?P<value>.*)$")


def _self_status_text(lines: list[str]) -> str:
    """The parts of the header where a document speaks about its own standing.

    Three positions carry that claim in this repository's plans: the H1 title (often
    parenthesised, e.g. "(historical baseline)"), the value of a self-status field such
    as `**Status:**`, and a banner blockquote. Everything else in a header -- dates,
    bases, what the document preserves or supersedes -- describes other objects.
    """
    header = _header_region(lines)
    claims: list[str] = []
    current_field: str | None = None

    for line in header:
        heading = _HEADING_RE.match(line)
        if heading and len(heading.group("hashes")) == 1:
            claims.append(heading.group("text"))
            current_field = None
            continue

        if line.lstrip().startswith(">"):
            claims.append(line)
            current_field = None
            continue

        field = _FIELD_RE.match(line)
        if field:
            current_field = field.group("name").strip().lower()
            if any(current_field.startswith(name) for name in _SELF_STATUS_FIELDS):
                claims.append(field.group("value"))
            continue

        # A field's value may wrap onto following unprefixed lines.
        if current_field and any(current_field.startswith(name) for name in _SELF_STATUS_FIELDS):
            if line.strip():
                claims.append(line)
            else:
                current_field = None

    return "\n".join(claims)


def _fenced_line_numbers(lines: list[str]) -> set[int]:
    """Indices inside fenced code blocks, fence lines included.

    A fenced block is already verbatim: its contents cannot be read as live instructions
    to the same degree, and requiring `> ` inside one would corrupt the code it holds.
    """
    inside = False
    fenced: set[int] = set()
    for index, line in enumerate(lines):
        if _FENCE_RE.match(line):
            fenced.add(index)
            inside = not inside
            continue
        if inside:
            fenced.add(index)
    return fenced


def _resolve_span(lines: list[str], label: str, path: str) -> Span | list[Finding]:
    """Find the span opened by the heading `label`, running to the next same-or-higher heading.

    Fails loudly on a label that matches no heading or more than one. A declaration
    pointing at a heading that has since been renamed is exactly the silent-rot case
    this gate exists to prevent, so it must be an error and never a skip.
    """
    if label == WHOLE_BODY:
        header_length = len(_header_region(lines))
        return Span(label=label, start=header_length, end=len(lines), level=1)

    matches: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match and match.group("text").startswith(label.lstrip("# ").strip()):
            declared_level = len(label) - len(label.lstrip("#"))
            if declared_level and len(match.group("hashes")) != declared_level:
                continue
            matches.append((index, len(match.group("hashes"))))

    if not matches:
        return [
            Finding(
                path,
                "R2-scope",
                None,
                f"retirement-scope names heading {label!r}, which no heading in this "
                f"document matches. A renamed or deleted heading silently empties the "
                f"declared scope -- update the declaration or restore the heading.",
            )
        ]
    if len(matches) > 1:
        return [
            Finding(
                path,
                "R2-scope",
                matches[0][0] + 1,
                f"retirement-scope names heading {label!r}, which matches "
                f"{len(matches)} headings (lines "
                f"{', '.join(str(index + 1) for index, _ in matches)}). Make the label "
                f"unambiguous.",
            )
        ]

    start, level = matches[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        match = _HEADING_RE.match(lines[index])
        if match and len(match.group("hashes")) <= level:
            end = index
            break
    return Span(label=label, start=start, end=end, level=level)


def _parse_declaration(text: str, path: str) -> tuple[dict | None, list[Finding]]:
    match = _DECLARATION_RE.search(text)
    if match is None:
        return None, []
    try:
        parsed = yaml.safe_load(match.group("body"))
    except yaml.YAMLError as error:
        return None, [Finding(path, "R1-declaration", None, f"retirement-scope block is not valid YAML: {error}")]
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        return None, [Finding(path, "R1-declaration", None, "retirement-scope block must be a YAML mapping.")]
    unknown = set(parsed) - {"retired", "retained", "note"}
    if unknown:
        return None, [
            Finding(
                path,
                "R1-declaration",
                None,
                f"retirement-scope has unknown key(s) {sorted(unknown)}; allowed: retired, retained, note.",
            )
        ]
    return parsed, []


def check_document(path: str, text: str) -> list[Finding]:
    """Apply R1 and R2 to one document's source."""
    lines = text.split("\n")
    findings: list[Finding] = []

    declaration, parse_findings = _parse_declaration(text, path)
    findings.extend(parse_findings)
    if parse_findings:
        return findings

    # The declaration comment itself carries retirement vocabulary and sits in the
    # header, so strip it before looking for a self-retirement claim.
    status_text = _self_status_text(_DECLARATION_RE.sub("", text).split("\n"))
    claims_retirement = bool(_MARKER_RE.search(status_text))

    if claims_retirement and declaration is None:
        return [
            Finding(
                path,
                "R1-declaration",
                None,
                "the header declares this document superseded/retired/non-operative but "
                "there is no retirement-scope block. A banner does not make executable "
                "prose historical (obs 2026-08-22). Add:\n"
                "    <!-- retirement-scope:\n"
                "    retired:\n"
                '      - "## <heading whose body is retired>"\n'
                "    retained:\n"
                '      - "### <sub-heading the successor still cites>"\n'
                "    -->\n"
                "  and blockquote the retired spans. Declaring `retired: []` is a valid "
                "answer, but it has to be written down.",
            )
        ]

    if declaration is None:
        return findings

    retired_labels = declaration.get("retired") or []
    retained_labels = declaration.get("retained") or []
    if not isinstance(retired_labels, list) or not isinstance(retained_labels, list):
        return [Finding(path, "R1-declaration", None, "retired and retained must be lists of heading labels.")]

    # An empty scope is a legitimate answer -- a document can state that it is superseded
    # as an authority while containing no span of retired prose. It is also the obvious
    # way to neuter this gate, so it costs a written justification. Requiring the note
    # keeps `retired: []` a decision somebody made rather than the path of least
    # resistance, and leaves the reasoning in the file for whoever revisits it.
    if claims_retirement and not retired_labels and not str(declaration.get("note") or "").strip():
        return [
            Finding(
                path,
                "R1-declaration",
                None,
                "the header claims retirement and retirement-scope declares no retired span, "
                "so a `note:` is required saying why nothing needs quoting -- for example that "
                "the superseded item is an obligation or a status rather than a passage of "
                "prose in this file.",
            )
        ]

    retired_spans: list[Span] = []
    for label in retired_labels:
        resolved = _resolve_span(lines, str(label), path)
        if isinstance(resolved, list):
            findings.extend(resolved)
        else:
            retired_spans.append(resolved)

    retained_spans: list[Span] = []
    for label in retained_labels:
        resolved = _resolve_span(lines, str(label), path)
        if isinstance(resolved, list):
            findings.extend(resolved)
            continue
        if not any(span.start <= resolved.start and resolved.end <= span.end for span in retired_spans):
            findings.append(
                Finding(
                    path,
                    "R2-scope",
                    resolved.start + 1,
                    f"retained heading {resolved.label!r} is not inside any retired span, so it "
                    f"carves out nothing. Either it belongs in a retired span or the entry is stale.",
                )
            )
            continue
        retained_spans.append(resolved)

    if findings:
        return findings

    fenced = _fenced_line_numbers(lines)
    exempt_headings = {span.start for span in retired_spans} | {span.start for span in retained_spans}
    retained_lines = {index for span in retained_spans for index in range(span.start, span.end)}

    for span in retired_spans:
        for index in range(span.start, span.end):
            if index in exempt_headings or index in retained_lines or index in fenced:
                continue
            line = lines[index]
            if not line.strip() or line.lstrip().startswith(">"):
                continue
            findings.append(
                Finding(
                    path,
                    "R2-unquoted",
                    index + 1,
                    f"line is inside retired span {span.label!r} but is not quoted. Prefix it "
                    f"with '> ' so it reads as historical record, or carve its sub-heading out "
                    f"under `retained` if the successor still cites it.",
                )
            )

    return findings


def scan(roots: tuple[str, ...] = DEFAULT_ROOTS, repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Apply the rules to every Markdown document under `roots`."""
    findings: list[Finding] = []
    self_path = Path(__file__).resolve()
    for root in roots:
        base = repo_root / root
        if not base.exists():
            continue
        for markdown in sorted(base.rglob("*.md")):
            if markdown.resolve() == self_path:
                continue
            relative = markdown.relative_to(repo_root).as_posix()
            findings.extend(check_document(relative, markdown.read_text(encoding="utf-8")))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        help="Repo-relative directory to scan; repeatable. Defaults to the ARS implementation plans.",
    )
    args = parser.parse_args(argv)
    roots = tuple(args.roots) if args.roots else DEFAULT_ROOTS

    findings = scan(roots)
    if not findings:
        print(f"retirement gate: clean across {', '.join(roots)}")
        return 0

    print(f"retirement gate: {len(findings)} finding(s)\n", file=sys.stderr)
    for finding in findings:
        print(f"  {finding.render()}\n", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
